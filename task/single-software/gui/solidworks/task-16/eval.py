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

OUTPUT_NAME = "gui_016_frame_corner_gusset_out.step"
TOL = 0.08


def load_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        raise FileNotFoundError(path)
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError("expected one valid solid")
    return solids[0]


def close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def check_bbox(solid) -> bool:
    bb = solid.BoundingBox()
    expected = (0.0, 120.0, 0.0, 120.0, 0.0, 30.0)
    actual = (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    return all(close(a, e) for a, e in zip(actual, expected))


def inside(solid, x: float, y: float, z: float) -> bool:
    return bool(solid.isInside(cq.Vector(x, y, z), 1e-5))


def all_material(solid, points) -> bool:
    return all(inside(solid, *point) for point in points)


def all_empty(solid, points) -> bool:
    return all(not inside(solid, *point) for point in points)


def check_square_tube_frame(solid) -> bool:
    wall_points = [
        (60, 1.5, 15), (60, 28.5, 15), (60, 15, 1.5), (60, 15, 28.5),
        (1.5, 60, 15), (28.5, 60, 15), (15, 60, 1.5), (15, 60, 28.5),
        (10, 10, 1.5), (10, 10, 28.5),
    ]
    void_points = [
        (60, 15, 15), (15, 60, 15), (116, 15, 15), (15, 116, 15),
        (90, 90, 15), (110, 40, 15), (40, 110, 15),
    ]
    return all_material(solid, wall_points) and all_empty(solid, void_points)


def check_gusset(solid) -> bool:
    gusset_material = [
        (40, 40, 12.5), (40, 40, 17.5),
        (55, 35, 15), (35, 55, 15),
        (70, 35, 15), (35, 70, 15),
    ]
    gusset_empty = [
        (40, 40, 11.2), (40, 40, 18.8),
        (70, 70, 15), (87, 31, 15), (31, 87, 15),
    ]
    return all_material(solid, gusset_material) and all_empty(solid, gusset_empty)


def check_vertical_hole(solid, cx: float, cy: float, outside_axis: str) -> bool:
    for z in (1.5, 28.5):
        if not all_empty(solid, [(cx, cy, z), (cx + 3.6, cy, z), (cx - 3.6, cy, z)]):
            return False
        if outside_axis == "x":
            material_points = [(cx + 4.5, cy, z), (cx - 4.5, cy, z)]
        else:
            material_points = [(cx, cy + 4.5, z), (cx, cy - 4.5, z)]
        if not all_material(solid, material_points):
            return False
    return True


def check_fixing_holes(solid) -> bool:
    x_tube = [(100, 7), (100, 23)]
    y_tube = [(7, 100), (23, 100)]
    return (
        all(check_vertical_hole(solid, cx, cy, "x") for cx, cy in x_tube)
        and all(check_vertical_hole(solid, cx, cy, "y") for cx, cy in y_tube)
    )


def check_volume(solid) -> bool:
    return abs(solid.Volume() - 72452.6) / 72452.6 <= 0.025


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = load_single_solid(OUTPUT_ROOT / OUTPUT_NAME)
    return all([
        check_bbox(solid),
        check_square_tube_frame(solid),
        check_gusset(solid),
        check_fixing_holes(solid),
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
