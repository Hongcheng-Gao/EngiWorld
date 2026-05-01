"""Scan for case-mismatch between instruction paths and eval references (Linux case-sensitive concern)."""
import sys, json
sys.path.insert(0, r"D:\research\project-engiworld\Engiworld")
import scan_tasks as s
from pathlib import Path

root = Path(r"D:\research\project-engiworld\Engiworld\task\task-v")

def strip_trailing(p):
    return p.rstrip(".,;:)\"'`]>}")

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
    bt = s._decode_bundle_text(et)
    combined = et + "\n" + bt

    # only Linux tasks matter for case
    is_linux = "/home/user/" in data.get("instruction", "")
    if not is_linux:
        continue

    inst = data.get("instruction", "")
    for _, _, raw in s.extract_paths(inst):
        p = strip_trailing(raw).replace("\\\\", "\\").replace("\\", "/")
        base_orig = p.rsplit("/", 1)[-1]
        if "." not in base_orig:
            continue
        if base_orig in combined:
            continue
        if base_orig.lower() in combined.lower():
            idx = combined.lower().find(base_orig.lower())
            actual = combined[idx:idx + len(base_orig)]
            if actual != base_orig:
                issues.append((str(jf.relative_to(root)), base_orig, actual))

print(f"Linux case-mismatch candidates: {len(issues)}")
for it in issues:
    print("  ", it)
