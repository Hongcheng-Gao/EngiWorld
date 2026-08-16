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
REV_A = TARGET / "revision_A.FCStd"
REV_B = TARGET / "revision_B.FCStd"
FCSTD = TARGET / "task-16_B.FCStd"
NC = TARGET / "task-16_B.nc"
FREECADCMD = Path("/usr/bin/freecadcmd")
EXPECTED_A_SHA256 = "b57967bf2111f32cf46af5a7ad3dc40681ac531ef4e85aa590c93898e4c32526"
EXPECTED_B_SHA256 = "57a44df014456db5ca83832c6f7d52596c1c80e460ba9b4a2dc3dd3262950ca4"
EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
TIMESTAMP_RE = re.compile(r"\(Output Time:[^()\r\n]*\)")
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.ASCII)
ALLOWED_ADDRESSES = {"N", "G", "M", "T", "H", "S", "F", "X", "Y", "Z", "I", "J", "R", "Q", "P"}
ALLOWED_G = {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 80, 81, 82, 83, 90, 94, 98, 99}
ALLOWED_M = {2, 3, 4, 5, 6, 7, 8, 9, 30}
G_MODAL_GROUPS = (
    {0, 1, 2, 3, 80, 81, 82, 83},
    {17}, {21}, {40}, {43, 49}, {54}, {90}, {94}, {98, 99},
)
REQUIRED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("Path.Main.Stock", "StockFromBase"): 1,
    ("Path.Tool.Controller", "ToolController"): 2,
    ("Path.Tool.Bit", "ToolBit"): 2,
    ("Path.Op.PocketShape", "ObjectPocket"): 1,
    ("Path.Op.Drilling", "ObjectDrilling"): 1,
    ("draftobjects.clone", "Clone"): 1,
})
OPTIONAL_PROXIES = {}


def fail(message):
    print("task-16 evaluator: " + message, file=sys.stderr)
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
    return result


def validate_archive(path, expected, null_features):
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
            null_count = proxies.pop((None, None), 0)
            if (isinstance(null_features, tuple) and not null_features[0] <= null_count <= null_features[1]) or (not isinstance(null_features, tuple) and null_count != null_features):
                return False
            if expected is None:
                return not proxies
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
    if not regular_file(path, 2_000, 2_000_000): return False
    blocks = parse_nc(path)
    if blocks is None: return False
    state = {"units": None, "absolute": False, "motion": None, "cycle": None, "tool": None,
             "changed": False, "speed": None, "feed": None, "spindle": False, "retract": None,
             "X": None, "Y": None, "Z": None}
    changed_tools, cycles, ended, saw_g54 = [], [], False, False
    t1_cut_z = []
    for index, block in enumerate(blocks):
        words = dict(block)
        gs = [integral(value) for letter, value in block if letter == "G"]
        ms = [integral(value) for letter, value in block if letter == "M"]
        if ended or any(code is None or code not in ALLOWED_G for code in gs) or any(code is None or code not in ALLOWED_M for code in ms): return False
        if any(sum(code in group for code in gs) > 1 for group in G_MODAL_GROUPS): return False
        if len(ms) != len(set(ms)) or (3 in ms and 4 in ms): return False
        if 21 in gs: state["units"] = "mm"
        if 90 in gs: state["absolute"] = True
        if 54 in gs: saw_g54 = True
        if 98 in gs: state["retract"] = 98
        if 99 in gs: state["retract"] = 99
        for code in gs:
            if code in {0, 1, 2, 3}: state["motion"] = code
            if code in {80, 81, 82, 83}: state["cycle"] = None if code == 80 else code
        if "T" in words:
            tool = integral(words["T"])
            if tool not in {1, 2}: return False
            if tool != state["tool"]: state["changed"] = False
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
            state["changed"] = True; changed_tools.append(state["tool"])
        if 4 in ms: return False
        if 3 in ms:
            if not state["changed"] or state["speed"] is None: return False
            state["spindle"] = True
        explicit_motion = next((code for code in gs if code in {0, 1, 2, 3}), None)
        if state["tool"] == 2 and explicit_motion in {1, 2, 3}: return False
        if explicit_motion == 0 and ("X" in words or "Y" in words):
            rapid_z = words.get("Z", state["Z"])
            if rapid_z is None or rapid_z <= 18: return False
        cycle_initial_z = state["Z"]
        for axis in ("X", "Y", "Z"):
            if axis in words: state[axis] = words[axis]
        explicit_cycle = next((code for code in gs if code in {81, 82, 83}), None)
        if explicit_cycle is not None:
            if state["tool"] != 2 or state["units"] != "mm" or not state["absolute"] or not saw_g54 or not state["changed"] or not state["spindle"] or state["feed"] is None: return False
            if state["X"] is None or state["Y"] is None or "Z" not in words or "R" not in words: return False
            if explicit_cycle == 82 and ("P" not in words or words["P"] < 0): return False
            if explicit_cycle == 83 and ("Q" not in words or words["Q"] <= 0): return False
            if not close(words["Z"], 4) or words["R"] <= 18: return False
            cycles.append((round(state["X"], 4), round(state["Y"], 4), round(words["Z"], 4)))
            state["Z"] = cycle_initial_z if state["retract"] == 98 else words["R"]
        elif state["tool"] == 1 and state["motion"] in {1, 2, 3} and state["Z"] is not None:
            if not state["spindle"] or state["feed"] is None: return False
            t1_cut_z.append(state["Z"])
        if 2 in ms or 30 in ms:
            if index != len(blocks) - 1 or state["spindle"]: return False
            ended = True
    expected_holes = {(-48.0, -28.0), (42.0, -28.0), (-48.0, 24.0), (42.0, 24.0)}
    return (ended and changed_tools == [1, 2] and len(cycles) == 4 and
            {value[:2] for value in cycles} == expected_holes and
            t1_cut_z and close(min(t1_cut_z), 10) and min(t1_cut_z) >= 10 - 1e-6)


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
EXPECTED_A_SHA256="b57967bf2111f32cf46af5a7ad3dc40681ac531ef4e85aa590c93898e4c32526"
EXPECTED_B_SHA256="57a44df014456db5ca83832c6f7d52596c1c80e460ba9b4a2dc3dd3262950ca4"
ENDMILL_FILE="/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Endmill.fctb"
DRILL_FILE="/usr/share/freecad/Mod/Path/Tools/Bit/5mm_Drill.fctb"
SPECS={"A":{"pocket":(60.0,36.0),"holes":((-45.0,-26.0),(45.0,-26.0),(-45.0,26.0),(45.0,26.0))},"B":{"pocket":(72.0,44.0),"holes":((-48.0,-28.0),(42.0,-28.0),(-48.0,24.0),(42.0,24.0))}}

def close(a,b,t=1e-6):
 try:return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=t
 except (TypeError,ValueError):return False
def proxy_module(o): return getattr(getattr(o,"Proxy",None).__class__,"__module__","")
def same_volume(a,b,t=1e-5): return a.isValid() and b.isValid() and a.cut(b).Volume<=t and b.cut(a).Volume<=t
def exact_bounds(shape,target):
 box=shape.BoundBox;actual=(box.XMin,box.XMax,box.YMin,box.YMax,box.ZMin,box.ZMax)
 return shape.isValid() and all(close(a,b) for a,b in zip(actual,target))
def expected_shape(letter):
 spec=SPECS[letter];l,w=spec["pocket"]
 shape=Part.makeBox(120,80,18,App.Vector(-60,-40,0)).cut(Part.makeBox(l,w,8,App.Vector(-l/2,-w/2,10)))
 for x,y in spec["holes"]:shape=shape.cut(Part.makeCylinder(3,14,App.Vector(x,y,4)))
 return shape
def verify_revision(doc,letter):
 part=doc.getObject("Revision%sPart"%letter);boundary=doc.getObject("Revision%sPocketBoundary"%letter)
 if part is None or boundary is None or not same_volume(part.Shape,expected_shape(letter)):return None
 spec=SPECS[letter];l,w=spec["pocket"]
 if str(part.RevisionID)!=letter or not close(part.PocketLength,l) or not close(part.PocketWidth,w) or not close(part.PocketFloorZ,10) or not close(part.HoleDiameter,6) or not close(part.HoleFloorZ,4):return None
 if boundary.Part!=part or len(boundary.Shape.Faces)!=1 or len(boundary.Shape.Edges)!=4 or len(boundary.Shape.Vertexes)!=4 or not exact_bounds(boundary.Shape,(-l/2,l/2,-w/2,w/2,18,18)) or not close(boundary.Shape.Area,l*w):return None
 records=[]
 for i,xy in enumerate(spec["holes"],1):
  o=doc.getObject("Revision%sH%02d"%(letter,i))
  if o is None or str(o.HoleID)!="H%02d"%i or not close(o.CenterX,xy[0]) or not close(o.CenterY,xy[1]) or not close(o.Diameter,6) or not close(o.TopZ,18) or not close(o.BottomZ,4):return None
  records.append(o)
 return part,boundary,records
def command_signature(op):
 out=[]
 for c in op.Path.Commands:
  out.append((str(c.Name).upper().replace(" ",""),tuple(sorted((str(k),round(float(v),6)) for k,v in c.Parameters.items()))))
 return tuple(out)
def segment_distance(px,py,a,b):
 ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay
 if close(dx,0) and close(dy,0):return math.hypot(px-ax,py-ay)
 t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
 return math.hypot(px-(ax+t*dx),py-(ay+t*dy))
def cut_segments(op):
 pos={"X":None,"Y":None,"Z":None};segments=[]
 for c in op.Path.Commands:
  name=str(c.Name).upper().replace(" ","");before=dict(pos)
  for axis in pos:
   if axis in c.Parameters:pos[axis]=float(c.Parameters[axis])
  if name=="G1" and all(before[a] is not None and pos[a] is not None for a in pos):
   segments.append((before["X"],before["Y"],before["Z"],pos["X"],pos["Y"],pos["Z"]))
  elif name in {"G2","G3"}:
   if not all(before[a] is not None and pos[a] is not None for a in pos) or "I" not in c.Parameters or "J" not in c.Parameters:return None
   cx=before["X"]+float(c.Parameters["I"]);cy=before["Y"]+float(c.Parameters["J"]);r=math.hypot(before["X"]-cx,before["Y"]-cy)
   a0=math.atan2(before["Y"]-cy,before["X"]-cx);a1=math.atan2(pos["Y"]-cy,pos["X"]-cx)
   if name=="G2":
    while a1>=a0:a1-=2*math.pi
   else:
    while a1<=a0:a1+=2*math.pi
   sweep=a1-a0;count=max(8,int(abs(sweep)*max(r,1)/0.5));angles={a0+sweep*i/count for i in range(1,count+1)}
   low,high=min(a0,a1),max(a0,a1);first=int(math.floor(low/(math.pi/2)))-1;last_cardinal=int(math.ceil(high/(math.pi/2)))+1
   angles.update(k*math.pi/2 for k in range(first,last_cardinal+1) if low-1e-12<=k*math.pi/2<=high+1e-12)
   ordered=sorted(angles,reverse=sweep<0);last=(before["X"],before["Y"]);previous_z=before["Z"]
   for a in ordered:
    fraction=(a-a0)/sweep;cur=(cx+r*math.cos(a),cy+r*math.sin(a));z=before["Z"]+(pos["Z"]-before["Z"])*fraction;segments.append((last[0],last[1],previous_z,cur[0],cur[1],z));last=cur;previous_z=z
 return segments
def validate_pocket_path(op):
 segments=cut_segments(op)
 if not segments:return False
 pos={"X":None,"Y":None,"Z":None}
 for c in op.Path.Commands:
  name=str(c.Name).upper().replace(" ","");before=dict(pos)
  if name=="G0" and any(axis in c.Parameters for axis in ("X","Y")):
   effective_z=float(c.Parameters["Z"]) if "Z" in c.Parameters else before["Z"]
   if effective_z is None or effective_z<=18:return False
  for axis in pos:
   if axis in c.Parameters:pos[axis]=float(c.Parameters[axis])
 if any(min(z1,z2)<10-1e-6 or x1<-32-1e-4 or x1>32+1e-4 or x2<-32-1e-4 or x2>32+1e-4 or y1<-18-1e-4 or y1>18+1e-4 or y2<-18-1e-4 or y2>18+1e-4 for x1,y1,z1,x2,y2,z2 in segments if min(z1,z2)<18-1e-6):return False
 final=[(x1,y1,x2,y2) for x1,y1,z1,x2,y2,z2 in segments if close(z1,10) and close(z2,10)]
 if not final:return False
 if min(min(s[0],s[2]) for s in final)>-32+1e-4 or max(max(s[0],s[2]) for s in final)<32-1e-4 or min(min(s[1],s[3]) for s in final)>-18+1e-4 or max(max(s[1],s[3]) for s in final)<18-1e-4:return False
 for x in range(-32,33,2):
  for y in range(-18,19,2):
   if min(segment_distance(x,y,(s[0],s[1]),(s[2],s[3])) for s in final)>4.001:return False
 return True
def comparison_semantics(o,part,records):
 try:
  if o.TypeId!="App::FeaturePython" or proxy_module(o) not in {"","builtins"}:return False
  kinds={"RecordRole":"App::PropertyString","RevisionAFile":"App::PropertyFile","RevisionBFile":"App::PropertyFile","RevisionASHA256":"App::PropertyString","RevisionBSHA256":"App::PropertyString","PocketALength":"App::PropertyLength","PocketAWidth":"App::PropertyLength","PocketBLength":"App::PropertyLength","PocketBWidth":"App::PropertyLength","PocketFloorZ":"App::PropertyLength","HoleAX":"App::PropertyStringList","HoleAY":"App::PropertyStringList","HoleBX":"App::PropertyStringList","HoleBY":"App::PropertyStringList","MachinedRevision":"App::PropertyString","RevisionBPart":"App::PropertyLink","RevisionBHoles":"App::PropertyLinkList"}
  if any(prop not in o.PropertiesList or o.getTypeIdOfProperty(prop)!=kind for prop,kind in kinds.items()):return False
  def values(name):return tuple(float(x) for x in o.getPropertyByName(name))
  return (str(o.RecordRole).strip().upper()=="REVISIONCOMPARISON" and os.path.normpath(str(o.RevisionAFile))=="/home/user/Desktop/revision_A.FCStd" and os.path.normpath(str(o.RevisionBFile))=="/home/user/Desktop/revision_B.FCStd" and str(o.RevisionASHA256).lower()==EXPECTED_A_SHA256 and str(o.RevisionBSHA256).lower()==EXPECTED_B_SHA256 and close(o.PocketALength,60) and close(o.PocketAWidth,36) and close(o.PocketBLength,72) and close(o.PocketBWidth,44) and close(o.PocketFloorZ,10) and values("HoleAX")==(-45,45,-45,45) and values("HoleAY")==(-26,-26,26,26) and values("HoleBX")==(-48,42,-48,42) and values("HoleBY")==(-28,-28,24,24) and str(o.MachinedRevision).strip().upper() in {"B","B ONLY","REVISION B ONLY"} and o.RevisionBPart==part and set(o.RevisionBHoles)==set(records) and len(o.RevisionBHoles)==4)
 except (AttributeError,TypeError,ValueError):return False
def comparison_candidate(o):
 fields={"RecordRole","RevisionAFile","RevisionBFile","RevisionASHA256","RevisionBSHA256","PocketALength","PocketAWidth","PocketBLength","PocketBWidth","PocketFloorZ","HoleAX","HoleAY","HoleBX","HoleBY","MachinedRevision","RevisionBPart","RevisionBHoles"}
 return o.TypeId=="App::FeaturePython" and bool(fields & set(o.PropertiesList))
def expected_tool_shape(doc,template,name,parameters):
 import Path.Tool.Bit as PathToolBit
 tool=PathToolBit.Factory.CreateFrom(template,name)
 for key,value in parameters.items():setattr(tool,key,value)
 tool.Proxy.loadBitBody(tool,force=True);tool.Proxy._updateBitShape(tool);tool.Proxy.unloadBitBody(tool);doc.recompute()
 return tool
def cycle_signature(op):
 out=[];pos={"X":None,"Y":None,"Z":None};cycle_active=False;retract=None
 for c in op.Path.Commands:
  n=str(c.Name).upper().replace(" ","");before=dict(pos)
  if n=="G98":retract=98
  if n=="G99":retract=99
  if n in {"G1","G2","G3"}:return None
  if n=="G0" and any(axis in c.Parameters for axis in ("X","Y")):
   effective_z=float(c.Parameters["Z"]) if "Z" in c.Parameters else before["Z"]
   if effective_z is None or effective_z<=18:return None
  for axis in pos:
   if axis in c.Parameters:pos[axis]=float(c.Parameters[axis])
  if n in {"G73","G81","G82","G83"}:
   cycle_active=True;out.append((n,round(float(c.Parameters["X"]),5),round(float(c.Parameters["Y"]),5),round(float(c.Parameters["Z"]),5),round(float(c.Parameters["R"]),5)));pos["Z"]=before["Z"] if retract==98 else float(c.Parameters["R"])
  elif n=="G80":cycle_active=False
  elif cycle_active and n!="G0" and any(axis in c.Parameters for axis in ("X","Y","Z")):return None
 return tuple(out)
def validate(a_path,b_path,fcstd_path,repost_path,fresh_path):
 if tuple(App.Version()[:4])!=EXPECTED_VERSION or App.Version()[-1]!=EXPECTED_COMMIT:return False
 if hashlib.sha256(a_path.read_bytes()).hexdigest()!=EXPECTED_A_SHA256 or hashlib.sha256(b_path.read_bytes()).hexdigest()!=EXPECTED_B_SHA256:return False
 a=App.openDocument(str(a_path));b=App.openDocument(str(b_path));sa=verify_revision(a,"A");sb=verify_revision(b,"B")
 if len(a.Objects)!=7 or len(b.Objects)!=7 or sa is None or sb is None or sa[0].Shape.cut(sb[0].Shape).Volume<=1 or sb[0].Shape.cut(sa[0].Shape).Volume<=1:return False
 doc=App.openDocument(str(fcstd_path))
 try:
  sdoc=verify_revision(doc,"B")
  if sdoc is None or not 18<=len(doc.Objects)<=40:return False
  part,boundary,records=sdoc
  jobs=[o for o in doc.Objects if proxy_module(o)=="Path.Main.Job"]
  pockets=[o for o in doc.Objects if proxy_module(o)=="Path.Op.PocketShape"]
  drills=[o for o in doc.Objects if proxy_module(o)=="Path.Op.Drilling"]
  ctrls=[o for o in doc.Objects if proxy_module(o)=="Path.Tool.Controller"]
  tools=[o for o in doc.Objects if proxy_module(o)=="Path.Tool.Bit"]
  comparison_candidates=[o for o in doc.Objects if comparison_candidate(o)]
  if len(comparison_candidates)!=1 or not comparison_semantics(comparison_candidates[0],part,records) or len(jobs)!=1 or len(pockets)!=1 or len(drills)!=1 or len(ctrls)!=2 or len(tools)!=2:return False
  job=jobs[0];pocket=pockets[0];drill=drills[0]
  if job.Operations.Group!=[pocket,drill] or [int(c.ToolNumber) for c in job.Tools.Group]!=[1,2] or str(job.PostProcessor).lower()!="linuxcnc" or list(job.Fixtures)!=["G54"] or bool(job.SplitOutput):return False
  if os.path.normpath(str(job.PostProcessorOutputFile))!="/home/user/Desktop/task-16_B.nc" or len(job.Model.Group)!=1:return False
  model=job.Model.Group[0];stock=job.Stock
  if proxy_module(model)!="draftobjects.clone" or list(model.Objects)!=[part] or not same_volume(model.Shape,sb[0].Shape):return False
  if proxy_module(stock)!="Path.Main.Stock" or stock.Base!=job.Model or any(not close(getattr(stock,name),0) for name in ("ExtXneg","ExtXpos","ExtYneg","ExtYpos","ExtZneg","ExtZpos")) or not same_volume(stock.Shape,Part.makeBox(120,80,18,App.Vector(-60,-40,0))):return False
  if pocket.ToolController not in ctrls or drill.ToolController not in ctrls or pocket.ToolController==drill.ToolController:return False
  endmill=pocket.ToolController.Tool;drillbit=drill.ToolController.Tool
  if not close(endmill.Diameter,8) or not 8<=float(endmill.CuttingEdgeHeight.Value)<=float(endmill.Length.Value)<=300 or not 0<float(endmill.ShankDiameter.Value)<=50:return False
  if not close(drillbit.Diameter,6) or not close(drillbit.TipAngle,118) or not 14<=float(drillbit.Length.Value)<=300:return False
  expected_endmill=expected_tool_shape(doc,ENDMILL_FILE,"ExpectedTask16Endmill",{"Diameter":8,"ShankDiameter":endmill.ShankDiameter.Value,"CuttingEdgeHeight":endmill.CuttingEdgeHeight.Value,"Length":endmill.Length.Value})
  expected_drill=expected_tool_shape(doc,DRILL_FILE,"ExpectedTask16Drill",{"Diameter":6,"TipAngle":118,"Length":drillbit.Length.Value})
  for op,num,diameter,shape_name,expected_shape in ((pocket,1,8,"endmill",expected_endmill.Shape),(drill,2,6,"drill",expected_drill.Shape)):
   tc=op.ToolController;tool=tc.Tool
   if int(tc.ToolNumber)!=num or tool not in tools or str(tool.ShapeName)!=shape_name or os.path.basename(str(tool.BitShape))!=shape_name+".fcstd" or tool.Shape.isNull() or len(tool.Shape.Solids)!=1 or not same_volume(tool.Shape,expected_shape,1e-4) or not close(tool.Diameter,diameter) or not close(tc.SpindleSpeed,7000) or str(tc.SpindleDir)!="Forward" or not close(tc.HorizFeed.getValueAs("mm/min").Value,500) or not close(tc.VertFeed.getValueAs("mm/min").Value,500):return False
  doc.removeObject(expected_endmill.Name);doc.removeObject(expected_drill.Name);doc.recompute()
  if not close(drill.ToolController.Tool.TipAngle,118) or not close(pocket.StartDepth,18) or not close(pocket.FinalDepth,10) or not math.isfinite(float(pocket.StepDown.Value)) or pocket.StepDown.Value<=0 or pocket.StepDown.Value>8 or not math.isfinite(float(pocket.StepOver)) or pocket.StepOver<=0 or pocket.StepOver>100 or pocket.SafeHeight.Value<=18 or pocket.ClearanceHeight.Value<=18:return False
  if str(pocket.CutMode) not in {"Climb","Conventional"} or str(pocket.OffsetPattern) not in {"ZigZag","Offset","ZigZagOffset","Line","Grid"} or pocket.ToolController.Tool.Diameter.Value!=8:return False
  base=list(pocket.Base)
  if len(base)!=1 or base[0][0]!=boundary or set(base[0][1])!={"Face1"} or not validate_pocket_path(pocket):return False
  if not close(drill.StartDepth,18) or not close(drill.FinalDepth,4) or drill.SafeHeight.Value<=18 or drill.ClearanceHeight.Value<=18 or str(drill.RetractMode) not in {"G98","G99"} or (bool(drill.KeepToolDown)!=(str(drill.RetractMode)=="G99")):return False
  if bool(drill.PeckEnabled) and (not math.isfinite(float(drill.PeckDepth.Value)) or drill.PeckDepth.Value<=0):return False
  if bool(drill.DwellEnabled) and (not math.isfinite(float(drill.DwellTime)) or drill.DwellTime<0):return False
  if bool(drill.PeckEnabled) and bool(drill.DwellEnabled):return False
  drill_base=list(drill.Base)
  if not drill_base or any(obj!=model or not tuple(subs) for obj,subs in drill_base):return False
  sig=cycle_signature(drill);expected=set(SPECS["B"]["holes"])
  if len(sig)!=4 or {v[1:3] for v in sig}!=expected or any(not close(v[3],4) or v[4]<=18 for v in sig):return False
  sections=PathPostCommand.buildPostList(job)
  if len(sections)!=1:return False
  PostProcessor.load("linuxcnc").export(sections[0][1],str(repost_path),str(job.PostProcessorArgs))
  saved=(command_signature(pocket),command_signature(drill))
  for o in doc.Objects:o.touch()
  doc.recompute();doc.recompute()
  if any(set(map(str,o.State)) & {"Touched","Invalid","Error"} for o in doc.Objects):return False
  if (command_signature(pocket),command_signature(drill))!=saved or not validate_pocket_path(pocket) or cycle_signature(drill)!=sig:return False
  sections=PathPostCommand.buildPostList(job)
  if len(sections)!=1:return False
  PostProcessor.load("linuxcnc").export(sections[0][1],str(fresh_path),str(job.PostProcessorArgs))
  return True
 finally:
  App.closeDocument(doc.Name);App.closeDocument(b.Name);App.closeDocument(a.Name)

marker,a_arg,b_arg,fcstd_arg,repost_arg,fresh_arg=sys.argv[1:7]
try:result=validate(pathlib.Path(a_arg),pathlib.Path(b_arg),pathlib.Path(fcstd_arg),pathlib.Path(repost_arg),pathlib.Path(fresh_arg))
except Exception as exc:
 print("task-16 FreeCAD validation: %s: %s"%(type(exc).__name__,exc),file=sys.stderr);result=False
print(marker+"="+("True" if result else "False"))
'''


def run_freecad_validation():
    try:
        executable = FREECADCMD.resolve(strict=True); info = executable.stat()
    except OSError: return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH): return False
    marker = "TASK16_" + secrets.token_hex(24)
    with tempfile.TemporaryDirectory(prefix="engiworld-task16-") as raw:
        temp = Path(raw); script = temp / "validate.py"; repost = temp / "repost.nc"; fresh = temp / "fresh.nc"
        script.write_text(CHILD_SOURCE, encoding="utf-8"); script.chmod(0o600)
        args = [str(script), marker, str(REV_A), str(REV_B), str(FCSTD), str(repost), str(fresh)]
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
    if not regular_file(REV_A, 2_000, 10_000_000) or sha256(REV_A) != EXPECTED_A_SHA256 or not validate_archive(REV_A, None, 4): return fail("invalid Revision A init")
    if not regular_file(REV_B, 2_000, 10_000_000) or sha256(REV_B) != EXPECTED_B_SHA256 or not validate_archive(REV_B, None, 4): return fail("invalid Revision B init")
    if not validate_archive(FCSTD, REQUIRED_PROXIES, (3, 20)): return fail("invalid answer FCStd archive")
    if not validate_nc(NC): return fail("invalid NC semantics")
    if not run_freecad_validation(): return fail("native FreeCAD validation or fresh repost failed")
    return True


if __name__ == "__main__":
    try: outcome = main()
    except Exception as exc:
        print("task-16 evaluator: %s: %s" % (type(exc).__name__, exc), file=sys.stderr); outcome = False
    print("True" if outcome else "False")
