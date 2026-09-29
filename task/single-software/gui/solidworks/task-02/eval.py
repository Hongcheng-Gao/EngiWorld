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

OUTPUT_STEP = "gui_002_flange_out.step"

BBOX_TOL = 0.10
POS_TOL = 0.20
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.02

EXPECTED_BOLT_HOLES = [
    (35.0 * math.cos(math.radians(angle)), 35.0 * math.sin(math.radians(angle)))
    for angle in (0, 60, 120, 180, 240, 300)
]
EXPECTED_VOLUME = 76095.896954


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
        "xmin": -50.0,
        "xmax": 50.0,
        "ymin": -50.0,
        "ymax": 50.0,
        "zmin": -6.0,
        "zmax": 6.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def cylinder_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        center = face.Center()
        faces.append((face, cylinder.Radius(), axis, center.x, center.y))
    return faces


def z_axis_through_cylinders(solid, radius: float):
    result = []
    for face, actual_radius, axis, center_x, center_y in cylinder_faces(solid):
        if not close(actual_radius, radius, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if not close(face.BoundingBox().zlen, 12.0, BBOX_TOL):
            continue
        result.append((center_x, center_y))
    return result


def center_bore_matches(solid) -> bool:
    bores = z_axis_through_cylinders(solid, 20.0)
    return len(bores) == 1 and close(bores[0][0], 0.0, POS_TOL) and close(bores[0][1], 0.0, POS_TOL)


def bolt_holes_match(solid) -> bool:
    holes = z_axis_through_cylinders(solid, 3.5)
    if len(holes) != 6:
        return False
    remaining = list(holes)
    for expected_x, expected_y in EXPECTED_BOLT_HOLES:
        match_index = next(
            (
                idx
                for idx, (actual_x, actual_y) in enumerate(remaining)
                if close(actual_x, expected_x, POS_TOL) and close(actual_y, expected_y, POS_TOL)
            ),
            None,
        )
        if match_index is None:
            return False
        remaining.pop(match_index)
    return True


def outside_fillets_match(solid) -> bool:
    fillets = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Torus:
            continue
        torus = surface.Torus()
        axis = torus.Axis().Direction()
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        if close(torus.MinorRadius(), 1.5, RADIUS_TOL) and close(torus.MajorRadius(), 48.5, RADIUS_TOL):
            fillets.append(torus.Location().Z())
    return (
        len(fillets) == 2
        and any(close(z, 4.5, BBOX_TOL) for z in fillets)
        and any(close(z, -4.5, BBOX_TOL) for z in fillets)
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
        and center_bore_matches(solid)
        and bolt_holes_match(solid)
        and outside_fillets_match(solid)
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
