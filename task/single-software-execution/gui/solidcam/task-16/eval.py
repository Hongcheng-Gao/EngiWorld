from __future__ import annotations

import math
import os
import re
from collections import defaultdict
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
TARGET_NAME = "task-16.nc"

WORD_RE = re.compile(r"([A-Z])\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", re.IGNORECASE)
COMMENT_RE = re.compile(r"\([^)]*\)")


def close(a: float, b: float, tolerance: float) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def strip_comments(line: str) -> str:
    return COMMENT_RE.sub(" ", line).split(";", 1)[0].upper()


def parse_nc(source: str):
    records = []
    tools = []
    forbidden_axes = set()
    invalid_b = False
    state = {
        "x": None,
        "z": None,
        "motion": None,
        "tool": None,
        "unit": 1.0,
        "absolute": True,
    }

    for line_number, raw in enumerate(source.splitlines(), start=1):
        code = strip_comments(raw)
        words = [(letter.upper(), float(value)) for letter, value in WORD_RE.findall(code)]
        if not words:
            continue

        by_letter = defaultdict(list)
        for letter, value in words:
            by_letter[letter].append(value)

        g_codes = {int(round(value)) for value in by_letter.get("G", []) if close(value, round(value), 1e-6)}
        if 20 in g_codes:
            state["unit"] = 25.4
        if 21 in g_codes:
            state["unit"] = 1.0
        if 90 in g_codes:
            state["absolute"] = True
        if 91 in g_codes:
            state["absolute"] = False
        if 80 in g_codes:
            state["motion"] = None
        explicit_motion = next((g for g in (0, 1, 2, 3) if g in g_codes), None)
        if explicit_motion is not None:
            state["motion"] = explicit_motion

        if "T" in by_letter:
            tool = int(round(by_letter["T"][-1]))
            if state["tool"] != tool:
                tools.append(tool)
            state["tool"] = tool

        forbidden_axes.update(letter for letter in ("Y", "A", "C", "U", "V", "W") if letter in by_letter)

        if "B" in by_letter:
            b_value = by_letter["B"][-1]
            has_motion_word = bool(g_codes.intersection({0, 1, 2, 3}))
            has_path_word = any(letter in by_letter for letter in ("X", "Y", "Z", "A", "C", "U", "V", "W", "I", "J", "K", "R", "F"))
            if len(by_letter["B"]) != 1 or not (close(b_value, 0.0, 1e-6) or close(b_value, 90.0, 1e-6)) or has_motion_word or has_path_word:
                invalid_b = True

        explicit = {}
        for axis in ("X", "Z"):
            if axis not in by_letter:
                continue
            value_mm = by_letter[axis][-1] * state["unit"]
            key = axis.lower()
            if state["absolute"] or state[key] is None:
                explicit[key] = value_mm
            else:
                explicit[key] = state[key] + value_mm

        if state["motion"] is None or not explicit:
            for key, value in explicit.items():
                state[key] = value
            continue

        start = {"x": state["x"], "z": state["z"]}
        for key, value in explicit.items():
            state[key] = value
        end = {"x": state["x"], "z": state["z"]}
        changed = any(
            start[axis] is None or end[axis] is None or not close(start[axis], end[axis], 1e-7)
            for axis in explicit
        )
        if changed:
            records.append(
                {
                    "line": line_number,
                    "motion": state["motion"],
                    "start": start,
                    "end": end,
                    "tool": state["tool"],
                }
            )

    return records, tools, forbidden_axes, invalid_b


def is_cut(record) -> bool:
    if record["motion"] not in {1, 2, 3}:
        return False
    start, end = record["start"], record["end"]
    return None not in (start["x"], start["z"], end["x"], end["z"])


def z_span(records) -> float:
    values = [point["z"] for record in records for point in (record["start"], record["end"]) if point["z"] is not None]
    return max(values) - min(values) if values else 0.0


def longitudinal(record, minimum: float) -> bool:
    start, end = record["start"], record["end"]
    return (
        None not in (start["x"], start["z"], end["x"], end["z"])
        and abs(end["x"] - start["x"]) <= 1.25
        and abs(end["z"] - start["z"]) >= minimum
    )


def find_finish_profile(cuts_by_tool):
    candidates = []
    for tool, records in cuts_by_tool.items():
        first_plateaus = []
        second_plateaus = []
        for record in records:
            if not longitudinal(record, 20.0):
                continue
            start, end = record["start"], record["end"]
            diameter = (start["x"] + end["x"]) / 2.0
            near, far = sorted((abs(start["z"]), abs(end["z"])))
            if 26.0 <= diameter <= 30.5 and near <= 5.0 and 50.0 <= far <= 64.0:
                first_plateaus.append(record)
            if 30.0 <= diameter <= 34.5 and 54.0 <= near <= 64.0 and 86.0 <= far <= 98.0:
                second_plateaus.append(record)
        if first_plateaus and second_plateaus:
            first = first_plateaus[0]
            face_z = min((first["start"]["z"], first["end"]["z"]), key=abs)
            far_z = max((first["start"]["z"], first["end"]["z"]), key=lambda value: abs(value - face_z))
            orientation = 1.0 if far_z > face_z else -1.0
            candidates.append((tool, face_z, orientation))
    return candidates


def has_rough_profile(cuts_by_tool, finish_tool: int) -> bool:
    for tool, records in cuts_by_tool.items():
        if tool == finish_tool or len(records) < 8 or z_span(records) < 80.0:
            continue
        long_moves = [record for record in records if longitudinal(record, 25.0)]
        diameters = {
            round((record["start"]["x"] + record["end"]["x"]) / 2.0, 1)
            for record in long_moves
        }
        touches_face = any(abs(point["z"]) <= 3.0 for record in records for point in (record["start"], record["end"]))
        reaches_shoulder = any(abs(point["z"]) >= 86.0 for record in records for point in (record["start"], record["end"]))
        if len(long_moves) >= 2 and len(diameters) >= 2 and touches_face and reaches_shoulder:
            return True
    return False


def groove_tools(cuts_by_tool, face_z: float, orientation: float, excluded_tools: set[int]):
    tools = set()
    low_points = []
    radial_count = 0
    for tool, records in cuts_by_tool.items():
        if tool in excluded_tools:
            continue
        for record in records:
            start, end = record["start"], record["end"]
            distance = orientation * (end["z"] - face_z)
            if 39.0 <= distance <= 51.0 and 15.5 <= end["x"] <= 20.5:
                low_points.append(distance)
                tools.add(tool)
                if abs(end["z"] - start["z"]) <= 0.5 and start["x"] - end["x"] >= 6.0:
                    radial_count += 1
    if not low_points or max(low_points) - min(low_points) < 3.5 or radial_count < 2:
        return set()
    return tools


def has_center_drill(cuts_by_tool, face_z: float, orientation: float, excluded_tools: set[int]) -> bool:
    found = False
    for tool, records in cuts_by_tool.items():
        if tool in excluded_tools:
            continue
        for record in records:
            end = record["end"]
            if abs(end["x"]) > 0.5:
                continue
            depth = orientation * (end["z"] - face_z)
            if depth > 12.0:
                return False
            if 2.0 <= depth <= 8.0:
                found = True
    return found


def validate_file(path: Path) -> bool:
    try:
        if not path.is_file() or not 200 <= path.stat().st_size <= 2_000_000:
            return False
        source = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return False

    code = "\n".join(strip_comments(line) for line in source.splitlines())
    if not re.search(r"(?<![A-Z0-9])M0*30(?![0-9])", code):
        return False

    records, tools, forbidden_axes, invalid_b = parse_nc(source)
    if forbidden_axes or invalid_b or len(set(tools)) < 4:
        return False

    cuts = [record for record in records if is_cut(record)]
    if len(cuts) < 20:
        return False
    cuts_by_tool = defaultdict(list)
    for record in cuts:
        if record["tool"] is not None:
            cuts_by_tool[record["tool"]].append(record)

    for finish_tool, face_z, orientation in find_finish_profile(cuts_by_tool):
        if not has_rough_profile(cuts_by_tool, finish_tool):
            continue
        groove = groove_tools(cuts_by_tool, face_z, orientation, {finish_tool})
        if not groove:
            continue
        if has_center_drill(cuts_by_tool, face_z, orientation, {finish_tool, *groove}):
            return True
    return False


def evaluate() -> bool:
    return validate_file(TARGET / TARGET_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
