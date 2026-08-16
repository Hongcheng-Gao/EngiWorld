from __future__ import annotations

import base64
import hashlib
import json
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
from pathlib import Path, PurePosixPath


TARGET = Path("/home/user/Desktop")
STEP = TARGET / "two_sided_part.step"
FCSTD = TARGET / "task-17_real.fcstd"
NC_A = TARGET / "task-17_A.nc"
NC_B = TARGET / "task-17_B.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_STEP_SHA256 = "e8595d746534ccf3a477f5e6de54b09a3ebef10e4933b342311b384c97fa70e0"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
HOLES = {(-45.0, -25.0), (45.0, -25.0), (-45.0, 25.0), (45.0, 25.0)}
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J", "R", "Q", "P"}
ALLOWED_G = {0, 1, 2, 3, 17, 20, 21, 40, 43, 49, 54, 55, 80, 81, 82, 83, 90, 94, 98, 99}
ALLOWED_M = {2, 3, 5, 6, 7, 8, 9, 30}
G_MODAL_GROUPS = (
    {0, 1, 2, 3, 80, 81, 82, 83},
    {17},
    {20, 21},
    {40},
    {43, 49},
    {54, 55},
    {90},
    {94},
    {98, 99},
)
M_MODAL_GROUPS = ({2, 30}, {3, 5})
PROXY_RULES = {
    ("Path.Main.Job", "ObjectJob"): 2,
    ("Path.Base.SetupSheet", "SetupSheet"): 2,
    ("Path.Main.Stock", "StockFromBase"): 2,
    ("Path.Tool.Controller", "ToolController"): (3, 6),
    ("Path.Tool.Bit", "ToolBit"): (3, 6),
    ("Path.Op.PocketShape", "ObjectPocket"): (1, 4),
    ("Path.Op.Drilling", "ObjectDrilling"): (1, 4),
    ("Path.Op.Helix", "ObjectHelix"): (1, 4),
    ("draftobjects.clone", "Clone"): 2,
}
ALLOWED_EXTERNAL_FILES = {
    "",
    "/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Shape/drill.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Endmill.fctb",
    "/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Drill.fctb",
}
EXPECTED_OUTPUT_FILES = {"/home/user/Desktop/task-17_A.nc", "/home/user/Desktop/task-17_B.nc"}


def fail(message):
    print("task-17 evaluator: " + message, file=sys.stderr)
    return False


def close(a, b, tolerance=1e-6):
    try:
        left, right = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


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
            chunks, remaining = [], maximum + 1
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
        if not stable or len(data) != before.st_size or not minimum <= len(data) <= maximum:
            return False
        target.write_bytes(data)
        target.chmod(0o600)
        return True
    except OSError:
        return False


def document_manifest(document, archive_names):
    root = ET.fromstring(document)
    result = Counter()
    for element in root.iter("Python"):
        module, class_name = element.attrib.get("module"), element.attrib.get("class")
        encoded, value = element.attrib.get("encoded"), element.attrib.get("value")
        if encoded != "yes" or not isinstance(value, str) or len(value) > 100_000:
            raise ValueError("invalid proxy serialization")
        payload = json.loads(base64.b64decode(value, validate=True).decode("utf-8"))
        if module is None and class_name is None:
            if payload is not None:
                raise ValueError("invalid null feature proxy")
        elif (module, class_name) == ("draftobjects.clone", "Clone"):
            if not isinstance(payload, str):
                raise ValueError("invalid clone proxy")
        elif payload is not None and not isinstance(payload, dict):
            raise ValueError("invalid proxy payload")
        result[(module, class_name)] += 1
    outputs = []
    for prop in root.iter("Property"):
        if prop.attrib.get("type") != "App::PropertyFile":
            continue
        values = [element.attrib.get("value") for element in prop if element.tag == "String"]
        if len(values) != 1 or values[0] is None:
            raise ValueError("invalid file property")
        name, value = prop.attrib.get("name"), values[0]
        if name == "PostProcessorOutputFile":
            outputs.append(value)
        elif name in {"BitShape", "File"}:
            if value not in ALLOWED_EXTERNAL_FILES:
                raise ValueError("unsafe external tool file")
        elif value:
            raise ValueError("unexpected external file property")
    if len(outputs) != 2 or set(outputs) != EXPECTED_OUTPUT_FILES:
        raise ValueError("invalid output file properties")
    for element in root.iter():
        if element.tag not in {"Part", "Path"}:
            continue
        member = element.attrib.get("file")
        if not member or member not in archive_names or PurePosixPath(member).suffix.lower() not in {".brp", ".nc"}:
            raise ValueError("invalid internal archive reference")
    return result


def validate_archive(path):
    if not regular_file(path, 10_000, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "Document.xml" not in names or len(names) != len(set(names)) or len(names) > 300:
                return False
            total = 0
            for entry in archive.infolist():
                name = entry.filename
                pure = PurePosixPath(name)
                unix_mode = entry.external_attr >> 16
                if (
                    not name
                    or "\\" in name
                    or pure.is_absolute()
                    or ".." in pure.parts
                    or entry.flag_bits & 1
                    or stat.S_ISLNK(unix_mode)
                    or entry.file_size > 20_000_000
                    or (entry.compress_size == 0 and entry.file_size > 0)
                    or (entry.compress_size and entry.file_size / entry.compress_size > 250)
                    or pure.suffix.lower() in {".py", ".pyc", ".pyo", ".so", ".sh", ".dll", ".dylib", ".exe"}
                ):
                    return False
                total += entry.file_size
                if total > 60_000_000:
                    return False
            proxies = document_manifest(archive.read("Document.xml"), set(names))
            null_count = proxies.pop((None, None), 0)
            if not 0 <= null_count <= 20 or set(proxies) != set(PROXY_RULES):
                return False
            for key, requirement in PROXY_RULES.items():
                count = proxies[key]
                if isinstance(requirement, tuple):
                    if not requirement[0] <= count <= requirement[1]:
                        return False
                elif count != requirement:
                    return False
            return True
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError):
        return False


def strip_comments(text):
    output, in_comment = [], False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        code, index = [], 0
        while index < len(line):
            char = line[index]
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
            index += 1
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
        words, cursor = [], 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            value = float(match.group(2))
            if not math.isfinite(value):
                return None
            words.append((match.group(1), value))
            cursor = match.end()
        if line[cursor:].strip() or not words or any(letter not in ALLOWED_ADDRESSES for letter, _ in words):
            return None
        if any(sum(letter == key for letter, _ in words) > 1 for key in ALLOWED_ADDRESSES - {"G", "M"}):
            return None
        blocks.append(words)
    return blocks or None


def arc_parts(start, end, i_value, j_value, clockwise):
    cx, cy = start[0] + i_value, start[1] + j_value
    radius = math.hypot(start[0] - cx, start[1] - cy)
    if radius <= 1e-9 or not close(math.hypot(end[0] - cx, end[1] - cy), radius, 0.01):
        return None
    first = math.atan2(start[1] - cy, start[0] - cx)
    last = math.atan2(end[1] - cy, end[0] - cx)
    if clockwise:
        while last >= first:
            last -= 2 * math.pi
    else:
        while last <= first:
            last += 2 * math.pi
    sweep = last - first
    count = max(12, int(abs(sweep) * max(radius, 1.0) / 0.25))
    points = []
    for index in range(count + 1):
        fraction = index / count
        angle = first + sweep * fraction
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle), start[2] + (end[2] - start[2]) * fraction))
    return (cx, cy, radius, sweep, points)


def simulate_nc(path, side):
    blocks = parse_nc(path)
    if blocks is None:
        return None
    allowed_tools = {1} if side == "A" else {2, 3}
    expected_wcs = 54 if side == "A" else 55
    state = {
        "units": None,
        "absolute": False,
        "plane": None,
        "wcs": None,
        "motion": None,
        "cycle": None,
        "cycle_z": None,
        "cycle_r": None,
        "cycle_p": None,
        "cycle_q": None,
        "cycle_kind": None,
        "retract": 98,
        "tool": None,
        "changed": False,
        "speed": None,
        "feed": None,
        "spindle": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    changed_tools, motions, cycles = [], [], []
    ended = False
    for index, block in enumerate(blocks):
        words = dict(block)
        gs = [integral(value) for letter, value in block if letter == "G"]
        ms = [integral(value) for letter, value in block if letter == "M"]
        if ended or any(code is None or code not in ALLOWED_G for code in gs) or any(code is None or code not in ALLOWED_M for code in ms):
            return None
        if any(sum(code in group for code in gs) > 1 for group in G_MODAL_GROUPS):
            return None
        if len(ms) != len(set(ms)) or any(sum(code in group for code in ms) > 1 for group in M_MODAL_GROUPS):
            return None
        if 21 in gs:
            state["units"] = "mm"
        if 20 in gs:
            state["units"] = "inch"
        if 17 in gs:
            state["plane"] = "XY"
        if 90 in gs:
            state["absolute"] = True
        for code in (54, 55):
            if code in gs:
                state["wcs"] = code
        if state["spindle"] and state["wcs"] not in {None, expected_wcs}:
            return None
        if 98 in gs:
            state["retract"] = 98
        if 99 in gs:
            state["retract"] = 99
        for code in gs:
            if code in {0, 1, 2, 3}:
                state["motion"] = code
                state["cycle"] = None
            if code in {80, 81, 82, 83}:
                state["cycle"] = None if code == 80 else code
                if code == 80:
                    state["motion"] = None
                    state["cycle_z"] = state["cycle_r"] = None
                    state["cycle_p"] = state["cycle_q"] = None
                    state["cycle_kind"] = None
        if "T" in words:
            tool = integral(words["T"])
            if tool not in allowed_tools:
                return None
            if tool != state["tool"]:
                state["changed"] = False
            state["tool"] = tool
        if "H" in words and integral(words["H"]) != state["tool"]:
            return None
        if "S" in words:
            if not close(words["S"], 7000):
                return None
            state["speed"] = words["S"]
        if "F" in words:
            scale = 25.4 if state["units"] == "inch" else 1.0
            if state["units"] is None or not close(words["F"] * scale, 500, 0.05):
                return None
            state["feed"] = words["F"] * scale
        if 5 in ms:
            state["spindle"] = False
        if 6 in ms:
            if state["spindle"] or state["tool"] not in allowed_tools:
                return None
            state["changed"] = True
            changed_tools.append(state["tool"])
        if 3 in ms:
            if not state["changed"] or state["speed"] is None:
                return None
            state["spindle"] = True

        before = (state["X"], state["Y"], state["Z"])
        scale = 25.4 if state["units"] == "inch" else 1.0
        target = tuple(words[axis] * scale if axis in words else state[axis] for axis in ("X", "Y", "Z"))
        explicit_cycle = next((code for code in gs if code in {81, 82, 83}), None)
        invoke_modal_cycle = explicit_cycle is None and state["cycle"] is not None and any(axis in words for axis in ("X", "Y")) and not any(code in {0, 1, 2, 3, 80} for code in gs)
        if explicit_cycle is not None:
            if state["cycle_kind"] != explicit_cycle:
                state["cycle_p"] = state["cycle_q"] = None
            state["cycle_kind"] = explicit_cycle
        if explicit_cycle is not None or invoke_modal_cycle:
            if "Z" in words:
                state["cycle_z"] = words["Z"] * scale
            if "R" in words:
                state["cycle_r"] = words["R"] * scale
            if "P" in words:
                state["cycle_p"] = words["P"]
            if "Q" in words:
                state["cycle_q"] = words["Q"] * scale
            code = explicit_cycle if explicit_cycle is not None else state["cycle"]
            if (
                side != "B"
                or state["tool"] != 2
                or state["units"] not in {"mm", "inch"}
                or not state["absolute"]
                or state["plane"] != "XY"
                or state["wcs"] != 55
                or not state["changed"]
                or not state["spindle"]
                or state["feed"] is None
                or target[0] is None
                or target[1] is None
                or state["cycle_z"] is None
                or state["cycle_r"] is None
            ):
                return None
            if code == 82 and (state["cycle_p"] is None or state["cycle_p"] < 0):
                return None
            if code == 83 and (state["cycle_q"] is None or state["cycle_q"] <= 0):
                return None
            cycles.append((code, target[0], target[1], state["cycle_z"], state["cycle_r"], state["tool"], state["retract"]))
            state["X"], state["Y"] = target[0], target[1]
            initial_z = before[2]
            state["Z"] = initial_z if state["retract"] == 98 else state["cycle_r"]
        else:
            explicit_motion = next((code for code in gs if code in {0, 1, 2, 3}), None)
            has_axes = any(axis in words for axis in ("X", "Y", "Z"))
            if has_axes and (explicit_motion is not None or state["cycle"] is None):
                motion = explicit_motion if explicit_motion is not None else state["motion"]
                if motion is None:
                    return None
                complete = all(value is not None for value in before) and all(value is not None for value in target)
                if motion == 0:
                    present = {axis for axis in ("X", "Y", "Z") if axis in words}
                    if before[2] is None:
                        if present != {"Z"} or target[2] is None or target[2] <= 18.0:
                            return None
                    elif target[2] is None:
                        return None
                    elif "Z" in words and target[2] < before[2] - 1e-6 and target[2] < 18.0 - 1e-6:
                        return None
                    elif present & {"X", "Y"} and min(before[2], target[2]) < 18.0 - 1e-6 and not complete:
                        return None
                elif not complete:
                    return None
                if complete:
                    arc = None
                    if motion in {2, 3}:
                        if ("I" not in words and "J" not in words) or state["plane"] != "XY":
                            return None
                        arc = arc_parts(before, target, words.get("I", 0.0) * scale, words.get("J", 0.0) * scale, motion == 2)
                        if arc is None:
                            return None
                    motions.append((motion, before, target, state["tool"], state["wcs"], state["spindle"], state["feed"], arc))
                state["X"], state["Y"], state["Z"] = target
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"]:
                return None
            ended = True
    if not ended or state["units"] not in {"mm", "inch"} or not state["absolute"] or state["plane"] != "XY":
        return None
    return {"tools": changed_tools, "motions": motions, "cycles": cycles}


def line_distance(px, py, start, end):
    ax, ay = start[0], start[1]
    bx, by = end[0], end[1]
    dx, dy = bx - ax, by - ay
    if close(dx, 0) and close(dy, 0):
        return math.hypot(px - ax, py - ay)
    ratio = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + ratio * dx), py - (ay + ratio * dy))


def expanded_segments(motion):
    code, start, end, _, _, _, _, arc = motion
    if code in {2, 3}:
        points = arc[4]
        return list(zip(points, points[1:]))
    return [(start, end)]


def validate_nc_a(path):
    if not regular_file(path, 500, 2_000_000):
        return False
    result = simulate_nc(path, "A")
    if result is None or result["tools"] != [1] or result["cycles"]:
        return False
    cutting, floor = [], []
    for motion in result["motions"]:
        code, start, end, tool, wcs, spindle, feed, _ = motion
        if code == 0 and (not close(start[0], end[0]) or not close(start[1], end[1])) and min(start[2], end[2]) < 18 - 0.01:
            return False
        if code not in {1, 2, 3}:
            continue
        if tool != 1 or wcs != 54 or not spindle or feed is None:
            return False
        for first, last in expanded_segments(motion):
            if min(first[2], last[2]) < -0.02:
                return False
            if min(first[2], last[2]) < 18 - 1e-6:
                if any(point[0] < -26.02 or point[0] > 26.02 or point[1] < -14.02 or point[1] > 14.02 for point in (first, last)):
                    return False
                cutting.append((first, last))
                if close(first[2], 0, 0.02) and close(last[2], 0, 0.02):
                    floor.append((first, last))
    if not cutting or not floor or not close(min(min(a[2], b[2]) for a, b in cutting), 0, 0.02):
        return False
    if (
        min(min(first[0], last[0]) for first, last in floor) > -25.98
        or max(max(first[0], last[0]) for first, last in floor) < 25.98
        or min(min(first[1], last[1]) for first, last in floor) > -13.98
        or max(max(first[1], last[1]) for first, last in floor) < 13.98
    ):
        return False
    for xi in range(-52, 53):
        for yi in range(-28, 29):
            x, y = xi / 2.0, yi / 2.0
            if min(line_distance(x, y, first, last) for first, last in floor) > 4.02:
                return False
    return True


def nearest_hole(x, y, tolerance=0.01):
    matches = [center for center in HOLES if math.hypot(x - center[0], y - center[1]) <= tolerance]
    return matches[0] if len(matches) == 1 else None


def validate_nc_b(path):
    if not regular_file(path, 700, 2_000_000):
        return False
    result = simulate_nc(path, "B")
    if result is None or result["tools"] != [2, 3] or len(result["cycles"]) != 4:
        return False
    cycle_centers = [nearest_hole(cycle[1], cycle[2]) for cycle in result["cycles"]]
    if None in cycle_centers or len(set(cycle_centers)) != 4 or set(cycle_centers) != HOLES:
        return False
    cycle_depths = []
    for code, _, _, z_value, r_value, tool, _ in result["cycles"]:
        if code not in {81, 82, 83} or tool != 2 or not -4.1 <= z_value <= -0.75 or r_value <= 18:
            return False
        cycle_depths.append(z_value)
    if max(cycle_depths) - min(cycle_depths) > 0.02:
        return False
    floor_sweep = Counter()
    descending = set()
    arc_count = 0
    for motion in result["motions"]:
        code, start, end, tool, wcs, spindle, feed, arc = motion
        if code == 0 and (not close(start[0], end[0]) or not close(start[1], end[1])) and min(start[2], end[2]) < 18 - 1e-6:
            if tool != 3:
                return False
            centers = [center for center in HOLES if math.hypot(start[0] - center[0], start[1] - center[1]) <= 2.02 and math.hypot(end[0] - center[0], end[1] - center[1]) <= 2.02]
            if len(centers) != 1:
                return False
        if code not in {1, 2, 3}:
            continue
        if tool == 2:
            if min(start[2], end[2]) < 18 - 1e-6:
                return False
            continue
        if tool != 3 or wcs != 55 or not spindle or feed is None:
            return False
        if min(start[2], end[2]) < 13.98:
            return False
        if code in {2, 3}:
            cx, cy, radius, sweep, points = arc
            center = nearest_hole(cx, cy)
            if center is None or not close(radius, 2, 0.01):
                return False
            if any(math.hypot(point[0] - center[0], point[1] - center[1]) > 2.02 for point in points):
                return False
            arc_count += 1
            if min(start[2], end[2]) <= 14.02:
                descending.add(center)
            if close(start[2], 14, 0.02) and close(end[2], 14, 0.02):
                floor_sweep[center] += abs(sweep)
        elif min(start[2], end[2]) < 18 - 1e-6:
            centers = [center for center in HOLES if math.hypot(start[0] - center[0], start[1] - center[1]) <= 2.02 and math.hypot(end[0] - center[0], end[1] - center[1]) <= 2.02]
            if len(centers) != 1:
                return False
    return arc_count >= 8 and descending == HOLES and all(floor_sweep[center] >= 2 * math.pi - 1e-3 for center in HOLES)


def normalized_nc(path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    text = TIMESTAMP_RE.sub("(Output Time:<normalized>)", text).replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"(?<![\d.])-0(?:\.0+)?(?![\d.])", lambda match: match.group(0)[1:], text)


CHILD_SOURCE = r'''
import hashlib, math, os, pathlib, shlex, stat, sys
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor

EXPECTED_VERSION=("0","21","2","33771 (Git)")
EXPECTED_COMMIT="b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256="e8595d746534ccf3a477f5e6de54b09a3ebef10e4933b342311b384c97fa70e0"
ENDMILL_FILE="/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Endmill.fctb"
DRILL_FILE="/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Drill.fctb"
HOLES={(-45.0,-25.0),(45.0,-25.0),(-45.0,25.0),(45.0,25.0)}

def number(value):
 value=getattr(value,"Value",value)
 return float(value)
def close(a,b,t=1e-6):
 try:
  left,right=number(a),number(b)
  return math.isfinite(left) and math.isfinite(right) and abs(left-right)<=t
 except (AttributeError,TypeError,ValueError):return False
def proxy_module(obj):return getattr(getattr(obj,"Proxy",None).__class__,"__module__","")
def same_volume(first,second,t=1e-4):
 try:return first.isValid() and second.isValid() and first.cut(second).Volume<=t and second.cut(first).Volume<=t
 except Exception:return False
def exact_bounds(shape,target,t=1e-5):
 box=shape.BoundBox;actual=(box.XMin,box.XMax,box.YMin,box.YMax,box.ZMin,box.ZMax)
 return shape.isValid() and all(close(a,b,t) for a,b in zip(actual,target))
def expected_shapes():
 shape=Part.makeBox(120,80,18,App.Vector(-60,-40,0)).cut(Part.makeBox(60,36,18,App.Vector(-30,-18,0)))
 for x,y in HOLES:
  shape=shape.cut(Part.makeCylinder(3,18,App.Vector(x,y,0)))
  shape=shape.cut(Part.makeCylinder(6,4,App.Vector(x,y,0)))
 flipped=shape.copy();flipped.rotate(App.Vector(0,0,0),App.Vector(1,0,0),180);flipped.translate(App.Vector(0,0,18))
 return shape,flipped
def command_signature(op):
 return tuple((str(command.Name).upper().replace(" ",""),tuple(sorted((str(key),round(float(value),6)) for key,value in command.Parameters.items()))) for command in op.Path.Commands)
def circle_record(shape):
 try:
  if shape.ShapeType!="Edge" or not isinstance(shape.Curve,Part.Circle):return None
  curve=shape.Curve
  if not close(shape.Length,2*math.pi*curve.Radius,1e-4):return None
  return (round(curve.Center.x,5),round(curve.Center.y,5),round(curve.Center.z,5),round(curve.Radius,5))
 except (AttributeError,TypeError,ValueError):return None
def selected_shapes(op):
 result=[]
 try:
  for obj,names in list(op.Base):
   for name in tuple(names):
    shape=obj.getSubObject(str(name))
    if shape is None or shape.isNull():return None
    result.append((obj,str(name),shape))
 except Exception:return None
 return result
def validate_circle_bases(ops,allowed_objects,radius,allowed_z,allow_helpers=False):
 selected=[]
 for op in ops:
  values=selected_shapes(op)
  if not values:return False
  selected.extend(values)
 if len(selected)!=4:return False
 records=[];helpers=set()
 for obj,_,shape in selected:
  if obj not in allowed_objects:
   if not allow_helpers or proxy_module(obj) not in {"","builtins"} or obj.TypeId not in {"PartDesign::Feature","Part::Feature"}:return False
   helpers.add(obj)
  record=circle_record(shape)
  if record is None or not close(record[3],radius,1e-4) or not any(close(record[2],z,1e-4) for z in allowed_z):return False
  records.append((record[0],record[1]))
 for helper in helpers:
  helper_records=[circle_record(edge) for edge in helper.Shape.Edges]
  if not helper_records or any(record is None or not close(record[3],radius,1e-4) or not any(close(record[2],z,1e-4) for z in allowed_z) for record in helper_records):return False
 return len(set(records))==4 and set(records)==HOLES
def validate_pocket_bases(ops,allowed_objects):
 for op in ops:
  selected=selected_shapes(op)
  if not selected:return False
  for obj,_,shape in selected:
   try:
    box=shape.BoundBox
    if (obj not in allowed_objects and proxy_module(obj) not in {"","builtins"}) or shape.ShapeType!="Face" or len(shape.Faces)!=1 or shape.Area<=0 or box.XMin<-30.0001 or box.XMax>30.0001 or box.YMin<-18.0001 or box.YMax>18.0001 or not close(box.ZMin,box.ZMax) or not -1e-5<=box.ZMin<=19.00001:return False
   except (AttributeError,TypeError,ValueError):return False
 return True
def arc_parts(start,end,i_value,j_value,clockwise):
 cx,cy=start[0]+i_value,start[1]+j_value;radius=math.hypot(start[0]-cx,start[1]-cy)
 if radius<=1e-9 or not close(math.hypot(end[0]-cx,end[1]-cy),radius,2e-3):return None
 first=math.atan2(start[1]-cy,start[0]-cx);last=math.atan2(end[1]-cy,end[0]-cx)
 if clockwise:
  while last>=first:last-=2*math.pi
 else:
  while last<=first:last+=2*math.pi
 sweep=last-first;count=max(12,int(abs(sweep)*max(radius,1)/0.25));points=[]
 for index in range(count+1):
  fraction=index/count;angle=first+sweep*fraction
  points.append((cx+radius*math.cos(angle),cy+radius*math.sin(angle),start[2]+(end[2]-start[2])*fraction))
 return cx,cy,radius,sweep,points
def path_motions(op):
 position={"X":None,"Y":None,"Z":None};motions=[]
 allowed={"G0","G00","G1","G01","G2","G02","G3","G03"}
 for command in op.Path.Commands:
  name=str(command.Name).upper().replace(" ","");before=tuple(position[a] for a in ("X","Y","Z"))
  if name.startswith("(") and name.endswith(")") and not command.Parameters:continue
  if name not in allowed:return None
  for axis in position:
   if axis in command.Parameters:position[axis]=float(command.Parameters[axis])
  after=tuple(position[a] for a in ("X","Y","Z"))
  code=int(name[1:]);arc=None
  present={axis for axis in position if axis in command.Parameters}
  if not present:continue
  complete=not any(v is None for v in before+after)
  if code==0:
   if before[2] is None:
    if present!={"Z"} or after[2] is None or after[2]<=18:return None
   elif after[2] is None:return None
   elif "Z" in present and after[2]<before[2]-1e-6 and after[2]<18-1e-6:return None
   elif present & {"X","Y"} and min(before[2],after[2])<18-1e-6 and not complete:return None
  elif not complete:return None
  if not complete:continue
  if code in {2,3}:
   if "I" not in command.Parameters and "J" not in command.Parameters:return None
   arc=arc_parts(before,after,float(command.Parameters.get("I",0)),float(command.Parameters.get("J",0)),code==2)
   if arc is None:return None
  motions.append((code,before,after,arc))
 return motions
def line_distance(px,py,start,end):
 ax,ay=start[0],start[1];bx,by=end[0],end[1];dx,dy=bx-ax,by-ay
 if close(dx,0) and close(dy,0):return math.hypot(px-ax,py-ay)
 ratio=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
 return math.hypot(px-(ax+ratio*dx),py-(ay+ratio*dy))
def expanded(motion):
 if motion[0] in {2,3}:
  points=motion[3][4];return list(zip(points,points[1:]))
 return [(motion[1],motion[2])]
def validate_pocket_paths(ops):
 motions=[]
 for op in ops:
  values=path_motions(op)
  if not values:return False
  motions.extend(values)
 cutting=[];floor=[]
 for motion in motions:
  code,start,end,_=motion
  if code==0 and (not close(start[0],end[0]) or not close(start[1],end[1])) and min(start[2],end[2])<18-1e-6:return False
  if code not in {1,2,3}:continue
  for first,last in expanded(motion):
   if min(first[2],last[2]) < -1e-5:return False
   if min(first[2],last[2]) < 18-1e-6:
    if any(p[0]<-26.001 or p[0]>26.001 or p[1]<-14.001 or p[1]>14.001 for p in (first,last)):return False
    cutting.append((first,last))
    if close(first[2],0,1e-4) and close(last[2],0,1e-4):floor.append((first,last))
 if not cutting or not floor or not close(min(min(a[2],b[2]) for a,b in cutting),0,1e-4):return False
 if min(min(a[0],b[0]) for a,b in floor)>-25.999 or max(max(a[0],b[0]) for a,b in floor)<25.999 or min(min(a[1],b[1]) for a,b in floor)>-13.999 or max(max(a[1],b[1]) for a,b in floor)<13.999:return False
 for xi in range(-52,53):
  for yi in range(-28,29):
   x,y=xi/2.0,yi/2.0
   if min(line_distance(x,y,a,b) for a,b in floor)>4.01:return False
 return True
def drilling_signature(op):
 position={"X":None,"Y":None,"Z":None};cycle=None;cycle_kind=None;cycle_z=None;cycle_r=None;cycle_p=None;cycle_q=None;retract=98;records=[]
 allowed={"G0","G00","G80","G81","G82","G83","G90","G98","G99"}
 for command in op.Path.Commands:
  name=str(command.Name).upper().replace(" ","");before=dict(position)
  if name.startswith("(") and name.endswith(")") and not command.Parameters:continue
  if name not in allowed:return None
  if name=="G98":retract=98
  if name=="G99":retract=99
  if name in {"G0","G00"}:cycle=None
  if name=="G80":cycle=None;cycle_kind=None;cycle_z=None;cycle_r=None;cycle_p=None;cycle_q=None
  if name in {"G81","G82","G83"}:
   cycle=name
   if cycle_kind!=name:cycle_p=None;cycle_q=None
   cycle_kind=name
   if "Z" in command.Parameters:cycle_z=float(command.Parameters["Z"])
   if "R" in command.Parameters:cycle_r=float(command.Parameters["R"])
   if "P" in command.Parameters:cycle_p=float(command.Parameters["P"])
   if "Q" in command.Parameters:cycle_q=float(command.Parameters["Q"])
  for axis in position:
   if axis in command.Parameters:position[axis]=float(command.Parameters[axis])
  if name in {"G81","G82","G83"}:
   if position["X"] is None or position["Y"] is None or cycle_z is None or cycle_r is None:return None
   if name=="G82" and (cycle_p is None or cycle_p<0):return None
   if name=="G83" and (cycle_q is None or cycle_q<=0):return None
   records.append((name,round(position["X"],5),round(position["Y"],5),round(cycle_z,5),round(cycle_r,5)))
   position["Z"]=before["Z"] if retract==98 else cycle_r
  elif name in {"G0","G00"}:
   present={axis for axis in position if axis in command.Parameters};effective=position["Z"]
   if before["Z"] is None:
    if present!={"Z"} or effective is None or effective<=18:return None
   elif effective is None:return None
   elif "Z" in present and effective<before["Z"]-1e-6 and effective<18-1e-6:return None
   elif present & {"X","Y"} and min(before["Z"],effective)<18-1e-6:return None
 return tuple(records)
def nearest_hole(x,y,t=1e-3):
 matches=[center for center in HOLES if math.hypot(x-center[0],y-center[1])<=t]
 return matches[0] if len(matches)==1 else None
def validate_helix_paths(ops):
 motions=[]
 for op in ops:
  values=path_motions(op)
  if not values:return False
  motions.extend(values)
 floor={center:0.0 for center in HOLES};descending=set();arcs=0
 for code,start,end,arc in motions:
  if code==0 and (not close(start[0],end[0]) or not close(start[1],end[1])) and min(start[2],end[2])<18-1e-6:
   centers=[c for c in HOLES if math.hypot(start[0]-c[0],start[1]-c[1])<=2.001 and math.hypot(end[0]-c[0],end[1]-c[1])<=2.001]
   if len(centers)!=1:return False
  if code not in {1,2,3}:continue
  if min(start[2],end[2])<14-1e-5:return False
  if code in {2,3}:
   cx,cy,radius,sweep,points=arc;center=nearest_hole(cx,cy)
   if center is None or not close(radius,2,2e-3) or any(math.hypot(p[0]-center[0],p[1]-center[1])>2.002 for p in points):return False
   arcs+=1
   if min(start[2],end[2])<=14+1e-4:descending.add(center)
   if close(start[2],14,1e-4) and close(end[2],14,1e-4):floor[center]+=abs(sweep)
  elif min(start[2],end[2])<18-1e-6:
   centers=[c for c in HOLES if math.hypot(start[0]-c[0],start[1]-c[1])<=2.002 and math.hypot(end[0]-c[0],end[1]-c[1])<=2.002]
   if len(centers)!=1:return False
 return arcs>=8 and descending==HOLES and all(floor[c]>=2*math.pi-1e-3 for c in HOLES)
def expected_tool_shape(doc,template,name,parameters):
 import Path.Tool.Bit as PathToolBit
 tool=PathToolBit.Factory.CreateFrom(template,name)
 for key,value in parameters.items():setattr(tool,key,value)
 tool.Proxy.loadBitBody(tool,force=True);tool.Proxy._updateBitShape(tool);tool.Proxy.unloadBitBody(tool);doc.recompute()
 return tool
def secure_system_file(value,allowed,allow_empty=False):
 try:
  if not value:return allow_empty
  path=pathlib.Path(str(value)).resolve(strict=True);accepted={pathlib.Path(item).resolve(strict=True) for item in allowed}
  info=path.stat()
  return path in accepted and stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode & (stat.S_IWGRP|stat.S_IWOTH)
 except (OSError,RuntimeError,ValueError):return False
def validate_controller(doc,controller,number_value,kind,diameter):
 try:
  tool=controller.Tool
  if int(controller.ToolNumber)!=number_value or tool is None or tool.Shape.isNull() or len(tool.Shape.Solids)!=1:return None
  if not close(tool.Diameter,diameter) or not close(controller.SpindleSpeed,7000) or str(controller.SpindleDir)!="Forward" or not close(controller.HorizFeed.getValueAs("mm/min").Value,500) or not close(controller.VertFeed.getValueAs("mm/min").Value,500):return None
  if kind=="endmill":
   shapes={"/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd","/usr/share/freecad/Mod/Path/Tools/Shape/endmill.fcstd"}
   if str(tool.ShapeName)!="endmill" or not secure_system_file(tool.BitShape,shapes) or not secure_system_file(getattr(tool,"File",""),{ENDMILL_FILE},True) or not secure_system_file(ENDMILL_FILE,{ENDMILL_FILE}) or not 0<number(tool.ShankDiameter)<=50 or not 0<number(tool.CuttingEdgeHeight)<=number(tool.Length)<=300:return None
   expected=expected_tool_shape(doc,ENDMILL_FILE,"ExpectedTask17Endmill%d"%number_value,{"Diameter":diameter,"ShankDiameter":number(tool.ShankDiameter),"CuttingEdgeHeight":number(tool.CuttingEdgeHeight),"Length":number(tool.Length)})
  else:
   shapes={"/usr/share/freecad/Mod/Path/Tools/Shape/drill.fcstd"}
   if str(tool.ShapeName)!="drill" or not secure_system_file(tool.BitShape,shapes) or not secure_system_file(getattr(tool,"File",""),{DRILL_FILE},True) or not secure_system_file(DRILL_FILE,{DRILL_FILE}) or not 90<=number(tool.TipAngle)<=150 or not 18<=number(tool.Length)<=300:return None
   expected=expected_tool_shape(doc,DRILL_FILE,"ExpectedTask17Drill",{"Diameter":diameter,"TipAngle":number(tool.TipAngle),"Length":number(tool.Length)})
  valid=same_volume(tool.Shape,expected.Shape,1e-4);doc.removeObject(expected.Name);doc.recompute()
  return tool if valid else None
 except (AttributeError,TypeError,ValueError):return None
def valid_post_args(value):
 try:
  text=str(value)
  if len(text)>1000 or any(ord(char)<32 and char not in "\t" for char in text):return False
  tokens=shlex.split(text);flags={"--no-comments","--no-header","--line-numbers","--no-show-editor","--inches","--modal","--axis-modal","--no-tlo"};valued={"--precision","--preamble","--postamble"};seen=set();index=0
  while index<len(tokens):
   token=tokens[index];option,value=(token.split("=",1)+[None])[:2] if "=" in token else (token,None)
   if option in flags:
    if value is not None or option in seen:return False
   elif option in valued:
    if option in seen:return False
    if value is None:
     index+=1
     if index>=len(tokens):return False
     value=tokens[index]
    if not value or len(value)>500 or "\n" in value or "\r" in value:return False
    if option=="--precision" and (not value.isdigit() or not 0<=int(value)<=8):return False
   else:return False
   seen.add(option);index+=1
  return "--no-show-editor" in seen
 except (TypeError,ValueError):return False
def clean_state(objects):
 return all(set(map(str,obj.State))=={"Up-to-date"} for obj in objects)
def export_job(job,path):
 sections=PathPostCommand.buildPostList(job)
 if len(sections)!=1:return False
 PostProcessor.load("linuxcnc").export(sections[0][1],str(path),str(job.PostProcessorArgs))
 return path.is_file() and path.stat().st_size>500
def validate(step_path,fcstd_path,repost_a,repost_b,fresh_a,fresh_b):
 if tuple(App.Version()[:4])!=EXPECTED_VERSION or App.Version()[-1]!=EXPECTED_COMMIT:return False
 if hashlib.sha256(step_path.read_bytes()).hexdigest()!=EXPECTED_STEP_SHA256:return False
 source=Part.read(str(step_path))
 if source is None or len(source.Solids)!=1 or not exact_bounds(source,(-60,60,-40,40,0,18)) or not close(source.Volume,172800,1e-3):return False
 expected_a,expected_b=expected_shapes()
 doc=App.openDocument(str(fcstd_path))
 try:
  if not 20<=len(doc.Objects)<=100 or not clean_state(doc.Objects):return False
  jobs=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Main.Job"]
  pockets=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Op.PocketShape"]
  drills=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Op.Drilling"]
  helices=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Op.Helix"]
  controllers=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Tool.Controller"]
  tools=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Tool.Bit"]
  clones=[obj for obj in doc.Objects if proxy_module(obj)=="draftobjects.clone"]
  stocks=[obj for obj in doc.Objects if proxy_module(obj)=="Path.Main.Stock"]
  if len(jobs)!=2 or not 1<=len(pockets)<=4 or not 1<=len(drills)<=4 or not 1<=len(helices)<=4 or not 3<=len(controllers)<=6 or len(tools)!=len(controllers) or len(clones)!=2 or len(stocks)!=2:return False
  by_wcs={}
  for job in jobs:
   fixtures=list(job.Fixtures)
   if len(fixtures)!=1 or fixtures[0] not in {"G54","G55"} or fixtures[0] in by_wcs:return False
   by_wcs[fixtures[0]]=job
  if set(by_wcs)!={"G54","G55"}:return False
  job_a,job_b=by_wcs["G54"],by_wcs["G55"]
  ops_a=list(job_a.Operations.Group);ops_b=list(job_b.Operations.Group)
  if len(ops_a)!=len(pockets) or set(ops_a)!=set(pockets) or len(ops_b)!=len(drills)+len(helices) or set(ops_b)!=set(drills+helices):return False
  seen_helix=False
  for op in ops_b:
   if op in helices:seen_helix=True
   elif seen_helix:return False
  if str(job_a.PostProcessor).lower()!="linuxcnc" or str(job_b.PostProcessor).lower()!="linuxcnc" or not valid_post_args(job_a.PostProcessorArgs) or not valid_post_args(job_b.PostProcessorArgs):return False
  if bool(job_a.SplitOutput) or bool(job_b.SplitOutput) or os.path.normpath(str(job_a.PostProcessorOutputFile))!="/home/user/Desktop/task-17_A.nc" or os.path.normpath(str(job_b.PostProcessorOutputFile))!="/home/user/Desktop/task-17_B.nc":return False
  if len(job_a.Model.Group)!=1 or len(job_b.Model.Group)!=1:return False
  model_a,model_b=job_a.Model.Group[0],job_b.Model.Group[0]
  if model_a==model_b or proxy_module(model_a)!="draftobjects.clone" or proxy_module(model_b)!="draftobjects.clone":return False
  if len(list(model_a.Objects))!=1 or len(list(model_b.Objects))!=1:return False
  part_a,part_b=list(model_a.Objects)[0],list(model_b.Objects)[0]
  if part_a==part_b or not same_volume(part_a.Shape,expected_a) or not same_volume(part_b.Shape,expected_b) or not same_volume(model_a.Shape,expected_a) or not same_volume(model_b.Shape,expected_b):return False
  stock_tops={}
  for job,model in ((job_a,model_a),(job_b,model_b)):
   stock=job.Stock
   if stock not in stocks or proxy_module(stock)!="Path.Main.Stock" or stock.Base!=job.Model:return False
   names=("ExtXneg","ExtXpos","ExtYneg","ExtYpos","ExtZneg","ExtZpos");extensions=[number(getattr(stock,name)) for name in names]
   if any(not math.isfinite(value) or value<0 or value>20 for value in extensions):return False
   xn,xp,yn,yp,zn,zp=extensions;stock_shape=Part.makeBox(120+xn+xp,80+yn+yp,18+zn+zp,App.Vector(-60-xn,-40-yn,-zn))
   if not same_volume(stock.Shape,stock_shape):return False
   stock_tops[job]=18+zp
  ctrls_a=list(job_a.Tools.Group);ctrls_b=list(job_b.Tools.Group)
  if len(ctrls_a)!=1 or len(ctrls_b)!=2 or len(set(ctrls_a+ctrls_b))!=3:return False
  if [int(controller.ToolNumber) for controller in ctrls_a]!=[1] or [int(controller.ToolNumber) for controller in ctrls_b]!=[2,3]:return False
  tc1,tc2,tc3=ctrls_a[0],ctrls_b[0],ctrls_b[1]
  if any(op.ToolController!=tc1 for op in pockets) or any(op.ToolController!=tc2 for op in drills) or any(op.ToolController!=tc3 for op in helices):return False
  bit1=validate_controller(doc,tc1,1,"endmill",8);bit2=validate_controller(doc,tc2,2,"drill",6);bit3=validate_controller(doc,tc3,3,"endmill",8)
  if bit1 is None or bit2 is None or bit3 is None or len({bit1.Name,bit2.Name,bit3.Name})!=3 or any(bit not in tools for bit in (bit1,bit2,bit3)):return False
  for pocket in pockets:
   if not (18-1e-5<=number(pocket.StartDepth)<=stock_tops[job_a]+1e-5 and 0-1e-5<=number(pocket.FinalDepth)<18 and number(pocket.SafeHeight)>stock_tops[job_a] and number(pocket.ClearanceHeight)>=number(pocket.SafeHeight) and 0<number(pocket.StepDown)<=18 and 0<number(pocket.StepOver)<=100):return False
   if str(pocket.CutMode) not in {"Climb","Conventional"} or str(pocket.OffsetPattern) not in {"ZigZag","Offset","ZigZagOffset","Line","Grid"}:return False
  if not any(close(pocket.FinalDepth,0) for pocket in pockets) or not validate_pocket_bases(pockets,{model_a,part_a}) or not validate_pocket_paths(pockets):return False
  tip_length=3.0/math.tan(math.radians(number(bit2.TipAngle)/2.0));drill_sigs=[]
  for drill in drills:
   if not (18-1e-5<=number(drill.StartDepth)<=stock_tops[job_b]+1e-5 and number(drill.SafeHeight)>stock_tops[job_b] and number(drill.ClearanceHeight)>=number(drill.SafeHeight) and str(drill.RetractMode) in {"G98","G99"}):return False
   if bool(drill.KeepToolDown)!=(str(drill.RetractMode)=="G99"):return False
   if bool(drill.PeckEnabled) and (not math.isfinite(number(drill.PeckDepth)) or number(drill.PeckDepth)<=0):return False
   if bool(drill.DwellEnabled) and (not math.isfinite(number(drill.DwellTime)) or number(drill.DwellTime)<0):return False
   if bool(drill.PeckEnabled) and bool(drill.DwellEnabled):return False
   offset=str(drill.ExtraOffset)
   if not ((offset in {"Drill Tip","2x Drill Tip"} and close(drill.FinalDepth,0)) or (offset=="None" and -2*tip_length-0.02<=number(drill.FinalDepth)<=-tip_length+0.02)):return False
   signature=drilling_signature(drill)
   if not signature: return False
   drill_sigs.append(signature)
  drill_sig=tuple(entry for signature in drill_sigs for entry in signature)
  if not validate_circle_bases(drills,{model_b,part_b},3,{0,18}) or len(drill_sig)!=4 or {entry[1:3] for entry in drill_sig}!=HOLES or any(entry[0] not in {"G81","G82","G83"} or not -2*tip_length-0.02<=entry[3]<=-tip_length+0.02 or entry[4]<=stock_tops[job_b] for entry in drill_sig):return False
  for helix in helices:
   if not (18-1e-5<=number(helix.StartDepth)<=stock_tops[job_b]+1e-5 and close(helix.FinalDepth,14) and number(helix.SafeHeight)>stock_tops[job_b] and number(helix.ClearanceHeight)>=number(helix.SafeHeight) and 0<number(helix.StepDown)<=18 and 0<number(helix.StepOver)<=100):return False
  if not validate_circle_bases(helices,{model_b,part_b},6,{14,18},True) or not validate_helix_paths(helices):return False
  all_ops=tuple(ops_a+ops_b);saved=tuple(command_signature(op) for op in all_ops)
  if not export_job(job_a,repost_a) or not export_job(job_b,repost_b):return False
  for obj in doc.Objects:obj.touch()
  doc.recompute();doc.recompute()
  if not clean_state(doc.Objects) or tuple(command_signature(op) for op in all_ops)!=saved:return False
  post_drill_sig=tuple(entry for drill in drills for entry in drilling_signature(drill))
  stable_drill=(len(post_drill_sig)==len(drill_sig) and all(a[:3]==b[:3] and close(a[3],b[3],1e-4) and close(a[4],b[4],1e-4) for a,b in zip(post_drill_sig,drill_sig)))
  post_checks=(same_volume(part_a.Shape,expected_a),same_volume(part_b.Shape,expected_b),validate_pocket_paths(pockets),stable_drill,validate_helix_paths(helices))
  if not all(post_checks):return False
  if not export_job(job_a,fresh_a) or not export_job(job_b,fresh_b):return False
  return True
 finally:
  App.closeDocument(doc.Name)

marker,step_arg,fcstd_arg,repost_a_arg,repost_b_arg,fresh_a_arg,fresh_b_arg=sys.argv[1:8]
try:
 result=validate(pathlib.Path(step_arg),pathlib.Path(fcstd_arg),pathlib.Path(repost_a_arg),pathlib.Path(repost_b_arg),pathlib.Path(fresh_a_arg),pathlib.Path(fresh_b_arg))
except Exception as exc:
 print("task-17 FreeCAD validation: %s: %s"%(type(exc).__name__,exc),file=sys.stderr);result=False
print(marker+"="+("True" if result else "False"))
'''


def run_freecad_validation(step_path, fcstd_path, nc_a_path, nc_b_path):
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    marker = "TASK17_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-task17-") as raw:
        temp = Path(raw)
        script = temp / "validate.py"
        repost_a, repost_b = temp / "repost_A.nc", temp / "repost_B.nc"
        fresh_a, fresh_b = temp / "fresh_A.nc", temp / "fresh_B.nc"
        script.write_text(CHILD_SOURCE, encoding="utf-8")
        script.chmod(0o600)
        args = [str(script), marker, str(step_path), str(fcstd_path), str(repost_a), str(repost_b), str(fresh_a), str(fresh_b)]
        command = [
            str(executable),
            "-c",
            "import builtins,sys; sys.argv=%r; builtins.pythonopen=open; exec(compile(open(%r,encoding='utf-8').read(),%r,'exec'))"
            % (args, str(script), str(script)),
        ]
        env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(temp),
            "TMPDIR": str(temp),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONNOUSERSITE": "1",
            "QT_QPA_PLATFORM": "offscreen",
            "XDG_CACHE_HOME": str(temp / ".cache"),
            "XDG_CONFIG_HOME": str(temp / ".config"),
        }
        try:
            completed = subprocess.run(
                command,
                cwd=temp,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        expected = marker + "=True"
        if completed.returncode != 0 or [line for line in completed.stdout.splitlines() if line.startswith(marker + "=")] != [expected]:
            if completed.stderr:
                print(completed.stderr[-4000:], file=sys.stderr)
            return False
        base_a, base_b = normalized_nc(nc_a_path), normalized_nc(nc_b_path)
        checks = (
            base_a is not None,
            base_b is not None,
            base_a == normalized_nc(fresh_a),
            base_b == normalized_nc(fresh_b),
            validate_nc_a(repost_a),
            validate_nc_a(fresh_a),
            validate_nc_b(repost_b),
            validate_nc_b(fresh_b),
        )
        return all(checks)


def main():
    with tempfile.TemporaryDirectory(prefix="engiworld-task17-input-") as raw:
        frozen = Path(raw)
        step = frozen / STEP.name
        fcstd = frozen / FCSTD.name
        nc_a = frozen / NC_A.name
        nc_b = frozen / NC_B.name
        if not freeze_file(STEP, step, 1_000, 10_000_000) or sha256(step) != EXPECTED_STEP_SHA256:
            return fail("invalid init STEP")
        if not freeze_file(FCSTD, fcstd, 10_000, 20_000_000) or not validate_archive(fcstd):
            return fail("invalid answer FCStd archive")
        if not freeze_file(NC_A, nc_a, 500, 2_000_000) or not validate_nc_a(nc_a):
            return fail("invalid Side A NC semantics")
        if not freeze_file(NC_B, nc_b, 700, 2_000_000) or not validate_nc_b(nc_b):
            return fail("invalid Side B NC semantics")
        if not run_freecad_validation(step, fcstd, nc_a, nc_b):
            return fail("native FreeCAD validation or fresh repost failed")
        return True


if __name__ == "__main__":
    try:
        outcome = main()
    except Exception as exc:
        print("task-17 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        outcome = False
    print("True" if outcome else "False")
