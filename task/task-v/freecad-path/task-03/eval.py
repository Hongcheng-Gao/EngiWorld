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
STEP_NAME = "drill_plate.step"
FCSTD_NAME = "task-3.FCStd"
NC_NAME = "task-3.nc"
EXPECTED_STEP_SHA256 = "9fda7becde0bd2ff39666e9ee082ff603de8569676844fd1c1f6d00489d79c74"
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".pyc", ".pyo", ".ipynb", ".sh", ".bash", ".zsh",
    ".bat", ".cmd", ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr", ".so", ".dll", ".dylib", ".exe",
}
REQUIRED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("draftobjects.clone", "Clone"): 1,
    ("Path.Tool.Controller", "ToolController"): 2,
    ("Path.Tool.Bit", "ToolBit"): 2,
    ("Path.Op.Drilling", "ObjectDrilling"): 2,
})
MARKER = "TASK_V03_RESULT="


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


def allowed_property_file(value: str) -> bool:
    if value in {"", "/home/user/Desktop/drill_plate.step", "/home/user/Desktop/task-3.nc"}:
        return True
    pure = PurePosixPath(value)
    tool_roots = (
        PurePosixPath("/usr/share/freecad/Mod/Path/Tools"),
        PurePosixPath("/usr/lib/freecad/Mod/Path/Tools"),
        PurePosixPath("/home/user/.local/share/FreeCAD/Mod/Path/Tools"),
        PurePosixPath("/home/user/.FreeCAD/Mod/Path/Tools"),
    )
    return (
        pure.is_absolute()
        and ".." not in pure.parts
        and "\x00" not in value
        and pure.suffix.lower() in {".fctb", ".fcstd"}
        and any(root in pure.parents for root in tool_roots)
    )


def fcstd_preflight(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [entry.filename for entry in infos]
            if not 1 <= len(infos) <= 128 or names.count("Document.xml") != 1 or len(names) != len(set(names)):
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
        proxies = Counter({key: count for key, count in proxies.items() if key[0] != "Path.Main.Stock"})
        if stock_count != 1 or proxies != REQUIRED_PROXIES:
            return False

        for prop in root.iter("Property"):
            if prop.attrib.get("type") != "App::PropertyFile":
                continue
            values = [child.attrib.get("value") for child in prop if child.tag == "String"]
            if len(values) != 1 or not allowed_property_file(values[0]):
                return False
        for element in root.iter():
            member = element.attrib.get("file")
            if member is None:
                continue
            if member not in names or PurePosixPath(member).suffix.lower() not in {"", ".brp", ".nc"}:
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
import Path.Tool.Bit as PathToolBit
from Path.Post.Processor import PostProcessor


EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256 = "9fda7becde0bd2ff39666e9ee082ff603de8569676844fd1c1f6d00489d79c74"
HOLES = {(-25.0, -15.0), (-25.0, 15.0), (25.0, -15.0), (25.0, 15.0)}
SOURCE_BOUNDS = (-60.0, 60.0, -40.0, 40.0, 0.0, 12.0)
MODEL_BOUNDS = (-60.0, 60.0, -40.0, 40.0, -12.0, 0.0)
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)", re.I)
ALLOWED_WORDS = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "R", "P", "Q", "L"}
ALLOWED_G = {0, 1, 17, 21, 40, 43, 49, 54, 64, 73, 80, 81, 82, 83, 90, 91.1, 94, 98, 99}
ALLOWED_M = {2, 3, 5, 6, 30}


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


def source_shape():
    shape = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, 0.0))
    for x_value, y_value in sorted(HOLES):
        shape = shape.cut(Part.makeCylinder(1.0, 0.25, App.Vector(x_value, y_value, 11.75)))
    return shape.removeSplitter()


def translated(shape, z_value):
    result = shape.copy()
    result.translate(App.Vector(0.0, 0.0, z_value))
    return result


def quantity_mm_per_minute(value):
    try:
        return float(value.getValueAs("mm/min").Value)
    except Exception:
        return float(value.Value) * 60.0


def expected_tool_shape(parent_doc, name, diameter, tip_angle, length):
    scratch = App.newDocument(name)
    try:
        tool = PathToolBit.Factory.CreateFromAttrs(
            {
                "version": 2,
                "name": name,
                "shape": "drill.fcstd",
                "parameter": {
                    "Diameter": "%g mm" % diameter,
                    "Length": "%g mm" % length,
                    "TipAngle": "%g deg" % tip_angle,
                },
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
    address_order = {letter: index for index, letter in enumerate("GMTHSFXYZRPQL")}
    for raw in executable.splitlines():
        line = raw.strip().upper()
        if not line or line == "%":
            continue
        words = []
        saw_line_number = False
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            letter = match.group(1).upper()
            value = float(match.group(2))
            if letter not in ALLOWED_WORDS or not math.isfinite(value):
                return None
            if letter == "N":
                saw_line_number = True
            else:
                if letter == "M" and near(value, 30.0):
                    value = 2.0
                value = 0.0 if abs(value) < 5e-7 else round(value, 6)
                words.append((letter, value))
            cursor = match.end()
        if line[cursor:].strip():
            return None
        if not words:
            if saw_line_number:
                continue
            return None
        words.sort(key=lambda word: (address_order[word[0]], word[1]))
        result.append(tuple(words))
    return tuple(result)


def integral(value):
    rounded = round(value)
    return int(rounded) if math.isfinite(value) and abs(value - rounded) <= 1e-8 else None


def validate_nc_execution(signature, spot_z, through_z):
    if not signature or signature[-1] != (("M", 2.0),):
        return False
    units = absolute = wcs = False
    position = {"X": None, "Y": None, "Z": None}
    tool = speed = feed = None
    spindle = False
    retract_mode = None
    terminated = False
    tool_changes = []
    visits = {1: [], 2: []}
    cancelled_after = {1: False, 2: False}
    current_cycle_tool = None
    active_cycle = None
    cycle_params = {}
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
            code = 91.1 if near(value, 91.1) else integral(value)
            if code not in ALLOWED_G:
                return False
            g_codes.append(code)
        m_codes = []
        for value in by_letter.get("M", []):
            code = integral(value)
            if code not in ALLOWED_M:
                return False
            m_codes.append(2 if code == 30 else code)
        if 21 in g_codes:
            units = True
        if 90 in g_codes:
            absolute = True
        if 54 in g_codes:
            wcs = True
        if 98 in g_codes:
            retract_mode = 98
        if 99 in g_codes:
            retract_mode = 99
        if 80 in g_codes and current_cycle_tool in {1, 2}:
            cancelled_after[current_cycle_tool] = True
            current_cycle_tool = None
            active_cycle = None
            cycle_params = {}
        if "T" in by_letter:
            candidate = integral(by_letter["T"][0])
            if candidate not in {1, 2}:
                return False
            tool = candidate
        if "S" in by_letter:
            speed = by_letter["S"][0]
        if "F" in by_letter:
            feed = by_letter["F"][0]
        if 5 in m_codes:
            spindle = False
        if 6 in m_codes:
            if spindle or tool not in {1, 2}:
                return False
            tool_changes.append(tool)
        if 3 in m_codes:
            if tool not in {1, 2} or speed is None:
                return False
            spindle = True
        if 2 in m_codes:
            if block_index != len(signature) - 1 or block != (("M", 2.0),):
                return False
            terminated = True
            continue

        if 0 in g_codes:
            active_cycle = None
            for axis in ("X", "Y", "Z"):
                if axis in by_letter:
                    position[axis] = by_letter[axis][0]
            if ("X" in by_letter or "Y" in by_letter) and (
                position["Z"] is None or position["Z"] < 0.5 - 1e-6
            ):
                return False
        if 1 in g_codes:
            before = dict(position)
            for axis in ("X", "Y", "Z"):
                if axis in by_letter:
                    position[axis] = by_letter[axis][0]
            if (
                ("X" in by_letter or "Y" in by_letter)
                and before["Z"] is not None
                and position["Z"] is not None
                and min(before["Z"], position["Z"]) <= 0.0
            ):
                return False

        explicit_cycle = next((code for code in g_codes if code in {73, 81, 82, 83}), None)
        if explicit_cycle is not None:
            active_cycle = explicit_cycle
        cycle = active_cycle if explicit_cycle is not None or (
            active_cycle is not None and any(axis in by_letter for axis in ("X", "Y", "Z", "R"))
        ) else None
        if cycle is not None:
            for axis in ("X", "Y", "Z", "R"):
                if axis in by_letter:
                    cycle_params[axis] = by_letter[axis][0]
            x_value = cycle_params.get("X", position["X"])
            y_value = cycle_params.get("Y", position["Y"])
            z_value = cycle_params.get("Z")
            r_value = cycle_params.get("R")
            if (
                not units
                or not absolute
                or not wcs
                or not spindle
                or tool not in {1, 2}
                or retract_mode not in {98, 99}
                or None in {x_value, y_value, z_value, r_value}
            ):
                return False
            if r_value < 0.5 - 1e-6:
                return False
            expected_speed = 8000.0 if tool == 1 else 5000.0
            expected_feed = 250.0 if tool == 1 else 180.0
            if not near(speed, expected_speed, 1e-3) or not near(feed, expected_feed, 1e-3):
                return False
            expected_z = spot_z if tool == 1 else through_z
            if not near(z_value, expected_z, 0.0015):
                return False
            point = (round(x_value, 6), round(y_value, 6))
            if point not in HOLES or point in visits[tool]:
                return False
            visits[tool].append(point)
            current_cycle_tool = tool
            position["X"] = x_value
            position["Y"] = y_value
            if retract_mode == 99 or position["Z"] is None:
                position["Z"] = r_value
    return (
        terminated
        and tool_changes == [1, 2]
        and set(visits[1]) == HOLES
        and set(visits[2]) == HOLES
        and cancelled_after == {1: True, 2: True}
    )


def target_points(operation, model):
    points = set()
    try:
        for base, names in list(operation.Base):
            if base is not model:
                return None
            for name in names:
                if not re.fullmatch(r"Edge\d+", str(name)):
                    return None
                edge = getattr(model.Shape, str(name))
                if not isinstance(edge.Curve, Part.Circle):
                    return None
                center = edge.Curve.Center
                if not near(center.z, 0.0) or not near(edge.Curve.Radius, 1.0):
                    return None
                points.add((round(float(center.x), 6), round(float(center.y), 6)))
        for location in list(operation.Locations):
            points.add((round(float(location.x), 6), round(float(location.y), 6)))
    except Exception:
        return None
    return points


def cycle_info(operation):
    result = []
    for command in operation.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        params = {str(key).upper(): float(value) for key, value in command.Parameters.items()}
        if name in {"G1", "G2", "G3"} and ("X" in params or "Y" in params):
            return None
        if name not in {"G73", "G81", "G82", "G83"}:
            continue
        if not {"X", "Y", "Z", "R"}.issubset(params):
            return None
        result.append((name, params))
    return result


def safe_post_arguments(value):
    return len(value) <= 500 and not any(char in value for char in "\x00\r\n;&|`$<>")


def validate_operation(operation, controller, model, is_spot, tip_length):
    if (
        module(operation) != "Path.Op.Drilling"
        or type(operation.Proxy).__name__ != "ObjectDrilling"
        or operation.ToolController is not controller
        or not bool(operation.Active)
        or list(operation.State) != ["Up-to-date"]
        or target_points(operation, model) != HOLES
        or not near(operation.StartDepth.Value, 0.0)
        or not math.isfinite(float(operation.FinalDepth.Value))
        or not math.isfinite(float(operation.RetractHeight.Value))
        or not math.isfinite(float(operation.SafeHeight.Value))
        or not math.isfinite(float(operation.ClearanceHeight.Value))
        or operation.RetractHeight.Value < 0.5
        or operation.SafeHeight.Value < 0.5
        or operation.ClearanceHeight.Value < operation.SafeHeight.Value
        or operation.ClearanceHeight.Value > 100.0
    ):
        return None
    if is_spot:
        if not -3.0 <= operation.FinalDepth.Value < -0.2501 or str(operation.ExtraOffset) != "None":
            return None
        expected_z = float(operation.FinalDepth.Value)
    else:
        if not near(operation.FinalDepth.Value, -13.0) or str(operation.ExtraOffset) != "Drill Tip":
            return None
        expected_z = -13.0 - tip_length
    info = cycle_info(operation)
    if info is None or len(info) != 4:
        return None
    points = set()
    for _name, params in info:
        point = (round(params["X"], 6), round(params["Y"], 6))
        if point in points or point not in HOLES or not near(params["Z"], expected_z, 1e-5) or params["R"] < 0.5:
            return None
        points.add(point)
    return expected_z if points == HOLES else None


def validate_document(doc):
    jobs = [obj for obj in doc.Objects if module(obj) == "Path.Main.Job"]
    drills = [obj for obj in doc.Objects if module(obj) == "Path.Op.Drilling"]
    controllers = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Controller"]
    tools = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Bit"]
    if len(jobs) != 1 or len(drills) != 2 or len(controllers) != 2 or len(tools) != 2:
        return None
    job = jobs[0]
    model_group = list(job.Model.Group)
    if len(model_group) != 1:
        return None
    model = model_group[0]
    expected_source = source_shape()
    expected_model = translated(expected_source, -12.0)
    if module(model) != "draftobjects.clone" or not same_shape(model.Shape, expected_model):
        return None
    sources = list(getattr(model, "Objects", []))
    if len(sources) != 1 or not (
        same_shape(sources[0].Shape, expected_source) or same_shape(sources[0].Shape, expected_model)
    ):
        return None
    if hasattr(sources[0], "SourceSHA256") and str(sources[0].SourceSHA256) != EXPECTED_STEP_SHA256:
        return None
    stock = job.Stock
    expected_stock = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, -12.0))
    if module(stock) != "Path.Main.Stock" or not same_shape(stock.Shape, expected_stock):
        return None
    if any(not near(actual, wanted) for actual, wanted in zip(bounds(model.Shape), MODEL_BOUNDS)):
        return None
    if list(job.Fixtures) != ["G54"] or bool(job.SplitOutput):
        return None
    if str(job.PostProcessor).strip().lower() != "linuxcnc" or not safe_post_arguments(str(job.PostProcessorArgs)):
        return None
    if os.path.normpath(str(job.PostProcessorOutputFile)) != "/home/user/Desktop/task-3.nc":
        return None

    operations = list(job.Operations.Group)
    controller_group = list(job.Tools.Group)
    if len(operations) != 2 or set(operations) != set(drills) or len(controller_group) != 2:
        return None
    spot, through = operations
    t1, t2 = controller_group
    tool1 = getattr(t1, "Tool", None)
    tool2 = getattr(t2, "Tool", None)
    if tool1 not in tools or tool2 not in tools or spot.ToolController is not t1 or through.ToolController is not t2:
        return None
    if (
        int(t1.ToolNumber) != 1
        or int(t2.ToolNumber) != 2
        or not near(t1.SpindleSpeed, 8000.0, 1e-3)
        or not near(t2.SpindleSpeed, 5000.0, 1e-3)
        or str(t1.SpindleDir) != "Forward"
        or str(t2.SpindleDir) != "Forward"
        or not near(quantity_mm_per_minute(t1.HorizFeed), 250.0, 1e-3)
        or not near(quantity_mm_per_minute(t1.VertFeed), 250.0, 1e-3)
        or not near(quantity_mm_per_minute(t2.HorizFeed), 180.0, 1e-3)
        or not near(quantity_mm_per_minute(t2.VertFeed), 180.0, 1e-3)
    ):
        return None
    try:
        diameter1 = float(tool1.Diameter.Value)
        angle1 = float(tool1.TipAngle.Value)
        length1 = float(tool1.Length.Value)
        diameter2 = float(tool2.Diameter.Value)
        angle2 = float(tool2.TipAngle.Value)
        length2 = float(tool2.Length.Value)
    except Exception:
        return None
    if (
        not 1.0 <= diameter1 <= 20.0
        or not near(angle1, 90.0, 1e-3)
        or not near(diameter2, 5.0, 1e-3)
        or not 60.0 <= angle2 <= 160.0
        or not 10.0 <= length1 <= 500.0
        or not 10.0 <= length2 <= 500.0
        or str(tool1.ShapeName).lower() != "drill"
        or str(tool2.ShapeName).lower() != "drill"
        or pathlib.Path(str(tool1.BitShape)).name.lower() != "drill.fcstd"
        or pathlib.Path(str(tool2.BitShape)).name.lower() != "drill.fcstd"
    ):
        return None
    expected_t1 = expected_tool_shape(doc, "ExpectedTaskV03T1", diameter1, angle1, length1)
    expected_t2 = expected_tool_shape(doc, "ExpectedTaskV03T2", diameter2, angle2, length2)
    if not same_shape(tool1.Shape, expected_t1, 1e-4) or not same_shape(tool2.Shape, expected_t2, 1e-4):
        return None
    tip_length = (diameter2 / 2.0) / math.tan(math.radians(angle2 / 2.0))
    spot_z = validate_operation(spot, t1, model, True, tip_length)
    through_z = validate_operation(through, t2, model, False, tip_length)
    if spot_z is None or through_z is None or abs(spot_z) > diameter1 / 2.0 + 0.05:
        return None
    return job, spot_z, through_z


def validate(step_path, fcstd_path, nc_path, work_dir):
    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        return False
    expected_source = source_shape()
    source = Part.read(str(step_path))
    if not same_shape(source, expected_source):
        return False
    if any(not near(actual, wanted) for actual, wanted in zip(bounds(source), SOURCE_BOUNDS)):
        return False

    submitted_signature = code_signature(nc_path)
    if submitted_signature is None:
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
        if second is None or not near(first[1], second[1]) or not near(first[2], second[2]):
            return False
        recomputed = pathlib.Path(work_dir) / "recomputed.FCStd"
        doc.saveAs(str(recomputed))
    finally:
        App.closeDocument(doc.Name)

    reopened = App.openDocument(str(recomputed))
    try:
        reopened.recompute()
        final = validate_document(reopened)
        if final is None or not near(second[1], final[1]) or not near(second[2], final[2]):
            return False
        job, spot_z, through_z = final
        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1 or not sections[0][1]:
            return False
        repost = pathlib.Path(work_dir) / "fresh-post.nc"
        PostProcessor.load("linuxcnc").export(sections[0][1], str(repost), str(job.PostProcessorArgs))
    finally:
        App.closeDocument(reopened.Name)

    repost_signature = code_signature(repost)
    return (
        repost_signature is not None
        and validate_nc_execution(submitted_signature, spot_z, through_z)
        and validate_nc_execution(repost_signature, spot_z, through_z)
        and submitted_signature == repost_signature
    )


try:
    ok = validate(
        pathlib.Path(os.environ["TASK_V03_STEP"]),
        pathlib.Path(os.environ["TASK_V03_FCSTD"]),
        pathlib.Path(os.environ["TASK_V03_NC"]),
        os.environ["TASK_V03_WORK"],
    )
except Exception:
    ok = False
print("TASK_V03_RESULT=" + json.dumps({"ok": bool(ok)}, sort_keys=True))
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
        with tempfile.TemporaryDirectory(prefix="task_v03_eval_") as temporary:
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
                    "TASK_V03_STEP=" + str(step_copy),
                    "TASK_V03_FCSTD=" + str(fcstd_copy),
                    "TASK_V03_NC=" + str(nc_copy),
                    "TASK_V03_WORK=" + str(work),
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
