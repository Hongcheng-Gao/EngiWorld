"""Scan task-v tasks for potential mismatches between what the instruction
asks the agent to save and what eval.py actually checks.

Checks performed:

1. Output-path mismatch:
   - Collect paths mentioned in the instruction that are introduced by "save/export/write/output/render to".
   - Collect paths referenced in eval.py (literal strings and spec dicts with "path"/"filename").
   - If an instruction output path's basename (and also full normalized path, when present) does not show up anywhere in eval.py text, flag it.
   - If eval.py references a non-input path (not in config.upload_file) that the instruction never asks the agent to produce, flag it too.

2. expected-string mismatch:
   - From task-XX.json: evaluator.expected.rules.expected
   - Try to derive what eval.py prints on success vs failure. If eval prints a string that doesn't match the expected (after normalising CRLF), flag it.

3. Sanity:
   - eval.py must exist.
   - Task JSON must parse.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"D:\research\project-engiworld\Engiworld\task\task-v")


# ---------- path extraction ----------

# Match Unix-absolute paths and Windows absolute paths
UNIX_PATH = re.compile(r"(/(?:home|root|tmp|mnt|opt|var)/[^\s'\"`<>\)\]\|]+)")
# Windows path, either single-backslash or escaped-backslash (C:\ or C:\\ form).
# Accept forward slashes too.
WIN_PATH = re.compile(r"([A-Za-z]:(?:\\\\|/|\\)[^\s'\"`<>\)\]\|]+)")


def _strip_trailing(p: str) -> str:
    return p.rstrip(".,;:)\"'`]}>")


def _normalize_path(p: str) -> str:
    """Normalize path to canonical form (single forward slashes, lowercased drive)."""
    p = _strip_trailing(p)
    p = p.replace("\\\\", "\\")
    p = p.replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = p[0].lower() + p[1:]
    return p


def extract_paths(text: str) -> list[tuple[int, int, str]]:
    """Return (start, end, raw) for all path-like matches."""
    results = []
    for m in UNIX_PATH.finditer(text):
        results.append((m.start(1), m.end(1), m.group(1)))
    for m in WIN_PATH.finditer(text):
        results.append((m.start(1), m.end(1), m.group(1)))
    return results


SAVE_KEYS = [
    r"\bexport\w*", r"\bsave\w*", r"\bwrite\w*", r"\boutput\w*",
    r"\bstore\b", r"\bstores\b", r"\bstored\b", r"\bstoring\b",
    r"\brender to\b", r"\brender out\b", r"\bdump\w*", r"\bemit\w*",
    r"\bproduce\w*", r"\bgenerate\w*", r"\bas\b",
]
SAVE_KEY_RE = re.compile("|".join(SAVE_KEYS), re.IGNORECASE)
READ_KEYS = [r"\bopen\w*", r"\bload\w*", r"\bimport\w*", r"\bread\w*", r"\bfrom\b", r"\bprovided\b", r"\binitial\b", r"\binput\b"]
READ_KEY_RE = re.compile("|".join(READ_KEYS), re.IGNORECASE)


def instruction_outputs(instruction: str) -> list[str]:
    """Paths that instruction tells the agent to create/write.

    Heuristic:
    - Any path whose basename starts with "output" or contains _output is an output.
    - Otherwise, require a save-keyword within ~80 chars before the path.
    - Exclude any path whose basename contains "_input" or "init_file".
    """
    outs = []
    for start, end, raw in extract_paths(instruction):
        p = _strip_trailing(raw)
        norm = _normalize_path(p)
        base = norm.rsplit("/", 1)[-1].lower()
        if "_input" in base or "init_file" in base:
            continue
        # Narrow context: look only between the previous path occurrence (or sentence start)
        # and this path, to avoid bleeding save-keywords from earlier sentences.
        left_bound = max(0, start - 120)
        # Trim back to nearest sentence boundary
        sub = instruction[left_bound:start]
        for sep in [". ", "? ", "! ", "\n\n", "\n", ";", "："]:
            idx = sub.rfind(sep)
            if idx != -1:
                left_bound = left_bound + idx + len(sep)
                sub = instruction[left_bound:start]
        ctx = instruction[left_bound:end]
        is_output = False
        is_input = False
        if "_output" in base or base.startswith("output."):
            is_output = True
        if base.startswith("init.") or base.startswith("input") or "_input" in base or "initial" in base:
            is_input = True
        if not is_input and SAVE_KEY_RE.search(ctx):
            is_output = True
        # But if in the SAME sentence there is both a read-keyword and a save-keyword,
        # prefer not to flag init-style filenames as outputs.
        if is_output and READ_KEY_RE.search(ctx) and base.startswith("init"):
            is_output = False
        if is_output:
            outs.append(norm)
    # dedupe, preserve order
    seen, ordered = set(), []
    for p in outs:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def instruction_inputs(instruction: str) -> list[str]:
    ins = []
    for start, end, raw in extract_paths(instruction):
        p = _strip_trailing(raw)
        norm = _normalize_path(p)
        base = norm.rsplit("/", 1)[-1].lower()
        ctx = instruction[max(0, start - 120):end]
        is_input = False
        if "_input" in base or base.startswith("init."):
            is_input = True
        elif READ_KEY_RE.search(ctx) and "_output" not in base:
            is_input = True
        if is_input:
            ins.append(norm)
    return sorted(set(ins))


# ---------- eval.py scanning ----------

SPEC_RE = re.compile(
    r"['\"](path|filename|file|name|output_path|out_path|dst|target|rel|relpath)['\"]\s*:\s*['\"]([^'\"]+)['\"]"
)

ROOT_VAR_RE = re.compile(
    r"(?P<var>[A-Z_][A-Z0-9_]*)\s*=\s*(?:Path\()?\s*r?['\"](?P<val>[^'\"]+)['\"]\)?"
)


BUNDLE_RE = re.compile(r"BUNDLE\s*=\s*\{([^}]+)\}", re.DOTALL)
B64_ENTRY_RE = re.compile(r"['\"]([^'\"]+\.py)['\"]\s*:\s*['\"]([A-Za-z0-9+/=]+)['\"]")


def _decode_bundle_text(eval_text: str) -> str:
    """If eval.py has a zlib+base64 BUNDLE, decode all .py entries and concatenate.

    Returns empty string if no bundle is present.
    """
    import base64, zlib

    bm = BUNDLE_RE.search(eval_text)
    if not bm:
        return ""
    out_parts = []
    for m in B64_ENTRY_RE.finditer(bm.group(1)):
        name, payload = m.group(1), m.group(2)
        try:
            raw = zlib.decompress(base64.b64decode(payload.encode("ascii")))
            out_parts.append(f"\n# --- bundle entry: {name} ---\n")
            out_parts.append(raw.decode("utf-8", errors="replace"))
        except Exception:
            continue
    return "".join(out_parts)


def collect_eval_paths(eval_text: str) -> dict:
    """Return dict with:
    - literal: set of normalized literal path strings found in eval.py
    - basenames: set of basenames referenced in the file (from literals and spec dicts)
    - root_vars: dict var->path value
    """
    literal = set()
    basenames = set()

    bundle_text = _decode_bundle_text(eval_text)
    combined = eval_text + "\n" + bundle_text

    for start, end, raw in extract_paths(combined):
        norm = _normalize_path(raw)
        literal.add(norm)
        basenames.add(norm.rsplit("/", 1)[-1].lower())

    for m in SPEC_RE.finditer(combined):
        val = m.group(2).strip()
        basenames.add(val.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower())

    # Capture obvious "filename" or "path" bare strings anywhere (just basenames)
    for m in re.finditer(r"['\"]([A-Za-z0-9_\-. /\\]+\.[A-Za-z0-9]{2,6})['\"]", combined):
        val = m.group(1).strip()
        basenames.add(val.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower())

    root_vars = {}
    for m in ROOT_VAR_RE.finditer(combined):
        val = m.group("val")
        if "/" in val or "\\" in val or ":" in val:
            root_vars[m.group("var")] = _normalize_path(val)

    return {"literal": literal, "basenames": basenames, "root_vars": root_vars, "has_bundle": bool(bundle_text)}


# ---------- expected string check ----------

PRINT_RE = re.compile(r"print\((.+)\)")


def derive_expected_output(eval_text: str) -> set[str]:
    """Return the set of strings eval.py might print on success.

    Supports the common patterns:
    - print(True if ok else False)          -> {"True"}
    - print("true" if _run() else "false")  -> {"true"}
    - print(result)
    - print("pass" if x else "fail")        -> {"pass"}

    Returns raw strings without trailing newline.
    """
    candidates: set[str] = set()
    for m in PRINT_RE.finditer(eval_text):
        expr = m.group(1).strip()
        # Pattern: A if cond else B
        ternary = re.match(r"^(.+?)\s+if\s+.+?\s+else\s+(.+)$", expr)
        if ternary:
            a = ternary.group(1).strip()
            candidates.add(_literal_strip(a))
            continue
        candidates.add(_literal_strip(expr))
    candidates.discard("")
    return candidates


def _literal_strip(expr: str) -> str:
    expr = expr.strip()
    if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
        return expr[1:-1]
    # True/False literal → Python's print outputs str(True)="True"
    if expr == "True":
        return "True"
    if expr == "False":
        return "False"
    return expr  # variable / expression we can't resolve; return as-is


# ---------- main scan ----------

def scan_task(task_json: Path) -> dict:
    rec = {"task": str(task_json.relative_to(ROOT)), "issues": []}
    try:
        raw = task_json.read_text(encoding="utf-8")
    except Exception as e:
        rec["issues"].append(f"JSON read error: {e}")
        return rec
    if raw.startswith("\ufeff"):
        rec["issues"].append("JSON-BOM  task file begins with UTF-8 BOM (may break strict json.load)")
        raw = raw.lstrip("\ufeff")
    try:
        data = json.loads(raw)
    except Exception as e:
        rec["issues"].append(f"JSON parse error: {e}")
        return rec

    instruction = data.get("instruction", "")
    inst_outs = instruction_outputs(instruction)
    inst_ins = instruction_inputs(instruction)

    # Config uploaded files are inputs
    config_inputs = set()
    for c in data.get("config", []) or []:
        if c.get("type") == "upload_file":
            for f in c.get("parameters", {}).get("files", []) or []:
                if "path" in f:
                    config_inputs.add(_normalize_path(f["path"]))

    eval_file = task_json.parent / "eval.py"
    if not eval_file.exists():
        rec["issues"].append("eval.py missing")
        return rec
    eval_text = eval_file.read_text(encoding="utf-8", errors="ignore")
    einfo = collect_eval_paths(eval_text)

    # 1) Each instruction output must be referenced by eval.py (by basename at least)
    # Precompute combined eval text (eval.py + decoded bundle) for fuzzy substring match
    combined_eval = eval_text + "\n" + _decode_bundle_text(eval_text)
    combined_lower = combined_eval.lower()
    for op in inst_outs:
        base = op.rsplit("/", 1)[-1].lower()
        if not base or "." not in base:
            continue
        if base in einfo["basenames"] or base in combined_lower:
            continue
        # Also try stem match (helpful when ext casing differs or path was concatenated)
        stem = base.rsplit(".", 1)[0]
        ext = base.rsplit(".", 1)[1]
        if stem in combined_lower and ext in combined_lower:
            # both pieces mentioned — still flag but marker weaker (we'll keep simple criterion)
            continue
        rec["issues"].append(
            f"INSTR-OUT-NOT-IN-EVAL  instruction wants to produce '{op}' but eval.py never references basename '{base}'"
        )

    # 2) Each eval output path (non-input) should be mentioned by instruction (by basename).
    # Filter eval literal paths: skip if it's a config input, or an obvious init/input/eval path.
    inst_out_bases = {p.rsplit("/", 1)[-1].lower() for p in inst_outs}
    inst_in_bases = {p.rsplit("/", 1)[-1].lower() for p in inst_ins}
    config_bases = {p.rsplit("/", 1)[-1].lower() for p in config_inputs}

    for lp in sorted(einfo["literal"]):
        base = lp.rsplit("/", 1)[-1].lower()
        if not base:
            continue
        if base in ("eval.py", "eval_inner.py"):
            continue
        # skip directory-only (no extension)
        if "." not in base:
            continue
        if base in config_bases or base in inst_in_bases:
            continue
        if "_input" in base or base.startswith("input") or "init" in base:
            continue
        if base in inst_out_bases:
            continue
        # Not input, not referenced by instruction → possibly check path agent never knew
        # Ignore common output-filename patterns if instruction has only one output
        # but that output differs: only flag when eval file clearly denotes it as a check
        rec["issues"].append(
            f"EVAL-CHECKS-UNMENTIONED  eval.py references '{lp}' (basename '{base}') that instruction does not mention as output/input"
        )

    # 3) expected-string check
    expected = (
        data.get("evaluator", {})
        .get("expected", {})
        .get("rules", {})
        .get("expected")
    )
    if expected is not None:
        exp_norm = expected.replace("\r", "").replace("\n", "").strip()
        cands = derive_expected_output(eval_text)
        cands_norm = {c.strip() for c in cands}
        # If we couldn't resolve to literals (e.g. ternary returned the var expression), skip
        resolvable = {c for c in cands_norm if c in ("true", "True", "false", "False", "PASS", "FAIL", "pass", "fail", "1", "0")}
        if resolvable and exp_norm not in resolvable:
            rec["issues"].append(
                f"EXPECTED-MISMATCH  task expects {expected!r}; eval.py print() yields one of {sorted(resolvable)}"
            )

    rec["inst_outs"] = inst_outs
    rec["inst_ins"] = inst_ins
    rec["config_inputs"] = sorted(config_inputs)
    return rec


def main():
    tasks = sorted(ROOT.rglob("task-*.json"))
    print(f"Found {len(tasks)} tasks")

    reports = []
    by_issue_type = defaultdict(list)
    for jf in tasks:
        r = scan_task(jf)
        if r.get("issues"):
            reports.append(r)
            for issue in r["issues"]:
                typ = issue.split()[0]
                by_issue_type[typ].append(r["task"])

    out = ROOT.parent.parent / "scan_tasks_report.json"
    out.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Tasks with issues: {len(reports)}")
    print(f"Report: {out}")
    print("\nIssue count by type:")
    for typ, lst in sorted(by_issue_type.items(), key=lambda x: -len(x[1])):
        print(f"  {typ}: {len(lst)}")

    # Summary grouped by app
    app_issues = defaultdict(int)
    for r in reports:
        app = r["task"].split("\\")[0].split("/")[0]
        app_issues[app] += 1
    print("\nIssue count by app:")
    for app, n in sorted(app_issues.items(), key=lambda x: -x[1]):
        print(f"  {app}: {n}")


if __name__ == "__main__":
    main()
