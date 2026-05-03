"""Build the final comparison report.

Categorise every task into one of:
  - True       eval ran cleanly on the GT folder and printed True/true
  - mismatch   eval ran cleanly and printed False/false (real GT vs eval mismatch)
  - cli_skip   eval failed because an external CLI/lib was missing
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

REPORT = Path(r"d:/research/project-engiworld/Engiworld/_eval_vs_gt_report.json")
data = json.loads(REPORT.read_text(encoding="utf-8"))


def classify(row):
    if row["verdict"] == "True":
        return "True"
    if row["verdict"] == "False":
        return "mismatch"
    return "cli_skip"


def reason(row):
    err = row.get("stderr_tail") or ""
    if "cadquery" in err:
        return "missing cadquery (STEP)"
    if "pymupdf" in err or "fitz" in err:
        return "missing pymupdf"
    return err.splitlines()[-1][:120] if err else "(no stderr)"


for bucket, rows in data.items():
    print(f"\n{'='*70}\n{bucket}\n{'='*70}")
    by_app = defaultdict(Counter)
    for r in rows:
        by_app[r["task"].split("/", 1)[0]][classify(r)] += 1
    print(f"{'app':<20}{'OK':>5}{'mismatch':>10}{'cli_skip':>10}")
    for app in sorted(by_app):
        c = by_app[app]
        print(f"{app:<20}{c['True']:>5}{c['mismatch']:>10}{c['cli_skip']:>10}")

    print(f"\n--- mismatches in {bucket} ---")
    for r in rows:
        if classify(r) == "mismatch":
            print(f"  {r['task']}")

    print(f"\n--- cli_skip reasons in {bucket} ---")
    rc = Counter()
    for r in rows:
        if classify(r) == "cli_skip":
            rc[reason(r)] += 1
    for k, v in rc.most_common():
        print(f"  {v:>3}x  {k}")

# Final cross-bucket diff
gt = {r["task"]: classify(r) for r in data["task-gt/task-c"]}
tt = {r["task"]: classify(r) for r in data["task/task-c"]}
print(f"\n\n========== Tasks where task-gt != task verdict ==========")
for tag in sorted(set(gt) | set(tt)):
    if gt.get(tag) != tt.get(tag):
        print(f"  {tag:<35}  gt={gt.get(tag,'?'):<10}  task={tt.get(tag,'?'):<10}")
