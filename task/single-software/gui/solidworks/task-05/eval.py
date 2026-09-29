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

OUTPUT_STEP = "gui_005_heat_sink_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.08
VOLUME_REL_TOL = 0.02

EXPECTED_FIN_X = [-32.0, -24.0, -16.0, -8.0, 0.0, 8.0, 16.0, 24.0, 32.0]
EXPECTED_VOLUME = 43150.214587


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
        "xmin": -45.0,
        "xmax": 45.0,
        "ymin": -25.0,
        "ymax": 25.0,
        "zmin": 0.0,
        "zmax": 24.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def plane_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Plane:
            faces.append(face)
    return faces


def base_matches(solid) -> bool:
    for face in plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(bbox.xlen, 90.0, BBOX_TOL)
            and close(bbox.ylen, 50.0, BBOX_TOL)
            and bbox.zlen <= 0.02
            and close(center.z, 0.0, POS_TOL)
        ):
            return True
    return False


def fin_top_faces_match(solid) -> bool:
    top_centers = []
    for face in plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(bbox.xlen, 1.0, POS_TOL)
            and close(bbox.ylen, 49.0, POS_TOL)
            and bbox.zlen <= 0.02
            and close(center.z, 24.0, POS_TOL)
        ):
            top_centers.append(center.x)
    if len(top_centers) != 9:
        return False
    remaining = list(top_centers)
    for expected_x in EXPECTED_FIN_X:
        match_index = next((idx for idx, actual_x in enumerate(remaining) if close(actual_x, expected_x, POS_TOL)), None)
        if match_index is None:
            return False
        remaining.pop(match_index)
    return True


def fin_side_faces_match(solid) -> bool:
    for expected_x in EXPECTED_FIN_X:
        left = False
        right = False
        for face in plane_faces(solid):
            bbox = face.BoundingBox()
            center = face.Center()
            if bbox.xlen <= 0.02 and close(bbox.ylen, 50.0, BBOX_TOL) and 17.0 <= bbox.zlen <= 18.2:
                if close(center.x, expected_x - 1.0, POS_TOL):
                    left = True
                if close(center.x, expected_x + 1.0, POS_TOL):
                    right = True
        if not (left and right):
            return False
    return True


def top_fillets_match(solid) -> bool:
    y_axis_fillets = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(cylinder.Radius(), 0.5, RADIUS_TOL)
            and abs(abs(axis.Y()) - 1.0) <= 0.01
            and close(bbox.ylen, 50.0, BBOX_TOL)
            and close(center.z, 23.82, POS_TOL)
        ):
            y_axis_fillets.append(center.x)
    for expected_x in EXPECTED_FIN_X:
        if not any(close(actual_x, expected_x - 0.82, 0.35) for actual_x in y_axis_fillets):
            return False
        if not any(close(actual_x, expected_x + 0.82, 0.35) for actual_x in y_axis_fillets):
            return False
    return True


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
        and base_matches(solid)
        and fin_top_faces_match(solid)
        and fin_side_faces_match(solid)
        and top_fillets_match(solid)
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
