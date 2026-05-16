#!/usr/bin/env python3
"""Fill or insert launch only under task-v/ (GUI). task-c has no launch."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"
TASK_V = TASK / "task-v"
LOG = REPO / "tools" / "TASK_LAUNCH_FILL_LOG.md"

# Mirror names (same as fix_task_dataset)
SNAPSHOT: dict[str, str] = {
    "bonsai": "Bonsai-0.8.5",
    "openstudio": "OpenStudio-1.11.0",
    "librecad": "LibreCAD2.2.0.2",
    "freecad": "FreeCAD0.21.2",
    "freecad-path": "freecad-path0.21.2",
    "solvespace": "solvespace3.1ds1-3.1build2",
    "openscad": "OpenSCAD2021.01",
    "brl-cad": "BRL-CAD7.32.2",
    "openfoam": "OpenFOAM11",
    "calculix": "CalculiX-2.21",
    "fenics": "FEniCS",
    "floris": "FLORIS4.6.4",
    "kicad": "kicad-10.0.2",
    "eagle": "eagle-7.7.0",
    "autocad": "AutoCAD2024",
    "revit": "Revit2025",
    "archicad": "ArchiCAD-27",
    "ansys": "ANSYS-2024R1",
    "abaqus": "Abaqus-2023",
    "altium-designer": "altium-designer",
    "zbrush": "ZBrush-2024",
    "solidworks": "SolidWorks-2025",
    "sketchup": "SketchUp2026",
    "cadence-orcad": "OrCAD24.1",
    "solidcam": "SolidCAM-2025",
    "nx-cam": "NX-CAM",
    "openfast": "openfast5",
    "blender": "Blender-4.2.3",
}

# Windows: full paths per table (SLDWORKS.exe is the standard entrypoint under the SOLIDWORKS folder)
WIN_LAUNCH: dict[str, list[str]] = {
    "autocad": [r"C:\Program Files\Autodesk\AutoCAD 2024\acad.exe"],
    "revit": [r"C:\Program Files\Autodesk\Revit 2025\Revit.exe"],
    "archicad": [r"C:\Program Files\Graphisoft\Archicad 27\Archicad"],
    "ansys": [r"C:\Program Files\ANSYS Inc\v241\Framework\bin\Win64\runwb2.exe"],
    "abaqus": [
        r"C:\SIMULIA\EstProducts\2023\win_b64\resources\install\cmdDirFeature\launcher.bat",
        "cae",
    ],
    "altium-designer": [r"D:\Program Files (x86)\Altium\AD17\DXP.EXE"],
    "zbrush": [r"C:\Maxon ZBrush 2025\ZBrush.exe"],
    "solidworks": [r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"],
    "sketchup": [r"C:\SketchUp 2026 26.0.429 x64 En Portable\SketchUp.exe"],
    "cadence-orcad": [r"C:\Cadence\SPB_24.1\tools\bin\capture.exe"],
    "solidcam": [r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"],
    "nx-cam": [r"C:\Program Files\Siemens\NX2306\NXBIN\ugraf.exe", "-nx"],
}

LINUX_LAUNCH: dict[str, list[str]] = {
    "bonsai": ["blender"],
    "blender": ["blender"],
    "openstudio": ["OpenStudioApp"],
    "librecad": ["librecad"],
    "freecad": ["freecad"],
    "solvespace": ["solvespace"],
    "freecad-path": ["freecad"],
    "openscad": ["openscad"],
    "brl-cad": ["mged"],
    "openfoam": ["foamRun", "-help"],
    "calculix": ["ccx", "--version"],
    "kicad": ["kicad"],
    "eagle": ["/opt/eagle-7.7.0/bin/eagle"],
    "openfast": ["openfast"],
}

# Do not append uploaded paths as argv for these (CLI / help-style)
NO_FILE_ARGS = frozenset(
    {"openfoam", "calculix", "fenics", "floris", "brl-cad"}
)

# OrCAD tasks that intentionally keep launch.parameters.command empty (no auto argv).
CADENCE_KEEP_EMPTY_LAUNCH = frozenset(
    {
        "task/task-v/cadence-orcad/task-38/task-38.json",
    }
)


def detect_os(data: dict, path: Path) -> str:
    tid = str(data.get("id", ""))
    if tid.endswith("-ubuntu"):
        return "ubuntu"
    if tid.endswith("-windows"):
        return "windows"
    blob = json.dumps(data, ensure_ascii=False)
    if "/home/user" in blob:
        return "ubuntu"
    if re.search(r"C:\\\\Users", blob) or re.search(r"C:\\Users", blob):
        return "windows"
    return "windows"


def collect_upload_paths(data: dict) -> list[str]:
    out: list[str] = []
    for block in data.get("config") or []:
        if block.get("type") != "upload_file":
            continue
        for f in (block.get("parameters") or {}).get("files") or []:
            p = f.get("path")
            if isinstance(p, str) and p and "eval.py" not in p.replace("\\", "/").lower():
                out.append(p)
    return out


def pick_extra_args(app: str, paths: list[str]) -> list[str]:
    if app in NO_FILE_ARGS:
        return []
    # Base command only: many flows are CLI (OpenFAST) or non-Capture (PSpice/Allegro).
    if app in ("cadence-orcad", "openfast"):
        return []
    if app in {"blender", "bonsai"}:
        extras = [p for p in paths if p.lower().endswith((".blend", ".obj"))]
        return extras[:3]
    if app in {"freecad", "freecad-path"}:
        for p in paths:
            if p.lower().endswith((".fcstd", ".FCStd", ".step", ".stp", ".iges", ".igs")):
                return [p]
        return paths[:1] if paths else []
    if app == "openscad":
        for p in paths:
            if p.lower().endswith(".scad"):
                return [p]
        return []
    if app == "kicad":
        for p in paths:
            if p.lower().endswith((".kicad_pro", ".pro", ".sch", ".kicad_pcb", ".brd")):
                return [p]
        return paths[:1] if paths else []
    if app == "eagle":
        for p in paths:
            if p.lower().endswith((".sch", ".brd")):
                return [p]
        return paths[:1] if paths else []
    if app == "librecad":
        return [paths[0]] if paths else []
    if app == "solvespace":
        for p in paths:
            if p.lower().endswith(".slvs"):
                return [p]
        return paths[:1] if paths else []
    if app == "openstudio":
        return [paths[0]] if paths else []
    # Windows CAD: pass first model-like file
    exts = (
        ".dwg",
        ".dxf",
        ".rvt",
        ".pln",
        ".prj",
        ".step",
        ".stp",
        ".prt",
        ".asm",
        ".sldprt",
        ".sldasm",
        ".skp",
        ".dsn",
        ".opj",
        ".olb",
        ".pcb",
        ".prjpcb",
        ".sch",
        ".brd",
        ".cae",
        ".inp",
    )
    for p in paths:
        low = p.lower()
        if any(low.endswith(e) for e in exts):
            return [p]
    return paths[:1] if paths else []


def base_launch(os: str, app: str) -> list[str] | None:
    if os == "windows":
        return WIN_LAUNCH.get(app)
    return LINUX_LAUNCH.get(app)


def ensure_launch_block(cfg: list) -> dict:
    for b in cfg:
        if b.get("type") == "launch":
            return b
    b = {"type": "launch", "parameters": {"command": []}}
    cfg.append(b)
    return b


def fill_one(path: Path, lines: list[str]) -> bool:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    parts = path.parts
    try:
        ti = parts.index("task")
    except ValueError:
        return False
    app = parts[ti + 2].lower()
    rel = str(path.relative_to(REPO)).replace("\\", "/")
    if app == "cadence-orcad" and rel in CADENCE_KEEP_EMPTY_LAUNCH:
        return False
    os = detect_os(data, path)
    base = base_launch(os, app)
    if not base:
        return False
    cfg = data.get("config")
    if not isinstance(cfg, list):
        return False

    launch_block = ensure_launch_block(cfg)
    params = launch_block.setdefault("parameters", {})
    cmd = params.get("command")
    if not isinstance(cmd, list):
        cmd = []

    uploads = collect_upload_paths(data)
    extras = pick_extra_args(app, uploads)
    new_cmd = list(base)
    for e in extras:
        if e not in new_cmd:
            new_cmd.append(e)

    # If already filled with same executable as first token, keep user extra args
    if cmd and cmd[0] == new_cmd[0] and len(cmd) > 1:
        merged = [cmd[0]]
        for x in cmd[1:] + new_cmd[1:]:
            if x not in merged:
                merged.append(x)
        new_cmd = merged

    changed = False
    if cmd != new_cmd:
        params["command"] = new_cmd
        changed = True

    snap = SNAPSHOT.get(app)
    if snap and data.get("snapshot") != snap:
        data["snapshot"] = snap
        changed = True

    if not changed:
        return False
    new_raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(new_raw, encoding="utf-8")
    lines.append(f"{path.relative_to(REPO)}\t{json.dumps(new_cmd, ensure_ascii=False)}")
    return True


def main() -> None:
    lines: list[str] = []
    n = 0
    for jf in sorted(TASK_V.rglob("task-*.json")):
        if jf.name.startswith("task-") and jf.suffix == ".json":
            if fill_one(jf, lines):
                n += 1
    LOG.write_text(
        "# Launch fill\n\nUpdated files: "
        + str(n)
        + "\n\n"
        + "\n".join(lines[:8000])
        + ("\n\n...(truncated)\n" if len(lines) > 8000 else ""),
        encoding="utf-8",
    )
    print(f"updated {n} files, log {LOG}")


if __name__ == "__main__":
    main()
