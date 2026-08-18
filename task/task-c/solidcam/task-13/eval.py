from __future__ import annotations

import math
import os
import re
import statistics
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_PATH = TARGET / "task-13.nc"
WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.I)

BLIND = {
    (-45.0, 0.0),
    (-30.0, 0.0),
    (-15.0, 0.0),
    (0.0, 0.0),
    (15.0, 0.0),
    (30.0, 0.0),
    (45.0, 0.0),
    (0.0, 25.0),
}
COUNTERBORE = {(-30.0, 15.0), (-10.0, 15.0), (10.0, 15.0), (30.0, 15.0)}
THROUGH = {
    (-45.0, -25.0),
    (-45.0, 25.0),
    (-15.0, -25.0),
    (-15.0, 25.0),
    (15.0, -25.0),
    (15.0, 25.0),
    (45.0, -25.0),
    (45.0, 25.0),
}
THREADED = {(-30.0, -15.0), (-10.0, -15.0), (10.0, -15.0), (30.0, -15.0)}
ALL_HOLES = BLIND | COUNTERBORE | THROUGH | THREADED


@dataclass(frozen=True)
class Action:
    kind: str
    code: int
    tool: int | None
    spindle: float | None
    feed: float | None
    start: tuple[float | None, float | None, float | None]
    end: tuple[float | None, float | None, float | None]
    i: float | None = None
    j: float | None = None


@dataclass
class Program:
    actions: list[Action]
    tools: set[int]
    saw_g21: bool
    saw_g90: bool
    saw_g20: bool
    saw_m30: bool


@dataclass(frozen=True)
class Transform:
    expected_origin: tuple[float, float]
    actual_origin: tuple[float, float]
    expected_axis: tuple[float, float]
    actual_axis: tuple[float, float]
    determinant: int

    def apply(self, point: tuple[float, float]) -> tuple[float, float]:
        ex, ey = self.expected_axis
        ax, ay = self.actual_axis
        px = point[0] - self.expected_origin[0]
        py = point[1] - self.expected_origin[1]
        along = px * ex + py * ey
        across = px * -ey + py * ex
        actual_perp = (-ay, ax)
        return (
            self.actual_origin[0]
            + along * ax
            + self.determinant * across * actual_perp[0],
            self.actual_origin[1]
            + along * ay
            + self.determinant * across * actual_perp[1],
        )


def uncomment(raw: str) -> list[str]:
    lines: list[str] = []
    for original in raw.upper().splitlines():
        line = original
        previous = None
        while previous != line:
            previous = line
            line = re.sub(r"\([^()]*\)", " ", line)
        line = line.split(";", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def parse(path: Path) -> Program:
    raw_bytes = path.read_bytes()
    if not 500 <= len(raw_bytes) <= 5_000_000 or b"\x00" in raw_bytes:
        raise ValueError("invalid NC size or binary content")
    raw = raw_bytes.decode("ascii", errors="ignore")
    if sum(ch.isprintable() or ch in "\r\n\t" for ch in raw) / max(len(raw), 1) < 0.98:
        raise ValueError("NC is not printable text")

    x = y = z = None
    tool: int | None = None
    spindle = feed = None
    absolute = True
    motion_mode: int | None = None
    active_cycle: int | None = None
    cycle_z: float | None = None
    tools: set[int] = set()
    actions: list[Action] = []
    saw_g21 = saw_g90 = saw_g20 = saw_m30 = False

    ended = False
    for line in uncomment(raw):
        if ended:
            if line.strip().strip("%").strip():
                raise ValueError("executable content after M30")
            continue
        words = [(letter.upper(), float(value)) for letter, value in WORD_RE.findall(line)]
        if not words:
            continue
        by_letter: dict[str, list[float]] = {}
        for letter, value in words:
            by_letter.setdefault(letter, []).append(value)

        gcodes = {int(round(value)) for value in by_letter.get("G", [])}
        mcodes = {int(round(value)) for value in by_letter.get("M", [])}
        saw_g21 |= 21 in gcodes
        saw_g20 |= 20 in gcodes
        saw_g90 |= 90 in gcodes
        saw_m30 |= 30 in mcodes
        if 30 in mcodes:
            forbidden = set(by_letter) & {"G", "T", "S", "F", "X", "Y", "Z", "I", "J", "K", "R"}
            if forbidden or any(code != 30 for code in mcodes):
                raise ValueError("motion or setup words on M30 block")
            ended = True
            continue
        if 90 in gcodes:
            absolute = True
        if 91 in gcodes:
            absolute = False
        if "T" in by_letter:
            tool = int(round(by_letter["T"][-1]))
            tools.add(tool)
        if "S" in by_letter:
            spindle = by_letter["S"][-1]
        if "F" in by_letter:
            feed = by_letter["F"][-1]

        for candidate in (0, 1, 2, 3):
            if candidate in gcodes:
                motion_mode = candidate
        if 80 in gcodes:
            active_cycle = None
            cycle_z = None
        cycle_codes = gcodes & {73, 74, 76, 81, 82, 83, 84, 85, 86, 87, 88, 89}
        cycle_started = bool(cycle_codes)
        if cycle_started:
            active_cycle = sorted(cycle_codes)[0]
        if active_cycle is not None and "Z" in by_letter:
            cycle_z = by_letter["Z"][-1]

        start = (x, y, z)

        def coordinate(letter: str, current: float | None) -> float | None:
            if letter not in by_letter:
                return current
            value = by_letter[letter][-1]
            if absolute or current is None:
                return value
            return current + value

        nx = coordinate("X", x)
        ny = coordinate("Y", y)
        nz = coordinate("Z", z)
        has_axis = any(letter in by_letter for letter in ("X", "Y", "Z"))

        if active_cycle is not None and (cycle_started or "X" in by_letter or "Y" in by_letter):
            if nx is not None and ny is not None and cycle_z is not None:
                actions.append(
                    Action(
                        "cycle",
                        active_cycle,
                        tool,
                        spindle,
                        feed,
                        start,
                        (nx, ny, cycle_z),
                    )
                )
            x, y = nx, ny
            continue

        if has_axis and motion_mode in {0, 1, 2, 3}:
            end = (nx, ny, nz)
            if motion_mode in {1, 2, 3}:
                actions.append(
                    Action(
                        "arc" if motion_mode in {2, 3} else "line",
                        motion_mode,
                        tool,
                        spindle,
                        feed,
                        start,
                        end,
                        by_letter.get("I", [None])[-1],
                        by_letter.get("J", [None])[-1],
                    )
                )
            x, y, z = end

    return Program(actions, tools, saw_g21, saw_g90, saw_g20, saw_m30)


def close(actual: float | None, expected: float, tolerance: float) -> bool:
    return actual is not None and abs(actual - expected) <= tolerance


def at_point(action: Action, point: tuple[float, float], tolerance: float = 0.35) -> bool:
    x, y, _z = action.end
    return close(x, point[0], tolerance) and close(y, point[1], tolerance)


def unique_points(actions: list[Action], tolerance: float = 0.2) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for action in actions:
        x, y, _z = action.end
        if x is None or y is None:
            continue
        point = (x, y)
        if not any(math.dist(point, existing) <= tolerance for existing in points):
            points.append(point)
    return points


def infer_transform(program: Program) -> Transform | None:
    spot_actions = matching_actions(program, 1, 8000.0, 250.0)
    observed = unique_points(spot_actions)
    if len(observed) != len(ALL_HOLES):
        return None
    expected_a = (-45.0, -25.0)
    expected_b = (45.0, 25.0)
    evx = expected_b[0] - expected_a[0]
    evy = expected_b[1] - expected_a[1]
    expected_distance = math.hypot(evx, evy)
    expected_axis = (evx / expected_distance, evy / expected_distance)

    for actual_a in observed:
        for actual_b in observed:
            if actual_a == actual_b:
                continue
            avx = actual_b[0] - actual_a[0]
            avy = actual_b[1] - actual_a[1]
            actual_distance = math.hypot(avx, avy)
            if abs(actual_distance - expected_distance) > 0.7:
                continue
            actual_axis = (avx / actual_distance, avy / actual_distance)
            for determinant in (1, -1):
                transform = Transform(
                    expected_a,
                    actual_a,
                    expected_axis,
                    actual_axis,
                    determinant,
                )
                mapped = [transform.apply(point) for point in ALL_HOLES]
                if all(any(math.dist(point, item) <= 0.45 for item in observed) for point in mapped):
                    if all(any(math.dist(point, item) <= 0.45 for item in mapped) for point in observed):
                        return transform
    return None


def matching_actions(
    program: Program,
    tool: int,
    spindle: float,
    feed: float | None = None,
) -> list[Action]:
    return [
        action
        for action in program.actions
        if action.tool == tool
        and close(action.spindle, spindle, 1.0)
        and (feed is None or close(action.feed, feed, 0.6))
    ]


def point_depth_ok(
    actions: list[Action],
    point: tuple[float, float],
    minimum_depth: float,
    maximum_depth: float,
    z_zero: float,
) -> bool:
    for action in actions:
        if not at_point(action, point):
            continue
        z_value = action.end[2]
        depth = None if z_value is None else z_zero - z_value
        if depth is not None and minimum_depth <= depth <= maximum_depth:
            return True
    return False


def no_overdeep(
    actions: list[Action], point: tuple[float, float], maximum_depth: float, z_zero: float
) -> bool:
    return all(
        action.end[2] is None or z_zero - action.end[2] <= maximum_depth
        for action in actions
        if at_point(action, point)
    )


def arc_geometry(
    action: Action,
) -> tuple[tuple[float, float], float, float] | None:
    if action.kind != "arc" or action.i is None or action.j is None:
        return None
    sx, sy, sz = action.start
    ex, ey, ez = action.end
    if None in {sx, sy, sz, ex, ey, ez}:
        return None
    cx = float(sx) + action.i
    cy = float(sy) + action.j
    start_angle = math.atan2(float(sy) - cy, float(sx) - cx)
    end_angle = math.atan2(float(ey) - cy, float(ex) - cx)
    if action.code == 2:
        sweep = (start_angle - end_angle) % (2 * math.pi)
    else:
        sweep = (end_angle - start_angle) % (2 * math.pi)
    if math.hypot(float(ex) - float(sx), float(ey) - float(sy)) <= 0.02:
        sweep = 2 * math.pi
    if sweep <= 0.02:
        return None
    pitch = abs(float(ez) - float(sz)) * (2 * math.pi / sweep)
    return (cx, cy), pitch, math.hypot(float(sx) - cx, float(sy) - cy)


def infer_z_zero(program: Program, transform: Transform) -> float | None:
    drill_actions = matching_actions(program, 2, 5000.0, 180.0)
    bore_actions = matching_actions(program, 3, 6500.0, 300.0)
    drill_candidates: list[float] = []
    bore_candidates: list[float] = []

    for expected, nominal_depth in [(point, 7.0) for point in BLIND] + [
        (point, 8.0) for point in COUNTERBORE
    ]:
        actual = transform.apply(expected)
        z_values = [action.end[2] for action in drill_actions if at_point(action, actual)]
        z_values = [value for value in z_values if value is not None]
        if z_values:
            drill_candidates.append(min(z_values) + nominal_depth)

    for expected in COUNTERBORE:
        actual = transform.apply(expected)
        z_values: list[float] = []
        for action in bore_actions:
            if at_point(action, actual) and action.end[2] is not None:
                z_values.append(action.end[2])
            geometry = arc_geometry(action)
            if geometry is not None and math.dist(geometry[0], actual) <= 0.45:
                z_values.extend(value for value in (action.start[2], action.end[2]) if value is not None)
        if z_values:
            bore_candidates.append(min(z_values) + 3.0)

    if len(drill_candidates) != 12 or len(bore_candidates) != 4:
        return None
    drill_zero = statistics.median(drill_candidates)
    bore_zero = statistics.median(bore_candidates)
    if abs(drill_zero - bore_zero) > 1.0:
        return None
    if any(abs(value - drill_zero) > 1.2 for value in drill_candidates):
        return None
    if any(abs(value - bore_zero) > 0.8 for value in bore_candidates):
        return None
    return (drill_zero + bore_zero) / 2.0


def check_spotting(program: Program, transform: Transform, z_zero: float) -> bool:
    actions = matching_actions(program, 1, 8000.0, 250.0)
    if not actions:
        return False
    return all(
        point_depth_ok(actions, transform.apply(point), 0.3, 6.5, z_zero)
        for point in ALL_HOLES
    )


def check_drilling(program: Program, transform: Transform, z_zero: float) -> bool:
    actions = matching_actions(program, 2, 5000.0, 180.0)
    if not actions:
        return False
    if not all(
        point_depth_ok(actions, transform.apply(point), 6.0, 9.5, z_zero)
        for point in BLIND
    ):
        return False
    if not all(
        point_depth_ok(actions, transform.apply(point), 7.0, 10.5, z_zero)
        for point in COUNTERBORE
    ):
        return False
    if not all(
        point_depth_ok(actions, transform.apply(point), 17.0, 23.0, z_zero)
        for point in THROUGH
    ):
        return False
    if not all(
        no_overdeep(actions, transform.apply(point), 11.0, z_zero)
        for point in BLIND | COUNTERBORE
    ):
        return False
    return not any(
        at_point(action, transform.apply(point)) for action in actions for point in THREADED
    )


def check_counterbores(program: Program, transform: Transform, z_zero: float) -> bool:
    actions = matching_actions(program, 3, 6500.0, 300.0)
    if not actions:
        return False
    for expected in COUNTERBORE:
        point = transform.apply(expected)
        direct = point_depth_ok(actions, point, 2.5, 4.5, z_zero)
        circular = False
        for action in actions:
            geometry = arc_geometry(action)
            if geometry is None:
                continue
            center, _pitch, radius = geometry
            z_values = [value for value in (action.start[2], action.end[2]) if value is not None]
            if (
                math.dist(center, point) <= 0.45
                and 0.05 <= radius <= 5.5
                and z_values
                and 2.5 <= z_zero - min(z_values) <= 4.5
            ):
                circular = True
                break
        if not (direct or circular):
            return False
    return True


def check_threads(program: Program, transform: Transform, z_zero: float) -> bool:
    tool_actions = matching_actions(program, 4, 4500.0)
    if not tool_actions or not any(close(action.feed, 140.0, 0.6) for action in tool_actions):
        return False
    arcs = [action for action in tool_actions if action.kind == "arc"]
    for expected in THREADED:
        point = transform.apply(expected)
        z_values: list[float] = []
        pitches: list[float] = []
        for action in arcs:
            geometry = arc_geometry(action)
            if geometry is None:
                continue
            center, pitch, radius = geometry
            if math.dist(center, point) > 0.45 or not 0.2 <= radius <= 3.3:
                continue
            z_values.extend(value for value in (action.start[2], action.end[2]) if value is not None)
            if pitch > 0.05:
                pitches.append(pitch)
        depths = [z_zero - value for value in z_values]
        if len(pitches) < 6 or not depths:
            return False
        median_pitch = statistics.median(pitches)
        pitch_tolerance = max(0.12, 0.15 * median_pitch)
        consistent = sum(abs(pitch - median_pitch) <= pitch_tolerance for pitch in pitches)
        if (
            not 0.45 <= median_pitch <= 1.80
            or consistent < math.ceil(0.7 * len(pitches))
            or max(depths) < 16.5
            or min(depths) > 1.0
            or max(depths) - min(depths) < 16.0
        ):
            return False
    return True


def main() -> bool:
    if not NC_PATH.is_file():
        return False
    program = parse(NC_PATH)
    if (
        not program.saw_g21
        or program.saw_g20
        or not program.saw_g90
        or not program.saw_m30
        or not {1, 2, 3, 4}.issubset(program.tools)
    ):
        return False
    transform = infer_transform(program)
    if transform is None:
        return False
    z_zero = infer_z_zero(program, transform)
    if z_zero is None:
        return False
    return (
        check_spotting(program, transform, z_zero)
        and check_drilling(program, transform, z_zero)
        and check_counterbores(program, transform, z_zero)
        and check_threads(program, transform, z_zero)
    )


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
