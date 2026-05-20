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

OUTPUT_STEP = "gui_004_cover_vented_out.step"

BBOX_TOL = 0.15
POS_TOL = 0.25
RADIUS_TOL = 0.10
VOLUME_REL_TOL = 0.03

EXPECTED_SLOT_Y = [-24.0 + i * (48.0 / 7.0) for i in range(8)]
EXPECTED_VOLUME = 22827.610658


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
        "ymin": -35.0,
        "ymax": 35.0,
        "zmin": -9.0,
        "zmax": 9.0,
    }
    return all(close(getattr(bbox, key), value, BBOX_TOL) for key, value in expected.items())


def plane_faces(solid):
    faces = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Plane:
            faces.append(face)
    return faces


def shell_matches(solid) -> bool:
    has_inside_top = False
    bottom_open = True
    has_inner_x = 0
    has_inner_y = 0
    for face in plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if (
            close(bbox.xlen, 96.0, BBOX_TOL)
            and close(bbox.ylen, 66.0, BBOX_TOL)
            and bbox.zlen <= 0.02
            and close(center.z, 7.0, POS_TOL)
        ):
            has_inside_top = True
        if (
            close(bbox.xlen, 100.0, BBOX_TOL)
            and close(bbox.ylen, 70.0, BBOX_TOL)
            and bbox.zlen <= 0.02
            and close(center.z, -9.0, POS_TOL)
            and face.Area() > 6000.0
        ):
            bottom_open = False
        if bbox.xlen <= 0.02 and close(bbox.ylen, 60.0, BBOX_TOL) and close(bbox.zlen, 16.0, BBOX_TOL):
            if close(abs(center.x), 48.0, POS_TOL):
                has_inner_x += 1
        if close(bbox.xlen, 90.0, BBOX_TOL) and bbox.ylen <= 0.02 and close(bbox.zlen, 16.0, BBOX_TOL):
            if close(abs(center.y), 33.0, POS_TOL):
                has_inner_y += 1
    return has_inside_top and bottom_open and has_inner_x >= 2 and has_inner_y >= 2


def slots_match(solid) -> bool:
    end_faces = []
    side_faces = []
    for face in plane_faces(solid):
        bbox = face.BoundingBox()
        center = face.Center()
        if bbox.xlen <= 0.02 and close(bbox.ylen, 3.0, POS_TOL) and close(bbox.zlen, 2.0, POS_TOL):
            if close(abs(center.x), 20.0, POS_TOL) and close(center.z, 8.0, POS_TOL):
                end_faces.append((center.x, center.y))
        if close(bbox.xlen, 40.0, POS_TOL) and bbox.ylen <= 0.02 and close(bbox.zlen, 2.0, POS_TOL):
            if close(center.x, 0.0, POS_TOL) and close(center.z, 8.0, POS_TOL):
                side_faces.append(center.y)

    for y in EXPECTED_SLOT_Y:
        if not any(close(x, -20.0, POS_TOL) and close(actual_y, y, POS_TOL) for x, actual_y in end_faces):
            return False
        if not any(close(x, 20.0, POS_TOL) and close(actual_y, y, POS_TOL) for x, actual_y in end_faces):
            return False
        if not any(close(actual_y, y - 1.5, POS_TOL) for actual_y in side_faces):
            return False
        if not any(close(actual_y, y + 1.5, POS_TOL) for actual_y in side_faces):
            return False
    return True


def inside_corner_fillets_match(solid) -> bool:
    fillets = []
    for face in solid.Faces():
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Cylinder:
            continue
        cylinder = surface.Cylinder()
        axis = cylinder.Axis().Direction()
        if abs(abs(axis.Z()) - 1.0) > 0.01:
            continue
        bbox = face.BoundingBox()
        if close(cylinder.Radius(), 3.0, RADIUS_TOL) and close(bbox.zlen, 16.0, BBOX_TOL):
            center = face.Center()
            fillets.append((center.x, center.y))
    return (
        len(fillets) == 4
        and any(x < 0 and y < 0 for x, y in fillets)
        and any(x > 0 and y < 0 for x, y in fillets)
        and any(x < 0 and y > 0 for x, y in fillets)
        and any(x > 0 and y > 0 for x, y in fillets)
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
        and shell_matches(solid)
        and slots_match(solid)
        and inside_corner_fillets_match(solid)
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
