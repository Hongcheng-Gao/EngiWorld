from __future__ import annotations

import os
import re
from pathlib import Path


DEFAULT_TARGET = r"C:\Users\User\Desktop"
TARGET = Path(os.environ.get("EVAL_TARGET_DIR", os.environ.get("OUTPUT_ROOT", DEFAULT_TARGET)))
OUTPUT_NAME = "task-2.nc"

FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".vbs", ".js", ".mjs", ".ts", ".rb", ".lua", ".tcl",
    ".ahk", ".scr",
}


def check_no_script_bypass(root: Path) -> bool:
    try:
        if not root.is_dir():
            return False
        return not any(
            path.is_file()
            and path.name.lower() != "eval.py"
            and path.suffix.lower() in FORBIDDEN_EXTENSIONS
            for path in root.rglob("*")
        )
    except Exception:
        return False


def comments(source: str) -> list[str]:
    found = re.findall(r"\(([^()]*)\)", source)
    found.extend(match for match in re.findall(r";([^\r\n]*)", source) if match.strip())
    return [item.strip().upper() for item in found if item.strip()]


def code_only(line: str) -> str:
    return re.sub(r"\([^)]*\)", " ", line).split(";", 1)[0].upper()


def close(a: float, b: float, tolerance: float = 0.5) -> bool:
    return abs(float(a) - float(b)) <= tolerance


def parse_nc(source: str):
    state = {
        "x": None,
        "y": None,
        "z": None,
        "motion": None,
        "absolute": True,
        "scale": 1.0,
        "wcs": None,
        "tool": None,
    }
    records = []
    tools = []
    g_seen = set()
    m_seen = set()
    axes_seen = set()
    positive_feeds = 0

    for line_number, raw in enumerate(source.splitlines(), 1):
        line = code_only(raw)
        if not line.strip():
            continue
        g_codes = [int(token) for token in re.findall(r"\bG0*(\d+)\b", line)]
        m_codes = [int(token) for token in re.findall(r"\bM0*(\d+)\b", line)]
        g_seen.update(g_codes)
        m_seen.update(m_codes)
        if 20 in g_codes:
            state["scale"] = 25.4
        if 21 in g_codes:
            state["scale"] = 1.0
        if 90 in g_codes:
            state["absolute"] = True
        if 91 in g_codes:
            state["absolute"] = False
        for g_code in g_codes:
            if 54 <= g_code <= 59:
                state["wcs"] = f"G{g_code}"
        motion = next((code for code in g_codes if code in {0, 1, 2, 3}), None)
        if motion is not None:
            state["motion"] = motion

        tool_match = re.search(r"\bT0*(\d+)\b", line)
        if tool_match:
            state["tool"] = int(tool_match.group(1))
            tools.append(state["tool"])
        feed_match = re.search(r"\bF([+]?(?:\d+(?:\.\d*)?|\.\d+))", line)
        if feed_match and float(feed_match.group(1)) > 0:
            positive_feeds += 1

        explicit = {}
        for axis in "XYZABCIJK":
            match = re.search(rf"\b{axis}([+-]?(?:\d+(?:\.\d*)?|\.\d+))", line)
            if match:
                explicit[axis.lower()] = float(match.group(1)) * state["scale"]
                axes_seen.add(axis)
        if state["motion"] is None or not any(axis in explicit for axis in "xyz"):
            continue

        start = {axis: state[axis] for axis in "xyz"}
        for axis in "xyz":
            if axis not in explicit:
                continue
            if state["absolute"] or state[axis] is None:
                state[axis] = explicit[axis]
            else:
                state[axis] += explicit[axis]
        records.append(
            {
                "line": line_number,
                "motion": state["motion"],
                "start": start,
                "end": {axis: state[axis] for axis in "xyz"},
                "tool": state["tool"],
                "wcs": state["wcs"],
                "machine_return": 28 in g_codes or 53 in g_codes,
            }
        )
    return records, tools, g_seen, m_seen, axes_seen, positive_feeds


def xy_length(record: dict) -> float:
    start, end = record["start"], record["end"]
    if None in (start["x"], start["y"], end["x"], end["y"]):
        return 0.0
    return ((end["x"] - start["x"]) ** 2 + (end["y"] - start["y"]) ** 2) ** 0.5


def cutting_records(records: list[dict]) -> list[dict]:
    return [
        record
        for record in records
        if record["motion"] in {1, 2, 3}
        and not record["machine_return"]
        and xy_length(record) > 0.01
        and record["end"]["z"] is not None
        and record["end"]["z"] < -0.05
    ]


def interval_coverage(intervals: list[tuple[float, float]], low: float, high: float) -> float:
    clipped = []
    for start, end in intervals:
        left, right = max(min(start, end), low), min(max(start, end), high)
        if right > left:
            clipped.append((left, right))
    if not clipped:
        return 0.0
    clipped.sort()
    merged = [list(clipped[0])]
    for left, right in clipped[1:]:
        if left <= merged[-1][1] + 0.75:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    return sum(right - left for left, right in merged)


def rectangular_outer_contour(records: list[dict]) -> bool:
    cuts = cutting_records(records)
    if not cuts:
        return False
    deepest = min(record["end"]["z"] for record in cuts)
    if deepest > -11.25:
        return False
    final = [record for record in cuts if close(record["end"]["z"], deepest, 0.35)]

    horizontals, verticals = [], []
    for record in final:
        start, end = record["start"], record["end"]
        if None in (start["x"], start["y"], end["x"], end["y"]):
            continue
        dx, dy = end["x"] - start["x"], end["y"] - start["y"]
        if abs(dy) <= 0.35 and abs(dx) >= 35.0:
            horizontals.append(((start["y"] + end["y"]) / 2.0, start["x"], end["x"]))
        if abs(dx) <= 0.35 and abs(dy) >= 25.0:
            verticals.append(((start["x"] + end["x"]) / 2.0, start["y"], end["y"]))
    if len(horizontals) < 2 or len(verticals) < 2:
        return False

    x_levels = sorted({round(item[0], 2) for item in verticals})
    y_levels = sorted({round(item[0], 2) for item in horizontals})
    left, right = x_levels[0], x_levels[-1]
    bottom, top = y_levels[0], y_levels[-1]
    width, height = right - left, top - bottom
    if not (118.0 <= width <= 145.0 and 78.0 <= height <= 105.0):
        return False
    if abs((left + right) / 2.0) > 1.5 or abs((bottom + top) / 2.0) > 1.5:
        return False

    for target_y in (bottom, top):
        intervals = [(x1, x2) for y, x1, x2 in horizontals if close(y, target_y, 0.5)]
        if interval_coverage(intervals, left, right) < 0.90 * width:
            return False
    for target_x in (left, right):
        intervals = [(y1, y2) for x, y1, y2 in verticals if close(x, target_x, 0.5)]
        if interval_coverage(intervals, bottom, top) < 0.90 * height:
            return False
    return True


def validate(path: Path) -> bool:
    if not path.is_file() or not 100 <= path.stat().st_size <= 1_000_000:
        return False
    source = path.read_text(encoding="utf-8", errors="ignore")
    if "\x00" in source or sum(char.isprintable() or char in "\r\n\t" for char in source) < 0.95 * len(source):
        return False
    upper_code = "\n".join(code_only(line) for line in source.splitlines())
    note = comments(source)
    if not any("CONTOUR" in item or "PROFILE" in item for item in note):
        return False
    if len(note) < 2 or not any(re.search(r"(?:FLAT|END\s*MILL|ENDMILL|\b\d+(?:\.\d+)?\s*MM\b)", item) for item in note):
        return False
    if not re.search(r"(?m)^\s*O\d+\b", upper_code):
        return False

    records, tools, g_seen, m_seen, axes_seen, positive_feeds = parse_nc(source)
    unique_tools = list(dict.fromkeys(tools))
    if len(unique_tools) != 1 or len(records) < 7 or positive_feeds < 1:
        return False
    if not ({20, 21} & g_seen) or 90 not in g_seen or not any(54 <= code <= 59 for code in g_seen):
        return False
    if 6 not in m_seen or 3 not in m_seen or 30 not in m_seen:
        return False
    if not ({0, 1} <= {record["motion"] for record in records}):
        return False
    if axes_seen & {"A", "B", "C"}:
        return False
    if re.search(r"\b(?:PRINT|PYTHON|POWERSHELL|CMD\.EXE|EVAL\.PY)\b", upper_code):
        return False
    return rectangular_outer_contour(records)


def evaluate() -> bool:
    return check_no_script_bypass(TARGET) and validate(TARGET / OUTPUT_NAME)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
