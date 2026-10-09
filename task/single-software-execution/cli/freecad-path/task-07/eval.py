from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import shlex
import stat
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path


ROOT = Path("/home/user/Desktop")
FCSTD_PATH = ROOT / "task-07.FCStd"
STEP_PATH = ROOT / "variant_template.step"
VARIANTS_PATH = ROOT / "variants.json"
EXPECTED_STEP_SHA256 = "b6e7de627bdf86ec3d576c2da9980f949c7bc5451d96783fb6c2bebb56266097"
EXPECTED_VARIANTS_SHA256 = "9a5d0ed08ccc5622b7c35a517937afbd4d4e92a2b3d9e00461b19f333737b32c"
EXPECTED_FREECAD_COMMIT = "b9bfa5c5507506e4515816414cd27f4851d00489"
FREECADCMD = Path("/usr/bin/freecadcmd")
INNER_ENV = "ENGIWORLD_TASK07_FREECAD"
MARKER_ENV = "ENGIWORLD_TASK07_MARKER"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.IGNORECASE)


def regular_file(path: Path, maximum_size: int) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(info.st_mode)
        and not path.is_symlink()
        and 0 < info.st_size <= maximum_size
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def close(a, b, tolerance: float = 1e-5) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def proxy_module(obj) -> str:
    proxy = getattr(obj, "Proxy", None)
    return getattr(proxy.__class__, "__module__", "") if proxy is not None else ""


def shapes_equal(first, second, tolerance: float = 1e-5) -> bool:
    try:
        return (
            first.isValid()
            and second.isValid()
            and first.cut(second).Volume <= tolerance
            and second.cut(first).Volume <= tolerance
        )
    except Exception:
        return False


def normalize_program_comment(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).upper()


def rectangle_frame(face, Part, expected_length: float, expected_width: float):
    if len(face.Wires) != 1:
        return None
    if not isinstance(face.Surface, Part.Plane):
        return None
    normal = face.normalAt(0.5, 0.5)
    if abs(abs(float(normal.z)) - 1.0) > 1e-5:
        return None
    points = []
    for vertex in face.Wires[0].OrderedVertexes:
        point = vertex.Point
        if not points or (point - points[-1]).Length > 1e-6:
            points.append(point)
    if len(points) > 1 and (points[0] - points[-1]).Length <= 1e-6:
        points.pop()
    changed = True
    while changed and len(points) > 4:
        changed = False
        for index in range(len(points)):
            before = points[index - 1]
            current = points[index]
            after = points[(index + 1) % len(points)]
            incoming = current - before
            outgoing = after - current
            incoming.z = 0.0
            outgoing.z = 0.0
            if incoming.Length <= 1e-8 or outgoing.Length <= 1e-8:
                points.pop(index)
                changed = True
                break
            cross = abs(incoming.x * outgoing.y - incoming.y * outgoing.x)
            if cross <= 1e-7 * incoming.Length * outgoing.Length and incoming.dot(outgoing) > 0:
                points.pop(index)
                changed = True
                break
    if len(points) != 4:
        return None
    origin = points[0]
    first = points[1] - origin
    second = points[-1] - origin
    first.z = 0.0
    second.z = 0.0
    first_length = first.Length
    second_length = second.Length
    if first_length <= 0 or second_length <= 0:
        return None
    first.normalize()
    second.normalize()
    if abs(first.dot(second)) > 1e-5:
        return None
    actual = sorted((first_length, second_length))
    expected = sorted((expected_length, expected_width))
    if not all(close(a, b, 1e-4) for a, b in zip(actual, expected)):
        return None
    if not close(face.Area, expected_length * expected_width, 1e-3):
        return None
    return origin, first, second, first_length, second_length, points


def local_xy(point, frame):
    origin, first, second, _, _, _ = frame
    delta = point - origin
    return delta.dot(first), delta.dot(second)


def removal_rectangle_frame(pocket, Part, expected_length: float, expected_width: float, model_top: float):
    try:
        removal = pocket.removalshape
    except Exception:
        return None
    if removal is None or removal.isNull() or not removal.isValid():
        return None
    top_faces = [
        face
        for face in removal.Faces
        if isinstance(face.Surface, Part.Plane)
        and abs(face.BoundBox.ZMin - model_top) <= 1e-4
        and abs(face.BoundBox.ZMax - model_top) <= 1e-4
    ]
    if not top_faces:
        return None
    fused = top_faces[0]
    for face in top_faces[1:]:
        fused = fused.fuse(face)
    try:
        fused = fused.removeSplitter()
    except Exception:
        pass
    for face in fused.Faces:
        frame = rectangle_frame(face, Part, expected_length, expected_width)
        if frame is not None:
            return frame
    return None


def distance_to_segment(px: float, py: float, start, end) -> float:
    ax, ay = start
    bx, by = end
    dx = bx - ax
    dy = by - ay
    denominator = dx * dx + dy * dy
    if denominator <= 1e-16:
        return math.hypot(px - ax, py - ay)
    scale = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denominator))
    return math.hypot(px - (ax + scale * dx), py - (ay + scale * dy))


def path_motions(commands):
    current = {"X": None, "Y": None, "Z": None}
    motions = []
    for command in commands:
        before = dict(current)
        parameters = command.Parameters
        for axis in ("X", "Y", "Z"):
            if axis in parameters:
                current[axis] = float(parameters[axis])
        name = str(command.Name).upper().replace(" ", "")
        if name in {"G0", "G00", "G1", "G01"} and all(
            before[axis] is not None and current[axis] is not None
            for axis in ("X", "Y", "Z")
        ):
            motions.append(("G0" if name in {"G0", "G00"} else "G1", before, dict(current)))
        elif name in {"G2", "G02", "G3", "G03"} and all(
            before[axis] is not None and current[axis] is not None
            for axis in ("X", "Y", "Z")
        ):
            if "I" not in parameters and "J" not in parameters:
                raise ValueError("unsupported arc without I/J center offsets")
            center_x = before["X"] + float(parameters.get("I", 0.0))
            center_y = before["Y"] + float(parameters.get("J", 0.0))
            start_angle = math.atan2(before["Y"] - center_y, before["X"] - center_x)
            end_angle = math.atan2(current["Y"] - center_y, current["X"] - center_x)
            radius = math.hypot(before["X"] - center_x, before["Y"] - center_y)
            end_radius = math.hypot(current["X"] - center_x, current["Y"] - center_y)
            if radius <= 1e-8 or abs(radius - end_radius) > 1e-4:
                raise ValueError("invalid arc radius")
            clockwise = name in {"G2", "G02"}
            sweep = (start_angle - end_angle) % (2.0 * math.pi) if clockwise else (end_angle - start_angle) % (2.0 * math.pi)
            if sweep <= 1e-10:
                sweep = 2.0 * math.pi
            steps = max(2, int(math.ceil(radius * sweep / 0.25)))
            previous = dict(before)
            direction = -1.0 if clockwise else 1.0
            for step in range(1, steps + 1):
                fraction = step / steps
                angle = start_angle + direction * sweep * fraction
                point = {
                    "X": center_x + radius * math.cos(angle),
                    "Y": center_y + radius * math.sin(angle),
                    "Z": before["Z"] + (current["Z"] - before["Z"]) * fraction,
                }
                if step == steps:
                    point = dict(current)
                motions.append(("G1", previous, point))
                previous = point
    return motions


def rounded_rectangle_contains(
    x: float,
    y: float,
    length: float,
    width: float,
    radius: float,
) -> bool:
    center_x = min(max(x, radius), length - radius)
    center_y = min(max(y, radius), width - radius)
    return math.hypot(x - center_x, y - center_y) <= radius + 1e-8


def validate_pocket_path(pocket, frame, bottom_z: float, diameter: float) -> bool:
    _, _, _, length, width, _ = frame
    radius = diameter / 2.0
    if length <= diameter or width <= diameter:
        return False
    motions = path_motions(list(pocket.Path.Commands))
    if len(motions) < 8:
        return False
    final_segments = []
    reached_bottom = False
    for mode, before, after in motions:
        if min(before["Z"], after["Z"]) < bottom_z - 1e-4:
            return False
        if mode == "G0":
            if after["Z"] <= pocket.StartDepth.Value + 1e-4:
                return False
            continue
        for point_data in (before, after):
            if point_data["Z"] <= pocket.StartDepth.Value + 1e-4:
                point = __import__("FreeCAD").Vector(point_data["X"], point_data["Y"], point_data["Z"])
                local_x, local_y = local_xy(point, frame)
                if not (
                    radius - 0.01 <= local_x <= length - radius + 0.01
                    and radius - 0.01 <= local_y <= width - radius + 0.01
                ):
                    return False
        if abs(after["Z"] - bottom_z) <= 1e-4:
            reached_bottom = True
        if abs(before["Z"] - bottom_z) <= 1e-4 and abs(after["Z"] - bottom_z) <= 1e-4:
            first_point = __import__("FreeCAD").Vector(before["X"], before["Y"], bottom_z)
            second_point = __import__("FreeCAD").Vector(after["X"], after["Y"], bottom_z)
            final_segments.append((local_xy(first_point, frame), local_xy(second_point, frame)))
    if not reached_bottom or len(final_segments) < 4:
        return False

    sample_step = 0.5
    x = 0.0
    samples = 0
    while x <= length + 1e-8:
        y = 0.0
        while y <= width + 1e-8:
            if rounded_rectangle_contains(x, y, length, width, radius):
                samples += 1
                if min(distance_to_segment(x, y, a, b) for a, b in final_segments) > radius + 0.01:
                    return False
            y += sample_step
        x += sample_step
    return samples >= 100


def strip_comments(text: str):
    comments = []
    output = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "(":
            end = text.find(")", index + 1)
            if end < 0 or "(" in text[index + 1 : end]:
                raise ValueError("malformed parenthesis comment")
            comments.append(text[index + 1 : end])
            output.extend(" " for _ in range(index, end + 1))
            index = end + 1
        elif char == ")":
            raise ValueError("unmatched parenthesis")
        elif char == ";":
            end = text.find("\n", index)
            if end < 0:
                end = len(text)
            comments.append(text[index + 1 : end])
            output.extend(" " for _ in range(index, end))
            index = end
        else:
            output.append(char)
            index += 1
    return "".join(output), comments


def parse_nc(text: str):
    executable, comments = strip_comments(text)
    raw_lines = executable.splitlines()
    percent_lines = [index for index, line in enumerate(raw_lines) if line.strip() == "%"]
    nonempty = [index for index, line in enumerate(raw_lines) if line.strip()]
    if percent_lines:
        if len(percent_lines) != 2 or percent_lines != [nonempty[0], nonempty[-1]]:
            raise ValueError("illegal percent wrapper")
    blocks = []
    for raw_line in raw_lines:
        line = raw_line.strip().upper()
        if not line or line == "%":
            continue
        tokens = []
        cursor = 0
        for match in WORD_RE.finditer(line):
            if line[cursor : match.start()].strip():
                raise ValueError("unparsed NC text")
            tokens.append((match.group(1).upper(), float(match.group(2))))
            cursor = match.end()
        if line[cursor:].strip() or not tokens:
            raise ValueError("unparsed NC line")
        blocks.append(tokens)
    if not blocks:
        raise ValueError("empty NC")
    return blocks, comments


def canonical_blocks(text: str):
    blocks, _ = parse_nc(text)
    result = []
    for block in blocks:
        normalized = []
        for letter, number in block:
            if letter == "N":
                continue
            if letter in {"G", "M", "T", "H", "O"} and close(number, round(number), 1e-9):
                value = str(int(round(number)))
            else:
                value = f"{number:.9f}".rstrip("0").rstrip(".")
                if value in {"-0", "+0"}:
                    value = "0"
            if letter == "M" and value == "30":
                value = "2"
            normalized.append(letter + value)
        result.append(tuple(sorted(normalized)))
    return result


def validate_nc_safety(text: str, program: int, model_top: float, bottom_z: float) -> bool:
    try:
        blocks, comments = parse_nc(text)
    except Exception:
        return False
    expected_comment = f"PROGRAM NUMBER {program}"
    exact_program_comments = [
        comment.strip()
        for comment in comments
        if re.fullmatch(r"PROGRAM NUMBER [+-]?\d+", comment.strip())
    ]
    mentioned_programs = [
        int(match.group(1))
        for comment in comments
        for match in [
            re.fullmatch(
                r"PROGRAM(?:\s+|[-_])NUMBER\s*(?:[:=#-]\s*)?([+-]?\d+)",
                comment.strip(),
                re.IGNORECASE,
            )
        ]
        if match is not None
    ]
    if exact_program_comments != [expected_comment] or any(value != program for value in mentioned_programs):
        return False

    state = {
        "units_mm": False,
        "absolute": False,
        "motion": None,
        "feed": None,
        "speed": None,
        "tool": None,
        "spindle": False,
        "tool_changed": False,
        "X": None,
        "Y": None,
        "Z": None,
    }
    saw_g21 = saw_g90 = saw_tool_change = saw_spindle = saw_cut = saw_bottom = False
    ended = False
    for block_index, block in enumerate(blocks):
        words = {}
        g_codes = []
        m_codes = []
        for letter, number in block:
            if letter == "G":
                if not close(number, round(number), 1e-9):
                    return False
                g_codes.append(int(round(number)))
            elif letter == "M":
                if not close(number, round(number), 1e-9):
                    return False
                m_codes.append(int(round(number)))
            else:
                if letter in words:
                    return False
                words[letter] = number
        if any(code not in {0, 1, 2, 3, 17, 21, 40, 43, 49, 54, 55, 56, 57, 58, 59, 80, 90, 94} for code in g_codes):
            return False
        if any(code not in {2, 3, 4, 5, 6, 7, 8, 9, 30} for code in m_codes):
            return False
        if 21 in g_codes:
            state["units_mm"] = True
            saw_g21 = True
        if 90 in g_codes:
            state["absolute"] = True
            saw_g90 = True
        for code in g_codes:
            if code in (0, 1, 2, 3):
                state["motion"] = code
        if "T" in words:
            if not close(words["T"], 1, 1e-9):
                return False
            state["tool"] = 1
        if "H" in words and not close(words["H"], 1, 1e-9):
            return False
        if "S" in words:
            if not close(words["S"], 7000, 1e-6):
                return False
            state["speed"] = words["S"]
        if "F" in words:
            if not close(words["F"], 500, 1e-5):
                return False
            state["feed"] = words["F"]
        if 5 in m_codes:
            state["spindle"] = False
        if 6 in m_codes:
            if state["spindle"] or state["tool"] != 1:
                return False
            state["tool_changed"] = True
            saw_tool_change = True
        if 3 in m_codes and 4 in m_codes:
            return False
        if 3 in m_codes or 4 in m_codes:
            if state["speed"] is None or not close(state["speed"], 7000, 1e-6):
                return False
            state["spindle"] = True
            saw_spindle = True
        before = {axis: state[axis] for axis in ("X", "Y", "Z")}
        moved = False
        for axis in ("X", "Y", "Z"):
            if axis in words:
                state[axis] = words[axis]
                moved = True
        if moved and state["motion"] in (0, 1, 2, 3):
            if not state["units_mm"] or not state["absolute"]:
                return False
            if state["motion"] == 0:
                xy_changed = any(
                    axis in words and before[axis] is not None and not close(before[axis], state[axis])
                    for axis in ("X", "Y")
                )
                if state["Z"] is not None and state["Z"] <= model_top + 1e-4:
                    return False
                if xy_changed and (before["Z"] is None or before["Z"] <= model_top + 1e-4):
                    return False
            else:
                if not state["tool_changed"] or not state["spindle"] or state["feed"] is None:
                    return False
                if state["Z"] is not None and state["Z"] < bottom_z - 1e-4:
                    return False
                saw_cut = True
                if state["Z"] is not None and abs(state["Z"] - bottom_z) <= 1e-4:
                    saw_bottom = True
        if 2 in m_codes or 30 in m_codes:
            if block_index != len(blocks) - 1 or state["spindle"]:
                return False
            ended = True
    return all(
        (saw_g21, saw_g90, saw_tool_change, saw_spindle, saw_cut, saw_bottom, ended)
    )


def valid_postprocessor_args(value: str) -> bool:
    try:
        arguments = shlex.split(value)
    except ValueError:
        return False
    flags = {"--no-header", "--line-numbers", "--no-show-editor", "--modal", "--axis-modal", "--no-tlo"}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in flags:
            index += 1
            continue
        if argument == "--precision":
            index += 1
            if index >= len(arguments) or not re.fullmatch(r"[3-9]", arguments[index]):
                return False
            index += 1
            continue
        match = re.fullmatch(r"--precision=([3-9])", argument)
        if match is not None:
            index += 1
            continue
        return False
    return True


def object_state_clean(obj) -> bool:
    try:
        states = {str(value) for value in obj.State}
    except Exception:
        return False
    return not states.intersection({"Touched", "Invalid", "Error"})


def validate_variants(data) -> list[dict] | None:
    if not isinstance(data, dict) or data.get("task") != "task-07" or data.get("unit") != "mm":
        return None
    variants = data.get("variants")
    if not isinstance(variants, list) or len(variants) != 5:
        return None
    seen_names = set()
    seen_programs = set()
    for variant in variants:
        if set(variant) != {"name", "pocket_size", "bottom_z", "tool_diameter", "program"}:
            return None
        name = variant["name"]
        size = variant["pocket_size"]
        if not isinstance(name, str) or not re.fullmatch(r"variant_0[1-5]", name):
            return None
        if not isinstance(size, list) or len(size) != 2:
            return None
        try:
            length, width = map(float, size)
            bottom = float(variant["bottom_z"])
            diameter = float(variant["tool_diameter"])
            program = int(variant["program"])
        except (TypeError, ValueError):
            return None
        if name in seen_names or program in seen_programs:
            return None
        if length <= diameter or width <= diameter or diameter <= 0 or not (0 < bottom < 18):
            return None
        seen_names.add(name)
        seen_programs.add(program)
    return variants


def evaluate_in_freecad() -> bool:
    import builtins

    builtins.pythonopen = open
    import FreeCAD as App
    import Part
    import Path.Post.Command as PathPostCommand
    from Path.Post.Processor import PostProcessor

    if App.Version()[:4] != ["0", "21", "2", "33771 (Git)"]:
        return False
    if App.Version()[-1] != EXPECTED_FREECAD_COMMIT:
        return False
    required = [FCSTD_PATH, STEP_PATH, VARIANTS_PATH] + [
        ROOT / f"variant_{index:02d}.nc" for index in range(1, 6)
    ]
    if not all(regular_file(path, 20 * 1024 * 1024 if path.suffix == ".FCStd" else 5 * 1024 * 1024) for path in required):
        return False
    if (
        normalized_text_sha256(STEP_PATH) != EXPECTED_STEP_SHA256
        or normalized_text_sha256(VARIANTS_PATH) != EXPECTED_VARIANTS_SHA256
    ):
        return False
    try:
        variants = validate_variants(json.loads(VARIANTS_PATH.read_text(encoding="utf-8")))
    except Exception:
        return False
    if variants is None:
        return False

    input_shape = Part.read(str(STEP_PATH))
    if (
        input_shape.ShapeType != "Solid"
        or len(input_shape.Solids) != 1
        or not input_shape.isValid()
        or not close(input_shape.Volume, 172800.0, 1e-3)
    ):
        return False
    document = App.openDocument(str(FCSTD_PATH))
    if document is None:
        return False
    jobs = [obj for obj in document.Objects if proxy_module(obj) == "Path.Main.Job"]
    if len(jobs) != 5:
        return False

    jobs_by_program = {}
    for job in jobs:
        if len(job.Operations.Group) != 2:
            return False
        custom_ops = [obj for obj in job.Operations.Group if proxy_module(obj) == "Path.Op.Custom"]
        pockets = [obj for obj in job.Operations.Group if proxy_module(obj) == "Path.Op.PocketShape"]
        if len(custom_ops) != 1 or len(pockets) != 1:
            return False
        lines = [str(line).strip() for line in custom_ops[0].Gcode]
        matches = [re.fullmatch(r"\(PROGRAM NUMBER (\d+)\)", line) for line in lines]
        programs = [int(match.group(1)) for match in matches if match]
        if len(programs) != 1 or programs[0] in jobs_by_program:
            return False
        jobs_by_program[programs[0]] = (job, custom_ops[0], pockets[0])
    if set(jobs_by_program) != {int(variant["program"]) for variant in variants}:
        return False

    for job, custom, pocket in jobs_by_program.values():
        for obj in list(job.Tools.Group) + [custom, pocket, job]:
            obj.touch()
    document.recompute()

    with tempfile.TemporaryDirectory(prefix="engiworld-task07-eval-") as temporary:
        for variant in variants:
            name = variant["name"]
            length, width = map(float, variant["pocket_size"])
            bottom_z = float(variant["bottom_z"])
            diameter = float(variant["tool_diameter"])
            program = int(variant["program"])
            job, custom, pocket = jobs_by_program[program]
            if str(job.PostProcessor).strip().lower() != "linuxcnc" or bool(job.SplitOutput):
                return False
            if os.path.normpath(str(job.PostProcessorOutputFile)) != str(ROOT / f"{name}.nc"):
                return False
            if not valid_postprocessor_args(str(job.PostProcessorArgs)):
                return False
            fixtures = [str(fixture).strip().upper() for fixture in job.Fixtures]
            if len(fixtures) != 1 or not re.fullmatch(r"G5[4-9]", fixtures[0]):
                return False
            if len(job.Model.Group) != 1 or not shapes_equal(job.Model.Group[0].Shape, input_shape):
                return False
            model = job.Model.Group[0]
            stock = job.Stock
            if (
                not stock.Shape.isValid()
                or len(stock.Shape.Solids) != 1
                or model.Shape.cut(stock.Shape).Volume > 1e-5
            ):
                return False
            if len(job.Tools.Group) != 1:
                return False
            controller = job.Tools.Group[0]
            if proxy_module(controller) != "Path.Tool.Controller" or proxy_module(controller.Tool) != "Path.Tool.Bit":
                return False
            if (
                int(controller.ToolNumber) != 1
                or not close(controller.Tool.Diameter.Value, diameter)
                or not close(controller.SpindleSpeed, 7000)
                or str(controller.SpindleDir) not in {"Forward", "Reverse"}
                or not close(controller.HorizFeed.getValueAs("mm/min").Value, 500)
                or not close(controller.VertFeed.getValueAs("mm/min").Value, 500)
            ):
                return False
            if custom.ToolController != controller or pocket.ToolController != controller:
                return False
            if [str(line).strip() for line in custom.Gcode] != [f"(PROGRAM NUMBER {program})"]:
                return False
            if (
                not close(pocket.StartDepth.Value, input_shape.BoundBox.ZMax)
                or not close(pocket.FinalDepth.Value, bottom_z)
                or pocket.StepDown.Value <= 0
                or pocket.ClearanceHeight.Value <= pocket.SafeHeight.Value
                or pocket.SafeHeight.Value <= input_shape.BoundBox.ZMax
                or not pocket.Base
            ):
                return False
            for boundary, subelements in pocket.Base:
                if boundary.Document != document or not subelements:
                    return False
                for subelement in subelements:
                    if not str(subelement).startswith("Face"):
                        return False
                    try:
                        boundary.Shape.getElement(str(subelement))
                    except Exception:
                        return False
            tracked_objects = [job, model, stock, controller, controller.Tool, custom, pocket]
            tracked_objects.extend(boundary for boundary, _ in pocket.Base)
            if not all(object_state_clean(obj) for obj in tracked_objects):
                return False
            frame = removal_rectangle_frame(
                pocket,
                Part,
                length,
                width,
                input_shape.BoundBox.ZMax,
            )
            if frame is None:
                return False
            _, _, _, _, _, points = frame
            if any(
                point.z < input_shape.BoundBox.ZMax - 1e-5
                or point.z > input_shape.BoundBox.ZMax + 1e-5
                or point.x < input_shape.BoundBox.XMin - 1e-5
                or point.x > input_shape.BoundBox.XMax + 1e-5
                or point.y < input_shape.BoundBox.YMin - 1e-5
                or point.y > input_shape.BoundBox.YMax + 1e-5
                for point in points
            ):
                return False
            if not validate_pocket_path(pocket, frame, bottom_z, diameter):
                return False

            submitted_path = ROOT / f"{name}.nc"
            try:
                submitted_text = submitted_path.read_text(encoding="utf-8")
            except Exception:
                return False
            if not validate_nc_safety(submitted_text, program, input_shape.BoundBox.ZMax, bottom_z):
                return False
            sections = PathPostCommand.buildPostList(job)
            if len(sections) != 1:
                return False
            repost_path = Path(temporary) / f"{name}.nc"
            try:
                PostProcessor.load("linuxcnc").export(
                    sections[0][1],
                    str(repost_path),
                    str(job.PostProcessorArgs),
                )
                repost_text = repost_path.read_text(encoding="utf-8")
            except BaseException:
                return False
            if canonical_blocks(submitted_text) != canonical_blocks(repost_text):
                return False
    return True


def run_outer() -> bool:
    try:
        executable = FREECADCMD.resolve(strict=True)
        info = executable.stat()
    except OSError:
        return False
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        return False
    marker = "TASK07_RESULT_" + secrets.token_hex(16)
    evaluator = str(Path(__file__).resolve())
    command = (
        "import builtins; builtins.pythonopen=open; "
        f"exec(compile(open({evaluator!r}, encoding='utf-8').read(), {evaluator!r}, 'exec'))"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="engiworld-task07-home-") as isolated_home:
            environment = {
                "HOME": isolated_home,
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "LOGNAME": "user",
                "PATH": "/usr/bin:/bin",
                "USER": "user",
                "XDG_CACHE_HOME": str(Path(isolated_home) / ".cache"),
                "XDG_CONFIG_HOME": str(Path(isolated_home) / ".config"),
                INNER_ENV: "1",
                MARKER_ENV: marker,
            }
            completed = subprocess.run(
                [str(executable), "-c", command],
                capture_output=True,
                text=True,
                timeout=240,
                env=environment,
                check=False,
            )
    except Exception:
        return False
    marker_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith(marker + "=")]
    return completed.returncode == 0 and marker_lines == [marker + "=True"]


if __name__ == "__main__":
    if os.environ.get(INNER_ENV) == "1":
        marker = os.environ.get(MARKER_ENV, "")
        ok = False
        try:
            ok = evaluate_in_freecad()
        except BaseException:
            traceback.print_exc(file=sys.stderr)
            ok = False
        print(f"{marker}={bool(ok)}")
    else:
        print(True if run_outer() else False)
