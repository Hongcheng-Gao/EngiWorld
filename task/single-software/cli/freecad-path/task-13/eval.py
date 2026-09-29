from __future__ import annotations

import math
import os
import re
from collections import defaultdict
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", "/home/user/Desktop"))
PROGRAM = TARGET / "task-13.nc"
XY_TOL = 0.15
Z_TOL = 0.10
RADIUS_TOL = 0.10
PITCH_TOL = 0.05

HOLES = {
    "H01": (-45.0, -25.0, "through"),
    "H02": (-15.0, -25.0, "through"),
    "H03": (15.0, -25.0, "through"),
    "H04": (45.0, -25.0, "through"),
    "H05": (-45.0, 25.0, "through"),
    "H06": (-15.0, 25.0, "through"),
    "H07": (15.0, 25.0, "through"),
    "H08": (45.0, 25.0, "through"),
    "H09": (-45.0, 0.0, "blind"),
    "H10": (-30.0, 0.0, "blind"),
    "H11": (-15.0, 0.0, "blind"),
    "H12": (0.0, 0.0, "blind"),
    "H13": (0.0, 25.0, "blind"),
    "H14": (15.0, 0.0, "blind"),
    "H15": (30.0, 0.0, "blind"),
    "H16": (45.0, 0.0, "blind"),
    "H17": (-30.0, 15.0, "counterbore"),
    "H18": (-10.0, 15.0, "counterbore"),
    "H19": (10.0, 15.0, "counterbore"),
    "H20": (30.0, 15.0, "counterbore"),
    "H21": (-30.0, -15.0, "threaded_pilot"),
    "H22": (-10.0, -15.0, "threaded_pilot"),
    "H23": (10.0, -15.0, "threaded_pilot"),
    "H24": (30.0, -15.0, "threaded_pilot"),
}

GROUP_IDS = {
    kind: {hole_id for hole_id, (_, _, group) in HOLES.items() if group == kind}
    for kind in {group for _, _, group in HOLES.values()}
}

EXPECTED_DEPTHS = {
    1: {hole_id: -1.0 for hole_id in HOLES},
    2: {
        **{hole_id: -19.0 for hole_id in GROUP_IDS["through"]},
        **{hole_id: -7.0 for hole_id in GROUP_IDS["blind"]},
        **{hole_id: -8.0 for hole_id in GROUP_IDS["counterbore"]},
    },
    3: {hole_id: -19.0 for hole_id in GROUP_IDS["threaded_pilot"]},
}

WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))")


def uncomment(source: str) -> str:
    lines = []
    for raw in source.upper().splitlines():
        depth = 0
        kept = []
        for character in raw:
            if character == ";" and depth == 0:
                break
            if character == "(":
                depth += 1
            elif character == ")" and depth:
                depth -= 1
            elif depth == 0:
                kept.append(character)
        line = "".join(kept).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def words(line: str) -> dict[str, list[float]]:
    parsed: dict[str, list[float]] = defaultdict(list)
    for letter, value in WORD_RE.findall(line):
        parsed[letter].append(float(value))
    return parsed


def nearest_hole(x: float | None, y: float | None) -> str | None:
    if x is None or y is None:
        return None
    matches = [
        hole_id
        for hole_id, (hx, hy, _) in HOLES.items()
        if math.hypot(x - hx, y - hy) <= XY_TOL
    ]
    return matches[0] if len(matches) == 1 else None


def parse_program(source: str) -> tuple[
    dict[int, list[str]],
    dict[int, dict[str, list[float]]],
    dict[int, list[dict[str, float | int | str]]],
    dict[int, bool],
    list[int],
    bool,
]:
    tool_lines: dict[int, list[str]] = defaultdict(list)
    plunges: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    arcs: dict[int, list[dict[str, float | int | str]]] = defaultdict(list)
    unexpected_plunge: dict[int, bool] = defaultdict(bool)
    tool_order: list[int] = []
    unsafe_rapid = False
    current_tool: int | None = None
    x = y = z = None

    for line in source.splitlines():
        parsed = words(line)
        if parsed.get("T"):
            current_tool = int(round(parsed["T"][-1]))
            if not tool_order or tool_order[-1] != current_tool:
                tool_order.append(current_tool)
        if current_tool is not None:
            tool_lines[current_tool].append(line)

        g_codes = [int(round(value)) for value in parsed.get("G", [])]
        motion = next((code for code in reversed(g_codes) if code in {0, 1, 2, 3, 81, 82, 83}), None)
        previous_x, previous_y, previous_z = x, y, z
        if parsed.get("X"):
            x = parsed["X"][-1]
        if parsed.get("Y"):
            y = parsed["Y"][-1]
        if parsed.get("Z"):
            z = parsed["Z"][-1]

        if current_tool in {1, 2, 3} and motion in {1, 81, 82, 83} and parsed.get("Z") and z is not None and z < -Z_TOL:
            hole_id = nearest_hole(x, y)
            if hole_id is None:
                unexpected_plunge[current_tool] = True
            else:
                plunges[current_tool][hole_id].append(z)

        if current_tool is not None and motion == 0 and parsed.get("Z") and z is not None and z < -Z_TOL:
            unsafe_rapid = True

        if current_tool is not None and motion in {2, 3} and previous_x is not None and previous_y is not None:
            i = parsed.get("I", [None])[-1]
            j = parsed.get("J", [None])[-1]
            if i is None or j is None:
                continue
            end_x = x if x is not None else previous_x
            end_y = y if y is not None else previous_y
            start_z = previous_z if previous_z is not None else z
            end_z = z if z is not None else previous_z
            if start_z is None or end_z is None:
                continue
            center_x = previous_x + i
            center_y = previous_y + j
            arcs[current_tool].append(
                {
                    "code": motion,
                    "start_x": previous_x,
                    "start_y": previous_y,
                    "start_z": start_z,
                    "end_x": end_x,
                    "end_y": end_y,
                    "end_z": end_z,
                    "center_x": center_x,
                    "center_y": center_y,
                    "radius": math.hypot(i, j),
                    "end_radius": math.hypot(end_x - center_x, end_y - center_y),
                    "hole_id": nearest_hole(center_x, center_y) or "",
                }
            )

    return tool_lines, plunges, arcs, unexpected_plunge, tool_order, unsafe_rapid


def has_setting(lines: list[str], letter: str, value: int) -> bool:
    pattern = re.compile(rf"\b{letter}\s*0*{value}(?:\.0+)?\b")
    return any(pattern.search(line) for line in lines)


def has_word_value(lines: list[str], letter: str, value: float) -> bool:
    return any(
        any(abs(actual - value) <= 1e-6 for actual in words(line).get(letter, []))
        for line in lines
    )


def has_tool_change(lines: list[str], tool: int) -> bool:
    return any(
        any(abs(actual - tool) <= 1e-6 for actual in words(line).get("T", []))
        and any(abs(actual - 6.0) <= 1e-6 for actual in words(line).get("M", []))
        for line in lines
    )


def check_plunges(
    plunges: dict[int, dict[str, list[float]]],
    unexpected: dict[int, bool],
) -> bool:
    for tool, expected in EXPECTED_DEPTHS.items():
        if unexpected.get(tool, False) or set(plunges.get(tool, {})) != set(expected):
            return False
        for hole_id, target_z in expected.items():
            actual = min(plunges[tool][hole_id])
            if abs(actual - target_z) > Z_TOL:
                return False
    return True


def arc_sweep(arc: dict[str, float | int | str]) -> float:
    start = math.atan2(
        float(arc["start_y"]) - float(arc["center_y"]),
        float(arc["start_x"]) - float(arc["center_x"]),
    )
    end = math.atan2(
        float(arc["end_y"]) - float(arc["center_y"]),
        float(arc["end_x"]) - float(arc["center_x"]),
    )
    if int(arc["code"]) == 3:
        sweep = (end - start) % (2.0 * math.pi)
    else:
        sweep = (start - end) % (2.0 * math.pi)
    return 2.0 * math.pi if sweep < 1e-6 else sweep


def descending_arcs(arcs: list[dict[str, float | int | str]]) -> list[dict[str, float | int | str]]:
    return [arc for arc in arcs if float(arc["end_z"]) < float(arc["start_z"]) - 1e-5]


def check_counterbores(arcs: dict[int, list[dict[str, float | int | str]]]) -> bool:
    expected = GROUP_IDS["counterbore"]
    descending = descending_arcs(arcs.get(4, []))
    if not descending or {str(arc["hole_id"]) for arc in descending} != expected:
        return False
    grouped: dict[str, list[dict[str, float | int | str]]] = defaultdict(list)
    for arc in descending:
        hole_id = str(arc["hole_id"])
        if hole_id not in expected or abs(float(arc["radius"]) - 3.0) > RADIUS_TOL:
            return False
        if abs(float(arc["end_radius"]) - 3.0) > RADIUS_TOL:
            return False
        grouped[hole_id].append(arc)
    for hole_id in expected:
        path = grouped[hole_id]
        if abs(float(path[0]["start_z"])) > Z_TOL:
            return False
        for previous, current in zip(path, path[1:]):
            if abs(float(previous["end_z"]) - float(current["start_z"])) > Z_TOL:
                return False
        if abs(float(path[-1]["end_z"]) + 3.0) > Z_TOL:
            return False
        if sum(arc_sweep(arc) for arc in path) < 2.0 * math.pi - 0.05:
            return False
    return True


def check_threads(arcs: dict[int, list[dict[str, float | int | str]]]) -> bool:
    expected = GROUP_IDS["threaded_pilot"]
    descending = descending_arcs(arcs.get(5, []))
    if not descending or {str(arc["hole_id"]) for arc in descending} != expected:
        return False
    grouped: dict[str, list[dict[str, float | int | str]]] = defaultdict(list)
    for arc in descending:
        hole_id = str(arc["hole_id"])
        if hole_id not in expected or int(arc["code"]) != 3:
            return False
        if abs(float(arc["radius"]) - 1.5) > RADIUS_TOL:
            return False
        if abs(float(arc["end_radius"]) - 1.5) > RADIUS_TOL:
            return False
        sweep = arc_sweep(arc)
        pitch = (float(arc["start_z"]) - float(arc["end_z"])) * 2.0 * math.pi / sweep
        if abs(pitch - 1.25) > PITCH_TOL:
            return False
        grouped[hole_id].append(arc)

    for hole_id in expected:
        path = grouped[hole_id]
        if abs(float(path[0]["start_z"])) > Z_TOL:
            return False
        for previous, current in zip(path, path[1:]):
            if abs(float(previous["end_z"]) - float(current["start_z"])) > Z_TOL:
                return False
        if abs(float(path[-1]["end_z"]) + 15.0) > Z_TOL:
            return False
        if abs(sum(arc_sweep(arc) for arc in path) - 24.0 * math.pi) > 0.10:
            return False
    return True


def main() -> bool:
    if not PROGRAM.exists() or PROGRAM.stat().st_size < 1000:
        return False
    source = uncomment(PROGRAM.read_text(encoding="utf-8", errors="ignore"))
    source_lines = source.splitlines()
    first_tool = next((index for index, line in enumerate(source_lines) if words(line).get("T")), None)
    if first_tool is None:
        return False
    header = source_lines[:first_tool]
    if not all(has_word_value(header, "G", code) for code in (21.0, 90.0, 91.1, 54.0)):
        return False

    tool_lines, plunges, arcs, unexpected, tool_order, unsafe_rapid = parse_program(source)
    if unsafe_rapid or tool_order != [1, 2, 3, 4, 5] or set(tool_lines) != {1, 2, 3, 4, 5}:
        return False
    for tool in range(1, 6):
        if not has_tool_change(tool_lines[tool], tool):
            return False
        if not has_setting(tool_lines[tool], "S", 7000) or not has_setting(tool_lines[tool], "F", 500):
            return False
    if not has_word_value(tool_lines[5], "M", 30.0):
        return False

    return check_plunges(plunges, unexpected) and check_counterbores(arcs) and check_threads(arcs)


if __name__ == "__main__":
    try:
        ok = main()
    except Exception:
        ok = False
    print("True" if ok else "False")
