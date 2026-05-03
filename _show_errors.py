"""Print stderr/stdout for specific failing tasks."""

import json
from pathlib import Path

REPORT = Path(r"d:/research/project-engiworld/Engiworld/_eval_vs_gt_report.json")
data = json.loads(REPORT.read_text(encoding="utf-8"))

WANT_PREFIXES = (
    "kicad/task-01",
    "openstudio/task-01",
    "openstudio/task-02",
    "sketchup/task-01",
    "sketchup/task-15",
    "bonsai/task-09",
    "eagle/task-05",
    "eagle/task-16",
    "revit/task-04",
    "revit/task-17",
    "revit/task-19",
    "revit/task-20",
)

for bucket, rows in data.items():
    print(f"\n========== {bucket} ==========")
    for r in rows:
        if any(r["task"].startswith(p) for p in WANT_PREFIXES):
            print(f"--- {r['task']} verdict={r['verdict']} ---")
            if r.get("stderr_tail"):
                print("  stderr:", r["stderr_tail"][-300:])
            if r.get("stdout_tail"):
                print("  stdout:", r["stdout_tail"][-300:])
