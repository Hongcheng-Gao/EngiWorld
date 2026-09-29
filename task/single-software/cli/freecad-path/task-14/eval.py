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
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


TARGET = Path("/home/user/Desktop")
INIT = TARGET / "broken_boundary_pocket.FCStd"
FCSTD = TARGET / "task-14.FCStd"
NC = TARGET / "task-14.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_INIT_SHA256 = "6303039d4323aa1ec1164e9a177cf3f3d47a8a1d0907290f5c851b6028b27f3e"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 90, 94}
ALLOWED_M = {2, 3, 4, 5, 6, 7, 8, 9}
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J"}
G_MODAL_GROUPS = (
    {0, 1, 2, 3, 80},
    {17},
    {21},
    {40},
    {43, 49},
    {54},
    {90},
    {94},
)
REQUIRED_PROXIES = Counter(
    {
        ("Path.Main.Job", "ObjectJob"): 1,
        ("Path.Base.SetupSheet", "SetupSheet"): 1,
        ("Path.Main.Stock", "StockFromBase"): 1,
        ("Path.Tool.Controller", "ToolController"): 1,
        ("Path.Tool.Bit", "ToolBit"): 1,
        ("Path.Op.PocketShape", "ObjectPocket"): 1,
    }
)
OPTIONAL_PROXIES = {("draftobjects.clone", "Clone"): 1}


def fail(message: str) -> bool:
    print("task-14 evaluator: " + message, file=sys.stderr)
    return False


def close(a: float, b: float, tolerance: float = 1e-6) -> bool:
    try:
        left = float(a)
        right = float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def regular_file(path: Path, minimum: int, maximum: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(info.st_mode)
        and not path.is_symlink()
        and minimum <= info.st_size <= maximum
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def proxy_manifest(document: bytes) -> Counter:
    root = ET.fromstring(document)
    result = Counter()
    for element in root.iter("Python"):
        module = element.attrib.get("module")
        class_name = element.attrib.get("class")
        value = element.attrib.get("value")
        if element.attrib.get("encoded") != "yes" or not isinstance(value, str) or len(value) > 100_000:
            raise ValueError("invalid Python proxy serialization")
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
        payload = json.loads(decoded)
        if (module, class_name) == ("draftobjects.clone", "Clone"):
            if not isinstance(payload, str):
                raise ValueError("invalid clone proxy payload")
        elif payload is not None and not isinstance(payload, dict):
            raise ValueError("invalid proxy payload")
        result[(module, class_name)] += 1
    return result


def validate_fcstd_archive(path: Path, expected_proxies: Counter | None) -> bool:
    minimum = 2_000 if expected_proxies is None else 10_000
    if not regular_file(path, minimum, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "Document.xml" not in names or len(names) != len(set(names)) or len(names) > 200:
                return False
            total = 0
            for entry in archive.infolist():
                pure = Path(entry.filename)
                if pure.is_absolute() or ".." in pure.parts:
                    return False
                if entry.file_size < 0 or entry.file_size > 20_000_000:
                    return False
                total += entry.file_size
                if total > 50_000_000:
                    return False
                if pure.suffix.lower() in {".py", ".pyc", ".so", ".dll", ".dylib", ".sh"}:
                    return False
            document = archive.read("Document.xml")
            if not document or len(document) > 5_000_000:
                return False
            proxies = proxy_manifest(document)
            if expected_proxies is None:
                return not proxies
            if any(proxies[key] != count for key, count in expected_proxies.items()):
                return False
            if any(proxies[key] > limit for key, limit in OPTIONAL_PROXIES.items()):
                return False
            if set(proxies) - set(expected_proxies) - set(OPTIONAL_PROXIES):
                return False
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, ET.ParseError):
        return False
    return True


def strip_comments(text: str) -> str | None:
    output: list[str] = []
    in_comment = False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        code: list[str] = []
        index = 0
        while index < len(line):
            char = line[index]
            if in_comment:
                if char == "(":
                    return None
                if char == ")":
                    in_comment = False
                index += 1
                continue
            if char == "(":
                in_comment = True
            elif char == ")":
                return None
            elif char == ";":
                break
            else:
                code.append(char)
            index += 1
        output.append("".join(code))
    if in_comment:
        return None
    return "\n".join(output)


def parse_nc(text: str) -> list[list[tuple[str, float]]] | None:
    executable = strip_comments(text)
    if executable is None:
        return None
    raw_lines = executable.splitlines()
    nonempty = [index for index, line in enumerate(raw_lines) if line.strip()]
    percent = [index for index, line in enumerate(raw_lines) if line.strip() == "%"]
    if percent and (len(percent) != 2 or not nonempty or percent != [nonempty[0], nonempty[-1]]):
        return None
    blocks: list[list[tuple[str, float]]] = []
    for raw in raw_lines:
        line = raw.strip().upper()
        if not line or line == "%":
            continue
        tokens: list[tuple[str, float]] = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            try:
                number = float(match.group(2))
            except ValueError:
                return None
            if not math.isfinite(number):
                return None
            tokens.append((match.group(1), number))
            cursor = match.end()
        if line[cursor:].strip() or not tokens or any(letter not in ALLOWED_ADDRESSES for letter, _ in tokens):
            return None
        g_codes = [integral(value) for letter, value in tokens if letter == "G"]
        if sum(letter == "N" for letter, _ in tokens) > 1:
            return None
        if any(code is None or code not in ALLOWED_G for code in g_codes):
            return None
        if any(sum(code in group for code in g_codes) > 1 for group in G_MODAL_GROUPS):
            return None
        blocks.append(tokens)
    return blocks or None


def integral(value: float) -> int | None:
    rounded = round(value)
    return int(rounded) if close(value, rounded, 1e-9) else None


def nc_semantics(path: Path) -> tuple | None:
    try:
        blocks = parse_nc(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    if blocks is None:
        return None
    motion = None
    position = {"X": None, "Y": None, "Z": None}
    program = []
    for block in blocks:
        control = []
        coordinates = {}
        for letter, value in block:
            if letter == "N":
                continue
            if letter == "G":
                code = integral(value)
                if code in {0, 1, 2, 3}:
                    motion = code
                else:
                    control.append((letter, code if code is not None else value))
            elif letter in {"X", "Y", "Z", "I", "J"}:
                coordinates[letter] = value
            elif letter in {"M", "T", "H"}:
                code = integral(value)
                control.append((letter, code if code is not None else value))
            else:
                control.append((letter, value))
        for axis in ("X", "Y", "Z"):
            if axis in coordinates:
                position[axis] = coordinates[axis]
        entry = [tuple(sorted(control))]
        if coordinates and motion is not None:
            entry.append(
                (
                    "motion",
                    motion,
                    *(None if position[axis] is None else round(position[axis], 9) for axis in ("X", "Y", "Z")),
                    *(None if axis not in coordinates else round(coordinates[axis], 9) for axis in ("I", "J")),
                )
            )
        elif motion is not None and any(letter == "G" and integral(value) in {0, 1, 2, 3} for letter, value in block):
            entry.append(("motion_mode", motion))
        program.append(tuple(entry))
    return tuple(program)


def nc_native_signature(path: Path) -> tuple | None:
    try:
        blocks = parse_nc(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    if blocks is None:
        return None

    motion = None
    position = {"X": None, "Y": None, "Z": None}
    controls = []
    rapids = []
    transitions = Counter()
    arcs = Counter()
    directed_lines = {}

    def quantized(value):
        return None if value is None else round(float(value), 3)

    for block in blocks:
        block_controls = []
        coordinates = {}
        for letter, value in block:
            if letter == "N":
                continue
            if letter == "G":
                code = integral(value)
                if code in {0, 1, 2, 3}:
                    motion = code
                else:
                    block_controls.append((letter, code if code is not None else round(value, 6)))
            elif letter in {"X", "Y", "Z", "I", "J"}:
                coordinates[letter] = value
            elif letter in {"M", "T", "H"}:
                code = integral(value)
                block_controls.append((letter, code if code is not None else round(value, 6)))
            # S and F are fixed by validate_nc; repeated feed words must not make
            # equivalent native paths depend on FreeCAD's segment count.
        if block_controls:
            controls.append(tuple(sorted(block_controls)))

        before = dict(position)
        for axis in position:
            if axis in coordinates:
                position[axis] = coordinates[axis]
        if not coordinates or motion is None:
            continue

        before_point = tuple(quantized(before[axis]) for axis in ("X", "Y", "Z"))
        after_point = tuple(quantized(position[axis]) for axis in ("X", "Y", "Z"))
        if motion == 0:
            rapids.append((before_point, after_point))
            continue
        if any(value is None for value in before_point + after_point):
            return None
        if before_point == after_point:
            continue
        if motion in {2, 3}:
            arcs[(motion, before_point, after_point, quantized(coordinates.get("I", 0.0)), quantized(coordinates.get("J", 0.0)))] += 1
            continue
        if motion != 1 or before_point[2] != after_point[2]:
            transitions[(motion, before_point, after_point)] += 1
            continue

        dx = after_point[0] - before_point[0]
        dy = after_point[1] - before_point[1]
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        ux, uy = dx / length, dy / length
        offset = -uy * before_point[0] + ux * before_point[1]
        start = ux * before_point[0] + uy * before_point[1]
        end = ux * after_point[0] + uy * after_point[1]
        key = (before_point[2], round(ux, 4), round(uy, 4), round(offset, 3))
        directed_lines.setdefault(key, []).append((min(start, end), max(start, end)))

    canonical_lines = {}
    for key, intervals in directed_lines.items():
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1] + 0.001:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        canonical_lines[key] = (
            tuple((round(start, 3), round(end, 3)) for start, end in merged),
            round(sum(end - start for start, end in intervals), 3),
        )
    return (
        tuple(controls),
        tuple(rapids),
        transitions,
        arcs,
        canonical_lines,
    )


def validate_nc(path: Path) -> bool:
    if not regular_file(path, 1_000, 2_000_000):
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    blocks = parse_nc(text)
    if blocks is None:
        return False
    state = {
        "units": None,
        "absolute": False,
        "motion": None,
        "tool": None,
        "changed": False,
        "speed": None,
        "feed": None,
        "spindle": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    saw = {"g21": False, "g90": False, "change": False, "spindle": False, "cut": False, "floor": False}
    ended = False
    floor_segments = 0
    for block_index, block in enumerate(blocks):
        words: dict[str, float] = {}
        g_codes: list[int] = []
        m_codes: list[int] = []
        for letter, value in block:
            if letter == "N":
                if integral(value) is None:
                    return False
                continue
            if letter == "G":
                code = integral(value)
                if code is None or code not in ALLOWED_G:
                    return False
                g_codes.append(code)
            elif letter == "M":
                code = integral(value)
                if code is None or code not in ALLOWED_M:
                    return False
                m_codes.append(code)
            else:
                if letter in words:
                    return False
                words[letter] = value
        if ended:
            return False
        if 21 in g_codes:
            state["units"] = "mm"
            saw["g21"] = True
        if 90 in g_codes:
            state["absolute"] = True
            saw["g90"] = True
        for code in g_codes:
            if code in {0, 1, 2, 3}:
                state["motion"] = code
        has_motion_coordinates = any(axis in words for axis in ("X", "Y", "Z", "I", "J"))
        if state["motion"] in {0, 1} and any(axis in words for axis in ("I", "J")):
            return False
        if (
            has_motion_coordinates
            and state["motion"] in {2, 3}
            and not any(axis in words for axis in ("I", "J"))
        ):
            return False
        if "T" in words:
            tool = integral(words["T"])
            if tool != 1:
                return False
            state["tool"] = tool
        if "H" in words and integral(words["H"]) != 1:
            return False
        if "S" in words:
            if not close(words["S"], 7000.0, 1e-5):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if not close(words["F"], 500.0, 1e-4):
                return False
            state["feed"] = words["F"]
        if 5 in m_codes:
            state["spindle"] = False
        if 6 in m_codes:
            if state["spindle"] or state["tool"] != 1:
                return False
            state["changed"] = True
            saw["change"] = True
        if 3 in m_codes and 4 in m_codes:
            return False
        if 3 in m_codes or 4 in m_codes:
            if not state["changed"] or state["speed"] is None:
                return False
            state["spindle"] = True
            saw["spindle"] = True

        before = {axis: state[axis] for axis in ("X", "Y", "Z")}
        moved = any(axis in words for axis in ("X", "Y", "Z"))
        for axis in ("X", "Y", "Z"):
            if axis in words:
                state[axis] = words[axis]
        if moved and state["motion"] in {0, 1, 2, 3}:
            if state["units"] != "mm" or not state["absolute"]:
                return False
            if any(state[axis] is not None and not math.isfinite(float(state[axis])) for axis in ("X", "Y", "Z")):
                return False
            if state["motion"] == 0:
                has_xy = any(axis in words for axis in ("X", "Y"))
                if has_xy and (before["Z"] is None or before["Z"] <= 18.0 + 1e-4):
                    return False
                if state["Z"] is not None and state["Z"] <= 18.0 + 1e-4:
                    return False
            else:
                if not state["changed"] or not state["spindle"] or state["feed"] is None:
                    return False
                if not all(state[axis] is not None for axis in ("X", "Y", "Z")):
                    return False
                if state["Z"] < 5.0 - 1e-4:
                    return False
                if state["Z"] <= 18.0 + 1e-4:
                    if not (-46.01 <= state["X"] <= 46.01 and -26.01 <= state["Y"] <= 26.01):
                        return False
                    saw["cut"] = True
                if close(state["Z"], 5.0, 1e-4):
                    saw["floor"] = True
                    if before["Z"] is not None and close(before["Z"], 5.0, 1e-4):
                        floor_segments += 1
        if 2 in m_codes:
            if block_index != len(blocks) - 1 or state["spindle"]:
                return False
            ended = True
        if 30 in m_codes:
            return False
    return ended and floor_segments >= 4 and all(saw.values())


CHILD_SOURCE = r'''
from __future__ import annotations

import math
import os
import pathlib
import re
import shlex
import sys
import tempfile
from collections import Counter

import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor


EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_INIT_SHA256 = "6303039d4323aa1ec1164e9a177cf3f3d47a8a1d0907290f5c851b6028b27f3e"
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")


def close(a, b, tolerance=1e-6):
    try:
        left = float(a)
        right = float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def proxy_module(obj):
    proxy = getattr(obj, "Proxy", None)
    return proxy.__class__.__module__ if proxy is not None else ""


def object_clean(obj):
    return not {"Touched", "Invalid", "Error"}.intersection({str(value) for value in obj.State})


def shape_bounds(shape):
    box = shape.BoundBox
    return (box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)


def exact_box(shape):
    return (
        shape.ShapeType == "Solid"
        and len(shape.Solids) == 1
        and shape.isValid()
        and close(shape.Volume, 172800.0, 1e-4)
        and all(close(a, b, 1e-6) for a, b in zip(shape_bounds(shape), (-60, 60, -40, 40, 0, 18)))
    )


def line_points(sketch):
    points = []
    for geometry in sketch.Geometry:
        if not isinstance(geometry, Part.LineSegment):
            return None
        points.append(
            (
                (float(geometry.StartPoint.x), float(geometry.StartPoint.y), float(geometry.StartPoint.z)),
                (float(geometry.EndPoint.x), float(geometry.EndPoint.y), float(geometry.EndPoint.z)),
            )
        )
    return points


def segment_equal(first, second, tolerance=1e-7):
    def point_equal(a, b):
        return all(close(x, y, tolerance) for x, y in zip(a, b))
    return (point_equal(first[0], second[0]) and point_equal(first[1], second[1])) or (
        point_equal(first[0], second[1]) and point_equal(first[1], second[0])
    )


def validate_broken(sketch):
    if sketch.TypeId != "Sketcher::SketchObject" or not close(sketch.Placement.Base.z, 18.0):
        return False
    points = line_points(sketch)
    if points is None or len(points) != 5 or sketch.Shape.isClosed():
        return False
    duplicates = sum(
        segment_equal(points[left], points[right])
        for left in range(len(points))
        for right in range(left + 1, len(points))
    )
    if duplicates != 1:
        return False
    expected = [
        ((-50, -30, 0), (50, -30, 0)),
        ((50, -30, 0), (50, 30, 0)),
        ((50, 30, 0), (-50, 30, 0)),
        ((-50, 30, 0), (-50, -29.95, 0)),
        ((-50, -30, 0), (50, -30, 0)),
    ]
    if any(not segment_equal(actual, target) for actual, target in zip(points, expected)):
        return False
    gap = math.dist(points[3][1], points[0][0])
    return close(gap, 0.05, 1e-7)


def validate_repair(sketch):
    if sketch.TypeId != "Sketcher::SketchObject" or not close(sketch.Placement.Base.z, 18.0):
        return False
    points = line_points(sketch)
    if points is None or len(points) != 4 or not sketch.Shape.isClosed():
        return False
    if any(segment_equal(points[left], points[right]) for left in range(4) for right in range(left + 1, 4)):
        return False
    expected_vertices = {(-50.0, -30.0), (50.0, -30.0), (50.0, 30.0), (-50.0, 30.0)}
    actual_vertices = {
        (round(point[0], 7), round(point[1], 7))
        for segment in points
        for point in segment
    }
    if actual_vertices != expected_vertices:
        return False
    degrees = {vertex: 0 for vertex in actual_vertices}
    for start, end in points:
        degrees[(round(start[0], 7), round(start[1], 7))] += 1
        degrees[(round(end[0], 7), round(end[1], 7))] += 1
    return set(degrees.values()) == {2}


def valid_post_args(value):
    try:
        arguments = shlex.split(str(value))
    except ValueError:
        return False
    flags = {
        "--no-header", "--no-comments", "--line-numbers", "--no-show-editor",
        "--modal", "--axis-modal", "--no-tlo",
    }
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in flags:
            index += 1
            continue
        if argument == "--precision":
            index += 1
            if index >= len(arguments) or not re.fullmatch(r"[3-9]", arguments[index]):
                return False
            index += 1
            continue
        if re.fullmatch(r"--precision=[3-9]", argument):
            index += 1
            continue
        return False
    return True


def distance_to_segment(px, py, start, end):
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
        for axis in current:
            if axis in command.Parameters:
                current[axis] = float(command.Parameters[axis])
        name = str(command.Name).upper().replace(" ", "")
        if name in {"G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"}:
            has_xy = "X" in command.Parameters or "Y" in command.Parameters
            if has_xy and before["Z"] is None:
                return None
            if name in {"G0", "G00"} and has_xy and before["Z"] <= 18.0 + 1e-5:
                return None
        if name in {"G0", "G00", "G1", "G01"} and all(
            before[axis] is not None and current[axis] is not None for axis in current
        ):
            motions.append(("G0" if name in {"G0", "G00"} else "G1", before, dict(current)))
        elif name in {"G2", "G02", "G3", "G03"} and all(
            before[axis] is not None and current[axis] is not None for axis in current
        ):
            if "I" not in command.Parameters and "J" not in command.Parameters:
                return None
            cx = before["X"] + float(command.Parameters.get("I", 0.0))
            cy = before["Y"] + float(command.Parameters.get("J", 0.0))
            radius = math.hypot(before["X"] - cx, before["Y"] - cy)
            end_radius = math.hypot(current["X"] - cx, current["Y"] - cy)
            if radius <= 1e-8 or not close(radius, end_radius, 1e-4):
                return None
            start_angle = math.atan2(before["Y"] - cy, before["X"] - cx)
            end_angle = math.atan2(current["Y"] - cy, current["X"] - cx)
            clockwise = name in {"G2", "G02"}
            sweep = (start_angle - end_angle) % (2 * math.pi) if clockwise else (end_angle - start_angle) % (2 * math.pi)
            if sweep <= 1e-10:
                sweep = 2 * math.pi
            steps = max(2, int(math.ceil(radius * sweep / 0.25)))
            previous = dict(before)
            direction = -1.0 if clockwise else 1.0
            for step in range(1, steps + 1):
                fraction = step / steps
                angle = start_angle + direction * sweep * fraction
                point = {
                    "X": cx + radius * math.cos(angle),
                    "Y": cy + radius * math.sin(angle),
                    "Z": before["Z"] + (current["Z"] - before["Z"]) * fraction,
                }
                if step == steps:
                    point = dict(current)
                motions.append(("G1", previous, point))
                previous = point
    return motions


def in_rounded_pocket(x, y, radius):
    cx = min(max(x, -50 + radius), 50 - radius)
    cy = min(max(y, -30 + radius), 30 - radius)
    return math.hypot(x - cx, y - cy) <= radius + 1e-8


def validate_path(pocket, diameter):
    motions = path_motions(list(pocket.Path.Commands))
    if motions is None or len(motions) < 12:
        return False
    radius = diameter / 2.0
    floor_segments = []
    reached_floor = False
    for mode, before, after in motions:
        if min(before["Z"], after["Z"]) < 5.0 - 1e-5:
            return False
        if mode == "G0":
            if after["Z"] <= 18.0 + 1e-5:
                return False
            continue
        for point in (before, after):
            if point["Z"] <= 18.0 + 1e-5:
                if not (-50 + radius - 0.01 <= point["X"] <= 50 - radius + 0.01):
                    return False
                if not (-30 + radius - 0.01 <= point["Y"] <= 30 - radius + 0.01):
                    return False
        if close(after["Z"], 5.0, 1e-5):
            reached_floor = True
        if close(before["Z"], 5.0, 1e-5) and close(after["Z"], 5.0, 1e-5):
            floor_segments.append(((before["X"], before["Y"]), (after["X"], after["Y"])))
    if not reached_floor or len(floor_segments) < 4:
        return False
    samples = 0
    x = -50.0
    while x <= 50.0 + 1e-8:
        y = -30.0
        while y <= 30.0 + 1e-8:
            if in_rounded_pocket(x, y, radius):
                samples += 1
                distance = min(distance_to_segment(x, y, start, end) for start, end in floor_segments)
                if distance > radius + 0.02:
                    return False
            y += 1.0
        x += 1.0
    return samples > 5_000


def ordered_cut_signature(pocket):
    motions = path_motions(list(pocket.Path.Commands))
    if motions is None:
        return None
    signature = []
    for mode, before, after in motions:
        dx = after["X"] - before["X"]
        dy = after["Y"] - before["Y"]
        length = math.hypot(dx, dy)
        if mode != "G1" or not close(before["Z"], after["Z"], 1e-6) or length <= 1e-7:
            continue
        depth = round(after["Z"], 4)
        segment = [
            depth,
            round(before["X"], 4),
            round(before["Y"], 4),
            round(after["X"], 4),
            round(after["Y"], 4),
        ]
        if signature:
            previous = signature[-1]
            previous_dx = previous[3] - previous[1]
            previous_dy = previous[4] - previous[2]
            joined = close(previous[3], segment[1], 1e-5) and close(previous[4], segment[2], 1e-5)
            collinear = abs(previous_dx * dy - previous_dy * dx) <= 1e-5 * max(
                1.0, math.hypot(previous_dx, previous_dy) * length
            )
            same_direction = previous_dx * dx + previous_dy * dy > 0
            if previous[0] == depth and joined and collinear and same_direction:
                previous[3], previous[4] = segment[3], segment[4]
                continue
        signature.append(segment)
    return tuple(tuple(segment) for segment in signature)


def layer_geometry_signature(pocket):
    motions = path_motions(list(pocket.Path.Commands))
    if motions is None:
        return None
    lines = {}
    for mode, before, after in motions:
        dx = after["X"] - before["X"]
        dy = after["Y"] - before["Y"]
        length = math.hypot(dx, dy)
        if mode != "G1" or not close(before["Z"], after["Z"], 1e-6) or length <= 1e-7:
            continue
        ux, uy = dx / length, dy / length
        if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0):
            ux, uy = -ux, -uy
        offset = -uy * before["X"] + ux * before["Y"]
        first = ux * before["X"] + uy * before["Y"]
        second = ux * after["X"] + uy * after["Y"]
        key = (
            round(after["Z"], 6),
            round(ux, 5),
            round(uy, 5),
            round(offset, 5),
        )
        lines.setdefault(key, []).append(tuple(sorted((first, second))))
    layers = {}
    for (depth, ux, uy, offset), intervals in lines.items():
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1] + 1e-5:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        canonical = layers.setdefault(depth, set())
        canonical.update(
            (ux, uy, offset, round(start, 5), round(end, 5))
            for start, end in merged
        )
    return {depth: frozenset(segments) for depth, segments in layers.items()}


def directed_layer_geometry_signature(pocket):
    motions = path_motions(list(pocket.Path.Commands))
    if motions is None:
        return None
    lines = {}
    for mode, before, after in motions:
        if mode != "G1" or not close(before["Z"], after["Z"], 1e-6):
            continue
        ax, ay = round(before["X"], 3), round(before["Y"], 3)
        bx, by = round(after["X"], 3), round(after["Y"], 3)
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length <= 1e-9:
            continue
        ux, uy = dx / length, dy / length
        offset = -uy * ax + ux * ay
        start = ux * ax + uy * ay
        end = ux * bx + uy * by
        key = (round(after["Z"], 3), round(ux, 4), round(uy, 4), round(offset, 3))
        lines.setdefault(key, []).append((min(start, end), max(start, end)))
    result = {}
    for key, intervals in lines.items():
        merged = []
        for start, end in sorted(intervals):
            if merged and start <= merged[-1][1] + 0.001:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        result[key] = (
            tuple((round(start, 3), round(end, 3)) for start, end in merged),
            round(sum(end - start for start, end in intervals), 3),
        )
    return result


def validate_depth_layers(pocket):
    motions = path_motions(list(pocket.Path.Commands))
    if motions is None:
        return False
    start = float(pocket.StartDepth.Value)
    final = float(pocket.FinalDepth.Value)
    stepdown = float(pocket.StepDown.Value)
    finish = float(pocket.FinishDepth.Value)
    total_depth = start - final
    if (
        not all(math.isfinite(value) for value in (start, final, stepdown, finish))
        or not final < start
        or stepdown <= 0
        or finish < 0
        or finish > stepdown + 1e-7
    ):
        return False
    actual = sorted(
        {
            round(after["Z"], 6)
            for mode, before, after in motions
            if mode == "G1"
            and close(before["Z"], after["Z"], 1e-6)
            and math.hypot(after["X"] - before["X"], after["Y"] - before["Y"]) > 1e-7
            and after["Z"] < start - 1e-7
        },
        reverse=True,
    )
    if not actual or not close(actual[-1], final, 1e-6):
        return False
    depths = [start] + actual
    if any(
        upper <= lower + 1e-7 or upper - lower > stepdown + 1e-6
        for upper, lower in zip(depths, depths[1:])
    ):
        return False
    if finish >= total_depth - 1e-7:
        return len(actual) == 1 and close(actual[0], final, 1e-6)
    if finish > 1e-7:
        return len(actual) >= 2 and close(actual[-2], final + finish, 1e-6)
    return True


def validate_rapid_heights(pocket):
    rapid_z = rapid_height_signature(pocket)
    if not rapid_z:
        return False
    safe = round(float(pocket.SafeHeight.Value), 6)
    clearance = round(float(pocket.ClearanceHeight.Value), 6)
    return (
        rapid_z[0] == max(safe, clearance)
        and rapid_z[-1] == clearance
        and safe in rapid_z
        and clearance in rapid_z
    )


def rapid_height_signature(pocket):
    return tuple(
        round(float(command.Parameters["Z"]), 6)
        for command in pocket.Path.Commands
        if str(command.Name).upper().replace(" ", "") in {"G0", "G00"}
        and "Z" in command.Parameters
    )


def rapid_motion_signature(pocket):
    current = {"X": None, "Y": None, "Z": None}
    signature = []
    for command in pocket.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        before = dict(current)
        for axis in current:
            if axis in command.Parameters:
                current[axis] = float(command.Parameters[axis])
        if name not in {"G0", "G00"}:
            continue
        has_xy = "X" in command.Parameters or "Y" in command.Parameters
        if has_xy and (before["Z"] is None or before["Z"] <= 18.0 + 1e-5):
            return None
        signature.append(
            tuple(None if current[axis] is None else round(current[axis], 5) for axis in ("X", "Y", "Z"))
        )
    return tuple(signature)


def validate_document(init_path, fcstd_path, nc_path, repost_path, recomputed_path):
    import hashlib

    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        return False
    if hashlib.sha256(init_path.read_bytes()).hexdigest() != EXPECTED_INIT_SHA256:
        return False

    init_doc = App.openDocument(str(init_path))
    if init_doc is None or len(init_doc.Objects) != 2:
        return False
    init_stock = init_doc.getObject("StockModel")
    init_broken = init_doc.getObject("BrokenPocketBoundary")
    if init_stock is None or init_broken is None or not exact_box(init_stock.Shape) or not validate_broken(init_broken):
        return False

    doc = App.openDocument(str(fcstd_path))
    if doc is None:
        return False
    try:
        stocks = [obj for obj in doc.Objects if obj.Name == "StockModel"]
        broken_objects = [obj for obj in doc.Objects if obj.Name == "BrokenPocketBoundary"]
        repairs = [
            obj
            for obj in doc.Objects
            if str(obj.Label).strip() == "BoundaryRepair"
        ]
        jobs = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Main.Job"]
        pockets = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Op.PocketShape"]
        controllers = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Tool.Controller"]
        tools = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Tool.Bit"]
        if not all(len(items) == 1 for items in (stocks, broken_objects, repairs, jobs, pockets, controllers, tools)):
            return False
        stock, broken, repair = stocks[0], broken_objects[0], repairs[0]
        job, pocket, controller, tool = jobs[0], pockets[0], controllers[0], tools[0]
        if not exact_box(stock.Shape) or not validate_broken(broken) or not validate_repair(repair):
            return False
        if len(pocket.Base) != 1 or tuple(str(value) for value in pocket.Base[0][1]) != ("Face1",):
            return False
        repair_face = pocket.Base[0][0]
        if (
            repair_face.TypeId not in {"Part::Feature", "PartDesign::Feature"}
            or not repair_face.Shape.isValid()
            or len(repair_face.Shape.Faces) != 1
            or not close(repair_face.Shape.Area, 6000.0, 1e-4)
            or not all(close(a, b, 1e-6) for a, b in zip(shape_bounds(repair_face.Shape), (-50, 50, -30, 30, 18, 18)))
        ):
            return False
        if (
            len(job.Operations.Group) != 1
            or job.Operations.Group[0] != pocket
            or len(job.Tools.Group) != 1
            or job.Tools.Group[0] != controller
            or controller.Tool != tool
            or pocket.ToolController != controller
        ):
            return False
        if (
            str(job.PostProcessor).strip().lower() != "linuxcnc"
            or bool(job.SplitOutput)
            or os.path.normpath(str(job.PostProcessorOutputFile)) != "/home/user/Desktop/task-14.nc"
            or not valid_post_args(job.PostProcessorArgs)
            or [str(value).strip().upper() for value in job.Fixtures] != ["G54"]
            or len(job.Model.Group) != 1
            or not exact_box(job.Model.Group[0].Shape)
            or not exact_box(job.Stock.Shape)
        ):
            return False
        if (
            int(controller.ToolNumber) != 1
            or str(getattr(tool, "ShapeName", "")).lower() != "endmill"
            or not close(tool.Diameter.Value, 8.0)
            or not close(controller.SpindleSpeed, 7000.0)
            or str(controller.SpindleDir) != "Forward"
            or not close(controller.HorizFeed.getValueAs("mm/min").Value, 500.0)
            or not close(controller.VertFeed.getValueAs("mm/min").Value, 500.0)
        ):
            return False
        if (
            not close(pocket.StartDepth.Value, 18.0)
            or not close(pocket.FinalDepth.Value, 5.0)
            or not math.isfinite(float(pocket.StepDown.Value))
            or pocket.StepDown.Value <= 0
            or not (0 < float(pocket.StepOver) <= 100)
            or pocket.SafeHeight.Value <= 18.0
            or pocket.ClearanceHeight.Value <= 18.0
            or not close(pocket.ExtraOffset.Value, 0.0)
            or str(pocket.OffsetPattern) not in {"Offset", "ZigZag", "ZigZagOffset", "Line", "Grid"}
            or str(pocket.StartAt) not in {"Center", "Edge"}
            or str(pocket.CutMode) not in {"Climb", "Conventional"}
        ):
            return False

        if (
            not validate_path(pocket, 8.0)
            or not validate_depth_layers(pocket)
            or not validate_rapid_heights(pocket)
        ):
            return False
        saved_layers = layer_geometry_signature(pocket)
        saved_directed_layers = directed_layer_geometry_signature(pocket)
        saved_rapid_heights = rapid_height_signature(pocket)
        saved_rapid_motions = rapid_motion_signature(pocket)
        if (
            saved_layers is None
            or not saved_directed_layers
            or not saved_rapid_heights
            or not saved_rapid_motions
        ):
            return False
        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1:
            return False
        PostProcessor.load("linuxcnc").export(sections[0][1], str(repost_path), str(job.PostProcessorArgs))
        for obj in doc.Objects:
            obj.touch()
        doc.recompute()
        doc.recompute()
        if not all(object_clean(obj) for obj in doc.Objects):
            return False
        if (
            not validate_broken(broken)
            or not validate_repair(repair)
            or not validate_path(pocket, 8.0)
            or not validate_depth_layers(pocket)
            or not validate_rapid_heights(pocket)
            or saved_layers != layer_geometry_signature(pocket)
            or saved_directed_layers != directed_layer_geometry_signature(pocket)
            or saved_rapid_heights != rapid_height_signature(pocket)
            or saved_rapid_motions != rapid_motion_signature(pocket)
        ):
            return False

        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1:
            return False
        PostProcessor.load("linuxcnc").export(
            sections[0][1], str(recomputed_path), str(job.PostProcessorArgs)
        )
        return True
    finally:
        App.closeDocument(doc.Name)
        App.closeDocument(init_doc.Name)


marker, init_arg, fcstd_arg, nc_arg, repost_arg, recomputed_arg = sys.argv[1:7]
try:
    result = validate_document(
        pathlib.Path(init_arg),
        pathlib.Path(fcstd_arg),
        pathlib.Path(nc_arg),
        pathlib.Path(repost_arg),
        pathlib.Path(recomputed_arg),
    )
except Exception as exc:
    print("task-14 FreeCAD validation: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
    result = False
print(marker + "=" + ("True" if result else "False"))
'''


def run_freecad_validation() -> bool:
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if (
        not stat.S_ISREG(info.st_mode)
        or not os.access(executable, os.X_OK)
        or info.st_uid != 0
        or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    ):
        return False
    marker = "TASK14_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-task14-") as raw_temp:
        temporary = Path(raw_temp)
        script = temporary / "validate.py"
        repost = temporary / "repost.nc"
        recomputed = temporary / "recomputed.nc"
        script.write_text(CHILD_SOURCE, encoding="utf-8")
        script.chmod(0o600)
        arguments = [
            str(script), marker, str(INIT), str(FCSTD), str(NC), str(repost), str(recomputed)
        ]
        command = [
            str(executable),
            "-c",
            (
                "import builtins,sys; sys.argv=%r; builtins.pythonopen=open; "
                "exec(compile(open(%r, encoding='utf-8').read(), %r, 'exec'))"
                % (arguments, str(script), str(script))
            ),
        ]
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(temporary),
            "TMPDIR": str(temporary),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONNOUSERSITE": "1",
            "QT_QPA_PLATFORM": "offscreen",
            "XDG_CACHE_HOME": str(temporary / ".cache"),
            "XDG_CONFIG_HOME": str(temporary / ".config"),
        }
        try:
            completed = subprocess.run(
                command,
                cwd=temporary,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        if len(completed.stdout) > 2_000_000 or len(completed.stderr) > 2_000_000:
            return False
        expected = marker + "=True"
        marker_lines = [line for line in completed.stdout.splitlines() if line.startswith(marker + "=")]
        if completed.returncode != 0 or marker_lines != [expected]:
            if completed.stderr:
                print(completed.stderr[-4000:], file=sys.stderr)
            return False
        submitted_semantics = nc_semantics(NC)
        submitted_native = nc_native_signature(NC)
        if (
            submitted_semantics is None
            or submitted_semantics != nc_semantics(repost)
            or submitted_native is None
            or submitted_native != nc_native_signature(recomputed)
            or not validate_nc(repost)
            or not validate_nc(recomputed)
        ):
            return False
    return True


def main() -> bool:
    if not regular_file(INIT, 2_000, 5_000_000) or sha256(INIT) != EXPECTED_INIT_SHA256:
        return fail("missing, unsafe, or unexpected init FCStd")
    if not validate_fcstd_archive(INIT, None):
        return fail("invalid init FCStd archive")
    if not validate_fcstd_archive(FCSTD, REQUIRED_PROXIES):
        return fail("invalid output FCStd archive or proxy manifest")
    if not validate_nc(NC):
        return fail("invalid NC syntax, modal state, safety, or cutting semantics")
    if not run_freecad_validation():
        return fail("FreeCAD topology, native CAM, coverage, or fresh repost validation failed")
    return True


if __name__ == "__main__":
    try:
        outcome = main()
    except Exception as exc:
        print("task-14 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        outcome = False
    print("True" if outcome else "False")
