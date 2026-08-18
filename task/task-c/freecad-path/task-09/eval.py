from __future__ import annotations

import base64
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
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from pathlib import PurePosixPath


ROOT = Path("/home/user/Desktop")
STEP_PATH = ROOT / "four_parts.step"
FCSTD_PATH = ROOT / "task-09.FCStd"
NC_PATH = ROOT / "task-09.nc"
EXPECTED_STEP_SHA256 = "4c21abad77d9eb4750e96b498aa9d199a17c1f088077a67eb8cbc3dced23d499"
EXPECTED_FREECAD_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
FREECADCMD = Path("/usr/bin/freecadcmd")
INNER_ENV = "ENGIWORLD_TASK09_FREECAD"
MARKER_ENV = "ENGIWORLD_TASK09_MARKER"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.IGNORECASE)
FIXTURES = ("G54", "G55", "G56", "G57")
G_MODAL_GROUPS = (
    frozenset({0, 1, 2, 3, 80}),
    frozenset({17}),
    frozenset({90}),
    frozenset({94}),
    frozenset({21}),
    frozenset({40}),
    frozenset({43, 49}),
    frozenset({54, 55, 56, 57}),
)
M_MODAL_GROUPS = (
    frozenset({2, 30}),
    frozenset({3, 4, 5}),
    frozenset({6}),
    frozenset({7, 8, 9}),
)
CENTERS = {
    "G54": (-60.0, -40.0),
    "G55": (60.0, -40.0),
    "G56": (-60.0, 40.0),
    "G57": (60.0, 40.0),
}
PART_BOUNDS = (-30.0, 30.0, -10.0, 10.0)
STOCK_BOUNDS = (-31.0, 31.0, -11.0, 11.0)
STOCK_TOP = 19.0
PART_TOP = 18.0
PART_BOTTOM = 0.0
TOOL_DIAMETER = 10.0
TOOL_RADIUS = TOOL_DIAMETER / 2.0
ALLOWED_OBJECT_TYPES = {
    "App::DocumentObjectGroup",
    "App::FeaturePython",
    "Part::Feature",
    "Part::FeaturePython",
    "PartDesign::Feature",
    "Path::FeaturePython",
}
ALLOWED_PROXY_PAIRS = {
    ("Path.Base.SetupSheet", "SetupSheet"),
    ("Path.Main.Job", "ObjectJob"),
    ("Path.Main.Stock", "StockCreateBox"),
    ("Path.Main.Stock", "StockFromBase"),
    ("Path.Op.MillFace", "ObjectFace"),
    ("Path.Op.Profile", "ObjectProfile"),
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


def normalized_text_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def safe_fcstd_container(path: Path) -> bool:
    if not regular_file(path, 30 * 1024 * 1024) or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (
                not 1 <= len(entries) <= 300
                or len(names) != len(set(names))
                or names.count("Document.xml") != 1
                or sum(entry.file_size for entry in entries) > 80 * 1024 * 1024
            ):
                return False
            for entry in entries:
                member = PurePosixPath(entry.filename)
                mode = (entry.external_attr >> 16) & 0o170000
                if (
                    entry.flag_bits & 0x1
                    or entry.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                    or entry.file_size > 30 * 1024 * 1024
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
    if len(xml_data) > 8 * 1024 * 1024 or b"<!DOCTYPE" in xml_data.upper() or b"<!ENTITY" in xml_data.upper():
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
        not 1 <= len(declarations) <= 150
        or len(declared_names) != len(set(declared_names))
        or set(declared_names) != set(data_names)
        or any(obj.get("type") not in ALLOWED_OBJECT_TYPES for obj in declarations)
    ):
        return False
    for extension in root.findall(".//Extension"):
        if extension.get("type") not in {
            "App::GroupExtension",
            "App::GroupExtensionPython",
            "Part::AttachExtensionPython",
        }:
            return False
    all_python_properties = root.findall('.//*[@type="App::PropertyPythonObject"]')
    audited_python_properties = []
    for obj in data_objects:
        python_properties = [
            prop
            for prop in obj.findall("./Properties/Property")
            if prop.get("type") == "App::PropertyPythonObject"
        ]
        audited_python_properties.extend(python_properties)
        for prop in python_properties:
            if prop.get("name") != "Proxy":
                return False
            nodes = prop.findall("Python")
            if len(nodes) != 1:
                return False
            node = nodes[0]
            if node.get("encoded") != "yes" or (node.get("module"), node.get("class")) not in ALLOWED_PROXY_PAIRS:
                return False
            try:
                decoded = base64.b64decode(node.get("value", ""), validate=True)
            except (ValueError, TypeError):
                return False
            if decoded not in ALLOWED_PROXY_STATES:
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


def distance_to_rectangle(x: float, y: float, bounds) -> float:
    xmin, xmax, ymin, ymax = bounds
    dx = max(xmin - x, 0.0, x - xmax)
    dy = max(ymin - y, 0.0, y - ymax)
    return math.hypot(dx, dy)


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
        before_complete = all(before[axis] is not None for axis in ("X", "Y", "Z"))
        current_complete = all(current[axis] is not None for axis in ("X", "Y", "Z"))
        if not before_complete and current_complete and name in {"G0", "G00", "G1", "G01"}:
            motions.append(("G0" if name in {"G0", "G00"} else "G1", dict(current), dict(current)))
            continue
        if name in {"G0", "G00", "G1", "G01"} and before_complete and current_complete:
            motions.append(("G0" if name in {"G0", "G00"} else "G1", before, dict(current)))
        elif name in {"G2", "G02", "G3", "G03"} and before_complete and current_complete:
            if "I" not in parameters and "J" not in parameters:
                raise ValueError("unsupported arc")
            center_x = before["X"] + float(parameters.get("I", 0.0))
            center_y = before["Y"] + float(parameters.get("J", 0.0))
            start_angle = math.atan2(before["Y"] - center_y, before["X"] - center_x)
            end_angle = math.atan2(current["Y"] - center_y, current["X"] - center_x)
            radius = math.hypot(before["X"] - center_x, before["Y"] - center_y)
            end_radius = math.hypot(current["X"] - center_x, current["Y"] - center_y)
            if radius <= 1e-8 or abs(radius - end_radius) > 1e-3:
                raise ValueError("invalid arc radius")
            clockwise = name in {"G2", "G02"}
            sweep = (start_angle - end_angle) % (2 * math.pi) if clockwise else (end_angle - start_angle) % (2 * math.pi)
            if sweep <= 1e-10:
                sweep = 2 * math.pi
            steps = max(2, int(math.ceil(radius * sweep / 0.2)))
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


def validate_rapid_safety(motions, safe_height: float) -> bool:
    for mode, before, after in motions:
        if mode != "G0":
            continue
        horizontal = math.hypot(after["X"] - before["X"], after["Y"] - before["Y"])
        if horizontal > 1e-6 and min(before["Z"], after["Z"]) < safe_height - 1e-4:
            return False
        if (
            horizontal <= 1e-6
            and min(before["Z"], after["Z"]) < PART_TOP - 1e-4
            and distance_to_rectangle(after["X"], after["Y"], PART_BOUNDS) < TOOL_RADIUS - 0.03
        ):
            return False
    return True


def validate_face_path(operation) -> bool:
    try:
        motions = path_motions(list(operation.Path.Commands))
    except Exception:
        return False
    if not motions or not validate_rapid_safety(motions, operation.SafeHeight.Value):
        return False
    horizontal = []
    reached = False
    for mode, before, after in motions:
        if mode == "G1" and min(before["Z"], after["Z"]) < PART_TOP - 1e-4:
            return False
        if mode == "G1" and close(before["Z"], PART_TOP, 1e-4) and close(after["Z"], PART_TOP, 1e-4):
            horizontal.append(((before["X"], before["Y"]), (after["X"], after["Y"])))
            reached = True
    if not reached or len(horizontal) < 4:
        return False
    xmin, xmax, ymin, ymax = STOCK_BOUNDS
    x = xmin
    sample_count = 0
    while x <= xmax + 1e-8:
        y = ymin
        while y <= ymax + 1e-8:
            if min(distance_to_segment(x, y, start, end) for start, end in horizontal) > TOOL_RADIUS + 0.12:
                return False
            sample_count += 1
            y += 0.5
        x += 0.5
    if sample_count < 4000:
        return False
    for start, end in horizontal:
        for point in (start, end):
            if not (-31.0 - TOOL_RADIUS - 0.25 <= point[0] <= 31.0 + TOOL_RADIUS + 0.25):
                return False
            if not (-11.0 - TOOL_RADIUS - 0.25 <= point[1] <= 11.0 + TOOL_RADIUS + 0.25):
                return False
    return True


def validate_profile_path(operation) -> bool:
    try:
        motions = path_motions(list(operation.Path.Commands))
    except Exception:
        return False
    if not motions or not validate_rapid_safety(motions, operation.SafeHeight.Value):
        return False
    bottom = []
    levels = set()
    contact_points = []
    for mode, before, after in motions:
        if mode != "G1":
            continue
        if min(before["Z"], after["Z"]) < PART_BOTTOM - 1e-4:
            return False
        if min(before["Z"], after["Z"]) < PART_TOP - 1e-4:
            contact_points.extend(((before["X"], before["Y"]), (after["X"], after["Y"])))
            if distance_to_rectangle(before["X"], before["Y"], PART_BOUNDS) < TOOL_RADIUS - 0.03:
                return False
            if distance_to_rectangle(after["X"], after["Y"], PART_BOUNDS) < TOOL_RADIUS - 0.03:
                return False
        if close(before["Z"], after["Z"], 1e-4) and after["Z"] < PART_TOP - 1e-4:
            levels.add(round(after["Z"], 3))
            if close(after["Z"], PART_BOTTOM, 1e-4):
                bottom.append(((before["X"], before["Y"]), (after["X"], after["Y"])))
    if levels != {0.0, 3.0, 6.0, 9.0, 12.0, 15.0} or len(bottom) < 8 or not contact_points:
        return False
    xmin, xmax, ymin, ymax = PART_BOUNDS
    boundary_samples = []
    value = xmin
    while value <= xmax + 1e-8:
        boundary_samples.extend(((value, ymin), (value, ymax)))
        value += 0.5
    value = ymin
    while value <= ymax + 1e-8:
        boundary_samples.extend(((xmin, value), (xmax, value)))
        value += 0.5
    for x, y in boundary_samples:
        if min(distance_to_segment(x, y, start, end) for start, end in bottom) > TOOL_RADIUS + 0.12:
            return False
    return True


def selected_top_geometry(operation, Part, allowed_objects, allow_empty=False, allow_edges=False) -> bool:
    try:
        bases = list(operation.Base)
    except Exception:
        return False
    if not bases and allow_empty:
        return True
    if len(bases) != 1:
        return False
    boundary, names = bases[0]
    names = [str(name) for name in names]
    if boundary not in allowed_objects or not names or len(names) != len(set(names)):
        return False
    top_faces = []
    for face in boundary.Shape.Faces:
        if isinstance(face.Surface, Part.Plane) and face.BoundBox.ZLength <= 1e-5:
            normal = face.normalAt(0.5, 0.5)
            if close(face.BoundBox.ZMin, PART_TOP) and close(normal.z, 1.0):
                top_faces.append(face)
    if len(top_faces) != 1:
        return False
    if len(names) == 1 and names[0].startswith("Face"):
        try:
            selected = boundary.Shape.getElement(names[0])
        except Exception:
            return False
        return selected.isSame(top_faces[0])
    if not allow_edges or not all(name.startswith("Edge") for name in names):
        return False
    try:
        selected_edges = [boundary.Shape.getElement(name) for name in names]
    except Exception:
        return False
    expected_edges = list(top_faces[0].OuterWire.Edges)
    return len(selected_edges) == len(expected_edges) and all(
        any(selected.isSame(expected) for expected in expected_edges) for selected in selected_edges
    )


def strip_comments(text: str):
    output = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "(":
            end = text.find(")", index + 1)
            if end < 0 or "(" in text[index + 1 : end]:
                raise ValueError("malformed comment")
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


def block_codes(block):
    codes = {"G": [], "M": []}
    for letter, number in block:
        if letter not in codes:
            continue
        if not close(number, round(number), 1e-9):
            raise ValueError("fractional G/M code")
        codes[letter].append(int(round(number)))
    for letter, groups in (("G", G_MODAL_GROUPS), ("M", M_MODAL_GROUPS)):
        values = codes[letter]
        if len(values) != len(set(values)):
            raise ValueError("duplicate G/M code")
        if any(sum(code in group for code in values) > 1 for group in groups):
            raise ValueError("conflicting modal codes")
    return codes["G"], codes["M"]


def canonical_blocks(text: str):
    result = []
    position = {axis: None for axis in ("X", "Y", "Z")}
    modal_motion = None
    for block in parse_nc(text):
        g_codes, _ = block_codes(block)
        words = {}
        code_words = []
        for letter, number in block:
            if letter == "N":
                continue
            if letter in {"G", "M"}:
                code_words.append((letter, number))
            else:
                if letter in words:
                    raise ValueError("duplicate NC word")
                words[letter] = number
        for code in g_codes:
            if code in (0, 1, 2, 3):
                modal_motion = code
        moved = any(axis in words for axis in ("X", "Y", "Z"))
        for axis in position:
            if axis in words:
                position[axis] = words[axis]
        if moved and modal_motion in (0, 1, 2, 3) and all(value is not None for value in position.values()):
            for axis, value in position.items():
                words.setdefault(axis, value)
        normalized = []
        for letter, number in code_words + list(words.items()):
            if letter in {"G", "M", "T", "H", "O"} and close(number, round(number), 1e-9):
                value = str(int(round(number)))
            else:
                precision = 3 if letter in {"X", "Y", "Z", "I", "J", "K", "F", "S"} else 6
                value = f"{number:.{precision}f}".rstrip("0").rstrip(".")
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
        "wcs": None,
        "X": None,
        "Y": None,
        "Z": None,
    }
    changed_tools = []
    cutting = {fixture: {"face": 0, "bottom": 0} for fixture in FIXTURES}
    saw_g21 = saw_g90 = ended = False
    terminators = 0
    for block_index, block in enumerate(blocks):
        words = {}
        try:
            g_codes, m_codes = block_codes(block)
        except ValueError:
            return False
        for letter, number in block:
            if letter not in {"G", "M"}:
                if letter in words:
                    return False
                words[letter] = number
        if any(code not in {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 55, 56, 57, 80, 90, 94} for code in g_codes):
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
            if 54 <= code <= 57:
                state["wcs"] = "G" + str(code)
        if "T" in words:
            tool = int(round(words["T"]))
            if not close(words["T"], tool, 1e-9) or tool != 1:
                return False
            state["tool"] = tool
        if "H" in words and (state["tool"] is None or not close(words["H"], state["tool"], 1e-9)):
            return False
        if "S" in words:
            if not close(words["S"], 7000, 1e-6):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if not close(words["F"], 500, 1e-4):
                return False
            state["feed"] = words["F"]
        if 5 in m_codes:
            state["spindle"] = False
        if 6 in m_codes:
            if state["spindle"] or state["tool"] is None or state["wcs"] not in FIXTURES:
                return False
            changed_tools.append((state["wcs"], state["tool"]))
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
            if not state["units_mm"] or not state["absolute"] or state["wcs"] not in FIXTURES:
                return False
            if state["motion"] != 0:
                if not state["tool_changed"] or not state["spindle"] or state["feed"] is None:
                    return False
                if state["Z"] is None or state["Z"] < PART_BOTTOM - 1e-4:
                    return False
                horizontal_motion = (
                    before["X"] is not None
                    and before["Y"] is not None
                    and state["X"] is not None
                    and state["Y"] is not None
                    and (
                        not close(before["X"], state["X"], 1e-9)
                        or not close(before["Y"], state["Y"], 1e-9)
                    )
                )
                if close(state["Z"], PART_TOP, 1e-4) and (
                    horizontal_motion
                ):
                    cutting[state["wcs"]]["face"] += 1
                if close(state["Z"], PART_BOTTOM, 1e-4) and (
                    horizontal_motion
                ):
                    cutting[state["wcs"]]["bottom"] += 1
        if 2 in m_codes or 30 in m_codes:
            terminators += 1
            if block_index != len(blocks) - 1 or state["spindle"]:
                return False
            ended = True
    return (
        saw_g21
        and saw_g90
        and changed_tools == [(fixture, 1) for fixture in FIXTURES]
        and all(values["face"] >= 4 and values["bottom"] >= 4 for values in cutting.values())
        and terminators == 1
        and ended
    )


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


def expected_source_shape(Part, App):
    return Part.makeCompound(
        [
            Part.makeBox(60.0, 20.0, 18.0, App.Vector(cx - 30.0, cy - 10.0, 0.0))
            for cx, cy in CENTERS.values()
        ]
    )


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
        for path, maximum in (
            (STEP_PATH, 5 * 1024 * 1024),
            (FCSTD_PATH, 30 * 1024 * 1024),
            (NC_PATH, 10 * 1024 * 1024),
        )
    ) or normalized_text_sha256(STEP_PATH) != EXPECTED_STEP_SHA256:
        return False

    source_shape = Part.read(str(STEP_PATH))
    expected_source = expected_source_shape(Part, App)
    if (
        source_shape.ShapeType != "Compound"
        or len(source_shape.Solids) != 4
        or not source_shape.isValid()
        or not shapes_equal(source_shape, expected_source, 1e-3)
    ):
        return False
    for solid in source_shape.Solids:
        if not close(solid.Volume, 21600.0, 1e-3):
            return False

    document = App.openDocument(str(FCSTD_PATH))
    if document is None:
        return False
    jobs = [obj for obj in document.Objects if proxy_module(obj) == "Path.Main.Job"]
    all_ops = [obj for obj in document.Objects if proxy_module(obj).startswith("Path.Op.")]
    if len(jobs) != 4 or len(all_ops) != 8:
        return False
    by_fixture = {}
    for job in jobs:
        fixtures = [str(value).strip().upper() for value in job.Fixtures]
        if len(fixtures) != 1 or fixtures[0] not in FIXTURES or fixtures[0] in by_fixture:
            return False
        by_fixture[fixtures[0]] = job
    if tuple(sorted(by_fixture, key=FIXTURES.index)) != FIXTURES:
        return False

    tracked = list(document.Objects)
    for obj in tracked:
        obj.touch()
    document.recompute()
    if not all(object_state_clean(obj) for obj in tracked):
        return False

    if not any(
        hasattr(obj, "Shape") and not obj.Shape.isNull() and shapes_equal(obj.Shape, source_shape, 1e-3)
        for obj in document.Objects
    ):
        return False
    expected_local = Part.makeBox(60.0, 20.0, 18.0, App.Vector(-30.0, -10.0, 0.0))
    expected_stock = Part.makeBox(62.0, 22.0, 19.0, App.Vector(-31.0, -11.0, 0.0))
    base_models = []
    combined = []
    post_args = None
    for fixture_index, fixture in enumerate(FIXTURES, start=1):
        job = by_fixture[fixture]
        if (
            str(job.PostProcessor).strip().lower() != "linuxcnc"
            or bool(job.SplitOutput)
            or os.path.normpath(str(job.PostProcessorOutputFile)) != str(NC_PATH)
            or not valid_postprocessor_args(str(job.PostProcessorArgs))
        ):
            return False
        if post_args is None:
            post_args = str(job.PostProcessorArgs)
        elif str(job.PostProcessorArgs) != post_args:
            return False
        if len(job.Model.Group) != 1 or not shapes_equal(job.Model.Group[0].Shape, expected_local, 1e-4):
            return False
        clone = job.Model.Group[0]
        linked_models = list(clone.Objects) if hasattr(clone, "Objects") else [clone]
        if len(linked_models) != 1 or not shapes_equal(linked_models[0].Shape, expected_local, 1e-4):
            return False
        local_model = linked_models[0]
        expected_center = CENTERS[fixture]
        if (
            not hasattr(local_model, "SourcePart")
            or local_model.SourcePart is None
            or not hasattr(local_model, "SourceSolidIndex")
            or int(local_model.SourceSolidIndex) != fixture_index
            or not hasattr(local_model, "Fixture")
            or str(local_model.Fixture).strip().upper() != fixture
            or not hasattr(local_model, "WorldCenter")
            or not close(local_model.WorldCenter.x, expected_center[0])
            or not close(local_model.WorldCenter.y, expected_center[1])
            or not close(local_model.WorldCenter.z, 0.0)
            or not hasattr(local_model, "WorldToLocalTranslation")
            or not close(local_model.WorldToLocalTranslation.x, -expected_center[0])
            or not close(local_model.WorldToLocalTranslation.y, -expected_center[1])
            or not close(local_model.WorldToLocalTranslation.z, 0.0)
        ):
            return False
        expected_world_part = Part.makeBox(
            60.0,
            20.0,
            18.0,
            App.Vector(expected_center[0] - 30.0, expected_center[1] - 10.0, 0.0),
        )
        if (
            not shapes_equal(local_model.SourcePart.Shape, expected_world_part, 1e-4)
            or not hasattr(local_model.SourcePart, "Fixture")
            or str(local_model.SourcePart.Fixture).strip().upper() != fixture
            or not hasattr(local_model.SourcePart, "SourceSolidIndex")
            or int(local_model.SourcePart.SourceSolidIndex) != fixture_index
        ):
            return False
        if not shapes_equal(job.Stock.Shape, expected_stock, 1e-4):
            return False
        operations = list(job.Operations.Group)
        if len(operations) != 2 or proxy_module(operations[0]) != "Path.Op.MillFace" or proxy_module(operations[1]) != "Path.Op.Profile":
            return False
        if not {obj.Name for obj in operations}.issubset({obj.Name for obj in all_ops}):
            return False
        if len(job.Tools.Group) != 1:
            return False
        controller = job.Tools.Group[0]
        if proxy_module(controller) != "Path.Tool.Controller" or proxy_module(controller.Tool) != "Path.Tool.Bit":
            return False
        if (
            int(controller.ToolNumber) != 1
            or not close(controller.Tool.Diameter.Value, TOOL_DIAMETER)
            or str(controller.Tool.ShapeName).strip().lower() != "endmill"
            or Path(str(controller.Tool.BitShape)).name.lower() != "endmill.fcstd"
            or not close(controller.SpindleSpeed, 7000)
            or str(controller.SpindleDir) != "Forward"
            or not close(controller.HorizFeed.getValueAs("mm/min").Value, 500)
            or not close(controller.VertFeed.getValueAs("mm/min").Value, 500)
        ):
            return False
        face, profile = operations
        if face.ToolController != controller or profile.ToolController != controller:
            return False
        allowed_models = {clone, linked_models[0]}
        if not selected_top_geometry(face, Part, allowed_models, allow_empty=True) or not selected_top_geometry(
            profile, Part, allowed_models, allow_edges=True
        ):
            return False
        base_models.append(profile.Base[0][0])
        if (
            not close(face.StartDepth.Value, STOCK_TOP)
            or not close(face.FinalDepth.Value, PART_TOP)
            or not close(face.StepDown.Value, 1.0)
            or not close(profile.StartDepth.Value, PART_TOP)
            or not close(profile.FinalDepth.Value, PART_BOTTOM)
            or not close(profile.StepDown.Value, 3.0)
            or face.ClearanceHeight.Value <= face.SafeHeight.Value
            or profile.ClearanceHeight.Value <= profile.SafeHeight.Value
            or not close(face.SafeHeight.Value, 21.0)
            or not close(face.ClearanceHeight.Value, 23.0)
            or not close(profile.SafeHeight.Value, 21.0)
            or not close(profile.ClearanceHeight.Value, 23.0)
            or str(profile.Side) != "Outside"
            or str(profile.Direction) != "CW"
            or not bool(profile.UseComp)
            or not close(profile.OffsetExtra.Value, 0.0)
        ):
            return False
        if not validate_face_path(face) or not validate_profile_path(profile):
            return False
        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1:
            return False
        combined.extend(sections[0][1])
    if len({obj.Name for obj in base_models}) != 4:
        return False

    try:
        submitted_text = NC_PATH.read_text(encoding="utf-8")
    except Exception:
        return False
    if not validate_nc_safety(submitted_text):
        return False
    with tempfile.TemporaryDirectory(prefix="engiworld-task09-eval-") as temporary:
        repost_path = Path(temporary) / "task-09.nc"
        try:
            PostProcessor.load("linuxcnc").export(combined, str(repost_path), post_args or "")
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
    marker = "TASK09_RESULT_" + secrets.token_hex(16)
    evaluator = str(Path(__file__).resolve())
    command = (
        "import builtins; builtins.pythonopen=open; "
        f"exec(compile(open({evaluator!r}, encoding='utf-8').read(), {evaluator!r}, 'exec'))"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="engiworld-task09-home-") as isolated_home:
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
                timeout=300,
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
