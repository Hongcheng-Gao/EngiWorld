"""Fix double-escaped backslashes in abaqus/ansys launch commands."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"

ABAQUS_LAUNCH_CMD = [
    r"C:\SIMULIA\EstProducts\2023\win_b64\resources\install\cmdDirFeature\launcher.bat",
    "cae",
]

ANSYS_RUNWB2 = [r"C:\Program Files\ANSYS Inc\v241\Framework\bin\Win64\runwb2.exe"]
ANSYS_APDL = [r"C:\Program Files\ANSYS Inc\v241\v241\ansys\bin\Win64\ANSYS241.exe", "-g"]
ANSYS_APDL_NP = [
    r"C:\Program Files\ANSYS Inc\v241\v241\ansys\bin\Win64\ANSYS241.exe",
    "-g",
    "-np",
    "2",
]
ANSYS_FLUENT = [r"C:\Program Files\ANSYS Inc\v241\fluent\ntbin\win64\fluent.exe", "-g"]


def ansys_cmd(inst: str, task_name: str, top: str) -> list[str]:
    low = inst.lower()
    if "fluent" in low[:200]:
        return ANSYS_FLUENT
    if "workbench" in low[:200]:
        return ANSYS_RUNWB2
    if top == "task-v" and task_name == "task-01":
        return ANSYS_APDL_NP
    return ANSYS_APDL


def main() -> None:
    n = 0
    for app in ("abaqus", "ansys"):
        for top in ("task-c", "task-v"):
            root = TASK / top / app
            if not root.is_dir():
                continue
            for jpath in sorted(root.glob("task-*/task-*.json")):
                obj = json.loads(jpath.read_text(encoding="utf-8"))
                inst = obj.get("instruction", "")
                if app == "abaqus":
                    new_cmd = ABAQUS_LAUNCH_CMD
                else:
                    new_cmd = ansys_cmd(inst, jpath.parent.name, top)
                changed = False
                for c in obj.get("config", []):
                    if c.get("type") == "launch":
                        if c["parameters"]["command"] != new_cmd:
                            c["parameters"]["command"] = new_cmd
                            changed = True
                if changed:
                    jpath.write_text(
                        json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    n += 1
                    print("fixed", jpath.relative_to(REPO))
    print("total", n)


if __name__ == "__main__":
    main()
