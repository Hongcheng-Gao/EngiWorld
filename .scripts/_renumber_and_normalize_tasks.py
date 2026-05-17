"""Normalize evaluator expected CRLF and compact task indices.

Run from repo root:

    python .scripts/_renumber_and_normalize_tasks.py
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"


def task_dir(n: int) -> str:
    return f"task-{n:02d}"


def normalize_expected_crlf() -> int:
    n = 0
    for p in TASK.rglob("*.json"):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        # JSON source uses escaped CRLF as literal \\r\\n (four chars), not U+000D U+000A.
        if '"expected": "True\\r\\n"' not in text:
            continue
        p.write_text(
            text.replace('"expected": "True\\r\\n"', '"expected": "True\\n"'),
            encoding="utf-8",
        )
        n += 1
    return n


def replace_task_tokens_per_dest_folders(
    app_root: Path, old_to_new: dict[int, int]
) -> None:
    """Only replace task-OLD -> task-NEW inside each destination task-NEW folder.

    Global descending replace breaks Revit (e.g. 15->13 then 13->11 rewrites
    legitimate task-13 paths).
    """
    exts = {
        ".json",
        ".py",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".csv",
        ".sch",
        ".brd",
        ".scr",
        ".cam",
        ".dru",
        ".sym",
    }
    new_to_old = {new: old for old, new in old_to_new.items()}
    for new_num, old_num in sorted(new_to_old.items()):
        if old_num == new_num:
            continue
        dest = app_root / task_dir(new_num)
        if not dest.is_dir():
            continue
        for path in dest.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in exts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            new_text = text.replace(task_dir(old_num), task_dir(new_num))
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")


def renumber_app(app_rel: str, old_nums: list[int]) -> None:
    app_root = TASK / app_rel.replace("/", os.sep)
    if not app_root.is_dir():
        print(f"SKIP missing {app_root}")
        return
    old_nums = sorted(old_nums)
    first_old = app_root / task_dir(old_nums[0])
    if not first_old.is_dir() and (app_root / task_dir(1)).is_dir():
        print(f"SKIP already compacted {app_rel}")
        return
    old_to_new = dict(zip(old_nums, range(1, len(old_nums) + 1)))
    if all(old_to_new[o] == o for o in old_nums):
        print(f"OK (no renames) {app_rel}")
        return

    staging = app_root / "_renumber_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    for old in old_nums:
        src = app_root / task_dir(old)
        if not src.is_dir():
            print(f"WARN missing {src}")
            continue
        shutil.move(str(src), str(staging / f"_t_{old:04d}"))

    for old in old_nums:
        new = old_to_new[old]
        mid = staging / f"_t_{old:04d}"
        if not mid.is_dir():
            continue
        inner_old = mid / f"{task_dir(old)}.json"
        inner_new = mid / f"{task_dir(new)}.json"
        if inner_old.exists() and inner_old != inner_new:
            if inner_new.exists():
                inner_new.unlink()
            inner_old.rename(inner_new)
        dst = app_root / task_dir(new)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(mid), str(dst))

    staging.rmdir()
    replace_task_tokens_per_dest_folders(app_root, old_to_new)
    print(f"DONE {app_rel}")


def renumber_revit_tail() -> None:
    revit_root = TASK / "task-v" / "revit"
    if not revit_root.is_dir():
        return
    # After compaction, folder task-18 is gone (was renamed to task-16).
    if not (revit_root / task_dir(18)).is_dir():
        print("SKIP task-v/revit (already compacted)")
        return
    staging = revit_root / "_renumber_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    moves = [(13, 11), (14, 12), (15, 13), (16, 14), (17, 15), (18, 16)]
    for old, _ in moves:
        shutil.move(str(revit_root / task_dir(old)), str(staging / f"_t_{old:04d}"))
    for old, new in moves:
        mid = staging / f"_t_{old:04d}"
        if not mid.is_dir():
            continue
        inner_old = mid / f"{task_dir(old)}.json"
        inner_new = mid / f"{task_dir(new)}.json"
        if inner_old.exists():
            if inner_new.exists():
                inner_new.unlink()
            inner_old.rename(inner_new)
        dst = revit_root / task_dir(new)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(mid), str(dst))
    staging.rmdir()
    m = {13: 11, 14: 12, 15: 13, 16: 14, 17: 15, 18: 16}
    replace_task_tokens_per_dest_folders(revit_root, m)
    print("DONE task-v/revit (13-18 -> 11-16)")


def main() -> None:
    n = normalize_expected_crlf()
    print(f"expected True\\r\\n -> True\\n: {n} files under task/")

    r21_40 = list(range(21, 41))
    for rel in (
        "task-c/autocad",
        "task-c/brl-cad",
        "task-c/freecad",
        "task-c/freecad-path",
        "task-c/nx-cam",
        "task-c/openscad",
        "task-c/solidcam",
        "task-c/solidworks",
    ):
        renumber_app(rel, r21_40)

    renumber_app("task-v/altium-designer", list(range(26, 51)))
    renumber_app("task-v/eagle", list(range(26, 51)))
    renumber_app("task-v/kicad", list(range(26, 51)))
    renumber_app("task-v/cadence-orcad", list(range(31, 61)))
    renumber_revit_tail()
    print("Finished.")


if __name__ == "__main__":
    main()
