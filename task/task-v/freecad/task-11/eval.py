from __future__ import annotations

from pathlib import Path

import cadquery as cq

DESKTOP = Path("/home/user/Desktop")



GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv",
    ".dxf", ".dwg", ".step", ".stp", ".fcstd", ".scad", ".stl", ".obj",
    ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl",
    "ifcopenshell", "openstudio", "energyplus",
    "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI",
    "freecad", "freecadcmd", "openscad", "librecad",
    "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace",
)


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(
                token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item")
            )
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(
                ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS
            ) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

STEP_SPECS = [{'path': '/home/user/Desktop/freecad_task-11_output.step', 'solid_count': 1, 'bbox': [70.0, 60.0, 8.0], 'volume': 30760.000241}]
BBOX_TOL = 0.05
VOLUME_REL_TOL = 0.01


def summarize_step(path: Path):
    wp = cq.importers.importStep(str(path))
    solids = wp.solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        raise ValueError("invalid STEP")
    xs, ys, zs = [], [], []
    volume = 0.0
    for solid in solids:
        bbox = solid.BoundingBox()
        xs.extend([bbox.xmin, bbox.xmax])
        ys.extend([bbox.ymin, bbox.ymax])
        zs.extend([bbox.zmin, bbox.zmax])
        volume += solid.Volume()
    return len(solids), [max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)], volume


def evaluate() -> bool:
    if not check_no_gui_bypass(DESKTOP):
        return False
    for spec in STEP_SPECS:
        path = Path(spec["path"])
        if not path.exists() or path.stat().st_size <= 0:
            return False
        solid_count, bbox, volume = summarize_step(path)
        if solid_count != spec["solid_count"]:
            return False
        if any(abs(float(a) - float(b)) > BBOX_TOL for a, b in zip(bbox, spec["bbox"])):
            return False
        if abs(volume - float(spec["volume"])) / max(1.0, abs(float(spec["volume"]))) > VOLUME_REL_TOL:
            return False
    return True


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(DESKTOP):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
    raise SystemExit(0)
