#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop")).resolve()
PRODUCTIVE_DESKTOP = Path("/home/user/Desktop")
SOFTWARE_SEQUENCE = ["KiCad", "OpenSCAD", "FreeCAD", "Blender"]
EXPECTED_VERSION_PATTERNS = {
    "KiCad": re.compile(r"(?<![0-9.])10\.0\.4(?![0-9.])"),
    "OpenSCAD": re.compile(r"\bOpenSCAD version 2021\.01\b", re.IGNORECASE),
    "FreeCAD": re.compile(r"\bFreeCAD 1\.1\.0\b", re.IGNORECASE),
    "Blender": re.compile(r"\bBlender 5\.2\.0\b", re.IGNORECASE),
}
EXPECTED_RELEASE_CHECKS = {
    "blender_review_pass",
    "c1_clamp_clearance_pass",
    "freecad_geometry_pass",
    "l1_keepout_pass",
    "required_artifacts_present",
    "u1_contact_pass",
}
MIN_RENDER_SIMILARITY = 0.95
REQUIRED_ARTIFACTS = [
    "01_kicad_board.kicad_pcb",
    "01_kicad_board.step",
    "01_kicad_export.json",
    "01_kicad_mechanical_map.csv",
    "01_kicad_parameters.scad",
    "02_openscad_enclosure.scad",
    "02_openscad_enclosure.stl",
    "02_openscad_parameters.json",
    "03_freecad_assembly.step",
    "03_freecad_assembly.obj",
    "03_freecad_clearance_report.json",
    "04_blender_review.blend",
    "04_blender_review.obj",
    "04_blender_review.mtl",
    "04_blender_review.png",
    "04_blender_scene_report.json",
    "toolchain_invocation_log.json",
    "final_release_package.json",
]
MIN_FILE_SIZE = {
    name: 1 for name in REQUIRED_ARTIFACTS
}
MAX_FILE_SIZE = 200 * 1024 * 1024


class EvaluationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise EvaluationError(message)


def number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        if not isinstance(value, str):
            fail(f"{label} is not numeric: {value!r}")
        match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value.strip())
        if match is None:
            fail(f"{label} is not numeric: {value!r}")
        result = float(match.group(0))
    if not math.isfinite(result):
        fail(f"{label} is not finite")
    return result


def close(actual: Any, expected: Any, tolerance: float, label: str) -> None:
    got = number(actual, label)
    want = number(expected, label)
    if abs(got - want) > tolerance:
        fail(f"{label}: expected {want} +/- {tolerance}, got {got}")


def close_vector(actual: Any, expected: Any, tolerance: float, label: str) -> None:
    if not isinstance(expected, (list, tuple)):
        fail(f"{label}: expected vector is missing or malformed: {expected!r}")
    if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
        fail(f"{label}: expected {len(expected)} values, got {actual!r}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        close(got, want, tolerance, f"{label}[{index}]")


def normalized(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def version_matches(software: str, value: Any) -> bool:
    pattern = EXPECTED_VERSION_PATTERNS.get(software)
    return pattern is not None and pattern.search(str(value or "")) is not None


FIELD_ALIASES = {
    "ref": ("ref", "reference", "reference_designator", "designator", "id"),
    "kind": ("kind", "type", "component_type", "footprint_kind"),
    "x_mm": ("x_mm", "x", "center_x_mm", "x_center_mm"),
    "y_mm": ("y_mm", "y", "center_y_mm", "y_center_mm"),
    "height_mm": ("height_mm", "height", "component_height_mm"),
    "keepout_radius_mm": ("keepout_radius_mm", "keepout_radius", "radius_mm", "clearance_radius_mm"),
    "diameter_mm": ("diameter_mm", "diameter", "hole_diameter_mm"),
    "body_bbox_mm": ("body_bbox_mm", "body_bbox", "body_dimensions_mm", "body_size_mm"),
    "board_bbox_mm": ("board_bbox_mm", "board_bbox", "board_dimensions_mm", "board_size_mm"),
    "components": ("components", "parts", "footprints"),
    "mounting_holes": ("mounting_holes", "holes", "mount_holes"),
    "commands": ("commands", "actual_invocations", "steps", "toolchain", "invocations"),
    "software": ("software", "software_stage", "stage", "tool", "application"),
    "command": ("command", "cmd", "command_line"),
    "inputs": ("inputs", "input", "input_files", "input_artifacts"),
    "outputs": ("outputs", "output", "output_files", "output_artifacts"),
    "version": ("version", "software_version", "tool_version"),
    "release_decision": ("release_decision", "decision", "status"),
    "required_artifacts": ("required_artifacts", "artifacts", "deliverables"),
}


def value_of(data: Any, key: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    aliases = FIELD_ALIASES.get(key, (key,))
    for alias in aliases:
        if alias in data:
            return data[alias]
    by_token = {normalized(actual): actual for actual in data}
    for alias in aliases:
        actual = by_token.get(normalized(alias))
        if actual is not None:
            return data[actual]
    return default


def json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot parse JSON {path.name}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.name} must contain a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trusted_input_paths() -> dict[str, Path]:
    override = os.environ.get("ENGIWORLD_TASK02_SPEC_DIR")
    if override:
        root = Path(override).resolve()
        paths = {
            "board": root / "board_input.kicad_pcb",
            "requirements": root / "mechanical_requirements.json",
            "connectors": root / "connector_keepouts.csv",
            "seed": root / "enclosure_seed.scad",
            "notes": root / "handoff_notes.md",
        }
    else:
        paths = {
            "board": DESKTOP / "_eval_task02_board_input.kicad_pcb",
            "requirements": DESKTOP / "_eval_task02_mechanical_requirements.json",
            "connectors": DESKTOP / "_eval_task02_connector_keepouts.csv",
            "seed": DESKTOP / "_eval_task02_enclosure_seed.scad",
            "notes": DESKTOP / "_eval_task02_handoff_notes.md",
        }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        fail("trusted postconfig input missing: " + ", ".join(missing))
    return paths


def sexpr_blocks(text: str, marker: str) -> list[str]:
    blocks: list[str] = []
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start < 0:
            return blocks
        depth = 0
        quoted = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
                continue
            if char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start : index + 1])
                    cursor = index + 1
                    break
        else:
            fail(f"unterminated KiCad block beginning with {marker!r}")


def property_number(block: str, name: str, default: float | None = None) -> float | None:
    match = re.search(rf'\(property\s+"{re.escape(name)}"\s+"([^"]+)"', block)
    return number(match.group(1), name) if match else default


def parse_board(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"cannot read KiCad board {path.name}: {exc}")
    if "(kicad_pcb" not in text:
        fail(f"{path.name} is not a KiCad PCB file")
    thickness_match = re.search(r"\((?:board_thickness|thickness)\s+([-+0-9.eE]+)\)", text)
    outline_match = re.search(
        r'\(gr_rect\s+\(start\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\)\s+'
        r'\(end\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\).*?\(layer\s+"Edge.Cuts"\)',
        text,
        flags=re.DOTALL,
    )
    if not thickness_match or not outline_match:
        fail(f"{path.name} lacks a readable thickness or rectangular Edge.Cuts outline")
    x1, y1, x2, y2 = (float(value) for value in outline_match.groups())
    footprints: dict[str, dict[str, Any]] = {}
    for block in sexpr_blocks(text, "(footprint "):
        name_match = re.search(r'\(footprint\s+"([^"]+)"', block)
        at_match = re.search(r"\(at\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", block)
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not name_match or not at_match or not ref_match:
            continue
        ref = ref_match.group(1)
        if ref in footprints:
            fail(f"{path.name} has duplicate footprint reference {ref}")
        drill_match = re.search(
            r'\(pad\s+"[^"]*"\s+np_thru_hole\b.*?\(drill\s+([-+0-9.eE]+)',
            block,
            flags=re.DOTALL,
        )
        footprints[ref] = {
            "block": block,
            "footprint": name_match.group(1),
            "kind": name_match.group(1).split(":")[-1],
            "ref": ref,
            "x_mm": float(at_match.group(1)),
            "y_mm": float(at_match.group(2)),
            "height_mm": property_number(block, "HEIGHT_MM", 0.0),
            "keepout_radius_mm": property_number(block, "KEEPOUT_RADIUS_MM", 0.0),
            "hole_diameter_mm": property_number(block, "HOLE_DIA_MM"),
            "npth_drill_mm": float(drill_match.group(1)) if drill_match else None,
        }
    return {
        "text": text,
        "thickness_mm": float(thickness_match.group(1)),
        "bounds_xy_mm": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
        "bbox_mm": [abs(x2 - x1), abs(y2 - y1), float(thickness_match.group(1))],
        "footprints": footprints,
    }


def read_connectors(path: Path) -> dict[str, dict[str, Any]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        fail(f"cannot parse trusted connector CSV: {exc}")
    required = {
        "ref", "kind", "body_x_mm", "body_y_mm",
        "wall_direction", "window_width_mm", "window_height_mm", "vertical_margin_mm",
    }
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not required.issubset(row):
            fail("trusted connector CSV lacks required columns")
        ref = str(row["ref"]).strip()
        if not ref or ref in result:
            fail(f"trusted connector CSV has invalid or duplicate ref {ref!r}")
        result[ref] = row
    if not result:
        fail("trusted connector CSV is empty")
    return result


def build_spec(paths: dict[str, Path]) -> dict[str, Any]:
    board = parse_board(paths["board"])
    requirements = json_file(paths["requirements"])
    connectors = read_connectors(paths["connectors"])
    if int(requirements.get("schema_version", 0)) < 2:
        fail("trusted mechanical requirements schema_version must be at least 2")
    for ref in connectors:
        if ref not in board["footprints"]:
            fail(f"trusted connector {ref} is absent from the KiCad board")
        connector = connectors[ref]
        height = number(board["footprints"][ref]["height_mm"], f"{ref} connector height")
        margin = number(connector["vertical_margin_mm"], f"{ref} vertical margin")
        close(
            connector["window_height_mm"],
            height + 2.0 * margin,
            1e-6,
            f"{ref} window_height = body height + two vertical margins",
        )
    return {"board": board, "requirements": requirements, "connectors": connectors, "paths": paths}


def check_required_files() -> None:
    for name in REQUIRED_ARTIFACTS:
        path = DESKTOP / name
        if not path.is_file():
            fail(f"missing required artifact {name}")
        if path.stat().st_size == 0:
            fail(f"required artifact {name} is empty")
        if path.stat().st_size > MAX_FILE_SIZE:
            fail(f"required artifact {name} is implausibly large ({path.stat().st_size} bytes)")


def check_answer_board(spec: dict[str, Any]) -> dict[str, Any]:
    canonical = spec["board"]
    answer = parse_board(DESKTOP / "01_kicad_board.kicad_pcb")
    axis_tol = number(spec["requirements"]["axis_tolerance_mm"], "axis_tolerance_mm")
    close(answer["thickness_mm"], canonical["thickness_mm"], axis_tol, "answer board nominal thickness")
    close_vector(answer["bounds_xy_mm"], canonical["bounds_xy_mm"], axis_tol, "answer board Edge.Cuts")
    for ref, expected in canonical["footprints"].items():
        actual = answer["footprints"].get(ref)
        if actual is None:
            fail(f"answer board is missing footprint {ref}")
        close(actual["x_mm"], expected["x_mm"], axis_tol, f"answer board {ref} x")
        close(actual["y_mm"], expected["y_mm"], axis_tol, f"answer board {ref} y")
        if ref.startswith("MH"):
            expected_diameter = number(expected["hole_diameter_mm"], f"trusted {ref} hole diameter")
            close(actual["hole_diameter_mm"], expected_diameter, axis_tol, f"answer board {ref} HOLE_DIA_MM")
            close(actual["npth_drill_mm"], expected_diameter, axis_tol, f"answer board {ref} NPTH drill")
        else:
            close(actual["height_mm"], expected["height_mm"], axis_tol, f"answer board {ref} height")
            close(
                actual["keepout_radius_mm"],
                expected["keepout_radius_mm"],
                axis_tol,
                f"answer board {ref} keepout radius",
            )
    return answer


def rows_by_ref(path: Path) -> dict[str, dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        fail(f"cannot parse {path.name}: {exc}")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        ref = str(value_of(row, "ref", "")).strip()
        if not ref or ref in result:
            fail(f"{path.name} has invalid or duplicate ref {ref!r}")
        result[ref] = row
    return result


def check_kicad_map_and_export(spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    board = spec["board"]
    req = spec["requirements"]
    connectors = spec["connectors"]
    axis_tol = number(req["axis_tolerance_mm"], "axis_tolerance_mm")
    rows = rows_by_ref(DESKTOP / "01_kicad_mechanical_map.csv")
    for ref, footprint in board["footprints"].items():
        row = rows.get(ref)
        if row is None:
            fail(f"mechanical map lacks {ref}")
        close(value_of(row, "x_mm"), footprint["x_mm"], axis_tol, f"map {ref} x")
        close(value_of(row, "y_mm"), footprint["y_mm"], axis_tol, f"map {ref} y")
        if ref.startswith("MH"):
            close(value_of(row, "diameter_mm"), footprint["hole_diameter_mm"], axis_tol, f"map {ref} hole diameter")
        else:
            close(value_of(row, "height_mm"), footprint["height_mm"], axis_tol, f"map {ref} height")
            close(value_of(row, "keepout_radius_mm"), footprint["keepout_radius_mm"], axis_tol, f"map {ref} keepout radius")
        if ref in connectors:
            connector = connectors[ref]
            for field in ("body_x_mm", "body_y_mm", "window_width_mm", "window_height_mm", "vertical_margin_mm"):
                actual = value_of(row, field)
                if actual not in (None, ""):
                    close(actual, connector[field], axis_tol, f"map {ref} {field}")
            direction = value_of(row, "wall_direction")
            if direction not in (None, "") and normalized(direction) != normalized(connector["wall_direction"]):
                fail(f"mechanical map {ref} wall direction mismatch")
            alignment = value_of(row, "alignment_tolerance_mm")
            if alignment not in (None, ""):
                close(alignment, req["aperture_center_tolerance_mm"], 1e-6, f"map {ref} alignment tolerance")

    export = json_file(DESKTOP / "01_kicad_export.json")
    close_vector(value_of(export, "board_bbox_mm"), board["bbox_mm"], axis_tol, "KiCad export board bbox")
    components = value_of(export, "components")
    if not isinstance(components, list):
        fail("01_kicad_export.json components must be a list")
    components_by_ref = {str(value_of(item, "ref")): item for item in components if isinstance(item, dict)}
    component_heights: list[float] = []
    for ref, footprint in board["footprints"].items():
        if ref.startswith("MH"):
            continue
        item = components_by_ref.get(ref)
        if item is None:
            fail(f"KiCad export is missing component {ref}")
        close(value_of(item, "x_mm"), footprint["x_mm"], axis_tol, f"export {ref} x")
        close(value_of(item, "y_mm"), footprint["y_mm"], axis_tol, f"export {ref} y")
        close(value_of(item, "height_mm"), footprint["height_mm"], axis_tol, f"export {ref} height")
        close(value_of(item, "keepout_radius_mm"), footprint["keepout_radius_mm"], axis_tol, f"export {ref} radius")
        component_heights.append(number(footprint["height_mm"], f"{ref} height"))
        if ref in connectors:
            expected_body = [
                number(connectors[ref]["body_x_mm"], f"{ref} body x"),
                number(connectors[ref]["body_y_mm"], f"{ref} body y"),
                number(footprint["height_mm"], f"{ref} body z"),
            ]
        else:
            expected_body = [number(value, f"{ref} body") for value in req["component_bodies"][ref]["bbox_mm"]]
        body_bbox = value_of(item, "body_bbox_mm")
        if body_bbox is not None:
            close_vector(body_bbox, expected_body, axis_tol, f"export {ref} body bbox")
    max_height = value_of(export, "max_component_height_mm")
    if max_height is not None:
        close(max_height, max(component_heights), axis_tol, "max_component_height_mm")
    holes = value_of(export, "mounting_holes")
    if not isinstance(holes, list):
        fail("KiCad export mounting_holes must be a list")
    holes_by_ref = {str(value_of(item, "ref")): item for item in holes if isinstance(item, dict)}
    for ref, footprint in board["footprints"].items():
        if not ref.startswith("MH"):
            continue
        item = holes_by_ref.get(ref)
        if item is None:
            fail(f"KiCad export is missing mounting hole {ref}")
        close(value_of(item, "x_mm"), footprint["x_mm"], axis_tol, f"export {ref} x")
        close(value_of(item, "y_mm"), footprint["y_mm"], axis_tol, f"export {ref} y")
        close(value_of(item, "diameter_mm"), footprint["hole_diameter_mm"], axis_tol, f"export {ref} diameter")
    if export.get("input_board_sha256") is not None and export["input_board_sha256"] != sha256(spec["paths"]["board"]):
        fail("KiCad export input_board_sha256 does not match the trusted input board")
    return export, rows


def expected_apertures(spec: dict[str, Any]) -> list[dict[str, Any]]:
    board = spec["board"]
    req = spec["requirements"]
    enclosure = [number(value, "enclosure bbox") for value in req["expected_enclosure_bbox_mm"]]
    board_top = number(req["board_bottom_z_mm"], "board_bottom_z_mm") + number(board["thickness_mm"], "board thickness")
    overcut = number(req["aperture_overcut_mm"], "aperture_overcut_mm")
    result = []
    for ref, connector in spec["connectors"].items():
        footprint = board["footprints"][ref]
        width = number(connector["window_width_mm"], f"{ref} window width")
        height = number(connector["window_height_mm"], f"{ref} window height")
        connector_height = number(footprint["height_mm"], f"{ref} connector height")
        center_z = board_top + connector_height / 2.0
        y1 = number(footprint["y_mm"], f"{ref} y") - width / 2.0
        y2 = number(footprint["y_mm"], f"{ref} y") + width / 2.0
        z1, z2 = center_z - height / 2.0, center_z + height / 2.0
        direction = str(connector["wall_direction"])
        if direction == "X_MINUS":
            x1 = -enclosure[0] / 2.0 - overcut
            x2 = -enclosure[0] / 2.0 + number(req["wall_mm"], "wall_mm") + overcut
        elif direction == "X_PLUS":
            x1 = enclosure[0] / 2.0 - number(req["wall_mm"], "wall_mm") - overcut
            x2 = enclosure[0] / 2.0 + overcut
        else:
            fail(f"unsupported connector wall direction {direction!r}")
        result.append(
            {
                "ref": ref,
                "wall_direction": direction,
                "bounds_mm": [x1, y1, z1, x2, y2, z2],
                "center_tangent_mm": number(footprint["y_mm"], f"{ref} y"),
                "center_z_mm": center_z,
                "window_width_mm": width,
                "window_height_mm": height,
            }
        )
    return result


def check_openscad_handoff(spec: dict[str, Any], apertures: list[dict[str, Any]]) -> dict[str, Any]:
    req = spec["requirements"]
    board = spec["board"]
    tol = number(req["geometry_tolerance_mm"], "geometry_tolerance_mm")
    handoff_path = DESKTOP / "01_kicad_parameters.scad"
    source_path = DESKTOP / "02_openscad_enclosure.scad"
    try:
        handoff_text = handoff_path.read_text(encoding="utf-8")
        source_text = source_path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"cannot read OpenSCAD handoff/source: {exc}")
    uncommented = re.sub(r"/\*.*?\*/|//[^\n]*", "", handoff_text, flags=re.DOTALL)
    assignments = re.findall(r"(?m)^\s*[A-Za-z_$][A-Za-z0-9_$]*\s*=", uncommented)
    if not assignments:
        fail("01_kicad_parameters.scad does not contain a parameter assignment")
    include_pattern = r"(?im)^\s*include\s*<\s*(?:[^>]+/)?01_kicad_parameters\.scad\s*>"
    if re.search(include_pattern, source_text) is None:
        fail("02_openscad_enclosure.scad must include and consume 01_kicad_parameters.scad")

    params = json_file(DESKTOP / "02_openscad_parameters.json")
    enclosure = [number(value, "enclosure") for value in req["expected_enclosure_bbox_mm"]]
    wall = number(req["wall_mm"], "wall_mm")
    base = number(req["base_thickness_mm"], "base_thickness_mm")
    lid = number(req["lid_thickness_mm"], "lid_thickness_mm")
    cavity = [enclosure[0] - 2 * wall, enclosure[1] - 2 * wall, enclosure[2] - base - lid]
    board_top = number(req["board_bottom_z_mm"], "board_bottom_z_mm") + board["thickness_mm"]
    for aliases, expected, label in (
        (("board_bbox_mm", "pcb_bbox_mm"), board["bbox_mm"], "OpenSCAD params board bbox"),
        (("enclosure_bbox_mm", "outer_bbox_mm", "package_bbox_mm"), enclosure, "OpenSCAD params enclosure bbox"),
        (("cavity_bbox_mm", "inner_cavity_bbox_mm"), cavity, "OpenSCAD params cavity bbox"),
    ):
        for field in aliases:
            if params.get(field) is not None:
                close_vector(params[field], expected, tol, label + " (" + field + ")")
    for field, expected in (
        ("wall_mm", wall),
        ("base_thickness_mm", base),
        ("lid_thickness_mm", lid),
        ("board_bottom_z_mm", req["board_bottom_z_mm"]),
        ("board_top_z_mm", board_top),
        ("lid_inner_z_mm", enclosure[2] - lid),
        ("standoff_height_mm", req["standoff_height_mm"]),
        ("standoff_outer_diameter_mm", req["standoff_outer_diameter_mm"]),
        ("standoff_bore_diameter_mm", req["standoff_bore_diameter_mm"]),
        ("aperture_overcut_mm", req["aperture_overcut_mm"]),
        ("minimum_c1_clamp_clearance_mm", req["minimum_c1_clamp_clearance_mm"]),
        ("maximum_u1_contact_gap_mm", req["maximum_u1_contact_gap_mm"]),
    ):
        if params.get(field) is not None:
            close(params.get(field), expected, tol, f"OpenSCAD params {field}")
    if params.get("standoff_count") is not None and int(number(params.get("standoff_count"), "standoff_count")) != 4:
        fail("OpenSCAD params standoff_count mismatch")
    for count_field in ("window_count", "aperture_count", "access_count"):
        if params.get(count_field) is not None and int(number(params[count_field], count_field)) != len(apertures):
            fail(f"OpenSCAD params {count_field} mismatch")
    for container_name in ("apertures", "windows", "accesses"):
        actual_apertures = params.get(container_name)
        if actual_apertures is None:
            continue
        if isinstance(actual_apertures, list):
            actual_by_ref = {str(item.get("ref")): item for item in actual_apertures if isinstance(item, dict)}
        elif isinstance(actual_apertures, dict):
            actual_by_ref = {}
            for ref, value in actual_apertures.items():
                if not isinstance(value, dict):
                    fail(f"OpenSCAD params {container_name}.{ref} must be an object")
                actual_by_ref[str(ref)] = value
        else:
            fail(f"OpenSCAD params {container_name} must be a list or object when provided")
        for expected in apertures:
            actual = actual_by_ref.get(expected["ref"])
            if actual is None:
                fail(f"OpenSCAD params {container_name} omit {expected['ref']}")
            for field in ("wall_direction", "direction"):
                if actual.get(field) is not None and normalized(actual[field]) != normalized(expected["wall_direction"]):
                    fail(f"OpenSCAD params {expected['ref']} {field} mismatch")
            for field in ("bounds_mm", "bbox_mm", "path_bounds_mm"):
                if actual.get(field) is not None:
                    close_vector(actual[field], expected["bounds_mm"], tol, f"OpenSCAD params {expected['ref']} {field}")
            for field in ("window_width_mm", "width_mm", "finished_width_mm"):
                if actual.get(field) is not None:
                    close(actual[field], expected["window_width_mm"], tol, f"OpenSCAD params {expected['ref']} {field}")
            for field in ("window_height_mm", "height_mm", "finished_height_mm"):
                if actual.get(field) is not None:
                    close(actual[field], expected["window_height_mm"], tol, f"OpenSCAD params {expected['ref']} {field}")
    if params.get("input_mechanical_map_sha256") is not None and params.get("input_mechanical_map_sha256") != sha256(DESKTOP / "01_kicad_mechanical_map.csv"):
        fail("OpenSCAD params input_mechanical_map_sha256 mismatch")
    if params.get("input_parameter_handoff") is not None and Path(str(params.get("input_parameter_handoff"))).name != "01_kicad_parameters.scad":
        fail("OpenSCAD params input_parameter_handoff mismatch")
    if params.get("source") is not None and Path(str(params.get("source"))).name != "02_openscad_enclosure.scad":
        fail("OpenSCAD params source reference mismatch")
    if params.get("mesh") is not None and Path(str(params.get("mesh"))).name != "02_openscad_enclosure.stl":
        fail("OpenSCAD params mesh reference mismatch")
    return params


def resolve_executable(name: str, candidates: list[str]) -> str:
    found = shutil.which(name)
    if found:
        return found
    for candidate in candidates:
        matches = sorted(Path("/").glob(candidate.lstrip("/"))) if "*" in candidate else [Path(candidate)]
        for path in reversed(matches):
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
    fail(f"required evaluator executable is unavailable: {name}")


def run_command(command: list[str], *, cwd: Path, timeout: int, label: str) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env={**os.environ, "PYTHONPATH": ""},
        )
    except Exception as exc:
        fail(f"{label} could not run: {exc}")
    if completed.returncode != 0:
        output = (completed.stdout + "\n" + completed.stderr)[-3000:]
        fail(f"{label} failed with return code {completed.returncode}: {output}")
    return completed


def run_kicad_export(answer_board: Path, output_step: Path, runtime: Path) -> None:
    kicad = resolve_executable(
        "kicad-cli",
        ["/home/user/Applications/kicad-*/kicad-*-x86_64.AppImage"],
    )
    if Path(kicad).suffix.lower() == ".appimage":
        prefix = [kicad, "--appimage-extract-and-run", "kicad-cli"]
    else:
        prefix = [kicad]
    run_command(
        prefix
        + [
            "pcb", "export", "step", "--force", "--board-only", "--output", str(output_step), str(answer_board)
        ],
        cwd=runtime,
        timeout=60,
        label="KiCad board STEP re-export",
    )
    if not output_step.is_file() or output_step.stat().st_size < 500:
        fail("KiCad re-export did not create a substantial STEP file")


def load_mesh_metrics(path: Path) -> dict[str, Any]:
    try:
        import numpy as np
    except Exception as exc:
        fail(f"evaluator mesh dependencies unavailable: {exc}")
    try:
        import struct

        data = path.read_bytes()
        triangles = None
        if len(data) >= 84:
            facet_count = struct.unpack_from("<I", data, 80)[0]
            if facet_count > 0 and 84 + facet_count * 50 == len(data):
                record_type = np.dtype([
                    ("normal", "<f4", (3,)),
                    ("vertices", "<f4", (3, 3)),
                    ("attribute", "<u2"),
                ])
                records = np.frombuffer(data, dtype=record_type, count=facet_count, offset=84)
                triangles = np.asarray(records["vertices"], dtype=float)
        if triangles is None:
            vertices = []
            for line in data.decode("utf-8", errors="strict").splitlines():
                fields = line.strip().split()
                if fields and fields[0].lower() == "vertex" and len(fields) == 4:
                    vertices.append([float(value) for value in fields[1:]])
            if not vertices or len(vertices) % 3:
                fail(f"{path.name} is not a valid binary or ASCII STL triangle mesh")
            triangles = np.asarray(vertices, dtype=float).reshape((-1, 3, 3))
        if not np.isfinite(triangles).all():
            fail(f"{path.name} contains non-finite coordinates")

        vertex_ids: dict[tuple[float, float, float], int] = {}
        mesh_vertices: list[tuple[float, float, float]] = []
        faces: list[tuple[int, int, int]] = []
        seen_faces: set[tuple[int, int, int]] = set()
        for triangle in triangles:
            ids = []
            for raw in triangle:
                key = tuple(round(float(value), 8) for value in raw)
                if key not in vertex_ids:
                    vertex_ids[key] = len(mesh_vertices)
                    mesh_vertices.append(key)
                ids.append(vertex_ids[key])
            if len(set(ids)) != 3:
                continue
            points = np.asarray([mesh_vertices[index] for index in ids], dtype=float)
            if float(np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0]))) <= 1e-12:
                continue
            canonical = tuple(sorted(ids))
            if canonical in seen_faces:
                continue
            seen_faces.add(canonical)
            faces.append(tuple(ids))
        if len(mesh_vertices) < 20 or len(faces) < 30:
            fail(f"{path.name} has implausibly little geometry")

        edge_uses: dict[tuple[int, int], list[int]] = {}
        for a, b, c in faces:
            for start, end in ((a, b), (b, c), (c, a)):
                edge = (min(start, end), max(start, end))
                edge_uses.setdefault(edge, []).append(1 if start < end else -1)
        if any(len(uses) != 2 for uses in edge_uses.values()):
            fail(f"{path.name} must be a watertight mesh")
        if any(uses[0] + uses[1] != 0 for uses in edge_uses.values()):
            fail(f"{path.name} must be consistently wound")

        vertex_array = np.asarray(mesh_vertices, dtype=float)
        face_points = vertex_array[np.asarray(faces, dtype=int)]
        cross = np.cross(face_points[:, 1] - face_points[:, 0], face_points[:, 2] - face_points[:, 0])
        signed_tetra = np.einsum("ij,ij->i", face_points[:, 0], np.cross(face_points[:, 1], face_points[:, 2])) / 6.0
        signed_volume = float(signed_tetra.sum())
        volume = abs(signed_volume)
        area = float((np.linalg.norm(cross, axis=1) * 0.5).sum())
        if volume <= 0 or area <= 0:
            fail(f"{path.name} must be a positive-volume mesh")
        center = ((face_points.sum(axis=1) / 4.0) * signed_tetra[:, None]).sum(axis=0) / signed_volume
        bounds = np.asarray([vertex_array.min(axis=0), vertex_array.max(axis=0)], dtype=float)
        dims = bounds[1] - bounds[0]
        return {
            "bounds": [float(value) for value in bounds.reshape(-1)],
            "bbox": [float(value) for value in dims],
            "volume": volume,
            "area": area,
            "center": [float(value) for value in center],
            "vertices": len(mesh_vertices),
            "faces": len(faces),
        }
    except EvaluationError:
        raise
    except Exception as exc:
        fail(f"cannot inspect mesh {path.name}: {exc}")


def compare_meshes(submitted: dict[str, Any], rendered: dict[str, Any], expected_bbox: list[float]) -> None:
    close_vector(submitted["bbox"], expected_bbox, 0.15, "submitted STL bbox")
    close_vector(rendered["bbox"], expected_bbox, 0.15, "OpenSCAD rerender bbox")
    expected_bounds = [-expected_bbox[0] / 2, -expected_bbox[1] / 2, 0.0, expected_bbox[0] / 2, expected_bbox[1] / 2, expected_bbox[2]]
    close_vector(submitted["bounds"], expected_bounds, 0.15, "submitted STL bounds")
    close_vector(rendered["bounds"], expected_bounds, 0.15, "OpenSCAD rerender bounds")
    outer_volume = math.prod(expected_bbox)
    for label, metrics in (("submitted", submitted), ("rerendered", rendered)):
        fill = metrics["volume"] / outer_volume
        if not 0.12 <= fill <= 0.65:
            fail(f"{label} enclosure fill ratio {fill:.4f} is not a plausible hollow enclosure")
    if abs(submitted["volume"] - rendered["volume"]) > max(2.0, rendered["volume"] * 0.01):
        fail("submitted STL volume does not agree with the submitted SCAD rerender")
    if abs(submitted["area"] - rendered["area"]) > max(5.0, rendered["area"] * 0.02):
        fail("submitted STL area does not agree with the submitted SCAD rerender")
    close_vector(submitted["center"], rendered["center"], 0.2, "SCAD/STL center of mass")


FREECAD_CHECKER = r'''
import json
import math
import os
import re
import traceback

import FreeCAD as App
import Import
import Mesh
import MeshPart
import Part


config = json.load(open(os.environ["ENGIWORLD_TASK02_CAD_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK02_CAD_RESULT"]


def vec_bbox(shape):
    box = shape.BoundBox
    return [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]


def shape_metrics(shape):
    return {
        "valid": bool(shape.isValid()),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "bounds_mm": vec_bbox(shape),
        "bbox_mm": [shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength],
    }


def read_step(path):
    shape = Part.read(path)
    if shape.isNull() or not shape.isValid() or not shape.Solids or shape.Volume <= 0:
        raise RuntimeError("STEP has no valid positive-volume solid: " + path)
    return shape


def read_step_objects(path, doc_name):
    doc = App.newDocument(doc_name)
    Import.insert(path, doc.Name)
    doc.recompute()
    values = []
    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull() or not shape.isValid() or not shape.Solids or shape.Volume <= 0:
            continue
        solids = list(shape.Solids)
        if len(solids) == 1:
            values.append({"name": obj.Name, "label": obj.Label, "shape": shape})
        else:
            for index, solid in enumerate(solids):
                values.append({
                    "name": obj.Name + "_solid_" + str(index),
                    "label": obj.Label + " solid " + str(index),
                    "shape": solid,
                })
    unique = []
    for value in values:
        shape = value["shape"]
        duplicate = False
        for prior in unique:
            other = prior["shape"]
            if abs(float(shape.Volume) - float(other.Volume)) > 1e-4:
                continue
            if any(
                abs(float(first) - float(second)) > 1e-4
                for first, second in zip(vec_bbox(shape), vec_bbox(other))
            ):
                continue
            common = shape.common(other)
            common_volume = 0.0 if common.isNull() else float(common.Volume)
            if abs(float(shape.Volume) - common_volume) <= 1e-4:
                duplicate = True
                break
        if not duplicate:
            unique.append(value)
    values = unique
    if not values:
        raise RuntimeError("STEP import produced no shape objects: " + path)
    return doc, values


def mesh_solid(path):
    mesh = Mesh.Mesh(path)
    if mesh.CountFacets < 30:
        raise RuntimeError("STL has too few facets: " + path)
    shell_shape = Part.Shape()
    shell_shape.makeShapeFromMesh(mesh.Topology, 0.05)
    if not shell_shape.isClosed():
        raise RuntimeError("STL is not closed: " + path)
    shells = list(shell_shape.Shells)
    if not shells:
        shells = [shell_shape]
    solids = []
    for index, shell in enumerate(shells):
        if not shell.isClosed():
            raise RuntimeError("STL contains an open shell at index " + str(index) + ": " + path)
        try:
            candidate = Part.makeSolid(shell)
        except Exception as exc:
            raise RuntimeError("STL shell cannot form a solid at index " + str(index) + ": " + str(exc))
        if candidate.isNull() or not candidate.isValid() or not candidate.Solids or candidate.Volume <= 0:
            raise RuntimeError("STL shell is not a valid positive-volume solid at index " + str(index))
        solids.extend(candidate.Solids)
    solid = Part.makeCompound(solids) if len(solids) > 1 else solids[0]
    if solid.isNull() or not solid.isValid() or not solid.Solids or solid.Volume <= 0:
        raise RuntimeError("STL cannot be converted into valid solids: " + path)
    return solid.removeSplitter()


def inside(shape, x, y, z):
    return bool(shape.isInside(App.Vector(float(x), float(y), float(z)), 1e-4, False))


def empty_span(center, low, high, empty_at, precision):
    if not empty_at(center) or empty_at(low) or empty_at(high):
        return None

    def transition(material_value, empty_value):
        while abs(empty_value - material_value) > precision:
            midpoint = (material_value + empty_value) / 2.0
            if empty_at(midpoint):
                empty_value = midpoint
            else:
                material_value = midpoint
        return (material_value + empty_value) / 2.0

    return [transition(low, center), transition(high, center)]


def box_from_bounds(bounds):
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    return Part.makeBox(xmax - xmin, ymax - ymin, zmax - zmin, App.Vector(xmin, ymin, zmin))


def overlap_metrics(first, second):
    common = float(first.common(second).Volume)
    symmetric_difference = float(first.Volume + second.Volume - 2.0 * common)
    return {
        "common_volume_mm3": common,
        "first_only_volume_mm3": max(0.0, float(first.Volume) - common),
        "second_only_volume_mm3": max(0.0, float(second.Volume) - common),
        "symmetric_difference_volume_mm3": max(0.0, symmetric_difference),
    }


def export_reference_obj(objects, path):
    doc = App.newDocument("Task02EvalReferenceMesh")
    mesh_objects = []
    for index, value in enumerate(objects):
        mesh_obj = doc.addObject("Mesh::Feature", "Reference_%02d" % index)
        mesh_obj.Label = value["label"]
        mesh_obj.Mesh = MeshPart.meshFromShape(
            Shape=value["shape"],
            LinearDeflection=0.1,
            AngularDeflection=0.35,
            Relative=False,
        )
        if mesh_obj.Mesh.CountFacets <= 0:
            raise RuntimeError("cannot mesh assembly object for bridge verification: " + value["label"])
        mesh_objects.append(mesh_obj)
    Mesh.export(mesh_objects, path)
    if not os.path.isfile(path) or os.path.getsize(path) < 1000:
        raise RuntimeError("FreeCAD checker could not create its assembly reference OBJ")


def aperture_metrics(shape, aperture):
    outer = config["enclosure_bbox_mm"]
    wall = config["wall_mm"]
    direction = aperture["wall_direction"]
    if direction == "X_MINUS":
        wall_x = [-outer[0] / 2.0, -outer[0] / 2.0 + wall]
    elif direction == "X_PLUS":
        wall_x = [outer[0] / 2.0 - wall, outer[0] / 2.0]
    else:
        raise RuntimeError("unsupported wall direction: " + str(direction))
    xmin, ymin, zmin, xmax, ymax, zmax = aperture["bounds_mm"]
    edge_slack = 0.005
    core = box_from_bounds([xmin, ymin + edge_slack, zmin + edge_slack, xmax, ymax - edge_slack, zmax - edge_slack])
    residual = float(shape.common(core).Volume)
    core_empty = residual <= max(0.01, float(core.Volume) * 1e-5)

    step = 0.02
    center_y = aperture["center_tangent_mm"]
    center_z = aperture["center_z_mm"]
    x_mid = (wall_x[0] + wall_x[1]) / 2.0
    search_margin = config["aperture_center_tolerance_mm"] + config["geometry_tolerance_mm"] + 0.2
    y_span = empty_span(center_y, ymin - search_margin, ymax + search_margin,
                        lambda value: not inside(shape, x_mid, value, center_z), step)
    z_span = empty_span(center_z, zmin - search_margin, zmax + search_margin,
                        lambda value: not inside(shape, x_mid, center_y, value), step)
    measured_width = y_span[1] - y_span[0] if y_span else 0.0
    measured_height = z_span[1] - z_span[0] if z_span else 0.0
    measured_center_y = (y_span[0] + y_span[1]) / 2.0 if y_span else float("inf")
    measured_center_z = (z_span[0] + z_span[1]) / 2.0 if z_span else float("inf")
    dimension_ok = (
        abs(measured_width - aperture["window_width_mm"]) <= config["geometry_tolerance_mm"] + step
        and abs(measured_height - aperture["window_height_mm"]) <= config["geometry_tolerance_mm"] + step
        and abs(measured_center_y - center_y) <= config["aperture_center_tolerance_mm"] + step
        and abs(measured_center_z - center_z) <= config["aperture_center_tolerance_mm"] + step
    )

    guard_gap = config["aperture_center_tolerance_mm"] + config["geometry_tolerance_mm"] / 2.0 + 0.05
    guard_width = 0.3
    guards = [
        box_from_bounds([wall_x[0], ymin - guard_gap - guard_width, zmin + edge_slack, wall_x[1], ymin - guard_gap, zmax - edge_slack]),
        box_from_bounds([wall_x[0], ymax + guard_gap, zmin + edge_slack, wall_x[1], ymax + guard_gap + guard_width, zmax - edge_slack]),
        box_from_bounds([wall_x[0], ymin + edge_slack, zmin - guard_gap - guard_width, wall_x[1], ymax - edge_slack, zmin - guard_gap]),
        box_from_bounds([wall_x[0], ymin + edge_slack, zmax + guard_gap, wall_x[1], ymax - edge_slack, zmax + guard_gap + guard_width]),
    ]
    guard_fill = [float(shape.common(guard).Volume) / float(guard.Volume) for guard in guards]
    bounded = all(value >= 0.95 for value in guard_fill)
    through = core_empty and bounded and dimension_ok
    return {
        "ref": aperture["ref"],
        "through": bool(through),
        "wall_direction": direction,
        "corridor_residual_volume_mm3": residual,
        "guard_fill_ratios": guard_fill,
        "bounded_by_wall_material": bool(bounded),
        "measured_center_tangent_mm": measured_center_y,
        "measured_center_z_mm": measured_center_z,
        "measured_window_height_mm": measured_height,
        "measured_window_width_mm": measured_width,
    }


def enclosure_sanity(shape):
    outer = config["enclosure_bbox_mm"]
    wall = config["wall_mm"]
    base = config["base_thickness_mm"]
    lid = config["lid_thickness_mm"]
    z_cavity = (base + outer[2] - lid) / 2.0
    cavity_x = outer[0] - 2.0 * wall
    cavity_y = outer[1] - 2.0 * wall
    lid_probe = Part.makeBox(
        cavity_x,
        cavity_y,
        max(0.1, lid - 0.2),
        App.Vector(-cavity_x / 2.0, -cavity_y / 2.0, outer[2] - lid + 0.1),
    )
    lid_coverage = float(shape.common(lid_probe).Volume) / float(lid_probe.Volume)
    base_slab = Part.makeBox(outer[0], outer[1], base, App.Vector(-outer[0] / 2.0, -outer[1] / 2.0, 0.0))
    lid_slab = Part.makeBox(outer[0], outer[1], lid, App.Vector(-outer[0] / 2.0, -outer[1] / 2.0, outer[2] - lid))
    wall_height = outer[2] - lid - base
    wall_slabs = [
        Part.makeBox(wall, outer[1], wall_height, App.Vector(-outer[0] / 2.0, -outer[1] / 2.0, base)),
        Part.makeBox(wall, outer[1], wall_height, App.Vector(outer[0] / 2.0 - wall, -outer[1] / 2.0, base)),
        Part.makeBox(outer[0] - 2.0 * wall, wall, wall_height, App.Vector(-outer[0] / 2.0 + wall, -outer[1] / 2.0, base)),
        Part.makeBox(outer[0] - 2.0 * wall, wall, wall_height, App.Vector(-outer[0] / 2.0 + wall, outer[1] / 2.0 - wall, base)),
    ]
    expected_walls = wall_slabs[0].fuse(wall_slabs[1]).fuse(wall_slabs[2]).fuse(wall_slabs[3])
    for aperture in config["apertures"]:
        expected_walls = expected_walls.cut(box_from_bounds(aperture["bounds_mm"]))
    base_fill = float(shape.common(base_slab).Volume) / float(base_slab.Volume)
    lid_fill = float(shape.common(lid_slab).Volume) / float(lid_slab.Volume)
    wall_fill = float(shape.common(expected_walls).Volume) / float(expected_walls.Volume)
    checks = {
        "base_slab_coverage": base_fill >= 0.98,
        "floor": inside(shape, 0, 0, base / 2.0),
        "center_cavity": not inside(shape, 0, 0, z_cavity),
        "lid_center": inside(shape, 0, 0, outer[2] - lid / 2.0),
        "lid_corners": all(
            inside(shape, x, y, outer[2] - lid / 2.0)
            for x, y in [(-40, -24), (-40, 24), (40, -24), (40, 24)]
        ),
        "x_walls": inside(shape, -outer[0] / 2.0 + wall / 2.0, 24, z_cavity)
                   and inside(shape, outer[0] / 2.0 - wall / 2.0, 24, z_cavity),
        "y_walls": inside(shape, 0, -outer[1] / 2.0 + wall / 2.0, z_cavity)
                   and inside(shape, 0, outer[1] / 2.0 - wall / 2.0, z_cavity),
        "lid_coverage": lid_coverage >= 0.98,
        "lid_slab_coverage": lid_fill >= 0.98,
        "side_wall_coverage": wall_fill >= 0.98,
    }
    return checks


def standoff_checks(shape):
    base = config["base_thickness_mm"]
    standoff_height = config["standoff_height_mm"]
    bore = config["standoff_bore_diameter_mm"]
    outer = config["standoff_outer_diameter_mm"]
    result = {}
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        outside = Part.makeCylinder(outer / 2.0, standoff_height, App.Vector(x, y, base))
        bore_shape = Part.makeCylinder(bore / 2.0, standoff_height, App.Vector(x, y, base))
        expected_annulus = outside.cut(bore_shape)
        annulus_fill = float(shape.common(expected_annulus).Volume) / float(expected_annulus.Volume)
        bore_residual = float(shape.common(bore_shape).Volume)
        oversize_outer = Part.makeCylinder(outer / 2.0 + 0.5, standoff_height, App.Vector(x, y, base))
        oversize_inner = Part.makeCylinder(outer / 2.0 + 0.2, standoff_height, App.Vector(x, y, base))
        oversize_ring = oversize_outer.cut(oversize_inner)
        oversize_fill = float(shape.common(oversize_ring).Volume) / float(oversize_ring.Volume)
        result[hole["ref"]] = {
            "bore_empty": bore_residual <= max(0.05, float(bore_shape.Volume) * 0.005),
            "annulus_present": annulus_fill >= 0.95,
            "not_oversized": oversize_fill <= 0.05,
            "annulus_fill_ratio": annulus_fill,
            "bore_residual_volume_mm3": bore_residual,
        }
    return result


def pick_object(objects, role, ref=None):
    role_hint = config.get("freecad_object_roles", {})
    wanted_names = []
    if isinstance(role_hint, dict):
        value = role_hint.get(role if ref is None else ref)
        if isinstance(value, str):
            wanted_names.append(value)
    for obj in objects:
        if obj["name"] in wanted_names or obj["label"] in wanted_names:
            return obj
    for obj in objects:
        blob = (obj["name"] + " " + obj["label"]).upper()
        if role == "enclosure" and ("ENCLOSURE" in blob or "OPENSCAD" in blob):
            return obj
        if role == "board" and ("PCB" in blob or "KICAD" in blob or "BOARD" in blob):
            return obj
        if role == "component" and ref and re.search(r"(^|[^A-Z0-9])" + re.escape(ref.upper()) + r"([^A-Z0-9]|$)", blob):
            return obj
    if role == "board":
        candidates = [
            obj for obj in objects
            if abs(obj["shape"].BoundBox.XLength - config["board_bbox_mm"][0]) <= 0.2
            and abs(obj["shape"].BoundBox.YLength - config["board_bbox_mm"][1]) <= 0.2
            and obj["shape"].BoundBox.ZLength <= 3.0
        ]
        if len(candidates) == 1:
            return candidates[0]
    if role == "component" and ref:
        expected = next((item for item in config["components"] if item["ref"] == ref), None)
        if expected is not None:
            sx, sy, sz = expected["body_bbox_mm"]
            candidates = []
            for obj in objects:
                box = obj["shape"].BoundBox
                if (
                    abs(box.XLength - sx) <= 0.2
                    and abs(box.YLength - sy) <= 0.2
                    and abs(box.ZLength - sz) <= 0.2
                    and abs((box.XMin + box.XMax) / 2.0 - expected["x_mm"]) <= 0.2
                    and abs((box.YMin + box.YMax) / 2.0 - expected["y_mm"]) <= 0.2
                ):
                    candidates.append(obj)
            if len(candidates) == 1:
                return candidates[0]
    diagnostic = [
        {
            "name": obj["name"],
            "label": obj["label"],
            "bbox": [obj["shape"].BoundBox.XLength, obj["shape"].BoundBox.YLength, obj["shape"].BoundBox.ZLength],
            "center": [
                (obj["shape"].BoundBox.XMin + obj["shape"].BoundBox.XMax) / 2.0,
                (obj["shape"].BoundBox.YMin + obj["shape"].BoundBox.YMax) / 2.0,
                (obj["shape"].BoundBox.ZMin + obj["shape"].BoundBox.ZMax) / 2.0,
            ],
        }
        for obj in objects
    ]
    raise RuntimeError("cannot locate STEP role " + role + (" " + ref if ref else "") + ": " + json.dumps(diagnostic))


def bounds_contained(shape, expected, tolerance):
    actual = vec_bbox(shape)
    return all(actual[index] >= expected[index] - tolerance for index in range(3)) and all(
        actual[index] <= expected[index] + tolerance for index in range(3, 6)
    )


def group_role(objects, expected, label, tolerance):
    matches = [obj for obj in objects if bounds_contained(obj["shape"], expected, tolerance)]
    if not matches:
        raise RuntimeError("cannot locate STEP role geometry: " + label)
    shape = Part.makeCompound([obj["shape"] for obj in matches])
    if max(abs(a - b) for a, b in zip(vec_bbox(shape), expected)) > tolerance:
        raise RuntimeError(
            "STEP role geometry union has unexpected bounds: " + label
            + " expected=" + json.dumps(expected)
            + " actual=" + json.dumps(vec_bbox(shape))
        )
    return matches, shape


def component_config(ref):
    return next(item for item in config["components"] if item["ref"] == ref)


def component_nominal_top(ref):
    item = component_config(ref)
    return config["board_bottom_z_mm"] + config["board_bbox_mm"][2] + item["body_bbox_mm"][2]


def l1_keepout_metrics(enclosure):
    item = component_config("L1")
    z0 = config["board_bottom_z_mm"] + config["board_bbox_mm"][2]
    z1 = config["lid_inner_z_mm"]
    keepout = Part.makeCylinder(
        item["keepout_radius_mm"],
        z1 - z0,
        App.Vector(item["x_mm"], item["y_mm"], z0),
    )
    common = enclosure.common(keepout)
    return {
        "bounds_mm": vec_bbox(keepout),
        "volume_mm3": float(keepout.Volume),
        "intersection_mm3": 0.0 if common.isNull() else float(common.Volume),
    }


def c1_clearance_metrics(enclosure):
    item = component_config("C1")
    z0 = component_nominal_top("C1")
    z1 = config["enclosure_bbox_mm"][2]
    probe = Part.makeCylinder(
        item["keepout_radius_mm"],
        z1 - z0,
        App.Vector(item["x_mm"], item["y_mm"], z0),
    )
    covering = enclosure.common(probe)
    if covering.isNull() or covering.Volume <= 0:
        return {"covered": False, "clearance_mm": None, "covering_volume_mm3": 0.0}
    return {
        "covered": True,
        "clearance_mm": float(covering.BoundBox.ZMin - z0),
        "covering_volume_mm3": float(covering.Volume),
        "covering_bounds_mm": vec_bbox(covering),
    }


def u1_contact_metrics(enclosure):
    item = component_config("U1")
    size_x, size_y = config["u1_contact_pad_bbox_mm"]
    z0 = component_nominal_top("U1")
    lid_inner = config["lid_inner_z_mm"]
    tolerance = config["geometry_tolerance_mm"]
    probe_bottom = z0 - tolerance
    probe = Part.makeBox(
        size_x,
        size_y,
        lid_inner - probe_bottom + tolerance,
        App.Vector(item["x_mm"] - size_x / 2.0, item["y_mm"] - size_y / 2.0, probe_bottom),
    )
    contact = enclosure.common(probe)
    if contact.isNull() or contact.Volume <= 0:
        return {
            "present": False,
            "gap_mm": None,
            "continuous_to_lid_inner_face": False,
            "column_fill_ratio": 0.0,
            "lower_face_fill_ratio": 0.0,
        }
    lower = float(contact.BoundBox.ZMin)
    gap = lower - z0
    inset = min(0.02, max(0.002, tolerance / 10.0))
    column_bottom = lower + inset
    column_height = lid_inner - column_bottom
    if column_height <= 0:
        fill = 0.0
        lower_fill = 0.0
    else:
        required_column = Part.makeBox(
            size_x,
            size_y,
            column_height,
            App.Vector(item["x_mm"] - size_x / 2.0, item["y_mm"] - size_y / 2.0, column_bottom),
        )
        fill = float(enclosure.common(required_column).Volume) / float(required_column.Volume)
        slice_height = min(0.1, column_height)
        lower_slice = Part.makeBox(
            size_x,
            size_y,
            slice_height,
            App.Vector(item["x_mm"] - size_x / 2.0, item["y_mm"] - size_y / 2.0, column_bottom),
        )
        lower_fill = float(enclosure.common(lower_slice).Volume) / float(lower_slice.Volume)
    return {
        "present": True,
        "gap_mm": gap,
        "bounds_mm": vec_bbox(contact),
        "continuous_to_lid_inner_face": bool(contact.BoundBox.ZMax >= lid_inner - tolerance),
        "column_fill_ratio": fill,
        "lower_face_fill_ratio": lower_fill,
    }


def side_clearance_metrics(enclosure, board):
    box = board.BoundBox
    inset = min(0.1, box.ZLength / 4.0)
    z0 = box.ZMin + inset
    z_size = max(0.05, box.ZLength - 2.0 * inset)
    package_box = enclosure.BoundBox
    level_slab = Part.makeBox(
        package_box.XLength + 2.0,
        package_box.YLength + 2.0,
        z_size,
        App.Vector(package_box.XMin - 1.0, package_box.YMin - 1.0, z0),
    )
    level_material = enclosure.common(level_slab)
    if level_material.isNull() or level_material.Volume <= 0:
        raise RuntimeError("package has no side-wall material across the PCB thickness")
    edge_inset = min(0.1, box.XLength / 10.0, box.YLength / 10.0)
    thickness = 0.001
    probes = {
        "X_MINUS": Part.makeBox(
            thickness, box.YLength - 2.0 * edge_inset, z_size,
            App.Vector(box.XMin - thickness / 2.0, box.YMin + edge_inset, z0),
        ),
        "X_PLUS": Part.makeBox(
            thickness, box.YLength - 2.0 * edge_inset, z_size,
            App.Vector(box.XMax - thickness / 2.0, box.YMin + edge_inset, z0),
        ),
        "Y_MINUS": Part.makeBox(
            box.XLength - 2.0 * edge_inset, thickness, z_size,
            App.Vector(box.XMin + edge_inset, box.YMin - thickness / 2.0, z0),
        ),
        "Y_PLUS": Part.makeBox(
            box.XLength - 2.0 * edge_inset, thickness, z_size,
            App.Vector(box.XMin + edge_inset, box.YMax - thickness / 2.0, z0),
        ),
    }
    return {direction: float(level_material.distToShape(probe)[0]) for direction, probe in probes.items()}


def critical_package_metrics(package):
    l1 = l1_keepout_metrics(package)
    c1 = c1_clearance_metrics(package)
    u1 = u1_contact_metrics(package)
    return {
        "l1_keepout": l1,
        "l1_keepout_intersection_mm3": l1["intersection_mm3"],
        "c1_clearance": c1,
        "c1_clamp_clearance_mm": c1["clearance_mm"],
        "u1_contact": u1,
        "u1_contact_gap_mm": u1["gap_mm"],
    }


def main():
    board_submitted = read_step(config["submitted_board_step"])
    board_rerendered = read_step(config["rerendered_board_step"])
    stl_submitted = mesh_solid(config["submitted_stl"])
    stl_rerendered = mesh_solid(config["rerendered_stl"])
    assembly_shape = read_step(config["assembly_step"])
    doc, objects = read_step_objects(config["assembly_step"], "Task02EvalAssembly")
    board_z0 = config["board_bottom_z_mm"]
    board_expected = [
        -config["board_bbox_mm"][0] / 2.0,
        -config["board_bbox_mm"][1] / 2.0,
        board_z0,
        config["board_bbox_mm"][0] / 2.0,
        config["board_bbox_mm"][1] / 2.0,
        board_z0 + config["board_bbox_mm"][2],
    ]
    board_objects, assembly_board = group_role(objects, board_expected, "PCB", 0.2)
    component_objects = {}
    component_shapes = {}
    board_top = board_z0 + config["board_bbox_mm"][2]
    for item in config["components"]:
        sx, sy, sz = item["body_bbox_mm"]
        expected = [
            item["x_mm"] - sx / 2.0,
            item["y_mm"] - sy / 2.0,
            board_top,
            item["x_mm"] + sx / 2.0,
            item["y_mm"] + sy / 2.0,
            board_top + sz,
        ]
        matches, shape = group_role(objects, expected, "component " + item["ref"], 0.2)
        component_objects[item["ref"]] = matches
        component_shapes[item["ref"]] = shape
    assigned = [*board_objects, *(obj for values in component_objects.values() for obj in values)]
    enclosure_parts = [obj for obj in objects if all(obj is not used for used in assigned)]
    if not enclosure_parts:
        raise RuntimeError("cannot locate any enclosure solids after identifying PCB and components")
    enclosure = Part.makeCompound([obj["shape"] for obj in enclosure_parts])
    export_reference_obj(objects, config["reference_bridge_obj"])

    hole_checks = {}
    zmid = (board_rerendered.BoundBox.ZMin + board_rerendered.BoundBox.ZMax) / 2.0
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        probe_r = hole["diameter_mm"] / 2.0 + 0.3
        hole_checks[hole["ref"]] = {
            "center_empty_submitted": not inside(board_submitted, x, y, zmid),
            "center_empty_rerendered": not inside(board_rerendered, x, y, zmid),
            "surrounding_board_submitted": inside(board_submitted, x + probe_r, y, zmid),
            "surrounding_board_rerendered": inside(board_rerendered, x + probe_r, y, zmid),
        }

    apertures_submitted = [aperture_metrics(stl_submitted, item) for item in config["apertures"]]
    apertures_rerendered = [aperture_metrics(stl_rerendered, item) for item in config["apertures"]]
    apertures_assembly = [aperture_metrics(enclosure, item) for item in config["apertures"]]
    component_metrics = {}
    intersections = {"PCB": float(enclosure.common(assembly_board).Volume)}
    for item in config["components"]:
        ref = item["ref"]
        shape = component_shapes[ref]
        component_metrics[ref] = shape_metrics(shape)
        intersections[ref] = float(enclosure.common(shape).Volume)
    critical_by_geometry = {
        "submitted_stl": critical_package_metrics(stl_submitted),
        "rerendered_stl": critical_package_metrics(stl_rerendered),
        "assembly_step": critical_package_metrics(enclosure),
    }
    assembly_critical = critical_by_geometry["assembly_step"]
    u1_item = component_config("U1")
    contact_x, contact_y = config["u1_contact_pad_bbox_mm"]
    contact_allowance = config["geometry_tolerance_mm"]
    contact_z0 = component_nominal_top("U1") - contact_allowance
    allowed_contact = Part.makeBox(
        contact_x + 2.0 * contact_allowance,
        contact_y + 2.0 * contact_allowance,
        config["lid_inner_z_mm"] - contact_z0 + contact_allowance,
        App.Vector(
            u1_item["x_mm"] - contact_x / 2.0 - contact_allowance,
            u1_item["y_mm"] - contact_y / 2.0 - contact_allowance,
            contact_z0,
        ),
    )
    assembly_extra = enclosure.cut(stl_submitted)
    if assembly_extra.isNull():
        assembly_extra_outside_contact = 0.0
    else:
        allowed_overlap = assembly_extra.common(allowed_contact)
        allowed_overlap_volume = 0.0 if allowed_overlap.isNull() else float(allowed_overlap.Volume)
        assembly_extra_outside_contact = max(0.0, float(assembly_extra.Volume) - allowed_overlap_volume)
    volume = float(enclosure.Volume)
    density = config["material_density_g_cm3"]
    side = side_clearance_metrics(enclosure, assembly_board)
    return {
        "board_submitted": shape_metrics(board_submitted),
        "board_rerendered": shape_metrics(board_rerendered),
        "board_submitted_vs_rerendered": overlap_metrics(board_submitted, board_rerendered),
        "board_holes": hole_checks,
        "stl_submitted": shape_metrics(stl_submitted),
        "stl_rerendered": shape_metrics(stl_rerendered),
        "stl_submitted_vs_rerendered": overlap_metrics(stl_submitted, stl_rerendered),
        "assembly": shape_metrics(assembly_shape),
        "assembly_enclosure": shape_metrics(enclosure),
        "assembly_enclosure_vs_submitted_stl": overlap_metrics(enclosure, stl_submitted),
        "assembly_extra_outside_u1_contact_mm3": assembly_extra_outside_contact,
        "assembly_board": shape_metrics(assembly_board),
        "components": component_metrics,
        "apertures_submitted": apertures_submitted,
        "apertures_rerendered": apertures_rerendered,
        "apertures_assembly": apertures_assembly,
        "enclosure_sanity": enclosure_sanity(enclosure),
        "standoffs": standoff_checks(enclosure),
        "interference_by_object_mm3": intersections,
        "interference_volume_mm3": sum(intersections.values()),
        "critical_by_geometry": critical_by_geometry,
        "l1_keepout": assembly_critical["l1_keepout"],
        "l1_keepout_intersection_mm3": assembly_critical["l1_keepout_intersection_mm3"],
        "c1_clearance": assembly_critical["c1_clearance"],
        "c1_clamp_clearance_mm": assembly_critical["c1_clamp_clearance_mm"],
        "u1_contact": assembly_critical["u1_contact"],
        "u1_contact_gap_mm": assembly_critical["u1_contact_gap_mm"],
        "nominal_side_clearances_mm": side,
        "enclosure_volume_mm3": volume,
        "estimated_shell_mass_g": volume * density / 1000.0,
        "object_labels": {
            "enclosure": [obj["label"] for obj in enclosure_parts],
            "board": [obj["label"] for obj in board_objects],
            **{ref: [obj["label"] for obj in values] for ref, values in component_objects.items()},
        },
    }


try:
    payload = {"ok": True, "result": main()}
except Exception as exc:
    payload = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
with open(result_path, "w") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
'''


def run_freecad_checker(
    runtime: Path,
    spec: dict[str, Any],
    export: dict[str, Any],
    apertures: list[dict[str, Any]],
    rerendered_board_step: Path,
    rerendered_stl: Path,
    freecad_report: dict[str, Any],
) -> dict[str, Any]:
    freecad = resolve_executable(
        "freecadcmd",
        ["/home/user/.local/bin/freecadcmd", "/usr/bin/freecadcmd", "/usr/bin/FreeCADCmd"],
    )
    req = spec["requirements"]
    board = spec["board"]
    components = []
    exported = {str(item.get("ref")): item for item in export["components"]}
    for ref, footprint in board["footprints"].items():
        if ref.startswith("MH"):
            continue
        item = exported[ref]
        components.append(
            {
                "ref": ref,
                "x_mm": footprint["x_mm"],
                "y_mm": footprint["y_mm"],
                "height_mm": footprint["height_mm"],
                "keepout_radius_mm": footprint["keepout_radius_mm"],
                "body_bbox_mm": [number(value, f"{ref} body") for value in item["body_bbox_mm"]],
            }
        )
    mounting_holes = [
        {
            "ref": ref,
            "x_mm": item["x_mm"],
            "y_mm": item["y_mm"],
            "diameter_mm": item["hole_diameter_mm"],
        }
        for ref, item in board["footprints"].items()
        if ref.startswith("MH")
    ]
    config = {
        "submitted_board_step": str(DESKTOP / "01_kicad_board.step"),
        "rerendered_board_step": str(rerendered_board_step),
        "submitted_stl": str(DESKTOP / "02_openscad_enclosure.stl"),
        "rerendered_stl": str(rerendered_stl),
        "assembly_step": str(DESKTOP / "03_freecad_assembly.step"),
        "reference_bridge_obj": str(runtime / "assembly_reference.obj"),
        "board_bbox_mm": board["bbox_mm"],
        "enclosure_bbox_mm": [number(value, "enclosure bbox") for value in req["expected_enclosure_bbox_mm"]],
        "wall_mm": number(req["wall_mm"], "wall_mm"),
        "base_thickness_mm": number(req["base_thickness_mm"], "base_thickness_mm"),
        "lid_thickness_mm": number(req["lid_thickness_mm"], "lid_thickness_mm"),
        "lid_inner_z_mm": number(req["expected_enclosure_bbox_mm"][2], "enclosure z") - number(req["lid_thickness_mm"], "lid thickness"),
        "board_bottom_z_mm": number(req["board_bottom_z_mm"], "board_bottom_z_mm"),
        "standoff_height_mm": number(req["standoff_height_mm"], "standoff_height_mm"),
        "standoff_bore_diameter_mm": number(req["standoff_bore_diameter_mm"], "standoff_bore_diameter_mm"),
        "standoff_outer_diameter_mm": number(req["standoff_outer_diameter_mm"], "standoff_outer_diameter_mm"),
        "aperture_center_tolerance_mm": number(req["aperture_center_tolerance_mm"], "aperture center tolerance"),
        "minimum_aperture_guard_mm": number(req["minimum_aperture_guard_mm"], "minimum aperture guard"),
        "geometry_tolerance_mm": number(req["geometry_tolerance_mm"], "geometry tolerance"),
        "material_density_g_cm3": number(req["material_density_g_cm3"], "material density"),
        "u1_contact_pad_bbox_mm": [number(value, "U1 contact pad bbox") for value in req["clamp_contact_pad_bbox_mm"]],
        "mounting_holes": mounting_holes,
        "components": components,
        "apertures": apertures,
        "freecad_object_roles": freecad_report.get("object_roles", {}),
    }
    config_path = runtime / "cad_config.json"
    result_path = runtime / "cad_result.json"
    checker_path = runtime / "freecad_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(FREECAD_CHECKER, encoding="utf-8")
    env_before = os.environ.get("ENGIWORLD_TASK02_CAD_CONFIG"), os.environ.get("ENGIWORLD_TASK02_CAD_RESULT")
    os.environ["ENGIWORLD_TASK02_CAD_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK02_CAD_RESULT"] = str(result_path)
    completed: subprocess.CompletedProcess[str]
    try:
        completed = subprocess.run(
            [freecad, str(checker_path)],
            cwd=runtime,
            text=True,
            capture_output=True,
            timeout=300,
            check=False,
            env={**os.environ, "PYTHONPATH": ""},
        )
    finally:
        for key, old in zip(("ENGIWORLD_TASK02_CAD_CONFIG", "ENGIWORLD_TASK02_CAD_RESULT"), env_before):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
    if not result_path.is_file():
        output = (completed.stdout + "\n" + completed.stderr)[-3000:]
        fail(f"FreeCAD/OCC geometry checker failed with return code {completed.returncode}: {output}")
    payload = json_file(result_path)
    if not payload.get("ok"):
        detail = str(payload.get("traceback") or "")[-3000:]
        fail(f"FreeCAD/OCC checker rejected artifacts: {payload.get('error')}\n{detail}")
    # This FreeCAD 1.1.0 build reports its post-result closeAllDocuments SIGSEGV
    # as either a direct signal or wrapper rc=1. Keep the wrapper exception tied
    # to the observed shutdown stack so ordinary nonzero failures remain fatal.
    output = completed.stdout + "\n" + completed.stderr
    wrapped_shutdown_sigsegv = (
        completed.returncode == 1
        and "Program received signal SIGSEGV" in output
        and "closeAllDocuments" in output
    )
    if completed.returncode not in (0, -11) and not wrapped_shutdown_sigsegv:
        output = output[-3000:]
        fail(f"FreeCAD/OCC geometry checker failed with return code {completed.returncode}: {output}")
    result = payload.get("result")
    if not isinstance(result, dict):
        fail("FreeCAD/OCC checker returned no result")
    return result


def validate_critical_geometry(
    req: dict[str, Any],
    metrics: dict[str, Any],
    label: str,
    *,
    require_u1_contact: bool,
) -> tuple[float, float, float | None]:
    geom_tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    l1_intersection = number(metrics["l1_keepout_intersection_mm3"], f"{label} L1 keepout intersection")
    l1_limit = number(req["l1_keepout"]["max_package_intersection_mm3"], "L1 intersection limit")
    if l1_intersection > l1_limit + 1e-6:
        fail(f"{label} L1 keepout intrusion is too large: {l1_intersection}")
    c1_details = metrics.get("c1_clearance", {})
    if not c1_details.get("covered"):
        fail(f"{label} C1 keepout region has no installed covering clamp/lid material")
    c1_clearance = number(metrics["c1_clamp_clearance_mm"], f"{label} C1 clamp clearance")
    if c1_clearance + geom_tol < number(req["minimum_c1_clamp_clearance_mm"], "minimum C1 clearance"):
        fail(f"{label} C1 clamp clearance is insufficient: {c1_clearance}")
    if not require_u1_contact:
        return l1_intersection, c1_clearance, None
    u1_details = metrics.get("u1_contact", {})
    if not u1_details.get("present"):
        fail(f"{label} U1 thermal contact pad is missing")
    u1_gap = number(metrics["u1_contact_gap_mm"], f"{label} U1 contact gap")
    if u1_gap < -geom_tol / 10.0:
        fail(f"{label} U1 contact penetrates the nominal body: {u1_gap}")
    if u1_gap > number(req["maximum_u1_contact_gap_mm"], "maximum U1 contact gap") + geom_tol / 10.0:
        fail(f"{label} U1 contact gap is too large: {u1_gap}")
    if not u1_details.get("continuous_to_lid_inner_face"):
        fail(f"{label} U1 contact solid does not continue to the lid inner face")
    if number(u1_details.get("column_fill_ratio"), f"{label} U1 contact column fill") < 0.95:
        fail(f"{label} U1 contact does not fill a continuous 6 x 6 mm column")
    if number(u1_details.get("lower_face_fill_ratio"), f"{label} U1 contact lower-face fill") < 0.95:
        fail(f"{label} U1 contact lower face is not a real 6 x 6 mm pad")
    return l1_intersection, c1_clearance, u1_gap


def check_cad_result(spec: dict[str, Any], export: dict[str, Any], result: dict[str, Any], report: dict[str, Any]) -> None:
    req = spec["requirements"]
    board = spec["board"]
    geom_tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    expected_enclosure = [number(value, "enclosure bbox") for value in req["expected_enclosure_bbox_mm"]]
    submitted_board = result["board_submitted"]
    rerendered_board = result["board_rerendered"]
    close_vector(submitted_board["bbox_mm"], rerendered_board["bbox_mm"], 0.05, "submitted/re-exported board STEP bbox")
    close_vector(submitted_board["bounds_mm"], rerendered_board["bounds_mm"], 0.05, "submitted/re-exported board STEP bounds")
    if abs(number(submitted_board["volume_mm3"], "board volume") - number(rerendered_board["volume_mm3"], "board volume")) > max(0.5, number(rerendered_board["volume_mm3"], "board volume") * 0.002):
        fail("submitted board STEP volume differs from the KiCad re-export")
    board_delta = number(
        result["board_submitted_vs_rerendered"]["symmetric_difference_volume_mm3"],
        "submitted/re-exported board STEP symmetric difference",
    )
    if board_delta > max(0.5, number(rerendered_board["volume_mm3"], "board volume") * 0.002):
        fail(f"submitted board STEP geometry differs from the KiCad re-export: {board_delta}")
    for ref, checks in result["board_holes"].items():
        if not all(bool(value) for value in checks.values()):
            fail(f"board STEP does not contain the required real NPTH geometry at {ref}")
    for key in ("apertures_submitted", "apertures_rerendered", "apertures_assembly"):
        values = result.get(key)
        if not isinstance(values, list) or {item.get("ref") for item in values} != set(spec["connectors"]):
            fail(f"{key} did not inspect all required apertures")
        for item in values:
            if not item.get("through") or not item.get("bounded_by_wall_material"):
                fail(f"{key} aperture {item.get('ref')} is not an aligned, bounded through-opening")
    if not all(bool(value) for value in result.get("enclosure_sanity", {}).values()):
        fail(f"assembly enclosure lacks a real floor, cavity, lid, or continuous walls: {result.get('enclosure_sanity')}")
    for ref, checks in result.get("standoffs", {}).items():
        if not checks.get("bore_empty") or not checks.get("annulus_present") or not checks.get("not_oversized"):
            fail(f"standoff/bore geometry is invalid at {ref}: {checks}")
    close_vector(result["assembly_enclosure"]["bbox_mm"], expected_enclosure, 0.2, "assembly enclosure bbox")
    close_vector(result["assembly_enclosure"]["bbox_mm"], result["stl_submitted"]["bbox_mm"], 0.2, "STL/STEP enclosure bbox")
    stl_volume = number(result["stl_submitted"]["volume_mm3"], "STL volume")
    enclosure_volume = number(result["assembly_enclosure"]["volume_mm3"], "assembly enclosure volume")
    submitted_rerendered_delta = number(
        result["stl_submitted_vs_rerendered"]["symmetric_difference_volume_mm3"],
        "submitted/rerendered STL symmetric difference",
    )
    if submitted_rerendered_delta > max(5.0, stl_volume * 0.005):
        fail(f"submitted STL geometry differs materially from the submitted SCAD rerender: {submitted_rerendered_delta}")
    assembly_overlap = result["assembly_enclosure_vs_submitted_stl"]
    missing_stl_volume = number(assembly_overlap["second_only_volume_mm3"], "OpenSCAD geometry missing from assembly")
    if missing_stl_volume > max(5.0, stl_volume * 0.005):
        fail(f"FreeCAD assembly omits material from the submitted OpenSCAD STL: {missing_stl_volume}")
    extra_outside_contact = number(
        result["assembly_extra_outside_u1_contact_mm3"],
        "FreeCAD assembly material outside the OpenSCAD package and allowed U1 contact",
    )
    if extra_outside_contact > number(req["interference_volume_tolerance_mm3"], "extra material tolerance") + 1e-6:
        fail(f"FreeCAD assembly adds unauthorized package material outside the U1 contact: {extra_outside_contact}")
    close_vector(result["assembly_board"]["bbox_mm"], submitted_board["bbox_mm"], 0.1, "assembly/submitted board bbox")
    close(
        (result["assembly_board"]["bounds_mm"][0] + result["assembly_board"]["bounds_mm"][3]) / 2.0,
        (submitted_board["bounds_mm"][0] + submitted_board["bounds_mm"][3]) / 2.0,
        0.05,
        "assembly PCB center X",
    )
    close(
        (result["assembly_board"]["bounds_mm"][1] + result["assembly_board"]["bounds_mm"][4]) / 2.0,
        (submitted_board["bounds_mm"][1] + submitted_board["bounds_mm"][4]) / 2.0,
        0.05,
        "assembly PCB center Y",
    )
    close(result["assembly_board"]["bounds_mm"][2], req["board_bottom_z_mm"], 0.1, "assembly PCB bottom Z")
    exported_components = {str(item.get("ref")): item for item in export["components"]}
    board_top = number(req["board_bottom_z_mm"], "board bottom") + board["thickness_mm"]
    for ref, metrics in result["components"].items():
        expected = exported_components[ref]
        close_vector(metrics["bbox_mm"], expected["body_bbox_mm"], 0.1, f"assembly {ref} body bbox")
        bounds = metrics["bounds_mm"]
        close((bounds[0] + bounds[3]) / 2.0, expected["x_mm"], 0.1, f"assembly {ref} center x")
        close((bounds[1] + bounds[4]) / 2.0, expected["y_mm"], 0.1, f"assembly {ref} center y")
        close(bounds[2], board_top, 0.1, f"assembly {ref} bottom z")
    interference = number(result["interference_volume_mm3"], "computed interference")
    if interference > number(req["interference_volume_tolerance_mm3"], "interference tolerance") + 1e-6:
        fail(f"computed unintended interference is too large: {interference}")

    critical_by_geometry = result.get("critical_by_geometry")
    if not isinstance(critical_by_geometry, dict):
        fail("FreeCAD/OCC checker did not return per-geometry critical metrics")
    expected_critical = {"submitted_stl", "rerendered_stl", "assembly_step"}
    if set(critical_by_geometry) != expected_critical:
        fail("FreeCAD/OCC checker did not inspect every submitted/rerendered/assembly package geometry")
    validated_critical = {
        key: validate_critical_geometry(
            req,
            critical_by_geometry[key],
            key.replace("_", " "),
            require_u1_contact=(key == "assembly_step"),
        )
        for key in ("submitted_stl", "rerendered_stl", "assembly_step")
    }
    l1_intersection, c1_clearance, u1_gap = validated_critical["assembly_step"]

    required_report_fields = {
        "package_volume_mm3",
        "package_mass_g",
        "minimum_side_clearance_mm",
        "unintended_interference_volume_mm3",
        "c1_clamp_clearance_mm",
        "l1_keepout_intersection_mm3",
        "u1_contact_gap_mm",
        "decision",
    }
    missing_report_fields = sorted(required_report_fields - set(report))
    if missing_report_fields:
        fail("FreeCAD clearance report lacks required fields: " + ", ".join(missing_report_fields))
    if normalized(report.get("decision")) not in {"PASS", "PASSED"}:
        fail("FreeCAD clearance report decision must be pass")
    if report.get("inputs") is not None:
        report_inputs = {Path(str(value)).name for value in report.get("inputs", [])}
        required_report_inputs = {"01_kicad_board.step", "02_openscad_enclosure.stl", "02_openscad_parameters.json"}
        if not required_report_inputs.issubset(report_inputs):
            fail("FreeCAD clearance report does not record all consumed KiCad/OpenSCAD inputs")
    if report.get("assembly_step") is not None and Path(str(report.get("assembly_step"))).name != "03_freecad_assembly.step":
        fail("FreeCAD clearance report assembly_step mismatch")
    if report.get("assembly_mesh") is not None and Path(str(report.get("assembly_mesh"))).name != "03_freecad_assembly.obj":
        fail("FreeCAD clearance report assembly_mesh mismatch")
    if report.get("nominal_board_bbox_mm") is not None:
        close_vector(
            report.get("nominal_board_bbox_mm"),
            board["bbox_mm"],
            geom_tol,
            "FreeCAD report nominal board bbox",
        )
    if report.get("measured_board_step_bbox_mm") is not None:
        close_vector(
            report.get("measured_board_step_bbox_mm"),
            result["assembly_board"]["bbox_mm"],
            0.1,
            "FreeCAD report measured board STEP bbox",
        )
    if report.get("enclosure_bbox_mm") is not None:
        close_vector(report.get("enclosure_bbox_mm"), expected_enclosure, 0.2, "FreeCAD report enclosure bbox")
    close(report.get("package_volume_mm3"), enclosure_volume, max(2.0, enclosure_volume * 0.01), "FreeCAD report package volume")
    close(report.get("package_mass_g"), result["estimated_shell_mass_g"], max(0.05, result["estimated_shell_mass_g"] * number(req["mass_relative_tolerance"], "mass tolerance")), "FreeCAD report package mass")
    close(report.get("unintended_interference_volume_mm3"), interference, max(0.01, geom_tol), "FreeCAD report unintended interference")
    close(report.get("l1_keepout_intersection_mm3"), l1_intersection, max(0.01, geom_tol), "FreeCAD report L1 keepout intersection")
    close(report.get("c1_clamp_clearance_mm"), c1_clearance, geom_tol, "FreeCAD report C1 clamp clearance")
    close(report.get("u1_contact_gap_mm"), u1_gap, geom_tol, "FreeCAD report U1 contact gap")
    minimum_side = min(number(value, "computed side clearance") for value in result["nominal_side_clearances_mm"].values())
    close(report.get("minimum_side_clearance_mm"), minimum_side, geom_tol, "FreeCAD report minimum side clearance")
    side_report = report.get("nominal_side_clearances_mm")
    if side_report is not None and not isinstance(side_report, dict):
        fail("FreeCAD report nominal_side_clearances_mm must be an object when provided")
    for direction, measured in result["nominal_side_clearances_mm"].items():
        if measured + geom_tol < number(req["minimum_side_clearance_mm"], "minimum side clearance"):
            fail(f"computed side clearance is insufficient at {direction}")
        if side_report is not None:
            close(side_report.get(direction), measured, geom_tol, f"FreeCAD report side clearance {direction}")
    reported_apertures = report.get("aperture_checks")
    if reported_apertures is not None:
        if not isinstance(reported_apertures, list):
            fail("FreeCAD report aperture_checks must be a list when provided")
        reported_by_ref = {str(item.get("ref")): item for item in reported_apertures if isinstance(item, dict)}
        for ref in spec["connectors"]:
            if not reported_by_ref.get(ref, {}).get("through"):
                fail(f"FreeCAD report does not record a passing through-aperture for {ref}")


BLENDER_CHECKER = r'''
import json
import math
import os
import traceback

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree


config = json.load(open(os.environ["ENGIWORLD_TASK02_BLEND_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK02_BLEND_RESULT"]


def world_bounds(objects):
    points = []
    for obj in objects:
        for corner in obj.bound_box:
            points.append(obj.matrix_world @ Vector(corner))
    if not points:
        raise RuntimeError("cannot compute empty object bounds")
    mins = [min(point[i] for point in points) for i in range(3)]
    maxs = [max(point[i] for point in points) for i in range(3)]
    return mins + maxs


def bounds_close(actual, expected, tolerance=0.5):
    return len(actual) == len(expected) and all(abs(float(a) - float(b)) <= tolerance for a, b in zip(actual, expected))


def object_bounds(obj):
    return world_bounds([obj])


def mesh_data(objects):
    vertices = []
    polygons = []
    for obj in objects:
        if obj.type != "MESH":
            continue
        offset = len(vertices)
        vertices.extend(tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices)
        polygons.extend(tuple(offset + index for index in polygon.vertices) for polygon in obj.data.polygons)
    if not vertices or not polygons:
        raise RuntimeError("cannot compare empty role geometry")
    return {"vertices": vertices, "polygons": polygons}


def geometry_mesh_data(geometry):
    return {
        "enclosure": mesh_data(geometry["enclosure"]),
        "pcb": mesh_data(geometry["pcb"]),
        **{"component_" + ref: mesh_data(objects) for ref, objects in geometry["components"].items()},
    }


def directed_surface_distance(source, target, sample_limit=5000):
    tree = BVHTree.FromPolygons(
        [Vector(value) for value in target["vertices"]],
        target["polygons"],
        all_triangles=False,
    )
    if tree is None:
        raise RuntimeError("cannot build geometry comparison BVH")
    points = list(source["vertices"])
    for polygon in source["polygons"]:
        count = float(len(polygon))
        points.append(tuple(sum(source["vertices"][index][axis] for index in polygon) / count for axis in range(3)))
    stride = max(1, int(math.ceil(len(points) / float(sample_limit))))
    maximum = 0.0
    for value in points[::stride]:
        nearest = tree.find_nearest(Vector(value))
        if nearest is None:
            raise RuntimeError("geometry comparison found no nearest surface")
        maximum = max(maximum, float(nearest[3]))
    return maximum


def compare_role_meshes(label, actual, reference, tolerance=0.5):
    if set(actual) != set(reference):
        raise RuntimeError(label + " role set differs from the FreeCAD assembly reference")
    distances = {}
    for role in reference:
        distance = max(
            directed_surface_distance(actual[role], reference[role]),
            directed_surface_distance(reference[role], actual[role]),
        )
        distances[role] = distance
        if distance > tolerance:
            raise RuntimeError(
                label + " role geometry differs from the FreeCAD assembly reference: "
                + role + " distance=" + str(distance)
            )
    return distances


def expected_board_bounds():
    sx, sy, sz = config["board_bbox_mm"]
    z0 = config["board_bottom_z_mm"]
    return [-sx / 2.0, -sy / 2.0, z0, sx / 2.0, sy / 2.0, z0 + sz]


def expected_component_bounds(item):
    sx, sy, sz = item["body_bbox_mm"]
    z0 = config["board_bottom_z_mm"] + config["board_bbox_mm"][2]
    return [item["x_mm"] - sx / 2.0, item["y_mm"] - sy / 2.0, z0,
            item["x_mm"] + sx / 2.0, item["y_mm"] + sy / 2.0, z0 + sz]


def aperture_overlay_matches(obj, expected, tolerance=0.6):
    bounds = object_bounds(obj)
    center_y = (bounds[1] + bounds[4]) / 2.0
    center_z = (bounds[2] + bounds[5]) / 2.0
    localized = (
        bounds[3] - bounds[0] <= config["enclosure_bbox_mm"][0] / 2.0
        and bounds[4] - bounds[1] <= expected["window_width_mm"] * 2.0 + tolerance
        and bounds[5] - bounds[2] <= expected["window_height_mm"] * 2.0 + tolerance
    )
    if expected["wall_direction"] == "X_MINUS":
        crosses = bounds[0] <= -config["enclosure_bbox_mm"][0] / 2.0 + tolerance and bounds[3] >= -config["enclosure_bbox_mm"][0] / 2.0 + config["wall_mm"] - tolerance
    else:
        crosses = bounds[0] <= config["enclosure_bbox_mm"][0] / 2.0 - config["wall_mm"] + tolerance and bounds[3] >= config["enclosure_bbox_mm"][0] / 2.0 - tolerance
    return (
        abs(center_y - expected["center_tangent_mm"]) <= expected["window_width_mm"] / 2.0 + tolerance
        and abs(center_z - expected["center_z_mm"]) <= expected["window_height_mm"] / 2.0 + tolerance
        and localized
        and crosses
    )


def component_item(ref):
    return next(item for item in config["components"] if item["ref"] == ref)


def feature_overlay_bounds(ref):
    item = component_item(ref)
    board_top = config["board_bottom_z_mm"] + config["board_bbox_mm"][2]
    if ref == "L1":
        radius = item["keepout_radius_mm"]
        return [
            item["x_mm"] - radius, item["y_mm"] - radius, board_top,
            item["x_mm"] + radius, item["y_mm"] + radius, config["lid_inner_z_mm"],
        ]
    if ref == "C1":
        radius = item["keepout_radius_mm"]
        body_top = board_top + item["body_bbox_mm"][2]
        return [
            item["x_mm"] - radius, item["y_mm"] - radius, body_top,
            item["x_mm"] + radius, item["y_mm"] + radius, config["lid_inner_z_mm"],
        ]
    if ref == "U1":
        size_x, size_y = config["u1_contact_pad_bbox_mm"]
        body_top = board_top + item["body_bbox_mm"][2]
        return [
            item["x_mm"] - size_x / 2.0, item["y_mm"] - size_y / 2.0, body_top,
            item["x_mm"] + size_x / 2.0, item["y_mm"] + size_y / 2.0, config["lid_inner_z_mm"],
        ]
    raise RuntimeError("unsupported critical review feature: " + ref)


def feature_overlay_matches(obj, ref, tolerance=0.6):
    bounds = object_bounds(obj)
    return bounds_close(bounds, feature_overlay_bounds(ref), tolerance)


def bounds_contained(actual, expected, tolerance=0.5):
    return all(actual[index] >= expected[index] - tolerance for index in range(3)) and all(
        actual[index] <= expected[index] + tolerance for index in range(3, 6)
    )


def find_geometry_group(objects, expected, label, tolerance=0.5):
    matches = [obj for obj in objects if bounds_contained(object_bounds(obj), expected, tolerance)]
    if not matches or not bounds_close(world_bounds(matches), expected, tolerance):
        raise RuntimeError(
            label + " geometry union cannot be identified"
            + "; expected=" + json.dumps(expected)
            + "; actual=" + json.dumps({obj.name: object_bounds(obj) for obj in objects})
        )
    return matches


def classify_base_geometry(objects, excluded_overlays=None):
    overlays = {id(obj) for obj in (excluded_overlays or [])}
    overlays.update({
        id(obj)
        for obj in objects
        if any(aperture_overlay_matches(obj, expected) for expected in config["apertures"])
        or feature_overlay_matches(obj, "L1")
        or feature_overlay_matches(obj, "C1")
    })
    physical = [obj for obj in objects if id(obj) not in overlays]
    board = find_geometry_group(physical, expected_board_bounds(), "PCB", 0.6)
    components = {
        item["ref"]: find_geometry_group(physical, expected_component_bounds(item), "component " + item["ref"], 0.3)
        for item in config["components"]
    }
    assigned = {id(obj) for obj in board}
    assigned.update(id(obj) for values in components.values() for obj in values)
    enclosure = [obj for obj in physical if id(obj) not in assigned]
    if not enclosure:
        raise RuntimeError("enclosure geometry is missing")
    expected_enclosure = [
        -config["enclosure_bbox_mm"][0] / 2.0, -config["enclosure_bbox_mm"][1] / 2.0, 0.0,
        config["enclosure_bbox_mm"][0] / 2.0, config["enclosure_bbox_mm"][1] / 2.0, config["enclosure_bbox_mm"][2],
    ]
    if not bounds_close(world_bounds(enclosure), expected_enclosure, 0.5):
        raise RuntimeError("enclosure geometry bounds mismatch")
    return {"enclosure": enclosure, "pcb": board, "components": components}


def used_materials(obj):
    values = []
    if obj.type != "MESH":
        return values
    for polygon in obj.data.polygons:
        if polygon.material_index < len(obj.material_slots):
            material = obj.material_slots[polygon.material_index].material
            if material and material not in values:
                values.append(material)
    return values


def semantic_role(value):
    token = str(value or "").lower()
    if "enclosure" in token or "package" in token or "openscad" in token:
        return "enclosure"
    if "pcb" in token or "board" in token or "kicad" in token:
        return "pcb"
    if "component" in token or "envelope" in token:
        return "component_envelope"
    if "window" in token or "aperture" in token:
        return "window_overlay"
    if "contact" in token:
        return "contact_overlay"
    if "clearance" in token:
        return "clearance_overlay"
    if "keepout" in token or "keep_out" in token:
        return "keepout_overlay"
    return ""


def role_of(obj):
    direct = obj.get("engiworld_role")
    if direct:
        role = semantic_role(direct)
        if role:
            return role
    mapping = config.get("object_roles", {})
    if isinstance(mapping, dict):
        if obj.name in mapping:
            role = semantic_role(mapping[obj.name])
            if role:
                return role
        for role, names in mapping.items():
            if isinstance(names, str) and names == obj.name:
                classified = semantic_role(role)
                if classified:
                    return classified
            if isinstance(names, list) and obj.name in names:
                classified = semantic_role(role)
                if classified:
                    return classified
    named_role = semantic_role(obj.name)
    if named_role:
        return named_role
    bounds = object_bounds(obj)
    expected_enclosure = [
        -config["enclosure_bbox_mm"][0] / 2.0, -config["enclosure_bbox_mm"][1] / 2.0, 0.0,
        config["enclosure_bbox_mm"][0] / 2.0, config["enclosure_bbox_mm"][1] / 2.0, config["enclosure_bbox_mm"][2],
    ]
    if bounds_close(bounds, expected_enclosure, 0.5):
        return "enclosure"
    if bounds_close(bounds, expected_board_bounds(), 0.6):
        return "pcb"
    if any(bounds_close(bounds, expected_component_bounds(item), 0.3) for item in config["components"]):
        return "component_envelope"
    if any(aperture_overlay_matches(obj, expected) for expected in config["apertures"]):
        return "window_overlay"
    if feature_overlay_matches(obj, "L1"):
        return "keepout_overlay"
    if feature_overlay_matches(obj, "C1"):
        return "clearance_overlay"
    if feature_overlay_matches(obj, "U1"):
        return "contact_overlay"
    return ""


def material_color(material):
    color = material.diffuse_color
    return [float(color[0]), float(color[1]), float(color[2]), float(color[3])]


def material_alpha(material):
    alpha = float(material.diffuse_color[3])
    if material.use_nodes and material.node_tree:
        node = material.node_tree.nodes.get("Principled BSDF")
        if node and node.inputs.get("Alpha"):
            alpha = min(alpha, float(node.inputs["Alpha"].default_value))
    return alpha


def dominant_material(objects):
    counts = {}
    materials = {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        for polygon in obj.data.polygons:
            if polygon.material_index >= len(obj.material_slots):
                continue
            material = obj.material_slots[polygon.material_index].material
            if material is None:
                continue
            counts[id(material)] = counts.get(id(material), 0) + 1
            materials[id(material)] = material
    if not counts:
        return None
    return materials[max(counts, key=counts.get)]


def materially_distinct(material, baseline):
    if baseline is None:
        return True
    first = material_color(material)
    second = material_color(baseline)
    rgb_distance = math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))
    return rgb_distance >= 0.25 or abs(material_alpha(material) - material_alpha(baseline)) >= 0.15


def camera_visible(scene, camera, obj):
    points = [obj.matrix_world @ polygon.center for polygon in obj.data.polygons]
    if not points:
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    stride = max(1, int(math.ceil(len(points) / 64.0)))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    camera_forward = (camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
    for point in points[::stride]:
        projected = world_to_camera_view(scene, camera, point)
        if projected.z <= 0 or not (0.0 <= projected.x <= 1.0 and 0.0 <= projected.y <= 1.0):
            continue
        if camera.data.type == "ORTHO":
            ray_origin = point - camera_forward * 10000.0
            ray_direction = camera_forward
            remaining = 10000.1
        else:
            ray_origin = camera.matrix_world.translation
            offset = point - ray_origin
            remaining = offset.length + 0.1
            ray_direction = offset.normalized()
        for _ in range(32):
            hit, location, _normal, _index, hit_object, _matrix = scene.ray_cast(
                depsgraph, ray_origin, ray_direction, distance=remaining,
            )
            if not hit or hit_object is None:
                break
            if hit_object == obj or hit_object.name == obj.name:
                return True
            materials = used_materials(hit_object) if hit_object.type == "MESH" else []
            if not materials or any(material_alpha(material) >= 0.98 for material in materials):
                break
            advance = (location - ray_origin).length + 0.001
            remaining -= advance
            if remaining <= 0.0:
                break
            ray_origin = location + ray_direction * 0.001
    return False


def materially_marked(obj, baseline):
    return (
        not obj.hide_render
        and not obj.hide_get()
        and any(materially_distinct(material, baseline) for material in used_materials(obj))
    )


def visible_review_object(obj, baseline, scene, camera):
    return materially_marked(obj, baseline) and camera_visible(scene, camera, obj)


def image_similarity(first_path, second_path):
    images = []
    try:
        for path in (first_path, second_path):
            image = bpy.data.images.load(path, check_existing=False)
            image.scale(64, 48)
            images.append([float(value) for value in image.pixels[:]])
        first, second = images
        if len(first) != len(second) or not first:
            return 0.0
        rgb_indices = [index for index in range(len(first)) if index % 4 != 3]
        error = sum(abs(first[index] - second[index]) for index in rgb_indices) / len(rgb_indices)
        return max(0.0, 1.0 - error)
    finally:
        for image in list(bpy.data.images):
            if image.filepath in {first_path, second_path}:
                bpy.data.images.remove(image)


def main():
    bpy.ops.wm.open_mainfile(filepath=config["blend_path"])
    scene = bpy.context.scene
    native_render_resolution = [
        round(scene.render.resolution_x * scene.render.resolution_percentage / 100),
        round(scene.render.resolution_y * scene.render.resolution_percentage / 100),
    ]
    camera = scene.camera
    if camera is None or camera.type != "CAMERA" or camera.data.type not in {"ORTHO", "PERSP"} or camera.hide_render:
        raise RuntimeError("scene lacks an active visible review camera")
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    grouped = {}
    for obj in meshes:
        grouped.setdefault(role_of(obj), []).append(obj)
    native_aperture_overlays = [
        obj for obj in meshes
        if any(aperture_overlay_matches(obj, expected) for expected in config["apertures"])
    ]
    native_l1_overlays = [obj for obj in meshes if feature_overlay_matches(obj, "L1")]
    native_c1_overlays = [obj for obj in meshes if feature_overlay_matches(obj, "C1")]
    native_u1_overlays = [obj for obj in meshes if feature_overlay_matches(obj, "U1")]
    native_excluded = native_aperture_overlays + native_l1_overlays + native_c1_overlays
    native_enclosure_baseline = dominant_material(meshes)
    native_excluded.extend(
        obj for obj in native_u1_overlays
        if visible_review_object(obj, native_enclosure_baseline, scene, camera)
    )
    native_geometry = classify_base_geometry(meshes, native_excluded)
    enclosure_material = dominant_material(native_geometry["enclosure"])
    if enclosure_material is None:
        raise RuntimeError("enclosure has no actually assigned material")
    warning_refs = {}
    for expected in config["apertures"]:
        matching = [obj for obj in native_aperture_overlays if aperture_overlay_matches(obj, expected)]
        warning_refs[expected["ref"]] = any(visible_review_object(obj, enclosure_material, scene, camera) for obj in matching)
    if not all(warning_refs.get(ref) for ref in config["connector_refs"]):
        raise RuntimeError("J1/J2 window overlays are missing, hidden, or lack an assigned warning material")
    critical_overlays = {
        "L1": native_l1_overlays,
        "C1": native_c1_overlays,
        "U1": native_u1_overlays,
    }
    for ref, objects in critical_overlays.items():
        if not any(visible_review_object(obj, enclosure_material, scene, camera) for obj in objects):
            raise RuntimeError(ref + " review overlay is missing, hidden, or not materially distinct")

    enclosure_materials = [material for obj in native_geometry["enclosure"] for material in used_materials(obj)]
    board_materials = [material for obj in native_geometry["pcb"] for material in used_materials(obj)]
    if not board_materials:
        raise RuntimeError("PCB has no actually assigned material")
    if {material.name for material in enclosure_materials} == {material.name for material in board_materials}:
        raise RuntimeError("PCB and enclosure are not materially distinguished")

    direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    target = Vector((0, 0, config["enclosure_bbox_mm"][2] / 2.0))
    toward = (target - camera.matrix_world.translation).normalized()
    if direction.dot(toward) < 0.75:
        raise RuntimeError("active camera is not aimed at the engineering assembly")

    blend_bounds = world_bounds(meshes)
    enclosure_bounds = world_bounds(native_geometry["enclosure"])
    pcb_bounds = world_bounds(native_geometry["pcb"])
    role_collections = {
        collection.name
        for obj in meshes
        for collection in obj.users_collection
    }
    if not role_collections:
        raise RuntimeError("native scene review objects are not linked to collections")

    aperture_checks = {}
    for expected in config["apertures"]:
        matching = [obj for obj in native_aperture_overlays if aperture_overlay_matches(obj, expected)]
        if not matching:
            aperture_checks[expected["ref"]] = False
            continue
        bounds = world_bounds(matching)
        center_y = (bounds[1] + bounds[4]) / 2.0
        center_z = (bounds[2] + bounds[5]) / 2.0
        crosses_wall = bounds[0] <= -config["enclosure_bbox_mm"][0] / 2.0 and bounds[3] >= -config["enclosure_bbox_mm"][0] / 2.0 + config["wall_mm"]
        if expected["wall_direction"] == "X_PLUS":
            crosses_wall = bounds[0] <= config["enclosure_bbox_mm"][0] / 2.0 - config["wall_mm"] and bounds[3] >= config["enclosure_bbox_mm"][0] / 2.0
        aperture_checks[expected["ref"]] = (
            abs(center_y - expected["center_tangent_mm"]) <= 0.5
            and abs(center_z - expected["center_z_mm"]) <= 0.5
            and crosses_wall
        )
    if not all(aperture_checks.values()):
        raise RuntimeError("Blender aperture overlays do not align with the real window paths")

    scene.render.resolution_x = 160
    scene.render.resolution_y = 120
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = config["rerender_path"]
    bpy.ops.render.render(write_still=True)
    render_similarity = image_similarity(config["submitted_render_path"], config["rerender_path"])

    native_mesh_count = len(meshes)
    native_role_counts = {key: len(value) for key, value in grouped.items()}
    active_camera_name = camera.name
    camera_is_orthographic = camera.data.type == "ORTHO"
    native_base_bounds = {
        "enclosure": world_bounds(native_geometry["enclosure"]),
        "pcb": world_bounds(native_geometry["pcb"]),
        **{"component_" + ref: world_bounds(objects) for ref, objects in native_geometry["components"].items()},
    }
    native_role_meshes = geometry_mesh_data(native_geometry)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=config["reference_bridge_obj_path"],
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
    )
    reference_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    reference_geometry = classify_base_geometry(reference_objects)
    reference_role_meshes = geometry_mesh_data(reference_geometry)
    native_reference_distances = compare_role_meshes(
        "native scene",
        native_role_meshes,
        reference_role_meshes,
    )

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=config["bridge_obj_path"],
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
    )
    bridge_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    bridge_geometry = classify_base_geometry(bridge_objects)
    bridge_base_bounds = {
        "enclosure": world_bounds(bridge_geometry["enclosure"]),
        "pcb": world_bounds(bridge_geometry["pcb"]),
        **{"component_" + ref: world_bounds(objects) for ref, objects in bridge_geometry["components"].items()},
    }
    bridge_reference_distances = compare_role_meshes(
        "FreeCAD bridge OBJ",
        geometry_mesh_data(bridge_geometry),
        reference_role_meshes,
    )
    for role, expected_bounds in native_base_bounds.items():
        if not bounds_close(bridge_base_bounds[role], expected_bounds, 0.5):
            raise RuntimeError("FreeCAD bridge OBJ differs from native scene role: " + role)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=config["obj_path"],
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
    )
    imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    obj_bounds = world_bounds(imported)
    review_baseline = dominant_material(imported)
    review_u1_visual_overlays = [
        obj for obj in imported
        if feature_overlay_matches(obj, "U1") and materially_marked(obj, review_baseline)
    ]
    review_geometry = classify_base_geometry(imported, review_u1_visual_overlays)
    review_enclosure_material = dominant_material(review_geometry["enclosure"])
    if review_enclosure_material is None:
        raise RuntimeError("review OBJ enclosure has no assigned material")
    review_base_bounds = {
        "enclosure": world_bounds(review_geometry["enclosure"]),
        "pcb": world_bounds(review_geometry["pcb"]),
        **{"component_" + ref: world_bounds(objects) for ref, objects in review_geometry["components"].items()},
    }
    review_reference_distances = compare_role_meshes(
        "review OBJ",
        geometry_mesh_data(review_geometry),
        reference_role_meshes,
    )
    for role, expected_bounds in native_base_bounds.items():
        if not bounds_close(review_base_bounds[role], expected_bounds, 0.5):
            raise RuntimeError("review OBJ differs from native scene role: " + role)
    warning_imports = []
    for expected in config["apertures"]:
        matches = [obj for obj in imported if aperture_overlay_matches(obj, expected)]
        visible_warning = [
            obj for obj in matches
            if materially_marked(obj, review_enclosure_material)
        ]
        if not visible_warning:
            raise RuntimeError("review OBJ lacks materially distinct aperture overlay: " + expected["ref"])
        warning_imports.extend(visible_warning)
    if len({id(obj) for obj in warning_imports}) < 2:
        raise RuntimeError("review OBJ/MTL does not retain warning material assignments")
    obj_feature_counts = {}
    for ref in ("L1", "C1", "U1"):
        matching = [
            obj for obj in imported
            if feature_overlay_matches(obj, ref) and materially_marked(obj, review_enclosure_material)
        ]
        if not matching:
            raise RuntimeError("review OBJ lacks a materially distinct " + ref + " engineering overlay")
        obj_feature_counts[ref] = len(matching)
    return {
        "mesh_object_count": native_mesh_count,
        "roles": native_role_counts,
        "warning_refs": warning_refs,
        "critical_overlay_counts": {ref: len(objects) for ref, objects in critical_overlays.items()},
        "active_camera": active_camera_name,
        "camera_orthographic": camera_is_orthographic,
        "render_similarity": render_similarity,
        "native_render_resolution": native_render_resolution,
        "blend_bounds_mm": blend_bounds,
        "enclosure_bounds_mm": enclosure_bounds,
        "pcb_bounds_mm": pcb_bounds,
        "role_collections": sorted(role_collections),
        "aperture_checks": aperture_checks,
        "native_reference_surface_distances_mm": native_reference_distances,
        "bridge_reference_surface_distances_mm": bridge_reference_distances,
        "review_reference_surface_distances_mm": review_reference_distances,
        "bridge_object_count": len(bridge_objects),
        "bridge_role_bounds_mm": bridge_base_bounds,
        "obj_object_count": len(imported),
        "obj_role_bounds_mm": review_base_bounds,
        "obj_bounds_mm": obj_bounds,
        "obj_warning_object_count": len(warning_imports),
        "obj_critical_overlay_counts": obj_feature_counts,
    }


try:
    payload = {"ok": True, "result": main()}
except Exception as exc:
    payload = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
with open(result_path, "w") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
'''


def run_blender_checker(
    runtime: Path,
    spec: dict[str, Any],
    apertures: list[dict[str, Any]],
    scene_report: dict[str, Any],
) -> dict[str, Any]:
    blender = resolve_executable(
        "blender",
        ["/home/user/Applications/blender-*/blender"],
    )
    req = spec["requirements"]
    board = spec["board"]
    components = []
    for ref, footprint in board["footprints"].items():
        if ref.startswith("MH"):
            continue
        if ref in spec["connectors"]:
            body = [
                number(spec["connectors"][ref]["body_x_mm"], f"{ref} body x"),
                number(spec["connectors"][ref]["body_y_mm"], f"{ref} body y"),
                number(footprint["height_mm"], f"{ref} body z"),
            ]
        else:
            body = [number(value, f"{ref} body") for value in req["component_bodies"][ref]["bbox_mm"]]
        components.append(
            {
                "ref": ref,
                "x_mm": number(footprint["x_mm"], f"{ref} x"),
                "y_mm": number(footprint["y_mm"], f"{ref} y"),
                "keepout_radius_mm": number(footprint["keepout_radius_mm"], f"{ref} keepout radius"),
                "body_bbox_mm": body,
            }
        )
    config = {
        "blend_path": str(DESKTOP / "04_blender_review.blend"),
        "reference_bridge_obj_path": str(runtime / "assembly_reference.obj"),
        "bridge_obj_path": str(DESKTOP / "03_freecad_assembly.obj"),
        "obj_path": str(DESKTOP / "04_blender_review.obj"),
        "submitted_render_path": str(DESKTOP / "04_blender_review.png"),
        "rerender_path": str(runtime / "blender_rerender.png"),
        "object_roles": scene_report.get("object_roles", {}),
        "component_refs": [ref for ref in spec["board"]["footprints"] if not ref.startswith("MH")],
        "connector_refs": list(spec["connectors"]),
        "board_bbox_mm": [number(value, "board bbox") for value in board["bbox_mm"]],
        "board_bottom_z_mm": number(req["board_bottom_z_mm"], "board bottom z"),
        "components": components,
        "enclosure_bbox_mm": [number(value, "enclosure bbox") for value in req["expected_enclosure_bbox_mm"]],
        "lid_inner_z_mm": number(req["expected_enclosure_bbox_mm"][2], "enclosure z") - number(req["lid_thickness_mm"], "lid thickness"),
        "wall_mm": number(req["wall_mm"], "wall_mm"),
        "u1_contact_pad_bbox_mm": [number(value, "U1 contact pad bbox") for value in req["clamp_contact_pad_bbox_mm"]],
        "apertures": apertures,
    }
    config_path = runtime / "blend_config.json"
    result_path = runtime / "blend_result.json"
    checker_path = runtime / "blender_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(BLENDER_CHECKER, encoding="utf-8")
    old_config = os.environ.get("ENGIWORLD_TASK02_BLEND_CONFIG")
    old_result = os.environ.get("ENGIWORLD_TASK02_BLEND_RESULT")
    os.environ["ENGIWORLD_TASK02_BLEND_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK02_BLEND_RESULT"] = str(result_path)
    try:
        run_command(
            [blender, "--background", "--factory-startup", "--disable-autoexec", "--python", str(checker_path)],
            cwd=runtime,
            timeout=120,
            label="Blender native-scene and OBJ checker",
        )
    finally:
        for key, old in (("ENGIWORLD_TASK02_BLEND_CONFIG", old_config), ("ENGIWORLD_TASK02_BLEND_RESULT", old_result)):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
    payload = json_file(result_path)
    if not payload.get("ok"):
        fail(f"Blender checker rejected artifacts: {payload.get('error')}")
    result = payload.get("result")
    if not isinstance(result, dict):
        fail("Blender checker returned no result")
    return result


def check_blender_report(
    spec: dict[str, Any],
    cad_result: dict[str, Any],
    result: dict[str, Any],
    report: dict[str, Any],
    submitted_png_size: tuple[int, int],
) -> None:
    if report.get("decision") is not None and normalized(report.get("decision")) not in {"PASS", "PASSED"}:
        fail("Blender scene report decision must be pass")
    if report.get("inputs") is not None:
        inputs = {Path(str(value)).name for value in report.get("inputs", [])}
        if not {"03_freecad_assembly.obj", "03_freecad_clearance_report.json"}.issubset(inputs):
            fail("Blender scene report does not record both FreeCAD inputs")
    if report.get("native_scene") is not None and Path(str(report.get("native_scene"))).name != "04_blender_review.blend":
        fail("Blender scene report native_scene mismatch")
    if report.get("review_obj") is not None and Path(str(report.get("review_obj"))).name != "04_blender_review.obj":
        fail("Blender scene report review_obj mismatch")
    if report.get("review_mtl") is not None and Path(str(report.get("review_mtl"))).name != "04_blender_review.mtl":
        fail("Blender scene report review_mtl mismatch")
    if report.get("render") is not None and Path(str(report.get("render"))).name != "04_blender_review.png":
        fail("Blender scene report render mismatch")
    if report.get("visible_keepouts") is not None:
        visible = {str(value) for value in report.get("visible_keepouts", [])}
        if not {"J1", "J2", "L1", "C1", "U1"}.issubset(visible):
            fail("Blender scene report does not record every required engineering overlay")
    if report.get("active_camera") is not None and str(report.get("active_camera")) != str(result.get("active_camera")):
        fail("Blender scene report active camera does not match the native scene")
    close_vector(result.get("blend_bounds_mm"), result.get("obj_bounds_mm"), 0.5, "Blender native/OBJ review bounds")
    enclosure_bounds = result.get("enclosure_bounds_mm")
    if not isinstance(enclosure_bounds, list) or len(enclosure_bounds) != 6:
        fail("Blender checker did not return enclosure bounds")
    enclosure_dims = [enclosure_bounds[3] - enclosure_bounds[0], enclosure_bounds[4] - enclosure_bounds[1], enclosure_bounds[5] - enclosure_bounds[2]]
    close_vector(enclosure_dims, spec["requirements"]["expected_enclosure_bbox_mm"], 0.5, "Blender enclosure bbox")
    for ref in ("L1", "C1", "U1"):
        if int(result.get("critical_overlay_counts", {}).get(ref, 0)) < 1:
            fail(f"Blender native scene lacks a visible {ref} engineering overlay")
        if int(result.get("obj_critical_overlay_counts", {}).get(ref, 0)) < 1:
            fail(f"Blender review OBJ lacks a visible {ref} engineering overlay")
    for field, expected in (
        ("visible_c1_clearance_mm", cad_result["c1_clamp_clearance_mm"]),
        ("visible_l1_intersection_mm3", cad_result["l1_keepout_intersection_mm3"]),
        ("visible_u1_contact_gap_mm", cad_result["u1_contact_gap_mm"]),
    ):
        if report.get(field) is not None:
            close(report.get(field), expected, 0.1, f"Blender report {field}")
    similarity = number(result.get("render_similarity"), "Blender submitted/rerendered image similarity")
    if similarity < MIN_RENDER_SIMILARITY:
        fail(
            f"Blender review PNG does not match the native scene rerender: "
            f"similarity {similarity:.4f} < {MIN_RENDER_SIMILARITY:.2f}"
        )
    close_vector(
        list(submitted_png_size),
        result.get("native_render_resolution"),
        0,
        "Blender submitted PNG/native scene render resolution",
    )


def check_png(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        fail("04_blender_review.png is not a PNG file")
    cursor = 8
    width = height = 0
    compressed = bytearray()
    while cursor + 12 <= len(data):
        length = struct.unpack(">I", data[cursor : cursor + 4])[0]
        kind = data[cursor + 4 : cursor + 8]
        payload = data[cursor + 8 : cursor + 8 + length]
        cursor += 12 + length
        if kind == b"IHDR" and len(payload) >= 8:
            width, height = struct.unpack(">II", payload[:8])
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if width < 320 or height < 240 or width > 8192 or height > 8192 or not compressed:
        fail(f"Blender review PNG is too small or malformed: {width}x{height}")
    if len(compressed) > 100 * 1024 * 1024:
        fail("Blender review PNG compressed payload is too large")
    try:
        raw = zlib.decompress(bytes(compressed))
    except Exception as exc:
        fail(f"Blender review PNG pixel data cannot be decoded: {exc}")
    if len(raw) < width * height or len(set(raw)) < 16:
        fail("Blender review PNG appears blank or nearly uniform")
    return width, height


def check_release_chain(spec: dict[str, Any], cad_result: dict[str, Any], scene_report: dict[str, Any]) -> None:
    log = json_file(DESKTOP / "toolchain_invocation_log.json")
    commands = value_of(log, "commands")
    if not isinstance(commands, list) or len(commands) < 5:
        fail("toolchain log must contain the handoff preparation and four software stages")

    def artifact_names(value: Any, label: str) -> set[str]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            fail(f"{label} must be a list or string")
        return {Path(str(item)).name for item in value}

    def entry_names(entry: dict[str, Any], key: str) -> set[str]:
        return artifact_names(value_of(entry, key, []), f"recorded {key}")

    def outputs_are_direct_desktop(entry: dict[str, Any]) -> bool:
        try:
            cwd = Path(str(entry.get("cwd", ""))).resolve()
        except Exception:
            return False
        if cwd != PRODUCTIVE_DESKTOP:
            return False
        values = value_of(entry, "outputs", [])
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list) or not values:
            return False
        return all(
            (Path(str(value)).resolve().parent == PRODUCTIVE_DESKTOP if Path(str(value)).is_absolute() else Path(str(value)).parent == Path("."))
            for value in values
        )

    def explicit_pass(value: Any) -> bool:
        return value is True or (isinstance(value, str) and normalized(value) in {"PASS", "PASSED", "TRUE", "OK"})

    def require_recorded_execution(
        entry: dict[str, Any],
        *,
        expected_inputs: set[str],
        expected_outputs: set[str],
        software: str | None,
        trusted_input_files: dict[str, Path] | None = None,
    ) -> str:
        if type(entry.get("exit_code")) is not int or entry["exit_code"] != 0:
            fail(f"recorded {entry.get('stage', 'stage')} execution did not exit successfully")
        try:
            started = datetime.fromisoformat(str(entry["started_at_utc"]).replace("Z", "+00:00"))
            finished = datetime.fromisoformat(str(entry["finished_at_utc"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            fail(f"recorded {entry.get('stage', 'stage')} execution lacks valid timestamps")
        if started.tzinfo is None or finished.tzinfo is None or finished < started:
            fail(f"recorded {entry.get('stage', 'stage')} execution timestamps are invalid")
        argv = entry.get("argv")
        command = str(value_of(entry, "command", ""))
        if not isinstance(argv, list) or not argv or not all(isinstance(token, str) and token for token in argv):
            fail(f"recorded {entry.get('stage', 'stage')} execution lacks argv")
        try:
            parsed_command = shlex.split(command)
        except ValueError:
            fail(f"recorded {entry.get('stage', 'stage')} command cannot be parsed")
        if parsed_command != argv:
            fail(f"recorded {entry.get('stage', 'stage')} command does not match argv")
        if software is not None:
            executable = Path(argv[0]).name.lower()
            expected_token = {"KiCad": "kicad", "OpenSCAD": "openscad", "FreeCAD": "freecad", "Blender": "blender"}[software]
            if expected_token not in executable:
                fail(f"recorded {software} stage does not invoke the required software executable")
        if not outputs_are_direct_desktop(entry):
            fail(f"recorded {entry.get('stage', 'stage')} outputs were not generated directly on the desktop")
        inputs = entry_names(entry, "inputs")
        outputs = entry_names(entry, "outputs")
        if not expected_inputs.issubset(inputs) or not expected_outputs.issubset(outputs):
            fail(f"recorded {entry.get('stage', 'stage')} execution has incomplete inputs or outputs")
        input_hashes = entry.get("input_sha256")
        output_hashes = entry.get("output_sha256")
        if not isinstance(input_hashes, dict) or not expected_inputs.issubset(input_hashes):
            fail(f"recorded {entry.get('stage', 'stage')} execution lacks required input hashes")
        if not isinstance(output_hashes, dict) or not expected_outputs.issubset(output_hashes):
            fail(f"recorded {entry.get('stage', 'stage')} execution lacks required output hashes")
        trusted_input_files = trusted_input_files or {}
        for name in expected_inputs:
            artifact = trusted_input_files.get(name, DESKTOP / name)
            if not artifact.is_file() or input_hashes.get(name) != sha256(artifact):
                fail(f"recorded {entry.get('stage', 'stage')} input hash mismatch for {name}")
        for name in expected_outputs:
            artifact = DESKTOP / name
            if not artifact.is_file() or output_hashes.get(name) != sha256(artifact):
                fail(f"recorded {entry.get('stage', 'stage')} output hash mismatch for {name}")
        version = str(value_of(entry, "version", "")).strip()
        if software is not None and not version_matches(software, version):
            fail(f"recorded {software} stage has the wrong software version")
        return version

    def find_valid_entry(
        *,
        expected_inputs: set[str],
        expected_outputs: set[str],
        software: str | None,
        start_index: int = 0,
        trusted_input_files: dict[str, Path] | None = None,
    ) -> tuple[int, dict[str, Any], str]:
        for index in range(start_index, len(commands)):
            entry = commands[index]
            if not isinstance(entry, dict):
                continue
            try:
                if not expected_inputs.issubset(entry_names(entry, "inputs")):
                    continue
                if not expected_outputs.issubset(entry_names(entry, "outputs")):
                    continue
                version = require_recorded_execution(
                    entry,
                    expected_inputs=expected_inputs,
                    expected_outputs=expected_outputs,
                    software=software,
                    trusted_input_files=trusted_input_files,
                )
            except EvaluationError:
                continue
            return index, entry, version
        label = software or "handoff preparation"
        fail(f"toolchain log lacks a valid recorded {label} execution")

    trusted_paths = trusted_input_paths()
    preparation_inputs = {
        "board_input.kicad_pcb", "mechanical_requirements.json",
        "connector_keepouts.csv", "enclosure_seed.scad",
    }
    preparation_outputs = {
        "01_kicad_board.kicad_pcb", "01_kicad_export.json",
        "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad",
        "02_openscad_enclosure.scad", "02_openscad_parameters.json",
    }
    preparation_index, _preparation, _ = find_valid_entry(
        expected_inputs=preparation_inputs,
        expected_outputs=preparation_outputs,
        software=None,
        trusted_input_files={
            "board_input.kicad_pcb": trusted_paths["board"],
            "mechanical_requirements.json": trusted_paths["requirements"],
            "connector_keepouts.csv": trusted_paths["connectors"],
            "enclosure_seed.scad": trusted_paths["seed"],
        },
    )
    expected_command_inputs = {
        "KiCad": {"01_kicad_board.kicad_pcb"},
        "OpenSCAD": {"01_kicad_parameters.scad", "02_openscad_enclosure.scad"},
        "FreeCAD": {"01_kicad_board.step", "02_openscad_enclosure.stl", "02_openscad_parameters.json"},
        "Blender": {"03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
    }
    expected_command_outputs = {
        "KiCad": {"01_kicad_board.step"},
        "OpenSCAD": {"02_openscad_enclosure.stl"},
        "FreeCAD": {"03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
        "Blender": {"04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"},
    }
    kicad_index, _kicad_entry, kicad_version = find_valid_entry(
        expected_inputs=expected_command_inputs["KiCad"],
        expected_outputs=expected_command_outputs["KiCad"],
        software="KiCad",
    )
    previous_index = max(preparation_index, kicad_index)
    stage_versions = {"KiCad": kicad_version}
    for software in SOFTWARE_SEQUENCE[1:]:
        previous_index, _entry, stage_versions[software] = find_valid_entry(
            expected_inputs=expected_command_inputs[software],
            expected_outputs=expected_command_outputs[software],
            software=software,
            start_index=previous_index + 1,
        )

    package = json_file(DESKTOP / "final_release_package.json")
    if normalized(value_of(package, "release_decision")) not in {"PASS", "PASSED"}:
        fail("final release package decision must be pass")
    if package.get("software_sequence") is not None and [normalized(value) for value in package.get("software_sequence", [])] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("final release package software sequence mismatch")
    listed = artifact_names(value_of(package, "required_artifacts", []), "final required_artifacts")
    if not set(REQUIRED_ARTIFACTS).issubset(listed):
        fail("final release package required_artifacts is incomplete")
    hashes = package.get("artifact_sha256")
    hashed_artifacts = set(REQUIRED_ARTIFACTS) - {"final_release_package.json"}
    if not isinstance(hashes, dict) or not hashed_artifacts.issubset(hashes):
        fail("final release package artifact_sha256 is incomplete")
    for name in hashed_artifacts:
        artifact = DESKTOP / name
        if hashes.get(name) != sha256(artifact):
            fail(f"final release package hash mismatch for {artifact.name}")
    checks = package.get("checks")
    if (
        not isinstance(checks, dict)
        or not EXPECTED_RELEASE_CHECKS.issubset(checks)
        or not all(explicit_pass(checks[key]) for key in EXPECTED_RELEASE_CHECKS)
    ):
        fail("final release package contains a failed release check")
    metrics = package.get("key_metrics")
    required_metrics = {
        "board_bbox_mm", "c1_clamp_clearance_mm", "enclosure_bbox_mm",
        "enclosure_volume_mm3", "estimated_shell_mass_g", "interference_volume_mm3",
        "l1_keepout_intersection_mm3", "side_clearances_mm", "u1_contact_gap_mm",
    }
    if not isinstance(metrics, dict) or not required_metrics.issubset(metrics):
        fail("final release package key_metrics is incomplete")
    close_vector(metrics["board_bbox_mm"], spec["board"]["bbox_mm"], 0.05, "release package board bbox")
    close_vector(metrics["enclosure_bbox_mm"], spec["requirements"]["expected_enclosure_bbox_mm"], 0.2, "release package enclosure bbox")
    metric_contract = {
        "enclosure_volume_mm3": (cad_result["enclosure_volume_mm3"], max(2.0, cad_result["enclosure_volume_mm3"] * 0.01)),
        "estimated_shell_mass_g": (cad_result["estimated_shell_mass_g"], max(0.05, cad_result["estimated_shell_mass_g"] * 0.01)),
        "interference_volume_mm3": (cad_result["interference_volume_mm3"], 0.1),
        "c1_clamp_clearance_mm": (cad_result["c1_clamp_clearance_mm"], 0.1),
        "l1_keepout_intersection_mm3": (cad_result["l1_keepout_intersection_mm3"], 0.1),
        "u1_contact_gap_mm": (cad_result["u1_contact_gap_mm"], 0.1),
    }
    for key, (expected, tolerance) in metric_contract.items():
        close(metrics[key], expected, tolerance, f"release package {key}")
    side_metrics = metrics["side_clearances_mm"]
    if not isinstance(side_metrics, dict) or set(side_metrics) != set(cad_result["nominal_side_clearances_mm"]):
        fail("release package side_clearances_mm is incomplete")
    for direction, expected in cad_result["nominal_side_clearances_mm"].items():
        close(side_metrics[direction], expected, 0.1, f"release package side clearance {direction}")
    package_versions = package.get("tool_versions")
    if not isinstance(package_versions, dict) or set(SOFTWARE_SEQUENCE) - set(package_versions):
        fail("final release package tool_versions is incomplete")
    for software in SOFTWARE_SEQUENCE:
        package_version = str(package_versions[software]).strip()
        if not version_matches(software, package_version) or package_version != stage_versions[software]:
            fail(f"final release package {software} version does not match the recorded stage")


def main() -> bool:
    check_required_files()
    trusted = trusted_input_paths()
    spec = build_spec(trusted)
    check_answer_board(spec)
    export, _map_rows = check_kicad_map_and_export(spec)
    apertures = expected_apertures(spec)
    check_openscad_handoff(spec, apertures)
    freecad_report = json_file(DESKTOP / "03_freecad_clearance_report.json")
    scene_report = json_file(DESKTOP / "04_blender_scene_report.json")

    with tempfile.TemporaryDirectory(prefix="engiworld_task02_eval_") as temp_dir:
        runtime = Path(temp_dir)
        rerendered_board_step = runtime / "kicad_board_rerender.step"
        rerendered_stl = runtime / "openscad_rerender.stl"
        run_kicad_export(DESKTOP / "01_kicad_board.kicad_pcb", rerendered_board_step, runtime)
        openscad = resolve_executable("openscad", ["/usr/bin/openscad"])
        run_command(
            [openscad, "-o", str(rerendered_stl), str(DESKTOP / "02_openscad_enclosure.scad")],
            cwd=runtime,
            timeout=120,
            label="OpenSCAD enclosure rerender",
        )
        if not rerendered_stl.is_file() or rerendered_stl.stat().st_size < 1000:
            fail("OpenSCAD rerender did not produce a substantial STL")
        submitted_mesh = load_mesh_metrics(DESKTOP / "02_openscad_enclosure.stl")
        rerendered_mesh = load_mesh_metrics(rerendered_stl)
        expected_bbox = [number(value, "enclosure bbox") for value in spec["requirements"]["expected_enclosure_bbox_mm"]]
        compare_meshes(submitted_mesh, rerendered_mesh, expected_bbox)
        cad_result = run_freecad_checker(
            runtime,
            spec,
            export,
            apertures,
            rerendered_board_step,
            rerendered_stl,
            freecad_report,
        )
        check_cad_result(spec, export, cad_result, freecad_report)
        blender_result = run_blender_checker(runtime, spec, apertures, scene_report)
        submitted_png_size = check_png(DESKTOP / "04_blender_review.png")
        check_blender_report(spec, cad_result, blender_result, scene_report, submitted_png_size)

    check_release_chain(spec, cad_result, scene_report)
    return True


if __name__ == "__main__":
    detail_path = DESKTOP / "eval_detail.txt"
    try:
        passed = main()
        detail = "PASS: task-02 artifacts satisfy the trusted semantic and geometry contract.\n"
    except Exception as exc:
        passed = False
        detail = f"FAIL: {type(exc).__name__}: {exc}\n"
    try:
        detail_path.write_text(detail, encoding="utf-8")
    except Exception:
        pass
    if not passed:
        print(detail.rstrip(), file=sys.stderr)
    print("True" if passed else "False")
