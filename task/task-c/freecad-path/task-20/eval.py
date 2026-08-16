from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path, PurePosixPath


TARGET = Path("/home/user/Desktop")
STEP = TARGET / "final_benchmark.step"
PARAMS = TARGET / "params.json"
FCSTD = TARGET / "task-20.FCStd"
NC = TARGET / "task-20.nc"
POST_LOG = TARGET / "post_log.txt"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_STEP_SHA256 = "259a0d5d6d7836c0b361b994b4f6f766a54787ade9f7b5e84b9d9173e983751e"
EXPECTED_PARAMS_SHA256 = "9eceee889093cdb2c5bf98397521ba1421c0da1fd4f61a4ec7005ac51ffcd232"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J", "R", "P", "Q"}
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 81, 82, 83, 90, 94, 98, 99}
ALLOWED_M = {2, 3, 5, 6, 8, 9, 30}
EXPECTED_HOLES = {
    (x, y)
    for y in (-32.0, -16.0)
    for x in (-70.0, -50.0, -30.0, -10.0, 10.0, 30.0, 50.0, 70.0)
} | {(-78.0, 38.0), (78.0, 38.0)}
REQUIRED_PROXIES = Counter(
    {
        ("Path.Main.Job", "ObjectJob"): 1,
        ("Path.Base.SetupSheet", "SetupSheet"): 1,
        ("draftobjects.clone", "Clone"): 1,
        ("Path.Tool.Controller", "ToolController"): 5,
        ("Path.Tool.Bit", "ToolBit"): 5,
        ("Path.Op.MillFace", "ObjectFace"): 1,
        ("Path.Op.PocketShape", "ObjectPocket"): 3,
        ("Path.Op.Drilling", "ObjectDrilling"): 1,
        ("Path.Op.Helix", "ObjectHelix"): 1,
        ("Path.Op.Surface", "ObjectSurface"): 1,
        ("Path.Op.Profile", "ObjectProfile"): 1,
    }
)


def fail(message):
    print("task-20 evaluator: " + message, file=sys.stderr)
    return False


def close(left, right, tolerance=1e-6):
    try:
        a, b = float(left), float(right)
    except (TypeError, ValueError):
        return False
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance


def regular_file(path, minimum, maximum):
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not path.is_symlink() and minimum <= info.st_size <= maximum


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze_file(source, target, minimum, maximum):
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
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
        stable = (
            before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns
        ) == (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
        )
        data = b"".join(chunks)
        if not stable or len(data) != before.st_size:
            return False
        target.write_bytes(data)
        target.chmod(0o600)
        return True
    except OSError:
        return False


def validate_params(path):
    if not regular_file(path, 1_000, 100_000) or sha256(path) != EXPECTED_PARAMS_SHA256:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    try:
        return (
            data["task"] == "task-20"
            and data["version"] == "0.21.2"
            and data["wcs"] == "G54"
            and len(data["pockets"]) == 3
            and data["ordinary_through_holes"]["count"] == 16
            and len(data["counterbores"]) == 2
            and len(data["fixtures"]) == 4
            and len(data["tools"]) == 5
            and len(data["operations"]) == 8
            and data["postprocessor"] == "linuxcnc"
        )
    except (KeyError, TypeError):
        return False


def allowed_property_file(value):
    if value in {"", "/home/user/Desktop/task-20.nc"}:
        return True
    pure = PurePosixPath(value)
    return (
        pure.is_absolute()
        and ".." not in pure.parts
        and pure.suffix.lower() in {".fcstd", ".fctb"}
        and (
            value.startswith("/usr/share/freecad/Mod/Path/Tools/")
            or value.startswith("/usr/lib/freecad/Mod/Path/Tools/")
        )
    )


def validate_archive(path):
    if not regular_file(path, 20_000, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "Document.xml" not in names or len(names) != len(set(names)) or len(names) > 250:
                return False
            total = 0
            for entry in archive.infolist():
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
                    or pure.suffix.lower() in {".py", ".pyc", ".pyo", ".sh", ".so", ".dll", ".dylib", ".exe"}
                ):
                    return False
                total += entry.file_size
                if total > 80_000_000:
                    return False
            root = ET.fromstring(archive.read("Document.xml"))
            proxies = Counter()
            for element in root.iter("Python"):
                module_name = element.attrib.get("module")
                class_name = element.attrib.get("class")
                encoded = element.attrib.get("encoded")
                value = element.attrib.get("value")
                if encoded != "yes" or not isinstance(value, str) or len(value) > 100_000:
                    return False
                payload = json.loads(base64.b64decode(value, validate=True).decode("utf-8"))
                if (module_name, class_name) == ("draftobjects.clone", "Clone"):
                    if not isinstance(payload, str):
                        return False
                elif (module_name, class_name) == (None, None):
                    if payload is not None:
                        return False
                elif payload is not None and not isinstance(payload, dict):
                    return False
                proxies[(module_name, class_name)] += 1
            # A no-code FeaturePython object with a null Proxy is inert metadata,
            # not part of the native CAM contract.  Do not require or reject it.
            proxies.pop((None, None), None)
            stock_count = proxies.pop(("Path.Main.Stock", "StockFromBase"), 0)
            stock_count += proxies.pop(("Path.Main.Stock", "StockCreateBox"), 0)
            if stock_count != 1:
                return False
            if proxies != REQUIRED_PROXIES:
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
                if not member or member not in names or PurePosixPath(member).suffix.lower() not in {".brp", ".nc"}:
                    return False
            return True
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError):
        return False


def strip_comments(text):
    output = []
    in_comment = False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        code = []
        for char in line:
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
                code.append(char)
        output.append("".join(code))
    return None if in_comment else "\n".join(output)


def integral(value):
    rounded = round(value)
    return int(rounded) if math.isfinite(value) and abs(value - rounded) <= 1e-9 else None


def parse_nc(path):
    try:
        executable = strip_comments(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    if executable is None:
        return None
    blocks = []
    for raw in executable.splitlines():
        line = raw.strip().upper()
        if not line or line == "%":
            continue
        words = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            value = float(match.group(2))
            if not math.isfinite(value):
                return None
            words.append((match.group(1), value))
            cursor = match.end()
        if line[cursor:].strip() or not words:
            return None
        if any(letter not in ALLOWED_ADDRESSES for letter, _ in words):
            return None
        if any(sum(letter == address for letter, _ in words) > 1 for address in ALLOWED_ADDRESSES - {"G", "M"}):
            return None
        blocks.append(words)
    return blocks or None


def validate_nc(path):
    if not regular_file(path, 8_000, 2_000_000):
        return False
    blocks = parse_nc(path)
    if blocks is None:
        return False
    state = {
        "units": None, "absolute": False, "plane": None, "wcs": None,
        "tool": None, "changed": False, "spindle": False, "speed": None,
        "feed": None, "cycle": None, "X": None, "Y": None, "Z": None,
    }
    saw_m5 = False
    ended = False
    changed_tools = []
    cycles = []
    cuts = {number: [] for number in range(1, 6)}
    for index, block in enumerate(blocks):
        words = dict(block)
        gs = [integral(value) for letter, value in block if letter == "G"]
        ms = [integral(value) for letter, value in block if letter == "M"]
        if ended or any(code is None or code not in ALLOWED_G for code in gs) or any(code is None or code not in ALLOWED_M for code in ms):
            return False
        if 21 in gs:
            state["units"] = "mm"
        if 17 in gs:
            state["plane"] = "XY"
        if 90 in gs:
            state["absolute"] = True
        if 54 in gs:
            state["wcs"] = 54
        if 80 in gs:
            state["cycle"] = None
        if "T" in words:
            tool = integral(words["T"])
            if tool not in range(1, 6):
                return False
            state["tool"] = tool
            state["changed"] = False
        if "H" in words and integral(words["H"]) != state["tool"]:
            return False
        if "S" in words:
            if not close(words["S"], 7000.0):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if state["units"] != "mm" or not close(words["F"], 500.0, 0.01):
                return False
            state["feed"] = words["F"]
        if 5 in ms:
            state["spindle"] = False
            saw_m5 = True
        if 6 in ms:
            if not saw_m5 or state["spindle"] or state["tool"] not in range(1, 6) or state["cycle"] is not None:
                return False
            state["changed"] = True
            changed_tools.append(state["tool"])
            saw_m5 = False
        if 3 in ms:
            if not state["changed"] or state["speed"] is None:
                return False
            state["spindle"] = True
        before = (state["X"], state["Y"], state["Z"])
        for axis in ("X", "Y", "Z"):
            if axis in words:
                state[axis] = words[axis]
        motion = next((code for code in gs if code in {0, 1, 2, 3}), None)
        cycle = next((code for code in gs if code in {81, 82, 83}), None)
        if motion == 0 and ("X" in words or "Y" in words) and (state["Z"] is None or state["Z"] < -0.001):
            safe_helix_centering = (
                state["tool"] == 4
                and state["Z"] is not None
                and state["Z"] >= -4.001
                and close(state["Y"], 38.0, 0.01)
                and min(abs(state["X"] + 78.0), abs(state["X"] - 78.0)) <= 1.01
                and before[0] is not None
                and before[1] is not None
                and close(before[1], 38.0, 0.01)
                and min(abs(before[0] + 78.0), abs(before[0] - 78.0)) <= 1.01
            )
            if not safe_helix_centering:
                return False
        if cycle is not None:
            state["cycle"] = cycle
            if state["tool"] != 3 or not state["spindle"] or "X" not in words or "Y" not in words or "Z" not in words or "R" not in words:
                return False
            if words["Z"] > -20.0 + 1e-6 or not close(words["R"], 2.0, 0.01):
                return False
            cycles.append((round(words["X"], 4), round(words["Y"], 4), words["Z"]))
            state["Z"] = words["R"]
        elif motion in {1, 2, 3} and any(axis in words for axis in ("X", "Y", "Z")):
            if state["cycle"] is not None or not state["spindle"] or not state["changed"] or state["feed"] is None:
                return False
            if state["units"] != "mm" or not state["absolute"] or state["plane"] != "XY" or state["wcs"] != 54:
                return False
            if any(state[axis] is None for axis in ("X", "Y", "Z")):
                return False
            if motion in {2, 3} and not all(letter in words for letter in ("I", "J")):
                return False
            cuts[state["tool"]].append((state["X"], state["Y"], state["Z"], motion, before, words))
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"] or state["cycle"] is not None:
                return False
            ended = True
    if not ended or changed_tools != [1, 2, 3, 4, 5, 2]:
        return False
    if len(cycles) != 18 or {(x, y) for x, y, _ in cycles} != EXPECTED_HOLES:
        return False
    if len({round(z, 3) for _, _, z in cycles}) != 1:
        return False
    face = cuts[1]
    if len(face) < 30 or min(p[0] for p in face) > -90.1 or max(p[0] for p in face) < 90.1 or any(abs(p[2]) > 0.001 for p in face):
        return False
    for cx, floor in ((-55.0, -4.0), (0.0, -6.0), (55.0, -8.0)):
        hits = [p for p in cuts[2] if close(p[2], floor, 0.01) and cx - 14 <= p[0] <= cx + 14 and 7 <= p[1] <= 23]
        if len(hits) < 8:
            return False
    profile = [p for p in cuts[2] if close(p[2], -18.0, 0.01)]
    if len(profile) < 8 or not close(min(p[0] for p in profile), -94.0, 0.05) or not close(max(p[0] for p in profile), 94.0, 0.05) or not close(min(p[1] for p in profile), -54.0, 0.05) or not close(max(p[1] for p in profile), 54.0, 0.05):
        return False
    helix = cuts[4]
    if len(helix) < 12 or min(p[2] for p in helix) > -3.999 or not all(36.9 <= p[1] <= 39.1 for p in helix):
        return False
    if not any(p[0] < -77 for p in helix) or not any(p[0] > 77 for p in helix):
        return False
    surface = [p for p in cuts[5] if close(p[2], -0.5, 0.01)]
    if len(surface) < 6 or min(p[0] for p in surface) > -18.0 or max(p[0] for p in surface) < 18.0 or min(p[1] for p in surface) > 36.6 or max(p[1] for p in surface) < 39.4:
        return False
    return True


def validate_post_log(path, step_path, fcstd_path, nc_path):
    if not regular_file(path, 800, 100_000):
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    lowered = text.lower()
    if (
        not re.search(r"0\D+21\D+2\D+33771", text)
        or "b9bfa5c5507506e4515816414cd27f4851d00489" not in lowered
        or "linuxcnc" not in lowered
        or "g54" not in lowered
        or not re.search(r"(?:operation(?:_count| count)?|operations)\D{0,12}8\b", lowered)
        or lowered.count("show editor = 0") < 2
        or lowered.count("postprocessing...") < 2
        or lowered.count("done postprocessing.") < 2
        or "reopen" not in lowered
        or "recompute" not in lowered
        or "repost" not in lowered
        or "up-to-date" not in lowered
        or not re.search(r"(?:warning|error)[^\n]{0,30}\b0\b", lowered)
    ):
        return False
    modules = ["MillFace", "PocketShape", "PocketShape", "PocketShape", "Drilling", "Helix", "Surface", "Profile"]
    if any(lowered.count("path.op." + name.lower()) < modules.count(name) for name in set(modules)):
        return False
    expected_hashes = {
        "NC": sha256(nc_path),
        "FCStd": sha256(fcstd_path),
        "STEP": sha256(step_path),
    }
    for label, digest in expected_hashes.items():
        pattern = r"(?i)\b{}\b[^\n]{{0,30}}\bsha[-_ ]?256\b[^0-9a-f]{{0,12}}([0-9a-f]{{64}})".format(label)
        matches = re.findall(pattern, text)
        if digest not in [value.lower() for value in matches]:
            return False
    return True


CHILD_SOURCE = r'''
import builtins
import json
import math
import os
import pathlib
import re
import sys
import traceback

builtins.pythonopen = open

import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor

VERSION = ("0", "21", "2", "33771 (Git)")
COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
POCKETS = (
    ("Pocket1", -55.0, 15.0, 34.0, 24.0, 4.0, 4.0),
    ("Pocket2", 0.0, 15.0, 34.0, 24.0, 4.0, 6.0),
    ("Pocket3", 55.0, 15.0, 34.0, 24.0, 4.0, 8.0),
)
HOLES = tuple((x, y) for y in (-32.0, -16.0) for x in (-70.0, -50.0, -30.0, -10.0, 10.0, 30.0, 50.0, 70.0)) + ((-78.0, 38.0), (78.0, 38.0))
FIXTURES = (
    (-112.0, -102.0, -40.0, -20.0, -2.0, 4.0),
    (-112.0, -102.0, 20.0, 40.0, -2.0, 4.0),
    (102.0, 112.0, -40.0, -20.0, -2.0, 4.0),
    (102.0, 112.0, 20.0, 40.0, -2.0, 4.0),
)
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(r"([A-Z])\s*(" + NUMBER + r")", re.ASCII)


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def close(a, b, tolerance=1e-6):
    try:
        left, right = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def module(obj):
    proxy = getattr(obj, "Proxy", None)
    return type(proxy).__module__ if proxy is not None else ""


def bounds(shape):
    box = shape.BoundBox
    return (box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax)


def same_shape(left, right, tolerance=1e-4):
    try:
        return left.isValid() and right.isValid() and len(left.Solids) == len(right.Solids) == 1 and left.cut(right).Volume <= tolerance and right.cut(left).Volume <= tolerance
    except Exception:
        return False


def rounded_prism(cx, cy, length, width, radius, zmin, height):
    pieces = [
        Part.makeBox(length - 2 * radius, width, height, App.Vector(cx - length / 2 + radius, cy - width / 2, zmin)),
        Part.makeBox(length, width - 2 * radius, height, App.Vector(cx - length / 2, cy - width / 2 + radius, zmin)),
    ]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            pieces.append(Part.makeCylinder(radius, height, App.Vector(cx + sx * (length / 2 - radius), cy + sy * (width / 2 - radius), zmin)))
    result = pieces[0]
    for piece in pieces[1:]:
        result = result.fuse(piece)
    return result.removeSplitter()


def expected_shape():
    shape = Part.makeBox(180.0, 100.0, 18.0, App.Vector(-90.0, -50.0, -18.0))
    for _, cx, cy, length, width, radius, depth in POCKETS:
        shape = shape.cut(rounded_prism(cx, cy, length, width, radius, -depth, depth))
    for x, y in HOLES:
        shape = shape.cut(Part.makeCylinder(2.5, 20.0, App.Vector(x, y, -19.0)))
    for x, y in ((-78.0, 38.0), (78.0, 38.0)):
        shape = shape.cut(Part.makeCylinder(6.0, 4.0, App.Vector(x, y, -4.0)))
    shape = shape.cut(Part.makeBox(44.0, 10.0, 0.5, App.Vector(-22.0, 33.0, -0.5)))
    return shape.removeSplitter()


def selected_face(op):
    try:
        base = list(op.Base)
        if len(base) != 1 or len(base[0][1]) != 1:
            return None
        obj, names = base[0]
        name = names[0]
        if obj is None or not name.startswith("Face"):
            return None
        return obj.Shape.getElement(name)
    except Exception:
        return None


def motion_records(op):
    position = {"X": None, "Y": None, "Z": None}
    records = []
    for command in op.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        before = dict(position)
        for axis in position:
            if axis in command.Parameters:
                position[axis] = float(command.Parameters[axis])
        if name in {"G0", "G1", "G2", "G3", "G81", "G82", "G83"}:
            records.append((name, before, dict(position), {key: float(value) for key, value in command.Parameters.items()}))
    return records


def operation_signature(op):
    result = []
    for command in op.Path.Commands:
        params = tuple(sorted((str(key), 0.0 if abs(float(value)) < 0.0000005 else round(float(value), 6)) for key, value in command.Parameters.items()))
        result.append((str(command.Name).upper().replace(" ", ""), params))
    return tuple(result)


def path_bounds(op, names={"G0", "G1", "G2", "G3", "G81", "G82", "G83"}):
    points = [record[2] for record in motion_records(op) if record[0] in names and all(record[2][axis] is not None for axis in ("X", "Y", "Z"))]
    check(points, op.Name + " has no motion points")
    return tuple((min(point[axis] for point in points), max(point[axis] for point in points)) for axis in ("X", "Y", "Z"))


def strip_comments(text):
    result = []
    active = False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        code = []
        for char in line:
            if active:
                if char == "(":
                    return None
                if char == ")":
                    active = False
            elif char == "(":
                active = True
            elif char == ")":
                return None
            elif char == ";":
                break
            else:
                code.append(char)
        result.append("".join(code))
    return None if active else "\n".join(result)


def code_signature(path):
    try:
        text = strip_comments(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None
    if text is None:
        return None
    result = []
    for raw in text.splitlines():
        line = raw.strip().upper()
        if not line or line == "%":
            continue
        words = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            if match.group(1) != "N":
                value = float(match.group(2))
                value = 0.0 if abs(value) < 0.0000005 else round(value, 6)
                words.append((match.group(1), value))
            cursor = match.end()
        if line[cursor:].strip() or not words:
            return None
        if words == [("M", 30.0)]:
            words = [("M", 2.0)]
        result.append(tuple(words))
    return tuple(result)


def point_rect_distance(point, rect):
    x, y = point
    xmin, xmax, ymin, ymax = rect
    dx = max(xmin - x, 0.0, x - xmax)
    dy = max(ymin - y, 0.0, y - ymax)
    return math.hypot(dx, dy)


def point_segment_distance(point, a, b):
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx * dx + dy * dy <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def segment_rect_distance(a, b, rect):
    xmin, xmax, ymin, ymax = rect
    if (min(a[0], b[0]) <= xmax and max(a[0], b[0]) >= xmin and min(a[1], b[1]) <= ymax and max(a[1], b[1]) >= ymin):
        # Exact clipping for an axis-aligned rectangle.
        t0, t1 = 0.0, 1.0
        dx, dy = b[0] - a[0], b[1] - a[1]
        for p, q in ((-dx, a[0] - xmin), (dx, xmax - a[0]), (-dy, a[1] - ymin), (dy, ymax - a[1])):
            if abs(p) < 1e-15:
                if q < 0:
                    break
            else:
                r = q / p
                if p < 0:
                    t0 = max(t0, r)
                else:
                    t1 = min(t1, r)
        else:
            if t0 <= t1:
                return 0.0
    corners = ((xmin, ymin), (xmin, ymax), (xmax, ymin), (xmax, ymax))
    return min(point_rect_distance(a, rect), point_rect_distance(b, rect), *(point_segment_distance(corner, a, b) for corner in corners))


def validate(step_path, fcstd_path, nc_path, log_path, repost_a, repost_b, resaved):
    check(tuple(App.Version()[:4]) == VERSION and App.Version()[-1] == COMMIT, "wrong FreeCAD version")
    expected = expected_shape()
    check(expected.isValid() and len(expected.Solids) == 1 and close(expected.Volume, 310244.0 - 2551.0 * math.pi, 1e-4), "internal expected shape failed")
    submitted_step = Part.read(str(step_path))
    check(same_shape(submitted_step, expected), "STEP BRep mismatch")
    check(all(close(a, b) for a, b in zip(bounds(submitted_step), (-90, 90, -50, 50, -18, 0))), "STEP bounds mismatch")

    doc = App.openDocument(str(fcstd_path))
    try:
        jobs = [obj for obj in doc.Objects if module(obj) == "Path.Main.Job"]
        controllers = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Controller"]
        tools = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Bit"]
        check(len(jobs) == 1 and len(controllers) == 5 and len(tools) == 5, "Job/tool count mismatch")
        job = jobs[0]
        operations = list(job.Operations.Group)
        expected_modules = ["Path.Op.MillFace", "Path.Op.PocketShape", "Path.Op.PocketShape", "Path.Op.PocketShape", "Path.Op.Drilling", "Path.Op.Helix", "Path.Op.Surface", "Path.Op.Profile"]
        check([module(op) for op in operations] == expected_modules, "operation order/type mismatch")
        check([int(op.ToolController.ToolNumber) for op in operations] == [1, 2, 2, 2, 3, 4, 5, 2], "operation/tool mapping mismatch")
        log_text = pathlib.Path(log_path).read_text(encoding="utf-8")
        remaining_log_lines = list(log_text.splitlines())
        for op in operations:
            expected_module = module(op).lower()
            expected_tool = "t%d" % int(op.ToolController.ToolNumber)
            expected_commands = str(len(op.Path.Commands))
            matching_indexes = [
                index
                for index, line in enumerate(remaining_log_lines)
                if expected_module in line.lower()
                and re.search(r"\b" + re.escape(expected_tool) + r"\b", line, re.IGNORECASE)
                and "up-to-date" in line.lower()
                and re.search(r"(?:command(?:s|_count| count)?)\D{0,12}" + re.escape(expected_commands) + r"\b", line, re.IGNORECASE)
            ]
            check(matching_indexes, "post log does not match native operation " + op.Name)
            remaining_log_lines.pop(matching_indexes[0])
        check(not any(
            re.search(r"\bPath\.Op\.[A-Za-z0-9_]+\b", line, re.IGNORECASE)
            and re.search(r"\bT[1-5]\b", line, re.IGNORECASE)
            and "up-to-date" in line.lower()
            and re.search(r"(?:command(?:s|_count| count)?)\D{0,12}\d+\b", line, re.IGNORECASE)
            for line in remaining_log_lines
        ), "post log contains an extra operation row")
        check(len(job.Model.Group) == 1 and list(job.Fixtures) == ["G54"] and str(job.PostProcessor).lower() == "linuxcnc" and not bool(job.SplitOutput), "Job setup mismatch")
        check(os.path.normpath(str(job.PostProcessorOutputFile)) == "/home/user/Desktop/task-20.nc", "post output path mismatch")
        model = job.Model.Group[0]
        check(module(model) == "draftobjects.clone" and same_shape(model.Shape, expected), "Job model mismatch")
        check(all(close(a, b) for a, b in zip(bounds(model.Shape), (-90, 90, -50, 50, -18, 0))), "Job model moved")
        check(same_shape(job.Stock.Shape, Part.makeBox(190, 110, 19, App.Vector(-95, -55, -18))), "stock shape mismatch")
        check(all(close(a, b) for a, b in zip(bounds(job.Stock.Shape), (-95, 95, -55, 55, -18, 1))), "stock bounds mismatch")
        by_number = {int(tc.ToolNumber): tc for tc in controllers}
        specs = {1: ("endmill", 20.0), 2: ("endmill", 8.0), 3: ("drill", 5.0), 4: ("endmill", 10.0), 5: ("ballend", 6.0)}
        check(set(by_number) == set(specs), "tool numbers mismatch")
        for number, (shape_name, diameter) in specs.items():
            controller = by_number[number]
            tool = controller.Tool
            check(tool in tools and sum(other.Tool == tool for other in controllers) == 1, "shared/missing tool")
            check(close(tool.Diameter, diameter) and str(tool.ShapeName).lower() == shape_name and os.path.basename(str(tool.BitShape)).lower() == shape_name + ".fcstd", "tool geometry fields mismatch")
            check(close(controller.SpindleSpeed, 7000) and str(controller.SpindleDir) == "Forward", "controller spindle mismatch")
            check(close(controller.HorizFeed.getValueAs("mm/min").Value, 500) and close(controller.VertFeed.getValueAs("mm/min").Value, 500), "controller feed mismatch")
            if shape_name == "drill":
                check(close(tool.TipAngle, 118), "drill angle mismatch")
            tool.touch()
        doc.recompute()
        check(all(tool.Shape.isValid() and len(tool.Shape.Solids) == 1 and tool.Shape.Volume > 0 for tool in tools), "invalid ToolBit shape")

        expected_fixture_bounds = sorted(FIXTURES)
        fixture_objects = []
        for obj in doc.Objects:
            shape = getattr(obj, "Shape", None)
            try:
                actual = tuple(round(value, 6) for value in bounds(shape))
                if actual in expected_fixture_bounds:
                    xmin, xmax, ymin, ymax, zmin, zmax = actual
                    expected_fixture = Part.makeBox(
                        xmax - xmin,
                        ymax - ymin,
                        zmax - zmin,
                        App.Vector(xmin, ymin, zmin),
                    )
                else:
                    expected_fixture = None
                if expected_fixture is not None and same_shape(shape, expected_fixture):
                    fixture_objects.append(obj)
            except Exception:
                pass
        check(len(fixture_objects) == 4, "fixture count mismatch")
        actual_fixture_bounds = sorted(tuple(round(v, 6) for v in bounds(obj.Shape)) for obj in fixture_objects)
        check(actual_fixture_bounds == expected_fixture_bounds, "fixture geometry mismatch")

        face, pocket1, pocket2, pocket3, drilling, helix, surface, profile = operations
        top = selected_face(face)
        check(top is not None and type(top.Surface).__name__ == "Plane" and close(top.BoundBox.ZMin, 0) and close(face.StartDepth, 1) and close(face.FinalDepth, 0), "Face setup mismatch")
        check(close(face.StepDown, 1) and close(face.StepOver, 60), "Face parameters mismatch")
        fb = path_bounds(face)
        check(fb[0][0] <= -90.1 and fb[0][1] >= 90.1 and fb[1][0] <= -50.1 and fb[1][1] >= 50.1 and fb[2][0] >= -0.001, "Face path coverage mismatch")

        for op, spec in zip((pocket1, pocket2, pocket3), POCKETS):
            _, cx, cy, length, width, radius, depth = spec
            floor = selected_face(op)
            check(floor is not None and type(floor.Surface).__name__ == "Plane" and close(floor.CenterOfMass.x, cx, 1e-4) and close(floor.CenterOfMass.y, cy, 1e-4) and close(floor.BoundBox.ZMin, -depth), "pocket Base mismatch")
            check(close(op.StartDepth, 0) and close(op.FinalDepth, -depth) and close(op.StepDown, 2) and close(op.StepOver, 50), "pocket parameters mismatch")
            pb = path_bounds(op)
            check(close(pb[2][0], -depth, 0.01) and pb[0][0] <= cx - 12.9 and pb[0][1] >= cx + 12.9 and pb[1][0] <= 7.01 and pb[1][1] >= 22.99, "pocket path mismatch")

        check(close(drilling.StartDepth, 0) and close(drilling.FinalDepth, -20) and close(drilling.RetractHeight, 2) and str(drilling.ExtraOffset) == "Drill Tip" and not bool(drilling.KeepToolDown), "drilling parameters mismatch")
        location_set = {(round(v.x, 4), round(v.y, 4)) for v in drilling.Locations}
        check(len(drilling.Locations) == 18 and location_set == set(HOLES), "drilling Locations mismatch")
        drill_records = [record for record in motion_records(drilling) if record[0] in {"G81", "G82", "G83"}]
        check(len(drill_records) == 18 and {(round(r[2]["X"], 4), round(r[2]["Y"], 4)) for r in drill_records} == set(HOLES), "drilling cycle mismatch")
        expected_tip_z = -20.0 - 2.5 / math.tan(math.radians(59.0))
        check(all(close(record[3].get("Z"), expected_tip_z, 1e-5) and close(record[3].get("R"), 2, 1e-5) for record in drill_records), "drill tip depth mismatch")

        check(close(helix.StartDepth, 0) and close(helix.FinalDepth, -4) and close(helix.StepDown, 2), "Helix parameters mismatch")
        hbase = list(helix.Base)
        selected_helix_edges = []
        for base_object, names in hbase:
            for name in names:
                try:
                    edge = base_object.Shape.getElement(name)
                    curve = edge.Curve
                    selected_helix_edges.append((round(curve.Center.x, 4), round(curve.Center.y, 4), float(curve.Radius)))
                except Exception:
                    selected_helix_edges.append((None, None, None))
        check(
            len(selected_helix_edges) == 2
            and {(x, y) for x, y, _ in selected_helix_edges} == {(-78.0, 38.0), (78.0, 38.0)}
            and all(close(radius, 6.0, 1e-5) for _, _, radius in selected_helix_edges),
            "Helix Base mismatch",
        )
        arcs = [record for record in motion_records(helix) if record[0] in {"G2", "G3"}]
        centers = []
        for name, before, after, params in arcs:
            if before["X"] is not None and before["Y"] is not None and "I" in params and "J" in params:
                centers.append((round(before["X"] + params["I"], 4), round(before["Y"] + params["J"], 4), after["Z"], before["Z"], math.hypot(params["I"], params["J"])))
        helix_centers = {(-78.0, 38.0), (78.0, 38.0)}
        check(len(arcs) >= 12 and {(x, y) for x, y, _, _, _ in centers} == helix_centers, "Helix path centers mismatch")
        for center in helix_centers:
            records = [record for record in centers if record[:2] == center]
            check(
                records
                and all(close(record[4], 1.0, 0.01) for record in records)
                and min(record[2] for record in records) <= -4 + 1e-6
                and any(record[3] is not None and record[2] < record[3] - 1e-6 for record in records),
                "Helix radius/depth mismatch",
            )

        sf = selected_face(surface)
        check(sf is not None and type(sf.Surface).__name__ == "Plane" and all(close(a, b, 1e-5) for a, b in zip(bounds(sf), (-22, 22, 33, 43, -0.5, -0.5))), "Surface Base mismatch")
        check(str(surface.ScanType) == "Planar" and str(surface.CutPattern) == "ZigZag" and str(surface.LayerMode) == "Single-pass", "Surface mode mismatch")
        check(close(surface.StartDepth, 0) and close(surface.SampleInterval, 1) and close(surface.DepthOffset, 0) and close(surface.StepOver, 25) and close(surface.FinalDepth, -0.5), "Surface parameters mismatch")
        sb = path_bounds(surface)
        check(close(sb[2][0], -0.5, 0.01) and -22.01 <= sb[0][0] <= -18 and 18 <= sb[0][1] <= 22.01 and 32.99 <= sb[1][0] <= 36.51 and 39.49 <= sb[1][1] <= 43.01, "Surface path mismatch")

        check(str(profile.Side) == "Outside" and str(profile.Direction) == "CW" and bool(profile.UseComp) and bool(profile.processPerimeter) and not bool(profile.processHoles) and not bool(profile.processCircles), "Profile mode mismatch")
        check(close(profile.StartDepth, 0) and close(profile.FinalDepth, -18) and close(profile.StepDown, 3), "Profile depth mismatch")
        profile_records = motion_records(profile)
        final_points = [r[2] for r in profile_records if r[0] in {"G1", "G2", "G3"} and r[2]["Z"] is not None and close(r[2]["Z"], -18, 0.01)]
        check(len(final_points) >= 8 and close(min(p["X"] for p in final_points), -94, 0.05) and close(max(p["X"] for p in final_points), 94, 0.05) and close(min(p["Y"] for p in final_points), -54, 0.05) and close(max(p["Y"] for p in final_points), 54, 0.05), "Profile path mismatch")
        segments = []
        for name, before, after, params in profile_records:
            if name == "G1" and before["X"] is not None and before["Y"] is not None and after["X"] is not None and after["Y"] is not None and math.hypot(after["X"] - before["X"], after["Y"] - before["Y"]) > 1e-7:
                segments.append(((before["X"], before["Y"]), (after["X"], after["Y"])))
        clearances = []
        for fixture in FIXTURES:
            rect = fixture[:4]
            centerline = min(segment_rect_distance(a, b, rect) for a, b in segments)
            clearances.append(centerline - 4.0)
        check(all(close(value, 4.0, 0.02) and value >= 3.0 - 1e-6 for value in clearances), "fixture swept clearance mismatch")
        check(all(close(op.SafeHeight, 5) and close(op.ClearanceHeight, 8) for op in operations), "operation safe/clearance heights mismatch")
        check(all(float(op.ClearanceHeight.Value) - 4.0 >= 3.0 for op in operations), "vertical fixture clearance mismatch")

        before_signatures = [operation_signature(op) for op in operations]
        check(all(list(op.State) == ["Up-to-date"] and len(op.Path.Commands) > 0 for op in operations), "pre-recompute state/path mismatch")
        for obj in controllers + operations + [job]:
            obj.touch()
        doc.recompute()
        doc.recompute()
        after_signatures = [operation_signature(op) for op in operations]
        check(before_signatures == after_signatures and all(list(op.State) == ["Up-to-date"] for op in operations), "recompute changed paths")
        sections = PathPostCommand.buildPostList(job)
        check(len(sections) == 1, "split post output")
        PostProcessor.load("linuxcnc").export(sections[0][1], str(repost_a), job.PostProcessorArgs)
        doc.saveAs(str(resaved))
    finally:
        App.closeDocument(doc.Name)

    reopened = App.openDocument(str(resaved))
    try:
        reopened.recompute()
        reopened.recompute()
        job = next(obj for obj in reopened.Objects if module(obj) == "Path.Main.Job")
        operations = list(job.Operations.Group)
        check([module(op) for op in operations] == ["Path.Op.MillFace", "Path.Op.PocketShape", "Path.Op.PocketShape", "Path.Op.PocketShape", "Path.Op.Drilling", "Path.Op.Helix", "Path.Op.Surface", "Path.Op.Profile"], "reopen operation mismatch")
        check(all(list(op.State) == ["Up-to-date"] and len(op.Path.Commands) > 0 for op in operations), "reopen path state mismatch")
        sections = PathPostCommand.buildPostList(job)
        check(len(sections) == 1, "reopen split post")
        PostProcessor.load("linuxcnc").export(sections[0][1], str(repost_b), job.PostProcessorArgs)
    finally:
        App.closeDocument(reopened.Name)
    submitted = code_signature(nc_path)
    check(submitted is not None and submitted == code_signature(repost_a) == code_signature(repost_b), "fresh repost mismatch")
    return True


ok = False
try:
    ok = validate(
        pathlib.Path(os.environ["TASK20_STEP"]),
        pathlib.Path(os.environ["TASK20_FCSTD"]),
        pathlib.Path(os.environ["TASK20_NC"]),
        pathlib.Path(os.environ["TASK20_LOG"]),
        pathlib.Path(os.environ["TASK20_REPOST_A"]),
        pathlib.Path(os.environ["TASK20_REPOST_B"]),
        pathlib.Path(os.environ["TASK20_RESAVED"]),
    )
except Exception as error:
    print("task-20 child: %s" % error, file=sys.stderr)
    traceback.print_exc()
pathlib.Path(os.environ["TASK20_RESULT"]).write_text(json.dumps({"ok": bool(ok)}, sort_keys=True), encoding="utf-8")
raise SystemExit(0 if ok else 1)
'''


def validate_freecad(step_path, fcstd_path, nc_path, log_path, workdir):
    child = workdir / "validate_task20.py"
    result_file = workdir / "result.json"
    child.write_text(CHILD_SOURCE, encoding="utf-8")
    child.chmod(0o600)
    env = {
        "HOME": str(workdir), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": "/usr/bin:/bin", "TMPDIR": str(workdir),
        "TASK20_STEP": str(step_path), "TASK20_FCSTD": str(fcstd_path), "TASK20_NC": str(nc_path),
        "TASK20_LOG": str(log_path),
        "TASK20_REPOST_A": str(workdir / "repost-a.nc"), "TASK20_REPOST_B": str(workdir / "repost-b.nc"),
        "TASK20_RESAVED": str(workdir / "resaved.FCStd"), "TASK20_RESULT": str(result_file),
    }
    try:
        result = subprocess.run(
            [str(FREECADCMD), str(child)], cwd=workdir, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300,
            check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        payload = None
    if result.returncode != 0 or payload != {"ok": True}:
        if result.stderr:
            print(result.stderr[-6000:], file=sys.stderr)
        return False
    return all(regular_file(workdir / name, 8_000 if name.endswith(".nc") else 20_000, 20_000_000) for name in ("repost-a.nc", "repost-b.nc", "resaved.FCStd"))


def main():
    if not FREECADCMD.is_file():
        return fail("freecadcmd missing")
    if not regular_file(STEP, 10_000, 5_000_000) or sha256(STEP) != EXPECTED_STEP_SHA256:
        return fail("wrong init STEP")
    if not validate_params(PARAMS):
        return fail("wrong params.json")
    if not validate_archive(FCSTD):
        return fail("invalid FCStd archive")
    if not validate_nc(NC):
        return fail("invalid NC semantics")
    if not validate_post_log(POST_LOG, STEP, FCSTD, NC):
        return fail("invalid post log")
    with tempfile.TemporaryDirectory(prefix="task-20-eval-") as directory:
        workdir = Path(directory)
        frozen = {
            "step": (STEP, workdir / "final_benchmark.step", 10_000, 5_000_000),
            "params": (PARAMS, workdir / "params.json", 1_000, 100_000),
            "fcstd": (FCSTD, workdir / "task-20.FCStd", 20_000, 20_000_000),
            "nc": (NC, workdir / "task-20.nc", 8_000, 2_000_000),
            "log": (POST_LOG, workdir / "post_log.txt", 800, 100_000),
        }
        for name, (source, target, minimum, maximum) in frozen.items():
            if not freeze_file(source, target, minimum, maximum):
                return fail("could not freeze " + name)
        if sha256(frozen["step"][1]) != EXPECTED_STEP_SHA256 or not validate_params(frozen["params"][1]):
            return fail("init changed during evaluation")
        if not validate_archive(frozen["fcstd"][1]) or not validate_nc(frozen["nc"][1]):
            return fail("GT changed during evaluation")
        if not validate_post_log(frozen["log"][1], frozen["step"][1], frozen["fcstd"][1], frozen["nc"][1]):
            return fail("log changed during evaluation")
        if not validate_freecad(frozen["step"][1], frozen["fcstd"][1], frozen["nc"][1], frozen["log"][1], workdir):
            return fail("FreeCAD validation failed")
    return True


if __name__ == "__main__":
    try:
        result = main()
    except Exception as error:
        print("task-20 evaluator exception: " + str(error), file=sys.stderr)
        result = False
    print(True if result else False)
