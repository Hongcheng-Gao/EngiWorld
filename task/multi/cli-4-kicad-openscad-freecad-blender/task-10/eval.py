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
MIN_RENDER_SIMILARITY = 0.95
OCC_BOOLEAN_VOLUME_SLACK_MM3 = 0.0001
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
    "01_kicad_board.kicad_pcb": 800,
    "01_kicad_board.step": 500,
    "01_kicad_export.json": 300,
    "01_kicad_mechanical_map.csv": 300,
    "01_kicad_parameters.scad": 500,
    "02_openscad_enclosure.scad": 500,
    "02_openscad_enclosure.stl": 1000,
    "02_openscad_parameters.json": 500,
    "03_freecad_assembly.step": 1000,
    "03_freecad_assembly.obj": 1000,
    "03_freecad_clearance_report.json": 800,
    "04_blender_review.blend": 1000,
    "04_blender_review.obj": 1000,
    "04_blender_review.mtl": 100,
    "04_blender_review.png": 1000,
    "04_blender_scene_report.json": 500,
    "toolchain_invocation_log.json": 500,
    "final_release_package.json": 800,
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
        fail(f"{label} is not numeric: {value!r}")
    if not math.isfinite(result):
        fail(f"{label} is not finite")
    return result


def close(actual: Any, expected: Any, tolerance: float, label: str) -> None:
    got = number(actual, label)
    want = number(expected, label)
    if abs(got - want) > tolerance:
        fail(f"{label}: expected {want} +/- {tolerance}, got {got}")


def close_vector(actual: Any, expected: Any, tolerance: float, label: str) -> None:
    if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
        fail(f"{label}: expected {len(expected)} values, got {actual!r}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        close(got, want, tolerance, f"{label}[{index}]")


def normalized(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def version_matches(software: str, value: Any) -> bool:
    pattern = EXPECTED_VERSION_PATTERNS.get(software)
    return pattern is not None and pattern.search(str(value or "")) is not None


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
    override = os.environ.get("ENGIWORLD_TASK10_SPEC_DIR")
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
            "board": DESKTOP / "_eval_task10_board_input.kicad_pcb",
            "requirements": DESKTOP / "_eval_task10_mechanical_requirements.json",
            "connectors": DESKTOP / "_eval_task10_connector_keepouts.csv",
            "seed": DESKTOP / "_eval_task10_enclosure_seed.scad",
            "notes": DESKTOP / "_eval_task10_handoff_notes.md",
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


def read_connectors(path: Path) -> dict[str, dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        fail(f"cannot parse trusted connector CSV: {exc}")
    required = {
        "ref", "kind", "access_type", "direction", "finished_width_mm",
        "finished_height_mm", "finished_diameter_mm", "vertical_margin_mm",
        "cutter_x_min_mm", "cutter_y_min_mm", "cutter_z_min_mm",
        "cutter_x_max_mm", "cutter_y_max_mm", "cutter_z_max_mm",
        "path_x_min_mm", "path_y_min_mm", "path_z_min_mm",
        "path_x_max_mm", "path_y_max_mm", "path_z_max_mm",
    }
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        if not required.issubset(row):
            fail("trusted connector CSV lacks required columns")
        ref = str(row["ref"]).strip()
        if not ref or ref in result:
            fail(f"trusted connector CSV has invalid or duplicate ref {ref!r}")
        result[ref] = row
    expected_semantics = {
        "A1": ("reserved_volume", "Z_PLUS"),
        "J1": ("side_window", "X_PLUS"),
        "TP1": ("top_bore", "Z_PLUS"),
    }
    if set(result) != set(expected_semantics):
        fail("trusted connector CSV must define exactly A1, J1, and TP1")
    for ref, (access_type, direction) in expected_semantics.items():
        row = result[ref]
        if normalized(row.get("access_type")) != normalized(access_type) or normalized(row.get("direction")) != normalized(direction):
            fail(f"trusted connector {ref} must be {direction} {access_type}")
    return result


def build_spec(paths: dict[str, Path]) -> dict[str, Any]:
    board = parse_board(paths["board"])
    req = json_file(paths["requirements"])
    connectors = read_connectors(paths["connectors"])
    if int(req.get("schema_version", 0)) != 2:
        fail("trusted mechanical requirements schema_version must be 2")
    required_fields = {
        "access_center_tolerance_mm", "access_overcut_mm", "axis_tolerance_mm",
        "base_thickness_mm", "board_bottom_z_mm", "component_bodies",
        "enclosure_material_density_g_cm3", "expected_enclosure_bbox_mm",
        "geometry_tolerance_mm", "interference_volume_tolerance_mm3",
        "inner_cavity_xy_bounds_mm",
        "lid_inner_z_mm", "lid_separation_mm", "lid_thickness_mm",
        "antenna_keepout", "mass_report_relative_tolerance", "minimum_access_guard_mm",
        "minimum_side_clearance_mm", "minimum_top_clearance_mm",
        "mount_hole_diameter_mm", "standoff_bore_cutter_z_bounds_mm",
        "standoff_bore_diameter_mm", "standoff_bore_overcut_mm",
        "standoff_height_mm", "standoff_outer_diameter_mm",
        "tray_outer_top_z_mm", "wall_mm",
    }
    missing = sorted(required_fields - set(req))
    if missing:
        fail("trusted mechanical requirements lack: " + ", ".join(missing))
    enclosure = [number(value, "expected enclosure bbox") for value in req["expected_enclosure_bbox_mm"]]
    if len(enclosure) != 3 or min(enclosure) <= 0:
        fail("trusted expected_enclosure_bbox_mm must contain three positive values")
    tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    wall = number(req["wall_mm"], "wall thickness")
    expected_cavity = [
        -enclosure[0] / 2.0 + wall, -enclosure[1] / 2.0 + wall,
        enclosure[0] / 2.0 - wall, enclosure[1] / 2.0 - wall,
    ]
    close_vector(req["inner_cavity_xy_bounds_mm"], expected_cavity, tol, "trusted inner cavity")
    close(req["tray_outer_top_z_mm"], number(req["lid_inner_z_mm"], "lid inner") - number(req["lid_separation_mm"], "lid separation"), tol, "tray/lid separation")
    close(number(req["lid_inner_z_mm"], "lid inner") + number(req["lid_thickness_mm"], "lid thickness"), enclosure[2], tol, "lid outer top")
    close(number(req["base_thickness_mm"], "base thickness") + number(req["standoff_height_mm"], "standoff height"), req["board_bottom_z_mm"], tol, "standoff installed height")
    component_refs = {"A1", "U1", "J1", "BT1", "TP1"}
    expected_refs = component_refs | {"MH1", "MH2", "MH3", "MH4"}
    if set(board["footprints"]) != expected_refs:
        fail(f"trusted KiCad board refs mismatch: expected {sorted(expected_refs)}, got {sorted(board['footprints'])}")
    for ref in ("MH1", "MH2", "MH3", "MH4"):
        close(req["mount_hole_diameter_mm"], board["footprints"][ref]["hole_diameter_mm"], number(req["axis_tolerance_mm"], "axis tolerance"), f"trusted {ref} diameter")
    expected_bore_z = [
        number(req["base_thickness_mm"], "base thickness") - number(req["standoff_bore_overcut_mm"], "standoff bore overcut"),
        number(req["board_bottom_z_mm"], "board bottom") + number(req["standoff_bore_overcut_mm"], "standoff bore overcut"),
    ]
    close_vector(req["standoff_bore_cutter_z_bounds_mm"], expected_bore_z, tol, "trusted standoff bore cutter z")
    for ref, connector in connectors.items():
        footprint = board["footprints"].get(ref)
        if footprint is None:
            fail(f"trusted access {ref} is absent from the KiCad board")
        if normalized(connector.get("kind")) != normalized(footprint["kind"]):
            fail(f"trusted connector {ref} kind does not match KiCad")
        overcut = number(req["access_overcut_mm"], "access overcut")
        if ref == "J1":
            expected_height = number(footprint["height_mm"], f"{ref} height") + 2.0 * number(connector["vertical_margin_mm"], f"{ref} vertical margin")
            close(connector["finished_height_mm"], expected_height, tol, f"{ref} finished height")
            width = number(connector["finished_width_mm"], f"{ref} finished width")
            body_x, body_y, _body_z = [number(value, f"{ref} body") for value in req["component_bodies"][ref]["bbox_mm"]]
            close(width, body_y, tol, f"trusted {ref} side-window width")
            center_z = number(req["board_bottom_z_mm"], "board bottom") + board["thickness_mm"] + footprint["height_mm"] / 2.0
            z_min, z_max = center_z - expected_height / 2.0, center_z + expected_height / 2.0
            y_min, y_max = footprint["y_mm"] - width / 2.0, footprint["y_mm"] + width / 2.0
            if normalized(connector["direction"]) == normalized("X_MINUS"):
                expected_bounds = [-enclosure[0] / 2.0 - overcut, y_min, z_min, expected_cavity[0] + overcut, y_max, z_max]
                expected_path = [-enclosure[0] / 2.0 - overcut, y_min, z_min, footprint["x_mm"] + body_x / 2.0, y_max, z_max]
            elif normalized(connector["direction"]) == normalized("X_PLUS"):
                expected_bounds = [expected_cavity[2] - overcut, y_min, z_min, enclosure[0] / 2.0 + overcut, y_max, z_max]
                expected_path = [footprint["x_mm"] - body_x / 2.0, y_min, z_min, enclosure[0] / 2.0 + overcut, y_max, z_max]
            else:
                fail(f"trusted {ref} side-window direction must be X_MINUS or X_PLUS")
        elif ref == "TP1":
            diameter = number(connector["finished_diameter_mm"], f"{ref} finished diameter")
            close(diameter, 2.0 * footprint["keepout_radius_mm"], tol, f"trusted {ref} bore diameter")
            radius = diameter / 2.0
            expected_bounds = [
                footprint["x_mm"] - radius, footprint["y_mm"] - radius,
                number(req["lid_inner_z_mm"], "lid inner") - overcut,
                footprint["x_mm"] + radius, footprint["y_mm"] + radius,
                enclosure[2] + overcut,
            ]
            expected_path = [
                footprint["x_mm"] - radius, footprint["y_mm"] - radius,
                number(req["board_bottom_z_mm"], "board bottom") + board["thickness_mm"] + footprint["height_mm"],
                footprint["x_mm"] + radius, footprint["y_mm"] + radius,
                enclosure[2] + overcut,
            ]
        else:
            keepout = req["antenna_keepout"]
            diameter = number(connector["finished_diameter_mm"], "A1 reserved diameter")
            close(diameter, 2.0 * footprint["keepout_radius_mm"], tol, "trusted A1 reserved diameter")
            expected_path = [number(value, "antenna bbox") for value in keepout["bbox_mm"]]
            actual_path = [number(connector[field], f"{ref} {field}") for field in ("path_x_min_mm", "path_y_min_mm", "path_z_min_mm", "path_x_max_mm", "path_y_max_mm", "path_z_max_mm")]
            close_vector(actual_path, expected_path, tol, f"trusted {ref} reserved-volume bounds")
            if any(str(connector.get(field, "")).strip() for field in ("cutter_x_min_mm", "cutter_y_min_mm", "cutter_z_min_mm", "cutter_x_max_mm", "cutter_y_max_mm", "cutter_z_max_mm")):
                fail("trusted A1 reserved volume must not define an exterior cutter")
            continue
        actual_bounds = [number(connector[field], f"{ref} {field}") for field in ("cutter_x_min_mm", "cutter_y_min_mm", "cutter_z_min_mm", "cutter_x_max_mm", "cutter_y_max_mm", "cutter_z_max_mm")]
        close_vector(actual_bounds, expected_bounds, tol, f"trusted {ref} cutter bounds")
        actual_path = [number(connector[field], f"{ref} {field}") for field in ("path_x_min_mm", "path_y_min_mm", "path_z_min_mm", "path_x_max_mm", "path_y_max_mm", "path_z_max_mm")]
        close_vector(actual_path, expected_path, tol, f"trusted {ref} path bounds")
    components = req.get("component_bodies")
    if not isinstance(components, dict):
        fail("trusted requirements component_bodies must be an object")
    if set(components) != component_refs:
        fail("trusted component_bodies must define exactly A1, U1, J1, BT1, and TP1")
    for ref, body in components.items():
        expected_shape = "cylinder" if ref in {"BT1", "TP1"} else "box"
        if not isinstance(body, dict) or normalized(body.get("shape")) != normalized(expected_shape):
            fail(f"trusted component body {ref} must be a {expected_shape}")
        bbox = body.get("bbox_mm")
        if not isinstance(bbox, list) or len(bbox) != 3 or min(number(value, f"{ref} body") for value in bbox) <= 0:
            fail(f"trusted component body {ref} has invalid bbox_mm")
        close(bbox[2], board["footprints"][ref]["height_mm"], tol, f"trusted {ref} body height")
    board_top = number(req["board_bottom_z_mm"], "board bottom") + board["thickness_mm"]
    keepout = req["antenna_keepout"]
    if normalized(keepout.get("shape")) != normalized("cylinder") or normalized(keepout.get("view_direction")) != normalized("Z_PLUS"):
        fail("trusted A1 keepout must be a finite Z_PLUS cylinder")
    if keepout.get("ref") != "A1" or keepout.get("exterior_opening_required") is not False:
        fail("trusted A1 keepout must be an internal reserved volume, not an exterior opening")
    expected_carrier_roles = {normalized(value) for value in ("tray", "lid", "standoff", "extra_structure")}
    if {normalized(value) for value in keepout.get("carrier_material_roles", [])} != expected_carrier_roles:
        fail("trusted A1 keepout carrier roles are incomplete")
    radius = board["footprints"]["A1"]["keepout_radius_mm"]
    z_bounds = [board_top + board["footprints"]["A1"]["height_mm"], number(req["lid_inner_z_mm"], "lid inner")]
    expected_keepout_bbox = [
        board["footprints"]["A1"]["x_mm"] - radius,
        board["footprints"]["A1"]["y_mm"] - radius,
        z_bounds[0],
        board["footprints"]["A1"]["x_mm"] + radius,
        board["footprints"]["A1"]["y_mm"] + radius,
        z_bounds[1],
    ]
    close_vector(keepout.get("z_bounds_mm"), z_bounds, tol, "trusted A1 keepout z bounds")
    close_vector(keepout.get("bbox_mm"), expected_keepout_bbox, tol, "trusted A1 keepout bbox")
    cavity = [number(value, "cavity bound") for value in req["inner_cavity_xy_bounds_mm"]]
    radial_clearance = min(
        board["footprints"]["A1"]["x_mm"] - radius - cavity[0],
        cavity[2] - board["footprints"]["A1"]["x_mm"] - radius,
        board["footprints"]["A1"]["y_mm"] - radius - cavity[1],
        cavity[3] - board["footprints"]["A1"]["y_mm"] - radius,
    )
    if radial_clearance + tol < number(keepout["minimum_radial_clearance_to_cavity_wall_mm"], "A1 radial clearance"):
        fail("trusted A1 reserved volume cannot satisfy its radial wall-clearance contract")
    for field in ("maximum_carrier_intersection_mm3", "maximum_non_a1_component_intersection_mm3"):
        if number(keepout.get(field), f"A1 {field}") < 0.0:
            fail(f"trusted A1 {field} must be nonnegative")
    side_clearances = [
        board["bounds_xy_mm"][0] - expected_cavity[0],
        expected_cavity[2] - board["bounds_xy_mm"][2],
        board["bounds_xy_mm"][1] - expected_cavity[1],
        expected_cavity[3] - board["bounds_xy_mm"][3],
    ]
    if min(side_clearances) + tol < number(req["minimum_side_clearance_mm"], "minimum side clearance"):
        fail("trusted contract cannot satisfy its minimum side clearance")
    tallest = max(number(board["footprints"][ref]["height_mm"], f"{ref} height") for ref in component_refs)
    if number(req["lid_inner_z_mm"], "lid inner") - (board_top + tallest) + tol < number(req["minimum_top_clearance_mm"], "minimum top clearance"):
        fail("trusted contract cannot satisfy its minimum top clearance")
    return {"board": board, "requirements": req, "connectors": connectors, "paths": paths}


def check_required_files() -> None:
    for name in REQUIRED_ARTIFACTS:
        path = DESKTOP / name
        if not path.is_file():
            fail(f"missing required artifact {name}")
        size = path.stat().st_size
        minimum = MIN_FILE_SIZE[name]
        if size < minimum:
            fail(f"required artifact {name} is too small ({size} bytes; expected at least {minimum})")
        if size > MAX_FILE_SIZE:
            fail(f"required artifact {name} is implausibly large ({size} bytes)")


def check_answer_board(spec: dict[str, Any]) -> dict[str, Any]:
    canonical = spec["board"]
    answer = parse_board(DESKTOP / "01_kicad_board.kicad_pcb")
    tol = number(spec["requirements"]["axis_tolerance_mm"], "axis_tolerance_mm")
    close(answer["thickness_mm"], canonical["thickness_mm"], tol, "answer board thickness")
    close_vector(answer["bounds_xy_mm"], canonical["bounds_xy_mm"], tol, "answer board Edge.Cuts")
    for ref, expected in canonical["footprints"].items():
        actual = answer["footprints"].get(ref)
        if actual is None:
            fail(f"answer board is missing footprint {ref}")
        close(actual["x_mm"], expected["x_mm"], tol, f"answer board {ref} x")
        close(actual["y_mm"], expected["y_mm"], tol, f"answer board {ref} y")
        if ref.startswith("MH"):
            close(actual["hole_diameter_mm"], expected["hole_diameter_mm"], tol, f"answer board {ref} hole")
            close(actual["npth_drill_mm"], expected["hole_diameter_mm"], tol, f"answer board {ref} NPTH")
        else:
            close(actual["height_mm"], expected["height_mm"], tol, f"answer board {ref} height")
            close(actual["keepout_radius_mm"], expected["keepout_radius_mm"], tol, f"answer board {ref} radius")
    return answer


def rows_by_ref(path: Path) -> dict[str, dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        fail(f"cannot parse {path.name}: {exc}")
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        ref = str(row.get("ref", "")).strip()
        if not ref or ref in result:
            fail(f"{path.name} has invalid or duplicate ref {ref!r}")
        result[ref] = row
    return result


def check_kicad_handoff(spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    board = spec["board"]
    req = spec["requirements"]
    connectors = spec["connectors"]
    tol = number(req["axis_tolerance_mm"], "axis_tolerance_mm")
    rows = rows_by_ref(DESKTOP / "01_kicad_mechanical_map.csv")
    for ref, footprint in board["footprints"].items():
        row = rows.get(ref)
        if row is None:
            fail(f"mechanical map lacks {ref}")
        close(row.get("x_mm"), footprint["x_mm"], tol, f"map {ref} x")
        close(row.get("y_mm"), footprint["y_mm"], tol, f"map {ref} y")
        if ref.startswith("MH"):
            if normalized(row.get("kind")) != normalized("MOUNTING_HOLE"):
                fail(f"mechanical map {ref} kind mismatch")
            if str(row.get("hole_diameter_mm", "")).strip():
                close(row.get("hole_diameter_mm"), footprint["hole_diameter_mm"], tol, f"map {ref} hole")
            elif str(row.get("keepout_radius_mm", "")).strip():
                close(2.0 * number(row.get("keepout_radius_mm"), f"map {ref} radius"), footprint["hole_diameter_mm"], tol, f"map {ref} hole")
            else:
                fail(f"mechanical map {ref} lacks mounting-hole diameter")
            if normalized(row.get("role")) != normalized("standoff_axis"):
                fail(f"mechanical map {ref} is not a standoff axis")
        else:
            if normalized(row.get("kind")) != normalized(footprint["kind"]):
                fail(f"mechanical map {ref} kind mismatch")
            close(row.get("height_mm"), footprint["height_mm"], tol, f"map {ref} height")
            close(row.get("keepout_radius_mm"), footprint["keepout_radius_mm"], tol, f"map {ref} radius")
            allowed_roles = (
                {normalized("connector_window"), normalized("access"), normalized("access_corridor"), normalized("side_window")}
                if ref == "J1"
                else {
                    normalized("top_bore"), normalized("test_access"),
                    normalized("access_bore"), normalized("access"),
                    normalized("component_keepout"),
                }
                if ref == "TP1"
                else {
                    normalized("reserved_volume"), normalized("antenna_keepout"),
                    normalized("component_keepout"),
                }
                if ref == "A1"
                else {normalized("component_keepout")}
            )
            if normalized(row.get("role")) not in allowed_roles:
                fail(f"mechanical map {ref} role mismatch")
        if ref in connectors:
            connector = connectors[ref]
            if normalized(row.get("kind")) != normalized(connector["kind"]):
                fail(f"mechanical map {ref} kind mismatch")
            for field in ("finished_width_mm", "finished_height_mm", "finished_diameter_mm"):
                if str(row.get(field, "")).strip():
                    close(row.get(field), connector[field], tol, f"map {ref} {field}")
            for field in (
                "vertical_margin_mm", "cutter_x_min_mm", "cutter_y_min_mm",
                "cutter_z_min_mm", "cutter_x_max_mm", "cutter_y_max_mm",
                "cutter_z_max_mm", "path_x_min_mm", "path_y_min_mm", "path_z_min_mm",
                "path_x_max_mm", "path_y_max_mm", "path_z_max_mm",
            ):
                if str(row.get(field, "")).strip() and str(connector.get(field, "")).strip():
                    close(row.get(field), connector[field], tol, f"map {ref} {field}")
            if str(row.get("access_type", "")).strip() and normalized(row.get("access_type")) != normalized(connector["access_type"]):
                fail(f"mechanical map {ref} access_type mismatch")
            if str(row.get("direction", "")).strip() and normalized(row.get("direction")) != normalized(connector["direction"]):
                fail(f"mechanical map {ref} direction mismatch")
            if str(row.get("alignment_tolerance_mm", "")).strip():
                close(row.get("alignment_tolerance_mm"), req["access_center_tolerance_mm"], tol, f"map {ref} alignment tolerance")

    export = json_file(DESKTOP / "01_kicad_export.json")
    close_vector(export.get("board_bbox_mm"), board["bbox_mm"], tol, "KiCad export board bbox")
    components = export.get("components")
    if not isinstance(components, list):
        fail("KiCad export components must be a list")
    by_ref = {str(item.get("ref")): item for item in components if isinstance(item, dict)}
    for ref, footprint in board["footprints"].items():
        if ref.startswith("MH"):
            continue
        item = by_ref.get(ref)
        if item is None:
            fail(f"KiCad export is missing component {ref}")
        for field in ("x_mm", "y_mm", "height_mm", "keepout_radius_mm"):
            expected = footprint[field]
            close(item.get(field), expected, tol, f"export {ref} {field}")
        if item.get("body_bbox_mm") is not None:
            close_vector(item["body_bbox_mm"], req["component_bodies"][ref]["bbox_mm"], tol, f"export {ref} body")
    close(export.get("max_component_height_mm"), max(item["height_mm"] for item in board["footprints"].values() if not item["ref"].startswith("MH")), tol, "KiCad export max component height")
    holes = export.get("mounting_holes")
    if not isinstance(holes, list):
        fail("KiCad export mounting_holes must be a list")
    holes_by_ref = {str(item.get("ref")): item for item in holes if isinstance(item, dict)}
    for ref, footprint in board["footprints"].items():
        if not ref.startswith("MH"):
            continue
        item = holes_by_ref.get(ref)
        if item is None:
            fail(f"KiCad export is missing mounting hole {ref}")
        close(item.get("x_mm"), footprint["x_mm"], tol, f"export {ref} x")
        close(item.get("y_mm"), footprint["y_mm"], tol, f"export {ref} y")
        close(item.get("diameter_mm"), footprint["hole_diameter_mm"], tol, f"export {ref} diameter")
    if export.get("input_board_sha256") is not None and export["input_board_sha256"] != sha256(spec["paths"]["board"]):
        fail("KiCad export input_board_sha256 does not match trusted postconfig")
    return export, rows


def expected_geometry(spec: dict[str, Any]) -> dict[str, Any]:
    board = spec["board"]
    req = spec["requirements"]
    enclosure = [number(value, "enclosure bbox") for value in req["expected_enclosure_bbox_mm"]]
    board_bottom = number(req["board_bottom_z_mm"], "board bottom")
    board_top = board_bottom + board["thickness_mm"]
    half_x, half_y = enclosure[0] / 2.0, enclosure[1] / 2.0
    tray_bounds = [-half_x, -half_y, 0.0, half_x, half_y, number(req["tray_outer_top_z_mm"], "tray top")]
    lid_bounds = [-half_x, -half_y, number(req["lid_inner_z_mm"], "lid inner"), half_x, half_y, enclosure[2]]
    board_bounds = [
        board["bounds_xy_mm"][0], board["bounds_xy_mm"][1], board_bottom,
        board["bounds_xy_mm"][2], board["bounds_xy_mm"][3], board_top,
    ]
    components = []
    for ref in ("A1", "U1", "J1", "BT1", "TP1"):
        footprint = board["footprints"][ref]
        sx, sy, sz = [number(value, f"{ref} body") for value in req["component_bodies"][ref]["bbox_mm"]]
        x, y = footprint["x_mm"], footprint["y_mm"]
        bounds = [x - sx / 2.0, y - sy / 2.0, board_top, x + sx / 2.0, y + sy / 2.0, board_top + sz]
        component = {
            "ref": ref, "shape": req["component_bodies"][ref]["shape"],
            "x_mm": x, "y_mm": y, "body_bbox_mm": [sx, sy, sz], "bounds_mm": bounds,
        }
        if normalized(component["shape"]) == normalized("cylinder"):
            component["cylinder_mm"] = [x, y, sx / 2.0, board_top, board_top + sz]
        components.append(component)
    accesses = []
    fields = ("x_min_mm", "y_min_mm", "z_min_mm", "x_max_mm", "y_max_mm", "z_max_mm")
    for ref in ("J1",):
        connector = spec["connectors"][ref]
        cutter_bounds = [number(connector["cutter_" + field], f"{ref} cutter {field}") for field in fields]
        path_bounds = [number(connector["path_" + field], f"{ref} path {field}") for field in fields]
        accesses.append({
            "ref": ref, "access_type": "side_window", "direction": connector["direction"],
            "bounds_mm": cutter_bounds, "path_bounds_mm": path_bounds,
            "finished_width_mm": number(connector["finished_width_mm"], f"{ref} width"),
            "finished_height_mm": number(connector["finished_height_mm"], f"{ref} height"),
            "center_y_mm": (cutter_bounds[1] + cutter_bounds[4]) / 2.0,
            "center_z_mm": (cutter_bounds[2] + cutter_bounds[5]) / 2.0,
        })
    for ref in ("TP1",):
        connector = spec["connectors"][ref]
        footprint = board["footprints"][ref]
        diameter = number(connector["finished_diameter_mm"], f"{ref} diameter")
        cutter_bounds = [number(connector["cutter_" + field], f"{ref} cutter {field}") for field in fields]
        path_bounds = [number(connector["path_" + field], f"{ref} path {field}") for field in fields]
        accesses.append({
            "ref": ref, "access_type": "top_bore", "direction": "Z_PLUS",
            "x_mm": footprint["x_mm"], "y_mm": footprint["y_mm"],
            "finished_diameter_mm": diameter,
            "bounds_mm": cutter_bounds, "path_bounds_mm": path_bounds,
            "path_cylinder_mm": [footprint["x_mm"], footprint["y_mm"], diameter / 2.0, path_bounds[2], path_bounds[5]],
            "cutter_cylinder_mm": [footprint["x_mm"], footprint["y_mm"], diameter / 2.0, cutter_bounds[2], cutter_bounds[5]],
        })
    standoffs = []
    for ref in ("MH1", "MH2", "MH3", "MH4"):
        footprint = board["footprints"][ref]
        standoffs.append({"ref": ref, "x_mm": footprint["x_mm"], "y_mm": footprint["y_mm"]})

    keepout_req = req["antenna_keepout"]
    a1 = board["footprints"]["A1"]
    keepout_bounds = [number(value, "antenna keepout bbox") for value in keepout_req["bbox_mm"]]
    antenna_keepout = {
        "ref": "A1", "shape": "cylinder", "direction": "Z_PLUS",
        "x_mm": a1["x_mm"], "y_mm": a1["y_mm"], "radius_mm": a1["keepout_radius_mm"],
        "z_bounds_mm": [number(value, "antenna keepout z") for value in keepout_req["z_bounds_mm"]],
        "bounds_mm": keepout_bounds,
        "cylinder_mm": [a1["x_mm"], a1["y_mm"], a1["keepout_radius_mm"], keepout_bounds[2], keepout_bounds[5]],
        "maximum_carrier_intersection_mm3": number(keepout_req["maximum_carrier_intersection_mm3"], "A1 carrier intersection"),
        "maximum_non_a1_component_intersection_mm3": number(keepout_req["maximum_non_a1_component_intersection_mm3"], "A1 component intersection"),
        "minimum_radial_clearance_to_cavity_wall_mm": number(keepout_req["minimum_radial_clearance_to_cavity_wall_mm"], "A1 radial clearance"),
    }
    overlays = []
    for access in accesses:
        overlay = {
            "id": f"{access['ref']}_{access['direction']}_access", "ref": access["ref"],
            "role": "access_corridor", "direction": access["direction"],
        }
        if access["access_type"] == "top_bore":
            overlay.update({"shape": "cylinder", "cylinder_mm": access["path_cylinder_mm"], "bounds_mm": access["path_bounds_mm"]})
        else:
            overlay.update({"shape": "box", "bounds_mm": access["path_bounds_mm"]})
        overlays.append(overlay)
    overlays.append({
        "id": "A1_antenna_reserved_volume", "ref": "A1", "role": "antenna_reserved_volume",
        "direction": "Z_PLUS", "shape": "cylinder", "cylinder_mm": antenna_keepout["cylinder_mm"],
        "bounds_mm": antenna_keepout["bounds_mm"],
    })
    return {
        "enclosure_bbox_mm": enclosure, "tray_bounds_mm": tray_bounds, "lid_bounds_mm": lid_bounds,
        "board_bounds_mm": board_bounds, "board_top_z_mm": board_top, "components": components,
        "accesses": accesses, "standoffs": standoffs, "antenna_keepout": antenna_keepout, "overlays": overlays,
    }


def check_openscad_handoff(spec: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    req = spec["requirements"]
    tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    handoff_text = (DESKTOP / "01_kicad_parameters.scad").read_text(encoding="utf-8")
    source_text = (DESKTOP / "02_openscad_enclosure.scad").read_text(encoding="utf-8")
    uncommented = re.sub(r"/\*.*?\*/|//[^\n]*", "", handoff_text, flags=re.DOTALL)
    if not re.findall(r"(?m)^\s*[A-Za-z_$][A-Za-z0-9_$]*\s*=", uncommented):
        fail("01_kicad_parameters.scad does not contain a parameter assignment")
    if re.search(r"(?im)^\s*include\s*<\s*(?:[^>]+/)?01_kicad_parameters\.scad\s*>", source_text) is None:
        fail("OpenSCAD source does not consume 01_kicad_parameters.scad")
    params = json_file(DESKTOP / "02_openscad_parameters.json")
    close_vector(params.get("board_bbox_mm"), spec["board"]["bbox_mm"], tol, "OpenSCAD board bbox")
    close_vector(params.get("enclosure_bbox_mm"), geometry["enclosure_bbox_mm"], tol, "OpenSCAD enclosure bbox")
    for field in (
        "wall_mm", "tray_outer_top_z_mm", "lid_inner_z_mm",
        "lid_separation_mm", "lid_thickness_mm", "board_bottom_z_mm",
    ):
        close(params.get(field), req[field], tol, f"OpenSCAD {field}")
    for field in (
        "base_thickness_mm", "standoff_height_mm", "standoff_outer_diameter_mm",
        "standoff_bore_diameter_mm", "standoff_bore_overcut_mm", "access_overcut_mm",
    ):
        if params.get(field) is not None:
            close(params[field], req[field], tol, f"OpenSCAD {field}")
    close(params.get("board_top_z_mm"), geometry["board_top_z_mm"], tol, "OpenSCAD board top")
    close_vector(params.get("cavity_bounds_mm"), req["inner_cavity_xy_bounds_mm"], tol, "OpenSCAD cavity bounds")
    if params.get("cavity_bbox_mm") is not None:
        cavity = req["inner_cavity_xy_bounds_mm"]
        expected_cavity_bbox = [
            number(cavity[2], "cavity xmax") - number(cavity[0], "cavity xmin"),
            number(cavity[3], "cavity ymax") - number(cavity[1], "cavity ymin"),
            number(req["tray_outer_top_z_mm"], "tray top") - number(req["base_thickness_mm"], "base"),
        ]
        close_vector(params["cavity_bbox_mm"], expected_cavity_bbox, tol, "OpenSCAD cavity bbox")
    if params.get("tray_bounds_mm") is not None:
        close_vector(params["tray_bounds_mm"], geometry["tray_bounds_mm"], tol, "OpenSCAD tray bounds")
    if params.get("lid_bounds_mm") is not None:
        close_vector(params["lid_bounds_mm"], geometry["lid_bounds_mm"], tol, "OpenSCAD lid bounds")
    bore_z = params.get("standoff_bore_z_bounds_mm", params.get("standoff_bore_cutter_z_bounds_mm"))
    close_vector(bore_z, req["standoff_bore_cutter_z_bounds_mm"], tol, "OpenSCAD standoff bore z")

    def records(*keys: str) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for key in keys:
            raw = params.get(key)
            if isinstance(raw, list):
                values.extend(item for item in raw if isinstance(item, dict))
            elif isinstance(raw, dict):
                for ref, item in raw.items():
                    if isinstance(item, dict):
                        values.append({**item, "ref": ref})
        return values

    actual_standoffs = {
        str(item.get("ref")): item
        for item in records("standoff_axes", "standoffs")
        if item.get("ref")
    }
    for expected in geometry["standoffs"]:
        actual = actual_standoffs.get(expected["ref"])
        if actual is None:
            fail(f"OpenSCAD parameters lack standoff {expected['ref']}")
        axis_xy = actual.get("axis_xy_mm")
        actual_x = axis_xy[0] if isinstance(axis_xy, list) and len(axis_xy) == 2 else actual.get("x_mm")
        actual_y = axis_xy[1] if isinstance(axis_xy, list) and len(axis_xy) == 2 else actual.get("y_mm")
        close(actual_x, expected["x_mm"], tol, f"OpenSCAD {expected['ref']} x")
        close(actual_y, expected["y_mm"], tol, f"OpenSCAD {expected['ref']} y")
        close(
            actual.get("height_mm", params.get("standoff_height_mm")),
            req["standoff_height_mm"], tol, f"OpenSCAD {expected['ref']} height",
        )
        close(
            actual.get("outer_diameter_mm", params.get("standoff_outer_diameter_mm")),
            req["standoff_outer_diameter_mm"], tol, f"OpenSCAD {expected['ref']} outer diameter",
        )
        close(
            actual.get("bore_diameter_mm", params.get("standoff_bore_diameter_mm")),
            req["standoff_bore_diameter_mm"], tol, f"OpenSCAD {expected['ref']} bore diameter",
        )
        if actual.get("diameter_mm") is not None:
            close(actual["diameter_mm"], req["mount_hole_diameter_mm"], tol, f"OpenSCAD {expected['ref']} mounting-hole diameter")
    actual_accesses = records(
        "accesses", "side_windows", "connector_windows", "top_openings",
        "top_bores", "access_bores", "test_accesses",
    )
    grouped_accesses: dict[str, list[dict[str, Any]]] = {}
    for item in actual_accesses:
        if item.get("ref"):
            grouped_accesses.setdefault(str(item["ref"]), []).append(item)
    for expected in geometry["accesses"]:
        items = grouped_accesses.get(expected["ref"], [])
        if not items:
            fail(f"OpenSCAD parameters lack access {expected['ref']}")
        declared_types = [
            item.get("access_type", item.get("type"))
            for item in items
            if str(item.get("access_type", item.get("type", ""))).strip()
        ]
        declared_directions = [item.get("direction") for item in items if str(item.get("direction", "")).strip()]
        if not declared_types or any(normalized(value) != normalized(expected["access_type"]) for value in declared_types):
            fail(f"OpenSCAD access {expected['ref']} type mismatch")
        if not declared_directions or any(normalized(value) != normalized(expected["direction"]) for value in declared_directions):
            fail(f"OpenSCAD access {expected['ref']} direction mismatch")
        cutter_bounds = [
            item[key]
            for item in items
            for key in ("cutter_bounds_mm", "lid_cutter_bounds_mm", "bounds_mm")
            if isinstance(item.get(key), list) and len(item[key]) == 6
        ]
        path_bounds = [
            item[key]
            for item in items
            for key in ("path_bounds_mm", "continuous_path_bounds_mm", "clearance_path_bounds_mm")
            if isinstance(item.get(key), list) and len(item[key]) == 6
        ]
        if not cutter_bounds:
            cylinder_bounds = [item["cutter_cylinder_mm"] for item in items if isinstance(item.get("cutter_cylinder_mm"), list)]
            cutter_bounds = [
                [value[0] - value[2], value[1] - value[2], value[3], value[0] + value[2], value[1] + value[2], value[4]]
                for value in cylinder_bounds if len(value) == 5
            ]
        if not path_bounds:
            cylinder_bounds = [item["path_cylinder_mm"] for item in items if isinstance(item.get("path_cylinder_mm"), list)]
            path_bounds = [
                [value[0] - value[2], value[1] - value[2], value[3], value[0] + value[2], value[1] + value[2], value[4]]
                for value in cylinder_bounds if len(value) == 5
            ]
        if expected["access_type"] == "top_bore":
            radius = expected["finished_diameter_mm"] / 2.0
            for item in items:
                axis = item.get("axis_xy_mm")
                x = axis[0] if isinstance(axis, list) and len(axis) == 2 else item.get("x_mm")
                y = axis[1] if isinstance(axis, list) and len(axis) == 2 else item.get("y_mm")
                cutter_z = item.get("cutter_z_bounds_mm")
                path_z = item.get("path_z_bounds_mm", item.get("continuous_path_z_bounds_mm"))
                if x is not None and y is not None and isinstance(cutter_z, list) and len(cutter_z) == 2:
                    cutter_bounds.append([number(x, "top-opening x") - radius, number(y, "top-opening y") - radius, cutter_z[0], number(x, "top-opening x") + radius, number(y, "top-opening y") + radius, cutter_z[1]])
                if x is not None and y is not None and isinstance(path_z, list) and len(path_z) == 2:
                    path_bounds.append([number(x, "top-opening x") - radius, number(y, "top-opening y") - radius, path_z[0], number(x, "top-opening x") + radius, number(y, "top-opening y") + radius, path_z[1]])
        if not cutter_bounds or not path_bounds:
            fail(f"OpenSCAD access {expected['ref']} lacks cutter or continuous-path geometry")
        for value in cutter_bounds:
            close_vector(value, expected["bounds_mm"], tol, f"OpenSCAD {expected['ref']} bounds")
        for value in path_bounds or cutter_bounds:
            close_vector(value, expected["path_bounds_mm"], tol, f"OpenSCAD {expected['ref']} path bounds")
        if expected["access_type"] == "side_window":
            widths = [item["finished_width_mm"] for item in items if item.get("finished_width_mm") is not None]
            heights = [item["finished_height_mm"] for item in items if item.get("finished_height_mm") is not None]
            if not widths or not heights:
                fail(f"OpenSCAD access {expected['ref']} lacks finished window dimensions")
            for value in widths:
                close(value, expected["finished_width_mm"], tol, f"OpenSCAD {expected['ref']} width")
            for value in heights:
                close(value, expected["finished_height_mm"], tol, f"OpenSCAD {expected['ref']} height")
        else:
            diameters = [
                item.get("finished_diameter_mm", item.get("diameter_mm"))
                for item in items
                if item.get("finished_diameter_mm", item.get("diameter_mm")) is not None
            ]
            if not diameters:
                fail(f"OpenSCAD access {expected['ref']} lacks finished opening diameter")
            for value in diameters:
                close(value, expected["finished_diameter_mm"], tol, f"OpenSCAD {expected['ref']} diameter")

    keepout_records = records("antenna_keepout", "antenna_keepouts", "reserved_volume", "reserved_volumes")
    a1_records = [item for item in keepout_records if str(item.get("ref", "A1")) == "A1"]
    if not a1_records:
        fail("OpenSCAD parameters lack the A1 antenna reserved volume")
    expected_keepout = geometry["antenna_keepout"]
    matched = False
    for item in a1_records:
        declared_type = item.get("access_type", item.get("type", item.get("role", "reserved_volume")))
        if normalized(declared_type) not in {normalized("reserved_volume"), normalized("antenna_keepout"), normalized("antenna_reserved_volume")}:
            continue
        bounds = item.get("bounds_mm", item.get("bbox_mm", item.get("path_bounds_mm")))
        cylinder = item.get("cylinder_mm")
        if not isinstance(bounds, list) and isinstance(cylinder, list) and len(cylinder) == 5:
            bounds = [cylinder[0] - cylinder[2], cylinder[1] - cylinder[2], cylinder[3], cylinder[0] + cylinder[2], cylinder[1] + cylinder[2], cylinder[4]]
        if isinstance(bounds, list) and len(bounds) == 6:
            close_vector(bounds, expected_keepout["bounds_mm"], tol, "OpenSCAD A1 reserved bounds")
            radius = item.get("radius_mm")
            if radius is None and isinstance(cylinder, list) and len(cylinder) == 5:
                radius = cylinder[2]
            if radius is not None:
                close(radius, expected_keepout["radius_mm"], tol, "OpenSCAD A1 reserved radius")
            matched = True
    if not matched:
        fail("OpenSCAD A1 reserved volume does not match its trusted finite cylinder")

    if params.get("input_mechanical_map_sha256") is not None and params["input_mechanical_map_sha256"] != sha256(DESKTOP / "01_kicad_mechanical_map.csv"):
        fail("OpenSCAD input mechanical-map hash mismatch")
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
        output = (completed.stdout + "\n" + completed.stderr)[-4000:]
        fail(f"{label} failed with return code {completed.returncode}: {output}")
    return completed


def run_kicad_export(answer_board: Path, output_step: Path, runtime: Path) -> None:
    kicad = resolve_executable("kicad-cli", ["/home/user/Applications/kicad-*/kicad-*-x86_64.AppImage"])
    prefix = [kicad, "--appimage-extract-and-run", "kicad-cli"] if Path(kicad).suffix.lower() == ".appimage" else [kicad]
    run_command(
        prefix + ["pcb", "export", "step", "--force", "--board-only", "--output", str(output_step), str(answer_board)],
        cwd=runtime,
        timeout=90,
        label="KiCad board STEP re-export",
    )
    if not output_step.is_file() or output_step.stat().st_size < 500:
        fail("KiCad re-export did not create a substantial STEP file")


def load_mesh_metrics(path: Path) -> dict[str, Any]:
    try:
        import numpy as np
        import trimesh
    except Exception as exc:
        fail(f"evaluator mesh dependencies unavailable: {exc}")
    try:
        loaded = trimesh.load_mesh(str(path), file_type="stl", process=True)
        if isinstance(loaded, trimesh.Scene):
            meshes = [mesh for mesh in loaded.geometry.values() if isinstance(mesh, trimesh.Trimesh)]
            if not meshes:
                fail(f"{path.name} contains no mesh geometry")
            mesh = trimesh.util.concatenate(meshes)
        else:
            mesh = loaded
        if not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) < 20 or len(mesh.faces) < 30:
            fail(f"{path.name} has implausibly little triangle geometry")
        bounds = np.asarray(mesh.bounds, dtype=float)
        volume = abs(float(mesh.volume))
        if not bool(mesh.is_watertight) or not bool(mesh.is_winding_consistent) or volume <= 0:
            fail(f"{path.name} must be a watertight, consistently wound positive-volume mesh")
        components = []
        for component in mesh.split(only_watertight=False):
            if len(component.faces) < 4:
                continue
            cbounds = np.asarray(component.bounds, dtype=float)
            components.append({
                "bounds": [float(value) for value in cbounds.reshape(-1)],
                "bbox": [float(value) for value in cbounds[1] - cbounds[0]],
                "volume": abs(float(component.volume)),
                "faces": int(len(component.faces)),
            })
        return {
            "bounds": [float(value) for value in bounds.reshape(-1)],
            "bbox": [float(value) for value in bounds[1] - bounds[0]],
            "volume": volume,
            "area": float(mesh.area),
            "center": [float(value) for value in np.asarray(mesh.center_mass, dtype=float)],
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "components": components,
        }
    except EvaluationError:
        raise
    except Exception as exc:
        fail(f"cannot inspect mesh {path.name}: {exc}")


def find_mesh_component(metrics: dict[str, Any], bounds: list[float], label: str) -> dict[str, Any]:
    matches = []
    for component in metrics["components"]:
        error = max(abs(a - b) for a, b in zip(component["bounds"], bounds))
        if error <= 0.25:
            matches.append((error, component))
    if not matches:
        fail(f"{label} does not contain the expected disconnected solid at {bounds}")
    return min(matches, key=lambda item: item[0])[1]


def compare_meshes(submitted: dict[str, Any], rendered: dict[str, Any], geometry: dict[str, Any]) -> None:
    expected_bbox = geometry["enclosure_bbox_mm"]
    expected_bounds = [-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, 0.0, expected_bbox[0] / 2.0, expected_bbox[1] / 2.0, expected_bbox[2]]
    for label, metrics in (("submitted STL", submitted), ("OpenSCAD rerender", rendered)):
        close_vector(metrics["bbox"], expected_bbox, 0.15, f"{label} bbox")
        close_vector(metrics["bounds"], expected_bounds, 0.15, f"{label} bounds")
        if len(metrics["components"]) < 2:
            fail(f"{label} must retain disconnected tray and lid solids")
        find_mesh_component(metrics, geometry["tray_bounds_mm"], f"{label} tray")
        find_mesh_component(metrics, geometry["lid_bounds_mm"], f"{label} lid")
        fill = metrics["volume"] / math.prod(expected_bbox)
        if not 0.10 <= fill <= 0.65:
            fail(f"{label} has an implausible tray/lid fill ratio: {fill}")
    if abs(submitted["volume"] - rendered["volume"]) > max(5.0, rendered["volume"] * 0.005):
        fail("submitted STL volume differs materially from the submitted SCAD rerender")
    if abs(submitted["area"] - rendered["area"]) > max(10.0, rendered["area"] * 0.01):
        fail("submitted STL area differs materially from the submitted SCAD rerender")


FREECAD_CHECKER = r'''
import json
import math
import os
import traceback

import FreeCAD as App
import Import
import Mesh
import MeshPart
import Part


config = json.load(open(os.environ["ENGIWORLD_TASK10_CAD_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK10_CAD_RESULT"]


def bounds(shape):
    box = shape.BoundBox
    return [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]


def metrics(shape):
    return {
        "valid": bool(shape.isValid()),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "bounds_mm": bounds(shape),
        "bbox_mm": [shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength],
    }


def read_step(path):
    shape = Part.read(path)
    if shape.isNull() or not shape.isValid() or not shape.Solids or shape.Volume <= 0:
        raise RuntimeError("STEP has no valid positive-volume solid: " + path)
    return shape


def read_step_objects(path):
    doc = App.newDocument("Task10EvalAssembly")
    Import.insert(path, doc.Name)
    doc.recompute()
    values = []
    for obj in doc.Objects:
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull() or not shape.isValid() or shape.Volume <= 0:
            continue
        solids = list(shape.Solids)
        for index, solid in enumerate(solids):
            if solid.Volume > 0:
                values.append({"name": obj.Name + "_" + str(index), "label": obj.Label, "shape": solid})
    unique = []
    seen = set()
    for value in values:
        shape = value["shape"]
        key = tuple(round(v, 4) for v in bounds(shape) + [float(shape.Volume)])
        if key not in seen:
            seen.add(key)
            unique.append(value)
    if not unique:
        raise RuntimeError("assembly STEP import produced no solid objects")
    return doc, unique


def mesh_solids(path):
    mesh = Mesh.Mesh(path)
    if mesh.CountFacets < 30:
        raise RuntimeError("STL has too few facets: " + path)
    shell_shape = Part.Shape()
    shell_shape.makeShapeFromMesh(mesh.Topology, 0.05)
    if not shell_shape.isClosed():
        raise RuntimeError("STL contains an open shell: " + path)
    solids = []
    for shell in shell_shape.Shells or [shell_shape]:
        candidate = Part.makeSolid(shell)
        if candidate.isNull() or not candidate.isValid() or candidate.Volume <= 0:
            raise RuntimeError("STL shell cannot form a valid solid: " + path)
        solids.extend(candidate.Solids)
    if len(solids) < 2:
        raise RuntimeError("STL does not retain distinct tray and lid solids: " + path)
    return solids, Part.makeCompound(solids), int(mesh.CountFacets)


def bounds_error(shape, expected):
    return max(abs(a - b) for a, b in zip(bounds(shape), expected))


def pick(values, expected, label, tolerance=0.25):
    ranked = [(bounds_error(value["shape"], expected), value) for value in values]
    ranked.sort(key=lambda item: item[0])
    if not ranked or ranked[0][0] > tolerance:
        raise RuntimeError("cannot identify " + label + " by trusted geometry")
    if len(ranked) > 1 and ranked[1][0] <= tolerance and abs(ranked[1][0] - ranked[0][0]) < 1e-6:
        raise RuntimeError("ambiguous geometry for " + label)
    return ranked[0][1]


def bounds_contained(actual, expected, tolerance=0.05):
    return all(actual[index] >= expected[index] - tolerance for index in range(3)) and all(actual[index] <= expected[index] + tolerance for index in range(3, 6))


def pick_group(values, expected, label, excluded_ids, tolerance=0.25):
    matches = [value for value in values if id(value) not in excluded_ids and bounds_contained(bounds(value["shape"]), expected)]
    if not matches: raise RuntimeError("cannot identify " + label + " by trusted geometry")
    shape = Part.makeCompound([value["shape"] for value in matches])
    if bounds_error(shape, expected) > tolerance: raise RuntimeError("cannot identify complete " + label + " by trusted geometry")
    return {"name": label, "label": label, "shape": shape, "members": matches}


def pick_shape(values, expected, label, tolerance=0.25):
    ranked = [(bounds_error(shape, expected), shape) for shape in values]
    ranked.sort(key=lambda item: item[0])
    if not ranked or ranked[0][0] > tolerance:
        raise RuntimeError("cannot identify " + label + " in STL")
    return ranked[0][1]


def box_shape(box):
    xmin, ymin, zmin, xmax, ymax, zmax = box
    return Part.makeBox(xmax - xmin, ymax - ymin, zmax - zmin, App.Vector(xmin, ymin, zmin))


def cylinder_shape(volume):
    x, y, radius, zmin, zmax = volume
    return Part.makeCylinder(radius, zmax - zmin, App.Vector(x, y, zmin))


def overlap(first, second):
    common = float(first.common(second).Volume)
    return {
        "common_volume_mm3": common,
        "first_only_volume_mm3": max(0.0, float(first.Volume) - common),
        "second_only_volume_mm3": max(0.0, float(second.Volume) - common),
        "symmetric_difference_volume_mm3": max(0.0, float(first.Volume + second.Volume - 2.0 * common)),
    }


def inside(shape, x, y, z):
    return bool(shape.isInside(App.Vector(float(x), float(y), float(z)), 1e-4, False))


def export_reference(objects, path):
    doc = App.newDocument("Task10EvalReference")
    meshes = []
    for index, value in enumerate(objects):
        obj = doc.addObject("Mesh::Feature", "Reference_%02d" % index)
        obj.Label = "Evaluation reference %02d" % index
        obj.Mesh = MeshPart.meshFromShape(
            Shape=value["shape"], LinearDeflection=0.1, AngularDeflection=0.35, Relative=False
        )
        if obj.Mesh.CountFacets <= 0:
            raise RuntimeError("cannot mesh assembly role for bridge validation")
        meshes.append(obj)
    Mesh.export(meshes, path)
    if not os.path.isfile(path) or os.path.getsize(path) < 1000:
        raise RuntimeError("cannot export evaluator reference OBJ")


def centered_void(shape, x, y, z):
    candidates = [
        solid for solid in shape.Solids
        if solid.BoundBox.XMin - 1e-4 <= x <= solid.BoundBox.XMax + 1e-4
        and solid.BoundBox.YMin - 1e-4 <= y <= solid.BoundBox.YMax + 1e-4
        and solid.BoundBox.ZMin - 1e-4 <= z <= solid.BoundBox.ZMax + 1e-4
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda solid: solid.BoundBox.XLength * solid.BoundBox.YLength * solid.BoundBox.ZLength,
    )


def top_bore_metrics(material, access):
    tolerance = config["interference_tolerance_mm3"]
    geometry_tolerance = config["geometry_tolerance_mm"]
    axis_tolerance = config["access_center_tolerance_mm"]
    guard = config["minimum_access_guard_mm"]
    x, y, radius, zmin, zmax = access["path_cylinder_mm"]
    path_probe = Part.makeCylinder(
        radius,
        zmax - zmin,
        App.Vector(x, y, zmin),
    )
    residual = float(material.common(path_probe).Volume)

    lid_zmin, lid_zmax = config["lid_bounds_mm"][2], config["lid_bounds_mm"][5]
    section_height = min(0.2, (lid_zmax - lid_zmin) / 4.0)
    section_z = (lid_zmin + lid_zmax - section_height) / 2.0
    search_radius = radius + guard + 0.4
    search = Part.makeCylinder(search_radius, section_height, App.Vector(x, y, section_z))
    void = centered_void(search.cut(material), x, y, section_z + section_height / 2.0)
    ideal_void = Part.makeCylinder(radius, section_height, App.Vector(x, y, section_z))
    open_area_ratio = float(ideal_void.cut(material).Volume) / max(float(ideal_void.Volume), 1e-9)
    if void is None:
        measured_diameter = center = center_error = section_difference = None
    else:
        measured_diameter = (float(void.BoundBox.XLength) + float(void.BoundBox.YLength)) / 2.0
        center = [float(void.BoundBox.Center.x), float(void.BoundBox.Center.y)]
        center_error = math.hypot(center[0] - x, center[1] - y)
        section_difference = overlap(void, ideal_void)["symmetric_difference_volume_mm3"]
    outer_guard = Part.makeCylinder(radius + guard, section_height, App.Vector(x, y, section_z))
    inner_guard = Part.makeCylinder(radius + geometry_tolerance, section_height, App.Vector(x, y, section_z))
    guard_ring = outer_guard.cut(inner_guard)
    guard_fraction = float(material.common(guard_ring).Volume) / max(float(guard_ring.Volume), 1e-9)
    dimensions_pass = (
        measured_diameter is not None
        and abs(measured_diameter - 2.0 * radius) <= geometry_tolerance
        and center_error is not None
        and center_error <= axis_tolerance
        and section_difference is not None
        and section_difference <= max(tolerance, float(math.pi * radius * radius * section_height) * 0.03)
    )
    through = (
        residual <= tolerance
        and open_area_ratio >= 0.97
        and guard_fraction >= 0.90
        and dimensions_pass
    )
    return {
        "ref": access["ref"], "access_type": "top_bore", "direction": access["direction"],
        "axis_xy_mm": [x, y], "measured_center_xy_mm": center, "center_error_mm": center_error,
        "finished_diameter_mm": measured_diameter, "path_z_bounds_mm": [zmin, zmax],
        "cutter_z_bounds_mm": access["cutter_cylinder_mm"][-2:],
        "residual_material_volume_mm3": residual, "carrier_intersection_volume_mm3": residual,
        "open_area_ratio": open_area_ratio, "annular_guard_fill_ratio": guard_fraction,
        "measured_opening_bounds_mm": None if void is None else [
            float(void.BoundBox.XMin), float(void.BoundBox.YMin), lid_zmin,
            float(void.BoundBox.XMax), float(void.BoundBox.YMax), lid_zmax,
        ],
        "section_symmetric_difference_mm3": section_difference,
        "guard_material_present": guard_fraction >= 0.90, "continuous": through, "through": through,
    }


def side_window_metrics(material, access):
    tolerance = config["interference_tolerance_mm3"]
    geometry_tolerance = config["geometry_tolerance_mm"]
    center_tolerance = config["access_center_tolerance_mm"]
    guard = config["minimum_access_guard_mm"]
    wall = config["wall_mm"]
    enclosure = config["enclosure_bbox_mm"]
    if access["direction"] not in {"X_MINUS", "X_PLUS"}:
        raise RuntimeError("task-10 connector windows must use X_MINUS or X_PLUS")
    _cutter_xmin, ymin, zmin, _cutter_xmax, ymax, zmax = access["bounds_mm"]
    if access["direction"] == "X_MINUS":
        wall_min, wall_max = -enclosure[0] / 2.0, -enclosure[0] / 2.0 + wall
        opposite_min, opposite_max = enclosure[0] / 2.0 - wall, enclosure[0] / 2.0
    else:
        wall_min, wall_max = enclosure[0] / 2.0 - wall, enclosure[0] / 2.0
        opposite_min, opposite_max = -enclosure[0] / 2.0, -enclosure[0] / 2.0 + wall
    inset = min(0.05, (ymax - ymin) / 20.0, (zmax - zmin) / 20.0)
    core = box_shape([wall_min + inset, ymin + inset, zmin + inset, wall_max - inset, ymax - inset, zmax - inset])
    residual = float(material.common(core).Volume)
    path_bounds = access["path_bounds_mm"]
    path_probe = box_shape([path_bounds[0] + inset, path_bounds[1] + inset, path_bounds[2] + inset, path_bounds[3] - inset, path_bounds[4] - inset, path_bounds[5] - inset])
    path_residual = float(material.common(path_probe).Volume)

    section_thickness = min(0.2, wall / 4.0)
    section_x = (wall_min + wall_max - section_thickness) / 2.0
    search = box_shape([
        section_x, ymin - guard - 0.4, max(0.0, zmin - guard - 0.4),
        section_x + section_thickness, ymax + guard + 0.4,
        min(config["tray_outer_top_z_mm"], zmax + guard + 0.4),
    ])
    void = centered_void(search.cut(material), section_x + section_thickness / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0)
    if void is None:
        measured_width = measured_height = center_error = None
        measured_bounds = None
        section_difference = None
    else:
        measured_width = float(void.BoundBox.YLength)
        measured_height = float(void.BoundBox.ZLength)
        center_error = math.hypot(
            float(void.BoundBox.Center.y) - (ymin + ymax) / 2.0,
            float(void.BoundBox.Center.z) - (zmin + zmax) / 2.0,
        )
        measured_bounds = [
            wall_min, float(void.BoundBox.YMin), float(void.BoundBox.ZMin),
            wall_max, float(void.BoundBox.YMax), float(void.BoundBox.ZMax),
        ]
        ideal_section = box_shape([section_x, ymin, zmin, section_x + section_thickness, ymax, zmax])
        section_difference = overlap(void, ideal_section)["symmetric_difference_volume_mm3"]

    gap = geometry_tolerance + 0.03
    width = max(0.08, guard - gap)
    probes = [
        box_shape([wall_min, ymin - gap - width, zmin + inset, wall_max, ymin - gap, zmax - inset]),
        box_shape([wall_min, ymax + gap, zmin + inset, wall_max, ymax + gap + width, zmax - inset]),
        box_shape([wall_min, ymin + inset, zmin - gap - width, wall_max, ymax - inset, zmin - gap]),
        box_shape([wall_min, ymin + inset, zmax + gap, wall_max, ymax - inset, zmax + gap + width]),
    ]
    fractions = [float(material.common(probe).Volume) / max(float(probe.Volume), 1e-9) for probe in probes]
    opposite_probe = box_shape([
        opposite_min + inset, ymin + inset, zmin + inset,
        opposite_max - inset, ymax - inset, zmax - inset,
    ])
    for other in config["accesses"]:
        if other["ref"] != access["ref"] and other["access_type"] == "side_window":
            opposite_probe = opposite_probe.cut(box_shape(other["bounds_mm"]))
    opposite_fill = float(material.common(opposite_probe).Volume) / max(float(opposite_probe.Volume), 1e-9)
    guards = [
        ymin + enclosure[1] / 2.0,
        enclosure[1] / 2.0 - ymax,
        zmin,
        config["tray_outer_top_z_mm"] - zmax,
    ]
    dimensions_pass = (
        measured_width is not None
        and measured_height is not None
        and abs(measured_width - access["finished_width_mm"]) <= geometry_tolerance
        and abs(measured_height - access["finished_height_mm"]) <= geometry_tolerance
        and center_error is not None
        and center_error <= center_tolerance
        and section_difference is not None
        and section_difference <= max(tolerance, access["finished_width_mm"] * access["finished_height_mm"] * section_thickness * 0.02)
    )
    through = (
        residual <= tolerance
        and path_residual <= tolerance
        and dimensions_pass
        and min(fractions) >= 0.90
        and min(guards) + geometry_tolerance >= guard
    )
    return {
        "ref": access["ref"], "access_type": "side_window", "direction": access["direction"],
        "contract_cutter_bounds_mm": access["bounds_mm"], "measured_opening_bounds_mm": measured_bounds,
        "finished_width_mm": measured_width, "finished_height_mm": measured_height,
        "center_error_mm": center_error, "minimum_guard_mm": min(guards),
        "guard_fill_fractions": fractions, "guard_material_present": min(fractions) >= 0.90,
        "opposite_wall_fill_ratio": opposite_fill, "residual_material_volume_mm3": residual,
        "path_residual_material_volume_mm3": path_residual,
        "section_symmetric_difference_mm3": section_difference, "continuous": through, "through": through,
    }


def antenna_keepout_metrics(material, non_a1_components=None):
    contract = config["antenna_keepout"]
    reserved = cylinder_shape(contract["cylinder_mm"])
    carrier_intersection = float(material.common(reserved).Volume)
    zmin, zmax = contract["z_bounds_mm"]
    slice_height = min(0.2, max(0.05, (zmax - zmin) / 20.0))
    slice_z = (zmin + zmax - slice_height) / 2.0
    x, y, radius, _zmin, _zmax = contract["cylinder_mm"]
    reserved_slice = Part.makeCylinder(radius, slice_height, App.Vector(x, y, slice_z))
    cavity = config["cavity_bounds_xy_mm"]
    radial_clearance = min(
        x - radius - cavity[0], cavity[2] - (x + radius),
        y - radius - cavity[1], cavity[3] - (y + radius),
    )
    component_intersection = 0.0
    if non_a1_components:
        component_material = Part.makeCompound(non_a1_components)
        component_intersection = float(component_material.common(reserved).Volume)
    passed = (
        carrier_intersection <= contract["maximum_carrier_intersection_mm3"]
        and component_intersection <= contract["maximum_non_a1_component_intersection_mm3"]
        and radial_clearance + config["geometry_tolerance_mm"] >= contract["minimum_radial_clearance_to_cavity_wall_mm"]
    )
    return {
        "ref": "A1", "shape": "cylinder", "bounds_mm": bounds(reserved),
        "carrier_intersection_volume_mm3": carrier_intersection,
        "non_a1_component_intersection_volume_mm3": component_intersection,
        "minimum_radial_clearance_to_cavity_wall_mm": radial_clearance,
        "required_minimum_radial_clearance_mm": contract["minimum_radial_clearance_to_cavity_wall_mm"],
        "pass": passed,
    }


def access_metrics(material, access):
    if access["access_type"] == "top_bore":
        return top_bore_metrics(material, access)
    if access["access_type"] == "side_window":
        return side_window_metrics(material, access)
    raise RuntimeError("unsupported task-10 access type: " + str(access["access_type"]))

def side_clearance(package, board, direction):
    epsilon = 0.02
    z_height = max(0.05, min(0.2, board.BoundBox.ZLength / 2.0))
    z0 = board.BoundBox.Center.z - z_height / 2.0
    x_outer = config["enclosure_bbox_mm"][0] / 2.0 + 1.0
    y_outer = config["enclosure_bbox_mm"][1] / 2.0 + 1.0
    box = board.BoundBox
    if direction == "X_PLUS":
        reference = Part.makeBox(epsilon, box.YLength, z_height, App.Vector(box.XMax - epsilon, box.YMin, z0))
        search = Part.makeBox(x_outer - box.XMax, box.YLength, z_height, App.Vector(box.XMax, box.YMin, z0))
    elif direction == "X_MINUS":
        reference = Part.makeBox(epsilon, box.YLength, z_height, App.Vector(box.XMin, box.YMin, z0))
        search = Part.makeBox(box.XMin + x_outer, box.YLength, z_height, App.Vector(-x_outer, box.YMin, z0))
    elif direction == "Y_PLUS":
        reference = Part.makeBox(box.XLength, epsilon, z_height, App.Vector(box.XMin, box.YMax - epsilon, z0))
        search = Part.makeBox(box.XLength, y_outer - box.YMax, z_height, App.Vector(box.XMin, box.YMax, z0))
    else:
        reference = Part.makeBox(box.XLength, epsilon, z_height, App.Vector(box.XMin, box.YMin, z0))
        search = Part.makeBox(box.XLength, box.YMin + y_outer, z_height, App.Vector(box.XMin, -y_outer, z0))
    material = package.common(search)
    if material.isNull() or material.Volume <= 0:
        return None
    return float(reference.distToShape(material)[0])


def top_clearance(material, component):
    box = component.BoundBox
    top = float(box.ZMax)
    height = max(0.0, config["enclosure_bbox_mm"][2] - top)
    if height <= 0:
        return -1.0
    probe = Part.makeBox(
        float(box.XLength),
        float(box.YLength),
        height,
        App.Vector(float(box.XMin), float(box.YMin), top),
    )
    covering = material.common(probe)
    if covering.isNull() or covering.Volume <= 1e-6:
        return None
    return float(covering.BoundBox.ZMin - top)


def standoff_metrics(material):
    values = {}
    base = config["base_thickness_mm"]
    height = config["standoff_height_mm"]
    outer_radius = config["standoff_outer_diameter_mm"] / 2.0
    bore_radius = config["standoff_bore_diameter_mm"] / 2.0
    geometry_tolerance = config["geometry_tolerance_mm"]
    volume_tolerance = config["interference_tolerance_mm3"]
    board_bottom = config["board_bounds_mm"][2]
    bore_zmin, bore_zmax = config["standoff_bore_z_bounds_mm"]
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        probe_radius = max(0.05, bore_radius - geometry_tolerance)
        bore = Part.makeCylinder(probe_radius, bore_zmax - bore_zmin, App.Vector(x, y, bore_zmin))
        residual = float(material.common(bore).Volume)

        section_height = 0.2
        section_z = board_bottom - 0.6
        outer_search = Part.makeCylinder(
            outer_radius + 0.5,
            section_height,
            App.Vector(x, y, section_z),
        )
        actual_section = material.common(outer_search).removeSplitter()
        expected_section = Part.makeCylinder(outer_radius, section_height, App.Vector(x, y, section_z)).cut(
            Part.makeCylinder(bore_radius, section_height, App.Vector(x, y, section_z))
        )
        expected_section_volume = math.pi * (outer_radius * outer_radius - bore_radius * bore_radius) * section_height
        fill = float(actual_section.Volume) / max(expected_section_volume, 1e-9)
        section_difference = overlap(actual_section, expected_section)["symmetric_difference_volume_mm3"]
        section_box = actual_section.BoundBox
        measured_outer_diameter = (float(section_box.XLength) + float(section_box.YLength)) / 2.0
        measured_outer_center = (float(section_box.Center.x), float(section_box.Center.y))
        restricted = Part.makeCylinder(
            max(bore_radius + 0.25, outer_radius - 0.2),
            section_height,
            App.Vector(x, y, section_z),
        )
        void_shape = restricted.cut(material)
        bore_voids = [solid for solid in void_shape.Solids if float(solid.Volume) > min(volume_tolerance, 0.01)]
        centered_voids = [
            shape
            for shape in bore_voids
            if shape.BoundBox.XMin - geometry_tolerance <= x <= shape.BoundBox.XMax + geometry_tolerance
            and shape.BoundBox.YMin - geometry_tolerance <= y <= shape.BoundBox.YMax + geometry_tolerance
        ]
        if centered_voids:
            bore_void = min(
                centered_voids,
                key=lambda shape: math.hypot(shape.BoundBox.Center.x - x, shape.BoundBox.Center.y - y),
            )
            bore_box = bore_void.BoundBox
            measured_bore_diameter = (float(bore_box.XLength) + float(bore_box.YLength)) / 2.0
            measured_bore_center = (float(bore_box.Center.x), float(bore_box.Center.y))
            axis_error = math.hypot(measured_bore_center[0] - x, measured_bore_center[1] - y)
            concentric_error = math.hypot(
                measured_bore_center[0] - measured_outer_center[0],
                measured_bore_center[1] - measured_outer_center[1],
            )
        else:
            measured_bore_diameter = None
            measured_bore_center = None
            axis_error = None
            concentric_error = None
        dimensions_pass = (
            measured_bore_diameter is not None
            and abs(measured_bore_diameter - 2.0 * bore_radius) <= geometry_tolerance
            and abs(measured_outer_diameter - 2.0 * outer_radius) <= geometry_tolerance
            and axis_error is not None
            and axis_error <= config["axis_tolerance_mm"]
            and concentric_error is not None
            and concentric_error <= config["axis_tolerance_mm"]
            and section_difference <= max(volume_tolerance, expected_section_volume * 0.03)
        )
        probe_margin = geometry_tolerance
        probe_height = max(0.01, height - 2.0 * probe_margin)
        ideal_standoff = Part.makeCylinder(
            outer_radius - probe_margin,
            probe_height,
            App.Vector(x, y, base + probe_margin),
        ).cut(
            Part.makeCylinder(
                bore_radius + probe_margin,
                probe_height,
                App.Vector(x, y, base + probe_margin),
            )
        )
        standoff_fill = float(material.common(ideal_standoff).Volume) / max(float(ideal_standoff.Volume), 1e-9)
        values[hole["ref"]] = {
            "axis_error_mm": axis_error,
            "bore_center_xy_mm": measured_bore_center,
            "bore_diameter_mm": measured_bore_diameter,
            "bore_residual_mm3": residual,
            "bore_z_max_mm": bore_zmax,
            "bore_z_min_mm": bore_zmin,
            "concentric_error_mm": concentric_error,
            "continuous_bore": residual <= volume_tolerance and dimensions_pass,
            "annulus_fill_ratio": fill,
            "full_height_annulus_fill_ratio": standoff_fill,
            "outer_center_xy_mm": measured_outer_center,
            "outer_diameter_mm": measured_outer_diameter,
            "section_symmetric_difference_mm3": section_difference,
            "standoff_present": fill >= 0.95 and standoff_fill >= 0.95 and dimensions_pass,
            "x_mm": x,
            "y_mm": y,
        }
    return values


def main():
    rerendered_board = read_step(config["rerendered_board_step"])
    submitted_board = read_step(config["submitted_board_step"])
    submitted_parts, submitted_material, submitted_facets = mesh_solids(config["submitted_stl"])
    rendered_parts, rendered_material, rendered_facets = mesh_solids(config["rerendered_stl"])
    assembly = read_step(config["assembly_step"])
    _doc, objects = read_step_objects(config["assembly_step"])

    tray_obj = pick(objects, config["tray_bounds_mm"], "tray")
    lid_obj = pick(objects, config["lid_bounds_mm"], "lid")
    used_ids = {id(tray_obj), id(lid_obj)}
    board_obj = pick_group(objects, config["board_bounds_mm"], "installed PCB", used_ids)
    used_ids.update(id(value) for value in board_obj["members"])
    component_objects = {}
    for component in config["components"]:
        component_objects[component["ref"]] = pick_group(objects, component["bounds_mm"], "component " + component["ref"], used_ids)
        used_ids.update(id(value) for value in component_objects[component["ref"]]["members"])
    physical = [tray_obj, lid_obj, board_obj] + [component_objects[item["ref"]] for item in config["components"]]
    export_reference(physical, config["reference_bridge_obj"])

    submitted_tray = pick_shape(submitted_parts, config["tray_bounds_mm"], "submitted tray")
    submitted_lid = pick_shape(submitted_parts, config["lid_bounds_mm"], "submitted lid")
    tray = tray_obj["shape"]
    lid = lid_obj["shape"]
    board = board_obj["shape"]
    non_carrier_ids = {id(value) for role in [board_obj] + list(component_objects.values()) for value in role["members"]}
    carrier_shapes = [value["shape"] for value in objects if id(value) not in non_carrier_ids]
    material = Part.makeCompound(carrier_shapes)

    rerendered_board_installed = rerendered_board.copy()
    rerendered_board_installed.translate(
        App.Vector(0, 0, config["board_bounds_mm"][2] - rerendered_board.BoundBox.ZMin)
    )
    submitted_board_installed = submitted_board.copy()
    submitted_board_installed.translate(
        App.Vector(0, 0, config["board_bounds_mm"][2] - submitted_board.BoundBox.ZMin)
    )

    board_holes = {}
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        probe = hole["diameter_mm"] / 2.0 + 0.3
        board_holes[hole["ref"]] = {
            "rerendered_center_empty": not inside(rerendered_board, x, y, rerendered_board.BoundBox.Center.z),
            "rerendered_surrounding_material": inside(rerendered_board, x + probe, y, rerendered_board.BoundBox.Center.z),
            "submitted_center_empty": not inside(submitted_board, x, y, submitted_board.BoundBox.Center.z),
            "submitted_surrounding_material": inside(submitted_board, x + probe, y, submitted_board.BoundBox.Center.z),
        }

    component_geometry = {}
    interference = {"enclosure": {}}
    for component in config["components"]:
        ref = component["ref"]
        actual = component_objects[ref]["shape"]
        ideal = (
            cylinder_shape(component["cylinder_mm"])
            if component["shape"] == "cylinder"
            else box_shape(component["bounds_mm"])
        )
        component_geometry[ref] = {"metrics": metrics(actual), "vs_ideal": overlap(actual, ideal)}
        interference["enclosure"][ref] = float(material.common(actual).Volume)
    interference["enclosure"]["PCB"] = float(material.common(board).Volume)
    total_interference = sum(value for role in interference.values() for value in role.values())

    access_by_geometry = {}
    antenna_keepout_by_geometry = {}
    non_a1_component_shapes = [
        value["shape"] for ref, value in component_objects.items() if ref != "A1"
    ]
    for label, combined in (
        ("submitted_stl", submitted_material),
        ("assembly_step", material),
    ):
        access_by_geometry[label] = [access_metrics(combined, item) for item in config["accesses"]]
        antenna_keepout_by_geometry[label] = antenna_keepout_metrics(
            combined,
            non_a1_component_shapes if label == "assembly_step" else None,
        )

    side = {direction: side_clearance(material, board, direction) for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")}
    top_clearances = {
        ref: None if ref in config["open_component_refs"] else top_clearance(material, component_objects[ref]["shape"])
        for ref in component_objects
    }
    tray_sanity = {
        "floor": inside(tray, 0, 0, config["base_thickness_mm"] / 2.0),
        "cavity": not inside(tray, 0, 0, (config["base_thickness_mm"] + config["tray_outer_top_z_mm"]) / 2.0),
        "x_wall": inside(tray, config["enclosure_bbox_mm"][0] / 2.0 - config["wall_mm"] / 2.0, config["enclosure_bbox_mm"][1] / 2.0 - 2.0, 6.0),
        "y_wall": inside(tray, 0, config["enclosure_bbox_mm"][1] / 2.0 - config["wall_mm"] / 2.0, 6.0),
    }
    submitted_vs_rendered = overlap(submitted_material, rendered_material)
    assembly_vs_submitted = overlap(material, submitted_material)
    assembly_board_comparison = overlap(board, rerendered_board_installed)
    submitted_board_comparison = overlap(submitted_board, rerendered_board)
    assembly_submitted_board_comparison = overlap(board, submitted_board_installed)
    access_checks = {item["ref"]: item for item in access_by_geometry["submitted_stl"]}
    enclosure_volume = float(submitted_material.Volume)
    tray_volume = float(submitted_tray.Volume)
    lid_volume = float(submitted_lid.Volume)
    return {
        "rerendered_board": metrics(rerendered_board),
        "submitted_board": metrics(submitted_board),
        "submitted_board_symmetric_difference_mm3": submitted_board_comparison["symmetric_difference_volume_mm3"],
        "board_holes": board_holes,
        "assembly_board_symmetric_difference_mm3": assembly_board_comparison["symmetric_difference_volume_mm3"],
        "assembly_submitted_board_symmetric_difference_mm3": assembly_submitted_board_comparison["symmetric_difference_volume_mm3"],
        "submitted_stl": metrics(submitted_material),
        "rerendered_stl": metrics(rendered_material),
        "submitted_stl_facets": submitted_facets,
        "rerendered_stl_facets": rendered_facets,
        "submitted_stl_solid_count": len(submitted_parts),
        "rerendered_stl_solid_count": len(rendered_parts),
        "submitted_vs_rerendered": submitted_vs_rendered,
        "stl_symmetric_difference_mm3": submitted_vs_rendered["symmetric_difference_volume_mm3"],
        "step_stl_symmetric_difference_mm3": assembly_vs_submitted["symmetric_difference_volume_mm3"],
        "assembly": metrics(assembly),
        "assembly_object_count": len(objects),
        "tray": metrics(tray),
        "lid": metrics(lid),
        "board": metrics(board),
        "components": component_geometry,
        "tray_vs_submitted": overlap(tray, submitted_tray),
        "lid_vs_submitted": overlap(lid, submitted_lid),
        "lid_separation_mm": float(lid.BoundBox.ZMin - tray.BoundBox.ZMax),
        "tray_lid_intersection_mm3": float(tray.common(lid).Volume),
        "tray_sanity": tray_sanity,
        "standoff_checks": standoff_metrics(submitted_material),
        "access_by_geometry": access_by_geometry,
        "access_checks": access_checks,
        "antenna_keepout_by_geometry": antenna_keepout_by_geometry,
        "antenna_keepout_check": antenna_keepout_by_geometry["assembly_step"],
        "antenna_carrier_intersection_mm3": antenna_keepout_by_geometry["assembly_step"]["carrier_intersection_volume_mm3"],
        "antenna_component_intersection_mm3": antenna_keepout_by_geometry["assembly_step"]["non_a1_component_intersection_volume_mm3"],
        "interference_by_role_mm3": interference,
        "unintended_interference_volume_mm3": total_interference,
        "side_clearances_mm": side,
        "minimum_side_clearance_mm": min(value for value in side.values() if value is not None),
        "component_top_clearances_mm": top_clearances,
        "minimum_top_clearance_mm": min(value for value in top_clearances.values() if value is not None),
        "enclosure_bbox_mm": [submitted_material.BoundBox.XLength, submitted_material.BoundBox.YLength, submitted_material.BoundBox.ZLength],
        "enclosure_volume_mm3": enclosure_volume,
        "enclosure_mass_g": enclosure_volume * config["enclosure_density_g_cm3"] / 1000.0,
        "tray_volume_mm3": tray_volume,
        "tray_mass_g": tray_volume * config["enclosure_density_g_cm3"] / 1000.0,
        "lid_volume_mm3": lid_volume,
        "lid_mass_g": lid_volume * config["enclosure_density_g_cm3"] / 1000.0,
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
    geometry: dict[str, Any],
    rerendered_board_step: Path,
    rerendered_stl: Path,
) -> dict[str, Any]:
    freecad = resolve_executable("freecadcmd", ["/home/user/.local/bin/freecadcmd", "/usr/bin/freecadcmd", "/usr/bin/FreeCADCmd"])
    req = spec["requirements"]
    board = spec["board"]
    board_bottom = number(req["board_bottom_z_mm"], "board bottom")
    board_bounds = geometry["board_bounds_mm"]
    components = []
    for item in geometry["components"]:
        sx, sy, sz = item["body_bbox_mm"]
        component = {
            **item,
            "bounds_mm": [
                item["x_mm"] - sx / 2.0,
                item["y_mm"] - sy / 2.0,
                geometry["board_top_z_mm"],
                item["x_mm"] + sx / 2.0,
                item["y_mm"] + sy / 2.0,
                geometry["board_top_z_mm"] + sz,
            ],
        }
        if normalized(item["shape"]) == normalized("cylinder"):
            component["cylinder_mm"] = [
                item["x_mm"], item["y_mm"], sx / 2.0,
                geometry["board_top_z_mm"], geometry["board_top_z_mm"] + sz,
            ]
        components.append(component)
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
    enclosure = geometry["enclosure_bbox_mm"]
    config = {
        "rerendered_board_step": str(rerendered_board_step),
        "submitted_board_step": str(DESKTOP / "01_kicad_board.step"),
        "submitted_stl": str(DESKTOP / "02_openscad_enclosure.stl"),
        "rerendered_stl": str(rerendered_stl),
        "assembly_step": str(DESKTOP / "03_freecad_assembly.step"),
        "reference_bridge_obj": str(runtime / "assembly_reference.obj"),
        "enclosure_bbox_mm": enclosure,
        "tray_bounds_mm": geometry["tray_bounds_mm"],
        "lid_bounds_mm": geometry["lid_bounds_mm"],
        "board_bounds_mm": board_bounds,
        "components": components,
        "covered_component_refs": ["A1", "U1", "J1", "BT1"],
        "open_component_refs": ["TP1"],
        "mounting_holes": mounting_holes,
        "accesses": geometry["accesses"],
        "antenna_keepout": geometry["antenna_keepout"],
        "cavity_bounds_xy_mm": [number(value, "cavity bound") for value in req["inner_cavity_xy_bounds_mm"]],
        "wall_mm": number(req["wall_mm"], "wall"),
        "base_thickness_mm": number(req["base_thickness_mm"], "base"),
        "lid_thickness_mm": number(req["lid_thickness_mm"], "lid"),
        "tray_outer_top_z_mm": number(req["tray_outer_top_z_mm"], "tray top"),
        "standoff_height_mm": number(req["standoff_height_mm"], "standoff height"),
        "standoff_outer_diameter_mm": number(req["standoff_outer_diameter_mm"], "standoff OD"),
        "standoff_bore_diameter_mm": number(req["standoff_bore_diameter_mm"], "standoff bore"),
        "standoff_bore_overcut_mm": number(req["standoff_bore_overcut_mm"], "standoff bore overcut"),
        "standoff_bore_z_bounds_mm": [number(value, "standoff bore z") for value in req["standoff_bore_cutter_z_bounds_mm"]],
        "axis_tolerance_mm": number(req["axis_tolerance_mm"], "axis tolerance"),
        "access_center_tolerance_mm": number(req["access_center_tolerance_mm"], "access center tolerance"),
        "geometry_tolerance_mm": number(req["geometry_tolerance_mm"], "geometry tolerance"),
        "interference_tolerance_mm3": number(req["interference_volume_tolerance_mm3"], "interference tolerance"),
        "minimum_access_guard_mm": number(req["minimum_access_guard_mm"], "access guard"),
        "enclosure_density_g_cm3": number(req["enclosure_material_density_g_cm3"], "enclosure density"),
    }
    config_path = runtime / "cad_config.json"
    result_path = runtime / "cad_result.json"
    checker_path = runtime / "freecad_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(FREECAD_CHECKER, encoding="utf-8")
    old = (os.environ.get("ENGIWORLD_TASK10_CAD_CONFIG"), os.environ.get("ENGIWORLD_TASK10_CAD_RESULT"))
    os.environ["ENGIWORLD_TASK10_CAD_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK10_CAD_RESULT"] = str(result_path)
    try:
        completed = subprocess.run(
            [freecad, str(checker_path)], cwd=str(runtime), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
            timeout=150, check=False, env={**os.environ, "PYTHONPATH": ""},
        )
        output = completed.stdout + "\n" + completed.stderr
        shutdown_crash = completed.returncode == 1 and result_path.is_file() and "Program received signal SIGSEGV" in output and "closeAllDocuments" in output
        if completed.returncode != 0 and not shutdown_crash:
            fail(f"FreeCAD/OCC semantic checker failed with return code {completed.returncode}: {output[-4000:]}")
    finally:
        for key, value in zip(("ENGIWORLD_TASK10_CAD_CONFIG", "ENGIWORLD_TASK10_CAD_RESULT"), old):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    payload = json_file(result_path)
    if not payload.get("ok"):
        fail(f"FreeCAD/OCC checker rejected artifacts: {payload.get('error')}")
    result = payload.get("result")
    if not isinstance(result, dict):
        fail("FreeCAD/OCC checker returned no result")
    return result


def unique_records_by_ref(raw: Any, label: str) -> dict[str, dict[str, Any]]:
    if isinstance(raw, dict):
        return {str(ref): item for ref, item in raw.items() if isinstance(item, dict)}
    if isinstance(raw, list):
        result = {}
        for item in raw:
            if not isinstance(item, dict) or not item.get("ref"):
                continue
            ref = str(item["ref"])
            if ref in result:
                fail(f"{label} contains duplicate reference {ref}")
            result[ref] = item
        return result
    fail(f"{label} must be an object or list")


def report_accesses(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return unique_records_by_ref(report.get("access_checks"), "FreeCAD report access_checks")


def check_standoff_records(records: dict[str, dict[str, Any]], label: str, cad_result: dict[str, Any]) -> None:
    measured_all = cad_result.get("standoff_checks")
    if not isinstance(measured_all, dict) or set(records) != set(measured_all):
        fail(f"{label} does not match the geometry-derived standoff set")
    for ref, measured in measured_all.items():
        item = records[ref]
        if item.get("continuous_bore") is not True or item.get("standoff_present") is not True:
            fail(f"{label} records a failed standoff at {ref}")
        for field, tolerance in (
            ("x_mm", 0.1), ("y_mm", 0.1),
            ("outer_diameter_mm", 0.1), ("bore_diameter_mm", 0.1),
            ("axis_error_mm", 0.05), ("concentric_error_mm", 0.05),
        ):
            close(item.get(field), measured.get(field), tolerance, f"{label} {ref} {field}")
        close(item.get("residual_bore_material_volume_mm3"), measured.get("bore_residual_mm3"), 0.1001, f"{label} {ref} bore residual")


def check_access_report(
    item: dict[str, Any],
    expected: dict[str, Any],
    measured: dict[str, Any],
    geometry_tolerance: float,
    volume_tolerance: float,
    minimum_guard_mm: float,
    label: str = "FreeCAD report access_checks",
) -> None:
    if str(item.get("ref", expected["ref"])) != expected["ref"]:
        fail(f"{label} {expected['ref']} reference mismatch")
    actual_type = normalized(item.get("access_type", item.get("type")))
    allowed_types = (
        {normalized("side_window"), normalized("connector_window")}
        if expected["access_type"] == "side_window"
        else {normalized("top_bore"), normalized("access_bore"), normalized("test_access")}
    )
    if actual_type not in allowed_types:
        fail(f"{label} {expected['ref']} access type mismatch")
    reported_direction = item.get("direction", item.get("wall_direction"))
    if normalized(reported_direction) != normalized(expected["direction"]):
        fail(f"{label} {expected['ref']} access direction mismatch")
    verdicts = [item[key] for key in ("through", "continuous", "access_continuous", "continuity_pass") if key in item]
    if not verdicts or any(value is not True for value in verdicts):
        fail(f"{label} {expected['ref']} does not record a passing continuous access")
    if item.get("decision") is not None and normalized(item.get("decision")) != "PASS":
        fail(f"{label} {expected['ref']} decision is not pass")
    if item.get("pass") is not None and item.get("pass") is not True:
        fail(f"{label} {expected['ref']} pass flag is false")
    center_error = item.get("center_error_mm", item.get("axis_error_mm"))
    close(center_error, measured["center_error_mm"], geometry_tolerance, f"{label} {expected['ref']} center error")
    reported_residual = item.get(
        "residual_material_volume_mm3",
        item.get("path_residual_material_volume_mm3", item.get("carrier_intersection_volume_mm3")),
    )
    close(reported_residual, measured["residual_material_volume_mm3"], volume_tolerance + OCC_BOOLEAN_VOLUME_SLACK_MM3, f"{label} {expected['ref']} residual material")
    dimension_fields = (
        ("finished_width_mm", "finished_height_mm")
        if expected["access_type"] == "side_window"
        else ("finished_diameter_mm",)
    )
    for field in dimension_fields:
        close(item.get(field), measured[field], geometry_tolerance, f"{label} {expected['ref']} {field}")
    if expected["access_type"] == "top_bore":
        carrier_intersection = item.get(
            "carrier_intersection_volume_mm3",
            item.get("residual_material_volume_mm3", item.get("path_residual_material_volume_mm3")),
        )
        close(carrier_intersection, measured["carrier_intersection_volume_mm3"], volume_tolerance + OCC_BOOLEAN_VOLUME_SLACK_MM3, f"{label} {expected['ref']} carrier intersection")
        close(item.get("open_area_ratio"), measured["open_area_ratio"], 0.01, f"{label} {expected['ref']} open area ratio")
        close(item.get("guard_material_fraction"), measured["annular_guard_fill_ratio"], 0.02, f"{label} {expected['ref']} guard material fraction")
    else:
        if number(item.get("minimum_guard_mm"), f"{label} {expected['ref']} minimum guard") + geometry_tolerance < minimum_guard_mm:
            fail(f"{label} {expected['ref']} minimum guard is insufficient")
    contract_bounds = item.get("contract_cutter_bounds_mm", item.get("cutter_bounds_mm", item.get("bounds_mm")))
    close_vector(contract_bounds, expected["bounds_mm"], geometry_tolerance, f"{label} {expected['ref']} cutter bounds")
    close_vector(item.get("path_bounds_mm"), expected["path_bounds_mm"], geometry_tolerance, f"{label} {expected['ref']} path bounds")
    guard_verdicts = [item[key] for key in ("guard_material_present", "guard_wall_material_present", "minimum_guard_material_present") if key in item]
    if not guard_verdicts or any(value is not True for value in guard_verdicts):
        fail(f"{label} {expected['ref']} guard check is missing or failed")


def check_access_records(
    records: dict[str, dict[str, Any]],
    label: str,
    spec: dict[str, Any],
    geometry: dict[str, Any],
    cad_result: dict[str, Any],
) -> None:
    expected_by_ref = {item["ref"]: item for item in geometry["accesses"]}
    measured_by_ref = cad_result.get("access_checks")
    if not isinstance(measured_by_ref, dict) or set(records) != set(expected_by_ref) or set(records) != set(measured_by_ref):
        fail(f"{label} does not match the geometry-derived access set")
    req = spec["requirements"]
    geometry_tolerance = number(req["geometry_tolerance_mm"], "geometry tolerance")
    volume_tolerance = number(req["interference_volume_tolerance_mm3"], "interference tolerance")
    minimum_guard_mm = number(req["minimum_access_guard_mm"], "minimum access guard")
    for ref, expected in expected_by_ref.items():
        check_access_report(
            records[ref], expected, measured_by_ref[ref],
            geometry_tolerance, volume_tolerance, minimum_guard_mm, label,
        )


def check_cad_result(
    spec: dict[str, Any],
    geometry: dict[str, Any],
    result: dict[str, Any],
    report: dict[str, Any],
) -> None:
    req = spec["requirements"]
    geom_tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    volume_tol = number(req["interference_volume_tolerance_mm3"], "interference tolerance")
    mass_rel = number(req["mass_report_relative_tolerance"], "mass report relative tolerance")
    board_reference_volume = number(result["rerendered_board"]["volume_mm3"], "rerendered board volume")
    if number(result.get("submitted_board_symmetric_difference_mm3"), "submitted board symmetric difference") > max(0.5, board_reference_volume * 0.002):
        fail("submitted board STEP differs materially from a fresh KiCad export")
    if number(result.get("assembly_board_symmetric_difference_mm3"), "assembly board symmetric difference") > max(0.5, board_reference_volume * 0.002):
        fail("assembly STEP does not contain the fresh KiCad-exported PCB geometry")
    if number(result.get("assembly_submitted_board_symmetric_difference_mm3"), "assembly/submitted board symmetric difference") > max(0.5, board_reference_volume * 0.002):
        fail("assembly STEP does not contain the submitted KiCad board STEP geometry")
    if set(result.get("board_holes", {})) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("board STEP checker did not inspect all four mounting-hole axes")
    for ref, checks in result["board_holes"].items():
        if not all(bool(value) for value in checks.values()):
            fail(f"board STEP lacks real NPTH geometry at {ref}: {checks}")
    if int(result.get("submitted_stl_solid_count", 0)) < 2 or int(result.get("rerendered_stl_solid_count", 0)) < 2:
        fail("OpenSCAD geometry does not contain distinct tray and lid solids")
    close_vector(result["tray"]["bounds_mm"], geometry["tray_bounds_mm"], 0.2, "assembly tray bounds")
    close_vector(result["lid"]["bounds_mm"], geometry["lid_bounds_mm"], 0.2, "assembly lid bounds")
    for key in ("tray_vs_submitted", "lid_vs_submitted"):
        delta = number(result[key]["symmetric_difference_volume_mm3"], f"{key} difference")
        reference_volume = number(result["submitted_stl"]["volume_mm3"], "submitted STL volume")
        if delta > max(8.0, reference_volume * 0.005):
            fail(f"geometry handoff differs materially at {key}: {delta}")
    if number(result.get("tray_lid_intersection_mm3"), "tray/lid intersection") > volume_tol:
        fail("tray and lid are not distinct non-overlapping solids")
    close(result.get("lid_separation_mm"), req["lid_separation_mm"], geom_tol, "tray/lid separation")
    if not all(bool(value) for value in result.get("tray_sanity", {}).values()):
        fail(f"tray lacks a real floor, cavity, or walls: {result.get('tray_sanity')}")

    standoffs = result.get("standoff_checks", {})
    if set(standoffs) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("FreeCAD checker did not find exactly four required standoffs")
    for ref, values in standoffs.items():
        if values.get("continuous_bore") is not True or values.get("standoff_present") is not True:
            fail(f"invalid bored standoff geometry at {ref}: {values}")
        if (
            number(values.get("bore_residual_mm3"), f"{ref} bore residual") > volume_tol
            or number(values.get("annulus_fill_ratio"), f"{ref} section annulus") < 0.95
            or number(values.get("full_height_annulus_fill_ratio"), f"{ref} full-height annulus") < 0.95
        ):
            fail(f"invalid bored standoff geometry at {ref}: {values}")
        close(values.get("outer_diameter_mm"), req["standoff_outer_diameter_mm"], geom_tol, f"{ref} outer diameter")
        close(values.get("bore_diameter_mm"), req["standoff_bore_diameter_mm"], geom_tol, f"{ref} bore diameter")

    for ref, component in result.get("components", {}).items():
        delta = number(component["vs_ideal"]["symmetric_difference_volume_mm3"], f"{ref} proxy difference")
        if delta > max(volume_tol, number(component["metrics"]["volume_mm3"], f"{ref} volume") * 0.01):
            fail(f"assembly component {ref} is not a real expected body")
    expected_component_refs = {"A1", "U1", "J1", "BT1", "TP1"}
    expected_access_refs = {"J1", "TP1"}
    covered_component_refs = {"A1", "U1", "J1", "BT1"}
    if set(result.get("components", {})) != expected_component_refs:
        fail("assembly STEP does not retain all five expected component bodies")
    for source, values in result.get("access_by_geometry", {}).items():
        by_ref = {item.get("ref"): item for item in values if isinstance(item, dict)}
        if set(by_ref) != expected_access_refs:
            fail(f"{source} did not inspect every required access")
        for expected in geometry["accesses"]:
            item = by_ref[expected["ref"]]
            if not item.get("through"):
                fail(f"{source} {expected['ref']} is not a bounded continuous access: {item}")
            if normalized(item.get("direction")) != normalized(expected["direction"]):
                fail(f"{source} {expected['ref']} is cut through the wrong wall")
            if expected["access_type"] == "side_window":
                close(item.get("finished_width_mm"), expected["finished_width_mm"], geom_tol, f"{source} {expected['ref']} width")
                close(item.get("finished_height_mm"), expected["finished_height_mm"], geom_tol, f"{source} {expected['ref']} height")
                if number(item.get("minimum_guard_mm"), f"{source} {expected['ref']} guard") + geom_tol < number(req["minimum_access_guard_mm"], "minimum access guard"):
                    fail(f"{source} {expected['ref']} does not retain the minimum wall guard")
            else:
                close(item.get("finished_diameter_mm"), expected["finished_diameter_mm"], geom_tol, f"{source} {expected['ref']} diameter")
                close_vector(item.get("axis_xy_mm"), [expected["x_mm"], expected["y_mm"]], geom_tol, f"{source} {expected['ref']} axis")
                if number(item.get("carrier_intersection_volume_mm3"), f"{source} {expected['ref']} carrier intersection") > volume_tol:
                    fail(f"{source} {expected['ref']} top-bore path is obstructed")
                if number(item.get("open_area_ratio"), f"{source} {expected['ref']} open area ratio") + 1e-6 < 0.97:
                    fail(f"{source} {expected['ref']} top-bore area is insufficient")
            if item.get("guard_material_present") is not True:
                fail(f"{source} {expected['ref']} is unbounded or lacks real guard material")
    keepout_sources = result.get("antenna_keepout_by_geometry", {})
    if set(keepout_sources) != {"submitted_stl", "assembly_step"}:
        fail("FreeCAD checker did not inspect the A1 reserved volume in submitted and assembly carrier geometry")
    keepout_contract = geometry["antenna_keepout"]
    for source, keepout in keepout_sources.items():
        close_vector(keepout.get("bounds_mm"), keepout_contract["bounds_mm"], geom_tol, f"{source} A1 reserved bounds")
        if number(keepout.get("carrier_intersection_volume_mm3"), f"{source} A1 carrier intersection") > keepout_contract["maximum_carrier_intersection_mm3"]:
            fail(f"{source} carrier geometry intrudes into the A1 reserved volume")
        if number(keepout.get("minimum_radial_clearance_to_cavity_wall_mm"), f"{source} A1 radial clearance") + geom_tol < keepout_contract["minimum_radial_clearance_to_cavity_wall_mm"]:
            fail(f"{source} does not preserve the required A1 radial clearance")
        if source == "assembly_step" and number(keepout.get("non_a1_component_intersection_volume_mm3"), "assembly A1 component intersection") > keepout_contract["maximum_non_a1_component_intersection_mm3"]:
            fail("a non-A1 component intrudes into the A1 reserved volume")
        if keepout.get("pass") is not True:
            fail(f"{source} A1 reserved-volume geometry failed")
    if number(result.get("unintended_interference_volume_mm3"), "unintended interference") > volume_tol:
        fail("assembly has unintended enclosure interference with PCB or components")
    side_clearances = result.get("side_clearances_mm", {})
    if set(side_clearances) != {"X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS"}:
        fail("FreeCAD checker did not measure all four PCB side clearances")
    for direction, value in side_clearances.items():
        if value is None or number(value, f"side clearance {direction}") + geom_tol < number(req["minimum_side_clearance_mm"], "minimum side clearance"):
            fail(f"insufficient geometry-derived side clearance at {direction}: {value}")
    top_clearances = result.get("component_top_clearances_mm", {})
    if set(top_clearances) != expected_component_refs:
        fail("FreeCAD checker did not classify every component top clearance")
    if top_clearances.get("TP1") is not None:
        fail("TP1 has a full lid bore and must report unbounded top clearance")
    if min(number(top_clearances[ref], f"top clearance {ref}") for ref in covered_component_refs) + geom_tol < number(req["minimum_top_clearance_mm"], "minimum top clearance"):
        fail("assembly has insufficient component-to-lid clearance")
    close_vector(result.get("enclosure_bbox_mm"), geometry["enclosure_bbox_mm"], 0.2, "measured enclosure bbox")
    for field in ("enclosure_volume_mm3", "tray_volume_mm3", "lid_volume_mm3", "enclosure_mass_g", "tray_mass_g", "lid_mass_g"):
        if number(result.get(field), field) <= 0:
            fail(f"FreeCAD checker produced a non-positive {field}")
    close(
        result["enclosure_mass_g"],
        number(result["enclosure_volume_mm3"], "enclosure volume") * number(req["enclosure_material_density_g_cm3"], "density") / 1000.0,
        max(0.02, number(result["enclosure_mass_g"], "enclosure mass") * 0.005),
        "geometry-derived enclosure mass",
    )

    if normalized(report.get("decision")) not in {"PASS", "PASSED"}:
        fail("FreeCAD report decision must be pass")
    report_inputs = names_from(report.get("inputs", []), "FreeCAD report inputs")
    required_report_inputs = {"01_kicad_board.step", "02_openscad_enclosure.stl", "02_openscad_parameters.json"}
    if not required_report_inputs.issubset(report_inputs):
        fail("FreeCAD report inputs omit a required KiCad or OpenSCAD artifact")
    checks = report.get("checks")
    if not isinstance(checks, dict) or not checks or any(value is not True for value in checks.values()):
        fail("FreeCAD report checks must be nonempty and all exactly true")
    close_vector(report.get("enclosure_bbox_mm"), geometry["enclosure_bbox_mm"], geom_tol, "FreeCAD report enclosure bbox")
    metric_contract = {
        "enclosure_volume_mm3": (result["enclosure_volume_mm3"], max(2.0, result["enclosure_volume_mm3"] * 0.01)),
        "enclosure_mass_g": (result["enclosure_mass_g"], max(0.02, result["enclosure_mass_g"] * mass_rel)),
        "tray_volume_mm3": (result["tray_volume_mm3"], max(1.0, result["tray_volume_mm3"] * 0.01)),
        "tray_mass_g": (result["tray_mass_g"], max(0.02, result["tray_mass_g"] * mass_rel)),
        "lid_volume_mm3": (result["lid_volume_mm3"], max(1.0, result["lid_volume_mm3"] * 0.01)),
        "lid_mass_g": (result["lid_mass_g"], max(0.02, result["lid_mass_g"] * mass_rel)),
        "lid_separation_mm": (result["lid_separation_mm"], geom_tol),
        "minimum_side_clearance_mm": (min(result["side_clearances_mm"].values()), geom_tol),
        "minimum_top_clearance_mm": (result["minimum_top_clearance_mm"], geom_tol),
        "antenna_carrier_intersection_mm3": (result["antenna_carrier_intersection_mm3"], volume_tol),
        "antenna_component_intersection_mm3": (result["antenna_component_intersection_mm3"], volume_tol),
        "unintended_interference_volume_mm3": (result["unintended_interference_volume_mm3"], volume_tol),
    }
    required_metrics = {
        "enclosure_volume_mm3", "enclosure_mass_g", "minimum_side_clearance_mm",
        "minimum_top_clearance_mm", "antenna_carrier_intersection_mm3",
        "antenna_component_intersection_mm3",
        "unintended_interference_volume_mm3",
    }
    for field, (expected, tolerance) in metric_contract.items():
        if field in report:
            close(report[field], expected, tolerance, f"FreeCAD report {field}")
        elif field in required_metrics:
            fail(f"FreeCAD report is missing required metric {field}")
    report_keepout = report.get("antenna_keepout_check", report.get("antenna_keepout"))
    if not isinstance(report_keepout, dict):
        fail("FreeCAD report must contain geometry-derived antenna_keepout_check")
    measured_keepout = result["antenna_keepout_check"]
    for field, tolerance in (
        ("carrier_intersection_volume_mm3", volume_tol),
        ("non_a1_component_intersection_volume_mm3", volume_tol),
        ("minimum_radial_clearance_to_cavity_wall_mm", geom_tol),
    ):
        close(report_keepout.get(field), measured_keepout[field], tolerance, f"FreeCAD report A1 {field}")
    verdict = report_keepout.get("passed")
    if verdict is not True:
        fail("FreeCAD report does not record the A1 reserved volume as passing")
    if report.get("tray_bounds_mm") is not None:
        close_vector(report["tray_bounds_mm"], geometry["tray_bounds_mm"], geom_tol, "FreeCAD report tray bounds")
    if report.get("lid_bounds_mm") is not None:
        close_vector(report["lid_bounds_mm"], geometry["lid_bounds_mm"], geom_tol, "FreeCAD report lid bounds")
    report_side = report.get("side_clearances_mm")
    if not isinstance(report_side, dict) or not {"X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS"}.issubset(report_side):
        fail("FreeCAD report must include all four side_clearances_mm")
    for direction, measured in result["side_clearances_mm"].items():
        close(report_side[direction], measured, geom_tol, f"FreeCAD report side clearance {direction}")
    report_top = report.get("component_top_clearances_mm")
    if not isinstance(report_top, dict) or not expected_component_refs.issubset(report_top):
        fail("FreeCAD report must include every component top clearance")
    for ref, measured in result["component_top_clearances_mm"].items():
        if measured is None:
            if report_top[ref] is not None and normalized(report_top[ref]) not in {"UNBOUNDED", "NOTCOVERED", "OPEN"}:
                fail(f"FreeCAD report top clearance {ref} must be null or unbounded")
        else:
            close(report_top[ref], measured, geom_tol, f"FreeCAD report top clearance {ref}")
    for field in ("standoff_checks", "access_checks"):
        value = report.get(field)
        if not isinstance(value, (dict, list)) or not value:
            fail(f"FreeCAD report must include nonempty {field}")
    reported_standoffs = unique_records_by_ref(report["standoff_checks"], "FreeCAD report standoff_checks")
    if set(reported_standoffs) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("FreeCAD report standoff_checks must contain exactly MH1-MH4")
    check_standoff_records(reported_standoffs, "FreeCAD report standoff_checks", result)
    reported_accesses = report_accesses(report)
    if set(reported_accesses) != {"J1", "TP1"}:
        fail("FreeCAD report access_checks must contain exactly J1 and TP1")
    check_access_records(reported_accesses, "FreeCAD report access_checks", spec, geometry, result)


BLENDER_CHECKER = r'''
import json
import math
import os
import traceback

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree


config = json.load(open(os.environ["ENGIWORLD_TASK10_BLEND_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK10_BLEND_RESULT"]


def world_bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError("cannot compute bounds of empty geometry")
    return [min(point[i] for point in points) for i in range(3)] + [max(point[i] for point in points) for i in range(3)]


def object_bounds(obj):
    return world_bounds([obj])


def bounds_error(actual, expected):
    return max(abs(float(a) - float(b)) for a, b in zip(actual, expected))


def bounds_contained(actual, expected, tolerance=0.10):
    return all(actual[index] >= expected[index] - tolerance for index in range(3)) and all(actual[index] <= expected[index] + tolerance for index in range(3, 6))


def classify(objects, label):
    roles = {}
    used = set()
    for role, expected in config["role_bounds"].items():
        if role == "pcb" or role.startswith("component_"):
            matches = [obj for obj in objects if id(obj) not in used and bounds_contained(object_bounds(obj), expected)]
            if not matches or bounds_error(world_bounds(matches), expected) > 0.6: raise RuntimeError(label + " cannot identify physical role " + role + " by geometry")
            roles[role] = matches
            used.update(id(obj) for obj in matches)
            continue
        ranked = [(bounds_error(object_bounds(obj), expected), obj) for obj in objects if id(obj) not in used]
        ranked.sort(key=lambda item: item[0])
        if not ranked or ranked[0][0] > 0.6:
            raise RuntimeError(label + " cannot identify physical role " + role + " by geometry")
        roles[role] = [ranked[0][1]]
        used.add(id(ranked[0][1]))
    return roles


def mesh_data(objects):
    vertices = []
    polygons = []
    for obj in objects:
        offset = len(vertices)
        vertices.extend(tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices)
        polygons.extend(tuple(offset + index for index in polygon.vertices) for polygon in obj.data.polygons)
    if not vertices or not polygons:
        raise RuntimeError("empty role mesh")
    return {"vertices": vertices, "polygons": polygons}


def directed_distance(source, target, sample_limit=5000):
    tree = BVHTree.FromPolygons([Vector(value) for value in target["vertices"]], target["polygons"], all_triangles=False)
    if tree is None:
        raise RuntimeError("cannot build role comparison BVH")
    points = list(source["vertices"])
    for polygon in source["polygons"]:
        count = float(len(polygon))
        points.append(tuple(sum(source["vertices"][index][axis] for index in polygon) / count for axis in range(3)))
    stride = max(1, int(math.ceil(len(points) / float(sample_limit))))
    maximum = 0.0
    for point in points[::stride]:
        nearest = tree.find_nearest(Vector(point))
        if nearest is None:
            raise RuntimeError("role surface has no nearest comparison point")
        maximum = max(maximum, float(nearest[3]))
    return maximum


def role_meshes(roles):
    return {role: mesh_data(objects) for role, objects in roles.items()}


def compare_roles(label, actual, reference):
    if set(actual) != set(reference):
        raise RuntimeError(label + " physical role set mismatch")
    distances = {}
    for role in reference:
        first = actual[role]
        second = reference[role]
        distance = max(directed_distance(first, second), directed_distance(second, first))
        distances[role] = distance
        if distance > 0.6:
            raise RuntimeError(label + " geometry differs from assembly STEP role " + role + ": " + str(distance))
    return distances


def object_volume(obj):
    obj.data.calc_loop_triangles()
    total = 0.0
    for triangle in obj.data.loop_triangles:
        a, b, c = (obj.matrix_world @ obj.data.vertices[index].co for index in triangle.vertices)
        total += a.dot(b.cross(c)) / 6.0
    return abs(float(total))


def used_materials(obj):
    values = []
    used_indices = {int(polygon.material_index) for polygon in obj.data.polygons}
    for index, slot in enumerate(obj.material_slots):
        if index not in used_indices:
            continue
        if slot.material is not None and slot.material not in values:
            values.append(slot.material)
    return values


def material_signature(material):
    diffuse = tuple(float(value) for value in material.diffuse_color)
    node_color = diffuse
    metallic = 0.0
    if material.use_nodes:
        node = material.node_tree.nodes.get("Principled BSDF")
        if node is not None:
            node_color = tuple(float(value) for value in node.inputs["Base Color"].default_value)
            metallic = float(node.inputs["Metallic"].default_value)
    return (
        tuple(round(value, 2) for value in diffuse)
        + tuple(round(value, 2) for value in node_color)
        + (round(metallic, 2),)
    )


def physical_material_signatures(objects, roles):
    signatures = set()
    for role, role_objects in roles.items():
        if any(obj.hide_render or obj.hide_get() for obj in role_objects):
            raise RuntimeError("physical role is hidden from the review: " + role)
        materials = [material for obj in role_objects for material in used_materials(obj)]
        if not materials:
            raise RuntimeError("physical role has no actually assigned material: " + role)
        signatures.update(material_signature(material) for material in materials)
    return signatures


def overlay_matches(obj, expected):
    actual = object_bounds(obj)
    wanted = expected["bounds_mm"]
    if expected.get("role") == "antenna_reserved_volume" and expected.get("shape") == "cylinder":
        if bounds_error(actual, wanted) > 0.25:
            return False
        got = object_volume(obj)
        want = float(expected["volume_mm3"])
        return abs(got - want) <= max(5.0, want * 0.05)
    if expected.get("role") == "access_corridor" and expected.get("shape") == "box":
        # A review overlay may show only the wall penetration or extend inward to
        # the connector. Its transverse opening and passage through the outer
        # wall are the semantic requirements; the cutter's full axial length is
        # an OpenSCAD implementation detail.
        if max(abs(actual[index] - wanted[index]) for index in (1, 2, 4, 5)) > 0.65:
            return False
        inner_wall = float(expected["inner_wall_x_mm"])
        outer_wall = float(expected["outer_wall_x_mm"])
        actual_volume = object_volume(obj)
        wall_volume = (wanted[4] - wanted[1]) * abs(outer_wall - inner_wall) * (wanted[5] - wanted[2])
        spans_wall = (
            actual[0] <= min(inner_wall, outer_wall) + 0.65
            and actual[3] >= max(inner_wall, outer_wall) - 0.65
        )
        within_cutter = actual[0] >= wanted[0] - 0.65 and actual[3] <= wanted[3] + 0.65
        return (
            expected.get("direction") in {"X_MINUS", "X_PLUS"}
            and spans_wall
            and within_cutter
            and actual_volume >= wall_volume * 0.50
            and actual_volume <= expected["volume_mm3"] * 1.25
        )
    if bounds_error(actual, wanted) > 0.65:
        return False
    got = object_volume(obj)
    want = float(expected["volume_mm3"])
    return abs(got - want) <= max(2.0, want * 0.08)


def material_alpha(material):
    alpha = float(material.diffuse_color[3])
    if material.use_nodes and material.node_tree:
        node = material.node_tree.nodes.get("Principled BSDF")
        if node is not None and node.inputs.get("Alpha") is not None:
            alpha = min(alpha, float(node.inputs["Alpha"].default_value))
    return alpha


def hit_material(obj, polygon_index):
    if obj.type != "MESH" or polygon_index < 0 or polygon_index >= len(obj.data.polygons): return None
    slot_index = obj.data.polygons[polygon_index].material_index
    if slot_index < 0 or slot_index >= len(obj.material_slots): return None
    return obj.material_slots[slot_index].material


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
            origin = point - camera_forward * 10000.0
            ray_direction = camera_forward
            distance = 10000.1
        else:
            origin = camera.matrix_world.translation
            offset = point - origin
            distance = offset.length + 0.1
            ray_direction = offset.normalized()
        remaining = distance
        ray_origin = origin
        for _ in range(32):
            hit, location, _normal, polygon_index, hit_object, _matrix = scene.ray_cast(
                depsgraph,
                ray_origin,
                ray_direction,
                distance=remaining,
            )
            if not hit or hit_object is None:
                break
            if hit_object == obj or hit_object.name == obj.name:
                return True
            material = hit_material(hit_object, polygon_index)
            if material is None or material_alpha(material) >= 0.98:
                break
            advance = (location - ray_origin).length + 0.001
            remaining -= advance
            if remaining <= 0.0:
                break
            ray_origin = location + ray_direction * 0.001
    return False


def overlay_materials(objects, physical_signatures, visible_only, scene=None, camera=None):
    signatures = {}
    for expected in config["overlays"]:
        matches = [obj for obj in objects if overlay_matches(obj, expected)]
        if visible_only:
            matches = [
                obj for obj in matches
                if not obj.hide_render
                and not obj.hide_get()
                and scene is not None
                and camera is not None
                and camera_visible(scene, camera, obj)
            ]
        feature_signatures = {
            material_signature(material)
            for obj in matches
            for material in used_materials(obj)
            if material_signature(material) not in physical_signatures
        }
        if not feature_signatures:
            raise RuntimeError("missing visible review feature " + expected["id"])
        signatures[expected["id"]] = feature_signatures
    return {key: len(value) for key, value in signatures.items()}


def projected_bounds(scene, camera, obj):
    points = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
    return [min(point.x for point in points), min(point.y for point in points), max(point.x for point in points), max(point.y for point in points)]


def boxes_overlap(first, second, padding=0.002):
    return not (
        first[2] + padding <= second[0]
        or second[2] + padding <= first[0]
        or first[3] + padding <= second[1]
        or second[3] + padding <= first[1]
    )


def check_optional_labels(scene, camera):
    labels = [
        obj for obj in scene.objects
        if obj.type == "FONT" and not obj.hide_render and not obj.hide_get()
    ]
    return len(labels)


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
        indices = [index for index in range(len(first)) if index % 4 != 3]
        error = sum(abs(first[index] - second[index]) for index in indices) / len(indices)
        return max(0.0, 1.0 - error)
    finally:
        for image in list(bpy.data.images):
            if image.filepath in {first_path, second_path}:
                bpy.data.images.remove(image)


def import_obj(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=path,
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
    )
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects:
        raise RuntimeError("OBJ imported no mesh objects: " + path)
    return objects


def main():
    bpy.ops.wm.open_mainfile(filepath=config["blend_path"])
    scene = bpy.context.scene
    native = [obj for obj in scene.objects if obj.type == "MESH"]
    native_roles = classify(native, "native scene")
    physical_signatures = physical_material_signatures(native, native_roles)
    native_role_meshes = role_meshes(native_roles)

    camera = scene.camera
    if camera is None or camera.type != "CAMERA" or camera.hide_render or camera.data.type not in {"ORTHO", "PERSP"}:
        raise RuntimeError("native scene lacks an active visible engineering camera")
    direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
    target = Vector((0, 0, config["enclosure_bbox_mm"][2] / 2.0))
    toward = (target - camera.matrix_world.translation).normalized()
    if direction.dot(toward) < 0.75:
        raise RuntimeError("native scene camera is not aimed at the assembly")
    native_overlays = overlay_materials(native, physical_signatures, True, scene, camera)
    collections = {collection.name for obj in native for collection in obj.users_collection}
    visible_meshes = [obj for obj in native if not obj.hide_render and not obj.hide_get()]
    framed = [projected_bounds(scene, camera, obj) for obj in visible_meshes]
    if any(box[0] < -0.03 or box[1] < -0.03 or box[2] > 1.03 or box[3] > 1.03 for box in framed):
        raise RuntimeError("native scene camera does not frame the physical assembly")
    label_count = check_optional_labels(scene, camera)

    scene.render.resolution_x = 160
    scene.render.resolution_y = 120
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = config["rerender_path"]
    bpy.ops.render.render(write_still=True)
    similarity = image_similarity(config["submitted_render_path"], config["rerender_path"])
    native_camera = camera.name
    native_bounds = world_bounds(native)

    reference_objects = import_obj(config["reference_obj_path"])
    reference_roles = classify(reference_objects, "evaluator STEP reference")
    reference_role_meshes = role_meshes(reference_roles)
    native_distances = compare_roles("native scene", native_role_meshes, reference_role_meshes)

    bridge_objects = import_obj(config["bridge_obj_path"])
    bridge_roles = classify(bridge_objects, "FreeCAD bridge OBJ")
    bridge_distances = compare_roles("FreeCAD bridge OBJ", role_meshes(bridge_roles), reference_role_meshes)

    review_objects = import_obj(config["review_obj_path"])
    review_roles = classify(review_objects, "review OBJ")
    review_distances = compare_roles("review OBJ", role_meshes(review_roles), reference_role_meshes)
    review_physical_signatures = physical_material_signatures(review_objects, review_roles)
    review_overlays = overlay_materials(review_objects, review_physical_signatures, False)
    return {
        "active_camera": native_camera,
        "native_bounds_mm": native_bounds,
        "native_object_count": len(native),
        "native_overlay_material_counts": native_overlays,
        "review_overlay_material_counts": review_overlays,
        "role_collections": sorted(collections),
        "render_similarity": similarity,
        "native_reference_surface_distances_mm": native_distances,
        "bridge_reference_surface_distances_mm": bridge_distances,
        "review_reference_surface_distances_mm": review_distances,
        "bridge_object_count": len(bridge_objects),
        "review_object_count": len(review_objects),
        "visible_label_count": label_count,
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
    geometry: dict[str, Any],
) -> dict[str, Any]:
    blender = resolve_executable("blender", ["/snap/bin/blender", "/home/user/Applications/blender-*/blender"])
    req = spec["requirements"]
    board = spec["board"]
    board_bottom = number(req["board_bottom_z_mm"], "board bottom")
    board_top = geometry["board_top_z_mm"]
    enclosure = geometry["enclosure_bbox_mm"]
    role_bounds = {
        "tray": geometry["tray_bounds_mm"],
        "lid": geometry["lid_bounds_mm"],
        "pcb": [-board["bbox_mm"][0] / 2.0, -board["bbox_mm"][1] / 2.0, board_bottom, board["bbox_mm"][0] / 2.0, board["bbox_mm"][1] / 2.0, board_top],
    }
    for component in geometry["components"]:
        sx, sy, sz = component["body_bbox_mm"]
        role_bounds["component_" + component["ref"]] = [
            component["x_mm"] - sx / 2.0,
            component["y_mm"] - sy / 2.0,
            board_top,
            component["x_mm"] + sx / 2.0,
            component["y_mm"] + sy / 2.0,
            board_top + sz,
        ]
    overlays = []
    wall = number(req["wall_mm"], "wall thickness")
    for item in geometry["overlays"]:
        if item["shape"] == "box":
            bounds = item["bounds_mm"]
            volume = (bounds[3] - bounds[0]) * (bounds[4] - bounds[1]) * (bounds[5] - bounds[2])
        elif item["shape"] == "cylinder":
            bounds = item["bounds_mm"]
            _x, _y, radius, zmin, zmax = item["cylinder_mm"]
            volume = math.pi * radius * radius * (zmax - zmin)
        else:
            bounds = None
            volume = None
        entry = {
            "id": item["id"],
            "bounds_mm": bounds,
            "volume_mm3": volume,
            "shape": item["shape"],
            "role": item["role"],
            "direction": item.get("direction"),
            "material_group": item.get("ref", item["id"]),
        }
        if item["role"] == "access_corridor" and item["shape"] == "box":
            if item["direction"] not in {"X_MINUS", "X_PLUS"}:
                fail(f"unsupported Blender access-overlay direction {item['direction']}")
            if item["direction"] == "X_MINUS":
                entry["inner_wall_x_mm"] = -enclosure[0] / 2.0 + wall
                entry["outer_wall_x_mm"] = -enclosure[0] / 2.0
            else:
                entry["inner_wall_x_mm"] = enclosure[0] / 2.0 - wall
                entry["outer_wall_x_mm"] = enclosure[0] / 2.0
        overlays.append(entry)
    config = {
        "blend_path": str(DESKTOP / "04_blender_review.blend"),
        "reference_obj_path": str(runtime / "assembly_reference.obj"),
        "bridge_obj_path": str(DESKTOP / "03_freecad_assembly.obj"),
        "review_obj_path": str(DESKTOP / "04_blender_review.obj"),
        "submitted_render_path": str(DESKTOP / "04_blender_review.png"),
        "rerender_path": str(runtime / "blender_rerender.png"),
        "enclosure_bbox_mm": enclosure,
        "role_bounds": role_bounds,
        "overlays": overlays,
    }
    config_path = runtime / "blend_config.json"
    result_path = runtime / "blend_result.json"
    checker_path = runtime / "blender_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(BLENDER_CHECKER, encoding="utf-8")
    old = (os.environ.get("ENGIWORLD_TASK10_BLEND_CONFIG"), os.environ.get("ENGIWORLD_TASK10_BLEND_RESULT"))
    os.environ["ENGIWORLD_TASK10_BLEND_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK10_BLEND_RESULT"] = str(result_path)
    try:
        run_command(
            [blender, "--background", "--factory-startup", "--disable-autoexec", "--python", str(checker_path)],
            cwd=runtime,
            timeout=180,
            label="Blender native/bridge/review/render checker",
        )
    finally:
        for key, value in zip(("ENGIWORLD_TASK10_BLEND_CONFIG", "ENGIWORLD_TASK10_BLEND_RESULT"), old):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    payload = json_file(result_path)
    if not payload.get("ok"):
        fail(f"Blender checker rejected artifacts: {payload.get('error')}")
    result = payload.get("result")
    if not isinstance(result, dict):
        fail("Blender checker returned no result")
    return result


def check_blender_report(
    spec: dict[str, Any],
    geometry: dict[str, Any],
    cad_result: dict[str, Any],
    blender_result: dict[str, Any],
    report: dict[str, Any],
) -> None:
    if normalized(report.get("decision")) not in {"PASS", "PASSED"}:
        fail("Blender scene report decision must be pass")
    inputs = names_from(report.get("inputs", []), "Blender report inputs")
    if not {"03_freecad_assembly.obj", "03_freecad_clearance_report.json"}.issubset(inputs):
        fail("Blender report inputs omit a required FreeCAD artifact")
    for field, expected in (
        ("native_scene", "04_blender_review.blend"),
        ("review_obj", "04_blender_review.obj"),
        ("review_mtl", "04_blender_review.mtl"),
        ("render", "04_blender_review.png"),
    ):
        if Path(str(report.get(field, ""))).name != expected:
            fail(f"Blender report {field} mismatch")
    if str(report.get("active_camera", "")) != str(blender_result["active_camera"]):
        fail("Blender report active camera does not match native scene")
    visible_features = report.get("visible_features", report.get("visible_keepouts"))
    if not isinstance(visible_features, list) or not {"A1_Z_PLUS_reserved_volume", "J1_X_PLUS_window", "TP1_Z_PLUS_bore"}.issubset(set(visible_features)):
        fail("Blender report visible features omit A1, J1, or TP1")
    roles = report.get("object_roles")
    if not isinstance(roles, dict) or not roles:
        fail("Blender report object_roles must be a nonempty object")
    assignments = report.get("material_assignments")
    if not isinstance(assignments, dict) or not assignments:
        fail("Blender report material_assignments must be nonempty")
    camera = report.get("camera")
    if isinstance(camera, dict) and camera.get("framing_pass") is not True:
        fail("Blender report records a failed camera framing check")
    copied = report.get("freecad_metrics")
    if not isinstance(copied, dict):
        fail("Blender report freecad_metrics must be an object")
    copied_contract = {
        "enclosure_volume_mm3": cad_result["enclosure_volume_mm3"],
        "enclosure_mass_g": cad_result["enclosure_mass_g"],
        "minimum_side_clearance_mm": min(cad_result["side_clearances_mm"].values()),
        "minimum_top_clearance_mm": cad_result["minimum_top_clearance_mm"],
        "antenna_carrier_intersection_mm3": cad_result["antenna_carrier_intersection_mm3"],
        "antenna_component_intersection_mm3": cad_result["antenna_component_intersection_mm3"],
        "unintended_interference_volume_mm3": cad_result["unintended_interference_volume_mm3"],
    }
    for key, expected in copied_contract.items():
        close(copied.get(key), expected, max(0.1, abs(expected) * 0.02), f"Blender copied metric {key}")
    if normalized(copied.get("decision")) not in {"PASS", "PASSED"}:
        fail("Blender copied metrics do not retain the FreeCAD pass decision")
    copied_accesses = copied.get("access_checks")
    copied_access_map = unique_records_by_ref(copied_accesses, "Blender copied access_checks")
    if set(copied_access_map) != {"J1", "TP1"}:
        fail("Blender copied access_checks must contain exactly J1 and TP1")
    check_access_records(copied_access_map, "Blender copied access_checks", spec, geometry, cad_result)
    copied_keepout = copied.get("antenna_keepout_check")
    if not isinstance(copied_keepout, dict):
        fail("Blender copied antenna_keepout_check must be an object")
    for field in ("carrier_intersection_volume_mm3", "non_a1_component_intersection_volume_mm3", "minimum_radial_clearance_to_cavity_wall_mm"):
        close(copied_keepout.get(field), cad_result["antenna_keepout_check"][field], 0.1, f"Blender copied A1 {field}")
    copied_standoffs = copied.get("standoff_checks")
    copied_standoff_map = unique_records_by_ref(copied_standoffs, "Blender copied standoff_checks")
    if set(copied_standoff_map) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("Blender copied standoff_checks must contain exactly MH1-MH4")
    check_standoff_records(copied_standoff_map, "Blender copied standoff_checks", cad_result)
    if number(blender_result.get("render_similarity"), "Blender render similarity") < MIN_RENDER_SIMILARITY:
        fail("submitted Blender render does not match a fresh native-scene render")


def check_png(path: Path, *, minimum_width: int = 160, minimum_height: int = 120) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        fail(f"{path.name} is not a PNG file")
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
    if width < minimum_width or height < minimum_height or width > 8192 or height > 8192 or not compressed:
        fail(f"{path.name} is too small or malformed: {width}x{height}")
    if len(compressed) > 100 * 1024 * 1024:
        fail(f"{path.name} compressed payload is implausibly large")
    try:
        raw = zlib.decompress(bytes(compressed))
    except Exception as exc:
        fail(f"{path.name} pixel data cannot be decoded: {exc}")
    if len(raw) < width * height or len(set(raw)) < 16:
        fail(f"{path.name} appears blank or nearly uniform")


def names_from(value: Any, label: str) -> set[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        fail(f"{label} must be a list or string")
    return {Path(str(item)).name for item in value}


def unique_names_from(value: Any, label: str) -> set[str]:
    if not isinstance(value, list):
        fail(f"{label} must be a list")
    names = [Path(str(item)).name for item in value]
    if len(names) != len(set(names)):
        fail(f"{label} contains duplicate artifact names")
    return set(names)


def option_value(argv: list[str], options: set[str]) -> str | None:
    for index, value in enumerate(argv):
        if value in options and index + 1 < len(argv):
            return argv[index + 1]
        for option in options:
            if value.startswith(option + "="):
                return value.split("=", 1)[1]
    return None


def productive_argv_matches(software: str, argv: list[str], expected_outputs: set[str]) -> bool:
    args = [str(value) for value in argv[1:]]
    lowered = [value.lower() for value in args]
    if any(value in {"--version", "-v", "--help", "-h", "-?"} for value in lowered):
        return False
    basenames = {Path(value).name for value in args}
    if software == "KiCad":
        output = option_value(args, {"-o", "--output"})
        return lowered[:3] == ["pcb", "export", "step"] and output is not None and Path(output).name in expected_outputs and "01_kicad_board.kicad_pcb" in basenames
    if software == "OpenSCAD":
        output = option_value(args, {"-o", "--output"})
        return output is not None and Path(output).name in expected_outputs and "02_openscad_enclosure.scad" in basenames
    if software == "FreeCAD":
        return len([value for value in args if not value.startswith("-") and Path(value).suffix.lower() == ".py"]) == 1
    if software == "Blender":
        script = option_value(args, {"--python"})
        return "--background" in lowered and script is not None and Path(script).suffix.lower() == ".py"
    return False


def check_release_chain(spec: dict[str, Any], geometry: dict[str, Any], cad_result: dict[str, Any]) -> None:
    log = json_file(DESKTOP / "toolchain_invocation_log.json")
    actual = log.get("actual_invocations")
    legacy_commands = log.get("commands")
    if isinstance(actual, list) and isinstance(legacy_commands, list) and actual == legacy_commands:
        fail("toolchain log duplicates actual_invocations in the legacy commands field")
    commands = actual if isinstance(actual, list) else legacy_commands
    if not isinstance(commands, list) or len(commands) < 4:
        fail("toolchain log must contain productive commands; retries and helper calls are allowed")
    strict_expected = {
        "prepare": ({"board_input.kicad_pcb", "mechanical_requirements.json", "connector_keepouts.csv", "enclosure_seed.scad", "handoff_notes.md"}, {"01_kicad_board.kicad_pcb", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad", "02_openscad_enclosure.scad", "02_openscad_parameters.json"}),
        "KiCad": ({"01_kicad_board.kicad_pcb"}, {"01_kicad_board.step"}),
        "OpenSCAD": ({"01_kicad_parameters.scad", "02_openscad_enclosure.scad"}, {"02_openscad_enclosure.stl"}),
        "FreeCAD": ({"01_kicad_board.step", "02_openscad_enclosure.stl", "02_openscad_parameters.json"}, {"03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"}),
        "Blender": ({"03_freecad_assembly.obj", "03_freecad_clearance_report.json"}, {"04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"}),
    }
    trusted_by_name = {path.name: path for path in trusted_input_paths().values()}
    cursor = 0
    for stage in ["prepare", *SOFTWARE_SEQUENCE]:
        found = None
        required_inputs, required_outputs = strict_expected[stage]
        for index in range(cursor, len(commands)):
            entry = commands[index]
            if not isinstance(entry, dict) or entry.get("stage") != stage or entry.get("exit_code") != 0:
                continue
            argv = entry.get("argv")
            if not isinstance(argv, list) or not argv or shlex.split(str(entry.get("command", ""))) != argv or Path(str(entry.get("cwd", ""))).resolve() != PRODUCTIVE_DESKTOP:
                continue
            if not required_inputs.issubset(names_from(entry.get("inputs", []), "recorded inputs")) or not required_outputs.issubset(names_from(entry.get("outputs", []), "recorded outputs")):
                continue
            if any(Path(str(value)).parent != Path(".") for value in entry.get("outputs", [])):
                continue
            try:
                started = datetime.fromisoformat(str(entry["started_at_utc"]).replace("Z", "+00:00")); finished = datetime.fromisoformat(str(entry["finished_at_utc"]).replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError):
                continue
            if started.tzinfo is None or finished.tzinfo is None or finished < started:
                continue
            input_hashes, output_hashes = entry.get("input_sha256"), entry.get("output_sha256")
            if not isinstance(input_hashes, dict) or not required_inputs.issubset(input_hashes) or not isinstance(output_hashes, dict) or not required_outputs.issubset(output_hashes):
                continue
            if any(input_hashes[name] != sha256(trusted_by_name.get(name, DESKTOP / name)) for name in required_inputs) or any(output_hashes[name] != sha256(DESKTOP / name) for name in required_outputs):
                continue
            if stage != "prepare":
                token = {"KiCad": "kicad", "OpenSCAD": "openscad", "FreeCAD": "freecad", "Blender": "blender"}[stage]
                if token not in Path(argv[0]).name.lower() or not version_matches(stage, entry.get("version")) or not productive_argv_matches(stage, argv, required_outputs):
                    continue
            found = entry; cursor = index + 1; break
        if found is None:
            fail(f"toolchain log lacks an ordered, hashed, directly executed {stage} stage")
    helper_entries = list(commands)
    preparation = log.get("preparation")
    if isinstance(preparation, dict):
        helper_entries.append(preparation)
    elif isinstance(preparation, list):
        helper_entries.extend(item for item in preparation if isinstance(item, dict))
    trusted_inputs = {"board_input.kicad_pcb", "mechanical_requirements.json", "connector_keepouts.csv", "enclosure_seed.scad"}
    derived_handoffs = {
        "01_kicad_board.kicad_pcb", "01_kicad_board.step", "01_kicad_export.json",
        "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad",
        "02_openscad_enclosure.scad", "02_openscad_parameters.json",
    }
    recorded_inputs: set[str] = set()
    recorded_outputs: set[str] = set()
    for entry in helper_entries:
        if not isinstance(entry, dict):
            continue
        if not isinstance(entry.get("inputs", []), (str, list)) or not isinstance(entry.get("outputs", []), (str, list)):
            continue
        recorded_inputs.update(names_from(entry.get("inputs", []), "preparation inputs"))
        recorded_outputs.update(names_from(entry.get("outputs", []), "preparation outputs"))
    if not trusted_inputs.issubset(recorded_inputs) or not derived_handoffs.issubset(recorded_outputs):
        fail("toolchain log does not collectively record derivation of the handoffs from all trusted inputs")
    logged_sequence = log.get("required_software_sequence")
    if logged_sequence is not None and [normalized(value) for value in logged_sequence] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("toolchain log required software sequence mismatch")
    logged_versions = log.get("tool_versions") if isinstance(log.get("tool_versions"), dict) else {}
    expected = {
        "KiCad": {
            "input_any": {"board_input.kicad_pcb", "01_kicad_board.kicad_pcb"},
            "output_all": {"01_kicad_board.step"},
        },
        "OpenSCAD": {
            "input_all": {"02_openscad_enclosure.scad"},
            "input_any": {"01_kicad_parameters.scad", "02_openscad_parameters.json"},
            "output_all": {"02_openscad_enclosure.stl"},
        },
        "FreeCAD": {
            "input_all": {"01_kicad_board.step", "02_openscad_enclosure.stl", "02_openscad_parameters.json"},
            "output_all": {"03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
        },
        "Blender": {
            "input_all": {"03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
            "output_all": {"04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"},
        },
    }
    tokens = {"KiCad": "kicad", "OpenSCAD": "openscad", "FreeCAD": "freecad", "Blender": "blender"}

    def logged_version(software: str) -> str:
        for key, value in logged_versions.items():
            if normalized(key) == normalized(software):
                return str(value).strip()
        return ""

    def entry_software(entry: dict[str, Any]) -> str | None:
        label = normalized(" ".join(str(entry.get(key, "")) for key in ("software", "stage")))
        for software in SOFTWARE_SEQUENCE:
            if label and normalized(software) in label:
                return software
        command = str(entry.get("command", "")).lower()
        matches = [software for software in SOFTWARE_SEQUENCE if tokens[software] in command]
        return matches[0] if len(matches) == 1 else None

    previous = -1
    for sequence_index, software in enumerate(SOFTWARE_SEQUENCE):
        stage_entries: list[tuple[int, dict[str, Any]]] = []
        later = set(SOFTWARE_SEQUENCE[sequence_index + 1 :])
        for index, entry in enumerate(commands):
            if index <= previous or not isinstance(entry, dict):
                continue
            detected = entry_software(entry)
            if detected == software:
                stage_entries.append((index, entry))
            elif detected in later:
                break
        if not stage_entries:
            fail(f"toolchain log lacks an ordered productive {software} stage")
        inputs: set[str] = set()
        outputs: set[str] = set()
        versions: set[str] = set()
        for _index, entry in stage_entries:
            inputs.update(names_from(entry.get("inputs", []), f"{software} log inputs"))
            outputs.update(names_from(entry.get("outputs", []), f"{software} log outputs"))
            version = str(entry.get("version", entry.get("software_version", ""))).strip()
            if version:
                versions.add(version)
        if logged_version(software):
            versions.add(logged_version(software))
        contract = expected[software]
        if not (
            versions
            and contract.get("input_all", set()).issubset(inputs)
            and (not contract.get("input_any") or bool(contract["input_any"] & inputs))
            and contract.get("output_all", set()).issubset(outputs)
            and (not contract.get("output_any") or bool(contract["output_any"] & outputs))
        ):
            fail(f"toolchain log lacks complete inputs, outputs, or version evidence for {software}")
        previous = stage_entries[-1][0]

    package = json_file(DESKTOP / "final_release_package.json")
    if normalized(package.get("release_decision")) not in {"PASS", "PASSED"}:
        fail("final release package decision must be pass")
    if not isinstance(package.get("software_sequence"), list) or [normalized(value) for value in package["software_sequence"]] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("final release package software sequence mismatch")
    listed = unique_names_from(package.get("required_artifacts", []), "final required_artifacts")
    if listed != set(REQUIRED_ARTIFACTS):
        fail("final package required_artifacts is incomplete")
    produced = package.get("produced_artifacts")
    if unique_names_from(produced, "final produced_artifacts") != set(REQUIRED_ARTIFACTS):
        fail("final package produced_artifacts omits a required artifact")
    stage_outputs = package.get("stage_outputs")
    if not isinstance(stage_outputs, dict):
        fail("final package stage_outputs must be an object")
    if isinstance(stage_outputs, dict):
        expected_stage_outputs = {
            "KiCad": {"01_kicad_board.kicad_pcb", "01_kicad_board.step", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad"},
            "OpenSCAD": {"02_openscad_enclosure.scad", "02_openscad_enclosure.stl", "02_openscad_parameters.json"},
            "FreeCAD": {"03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
            "Blender": {"04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"},
        }
        for software, required in expected_stage_outputs.items():
            if unique_names_from(stage_outputs.get(software, []), f"{software} stage_outputs") != required:
                fail(f"final package {software} stage_outputs is incomplete")
    hashes = package.get("artifact_sha256")
    hashed_artifacts = set(REQUIRED_ARTIFACTS) - {"final_release_package.json"}
    if not isinstance(hashes, dict) or set(hashes) != hashed_artifacts:
        fail("final package artifact_sha256 is incomplete")
    if isinstance(hashes, dict):
        for name in hashed_artifacts:
            expected_hash = hashes[name]
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                fail(f"final package has an invalid SHA-256 for {name}")
            if expected_hash.lower() != sha256(DESKTOP / name):
                fail(f"final package hash mismatch for {name}")
    checks = package.get("checks")
    if not isinstance(checks, dict) or not checks or any(value is not True for value in checks.values()):
        fail("final package checks must be nonempty and all exactly true")
    versions = package.get("tool_versions")
    if not isinstance(versions, dict) or set(versions) != set(SOFTWARE_SEQUENCE):
        fail("final package tool_versions is incomplete")
    for software in SOFTWARE_SEQUENCE:
        if not version_matches(software, versions[software]) or str(versions[software]) != str(logged_versions.get(software, "")):
            fail(f"final package {software} version is not verified")
    metrics = package.get("key_metrics")
    if not isinstance(metrics, dict):
        fail("final package key_metrics must be an object")
    mass_rel = number(spec["requirements"]["mass_report_relative_tolerance"], "mass report relative tolerance")
    metric_contract = {
        "enclosure_volume_mm3": (cad_result["enclosure_volume_mm3"], max(2.0, cad_result["enclosure_volume_mm3"] * 0.01)),
        "enclosure_mass_g": (cad_result["enclosure_mass_g"], max(0.02, cad_result["enclosure_mass_g"] * mass_rel)),
        "tray_volume_mm3": (cad_result["tray_volume_mm3"], max(1.0, cad_result["tray_volume_mm3"] * 0.01)),
        "tray_mass_g": (cad_result["tray_mass_g"], max(0.02, cad_result["tray_mass_g"] * mass_rel)),
        "lid_volume_mm3": (cad_result["lid_volume_mm3"], max(1.0, cad_result["lid_volume_mm3"] * 0.01)),
        "lid_mass_g": (cad_result["lid_mass_g"], max(0.02, cad_result["lid_mass_g"] * mass_rel)),
        "lid_separation_mm": (cad_result["lid_separation_mm"], 0.1),
        "minimum_side_clearance_mm": (min(cad_result["side_clearances_mm"].values()), 0.1),
        "minimum_top_clearance_mm": (cad_result["minimum_top_clearance_mm"], 0.1),
        "antenna_carrier_intersection_mm3": (cad_result["antenna_carrier_intersection_mm3"], 0.1),
        "antenna_component_intersection_mm3": (cad_result["antenna_component_intersection_mm3"], 0.1),
        "unintended_interference_volume_mm3": (cad_result["unintended_interference_volume_mm3"], 0.1),
    }
    for field, (expected_value, tolerance) in metric_contract.items():
        close(metrics.get(field), expected_value, tolerance, f"final package {field}")
    final_accesses = unique_records_by_ref(metrics.get("access_checks"), "final package access_checks")
    if set(final_accesses) != {"J1", "TP1"}:
        fail("final package access_checks must contain exactly J1 and TP1")
    check_access_records(final_accesses, "final package access_checks", spec, geometry, cad_result)
    final_keepout = metrics.get("antenna_keepout_check")
    if not isinstance(final_keepout, dict):
        fail("final package antenna_keepout_check must be an object")
    for field in ("carrier_intersection_volume_mm3", "non_a1_component_intersection_volume_mm3", "minimum_radial_clearance_to_cavity_wall_mm"):
        close(final_keepout.get(field), cad_result["antenna_keepout_check"][field], 0.1, f"final A1 {field}")
    final_standoffs = unique_records_by_ref(metrics.get("standoff_checks"), "final package standoff_checks")
    if set(final_standoffs) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("final package standoff_checks must contain exactly MH1-MH4")
    check_standoff_records(final_standoffs, "final package standoff_checks", cad_result)


def main() -> bool:
    check_required_files()
    spec = build_spec(trusted_input_paths())
    check_answer_board(spec)
    check_kicad_handoff(spec)
    geometry = expected_geometry(spec)
    check_openscad_handoff(spec, geometry)
    freecad_report = json_file(DESKTOP / "03_freecad_clearance_report.json")
    blender_report = json_file(DESKTOP / "04_blender_scene_report.json")

    with tempfile.TemporaryDirectory(prefix="engiworld_task10_eval_") as temp_dir:
        runtime = Path(temp_dir)
        rerendered_board_step = runtime / "kicad_board_rerender.step"
        rerendered_stl = runtime / "openscad_rerender.stl"
        run_kicad_export(DESKTOP / "01_kicad_board.kicad_pcb", rerendered_board_step, runtime)
        openscad = resolve_executable("openscad", ["/usr/bin/openscad"])
        run_command(
            [openscad, "-o", str(rerendered_stl), str(DESKTOP / "02_openscad_enclosure.scad")],
            cwd=runtime,
            timeout=150,
            label="OpenSCAD tray/lid rerender",
        )
        if not rerendered_stl.is_file() or rerendered_stl.stat().st_size < 1000:
            fail("OpenSCAD rerender did not produce a substantial STL")
        submitted_mesh = load_mesh_metrics(DESKTOP / "02_openscad_enclosure.stl")
        rendered_mesh = load_mesh_metrics(rerendered_stl)
        compare_meshes(submitted_mesh, rendered_mesh, geometry)
        cad_result = run_freecad_checker(runtime, spec, geometry, rerendered_board_step, rerendered_stl)
        check_cad_result(spec, geometry, cad_result, freecad_report)
        blender_result = run_blender_checker(runtime, spec, geometry)
        check_blender_report(spec, geometry, cad_result, blender_result, blender_report)
        check_png(runtime / "blender_rerender.png", minimum_width=120, minimum_height=90)

    check_png(DESKTOP / "04_blender_review.png", minimum_width=320, minimum_height=240)
    check_release_chain(spec, geometry, cad_result)
    return True


if __name__ == "__main__":
    try:
        passed = main()
        detail = "PASS: task-10 artifacts satisfy the trusted semantic, geometry, bridge, and review contract.\n"
    except Exception as exc:
        passed = False
        detail = f"FAIL: {type(exc).__name__}: {exc}\n"
    if not passed:
        print(detail.rstrip(), file=sys.stderr)
    print("True" if passed else "False")
