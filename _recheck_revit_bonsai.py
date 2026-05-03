"""Re-check just bonsai + revit after the sync."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _check_eval_vs_gt import collect_tasks, run_eval

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
]
APPS = {"bonsai", "revit"}

for root in ROOTS:
    bucket = root.parent.name + "/" + root.name
    print(f"\n=== {bucket} ===")
    for task_dir, eval_py, gt_dir, init_dir in collect_tasks(root):
        rel = task_dir.relative_to(root).as_posix()
        if rel.split("/", 1)[0] not in APPS:
            continue
        verdict, stdout, stderr = run_eval(eval_py, gt_dir, init_dir)
        marker = {"True": ".", "False": "X", "error": "?"}[verdict]
        print(f"  {marker} {rel:<25} -> {verdict}")
        if verdict != "True" and stderr:
            print(f"     stderr: {stderr.splitlines()[-1][:160]}")
