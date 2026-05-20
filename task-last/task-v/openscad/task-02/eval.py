from __future__ import annotations

import math
import os
import struct
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))



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

SPEC = {'output': 'task-002_output.stl',
 'bbox': [100.0, 60.0, 6.0],
 'bbox_tol': 1.0,
 'min_triangles': 120,
 'checks': [{'kind': 'cylinder', 'axis': 'z', 'center': [-38.0, -18.0], 'radius': 3.0, 'span': 5.0, 'bins': 12},
            {'kind': 'cylinder', 'axis': 'z', 'center': [-38.0, 18.0], 'radius': 3.0, 'span': 5.0, 'bins': 12},
            {'kind': 'cylinder', 'axis': 'z', 'center': [38.0, -18.0], 'radius': 3.0, 'span': 5.0, 'bins': 12},
            {'kind': 'cylinder', 'axis': 'z', 'center': [38.0, 18.0], 'radius': 3.0, 'span': 5.0, 'bins': 12}]}


def _parse_stl(path: Path):
    data = path.read_bytes()
    triangles = []
    if len(data) >= 84:
        count = struct.unpack("<I", data[80:84])[0]
        if 84 + count * 50 == len(data):
            for i in range(count):
                values = struct.unpack("<12fH", data[84 + i * 50:134 + i * 50])
                coords = values[3:12]
                triangles.append(tuple((coords[j], coords[j + 1], coords[j + 2]) for j in range(0, 9, 3)))
            return triangles
    vertices = []
    for raw in data.decode("utf-8", errors="ignore").splitlines():
        parts = raw.strip().split()
        if len(parts) == 4 and parts[0].lower() == "vertex":
            vertices.append(tuple(float(v) for v in parts[1:]))
            if len(vertices) == 3:
                triangles.append(tuple(vertices))
                vertices = []
    return triangles


def _parse_off(path: Path):
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#")]
    if not lines or lines[0] != "OFF":
        return []
    n_vertices, n_faces, _ = [int(v) for v in lines[1].split()[:3]]
    vertices = [tuple(float(v) for v in lines[2 + i].split()[:3]) for i in range(n_vertices)]
    triangles = []
    for line in lines[2 + n_vertices:2 + n_vertices + n_faces]:
        parts = [int(v) for v in line.split()]
        if parts[0] >= 3:
            ids = parts[1:1 + parts[0]]
            for i in range(1, len(ids) - 1):
                triangles.append((vertices[ids[0]], vertices[ids[i]], vertices[ids[i + 1]]))
    return triangles


def _parse_3mf(path: Path):
    with zipfile.ZipFile(path) as archive:
        model_name = next(name for name in archive.namelist() if name.lower().endswith(".model"))
        root = ET.fromstring(archive.read(model_name))
    vertices = []
    triangles = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "vertex":
            vertices.append((float(elem.attrib["x"]), float(elem.attrib["y"]), float(elem.attrib["z"])))
        elif tag == "triangle":
            triangles.append((vertices[int(elem.attrib["v1"])], vertices[int(elem.attrib["v2"])], vertices[int(elem.attrib["v3"])]))
    return triangles


def _mesh_triangles(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".stl":
        return _parse_stl(path)
    if suffix == ".off":
        return _parse_off(path)
    if suffix == ".3mf":
        return _parse_3mf(path)
    return []


class Mesh:
    def __init__(self, triangles):
        self.triangles = triangles
        seen = {}
        for tri in triangles:
            for point in tri:
                seen[(round(point[0], 3), round(point[1], 3), round(point[2], 3))] = point
        self.vertices = list(seen.values())
        if self.vertices:
            self.mins = [min(p[i] for p in self.vertices) for i in range(3)]
            self.maxs = [max(p[i] for p in self.vertices) for i in range(3)]
        else:
            self.mins = [0.0, 0.0, 0.0]
            self.maxs = [0.0, 0.0, 0.0]

    @property
    def extents(self):
        return [self.maxs[i] - self.mins[i] for i in range(3)]

    @property
    def center(self):
        return [(self.maxs[i] + self.mins[i]) / 2 for i in range(3)]


def _close(actual, expected, tol):
    return abs(float(actual) - float(expected)) <= tol


def _bbox_ok(mesh: Mesh, expected, tol):
    return all(_close(actual, want, tol) for actual, want in zip(mesh.extents, expected))


def _axis_components(point, axis):
    x, y, z = point
    if axis == "z":
        return x, y, z
    if axis == "y":
        return x, z, y
    if axis == "x":
        return y, z, x
    raise ValueError(axis)


def _angle_in_range(angle, start, end):
    if start is None:
        return True
    deg = math.degrees(angle)
    if deg < 0:
        deg += 360
    start = float(start) % 360
    end = float(end) % 360
    if start <= end:
        return start <= deg <= end
    return deg >= start or deg <= end


def _cylinder_points(mesh: Mesh, check):
    axis = check["axis"]
    center_a, center_b = check["center"]
    radius = float(check["radius"])
    tol = float(check.get("tol", max(0.35, radius * 0.18)))
    axial_range = check.get("axial_range")
    angle_range = check.get("angle_range")
    points = []
    for point in mesh.vertices:
        a, b, axial = _axis_components(point, axis)
        if axial_range and not (float(axial_range[0]) - 0.75 <= axial <= float(axial_range[1]) + 0.75):
            continue
        angle = math.atan2(b - center_b, a - center_a)
        if angle_range and not _angle_in_range(angle, angle_range[0], angle_range[1]):
            continue
        dist = math.hypot(a - center_a, b - center_b)
        if abs(dist - radius) <= tol:
            points.append((angle, axial))
    return points


def _has_cylinder(mesh: Mesh, check):
    points = _cylinder_points(mesh, check)
    if len(points) < int(check.get("min_points", 8)):
        return False
    bins = {int(((angle + math.pi) / (2 * math.pi)) * 72) % 72 for angle, _ in points}
    if len(bins) < int(check.get("bins", 10)):
        return False
    axials = [axis for _, axis in points]
    return max(axials) - min(axials) >= float(check.get("span", 0.0))


def _has_circle_at(mesh: Mesh, check):
    axis = check["axis"]
    center_a, center_b = check.get("center", [0.0, 0.0])
    radius = float(check["radius"])
    axial = float(check["axial"])
    tol = float(check.get("tol", 0.6))
    bins = set()
    for point in mesh.vertices:
        a, b, t = _axis_components(point, axis)
        if abs(t - axial) > float(check.get("axial_tol", 0.75)):
            continue
        dist = math.hypot(a - center_a, b - center_b)
        if abs(dist - radius) <= tol:
            angle = math.atan2(b - center_b, a - center_a)
            bins.add(int(((angle + math.pi) / (2 * math.pi)) * 72) % 72)
    return len(bins) >= int(check.get("bins", 10))


def _has_slot(mesh: Mesh, check):
    cx, cy = check["center"]
    length = float(check["length"])
    width = float(check["width"])
    span = float(check["span"])
    tol = float(check.get("tol", 0.8))
    pts = [p for p in mesh.vertices if abs(p[0] - cx) <= length / 2 + tol and abs(p[1] - cy) <= width / 2 + tol]
    if len(pts) < 8:
        return False
    if max(p[2] for p in pts) - min(p[2] for p in pts) < span:
        return False
    if max(p[0] for p in pts) - min(p[0] for p in pts) < length - 1.0:
        return False
    if max(p[1] for p in pts) - min(p[1] for p in pts) < width - 0.8:
        return False
    offset = (length - width) / 2
    left = {"axis": "z", "center": [cx - offset, cy], "radius": width / 2, "span": span, "bins": 4, "tol": 0.5}
    right = {"axis": "z", "center": [cx + offset, cy], "radius": width / 2, "span": span, "bins": 4, "tol": 0.5}
    return _has_cylinder(mesh, left) and _has_cylinder(mesh, right)


def _near_vertex(mesh: Mesh, target, tol):
    tx, ty, tz = target
    return any(abs(x - tx) <= tol and abs(y - ty) <= tol and abs(z - tz) <= tol for x, y, z in mesh.vertices)


def _has_rect_outline(mesh: Mesh, check):
    width = float(check["width"])
    height = float(check["height"])
    tol = float(check.get("tol", 0.75))
    for z in check["zs"]:
        for x in (-width / 2, width / 2):
            for y in (-height / 2, height / 2):
                if not _near_vertex(mesh, (x, y, float(z)), tol):
                    return False
    return True


def _has_box_outline(mesh: Mesh, check):
    tol = float(check.get("tol", 1.0))
    for x in check["xs"]:
        for y in check["ys"]:
            for z in check["zs"]:
                if not _near_vertex(mesh, (float(x), float(y), float(z)), tol):
                    return False
    return True


def _cluster_count(values, gap):
    if not values:
        return 0
    values = sorted(values)
    clusters = 1
    last = values[0]
    for value in values[1:]:
        if value - last > gap:
            clusters += 1
        last = value
    return clusters


def _has_rib_clusters(mesh: Mesh, check):
    xs = []
    for x, y, z in mesh.vertices:
        if check["x_range"][0] <= x <= check["x_range"][1] and check["y_range"][0] <= y <= check["y_range"][1] and check["z_range"][0] <= z <= check["z_range"][1]:
            xs.append(x)
    return _cluster_count(xs, float(check.get("gap", 8.0))) >= int(check["count"])


def _has_raised(mesh: Mesh, check):
    pts = [p for p in mesh.vertices if p[2] >= float(check["z_min"])]
    if len(pts) < int(check.get("min_points", 8)):
        return False
    return (max(p[0] for p in pts) - min(p[0] for p in pts) >= float(check["x_span"]) and
            max(p[1] for p in pts) - min(p[1] for p in pts) >= float(check["y_span"]))


def _has_steps(mesh: Mesh, check):
    tol = float(check.get("tol", 0.75))
    depth = float(check["depth"])
    for item in check["levels"]:
        z = float(item["top"])
        width = float(item["width"])
        for x in (-width / 2, width / 2):
            for y in (-depth / 2, depth / 2):
                if not _near_vertex(mesh, (x, y, z), tol):
                    return False
    return True


def _has_angular_clusters(mesh: Mesh, check):
    center = check.get("center", [0.0, 0.0])
    r0, r1 = check["radius_range"]
    z0, z1 = check["z_range"]
    angles = []
    for x, y, z in mesh.vertices:
        r = math.hypot(x - center[0], y - center[1])
        if float(r0) <= r <= float(r1) and float(z0) <= z <= float(z1):
            deg = math.degrees(math.atan2(y - center[1], x - center[0]))
            if deg < 0:
                deg += 360
            angles.append(deg)
    if not angles:
        return False
    angles.sort()
    clusters = 1
    last = angles[0]
    gap = float(check.get("gap", 6.0))
    for angle in angles[1:]:
        if angle - last > gap:
            clusters += 1
        last = angle
    if angles[0] + 360 - angles[-1] <= gap and clusters > 1:
        clusters -= 1
    return clusters >= int(check["count"])


def _parse_dxf(path: Path):
    raw = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    pairs = []
    for i in range(0, len(raw) - 1, 2):
        pairs.append((raw[i], raw[i + 1]))
    entities = []
    current = None
    for code, value in pairs:
        if code == "0":
            if current:
                entities.append(current)
            current = {"type": value, "points": []}
            continue
        if current is None:
            continue
        if code == "10":
            current.setdefault("_x", []).append(float(value))
        elif code == "20":
            xs = current.setdefault("_x", [])
            if xs:
                current["points"].append((xs.pop(0), float(value)))
        elif code == "40":
            current["radius"] = float(value)
    if current:
        entities.append(current)
    circles = []
    polylines = []
    for ent in entities:
        if ent.get("type") == "CIRCLE" and ent.get("points"):
            x, y = ent["points"][0]
            circles.append((x, y, float(ent.get("radius", 0.0))))
        elif ent.get("type") in {"LWPOLYLINE", "POLYLINE"} and ent.get("points"):
            polylines.append(ent["points"])
    return circles, polylines


def _dxf_circle(circles, check):
    cx, cy = check["center"]
    r = float(check["radius"])
    tol = float(check.get("tol", 0.5))
    return any(abs(x - cx) <= tol and abs(y - cy) <= tol and abs(rad - r) <= tol for x, y, rad in circles)


def _dxf_rect(polylines, check):
    width = float(check["width"])
    height = float(check["height"])
    cx, cy = check.get("center", [0.0, 0.0])
    tol = float(check.get("tol", 0.75))
    for pts in polylines:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if abs((max(xs) - min(xs)) - width) <= tol and abs((max(ys) - min(ys)) - height) <= tol:
            if abs((max(xs) + min(xs)) / 2 - cx) <= tol and abs((max(ys) + min(ys)) / 2 - cy) <= tol:
                return True
    return False


def _dxf_outline_min(polylines, check):
    width = float(check["min_width"])
    height = float(check["min_height"])
    for pts in polylines:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        if max(xs) - min(xs) >= width and max(ys) - min(ys) >= height:
            return True
    return False


def _run_mesh_check(mesh: Mesh, check):
    kind = check["kind"]
    if kind == "cylinder":
        return _has_cylinder(mesh, check)
    if kind == "circle_at":
        return _has_circle_at(mesh, check)
    if kind == "slot":
        return _has_slot(mesh, check)
    if kind == "rib_clusters":
        return _has_rib_clusters(mesh, check)
    if kind == "rect_outline":
        return _has_rect_outline(mesh, check)
    if kind == "box_outline":
        return _has_box_outline(mesh, check)
    if kind == "raised":
        return _has_raised(mesh, check)
    if kind == "steps":
        return _has_steps(mesh, check)
    if kind == "angular_clusters":
        return _has_angular_clusters(mesh, check)
    return False


def _evaluate_mesh(path: Path) -> bool:
    mesh = Mesh(_mesh_triangles(path))
    if len(mesh.triangles) < int(SPEC.get("min_triangles", 1)):
        return False
    if len(mesh.vertices) < int(SPEC.get("min_vertices", 8)):
        return False
    tol = float(SPEC.get("bbox_tol", 1.0))
    if "bbox" in SPEC and not _bbox_ok(mesh, SPEC["bbox"], tol):
        return False
    if "bbox_sorted_xy" in SPEC:
        actual = sorted(mesh.extents[:2])
        expected = sorted([float(v) for v in SPEC["bbox_sorted_xy"]])
        if any(abs(a - b) > tol for a, b in zip(actual, expected)):
            return False
    if "z_extent" in SPEC and abs(mesh.extents[2] - float(SPEC["z_extent"])) > tol:
        return False
    if "center" in SPEC:
        center_tol = float(SPEC.get("center_tol", tol))
        if any(abs(a - b) > center_tol for a, b in zip(mesh.center, SPEC["center"])):
            return False
    return all(_run_mesh_check(mesh, check) for check in SPEC.get("checks", []))


def _evaluate_dxf(path: Path) -> bool:
    circles, polylines = _parse_dxf(path)
    for check in SPEC.get("checks", []):
        if check["kind"] == "dxf_circle" and not _dxf_circle(circles, check):
            return False
        if check["kind"] == "dxf_rect" and not _dxf_rect(polylines, check):
            return False
        if check["kind"] == "dxf_outline_min" and not _dxf_outline_min(polylines, check):
            return False
    return True


def _evaluate_csg(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if len(text) < int(SPEC.get("min_size", 1)):
        return False
    return all(token in text for token in SPEC.get("tokens", []))


def evaluate() -> bool:
    if not check_no_gui_bypass(OUTPUT_ROOT):
        return False
    path = OUTPUT_ROOT / SPEC["output"]
    if not path.exists() or path.stat().st_size <= 0:
        return False
    suffix = path.suffix.lower()
    if suffix == ".dxf":
        return _evaluate_dxf(path)
    if suffix == ".csg":
        return _evaluate_csg(path)
    return _evaluate_mesh(path)


if __name__ == "__main__":
    try:
        if not check_no_gui_bypass(OUTPUT_ROOT):
            ok = False
        else:
            ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
