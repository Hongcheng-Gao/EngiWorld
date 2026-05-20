"""Update [Software] paths in task-c abaqus/ansys instructions."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"

ABAQUS_OLD = (
    r"C:\SIMULIA\EstProducts\2023\win_b64\resources\install\cmdDirFeature\launcher.bat cae"
)
ABAQUS_NEW = (
    r"C:\SIMULIA\CAE\2025LE\win_b64\resources\install\le\launcher.bat cae"
)

ANSYS_RUNWB2_OLD = r"C:\Program Files\ANSYS Inc\v241\Framework\bin\Win64\runwb2.exe"

ANSYS261_CMD = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe -g"
FLUENT_CMD = r"C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe -g"

# Match [Software] ... `path` (adjust ...).
SOFTWARE_BLOCK = re.compile(
    r"(\[Software\][^\`]*\`)[^\`]+(\` \(adjust path to your install\)\.)",
    re.IGNORECASE,
)
SOFTWARE_BLOCK_VER = re.compile(
    r"(\[Software\][^\`]*\`)[^\`]+(\` \(version/path may differ on your machine\)\.)",
    re.IGNORECASE,
)


def ansys_software_prefix(inst: str) -> str:
    low = inst.lower()
    if "fluent" in low[:200]:
        return "[Software] To start ANSYS Fluent, run `"
    if "workbench" in low[:200]:
        return "[Software] To start ANSYS Workbench, run `"
    if "mechanical apdl" in low[:200] or "apdl" in low[:200]:
        return "[Software] To start ANSYS Mechanical APDL, run `"
    return "[Software] To start ANSYS, run `"


def ansys_software_cmd(inst: str) -> str:
    if "fluent" in inst.lower()[:200]:
        return FLUENT_CMD
    return ANSYS261_CMD


def replace_software(inst: str, prefix: str, cmd: str) -> str:
    suffix_adjust = "` (adjust path to your install)."
    suffix_ver = "` (version/path may differ on your machine)."
    new_tail = prefix + cmd + suffix_adjust
    m = SOFTWARE_BLOCK.search(inst)
    if m:
        return inst[: m.start()] + new_tail
    m = SOFTWARE_BLOCK_VER.search(inst)
    if m:
        return inst[: m.start()] + prefix + cmd + suffix_ver
    # fallback: replace inside backticks only
    if "`" in inst and "[Software]" in inst:
        start = inst.rfind("[Software]")
        chunk = inst[start:]
        m2 = re.search(r"`([^`]+)`", chunk)
        if m2:
            old = m2.group(1)
            return inst.replace(old, cmd, 1)
    return inst


def main() -> None:
    n = 0
    # abaqus
    for jpath in sorted((TASK / "task-c" / "abaqus").glob("task-*/task-*.json")):
        obj = json.loads(jpath.read_text(encoding="utf-8"))
        inst = obj["instruction"]
        if ABAQUS_OLD in inst:
            inst = inst.replace(ABAQUS_OLD, ABAQUS_NEW)
        elif "EstProducts" in inst or "cmdDirFeature" in inst:
            inst = replace_software(
                inst,
                "[Software] To start Abaqus/CAE, run `",
                ABAQUS_NEW,
            )
        elif "[Software]" in inst and "2025LE" not in inst:
            inst = replace_software(
                inst,
                "[Software] To start Abaqus/CAE, run `",
                ABAQUS_NEW,
            )
        if inst != obj["instruction"]:
            obj["instruction"] = inst
            jpath.write_text(
                json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            n += 1
            print("abaqus", jpath.parent.name)

    # ansys
    for jpath in sorted((TASK / "task-c" / "ansys").glob("task-*/task-*.json")):
        obj = json.loads(jpath.read_text(encoding="utf-8"))
        inst = obj["instruction"]
        prefix = ansys_software_prefix(inst)
        cmd = ansys_software_cmd(inst)
        new_inst = replace_software(inst, prefix, cmd)
        if ANSYS_RUNWB2_OLD in new_inst:
            new_inst = new_inst.replace(ANSYS_RUNWB2_OLD, cmd)
        exe_only = cmd.split(" -g")[0] if " -g" in cmd else cmd
        for old in (
            r"C:\Program Files\ANSYS Inc\v241\Framework\bin\Win64\runwb2.exe",
            r"C:\Program Files\ANSYS Inc\v241\v241\ansys\bin\Win64\ANSYS241.exe",
        ):
            if old in new_inst:
                new_inst = new_inst.replace(old, exe_only)
        if new_inst != inst:
            obj["instruction"] = new_inst
            jpath.write_text(
                json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            n += 1
            print("ansys", jpath.parent.name, "->", cmd[:60])

    print("updated", n)


if __name__ == "__main__":
    main()
