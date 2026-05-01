"""Find tasks where eval.py references an output file that the instruction does NOT mention."""
import sys, json
sys.path.insert(0, r"D:\research\project-engiworld\Engiworld")
import scan_tasks as s
from pathlib import Path


def strip_trailing(p):
    return p.rstrip(".,;:)\"'`]}>")


def norm_path(p):
    p = strip_trailing(p).replace("\\\\", "\\").replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = p[0].lower() + p[1:]
    return p


def instr_bases(text):
    bases = set()
    for _, _, raw in s.extract_paths(text):
        n = norm_path(raw)
        bases.add(n.rsplit("/", 1)[-1].lower())
    # also: mention of just the filename anywhere (backtick-wrapped or otherwise)
    import re
    for m in re.finditer(r"`([A-Za-z0-9_./\-]+\.[A-Za-z0-9]{2,8})`", text):
        bases.add(m.group(1).rsplit("/", 1)[-1].lower())
    return bases


root = Path(r"D:\research\project-engiworld\Engiworld\task\task-v")
issues = []
for jf in root.rglob("task-*.json"):
    try:
        data = json.loads(jf.read_text(encoding="utf-8-sig"))
    except Exception:
        continue
    ep = jf.parent / "eval.py"
    if not ep.exists():
        continue
    et = ep.read_text(encoding="utf-8", errors="ignore")
    combined = et + "\n" + s._decode_bundle_text(et)
    config_bases = set()
    for c in data.get("config", []) or []:
        if c.get("type") == "upload_file":
            for f in c.get("parameters", {}).get("files", []) or []:
                if "path" in f:
                    config_bases.add(norm_path(f["path"]).rsplit("/", 1)[-1].lower())
    instr = data.get("instruction", "")
    ibases = instr_bases(instr)
    # skip files present as ground-truth fixtures in the bundle (their names show up there, so won't be flagged)

    # collect eval paths (only those under a known desktop-style prefix)
    import re
    evp = set()
    for _, _, raw in s.extract_paths(combined):
        n = norm_path(raw)
        if "/desktop/" in n.lower() or "/home/user/" in n.lower():
            b = n.rsplit("/", 1)[-1].lower()
            if "." in b and b not in ("eval.py", "eval_inner.py"):
                evp.add((b, n))
    # also capture bare filenames coerced with DESKTOP / paths inside bundle
    for m in re.finditer(r"['\"]([A-Za-z0-9_\-]+\.[A-Za-z0-9]{2,8})['\"]", combined):
        b = m.group(1).lower()
        if b.endswith(".py") or b in ("eval.py", "eval_inner.py"):
            continue
        evp.add((b, m.group(1)))

    uncovered = []
    for base, norm in evp:
        if base in config_bases:
            continue
        if base in ibases:
            continue
        stem = base.rsplit(".", 1)[0]
        if stem and (stem in instr.lower()):
            continue
        # some scaffolding names to ignore
        if base in {"requirements.txt", "__init__.py", "eval.json", "ground_truth.json"}:
            continue
        uncovered.append((base, norm))
    if uncovered:
        issues.append((str(jf.relative_to(root)), uncovered))

print(f"Tasks where eval references a file name not mentioned in instruction: {len(issues)}")
for t, u in issues[:80]:
    print(" ", t)
    for b, n in u[:6]:
        print("      ", b, "<-", n)
