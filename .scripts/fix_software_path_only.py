"""Replace only the path inside [Software] backticks; keep prefix/suffix unchanged."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"

# Original [Software] lead-in before path-only fix (all task-c ansys used Workbench wording).
ANSYS_PREFIX = "[Software] To start ANSYS Workbench, run `"
ANSYS_SUFFIX = "` (version/path may differ on your machine)."

ANSYS261 = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe -g"
FLUENT = r"C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe -g"

ABAQUS_PREFIX = "[Software] To start Abaqus/CAE, run `"
ABAQUS_SUFFIX = "` (adjust path to your install)."
ABAQUS_PATH = r"C:\SIMULIA\CAE\2025LE\win_b64\resources\install\le\launcher.bat cae"

SOFTWARE_TAIL = re.compile(
    r"\[Software\][^\`]*\`[^\`]*\` \([^)]+\)\."
)


def fluent_task(inst: str) -> bool:
    return "fluent" in inst.lower()[:250]


def replace_software_block(inst: str, prefix: str, path: str, suffix: str) -> str:
    m = SOFTWARE_TAIL.search(inst)
    if not m:
        return inst
    new_block = prefix + path + suffix
    return inst[: m.start()] + new_block + inst[m.end() :]


def main() -> None:
    for jpath in sorted((TASK / "task-c" / "abaqus").glob("task-*/task-*.json")):
        obj = json.loads(jpath.read_text(encoding="utf-8"))
        inst = obj["instruction"]
        new_inst = replace_software_block(inst, ABAQUS_PREFIX, ABAQUS_PATH, ABAQUS_SUFFIX)
        if new_inst != inst:
            obj["instruction"] = new_inst
            jpath.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("abaqus", jpath.parent.name)

    for jpath in sorted((TASK / "task-c" / "ansys").glob("task-*/task-*.json")):
        obj = json.loads(jpath.read_text(encoding="utf-8"))
        inst = obj["instruction"]
        path = FLUENT if fluent_task(inst) else ANSYS261
        new_inst = replace_software_block(inst, ANSYS_PREFIX, path, ANSYS_SUFFIX)
        if new_inst != inst:
            obj["instruction"] = new_inst
            jpath.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("ansys", jpath.parent.name, "fluent" if fluent_task(inst) else "apdl")

    print("done")


if __name__ == "__main__":
    main()
