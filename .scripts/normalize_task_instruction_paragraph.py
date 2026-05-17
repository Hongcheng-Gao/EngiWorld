"""Normalize task instruction: single English paragraph + [Software] hint for task-c only.

Does not modify `source`. Does not process task-v (no [Software] block on task-v).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SOFTWARE_MARK = "[Software]"
SOFTWARE_SEP = f" {SOFTWARE_MARK} "

SNAPSHOT_HINT_EN: dict[str, str] = {
    "altium-designer": "To use Altium Designer on Windows, run `D:\\Program Files (x86)\\Altium\\AD17\\DXP.EXE` (adjust if your install path differs).",
    "kicad-10.0.2": "To use KiCad, run `kicad` for the GUI or `kicad-cli` for scripting/headless use (use PATH or the full install path).",
    "eagle-7.7.0": "On Linux, launch CadSoft EAGLE with `/opt/eagle-7.7.0/bin/eagle` (adjust to your install).",
    "FreeCAD0.21.2": "To use FreeCAD, run `freecad` from a terminal (use the full executable path if it is not on PATH).",
    "freecad-path0.21.2": "To use FreeCAD, run `freecad` from a terminal (use the full executable path if it is not on PATH).",
    "OpenSCAD2021.01": "To use OpenSCAD, run `openscad` from a terminal.",
    "OpenFOAM11": "OpenFOAM is normally used from a shell after sourcing your installation environment (e.g. its `etc/bashrc`); `foamRun -help` verifies solver binaries are available.",
    "CalculiX-2.21": "Run `ccx --version` or invoke the installed `ccx` binary from a terminal.",
    "FEniCS": "Run your scripts with Python in an environment where dolfinx is installed (e.g. `import dolfinx`).",
    "FLORIS4.6.4": "Run your scripts with Python in an environment where `floris` is installed (e.g. `from floris import FlorisModel`).",
    "ANSYS-2024R1": "To start ANSYS Workbench, run `C:\\Program Files\\ANSYS Inc\\v241\\Framework\\bin\\Win64\\runwb2.exe` (version/path may differ on your machine).",
    "Abaqus-2023": "To start Abaqus/CAE, run `C:\\SIMULIA\\EstProducts\\2023\\win_b64\\resources\\install\\cmdDirFeature\\launcher.bat cae` (adjust path to your install).",
    "ArchiCAD-27": "Launch ArchiCAD with `C:\\Program Files\\Graphisoft\\Archicad 27\\Archicad` (adjust version/path).",
    "AutoCAD2024": "Launch AutoCAD with `C:\\Program Files\\Autodesk\\AutoCAD 2024\\acad.exe`.",
    "Revit2025": "Launch Revit with `C:\\Program Files\\Autodesk\\Revit 2025\\Revit.exe`.",
    "SolidWorks-2025": "Launch SOLIDWORKS from `C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\` (use your actual executable or shortcut).",
    "SolidCAM-2025": "SolidCAM runs inside SOLIDWORKS; start SOLIDWORKS from `C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\` first (adjust path).",
    "NX-CAM": "Launch Siemens NX with `C:\\Program Files\\Siemens\\NX2306\\NXBIN\\ugraf.exe -nx` (adjust version/path).",
    "SketchUp2026": "Launch SketchUp with `C:\\SketchUp 2026 26.0.429 x64 En Portable\\SketchUp.exe` (adjust if your install differs).",
    "OpenStudio-1.11.0": "Launch the OpenStudio GUI with `OpenStudioApp` from a terminal (PATH or full path to the binary).",
    "OrCAD24.1": "Launch OrCAD Capture with `C:\\Cadence\\SPB_24.1\\tools\\bin\\capture.exe` (adjust to your Cadence install root).",
    "BRL-CAD7.32.2": "Run `mged` from a terminal (use the full path if it is not on PATH).",
    "Blender-4.2.3": "Launch Blender by running `blender` from a terminal.",
    "Bonsai-0.8.5": "Bonsai workflows are used together with Blender; start Blender with `blender` (adjust path if needed).",
    "openfast5": "Run `openfast` from a terminal (use the full path if it is not on PATH).",
    # task-v only
    "LibreCAD2.2.0.2": "Launch LibreCAD with the `librecad` command from a terminal (use the full path if it is not on PATH).",
    "solvespace3.1ds1-3.1build2": "Launch SolveSpace with the `solvespace` command from a terminal (use the full path if it is not on PATH).",
    "zbrush": "Launch ZBrush with `C:\\Maxon ZBrush 2025\\ZBrush.exe` (adjust version/path to your install).",
}

DEFAULT_HINT_EN = (
    "Locate the correct engineering application executable or terminal command on this machine "
    "(paths may differ from the examples above)."
)

def strip_software_block(instruction: str) -> str:
    s = instruction
    if "\n\n[Software] " in s:
        return s.split("\n\n[Software] ", 1)[0].strip()
    if SOFTWARE_SEP in s:
        return s.split(SOFTWARE_SEP, 1)[0].strip()
    if s.strip().startswith(f"{SOFTWARE_MARK} "):
        return ""
    return s.strip()


def one_paragraph(text: str) -> str:
    t = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r" +", " ", t).strip()


def iter_task_json_roots(roots: list[Path]):
    for root in roots:
        for path in sorted(root.rglob("task-*.json")):
            if path.parent.name != path.stem:
                continue
            if "ground_truth" in path.parts:
                continue
            yield path


def process_file(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    inst = data.get("instruction")
    if not isinstance(inst, str):
        return False

    snap = data.get("snapshot")
    snap_key = snap if isinstance(snap, str) else ""
    hint = SNAPSHOT_HINT_EN.get(snap_key, DEFAULT_HINT_EN)

    base = strip_software_block(inst)
    base_1 = one_paragraph(base)
    hint_1 = one_paragraph(hint)
    new_inst = f"{base_1}{SOFTWARE_SEP}{hint_1}" if base_1 else f"{SOFTWARE_MARK} {hint_1}"

    if new_inst == inst:
        return False
    data["instruction"] = new_inst
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    roots = [REPO / "task" / "task-c"]
    updated = 0
    missing: set[str] = set()
    for root in roots:
        if not root.is_dir():
            print("skip missing", root)
            continue
        for path in iter_task_json_roots([root]):
            data = json.loads(path.read_text(encoding="utf-8"))
            snap = data.get("snapshot")
            if isinstance(snap, str) and snap not in SNAPSHOT_HINT_EN:
                missing.add(snap)
            if process_file(path):
                updated += 1
    print("updated", updated, "files")
    if missing:
        print("WARN snapshots missing dedicated hint (default used):", sorted(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
