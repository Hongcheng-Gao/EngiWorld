from __future__ import annotations

import json
import hashlib
import math
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


TARGET = Path("/home/user/Desktop")
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256 = "08326459e03c3a8bc2d6f9b20ae795f797f4d269552398c8158bb90ee3863be1"
EXPECTED_CONFIG = {
    "task": "task-12",
    "unit": "mm",
    "coordinate_system": "G54",
    "postprocessor": "linuxcnc",
    "post_arguments": ["--line-numbers", "--no-show-editor"],
    "sequence_numbers": True,
    "sequence_start": 110,
    "sequence_increment": 10,
    "program_number": None,
    "program_end": "M2",
    "part": {
        "stock_size": [120, 80, 18],
        "stock_bounds": {"x": [-60, 60], "y": [-40, 40], "z": [0, 18]},
        "pocket": {
            "center": [0, 0],
            "size": [40, 24],
            "top_z": 18,
            "bottom_z": 13,
            "depth": 5,
        },
        "holes": {
            "diameter": 5,
            "top_z": 18,
            "bottom_z": 10,
            "depth": 8,
            "centers": [[-40, -25], [-40, 25], [40, -25], [40, 25]],
        },
    },
    "tools": [
        {
            "tool": 1,
            "name": "flat end mill",
            "diameter": 6,
            "spindle": 7000,
            "feed": 600,
            "operations": ["pocket_shape"],
        },
        {
            "tool": 2,
            "name": "drill",
            "diameter": 5,
            "spindle": 7000,
            "feed": 600,
            "operations": ["drilling"],
        },
    ],
    "operations": ["PocketShape", "Drilling"],
    "operation_settings": {
        "pocket_shape": {
            "step_down": 5,
            "step_over_percent": 50,
            "safe_height": 20,
            "clearance_height": 23,
            "offset_pattern": "ZigZag",
            "start_at": "Center",
            "cut_mode": "Climb",
        },
        "drilling": {
            "cycle": "G81",
            "safe_height": 20,
            "clearance_height": 23,
            "retract_height": 20,
            "peck": False,
            "dwell": False,
            "keep_tool_down": False,
        },
    },
    "outputs": [
        "/home/user/Desktop/task-12.FCStd",
        "/home/user/Desktop/task-12.nc",
    ],
}
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.ASCII)
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")
HOLE_CENTERS = {(-40.0, -25.0), (-40.0, 25.0), (40.0, -25.0), (40.0, 25.0)}
ALLOWED_G_CODES = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 81, 90, 98}
ALLOWED_M_CODES = {2, 3, 5, 6}
REQUIRED_PROXY_RECORDS = Counter(
    {
        ("Path.Main.Job", "ObjectJob", "bnVsbA==", "yes"): 1,
        ("Path.Tool.Controller", "ToolController", "e30=", "yes"): 2,
        ("Path.Tool.Bit", "ToolBit", "bnVsbA==", "yes"): 2,
        ("Path.Op.PocketShape", "ObjectPocket", "bnVsbA==", "yes"): 1,
        ("Path.Op.Drilling", "ObjectDrilling", "bnVsbA==", "yes"): 1,
    }
)
OPTIONAL_PROXY_RECORDS = {
    ("Path.Base.SetupSheet", "SetupSheet", "bnVsbA==", "yes"),
    ("draftobjects.clone", "Clone", "IkNsb25lIg==", "yes"),
}
STOCK_PROXY_RECORDS = {
    ("Path.Main.Stock", "StockFromBase", "bnVsbA==", "yes"),
    ("Path.Main.Stock", "StockCreateBox", "bnVsbA==", "yes"),
    ("Path.Main.Stock", "StockCreateCylinder", "bnVsbA==", "yes"),
}


def fail(message: str) -> bool:
    print("task-12 evaluator: " + message, file=sys.stderr)
    return False


def close(a: float, b: float, tolerance: float = 1e-6) -> bool:
    return math.isfinite(a) and abs(a - b) <= tolerance


def ensure_regular(path: Path, minimum: int, maximum: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(info.st_mode)
        and not path.is_symlink()
        and minimum <= info.st_size <= maximum
    )


def normalized_text_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def strict_equal(actual: object, expected: object) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            strict_equal(actual[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            strict_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_config(path: Path) -> dict | None:
    if not ensure_regular(path, 200, 50_000):
        return None
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return value if strict_equal(value, EXPECTED_CONFIG) else None


def strip_comments(line: str) -> str | None:
    output: list[str] = []
    depth = 0
    for character in line:
        if depth == 0 and character == ";":
            break
        if character == "(":
            depth += 1
            continue
        if character == ")":
            if depth == 0:
                return None
            depth -= 1
            continue
        if depth == 0:
            output.append(character)
    if depth:
        return None
    return "".join(output).strip().upper()


def parse_words(code: str) -> list[tuple[str, float]] | None:
    if not code:
        return []
    matches = list(WORD_RE.finditer(code))
    residue = WORD_RE.sub("", code).replace("%", "")
    if residue.strip():
        return None
    words: list[tuple[str, float]] = []
    for match in matches:
        try:
            number = float(match.group(2))
        except ValueError:
            return None
        if not math.isfinite(number):
            return None
        words.append((match.group(1), number))
    return words


def integral_code(value: float) -> int | None:
    rounded = round(value)
    if abs(value - rounded) > 1e-9:
        return None
    return int(rounded)


def point_segment_distance(
    px: float, py: float, segment: tuple[float, float, float, float]
) -> float:
    x1, y1, x2, y2 = segment
    dx = x2 - x1
    dy = y2 - y1
    denominator = dx * dx + dy * dy
    if denominator <= 1e-18:
        return math.hypot(px - x1, py - y1)
    factor = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / denominator))
    return math.hypot(px - (x1 + factor * dx), py - (y1 + factor * dy))


def validate_pocket_segments(
    segments: list[tuple[float, float, float, float]]
) -> bool:
    if len(segments) < 20:
        return False
    points = [(segment[0], segment[1]) for segment in segments]
    points.extend((segment[2], segment[3]) for segment in segments)
    if any(
        x < -17.01 or x > 17.01 or y < -9.01 or y > 9.01
        for x, y in points
    ):
        return False
    if not (
        min(x for x, _ in points) <= -16.99
        and max(x for x, _ in points) >= 16.99
        and min(y for _, y in points) <= -8.99
        and max(y for _, y in points) >= 8.99
    ):
        return False
    # A 50% stepover with a 6 mm cutter should cover the compensated 34 x 18 mm
    # center region. Grid coverage rejects sparse outlines and comment-only fakes.
    for grid_y in range(-9, 10, 2):
        for grid_x in range(-17, 18, 2):
            if min(
                point_segment_distance(float(grid_x), float(grid_y), segment)
                for segment in segments
            ) > 2.2:
                return False
    return True


def validate_nc_text(text: str) -> bool:
    if not text or "\x00" in text or len(text.encode("utf-8")) > 200_000:
        return False
    numbered: list[int] = []
    parsed_lines: list[list[tuple[str, float]]] = []
    for raw_line in text.splitlines():
        code = strip_comments(raw_line)
        if code is None:
            return False
        words = parse_words(code)
        if words is None:
            return False
        n_values = [number for letter, number in words if letter == "N"]
        if len(n_values) > 1:
            return False
        if n_values:
            if not code.lstrip().startswith("N"):
                return False
            n_code = integral_code(n_values[0])
            if n_code is None or n_code < 0:
                return False
            numbered.append(n_code)
        executable = [(letter, value) for letter, value in words if letter != "N"]
        if executable and not n_values:
            # FreeCAD 0.21.2 stock linuxcnc emits G43 Hn as the sole unnumbered
            # executable continuation after each numbered M6 Tn block.
            if not (
                len(executable) == 2
                and executable[0][0] == "G"
                and integral_code(executable[0][1]) == 43
                and executable[1][0] == "H"
                and integral_code(executable[1][1]) in {1, 2}
            ):
                return False
        parsed_lines.append(executable)

    if len(numbered) < 30 or numbered[0] != 110:
        return False
    if any(next_number - number != 10 for number, next_number in zip(numbered, numbered[1:])):
        return False

    metric = False
    absolute = False
    current_tool: int | None = None
    pending_tool: int | None = None
    spindle = 0.0
    spindle_on = False
    feed: float | None = None
    motion: int | None = None
    position: dict[str, float | None] = {"X": None, "Y": None, "Z": None}
    pocket_segments: list[tuple[float, float, float, float]] = []
    drill_cycles: list[tuple[float, float, float, float]] = []
    g80_after_cycles = False
    m2_count = 0
    seen_t1 = False
    seen_t2 = False

    for words in parsed_lines:
        by_letter: dict[str, list[float]] = {}
        for letter, value in words:
            by_letter.setdefault(letter, []).append(value)
        if any(letter not in {"G", "M", "T", "S", "F", "X", "Y", "Z", "R", "H"} for letter in by_letter):
            return False
        if "O" in by_letter:
            return False
        g_codes: list[int] = []
        for value in by_letter.get("G", []):
            code = integral_code(value)
            if code is None or code not in ALLOWED_G_CODES:
                return False
            g_codes.append(code)
        m_codes: list[int] = []
        for value in by_letter.get("M", []):
            code = integral_code(value)
            if code is None or code not in ALLOWED_M_CODES:
                return False
            m_codes.append(code)
        if 20 in g_codes or 91 in g_codes:
            return False
        if 21 in g_codes:
            metric = True
        if 90 in g_codes:
            absolute = True
        if any(code in {0, 1, 2, 3, 81, 82, 83, 73} for code in g_codes):
            motion = next(code for code in g_codes if code in {0, 1, 2, 3, 81, 82, 83, 73})
        if "T" in by_letter:
            if len(by_letter["T"]) != 1:
                return False
            pending_tool = integral_code(by_letter["T"][0])
            if pending_tool not in {1, 2}:
                return False
        if 6 in m_codes:
            if pending_tool is None:
                return False
            current_tool = pending_tool
            if current_tool == 1:
                seen_t1 = True
            if current_tool == 2:
                seen_t2 = True
        if "S" in by_letter:
            if len(by_letter["S"]) != 1:
                return False
            spindle = by_letter["S"][0]
        if 3 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if "F" in by_letter:
            if len(by_letter["F"]) != 1 or by_letter["F"][0] <= 0:
                return False
            feed = by_letter["F"][0]
        old = position.copy()
        for axis in ("X", "Y", "Z"):
            if axis in by_letter:
                if len(by_letter[axis]) != 1:
                    return False
                position[axis] = by_letter[axis][0]

        if motion == 0 and any(axis in by_letter for axis in ("X", "Y", "Z")):
            if not metric or not absolute or current_tool not in {1, 2} or not spindle_on:
                return False
            if not close(spindle, 7000.0):
                return False
            if position["Z"] is None or float(position["Z"]) < 19.99:
                return False
            if position["X"] is not None and not (-60.01 <= float(position["X"]) <= 60.01):
                return False
            if position["Y"] is not None and not (-40.01 <= float(position["Y"]) <= 40.01):
                return False

        if motion in {1, 2, 3} and any(axis in by_letter for axis in ("X", "Y", "Z")):
            if not metric or not absolute or current_tool not in {1, 2}:
                return False
            if not spindle_on or not close(spindle, 7000.0, 1e-6):
                return False
            if current_tool == 1:
                if feed is None or not close(feed, 600.0, 1e-6):
                    return False
                z_value = position["Z"]
                if z_value is None or z_value < 12.99:
                    return False
                if close(z_value, 13.0, 1e-6):
                    if None not in (old["X"], old["Y"], position["X"], position["Y"]):
                        pocket_segments.append(
                            (
                                float(old["X"]),
                                float(old["Y"]),
                                float(position["X"]),
                                float(position["Y"]),
                            )
                        )
            elif current_tool == 2 and motion in {1, 2, 3}:
                # T2 is a drill; lateral feed cuts are not part of the configured operation.
                return False

        if any(code in {82, 83, 73} for code in g_codes):
            return False
        if motion == 81 and 81 in g_codes:
            if not metric or not absolute or current_tool != 2 or not spindle_on:
                return False
            if not close(spindle, 7000.0) or feed is None or not close(feed, 600.0):
                return False
            required = {axis: by_letter.get(axis, []) for axis in ("X", "Y", "Z", "R")}
            if any(len(values) != 1 for values in required.values()):
                return False
            x_value, y_value, z_value, r_value = (
                required[axis][0] for axis in ("X", "Y", "Z", "R")
            )
            drill_cycles.append((x_value, y_value, z_value, r_value))
            position["Z"] = r_value
            g80_after_cycles = False
        if 80 in g_codes and drill_cycles:
            g80_after_cycles = True
        if 30 in m_codes:
            return False
        if 2 in m_codes:
            m2_count += 1

    if not seen_t1 or not seen_t2 or m2_count != 1 or not g80_after_cycles:
        return False
    if not validate_pocket_segments(pocket_segments):
        return False
    if len(drill_cycles) != 4:
        return False
    observed_centers = {(round(x, 6), round(y, 6)) for x, y, _, _ in drill_cycles}
    if observed_centers != HOLE_CENTERS:
        return False
    if any(not close(z_value, 10.0) or not close(r_value, 20.0) for _, _, z_value, r_value in drill_cycles):
        return False
    return True


def validate_nc_file(path: Path) -> bool:
    if not ensure_regular(path, 500, 200_000):
        return False
    try:
        return validate_nc_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return False


def canonical_nc(text: str) -> str:
    return TIMESTAMP_RE.sub("(Output Time:<TIMESTAMP>)", text).replace("\r\n", "\n")


def validate_fcstd_archive(path: Path) -> bool:
    if not ensure_regular(path, 2_000, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if (
                "Document.xml" not in names
                or len(names) != len(set(names))
                or len(names) > 300
            ):
                return False
            total = 0
            for entry in archive.infolist():
                pure = Path(entry.filename)
                if pure.is_absolute() or ".." in pure.parts:
                    return False
                total += entry.file_size
                if entry.file_size > 20_000_000 or total > 50_000_000:
                    return False
                if pure.suffix.lower() in {".py", ".pyc", ".so", ".dll", ".dylib"}:
                    return False
            document = archive.read("Document.xml")
            if len(document) > 5_000_000:
                return False
            root = ET.fromstring(document)
            proxies = Counter(
                (
                    element.attrib.get("module"),
                    element.attrib.get("class"),
                    element.attrib.get("value"),
                    element.attrib.get("encoded"),
                )
                for element in root.iter("Python")
            )
            if any(proxies[record] != count for record, count in REQUIRED_PROXY_RECORDS.items()):
                return False
            if sum(proxies[record] for record in STOCK_PROXY_RECORDS) != 1:
                return False
            allowed = set(REQUIRED_PROXY_RECORDS) | OPTIONAL_PROXY_RECORDS | STOCK_PROXY_RECORDS
            if any(record not in allowed or count != 1 for record, count in proxies.items() if record not in REQUIRED_PROXY_RECORDS):
                return False
    except (OSError, zipfile.BadZipFile, RuntimeError, ET.ParseError):
        return False
    return True


CHILD_SOURCE = r'''
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re
import sys

import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor


EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256 = "08326459e03c3a8bc2d6f9b20ae795f797f4d269552398c8158bb90ee3863be1"
HOLES = {(-40.0, -25.0), (-40.0, 25.0), (40.0, -25.0), (40.0, 25.0)}
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")


def close(a, b, tolerance=1e-6):
    return math.isfinite(float(a)) and abs(float(a) - float(b)) <= tolerance


def normalized_text_sha256(path):
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def bounds(shape):
    box = shape.BoundBox
    return (box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)


def point_segment_distance(px, py, segment):
    x1, y1, x2, y2 = segment
    dx = x2 - x1
    dy = y2 - y1
    denominator = dx * dx + dy * dy
    if denominator <= 1e-18:
        return math.hypot(px - x1, py - y1)
    factor = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / denominator))
    return math.hypot(px - (x1 + factor * dx), py - (y1 + factor * dy))


def validate_segments(segments):
    if len(segments) < 20:
        return False
    points = [(s[0], s[1]) for s in segments] + [(s[2], s[3]) for s in segments]
    if any(x < -17.01 or x > 17.01 or y < -9.01 or y > 9.01 for x, y in points):
        return False
    if not (min(x for x, _ in points) <= -16.99 and max(x for x, _ in points) >= 16.99):
        return False
    if not (min(y for _, y in points) <= -8.99 and max(y for _, y in points) >= 8.99):
        return False
    for grid_y in range(-9, 10, 2):
        for grid_x in range(-17, 18, 2):
            if min(point_segment_distance(grid_x, grid_y, s) for s in segments) > 2.2:
                return False
    return True


def proxy_module(obj):
    proxy = getattr(obj, "Proxy", None)
    return getattr(getattr(proxy, "__class__", None), "__module__", None)


def tool_feed(controller, name):
    return float(getattr(controller, name).getValueAs("mm/min").Value)


def safe_post_text(value):
    text = str(value)
    return (
        len(text) <= 500
        and text.isprintable()
        and not any(character in text for character in "()\r\n")
    )


def validate_part_shape(shape):
    if not shape.isValid() or shape.ShapeType != "Solid" or len(shape.Solids) != 1:
        return False
    if any(not close(a, b, 1e-6) for a, b in zip(bounds(shape), (-60, 60, -40, 40, 0, 18))):
        return False
    expected_volume = 120.0 * 80.0 * 18.0 - 40.0 * 24.0 * 5.0 - 4.0 * math.pi * 2.5 * 2.5 * 8.0
    if not close(shape.Volume, expected_volume, 1e-4):
        return False
    pocket_faces = [
        face for face in shape.Faces
        if close(face.BoundBox.ZMin, 13.0) and close(face.BoundBox.ZMax, 13.0)
        and close(face.Area, 960.0, 1e-4)
        and close(face.BoundBox.XMin, -20.0) and close(face.BoundBox.XMax, 20.0)
        and close(face.BoundBox.YMin, -12.0) and close(face.BoundBox.YMax, 12.0)
    ]
    if len(pocket_faces) != 1:
        return False
    top_holes = set()
    bottom_holes = set()
    for edge in shape.Edges:
        curve = edge.Curve
        if type(curve).__name__ != "Circle" or not close(curve.Radius, 2.5):
            continue
        center = (round(curve.Center.x, 6), round(curve.Center.y, 6))
        if close(curve.Center.z, 18.0):
            top_holes.add(center)
        if close(curve.Center.z, 10.0):
            bottom_holes.add(center)
    if top_holes != HOLES or bottom_holes != HOLES:
        return False
    cylindrical = []
    for face in shape.Faces:
        surface = face.Surface
        if type(surface).__name__ == "Cylinder" and close(surface.Radius, 2.5):
            cylindrical.append(face)
    if len(cylindrical) != 4:
        return False
    return True


def validate_step(path):
    shape = Part.Shape()
    shape.read(str(path))
    return shape if validate_part_shape(shape) else None


def validate_document(fcstd, step, nc, repost):
    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        return False
    if normalized_text_sha256(step) != EXPECTED_STEP_SHA256:
        return False
    step_shape = validate_step(step)
    if step_shape is None:
        return False
    doc = App.openDocument(str(fcstd))
    try:
        jobs = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Main.Job"]
        pockets = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Op.PocketShape"]
        drillings = [obj for obj in doc.Objects if proxy_module(obj) == "Path.Op.Drilling"]
        if len(jobs) != 1 or len(pockets) != 1 or len(drillings) != 1:
            return False
        job, pocket, drilling = jobs[0], pockets[0], drillings[0]
        if not safe_post_text(job.Label):
            return False
        if job.PostProcessor != "linuxcnc":
            return False
        if job.PostProcessorArgs.split() != ["--line-numbers", "--no-show-editor"]:
            return False
        if pathlib.Path(job.PostProcessorOutputFile) != pathlib.Path("/home/user/Desktop/task-12.nc"):
            # Candidate generation uses a temporary name; only formal evaluation requires exact output.
            return False
        if list(job.Fixtures) != ["G54"] or job.SplitOutput:
            return False
        operations = list(job.Operations.Group)
        if operations != [pocket, drilling]:
            return False
        models = list(job.Model.Group)
        if len(models) != 1 or not validate_part_shape(models[0].Shape):
            return False
        model = models[0]
        if model.Shape.cut(step_shape).Volume > 1e-5 or step_shape.cut(model.Shape).Volume > 1e-5:
            return False
        stock = job.Stock
        if proxy_module(stock) != "Path.Main.Stock":
            return False
        if not stock.Shape.isValid() or len(stock.Shape.Solids) != 1:
            return False
        if any(not close(a, b) for a, b in zip(bounds(stock.Shape), (-60, 60, -40, 40, 0, 18))):
            return False
        if not close(stock.Shape.Volume, 120.0 * 80.0 * 18.0, 1e-4):
            return False
        extension_names = ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos")
        if all(hasattr(stock, name) for name in extension_names):
            if any(
                not close(getattr(stock, name).getValueAs("mm").Value, 0.0)
                for name in extension_names
            ):
                return False
        controllers = list(job.Tools.Group)
        if len(controllers) != 2:
            return False
        by_number = {int(controller.ToolNumber): controller for controller in controllers}
        if set(by_number) != {1, 2}:
            return False
        t1, t2 = by_number[1], by_number[2]
        if proxy_module(t1) != "Path.Tool.Controller" or proxy_module(t2) != "Path.Tool.Controller":
            return False
        if proxy_module(t1.Tool) != "Path.Tool.Bit" or proxy_module(t2.Tool) != "Path.Tool.Bit":
            return False
        if not close(t1.Tool.Diameter.Value, 6.0) or not close(t2.Tool.Diameter.Value, 5.0):
            return False
        if t1.Tool.ShapeName != "endmill" or pathlib.Path(t1.Tool.BitShape).name != "endmill.fcstd":
            return False
        if t2.Tool.ShapeName != "drill" or pathlib.Path(t2.Tool.BitShape).name != "drill.fcstd":
            return False
        for controller in (t1, t2):
            if not safe_post_text(controller.Label):
                return False
            if not safe_post_text(controller.Tool.Label):
                return False
            if not close(controller.SpindleSpeed, 7000.0):
                return False
            if controller.SpindleDir != "Forward":
                return False
            if not close(tool_feed(controller, "HorizFeed"), 600.0):
                return False
            if not close(tool_feed(controller, "VertFeed"), 600.0):
                return False
        if pocket.ToolController != t1 or drilling.ToolController != t2:
            return False
        for operation in (pocket, drilling):
            if not safe_post_text(operation.Label) or not safe_post_text(operation.Comment):
                return False
            if hasattr(operation, "UserLabel") and not safe_post_text(operation.UserLabel):
                return False
        if not (close(pocket.StartDepth.Value, 18.0) and close(pocket.FinalDepth.Value, 13.0)):
            return False
        if not close(pocket.StepDown.Value, 5.0) or int(pocket.StepOver) != 50:
            return False
        if pocket.OffsetPattern != "ZigZag" or pocket.StartAt != "Center" or pocket.CutMode != "Climb":
            return False
        if not (close(pocket.SafeHeight.Value, 20.0) and close(pocket.ClearanceHeight.Value, 23.0)):
            return False
        if len(pocket.Base) != 1 or len(pocket.Base[0][1]) != 1:
            return False
        boundary = pocket.Base[0][0]
        if len(boundary.Shape.Faces) != 1:
            return False
        if any(not close(a, b) for a, b in zip(bounds(boundary.Shape), (-20, 20, -12, 12, 18, 18))):
            return False
        if not close(boundary.Shape.Faces[0].Area, 960.0):
            return False
        selected = boundary.Shape.getElement(pocket.Base[0][1][0])
        if selected.ShapeType != "Face" or not close(selected.Area, 960.0):
            return False
        if not (close(drilling.StartDepth.Value, 18.0) and close(drilling.FinalDepth.Value, 10.0)):
            return False
        if not (close(drilling.SafeHeight.Value, 20.0) and close(drilling.ClearanceHeight.Value, 23.0)):
            return False
        if not close(drilling.RetractHeight.Value, 20.0):
            return False
        if drilling.PeckEnabled or drilling.DwellEnabled or drilling.KeepToolDown:
            return False
        if len(drilling.Base) != 1 or len(drilling.Base[0][1]) != 4:
            return False
        if drilling.Base[0][0] != model:
            return False
        centers = set()
        for sub in drilling.Base[0][1]:
            edge = model.Shape.getElement(sub)
            curve = edge.Curve
            if type(curve).__name__ != "Circle" or not close(curve.Radius, 2.5):
                return False
            centers.add((round(curve.Center.x, 6), round(curve.Center.y, 6)))
        if centers != HOLES:
            return False
        for obj in doc.Objects:
            obj.touch()
        doc.recompute()
        doc.recompute()
        if any(
            any(state in {"Touched", "Invalid", "Error"} for state in obj.State)
            for obj in doc.Objects
        ):
            return False

        pocket_segments = []
        position = {"X": None, "Y": None, "Z": None}
        for command in pocket.Path.Commands:
            old = position.copy()
            for axis in ("X", "Y", "Z"):
                if axis in command.Parameters:
                    position[axis] = float(command.Parameters[axis])
            if command.Name in {"G1", "G2", "G3"} and close(position["Z"], 13.0):
                if None not in (old["X"], old["Y"], position["X"], position["Y"]):
                    pocket_segments.append((old["X"], old["Y"], position["X"], position["Y"]))
        if not validate_segments(pocket_segments):
            return False
        cycles = []
        for command in drilling.Path.Commands:
            if command.Name == "G81":
                params = command.Parameters
                if not all(axis in params for axis in ("X", "Y", "Z", "R")):
                    return False
                cycles.append((float(params["X"]), float(params["Y"]), float(params["Z"]), float(params["R"])))
        if len(cycles) != 4:
            return False
        if {(round(x, 6), round(y, 6)) for x, y, _, _ in cycles} != HOLES:
            return False
        if any(not close(z, 10.0) or not close(r, 20.0) for _, _, z, r in cycles):
            return False

        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1:
            return False
        PostProcessor.load("linuxcnc").export(
            sections[0][1], str(repost), job.PostProcessorArgs
        )
        submitted = nc.read_text(encoding="utf-8")
        fresh = repost.read_text(encoding="utf-8")
        canonical = lambda text: TIMESTAMP_RE.sub("(Output Time:<TIMESTAMP>)", text).replace("\r\n", "\n")
        return canonical(submitted) == canonical(fresh)
    finally:
        App.closeDocument(doc.Name)


marker, fcstd_arg, step_arg, nc_arg, repost_arg = sys.argv[1:6]
try:
    result = validate_document(
        pathlib.Path(fcstd_arg),
        pathlib.Path(step_arg),
        pathlib.Path(nc_arg),
        pathlib.Path(repost_arg),
    )
except Exception as exc:
    print("task-12 FreeCAD validation: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
    result = False
print(marker + "=" + ("True" if result else "False"))
'''


def run_freecad_validation(fcstd: Path, step: Path, nc: Path) -> bool:
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or not os.access(executable, os.X_OK):
        return False
    if info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    marker = "TASK12_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-task12-") as raw_temp:
        temp = Path(raw_temp)
        script = temp / "validate.py"
        repost = temp / "repost.nc"
        script.write_text(CHILD_SOURCE, encoding="utf-8")
        script.chmod(0o600)
        command = [
            str(executable),
            "-c",
            (
                "import builtins,sys; sys.argv=%r; builtins.pythonopen=open; "
                "exec(compile(open(%r, encoding='utf-8').read(), %r, 'exec'))"
                % (
                    [str(script), marker, str(fcstd), str(step), str(nc), str(repost)],
                    str(script),
                    str(script),
                )
            ),
        ]
        environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(temp),
            "TMPDIR": str(temp),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONNOUSERSITE": "1",
            "QT_QPA_PLATFORM": "offscreen",
        }
        try:
            completed = subprocess.run(
                command,
                cwd=temp,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=240,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        if len(completed.stdout) > 2_000_000 or len(completed.stderr) > 2_000_000:
            return False
        expected = marker + "=True"
        marker_lines = [
            line for line in completed.stdout.splitlines() if line.startswith(marker + "=")
        ]
        if completed.returncode != 0 or marker_lines != [expected]:
            if completed.stderr:
                print(completed.stderr[-4000:], file=sys.stderr)
            return False
        return True


def main() -> bool:
    config = TARGET / "post_config.json"
    step = TARGET / "post_test_part.step"
    fcstd = TARGET / "task-12.FCStd"
    nc = TARGET / "task-12.nc"
    if load_config(config) is None:
        return fail("invalid post_config.json")
    if not ensure_regular(step, 5_000, 5_000_000):
        return fail("invalid STEP file")
    try:
        if normalized_text_sha256(step) != EXPECTED_STEP_SHA256:
            return fail("unexpected STEP file")
    except OSError:
        return fail("unreadable STEP file")
    if not validate_fcstd_archive(fcstd):
        return fail("invalid FCStd archive")
    if not validate_nc_file(nc):
        return fail("invalid NC semantics")
    if not run_freecad_validation(fcstd, step, nc):
        return fail("FreeCAD validation or fresh repost failed")
    return True


if __name__ == "__main__":
    try:
        outcome = main()
    except Exception as exc:
        print("task-12 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        outcome = False
    print("True" if outcome else "False")
