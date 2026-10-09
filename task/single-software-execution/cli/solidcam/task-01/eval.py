from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

TARGET = Path(__import__("os").environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
EXPECTED_INIT_SHA256 = "57ca918f0e5f6f050c5da942ff9037bd3b8dad17dbf0d0a98726ac9572e4c70b"
EXPECTED_OPERATIONS = [
    "ROUGH MILL1", "ROUGH MILL2", "CONTOUR MILL1", "ROUGH MILL3", "ROUGH MILL4", "CONTOUR MILL2",
    "ROUGH MILL5", "ROUGH MILL6", "CONTOUR MILL3", "ROUGH MILL7", "ROUGH MILL8", "CONTOUR MILL4",
    "ROUGH MILL9", "ROUGH MILL10", "CONTOUR MILL5", "CENTER DRILL1", "DRILL1",
]
EXPECTED_TOOLS = {1, 2, 3, 4, 5, 15, 16}
EXPECTED_TOOL_BY_OPERATION = {
    "ROUGH MILL1": 5, "ROUGH MILL2": 2, "CONTOUR MILL1": 2, "ROUGH MILL3": 5,
    "ROUGH MILL4": 2, "CONTOUR MILL2": 2, "ROUGH MILL5": 5, "ROUGH MILL6": 3,
    "CONTOUR MILL3": 4, "ROUGH MILL7": 4, "ROUGH MILL8": 3, "CONTOUR MILL4": 4,
    "ROUGH MILL9": 5, "ROUGH MILL10": 3, "CONTOUR MILL5": 1, "CENTER DRILL1": 15, "DRILL1": 16,
}
EXPECTED_FEATURES = {
    "IRREGULAR POCKET1", "IRREGULAR POCKET2", "RECTANGULAR POCKET1",
    "IRREGULAR POCKET3", "IRREGULAR POCKET4", "HOLE GROUP1",
}
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
WORD_RE = re.compile(rf"([A-Z])({NUMBER})")
OP_RE = re.compile(
    r"^\s*(?:(?:N\d+)\s*)?\(\s*((?:ROUGH|CONTOUR)\s+MILL\d+|CENTER\s+DRILL\d+|DRILL\d+)\s*\)\s*$",
    re.IGNORECASE,
)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def strip_comments(line: str) -> tuple[str, bool]:
    out: list[str] = []
    depth = 0
    for char in line:
        if char == ";" and depth == 0:
            break
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                return "", False
            depth -= 1
        elif depth == 0:
            out.append(char)
    return "".join(out), depth == 0

def normalize_code(line: str) -> tuple[str, bool]:
    code, balanced = strip_comments(line.upper())
    if not balanced:
        return "", False
    code = code.strip().strip("%").strip()
    code = re.sub(r"^N\d+\s*", "", code)
    return code.strip(), True

def words(code: str) -> list[tuple[str, float]]:
    return [(letter, float(number)) for letter, number in WORD_RE.findall(code)]

def g_codes(code: str) -> set[int]:
    return {int(value) for letter, value in words(code) if letter == "G" and value.is_integer()}

def m_codes(code: str) -> set[int]:
    return {int(value) for letter, value in words(code) if letter == "M" and value.is_integer()}

def extract_operations(raw_lines: list[str]) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for index, line in enumerate(raw_lines):
        match = OP_RE.match(line)
        if match:
            found.append((re.sub(r"\s+", " ", match.group(1).upper()), index))
    return found

def check_operation_sections(raw_lines: list[str], markers: list[tuple[str, int]]) -> bool:
    current_tool: int | None = None
    for marker_index, (name, start) in enumerate(markers):
        end = markers[marker_index + 1][1] if marker_index + 1 < len(markers) else len(raw_lines)
        section_motion = 0
        section_cycle_points = 0
        for line in raw_lines[start:end]:
            code, balanced = normalize_code(line)
            if not balanced:
                return False
            if not code:
                continue
            parsed = words(code)
            for letter, value in parsed:
                if letter == "T":
                    current_tool = int(round(value))
            axes = {letter for letter, _value in parsed if letter in {"X", "Y", "Z"}}
            codes = g_codes(code)
            if axes and (codes & {0, 1, 2, 3} or not codes):
                section_motion += 1
            if axes and codes & {81, 82, 83}:
                section_cycle_points += 1
        if current_tool != EXPECTED_TOOL_BY_OPERATION[name]:
            return False
        minimum = 4 if name in {"CENTER DRILL1", "DRILL1"} else 8
        if section_motion + section_cycle_points < minimum:
            return False
    return True

def check_nc(path: Path) -> bool:
    if not path.is_file() or not (30000 <= path.stat().st_size <= 2_000_000):
        return False
    raw = path.read_text(encoding="utf-8", errors="strict")
    if "\x00" in raw:
        return False
    raw_lines = raw.splitlines()
    markers = extract_operations(raw_lines)
    if [name for name, _index in markers] != EXPECTED_OPERATIONS:
        return False
    executable: list[str] = []
    for line in raw_lines:
        code, balanced = normalize_code(line)
        if not balanced:
            return False
        if code and not re.fullmatch(r"O\d+", code):
            executable.append(code)
    if not executable:
        return False
    m30_positions = [i for i, code in enumerate(executable) if 30 in m_codes(code)]
    if len(m30_positions) != 1 or m30_positions[0] != len(executable) - 1:
        return False
    executable = executable[:m30_positions[0] + 1]
    all_code = "\n".join(executable)
    all_g = set().union(*(g_codes(line) for line in executable))
    all_m = set().union(*(m_codes(line) for line in executable))
    if not {21, 54, 90}.issubset(all_g) or not {3, 6, 8, 9, 30}.issubset(all_m):
        return False
    if not {40, 43, 80, 82, 83}.issubset(all_g):
        return False
    tools = {int(value) for value in re.findall(r"\bT0*(\d+)(?![\d.])", all_code)}
    length_offsets = {int(value) for value in re.findall(r"\bH0*(\d+)(?![\d.])", all_code)}
    if tools != EXPECTED_TOOLS or not EXPECTED_TOOLS.issubset(length_offsets):
        return False
    if sum(6 in m_codes(line) for line in executable) < 7 or sum(43 in g_codes(line) for line in executable) < 7:
        return False
    motion_mode: int | None = None
    cycle_mode: int | None = None
    absolute = True
    x = y = z = 0.0
    points: list[tuple[float, float, float]] = []
    explicit_arcs = 0
    feed_values: list[float] = []
    spindle_values: list[float] = []
    cycle_points = {82: 0, 83: 0}
    for code in executable:
        parsed = words(code)
        codes = g_codes(code)
        if 90 in codes: absolute = True
        if 91 in codes: absolute = False
        for candidate in (0, 1, 2, 3):
            if candidate in codes: motion_mode = candidate
        if 80 in codes: cycle_mode = None
        for candidate in (81, 82, 83):
            if candidate in codes: cycle_mode = candidate
        explicit_arcs += int(bool(codes & {2, 3}))
        for letter, value in parsed:
            if letter == "F" and value > 0: feed_values.append(value)
            if letter == "S" and value > 0: spindle_values.append(value)
        axis_values = {letter: value for letter, value in parsed if letter in {"X", "Y", "Z"}}
        if not axis_values:
            continue
        nx, ny, nz = x, y, z
        for letter, value in axis_values.items():
            if absolute:
                if letter == "X": nx = value
                if letter == "Y": ny = value
                if letter == "Z": nz = value
            else:
                if letter == "X": nx += value
                if letter == "Y": ny += value
                if letter == "Z": nz += value
        if cycle_mode in cycle_points:
            cycle_points[cycle_mode] += 1
        if motion_mode in {0, 1, 2, 3} or cycle_mode in {81, 82, 83}:
            if (nx, ny, nz) != (x, y, z):
                points.append((nx, ny, nz))
        x, y, z = nx, ny, nz
    if len(points) < 1200 or len(set(points)) < 700 or explicit_arcs < 300:
        return False
    if len(feed_values) < 20 or len(spindle_values) < 7:
        return False
    if cycle_points[82] < 5 or cycle_points[83] < 5 or min(point[2] for point in points) > -39.5:
        return False
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    if max(xs) - min(xs) < 300 or max(ys) - min(ys) < 180:
        return False
    return check_operation_sections(raw_lines, markers)

def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def check_audit(path: Path, nc_path: Path, init_path: Path) -> bool:
    if not path.is_file() or path.stat().st_size > 1_000_000:
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 2 or data.get("ok") is not True:
        return False
    if data.get("engine") != "SOLIDWORKS CAM 2025 / CAMWorks API":
        return False
    if not init_path.is_file() or sha256(init_path) != EXPECTED_INIT_SHA256:
        return False
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        return False
    input_artifact = artifacts.get("input")
    output_artifact = artifacts.get("output")
    if not isinstance(input_artifact, dict) or not isinstance(output_artifact, dict):
        return False
    if not str(input_artifact.get("path", "")).lower().endswith(r"\cam_part.sldprt"):
        return False
    if str(input_artifact.get("sha256", "")).lower() != EXPECTED_INIT_SHA256:
        return False
    if int(input_artifact.get("size", 0)) != init_path.stat().st_size:
        return False
    if not str(output_artifact.get("path", "")).lower().endswith(r"\task-01.nc"):
        return False
    if str(output_artifact.get("sha256", "")).lower() != sha256(nc_path):
        return False
    if int(output_artifact.get("size", 0)) != nc_path.stat().st_size:
        return False
    job = data.get("parsed_job")
    tools_csv = data.get("parsed_tools")
    if not isinstance(job, dict) or not isinstance(tools_csv, list) or len(tools_csv) < 3:
        return False
    if not str(job.get("model", "")).lower().endswith(r"\cam_part.sldprt"):
        return False
    if not str(job.get("output", "")).lower().endswith(r"\task-01.nc"):
        return False
    machine = data.get("machine")
    if not isinstance(machine, dict) or machine.get("binding") != "IOpenDocument":
        return False
    if machine.get("setup_count") != 1 or machine.get("operation_setup_count") != 1 or machine.get("operation_count") != 17:
        return False
    if machine.get("work_coordinate") != 54 or machine.get("origin") != [0.0, 10.0, 50.0]:
        return False
    if machine.get("controller_sha256", "").lower() != "98976cc31ac9dd35f42daab9a14b483b1a45fe40b74bb33ab6a02936954811f0":
        return False
    features = data.get("features")
    if not isinstance(features, list) or {str(item.get("name", "")).upper() for item in features if isinstance(item, dict)} != EXPECTED_FEATURES:
        return False
    operations = data.get("operations")
    if not isinstance(operations, list) or len(operations) != 17:
        return False
    if [str(item.get("name", "")).upper() for item in operations if isinstance(item, dict)] != EXPECTED_OPERATIONS:
        return False
    total_segments = 0
    for item in operations:
        if not isinstance(item, dict) or item.get("generated") is not True or int(item.get("total_segments", 0)) <= 0:
            return False
        tool = item.get("tool")
        name = str(item.get("name", "")).upper()
        if not isinstance(tool, dict) or int(tool.get("station", -1)) != EXPECTED_TOOL_BY_OPERATION[name]:
            return False
        total_segments += int(item["total_segments"])
    if total_segments < 1800 or int(machine.get("total_segments", 0)) != total_segments:
        return False
    calls = data.get("calls")
    if not isinstance(calls, list):
        return False
    call_names = [str(item.get("name", "")) for item in calls if isinstance(item, dict) and item.get("ok") is True]
    if not {"IOpenDocument", "IGetMachine", "PostProcess"}.issubset(set(call_names)):
        return False
    gop_features = {
        str(item.get("feature", "")).upper() for item in calls
        if isinstance(item, dict) and item.get("name") == "GenerateOpPlan" and item.get("ok") is True
    }
    generation_policy = data.get("generation_policy")
    if generation_policy == "regenerated":
        if gop_features != EXPECTED_FEATURES or "GenerateToolpath" not in call_names:
            return False
    elif generation_policy == "reuse_generated":
        if gop_features or any(item.get("name") == "GenerateToolpath" for item in calls if isinstance(item, dict)):
            return False
    else:
        return False
    post_calls = [item for item in calls if isinstance(item, dict) and item.get("name") == "PostProcess"]
    if len(post_calls) != 1 or post_calls[0].get("return") != 0:
        return False
    opened = [item for item in calls if isinstance(item, dict) and item.get("name") == "OpenDoc6"]
    if not opened or opened[-1].get("errors") != 0 or opened[-1].get("warnings") != 0:
        return False
    started = parse_time(data.get("started_utc"))
    finished = parse_time(data.get("finished_utc"))
    return started is not None and finished is not None and finished >= started

def main() -> bool:
    nc_path = TARGET / "task-01.nc"
    return check_nc(nc_path) and check_audit(
        TARGET / "solidcam_cli_run.json", nc_path, TARGET / "cam_part.sldprt"
    )

if __name__ == "__main__":
    try:
        result = main()
    except Exception:
        result = False
    print("True" if result else "False")
    raise SystemExit(0)
