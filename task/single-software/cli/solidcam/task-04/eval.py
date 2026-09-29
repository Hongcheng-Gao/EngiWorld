from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_TARGET = Path(os.environ.get("EVAL_TARGET_DIR", r"C:\Users\User\Desktop"))
NC_NAME = "task-04.nc"

FORMAL_INPUT_SHA256 = {
    "hole_table_plate.step": "3094AF53D864C0031251B738D51201551E439A32CD556E1AA09B345F3978C39D",
    "hole_table.csv": "25B7FDFF9FC8522F0882D77A0930242123FD9FEC2774D8EEE0969F530F725B5E",
}

XY_TOL_MM = 0.35
DEPTH_TOL_MM = 0.30
THROUGH_TIP_COMP_MAX_MM = 0.65
SAFE_CLEARANCE_MM = 1.0
WORD_RE = re.compile(r"([A-Z])([-+]?(?:\d+(?:\.\d*)?|\.\d+))")
RUN_ID_RE = re.compile(r"[A-Za-z0-9._:-]{8,128}")


@dataclass(frozen=True)
class Hole:
    x: float
    y: float
    diameter: float
    depth: float
    kind: str


HOLES = (
    Hole(-45.0, -10.0, 5.0, 13.0, "through"),
    Hole(-35.0, 10.0, 5.0, 13.0, "through"),
    Hole(-25.0, -10.0, 5.0, 13.0, "through"),
    Hole(-15.0, 10.0, 5.0, 13.0, "through"),
    Hole(-5.0, -10.0, 5.0, 13.0, "through"),
    Hole(5.0, 10.0, 5.0, 13.0, "through"),
    Hole(15.0, -10.0, 6.0, 6.0, "blind"),
    Hole(25.0, 10.0, 6.0, 7.0, "blind"),
    Hole(35.0, -10.0, 6.0, 8.0, "blind"),
    Hole(45.0, 10.0, 6.0, 9.0, "blind"),
)


class EvaluationError(ValueError):
    pass


@dataclass
class Record:
    line: int
    motion: int
    start: tuple[float, float, float]
    end: tuple[float, float, float]
    tool: int | None
    spindle_on: bool
    spindle: float | None
    feed: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None


@dataclass
class DrillEvent:
    line: int
    x: float
    y: float
    bottom_z: float
    approach_z: float | None
    retract_z: float | None
    tool: int | None
    spindle_on: bool
    spindle: float | None
    feed: float | None
    wcs: str | None
    length_comp: bool
    h_offset: int | None
    method: str


@dataclass
class Program:
    records: list[Record]
    cycle_events: list[DrillEvent]
    saw_m30: bool


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def strip_comments(raw: str, line_number: int) -> str:
    output: list[str] = []
    depth = 0
    for char in raw:
        if char == ";" and depth == 0:
            break
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                raise EvaluationError(f"unmatched comment close on line {line_number}")
            depth -= 1
        elif depth == 0:
            output.append(char)
    if depth:
        raise EvaluationError(f"unterminated comment on line {line_number}")
    return "".join(output).upper().strip()


def parse_words(code: str, line_number: int) -> list[tuple[str, float]]:
    if code == "%":
        return []
    if code.startswith("/"):
        code = code[1:].lstrip()
    matches = list(WORD_RE.finditer(code))
    residue = WORD_RE.sub(" ", code)
    if residue.strip():
        raise EvaluationError(f"unknown executable text on line {line_number}: {residue.strip()!r}")
    return [(match.group(1), float(match.group(2))) for match in matches]


def exact_int(value: float, label: str, line_number: int) -> int:
    rounded = round(value)
    if not close(value, rounded, 1e-8):
        raise EvaluationError(f"fractional {label} code on line {line_number}")
    return int(rounded)


def g_is(value: float, expected: float) -> bool:
    return close(value, expected, 1e-7)


def parse_program(source: str) -> Program:
    units: float | None = None
    distance_mode: int | None = None
    motion: int | None = None
    active_cycle: int | None = None
    cycle_z: float | None = None
    cycle_r: float | None = None
    cycle_q: float | None = None
    retract_mode = 98
    selected_tool: int | None = None
    active_tool: int | None = None
    spindle_on = False
    spindle: float | None = None
    feed: float | None = None
    wcs: str | None = None
    length_comp = False
    h_offset: int | None = None
    x = y = z = 0.0
    terminated = False
    saw_m30 = False
    records: list[Record] = []
    cycle_events: list[DrillEvent] = []

    allowed_g = {
        0.0, 1.0, 2.0, 3.0, 17.0, 20.0, 21.0, 28.0, 40.0, 43.0,
        49.0, 53.0, 54.0, 54.1, 55.0, 56.0, 57.0, 58.0, 59.0,
        80.0, 81.0, 82.0, 83.0, 90.0, 91.0, 94.0, 98.0, 99.0,
    }
    allowed_m = {0, 1, 2, 3, 4, 5, 6, 8, 9, 30}

    for line_number, raw in enumerate(source.splitlines(), 1):
        code = strip_comments(raw, line_number)
        if not code or code == "%":
            continue
        words = parse_words(code, line_number)
        if not words:
            continue
        if terminated:
            raise EvaluationError(f"executable code after M30 on line {line_number}")

        by_letter: dict[str, list[float]] = {}
        for letter, value in words:
            by_letter.setdefault(letter, []).append(value)
        for letter in by_letter:
            if letter not in "NGMTSFXYZIJRQHDPLO":
                raise EvaluationError(f"unsupported word {letter} on line {line_number}")
        for letter in "XYZIJRQHDFSTP":
            if len(by_letter.get(letter, [])) > 1:
                raise EvaluationError(f"duplicate {letter} word on line {line_number}")

        g_codes = by_letter.get("G", [])
        m_codes = [exact_int(v, "M", line_number) for v in by_letter.get("M", [])]
        for g in g_codes:
            if not any(g_is(g, allowed) for allowed in allowed_g):
                raise EvaluationError(f"unsupported G code G{g:g} on line {line_number}")
        for m in m_codes:
            if m not in allowed_m:
                raise EvaluationError(f"unsupported M code M{m} on line {line_number}")

        axis_present = any(letter in by_letter for letter in "XYZ")
        block_motion = any(any(g_is(g, candidate) for candidate in (0, 1, 2, 3, 81, 82, 83)) for g in g_codes)
        if 30 in m_codes:
            if axis_present or block_motion:
                raise EvaluationError(f"motion or cycle in M30 block on line {line_number}")
            saw_m30 = True
            terminated = True
            continue

        for g in g_codes:
            if g_is(g, 20):
                units = 25.4
            elif g_is(g, 21):
                units = 1.0
            elif g_is(g, 90):
                distance_mode = 90
            elif g_is(g, 91):
                distance_mode = 91
            elif any(g_is(g, candidate) for candidate in (0, 1, 2, 3)):
                motion = int(round(g))
                active_cycle = None
            elif g_is(g, 80):
                active_cycle = None
            elif any(g_is(g, candidate) for candidate in (81, 82, 83)):
                active_cycle = int(round(g))
            elif g_is(g, 98):
                retract_mode = 98
            elif g_is(g, 99):
                retract_mode = 99
            elif g_is(g, 43):
                length_comp = True
            elif g_is(g, 49):
                length_comp = False
                h_offset = None
            elif any(g_is(g, candidate) for candidate in (54, 55, 56, 57, 58, 59)):
                wcs = f"G{int(round(g))}"
            elif g_is(g, 54.1):
                p_value = by_letter.get("P", [None])[-1]
                if p_value is None or exact_int(p_value, "P", line_number) <= 0:
                    raise EvaluationError(f"G54.1 requires positive P on line {line_number}")
                wcs = f"G54.1 P{exact_int(p_value, 'P', line_number)}"

        if "T" in by_letter:
            selected_tool = exact_int(by_letter["T"][-1], "T", line_number)
            if selected_tool <= 0:
                raise EvaluationError(f"tool number must be positive on line {line_number}")
        if 6 in m_codes:
            if selected_tool is None:
                raise EvaluationError(f"M6 without selected tool on line {line_number}")
            active_tool = selected_tool
        if "S" in by_letter:
            spindle = by_letter["S"][-1]
            if spindle <= 0:
                raise EvaluationError(f"spindle speed must be positive on line {line_number}")
        if 3 in m_codes or 4 in m_codes:
            spindle_on = True
        if 5 in m_codes:
            spindle_on = False
        if "F" in by_letter:
            if units is None:
                raise EvaluationError(f"feed appears before G20/G21 on line {line_number}")
            feed = by_letter["F"][-1] * units
            if feed <= 0:
                raise EvaluationError(f"feed must be positive on line {line_number}")
        if "H" in by_letter:
            h_offset = exact_int(by_letter["H"][-1], "H", line_number)
            if h_offset <= 0:
                raise EvaluationError(f"H offset must be positive on line {line_number}")

        if axis_present and (units is None or distance_mode is None):
            raise EvaluationError(f"axis motion before explicit units and distance mode on line {line_number}")

        initial = (x, y, z)
        scale = units or 1.0
        machine_coordinate_block = any(g_is(g, 28) or g_is(g, 53) for g in g_codes)

        if machine_coordinate_block and active_cycle is not None:
            raise EvaluationError(f"machine-coordinate motion cannot launch a drilling cycle on line {line_number}")
        if machine_coordinate_block and axis_present:
            # G28/G53 do not establish a point in the active work coordinate system.
            # They may appear in a native post's safe-home sequence, but cannot
            # supply approach, hole, depth, or retract evidence.
            continue

        if active_cycle is not None:
            if distance_mode != 90:
                raise EvaluationError(f"canned cycles require G90 in this evaluator on line {line_number}")
            if "Z" in by_letter:
                cycle_z = by_letter["Z"][-1] * scale
            if "R" in by_letter:
                cycle_r = by_letter["R"][-1] * scale
            if "Q" in by_letter:
                cycle_q = by_letter["Q"][-1] * scale
            if "X" in by_letter:
                x = by_letter["X"][-1] * scale
            if "Y" in by_letter:
                y = by_letter["Y"][-1] * scale
            launches_cycle = any(g_is(g, candidate) for g in g_codes for candidate in (81, 82, 83)) or "X" in by_letter or "Y" in by_letter
            if launches_cycle:
                if cycle_z is None or cycle_r is None:
                    raise EvaluationError(f"incomplete canned cycle on line {line_number}")
                if active_cycle == 83 and (cycle_q is None or cycle_q <= 0):
                    raise EvaluationError(f"G83 requires positive Q on line {line_number}")
                retract_z = max(initial[2], cycle_r) if retract_mode == 98 else cycle_r
                cycle_events.append(
                    DrillEvent(
                        line_number, x, y, cycle_z, initial[2], retract_z,
                        active_tool, spindle_on, spindle, feed, wcs,
                        length_comp, h_offset, f"G{active_cycle}",
                    )
                )
                z = retract_z
            continue

        if axis_present:
            if motion is None:
                raise EvaluationError(f"axis words before an explicit motion mode on line {line_number}")
            values: dict[str, float] = {}
            for axis in "XYZ":
                if axis in by_letter:
                    values[axis] = by_letter[axis][-1] * scale
            if distance_mode == 90:
                x = values.get("X", x)
                y = values.get("Y", y)
                z = values.get("Z", z)
            else:
                x += values.get("X", 0.0)
                y += values.get("Y", 0.0)
                z += values.get("Z", 0.0)
            records.append(
                Record(
                    line_number, motion, initial, (x, y, z), active_tool,
                    spindle_on, spindle, feed, wcs, length_comp, h_offset,
                )
            )

    if not saw_m30:
        raise EvaluationError("M30 is required")
    return Program(records, cycle_events, saw_m30)


def near_hole(x: float, y: float, hole: Hole) -> bool:
    return math.hypot(x - hole.x, y - hole.y) <= XY_TOL_MM


def pure_vertical(record: Record) -> bool:
    return (
        math.hypot(record.end[0] - record.start[0], record.end[1] - record.start[1]) <= 0.05
    )


def explicit_events(program: Program) -> list[DrillEvent]:
    events: list[DrillEvent] = []
    approach_z: float | None = None
    plunge: Record | None = None
    plunge_approach_z: float | None = None

    def emit(retract_z: float | None) -> None:
        nonlocal plunge, plunge_approach_z
        if plunge is None:
            return
        events.append(
            DrillEvent(
                plunge.line, plunge.end[0], plunge.end[1], plunge.end[2],
                plunge_approach_z if plunge_approach_z is not None else plunge.start[2],
                retract_z, plunge.tool, plunge.spindle_on, plunge.spindle,
                plunge.feed, plunge.wcs, plunge.length_comp,
                plunge.h_offset, "explicit",
            )
        )
        plunge = None
        plunge_approach_z = None

    for record in program.records:
        if plunge is not None:
            same_xy = math.hypot(record.end[0] - plunge.end[0], record.end[1] - plunge.end[1]) <= 0.05
            if record.motion == 0 and same_xy and record.end[2] > plunge.end[2] + 0.5:
                emit(record.end[2])
                approach_z = record.end[2]
                continue
            if (
                record.motion in (1, 2, 3)
                and pure_vertical(record)
                and same_xy
                and record.end[2] < plunge.end[2] - 0.05
            ):
                plunge = record
                continue
            if not same_xy:
                emit(None)

        if record.motion == 0:
            approach_z = record.end[2]
        elif (
            record.motion in (1, 2, 3)
            and pure_vertical(record)
            and record.end[2] < record.start[2] - 0.05
        ):
            plunge = record
            plunge_approach_z = approach_z if approach_z is not None else record.start[2]

    if plunge is not None:
        emit(None)
    return events


def state_is_valid(event: DrillEvent) -> bool:
    return (
        event.tool is not None
        and event.tool > 0
        and event.spindle_on
        and event.spindle is not None
        and event.spindle > 0
        and event.feed is not None
        and event.feed > 0
        and event.wcs is not None
        and event.length_comp
        and event.h_offset is not None
        and event.h_offset > 0
    )


def choose_coordinate_frame(events: Iterable[DrillEvent]) -> tuple[float, dict[Hole, DrillEvent]]:
    event_list = list(events)
    valid_frames: list[tuple[float, dict[Hole, DrillEvent]]] = []
    for top_z in (0.0, 12.0):
        selected: dict[Hole, DrillEvent] = {}
        frame_ok = True
        for hole in HOLES:
            matching = [event for event in event_list if near_hole(event.x, event.y, hole)]
            expected_bottom = top_z - hole.depth
            deepest_allowed = expected_bottom - (
                THROUGH_TIP_COMP_MAX_MM if hole.kind == "through" else DEPTH_TOL_MM
            )
            shallowest_allowed = expected_bottom + DEPTH_TOL_MM
            final = [
                event
                for event in matching
                if deepest_allowed <= event.bottom_z <= shallowest_allowed
            ]
            if len(final) != 1:
                frame_ok = False
                break
            if any(event.bottom_z < deepest_allowed for event in matching):
                frame_ok = False
                break
            selected[hole] = final[0]
        if frame_ok:
            valid_frames.append((top_z, selected))
    if len(valid_frames) != 1:
        raise EvaluationError("hole depths do not match exactly one supported WCS frame")
    return valid_frames[0]


def validate_program(program: Program) -> dict[str, object]:
    events = [*program.cycle_events, *explicit_events(program)]
    if not events:
        raise EvaluationError("no drilling operations found")

    for event in events:
        if not any(near_hole(event.x, event.y, hole) for hole in HOLES):
            raise EvaluationError(f"unexpected drilling location near line {event.line}")

    top_z, selected = choose_coordinate_frame(events)
    diameter_tools: dict[float, set[int]] = {5.0: set(), 6.0: set()}
    for hole, event in selected.items():
        if not state_is_valid(event):
            raise EvaluationError(f"invalid machining state for hole ({hole.x:g},{hole.y:g})")
        if event.approach_z is None or event.approach_z < top_z + SAFE_CLEARANCE_MM:
            raise EvaluationError(f"unsafe approach for hole ({hole.x:g},{hole.y:g})")
        if event.retract_z is None or event.retract_z < top_z + SAFE_CLEARANCE_MM:
            raise EvaluationError(f"unsafe retract for hole ({hole.x:g},{hole.y:g})")
        diameter_tools[hole.diameter].add(int(event.tool))

    if any(len(tools) != 1 for tools in diameter_tools.values()):
        raise EvaluationError("each diameter group must use one consistent final drilling tool")
    if diameter_tools[5.0] == diameter_tools[6.0]:
        raise EvaluationError("5 mm and 6 mm holes require distinct final drilling tools")

    return {
        "coordinate_frame_top_z_mm": top_z,
        "hole_count": len(selected),
        "diameter_tools": {str(key): sorted(value) for key, value in diameter_tools.items()},
        "methods": sorted({event.method for event in selected.values()}),
    }


def validate_outputs(target: Path) -> tuple[Program, dict[str, object]]:
    path = target / NC_NAME
    if not path.is_file() or path.stat().st_size < 80:
        raise EvaluationError(f"missing or empty {NC_NAME}")
    source = path.read_text(encoding="utf-8", errors="strict")
    program = parse_program(source)
    summary = validate_program(program)
    return program, summary


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def load_trusted_provenance(target: Path, path: Path | None, expected_hash: str | None) -> dict[str, object]:
    if path is None or expected_hash is None:
        raise EvaluationError("trusted provenance path and hash must be injected by the evaluator host")
    resolved = path.resolve(strict=True)
    target_resolved = target.resolve()
    writable_root = target_resolved
    for candidate in (target_resolved, *target_resolved.parents):
        if candidate.name.casefold() == "desktop":
            writable_root = candidate
            break
    if is_relative_to(resolved, writable_root):
        raise EvaluationError("provenance may not be read from the agent-writable target directory")
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", expected_hash):
        raise EvaluationError("trusted provenance hash pin is malformed")
    if sha256_file(resolved) != expected_hash.upper():
        raise EvaluationError("trusted provenance file is absent or not host-pinned")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EvaluationError("trusted provenance must be a JSON object")
    return data


def expect_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise EvaluationError(f"{label} must be a finite number")
    return float(value)


def validate_provenance(
    data: dict[str, object],
    target: Path,
    expected_run_id: str,
    nc_summary: dict[str, object],
) -> None:
    if data.get("schema") != "engiworld.trusted-cam-run.v1":
        raise EvaluationError("wrong provenance schema")
    if data.get("run_id") != expected_run_id:
        raise EvaluationError("provenance belongs to a stale or different evaluator run")
    if data.get("authority") != "evaluator-host-monitor" or data.get("immutable") is not True:
        raise EvaluationError("provenance is not trusted host evidence")

    product = data.get("product")
    if not isinstance(product, dict):
        raise EvaluationError("missing native product evidence")
    if str(product.get("name", "")).upper() != "SOLIDWORKS CAM" or int(product.get("major", 0)) != 2025:
        raise EvaluationError("native product must be SOLIDWORKS CAM 2025")
    if product.get("progid") != "SWCAM.CWApp" or product.get("addin_loaded") is not True:
        raise EvaluationError("SOLIDWORKS CAM add-in identity was not captured")

    inputs = data.get("formal_inputs")
    if not isinstance(inputs, dict):
        raise EvaluationError("missing formal input hashes")
    for name, expected in FORMAL_INPUT_SHA256.items():
        if str(inputs.get(name, "")).upper() != expected:
            raise EvaluationError(f"wrong formal input hash for {name}")

    output = data.get("output")
    if not isinstance(output, dict) or output.get("name") != NC_NAME:
        raise EvaluationError("missing posted output evidence")
    if str(output.get("sha256", "")).upper() != sha256_file(target / NC_NAME):
        raise EvaluationError("posted output hash mismatch")
    if int(output.get("bytes", 0)) != (target / NC_NAME).stat().st_size:
        raise EvaluationError("posted output size mismatch")

    setup = data.get("setup")
    if not isinstance(setup, dict):
        raise EvaluationError("missing CAM setup evidence")
    origin = setup.get("cad_origin_mm")
    if origin != [0.0, 0.0, 12.0] or setup.get("tool_axis") != "-Z" or setup.get("work_offset") != "G54":
        raise EvaluationError("wrong CAM setup transform")

    post = data.get("postprocess")
    if not isinstance(post, dict) or post.get("return_code") != 0:
        raise EvaluationError("native postprocess did not succeed")
    if not str(post.get("postprocessor", "")).lower().endswith(".ctl"):
        raise EvaluationError("native .ctl postprocessor was not captured")
    if not re.fullmatch(r"[0-9A-Fa-f]{64}", str(post.get("postprocessor_sha256", ""))):
        raise EvaluationError("postprocessor hash is missing")

    operations = data.get("operations")
    if not isinstance(operations, list) or len(operations) != len(HOLES):
        raise EvaluationError("native operation evidence must cover ten holes")
    summary_tools = nc_summary.get("diameter_tools")
    if not isinstance(summary_tools, dict):
        raise EvaluationError("NC tool-group summary is missing")
    for hole in HOLES:
        matches = [
            item for item in operations
            if isinstance(item, dict)
            and close(expect_number(item.get("x_mm"), "operation x"), hole.x, XY_TOL_MM)
            and close(expect_number(item.get("y_mm"), "operation y"), hole.y, XY_TOL_MM)
        ]
        if len(matches) != 1:
            raise EvaluationError(f"native operation evidence is ambiguous for ({hole.x:g},{hole.y:g})")
        item = matches[0]
        if not close(expect_number(item.get("diameter_mm"), "operation diameter"), hole.diameter, 0.05):
            raise EvaluationError("native operation diameter mismatch")
        if not close(expect_number(item.get("depth_mm"), "operation depth"), hole.depth, DEPTH_TOL_MM):
            raise EvaluationError("native operation depth mismatch")
        if item.get("kind") != hole.kind or item.get("toolpath_generated") is not True:
            raise EvaluationError("native operation lifecycle evidence is incomplete")
        if int(item.get("tool_station", 0)) <= 0 or int(item.get("segment_count", 0)) <= 0:
            raise EvaluationError("native tool or toolpath segment evidence is missing")
        expected_stations = summary_tools.get(str(hole.diameter))
        if expected_stations != [int(item.get("tool_station", 0))]:
            raise EvaluationError("native operation tool station does not match the posted NC")

    simulation = data.get("simulation")
    if not isinstance(simulation, dict) or simulation.get("completed") is not True:
        raise EvaluationError("native simulation was not completed")
    if simulation.get("collision_free") is not True or simulation.get("all_holes_verified") is not True:
        raise EvaluationError("native simulation did not verify the requested result")


def evaluate(
    target: Path,
    provenance_path: Path | None = None,
    provenance_sha256: str | None = None,
    expected_run_id: str | None = None,
) -> bool:
    _program, nc_summary = validate_outputs(target)
    if expected_run_id is None:
        expected_run_id = os.environ.get("ENGIWORLD_TRUSTED_RUN_ID")
    if not expected_run_id or not RUN_ID_RE.fullmatch(expected_run_id):
        raise EvaluationError("trusted run id was not injected by the evaluator host")
    provenance = load_trusted_provenance(target, provenance_path, provenance_sha256)
    validate_provenance(provenance, target, expected_run_id, nc_summary)
    return True


def main() -> bool:
    try:
        _program, nc_summary = validate_outputs(DEFAULT_TARGET)
        provenance_path = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE")
        provenance_sha256 = os.environ.get("ENGIWORLD_TRUSTED_PROVENANCE_SHA256")
        expected_run_id = os.environ.get("ENGIWORLD_TRUSTED_RUN_ID")
        supplied = [provenance_path, provenance_sha256, expected_run_id]
        if any(supplied) and not all(supplied):
            raise EvaluationError("trusted provenance injection is incomplete")
        if all(supplied):
            if not RUN_ID_RE.fullmatch(str(expected_run_id)):
                raise EvaluationError("trusted run id is malformed")
            provenance = load_trusted_provenance(
                DEFAULT_TARGET, Path(str(provenance_path)), str(provenance_sha256)
            )
            validate_provenance(provenance, DEFAULT_TARGET, str(expected_run_id), nc_summary)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print("True" if main() else "False")
    raise SystemExit(0)
