from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane


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

OUTPUT_STEP = "gui_003_shaft_keyway_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_VOLUME = 60548.872075


def close(actual: float, expected: float, tol: float) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def import_single_solid(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        return None
    workplane = cq.importers.importStep(str(path))
    solids = workplane.solids().vals()
    if len(solids) != 1 or any(not solid.isValid() for solid in solids):
        return None
    return solids[0]


def bbox_matches(solid) -> bool:
    bbox = solid.BoundingBox()
    expected = {
        "xmin": -10.0,
        "xmax": 100.0,
        "ymin": -15.0,
        "ymax": 15.0,
        "zmin": -15.0,
        "zmax": 15.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    result = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        center = face.Center()
        result.append((face, cylinder.Radius(), axis, center))
    return result


def shaft_segments_match(solid) -> bool:
    has_left = False
    has_right = False
    for face, radius, axis, center in cylinder_faces(solid):
        if abs(abs(axis.X()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        if close(radius, 15.0, RADIUS_TOL) and bbox.xlen >= 45.0 and close(center.x, 20.0, 1.0):
            has_left = True
        if close(radius, 11.0, RADIUS_TOL) and bbox.xlen >= 45.0 and close(center.x, 74.5, 1.0):
            has_right = True
    return has_left and has_right


def keyway_matches(solid) -> bool:
    bottom_found = False
    side_y = []
    end_x = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(bbox.xlen, 35.0, POS_TOL)
            and close(bbox.ylen, 8.0, POS_TOL)
            and bbox.zlen <= 0.02
            and close(center.x, 20.0, POS_TOL)
            and close(center.y, 0.0, POS_TOL)
            and close(center.z, 12.0, POS_TOL)
        ):
            bottom_found = True
        if close(bbox.xlen, 35.0, POS_TOL) and bbox.ylen <= 0.02 and 2.0 <= bbox.zlen <= 3.2:
            if close(center.x, 20.0, POS_TOL) and close(abs(center.y), 4.0, POS_TOL):
                side_y.append(center.y)
        if bbox.xlen <= 0.02 and close(bbox.ylen, 8.0, POS_TOL) and 2.5 <= bbox.zlen <= 3.5:
            if close(abs(center.x - 20.0), 17.5, POS_TOL) and close(center.y, 0.0, POS_TOL):
                end_x.append(center.x)
    return (
        bottom_found
        and any(y > 0 for y in side_y)
        and any(y < 0 for y in side_y)
        and any(close(x, 2.5, POS_TOL) for x in end_x)
        and any(close(x, 37.5, POS_TOL) for x in end_x)
    )


def end_chamfers_match(solid) -> bool:
    chamfer_x = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cone:
            continue
        cone = surface.Cone()
        axis = cone.Axis().Direction()
        if abs(abs(axis.X()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 1.0, BBOX_TOL):
            chamfer_x.append(center.x)
    return (
        len(chamfer_x) >= 2
        and any(close(x, -9.5, BBOX_TOL) for x in chamfer_x)
        and any(close(x, 99.5, BBOX_TOL) for x in chamfer_x)
    )


def volume_matches(solid) -> bool:
    return abs(solid.Volume() - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solid = import_single_solid(OUTPUT_ROOT / OUTPUT_STEP)
    if solid is None:
        return False
    return (
        bbox_matches(solid)
        and shaft_segments_match(solid)
        and keyway_matches(solid)
        and end_chamfers_match(solid)
        and volume_matches(solid)
    )


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print(True if ok else False)
