"""Run eval-vs-gt check just for archicad under task/task-c and task/task-v."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _check_eval_vs_gt import collect_tasks, run_eval

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v"),
]
APP = "archicad"

for root in ROOTS:
    bucket = root.parent.name + "/" + root.name
    print(f"\n=========== {bucket}/{APP} ===========")
    fails = []
    errors = []
    total = 0
    for task_dir, eval_py, gt_dir, init_dir in collect_tasks(root):
        rel = task_dir.relative_to(root).as_posix()
        if not rel.startswith(APP + "/"):
            continue
        total += 1
        verdict, stdout, stderr = run_eval(eval_py, gt_dir, init_dir)
        marker = {"True": ".", "False": "X", "error": "?"}[verdict]
        print(f"  {marker} {rel:<25} -> {verdict}")
        if verdict == "False":
            fails.append((rel, stdout, stderr))
        elif verdict == "error":
            errors.append((rel, stdout, stderr))

    good = total - len(fails) - len(errors)
    print(f"\n  Total: {total}, OK={good}, mismatch={len(fails)}, error={len(errors)}")

    if fails:
        print(f"\n  --- mismatches ---")
        for rel, sout, serr in fails:
            print(f"    {rel}")
            if serr:
                print(f"      stderr: {serr.splitlines()[-1][:160]}")
    if errors:
        print(f"\n  --- errors ---")
        for rel, sout, serr in errors:
            print(f"    {rel}")
            if serr:
                print(f"      stderr: {serr.splitlines()[-1][:160]}")
