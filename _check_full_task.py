"""Run eval-vs-gt check across the whole task/ directory (task-c + task-v)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _check_eval_vs_gt import collect_tasks, run_eval

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v"),
]


def main() -> None:
    summary: dict[str, list[dict]] = {}
    for root in ROOTS:
        bucket = root.parent.name + "/" + root.name
        tasks = list(collect_tasks(root))
        print(f"\n=== {bucket}: {len(tasks)} tasks ===", flush=True)
        results: list[dict] = []
        for idx, (task_dir, eval_py, gt_dir, init_dir) in enumerate(tasks, 1):
            verdict, stdout, stderr = run_eval(eval_py, gt_dir, init_dir)
            tag = task_dir.relative_to(root).as_posix()
            row = {
                "task": tag,
                "verdict": verdict,
                "stdout_tail": stdout[-400:],
                "stderr_tail": stderr[-400:],
            }
            results.append(row)
            marker = {"True": ".", "False": "X", "error": "?"}[verdict]
            print(f"[{idx:>3}/{len(tasks)}] {marker} {tag}", flush=True)
        summary[bucket] = results

    out = Path(r"d:/research/project-engiworld/Engiworld/_full_task_report.json")
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nReport written to: {out}")

    for bucket, rows in summary.items():
        good = sum(1 for r in rows if r["verdict"] == "True")
        bad = sum(1 for r in rows if r["verdict"] == "False")
        err = sum(1 for r in rows if r["verdict"] == "error")
        print(f"{bucket}: True={good}, False={bad}, error={err}, total={len(rows)}")


if __name__ == "__main__":
    main()
