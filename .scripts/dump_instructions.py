"""Dump all pilot task instructions to a single text file for review."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\research\project-engiworld\Engiworld\task")
PILOT = [
    "task-c/abaqus",
    "task-c/autocad",
    "task-v/abaqus",
    "task-v/autocad",
]
OUT = Path(r"D:\research\project-engiworld\Engiworld\.scripts\pilot_instructions.txt")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for app in PILOT:
        app_dir = ROOT / app.replace("/", "\\")
        if not app_dir.exists():
            continue
        for task_dir in sorted(app_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            jsons = list(task_dir.glob("task-*.json"))
            if not jsons:
                continue
            jpath = jsons[0]
            try:
                obj = json.loads(jpath.read_text(encoding="utf-8"))
            except Exception as exc:
                lines.append(f"===== {app}/{task_dir.name} ===== [JSON ERROR: {exc}]")
                continue
            inst = obj.get("instruction", "")
            lines.append(f"===== {app}/{task_dir.name} =====")
            lines.append(inst)
            lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({sum(1 for _ in lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
