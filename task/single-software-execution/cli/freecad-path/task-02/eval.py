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
NC_PATH = TARGET / "task-02.nc"
FCSTD_PATH = TARGET / "task-02.FCStd"
TOL = 1e-3
WORD_RE = re.compile(
    r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)",
    re.IGNORECASE,
)
NATIVE_MARKER = "TASK_C02_NATIVE="


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


def sample_move(move: Move, count: int = 32) -> list[tuple[float, float]]:
    if None in (move.start_x, move.start_y, move.end_x, move.end_y):
        return []
    start = (float(move.start_x), float(move.start_y))
    end = (float(move.end_x), float(move.end_y))
    if move.motion == 1:
        return [start, end]
    if move.motion not in (2, 3) or move.i is None or move.j is None:
        return []
    cx = start[0] + move.i
    cy = start[1] + move.j
    radius = math.hypot(move.i, move.j)
    if radius <= TOL or abs(math.hypot(end[0] - cx, end[1] - cy) - radius) > max(0.01, radius * 1e-5):
        return []
    start_angle = math.atan2(start[1] - cy, start[0] - cx)
    end_angle = math.atan2(end[1] - cy, end[0] - cx)
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
    return [(cx + radius * math.cos(angle), cy + radius * math.sin(angle)) for angle in angles]


def arc_length(move: Move) -> float:
    points = sample_move(move)
    if len(points) < 2:
        return move.xy_distance
    return sum(math.dist(first, second) for first, second in zip(points, points[1:]))


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
    length_offset_active = False
    length_offset: int | None = None
    stopped_after_cut = ended_after_cut = retracted_after_cut = False
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
        if set(values) - set("NGMTSFXYZIJH"):
            return None
        if any(len(values.get(letter, [])) > 1 for letter in "TSFXYZIJH"):
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

        for g in values.get("G", []):
            if close(g, 20.0):
                metric = False
            elif close(g, 21.0):
                metric = True
            elif close(g, 90.0):
                absolute = True
            elif close(g, 91.0):
                absolute = False
            elif any(close(g, code) for code in (54.0, 55.0, 56.0, 57.0, 58.0, 59.0)):
                active_fixture = next(code for code in (54.0, 55.0, 56.0, 57.0, 58.0, 59.0) if close(g, code))
            elif close(g, 17.0):
                active_plane = 17
            elif any(
                close(g, code)
                for code in (10.0, 28.0, 30.0, 50.0, 51.0, 52.0, 53.0, 68.0, 69.0, 92.0, 92.1, 92.2, 92.3)
            ):
                return None
            elif any(close(g, code) for code in (0.0, 1.0, 2.0, 3.0)):
                motion = int(round(g))
            elif any(close(g, code) for code in (40.0, 43.0, 49.0, 61.0, 61.1, 64.0, 80.0, 91.1, 94.0)):
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
        if any(
            not any(close(code, allowed) for allowed in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 30.0))
            for code in m_codes
        ):
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
            if not tool_changed or not close(spindle_speed, 8500.0):
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

        has_axis = any(axis in values for axis in ("X", "Y", "Z"))
        if not has_axis:
            continue
        if motion is None or not metric or not absolute or not close(active_fixture, 54.0):
            return None
        nx = values.get("X", [x])[-1]
        ny = values.get("Y", [y])[-1]
        nz = values.get("Z", [z])[-1]
        move = Move(
            block,
            motion,
            x,
            y,
            z,
            nx,
            ny,
            nz,
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
                or move.end_z is None
                or min(move.start_z, move.end_z) <= 18.0 + TOL
            ):
                return None
            if moved_z and move.end_z is not None and move.end_z <= 18.0 + TOL:
                return None

        intersects_material_z = (
            move.end_z is not None
            and (move.end_z <= 18.0 + TOL or move.start_z is not None and move.start_z <= 18.0 + TOL)
        )
        is_cut = motion in (1, 2, 3) and intersects_material_z and (moved_xy or moved_z)
        if is_cut:
            if not (
                tool_changed
                and spindle_on
                and close(spindle_speed, 8500.0)
                and close(active_fixture, 54.0)
            ):
                return None
            if move.end_z < -TOL:
                return None
            if moved_xy:
                if not close(feed, 500.0):
                    return None
                cutting_depths.add(round(float(move.end_z), 6))
            if moved_z and not moved_xy and (feed is None or feed <= 0.0):
                return None
            last_cut_block = block
            retracted_after_cut = False
        if last_cut_block >= 0 and block > last_cut_block and motion == 0 and move.end_z is not None and move.end_z > 18.0 + TOL:
            retracted_after_cut = True
        moves.append(move)
        x, y, z = nx, ny, nz

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
    if not any(abs(depth) <= TOL for depth in cutting_depths) or len(cutting_depths) < 2:
        return None
    return {"moves": moves, "depths": sorted(cutting_depths, reverse=True)}


def native_check(path: Path) -> dict[str, object] | None:
    if not path.is_file() or not 1_000 <= path.stat().st_size <= 20_000_000:
        return None
    checker = textwrap.dedent(
        f"""
        import json
        import math
        import FreeCAD as App

        FILE = {str(path)!r}
        MARKER = {NATIVE_MARKER!r}
        result = {{"ok": False}}
        doc = None

        def near(value, expected, tol=1e-5):
            return abs(float(value) - expected) <= tol

        def box(shape):
            bb = shape.BoundBox
            return [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]

        def operation_depths(operation):
            x = y = z = None
            depths = set()
            final_points = []
            for command in operation.Path.Commands:
                params = command.Parameters
                nx = float(params["X"]) if "X" in params else x
                ny = float(params["Y"]) if "Y" in params else y
                nz = float(params["Z"]) if "Z" in params else z
                moved_xy = (
                    nx is not None and ny is not None and x is not None and y is not None
                    and (abs(nx - x) > 1e-6 or abs(ny - y) > 1e-6 or command.Name in ("G2", "G3", "G02", "G03"))
                )
                if command.Name in ("G1", "G2", "G3", "G01", "G02", "G03") and moved_xy and nz is not None:
                    depths.add(round(nz, 6))
                    if near(nz, 0.0, 1e-3):
                        final_points.append((nx, ny))
                x, y, z = nx, ny, nz
            return sorted(depths, reverse=True), final_points

        try:
            if tuple(App.Version()[:3]) != ("0", "21", "2"):
                raise RuntimeError("wrong FreeCAD version")
            doc = App.openDocument(FILE)
            if doc is None:
                raise RuntimeError("document did not open")
            doc.recompute()
            jobs = [
                obj for obj in doc.Objects
                if type(getattr(obj, "Proxy", None)).__module__ == "Path.Main.Job"
                and type(getattr(obj, "Proxy", None)).__name__ == "ObjectJob"
            ]
            if len(jobs) != 1:
                raise RuntimeError("expected one native Job")
            job = jobs[0]
            operations = list(job.Operations.Group)
            controllers = list(job.Tools.Group)
            models = list(job.Model.Group)
            if len(operations) != 2 or len(controllers) != 1 or len(models) != 1:
                raise RuntimeError("wrong Job group cardinality")
            modules = [type(getattr(op, "Proxy", None)).__module__ for op in operations]
            classes = [type(getattr(op, "Proxy", None)).__name__ for op in operations]
            if modules != ["Path.Op.Slot", "Path.Op.PocketShape"] or classes != ["ObjectSlot", "ObjectPocket"]:
                raise RuntimeError("wrong operation types or order")
            if not all(bool(op.Active) for op in operations):
                raise RuntimeError("inactive operation")

            model_shape = models[0].Shape
            expected_box = [-60.0, 60.0, -40.0, 40.0, 0.0, 18.0]
            if model_shape.isNull() or not model_shape.isValid() or len(model_shape.Solids) != 1:
                raise RuntimeError("model is not one valid solid")
            if any(not near(a, b) for a, b in zip(box(model_shape), expected_box)):
                raise RuntimeError("model bounds are wrong")
            expected_volume = 120.0 * 80.0 * 18.0 - (32.0 * 8.0 + math.pi * 4.0 * 4.0) * 18.0
            if not near(model_shape.Volume, expected_volume, 1e-3):
                raise RuntimeError("model does not contain the specified through-slot")
            if model_shape.isInside(App.Vector(0, 0, 9), 1e-7, True):
                raise RuntimeError("slot center still contains material")
            if not model_shape.isInside(App.Vector(30, 0, 9), 1e-7, True):
                raise RuntimeError("plate material outside the slot is missing")

            stock = job.Stock
            if stock.Shape.isNull() or not stock.Shape.isValid() or len(stock.Shape.Solids) != 1:
                raise RuntimeError("stock is invalid")
            if any(not near(a, b) for a, b in zip(box(stock.Shape), expected_box)) or not near(stock.Shape.Volume, 172800.0, 1e-3):
                raise RuntimeError("stock is not the complete starting block")
            for prop in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos"):
                if not near(getattr(stock, prop).Value, 0.0):
                    raise RuntimeError("stock extension is nonzero")
            if str(job.PostProcessor).lower() != "linuxcnc" or "G54" not in list(job.Fixtures):
                raise RuntimeError("wrong postprocessor or fixture")

            controller = controllers[0]
            tool = controller.Tool
            if int(controller.ToolNumber) != 1 or not near(tool.Diameter.Value, 6.0):
                raise RuntimeError("T1 is not a 6 mm tool")
            descriptor = " ".join(str(value) for value in (tool.Label, getattr(tool, "ToolType", ""), getattr(tool, "ShapeName", ""))).lower().replace("_", " ").replace("-", " ")
            if "endmill" not in descriptor.replace(" ", "") or "flat" not in descriptor:
                raise RuntimeError("T1 is not a flat end mill")
            if not near(controller.SpindleSpeed, 8500.0) or str(controller.SpindleDir) != "Forward":
                raise RuntimeError("wrong spindle configuration")
            if not near(controller.HorizFeed.Value, 500.0 / 60.0):
                raise RuntimeError("horizontal feed is not 500 mm/min")

            for operation in operations:
                if operation.ToolController is not controller:
                    raise RuntimeError("operation uses the wrong ToolController")
                if not near(operation.StartDepth.Value, 18.0) or not near(operation.FinalDepth.Value, 0.0):
                    raise RuntimeError("operation depths are wrong")
                if not (0.0 < operation.StepDown.Value < 18.0):
                    raise RuntimeError("operation is not configured for multiple layers")
                if operation.SafeHeight.Value <= 18.0 or operation.ClearanceHeight.Value <= 18.0:
                    raise RuntimeError("unsafe operation heights")
                depths, points = operation_depths(operation)
                if len(depths) < 2 or not any(near(depth, 0.0, 1e-3) for depth in depths) or min(depths) < -1e-3:
                    raise RuntimeError("actual operation path lacks safe layered cutting to Z0")
                if len(points) < 1:
                    raise RuntimeError("operation lacks final-depth XY cutting")

            slot, pocket = operations
            if len(slot.Base) != 0:
                raise RuntimeError("Slot should use its stated custom centerline")
            endpoints = sorted([
                (round(slot.CustomPoint1.x, 6), round(slot.CustomPoint1.y, 6), round(slot.CustomPoint1.z, 6)),
                (round(slot.CustomPoint2.x, 6), round(slot.CustomPoint2.y, 6), round(slot.CustomPoint2.z, 6)),
            ])
            if endpoints != [(-16.0, 0.0, 18.0), (16.0, 0.0, 18.0)]:
                raise RuntimeError("Slot centerline endpoints are wrong")

            selected = []
            for base, subnames in pocket.Base:
                for subname in subnames:
                    face = base.Shape.getElement(subname)
                    bb = face.BoundBox
                    if not (
                        bb.XMin >= -20.001 and bb.XMax <= 20.001
                        and bb.YMin >= -4.001 and bb.YMax <= 4.001
                        and near(bb.ZMin, 0.0) and near(bb.ZMax, 18.0)
                    ):
                        raise RuntimeError("Pocket Shape is based on non-slot geometry")
                    selected.append(subname)
            if len(set(selected)) != 4:
                raise RuntimeError("Pocket Shape does not reference all four slot walls")
            result = {{"ok": True, "tool_diameter": float(tool.Diameter.Value)}}
        except Exception as exc:
            result = {{"ok": False, "error": str(exc)}}
        finally:
            if doc is not None:
                App.closeDocument(doc.Name)
        print(MARKER + json.dumps(result, sort_keys=True))
        """
    )
    try:
        with tempfile.TemporaryDirectory(prefix="task_c02_eval_") as tmp:
            script = Path(tmp) / "check_native.py"
            script.write_text(checker, encoding="utf-8")
            completed = subprocess.run(
                ["/usr/bin/freecadcmd", str(script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=90,
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
    return report


def slot_coverage_ok(moves: list[Move], tool_diameter: float) -> bool:
    radius = tool_diameter / 2.0
    final_moves = [
        move
        for move in moves
        if move.motion in (1, 2, 3)
        and close(move.start_z, 0.0)
        and close(move.end_z, 0.0)
        and (move.xy_distance > TOL or move.motion in (2, 3))
    ]
    if not final_moves:
        return False
    points = [point for move in final_moves for point in sample_move(move)]
    if not points:
        return False

    inset_radius = 4.0 - radius
    if inset_radius <= 0.0:
        return False
    if any(
        point_segment_distance(point, (-16.0, 0.0), (16.0, 0.0)) > inset_radius + 0.075
        for point in points
    ):
        return False

    path_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for move in final_moves:
        samples = sample_move(move)
        path_segments.extend(zip(samples, samples[1:]))
    if not path_segments:
        return False

    grid_step = 0.25
    target_points = []
    for x_index in range(-80, 81):
        x = x_index * grid_step
        for y_index in range(-16, 17):
            y = y_index * grid_step
            point = (x, y)
            if point_segment_distance(point, (-16.0, 0.0), (16.0, 0.0)) <= 4.0 + TOL:
                target_points.append(point)
    if any(
        min(point_segment_distance(point, start, end) for start, end in path_segments) > radius + 0.075
        for point in target_points
    ):
        return False

    travel = sum(arc_length(move) for move in final_moves)
    slot_area = 32.0 * 8.0 + math.pi * 4.0 * 4.0
    return travel >= 0.75 * slot_area / tool_diameter


def main() -> bool:
    native = native_check(FCSTD_PATH)
    if native is None:
        return False
    parsed = parse_nc(NC_PATH)
    if parsed is None:
        return False
    diameter = native.get("tool_diameter")
    moves = parsed.get("moves")
    if not isinstance(diameter, (int, float)) or not isinstance(moves, list):
        return False
    return slot_coverage_ok(moves, float(diameter))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print(True if result else False)
