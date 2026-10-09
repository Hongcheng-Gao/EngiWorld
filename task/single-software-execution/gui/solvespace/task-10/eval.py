import itertools
import os
from pathlib import Path
import ezdxf

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))


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

TARGET = "final_ss_gui_10.dxf"
TOL = 0.75


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _dedupe(points):
    out = []
    for point in points:
        if not any(_point_close(point, old) for old in out):
            out.append(point)
    return out


def _segment_points(doc):
    points = []
    for entity in doc.modelspace():
        if entity.dxftype() == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            points.extend([(float(start.x), float(start.y)), (float(end.x), float(end.y))])
        elif entity.dxftype() == "LWPOLYLINE":
            points.extend((float(p[0]), float(p[1])) for p in entity.get_points("xy"))
    return _dedupe(points)


def _outline_segments(doc):
    segments = []
    for entity in doc.modelspace():
        if entity.dxftype() == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            segments.append(((float(start.x), float(start.y)), (float(end.x), float(end.y))))
        elif entity.dxftype() == "LWPOLYLINE":
            points = [(float(p[0]), float(p[1])) for p in entity.get_points("xy")]
            segments.extend(zip(points, points[1:]))
            if entity.closed and len(points) > 2:
                segments.append((points[-1], points[0]))
    return segments


def _edge_present(segments, start, end, tol=0.15):
    return any(
        (_point_close(a, start, tol) and _point_close(b, end, tol))
        or (_point_close(a, end, tol) and _point_close(b, start, tol))
        for a, b in segments
    )


def _trapezoid_edges_present(doc, points):
    ys = sorted(set(round(p[1], 3) for p in points))
    if len(ys) != 2:
        return False
    bottom = sorted([p for p in points if _close(p[1], ys[0])])
    top = sorted([p for p in points if _close(p[1], ys[1])])
    if len(bottom) != 2 or len(top) != 2:
        return False
    expected_edges = (
        (bottom[0], bottom[1]),
        (bottom[1], top[1]),
        (top[1], top[0]),
        (top[0], bottom[0]),
    )
    segments = _outline_segments(doc)
    return all(_edge_present(segments, start, end) for start, end in expected_edges)


def _trapezoid_center(points):
    if len(points) != 4:
        return None
    ys = sorted(set(round(p[1], 3) for p in points))
    if len(ys) != 2:
        return None
    bottom = sorted([p for p in points if _close(p[1], ys[0])])
    top = sorted([p for p in points if _close(p[1], ys[1])])
    if len(bottom) != 2 or len(top) != 2:
        return None
    bottom_len = abs(bottom[1][0] - bottom[0][0])
    top_len = abs(top[1][0] - top[0][0])
    height = abs(ys[1] - ys[0])
    axis_bottom = (bottom[0][0] + bottom[1][0]) / 2
    axis_top = (top[0][0] + top[1][0]) / 2
    if _close(bottom_len, 140) and _close(top_len, 80) and _close(height, 60) and _close(axis_bottom, axis_top):
        return (axis_bottom, (ys[0] + ys[1]) / 2)
    return None


def _find_trapezoid(doc):
    for entity in doc.modelspace():
        if entity.dxftype() != "LWPOLYLINE":
            continue
        pts = _dedupe([(float(p[0]), float(p[1])) for p in entity.get_points("xy")])
        center = _trapezoid_center(pts)
        if center is not None and _trapezoid_edges_present(doc, pts):
            return center
    points = _segment_points(doc)
    for candidate in itertools.combinations(points, 4):
        center = _trapezoid_center(candidate)
        if center is not None and _trapezoid_edges_present(doc, candidate):
            return center
    return None


def _has_circle(doc, center, radius):
    for entity in doc.modelspace():
        if entity.dxftype() != "CIRCLE":
            continue
        c = entity.dxf.center
        if _point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius):
            return True
    return False


def evaluate():
    if not check_no_gui_bypass(Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))):
        return False
    path = OUTPUT_ROOT / TARGET
    if not path.exists() or path.stat().st_size <= 0:
        return False
    doc = ezdxf.readfile(path)
    hole_center = _find_trapezoid(doc)
    return (
        hole_center is not None
        and _has_circle(doc, hole_center, 10)
        and _has_circle(doc, (25, 20), 3)
        and _has_circle(doc, (115, 20), 3)
    )


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
