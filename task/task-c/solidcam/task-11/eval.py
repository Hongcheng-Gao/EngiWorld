from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path


TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
OUTPUT = TARGET / "task-11.nc"
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
TOKEN_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.IGNORECASE)
EXPECTED_TOOLS = [1, 2, 3, 4]
EXPECTED_SPINDLES = {1: 1800.0, 2: 2200.0, 3: 1500.0, 4: 3000.0}
EXPECTED_FEEDS = {1: (0.409, 99), 2: (0.409, 99), 3: (0.064, 99), 4: (100.0, 98)}


@dataclass
class Move:
    tool: int
    motion: int
    start_x: float | None
    start_z: float | None
    end_x: float | None
    end_z: float | None
    feed: float | None
    feed_mode: int


@dataclass
class Program:
    tools: list[int]
    spindles: dict[int, list[float]]
    moves: list[Move]
    segment_feeds: dict[int, list[tuple[float, int]]]
    spindle_on: set[int]


def strip_comments(raw: str) -> str:
    source = raw.replace("\x00", "")
    previous = None
    while previous != source:
        previous = source
        source = re.sub(r"\([^()]*\)", " ", source)
    return "\n".join(line.split(";", 1)[0] for line in source.splitlines()).upper()


def words(line: str) -> list[tuple[str, str]]:
    return [(match.group(1).upper(), match.group(2)) for match in TOKEN_RE.finditer(line)]


def g_codes(tokens: list[tuple[str, str]]) -> set[int]:
    result = set()
    for letter, raw in tokens:
        if letter != "G":
            continue
        value = float(raw)
        if abs(value - round(value)) <= 1e-9:
            result.add(int(round(value)))
    return result


def tool_number(raw: str) -> int | None:
    if not re.fullmatch(r"\+?\d+(?:\.0*)?", raw):
        return None
    digits = raw.lstrip("+").split(".", 1)[0]
    number = int(digits)
    if len(digits) >= 3 or number >= 100:
        number //= 100
    return number


def close(actual: float, expected: float, absolute: float = 1.0) -> bool:
    return abs(actual - expected) <= max(absolute, abs(expected) * 0.01)


def cluster(values: list[float], gap: float) -> list[list[float]]:
    groups: list[list[float]] = []
    for value in sorted(values):
        if not groups or value - groups[-1][-1] > gap:
            groups.append([value])
        else:
            groups[-1].append(value)
    return groups


def parse(source: str) -> Program | None:
    lines = source.splitlines()
    end_index = None
    for index, line in enumerate(lines):
        if any(letter == "M" and abs(float(raw) - 30.0) <= 1e-9 for letter, raw in words(line)):
            end_index = index
            break
    if end_index is None:
        return None
    trailing = "\n".join(lines[end_index + 1 :])
    trailing = re.sub(r"(?m)^\s*N\d+\s*$", "", trailing).replace("%", "").strip()
    if trailing:
        return None

    unit_scale = 1.0
    absolute = True
    feed_mode = 98
    motion = 0
    current_tool: int | None = None
    x: float | None = None
    z: float | None = None
    feed: float | None = None
    tools: list[int] = []
    spindles = {tool: [] for tool in EXPECTED_TOOLS}
    segment_feeds = {tool: [] for tool in EXPECTED_TOOLS}
    spindle_on: set[int] = set()
    moves: list[Move] = []

    for line in lines[: end_index + 1]:
        tokens = words(line)
        if not tokens:
            continue
        codes = g_codes(tokens)
        if 20 in codes:
            unit_scale = 25.4
        if 21 in codes:
            unit_scale = 1.0
        if 90 in codes:
            absolute = True
        if 91 in codes:
            absolute = False
        if 98 in codes:
            feed_mode = 98
        if 99 in codes:
            feed_mode = 99
        for code in (0, 1, 2, 3, 81, 82, 83):
            if code in codes:
                motion = code

        for letter, raw in tokens:
            if letter != "T":
                continue
            parsed_tool = tool_number(raw)
            if parsed_tool not in EXPECTED_TOOLS:
                return None
            current_tool = parsed_tool
            if not tools or tools[-1] != parsed_tool:
                tools.append(parsed_tool)

        if current_tool is None:
            continue
        for letter, raw in tokens:
            value = float(raw)
            if letter == "S":
                spindles[current_tool].append(value)
            elif letter == "F":
                feed = value * unit_scale
                segment_feeds[current_tool].append((feed, feed_mode))
            elif letter == "M" and int(round(value)) in (3, 4):
                spindle_on.add(current_tool)

        x_words = [float(raw) * unit_scale for letter, raw in tokens if letter == "X"]
        z_words = [float(raw) * unit_scale for letter, raw in tokens if letter == "Z"]
        if not x_words and not z_words:
            continue
        start_x, start_z = x, z
        if x_words:
            x = x_words[-1] if absolute or x is None else x + x_words[-1]
        if z_words:
            z = z_words[-1] if absolute or z is None else z + z_words[-1]
        if motion in (0, 1, 2, 3, 81, 82, 83):
            moves.append(Move(current_tool, motion, start_x, start_z, x, z, feed, feed_mode))

    return Program(tools, spindles, moves, segment_feeds, spindle_on)


def cutting(program: Program, tool: int) -> list[Move]:
    return [move for move in program.moves if move.tool == tool and move.motion in (1, 2, 3, 81, 82, 83)]


def valid_feed(program: Program, tool: int) -> bool:
    expected, expected_mode = EXPECTED_FEEDS[tool]
    feeds = [(feed, mode) for feed, mode in program.segment_feeds[tool] if feed > 0 and math.isfinite(feed)]
    tolerance = max(0.0005, abs(expected) * 0.005)
    return any(mode == expected_mode and abs(feed - expected) <= tolerance for feed, mode in feeds)


def axial_profile(moves: list[Move], minimum_moves: int) -> bool:
    positioned = [move for move in moves if move.end_x is not None and move.end_z is not None]
    if len(positioned) < minimum_moves:
        return False
    z_values = [move.end_z for move in positioned]
    x_values = [move.end_x for move in positioned]
    if max(z_values) - min(z_values) < 100.0 or min(z_values) > -100.0 or max(z_values) > 10.0:
        return False
    distinct_x = {round(value, 1) for value in x_values if 5.0 <= value <= 80.0}
    return len(distinct_x) >= 3


def valid_grooves(moves: list[Move]) -> bool:
    plunges = []
    for move in moves:
        if move.motion != 1 or None in (move.start_x, move.start_z, move.end_x, move.end_z):
            continue
        if abs(move.end_z - move.start_z) <= 0.75 and move.start_x - move.end_x >= 4.0:
            plunges.append(move)
    if len(plunges) < 4:
        return False
    groups = cluster([move.end_z for move in plunges], gap=8.0)
    if len(groups) != 2 or any(len(group) < 2 or max(group) - min(group) > 6.0 for group in groups):
        return False
    centers = [sum(group) / len(group) for group in groups]
    if not 20.0 <= centers[1] - centers[0] <= 80.0:
        return False
    return all(-160.0 <= center <= 5.0 for center in centers)


def valid_center_drill(moves: list[Move]) -> bool:
    for move in moves:
        if move.motion not in (1, 81, 82, 83) or move.end_x is None or move.end_z is None:
            continue
        start_z = move.start_z if move.start_z is not None else 0.0
        if abs(move.end_x) <= 0.25 and move.end_z <= -0.5 and start_z - move.end_z >= 1.0:
            return True
    return False


def check(path: Path) -> bool:
    if not path.is_file() or not 300 <= path.stat().st_size <= 2_000_000:
        return False
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if "\x00" in raw:
        return False
    program = parse(strip_comments(raw))
    if program is None or program.tools != EXPECTED_TOOLS or program.spindle_on != set(EXPECTED_TOOLS):
        return False
    for tool, expected in EXPECTED_SPINDLES.items():
        if not any(close(value, expected, 1.0) for value in program.spindles[tool]):
            return False
        if not valid_feed(program, tool):
            return False
    rough = cutting(program, 1)
    finish = cutting(program, 2)
    grooves = cutting(program, 3)
    center = cutting(program, 4)
    if not axial_profile(rough, 12) or not axial_profile(finish, 6):
        return False
    if not valid_grooves(grooves) or not valid_center_drill(center):
        return False
    if sum(1 for move in program.moves if move.motion in (1, 2, 3, 81, 82, 83)) < 30:
        return False
    return True


def main() -> bool:
    return check(OUTPUT)


if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
