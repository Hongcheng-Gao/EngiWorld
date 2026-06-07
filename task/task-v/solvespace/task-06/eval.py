import itertools
import math
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

TARGET = "final_ss_gui_06.dxf"
TOL = 0.75


def _close(a, b, tol=TOL):
    return abs(float(a) - float(b)) <= tol


def _point_close(a, b, tol=TOL):
    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)


def _dist(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def _dedupe(points):
    unique = []
    for point in points:
        if not any(_point_close(point, prev) for prev in unique):
            unique.append(point)
    return unique


def _segment_points(doc):
    points = []
    for entity in doc.modelspace():
        if entity.dxftype() == "LINE":
            start, end = entity.dxf.start, entity.dxf.end
            points.extend([(float(start.x), float(start.y)), (float(end.x), float(end.y))])
        elif entity.dxftype() == "LWPOLYLINE":
            points.extend((float(p[0]), float(p[1])) for p in entity.get_points("xy"))
    return _dedupe(points)


def _regular_hex_center(points):
    if len(points) != 6:
        return None
    center = (sum(p[0] for p in points) / 6, sum(p[1] for p in points) / 6)
    expected_top_y = 40 * math.sin(math.radians(60))
    if not all(_close(_dist(p, center), 40, 1.0) for p in points):
        return None
    rel = sorted((round(p[0] - center[0], 2), round(p[1] - center[1], 2)) for p in points)
    has_left_right = any(_point_close((dx, dy), (-40, 0), 1.0) for dx, dy in rel) and any(_point_close((dx, dy), (40, 0), 1.0) for dx, dy in rel)
    has_top = sum(1 for dx, dy in rel if _close(dy, expected_top_y, 1.0)) == 2
    has_bottom = sum(1 for dx, dy in rel if _close(dy, -expected_top_y, 1.0)) == 2
    if has_left_right and has_top and has_bottom:
        return center
    return None


def _hex_center(doc):
    for entity in doc.modelspace():
        if entity.dxftype() != "LWPOLYLINE":
            continue
        pts = _dedupe([(float(p[0]), float(p[1])) for p in entity.get_points("xy")])
        center = _regular_hex_center(pts)
        if center is not None:
            return center
    points = _segment_points(doc)
    for candidate in itertools.combinations(points, 6):
        center = _regular_hex_center(candidate)
        if center is not None:
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
    center = _hex_center(doc)
    if center is None:
        return False
    return (
        _has_circle(doc, center, 10)
        and _has_circle(doc, (center[0] - 28, center[1]), 3)
        and _has_circle(doc, (center[0] + 28, center[1]), 3)
        and all(
            _has_circle(
                doc,
                (
                    center[0] + 25 * math.cos(math.radians(angle)),
                    center[1] + 25 * math.sin(math.radians(angle)),
                ),
                2,
            )
            for angle in [0, 60, 120, 180, 240, 300]
        )
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
