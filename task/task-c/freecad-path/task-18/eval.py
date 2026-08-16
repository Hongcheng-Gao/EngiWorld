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
STEP = TARGET / "relief_surface.step"
FCSTD = TARGET / "task-18.FCStd"
NC = TARGET / "task-18.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_STEP_SHA256 = "82c2721b1d0bdd3bd76bdab27fd537828a0b1b96f1c2f6bc491e144382aec9e6"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J", "R", "P", "Q"}
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 90, 94}
ALLOWED_M = {2, 3, 5, 6, 30}
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
PROXY_COUNTS = Counter(
    {
        ("Path.Main.Job", "ObjectJob"): 1,
        ("Path.Base.SetupSheet", "SetupSheet"): 1,
        ("draftobjects.clone", "Clone"): 1,
        ("Path.Tool.Controller", "ToolController"): 2,
        ("Path.Tool.Bit", "ToolBit"): 2,
        ("Path.Main.Stock", "StockFromBase"): 1,
        ("Path.Op.Pocket", "ObjectPocket"): 1,
        ("Path.Op.Surface", "ObjectSurface"): 1,
    }
)
ALLOWED_EXTERNAL_FILES = {
    "",
    "/home/user/Desktop/task-18.nc",
    "/usr/lib/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Shape/endmill.fcstd",
    "/usr/lib/freecad/Mod/Path/Tools/Shape/ballend.fcstd",
    "/usr/share/freecad/Mod/Path/Tools/Shape/ballend.fcstd",
    "/usr/lib/freecad/Mod/Path/Tools/Bit/6mm_Ball_End.fctb",
    "/usr/share/freecad/Mod/Path/Tools/Bit/6mm_Ball_End.fctb",
}


def fail(message):
    print("task-18 evaluator: " + message, file=sys.stderr)
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


def validate_archive(path):
    if not regular_file(path, 10_000, 10_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "Document.xml" not in names or len(names) != len(set(names)) or len(names) > 100:
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
                    or entry.file_size > 10_000_000
                    or (entry.compress_size == 0 and entry.file_size > 0)
                    or (entry.compress_size and entry.file_size / entry.compress_size > 300)
                    or pure.suffix.lower() in {".py", ".pyc", ".pyo", ".sh", ".so", ".dll", ".dylib", ".exe"}
                ):
                    return False
                total += entry.file_size
                if total > 40_000_000:
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
                if payload is not None and not isinstance(payload, (dict, str)):
                    return False
                proxies[(module, class_name)] += 1
            if proxies != PROXY_COUNTS:
                return False
            for prop in root.iter("Property"):
                if prop.attrib.get("type") != "App::PropertyFile":
                    continue
                values = [child.attrib.get("value") for child in prop if child.tag == "String"]
                if len(values) != 1 or values[0] not in ALLOWED_EXTERNAL_FILES:
                    return False
            for element in root.iter():
                if element.tag not in {"Part", "Path"}:
                    continue
                member = element.attrib.get("file")
                if not member or member not in names or PurePosixPath(member).suffix.lower() not in {".brp", ".nc"}:
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
    if not regular_file(path, 10_000, 2_000_000):
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
        "tool": None,
        "changed": False,
        "speed": None,
        "feed": None,
        "spindle": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    changed_tools = []
    cuts = {1: [], 2: []}
    ended = False
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
        if len(ms) != len(set(ms)) or (2 in ms and 30 in ms):
            return False
        if 21 in gs:
            state["units"] = "mm"
        if 17 in gs:
            state["plane"] = "XY"
        if 90 in gs:
            state["absolute"] = True
        if 54 in gs:
            state["wcs"] = 54
        for code in gs:
            if code in {0, 1, 2, 3}:
                state["motion"] = code
        if "T" in words:
            tool = integral(words["T"])
            if tool not in {1, 2}:
                return False
            if tool != state["tool"]:
                state["changed"] = False
            state["tool"] = tool
        if "H" in words and integral(words["H"]) != state["tool"]:
            return False
        if "S" in words:
            if not close(words["S"], 7000):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if state["units"] != "mm" or not close(words["F"], 500, 0.01):
                return False
            state["feed"] = words["F"]
        if 5 in ms:
            state["spindle"] = False
        if 6 in ms:
            if state["spindle"] or state["tool"] not in {1, 2}:
                return False
            state["changed"] = True
            changed_tools.append(state["tool"])
        if 3 in ms:
            if not state["changed"] or state["speed"] is None:
                return False
            state["spindle"] = True

        before = (state["X"], state["Y"], state["Z"])
        for axis in ("X", "Y", "Z"):
            if axis in words:
                state[axis] = words[axis]
        motion = next((code for code in gs if code in {0, 1, 2, 3}), state["motion"])
        has_axis = any(axis in words for axis in ("X", "Y", "Z"))
        if has_axis and motion == 0 and any(axis in words for axis in ("X", "Y")):
            if state["Z"] is None or state["Z"] < 20.0 - 1e-6:
                return False
        if has_axis and motion in {1, 2, 3}:
            if (
                state["tool"] not in {1, 2}
                or not state["changed"]
                or not state["spindle"]
                or state["speed"] is None
                or state["feed"] is None
                or state["units"] != "mm"
                or not state["absolute"]
                or state["plane"] != "XY"
                or state["wcs"] != 54
                or any(state[axis] is None for axis in ("X", "Y", "Z"))
            ):
                return False
            if not (-60.001 <= state["X"] <= 60.001 and -40.001 <= state["Y"] <= 40.001 and 9.999 <= state["Z"] <= 23.001):
                return False
            if motion in {2, 3} and not all(letter in words for letter in ("I", "J")):
                return False
            cuts[state["tool"]].append((state["X"], state["Y"], state["Z"], motion, before))
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"]:
                return False
            ended = True

    if not ended or changed_tools != [1, 2]:
        return False
    t1, t2 = cuts[1], cuts[2]
    if len(t1) < 200 or len(t2) < 450:
        return False
    t1_x = [point[0] for point in t1]
    t1_y = [point[1] for point in t1]
    t1_z = [point[2] for point in t1]
    if not (
        close(min(t1_x), -54.5, 0.02)
        and close(max(t1_x), 54.5, 0.02)
        and close(min(t1_y), -34.5, 0.02)
        and close(max(t1_y), 34.5, 0.02)
        and close(min(t1_z), 12.0, 0.01)
        and close(max(t1_z), 16.0, 0.01)
    ):
        return False
    t2_x = [point[0] for point in t2]
    t2_y = [point[1] for point in t2]
    t2_z = [point[2] for point in t2]
    scanlines = sorted({round(value, 4) for value in t2_y})
    if not (
        min(t2_x) < -56.0
        and max(t2_x) > 56.0
        and min(t2_y) <= -36.0
        and max(t2_y) >= 36.0
        and close(min(t2_z), 10.0, 0.01)
        and max(t2_z) > 17.0
        and len(scanlines) >= 49
        and max(b - a for a, b in zip(scanlines, scanlines[1:])) <= 1.5001
    ):
        return False
    return True


CHILD_SOURCE = r'''
import builtins
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import traceback

builtins.pythonopen = open

import FreeCAD as App
import Import
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor

EXPECTED_VERSION=("0","21","2","33771 (Git)")
EXPECTED_COMMIT="b9bfa5c5507506e4515816414cd27f4851d00489"
TIMESTAMP_RE=re.compile(r"\(Output Time:[^()\r\n]*\)")
CODE_WORD_RE=re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")

def close(a,b,t=1e-6):
 try:return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=t
 except (TypeError,ValueError):return False
def module(o):return getattr(getattr(o,"Proxy",None).__class__,"__module__","")
def same_shape(a,b,t=1e-5):return a.isValid() and b.isValid() and a.cut(b).Volume<=t and b.cut(a).Volume<=t
def expected_shape():
 base=Part.makeBox(120,80,10,App.Vector(-60,-40,0))
 sphere=Part.makeSphere(30,App.Vector(0,0,-12))
 cap=sphere.common(Part.makeBox(120,80,8,App.Vector(-60,-40,10)))
 return base.fuse(cap).removeSplitter()
def face_types(op,model):
 if len(op.Base)!=1 or op.Base[0][0]!=model:return None
 names=list(op.Base[0][1])
 if len(names)!=2:return None
 result=[]
 for name in names:
  face=getattr(model.Shape,name);typ=type(face.Surface).__name__;box=face.BoundBox
  if typ=="Plane" and close(box.ZMin,10) and close(box.ZMax,10):result.append("Plane")
  elif typ=="Sphere" and box.ZMin>=10-1e-7 and close(box.ZMax,18):result.append("Sphere")
  else:return None
 return set(result)
def path_stats(op):
 pos={"X":None,"Y":None,"Z":None};cuts=[];motions=0
 for command in op.Path.Commands:
  name=str(command.Name).upper().replace(" ","")
  for axis in pos:
   if axis in command.Parameters:pos[axis]=float(command.Parameters[axis])
  if name in {"G0","G1","G2","G3"}:motions+=1
  if name in {"G1","G2","G3"} and all(pos[a] is not None for a in pos):cuts.append(tuple(pos[a] for a in ("X","Y","Z")))
 return motions,cuts
def code_signature(path):
 text=pathlib.Path(path).read_text(encoding="utf-8").replace("\r\n","\n").replace("\r","\n")
 text=re.sub(r"\([^()]*\)","",text)
 result=[]
 for raw in text.splitlines():
  line=raw.split(";",1)[0].strip().upper()
  if not line or line=="%":continue
  words=[];cursor=0
  for match in CODE_WORD_RE.finditer(line):
   if line[cursor:match.start()].strip():return None
   value=float(match.group(2));value=0.0 if abs(value)<0.0000005 else round(value,6)
   words.append((match.group(1),value));cursor=match.end()
  if line[cursor:].strip() or not words:return None
  result.append(tuple(words))
 return tuple(result)
def validate(step_path,fcstd_path,nc_path,repost_path):
 if tuple(App.Version()[:4])!=EXPECTED_VERSION or App.Version()[-1]!=EXPECTED_COMMIT:return False
 expected=expected_shape()
 source_doc=App.newDocument("Task18SourceCheck")
 try:
  Import.insert(str(step_path),source_doc.Name);source_doc.recompute()
  source_shapes=[o.Shape for o in source_doc.Objects if hasattr(o,"Shape") and not o.Shape.isNull()]
  if len(source_shapes)!=1:return False
  source=source_shapes[0]
  if len(source.Solids)!=1 or not same_shape(source,expected):return False
 finally:
  App.closeDocument(source_doc.Name)
 doc=App.openDocument(str(fcstd_path))
 try:
  jobs=[o for o in doc.Objects if module(o)=="Path.Main.Job"]
  pockets=[o for o in doc.Objects if module(o)=="Path.Op.Pocket"]
  surfaces=[o for o in doc.Objects if module(o)=="Path.Op.Surface"]
  ctrls=[o for o in doc.Objects if module(o)=="Path.Tool.Controller"]
  tools=[o for o in doc.Objects if module(o)=="Path.Tool.Bit"]
  if len(jobs)!=1 or len(pockets)!=1 or len(surfaces)!=1 or len(ctrls)!=2 or len(tools)!=2:return False
  job=jobs[0];pocket=pockets[0];surface=surfaces[0]
  if job.Operations.Group!=[pocket,surface] or len(job.Model.Group)!=1:return False
  model=job.Model.Group[0]
  if module(model)!="draftobjects.clone" or not same_shape(model.Shape,expected):return False
  if str(job.PostProcessor).lower()!="linuxcnc" or list(job.Fixtures)!=["G54"] or bool(job.SplitOutput):return False
  if os.path.normpath(str(job.PostProcessorOutputFile))!="/home/user/Desktop/task-18.nc":return False
  stock=job.Stock
  stock_expected=Part.makeBox(120,80,18,App.Vector(-60,-40,0))
  if module(stock)!="Path.Main.Stock" or not same_shape(stock.Shape,stock_expected):return False
  if any(not close(getattr(stock,name),0) for name in ("ExtXneg","ExtXpos","ExtYneg","ExtYpos","ExtZneg","ExtZpos")):return False
  by_number={int(tc.ToolNumber):tc for tc in ctrls}
  if set(by_number)!={1,2} or [int(tc.ToolNumber) for tc in job.Tools.Group]!=[1,2]:return False
  t1,t2=by_number[1],by_number[2]
  if pocket.ToolController!=t1 or surface.ToolController!=t2:return False
  if t1.Tool not in tools or t2.Tool not in tools or t1.Tool==t2.Tool:return False
  for tc,diameter,shape_name in ((t1,10,"endmill"),(t2,6,"ballend")):
   tool=tc.Tool
   if not close(tool.Diameter,diameter) or not close(tool.ShankDiameter,diameter) or not close(tool.Length,50) or str(tool.ShapeName)!=shape_name:return False
   if tool.Shape.isNull() or len(tool.Shape.Solids)!=1:return False
   if not close(tc.SpindleSpeed,7000) or str(tc.SpindleDir)!="Forward":return False
   if not close(tc.HorizFeed.getValueAs("mm/min").Value,500) or not close(tc.VertFeed.getValueAs("mm/min").Value,500):return False
  if not close(t1.Tool.CuttingEdgeHeight,25):return False
  if face_types(pocket,model)!={"Plane","Sphere"} or face_types(surface,model)!={"Plane","Sphere"}:return False
  if not bool(pocket.Active) or bool(pocket.ProcessStockArea) or not close(pocket.ExtraOffset,0.5):return False
  if not close(pocket.StartDepth,18) or not close(pocket.FinalDepth,10) or not close(pocket.StepDown,2) or not close(float(pocket.StepOver),50):return False
  if pocket.SafeHeight.Value<20-1e-7 or pocket.ClearanceHeight.Value<23-1e-7:return False
  if not bool(surface.Active) or not close(surface.StartDepth,18) or not close(surface.FinalDepth,10) or not close(surface.DepthOffset,0):return False
  if str(surface.ScanType)!="Planar" or str(surface.LayerMode)!="Single-pass" or str(surface.BoundBox)!="BaseBoundBox":return False
  stepover=t2.Tool.Diameter.Value*float(surface.StepOver)/100.0
  if stepover<=0 or stepover>1.5+1e-9 or not close(stepover,1.5):return False
  if surface.SampleInterval.Value<=0 or surface.SampleInterval.Value>1.5:return False
  doc.recompute();doc.recompute()
  if list(pocket.State)!=["Up-to-date"] or list(surface.State)!=["Up-to-date"]:return False
  pm,pc=path_stats(pocket);sm,sc=path_stats(surface)
  if pm<200 or sm<500 or len(pc)<200 or len(sc)<450:return False
  if not close(min(p[2] for p in pc),12,0.01) or not close(max(p[2] for p in pc),16,0.01):return False
  if not close(min(p[2] for p in sc),10,0.01) or max(p[2] for p in sc)<=17:return False
  sections=PathPostCommand.buildPostList(job)
  if len(sections)!=1:return False
  PostProcessor.load("linuxcnc").export(sections[0][1],str(repost_path),job.PostProcessorArgs)
  repost_sig=code_signature(repost_path);submitted_sig=code_signature(nc_path)
  if repost_sig!=submitted_sig:
   return False
  return True
 finally:
  App.closeDocument(doc.Name)

ok=False
try:ok=validate(pathlib.Path(os.environ["TASK18_STEP"]),pathlib.Path(os.environ["TASK18_FCSTD"]),pathlib.Path(os.environ["TASK18_NC"]),pathlib.Path(os.environ["TASK18_REPOST"]))
except Exception as error:
 print("task-18 child: %s"%error,file=sys.stderr)
 traceback.print_exc()
pathlib.Path(os.environ["TASK18_RESULT"]).write_text(json.dumps({"ok":bool(ok)},sort_keys=True),encoding="utf-8")
raise SystemExit(0 if ok else 1)
'''


def validate_freecad(step_path, fcstd_path, nc_path, workdir):
    child = workdir / "validate_task18.py"
    repost = workdir / "repost.nc"
    result_file = workdir / "result.json"
    child.write_text(CHILD_SOURCE, encoding="utf-8")
    child.chmod(0o600)
    try:
        result = subprocess.run(
            [
                str(FREECADCMD),
                str(child),
            ],
            cwd=workdir,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=240,
            check=False,
            env={
                "HOME": str(workdir),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": "/usr/bin:/bin",
                "TMPDIR": str(workdir),
                "TASK18_STEP": str(step_path),
                "TASK18_FCSTD": str(fcstd_path),
                "TASK18_NC": str(nc_path),
                "TASK18_REPOST": str(repost),
                "TASK18_RESULT": str(result_file),
            },
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    try:
        payload = json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        payload = None
    if payload != {"ok": True}:
        if result.stderr:
            print(result.stderr[-4000:], file=sys.stderr)
        return False
    return regular_file(repost, 10_000, 2_000_000)


def main():
    if not FREECADCMD.is_file():
        return fail("freecadcmd missing")
    if not regular_file(STEP, 2_000, 2_000_000):
        return fail("invalid STEP file")
    if sha256(STEP) != EXPECTED_STEP_SHA256:
        return fail("wrong init STEP")
    if not validate_archive(FCSTD):
        return fail("invalid FCStd archive")
    if not validate_nc(NC):
        return fail("invalid NC semantics")
    with tempfile.TemporaryDirectory(prefix="task-18-eval-") as directory:
        workdir = Path(directory)
        frozen_step = workdir / "relief_surface.step"
        frozen_fcstd = workdir / "task-18.FCStd"
        frozen_nc = workdir / "task-18.nc"
        if not freeze_file(STEP, frozen_step, 2_000, 2_000_000):
            return fail("could not freeze STEP")
        if not freeze_file(FCSTD, frozen_fcstd, 10_000, 10_000_000):
            return fail("could not freeze FCStd")
        if not freeze_file(NC, frozen_nc, 10_000, 2_000_000):
            return fail("could not freeze NC")
        if sha256(frozen_step) != EXPECTED_STEP_SHA256:
            return fail("STEP changed during evaluation")
        if not validate_freecad(frozen_step, frozen_fcstd, frozen_nc, workdir):
            return fail("FreeCAD validation failed")
    return True


if __name__ == "__main__":
    try:
        result = main()
    except Exception as error:
        print("task-18 evaluator exception: " + str(error), file=sys.stderr)
        result = False
    print(True if result else False)
