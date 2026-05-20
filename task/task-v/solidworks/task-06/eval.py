from __future__ import annotations

from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane


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

OUTPUT_STEP = "gui_006_bracket_reinforced_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.30
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 74343.80545


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
        "xmin": -40.0,
        "xmax": 40.0,
        "ymin": -25.0,
        "ymax": 25.0,
        "zmin": 0.0,
        "zmax": 68.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            faces.append((face, cylinder, cylinder.Axis().Direction(), cylinder.Location()))
    return faces


def base_holes_match(solid) -> bool:
    holes = []
    for face, cylinder, axis, _location in cylinder_faces(solid):
        if not close(cylinder.Radius(), 4.5, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if not close(face.BoundingBox().zlen, 8.0, BBOX_TOL):
            continue
        center = face.Center()
        holes.append((center.x, center.y))
    return (
        len(holes) == 2
        and any(close(x, -25.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
        and any(close(x, 25.0, POS_TOL) and close(y, 0.0, POS_TOL) for x, y in holes)
    )


def slot_matches(solid) -> bool:
    slot_ends = []
    for face, cylinder, axis, location in cylinder_faces(solid):
        if not close(cylinder.Radius(), 5.0, RADIUS_TOL):
            continue
        if abs(abs(axis.Y()) - 1.0) > 0.01:
            continue
        if not close(face.BoundingBox().ylen, 8.0, BBOX_TOL):
            continue
        if close(location.Z(), 35.0, POS_TOL):
            slot_ends.append(location.X())

    has_top = False
    has_bottom = False
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 22.0, POS_TOL) and close(bbox.ylen, 8.0, POS_TOL) and bbox.zlen <= 0.02:
            if close(center.x, 0.0, POS_TOL) and close(center.y, 21.0, POS_TOL):
                has_top = has_top or close(center.z, 40.0, POS_TOL)
                has_bottom = has_bottom or close(center.z, 30.0, POS_TOL)

    return (
        len(slot_ends) == 2
        and any(close(x, -11.0, POS_TOL) for x in slot_ends)
        and any(close(x, 11.0, POS_TOL) for x in slot_ends)
        and has_top
        and has_bottom
    )


def gussets_match(solid) -> bool:
    gusset_centers = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        if close(bbox.xlen, 6.0, POS_TOL) and close(bbox.ylen, 35.0, POS_TOL) and close(bbox.zlen, 35.0, POS_TOL):
            gusset_centers.append(center.x)
    return (
        len(gusset_centers) >= 2
        and any(close(x, -20.0, POS_TOL) for x in gusset_centers)
        and any(close(x, 20.0, POS_TOL) for x in gusset_centers)
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
        and base_holes_match(solid)
        and slot_matches(solid)
        and gussets_match(solid)
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
