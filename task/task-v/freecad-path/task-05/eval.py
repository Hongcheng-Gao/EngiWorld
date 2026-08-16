from __future__ import annotations

import ast
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
STEP = TARGET / "chamfer_plate.step"
FCSTD = TARGET / "task-5.FCStd"
NC = TARGET / "task-5.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_STEP_SHA256 = "8ec817c169849de20f8fd852faf71a7fffb18b48c21259f129d4fe88a4e46825"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J"}
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 90, 94}
ALLOWED_M = {2, 3, 4, 5, 6, 7, 8, 9, 30}
REQUIRED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("Path.Main.Stock", "StockFromBase"): 1,
    ("Path.Tool.Controller", "ToolController"): 1,
    ("Path.Tool.Bit", "ToolBit"): 1,
    ("draftobjects.clone", "Clone"): 1,
})
ALLOWED_TOOL_FILES = {
    "",
    "/usr/lib/freecad/Mod/Path/Tools/Shape/chamfer.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Shape/chamfer.fcstd",
}
FORBIDDEN_SUFFIXES = {
    ".py", ".pyw", ".pyc", ".pyo", ".sh", ".bash", ".zsh", ".so", ".dll",
    ".dylib", ".exe", ".js", ".mjs", ".ps1", ".bat", ".cmd", ".scr",
}


def fail(message: str) -> bool:
    print("task-v05 evaluator: " + message, file=sys.stderr)
    return False


def close(a, b, tolerance=1e-6) -> bool:
    try:
        left, right = float(a), float(b)
    except (TypeError, ValueError):
        return False
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tolerance


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
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        preliminary = os.lstat(source)
        if not stat.S_ISREG(preliminary.st_mode) or not minimum <= preliminary.st_size <= maximum:
            return False
        descriptor = os.open(source, flags)
        try:
            before = os.fstat(descriptor)
            if (preliminary.st_dev, preliminary.st_ino, preliminary.st_mode) != (
                before.st_dev, before.st_ino, before.st_mode
            ):
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


def no_script_bypass(root: Path) -> bool:
    try:
        if not root.is_dir() or root.is_symlink():
            return False
        for child in root.iterdir():
            if child.name == "eval.py":
                continue
            info = child.lstat()
            if stat.S_ISFIFO(info.st_mode) or stat.S_ISSOCK(info.st_mode) or stat.S_ISCHR(info.st_mode):
                return False
            if stat.S_ISLNK(info.st_mode):
                return False
            if stat.S_ISREG(info.st_mode) and child.suffix.lower() in FORBIDDEN_SUFFIXES:
                return False
        return True
    except OSError:
        return False


def document_manifest(document: bytes, archive_names: set[str]) -> Counter:
    if len(document) > 4_000_000 or b"<!DOCTYPE" in document.upper() or b"<!ENTITY" in document.upper():
        raise ValueError("unsafe XML")
    root = ET.fromstring(document)
    if root.tag != "Document" or root.attrib.get("ProgramVersion") != "0.21R33771 (Git)":
        raise ValueError("wrong FreeCAD document build")
    object_list = root.find("Objects")
    if object_list is None:
        raise ValueError("missing object list")
    objects = [node for node in object_list if node.tag == "Object"]
    names = {node.attrib.get("name") for node in objects}
    if None in names or len(names) != len(objects) or not 1 <= len(objects) <= 100:
        raise ValueError("invalid object manifest")
    for prop in root.iter("Property"):
        property_type = prop.attrib.get("type", "")
        if "XLink" in property_type:
            raise ValueError("external link property")
    external_keys = {"file", "filename", "document", "doc", "href", "uri"}
    for node in root.iter():
        if node.tag not in {"Link", "LinkSub", "LinkList", "LinkSubList"}:
            continue
        lowered = {str(k).lower(): str(v) for k, v in node.attrib.items()}
        if any(lowered.get(key, "") for key in external_keys):
            raise ValueError("external object link")
        allowed = ({"count"} if node.tag in {"LinkList", "LinkSubList"} else {"obj", "value", "sub"}) | external_keys
        if set(lowered) - allowed or any("\x00" in value or "\n" in value or "\r" in value for value in lowered.values()):
            raise ValueError("invalid link encoding")
        target = node.attrib.get("obj")
        if target is None and node.tag in {"Link", "LinkSub"}:
            target = node.attrib.get("value")
        if target and target not in names:
            raise ValueError("non-local object link")
        sub = node.attrib.get("sub", "")
        if sub and (PurePosixPath(sub).is_absolute() or ".." in PurePosixPath(sub).parts or "\\" in sub or "://" in sub):
            raise ValueError("escaped sub-object")
    proxies = Counter()
    for node in root.iter("Python"):
        module, class_name = node.attrib.get("module"), node.attrib.get("class")
        value = node.attrib.get("value")
        if node.attrib.get("encoded") != "yes" or not isinstance(value, str) or len(value) > 4096:
            raise ValueError("invalid Python proxy payload")
        payload = json.loads(base64.b64decode(value, validate=True).decode("utf-8"))
        key = (module, class_name)
        if key == (None, None):
            if payload is not None:
                raise ValueError("invalid null proxy")
        elif key == ("draftobjects.clone", "Clone"):
            if payload != "Clone":
                raise ValueError("invalid clone proxy")
        elif key in REQUIRED_PROXIES or key == ("Path.Op.Deburr", "ObjectDeburr"):
            if payload is not None and not isinstance(payload, dict):
                raise ValueError("invalid native proxy state")
        else:
            raise ValueError("unapproved Python proxy")
        proxies[key] += 1
    outputs = []
    for prop in root.iter("Property"):
        if prop.attrib.get("type") != "App::PropertyFile":
            continue
        values = [node.attrib.get("value") for node in prop if node.tag == "String"]
        if len(values) != 1 or values[0] is None:
            raise ValueError("invalid file property")
        name, value = prop.attrib.get("name"), values[0]
        if name == "PostProcessorOutputFile":
            outputs.append(value)
        elif name in {"BitShape", "File"}:
            if value not in ALLOWED_TOOL_FILES:
                raise ValueError("unsafe ToolBit file")
        elif value:
            raise ValueError("unexpected external file")
    if outputs != ["/home/user/Desktop/task-5.nc"]:
        raise ValueError("wrong post output path")
    for node in root.iter():
        if node.tag not in {"Part", "Path"}:
            continue
        member = node.attrib.get("file")
        if not member or member not in archive_names or PurePosixPath(member).suffix.lower() not in {".brp", ".nc"}:
            raise ValueError("bad archive member reference")
    return proxies


def validate_archive(path: Path) -> bool:
    if not regular_file(path, 8_000, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if names.count("Document.xml") != 1 or len(names) != len(set(names)) or not 3 <= len(names) <= 200:
                return False
            total = 0
            for entry in entries:
                pure = PurePosixPath(entry.filename)
                mode = entry.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if (
                    not entry.filename or "\\" in entry.filename or pure.is_absolute() or ".." in pure.parts
                    or entry.flag_bits & 1 or stat.S_ISLNK(mode)
                    or kind not in {0, stat.S_IFREG, stat.S_IFDIR}
                    or entry.file_size > 20_000_000
                    or (entry.compress_size == 0 and entry.file_size > 0)
                    or (entry.compress_size and entry.file_size / entry.compress_size > 250)
                    or pure.suffix.lower() in FORBIDDEN_SUFFIXES
                ):
                    return False
                total += entry.file_size
                if total > 50_000_000:
                    return False
            proxies = document_manifest(archive.read("Document.xml"), set(names))
            nulls = proxies.pop((None, None), 0)
            deburrs = proxies.pop(("Path.Op.Deburr", "ObjectDeburr"), 0)
            return 0 <= nulls <= 20 and 1 <= deburrs <= 5 and proxies == REQUIRED_PROXIES
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError):
        return False


def strip_comments(text: str):
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


def parse_nc(path: Path):
    try:
        if not regular_file(path, 200, 2_000_000):
            return None
        text = path.read_text(encoding="utf-8")
        if "\x00" in text or any(len(line) > 4096 for line in text.splitlines()):
            return None
        executable = strip_comments(text)
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


def simulate_nc(path: Path):
    blocks = parse_nc(path)
    if blocks is None:
        return None
    state = {
        "units": None, "absolute": False, "plane": None, "wcs": None, "motion": None,
        "tool": None, "changed": False, "speed": None, "feed": None, "spindle": False,
        "X": None, "Y": None, "Z": None,
    }
    motions, changed_tools, ended = [], [], False
    for index, block in enumerate(blocks):
        words = dict(block)
        gs = [integral(value) for letter, value in block if letter == "G"]
        ms = [integral(value) for letter, value in block if letter == "M"]
        if ended or any(code is None or code not in ALLOWED_G for code in gs) or any(code is None or code not in ALLOWED_M for code in ms):
            return None
        if 21 in gs: state["units"] = "mm"
        if 17 in gs: state["plane"] = "XY"
        if 90 in gs: state["absolute"] = True
        if 54 in gs: state["wcs"] = 54
        for code in gs:
            if code in {0, 1, 2, 3}: state["motion"] = code
            elif code == 80: state["motion"] = None
        if "T" in words:
            tool = integral(words["T"])
            if tool != 2: return None
            state["tool"], state["changed"] = tool, False
        if "H" in words and integral(words["H"]) != 2: return None
        if "S" in words:
            if words["S"] <= 0 or words["S"] > 100_000: return None
            state["speed"] = words["S"]
        if "F" in words:
            if state["units"] != "mm" or not 0 < words["F"] <= 100_000: return None
            state["feed"] = words["F"]
        if 5 in ms: state["spindle"] = False
        if 6 in ms:
            if state["spindle"] or state["tool"] != 2: return None
            state["changed"] = True
            changed_tools.append(2)
        if 3 in ms or 4 in ms:
            if not state["changed"] or state["speed"] is None: return None
            state["spindle"] = True
        before = tuple(state[axis] for axis in ("X", "Y", "Z"))
        target = tuple(words[axis] if axis in words else state[axis] for axis in ("X", "Y", "Z"))
        if any(axis in words for axis in ("X", "Y", "Z")):
            motion = next((code for code in gs if code in {0, 1, 2, 3}), state["motion"])
            if motion is None: return None
            if before[2] is None:
                if motion != 0 or "Z" not in words or target[2] is None or target[2] <= 12.001:
                    return None
            if motion == 0 and any(axis in words for axis in ("X", "Y")):
                known_z = [value for value in (before[2], target[2]) if value is not None]
                if not known_z or min(known_z) <= 12.001:
                    return None
            complete = all(value is not None for value in before + target)
            if motion != 0:
                if not complete or state["units"] != "mm" or not state["absolute"] or state["plane"] != "XY": return None
                if state["wcs"] != 54 or state["tool"] != 2 or not state["changed"] or not state["spindle"] or state["feed"] is None: return None
            if complete:
                xy = not close(before[0], target[0]) or not close(before[1], target[1]) or motion in {2, 3}
                motions.append((motion, before, target, xy))
            state["X"], state["Y"], state["Z"] = target
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"]: return None
            ended = True
    cuts = [item for item in motions if item[0] in {1, 2, 3} and item[3] and close(item[1][2], item[2][2], 0.002)]
    if not ended or changed_tools != [2] or len(cuts) < 5 or state["units"] != "mm" or not state["absolute"] or state["plane"] != "XY":
        return None
    for motion, start, end, xy in motions:
        if motion == 0 and xy and min(start[2], end[2]) <= 12.001:
            return None
    return {"motions": motions, "cuts": cuts}


def validate_nc_structure(path: Path) -> bool:
    return simulate_nc(path) is not None


def canonical_nc(path: Path):
    blocks = parse_nc(path)
    if blocks is None:
        return None
    order = {letter: index for index, letter in enumerate(("G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J"))}
    result = []
    for block in blocks:
        words = []
        for letter, value in block:
            if letter == "N":
                continue
            if letter in {"G", "M", "T", "H"}:
                normalized = integral(value)
                if normalized is None: return None
                if letter == "M" and normalized == 30: normalized = 2
            else:
                normalized = round(value, 6)
                if normalized == 0: normalized = 0.0
            words.append((letter, normalized))
        if words:
            result.append(tuple(sorted(words, key=lambda item: (order[item[0]], item[1]))))
    return tuple(result) or None


CHILD_SOURCE = r'''
import hashlib,math,os,pathlib,shlex,stat,sys
from collections import Counter
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor
import Path.Tool.Bit as PathToolBit
import Path.Op.Util as PathOpUtil

EXPECTED_VERSION=("0","21","2","33771 (Git)")
EXPECTED_COMMIT="b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_STEP_SHA256="8ec817c169849de20f8fd852faf71a7fffb18b48c21259f129d4fe88a4e46825"
HOLES=((-25.0,-15.0),(25.0,-15.0),(-25.0,15.0),(25.0,15.0))
def num(v):return float(getattr(v,"Value",v))
def close(a,b,t=1e-6):
 try:return math.isfinite(num(a)) and math.isfinite(num(b)) and abs(num(a)-num(b))<=t
 except (AttributeError,TypeError,ValueError):return False
def proxy(o):return getattr(getattr(o,"Proxy",None).__class__,"__module__","")
def bounds(s):
 b=s.BoundBox;return (b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax)
def same_shape(a,b,t=1e-4):
 try:return a.isValid() and b.isValid() and a.cut(b).Volume<=t and b.cut(a).Volume<=t
 except Exception:return False
def identity_placement(obj,t=1e-7):
 try:
  placement=obj.getGlobalPlacement()
  vectors=(App.Vector(0,0,0),App.Vector(1,0,0),App.Vector(0,1,0),App.Vector(0,0,1))
  return all((placement.multVec(vector)-vector).Length<=t for vector in vectors)
 except Exception:return False
def safe_file(value,names,empty=False):
 try:
  if not value:return empty
  p=pathlib.Path(str(value)).resolve(strict=True);st=p.stat()
  return p.name in names and stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&(stat.S_IWGRP|stat.S_IWOTH)
 except (OSError,RuntimeError):return False
def post_args(value):
 try:
  tokens=shlex.split(str(value));flags={"--no-comments","--no-header","--line-numbers","--no-show-editor","--modal","--axis-modal","--no-tlo"};valued={"--precision"};seen=set();i=0
  while i<len(tokens):
   tok=tokens[i];opt,val=(tok.split("=",1)+[None])[:2] if "=" in tok else (tok,None)
   if opt in flags:
    if val is not None or opt in seen:return False
   elif opt in valued:
    if opt in seen:return False
    if val is None:i+=1;val=tokens[i] if i<len(tokens) else None
    if val is None or not val or len(val)>500 or "\n" in val or "\r" in val:return False
    if opt=="--precision" and (not val.isdigit() or not 0<=int(val)<=8):return False
   else:return False
   seen.add(opt);i+=1
  return "--inches" not in seen
 except (TypeError,ValueError,IndexError):return False
def geometry(shape):
 if shape is None or shape.isNull() or not shape.isValid() or len(shape.Solids)!=1:return None
 b=bounds(shape)
 if not close(b[1]-b[0],120,.01) or not close(b[3]-b[2],80,.01) or not close(b[5]-b[4],12,.01) or not close(shape.Volume,114257.522203923,1e-3):return None
 centers=[]
 for face in shape.Faces:
  surf=getattr(face,"Surface",None)
  if surf is not None and hasattr(surf,"Radius") and hasattr(surf,"Center") and close(surf.Radius,2.5,.001):
   c=surf.Center;centers.append((round(c.x,4),round(c.y,4)))
 cx=(b[0]+b[1])/2;cy=(b[2]+b[3])/2
 expected=sorted((round(cx+x,4),round(cy+y,4)) for x,y in HOLES)
 return None if sorted(set(centers))!=expected else {"bounds":b,"cx":cx,"cy":cy,"top":b[5],"bottom":b[4]}
def translated_source_equal(source,model):
 gs,gm=geometry(source),geometry(model)
 if gs is None or gm is None:return False
 copy=model.copy();copy.translate(App.Vector(gs["cx"]-gm["cx"],gs["cy"]-gm["cy"],gs["bottom"]-gm["bottom"]))
 return same_shape(source,copy)
def top_features(owner,names,geo):
 edges=[]
 try:
  for name in names:
   sub=owner.getSubObject(str(name))
   if sub is None:return None
   if sub.ShapeType=="Face":
    box=sub.BoundBox
    if not close(box.ZMin,geo["top"],.001) or not close(box.ZMax,geo["top"],.001):return None
    edges.extend(sub.Edges)
   elif sub.ShapeType=="Edge":edges.append(sub)
   else:return None
 except Exception:return None
 keys=set();outer=0
 for edge in edges:
  if not all(close(v.Point.z,geo["top"],.001) for v in edge.Vertexes):return None
  curve=getattr(edge,"Curve",None)
  if curve is not None and hasattr(curve,"Radius") and hasattr(curve,"Center"):
   if not close(curve.Radius,2.5,.001):return None
   center=(curve.Center.x,curve.Center.y);match=next((h for h in HOLES if close(center[0],geo["cx"]+h[0],.002) and close(center[1],geo["cy"]+h[1],.002)),None)
   if match is None:return None
   keys.add(("hole",match[0],match[1]))
  else:
   outer+=1
 if outer:
  if outer!=4:return None
  keys.add(("outer",))
 return keys
def arc_points(start,end,i,j,cw):
 cx,cy=start[0]+i,start[1]+j;r=math.hypot(start[0]-cx,start[1]-cy)
 if r<=1e-8 or not close(math.hypot(end[0]-cx,end[1]-cy),r,.003):return None
 a=math.atan2(start[1]-cy,start[0]-cx);b=math.atan2(end[1]-cy,end[0]-cx)
 if close(start[0],end[0],1e-7) and close(start[1],end[1],1e-7):b=a+(-2*math.pi if cw else 2*math.pi)
 elif cw:
  while b>=a:b-=2*math.pi
 else:
  while b<=a:b+=2*math.pi
 n=max(24,int(abs(b-a)*max(r,1)/.1));return [(cx+r*math.cos(a+(b-a)*k/n),cy+r*math.sin(a+(b-a)*k/n),start[2]+(end[2]-start[2])*k/n) for k in range(n+1)]
def path_groups(op,final_z,top):
 pos={"X":None,"Y":None,"Z":None};groups=[];current=[];safe=num(op.SafeHeight);clear=num(op.ClearanceHeight)
 if not top+.001<safe<=clear:return None
 for cmd in op.Path.Commands:
  name=str(cmd.Name).upper().replace(" ","");params=cmd.Parameters;before=tuple(pos[a] for a in ("X","Y","Z"))
  if name.startswith("("):continue
  if name not in {"G0","G00","G1","G01","G2","G02","G3","G03"}:return None
  for axis in pos:
   if axis in params:pos[axis]=float(params[axis])
  after=tuple(pos[a] for a in ("X","Y","Z"));code=int(name[1:])
  if code==0:
   if current:groups.append(current);current=[]
   if before[2] is None:
    if after[2] is None or after[2]<=top+.001:return None
   if (after[0] is not None or after[1] is not None) and (before[0] is None or before[1] is None):
    if after[2] is None or after[2]<=top+.001:return None
   if None not in before+after and (not close(before[0],after[0]) or not close(before[1],after[1])) and min(before[2],after[2])<=top+.001:return None
   continue
  if None in before+after:return None
  if min(before[2],after[2])<final_z-.01:return None
  horizontal=(close(before[2],after[2],.002) and ((not close(before[0],after[0]) or not close(before[1],after[1])) or code in {2,3}))
  if horizontal and close(after[2],final_z,.003):
   pts=[before,after]
   if code in {2,3}:
    pts=arc_points(before,after,float(params.get("I",0)),float(params.get("J",0)),code==2)
    if pts is None:return None
   current.append((code,before,after,pts))
  elif current:groups.append(current);current=[]
 if current:groups.append(current)
 return groups
def closed(group):
 return group and close(group[0][1][0],group[-1][2][0],.01) and close(group[0][1][1],group[-1][2][1],.01)
def group_points(group):return [p for rec in group for p in rec[3]]
def match_outer(group,geo,offset):
 if not closed(group):return False
 pts=group_points(group);xs=[p[0] for p in pts];ys=[p[1] for p in pts]
 b=geo["bounds"];expected=(b[0]-offset,b[1]+offset,b[2]-offset,b[3]+offset)
 return all(close(a,e,.03) for a,e in zip((min(xs),max(xs),min(ys),max(ys)),expected))
def match_hole(group,geo,hole,radius):
 if not closed(group) or radius<=.02:return False
 pts=group_points(group);cx=geo["cx"]+hole[0];cy=geo["cy"]+hole[1];rs=[math.hypot(p[0]-cx,p[1]-cy) for p in pts]
 return rs and max(abs(r-radius) for r in rs)<=.02 and max(rs)-min(rs)<=.02
def tool_ok(doc,tc):
 try:
  tool=tc.Tool
  if int(tc.ToolNumber)!=2 or proxy(tool)!="Path.Tool.Bit" or not safe_file(tool.BitShape,{"chamfer.fcstd"}):return False
  if str(tool.ShapeName)!="chamfer" or not close(tool.CuttingEdgeAngle,90,.01):return False
  d=num(tool.Diameter);tip=num(tool.TipDiameter);height=num(tool.CuttingEdgeHeight);length=num(tool.Length);shank=num(tool.ShankDiameter)
  if not 0<d<=30 or not 0<=tip<5 or not .5<=height<=length<=300 or not 0<shank<=30:return False
  attrs={"version":2,"name":"Expected V05 chamfer","shape":"chamfer.fcstd","parameter":{"CuttingEdgeAngle":"90 deg","CuttingEdgeHeight":str(height)+" mm","Diameter":str(d)+" mm","Length":str(length)+" mm","ShankDiameter":str(shank)+" mm","TipDiameter":str(tip)+" mm"},"attribute":{}}
  expected=PathToolBit.Factory.CreateFromAttrs(attrs,"ExpectedV05Tool")
  valid=same_shape(tool.Shape,expected.Shape);doc.removeObject(expected.Name);doc.recompute();return valid
 except Exception:return False
def op_signature(op):return tuple((str(c.Name).upper().replace(" ",""),tuple(sorted((str(k),round(float(v),6)) for k,v in c.Parameters.items()))) for c in op.Path.Commands)
def check_doc(doc,step_shape):
 jobs=[o for o in doc.Objects if proxy(o)=="Path.Main.Job"];ctrls=[o for o in doc.Objects if proxy(o)=="Path.Tool.Controller"];tools=[o for o in doc.Objects if proxy(o)=="Path.Tool.Bit"];clones=[o for o in doc.Objects if proxy(o)=="draftobjects.clone"];stocks=[o for o in doc.Objects if proxy(o)=="Path.Main.Stock"];ops=[o for o in doc.Objects if proxy(o)=="Path.Op.Deburr"]
 if list(map(len,(jobs,ctrls,tools,clones,stocks)))!=[1,1,1,1,1] or not 1<=len(ops)<=5:return None
 job,tc,clone,stock=jobs[0],ctrls[0],clones[0],stocks[0]
 grouped=list(job.Operations.Group)
 if list(job.Fixtures)!=["G54"] or list(job.Tools.Group)!=[tc] or len(grouped)!=len(ops) or set(grouped)!=set(ops):return None
 if len(job.Model.Group)!=1 or job.Model.Group[0]!=clone or len(list(clone.Objects))!=1:return None
 source=list(clone.Objects)[0];gs=geometry(step_shape);gm=geometry(clone.Shape)
 if gs is None or gm is None or not same_shape(source.Shape,step_shape) or not same_shape(clone.Shape,step_shape):return None
 if not all(identity_placement(obj) for obj in (source,clone)):return None
 if not all(close(a,b,.001) for a,b in zip(bounds(source.Shape),(-60,60,-40,40,0,12))) or not all(close(a,b,.001) for a,b in zip(bounds(clone.Shape),(-60,60,-40,40,0,12))):return None
 if stock!=job.Stock or stock.Base!=job.Model or stock.Shape.isNull() or not stock.Shape.isValid() or len(stock.Shape.Solids)!=1:return None
 sb=bounds(stock.Shape)
 if not all(close(a,b,.001) for a,b in zip(sb,(-60,60,-40,40,0,12))) or not close(stock.Shape.Volume,115200,.01):return None
 expected_stock=Part.makeBox(120,80,12,App.Vector(-60,-40,0))
 if not same_shape(stock.Shape,expected_stock):return None
 if str(job.PostProcessor).lower()!="linuxcnc" or not post_args(job.PostProcessorArgs) or bool(job.SplitOutput) or os.path.normpath(str(job.PostProcessorOutputFile))!="/home/user/Desktop/task-5.nc":return None
 if not tool_ok(doc,tc):return None
 if num(tc.SpindleSpeed)<=0 or num(tc.HorizFeed)<=0 or num(tc.VertFeed)<=0:return None
 if str(tc.SpindleDir) not in {"Forward","Reverse"}:return None
 all_features=set();sigs=[]
 for op in ops:
  if op.ToolController!=tc or not close(op.Width,.5,.0001) or num(op.ExtraDepth)<0:return None
  if num(op.StepDown)<0 or num(op.ClearanceHeight)<num(op.SafeHeight):return None
  selected=set()
  for owner,names in list(op.Base):
   if owner!=clone:return None
   found=top_features(owner,tuple(names),gm)
   if found is None:return None
   selected|=found
  if not selected or selected&all_features:return None
  all_features|=selected
  extra=num(op.ExtraDepth);tip=num(tc.Tool.TipDiameter);tan=math.tan(math.radians(num(tc.Tool.CuttingEdgeAngle)/2));depth=.5/tan+extra;offset=tip/2+extra*tan
  if offset>=2.5-.02 or num(tc.Tool.CuttingEdgeHeight)+.001<depth or num(tc.Tool.Diameter)/2+.001<tip/2+depth*tan:return None
  groups=path_groups(op,gm["top"]-depth,gm["top"])
  if groups is None or len(groups)!=len(selected):return None
  unmatched=list(groups)
  for feature in selected:
   index=next((i for i,g in enumerate(unmatched) if match_outer(g,gm,offset) if feature==("outer",)),None) if feature==("outer",) else next((i for i,g in enumerate(unmatched) if match_hole(g,gm,(feature[1],feature[2]),2.5-offset)),None)
   if index is None:return None
   unmatched.pop(index)
  if unmatched:return None
  sigs.append(op_signature(op))
 expected={("outer",)}|{("hole",x,y) for x,y in HOLES}
 relevant=[job,tc,tc.Tool,clone,source,stock,job.SetupSheet]+ops
 if all_features!=expected or any(set(map(str,o.State))!={"Up-to-date"} for o in relevant):return None
 return job,relevant,tuple(sigs)
def export(job,path):
 sections=PathPostCommand.buildPostList(job)
 if len(sections)!=1:return False
 PostProcessor.load("linuxcnc").export(sections[0][1],str(path),str(job.PostProcessorArgs));return path.is_file() and path.stat().st_size>=200
def validate(step_path,fcstd_path,outputs):
 version=tuple(App.Version())
 if tuple(version[:4])!=EXPECTED_VERSION or version[-1]!=EXPECTED_COMMIT:return False
 if hashlib.sha256(step_path.read_bytes()).hexdigest()!=EXPECTED_STEP_SHA256:return False
 step_shape=Part.read(str(step_path));gs=geometry(step_shape)
 if gs is None or not all(close(a,b,.001) for a,b in zip(gs["bounds"],(-60,60,-40,40,0,12))):return False
 doc=App.openDocument(str(fcstd_path))
 try:
  checked=check_doc(doc,step_shape)
  if checked is None or not export(checked[0],outputs[0]):return False
  saved=checked[2]
  for obj in checked[1]:obj.touch()
  doc.recompute();doc.recompute();checked=check_doc(doc,step_shape)
  if checked is None or checked[2]!=saved or not export(checked[0],outputs[1]):return False
 finally:App.closeDocument(doc.Name)
 doc=App.openDocument(str(fcstd_path))
 try:
  checked=check_doc(doc,step_shape)
  if checked is None or checked[2]!=saved:return False
  for obj in checked[1]:obj.touch()
  doc.recompute();doc.recompute();checked=check_doc(doc,step_shape)
  return checked is not None and checked[2]==saved and export(checked[0],outputs[2])
 finally:App.closeDocument(doc.Name)
if len(sys.argv)!=7:raise RuntimeError("invalid child argument count")
marker,step_arg,fcstd_arg,*out_args=sys.argv[1:7]
try:ok=validate(pathlib.Path(step_arg),pathlib.Path(fcstd_arg),list(map(pathlib.Path,out_args)))
except Exception as exc:print("task-v05 FreeCAD validation: %s: %s"%(type(exc).__name__,exc),file=sys.stderr);ok=False
print(marker+"="+("True" if ok else "False"))
'''


def run_freecad_validation(step_path: Path, fcstd_path: Path, submitted_nc: Path) -> bool:
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    marker = "TASKV05_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-taskv05-native-") as raw:
        temp = Path(raw)
        script = temp / "validate.py"
        exports = [temp / name for name in ("initial.nc", "recomputed.nc", "fresh.nc")]
        script.write_text(CHILD_SOURCE, encoding="utf-8")
        script.chmod(0o600)
        args = [str(script), marker, str(step_path), str(fcstd_path), *(str(path) for path in exports)]
        command = [
            str(executable), "-c",
            "import builtins,sys;sys.argv=%r;builtins.pythonopen=open;exec(compile(open(%r,encoding='utf-8').read(),%r,'exec'))"
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
        baseline = canonical_nc(submitted_nc)
        reposts = [canonical_nc(path) for path in exports]
        return baseline is not None and all(value == baseline for value in reposts) and all(validate_nc_structure(path) for path in exports)


def main() -> bool:
    if not no_script_bypass(TARGET):
        return fail("unsafe output directory")
    with tempfile.TemporaryDirectory(prefix="engiworld-taskv05-input-") as raw:
        frozen = Path(raw)
        step, fcstd, nc = frozen / STEP.name, frozen / FCSTD.name, frozen / NC.name
        if not freeze_file(STEP, step, 1_000, 10_000_000) or sha256(step) != EXPECTED_STEP_SHA256:
            return fail("invalid init STEP")
        if not freeze_file(FCSTD, fcstd, 8_000, 20_000_000) or not validate_archive(fcstd):
            return fail("invalid answer FCStd")
        if not freeze_file(NC, nc, 200, 2_000_000) or not validate_nc_structure(nc):
            return fail("invalid NC structure or machine safety")
        if not run_freecad_validation(step, fcstd, nc):
            return fail("native FreeCAD validation or fresh repost failed")
        return True


if __name__ == "__main__":
    try:
        result = main()
    except Exception as exc:
        print("task-v05 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        result = False
    print("True" if result else "False")
