from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("ENGIWORLD_EVAL_TARGET", "/home/user/Desktop"))
PARTS = ("p1", "p2", "p3")
TOL = 1e-3
WORD_RE = re.compile(
    r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)",
    re.IGNORECASE,
)
NATIVE_MARKER = "TASK_C03_NATIVE="


@dataclass(frozen=True)
class Move:
    block: int
    motion: int
    start_x: float | None
    start_y: float | None
    start_z: float | None
    end_x: float | None
    end_y: float | None
    end_z: float | None
    feed: float | None
    i: float | None
    j: float | None

    @property
    def xy_distance(self) -> float:
        if None in (self.start_x, self.start_y, self.end_x, self.end_y):
            return 0.0
        return math.hypot(self.end_x - self.start_x, self.end_y - self.start_y)


def close(actual: float | None, expected: float, tolerance: float = TOL) -> bool:
    return actual is not None and abs(actual - expected) <= tolerance


def strip_comments(text: str) -> str:
    output: list[str] = []
    depth = 0
    for char in text:
        if char == "\n":
            depth = 0
            output.append(char)
        elif depth:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
        elif char == "(":
            depth = 1
        elif char == ";":
            depth = 1
        else:
            output.append(char)
    return "".join(output)


def parse_words(line: str) -> list[tuple[str, float]] | None:
    cleaned = line.strip().upper().replace("%", "")
    if not cleaned:
        return []
    words: list[tuple[str, float]] = []
    cursor = 0
    for match in WORD_RE.finditer(cleaned):
        if cleaned[cursor : match.start()].strip():
            return None
        try:
            value = float(match.group(2))
        except ValueError:
            return None
        if not math.isfinite(value):
            return None
        words.append((match.group(1), value))
        cursor = match.end()
    if cleaned[cursor:].strip() or not words:
        return None
    return words


def sample_move(move: Move, count: int = 48) -> list[tuple[float, float]]:
    if None in (move.start_x, move.start_y, move.end_x, move.end_y):
        return []
    start = (float(move.start_x), float(move.start_y))
    end = (float(move.end_x), float(move.end_y))
    if move.motion == 1:
        sample_count = max(1, int(math.ceil(math.dist(start, end) / 0.5)))
        return [
            (
                start[0] + (end[0] - start[0]) * index / sample_count,
                start[1] + (end[1] - start[1]) * index / sample_count,
            )
            for index in range(sample_count + 1)
        ]
    if move.motion not in (2, 3) or move.i is None or move.j is None:
        return []
    center_x = start[0] + move.i
    center_y = start[1] + move.j
    radius = math.hypot(move.i, move.j)
    if radius <= TOL or abs(math.hypot(end[0] - center_x, end[1] - center_y) - radius) > max(0.01, radius * 1e-5):
        return []
    start_angle = math.atan2(start[1] - center_y, start[0] - center_x)
    end_angle = math.atan2(end[1] - center_y, end[0] - center_x)
    if move.motion == 2:
        sweep = (start_angle - end_angle) % (2.0 * math.pi)
        if sweep <= 1e-9:
            sweep = 2.0 * math.pi
        angles = [start_angle - sweep * index / count for index in range(count + 1)]
    else:
        sweep = (end_angle - start_angle) % (2.0 * math.pi)
        if sweep <= 1e-9:
            sweep = 2.0 * math.pi
        angles = [start_angle + sweep * index / count for index in range(count + 1)]
    return [
        (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
        for angle in angles
    ]


def sample_cutting_xy(move: Move) -> list[tuple[float, float]]:
    points = sample_move(move)
    if not points or move.start_z is None or move.end_z is None:
        return points if move.end_z is not None and move.end_z <= TOL else []
    if move.start_z <= TOL and move.end_z <= TOL:
        return points
    if move.start_z > TOL and move.end_z > TOL:
        return []
    denominator = max(1, len(points) - 1)
    return [
        point
        for index, point in enumerate(points)
        if move.start_z + (move.end_z - move.start_z) * index / denominator <= TOL
    ]


def point_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= TOL * TOL:
        return math.dist(point, start)
    projection = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length_squared
    projection = max(0.0, min(1.0, projection))
    closest = (start[0] + projection * dx, start[1] + projection * dy)
    return math.dist(point, closest)


def distance_to_part(point: tuple[float, float]) -> float:
    dx = max(abs(point[0]) - 60.0, 0.0)
    dy = max(abs(point[1]) - 40.0, 0.0)
    return math.hypot(dx, dy)


def parse_nc(path: Path) -> dict[str, object] | None:
    if not path.is_file() or not 500 <= path.stat().st_size <= 2_000_000:
        return None
    raw = path.read_text(encoding="utf-8", errors="strict")
    if "\x00" in raw:
        return None

    x = y = z = feed = None
    motion: int | None = None
    selected_tool: int | None = None
    tool_changed = False
    spindle_on = False
    spindle_speed: float | None = None
    metric = absolute = False
    active_fixture: float | None = None
    active_plane: int | None = None
    stopped_after_cut = ended_after_cut = retracted_after_cut = False
    length_offset_active = False
    length_offset: int | None = None
    program_ended = False
    last_cut_block = -1
    moves: list[Move] = []
    cutting_depths: set[float] = set()

    for block, line in enumerate(strip_comments(raw).splitlines()):
        words = parse_words(line)
        if words is None:
            return None
        if not words:
            continue
        if program_ended:
            return None
        values: dict[str, list[float]] = {}
        for letter, value in words:
            values.setdefault(letter, []).append(value)
        if set(values) - set("NGXYZIJFSTHPM"):
            return None
        if any(len(values.get(letter, [])) > 1 for letter in "XYZIJFSTH"):
            return None
        motion_codes = [
            g
            for g in values.get("G", [])
            if any(close(g, code) for code in (0.0, 1.0, 2.0, 3.0))
        ]
        if len(motion_codes) > 1:
            return None
        modal_groups = (
            (20.0, 21.0),
            (90.0, 91.0),
            (90.1, 91.1),
            (17.0, 18.0, 19.0),
            (40.0, 41.0, 42.0),
            (43.0, 49.0),
            (54.0, 55.0, 56.0, 57.0, 58.0, 59.0),
            (61.0, 61.1, 64.0),
            (93.0, 94.0, 95.0),
        )
        if any(
            sum(any(close(g, code) for code in group) for g in values.get("G", [])) > 1
            for group in modal_groups
        ):
            return None
        has_g43 = any(close(g, 43.0) for g in values.get("G", []))
        has_g49 = any(close(g, 49.0) for g in values.get("G", []))
        if has_g43 and has_g49:
            return None

        for g_code in values.get("G", []):
            if close(g_code, 20.0):
                metric = False
            elif close(g_code, 21.0):
                metric = True
            elif close(g_code, 90.0):
                absolute = True
            elif close(g_code, 91.0):
                absolute = False
            elif any(close(g_code, code) for code in (54.0, 55.0, 56.0, 57.0, 58.0, 59.0)):
                active_fixture = next(code for code in (54.0, 55.0, 56.0, 57.0, 58.0, 59.0) if close(g_code, code))
            elif close(g_code, 17.0):
                active_plane = 17
            elif any(
                close(g_code, code)
                for code in (10.0, 28.0, 30.0, 50.0, 51.0, 52.0, 53.0, 68.0, 69.0, 92.0, 92.1, 92.2, 92.3)
            ):
                return None
            elif any(close(g_code, code) for code in (0.0, 1.0, 2.0, 3.0)):
                motion = int(round(g_code))
            elif any(close(g_code, code) for code in (4.0, 40.0, 43.0, 49.0, 61.0, 61.1, 64.0, 80.0, 91.1, 94.0)):
                pass
            else:
                return None

        if values.get("T"):
            tool_value = values["T"][-1]
            if abs(tool_value - round(tool_value)) > TOL:
                return None
            selected_tool = int(round(tool_value))
        if values.get("H"):
            if not has_g43:
                return None
            h_value = values["H"][-1]
            if abs(h_value - round(h_value)) > TOL or int(round(h_value)) != 1:
                return None
            length_offset = int(round(h_value))
        if has_g43:
            if length_offset != 1:
                return None
            length_offset_active = True
        if has_g49:
            length_offset_active = False
            length_offset = None
        if values.get("S"):
            spindle_speed = values["S"][-1]
        if values.get("F"):
            feed = values["F"][-1]

        m_codes = values.get("M", [])
        if any(not any(close(code, allowed) for allowed in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 30.0)) for code in m_codes):
            return None
        if len({round(code, 6) for code in m_codes}) != len(m_codes):
            return None
        if sum(any(close(code, value) for value in (3.0, 4.0, 5.0)) for code in m_codes) > 1:
            return None
        if any(close(code, 6.0) for code in m_codes) and any(close(code, value) for code in m_codes for value in (3.0, 4.0, 5.0)):
            return None
        if sum(any(close(code, value) for value in (2.0, 30.0)) for code in m_codes) > 1:
            return None
        if any(close(code, value) for code in m_codes for value in (2.0, 30.0)) and any(
            close(code, value) for code in m_codes for value in (3.0, 4.0, 6.0)
        ):
            return None
        if sum(any(close(code, value) for value in (7.0, 8.0, 9.0)) for code in m_codes) > 1:
            return None
        if any(close(code, 5.0) for code in m_codes):
            spindle_on = False
            if last_cut_block >= 0 and block > last_cut_block:
                stopped_after_cut = True
        if any(close(code, 6.0) for code in m_codes):
            if selected_tool != 1 or spindle_on or length_offset_active:
                return None
            tool_changed = True
        if any(close(code, value) for code in m_codes for value in (3.0, 4.0)):
            if not tool_changed or not close(spindle_speed, 7000.0):
                return None
            if any(close(code, 4.0) for code in m_codes):
                return None
            spindle_on = True
        if any(close(code, value) for code in m_codes for value in (2.0, 30.0)):
            if any(axis in values for axis in ("X", "Y", "Z")):
                return None
            if last_cut_block >= 0 and block > last_cut_block:
                ended_after_cut = True
                stopped_after_cut = True
            spindle_on = False
            program_ended = True

        if not any(axis in values for axis in ("X", "Y", "Z")):
            continue
        if motion is None or not metric or not absolute or not close(active_fixture, 54.0):
            return None
        next_x = values.get("X", [x])[-1]
        next_y = values.get("Y", [y])[-1]
        next_z = values.get("Z", [z])[-1]
        move = Move(
            block,
            motion,
            x,
            y,
            z,
            next_x,
            next_y,
            next_z,
            feed,
            values.get("I", [0.0])[-1] if motion in (2, 3) else values.get("I", [None])[-1],
            values.get("J", [0.0])[-1] if motion in (2, 3) else values.get("J", [None])[-1],
        )
        has_xy_word = "X" in values or "Y" in values
        moved_xy = has_xy_word and (
            move.start_x is None
            or move.start_y is None
            or move.end_x is None
            or move.end_y is None
            or move.xy_distance > TOL
            or motion in (2, 3)
        )
        moved_z = (
            move.start_z is not None
            and move.end_z is not None
            and abs(move.end_z - move.start_z) > TOL
        )
        if motion in (2, 3):
            if active_plane != 17 or not ("I" in values or "J" in values) or len(sample_move(move)) < 2:
                return None
        elif "I" in values or "J" in values:
            return None
        if motion == 0:
            if moved_xy and (
                move.start_z is None
                or move.start_z <= TOL
                or move.end_z is None
                or move.end_z <= TOL
            ):
                return None
            if moved_z and move.end_z is not None and move.end_z <= TOL:
                return None

        intersects_material_z = (
            move.end_z is not None
            and (move.end_z <= TOL or move.start_z is not None and move.start_z <= TOL)
        )
        is_cut = motion in (1, 2, 3) and intersects_material_z and (moved_xy or moved_z)
        if is_cut:
            if not (
                tool_changed
                and spindle_on
                and close(spindle_speed, 7000.0)
                and close(active_fixture, 54.0)
            ):
                return None
            if move.end_z < -18.0 - TOL:
                return None
            if moved_xy:
                if not close(feed, 500.0):
                    return None
                cutting_depths.add(round(float(move.end_z), 6))
            last_cut_block = block
            retracted_after_cut = False
        if last_cut_block >= 0 and block > last_cut_block and motion == 0 and move.end_z is not None and move.end_z > TOL:
            retracted_after_cut = True
        moves.append(move)
        x, y, z = next_x, next_y, next_z

    if not (
        metric
        and absolute
        and close(active_fixture, 54.0)
        and active_plane == 17
        and tool_changed
        and program_ended
    ):
        return None
    if not (last_cut_block >= 0 and stopped_after_cut and ended_after_cut and retracted_after_cut):
        return None
    if not any(close(depth, -18.0) for depth in cutting_depths):
        return None
    return {"moves": moves, "depths": sorted(cutting_depths, reverse=True)}


def native_check(paths: dict[str, Path]) -> dict[str, float] | None:
    if any(not path.is_file() or not 1_000 <= path.stat().st_size <= 20_000_000 for path in paths.values()):
        return None
    checker = textwrap.dedent(
        f"""
        import json
        import math
        import FreeCAD as App

        FILES = {dict((name, str(path)) for name, path in paths.items())!r}
        MARKER = {NATIVE_MARKER!r}
        EXPECTED_BOX = [-60.0, 60.0, -40.0, 40.0, -18.0, 0.0]
        SOURCE_BOX = [-60.0, 60.0, -40.0, 40.0, 0.0, 18.0]
        result = {{"ok": False}}
        opened = []

        def near(value, expected, tolerance=1e-5):
            return abs(float(value) - expected) <= tolerance

        def box(shape):
            bounds = shape.BoundBox
            return [bounds.XMin, bounds.XMax, bounds.YMin, bounds.YMax, bounds.ZMin, bounds.ZMax]

        def check_box(shape, expected, label):
            if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
                raise RuntimeError(label + " is not one valid solid")
            if any(not near(a, b) for a, b in zip(box(shape), expected)):
                raise RuntimeError(label + " bounds are wrong")

        try:
            if tuple(App.Version()[:3]) != ("0", "21", "2"):
                raise RuntimeError("wrong FreeCAD version")
            diameters = {{}}
            for part in sorted(FILES):
                doc = App.openDocument(FILES[part])
                if doc is None:
                    raise RuntimeError(part + " document did not open")
                opened.append(doc)
                doc.recompute()
                jobs = [
                    obj for obj in doc.Objects
                    if type(getattr(obj, "Proxy", None)).__module__ == "Path.Main.Job"
                    and type(getattr(obj, "Proxy", None)).__name__ == "ObjectJob"
                ]
                if len(jobs) != 1:
                    raise RuntimeError(part + " does not contain one native Job")
                job = jobs[0]
                identity = getattr(job, "PartIdentity", None)
                if identity is not None and str(identity) != part + ".step":
                    raise RuntimeError(part + " Job identity references a different source part")
                operations = list(job.Operations.Group)
                controllers = list(job.Tools.Group)
                models = list(job.Model.Group)
                if len(operations) != 1 or len(controllers) != 1 or len(models) != 1:
                    raise RuntimeError(part + " Job group cardinality is wrong")

                operation = operations[0]
                if type(getattr(operation, "Proxy", None)).__module__ != "Path.Op.Profile":
                    raise RuntimeError(part + " operation is not Profile")
                if type(operation.Proxy).__name__ != "ObjectProfile" or not bool(operation.Active):
                    raise RuntimeError(part + " Profile is inactive or invalid")
                if len(operation.Base) != 0:
                    raise RuntimeError(part + " Profile is not based on the whole model")
                if str(operation.Side) != "Outside" or not bool(operation.UseComp):
                    raise RuntimeError(part + " Profile is not outside compensated")
                if not bool(operation.processPerimeter):
                    raise RuntimeError(part + " Profile does not process the perimeter")
                if not near(operation.StartDepth.Value, 0.0) or not near(operation.FinalDepth.Value, -18.0):
                    raise RuntimeError(part + " Profile depths are wrong")
                if not (0.0 < operation.StepDown.Value <= 18.0):
                    raise RuntimeError(part + " Profile StepDown is invalid")
                if operation.SafeHeight.Value <= 0.0 or operation.ClearanceHeight.Value <= 0.0:
                    raise RuntimeError(part + " Profile heights are unsafe")

                model = models[0]
                check_box(model.Shape, EXPECTED_BOX, part + " Job model")
                check_box(job.Stock.Shape, EXPECTED_BOX, part + " Job stock")
                if not (
                    near(model.Placement.Base.x, 0.0)
                    and near(model.Placement.Base.y, 0.0)
                    and near(model.Placement.Base.z, -18.0)
                ):
                    raise RuntimeError(part + " Job origin is not the source top-face center")
                source_models = list(job.Proxy.baseObjects(job))
                if len(source_models) != 1:
                    raise RuntimeError(part + " does not reference one source part")
                source_label = " ".join(
                    str(getattr(source_models[0], name, ""))
                    for name in ("Label", "Label2")
                ).lower()
                declared_parts = [name for name in ("p1", "p2", "p3") if name + ".step" in source_label]
                if declared_parts and part not in declared_parts:
                    raise RuntimeError(part + " source label references a different part")
                check_box(source_models[0].Shape, SOURCE_BOX, part + " source part")
                for prop in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos"):
                    if not near(getattr(job.Stock, prop).Value, 0.0):
                        raise RuntimeError(part + " stock extension is nonzero")
                if str(job.PostProcessor).lower() != "linuxcnc" or list(job.Fixtures) != ["G54"]:
                    raise RuntimeError(part + " postprocessor or fixture is wrong")

                controller = controllers[0]
                if operation.ToolController is not controller or int(controller.ToolNumber) != 1:
                    raise RuntimeError(part + " uses the wrong ToolController")
                if not near(controller.SpindleSpeed, 7000.0) or str(controller.SpindleDir) != "Forward":
                    raise RuntimeError(part + " spindle configuration is wrong")
                if not near(controller.HorizFeed.Value, 500.0 / 60.0):
                    raise RuntimeError(part + " horizontal feed is not 500 mm/min")
                tool = controller.Tool
                shape_name = str(getattr(tool, "ShapeName", "")).lower().replace("_", "").replace("-", "").replace(" ", "")
                descriptor = " ".join(
                    str(value) for value in (
                        getattr(tool, "Label", ""),
                        getattr(tool, "ToolType", ""),
                        getattr(tool, "ShapeName", ""),
                    )
                ).lower().replace("_", " ").replace("-", " ")
                normalized_descriptor = descriptor.replace(" ", "")
                standard_flat_shape = shape_name.rsplit("/", 1)[-1].rsplit("\\\\", 1)[-1].split(".", 1)[0] == "endmill"
                if "endmill" not in normalized_descriptor or ("flat" not in descriptor and not standard_flat_shape):
                    raise RuntimeError(part + " T1 is not a flat end mill")
                diameter = float(tool.Diameter.Value)
                if not math.isfinite(diameter) or not (1.0 <= diameter <= 40.0):
                    raise RuntimeError(part + " tool diameter is unreasonable")
                cutting_edge = getattr(tool, "CuttingEdgeHeight", None)
                if cutting_edge is None or float(cutting_edge.Value) < 18.0 - 1e-5:
                    raise RuntimeError(part + " tool cutting edge is too short")

                commands = list(operation.Path.Commands)
                if len(commands) < 10:
                    raise RuntimeError(part + " Profile path is empty or trivial")
                depths = [
                    float(command.Parameters["Z"])
                    for command in commands
                    if command.Name in ("G1", "G2", "G3", "G01", "G02", "G03")
                    and "Z" in command.Parameters
                ]
                if not depths or not near(min(depths), -18.0, 1e-3) or min(depths) < -18.001:
                    raise RuntimeError(part + " native Profile path misses or exceeds bottom")
                diameters[part] = diameter
                App.closeDocument(doc.Name)
                opened.pop()

            values = list(diameters.values())
            if not values or any(not near(value, values[0]) for value in values[1:]):
                raise RuntimeError("T1 diameter is not reused across all three Jobs")
            result = {{"ok": True, "diameters": diameters}}
        except Exception as exc:
            result = {{"ok": False, "error": str(exc)}}
        finally:
            for doc in opened:
                try:
                    App.closeDocument(doc.Name)
                except Exception:
                    pass
        print(MARKER + json.dumps(result, sort_keys=True))
        """
    )
    try:
        with tempfile.TemporaryDirectory(prefix="task_c03_eval_") as temp_dir:
            script = Path(temp_dir) / "check_native.py"
            script.write_text(checker, encoding="utf-8")
            completed = subprocess.run(
                ["/usr/bin/freecadcmd", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=180,
                check=False,
            )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    reports = [line[len(NATIVE_MARKER) :] for line in completed.stdout.splitlines() if line.startswith(NATIVE_MARKER)]
    if len(reports) != 1:
        return None
    try:
        report = json.loads(reports[0])
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(report, dict) or report.get("ok") is not True:
        return None
    diameters = report.get("diameters")
    if not isinstance(diameters, dict) or set(diameters) != set(PARTS):
        return None
    if any(not isinstance(value, (int, float)) for value in diameters.values()):
        return None
    return {name: float(diameters[name]) for name in PARTS}


def profile_coverage_ok(moves: list[Move], tool_diameter: float) -> bool:
    radius = tool_diameter / 2.0
    cutting_moves = [
        move
        for move in moves
        if move.motion in (1, 2, 3)
        and move.end_z is not None
        and (move.end_z <= TOL or move.start_z is not None and move.start_z <= TOL)
        and (move.xy_distance > TOL or move.motion in (2, 3))
    ]
    all_points = [point for move in cutting_moves for point in sample_cutting_xy(move)]
    if not all_points:
        return False
    if any(distance_to_part(point) < radius - 0.1 for point in all_points):
        return False

    final_moves = [
        move for move in cutting_moves
        if close(move.start_z, -18.0) and close(move.end_z, -18.0)
    ]
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for move in final_moves:
        samples = sample_move(move)
        segments.extend(zip(samples, samples[1:]))
    if not segments:
        return False

    boundary_points = []
    for x in range(-60, 61):
        boundary_points.extend(((float(x), -40.0), (float(x), 40.0)))
    for y in range(-39, 40):
        boundary_points.extend(((-60.0, float(y)), (60.0, float(y))))
    if any(
        min(point_segment_distance(point, start, end) for start, end in segments) > radius + 0.1
        for point in boundary_points
    ):
        return False
    travel = sum(
        sum(math.dist(first, second) for first, second in zip(samples, samples[1:]))
        for move in final_moves
        if len(samples := sample_move(move)) >= 2
    )
    return travel >= 0.9 * (2.0 * (120.0 + 80.0))


def main() -> bool:
    fcstd_paths = {name: TARGET / (name + ".FCStd") for name in PARTS}
    diameters = native_check(fcstd_paths)
    if diameters is None:
        return False
    for part in PARTS:
        parsed = parse_nc(TARGET / (part + ".nc"))
        if parsed is None:
            return False
        moves = parsed.get("moves")
        if not isinstance(moves, list) or not profile_coverage_ok(moves, diameters[part]):
            return False
    return True


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print(True if result else False)
