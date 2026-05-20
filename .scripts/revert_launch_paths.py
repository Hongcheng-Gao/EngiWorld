"""Revert launch paths per user correction; remove launch from task-c abaqus/ansys."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"

ABAQUS_V = [
    r"C:\SIMULIA\CAE\2025LE\win_b64\resources\install\le\launcher.bat",
    "cae",
]
ANSYS261 = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
ANSYS261_G = [ANSYS261, "-g"]
ANSYS261_G_NP = [ANSYS261, "-g", "-np", "2"]
FLUENT261 = [
    r"C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe",
    "-g",
]


def remove_launch(obj: dict) -> bool:
    cfg = obj.get("config", [])
    new_cfg = [c for c in cfg if c.get("type") != "launch"]
    if len(new_cfg) == len(cfg):
        return False
    obj["config"] = new_cfg
    return True


def set_launch(obj: dict, command: list[str]) -> None:
    for c in obj.get("config", []):
        if c.get("type") == "launch":
            c["parameters"]["command"] = command
            return
    raise RuntimeError("no launch block")


def ansys_v_command(inst: str, task_name: str) -> list[str]:
    if "fluent" in inst.lower()[:250]:
        return FLUENT261
    if task_name == "task-01":
        return ANSYS261_G_NP
    return ANSYS261_G


def main() -> None:
    removed = 0
    fixed_v = 0
    for top, app in (("task-c", "abaqus"), ("task-c", "ansys")):
        root = TASK / top / app
        for jpath in sorted(root.glob("task-*/task-*.json")):
            obj = json.loads(jpath.read_text(encoding="utf-8"))
            if remove_launch(obj):
                jpath.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                removed += 1
                print("removed launch", jpath.relative_to(REPO))

    for app in ("abaqus", "ansys"):
        root = TASK / "task-v" / app
        for jpath in sorted(root.glob("task-*/task-*.json")):
            obj = json.loads(jpath.read_text(encoding="utf-8"))
            if app == "abaqus":
                cmd = ABAQUS_V
            else:
                cmd = ansys_v_command(obj.get("instruction", ""), jpath.parent.name)
            set_launch(obj, cmd)
            jpath.write_text(
                json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            fixed_v += 1
            print("fixed v", jpath.relative_to(REPO), cmd[0][:50])

    print(f"done: removed={removed}, fixed_v={fixed_v}")


if __name__ == "__main__":
    main()
