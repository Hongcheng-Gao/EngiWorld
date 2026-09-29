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

OUTPUT_STEP = "gui_007_elbow_flanges_out.step"

BBOX_TOL = 0.25
POS_TOL = 0.35
RADIUS_TOL = 0.12
VOLUME_REL_TOL = 0.03

EXPECTED_VOLUME = 63195.427511


def close(actual: float, expected: float, tol: float) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def import_solids(path: Path):
    if not path.exists() or path.stat().st_size <= 0:
        return []
    solids = cq.importers.importStep(str(path)).solids().vals()
    if not solids or any(not solid.isValid() for solid in solids):
        return []
    return solids


def all_faces(solids):
    for solid in solids:
        for face in solid.Faces():
            yield face


def bbox_matches(solids) -> bool:
    xs, ys, zs = [], [], []
    for solid in solids:
        bbox = solid.BoundingBox()
        xs.extend([bbox.xmin, bbox.xmax])
        ys.extend([bbox.ymin, bbox.ymax])
        zs.extend([bbox.zmin, bbox.zmax])
    return (
        close(min(xs), -30.0, BBOX_TOL)
        and close(max(xs), 29.0, BBOX_TOL)
        and close(min(ys), -29.0, BBOX_TOL)
        and close(max(ys), 29.0, BBOX_TOL)
        and close(min(zs), -8.0, BBOX_TOL)
        and close(max(zs), 119.0, BBOX_TOL)
    )


def pipe_ends_match(solids) -> bool:
    has_z_end = False
    has_x_end = False
    for face in all_faces(solids):
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() != GeomAbs_Plane:
            continue
        bbox = face.BoundingBox()
        center = face.Center()
        area = face.Area()
        if close(area, 392.7, 3.0) and close(bbox.xlen, 30.0, BBOX_TOL) and close(bbox.ylen, 30.0, BBOX_TOL):
            has_z_end = has_z_end or (bbox.zlen <= 0.02 and close(center.z, 0.0, POS_TOL))
        if close(area, 392.7, 3.0) and bbox.xlen <= 0.02 and close(bbox.ylen, 30.0, BBOX_TOL) and close(bbox.zlen, 30.0, BBOX_TOL):
            has_x_end = has_x_end or (close(center.x, 0.0, POS_TOL) and close(center.z, 90.0, POS_TOL))
    return has_z_end and has_x_end


def cylinder_faces(solids):
    for face in all_faces(solids):
        surface = BRepAdaptor_Surface(face.wrapped, True)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            yield face, cylinder, cylinder.Axis().Direction(), cylinder.Location()


def flange_outer_and_center_holes_match(solids) -> bool:
    z_outer = z_center = x_outer = x_center = False
    for face, cylinder, axis, location in cylinder_faces(solids):
        radius = cylinder.Radius()
        if abs(abs(axis.Z()) - 1.0) <= 0.01 and close(location.X(), 0.0, POS_TOL) and close(location.Y(), 0.0, POS_TOL):
            z_outer = z_outer or (close(radius, 29.0, RADIUS_TOL) and close(location.Z(), -8.0, POS_TOL))
            z_center = z_center or (close(radius, 10.0, RADIUS_TOL) and close(location.Z(), -8.0, POS_TOL))
        if abs(abs(axis.X()) - 1.0) <= 0.01 and close(location.Y(), 0.0, POS_TOL) and close(location.Z(), 90.0, POS_TOL):
            x_outer = x_outer or (close(radius, 29.0, RADIUS_TOL) and close(location.X(), 0.0, POS_TOL))
            x_center = x_center or (close(radius, 10.0, RADIUS_TOL) and close(location.X(), 0.0, POS_TOL))
    return z_outer and z_center and x_outer and x_center


def bolt_holes_match(solids) -> bool:
    z_holes = []
    x_holes = []
    for _face, cylinder, axis, location in cylinder_faces(solids):
        if not close(cylinder.Radius(), 3.0, RADIUS_TOL):
            continue
        if abs(abs(axis.Z()) - 1.0) <= 0.01 and close(location.Z(), -8.0, POS_TOL):
            z_holes.append((location.X(), location.Y()))
        if abs(abs(axis.X()) - 1.0) <= 0.01 and close(location.X(), 0.0, POS_TOL):
            x_holes.append((location.Y(), location.Z()))

    expected_z = [(22.0, 0.0), (-22.0, 0.0), (0.0, 22.0), (0.0, -22.0)]
    expected_x = [(22.0, 90.0), (-22.0, 90.0), (0.0, 112.0), (0.0, 68.0)]
    return all(any(close(x, ex, POS_TOL) and close(y, ey, POS_TOL) for x, y in z_holes) for ex, ey in expected_z) and all(
        any(close(y, ey, POS_TOL) and close(z, ez, POS_TOL) for y, z in x_holes) for ey, ez in expected_x
    )


def volume_matches(solids) -> bool:
    volume = sum(solid.Volume() for solid in solids)
    return abs(volume - EXPECTED_VOLUME) / EXPECTED_VOLUME <= VOLUME_REL_TOL


def evaluate() -> bool:
    if not check_no_gui_bypass(Path(r"C:\Users\User\Desktop")):
        return False
    solids = import_solids(OUTPUT_ROOT / OUTPUT_STEP)
    if not solids:
        return False
    return (
        bbox_matches(solids)
        and pipe_ends_match(solids)
        and flange_outer_and_center_holes_match(solids)
        and bolt_holes_match(solids)
        and volume_matches(solids)
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
