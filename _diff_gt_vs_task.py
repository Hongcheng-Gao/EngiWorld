"""Compare files between task-gt/task-c/<app>/<task> and task/task-c/<app>/<task>."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT_GT = Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c")
ROOT_T = Path(r"d:/research/project-engiworld/Engiworld/task/task-c")
REPORT_PATH = Path(r"d:/research/project-engiworld/Engiworld/_eval_vs_gt_report.json")

report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
gt_rows = {r["task"]: r["verdict"] for r in report["task-gt/task-c"]}
t_rows = {r["task"]: r["verdict"] for r in report["task/task-c"]}


def file_hash(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hashlib.md5(path.read_bytes()).hexdigest()


def collect_files(base: Path) -> dict[str, str]:
    out = {}
    for p in base.rglob("*"):
        if p.is_file():
            out[p.relative_to(base).as_posix()] = file_hash(p)
    return out


print("Tasks where verdict differs between task-gt and task:")
print(f"{'task':<40}{'task-gt':<10}{'task':<10}")
diff_tasks = []
for tag in sorted(set(gt_rows) | set(t_rows)):
    if gt_rows.get(tag) != t_rows.get(tag):
        diff_tasks.append(tag)
        print(f"  {tag:<38}{gt_rows.get(tag,'-'):<10}{t_rows.get(tag,'-'):<10}")

print(f"\nTotal tasks where verdict differs: {len(diff_tasks)}")

print("\n\nFor those tasks, list file-content differences:")
for tag in diff_tasks:
    gt_dir = ROOT_GT / tag
    t_dir = ROOT_T / tag
    gt_files = collect_files(gt_dir)
    t_files = collect_files(t_dir)
    keys = sorted(set(gt_files) | set(t_files))
    diffs = [k for k in keys if gt_files.get(k) != t_files.get(k)]
    if diffs:
        print(f"\n--- {tag} ---")
        for k in diffs:
            print(f"  {k}")
            print(f"    gt:   {gt_files.get(k, 'MISSING')}")
            print(f"    task: {t_files.get(k, 'MISSING')}")
