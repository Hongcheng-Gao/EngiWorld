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
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", "/home/user/Desktop"))
STEP = TARGET / "rect_pocket_block.step"
FCSTD = TARGET / "task-4.FCStd"
NC = TARGET / "task-4.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_STEP_SHA256 = "bbd090016c878f5bc07cde812a2de916678cc4de782df04f5b58c8b1741e1a41"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J"}
ALLOWED_G = {0, 1, 2, 3, 17, 20, 21, 40, 43, 49, 54, 80, 90, 94}
ALLOWED_M = {2, 3, 5, 6, 7, 8, 9, 30}
G_MODAL_GROUPS = ({0, 1, 2, 3, 80}, {17}, {20, 21}, {40}, {43, 49}, {54}, {90}, {94})
M_MODAL_GROUPS = ({2, 30}, {3, 5})
PROXY_RULES = {
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("Path.Main.Stock", "StockFromBase"): 1,
    ("Path.Tool.Controller", "ToolController"): 1,
    ("Path.Tool.Bit", "ToolBit"): 1,
    ("Path.Op.PocketShape", "ObjectPocket"): 1,
    ("draftobjects.clone", "Clone"): 1,
}
ALLOWED_EXTERNAL_FILES = {
    "",
    "/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Endmill.fctb",
}


def fail(message):
    print("task-v04 evaluator: " + message, file=sys.stderr)
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
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        preliminary = os.lstat(source)
        if not stat.S_ISREG(preliminary.st_mode) or not minimum <= preliminary.st_size <= maximum:
            return False
        descriptor = os.open(source, flags)
        try:
            before = os.fstat(descriptor)
            identity = (preliminary.st_dev, preliminary.st_ino, preliminary.st_mode)
            opened_identity = (before.st_dev, before.st_ino, before.st_mode)
            if identity != opened_identity or not stat.S_ISREG(before.st_mode) or not minimum <= before.st_size <= maximum:
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
            before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns
        ) == (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
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
    object_names = {element.attrib.get("name") for element in root.iter("Object") if element.attrib.get("name")}
    for prop in root.iter("Property"):
        property_type = prop.attrib.get("type", "")
        if "XLink" in property_type:
            raise ValueError("external document link property")
    link_tags = {"Link", "LinkSub", "LinkList", "LinkSubList"}
    external_keys = {"file", "filename", "document", "doc", "href", "uri"}
    for element in root.iter():
        if element.tag not in link_tags:
            continue
        lowered = {str(key).lower(): str(value) for key, value in element.attrib.items()}
        if any(lowered.get(key, "") for key in external_keys):
            raise ValueError("external file or document link")
        allowed_keys = ({"count"} if element.tag in {"LinkList", "LinkSubList"} else {"obj", "value", "sub"}) | external_keys
        if set(lowered) - allowed_keys:
            raise ValueError("unexpected link attribute")
        if any("\x00" in value or "\r" in value or "\n" in value for value in lowered.values()):
            raise ValueError("invalid link serialization")
        target = element.attrib.get("obj")
        if target is None and element.tag in {"Link", "LinkSub"}:
            target = element.attrib.get("value")
        if target and target not in object_names:
            raise ValueError("non-local object link")
        sub = element.attrib.get("sub", "")
        if sub and (".." in PurePosixPath(sub).parts or "\\" in sub or "://" in sub or "#" in sub or sub.startswith("/")):
            raise ValueError("escaped sub-object link")
    for element in root.iter("Python"):
        module, class_name = element.attrib.get("module"), element.attrib.get("class")
        encoded, value = element.attrib.get("encoded"), element.attrib.get("value")
        if encoded != "yes" or not isinstance(value, str) or len(value) > 100_000:
            raise ValueError("invalid proxy serialization")
        payload = json.loads(base64.b64decode(value, validate=True).decode("utf-8"))
        if module is None and class_name is None:
            if payload is not None:
                raise ValueError("invalid null proxy")
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
                raise ValueError("unsafe tool file")
        elif value:
            raise ValueError("unexpected external file")
    if outputs != ["/home/user/Desktop/task-4.nc"]:
        raise ValueError("invalid output file")
    for element in root.iter():
        if element.tag not in {"Part", "Path"}:
            continue
        member = element.attrib.get("file")
        if not member or member not in archive_names or PurePosixPath(member).suffix.lower() not in {".brp", ".nc"}:
            raise ValueError("invalid internal archive reference")
    return result


def validate_archive(path):
    if not regular_file(path, 8_000, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "Document.xml" not in names or len(names) != len(set(names)) or len(names) > 200:
                return False
            total = 0
            for entry in archive.infolist():
                pure = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                if (
                    not entry.filename or "\\" in entry.filename or pure.is_absolute() or ".." in pure.parts
                    or entry.flag_bits & 1 or stat.S_ISLNK(mode) or entry.file_size > 20_000_000
                    or (entry.compress_size == 0 and entry.file_size > 0)
                    or (entry.compress_size and entry.file_size / entry.compress_size > 250)
                    or pure.suffix.lower() in {".py", ".pyc", ".pyo", ".so", ".sh", ".dll", ".dylib", ".exe"}
                ):
                    return False
                total += entry.file_size
                if total > 50_000_000:
                    return False
            proxies = document_manifest(archive.read("Document.xml"), set(names))
            null_count = proxies.pop((None, None), 0)
            return 0 <= null_count <= 20 and proxies == Counter(PROXY_RULES)
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
    return points


def simulate_nc(path):
    blocks = parse_nc(path)
    if blocks is None:
        return None
    state = {
        "units": None, "absolute": False, "plane": None, "wcs": None, "motion": None,
        "tool": None, "changed": False, "speed": None, "feed": None, "spindle": False,
        "X": None, "Y": None, "Z": None,
    }
    changed_tools, motions, ended = [], [], False
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
        if 21 in gs: state["units"] = "mm"
        if 20 in gs: state["units"] = "inch"
        if 17 in gs: state["plane"] = "XY"
        if 90 in gs: state["absolute"] = True
        if 54 in gs: state["wcs"] = 54
        for code in gs:
            if code in {0, 1, 2, 3}: state["motion"] = code
            if code == 80: state["motion"] = None
        if "T" in words:
            if integral(words["T"]) != 1: return None
            if state["tool"] != 1: state["changed"] = False
            state["tool"] = 1
        if "H" in words and integral(words["H"]) != 1: return None
        if "S" in words:
            if not close(words["S"], 8000): return None
            state["speed"] = 8000.0
        if "F" in words:
            scale = 25.4 if state["units"] == "inch" else 1.0
            if state["units"] is None or not 0 < words["F"] * scale <= 100_000: return None
            state["feed"] = words["F"] * scale
        if 5 in ms: state["spindle"] = False
        if 6 in ms:
            if state["spindle"] or state["tool"] != 1: return None
            state["changed"] = True
            changed_tools.append(1)
        if 3 in ms:
            if not state["changed"] or state["speed"] is None: return None
            state["spindle"] = True
        before = (state["X"], state["Y"], state["Z"])
        scale = 25.4 if state["units"] == "inch" else 1.0
        target = tuple(words[axis] * scale if axis in words else state[axis] for axis in ("X", "Y", "Z"))
        explicit_motion = next((code for code in gs if code in {0, 1, 2, 3}), None)
        if any(axis in words for axis in ("X", "Y", "Z")):
            motion = explicit_motion if explicit_motion is not None else state["motion"]
            if motion is None: return None
            complete = all(value is not None for value in before) and all(value is not None for value in target)
            if motion == 0:
                present = {axis for axis in ("X", "Y", "Z") if axis in words}
                if before[2] is None:
                    if present != {"Z"} or target[2] is None or target[2] <= 18: return None
                elif target[2] is None: return None
                elif "Z" in words and target[2] < before[2] - 1e-6 and target[2] < 18 - 1e-6: return None
                elif present & {"X", "Y"} and min(before[2], target[2]) < 18 - 1e-6: return None
            elif not complete:
                return None
            if complete:
                points = None
                if motion in {2, 3}:
                    if ("I" not in words and "J" not in words) or state["plane"] != "XY": return None
                    points = arc_parts(before, target, words.get("I", 0) * scale, words.get("J", 0) * scale, motion == 2)
                    if points is None: return None
                motions.append((motion, before, target, state["tool"], state["wcs"], state["spindle"], state["feed"], points))
            state["X"], state["Y"], state["Z"] = target
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"]: return None
            ended = True
    if not ended or state["units"] not in {"mm", "inch"} or not state["absolute"] or state["plane"] != "XY":
        return None
    return {"tools": changed_tools, "motions": motions}


def line_distance(px, py, start, end):
    ax, ay, bx, by = start[0], start[1], end[0], end[1]
    dx, dy = bx - ax, by - ay
    if close(dx, 0) and close(dy, 0):
        return math.hypot(px - ax, py - ay)
    ratio = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + ratio * dx), py - (ay + ratio * dy))


def expanded_segments(motion):
    points = motion[7]
    return list(zip(points, points[1:])) if points is not None else [(motion[1], motion[2])]


def validate_pocket_motions(motions, check_machine_state):
    by_level = defaultdict(list)
    for motion in motions:
        code, start, end, tool, wcs, spindle, feed, _ = motion
        if code == 0:
            if (not close(start[0], end[0]) or not close(start[1], end[1])) and min(start[2], end[2]) < 18 - 1e-6:
                return False
            continue
        if code not in {1, 2, 3}:
            continue
        if check_machine_state and (tool != 1 or wcs != 54 or not spindle or feed is None):
            return False
        xy_change = not close(start[0], end[0]) or not close(start[1], end[1])
        horizontal_cut = xy_change and close(start[2], end[2], 0.001)
        if check_machine_state and horizontal_cut and not close(feed, 600, 0.05):
            return False
        if check_machine_state and not horizontal_cut and (feed is None or not 0 < feed <= 600.05):
            return False
        for first, last in expanded_segments(motion):
            if min(first[2], last[2]) < 8 - 0.01:
                return False
            if min(first[2], last[2]) < 18 - 1e-6:
                if any(point[0] < -21.01 or point[0] > 21.01 or point[1] < -11.01 or point[1] > 11.01 for point in (first, last)):
                    return False
                if close(first[2], last[2], 0.005):
                    by_level[round((first[2] + last[2]) / 2, 3)].append((first, last))
    levels = sorted(by_level, reverse=True)
    if not levels or not close(levels[-1], 8, 0.02) or not any(close(level, 8.1, 0.02) for level in levels):
        return False
    if 18 - levels[0] > 2.01 or any(high - low > 2.01 for high, low in zip(levels, levels[1:])):
        return False
    for level in levels:
        segments = by_level[level]
        for xi in range(-21, 22):
            for yi in range(-11, 12):
                if min(line_distance(xi, yi, first, last) for first, last in segments) > 4.01:
                    return False
    return True


def validate_nc(path):
    if not regular_file(path, 700, 2_000_000):
        return False
    result = simulate_nc(path)
    return result is not None and result["tools"] == [1] and validate_pocket_motions(result["motions"], True)


def canonical_nc(path):
    blocks = parse_nc(path)
    if blocks is None:
        return None
    canonical = []
    integral_letters = {"G", "M", "T", "H"}
    order = {letter: index for index, letter in enumerate(("G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J"))}
    for block in blocks:
        words = []
        for letter, value in block:
            if letter == "N":
                continue
            if letter in integral_letters:
                normalized = integral(value)
                if normalized is None:
                    return None
                if letter == "M" and normalized == 30:
                    normalized = 2
            else:
                normalized = round(value, 6)
                if close(normalized, 0, 0):
                    normalized = 0.0
            words.append((letter, normalized))
        if words:
            canonical.append(tuple(sorted(words, key=lambda item: (order[item[0]], item[1]))))
    return tuple(canonical) or None


CHILD_SOURCE = r'''
import hashlib,math,os,pathlib,shlex,stat,sys
from collections import defaultdict
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor

EXPECTED_VERSION=("0","21","2","33771 (Git)")
EXPECTED_COMMIT="b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256="bbd090016c878f5bc07cde812a2de916678cc4de782df04f5b58c8b1741e1a41"
ENDMILL_FILE="/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Endmill.fctb"
def number(value):return float(getattr(value,"Value",value))
def close(a,b,t=1e-6):
 try:return math.isfinite(number(a)) and math.isfinite(number(b)) and abs(number(a)-number(b))<=t
 except (AttributeError,TypeError,ValueError):return False
def proxy(obj):return getattr(getattr(obj,"Proxy",None).__class__,"__module__","")
def same_volume(a,b,t=1e-4):
 try:return a.isValid() and b.isValid() and a.cut(b).Volume<=t and b.cut(a).Volume<=t
 except Exception:return False
def bounds(shape,target,t=1e-5):
 box=shape.BoundBox;actual=(box.XMin,box.XMax,box.YMin,box.YMax,box.ZMin,box.ZMax)
 return shape.isValid() and all(close(a,b,t) for a,b in zip(actual,target))
def expected_shape():return Part.makeBox(120,80,18,App.Vector(-60,-40,0)).cut(Part.makeBox(50,30,10,App.Vector(-25,-15,8)))
def signature(op):return tuple((str(c.Name).upper().replace(" ",""),tuple(sorted((str(k),round(float(v),6)) for k,v in c.Parameters.items()))) for c in op.Path.Commands)
def line_distance(px,py,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1]
 if close(dx,0) and close(dy,0):return math.hypot(px-a[0],py-a[1])
 ratio=max(0,min(1,((px-a[0])*dx+(py-a[1])*dy)/(dx*dx+dy*dy)))
 return math.hypot(px-(a[0]+ratio*dx),py-(a[1]+ratio*dy))
def arc_points(start,end,i,j,cw):
 cx,cy=start[0]+i,start[1]+j;r=math.hypot(start[0]-cx,start[1]-cy)
 if r<=1e-9 or not close(math.hypot(end[0]-cx,end[1]-cy),r,0.002):return None
 first=math.atan2(start[1]-cy,start[0]-cx);last=math.atan2(end[1]-cy,end[0]-cx)
 if cw:
  while last>=first:last-=2*math.pi
 else:
  while last<=first:last+=2*math.pi
 sweep=last-first;count=max(12,int(abs(sweep)*max(r,1)/0.25));out=[]
 for n in range(count+1):
  f=n/count;angle=first+sweep*f;out.append((cx+r*math.cos(angle),cy+r*math.sin(angle),start[2]+(end[2]-start[2])*f))
 return out
def path_motions(op):
 position={"X":None,"Y":None,"Z":None};motions=[];allowed={"G0","G00","G1","G01","G2","G02","G3","G03"}
 for command in op.Path.Commands:
  name=str(command.Name).upper().replace(" ","");before=tuple(position[a] for a in ("X","Y","Z"))
  if name.startswith("(") and name.endswith(")") and not command.Parameters:continue
  if name not in allowed:return None
  for axis in position:
   if axis in command.Parameters:position[axis]=float(command.Parameters[axis])
  after=tuple(position[a] for a in ("X","Y","Z"));present={a for a in position if a in command.Parameters};code=int(name[1:])
  if not present:continue
  complete=not any(v is None for v in before+after)
  if code==0:
   if before[2] is None:
    if present!={"Z"} or after[2] is None or after[2]<=18:return None
   elif after[2] is None:return None
   elif "Z" in present and after[2]<before[2]-1e-6 and after[2]<18-1e-6:return None
   elif present & {"X","Y"} and min(before[2],after[2])<18-1e-6:return None
  elif not complete:return None
  if not complete:continue
  points=None
  if code in {2,3}:
   if "I" not in command.Parameters and "J" not in command.Parameters:return None
   points=arc_points(before,after,float(command.Parameters.get("I",0)),float(command.Parameters.get("J",0)),code==2)
   if points is None:return None
  motions.append((code,before,after,points))
 return motions
def validate_path(op):
 motions=path_motions(op)
 if not motions:return False
 by_level=defaultdict(list)
 for code,start,end,points in motions:
  if code==0:
   if (not close(start[0],end[0]) or not close(start[1],end[1])) and min(start[2],end[2])<18-1e-6:return False
   continue
  segments=list(zip(points,points[1:])) if points is not None else [(start,end)]
  for a,b in segments:
   if min(a[2],b[2])<8-1e-5:return False
   if min(a[2],b[2])<18-1e-6:
    if any(p[0]<-21.001 or p[0]>21.001 or p[1]<-11.001 or p[1]>11.001 for p in (a,b)):return False
    if close(a[2],b[2],1e-5):by_level[round((a[2]+b[2])/2,3)].append((a,b))
 levels=sorted(by_level,reverse=True)
 if not levels or not close(levels[-1],8,1e-4) or not any(close(z,8.1,1e-4) for z in levels):return False
 if 18-levels[0]>2.0001 or any(a-b>2.0001 for a,b in zip(levels,levels[1:])):return False
 for level in levels:
  for x in range(-21,22):
   for y in range(-11,12):
    if min(line_distance(x,y,a,b) for a,b in by_level[level])>4.001:return False
 return True
def selected_face(op,allowed):
 try:
  selected=[]
  for obj,names in list(op.Base):
   if obj not in allowed:return False
   for name in tuple(names):selected.append(obj.getSubObject(str(name)))
  if len(selected)!=1:return False
  shape=selected[0];box=shape.BoundBox
  return shape.ShapeType=="Face" and len(shape.Faces)==1 and close(shape.Area,1500,1e-4) and bounds(shape,(-25,25,-15,15,8,8),1e-4)
 except Exception:return False
def secure_file(value,allowed,empty=False):
 try:
  if not value:return empty
  path=pathlib.Path(str(value)).resolve(strict=True);accepted={pathlib.Path(item).resolve(strict=True) for item in allowed};info=path.stat()
  return path in accepted and stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&(stat.S_IWGRP|stat.S_IWOTH)
 except (OSError,RuntimeError,ValueError):return False
def validate_tool(doc,controller):
 try:
  tool=controller.Tool
  if int(controller.ToolNumber)!=1 or tool is None or proxy(tool)!="Path.Tool.Bit" or tool.Shape.isNull() or len(tool.Shape.Solids)!=1:return False
  if not close(tool.Diameter,8) or not close(controller.SpindleSpeed,8000) or str(controller.SpindleDir)!="Forward":return False
  if not close(controller.HorizFeed.getValueAs("mm/min").Value,600,1e-4) or not 0<number(controller.VertFeed.getValueAs("mm/min").Value)<=600:return False
  shapes={"/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd","/usr/share/freecad/Mod/Path/Tools/Shape/endmill.fcstd"}
  if str(tool.ShapeName)!="endmill" or not secure_file(tool.BitShape,shapes) or not secure_file(getattr(tool,"File",""),{ENDMILL_FILE},True) or not secure_file(ENDMILL_FILE,{ENDMILL_FILE}):return False
  if not 0<number(tool.ShankDiameter)<=50 or not 0<number(tool.CuttingEdgeHeight)<=number(tool.Length)<=300:return False
  import Path.Tool.Bit as PathToolBit
  expected=PathToolBit.Factory.CreateFrom(ENDMILL_FILE,"ExpectedTaskV04Tool")
  expected.Diameter=8;expected.ShankDiameter=number(tool.ShankDiameter);expected.CuttingEdgeHeight=number(tool.CuttingEdgeHeight);expected.Length=number(tool.Length)
  expected.Proxy.loadBitBody(expected,force=True);expected.Proxy._updateBitShape(expected);expected.Proxy.unloadBitBody(expected);doc.recompute()
  valid=same_volume(tool.Shape,expected.Shape);doc.removeObject(expected.Name);doc.recompute();return valid
 except (AttributeError,TypeError,ValueError):return False
def post_args(value):
 try:
  tokens=shlex.split(str(value));flags={"--no-comments","--no-header","--line-numbers","--no-show-editor","--inches","--modal","--axis-modal","--no-tlo"};valued={"--precision","--preamble","--postamble"};seen=set();i=0
  while i<len(tokens):
   token=tokens[i];option,val=(token.split("=",1)+[None])[:2] if "=" in token else (token,None)
   if option in flags:
    if val is not None or option in seen:return False
   elif option in valued:
    if option in seen:return False
    if val is None:
     i+=1
     if i>=len(tokens):return False
     val=tokens[i]
    if not val or len(val)>500 or "\n" in val or "\r" in val:return False
    if option=="--precision" and (not val.isdigit() or not 0<=int(val)<=8):return False
   else:return False
   seen.add(option);i+=1
  return True
 except (TypeError,ValueError):return False
def clean(objects):return all(set(map(str,obj.State))=={"Up-to-date"} for obj in objects)
def check_doc(doc,expected):
 jobs=[o for o in doc.Objects if proxy(o)=="Path.Main.Job"];ops=[o for o in doc.Objects if proxy(o)=="Path.Op.PocketShape"]
 ctrls=[o for o in doc.Objects if proxy(o)=="Path.Tool.Controller"];tools=[o for o in doc.Objects if proxy(o)=="Path.Tool.Bit"]
 clones=[o for o in doc.Objects if proxy(o)=="draftobjects.clone"];stocks=[o for o in doc.Objects if proxy(o)=="Path.Main.Stock"]
 if list(map(len,(jobs,ops,ctrls,tools,clones,stocks)))!=[1,1,1,1,1,1]:return None
 job,op,controller,clone,stock=jobs[0],ops[0],ctrls[0],clones[0],stocks[0]
 if list(job.Fixtures)!=["G54"] or list(job.Operations.Group)!=[op] or list(job.Tools.Group)!=[controller] or op.ToolController!=controller:return None
 if len(job.Model.Group)!=1 or job.Model.Group[0]!=clone or len(list(clone.Objects))!=1:return None
 source=list(clone.Objects)[0]
 if not same_volume(source.Shape,expected) or not same_volume(clone.Shape,expected):return None
 if stock!=job.Stock or stock.Base!=job.Model:return None
 names=("ExtXneg","ExtXpos","ExtYneg","ExtYpos","ExtZneg","ExtZpos");extensions=[number(getattr(stock,name)) for name in names]
 if any(not math.isfinite(value) or value<0 or value>20 for value in extensions):return None
 xn,xp,yn,yp,zn,zp=extensions;expected_stock=Part.makeBox(120+xn+xp,80+yn+yp,18+zn+zp,App.Vector(-60-xn,-40-yn,-zn))
 if not same_volume(stock.Shape,expected_stock):return None
 if str(job.PostProcessor).lower()!="linuxcnc" or not post_args(job.PostProcessorArgs) or bool(job.SplitOutput) or os.path.normpath(str(job.PostProcessorOutputFile))!="/home/user/Desktop/task-4.nc":return None
 if not validate_tool(doc,controller):return None
 if not 18-1e-5<=number(op.StartDepth)<=18+zp+1e-5 or not close(op.FinalDepth,8) or not 0<number(op.StepDown)<=2 or not close(op.FinishDepth,0.1):return None
 if not 0<number(op.StepOver)<=100 or str(op.CutMode) not in {"Climb","Conventional"} or str(op.OffsetPattern) not in {"ZigZag","Offset","ZigZagOffset","Line","Grid"}:return None
 if number(op.SafeHeight)<=18+zp or number(op.ClearanceHeight)<number(op.SafeHeight):return None
 if not selected_face(op,{clone,source}) or not validate_path(op):return None
 relevant=[job,op,controller,controller.Tool,clone,source,stock,job.SetupSheet]
 if not clean(relevant):return None
 return job,op,relevant,signature(op)
def export(job,path):
 sections=PathPostCommand.buildPostList(job)
 if len(sections)!=1:return False
 PostProcessor.load("linuxcnc").export(sections[0][1],str(path),str(job.PostProcessorArgs));return path.is_file() and path.stat().st_size>700
def validate(step_path,fcstd_path,initial,recomputed,fresh):
 if tuple(App.Version()[:4])!=EXPECTED_VERSION or App.Version()[-1]!=EXPECTED_COMMIT:return False
 if hashlib.sha256(step_path.read_bytes()).hexdigest()!=EXPECTED_STEP_SHA256:return False
 shape=Part.read(str(step_path));expected=expected_shape()
 if shape is None or len(shape.Solids)!=1 or not same_volume(shape,expected) or not bounds(shape,(-60,60,-40,40,0,18)) or not close(shape.Volume,157800,1e-3):return False
 doc=App.openDocument(str(fcstd_path))
 try:
  checked=check_doc(doc,expected)
  if checked is None:return False
  job,op,relevant,saved=checked
  if not export(job,initial):return False
  for obj in relevant:obj.touch()
  doc.recompute();doc.recompute();checked=check_doc(doc,expected)
  if checked is None or checked[3]!=saved or not export(checked[0],recomputed):return False
 finally:App.closeDocument(doc.Name)
 doc=App.openDocument(str(fcstd_path))
 try:
  checked=check_doc(doc,expected)
  if checked is None or checked[3]!=saved:return False
  for obj in checked[2]:obj.touch()
  doc.recompute();doc.recompute();checked=check_doc(doc,expected)
  return checked is not None and checked[3]==saved and export(checked[0],fresh)
 finally:App.closeDocument(doc.Name)
marker,step_arg,fcstd_arg,initial_arg,recomputed_arg,fresh_arg=sys.argv[1:7]
try:result=validate(pathlib.Path(step_arg),pathlib.Path(fcstd_arg),pathlib.Path(initial_arg),pathlib.Path(recomputed_arg),pathlib.Path(fresh_arg))
except Exception as exc:
 print("task-v04 FreeCAD validation: %s: %s"%(type(exc).__name__,exc),file=sys.stderr);result=False
print(marker+"="+("True" if result else "False"))
'''


def run_freecad_validation(step_path, fcstd_path, nc_path):
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    marker = "TASKV04_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-taskv04-") as raw:
        temp = Path(raw)
        script = temp / "validate.py"
        initial, recomputed, fresh = temp / "initial.nc", temp / "recomputed.nc", temp / "fresh.nc"
        script.write_text(CHILD_SOURCE, encoding="utf-8")
        script.chmod(0o600)
        args = [str(script), marker, str(step_path), str(fcstd_path), str(initial), str(recomputed), str(fresh)]
        command = [
            str(executable), "-c",
            "import builtins,sys; sys.argv=%r; builtins.pythonopen=open; exec(compile(open(%r,encoding='utf-8').read(),%r,'exec'))"
            % (args, str(script), str(script)),
        ]
        env = {
            "PATH": "/usr/bin:/bin", "HOME": str(temp), "TMPDIR": str(temp), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
            "PYTHONNOUSERSITE": "1", "QT_QPA_PLATFORM": "offscreen", "XDG_CACHE_HOME": str(temp / ".cache"),
            "XDG_CONFIG_HOME": str(temp / ".config"),
        }
        try:
            completed = subprocess.run(
                command, cwd=temp, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, timeout=300, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        expected = marker + "=True"
        if completed.returncode != 0 or [line for line in completed.stdout.splitlines() if line.startswith(marker + "=")] != [expected]:
            if completed.stderr:
                print(completed.stderr[-4000:], file=sys.stderr)
            return False
        baseline = canonical_nc(nc_path)
        exports = [canonical_nc(path) for path in (initial, recomputed, fresh)]
        return baseline is not None and all(value == baseline for value in exports) and all(validate_nc(path) for path in (initial, recomputed, fresh))


def main():
    with tempfile.TemporaryDirectory(prefix="engiworld-taskv04-input-") as raw:
        frozen = Path(raw)
        step, fcstd, nc = frozen / STEP.name, frozen / FCSTD.name, frozen / NC.name
        if not freeze_file(STEP, step, 1_000, 10_000_000) or sha256(step) != EXPECTED_STEP_SHA256:
            return fail("invalid init STEP")
        if not freeze_file(FCSTD, fcstd, 8_000, 20_000_000) or not validate_archive(fcstd):
            return fail("invalid answer FCStd archive")
        if not freeze_file(NC, nc, 700, 2_000_000) or not validate_nc(nc):
            return fail("invalid NC semantics")
        if not run_freecad_validation(step, fcstd, nc):
            return fail("native FreeCAD validation or fresh repost failed")
        return True


if __name__ == "__main__":
    try:
        outcome = main()
    except Exception as exc:
        print("task-v04 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        outcome = False
    print("True" if outcome else "False")
