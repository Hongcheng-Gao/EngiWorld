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

TARGET = "final_ss_gui_12.dxf"

TOL = 0.75





def _close(a, b, tol=TOL):

    return abs(float(a) - float(b)) <= tol





def _point_close(a, b, tol=TOL):

    return _close(a[0], b[0], tol) and _close(a[1], b[1], tol)





def _segments(doc):

    out = []

    for entity in doc.modelspace():

        if entity.dxftype() == "LINE":

            s, e = entity.dxf.start, entity.dxf.end

            out.append(((float(s.x), float(s.y)), (float(e.x), float(e.y)), 0.0))

        elif entity.dxftype() == "LWPOLYLINE":

            pts = [(float(p[0]), float(p[1]), float(p[2])) for p in entity.get_points("xyb")]

            for p1, p2 in zip(pts, pts[1:]):

                out.append(((p1[0], p1[1]), (p2[0], p2[1]), p1[2]))

            if entity.closed and len(pts) > 2:

                p1, p2 = pts[-1], pts[0]

                out.append(((p1[0], p1[1]), (p2[0], p2[1]), p1[2]))

    return out





def _has_segment(segs, start, end, straight=True):

    vx = float(end[0]) - float(start[0])

    vy = float(end[1]) - float(start[1])

    length = (vx * vx + vy * vy) ** 0.5

    if length <= 0:

        return False

    gap_tol = TOL / max(length, 1.0)



    def interval_for(a, b):

        ax = float(a[0]) - float(start[0])

        ay = float(a[1]) - float(start[1])

        bx = float(b[0]) - float(start[0])

        by = float(b[1]) - float(start[1])

        if abs(ax * vy - ay * vx) > TOL * max(length, 1.0):

            return None

        if abs(bx * vy - by * vx) > TOL * max(length, 1.0):

            return None

        t1 = (ax * vx + ay * vy) / (length * length)

        t2 = (bx * vx + by * vy) / (length * length)

        lo, hi = sorted((t1, t2))

        if hi < -gap_tol or lo > 1.0 + gap_tol:

            return None

        return max(0.0, lo), min(1.0, hi)



    intervals = []

    for a, b, bulge in segs:

        if straight and abs(bulge) > 0.05:

            continue

        interval = interval_for(a, b)

        if interval is not None:

            intervals.append(interval)

    if not intervals:

        return False

    covered = 0.0

    for lo, hi in sorted(intervals):

        if hi < covered - gap_tol:

            continue

        if lo > covered + gap_tol:

            return False

        covered = max(covered, hi)

        if covered >= 1.0 - gap_tol:

            return True

    return covered >= 1.0 - gap_tol





def _has_bulge_arc(segs, start, end):

    return any(

        abs(bulge) > 0.2 and ((_point_close(a, start) and _point_close(b, end)) or (_point_close(a, end) and _point_close(b, start)))

        for a, b, bulge in segs

    )





def _has_arc_entity(doc, center, radius, endpoints):

    for entity in doc.modelspace():

        if entity.dxftype() != "ARC":

            continue

        c = entity.dxf.center

        if not (_point_close((c.x, c.y), center) and _close(entity.dxf.radius, radius)):

            continue

        pts = []

        for angle in [entity.dxf.start_angle, entity.dxf.end_angle]:

            radians = math.radians(float(angle))

            pts.append((c.x + entity.dxf.radius * math.cos(radians), c.y + entity.dxf.radius * math.sin(radians)))

        if all(any(_point_close(p, q) for p in pts) for q in endpoints):

            return True

    return False





def _has_rect(doc):

    segs = _segments(doc)

    corners = [(0, 0), (180, 0), (180, 60), (0, 60)]

    return all(_has_segment(segs, corners[i], corners[(i + 1) % 4]) for i in range(4))





def _has_slot(doc, cx):

    segs = _segments(doc)

    left, right = cx - 13, cx + 13

    top = _has_segment(segs, (left, 35), (right, 35))

    bottom = _has_segment(segs, (left, 25), (right, 25))

    left_arc = _has_bulge_arc(segs, (left, 25), (left, 35)) or _has_arc_entity(doc, (left, 30), 5, [(left, 25), (left, 35)])

    right_arc = _has_bulge_arc(segs, (right, 35), (right, 25)) or _has_arc_entity(doc, (right, 30), 5, [(right, 35), (right, 25)])

    return top and bottom and left_arc and right_arc




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

    corner_holes = [(20, 15), (160, 15), (20, 45), (160, 45)]

    return (
        _has_rect(doc)
        and _has_slot(doc, 60)
        and _has_slot(doc, 120)
        and all(_has_circle(doc, p, 3) for p in corner_holes)
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
