from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-15.nc"
SAFE_POINTS = {
    (-45.0, -24.0), (-45.0, -8.0), (-45.0, 8.0),
    (-15.0, -24.0), (-15.0, -8.0), (-15.0, 8.0), (-15.0, 24.0),
    (15.0, -24.0), (15.0, -8.0), (15.0, 8.0),
    (45.0, -24.0), (45.0, -8.0), (45.0, 8.0),
}
FORBIDDEN_POINTS = {(-45.0, 24.0), (15.0, 24.0), (45.0, 24.0)}
FIXTURES = ((-54.0, 27.0, -36.0, 37.0), (6.0, 27.0, 24.0, 37.0), (36.0, 27.0, 54.0, 37.0))
TOOL_RADIUS = {1: 1.5, 2: 2.5}
SPINDLE = {1: 8000.0, 2: 5000.0}
FEED = {1: 250.0, 2: 180.0}
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Segment:
    start: Point
    end: Point
    motion: int
    tool: int | None
    wcs: int | None


@dataclass(frozen=True)
class CycleEvent:
    x: float
    y: float
    bottom: float
    r_plane: float
    return_z: float
    cycle: int
    tool: int | None
    spindle: float | None
    spindle_on: bool
    feed: float | None
    wcs: int | None
    length_comp: bool
    h_offset: int | None


@dataclass
class Program:
    events: list[CycleEvent]
    segments: list[Segment]
    tool_changes: list[int]
    executable_blocks: int
    terminated: bool


@dataclass(frozen=True)
class RigidTransform:
    c: float
    s: float
    tx: float
    ty: float

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return self.c * x - self.s * y + self.tx, self.s * x + self.c * y + self.ty


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def strip_comments(source: str) -> list[str]:
    lines: list[str] = []
    depth = 0
    for raw in source.upper().splitlines():
        clean: list[str] = []
        for char in raw:
            if char == ";" and depth == 0:
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    raise EvaluationError("unmatched closing comment")
                depth -= 1
            elif depth == 0:
                clean.append(char)
        lines.append("".join(clean).strip())
    if depth:
        raise EvaluationError("unterminated parenthesis comment")
    return lines


def parse_program(source: str) -> Program:
    units: str | None = None
    absolute: bool | None = None
    motion: int | None = None
    x = y = z = None
    pending_tool = active_tool = None
    spindle = feed = None
    spindle_on = False
    wcs = None
    length_comp = False
    h_offset = None
    cycle = None
    cycle_z = cycle_r = cycle_initial_z = None
    return_initial = True
    events: list[CycleEvent] = []
    segments: list[Segment] = []
    tool_changes: list[int] = []
    executable = 0
    terminated = False

    for line in strip_comments(source):
        if not line or line == "%":
            continue
        if terminated:
            raise EvaluationError("executable content after M30")
        if any(char in line for char in "#[]="):
            raise EvaluationError("expressions and macros are unsupported")
        if re.fullmatch(r"/?\s*O\d+", line):
            executable += 1
            continue
        words = WORD_RE.findall(line)
        residue = re.sub(r"[\s/]+", "", WORD_RE.sub("", line))
        if not words or residue:
            raise EvaluationError(f"unknown executable content: {line!r}")
        executable += 1
        grouped: dict[str, list[float]] = {}
        for letter, raw_value in words:
            grouped.setdefault(letter, []).append(float(raw_value))
        for letter in ("X", "Y", "Z", "R", "F", "S", "T", "H", "Q", "P"):
            if len(grouped.get(letter, [])) > 1:
                raise EvaluationError(f"ambiguous repeated {letter} word")
        gcodes = grouped.get("G", [])
        mcodes = []
        for raw_m in grouped.get("M", []):
            if not close(raw_m, round(raw_m), 1e-7):
                raise EvaluationError("non-integral M code")
            mcode = int(round(raw_m))
            if mcode not in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 30):
                raise EvaluationError(f"unsupported M code M{mcode}")
            mcodes.append(mcode)
        reference_return = False
        cancel_cycle = False
        new_cycle = None
        for raw_g in gcodes:
            rounded = int(round(raw_g))
            if not close(raw_g, rounded, 1e-7):
                raise EvaluationError(f"unsupported non-integral G code G{raw_g:g}")
            if rounded == 20:
                units = "inch"
            elif rounded == 21:
                units = "mm"
            elif rounded == 90:
                absolute = True
            elif rounded == 91:
                absolute = False
            elif rounded in (0, 1):
                motion = rounded
            elif rounded == 28:
                reference_return = True
            elif rounded in (54, 55, 56, 57, 58, 59):
                if wcs != rounded:
                    x = y = z = None
                wcs = rounded
            elif rounded == 43:
                length_comp = True
            elif rounded == 49:
                length_comp = False
                h_offset = None
            elif rounded in (81, 82, 83):
                new_cycle = rounded
            elif rounded == 80:
                cancel_cycle = True
            elif rounded == 98:
                return_initial = True
            elif rounded == 99:
                return_initial = False
            elif rounded in (17, 40, 94):
                pass
            else:
                raise EvaluationError(f"unsupported G code G{rounded}")

        if "T" in grouped:
            raw_tool = grouped["T"][0]
            if not close(raw_tool, round(raw_tool), 1e-7):
                raise EvaluationError("non-integral tool number")
            pending_tool = int(round(raw_tool))
        if "S" in grouped:
            spindle = grouped["S"][0]
        if "H" in grouped:
            raw_h = grouped["H"][0]
            if not close(raw_h, round(raw_h), 1e-7):
                raise EvaluationError("non-integral H offset")
            h_offset = int(round(raw_h))
        if 6 in mcodes:
            if pending_tool is None:
                raise EvaluationError("M6 without a pending tool")
            active_tool = pending_tool
            tool_changes.append(active_tool)
        if 3 in mcodes or 4 in mcodes:
            spindle_on = True
        if 5 in mcodes:
            spindle_on = False
        if 30 in mcodes:
            allowed_letters = {"N", "M"}
            if any(letter not in allowed_letters for letter in grouped) or mcodes != [30]:
                raise EvaluationError("M30 must be a terminal-only block")
            terminated = True
            continue

        if units is None and any(letter in grouped for letter in ("X", "Y", "Z", "R", "F", "Q")):
            raise EvaluationError("coordinate/feed before unit selection")
        factor = 25.4 if units == "inch" else 1.0
        if "F" in grouped:
            feed = grouped["F"][0] * factor
        if "Q" in grouped and grouped["Q"][0] <= 0.0:
            raise EvaluationError("non-positive peck amount")
        if new_cycle == 83 and "Q" not in grouped:
            raise EvaluationError("G83 requires an explicit positive Q peck amount")
        if reference_return:
            x = y = z = None
            cycle = cycle_z = cycle_r = cycle_initial_z = None
            continue
        if absolute is None and any(letter in grouped for letter in ("X", "Y", "Z", "R")):
            raise EvaluationError("coordinate before distance mode")

        old = (x, y, z)

        def coordinate(letter: str, current: float | None) -> float | None:
            if letter not in grouped:
                return current
            value = grouped[letter][0] * factor
            if absolute:
                return value
            if current is None:
                raise EvaluationError(f"incremental {letter} with unknown origin")
            return current + value

        x = coordinate("X", x)
        y = coordinate("Y", y)
        z = coordinate("Z", z)

        if new_cycle is not None:
            cycle = new_cycle
            cycle_initial_z = old[2]
        if "Z" in grouped and cycle is not None:
            cycle_z = z
        if "R" in grouped:
            raw_r = grouped["R"][0] * factor
            if absolute:
                cycle_r = raw_r
            else:
                if old[2] is None:
                    raise EvaluationError("incremental R with unknown origin")
                cycle_r = old[2] + raw_r
        if cancel_cycle:
            cycle = cycle_z = cycle_r = cycle_initial_z = None

        cycle_visit = cycle is not None and (
            new_cycle is not None or "X" in grouped or "Y" in grouped
        )
        if cycle_visit:
            if x is None or y is None or cycle_z is None or cycle_r is None:
                raise EvaluationError("incomplete canned-cycle position")
            if active_tool is None:
                raise EvaluationError("canned cycle without active tool")
            return_z = cycle_initial_z if return_initial else cycle_r
            if return_z is None:
                raise EvaluationError("G98 cycle with unknown initial plane")
            if old[0] is not None and old[1] is not None and old[2] is not None:
                start = Point(old[0], old[1], old[2])
                end = Point(x, y, old[2])
                if math.hypot(end.x - start.x, end.y - start.y) > 1e-9:
                    segments.append(Segment(start, end, 0, active_tool, wcs))
            events.append(
                CycleEvent(
                    x, y, cycle_z, cycle_r, return_z, cycle, active_tool,
                    spindle, spindle_on, feed, wcs, length_comp, h_offset,
                )
            )
            z = return_z
            continue

        if any(letter in grouped for letter in ("X", "Y", "Z")) and motion is not None:
            if all(value is not None for value in old) and x is not None and y is not None and z is not None:
                start = Point(float(old[0]), float(old[1]), float(old[2]))
                end = Point(x, y, z)
                if math.dist((start.x, start.y, start.z), (end.x, end.y, end.z)) > 1e-9:
                    segments.append(Segment(start, end, motion, active_tool, wcs))

    return Program(events, segments, tool_changes, executable, terminated)


def nearest_set(points: list[tuple[float, float]], expected: set[tuple[float, float]], tolerance: float) -> bool:
    remaining = set(expected)
    for point in points:
        matches = [target for target in remaining if math.dist(point, target) <= tolerance]
        if len(matches) != 1:
            return False
        remaining.remove(matches[0])
    return not remaining


def find_transform(observed: list[tuple[float, float]]) -> RigidTransform:
    if len(observed) != len(SAFE_POINTS):
        raise EvaluationError("wrong number of observed hole coordinates")
    canonical = list(SAFE_POINTS)
    for first_index, first in enumerate(observed):
        for second_index, second in enumerate(observed):
            if first_index == second_index:
                continue
            ox, oy = second[0] - first[0], second[1] - first[1]
            od = math.hypot(ox, oy)
            if od < 1.0:
                continue
            for target_first in canonical:
                for target_second in canonical:
                    if target_first == target_second:
                        continue
                    cx, cy = target_second[0] - target_first[0], target_second[1] - target_first[1]
                    cd = math.hypot(cx, cy)
                    if abs(cd - od) > 0.35:
                        continue
                    c = (ox * cx + oy * cy) / (od * cd)
                    s = (ox * cy - oy * cx) / (od * cd)
                    length = math.hypot(c, s)
                    if length < 0.999 or length > 1.001:
                        continue
                    c /= length
                    s /= length
                    tx = target_first[0] - (c * first[0] - s * first[1])
                    ty = target_first[1] - (s * first[0] + c * first[1])
                    transform = RigidTransform(c, s, tx, ty)
                    mapped = [transform.apply(x, y) for x, y in observed]
                    if nearest_set(mapped, SAFE_POINTS, 0.35):
                        return transform
    raise EvaluationError("hole coordinates do not form the required rigidly transformed safe set")


def rect_distance(x: float, y: float, rectangle: tuple[float, float, float, float]) -> float:
    xmin, ymin, xmax, ymax = rectangle
    return math.hypot(max(xmin - x, 0.0, x - xmax), max(ymin - y, 0.0, y - ymax))


def sample_segment(segment: Segment, spacing: float = 0.5) -> list[Point]:
    length = math.dist(
        (segment.start.x, segment.start.y, segment.start.z),
        (segment.end.x, segment.end.y, segment.end.z),
    )
    count = max(1, int(math.ceil(length / spacing)))
    return [
        Point(
            segment.start.x + (segment.end.x - segment.start.x) * index / count,
            segment.start.y + (segment.end.y - segment.start.y) * index / count,
            segment.start.z + (segment.end.z - segment.start.z) * index / count,
        )
        for index in range(count + 1)
    ]


def validate_program(program: Program) -> None:
    if not program.terminated or program.executable_blocks < 30:
        raise EvaluationError("program is incomplete")
    if program.tool_changes != [1, 2]:
        raise EvaluationError("expected exactly one T1 change followed by one T2 change")
    events_by_tool = {tool: [event for event in program.events if event.tool == tool] for tool in (1, 2)}
    if any(event.tool not in (1, 2) for event in program.events):
        raise EvaluationError("unexpected cutting tool")
    if any(len(events_by_tool[tool]) != 13 for tool in (1, 2)):
        raise EvaluationError("each tool must execute exactly thirteen cutting cycles")
    for tool, events in events_by_tool.items():
        for event in events:
            if (
                not event.spindle_on
                or event.spindle is None
                or not close(event.spindle, SPINDLE[tool], 1.0)
                or event.feed is None
                or not close(event.feed, FEED[tool], 0.8)
                or event.wcs is None
                or not event.length_comp
                or event.h_offset is None
                or event.h_offset <= 0
            ):
                raise EvaluationError(f"tool {tool} cycle state is incomplete or incorrect")

    transform = find_transform([(event.x, event.y) for event in events_by_tool[1]])
    mapped_drill = [transform.apply(event.x, event.y) for event in events_by_tool[2]]
    if not nearest_set(mapped_drill, SAFE_POINTS, 0.35):
        raise EvaluationError("T2 does not drill the same thirteen safe holes")
    for events in events_by_tool.values():
        mapped = [transform.apply(event.x, event.y) for event in events]
        if any(math.dist(point, forbidden) <= 0.35 for point in mapped for forbidden in FORBIDDEN_POINTS):
            raise EvaluationError("forbidden hole appears in a cutting cycle")

    drill_bottoms = [event.bottom for event in events_by_tool[2]]
    if max(drill_bottoms) - min(drill_bottoms) > 0.35:
        raise EvaluationError("inconsistent through-drilling depths")
    surface_z = sum(drill_bottoms) / len(drill_bottoms) + 18.0
    drill_depths = [surface_z - event.bottom for event in events_by_tool[2]]
    spot_depths = [surface_z - event.bottom for event in events_by_tool[1]]
    if any(depth < 17.8 or depth > 22.0 for depth in drill_depths):
        raise EvaluationError("T2 does not drill through the 18 mm plate")
    if any(depth < 0.2 or depth > 3.0 for depth in spot_depths):
        raise EvaluationError("T1 does not perform a plausible spotting cut")
    for events in events_by_tool.values():
        if any(event.return_z < surface_z + 12.8 for event in events):
            raise EvaluationError("canned-cycle lateral return plane is below fixture-top clearance")

    for segment in program.segments:
        if segment.tool not in (1, 2) or segment.wcs is None:
            continue
        if segment.motion == 1:
            raise EvaluationError("unvalidated standalone feed cutting move")
        horizontal = math.hypot(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
        if horizontal <= 0.05:
            continue
        if min(segment.start.z, segment.end.z) >= surface_z + 12.8:
            continue
        radius = TOOL_RADIUS[segment.tool]
        for point in sample_segment(segment):
            mapped_x, mapped_y = transform.apply(point.x, point.y)
            if point.z <= surface_z + 10.05 and any(
                rect_distance(mapped_x, mapped_y, rectangle) < radius + 2.95
                for rectangle in FIXTURES
            ):
                raise EvaluationError("low lateral tool motion violates fixture clearance")
        if segment.motion == 0:
            raise EvaluationError("rapid lateral positioning is below the required clearance plane")


def evaluate_text(source: str) -> bool:
    try:
        validate_program(parse_program(source))
        return True
    except (EvaluationError, ValueError, OverflowError):
        return False


def main() -> bool:
    path = TARGET / NC_NAME
    if not path.is_file() or path.stat().st_size < 100 or path.stat().st_size > 5_000_000:
        return False
    return evaluate_text(path.read_text(encoding="utf-8", errors="strict"))


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)


