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
NC_PATH = TARGET / "task-01.nc"
FCSTD_PATH = TARGET / "task-01.FCStd"
TOL = 1e-3
WORD_RE = re.compile(
    r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:E[+-]?\d+)?)",
    re.IGNORECASE,
)
NATIVE_MARKER = "TASK_C01_NATIVE="


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
        arc = self.arc_geometry
        if arc is not None:
            _center_x, _center_y, radius, sweep = arc
            return radius * sweep
        return math.hypot(self.end_x - self.start_x, self.end_y - self.start_y)

    @property
    def arc_geometry(self) -> tuple[float, float, float, float] | None:
        if self.motion not in (2, 3) or None in (self.start_x, self.start_y, self.end_x, self.end_y):
            return None
        i_offset = 0.0 if self.i is None else self.i
        j_offset = 0.0 if self.j is None else self.j
        center_x = float(self.start_x) + i_offset
        center_y = float(self.start_y) + j_offset
        radius = math.hypot(i_offset, j_offset)
        if radius <= TOL:
            return None
        start_angle = math.atan2(float(self.start_y) - center_y, float(self.start_x) - center_x)
        end_angle = math.atan2(float(self.end_y) - center_y, float(self.end_x) - center_x)
        sweep = (start_angle - end_angle) % math.tau if self.motion == 2 else (end_angle - start_angle) % math.tau
        if sweep <= 1e-9:
            sweep = math.tau
        return center_x, center_y, radius, sweep


def close(a: float | None, b: float, tol: float = TOL) -> bool:
    return a is not None and abs(a - b) <= tol


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


def point_move_distance(point: tuple[float, float], move: Move) -> float:
    if None in (move.start_x, move.start_y, move.end_x, move.end_y):
        return math.inf
    arc = move.arc_geometry
    if arc is None:
        return point_segment_distance(
            point,
            (float(move.start_x), float(move.start_y)),
            (float(move.end_x), float(move.end_y)),
        )
    center_x, center_y, radius, sweep = arc
    start_angle = math.atan2(float(move.start_y) - center_y, float(move.start_x) - center_x)
    point_angle = math.atan2(point[1] - center_y, point[0] - center_x)
    directed = (start_angle - point_angle) % math.tau if move.motion == 2 else (point_angle - start_angle) % math.tau
    if directed <= sweep + 1e-9:
        return abs(math.hypot(point[0] - center_x, point[1] - center_y) - radius)
    return min(
        math.dist(point, (float(move.start_x), float(move.start_y))),
        math.dist(point, (float(move.end_x), float(move.end_y))),
    )


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


def words_for_line(line: str) -> list[tuple[str, float]] | None:
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


def parse_nc(path: Path) -> dict[str, object] | None:
    if not path.is_file() or not 300 <= path.stat().st_size <= 2_000_000:
        return None
    raw = path.read_text(encoding="utf-8", errors="strict")
    if "\x00" in raw:
        return None
    lines = strip_comments(raw).splitlines()

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
    stop_after_cut = False
    end_after_cut = False
    program_ended = False
    last_cut_block = -1
    retract_after_cut = False
    moves: list[Move] = []

    for block, line in enumerate(lines):
        words = words_for_line(line)
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
            not any(close(m, allowed) for allowed in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 30.0))
            for m in m_codes
        ):
            return None
        if len({round(m, 6) for m in m_codes}) != len(m_codes):
            return None
        if sum(any(close(m, code) for code in (3.0, 4.0, 5.0)) for m in m_codes) > 1:
            return None
        if any(close(m, 6.0) for m in m_codes) and any(close(m, code) for m in m_codes for code in (3.0, 4.0, 5.0)):
            return None
        if sum(any(close(m, code) for code in (2.0, 30.0)) for m in m_codes) > 1:
            return None
        if any(close(m, code) for m in m_codes for code in (2.0, 30.0)) and any(
            close(m, code) for m in m_codes for code in (3.0, 4.0, 6.0)
        ):
            return None
        if sum(any(close(m, code) for code in (7.0, 8.0, 9.0)) for m in m_codes) > 1:
            return None
        if any(close(m, 5.0) for m in m_codes):
            spindle_on = False
            if last_cut_block >= 0 and block > last_cut_block:
                stop_after_cut = True
        if any(close(m, 6.0) for m in m_codes):
            if selected_tool != 1 or spindle_on or length_offset_active:
                return None
            tool_changed = True
        if any(close(m, code) for m in m_codes for code in (3.0, 4.0)):
            if not tool_changed or not close(spindle_speed, 6000.0):
                return None
            if any(close(m, 4.0) for m in m_codes):
                return None
            spindle_on = True
        if any(close(m, code) for m in m_codes for code in (2.0, 30.0)):
            if any(axis in values for axis in ("X", "Y", "Z")):
                return None
            if last_cut_block >= 0 and block > last_cut_block:
                end_after_cut = True
                stop_after_cut = True
            spindle_on = False
            program_ended = True

        has_axis = any(axis in values for axis in ("X", "Y", "Z"))
        if not has_axis:
            continue
        if motion is None or not absolute or not metric or not close(active_fixture, 54.0):
            return None

        nx = values.get("X", [x])[-1]
        ny = values.get("Y", [y])[-1]
        nz = values.get("Z", [z])[-1]
        i_value = values.get("I", [None])[-1]
        j_value = values.get("J", [None])[-1]
        move = Move(block, motion, x, y, z, nx, ny, nz, feed, i_value, j_value)
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
            if (
                active_plane != 17
                or not ("I" in values or "J" in values)
                or None in (move.start_x, move.start_y, move.end_x, move.end_y)
            ):
                return None
            i_offset = 0.0 if move.i is None else move.i
            j_offset = 0.0 if move.j is None else move.j
            radius = math.hypot(i_offset, j_offset)
            end_radius = math.hypot(
                float(move.end_x) - (float(move.start_x) + i_offset),
                float(move.end_y) - (float(move.start_y) + j_offset),
            )
            if radius <= TOL or abs(end_radius - radius) > max(0.01, radius * 1e-5):
                return None
        elif "I" in values or "J" in values:
            return None

        if motion == 0:
            if moved_xy and (
                move.start_z is None
                or move.end_z is None
                or min(move.start_z, move.end_z) <= TOL
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
                and close(spindle_speed, 6000.0)
                and close(active_fixture, 54.0)
            ):
                return None
            if move.end_z < -8.0 - TOL:
                return None
            if moved_xy and not close(feed, 750.0):
                return None
            if moved_z and not moved_xy and (feed is None or feed <= 0.0):
                return None
            last_cut_block = block
            retract_after_cut = False
        if last_cut_block >= 0 and block > last_cut_block and motion == 0 and move.end_z is not None and move.end_z > TOL:
            retract_after_cut = True
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
    if not (last_cut_block >= 0 and stop_after_cut and end_after_cut and retract_after_cut):
        return None
    return {"moves": moves}


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

        def near(value, expected, tol=1e-6):
            return abs(float(value) - expected) <= tol

        def bbox_values(shape):
            box = shape.BoundBox
            return [box.XMin, box.XMax, box.YMin, box.YMax, box.ZMin, box.ZMax]

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
            if len(operations) != 1 or len(controllers) != 1 or len(models) != 1:
                raise RuntimeError("wrong Job group cardinality")

            op = operations[0]
            if type(getattr(op, "Proxy", None)).__module__ != "Path.Op.MillFace":
                raise RuntimeError("operation is not MillFace")
            if type(op.Proxy).__name__ != "ObjectFace" or not bool(op.Active):
                raise RuntimeError("inactive or invalid MillFace")
            if not near(op.StartDepth.Value, 0.0) or not near(op.FinalDepth.Value, -8.0):
                raise RuntimeError("wrong operation depths")
            if op.SafeHeight.Value <= 0.0 or op.ClearanceHeight.Value <= 0.0:
                raise RuntimeError("unsafe operation heights")

            expected_box = [-60.0, 60.0, -40.0, 40.0, -18.0, 0.0]
            for shape in (models[0].Shape, job.Stock.Shape):
                if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
                    raise RuntimeError("model or stock is not one valid solid")
                if any(not near(a, b) for a, b in zip(bbox_values(shape), expected_box)):
                    raise RuntimeError("model or zero-extension stock bounds are wrong")
            for prop in ("ExtXneg", "ExtXpos", "ExtYneg", "ExtYpos", "ExtZneg", "ExtZpos"):
                if not near(getattr(job.Stock, prop).Value, 0.0):
                    raise RuntimeError("stock extension is nonzero")
            if str(job.PostProcessor).lower() != "linuxcnc" or "G54" not in list(job.Fixtures):
                raise RuntimeError("wrong postprocessor or fixture")

            if len(op.Base) != 1 or len(op.Base[0][1]) != 1:
                raise RuntimeError("Face operation lacks one base face")
            base_obj, subnames = op.Base[0]
            selected_face = base_obj.Shape.getElement(subnames[0])
            face_box = selected_face.BoundBox
            if not (
                near(face_box.XMin, -60.0) and near(face_box.XMax, 60.0)
                and near(face_box.YMin, -40.0) and near(face_box.YMax, 40.0)
                and near(face_box.ZMin, 0.0) and near(face_box.ZMax, 0.0)
                and near(abs(selected_face.normalAt(0, 0).z), 1.0)
            ):
                raise RuntimeError("operation is not based on the top face")

            controller = controllers[0]
            if op.ToolController is not controller or int(controller.ToolNumber) != 1:
                raise RuntimeError("wrong ToolController")
            if not near(controller.SpindleSpeed, 6000.0) or str(controller.SpindleDir) != "Forward":
                raise RuntimeError("wrong spindle configuration")
            if not near(controller.HorizFeed.Value, 12.5):
                raise RuntimeError("horizontal feed is not 750 mm/min")
            tool = controller.Tool
            descriptor = " ".join(
                str(value) for value in (
                    getattr(tool, "Label", ""),
                    getattr(tool, "ToolFamily", ""),
                    getattr(tool, "ShapeName", ""),
                )
            ).lower().replace("_", " ").replace("-", " ")
            if "face mill" not in descriptor:
                raise RuntimeError("T1 is not identified as a face mill")
            diameter = float(tool.Diameter.Value)
            if not math.isfinite(diameter) or diameter <= 0.0 or diameter > 500.0:
                raise RuntimeError("invalid tool diameter")

            commands = list(op.Path.Commands)
            if len(commands) < 10:
                raise RuntimeError("MillFace path is empty or trivial")
            path_z = [float(c.Parameters["Z"]) for c in commands if "Z" in c.Parameters]
            if not path_z or not near(min(path_z), -8.0, 1e-3):
                raise RuntimeError("actual MillFace path misses final depth")
            result = {{"ok": True, "tool_diameter": diameter}}
        except Exception as exc:
            result = {{"ok": False, "error": str(exc)}}
        finally:
            if doc is not None:
                App.closeDocument(doc.Name)
        print(MARKER + json.dumps(result, sort_keys=True))
        """
    )
    try:
        with tempfile.TemporaryDirectory(prefix="task_c01_eval_") as tmp:
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


def coverage_ok(moves: list[Move], tool_diameter: float) -> bool:
    radius = tool_diameter / 2.0
    final_moves = [
        move
        for move in moves
        if move.motion in (1, 2, 3)
        and close(move.start_z, -8.0)
        and close(move.end_z, -8.0)
        and move.xy_distance > TOL
    ]
    if not final_moves:
        return False
    xs = [value for move in final_moves for value in (move.start_x, move.end_x) if value is not None]
    ys = [value for move in final_moves for value in (move.start_y, move.end_y) if value is not None]
    if not xs or not ys:
        return False
    if min(xs) - radius > -60.0 + TOL or max(xs) + radius < 60.0 - TOL:
        return False
    if min(ys) - radius > -40.0 + TOL or max(ys) + radius < 40.0 - TOL:
        return False
    segments = [
        ((float(move.start_x), float(move.start_y)), (float(move.end_x), float(move.end_y)))
        for move in final_moves
        if None not in (move.start_x, move.start_y, move.end_x, move.end_y)
    ]
    if not segments:
        return False
    for x in range(-60, 61):
        for y in range(-40, 41):
            point = (float(x), float(y))
            if min(point_segment_distance(point, start, end) for start, end in segments) > radius + 0.1:
                return False
    travel = sum(move.xy_distance for move in final_moves)
    return travel >= 0.60 * (120.0 * 80.0) / tool_diameter


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
    return coverage_ok(moves, float(diameter))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print(True if result else False)
