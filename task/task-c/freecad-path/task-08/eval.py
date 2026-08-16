from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import shlex
import stat
import subprocess
import sys
import tempfile
import traceback
import base64
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from pathlib import PurePosixPath


ROOT = Path("/home/user/Desktop")
FCSTD_PATH = ROOT / "task-08.FCStd"
STEP_PATH = ROOT / "rest_shape.step"
NC_PATH = ROOT / "task-08.nc"
EXPECTED_STEP_SHA256 = "6422d10ff940f6e558a26d5b1a85597e103de0a3c36b83774397d5be500abcf7"
EXPECTED_FREECAD_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
FREECADCMD = Path("/usr/bin/freecadcmd")
INNER_ENV = "ENGIWORLD_TASK08_FREECAD"
MARKER_ENV = "ENGIWORLD_TASK08_MARKER"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.IGNORECASE)
TOP_Z = 18.0
FLOOR_Z = 6.0
ALLOWED_OBJECT_TYPES = {
    "App::DocumentObjectGroup",
    "App::FeaturePython",
    "Part::Feature",
    "Part::FeaturePython",
    "PartDesign::Feature",
    "Path::FeaturePython",
    "Sketcher::SketchObject",
}
ALLOWED_PROXY_PAIRS = {
    ("Path.Base.SetupSheet", "SetupSheet"),
    ("Path.Main.Job", "ObjectJob"),
    ("Path.Main.Stock", "StockCreateBox"),
    ("Path.Main.Stock", "StockFromBase"),
    ("Path.Op.Adaptive", "PathAdaptive"),
    ("Path.Op.PocketShape", "ObjectPocket"),
    ("Path.Tool.Bit", "ToolBit"),
    ("Path.Tool.Controller", "ToolController"),
    ("draftobjects.clone", "Clone"),
}
ALLOWED_PROXY_STATES = {b"null", b"{}", b'"Clone"'}


def regular_file(path: Path, maximum_size: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not path.is_symlink() and 0 < info.st_size <= maximum_size


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_fcstd_container(path: Path) -> bool:
    if not regular_file(path, 20 * 1024 * 1024) or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (
                not 1 <= len(entries) <= 200
                or len(names) != len(set(names))
                or names.count("Document.xml") != 1
                or sum(entry.file_size for entry in entries) > 50 * 1024 * 1024
            ):
                return False
            for entry in entries:
                member = PurePosixPath(entry.filename)
                mode = (entry.external_attr >> 16) & 0o170000
                if (
                    entry.flag_bits & 0x1
                    or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                    or entry.file_size > 25 * 1024 * 1024
                    or entry.filename.startswith("/")
                    or "\\" in entry.filename
                    or ".." in member.parts
                    or mode == stat.S_IFLNK
                    or member.suffix.lower() in {".py", ".pyc", ".pyd", ".so", ".dll", ".exe", ".sh"}
                ):
                    return False
            xml_data = archive.read("Document.xml")
    except (OSError, KeyError, RuntimeError, zipfile.BadZipFile):
        return False
    if len(xml_data) > 5 * 1024 * 1024 or b"<!DOCTYPE" in xml_data.upper() or b"<!ENTITY" in xml_data.upper():
        return False
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return False
    objects = root.find("Objects")
    object_data = root.find("ObjectData")
    if objects is None or object_data is None:
        return False
    declarations = objects.findall("Object")
    data_objects = object_data.findall("Object")
    declared_names = [obj.get("name", "") for obj in declarations]
    data_names = [obj.get("name", "") for obj in data_objects]
    if (
        not 1 <= len(declarations) <= 100
        or len(declared_names) != len(set(declared_names))
        or set(declared_names) != set(data_names)
        or any(obj.get("type") not in ALLOWED_OBJECT_TYPES for obj in declarations)
    ):
        return False
    for extension in root.findall(".//Extension"):
        if extension.get("type") not in {
            "App::GroupExtension",
            "App::GroupExtensionPython",
            "Part::AttachExtension",
            "Part::AttachExtensionPython",
        }:
            return False
    all_python_properties = root.findall('.//*[@type="App::PropertyPythonObject"]')
    audited_python_properties = []
    for obj in data_objects:
        proxy_pair = None
        python_properties = [
            prop
            for prop in obj.findall("./Properties/Property")
            if prop.get("type") == "App::PropertyPythonObject"
        ]
        audited_python_properties.extend(python_properties)
        for prop in python_properties:
            name = prop.get("name", "")
            nodes = prop.findall("Python")
            if len(nodes) != 1 or name not in {"Proxy", "AdaptiveInputState", "AdaptiveOutputState"}:
                return False
            node = nodes[0]
            if node.get("encoded") != "yes":
                return False
            try:
                decoded = base64.b64decode(node.get("value", ""), validate=True)
            except (ValueError, TypeError):
                return False
            module = node.get("module")
            class_name = node.get("class")
            if name == "Proxy":
                if (module, class_name) not in ALLOWED_PROXY_PAIRS or decoded not in ALLOWED_PROXY_STATES:
                    return False
                proxy_pair = (module, class_name)
            else:
                if module is not None or class_name is not None or node.get("json") != "yes":
                    return False
                try:
                    json.loads(decoded.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return False
        state_names = {prop.get("name") for prop in python_properties if prop.get("name") != "Proxy"}
        if state_names and proxy_pair is not None and proxy_pair[0] != "Path.Op.Adaptive":
            return False
    if len(all_python_properties) != len(audited_python_properties) or {
        id(prop) for prop in all_python_properties
    } != {id(prop) for prop in audited_python_properties}:
        return False
    return True


def close(first, second, tolerance: float = 1e-5) -> bool:
    return abs(float(first) - float(second)) <= tolerance


def proxy_module(obj) -> str:
    proxy = getattr(obj, "Proxy", None)
    return getattr(proxy.__class__, "__module__", "") if proxy is not None else ""


def shapes_equal(first, second, tolerance: float = 1e-5) -> bool:
    try:
        return (
            first.isValid()
            and second.isValid()
            and first.cut(second).Volume <= tolerance
            and second.cut(first).Volume <= tolerance
        )
    except Exception:
        return False


def object_state_clean(obj) -> bool:
    try:
        states = {str(value) for value in obj.State}
    except Exception:
        return False
    return not states.intersection({"Touched", "Invalid", "Error"})


def distance_to_segment(px: float, py: float, start, end) -> float:
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    denominator = dx * dx + dy * dy
    if denominator <= 1e-16:
        return math.hypot(px - ax, py - ay)
    scale = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denominator))
    return math.hypot(px - (ax + scale * dx), py - (ay + scale * dy))


def path_motions(commands):
    current = {"X": None, "Y": None, "Z": None}
    motions = []
    for command in commands:
        before = dict(current)
        parameters = command.Parameters
        for axis in ("X", "Y", "Z"):
            if axis in parameters:
                current[axis] = float(parameters[axis])
        name = str(command.Name).upper().replace(" ", "")
        current_complete = all(current[axis] is not None for axis in ("X", "Y", "Z"))
        before_complete = all(before[axis] is not None for axis in ("X", "Y", "Z"))
        if not before_complete and current_complete and name in {"G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"}:
            motions.append(("G0" if name in {"G0", "G00"} else "G1", dict(current), dict(current)))
            continue
        if name in {"G0", "G00", "G1", "G01"} and all(
            before[axis] is not None and current[axis] is not None for axis in ("X", "Y", "Z")
        ):
            motions.append(("G0" if name in {"G0", "G00"} else "G1", before, dict(current)))
        elif name in {"G2", "G02", "G3", "G03"} and all(
            before[axis] is not None and current[axis] is not None for axis in ("X", "Y", "Z")
        ):
            if "I" not in parameters and "J" not in parameters:
                raise ValueError("unsupported arc without I/J center offsets")
            center_x = before["X"] + float(parameters.get("I", 0.0))
            center_y = before["Y"] + float(parameters.get("J", 0.0))
            start_angle = math.atan2(before["Y"] - center_y, before["X"] - center_x)
            end_angle = math.atan2(current["Y"] - center_y, current["X"] - center_x)
            radius = math.hypot(before["X"] - center_x, before["Y"] - center_y)
            end_radius = math.hypot(current["X"] - center_x, current["Y"] - center_y)
            if radius <= 1e-8 or abs(radius - end_radius) > 1e-4:
                raise ValueError("invalid arc radius")
            clockwise = name in {"G2", "G02"}
            sweep = (start_angle - end_angle) % (2.0 * math.pi) if clockwise else (end_angle - start_angle) % (2.0 * math.pi)
            if sweep <= 1e-10:
                sweep = 2.0 * math.pi
            steps = max(2, int(math.ceil(radius * sweep / 0.25)))
            previous = dict(before)
            direction = -1.0 if clockwise else 1.0
            for step in range(1, steps + 1):
                fraction = step / steps
                angle = start_angle + direction * sweep * fraction
                point = {
                    "X": center_x + radius * math.cos(angle),
                    "Y": center_y + radius * math.sin(angle),
                    "Z": before["Z"] + (current["Z"] - before["Z"]) * fraction,
                }
                if step == steps:
                    point = dict(current)
                motions.append(("G1", previous, point))
                previous = point
    return motions


def contact_projection(before, after):
    """Return the XY projection of only the portion at or below the stock top."""
    before_z = before["Z"]
    after_z = after["Z"]
    if min(before_z, after_z) >= TOP_Z - 1e-4:
        return None

    start = dict(before)
    end = dict(after)
    delta_z = after_z - before_z
    if abs(delta_z) > 1e-12:
        fraction = (TOP_Z - before_z) / delta_z
        if 0.0 < fraction < 1.0:
            crossing = {
                axis: before[axis] + (after[axis] - before[axis]) * fraction
                for axis in ("X", "Y", "Z")
            }
            if before_z > TOP_Z:
                start = crossing
            elif after_z > TOP_Z:
                end = crossing
    return ((start["X"], start["Y"]), (end["X"], end["Y"]))


def operation_motions(operation):
    motions = path_motions(list(operation.Path.Commands))
    contact_segments = []
    floor_segments = []
    reached_floor = False
    for mode, before, after in motions:
        if min(before["Z"], after["Z"]) < FLOOR_Z - 1e-4:
            return None
        if mode == "G1" and abs(after["Z"] - FLOOR_Z) <= 1e-4:
            reached_floor = True
        if mode == "G1" and abs(before["Z"] - FLOOR_Z) <= 1e-4 and abs(after["Z"] - FLOOR_Z) <= 1e-4:
            floor_segments.append(((before["X"], before["Y"]), (after["X"], after["Y"])))
        contact = contact_projection(before, after)
        if contact is not None:
            contact_segments.append(contact)
    return (contact_segments, floor_segments) if reached_floor and floor_segments else None


def selected_faces(operation, Part, allow_edges: bool = False):
    faces = []
    boundaries = []
    try:
        bases = list(operation.Base)
    except Exception:
        return None
    if not bases:
        return None
    for boundary, names in bases:
        if boundary.Document != operation.Document or not names:
            return None
        boundaries.append(boundary)
        edges = []
        for name in names:
            name = str(name)
            if name.startswith("Edge") and allow_edges:
                try:
                    edges.append(boundary.Shape.getElement(name))
                except Exception:
                    return None
                continue
            if not name.startswith("Face"):
                return None
            try:
                face = boundary.Shape.getElement(name)
            except Exception:
                return None
            if not isinstance(face.Surface, Part.Plane):
                return None
            normal = face.normalAt(0.5, 0.5)
            if abs(abs(float(normal.z)) - 1.0) > 1e-5 or face.BoundBox.ZLength > 1e-5:
                return None
            copy = face.copy()
            copy.translate(__import__("FreeCAD").Vector(0.0, 0.0, TOP_Z - face.BoundBox.ZMin))
            faces.append(copy)
        if edges:
            try:
                import DraftGeomUtils

                wires = DraftGeomUtils.findWires(edges)
            except Exception:
                return None
            if not wires:
                return None
            for wire in wires:
                try:
                    if not wire.isClosed() or wire.BoundBox.ZLength > 1e-5:
                        return None
                    face = Part.Face(wire)
                    if not isinstance(face.Surface, Part.Plane):
                        return None
                    normal = face.normalAt(0.5, 0.5)
                    if abs(abs(float(normal.z)) - 1.0) > 1e-5:
                        return None
                    face.translate(__import__("FreeCAD").Vector(0.0, 0.0, TOP_Z - face.BoundBox.ZMin))
                    faces.append(face)
                except Exception:
                    return None
    return faces, boundaries


def fused_faces(faces):
    result = faces[0]
    for face in faces[1:]:
        result = result.fuse(face)
    try:
        result = result.removeSplitter()
    except Exception:
        pass
    return result


def expected_regions(Part, App):
    main = Part.makePlane(60.0, 36.0, App.Vector(-30.0, -18.0, TOP_Z))
    residuals = [
        Part.makePlane(8.0, 12.0, App.Vector(-4.0, 18.0, TOP_Z)),
        Part.makePlane(8.0, 12.0, App.Vector(-4.0, -30.0, TOP_Z)),
        Part.makePlane(12.0, 8.0, App.Vector(-42.0, -4.0, TOP_Z)),
        Part.makePlane(12.0, 8.0, App.Vector(30.0, -4.0, TOP_Z)),
    ]
    return main, residuals


def face_matches_region(face, expected, tolerance: float = 1e-4) -> bool:
    try:
        return face.cut(expected).Area <= tolerance and expected.cut(face).Area <= tolerance
    except Exception:
        return False


def rounded_rectangle_contains(x, y, bbox, radius):
    center_x = min(max(x, bbox.XMin + radius), bbox.XMax - radius)
    center_y = min(max(y, bbox.YMin + radius), bbox.YMax - radius)
    return math.hypot(x - center_x, y - center_y) <= radius + 1e-8


def segment_sweep(Part, App, start, end, radius: float):
    start_point = App.Vector(start[0], start[1], TOP_Z)
    end_point = App.Vector(end[0], end[1], TOP_Z)

    def disk(center):
        return Part.Face(Part.Wire([Part.makeCircle(radius, center)]))

    length = math.hypot(end[0] - start[0], end[1] - start[1])
    sweep = disk(start_point)
    if length <= 1e-10:
        return sweep
    normal_x = -(end[1] - start[1]) * radius / length
    normal_y = (end[0] - start[0]) * radius / length
    corners = [
        App.Vector(start[0] + normal_x, start[1] + normal_y, TOP_Z),
        App.Vector(end[0] + normal_x, end[1] + normal_y, TOP_Z),
        App.Vector(end[0] - normal_x, end[1] - normal_y, TOP_Z),
        App.Vector(start[0] - normal_x, start[1] - normal_y, TOP_Z),
    ]
    strip = Part.Face(Part.makePolygon(corners + [corners[0]]))
    return sweep.fuse(strip).fuse(disk(end_point)).removeSplitter()


def validate_region_path(operation, region_faces, allowed_face, diameter: float) -> bool:
    motion_sets = operation_motions(operation)
    if motion_sets is None:
        return False
    contact_segments, floor_segments = motion_sets
    radius = diameter / 2.0
    for face in region_faces:
        bbox = face.BoundBox
        if min(bbox.XLength, bbox.YLength) <= diameter:
            return False
        samples = 0
        x = bbox.XMin
        while x <= bbox.XMax + 1e-8:
            y = bbox.YMin
            while y <= bbox.YMax + 1e-8:
                point = __import__("FreeCAD").Vector(x, y, TOP_Z)
                if face.isInside(point, 1e-6, True) and rounded_rectangle_contains(x, y, bbox, radius):
                    if min(distance_to_segment(x, y, start, end) for start, end in floor_segments) > radius + 0.12:
                        return False
                    samples += 1
                y += 0.5
            x += 0.5
        if samples < 100:
            return False
    Part = __import__("Part")
    App = __import__("FreeCAD")
    stock_footprint = Part.makePlane(120.0, 80.0, App.Vector(-60.0, -40.0, TOP_Z))
    for start, end in contact_segments:
        sweep = segment_sweep(Part, App, start, end, radius)
        material_contact = sweep.common(stock_footprint)
        if material_contact.cut(allowed_face).Area > 1e-4:
            return False
    return True


def strip_comments(text: str):
    output = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "(":
            end = text.find(")", index + 1)
            if end < 0 or "(" in text[index + 1 : end]:
                raise ValueError("malformed parenthesis comment")
            output.extend(" " for _ in range(index, end + 1))
            index = end + 1
        elif char == ")":
            raise ValueError("unmatched parenthesis")
        elif char == ";":
            end = text.find("\n", index)
            if end < 0:
                end = len(text)
            output.extend(" " for _ in range(index, end))
            index = end
        else:
            output.append(char)
            index += 1
    return "".join(output)


def parse_nc(text: str):
    executable = strip_comments(text)
    raw_lines = executable.splitlines()
    percent_lines = [index for index, line in enumerate(raw_lines) if line.strip() == "%"]
    nonempty = [index for index, line in enumerate(raw_lines) if line.strip()]
    if percent_lines and (len(percent_lines) != 2 or percent_lines != [nonempty[0], nonempty[-1]]):
        raise ValueError("illegal percent wrapper")
    blocks = []
    for raw_line in raw_lines:
        line = raw_line.strip().upper()
        if not line or line == "%":
            continue
        tokens = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor : match.start()].strip():
                raise ValueError("unparsed NC text")
            tokens.append((match.group(1).upper(), float(match.group(2))))
            cursor = match.end()
        if line[cursor:].strip() or not tokens:
            raise ValueError("unparsed NC line")
        blocks.append(tokens)
    if not blocks:
        raise ValueError("empty NC")
    return blocks


def canonical_blocks(text: str):
    result = []
    for block in parse_nc(text):
        normalized = []
        for letter, number in block:
            if letter == "N":
                continue
            if letter in {"G", "M", "T", "H", "O"} and close(number, round(number), 1e-9):
                value = str(int(round(number)))
            else:
                value = f"{number:.9f}".rstrip("0").rstrip(".")
                if value in {"-0", "+0"}:
                    value = "0"
            normalized.append(letter + value)
        result.append(tuple(sorted(normalized)))
    return result


def validate_nc_safety(text: str) -> bool:
    try:
        blocks = parse_nc(text)
    except Exception:
        return False
    state = {
        "units_mm": False,
        "absolute": False,
        "motion": None,
        "feed": None,
        "speed": None,
        "tool": None,
        "spindle": False,
        "tool_changed": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    changed_tools = []
    bottom_tools = set()
    saw_g21 = saw_g90 = ended = False
    for block_index, block in enumerate(blocks):
        words = {}
        g_codes = []
        m_codes = []
        for letter, number in block:
            if letter == "G":
                if not close(number, round(number), 1e-9):
                    return False
                g_codes.append(int(round(number)))
            elif letter == "M":
                if not close(number, round(number), 1e-9):
                    return False
                m_codes.append(int(round(number)))
            else:
                if letter in words:
                    return False
                words[letter] = number
        if any(code not in {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 55, 56, 57, 58, 59, 80, 90, 94} for code in g_codes):
            return False
        if any(code not in {2, 3, 4, 5, 6, 7, 8, 9, 30} for code in m_codes):
            return False
        if 21 in g_codes:
            state["units_mm"] = True
            saw_g21 = True
        if 90 in g_codes:
            state["absolute"] = True
            saw_g90 = True
        for code in g_codes:
            if code in (0, 1, 2, 3):
                state["motion"] = code
        if "T" in words:
            tool = int(round(words["T"]))
            if not close(words["T"], tool, 1e-9) or tool not in {1, 2}:
                return False
            state["tool"] = tool
        if "H" in words and (state["tool"] is None or not close(words["H"], state["tool"], 1e-9)):
            return False
        if "S" in words:
            if not close(words["S"], 7000, 1e-6):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if not close(words["F"], 500, 1e-5):
                return False
            state["feed"] = words["F"]
        if 5 in m_codes:
            state["spindle"] = False
        if 6 in m_codes:
            if state["spindle"] or state["tool"] is None:
                return False
            changed_tools.append(state["tool"])
            state["tool_changed"] = True
        if 3 in m_codes and 4 in m_codes:
            return False
        if 3 in m_codes or 4 in m_codes:
            if state["speed"] is None or not close(state["speed"], 7000, 1e-6):
                return False
            state["spindle"] = True
        before = {axis: state[axis] for axis in ("X", "Y", "Z")}
        moved = False
        for axis in ("X", "Y", "Z"):
            if axis in words:
                state[axis] = words[axis]
                moved = True
        if moved and state["motion"] in (0, 1, 2, 3):
            if not state["units_mm"] or not state["absolute"]:
                return False
            if state["motion"] != 0:
                if not state["tool_changed"] or not state["spindle"] or state["feed"] is None:
                    return False
                if state["Z"] is not None and state["Z"] < FLOOR_Z - 1e-4:
                    return False
                if state["Z"] is not None and abs(state["Z"] - FLOOR_Z) <= 1e-4:
                    bottom_tools.add(state["tool"])
        if 2 in m_codes or 30 in m_codes:
            if block_index != len(blocks) - 1 or state["spindle"]:
                return False
            ended = True
    return saw_g21 and saw_g90 and changed_tools == [1, 2] and bottom_tools == {1, 2} and ended


def valid_postprocessor_args(value: str) -> bool:
    try:
        arguments = shlex.split(value)
    except ValueError:
        return False
    flags = {
        "--no-header",
        "--no-comments",
        "--line-numbers",
        "--no-show-editor",
        "--modal",
        "--axis-modal",
        "--no-tlo",
    }
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in flags:
            index += 1
            continue
        if argument == "--precision":
            index += 1
            if index >= len(arguments) or not re.fullmatch(r"(?:[3-9]|1[0-5])", arguments[index]):
                return False
            index += 1
            continue
        if re.fullmatch(r"--precision=(?:[3-9]|1[0-5])", argument):
            index += 1
            continue
        return False
    return True


def evaluate_in_freecad() -> bool:
    import builtins

    builtins.pythonopen = open
    import FreeCAD as App
    import Part
    import Path.Post.Command as PathPostCommand
    from Path.Post.Processor import PostProcessor

    if App.Version()[:4] != ["0", "21", "2", "33771 (Git)"] or App.Version()[-1] != EXPECTED_FREECAD_COMMIT:
        return False
    if not all(
        regular_file(path, maximum)
        for path, maximum in ((STEP_PATH, 5 * 1024 * 1024), (FCSTD_PATH, 20 * 1024 * 1024), (NC_PATH, 5 * 1024 * 1024))
    ):
        return False
    if sha256(STEP_PATH) != EXPECTED_STEP_SHA256:
        return False

    source_shape = Part.read(str(STEP_PATH))
    if (
        source_shape.ShapeType != "Solid"
        or len(source_shape.Solids) != 1
        or not source_shape.isValid()
        or not close(source_shape.Volume, 142272.0, 1e-3)
        or not close(source_shape.BoundBox.XMin, -60)
        or not close(source_shape.BoundBox.XMax, 60)
        or not close(source_shape.BoundBox.YMin, -40)
        or not close(source_shape.BoundBox.YMax, 40)
        or not close(source_shape.BoundBox.ZMin, 0)
        or not close(source_shape.BoundBox.ZMax, TOP_Z)
    ):
        return False
    stock_shape = Part.makeBox(120.0, 80.0, TOP_Z, App.Vector(-60.0, -40.0, 0.0))
    target_void = stock_shape.cut(source_shape).removeSplitter()
    if not target_void.isValid() or len(target_void.Solids) != 1 or not close(target_void.Volume, 30528.0, 1e-3):
        return False
    target_void = target_void.Solids[0]

    document = App.openDocument(str(FCSTD_PATH))
    if document is None:
        return False
    jobs = [obj for obj in document.Objects if proxy_module(obj) == "Path.Main.Job"]
    all_ops = [obj for obj in document.Objects if proxy_module(obj).startswith("Path.Op.")]
    if len(jobs) != 1 or len(all_ops) != 2:
        return False
    job = jobs[0]
    operations = list(job.Operations.Group)
    if len(operations) != 2 or {obj.Name for obj in operations} != {obj.Name for obj in all_ops}:
        return False
    main, rest = operations

    tracked = list(document.Objects)
    for obj in tracked:
        obj.touch()
    document.recompute()
    if not all(object_state_clean(obj) for obj in tracked):
        return False

    if proxy_module(main) != "Path.Op.PocketShape" or proxy_module(rest) != "Path.Op.Adaptive":
        return False
    if (
        not close(main.ExtraOffset.Value, 0.0)
        or str(rest.OperationType) != "Clearing"
        or not close(rest.StockToLeave.Value, 0.0)
    ):
        return False
    if (
        str(job.PostProcessor).strip().lower() != "linuxcnc"
        or bool(job.SplitOutput)
        or os.path.normpath(str(job.PostProcessorOutputFile)) != str(NC_PATH)
        or not valid_postprocessor_args(str(job.PostProcessorArgs))
    ):
        return False
    fixtures = [str(value).strip().upper() for value in job.Fixtures]
    if fixtures != ["G54"]:
        return False
    if len(job.Model.Group) != 1 or not shapes_equal(job.Model.Group[0].Shape, source_shape):
        return False
    if not shapes_equal(job.Stock.Shape, stock_shape):
        return False

    if len(job.Tools.Group) != 2:
        return False
    controllers = {int(controller.ToolNumber): controller for controller in job.Tools.Group}
    if set(controllers) != {1, 2} or main.ToolController != controllers[1] or rest.ToolController != controllers[2]:
        return False
    for number, diameter in ((1, 10.0), (2, 4.0)):
        controller = controllers[number]
        if proxy_module(controller) != "Path.Tool.Controller" or proxy_module(controller.Tool) != "Path.Tool.Bit":
            return False
        if (
            not close(controller.Tool.Diameter.Value, diameter)
            or not close(controller.SpindleSpeed, 7000)
            or str(controller.SpindleDir) not in {"Forward", "Reverse"}
            or not close(controller.HorizFeed.getValueAs("mm/min").Value, 500)
            or not close(controller.VertFeed.getValueAs("mm/min").Value, 500)
        ):
            return False
    if not controllers[2].Tool.Diameter.Value < controllers[1].Tool.Diameter.Value:
        return False
    for operation in operations:
        if (
            not close(operation.StartDepth.Value, TOP_Z)
            or not close(operation.FinalDepth.Value, FLOOR_Z)
            or operation.StepDown.Value <= 0
            or operation.ClearanceHeight.Value <= operation.SafeHeight.Value
            or operation.SafeHeight.Value <= TOP_Z
        ):
            return False

    main_selection = selected_faces(main, Part)
    rest_selection = selected_faces(rest, Part, allow_edges=True)
    if main_selection is None or rest_selection is None:
        return False
    main_faces, main_boundaries = main_selection
    rest_faces, rest_boundaries = rest_selection
    expected_main, expected_residuals = expected_regions(Part, App)
    main_region = fused_faces(main_faces)
    rest_region = fused_faces(rest_faces)
    expected_rest = fused_faces(expected_residuals)
    if not face_matches_region(main_region, expected_main) or not face_matches_region(rest_region, expected_rest):
        return False
    operation_void = main_region.extrude(App.Vector(0.0, 0.0, FLOOR_Z - TOP_Z))
    operation_void = operation_void.fuse(rest_region.extrude(App.Vector(0.0, 0.0, FLOOR_Z - TOP_Z))).removeSplitter()
    if not shapes_equal(operation_void, target_void, 1e-3):
        return False

    allowed_region = fused_faces([expected_main, *expected_residuals])
    if not validate_region_path(main, [expected_main], allowed_region, 10.0):
        return False
    if not validate_region_path(rest, expected_residuals, allowed_region, 4.0):
        return False

    try:
        submitted_text = NC_PATH.read_text(encoding="utf-8")
    except Exception:
        return False
    if not validate_nc_safety(submitted_text):
        return False
    sections = PathPostCommand.buildPostList(job)
    if len(sections) != 1:
        return False
    with tempfile.TemporaryDirectory(prefix="engiworld-task08-eval-") as temporary:
        repost_path = Path(temporary) / "task-08.nc"
        try:
            PostProcessor.load("linuxcnc").export(sections[0][1], str(repost_path), str(job.PostProcessorArgs))
            repost_text = repost_path.read_text(encoding="utf-8")
        except BaseException:
            return False
        if canonical_blocks(submitted_text) != canonical_blocks(repost_text):
            return False
    return True


def run_outer() -> bool:
    if not safe_fcstd_container(FCSTD_PATH):
        return False
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        return False
    marker = "TASK08_RESULT_" + secrets.token_hex(16)
    evaluator = str(Path(__file__).resolve())
    command = (
        "import builtins; builtins.pythonopen=open; "
        f"exec(compile(open({evaluator!r}, encoding='utf-8').read(), {evaluator!r}, 'exec'))"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="engiworld-task08-home-") as isolated_home:
            environment = {
                "HOME": isolated_home,
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "LOGNAME": "user",
                "PATH": "/usr/bin:/bin",
                "USER": "user",
                "XDG_CACHE_HOME": str(Path(isolated_home) / ".cache"),
                "XDG_CONFIG_HOME": str(Path(isolated_home) / ".config"),
                INNER_ENV: "1",
                MARKER_ENV: marker,
            }
            completed = subprocess.run(
                [str(executable), "-c", command],
                capture_output=True,
                text=True,
                timeout=240,
                env=environment,
                cwd=isolated_home,
                check=False,
            )
    except Exception:
        return False
    marker_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith(marker + "=")]
    return completed.returncode == 0 and marker_lines == [marker + "=True"]


if __name__ == "__main__":
    if os.environ.get(INNER_ENV) == "1":
        marker = os.environ.get(MARKER_ENV, "")
        ok = False
        try:
            ok = evaluate_in_freecad()
        except BaseException:
            traceback.print_exc(file=sys.stderr)
            ok = False
        print(f"{marker}={bool(ok)}")
    else:
        print(True if run_outer() else False)
