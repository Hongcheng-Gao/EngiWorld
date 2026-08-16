from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


TARGET = Path(os.environ.get("ENGIWORLD_EVAL_TARGET", "/home/user/Desktop"))
STEP_NAME = "plate_100x60x12.step"
FCSTD_NAME = "task-1.FCStd"
NC_NAME = "task-1.nc"
EXPECTED_STEP_SHA256 = "1e219fdb908ec2b038c532e00f1469adf6e691a774ca82bbf539905266dd3b32"
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl",
    ".ahk", ".scr", ".so", ".dll", ".dylib",
}
EXPECTED_FIXED_PROXIES = Counter({
    ("Path.Main.Job", "ObjectJob"): 1,
    ("Path.Base.SetupSheet", "SetupSheet"): 1,
    ("draftobjects.clone", "Clone"): 1,
    ("Path.Op.MillFace", "ObjectFace"): 1,
})
MARKER = "TASK_V01_RESULT="


def regular_file(path: Path, minimum: int, maximum: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and not path.is_symlink() and minimum <= info.st_size <= maximum


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def no_bypass_files(root: Path) -> bool:
    try:
        for path in root.rglob("*"):
            if path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS:
                return False
    except OSError:
        return False
    return True


def fcstd_preflight(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= 256:
                return False
            total = 0
            document_xml = None
            for info in infos:
                member = PurePosixPath(info.filename)
                if member.is_absolute() or ".." in member.parts or info.flag_bits & 0x1:
                    return False
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    return False
                total += info.file_size
                if info.file_size > 20_000_000 or total > 50_000_000:
                    return False
                if Path(info.filename).suffix.lower() in FORBIDDEN_EXTENSIONS:
                    return False
                if info.filename == "Document.xml":
                    document_xml = archive.read(info)
            if document_xml is None or len(document_xml) > 5_000_000:
                return False
        root = ElementTree.fromstring(document_xml)
        proxies = Counter(
            (element.attrib.get("module", ""), element.attrib.get("class", ""))
            for element in root.iter("Python")
        )
        stock_proxies = sum(
            count for (module, class_name), count in proxies.items()
            if module == "Path.Main.Stock" and class_name in {"StockFromBase", "StockCreateBox"}
        )
        proxies = Counter({
            key: count for key, count in proxies.items()
            if key[0] != "Path.Main.Stock"
        })
        controller_count = proxies.pop(("Path.Tool.Controller", "ToolController"), 0)
        tool_count = proxies.pop(("Path.Tool.Bit", "ToolBit"), 0)
        return (
            stock_proxies == 1
            and controller_count >= 1
            and tool_count >= 1
            and proxies == EXPECTED_FIXED_PROXIES
        )
    except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError):
        return False


CHILD_SOURCE = r'''
import builtins
import json
import math
import os
import pathlib
import re
import sys

builtins.pythonopen = open
import FreeCAD as App
import Part
import Path.Post.Command as PathPostCommand
from Path.Post.Processor import PostProcessor

EXPECTED_VERSION = ("0", "21", "2", "33771 (Git)")
EXPECTED_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
SOURCE_BOUNDS = (-60.0, 60.0, -40.0, 40.0, 0.0, 12.0)
MODEL_BOUNDS = (-60.0, 60.0, -40.0, 40.0, -13.0, -1.0)
STOCK_BOUNDS = (-62.0, 62.0, -42.0, 42.0, -13.0, 0.0)
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)", re.I)


def near(actual, expected, tolerance=1e-6):
    try:
        left = float(actual)
        right = float(expected)
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
        not left.isNull() and not right.isNull()
        and left.isValid() and right.isValid()
        and left.cut(right).Volume <= tolerance
        and right.cut(left).Volume <= tolerance
    )


def flat_bottom_tool(shape, diameter):
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        return False
    box = shape.BoundBox
    expected_area = math.pi * (diameter / 2.0) ** 2
    for face in shape.Faces:
        face_box = face.BoundBox
        if type(face.Surface).__name__ != "Plane":
            continue
        if face_box.ZLength > 1e-4 or not near(face_box.ZMin, box.ZMin, 1e-4):
            continue
        if not near(face_box.XLength, diameter, 1e-3) or not near(face_box.YLength, diameter, 1e-3):
            continue
        if abs(face.Area - expected_area) <= expected_area * 0.02:
            return True
    return False


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
        for match in WORD_RE.finditer(line):
            if line[cursor:match.start()].strip():
                return None
            letter = match.group(1).upper()
            value = float(match.group(2))
            if not math.isfinite(value):
                return None
            if letter != "N":
                value = 0.0 if abs(value) < 5e-7 else round(value, 6)
                words.append((letter, value))
            cursor = match.end()
        if line[cursor:].strip() or not words:
            return None
        if words == [("M", 30.0)]:
            words = [("M", 2.0)]
        result.append(tuple(words))
    return tuple(result)


def point_segment_distance(point, start, end):
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= 1e-12:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    factor = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator
    factor = max(0.0, min(1.0, factor))
    return math.hypot(point[0] - (start[0] + factor * dx), point[1] - (start[1] + factor * dy))


def face_segments(operation):
    position = {"X": None, "Y": None, "Z": None}
    segments = []
    minimum_z = math.inf
    for command in operation.Path.Commands:
        name = str(command.Name).upper().replace(" ", "")
        before = dict(position)
        for axis in position:
            if axis in command.Parameters:
                position[axis] = float(command.Parameters[axis])
        if name == "G0":
            moved_xy = (
                before["X"] is not None and before["Y"] is not None
                and position["X"] is not None and position["Y"] is not None
                and (not near(before["X"], position["X"]) or not near(before["Y"], position["Y"]))
            )
            if moved_xy and (position["Z"] is None or position["Z"] <= 0.0):
                return None
            if position["Z"] is not None and position["Z"] <= 0.0:
                return None
            continue
        if name not in {"G1", "G2", "G3"}:
            continue
        if position["Z"] is not None:
            minimum_z = min(minimum_z, position["Z"])
        if None in (before["X"], before["Y"], before["Z"], position["X"], position["Y"], position["Z"]):
            continue
        if not near(before["Z"], -1.0, 1e-3) or not near(position["Z"], -1.0, 1e-3):
            continue
        start = (before["X"], before["Y"])
        finish = (position["X"], position["Y"])
        if name == "G1":
            if math.dist(start, finish) > 1e-7:
                segments.append((start, finish))
            continue
        if "I" not in command.Parameters or "J" not in command.Parameters:
            return None
        center = (start[0] + float(command.Parameters["I"]), start[1] + float(command.Parameters["J"]))
        radius = math.dist(start, center)
        if radius <= 1e-8 or abs(math.dist(finish, center) - radius) > 0.02:
            return None
        start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
        finish_angle = math.atan2(finish[1] - center[1], finish[0] - center[0])
        if name == "G2":
            while finish_angle >= start_angle:
                finish_angle -= math.tau
        else:
            while finish_angle <= start_angle:
                finish_angle += math.tau
        count = max(2, int(math.ceil(abs(finish_angle - start_angle) * radius / 0.5)))
        previous = start
        for index in range(1, count + 1):
            angle = start_angle + (finish_angle - start_angle) * index / count
            point = (center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle))
            segments.append((previous, point))
            previous = point
    if minimum_z < -1.001 or not segments:
        return None
    return segments


def full_face_coverage(operation, diameter):
    segments = face_segments(operation)
    if segments is None:
        return False
    radius = diameter / 2.0
    for x_index in range(63):
        x = -62.0 + 2.0 * x_index
        for y_index in range(43):
            y = -42.0 + 2.0 * y_index
            if min(point_segment_distance((x, y), start, end) for start, end in segments) > radius + 0.15:
                return False
    travel = sum(math.dist(start, end) for start, end in segments)
    return travel >= 0.55 * (124.0 * 84.0) / diameter


def validate_document(doc):
    jobs = [obj for obj in doc.Objects if module(obj) == "Path.Main.Job"]
    operations = [obj for obj in doc.Objects if module(obj) == "Path.Op.MillFace"]
    controllers = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Controller"]
    tools = [obj for obj in doc.Objects if module(obj) == "Path.Tool.Bit"]
    if len(jobs) != 1 or len(operations) != 1 or not controllers or not tools:
        return None
    job, operation = jobs[0], operations[0]
    controller = operation.ToolController
    tool = getattr(controller, "Tool", None)
    if controller not in controllers or tool not in tools:
        return None
    if list(job.Operations.Group) != [operation] or controller not in job.Tools.Group or len(job.Model.Group) != 1:
        return None
    if operation.ToolController is not controller or controller.Tool is not tool:
        return None
    if not bool(operation.Active) or list(operation.State) != ["Up-to-date"]:
        return None
    if not (near(operation.StartDepth.Value, 0.0) and near(operation.FinalDepth.Value, -1.0)):
        return None
    if operation.StepDown.Value <= 0.0 or operation.SafeHeight.Value <= 0.0 or operation.ClearanceHeight.Value < operation.SafeHeight.Value:
        return None
    if int(controller.ToolNumber) != 1 or not near(controller.SpindleSpeed, 6000.0):
        return None
    if str(controller.SpindleDir) not in {"Forward", "Reverse"} or not near(controller.HorizFeed.Value, 800.0 / 60.0):
        return None
    if not math.isfinite(float(controller.VertFeed.Value)) or controller.VertFeed.Value <= 0.0:
        return None
    if not near(tool.Diameter.Value, 16.0, 1e-4) or tool.Shape.isNull() or not tool.Shape.isValid():
        return None
    tool_box = tool.Shape.BoundBox
    if not near(tool_box.XLength, 16.0, 1e-3) or not near(tool_box.YLength, 16.0, 1e-3):
        return None
    if not flat_bottom_tool(tool.Shape, 16.0):
        return None
    expected_model = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, -13.0))
    expected_stock = Part.makeBox(124.0, 84.0, 13.0, App.Vector(-62.0, -42.0, -13.0))
    model = job.Model.Group[0]
    if not same_shape(model.Shape, expected_model) or not same_shape(job.Stock.Shape, expected_stock):
        return None
    if any(not near(left, right) for left, right in zip(bounds(model.Shape), MODEL_BOUNDS)):
        return None
    if any(not near(left, right) for left, right in zip(bounds(job.Stock.Shape), STOCK_BOUNDS)):
        return None
    expected_ext = {"ExtXneg": 2.0, "ExtXpos": 2.0, "ExtYneg": 2.0, "ExtYpos": 2.0, "ExtZneg": 0.0, "ExtZpos": 1.0}
    if any(hasattr(job.Stock, name) and not near(getattr(job.Stock, name).Value, value) for name, value in expected_ext.items()):
        return None
    processor = str(job.PostProcessor).strip().lower()
    if processor not in {"linuxcnc", "grbl"} or list(job.Fixtures) != ["G54"] or bool(job.SplitOutput):
        return None
    if os.path.normpath(str(job.PostProcessorOutputFile)) != "/home/user/Desktop/task-1.nc":
        return None
    if len(operation.Path.Commands) < 12 or not full_face_coverage(operation, 16.0):
        return None
    return job, operation, processor


def validate(step_path, fcstd_path, nc_path, work_dir):
    if tuple(App.Version()[:4]) != EXPECTED_VERSION or App.Version()[-1] != EXPECTED_COMMIT:
        return False
    expected_source = Part.makeBox(120.0, 80.0, 12.0, App.Vector(-60.0, -40.0, 0.0))
    source = Part.read(str(step_path))
    if len(source.Solids) != 1 or not same_shape(source, expected_source):
        return False
    if any(not near(left, right) for left, right in zip(bounds(source), SOURCE_BOUNDS)):
        return False

    doc = App.openDocument(str(fcstd_path))
    try:
        doc.recompute()
        first = validate_document(doc)
        if first is None:
            return False
        job, operation, processor = first
        operation.touch()
        doc.recompute()
        doc.recompute()
        second = validate_document(doc)
        if second is None:
            return False
        recomputed = pathlib.Path(work_dir) / "recomputed.FCStd"
        doc.saveAs(str(recomputed))
    finally:
        App.closeDocument(doc.Name)

    reopened = App.openDocument(str(recomputed))
    try:
        reopened.recompute()
        final = validate_document(reopened)
        if final is None:
            return False
        final_job, _final_operation, final_processor = final
        if final_processor != processor:
            return False
        sections = PathPostCommand.buildPostList(final_job)
        if len(sections) != 1 or not sections[0][1]:
            return False
        repost = pathlib.Path(work_dir) / "fresh-post.nc"
        PostProcessor.load(final_processor).export(sections[0][1], str(repost), str(final_job.PostProcessorArgs))
    finally:
        App.closeDocument(reopened.Name)

    submitted_signature = code_signature(nc_path)
    repost_signature = code_signature(repost)
    if submitted_signature is None or repost_signature is None or submitted_signature != repost_signature:
        return False
    if not submitted_signature or submitted_signature[-1] != (("M", 2.0),):
        return False
    return True


try:
    ok = validate(
        pathlib.Path(os.environ["TASK_V01_STEP"]),
        pathlib.Path(os.environ["TASK_V01_FCSTD"]),
        pathlib.Path(os.environ["TASK_V01_NC"]),
        os.environ["TASK_V01_WORK"],
    )
except Exception:
    ok = False
print("TASK_V01_RESULT=" + json.dumps({"ok": bool(ok)}, sort_keys=True))
'''


def evaluate() -> bool:
    step = TARGET / STEP_NAME
    fcstd = TARGET / FCSTD_NAME
    nc = TARGET / NC_NAME
    if not no_bypass_files(TARGET):
        return False
    if not regular_file(step, 1_000, 5_000_000) or sha256(step) != EXPECTED_STEP_SHA256:
        return False
    if not regular_file(fcstd, 1_000, 20_000_000) or not fcstd_preflight(fcstd):
        return False
    if not regular_file(nc, 300, 2_000_000):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="task_v01_eval_") as temporary:
            work = Path(temporary)
            step_copy = work / STEP_NAME
            fcstd_copy = work / FCSTD_NAME
            nc_copy = work / NC_NAME
            shutil.copyfile(step, step_copy, follow_symlinks=False)
            shutil.copyfile(fcstd, fcstd_copy, follow_symlinks=False)
            shutil.copyfile(nc, nc_copy, follow_symlinks=False)
            script = work / "native_check.py"
            script.write_text(CHILD_SOURCE, encoding="utf-8")
            completed = subprocess.run(
                [
                    "/usr/bin/env",
                    "TASK_V01_STEP=" + str(step_copy),
                    "TASK_V01_FCSTD=" + str(fcstd_copy),
                    "TASK_V01_NC=" + str(nc_copy),
                    "TASK_V01_WORK=" + str(work),
                    "/usr/bin/freecadcmd",
                    str(script),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
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
