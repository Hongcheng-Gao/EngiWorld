from __future__ import annotations

import itertools
import math
import os
import re
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
FILES = ("task-20_sideA.nc", "task-20_sideB.nc")
FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl",
    ".ahk", ".scr",
}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])\s*({NUMBER})", re.I)


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def strip_code(line: str) -> str:
    previous = None
    while previous != line:
        previous = line
        line = re.sub(r"\([^()]*\)", " ", line)
    return line.split(";", 1)[0].upper().strip()


def check_no_gui_bypass(root: Path) -> bool:
    try:
        if not root.is_dir():
            return False
        for path in root.rglob("*"):
            if path.is_file() and path.name != "eval.py" and path.suffix.lower() in FORBIDDEN_EXTENSIONS:
                return False
    except Exception:
        return False
    return True


def check_program_end(lines: list[str]) -> bool:
    endings = []
    for index, raw in enumerate(lines):
        code = strip_code(raw)
        if re.search(r"\bM0*30\b", code):
            endings.append(index)
    if len(endings) != 1:
        return False
    for raw in lines[endings[0] + 1:]:
        code = strip_code(raw)
        code = re.sub(r"^\s*N\d+\s*", "", code).strip()
        if code not in {"", "%"}:
            return False
    return True


def parse_nc(source: str) -> dict:
    lines = source.splitlines()
    if not check_program_end(lines):
        raise ValueError("program must contain one terminal M30 and no executable code after it")
    state = {
        "x": None, "y": None, "z": None, "motion": None, "absolute": None,
        "unit": None, "tool": None, "wcs": None, "cycle_z": None, "cycle_r": None,
    }
    records = []
    tools = []
    units_seen = set()
    wcs_seen = set()
    rotary_seen = set()
    for line_index, raw in enumerate(lines):
        code = strip_code(raw)
        if not code:
            continue
        words = [(letter.upper(), float(number)) for letter, number in WORD_RE.findall(code)]
        if any(letter == "M" and int(round(number)) == 30 for letter, number in words):
            break
        g_codes = [int(round(number)) for letter, number in words if letter == "G"]
        if 20 in g_codes:
            state["unit"] = 25.4
            units_seen.add("G20")
        if 21 in g_codes:
            state["unit"] = 1.0
            units_seen.add("G21")
        if 90 in g_codes:
            state["absolute"] = True
        if 91 in g_codes:
            state["absolute"] = False
        for g_code in g_codes:
            if 54 <= g_code <= 59:
                state["wcs"] = f"G{g_code}"
                wcs_seen.add(state["wcs"])
        for letter, number in words:
            if letter == "T":
                state["tool"] = int(round(number))
                tools.append(state["tool"])
            if letter in "ABC":
                rotary_seen.add(letter)
        if 80 in g_codes:
            state["motion"] = None
            state["cycle_z"] = None
            state["cycle_r"] = None
        explicit_motion = next((g for g in g_codes if g in {0, 1, 2, 3} or 81 <= g <= 89), None)
        if explicit_motion is not None:
            state["motion"] = explicit_motion
        if 28 in g_codes:
            continue
        numeric = {}
        for letter, number in words:
            if letter in "XYZIJKRQF":
                numeric[letter.lower()] = number
        if not any(axis in numeric for axis in ("x", "y", "z", "i", "j")):
            continue
        if state["unit"] is None or state["absolute"] is None:
            raise ValueError("coordinate motion precedes explicit units or coordinate mode")
        start = {axis: state[axis] for axis in "xyz"}
        for axis in "xyz":
            if axis not in numeric:
                continue
            value = numeric[axis] * state["unit"]
            if state["absolute"] or state[axis] is None:
                state[axis] = value
            else:
                state[axis] += value
        motion = state["motion"]
        if motion is None:
            continue
        if 81 <= motion <= 89:
            if "z" in numeric:
                state["cycle_z"] = state["z"]
            if "r" in numeric:
                r_value = numeric["r"] * state["unit"]
                state["cycle_r"] = r_value if state["absolute"] or start["z"] is None else start["z"] + r_value
            if explicit_motion is None and not any(axis in numeric for axis in ("x", "y")):
                continue
        elif motion in {0, 1} and not any(axis in numeric for axis in ("x", "y", "z")):
            continue
        elif motion in {2, 3} and not any(axis in numeric for axis in ("x", "y", "i", "j")):
            continue
        records.append({
            "line": line_index,
            "motion": motion,
            "start": start,
            "end": {axis: state[axis] for axis in "xyz"},
            "explicit": {key: value * state["unit"] for key, value in numeric.items() if key in "xyzijkrq"},
            "tool": state["tool"],
            "wcs": state["wcs"],
            "cycle_z": state["cycle_z"],
            "cycle_r": state["cycle_r"],
        })
    if not records or not units_seen:
        raise ValueError("no parsed NC motion")
    return {
        "records": records,
        "tools": list(dict.fromkeys(tools)),
        "units": units_seen,
        "wcs": wcs_seen,
        "rotary": rotary_seen,
    }


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def unique_points(points, tolerance=0.6):
    result = []
    for point in points:
        if not any(distance(point, existing) <= tolerance for existing in result):
            result.append(point)
    return result


def cycle_visits(parsed: dict, minimum_depth: float) -> list[tuple[float, float]]:
    visits = []
    for record in parsed["records"]:
        if not 81 <= record["motion"] <= 89:
            continue
        end = record["end"]
        if end["x"] is None or end["y"] is None or record["cycle_z"] is None:
            continue
        reference = record["cycle_r"]
        if reference is None:
            reference = record["start"]["z"]
        if reference is None or abs(reference - record["cycle_z"]) + 0.2 < minimum_depth:
            continue
        visits.append((end["x"], end["y"]))
    return unique_points(visits)


def find_four_hole_frame(points: list[tuple[float, float]]):
    target = [40.0, 40.0, 70.0, 70.0, math.hypot(40.0, 70.0), math.hypot(40.0, 70.0)]
    for quartet in itertools.combinations(points, 4):
        actual = sorted(distance(a, b) for a, b in itertools.combinations(quartet, 2))
        if all(close(a, b, 2.0) for a, b in zip(actual, target)):
            origin = quartet[0]
            others = sorted(((distance(origin, point), point) for point in quartet[1:]), key=lambda item: item[0])
            short = next((point for length, point in others if close(length, 40.0, 2.0)), None)
            long = next((point for length, point in others if close(length, 70.0, 2.0)), None)
            if short is None or long is None:
                continue
            short_vector = (short[0] - origin[0], short[1] - origin[1])
            long_vector = (long[0] - origin[0], long[1] - origin[1])
            dot = short_vector[0] * long_vector[0] + short_vector[1] * long_vector[1]
            if abs(dot) > 100.0:
                continue
            center = (sum(point[0] for point in quartet) / 4.0, sum(point[1] for point in quartet) / 4.0)
            major = (long_vector[0] / 70.0, long_vector[1] / 70.0)
            minor = (short_vector[0] / 40.0, short_vector[1] / 40.0)
            return {"points": quartet, "center": center, "major": major, "minor": minor}
    return None


def xy_cut_records(parsed: dict):
    result = []
    for record in parsed["records"]:
        if record["motion"] not in {1, 2, 3}:
            continue
        start, end = record["start"], record["end"]
        if None in (start["x"], start["y"], end["x"], end["y"]):
            continue
        if distance((start["x"], start["y"]), (end["x"], end["y"])) <= 0.01 and record["motion"] not in {2, 3}:
            continue
        result.append(record)
    return result


def project(point, frame):
    delta = (point[0] - frame["center"][0], point[1] - frame["center"][1])
    return (
        delta[0] * frame["major"][0] + delta[1] * frame["major"][1],
        delta[0] * frame["minor"][0] + delta[1] * frame["minor"][1],
    )


def has_side_a_pocket(parsed: dict, frame: dict) -> bool:
    candidates = []
    for record in xy_cut_records(parsed):
        start = project((record["start"]["x"], record["start"]["y"]), frame)
        end = project((record["end"]["x"], record["end"]["y"]), frame)
        midpoint = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
        if abs(midpoint[0]) <= 32.0 and abs(midpoint[1]) <= 20.0:
            candidates.append((record, start, end))
    if len(candidates) < 16:
        return False
    major_edges = 0
    minor_edges = 0
    for _, start, end in candidates:
        du, dv = abs(end[0] - start[0]), abs(end[1] - start[1])
        if du >= 35.0 and dv <= 2.0:
            major_edges += 1
        if dv >= 12.0 and du <= 2.0:
            minor_edges += 1
    if major_edges < 2 or minor_edges < 2:
        return False
    minimum_z = min(record["end"]["z"] for record, _, _ in candidates if record["end"]["z"] is not None)
    safe_z = max((record["end"]["z"] for record in parsed["records"] if record["motion"] == 0 and record["end"]["z"] is not None), default=None)
    return safe_z is not None and safe_z - minimum_z >= 9.0


def arc_circles(parsed: dict):
    circles = []
    for record in parsed["records"]:
        if record["motion"] not in {2, 3}:
            continue
        start, explicit = record["start"], record["explicit"]
        if start["x"] is None or start["y"] is None or "i" not in explicit or "j" not in explicit:
            continue
        radius = math.hypot(explicit["i"], explicit["j"])
        if radius <= 0.05:
            continue
        circles.append({
            "center": (start["x"] + explicit["i"], start["y"] + explicit["j"]),
            "radius": radius,
            "z": record["end"]["z"],
        })
    return circles


def match_two_counterbores(parsed: dict, pilots: list[tuple[float, float]]) -> bool:
    for first, second in itertools.combinations(pilots, 2):
        if not close(distance(first, second), 40.0, 2.0):
            continue
        circles = [circle for circle in arc_circles(parsed) if 0.4 <= circle["radius"] <= 5.2]
        matches = []
        for pilot in (first, second):
            local = [circle for circle in circles if distance(circle["center"], pilot) <= 1.2]
            if not local:
                break
            matches.append(local)
        if len(matches) != 2:
            continue
        reference_z = max((record["cycle_r"] for record in parsed["records"] if 81 <= record["motion"] <= 89 and record["cycle_r"] is not None), default=None)
        if reference_z is None:
            reference_z = max((record["end"]["z"] for record in parsed["records"] if record["motion"] == 0 and record["end"]["z"] is not None), default=None)
        if reference_z is None:
            continue
        if all(any(circle["z"] is not None and reference_z - circle["z"] >= 3.5 for circle in local) for local in matches):
            return True
    return False


def validate_side_a(parsed: dict) -> bool:
    if parsed["rotary"] or len(parsed["tools"]) < 2:
        return False
    holes = cycle_visits(parsed, 17.0)
    frame = find_four_hole_frame(holes)
    return frame is not None and has_side_a_pocket(parsed, frame)


def validate_side_b(parsed: dict) -> bool:
    if parsed["rotary"]:
        return False
    pilots = cycle_visits(parsed, 7.5)
    return len(pilots) >= 2 and match_two_counterbores(parsed, pilots)


def evaluate() -> bool:
    if not check_no_gui_bypass(TARGET):
        return False
    paths = [TARGET / name for name in FILES]
    if any(not path.is_file() or path.stat().st_size < 120 or path.stat().st_size > 5_000_000 for path in paths):
        return False
    data = [path.read_bytes() for path in paths]
    if data[0] == data[1] or any(b"\x00" in item for item in data):
        return False
    parsed = [parse_nc(item.decode("utf-8", errors="strict")) for item in data]
    return validate_side_a(parsed[0]) and validate_side_b(parsed[1])


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
