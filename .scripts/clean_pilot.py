"""Pilot cleanup + mismatch scan for abaqus + autocad tasks.

Two passes:
1) Rule-based GUI/CLI removal in `instruction` field of task-*.json.
2) Compare instruction vs eval.py to flag obvious mismatches.

Default mode is DRY-RUN: writes proposed changes to a diff report, does not
modify files. Pass --apply to actually write the cleaned JSON back.
"""
from __future__ import annotations
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\research\project-engiworld\Engiworld\task")
PILOT = [
    "task-c/abaqus",
    "task-c/autocad",
    "task-v/abaqus",
    "task-v/autocad",
]
REPORT_DIR = Path(r"D:\research\project-engiworld\Engiworld\.scripts")
DIFF_FILE = REPORT_DIR / "pilot_diff.md"
MISMATCH_FILE = REPORT_DIR / "pilot_mismatch.md"

# ---- Rules ---------------------------------------------------------------

# Replacements applied in order. Each entry is (regex, replacement).
# Rules are intentionally precise to avoid over-deleting task content.
INSTRUCTION_RULES: list[tuple[str, str]] = [
    # abaqus leading phrases — strip "Use Abaqus/CAE via X to" and just
    # leave a capitalized verb.
    (r"Use Abaqus/CAE via the Command Line Interface \(CLI\) to ",
     ""),
    (r"Use Abaqus/CAE through the graphical user interface to ",
     ""),
    (r"Use the Abaqus/CAE GUI to ",
     ""),
    (r"Use Abaqus/CAE in GUI mode to ",
     ""),
    # parenthetical GUI annotation in section headers
    (r" \(key GUI operations\)", ""),

    # autocad task-c leading phrase
    (r"Use AutoCAD command line, Core Console, or an AutoCAD automation script\. ?",
     ""),
    # "Open only the DXF file(s) from the Desktop path(s): X. " -> "Read the DXF input file(s): X. "
    (r"Open only the DXF file\(s\) from the Desktop path\(s\): ",
     "Read the DXF input file(s): "),

    # autocad task-v "look at X. " -> "Read the DXF input file(s) X. "
    (r"^look at ",
     "Read the DXF input file(s) "),

    # generic mop-up: "via the Command Line Interface (CLI)" anywhere
    (r" via the Command Line Interface \(CLI\)", ""),
]


def capitalize_first_alpha(text: str) -> str:
    """Capitalize the first alphabetic character of a string."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
        if ch != " " and ch != "\t":
            return text
    return text


def clean_instruction(text: str) -> str:
    out = text
    for pattern, repl in INSTRUCTION_RULES:
        out = re.sub(pattern, repl, out, flags=re.MULTILINE)
    # Trim, capitalize first alphabetic character of the very first non-empty line.
    lines = out.split("\n")
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            lines[idx] = capitalize_first_alpha(line)
            break
    return "\n".join(lines)


# ---- Mismatch detection --------------------------------------------------

PLACEHOLDER_DXF_PATTERN = re.compile(
    r"DXF_SPECS\s*=\s*\[\s*\{\s*['\"]path['\"]\s*:\s*['\"]autocad_result\.dxf['\"]\s*,"
    r"\s*['\"]summary['\"]\s*:\s*\{\s*['\"]counts['\"]\s*:\s*"
    r"\{\s*['\"]LWPOLYLINE['\"]\s*:\s*1\s*,\s*['\"]TEXT['\"]\s*:\s*1\s*\}",
    re.DOTALL,
)


def detect_mismatch(task_dir: Path, instruction: str) -> str | None:
    """Return a short string describing a mismatch, or None."""
    eval_path = task_dir / "eval.py"
    if not eval_path.exists():
        return None
    try:
        eval_src = eval_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    issues: list[str] = []

    # Case 1: autocad placeholder eval that only checks 1 polyline + 1 text.
    m = PLACEHOLDER_DXF_PATTERN.search(eval_src)
    if m:
        # Extract the TASK NN text from the eval to confirm it is the placeholder.
        text_match = re.search(
            r"['\"]texts['\"]\s*:\s*\[\s*['\"](TASK[^'\"]*)['\"]\s*\]",
            eval_src,
        )
        text_required = text_match.group(1) if text_match else "(unknown)"
        # Heuristic: the instruction calls for "outlines, holes, slots,"
        # geometry intent — a real CAD recreation — but eval is the placeholder.
        if "outlines, holes, slots" in instruction or "Recreate" in instruction:
            issues.append(
                f"Eval is placeholder (LWPOLYLINE:1 + TEXT:1, layer 0, "
                f"text='{text_required}'); instruction asks to recreate a "
                f"complex 2D drawing"
            )

    return "; ".join(issues) if issues else None


# ---- Main ---------------------------------------------------------------

def iter_pilot_tasks():
    for app in PILOT:
        app_dir = ROOT / app.replace("/", "\\")
        if not app_dir.exists():
            continue
        for task_dir in sorted(app_dir.iterdir()):
            if not task_dir.is_dir() or task_dir.name == "ground_truth" or task_dir.name == "init_file":
                continue
            jsons = list(task_dir.glob("task-*.json"))
            if not jsons:
                continue
            yield app, task_dir, jsons[0]


def main(apply: bool) -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    diff_lines: list[str] = ["# Pilot instruction cleanup diff (DRY-RUN)\n"]
    mismatch_lines: list[str] = ["# Pilot instruction-vs-eval mismatch report\n"]
    changed = 0
    skipped = 0
    mismatches = 0

    for app, task_dir, jpath in iter_pilot_tasks():
        try:
            obj = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception as exc:
            diff_lines.append(f"## {app}/{task_dir.name}: JSON read error: {exc}\n")
            continue
        original = obj.get("instruction", "")
        cleaned = clean_instruction(original)
        rel = f"{app}/{task_dir.name}"

        if cleaned != original:
            changed += 1
            diff_lines.append(f"\n## {rel}\n")
            diff = difflib.unified_diff(
                original.splitlines(),
                cleaned.splitlines(),
                fromfile="before",
                tofile="after",
                lineterm="",
                n=1,
            )
            diff_lines.append("```diff")
            diff_lines.extend(list(diff))
            diff_lines.append("```\n")
            if apply:
                obj["instruction"] = cleaned
                jpath.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        else:
            skipped += 1

        # Mismatch detection (use cleaned instruction so we don't get tripped
        # up by the GUI/CLI prefix).
        issue = detect_mismatch(task_dir, cleaned)
        if issue:
            mismatches += 1
            mismatch_lines.append(f"- **{rel}**: {issue}")
            mismatch_lines.append(f"  - instruction (first 200 chars): "
                                  f"{cleaned[:200].replace(chr(10), ' / ')}")

    diff_lines.insert(
        1,
        f"\n_Total: changed={changed}, unchanged={skipped}, "
        f"apply={'YES' if apply else 'NO (dry-run)'}_\n",
    )
    mismatch_lines.insert(1, f"\n_Total mismatches: {mismatches}_\n")

    DIFF_FILE.write_text("\n".join(diff_lines), encoding="utf-8")
    MISMATCH_FILE.write_text("\n".join(mismatch_lines), encoding="utf-8")
    print(
        f"changed={changed}, unchanged={skipped}, mismatches={mismatches}; "
        f"apply={'YES' if apply else 'NO'}"
    )
    print(f"diff:     {DIFF_FILE}")
    print(f"mismatch: {MISMATCH_FILE}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Write cleaned JSON back to disk.")
    args = parser.parse_args()
    sys.exit(main(args.apply))
