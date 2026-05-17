"""Strip [Software] suffix from task-v instructions; restore `source` from git HEAD for task-c and task-v."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SOFTWARE_MARK = "[Software]"
SOFTWARE_SEP = f" {SOFTWARE_MARK} "


def strip_software_suffix(instruction: str) -> str:
    s = instruction
    if "\n\n[Software] " in s:
        return s.split("\n\n[Software] ", 1)[0].strip()
    if SOFTWARE_SEP in s:
        return s.split(SOFTWARE_SEP, 1)[0].strip()
    return s.strip()


def git_show_head(rel_posix: str) -> dict | None:
    try:
        raw = subprocess.check_output(
            ["git", "show", f"HEAD:{rel_posix}"],
            cwd=REPO,
            stderr=subprocess.DEVNULL,
        )
        return json.loads(raw.decode("utf-8"))
    except (subprocess.CalledProcessError, json.JSONDecodeError, OSError):
        return None


def iter_task_json(task_root: Path):
    for path in sorted(task_root.rglob("task-*.json")):
        if path.parent.name != path.stem:
            continue
        if "ground_truth" in path.parts:
            continue
        yield path


def main() -> int:
    task_c = REPO / "task" / "task-c"
    task_v = REPO / "task" / "task-v"

    stripped_v = 0
    restored_src = 0

    for path in iter_task_json(task_v):
        data = json.loads(path.read_text(encoding="utf-8"))
        inst = data.get("instruction")
        if not isinstance(inst, str):
            continue
        new_inst = strip_software_suffix(inst)
        if new_inst == inst:
            continue
        data["instruction"] = new_inst
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stripped_v += 1

    for task_root in (task_c, task_v):
        if not task_root.is_dir():
            continue
        for path in iter_task_json(task_root):
            rel = path.relative_to(REPO).as_posix()
            head = git_show_head(rel)
            if not head:
                continue
            head_src = head.get("source")
            if not isinstance(head_src, str):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            cur = data.get("source")
            if cur == head_src:
                continue
            data["source"] = head_src
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            restored_src += 1

    print("task-v [Software] stripped:", stripped_v)
    print("source restored from HEAD:", restored_src)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
