from __future__ import annotations

import base64
import csv
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
STEP = TARGET / "complex_pockets.step"
CSV_FILE = TARGET / "tool_candidates.csv"
FCSTD = TARGET / "task-19.FCStd"
NC = TARGET / "task-19.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_CSV_SHA256 = "1fe9ef157b2642a50dd0140e50acb6f889f226fff1b9b54078eb5f3ff698c366"
EXPECTED_STEP_SHA256 = "a013a4fe398f51898129934d04c3024f4c01b9c48abf50a1f526c91e7845775e"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_TOOLS = {
    1: ("end mill", 16.0, 7000.0, 500.0, 4),
    2: ("drill", 14.0, 7000.0, 500.0, 4),
    3: ("drill", 12.0, 7000.0, 500.0, 4),
    4: ("end mill", 10.0, 7000.0, 500.0, 4),
    5: ("end mill", 8.0, 7000.0, 500.0, 4),
}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {
    "N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J", "R", "P", "Q"
}
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 81, 82, 83, 90, 94, 98, 99}
ALLOWED_M = {2, 3, 5, 6, 8, 9, 30}
G_MODAL_GROUPS = (
    {0, 1, 2, 3, 80, 81, 82, 83},
    {17},
    {21},
    {40},
    {43, 49},
    {54},
    {90},
    {94},
    {98, 99},
)
REQUIRED_PROXIES = Counter(
    {
        ("Path.Main.Job", "ObjectJob"): 1,
        ("Path.Base.SetupSheet", "SetupSheet"): 1,
        ("Path.Main.Stock", "StockFromBase"): 1,
        ("draftobjects.clone", "Clone"): 1,
        ("Path.Tool.Controller", "ToolController"): 5,
        ("Path.Tool.Bit", "ToolBit"): 5,
        ("Path.Op.PocketShape", "ObjectPocket"): 5,
        ("Path.Op.Drilling", "ObjectDrilling"): 2,
        ("Path.Op.Profile", "ObjectProfile"): 1,
    }
)
POCKET_NC_SPECS = (
    (-48.0, 18.0, 18.0, -4.0, 1),
    (-24.0, 18.0, 16.0, -5.0, 4),
    (0.0, 18.0, 14.0, -6.0, 4),
    (24.0, 18.0, 12.0, -7.0, 4),
    (48.0, 18.0, 10.0, -8.0, 5),
)
EXPECTED_HOLES = {
    2: {(x, 27.0) for x in (-50.0, -30.0, -10.0, 10.0, 30.0, 50.0)},
    3: {(x, -27.0) for x in (-50.0, -30.0, -10.0, 10.0, 30.0, 50.0)},
}


def fail(message):
    print("task-19 evaluator: " + message, file=sys.stderr)
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
    return (
        stat.S_ISREG(info.st_mode)
        and not path.is_symlink()
        and minimum <= info.st_size <= maximum
    )


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
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) == (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        data = b"".join(chunks)
        if not stable or len(data) != before.st_size:
            return False
        target.write_bytes(data)
        target.chmod(0o600)
        return True
    except OSError:
        return False


def validate_csv(path):
    if not regular_file(path, 100, 10_000) or sha256(path) != EXPECTED_CSV_SHA256:
        return False
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != [
                "tool_number", "type", "diameter", "spindle", "feed", "operation_count"
            ]:
                return False
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error):
        return False
    if len(rows) != 5:
        return False
    found = {}
    try:
        for row in rows:
            if set(row) != set(reader.fieldnames) or any(value is None for value in row.values()):
                return False
            number = int(row["tool_number"])
            if number in found:
                return False
            found[number] = (
                row["type"].strip().lower(),
                float(row["diameter"]),
                float(row["spindle"]),
                float(row["feed"]),
                int(row["operation_count"]),
            )
    except (TypeError, ValueError):
        return False
    return found == EXPECTED_TOOLS


def allowed_property_file(value):
    if value in {"", "/home/user/Desktop/task-19.nc"}:
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
                    or pure.suffix.lower()
                    in {".py", ".pyc", ".pyo", ".sh", ".so", ".dll", ".dylib", ".exe"}
                ):
                    return False
                total += entry.file_size
                if total > 80_000_000:
                    return False
            root = ET.fromstring(archive.read("Document.xml"))
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
        ET.ParseError,
        json.JSONDecodeError,
    ):
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
            if line[cursor : match.start()].strip():
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
        if any(
            sum(letter == address for letter, _ in words) > 1
            for address in ALLOWED_ADDRESSES - {"G", "M"}
        ):
            return None
        blocks.append(words)
    return blocks or None


def validate_nc(path):
    if not regular_file(path, 5_000, 2_000_000):
        return False
    blocks = parse_nc(path)
    if blocks is None:
        return False
    state = {
        "units": None,
        "absolute": False,
        "plane": None,
        "wcs": None,
        "motion": None,
        "cycle": None,
        "cycle_z": None,
        "cycle_r": None,
        "retract": None,
        "tool": None,
        "changed": False,
        "speed": None,
        "feed": None,
        "spindle": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    ended = False
    saw_m5 = False
    changed_tools = []
    spindle_tools = set()
    cutting_tools = set()
    cycles = []
    cuts = {number: [] for number in EXPECTED_TOOLS}
    for index, block in enumerate(blocks):
        words = dict(block)
        gs = [integral(value) for letter, value in block if letter == "G"]
        ms = [integral(value) for letter, value in block if letter == "M"]
        if ended:
            return False
        if any(code is None or code not in ALLOWED_G for code in gs):
            return False
        if any(code is None or code not in ALLOWED_M for code in ms):
            return False
        if any(sum(code in group for code in gs) > 1 for group in G_MODAL_GROUPS):
            return False
        terminators = [code for code in ms if code in {2, 30}]
        if (
            len(ms) != len(set(ms))
            or len(terminators) > 1
            or (terminators and len(ms) != 1)
        ):
            return False
        if 21 in gs:
            state["units"] = "mm"
        if 17 in gs:
            state["plane"] = "XY"
        if 90 in gs:
            state["absolute"] = True
        if 54 in gs:
            state["wcs"] = 54
        if 98 in gs:
            state["retract"] = 98
        if 99 in gs:
            state["retract"] = 99
        for code in gs:
            if code in {0, 1, 2, 3}:
                state["motion"] = code
            if code in {81, 82, 83}:
                state["cycle"] = code
            elif code == 80:
                state["cycle"] = None
                state["cycle_z"] = None
                state["cycle_r"] = None
        if "T" in words:
            tool = integral(words["T"])
            if tool not in EXPECTED_TOOLS:
                return False
            if tool != state["tool"]:
                state["changed"] = False
            state["tool"] = tool
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
            if (
                len(ms) != 1
                or not saw_m5
                or state["spindle"]
                or state["tool"] not in EXPECTED_TOOLS
                or state["cycle"] is not None
            ):
                return False
            state["changed"] = True
            changed_tools.append(state["tool"])
            saw_m5 = False
        if 3 in ms:
            if (
                state["tool"] not in EXPECTED_TOOLS
                or not state["changed"]
                or state["speed"] is None
            ):
                return False
            state["spindle"] = True
            spindle_tools.add(state["tool"])

        before = (state["X"], state["Y"], state["Z"])
        for axis in ("X", "Y", "Z"):
            if axis in words:
                state[axis] = words[axis]
        explicit_motion = next((code for code in gs if code in {0, 1, 2, 3}), None)
        explicit_cycle = next((code for code in gs if code in {81, 82, 83}), None)
        has_axis = any(axis in words for axis in ("X", "Y", "Z"))
        if explicit_motion == 0 and ("X" in words or "Y" in words):
            if state["Z"] is None or state["Z"] < 2.0 - 1e-6:
                return False
        if explicit_cycle is not None:
            if "Z" not in words or "R" not in words:
                return False
            state["cycle_z"] = words["Z"]
            state["cycle_r"] = words["R"]
            if explicit_cycle == 82 and ("P" not in words or words["P"] < 0):
                return False
            if explicit_cycle == 83 and ("Q" not in words or words["Q"] <= 0):
                return False
        cycle_visit = (
            state["cycle"] in {81, 82, 83}
            and state["tool"] in {2, 3}
            and (explicit_cycle is not None or "X" in words or "Y" in words)
            and explicit_motion is None
            and 80 not in gs
        )
        if cycle_visit:
            if (
                not state["spindle"]
                or not state["changed"]
                or state["feed"] is None
                or state["units"] != "mm"
                or not state["absolute"]
                or state["plane"] != "XY"
                or state["wcs"] != 54
                or state["X"] is None
                or state["Y"] is None
                or state["cycle_z"] is None
                or state["cycle_r"] is None
                or state["retract"] != 98
                or state["cycle_z"] > -19.0 + 1e-6
                or not 1.9 <= state["cycle_r"] <= 5.1
            ):
                return False
            cycles.append(
                (
                    state["tool"],
                    round(state["X"], 4),
                    round(state["Y"], 4),
                    round(state["cycle_z"], 4),
                )
            )
            cutting_tools.add(state["tool"])
            state["Z"] = before[2] if state["retract"] == 98 else state["cycle_r"]
        elif has_axis and state["motion"] in {1, 2, 3} and explicit_motion != 0:
            if state["cycle"] is not None:
                return False
            if (
                state["tool"] not in {1, 4, 5}
                or not state["spindle"]
                or not state["changed"]
                or state["feed"] is None
                or state["units"] != "mm"
                or not state["absolute"]
                or state["plane"] != "XY"
                or state["wcs"] != 54
                or any(state[axis] is None for axis in ("X", "Y", "Z"))
                or not (-68.1 <= state["X"] <= 68.1)
                or not (-48.1 <= state["Y"] <= 48.1)
                or not (-18.001 <= state["Z"] <= 5.001)
            ):
                return False
            if state["motion"] in {2, 3} and not all(letter in words for letter in ("I", "J")):
                return False
            cuts[state["tool"]].append(
                (state["X"], state["Y"], state["Z"], state["motion"], before)
            )
            cutting_tools.add(state["tool"])
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"] or state["cycle"] is not None:
                return False
            ended = True

    if not ended or set(changed_tools) != set(EXPECTED_TOOLS):
        return False
    if spindle_tools != set(EXPECTED_TOOLS) or cutting_tools != set(EXPECTED_TOOLS):
        return False
    if len(cycles) != 12:
        return False
    for tool in (2, 3):
        tool_cycles = [item for item in cycles if item[0] == tool]
        if len(tool_cycles) != 6:
            return False
        if {(item[1], item[2]) for item in tool_cycles} != EXPECTED_HOLES[tool]:
            return False
        depths = {item[3] for item in tool_cycles}
        if len(depths) != 1 or not -25.0 <= next(iter(depths)) <= -19.0:
            return False
    for cx, length, width, floor, tool in POCKET_NC_SPECS:
        hits = [
            point
            for point in cuts[tool]
            if close(point[2], floor, 0.01)
            and cx - length / 2.0 - 0.05 <= point[0] <= cx + length / 2.0 + 0.05
            and -width / 2.0 - 0.05 <= point[1] <= width / 2.0 + 0.05
        ]
        if len(hits) < 2:
            return False
    profile = [point for point in cuts[1] if close(point[2], -18.0, 0.01)]
    if len(profile) < 8:
        return False
    px = [point[0] for point in profile]
    py = [point[1] for point in profile]
    if not (
        close(min(px), -68.0, 0.05)
        and close(max(px), 68.0, 0.05)
        and close(min(py), -48.0, 0.05)
        and close(max(py), 48.0, 0.05)
    ):
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
from collections import Counter

builtins.pythonopen = open

import FreeCAD as App
import Import
import Part
import Path.Post.Command as PathPostCommand
import Path.Tool.Bit as PathToolBit
from Path.Post.Processor import PostProcessor

EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
POCKETS = (
    ("P1", -48.0, 18.0, 18.0, 8.5, 4.0, 1, 16.0),
    ("P2", -24.0, 18.0, 16.0, 6.0, 5.0, 4, 10.0),
    ("P3", 0.0, 18.0, 14.0, 6.0, 6.0, 4, 10.0),
    ("P4", 24.0, 18.0, 12.0, 5.5, 7.0, 4, 10.0),
    ("P5", 48.0, 18.0, 10.0, 4.5, 8.0, 5, 8.0),
)
HOLE_X = (-50.0, -30.0, -10.0, 10.0, 30.0, 50.0)
EXPECTED_HOLES = {2: {(x, 27.0) for x in HOLE_X}, 3: {(x, -27.0) for x in HOLE_X}}
CODE_WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")


def close(a, b, tolerance=1e-6):
    try:
        left, right = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


def module(obj):
    return getattr(getattr(obj, "Proxy", None).__class__, "__module__", "")


def same_shape(left, right, tolerance=1e-4):
    return (
        left.isValid()
        and right.isValid()
        and left.cut(right).Volume <= tolerance
        and right.cut(left).Volume <= tolerance
    )


def rounded_prism(cx, cy, length, width, radius, zmin, height):
    parts = []
    if length - 2.0 * radius > 1e-9:
        parts.append(
            Part.makeBox(
                length - 2.0 * radius,
                width,
                height,
                App.Vector(cx - length / 2.0 + radius, cy - width / 2.0, zmin),
            )
        )
    if width - 2.0 * radius > 1e-9:
        parts.append(
            Part.makeBox(
                length,
                width - 2.0 * radius,
                height,
                App.Vector(cx - length / 2.0, cy - width / 2.0 + radius, zmin),
            )
        )
    centers = {
        (cx + sx * (length / 2.0 - radius), cy + sy * (width / 2.0 - radius))
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
    }
    parts.extend(
        Part.makeCylinder(radius, height, App.Vector(x, y, zmin))
        for x, y in sorted(centers)
    )
    result = parts[0]
    for part in parts[1:]:
        result = result.fuse(part)
    return result.removeSplitter()


def expected_source_shape():
    shape = Part.makeBox(120.0, 80.0, 18.0, App.Vector(-60.0, -40.0, 0.0))
    for _, x, length, width, radius, depth, _, _ in POCKETS:
        shape = shape.cut(rounded_prism(x, 0.0, length, width, radius, 18.0 - depth, depth))
    for x in HOLE_X:
        shape = shape.cut(Part.makeCylinder(7.0, 18.0, App.Vector(x, 27.0, 0.0)))
        shape = shape.cut(Part.makeCylinder(6.0, 18.0, App.Vector(x, -27.0, 0.0)))
    return shape.removeSplitter()


def translated(shape, z):
    result = shape.copy()
    result.translate(App.Vector(0.0, 0.0, z))
    return result


def horizontal_floor(op, model):
    try:
        base = list(op.Base)
        if len(base) != 1 or base[0][0] != model:
            return None
        names = list(base[0][1])
        if len(names) != 1 or not re.fullmatch(r"Face\d+", str(names[0])):
            return None
        face = getattr(model.Shape, str(names[0]))
        if type(face.Surface).__name__ != "Plane":
            return None
        box = face.BoundBox
        if not close(box.ZMin, box.ZMax):
            return None
        return face
    except (AttributeError, TypeError, ValueError):
        return None


def rounded_contains(x, y, cx, length, width, radius, shrink=0.0, tolerance=1e-6):
    hx = length / 2.0 - shrink
    hy = width / 2.0 - shrink
    rr = radius - shrink
    if hx <= 0.0 or hy <= 0.0 or rr < -tolerance:
        return False
    rr = max(0.0, rr)
    qx = max(abs(x - cx) - max(0.0, hx - rr), 0.0)
    qy = max(abs(y) - max(0.0, hy - rr), 0.0)
    return qx * qx + qy * qy <= (rr + tolerance) * (rr + tolerance)


def sample_motion(op, spacing=0.35):
    position = {"X": None, "Y": None, "Z": None}
    samples = []
    motions = 0
    for command in op.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        before = dict(position)
        for axis in position:
            if axis in command.Parameters:
                position[axis] = float(command.Parameters[axis])
        if name not in {"G0", "G1", "G2", "G3"}:
            continue
        motions += 1
        if name == "G0":
            if any(axis in command.Parameters for axis in ("X", "Y")):
                effective_z = position["Z"]
                if effective_z is None or effective_z < 2.0 - 1e-6:
                    return None
            continue
        if not all(before[axis] is not None and position[axis] is not None for axis in position):
            continue
        if name == "G1":
            distance = math.sqrt(
                sum((position[axis] - before[axis]) ** 2 for axis in ("X", "Y", "Z"))
            )
            count = max(1, int(math.ceil(distance / spacing)))
            for index in range(1, count + 1):
                fraction = index / float(count)
                samples.append(
                    (
                        before["X"] + (position["X"] - before["X"]) * fraction,
                        before["Y"] + (position["Y"] - before["Y"]) * fraction,
                        before["Z"] + (position["Z"] - before["Z"]) * fraction,
                    )
                )
            continue
        if "I" not in command.Parameters or "J" not in command.Parameters:
            return None
        center_x = before["X"] + float(command.Parameters["I"])
        center_y = before["Y"] + float(command.Parameters["J"])
        radius = math.hypot(before["X"] - center_x, before["Y"] - center_y)
        if radius <= 1e-9:
            return None
        start = math.atan2(before["Y"] - center_y, before["X"] - center_x)
        finish = math.atan2(position["Y"] - center_y, position["X"] - center_x)
        if name == "G2":
            while finish >= start:
                finish -= 2.0 * math.pi
        else:
            while finish <= start:
                finish += 2.0 * math.pi
        sweep = finish - start
        count = max(4, int(math.ceil(abs(sweep) * radius / spacing)))
        for index in range(1, count + 1):
            fraction = index / float(count)
            angle = start + sweep * fraction
            samples.append(
                (
                    center_x + radius * math.cos(angle),
                    center_y + radius * math.sin(angle),
                    before["Z"] + (position["Z"] - before["Z"]) * fraction,
                )
            )
    return motions, samples


def validate_pocket_path(op, spec):
    _, cx, length, width, radius, depth, _, diameter = spec
    result = sample_motion(op)
    if result is None:
        return False
    motions, samples = result
    if motions < 5 or not samples:
        return False
    final_z = -depth
    cutting = [point for point in samples if point[2] <= 1e-5]
    if not cutting or min(point[2] for point in cutting) < final_z - 1e-4:
        return False
    tool_radius = diameter / 2.0
    if any(
        not rounded_contains(
            point[0], point[1], cx, length, width, radius, tool_radius, tolerance=0.03
        )
        for point in cutting
    ):
        return False
    floor_samples = [point for point in cutting if close(point[2], final_z, 0.01)]
    if len(floor_samples) < 3:
        return False
    grid = 0.75
    x = cx - length / 2.0
    targets = []
    while x <= cx + length / 2.0 + 1e-9:
        y = -width / 2.0
        while y <= width / 2.0 + 1e-9:
            if rounded_contains(x, y, cx, length, width, radius, tolerance=0.01):
                targets.append((x, y))
            y += grid
        x += grid
    reach = tool_radius + 0.85
    for target_x, target_y in targets:
        if min(math.hypot(target_x - px, target_y - py) for px, py, _ in floor_samples) > reach:
            return False
    return True


def drilling_cycles(op):
    position = {"X": None, "Y": None, "Z": None}
    active = False
    cycle_z = None
    cycle_r = None
    records = []
    saw_cancel = False
    retract = None
    for command in op.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        before = dict(position)
        for axis in position:
            if axis in command.Parameters:
                position[axis] = float(command.Parameters[axis])
        if name in {"G1", "G2", "G3"}:
            return None
        if name == "G98":
            retract = 98
        elif name == "G99":
            retract = 99
        if name == "G0" and any(axis in command.Parameters for axis in ("X", "Y")):
            if position["Z"] is None or position["Z"] < 2.0 - 1e-6:
                return None
        if name in {"G81", "G82", "G83"}:
            active = True
            if "Z" in command.Parameters:
                cycle_z = float(command.Parameters["Z"])
            if "R" in command.Parameters:
                cycle_r = float(command.Parameters["R"])
            if (
                position["X"] is None
                or position["Y"] is None
                or cycle_z is None
                or cycle_r is None
                or retract != 98
            ):
                return None
            if name == "G82" and ("P" not in command.Parameters or float(command.Parameters["P"]) < 0):
                return None
            if name == "G83" and ("Q" not in command.Parameters or float(command.Parameters["Q"]) <= 0):
                return None
            records.append((position["X"], position["Y"], cycle_z, cycle_r))
            position["Z"] = before["Z"] if retract == 98 else cycle_r
        elif active and name == "G80":
            active = False
            saw_cancel = True
        elif active and name != "G0" and any(
            axis in command.Parameters for axis in ("X", "Y")
        ):
            if position["X"] is None or position["Y"] is None or retract != 98:
                return None
            records.append((position["X"], position["Y"], cycle_z, cycle_r))
            position["Z"] = before["Z"] if retract == 98 else cycle_r
        elif active and name not in {"G0", "G98", "G99"} and any(
            axis in command.Parameters for axis in ("X", "Y", "Z")
        ):
            return None
    if active or not saw_cancel:
        return None
    return records


def validate_profile_path(op):
    result = sample_motion(op)
    if result is None:
        return False
    motions, samples = result
    if motions < 20 or not samples:
        return False
    cutting = [point for point in samples if point[2] <= 1e-5]
    if not cutting or min(point[2] for point in cutting) < -18.0001:
        return False
    final = [point for point in cutting if close(point[2], -18.0, 0.01)]
    if len(final) < 100:
        return False
    if any(not (-68.05 <= x <= 68.05 and -48.05 <= y <= 48.05) for x, y, _ in final):
        return False
    xs = [point[0] for point in final]
    ys = [point[1] for point in final]
    if not (
        close(min(xs), -68.0, 0.05)
        and close(max(xs), 68.0, 0.05)
        and close(min(ys), -48.0, 0.05)
        and close(max(ys), 48.0, 0.05)
    ):
        return False
    for target in ((-68.0, 0.0), (68.0, 0.0), (0.0, -48.0), (0.0, 48.0)):
        if min(math.hypot(x - target[0], y - target[1]) for x, y, _ in final) > 0.75:
            return False
    return True


def expected_tool(doc, number, kind, diameter):
    attrs = {
        "version": 2,
        "name": "Evaluator T%d" % number,
        "shape": "drill.fcstd" if kind == "drill" else "endmill.fcstd",
        "parameter": {
            "Diameter": "%g mm" % diameter,
            "Length": "60 mm",
        },
        "attribute": {},
    }
    if kind == "drill":
        attrs["parameter"]["TipAngle"] = "118 deg"
    else:
        attrs["parameter"]["ShankDiameter"] = "%g mm" % diameter
        attrs["parameter"]["CuttingEdgeHeight"] = "24 mm"
    return PathToolBit.Factory.CreateFromAttrs(attrs, "EvaluatorTool%d" % number)


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
        for match in CODE_WORD_RE.finditer(line):
            if line[cursor : match.start()].strip():
                return None
            if match.group(1) != "N":
                value = float(match.group(2))
                if not math.isfinite(value):
                    return None
                value = 0.0 if abs(value) < 0.0000005 else round(value, 6)
                words.append((match.group(1), value))
            cursor = match.end()
        if line[cursor:].strip() or not words:
            return None
        if words == [("M", 30.0)]:
            words = [("M", 2.0)]
        result.append(tuple(words))
    return tuple(result)


def validate(step_path, fcstd_path, nc_path, repost_path):
    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        return False
    expected_source = expected_source_shape()
    if (
        not expected_source.isValid()
        or len(expected_source.Solids) != 1
        or not close(expected_source.Volume, 137669.0182180575, 1e-4)
    ):
        return False
    source_doc = App.newDocument("Task19SourceCheck")
    try:
        Import.insert(str(step_path), source_doc.Name)
        source_doc.recompute()
        source_shapes = [
            obj.Shape
            for obj in source_doc.Objects
            if hasattr(obj, "Shape") and not obj.Shape.isNull()
        ]
        if len(source_shapes) != 1:
            return False
        source_shape = source_shapes[0]
        bounds = source_shape.BoundBox
        if (
            len(source_shape.Solids) != 1
            or not same_shape(source_shape, expected_source)
            or not all(
                close(actual, wanted)
                for actual, wanted in zip(
                    (bounds.XMin, bounds.XMax, bounds.YMin, bounds.YMax, bounds.ZMin, bounds.ZMax),
                    (-60.0, 60.0, -40.0, 40.0, 0.0, 18.0),
                )
            )
        ):
            return False
    finally:
        App.closeDocument(source_doc.Name)

    doc = App.openDocument(str(fcstd_path))
    try:
        jobs = [obj for obj in doc.Objects if module(obj) == "Path.Main.Job"]
        pockets = [obj for obj in doc.Objects if module(obj) == "Path.Op.PocketShape"]
        drills = [obj for obj in doc.Objects if module(obj) == "Path.Op.Drilling"]
        profiles = [obj for obj in doc.Objects if module(obj) == "Path.Op.Profile"]
        controllers = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Controller"]
        tools = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Bit"]
        if not (
            len(jobs) == 1
            and len(pockets) == 5
            and len(drills) == 2
            and len(profiles) == 1
            and len(controllers) == 5
            and len(tools) == 5
        ):
            return False
        job = jobs[0]
        operations = list(job.Operations.Group)
        if len(operations) != 8 or set(operations) != set(pockets + drills + profiles):
            return False
        if (
            len(job.Model.Group) != 1
            or str(job.PostProcessor).strip().lower() != "linuxcnc"
            or list(job.Fixtures) != ["G54"]
            or bool(job.SplitOutput)
            or os.path.normpath(str(job.PostProcessorOutputFile))
            != "/home/user/Desktop/task-19.nc"
        ):
            return False
        model = job.Model.Group[0]
        expected_model = translated(expected_source, -18.0)
        if module(model) != "draftobjects.clone" or not same_shape(model.Shape, expected_model):
            return False
        source_links = list(getattr(model, "Objects", []))
        if len(source_links) != 1 or not same_shape(source_links[0].Shape, expected_source):
            return False
        stock = job.Stock
        expected_stock = Part.makeBox(124.0, 84.0, 18.0, App.Vector(-62.0, -42.0, -18.0))
        if (
            module(stock) != "Path.Main.Stock"
            or not same_shape(stock.Shape, expected_stock)
            or not close(stock.ExtXneg, 2.0)
            or not close(stock.ExtXpos, 2.0)
            or not close(stock.ExtYneg, 2.0)
            or not close(stock.ExtYpos, 2.0)
            or not close(stock.ExtZneg, 0.0)
            or not close(stock.ExtZpos, 0.0)
        ):
            return False
        by_number = {int(controller.ToolNumber): controller for controller in controllers}
        if set(by_number) != {1, 2, 3, 4, 5}:
            return False
        if [int(controller.ToolNumber) for controller in job.Tools.Group] != [1, 2, 3, 4, 5]:
            return False
        tool_specs = {
            1: ("end mill", 16.0),
            2: ("drill", 14.0),
            3: ("drill", 12.0),
            4: ("end mill", 10.0),
            5: ("end mill", 8.0),
        }
        temporary = []
        for number, (kind, diameter) in tool_specs.items():
            controller = by_number[number]
            tool = controller.Tool
            if tool not in tools or any(other.Tool == tool for n, other in by_number.items() if n != number):
                return False
            shape_name = "drill" if kind == "drill" else "endmill"
            if (
                not close(tool.Diameter, diameter)
                or str(tool.ShapeName).strip().lower() != shape_name
                or os.path.basename(str(tool.BitShape)).lower() != shape_name + ".fcstd"
                or tool.Shape.isNull()
                or len(tool.Shape.Solids) != 1
                or not close(tool.Length, 60.0)
                or not close(controller.SpindleSpeed, 7000.0)
                or str(controller.SpindleDir) != "Forward"
                or not close(controller.HorizFeed.getValueAs("mm/min").Value, 500.0)
                or not close(controller.VertFeed.getValueAs("mm/min").Value, 500.0)
            ):
                return False
            if kind == "drill":
                if not close(tool.TipAngle, 118.0):
                    return False
            elif not close(tool.ShankDiameter, diameter) or not close(tool.CuttingEdgeHeight, 24.0):
                return False
            reference = expected_tool(doc, number, kind, diameter)
            temporary.append(reference)
            doc.recompute()
            if not same_shape(tool.Shape, reference.Shape):
                return False
        for reference in temporary:
            doc.removeObject(reference.Name)
        doc.recompute()

        matched = {}
        for pocket in pockets:
            if not bool(pocket.Active) or pocket.ToolController not in controllers:
                return False
            face = horizontal_floor(pocket, model)
            if face is None:
                return False
            box = face.BoundBox
            candidates = [
                spec
                for spec in POCKETS
                if close(face.CenterOfMass.x, spec[1], 1e-4)
                and close(face.CenterOfMass.y, 0.0, 1e-4)
                and close(box.ZMin, -spec[5], 1e-5)
            ]
            if len(candidates) != 1:
                return False
            spec = candidates[0]
            if spec[0] in matched:
                return False
            matched[spec[0]] = pocket
            if (
                pocket.ToolController != by_number[spec[6]]
                or pocket.ToolController.Tool.Diameter.Value > min(spec[2], spec[3]) + 1e-7
                or not close(pocket.StartDepth, 0.0)
                or not close(pocket.FinalDepth, -spec[5])
                or not close(pocket.StepDown.Value, 2.0)
                or not close(float(pocket.StepOver), 50.0)
                or not close(pocket.SafeHeight.Value, 3.0)
                or not close(pocket.ClearanceHeight.Value, 5.0)
                or bool(pocket.UseOutline)
                or not validate_pocket_path(pocket, spec)
            ):
                return False
        if set(matched) != {spec[0] for spec in POCKETS}:
            return False

        drill_by_tool = {}
        for drill in drills:
            controller = drill.ToolController
            if controller not in controllers or int(controller.ToolNumber) not in {2, 3}:
                return False
            number = int(controller.ToolNumber)
            if number in drill_by_tool:
                return False
            drill_by_tool[number] = drill
            records = drilling_cycles(drill)
            if records is None or len(records) != 6:
                return False
            if {(round(x, 4), round(y, 4)) for x, y, _, _ in records} != EXPECTED_HOLES[number]:
                return False
            depths = {round(z, 4) for _, _, z, _ in records}
            retracts = {round(r, 4) for _, _, _, r in records}
            if (
                len(depths) != 1
                or not -25.0 <= next(iter(depths)) <= -19.0
                or len(retracts) != 1
                or not 1.9 <= next(iter(retracts)) <= 5.1
                or not bool(drill.Active)
                or not close(drill.StartDepth, 0.0)
                or not close(drill.FinalDepth, -19.0)
                or not close(drill.RetractHeight, 2.0)
                or str(drill.RetractMode) != "G98"
                or str(drill.ExtraOffset) != "Drill Tip"
                or not close(drill.SafeHeight.Value, 3.0)
                or not close(drill.ClearanceHeight.Value, 5.0)
                or bool(drill.KeepToolDown)
            ):
                return False
        if set(drill_by_tool) != {2, 3}:
            return False

        profile = profiles[0]
        if (
            profile.ToolController != by_number[1]
            or not bool(profile.Active)
            or str(profile.Side) != "Outside"
            or not bool(profile.UseComp)
            or not bool(profile.processPerimeter)
            or bool(profile.processHoles)
            or bool(profile.processCircles)
            or not close(profile.StartDepth, 0.0)
            or not close(profile.FinalDepth, -18.0)
            or not close(profile.StepDown.Value, 3.0)
            or str(profile.Direction) != "CW"
            or not close(profile.SafeHeight.Value, 3.0)
            or not close(profile.ClearanceHeight.Value, 5.0)
            or not validate_profile_path(profile)
        ):
            return False

        expected_operations = [
            matched["P1"],
            drill_by_tool[2],
            drill_by_tool[3],
            matched["P2"],
            matched["P3"],
            matched["P4"],
            matched["P5"],
            profile,
        ]
        if operations != expected_operations:
            return False

        operation_tools = Counter(int(op.ToolController.ToolNumber) for op in operations)
        if operation_tools != Counter({1: 2, 2: 1, 3: 1, 4: 3, 5: 1}):
            return False
        if any(count > 4 for count in operation_tools.values()):
            return False
        for obj in controllers + operations + [job]:
            obj.touch()
        doc.recompute()
        doc.recompute()
        if any(list(op.State) != ["Up-to-date"] or len(op.Path.Commands) == 0 for op in operations):
            return False
        for pocket in pockets:
            spec = next(spec for spec in POCKETS if matched[spec[0]] == pocket)
            if not validate_pocket_path(pocket, spec):
                return False
        if any(drilling_cycles(drill) is None for drill in drills) or not validate_profile_path(profile):
            return False
        sections = PathPostCommand.buildPostList(job)
        if len(sections) != 1:
            return False
        PostProcessor.load("linuxcnc").export(
            sections[0][1], str(repost_path), job.PostProcessorArgs
        )
        repost_signature = code_signature(repost_path)
        submitted_signature = code_signature(nc_path)
        return repost_signature is not None and repost_signature == submitted_signature
    finally:
        App.closeDocument(doc.Name)


ok = False
try:
    ok = validate(
        pathlib.Path(os.environ["TASK19_STEP"]),
        pathlib.Path(os.environ["TASK19_FCSTD"]),
        pathlib.Path(os.environ["TASK19_NC"]),
        pathlib.Path(os.environ["TASK19_REPOST"]),
    )
except Exception as error:
    print("task-19 child: %s" % error, file=sys.stderr)
    traceback.print_exc()
pathlib.Path(os.environ["TASK19_RESULT"]).write_text(
    json.dumps({"ok": bool(ok)}, sort_keys=True), encoding="utf-8"
)
raise SystemExit(0 if ok else 1)
'''


def validate_freecad(step_path, fcstd_path, nc_path, workdir):
    child = workdir / "validate_task19.py"
    repost = workdir / "repost.nc"
    result_file = workdir / "result.json"
    child.write_text(CHILD_SOURCE, encoding="utf-8")
    child.chmod(0o600)
    try:
        result = subprocess.run(
            [str(FREECADCMD), str(child)],
            cwd=workdir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
            check=False,
            env={
                "HOME": str(workdir),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": "/usr/bin:/bin",
                "TMPDIR": str(workdir),
                "TASK19_STEP": str(step_path),
                "TASK19_FCSTD": str(fcstd_path),
                "TASK19_NC": str(nc_path),
                "TASK19_REPOST": str(repost),
                "TASK19_RESULT": str(result_file),
            },
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        payload = None
    if result.returncode != 0 or payload != {"ok": True}:
        if result.stderr:
            print(result.stderr[-5000:], file=sys.stderr)
        return False
    return regular_file(repost, 5_000, 2_000_000)


def main():
    if not FREECADCMD.is_file():
        return fail("freecadcmd missing")
    if not validate_csv(CSV_FILE):
        return fail("wrong tool_candidates.csv")
    if not regular_file(STEP, 5_000, 5_000_000):
        return fail("invalid STEP file")
    if sha256(STEP) != EXPECTED_STEP_SHA256:
        return fail("wrong init STEP")
    if not validate_archive(FCSTD):
        return fail("invalid FCStd archive")
    if not validate_nc(NC):
        return fail("invalid NC semantics")
    with tempfile.TemporaryDirectory(prefix="task-19-eval-") as directory:
        workdir = Path(directory)
        frozen_step = workdir / "complex_pockets.step"
        frozen_csv = workdir / "tool_candidates.csv"
        frozen_fcstd = workdir / "task-19.FCStd"
        frozen_nc = workdir / "task-19.nc"
        if not freeze_file(STEP, frozen_step, 5_000, 5_000_000):
            return fail("could not freeze STEP")
        if not freeze_file(CSV_FILE, frozen_csv, 100, 10_000):
            return fail("could not freeze CSV")
        if not freeze_file(FCSTD, frozen_fcstd, 20_000, 20_000_000):
            return fail("could not freeze FCStd")
        if not freeze_file(NC, frozen_nc, 5_000, 2_000_000):
            return fail("could not freeze NC")
        if not validate_csv(frozen_csv):
            return fail("CSV changed during evaluation")
        if sha256(frozen_step) != EXPECTED_STEP_SHA256:
            return fail("STEP changed during evaluation")
        if not validate_freecad(frozen_step, frozen_fcstd, frozen_nc, workdir):
            return fail("FreeCAD validation failed")
    return True


if __name__ == "__main__":
    try:
        result = main()
    except Exception as error:
        print("task-19 evaluator exception: " + str(error), file=sys.stderr)
        result = False
    print(True if result else False)
