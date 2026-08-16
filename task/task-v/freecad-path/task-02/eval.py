from __future__ import annotations

# Prevent output-directory modules from shadowing standard library imports.
import sys as _sys

_SCRIPT_DIR = __file__.rsplit("/", 1)[0]
_sys.path[:] = [entry for entry in _sys.path if entry not in {"", _SCRIPT_DIR}]

import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


TARGET = Path(os.environ.get("ENGIWORLD_EVAL_TARGET", "/home/user/Desktop"))
STEP_NAME = "outer_plate.step"
FCSTD_NAME = "task-2.FCStd"
NC_NAME = "task-2.nc"
EXPECTED_STEP_SHA256 = "569f0f591448bf401d37e5ef41d4211656d2662d8c1a0bcd563fe83b680f37d1"
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".pyc", ".pyo", ".ipynb", ".sh", ".bash", ".zsh",
    ".bat", ".cmd", ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr", ".so", ".dll", ".dylib", ".exe",
}
REQUIRED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("draftobjects.clone", "Clone"): 1,
    ("Path.Tool.Controller", "ToolController"): 1,
    ("Path.Tool.Bit", "ToolBit"): 1,
    ("Path.Op.Profile", "ObjectProfile"): 2,
})
MARKER = "TASK_V02_RESULT="


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


def freeze_file(source: Path, target: Path, minimum: int, maximum: int) -> bool:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(source, flags)
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or not minimum <= before.st_size <= maximum:
                return False
            chunks = []
            remaining = maximum + 1
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        identity = lambda item: (
            item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns
        )
        data = b"".join(chunks)
        if identity(before) != identity(after) or len(data) != before.st_size:
            return False
        target.write_bytes(data)
        target.chmod(0o600)
        return True
    except OSError:
        return False


def allowed_property_file(value: str) -> bool:
    if value in {"", "/home/user/Desktop/task-2.nc"}:
        return True
    pure = PurePosixPath(value)
    return (
        pure.is_absolute()
        and ".." not in pure.parts
        and pure.suffix.lower() == ".fcstd"
        and (
            value.startswith("/usr/share/freecad/Mod/Path/Tools/Shape/")
            or value.startswith("/usr/lib/freecad/Mod/Path/Tools/Shape/")
        )
    )


def fcstd_preflight(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [entry.filename for entry in infos]
            if (
                not 1 <= len(infos) <= 128
                or names.count("Document.xml") != 1
                or len(names) != len(set(names))
            ):
                return False
            total = 0
            for entry in infos:
                pure = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                if (
                    not entry.filename
                    or "\\" in entry.filename
                    or pure.is_absolute()
                    or ".." in pure.parts
                    or entry.flag_bits & 1
                    or stat.S_ISLNK(mode)
                    or entry.file_size > 20_000_000
                    or (entry.compress_size == 0 and entry.file_size > 0)
                    or (entry.compress_size and entry.file_size / entry.compress_size > 400)
                    or pure.suffix.lower() in FORBIDDEN_EXTENSIONS
                ):
                    return False
                total += entry.file_size
                if total > 50_000_000:
                    return False
            document_xml = archive.read("Document.xml")
            if not document_xml or len(document_xml) > 5_000_000:
                return False

        root = ElementTree.fromstring(document_xml)
        proxies = Counter()
        for element in root.iter("Python"):
            module = element.attrib.get("module")
            class_name = element.attrib.get("class")
            encoded = element.attrib.get("encoded")
            value = element.attrib.get("value")
            if encoded != "yes" or not isinstance(value, str) or len(value) > 100_000:
                return False
            payload = json.loads(base64.b64decode(value, validate=True).decode("utf-8"))
            if (module, class_name) == ("draftobjects.clone", "Clone"):
                if not isinstance(payload, str):
                    return False
            elif payload is not None and not isinstance(payload, dict):
                return False
            proxies[(module, class_name)] += 1

        stock_count = sum(
            count
            for (module, class_name), count in proxies.items()
            if module == "Path.Main.Stock" and class_name in {"StockFromBase", "StockCreateBox"}
        )
        proxies = Counter({
            key: count for key, count in proxies.items() if key[0] != "Path.Main.Stock"
        })
        controller_count = proxies.pop(("Path.Tool.Controller", "ToolController"), 0)
        tool_count = proxies.pop(("Path.Tool.Bit", "ToolBit"), 0)
        required_without_tools = REQUIRED_PROXIES.copy()
        del required_without_tools[("Path.Tool.Controller", "ToolController")]
        del required_without_tools[("Path.Tool.Bit", "ToolBit")]
        if (
            stock_count != 1
            or not 1 <= controller_count <= 32
            or not 1 <= tool_count <= 32
            or proxies != required_without_tools
        ):
            return False

        for prop in root.iter("Property"):
            if prop.attrib.get("type") != "App::PropertyFile":
                continue
            values = [child.attrib.get("value") for child in prop if child.tag == "String"]
            if len(values) != 1 or not allowed_property_file(values[0]):
                return False
        for element in root.iter():
            if element.tag not in {"Part", "Path"}:
                continue
            member = element.attrib.get("file")
            if (
                not member
                or member not in names
                or PurePosixPath(member).suffix.lower() not in {".brp", ".nc"}
            ):
                return False
        return True
    except (
        OSError,
        UnicodeError,
        ValueError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        json.JSONDecodeError,
    ):
        return False


CHILD_SOURCE = r'''
import builtins
import json
import math
import os
import pathlib
import re

builtins.pythonopen = open
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor


EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
SOURCE_BOUNDS = (-60.0, 60.0, -40.0, 40.0, 0.0, 12.0)
MODEL_BOUNDS = (-60.0, 60.0, -40.0, 40.0, -12.0, 0.0)
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)", re.I)
ALLOWED_WORDS = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J", "K", "R", "P", "Q"}
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 64, 80, 90, 94}
ALLOWED_M = {2, 3, 4, 5, 6}


def near(actual, expected, tolerance=1e-6):
    try:
        left, right = float(actual), float(expected)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def module(obj):
    return type(getattr(obj, "Proxy", None)).__module__


def bounds(shape):
    box = shape.BoundBox
    return (box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)


def same_shape(left, right, tolerance=1e-5):
    return (
        not left.isNull()
        and not right.isNull()
        and left.isValid()
        and right.isValid()
        and len(left.Solids) == 1
        and len(right.Solids) == 1
        and left.cut(right).Volume <= tolerance
        and right.cut(left).Volume <= tolerance
    )


def quantity_mm_per_minute(value):
    try:
        return float(value.getValueAs("mm/min").Value)
    except Exception:
        return float(value.Value) * 60.0


def flat_bottom_tool(shape, diameter):
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        return False
    box = shape.BoundBox
    expected_area = math.pi * (diameter / 2.0) ** 2
    for face in shape.Faces:
        face_box = face.BoundBox
        if type(face.Surface).__name__ != "Plane":
            continue
        if face_box.ZLength > 1e-4 or not near(face_box.ZMin, box.ZMin, 1e-4):
            continue
        if not near(face_box.XLength, diameter, 1e-3) or not near(face_box.YLength, diameter, 1e-3):
            continue
        if abs(face.Area - expected_area) <= expected_area * 0.02:
            return True
    return False


def strip_comments(text):
    output = []
    in_comment = False
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = []
        for char in raw:
            if in_comment:
                if char == "(":
                    return None
                if char == ")":
                    in_comment = False
            elif char == "(":
                in_comment = True
            elif char == ")":
                return None
            elif char == ";":
                break
            else:
                line.append(char)
        output.append("".join(line))
    return None if in_comment else "\n".join(output)


def code_signature(path):
    try:
        executable = strip_comments(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    if executable is None:
        return None
    result = []
    for raw in executable.splitlines():
        line = raw.strip().upper()
        if not line or line == "%":
            continue
        words = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            letter = match.group(1).upper()
            value = float(match.group(2))
            if letter not in ALLOWED_WORDS or not math.isfinite(value):
                return None
            if letter != "N":
                value = 0.0 if abs(value) < 5e-7 else round(value, 6)
                words.append((letter, value))
            cursor = match.end()
        if line[cursor:].strip() or not words:
            return None
        if words == [("M", 30.0)]:
            words = [("M", 2.0)]
        address_order = {
            letter: index for index, letter in enumerate("GMT H S F XYZ IJKRPQ".replace(" ", ""))
        }
        words.sort(key=lambda word: (address_order[word[0]], word[1]))
        result.append(tuple(words))
    return tuple(result)


def integral(value):
    rounded = round(value)
    return int(rounded) if math.isfinite(value) and abs(value - rounded) <= 1e-8 else None


def validate_nc_execution(signature):
    if not signature or signature[-1] != (("M", 2.0),):
        return False
    units = absolute = wcs = False
    motion = None
    position = {"X": None, "Y": None, "Z": None}
    feed = speed = None
    tool = None
    spindle = False
    saw_lateral_cut = False
    terminated = False
    lateral_count = 0
    for block_index, block in enumerate(signature):
        if terminated:
            return False
        by_letter = {}
        for letter, value in block:
            by_letter.setdefault(letter, []).append(value)
        if any(len(values) > 1 for letter, values in by_letter.items() if letter not in {"G", "M"}):
            return False
        g_codes = []
        for value in by_letter.get("G", []):
            code = integral(value)
            if code not in ALLOWED_G:
                return False
            g_codes.append(code)
        m_codes = []
        for value in by_letter.get("M", []):
            code = integral(value)
            if code == 30:
                code = 2
            if code not in ALLOWED_M:
                return False
            m_codes.append(code)
        if sum(code in {0, 1, 2, 3, 80} for code in g_codes) > 1:
            return False
        if 21 in g_codes:
            units = True
        if 90 in g_codes:
            absolute = True
        if 54 in g_codes:
            wcs = True
        explicit_motion = next((code for code in g_codes if code in {0, 1, 2, 3}), None)
        if explicit_motion is not None:
            motion = explicit_motion
        if "T" in by_letter:
            tool = integral(by_letter["T"][0])
            if tool != 1:
                return False
        if "S" in by_letter:
            speed = by_letter["S"][0]
            if not near(speed, 9000.0, 1e-3):
                return False
        if "F" in by_letter:
            feed = by_letter["F"][0]
            if not math.isfinite(feed) or feed <= 0.0:
                return False
        if 6 in m_codes:
            if tool not in {None, 1}:
                return False
        if 3 in m_codes or 4 in m_codes:
            spindle = True
        if 5 in m_codes:
            spindle = False
        if 2 in m_codes:
            if block_index != len(signature) - 1 or block != (("M", 2.0),):
                return False
            terminated = True
            continue

        explicit = {
            axis: by_letter[axis][0]
            for axis in ("X", "Y", "Z")
            if axis in by_letter
        }
        if not explicit:
            continue
        if motion is None:
            return False
        start = dict(position)
        for axis, value in explicit.items():
            position[axis] = value
        end = dict(position)
        if any(value is not None and not math.isfinite(value) for value in end.values()):
            return False
        xy_changed = (
            None not in (start["X"], start["Y"], end["X"], end["Y"])
            and (not near(start["X"], end["X"]) or not near(start["Y"], end["Y"]))
        )
        if motion == 0 and ("X" in explicit or "Y" in explicit):
            if (
                start["Z"] is None
                or end["Z"] is None
                or min(start["Z"], end["Z"]) <= 0.05
            ):
                return False
        if motion not in {1, 2, 3} or end["Z"] is None:
            continue
        if end["Z"] < -12.0001:
            return False
        if end["Z"] <= 0.0001 and not (
            units
            and absolute
            and wcs
            and tool in {None, 1}
            and spindle
            and near(speed, 9000.0, 1e-3)
        ):
            return False
        if end["Z"] <= 0.0001 and (feed is None or feed <= 0.0):
            return False
        if motion in {2, 3} and xy_changed and not {"I", "J"}.issubset(by_letter):
            return False
        if xy_changed and end["Z"] <= 0.0001:
            if feed is None or not near(feed, 650.0, 0.01):
                return False
            lateral_count += 1
            saw_lateral_cut = True
    return terminated and saw_lateral_cut and lateral_count >= 8


def distance_to_part(point):
    dx = max(abs(point[0]) - 60.0, 0.0)
    dy = max(abs(point[1]) - 40.0, 0.0)
    return math.hypot(dx, dy)


def sample_line(start, end):
    length = math.dist(start[:2], end[:2])
    count = max(1, int(math.ceil(length / 0.5)))
    return [
        (
            start[0] + (end[0] - start[0]) * index / count,
            start[1] + (end[1] - start[1]) * index / count,
        )
        for index in range(count + 1)
    ], length


def sample_arc(name, start, end, params):
    if "I" not in params or "J" not in params:
        return None
    center = (start[0] + params["I"], start[1] + params["J"])
    radius = math.dist(start[:2], center)
    if radius <= 1e-7 or abs(math.dist(end[:2], center) - radius) > 0.02:
        return None
    start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
    end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
    if name == "G2":
        while end_angle >= start_angle - 1e-12:
            end_angle -= math.tau
    else:
        while end_angle <= start_angle + 1e-12:
            end_angle += math.tau
    sweep = end_angle - start_angle
    count = max(2, int(math.ceil(abs(sweep) * radius / 0.5)))
    samples = [
        (
            center[0] + radius * math.cos(start_angle + sweep * index / count),
            center[1] + radius * math.sin(start_angle + sweep * index / count),
        )
        for index in range(count + 1)
    ]
    samples[0], samples[-1] = start[:2], end[:2]
    return samples, abs(sweep) * radius


def operation_motion(operation, clearance):
    position = {"X": None, "Y": None, "Z": None}
    lateral = []
    for index, command in enumerate(operation.Path.Commands):
        name = str(command.Name).upper().replace(" ", "")
        name = {"G00": "G0", "G01": "G1", "G02": "G2", "G03": "G3"}.get(name, name)
        params = {}
        try:
            for key, value in command.Parameters.items():
                numeric = float(value)
                if not math.isfinite(numeric):
                    return None
                params[str(key).upper()] = numeric
        except Exception:
            return None
        if name not in {"G0", "G1", "G2", "G3"}:
            continue
        before = dict(position)
        for axis in position:
            if axis in params:
                position[axis] = params[axis]
        after = dict(position)
        if name == "G0":
            explicit_xy = "X" in params or "Y" in params
            if explicit_xy and (
                before["Z"] is None
                or after["Z"] is None
                or min(before["Z"], after["Z"]) < clearance - 1e-4
            ):
                return None
            if after["Z"] is not None and after["Z"] <= 0.0:
                return None
            continue
        if None in (before["X"], before["Y"], before["Z"], after["X"], after["Y"], after["Z"]):
            continue
        if min(before["Z"], after["Z"]) < -12.0001:
            return None
        xy_changed = not near(before["X"], after["X"]) or not near(before["Y"], after["Y"])
        if not xy_changed:
            continue
        if not near(before["Z"], after["Z"], 1e-5):
            return None
        start = (before["X"], before["Y"], before["Z"])
        end = (after["X"], after["Y"], after["Z"])
        sampled = sample_line(start, end) if name == "G1" else sample_arc(name, start, end, params)
        if sampled is None:
            return None
        lateral.append({
            "index": index,
            "name": name,
            "start": start,
            "end": end,
            "samples": sampled[0],
            "length": sampled[1],
        })
    return lateral or None


def ordered_levels(motions):
    result = []
    for motion in motions:
        level = motion["end"][2]
        if not any(near(level, existing, 1e-4) for existing in result):
            result.append(level)
    return result


def contour_groups(motions, level):
    selected = [motion for motion in motions if near(motion["end"][2], level, 1e-4)]
    groups = []
    current = []
    for motion in selected:
        if current and (
            motion["index"] != current[-1]["index"] + 1
            or math.dist(current[-1]["end"][:2], motion["start"][:2]) > 0.02
        ):
            groups.append(current)
            current = []
        current.append(motion)
    if current:
        groups.append(current)
    return groups


def validate_contour(group, extra):
    if len(group) < 4 or math.dist(group[0]["start"][:2], group[-1]["end"][:2]) > 0.03:
        return False
    expected = 3.0 + extra
    points = []
    for motion in group:
        if points:
            points.extend(motion["samples"][1:])
        else:
            points.extend(motion["samples"])
    if len(points) < 50:
        return False
    distances = [distance_to_part(point) for point in points]
    if min(distances) < expected - 0.06 or max(distances) > expected * math.sqrt(2.0) + 0.15:
        return False
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    wanted_bounds = (-60.0 - expected, 60.0 + expected, -40.0 - expected, 40.0 + expected)
    actual_bounds = (min(xs), max(xs), min(ys), max(ys))
    if any(not near(actual, wanted, 0.08) for actual, wanted in zip(actual_bounds, wanted_bounds)):
        return False
    targets = (
        (-60.0 - expected, 0.0), (60.0 + expected, 0.0),
        (0.0, -40.0 - expected), (0.0, 40.0 + expected),
    )
    if any(min(math.dist(point, target) for point in points) > 0.65 for target in targets):
        return False
    travel = sum(motion["length"] for motion in group)
    if not 390.0 <= travel <= 470.0:
        return False
    twice_area = sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(points, points[1:])
    )
    return abs(twice_area) > 15_000.0


def base_is_model(operation, model):
    bases = list(getattr(operation, "Base", []))
    if not bases:
        return True
    for base, subelements in bases:
        if base is not model or not subelements:
            return False
    return True


def common_profile_ok(operation, controller, model):
    if (
        module(operation) != "Path.Op.Profile"
        or type(operation.Proxy).__name__ != "ObjectProfile"
        or operation.ToolController is not controller
        or not bool(operation.Active)
        or list(operation.State) != ["Up-to-date"]
        or str(operation.Side) != "Outside"
        or not bool(operation.UseComp)
        or not bool(operation.processPerimeter)
        or bool(operation.processHoles)
        or bool(operation.processCircles)
        or str(operation.Direction) not in {"CW", "CCW"}
        or str(operation.JoinType) not in {"Round", "Square", "Miter"}
        or not base_is_model(operation, model)
        or not near(operation.StartDepth.Value, 0.0, 1e-5)
        or not near(operation.FinalDepth.Value, -12.0, 1e-5)
        or not math.isfinite(float(operation.StepDown.Value))
        or not 0.0 < operation.StepDown.Value <= 100.0
        or not math.isfinite(float(operation.SafeHeight.Value))
        or not math.isfinite(float(operation.ClearanceHeight.Value))
        or operation.SafeHeight.Value <= 0.05
        or operation.ClearanceHeight.Value < operation.SafeHeight.Value
        or operation.ClearanceHeight.Value > 100.0
    ):
        return False
    return True


def validate_rough(operation, controller, model):
    if not common_profile_ok(operation, controller, model):
        return False
    stepdown = float(operation.StepDown.Value)
    if not near(operation.OffsetExtra.Value, 0.2, 1e-4) or not 0.05 <= stepdown <= 12.0:
        return False
    motions = operation_motion(operation, float(operation.SafeHeight.Value))
    if motions is None:
        return False
    levels = ordered_levels(motions)
    if not 1 <= len(levels) <= 24 or not near(levels[-1], -12.0, 1e-4):
        return False
    previous = 0.0
    for level in levels:
        if level >= previous - 1e-5 or previous - level > stepdown + 0.02:
            return False
        groups = contour_groups(motions, level)
        if len(groups) != 1 or not validate_contour(groups[0], 0.2):
            return False
        previous = level
    return True


def validate_finish(operation, controller, model):
    if not common_profile_ok(operation, controller, model):
        return False
    if not near(operation.OffsetExtra.Value, 0.0, 1e-5):
        return False
    motions = operation_motion(operation, float(operation.SafeHeight.Value))
    if motions is None:
        return False
    levels = ordered_levels(motions)
    if len(levels) != 1 or not near(levels[0], -12.0, 1e-4):
        return False
    groups = contour_groups(motions, -12.0)
    return len(groups) == 1 and validate_contour(groups[0], 0.0)


def safe_post_arguments(value):
    return (
        len(value) <= 500
        and not any(char in value for char in "\x00\r\n;&|`$<>")
    )


def validate_document(doc):
    jobs = [obj for obj in doc.Objects if module(obj) == "Path.Main.Job"]
    profiles = [obj for obj in doc.Objects if module(obj) == "Path.Op.Profile"]
    controllers = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Controller"]
    tools = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Bit"]
    if len(jobs) != 1 or len(profiles) != 2 or not controllers or not tools:
        return None
    job = jobs[0]
    model_group = list(job.Model.Group)
    if len(model_group) != 1:
        return None
    model = model_group[0]
    expected_model = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, -12.0))
    if module(model) != "draftobjects.clone" or not same_shape(model.Shape, expected_model):
        return None
    if any(not near(actual, wanted, 1e-5) for actual, wanted in zip(bounds(model.Shape), MODEL_BOUNDS)):
        return None
    sources = list(getattr(model, "Objects", []))
    expected_source = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, 0.0))
    if (
        len(sources) != 1
        or not (
            same_shape(sources[0].Shape, expected_source)
            or same_shape(sources[0].Shape, expected_model)
        )
    ):
        return None
    stock = job.Stock
    if module(stock) != "Path.Main.Stock" or stock.Shape.isNull() or not stock.Shape.isValid() or len(stock.Shape.Solids) != 1:
        return None
    if model.Shape.cut(stock.Shape).Volume > 1e-5:
        return None
    stock_bounds = bounds(stock.Shape)
    if (
        stock_bounds[0] < -80.0 or stock_bounds[1] > 80.0
        or stock_bounds[2] < -60.0 or stock_bounds[3] > 60.0
        or not near(stock_bounds[4], -12.0, 1e-5)
        or not near(stock_bounds[5], 0.0, 1e-5)
    ):
        return None
    operations = list(job.Operations.Group)
    if len(operations) != 2 or set(operations) != set(profiles):
        return None
    rough, finish = operations
    controller = rough.ToolController
    tool = getattr(controller, "Tool", None)
    if (
        finish.ToolController is not controller
        or controller not in controllers
        or tool not in tools
        or controller not in list(job.Tools.Group)
        or list(job.Fixtures) != ["G54"]
        or bool(job.SplitOutput)
    ):
        return None
    processor = str(job.PostProcessor).strip().lower()
    arguments = str(job.PostProcessorArgs)
    if (
        processor not in {"linuxcnc", "grbl"}
        or not safe_post_arguments(arguments)
        or os.path.normpath(str(job.PostProcessorOutputFile)) != "/home/user/Desktop/task-2.nc"
    ):
        return None
    if (
        int(controller.ToolNumber) != 1
        or not near(controller.SpindleSpeed, 9000.0, 1e-3)
        or str(controller.SpindleDir) not in {"Forward", "Reverse"}
        or not near(quantity_mm_per_minute(controller.HorizFeed), 650.0, 1e-3)
        or not math.isfinite(quantity_mm_per_minute(controller.VertFeed))
        or quantity_mm_per_minute(controller.VertFeed) <= 0.0
        or not near(tool.Diameter.Value, 6.0, 1e-4)
        or str(tool.ShapeName).strip().lower() != "endmill"
        or pathlib.Path(str(tool.BitShape)).name.lower() != "endmill.fcstd"
        or not flat_bottom_tool(tool.Shape, 6.0)
    ):
        return None
    if not validate_rough(rough, controller, model) or not validate_finish(finish, controller, model):
        return None
    return job, processor


def validate(step_path, fcstd_path, nc_path, work_dir):
    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        return False
    expected_source = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, 0.0))
    source = Part.read(str(step_path))
    if not same_shape(source, expected_source):
        return False
    if any(not near(actual, wanted, 1e-5) for actual, wanted in zip(bounds(source), SOURCE_BOUNDS)):
        return False

    submitted_signature = code_signature(nc_path)
    if submitted_signature is None or not validate_nc_execution(submitted_signature):
        return False

    doc = App.openDocument(str(fcstd_path))
    try:
        doc.recompute()
        first = validate_document(doc)
        if first is None:
            return False
        for operation in list(first[0].Operations.Group):
            operation.touch()
        doc.recompute()
        doc.recompute()
        second = validate_document(doc)
        if second is None or second[1] != first[1]:
            return False
        recomputed = pathlib.Path(work_dir) / "recomputed.FCStd"
        doc.saveAs(str(recomputed))
    finally:
        App.closeDocument(doc.Name)

    reopened = App.openDocument(str(recomputed))
    try:
        reopened.recompute()
        final = validate_document(reopened)
        if final is None or final[1] != second[1]:
            return False
        final_job, final_processor = final
        sections = PathPostCommand.buildPostList(final_job)
        if len(sections) != 1 or not sections[0][1]:
            return False
        repost = pathlib.Path(work_dir) / "fresh-post.nc"
        PostProcessor.load(final_processor).export(
            sections[0][1], str(repost), str(final_job.PostProcessorArgs)
        )
    finally:
        App.closeDocument(reopened.Name)

    repost_signature = code_signature(repost)
    return (
        repost_signature is not None
        and validate_nc_execution(repost_signature)
        and submitted_signature == repost_signature
    )


try:
    ok = validate(
        pathlib.Path(os.environ["TASK_V02_STEP"]),
        pathlib.Path(os.environ["TASK_V02_FCSTD"]),
        pathlib.Path(os.environ["TASK_V02_NC"]),
        os.environ["TASK_V02_WORK"],
    )
except Exception:
    ok = False
print("TASK_V02_RESULT=" + json.dumps({"ok": bool(ok)}, sort_keys=True))
'''


def evaluate() -> bool:
    step = TARGET / STEP_NAME
    fcstd = TARGET / FCSTD_NAME
    nc = TARGET / NC_NAME
    if not regular_file(step, 1_000, 5_000_000) or sha256(step) != EXPECTED_STEP_SHA256:
        return False
    if not regular_file(fcstd, 1_000, 20_000_000) or not fcstd_preflight(fcstd):
        return False
    if not regular_file(nc, 300, 2_000_000):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="task_v02_eval_") as temporary:
            work = Path(temporary)
            step_copy = work / STEP_NAME
            fcstd_copy = work / FCSTD_NAME
            nc_copy = work / NC_NAME
            if not freeze_file(step, step_copy, 1_000, 5_000_000):
                return False
            if not freeze_file(fcstd, fcstd_copy, 1_000, 20_000_000):
                return False
            if not freeze_file(nc, nc_copy, 300, 2_000_000):
                return False
            if sha256(step_copy) != EXPECTED_STEP_SHA256 or not fcstd_preflight(fcstd_copy):
                return False
            script = work / "native_check.py"
            script.write_text(CHILD_SOURCE, encoding="utf-8")
            script.chmod(0o600)
            completed = subprocess.run(
                [
                    "/usr/bin/env",
                    "TASK_V02_STEP=" + str(step_copy),
                    "TASK_V02_FCSTD=" + str(fcstd_copy),
                    "TASK_V02_NC=" + str(nc_copy),
                    "TASK_V02_WORK=" + str(work),
                    "/usr/bin/freecadcmd",
                    str(script),
                ],
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=180,
                check=False,
            )
    except (OSError, subprocess.SubprocessError):
        return False
    if os.environ.get("ENGIWORLD_EVAL_DEBUG") == "1":
        print(completed.stdout)
    if completed.returncode != 0:
        return False
    reports = [
        line[len(MARKER):]
        for line in completed.stdout.splitlines()
        if line.startswith(MARKER)
    ]
    if len(reports) != 1:
        return False
    try:
        report = json.loads(reports[0])
    except (TypeError, json.JSONDecodeError):
        return False
    return isinstance(report, dict) and report.get("ok") is True


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
