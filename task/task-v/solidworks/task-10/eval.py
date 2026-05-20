from __future__ import annotations

import math
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Torus


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

OUTPUT_STEP = "gui_010_wheel_pattern_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.30
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_VOLUME = 199948.286009
EXPECTED_BOLT_HOLES = [
    (42.0 * math.cos(math.radians(90 + i * 72)), 42.0 * math.sin(math.radians(90 + i * 72)))
    for i in range(5)
]


def close(actual: float, expected: float, tol: float) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def import_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        return None
    solids = cq.importers.importStep(str(path)).solids().vals()
    if len(solids) != 1 or any(not solid.isValid() for solid in solids):
        return None
    return solids[0]


def bbox_matches(solid) -> bool:
    bbox = solid.BoundingBox()
    return (
        close(bbox.xmin, -60.0, BBOX_TOL)
        and close(bbox.xmax, 60.0, BBOX_TOL)
        and close(bbox.ymin, -60.0, BBOX_TOL)
        and close(bbox.ymax, 60.0, BBOX_TOL)
        and close(bbox.zmin, -10.0, BBOX_TOL)
        and close(bbox.zmax, 10.0, BBOX_TOL)
    )


def cylinder_faces(solid):
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction()


def z_axis_holes(solid, radius: float):
    holes = []
    for face, cylinder, axis in cylinder_faces(solid):
        if not close(cylinder.Radius(), radius, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if close(face.BoundingBox().zlen, 20.0, BBOX_TOL):
            center = face.Center()
            holes.append((center.x, center.y))
    return holes


def center_hole_matches(solid) -> bool:
    holes = z_axis_holes(solid, 17.5)
    return len(holes) == 1 and close(holes[0][0], 0.0, POS_TOL) and close(holes[0][1], 0.0, POS_TOL)


def bolt_holes_match(solid) -> bool:
    holes = z_axis_holes(solid, 4.5)
    if len(holes) != 5:
        return False
    return all(
        any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in holes)
        for ex, ey in EXPECTED_BOLT_HOLES
    )


def rim_fillets_match(solid) -> bool:
    z_values = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Torus:
            continue
        torus = surface.Torus()
        if close(torus.MajorRadius(), 58.0, RADIUS_TOL) and close(torus.MinorRadius(), 2.0, RADIUS_TOL):
            z_values.append(torus.Location().Z())
    return len(z_values) == 2 and any(close(z, 8.0, BBOX_TOL) for z in z_values) and any(close(z, -8.0, BBOX_TOL) for z in z_values)


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return bbox_matches(solid) and center_hole_matches(solid) and bolt_holes_match(solid) and rim_fillets_match(solid) and volume_matches(solid)


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
