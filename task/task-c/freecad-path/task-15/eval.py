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
from pathlib import Path

TARGET = Path("/home/user/Desktop")
INIT = TARGET / "risky_setup.FCStd"
FCSTD = TARGET / "task-15.FCStd"
NC = TARGET / "task-15.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_INIT_SHA256 = "adb7b1faef3cf5a65e9a82f1df18b54411a9a604b7c53d607c00481ef211fa82"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "R", "Q", "P"}
ALLOWED_G = {0, 17, 21, 40, 43, 49, 54, 80, 81, 82, 83, 90, 94, 98, 99}
ALLOWED_M = {2, 3, 4, 5, 6, 7, 8, 9}
G_MODAL_GROUPS = ({0, 80, 81, 82, 83}, {17}, {21}, {40}, {43, 49}, {54}, {90}, {94}, {98, 99})
REQUIRED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("Path.Main.Stock", "StockFromBase"): 1,
    ("Path.Tool.Controller", "ToolController"): 2,
    ("Path.Tool.Bit", "ToolBit"): 2,
    ("Path.Op.Drilling", "ObjectDrilling"): 2,
    ("draftobjects.clone", "Clone"): 1,
})
OPTIONAL_PROXIES = {}


def fail(message):
    print("task-15 evaluator: " + message, file=sys.stderr)
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


def proxy_manifest(document):
    root = ET.fromstring(document)
    result = Counter()
    for element in root.iter("Python"):
        module, class_name = element.attrib.get("module"), element.attrib.get("class")
        encoded = element.attrib.get("encoded")
        value = element.attrib.get("value")
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
    return result


def validate_archive(path, expected):
    if not regular_file(path, 2_000 if expected is None else 10_000, 20_000_000):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "Document.xml" not in names or len(names) != len(set(names)) or len(names) > 300:
                return False
            total = 0
            for entry in archive.infolist():
                pure = Path(entry.filename)
                if pure.is_absolute() or ".." in pure.parts or entry.file_size > 20_000_000:
                    return False
                total += entry.file_size
                if total > 60_000_000 or pure.suffix.lower() in {".py", ".pyc", ".so", ".sh", ".dll"}:
                    return False
            proxies = proxy_manifest(archive.read("Document.xml"))
            null_features = proxies.pop((None, None), 0)
            if expected is None:
                return null_features == 17 and not proxies
            if null_features != 18:
                return False
            if any(proxies[key] != count for key, count in expected.items()):
                return False
            if any(proxies[key] > count for key, count in OPTIONAL_PROXIES.items()):
                return False
            return not (set(proxies) - set(expected) - set(OPTIONAL_PROXIES))
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError):
        return False


def strip_comments(text):
    output, in_comment = [], False
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        code, index = [], 0
        while index < len(line):
            char = line[index]
            if in_comment:
                if char == "(": return None
                if char == ")": in_comment = False
            elif char == "(": in_comment = True
            elif char == ")": return None
            elif char == ";": break
            else: code.append(char)
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
        if not line or line == "%": continue
        words, cursor = [], 0
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip(): return None
            value = float(match.group(2))
            if not math.isfinite(value): return None
            words.append((match.group(1), value)); cursor = match.end()
        if line[cursor:].strip() or not words or any(letter not in ALLOWED_ADDRESSES for letter, _ in words):
            return None
        if any(sum(letter == key for letter, _ in words) > 1 for key in ALLOWED_ADDRESSES - {"G", "M"}):
            return None
        blocks.append(words)
    return blocks or None


def validate_nc(path):
    if not regular_file(path, 1_500, 1_000_000): return False
    blocks = parse_nc(path)
    if blocks is None: return False
    state = {"units": None, "absolute": False, "cycle": None, "tool": None, "changed": False,
             "speed": None, "feed": None, "spindle": False, "X": None, "Y": None}
    cycles = {1: [], 2: []}; ended = False; saw_g54 = False; changed_tools = []
    for index, block in enumerate(blocks):
        words = dict(block)
        gs = [integral(value) for letter, value in block if letter == "G"]
        ms = [integral(value) for letter, value in block if letter == "M"]
        if ended or any(code is None or code not in ALLOWED_G for code in gs) or any(code is None or code not in ALLOWED_M for code in ms):
            return False
        if any(sum(code in group for code in gs) > 1 for group in G_MODAL_GROUPS): return False
        if len(ms) != len(set(ms)) or (3 in ms and 4 in ms): return False
        if 21 in gs: state["units"] = "mm"
        if 90 in gs: state["absolute"] = True
        if 54 in gs: saw_g54 = True
        for code in gs:
            if code in {80, 81, 82, 83}: state["cycle"] = None if code == 80 else code
        if "T" in words:
            tool = integral(words["T"])
            if tool not in {1, 2}: return False
            if tool != state["tool"]:
                state["changed"] = False
            state["tool"] = tool
        if "H" in words and integral(words["H"]) != state["tool"]: return False
        if "S" in words:
            if not close(words["S"], 7000): return False
            state["speed"] = words["S"]
        if "F" in words:
            if not close(words["F"], 500, 1e-4): return False
            state["feed"] = words["F"]
        if 5 in ms: state["spindle"] = False
        if 6 in ms:
            if state["spindle"] or state["tool"] not in {1, 2}: return False
            state["changed"] = True
            changed_tools.append(state["tool"])
        if 3 in ms or 4 in ms:
            if not state["changed"] or state["speed"] is None: return False
            state["spindle"] = True
        for axis in ("X", "Y"):
            if axis in words: state[axis] = words[axis]
        explicit_cycle = next((code for code in gs if code in {81, 82, 83}), None)
        if explicit_cycle is not None:
            if state["units"] != "mm" or not state["absolute"] or not saw_g54 or not state["changed"] or not state["spindle"] or state["feed"] is None:
                return False
            if state["X"] is None or state["Y"] is None or "Z" not in words or "R" not in words: return False
            if explicit_cycle == 82 and ("P" not in words or words["P"] < 0): return False
            if explicit_cycle == 83 and ("Q" not in words or words["Q"] <= 0): return False
            expected_z = 17.0 if state["tool"] == 1 else 8.0
            if not close(words["Z"], expected_z) or words["R"] <= 18.0: return False
            cycles[state["tool"]].append((round(state["X"], 4), round(state["Y"], 4), round(words["Z"], 4)))
        if 2 in ms:
            if index != len(blocks) - 1 or state["spindle"]: return False
            ended = True
    expected = {(x, y) for y in (-27.0, -9.0, 9.0, 27.0) for x in (-45.0, -15.0, 15.0, 45.0)}
    risk = {(45.0, -27.0), (-45.0, 27.0), (45.0, 27.0)}
    safe = expected - risk
    return ended and changed_tools == [1, 2] and all(len(cycles[t]) == 13 for t in (1, 2)) and {p[:2] for p in cycles[1]} == safe and {p[:2] for p in cycles[2]} == safe


def normalized_nc(path):
    try: text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError): return None
    return TIMESTAMP_RE.sub("(Output Time:<normalized>)", text).replace("\r\n", "\n").replace("\r", "\n")


CHILD_SOURCE = r'''
import hashlib, json, math, os, pathlib, sys
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor

EXPECTED_VERSION=("0","21","2","33771 (Git)")
EXPECTED_COMMIT="b9bfa5c5507506e4515816414cd27f4851d00489"
EXPECTED_INIT_SHA256="adb7b1faef3cf5a65e9a82f1df18b54411a9a604b7c53d607c00481ef211fa82"
HOLES={"H%02d"%(r*4+c+1):(x,y) for r,y in enumerate((-27.0,-9.0,9.0,27.0)) for c,x in enumerate((-45.0,-15.0,15.0,45.0))}
EXPECTED_FIXTURES={"FixtureSouthEast":(50,-32,60,-22),"FixtureNorthWest":(-60,22,-50,32),"FixtureNorthEast":(50,22,60,32)}

def close(a,b,t=1e-6): return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=t
def proxy_module(o): return getattr(getattr(o,"Proxy",None).__class__,"__module__","")
def bounds(s):
 b=s.BoundBox; return (b.XMin,b.XMax,b.YMin,b.YMax,b.ZMin,b.ZMax)
def exact_bounds(s,target): return s.isValid() and all(close(a,b) for a,b in zip(bounds(s),target))
def same_volume(a,b,t=1e-6):
 return a.isValid() and b.isValid() and a.cut(b).Volume<=t and b.cut(a).Volume<=t
def circles(s):
 out={}
 for i,e in enumerate(s.Edges,1):
  if isinstance(e.Curve,Part.Circle) and close(e.Curve.Center.z,18) and close(e.Curve.Radius,2.5): out[(round(e.Curve.Center.x,6),round(e.Curve.Center.y,6))]=i
 return out
def all_hole_circles(s):
 return [(round(e.Curve.Center.x,6),round(e.Curve.Center.y,6),round(e.Curve.Center.z,6),round(e.Curve.Radius,6)) for e in s.Edges if isinstance(e.Curve,Part.Circle)]
def point_rect_distance(x,y,b):
 xmin,ymin,xmax,ymax=b; return math.hypot(max(xmin-x,0,x-xmax),max(ymin-y,0,y-ymax))
def verify_setup(doc):
 plate=doc.getObject("WorkpiecePlate"); spec=doc.getObject("ClearanceSpecification")
 if plate is None or spec is None or not exact_bounds(plate.Shape,(-60,60,-40,40,0,18)) or len(circles(plate.Shape))!=16:return None
 if len(plate.Shape.Solids)!=1 or len(plate.Shape.Faces)!=38 or len(plate.Shape.Edges)!=60 or len(plate.Shape.Vertexes)!=40 or not close(plate.Shape.Volume,169658.40734640986,1e-5):return None
 actual_circles=all_hole_circles(plate.Shape);expected_circles={(x,y,z,2.5) for x,y in HOLES.values() for z in (8.0,18.0)}
 if len(actual_circles)!=32 or set(actual_circles)!=expected_circles:return None
 records=[]
 for hid,xy in HOLES.items():
  o=doc.getObject(hid)
  if o is None or str(o.HoleID)!=hid or not close(o.CenterX,xy[0]) or not close(o.CenterY,xy[1]) or not close(o.Diameter,5) or not close(o.TopZ,18) or not close(o.BottomZ,8): return None
  records.append(o)
 fixtures=[]
 for name,target in EXPECTED_FIXTURES.items():
  o=doc.getObject(name)
  expected=Part.makeBox(target[2]-target[0],target[3]-target[1],20,App.Vector(target[0],target[1],18))
  if o is None or not exact_bounds(o.Shape,(target[0],target[2],target[1],target[3],18,38)) or not same_volume(o.Shape,expected): return None
  fixtures.append(o)
 if not close(spec.RequiredClearance,3) or not close(spec.ToolEnvelopeDiameter,12) or set(spec.Fixtures)!=set(fixtures) or set(spec.CandidateHoles)!=set(records): return None
 risk={hid for hid,(x,y) in HOLES.items() if min(point_rect_distance(x,y,b)-6 for b in EXPECTED_FIXTURES.values())<3-1e-9}
 return plate,records,fixtures,set(HOLES)-risk,risk
def cycle_signature(op):
 result=[]
 for c in op.Path.Commands:
  n=str(c.Name).upper().replace(" ","")
  if n in {"G73","G81","G82","G83"}: result.append((n,round(float(c.Parameters["X"]),5),round(float(c.Parameters["Y"]),5),round(float(c.Parameters["Z"]),5),round(float(c.Parameters["R"]),5)))
 return tuple(result)
def validate(init_path,fcstd_path,repost_path,fresh_path):
 if tuple(App.Version()[:4])!=EXPECTED_VERSION or App.Version()[-1]!=EXPECTED_COMMIT or hashlib.sha256(init_path.read_bytes()).hexdigest()!=EXPECTED_INIT_SHA256:return False
 init=App.openDocument(str(init_path)); init_setup=verify_setup(init)
 if init_setup is None or len(init.Objects)!=23:return False
 doc=App.openDocument(str(fcstd_path))
 try:
  setup=verify_setup(doc)
  if setup is None:return False
  plate,records,fixtures,safe,risk=setup
  if str(plate.SourceFile)!="/home/user/Desktop/risky_setup.FCStd" or str(plate.SourceSHA256)!=EXPECTED_INIT_SHA256 or len(doc.Objects)!=37 or not same_volume(plate.Shape,init_setup[0].Shape):return False
  collision=doc.getObject("CollisionFilter")
  jobs=[o for o in doc.Objects if proxy_module(o)=="Path.Main.Job"]
  ops=[o for o in doc.Objects if proxy_module(o)=="Path.Op.Drilling"]
  ctrls=[o for o in doc.Objects if proxy_module(o)=="Path.Tool.Controller"]
  tools=[o for o in doc.Objects if proxy_module(o)=="Path.Tool.Bit"]
  if collision is None or collision.Label!="Collision Filter" or len(jobs)!=1 or len(ops)!=2 or len(ctrls)!=2 or len(tools)!=2:return False
  job=jobs[0]
  if set(collision.SafeHoleIDs)!=safe or set(collision.RiskHoleIDs)!=risk or set(collision.SafeHoles)!={doc.getObject(x) for x in safe} or set(collision.RiskHoles)!={doc.getObject(x) for x in risk}:return False
  if not close(collision.RequiredClearance,3) or not close(collision.ToolEnvelopeDiameter,12) or set(collision.Fixtures)!=set(fixtures) or set(collision.Candidates)!=set(records):return False
  if job.Operations.Group!=ops or [int(c.ToolNumber) for c in job.Tools.Group]!=[1,2] or str(job.PostProcessor).lower()!="linuxcnc" or list(job.Fixtures)!=["G54"] or bool(job.SplitOutput):return False
  if os.path.normpath(str(job.PostProcessorOutputFile))!="/home/user/Desktop/task-15.nc":return False
  if len(job.Model.Group)!=1 or proxy_module(job.Model.Group[0])!="draftobjects.clone" or list(job.Model.Group[0].Objects)!=[plate] or not exact_bounds(job.Model.Group[0].Shape,(-60,60,-40,40,0,18)) or not exact_bounds(job.Stock.Shape,(-60,60,-40,40,0,18)):return False
  expected_xy={HOLES[x] for x in safe}; signatures=[]
  for op in ops:
   tc=op.ToolController; num=int(tc.ToolNumber); tool=tc.Tool
   if num not in {1,2} or tool not in tools or str(tool.ShapeName)!="drill" or not close(tool.Diameter,3 if num==1 else 5) or not close(tool.TipAngle,90 if num==1 else 118) or not close(tool.ToolEnvelopeDiameter,12) or not close(tc.SpindleSpeed,7000) or str(tc.SpindleDir)!="Forward" or not close(tc.HorizFeed.getValueAs("mm/min").Value,500) or not close(tc.VertFeed.getValueAs("mm/min").Value,500):return False
   if not close(op.StartDepth,18) or not close(op.FinalDepth,17 if num==1 else 8):return False
   if str(op.RetractMode) not in {"G98","G99"} or (bool(op.KeepToolDown) != (str(op.RetractMode)=="G99")):return False
   if bool(op.PeckEnabled) and (not math.isfinite(float(op.PeckDepth.Value)) or op.PeckDepth.Value<=0):return False
   if bool(op.DwellEnabled) and (not math.isfinite(float(op.DwellTime)) or op.DwellTime<0):return False
   sig=cycle_signature(op)
   if len(sig)!=13 or {v[1:3] for v in sig}!=expected_xy or any(not close(v[3],17 if num==1 else 8) or v[4]<=18 for v in sig):return False
   signatures.append(sig)
  sections=PathPostCommand.buildPostList(job)
  if len(sections)!=1:return False
  PostProcessor.load("linuxcnc").export(sections[0][1],str(repost_path),str(job.PostProcessorArgs))
  saved=tuple(signatures)
  for o in doc.Objects:o.touch()
  doc.recompute();doc.recompute()
  if any(set(map(str,o.State)) & {"Touched","Invalid","Error"} for o in doc.Objects):return False
  if tuple(cycle_signature(o) for o in ops)!=saved:return False
  sections=PathPostCommand.buildPostList(job)
  if len(sections)!=1:return False
  PostProcessor.load("linuxcnc").export(sections[0][1],str(fresh_path),str(job.PostProcessorArgs))
  return True
 finally:
  App.closeDocument(doc.Name);App.closeDocument(init.Name)

marker,init_arg,fcstd_arg,repost_arg,fresh_arg=sys.argv[1:6]
try: result=validate(pathlib.Path(init_arg),pathlib.Path(fcstd_arg),pathlib.Path(repost_arg),pathlib.Path(fresh_arg))
except Exception as exc:
 print("task-15 FreeCAD validation: %s: %s"%(type(exc).__name__,exc),file=sys.stderr);result=False
print(marker+"="+("True" if result else "False"))
'''


def run_freecad_validation():
    try:
        executable = FREECADCMD.resolve(strict=True); info = executable.stat()
    except OSError: return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH): return False
    marker = "TASK15_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-task15-") as raw:
        temp = Path(raw); script = temp / "validate.py"; repost = temp / "repost.nc"; fresh = temp / "fresh.nc"
        script.write_text(CHILD_SOURCE, encoding="utf-8"); script.chmod(0o600)
        args = [str(script), marker, str(INIT), str(FCSTD), str(repost), str(fresh)]
        command = [str(executable), "-c", "import builtins,sys; sys.argv=%r; builtins.pythonopen=open; exec(compile(open(%r,encoding='utf-8').read(),%r,'exec'))" % (args, str(script), str(script))]
        env = {"PATH":"/usr/bin:/bin","HOME":str(temp),"TMPDIR":str(temp),"LANG":"C.UTF-8","LC_ALL":"C.UTF-8","PYTHONNOUSERSITE":"1","QT_QPA_PLATFORM":"offscreen","XDG_CACHE_HOME":str(temp/".cache"),"XDG_CONFIG_HOME":str(temp/".config")}
        try: completed = subprocess.run(command,cwd=temp,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=300,check=False)
        except (OSError, subprocess.SubprocessError): return False
        expected = marker + "=True"
        if completed.returncode != 0 or [line for line in completed.stdout.splitlines() if line.startswith(marker+"=")] != [expected]:
            if completed.stderr: print(completed.stderr[-4000:], file=sys.stderr)
            return False
        base = normalized_nc(NC)
        return base is not None and base == normalized_nc(repost) == normalized_nc(fresh) and validate_nc(repost) and validate_nc(fresh)


def main():
    if not regular_file(INIT, 2_000, 10_000_000) or sha256(INIT) != EXPECTED_INIT_SHA256 or not validate_archive(INIT, None): return fail("invalid init")
    if not validate_archive(FCSTD, REQUIRED_PROXIES): return fail("invalid FCStd archive")
    if not validate_nc(NC): return fail("invalid NC semantics")
    if not run_freecad_validation(): return fail("native FreeCAD validation or fresh repost failed")
    return True


if __name__ == "__main__":
    try: outcome = main()
    except Exception as exc:
        print("task-15 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr); outcome = False
    print("True" if outcome else "False")
