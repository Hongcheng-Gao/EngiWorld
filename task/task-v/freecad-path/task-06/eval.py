from __future__ import annotations

import sys as _sys

_SCRIPT_DIR = __file__.rsplit("/", 1)[0]
_sys.path[:] = [entry for entry in _sys.path if entry not in {"", _SCRIPT_DIR}]

import base64
import hashlib
import json
import os
import stat
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


TARGET = Path(os.environ.get("ENGIWORLD_EVAL_TARGET", "/home/user/Desktop"))
STEP_NAME = "simple_cam_job.step"
FCSTD_NAME = "task-6.FCStd"
NC_NAME = "task-6.nc"
EXPECTED_STEP_SHA256 = "b8583cb4f37edeac903aa1c2ca45e4f59496573aeeb28d139e28f24fb9a6bafa"
MARKER = "TASK_V06_RESULT="
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".pyc", ".pyo", ".ipynb", ".sh", ".bash", ".zsh",
    ".bat", ".cmd", ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr", ".so", ".dll", ".dylib", ".exe",
}
REQUIRED_FIXED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("draftobjects.clone", "Clone"): 1,
})
OPERATION_PROXIES = {
    ("Path.Op.MillFace", "ObjectFace"),
    ("Path.Op.Drilling", "ObjectDrilling"),
    ("Path.Op.Profile", "ObjectProfile"),
}


def regular_file(path: Path, minimum: int, maximum: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not path.is_symlink() and minimum <= info.st_size <= maximum


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


def no_bypass_files(root: Path) -> bool:
    try:
        if not root.exists():
            return True
        for path in root.rglob("*"):
            if path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS:
                return False
    except OSError:
        return False
    return True


def allowed_property_file(name: str, value: str) -> bool:
    if name == "PostProcessorOutputFile":
        return value == "/home/user/Desktop/task-6.nc"
    if name == "File" and value == "":
        return True
    try:
        pure = PurePosixPath(value)
    except (TypeError, ValueError):
        return False
    if not pure.is_absolute() or ".." in pure.parts or "\x00" in value:
        return False
    system_roots = (
        PurePosixPath("/usr/lib/freecad/Mod/Path/Tools"),
        PurePosixPath("/usr/share/freecad/Mod/Path/Tools"),
    )
    if name == "BitShape":
        return pure.suffix.lower() == ".fcstd" and any(root in pure.parents for root in system_roots)
    if name == "File":
        metadata_roots = system_roots + (
            PurePosixPath("/home/user/.local/share/FreeCAD/Mod/Path/Tools/Bit"),
            PurePosixPath("/home/user/.FreeCAD/Mod/Path/Tools/Bit"),
        )
        return pure.suffix.lower() == ".fctb" and any(root in pure.parents for root in metadata_roots)
    return False


def fcstd_preflight(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if not 1 <= len(infos) <= 256 or names.count("Document.xml") != 1 or len(names) != len(set(names)):
                return False
            total = 0
            for item in infos:
                member = PurePosixPath(item.filename)
                mode = item.external_attr >> 16
                if (
                    not item.filename
                    or "\\" in item.filename
                    or member.is_absolute()
                    or ".." in member.parts
                    or item.flag_bits & 1
                    or stat.S_ISLNK(mode)
                    or item.file_size > 20_000_000
                    or (item.compress_size == 0 and item.file_size > 0)
                    or (item.compress_size and item.file_size / item.compress_size > 400)
                    or member.suffix.lower() in FORBIDDEN_EXTENSIONS
                ):
                    return False
                total += item.file_size
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
            value = element.attrib.get("value")
            if element.attrib.get("encoded") != "yes" or not isinstance(value, str) or len(value) > 100_000:
                return False
            payload = json.loads(base64.b64decode(value, validate=True).decode("utf-8"))
            if (module, class_name) == ("draftobjects.clone", "Clone"):
                if not isinstance(payload, str):
                    return False
            elif payload is not None and not isinstance(payload, dict):
                return False
            proxies[(module, class_name)] += 1
        allowed_stock_classes = {"StockFromBase", "StockCreateBox", "StockCreateCylinder"}
        if any(
            module == "Path.Main.Stock" and class_name not in allowed_stock_classes
            for module, class_name in proxies
        ):
            return False
        stock_count = sum(
            count for (module, class_name), count in proxies.items()
            if module == "Path.Main.Stock" and class_name in allowed_stock_classes
        )
        proxies = Counter({key: value for key, value in proxies.items() if key[0] != "Path.Main.Stock"})
        property_bags = proxies.pop(("Path.Base.PropertyBag", "PropertyBag"), 0)
        tool_controllers = proxies.pop(("Path.Tool.Controller", "ToolController"), 0)
        tool_bits = proxies.pop(("Path.Tool.Bit", "ToolBit"), 0)
        operation_counts = Counter({key: proxies.pop(key, 0) for key in OPERATION_PROXIES})
        if (
            stock_count != 1
            or not 2 <= tool_controllers <= 16
            or tool_bits != tool_controllers
            or not 0 <= property_bags <= tool_bits
            or proxies != REQUIRED_FIXED_PROXIES
            or any(operation_counts[key] < 1 for key in OPERATION_PROXIES)
        ):
            return False
        for prop in root.iter("Property"):
            if prop.attrib.get("type") != "App::PropertyFile":
                continue
            values = [child.attrib.get("value") for child in prop if child.tag == "String"]
            if len(values) != 1 or not allowed_property_file(prop.attrib.get("name", ""), values[0]):
                return False
        for element in root.iter():
            member = element.attrib.get("file")
            if member is None:
                continue
            if member not in names or PurePosixPath(member).suffix.lower() not in {"", ".brp", ".nc"}:
                return False
        return True
    except (
        OSError, UnicodeError, ValueError, zipfile.BadZipFile, ElementTree.ParseError,
        json.JSONDecodeError,
    ):
        return False


CHILD_SOURCE = r'''
import builtins
import hashlib
import json
import math
import os
import pathlib
import re
import shlex
import stat

builtins.pythonopen = open
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
import Path.Tool.Bit as PathToolBit
from Path.Post.Processor import PostProcessor


EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256 = "b8583cb4f37edeac903aa1c2ca45e4f59496573aeeb28d139e28f24fb9a6bafa"
ENDMILL_SHAPE = pathlib.Path("/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd")
DRILL_SHAPE = pathlib.Path("/usr/lib/freecad/Mod/Path/Tools/Shape/drill.fcstd")
TOOL_SHAPE_SHA256 = {
    ENDMILL_SHAPE: "30d93a314550d0cd1b1e4bc0efafcdcae57e0a450914dfbe64fdfbf211c04fcc",
    DRILL_SHAPE: "7512ec9478ffd10bb8885506dee988e0d12ea15c16f5d4c41ba011b73c366df6",
}
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)", re.I)
ALLOWED_WORDS = set("NGMTHDSFXYZABCIJKRPQL")
ALLOWED_G = {0, 1, 2, 3, 17, 20, 21, 40, 41, 42, 43, 49, 54, 55, 56, 57, 58, 59, 64, 73, 80, 81, 82, 83, 90, 91, 91.1, 94, 98, 99}
ALLOWED_M = {2, 3, 4, 5, 6, 7, 8, 9, 30}


def near(actual, expected, tolerance=1e-6):
    try:
        left, right = float(actual), float(expected)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def module(obj):
    return type(getattr(obj, "Proxy", None)).__module__


def proxy_class(obj):
    return type(getattr(obj, "Proxy", None)).__name__


def bounds(shape):
    box = shape.BoundBox
    return (box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)


def valid_solid(shape):
    return not shape.isNull() and shape.isValid() and len(shape.Solids) == 1


def same_shape(left, right, tolerance=1e-5):
    return (
        valid_solid(left) and valid_solid(right)
        and left.cut(right).Volume <= tolerance and right.cut(left).Volume <= tolerance
    )


def box_like(shape):
    if not valid_solid(shape) or not near(shape.Volume, 115200.0, 1e-3):
        return False
    box = shape.BoundBox
    if not (near(box.XLength, 120.0, 1e-4) and near(box.YLength, 80.0, 1e-4) and near(box.ZLength, 12.0, 1e-4)):
        return False
    return len(shape.Faces) == 6 and len(shape.Edges) == 12 and len(shape.Vertexes) == 8


def quantity_mm_per_minute(value):
    try:
        return float(value.getValueAs("mm/min").Value)
    except Exception:
        return float(value.Value) * 60.0


def flat_bottom_tool(shape, diameter):
    if not valid_solid(shape):
        return False
    box = shape.BoundBox
    expected_area = math.pi * (diameter / 2.0) ** 2
    for face in shape.Faces:
        face_box = face.BoundBox
        if type(face.Surface).__name__ != "Plane":
            continue
        if face_box.ZLength > 1e-4 or not near(face_box.ZMin, box.ZMin, 1e-4):
            continue
        if near(face_box.XLength, diameter, 1e-3) and near(face_box.YLength, diameter, 1e-3) and abs(face.Area - expected_area) <= expected_area * 0.02:
            return True
    return False


def secure_tool_template(value, expected):
    try:
        path = pathlib.Path(str(value)).resolve(strict=True)
        wanted = pathlib.Path(expected).resolve(strict=True)
        info = path.stat()
        return (
            path == wanted and stat.S_ISREG(info.st_mode) and info.st_uid == 0
            and not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            and hashlib.sha256(path.read_bytes()).hexdigest() == TOOL_SHAPE_SHA256[expected]
        )
    except (OSError, RuntimeError, ValueError):
        return False


def expected_tool_shape(parent_doc, name, shape_path, parameters):
    scratch = App.newDocument(name)
    try:
        tool = PathToolBit.Factory.CreateFromAttrs(
            {
                "version": 2,
                "name": name,
                "shape": str(shape_path),
                "parameter": parameters,
                "attribute": {},
            },
            name + "Bit",
        )
        scratch.recompute()
        return tool.Shape.copy()
    finally:
        App.closeDocument(scratch.Name)
        App.setActiveDocument(parent_doc.Name)


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
        saw_number = False
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            letter = match.group(1).upper()
            value = float(match.group(2))
            if letter not in ALLOWED_WORDS or not math.isfinite(value):
                return None
            if letter == "N":
                saw_number = True
            else:
                if letter == "M" and near(value, 30.0):
                    value = 2.0
                value = 0.0 if abs(value) < 5e-7 else round(value, 6)
                words.append((letter, value))
            cursor = match.end()
        if line[cursor:].strip():
            return None
        if not words:
            if saw_number:
                continue
            return None
        result.append(tuple(words))
    return tuple(result)


def integral(value):
    rounded = round(value)
    return int(rounded) if math.isfinite(value) and abs(value - rounded) <= 1e-8 else None


def validate_nc(signature, model_box, stock_box, drill_points, processor):
    if not signature or signature[-1] != (("M", 2.0),):
        return False
    units = absolute = terminated = spindle = False
    position = {"X": None, "Y": None, "Z": None}
    speed = feed = None
    selected_tool = active_tool = None
    t1_horizontal = 0
    drill_visits = []
    saw_m5 = False
    active_cycle = None
    cycle = {}
    for index, block in enumerate(signature):
        if terminated:
            return False
        values = {}
        for letter, value in block:
            values.setdefault(letter, []).append(value)
        if any(len(items) > 1 for letter, items in values.items() if letter not in {"G", "M"}):
            return False
        g_codes = []
        for value in values.get("G", []):
            code = 91.1 if near(value, 91.1) else integral(value)
            if code not in ALLOWED_G:
                return False
            g_codes.append(code)
        m_codes = []
        for value in values.get("M", []):
            code = integral(value)
            if code not in ALLOWED_M:
                return False
            m_codes.append(2 if code == 30 else code)
        modal_groups = (
            {0, 1, 2, 3, 73, 80, 81, 82, 83},
            {17},
            {20, 21},
            {90, 91},
            {91.1},
            {54, 55, 56, 57, 58, 59},
            {40, 41, 42},
            {43, 49},
            {93, 94},
            {98, 99},
        )
        if any(sum(code in group for code in g_codes) > 1 for group in modal_groups):
            return False
        if len(m_codes) != len(set(m_codes)) or sum(code in {3, 4, 5} for code in m_codes) > 1:
            return False
        if 20 in g_codes:
            return False
        if 21 in g_codes:
            units = True
        if 90 in g_codes:
            absolute = True
        if 91 in g_codes:
            absolute = False
        if "T" in values:
            selected_tool = integral(values["T"][0])
            if selected_tool not in {1, 2}:
                return False
        if "S" in values:
            speed = values["S"][0]
        if "F" in values:
            feed = values["F"][0]
        if 5 in m_codes:
            spindle = False
            saw_m5 = True
        if 6 in m_codes:
            if spindle or selected_tool not in {1, 2}:
                return False
            active_tool = selected_tool
        if "H" in values:
            if 43 not in g_codes or active_tool is None or integral(values["H"][0]) != active_tool:
                return False
        if 3 in m_codes or 4 in m_codes:
            if speed is None or not (near(speed, 7000.0, 1e-3) or near(speed, 5000.0, 1e-3)):
                return False
            inferred = 1 if near(speed, 7000.0, 1e-3) else 2
            if processor == "grbl" and 6 not in m_codes:
                active_tool = inferred
            if active_tool != inferred:
                return False
            spindle = True
        if 2 in m_codes:
            if spindle or index != len(signature) - 1 or block != (("M", 2.0),):
                return False
            terminated = True
            continue
        motion = next((code for code in g_codes if code in {0, 1, 2, 3}), None)
        before = dict(position)
        if motion is not None:
            if not units or not absolute:
                return False
            for axis in position:
                if axis in values:
                    position[axis] = values[axis][0]
            if motion == 0:
                if position["Z"] is None or position["Z"] < stock_box.ZMax + 0.1:
                    return False
            if motion in {1, 2, 3}:
                if not spindle or active_tool not in {1, 2}:
                    return False
                if active_tool == 1 and position["Z"] is not None and position["Z"] < stock_box.ZMin - 1.0:
                    return False
                xy = (
                    before["X"] is not None and before["Y"] is not None
                    and position["X"] is not None and position["Y"] is not None
                    and (not near(before["X"], position["X"]) or not near(before["Y"], position["Y"]))
                )
                if xy:
                    if active_tool != 1 or not near(speed, 7000.0, 1e-3) or not near(feed, 700.0, 1e-3):
                        return False
                    t1_horizontal += 1
                plunge = (
                    motion == 1 and before["Z"] is not None and position["Z"] is not None
                    and position["Z"] < before["Z"] - 0.1
                    and before["X"] is not None and before["Y"] is not None
                    and near(before["X"], position["X"]) and near(before["Y"], position["Y"])
                )
                if plunge and active_tool == 2:
                    if not near(speed, 5000.0, 1e-3) or not near(feed, 180.0, 1e-3):
                        return False
                    drill_visits.append((position["X"], position["Y"]))
                if active_tool == 2 and not plunge:
                    return False
        if 80 in g_codes:
            active_cycle = None
            cycle = {}
        explicit_cycle = next((code for code in g_codes if code in {73, 81, 82, 83}), None)
        if explicit_cycle is not None:
            active_cycle = explicit_cycle
        cycle_motion = active_cycle is not None and (
            explicit_cycle is not None or any(axis in values for axis in ("X", "Y", "Z", "R"))
        )
        if cycle_motion:
            for axis in ("X", "Y", "Z", "R"):
                if axis in values:
                    cycle[axis] = values[axis][0]
            x = cycle.get("X", position["X"])
            y = cycle.get("Y", position["Y"])
            z = cycle.get("Z")
            retract = cycle.get("R")
            if (
                not spindle or active_tool != 2
                or not near(speed, 5000.0, 1e-3) or not near(feed, 180.0, 1e-3)
                or None in {x, y, z, retract} or z >= model_box.ZMax - 0.1
                or retract < stock_box.ZMax + 0.1
            ):
                return False
            drill_visits.append((x, y))
            position["X"], position["Y"] = x, y
            position["Z"] = retract
    matched = {
        point for point in drill_points
        if any(near(point[0], actual[0], 1e-3) and near(point[1], actual[1], 1e-3) for actual in drill_visits)
    }
    return terminated and not spindle and active_cycle is None and saw_m5 and t1_horizontal >= 5 and bool(matched)


def safe_post_arguments(value, processor):
    if len(value) > 500 or any(char in value for char in "\x00\r\n;&|`$<>"):
        return False
    try:
        tokens = shlex.split(value)
    except ValueError:
        return False
    flags = {"--no-comments", "--no-header", "--line-numbers", "--no-show-editor"}
    if processor == "linuxcnc":
        flags.add("--no-tlo")
    else:
        flags.update({"--translate_drill", "--tool-change"})
    seen = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        option, separator, inline = token.partition("=")
        if option in flags:
            if separator or option in seen:
                return False
        elif option == "--precision":
            if option in seen:
                return False
            if not separator:
                index += 1
                if index >= len(tokens):
                    return False
                inline = tokens[index]
            if not inline.isdigit() or not 0 <= int(inline) <= 8:
                return False
        else:
            return False
        seen.add(option)
        index += 1
    return True


def operation_path_signature(operation):
    result = []
    for command in operation.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        params = tuple(sorted((str(key).upper(), round(float(value), 4)) for key, value in command.Parameters.items()))
        result.append((name, params))
    return tuple(result)


def point_segment_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= 1e-12:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    factor = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator
    factor = max(0.0, min(1.0, factor))
    return math.hypot(point[0] - start[0] - factor * dx, point[1] - start[1] - factor * dy)


def arc_segments(start, finish, i_value, j_value, clockwise):
    center = (start[0] + i_value, start[1] + j_value)
    radius = math.hypot(start[0] - center[0], start[1] - center[1])
    if radius <= 1e-8 or abs(math.hypot(finish[0] - center[0], finish[1] - center[1]) - radius) > 0.05:
        return None
    first = math.atan2(start[1] - center[1], start[0] - center[0])
    last = math.atan2(finish[1] - center[1], finish[0] - center[0])
    if clockwise:
        while last >= first:
            last -= math.tau
    else:
        while last <= first:
            last += math.tau
    count = max(2, int(math.ceil(abs(last - first) * radius / 0.75)))
    points = [start]
    for index in range(1, count + 1):
        angle = first + (last - first) * index / count
        points.append((center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle)))
    points[-1] = finish
    return list(zip(points, points[1:]))


def toolpath_segments(operation):
    position = {"X": None, "Y": None, "Z": None}
    groups = []
    current = []
    current_z = None
    for command in operation.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        before = dict(position)
        for axis in position:
            if axis in command.Parameters:
                position[axis] = float(command.Parameters[axis])
        if name not in {"G1", "G2", "G3"} or None in (
            before["X"], before["Y"], before["Z"], position["X"], position["Y"], position["Z"]
        ):
            if current:
                groups.append((current_z, current))
                current, current_z = [], None
            continue
        changed_xy = (
            not near(before["X"], position["X"]) or not near(before["Y"], position["Y"])
        )
        level = position["Z"]
        if not changed_xy or not near(before["Z"], level, 1e-4):
            if current:
                groups.append((current_z, current))
                current, current_z = [], None
            continue
        start, finish = (before["X"], before["Y"]), (position["X"], position["Y"])
        if name == "G1":
            pieces = [(start, finish)]
        else:
            if "I" not in command.Parameters and "J" not in command.Parameters:
                return None
            pieces = arc_segments(
                start, finish, float(command.Parameters.get("I", 0.0)),
                float(command.Parameters.get("J", 0.0)), name == "G2",
            )
            if pieces is None:
                return None
        if current and (
            not near(current_z, level, 1e-4)
            or math.dist(current[-1][1], pieces[0][0]) > 0.05
        ):
            groups.append((current_z, current))
            current, current_z = [], None
        if not current:
            current_z = level
        current.extend(pieces)
    if current:
        groups.append((current_z, current))
    return groups


def active_native(operation, expected_module, expected_class, controller):
    return (
        module(operation) == expected_module and proxy_class(operation) == expected_class
        and operation.ToolController is controller and bool(operation.Active)
        and set(map(str, operation.State)) == {"Up-to-date"}
        and len(operation.Path.Commands) >= 4
    )


def valid_depths(operation, model_box, stock_box):
    try:
        start = float(operation.StartDepth.Value)
        final = float(operation.FinalDepth.Value)
        safe = float(operation.SafeHeight.Value)
        clearance = float(operation.ClearanceHeight.Value)
    except Exception:
        return False
    return (
        all(math.isfinite(value) for value in (start, final, safe, clearance))
        and model_box.ZMax - 0.1 <= start <= stock_box.ZMax + 0.1
        and final <= start + 1e-6 and final >= stock_box.ZMin - 10.0
        and safe > stock_box.ZMax + 0.1
        and clearance >= safe and clearance <= stock_box.ZMax + 100.0
    )


def validate_face(operation, controller, model_box, stock_box):
    if not active_native(operation, "Path.Op.MillFace", "ObjectFace", controller) or not valid_depths(operation, model_box, stock_box):
        return False
    final_depth = float(operation.FinalDepth.Value)
    if final_depth < model_box.ZMin - 1e-4 or final_depth > model_box.ZMax + 1e-4 or final_depth >= stock_box.ZMax - 0.1:
        return False
    groups = toolpath_segments(operation)
    if groups is None:
        return False
    segments = [segment for z_value, group in groups if near(z_value, final_depth, 0.0015) for segment in group]
    if len(segments) < 5:
        return False
    radius = 5.0
    xs = [point[0] for segment in segments for point in segment]
    ys = [point[1] for segment in segments for point in segment]
    overlap_x = max(0.0, min(max(xs) + radius, model_box.XMax) - max(min(xs) - radius, model_box.XMin))
    overlap_y = max(0.0, min(max(ys) + radius, model_box.YMax) - max(min(ys) - radius, model_box.YMin))
    near_material = 0
    for start, end in segments:
        for index in range(5):
            factor = index / 4.0
            x = start[0] + (end[0] - start[0]) * factor
            y = start[1] + (end[1] - start[1]) * factor
            if (
                model_box.XMin - radius <= x <= model_box.XMax + radius
                and model_box.YMin - radius <= y <= model_box.YMax + radius
            ):
                near_material += 1
                break
    return overlap_x * overlap_y >= 25.0 and near_material >= 3


def drilling_targets(operation, model, model_box, radius):
    points = []
    try:
        for base, names in list(operation.Base):
            if (
                base not in operation.Document.Objects
                or not tuple(names)
                or not hasattr(base, "Shape")
                or base.Shape.isNull()
                or not base.Shape.isValid()
            ):
                return None
            for name in names:
                sub = base.getSubObject(str(name))
                curve = getattr(sub, "Curve", None)
                if (
                    sub.isNull()
                    or str(sub.ShapeType) != "Edge"
                    or not sub.isClosed()
                    or not isinstance(curve, Part.Circle)
                ):
                    return None
                center = sub.CenterOfMass
                points.append((float(center.x), float(center.y)))
        for location in list(operation.Locations):
            points.append((float(location.x), float(location.y)))
    except Exception:
        return None
    unique = []
    for point in points:
        if not any(near(point[0], old[0], 1e-5) and near(point[1], old[1], 1e-5) for old in unique):
            unique.append(point)
    if not unique:
        return None
    for x, y in unique:
        dx = max(model_box.XMin - x, 0.0, x - model_box.XMax)
        dy = max(model_box.YMin - y, 0.0, y - model_box.YMax)
        if dx * dx + dy * dy >= radius * radius - 1e-8:
            return None
    return tuple(unique)


def validate_drilling(operation, controller, model, model_box, stock_box, radius, tip_length):
    if not active_native(operation, "Path.Op.Drilling", "ObjectDrilling", controller) or not valid_depths(operation, model_box, stock_box):
        return None
    points = drilling_targets(operation, model, model_box, radius)
    final_depth = float(operation.FinalDepth.Value)
    if points is None or final_depth >= model_box.ZMax - 0.1 or final_depth < stock_box.ZMin - 5.0:
        return None
    extra = str(operation.ExtraOffset)
    factors = {"None": 0.0, "Drill Tip": 1.0, "2x Drill Tip": 2.0}
    if extra not in factors:
        return None
    expected_z = final_depth - factors[extra] * tip_length
    if expected_z < stock_box.ZMin - 10.0:
        return None
    cycles = []
    for command in operation.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        if name not in {"G73", "G81", "G82", "G83"}:
            continue
        params = {str(key).upper(): float(value) for key, value in command.Parameters.items()}
        if (
            not {"X", "Y", "Z", "R"}.issubset(params)
            or not near(params["Z"], expected_z, 0.0015)
            or params["R"] < stock_box.ZMax + 0.1
        ):
            return None
        cycles.append((params["X"], params["Y"]))
    if not cycles:
        return None
    for point in points:
        if not any(near(point[0], actual[0], 1e-4) and near(point[1], actual[1], 1e-4) for actual in cycles):
            return None
    return points


def validate_profile(operation, controller, model, model_box, stock_box, tool_diameter):
    if not active_native(operation, "Path.Op.Profile", "ObjectProfile", controller) or not valid_depths(operation, model_box, stock_box):
        return False
    try:
        bases = list(operation.Base)
        for base, names in bases:
            if not tuple(names) or not hasattr(base, "Shape") or base.Shape.isNull() or not base.Shape.isValid():
                return False
            if any(base.getSubObject(str(name)).isNull() for name in names):
                return False
    except Exception:
        return False
    final_depth = float(operation.FinalDepth.Value)
    if final_depth >= model_box.ZMax - 0.1 or final_depth < stock_box.ZMin - 1.0:
        return False
    groups = toolpath_segments(operation)
    if groups is None:
        return False
    for z_value, segments in groups:
        if not near(z_value, final_depth, 0.0015) or len(segments) < 4:
            continue
        points = [segments[0][0]] + [segment[1] for segment in segments]
        for first in range(len(points) - 3):
            for last in range(first + 3, len(points)):
                if math.dist(points[first], points[last]) > 0.08:
                    continue
                loop = points[first:last + 1]
                xs, ys = zip(*loop)
                span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
                intersects = not (
                    max(xs) + tool_diameter / 2.0 < model_box.XMin
                    or min(xs) - tool_diameter / 2.0 > model_box.XMax
                    or max(ys) + tool_diameter / 2.0 < model_box.YMin
                    or min(ys) - tool_diameter / 2.0 > model_box.YMax
                )
                if intersects and max(span_x, span_y) >= 1.0:
                    return True
    return False


def validate_tools(doc, controllers, tools):
    by_number = {}
    for controller in controllers:
        try:
            number = int(controller.ToolNumber)
        except Exception:
            print("TASK_V06_DEBUG=tool-number-exception")
            return None
        if number in by_number:
            print("TASK_V06_DEBUG=duplicate-tool-number:%r" % (number,))
            return None
        by_number[number] = controller
    if not {1, 2}.issubset(by_number) or any(number <= 0 or number > 999 for number in by_number):
        print("TASK_V06_DEBUG=tool-numbers:%r" % (sorted(by_number),))
        return None
    linked_tools = []
    for controller in controllers:
        tool = getattr(controller, "Tool", None)
        if tool not in tools or tool in linked_tools or not valid_solid(tool.Shape):
            print("TASK_V06_DEBUG=extra-tool-link-or-shape:%r:%r" % (
                getattr(controller, "Name", None), getattr(tool, "Name", None)
            ))
            return None
        try:
            diameter = float(tool.Diameter.Value)
        except Exception:
            print("TASK_V06_DEBUG=extra-tool-diameter")
            return None
        if not math.isfinite(diameter) or not 0.0 < diameter <= 100.0:
            print("TASK_V06_DEBUG=extra-tool-diameter-range:%r" % (diameter,))
            return None
        linked_tools.append(tool)
    if set(linked_tools) != set(tools):
        print("TASK_V06_DEBUG=unlinked-toolbits")
        return None
    t1, t2 = by_number[1], by_number[2]
    tool1, tool2 = getattr(t1, "Tool", None), getattr(t2, "Tool", None)
    if tool1 not in tools or tool2 not in tools or tool1 is tool2:
        print("TASK_V06_DEBUG=tool-links:%r:%r:%r" % (getattr(tool1, "Name", None), getattr(tool2, "Name", None), [tool.Name for tool in tools]))
        return None
    try:
        feeds = (
            quantity_mm_per_minute(t1.HorizFeed), quantity_mm_per_minute(t1.VertFeed),
            quantity_mm_per_minute(t2.HorizFeed), quantity_mm_per_minute(t2.VertFeed),
        )
    except Exception:
        print("TASK_V06_DEBUG=feed-conversion")
        return None
    if (
        not near(t1.SpindleSpeed, 7000.0, 1e-3) or not near(t2.SpindleSpeed, 5000.0, 1e-3)
        or not near(feeds[0], 700.0, 1e-3) or not near(feeds[3], 180.0, 1e-3)
        or any(not math.isfinite(value) or value <= 0.0 for value in feeds)
        or str(t1.SpindleDir) not in {"Forward", "Reverse"}
        or str(t2.SpindleDir) not in {"Forward", "Reverse"}
    ):
        print("TASK_V06_DEBUG=controller-values:%r" % ({
            "t1_spindle": float(t1.SpindleSpeed), "t2_spindle": float(t2.SpindleSpeed),
            "feeds": feeds, "t1_dir": str(t1.SpindleDir), "t2_dir": str(t2.SpindleDir),
        },))
        return None
    t1_checks = (
        near(tool1.Diameter.Value, 10.0, 1e-4),
        str(tool1.ShapeName).strip().lower() == "endmill",
        secure_tool_template(tool1.BitShape, ENDMILL_SHAPE),
        flat_bottom_tool(tool1.Shape, 10.0),
    )
    if not all(t1_checks):
        print("TASK_V06_DEBUG=t1-tool:%r:%r" % (t1_checks, {
            "diameter": float(tool1.Diameter.Value), "shape_name": str(tool1.ShapeName),
            "bit_shape": str(tool1.BitShape), "bounds": bounds(tool1.Shape),
        }))
        return None
    t2_checks = (
        near(tool2.Diameter.Value, 5.0, 1e-4),
        str(tool2.ShapeName).strip().lower() == "drill",
        secure_tool_template(tool2.BitShape, DRILL_SHAPE),
        valid_solid(tool2.Shape),
        near(tool2.Shape.BoundBox.XLength, 5.0, 1e-3),
        near(tool2.Shape.BoundBox.YLength, 5.0, 1e-3),
    )
    if not all(t2_checks):
        print("TASK_V06_DEBUG=t2-tool:%r:%r" % (t2_checks, {
            "diameter": float(tool2.Diameter.Value), "shape_name": str(tool2.ShapeName),
            "bit_shape": str(tool2.BitShape), "bounds": bounds(tool2.Shape),
        }))
        return None
    try:
        diameter1 = float(tool1.Diameter.Value)
        shank1 = float(tool1.ShankDiameter.Value)
        cutting1 = float(tool1.CuttingEdgeHeight.Value)
        length1 = float(tool1.Length.Value)
        diameter2 = float(tool2.Diameter.Value)
        angle2 = float(tool2.TipAngle.Value)
        length2 = float(tool2.Length.Value)
    except Exception:
        print("TASK_V06_DEBUG=tool-shape-parameters")
        return None
    if (
        not 0.0 < shank1 <= 100.0 or not 0.0 < cutting1 <= length1 <= 500.0
        or not 60.0 <= angle2 <= 160.0 or not 10.0 <= length2 <= 500.0
    ):
        print("TASK_V06_DEBUG=tool-shape-parameter-range")
        return None
    expected1 = expected_tool_shape(doc, "ExpectedTaskV06T1", ENDMILL_SHAPE, {
        "Diameter": "%g mm" % diameter1,
        "ShankDiameter": "%g mm" % shank1,
        "CuttingEdgeHeight": "%g mm" % cutting1,
        "Length": "%g mm" % length1,
    })
    expected2 = expected_tool_shape(doc, "ExpectedTaskV06T2", DRILL_SHAPE, {
        "Diameter": "%g mm" % diameter2,
        "TipAngle": "%g deg" % angle2,
        "Length": "%g mm" % length2,
    })
    if not same_shape(tool1.Shape, expected1, 1e-4) or not same_shape(tool2.Shape, expected2, 1e-4):
        print("TASK_V06_DEBUG=tool-brep-mismatch")
        return None
    tip_length = (diameter2 / 2.0) / math.tan(math.radians(angle2 / 2.0))
    return t1, t2, tip_length


def validate_document(doc):
    jobs = [obj for obj in doc.Objects if module(obj) == "Path.Main.Job"]
    faces = [obj for obj in doc.Objects if module(obj) == "Path.Op.MillFace"]
    drills = [obj for obj in doc.Objects if module(obj) == "Path.Op.Drilling"]
    profiles = [obj for obj in doc.Objects if module(obj) == "Path.Op.Profile"]
    controllers = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Controller"]
    tools = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Bit"]
    if (
        len(jobs) != 1 or not faces or not drills or not profiles
        or not 2 <= len(controllers) <= 16 or len(tools) != len(controllers)
    ):
        print("TASK_V06_DEBUG=document-counts:%s" % ((len(jobs), len(faces), len(drills), len(profiles), len(controllers), len(tools)),))
        return None
    job = jobs[0]
    setup = getattr(job, "SetupSheet", None)
    if (
        setup not in doc.Objects or module(setup) != "Path.Base.SetupSheet"
        or proxy_class(setup) != "SetupSheet"
    ):
        print("TASK_V06_DEBUG=setup-sheet")
        return None
    if len(job.Model.Group) != 1:
        print("TASK_V06_DEBUG=model-group")
        return None
    model = job.Model.Group[0]
    if module(model) != "draftobjects.clone" or not box_like(model.Shape):
        print("TASK_V06_DEBUG=model-clone-or-shape")
        return None
    sources = list(getattr(model, "Objects", []))
    if len(sources) != 1 or not box_like(sources[0].Shape):
        print("TASK_V06_DEBUG=source-count-or-shape")
        return None
    expected_source = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, 0.0))
    if not (same_shape(sources[0].Shape, expected_source) or same_shape(model.Shape, expected_source)):
        source_box = sources[0].Shape.BoundBox
        model_box = model.Shape.BoundBox
        if not all(near(left, right, 1e-4) for left, right in zip(
            (source_box.XLength, source_box.YLength, source_box.ZLength),
            (model_box.XLength, model_box.YLength, model_box.ZLength),
        )):
            print("TASK_V06_DEBUG=source-model-congruence")
            return None
    stock = job.Stock
    if (
        module(stock) != "Path.Main.Stock"
        or proxy_class(stock) not in {"StockFromBase", "StockCreateBox", "StockCreateCylinder"}
        or not valid_solid(stock.Shape)
    ):
        print("TASK_V06_DEBUG=stock-native-or-shape")
        return None
    if model.Shape.cut(stock.Shape).Volume > 1e-4:
        print("TASK_V06_DEBUG=stock-containment:%s" % model.Shape.cut(stock.Shape).Volume)
        return None
    model_box, stock_box = model.Shape.BoundBox, stock.Shape.BoundBox
    if (
        stock.Shape.Volume > model.Shape.Volume * 50.0
        or stock_box.XLength > model_box.XLength * 5.0
        or stock_box.YLength > model_box.YLength * 5.0
        or stock_box.ZLength > model_box.ZLength * 5.0
    ):
        print("TASK_V06_DEBUG=stock-size")
        return None
    operations = list(job.Operations.Group)
    expected_ops = set(faces + drills + profiles)
    job_tools = list(job.Tools.Group)
    if (
        len(operations) != len(expected_ops) or set(operations) != expected_ops
        or len(job_tools) != len(controllers) or set(job_tools) != set(controllers)
    ):
        print("TASK_V06_DEBUG=job-groups")
        return None
    checked_tools = validate_tools(doc, controllers, tools)
    if checked_tools is None:
        print("TASK_V06_DEBUG=tools")
        return None
    t1, t2, drill_tip_length = checked_tools
    if any(operation.ToolController is not t1 for operation in faces + profiles) or any(operation.ToolController is not t2 for operation in drills):
        print("TASK_V06_DEBUG=operation-controller-binding")
        return None
    processor = str(job.PostProcessor).strip().lower()
    if (
        processor not in {"linuxcnc", "grbl"} or not safe_post_arguments(str(job.PostProcessorArgs), processor)
        or bool(job.SplitOutput)
        or os.path.normpath(str(job.PostProcessorOutputFile)) != "/home/user/Desktop/task-6.nc"
    ):
        print("TASK_V06_DEBUG=post-config:%r:%r" % (processor, str(job.PostProcessorArgs)))
        return None
    if processor == "grbl" and "--translate_drill" not in shlex.split(str(job.PostProcessorArgs)):
        print("TASK_V06_DEBUG=grbl-translate-drill")
        return None
    if not all(validate_face(operation, t1, model_box, stock_box) for operation in faces):
        print("TASK_V06_DEBUG=face")
        return None
    drill_sets = [
        validate_drilling(operation, t2, model, model_box, stock_box, 2.5, drill_tip_length)
        for operation in drills
    ]
    profile_valid = all(
        validate_profile(operation, t1, model, model_box, stock_box, 10.0)
        for operation in profiles
    )
    if any(points is None for points in drill_sets) or not profile_valid:
        print("TASK_V06_DEBUG=drill-or-profile:%r" % (drill_sets,))
        return None
    drill_points = tuple(point for points in drill_sets for point in points)
    relevant = [job, model, sources[0], stock, setup] + operations + controllers + tools
    if any(set(map(str, obj.State)) != {"Up-to-date"} for obj in relevant):
        print("TASK_V06_DEBUG=object-state:%r" % ([(obj.Name, list(map(str, obj.State))) for obj in relevant],))
        return None
    signatures = tuple(operation_path_signature(operation) for operation in operations)
    return job, processor, model_box, drill_points, signatures, relevant, stock_box


def validate(step_path, fcstd_path, nc_path, work_dir):
    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        print("TASK_V06_DEBUG=version:%r" % (App.Version(),))
        return False
    if hashlib.sha256(step_path.read_bytes()).hexdigest() != EXPECTED_STEP_SHA256:
        print("TASK_V06_DEBUG=step-hash")
        return False
    source = Part.read(str(step_path))
    expected = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, 0.0))
    if not same_shape(source, expected) or not box_like(source):
        print("TASK_V06_DEBUG=step-shape")
        return False
    submitted = code_signature(nc_path)
    if submitted is None:
        print("TASK_V06_DEBUG=submitted-parse")
        return False
    doc = App.openDocument(str(fcstd_path))
    try:
        doc.recompute()
        first = validate_document(doc)
        if first is None:
            print("TASK_V06_DEBUG=first-document")
            return False
        for obj in first[5]:
            obj.touch()
        doc.recompute()
        doc.recompute()
        second = validate_document(doc)
        if second is None or second[1] != first[1] or second[4] != first[4]:
            print("TASK_V06_DEBUG=second-document-or-path-stability")
            return False
        recomputed = pathlib.Path(work_dir) / "recomputed.FCStd"
        doc.saveAs(str(recomputed))
    finally:
        App.closeDocument(doc.Name)
    reopened = App.openDocument(str(recomputed))
    try:
        reopened.recompute()
        final = validate_document(reopened)
        if final is None or final[1] != second[1] or final[4] != second[4]:
            print("TASK_V06_DEBUG=final-document-or-path-stability")
            return False
        job, processor, model_box, drill_points = final[:4]
        stock_box = final[6]
        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1 or not sections[0][1]:
            print("TASK_V06_DEBUG=post-sections:%s" % len(sections))
            return False
        repost = pathlib.Path(work_dir) / "fresh-post.nc"
        post = PostProcessor.load(processor)
        if processor == "grbl":
            post.script.pythonopen = builtins.open
        post.export(sections[0][1], str(repost), str(job.PostProcessorArgs))
    finally:
        App.closeDocument(reopened.Name)
    fresh = code_signature(repost)
    checks = (
        fresh is not None,
        fresh is not None and submitted == fresh,
        validate_nc(submitted, model_box, stock_box, drill_points, processor),
        fresh is not None and validate_nc(fresh, model_box, stock_box, drill_points, processor),
    )
    if not all(checks):
        print("TASK_V06_DEBUG=nc-checks:%r" % (checks,))
    return all(checks)


try:
    ok = validate(
        pathlib.Path(os.environ["TASK_V06_STEP"]),
        pathlib.Path(os.environ["TASK_V06_FCSTD"]),
        pathlib.Path(os.environ["TASK_V06_NC"]),
        os.environ["TASK_V06_WORK"],
    )
except Exception as exc:
    print("TASK_V06_DEBUG=exception:%s:%s" % (type(exc).__name__, exc))
    ok = False
print("TASK_V06_RESULT=" + json.dumps({"ok": bool(ok)}, sort_keys=True))
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
        with tempfile.TemporaryDirectory(prefix="task_v06_eval_") as temporary:
            work = Path(temporary)
            step_copy, fcstd_copy, nc_copy = work / STEP_NAME, work / FCSTD_NAME, work / NC_NAME
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
                    "TASK_V06_STEP=" + str(step_copy),
                    "TASK_V06_FCSTD=" + str(fcstd_copy),
                    "TASK_V06_NC=" + str(nc_copy),
                    "TASK_V06_WORK=" + str(work),
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
    reports = [line[len(MARKER):] for line in completed.stdout.splitlines() if line.startswith(MARKER)]
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
