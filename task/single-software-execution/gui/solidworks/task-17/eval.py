from __future__ import annotations

from pathlib import Path

import cadquery as cq


OUTPUT_ROOT = Path(r"C:\Users\User\Desktop")


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

OUTPUT_NAME = "gui_017_adapter_counterbore_out.step"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid solid")
    return solids[0]


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def material(solid, points) -> bool:
    return all(inside(solid, *point) for point in points)


def empty(solid, points) -> bool:
    return all(not inside(solid, *point) for point in points)


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    expected = (-35.0, 35.0, -25.0, 25.0, -9.0, 9.0)
    return all(abs(a - e) <= TOL for a, e in zip(actual, expected))


def check_center_hole(solid) -> bool:
    empties = [(0, 0, z) for z in (-8, 0, 8)] + [(12.2, 0, 0), (-12.2, 0, 0)]
    solids = [(13.2, 0, 0), (-13.2, 0, 0), (0, 13.2, 0), (0, -13.2, 0)]
    return empty(solid, empties) and material(solid, solids)


def check_counterbore(solid, cx: float, cy: float) -> bool:
    through_empty = [
        (cx, cy, -8), (cx, cy, 0), (cx, cy, 8),
        (cx + 2.7, cy, -7), (cx - 2.7, cy, 2),
    ]
    through_material = [(cx + 3.6, cy, -4), (cx - 3.6, cy, 0)]
    counterbore_empty = [(cx + 5.7, cy, 8), (cx - 5.7, cy, 6), (cx, cy + 5.7, 8)]
    counterbore_material = [(cx + 6.6, cy, 8), (cx, cy + 6.6, 6), (cx + 5.0, cy, 3.5)]
    return (
        empty(solid, through_empty)
        and material(solid, through_material)
        and empty(solid, counterbore_empty)
        and material(solid, counterbore_material)
    )


def check_all_counterbores(solid) -> bool:
    return all(
        check_counterbore(solid, cx, cy)
        for cx in (-25.0, 25.0)
        for cy in (-15.0, 15.0)
    )


def check_top_outer_chamfer(solid) -> bool:
    # A 2 mm top chamfer removes the sharp top perimeter while leaving the top
    # face inset and the side wall below the chamfer intact.
    return (
        material(solid, [(32.0, 0, 8.8), (-32.0, 0, 8.8), (0, 22.0, 8.8), (0, -22.0, 8.8)])
        and empty(solid, [(34.5, 0, 8.8), (-34.5, 0, 8.8), (0, 24.5, 8.8), (0, -24.5, 8.8)])
        and material(solid, [(34.8, 0, 6.8), (-34.8, 0, 6.8), (0, 24.8, 6.8), (0, -24.8, 6.8)])
    )


def check_volume(solid) -> bool:
    return abs(solid.Volume() - 49962.7) / 49962.7 <= 0.02


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return all([
        check_bbox(solid),
        check_center_hole(solid),
        check_all_counterbores(solid),
        check_top_outer_chamfer(solid),
        check_volume(solid),
    ])


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            print(True if evaluate() else False)
    except Exception:
        print(False)
