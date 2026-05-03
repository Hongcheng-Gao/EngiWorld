"""Find every task-XX.json whose local_path contains backslashes.

These will fail on Linux because '\' is not a directory separator there;
they need to be normalized to forward slashes.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v"),
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-v"),
]


def has_backslash_local_path(data) -> bool:
    """Walk the task json and look for any 'local_path' value with '\\'."""
    if isinstance(data, dict):
        if isinstance(data.get("local_path"), str) and "\\" in data["local_path"]:
            return True
        return any(has_backslash_local_path(v) for v in data.values())
    if isinstance(data, list):
        return any(has_backslash_local_path(v) for v in data)
    return False


def collect_bad_local_paths(data, out: list[str]) -> None:
    if isinstance(data, dict):
        lp = data.get("local_path")
        if isinstance(lp, str) and "\\" in lp:
            out.append(lp)
        for v in data.values():
            collect_bad_local_paths(v, out)
    elif isinstance(data, list):
        for v in data:
            collect_bad_local_paths(v, out)


def main() -> None:
    grand_total_files = 0
    grand_bad_files = 0
    grand_bad_paths = 0
    by_root: dict[str, dict[str, int]] = {}
    bad_files_list: dict[str, list[Path]] = {}

    for root in ROOTS:
        bucket = f"{root.parent.name}/{root.name}"
        json_files = list(root.rglob("task-*.json"))
        json_files = [j for j in json_files if j.parent.name.startswith("task-")]
        bad_count_by_app: Counter = Counter()
        bad_files: list[Path] = []
        bad_paths_total = 0

        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            paths_in_file: list[str] = []
            collect_bad_local_paths(data, paths_in_file)
            if paths_in_file:
                bad_files.append(jf)
                bad_paths_total += len(paths_in_file)
                app = jf.parent.parent.name  # ".../app/task-XX/task-XX.json"
                bad_count_by_app[app] += 1

        by_root[bucket] = bad_count_by_app
        bad_files_list[bucket] = bad_files
        grand_total_files += len(json_files)
        grand_bad_files += len(bad_files)
        grand_bad_paths += bad_paths_total

        print(f"\n=== {bucket}: {len(json_files)} task jsons, {len(bad_files)} have backslash local_paths ({bad_paths_total} bad path strings) ===")
        for app, n in sorted(bad_count_by_app.items()):
            total_in_app = sum(1 for j in json_files if j.parent.parent.name == app)
            print(f"  {app:<22}  {n:>3}/{total_in_app:<3}")

    print(f"\n\nGrand total: {grand_bad_files}/{grand_total_files} task jsons need path normalization "
          f"({grand_bad_paths} backslash local_path strings).")


if __name__ == "__main__":
    main()
