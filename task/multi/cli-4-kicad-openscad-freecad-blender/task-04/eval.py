#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", Path.home() / "Desktop")).resolve()
SOFTWARE_SEQUENCE = ["KiCad", "OpenSCAD", "FreeCAD", "Blender"]
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
    override = os.environ.get("ENGIWORLD_TASK04_SPEC_DIR")
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
            "board": DESKTOP / "_eval_task04_board_input.kicad_pcb",
            "requirements": DESKTOP / "_eval_task04_mechanical_requirements.json",
            "connectors": DESKTOP / "_eval_task04_connector_keepouts.csv",
            "seed": DESKTOP / "_eval_task04_enclosure_seed.scad",
            "notes": DESKTOP / "_eval_task04_handoff_notes.md",
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
        "ref", "kind", "access_type", "direction", "body_x_mm", "body_y_mm",
        "finished_width_mm", "finished_height_mm", "vertical_margin_mm",
    }
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        if not required.issubset(row):
            fail("trusted connector CSV lacks required columns")
        ref = str(row["ref"]).strip()
        if not ref or ref in result:
            fail(f"trusted connector CSV has invalid or duplicate ref {ref!r}")
        result[ref] = row
    if set(result) != {"J1", "J2"}:
        fail("trusted connector CSV must define exactly J1 and J2")
    expected_directions = {"J1": "X_PLUS", "J2": "X_MINUS"}
    for ref, direction in expected_directions.items():
        row = result[ref]
        if normalized(row.get("access_type")) != normalized("side_window"):
            fail(f"trusted connector {ref} must be a side_window")
        if normalized(row.get("direction")) != normalized(direction):
            fail(f"trusted connector {ref} must use {direction}")
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
        "lid_inner_z_mm", "lid_separation_mm", "lid_thickness_mm",
        "mass_report_relative_tolerance", "minimum_access_guard_mm",
        "minimum_rib_keepout_clearance_mm", "minimum_side_clearance_mm",
        "minimum_top_clearance_mm", "required_ribs", "rib_exclusion",
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
    close(req["tray_outer_top_z_mm"], number(req["lid_inner_z_mm"], "lid inner") - number(req["lid_separation_mm"], "lid separation"), tol, "tray/lid separation")
    close(number(req["lid_inner_z_mm"], "lid inner") + number(req["lid_thickness_mm"], "lid thickness"), enclosure[2], tol, "lid outer top")
    close(number(req["base_thickness_mm"], "base thickness") + number(req["standoff_height_mm"], "standoff height"), req["board_bottom_z_mm"], tol, "standoff installed height")
    close(req["mount_hole_diameter_mm"], board["footprints"].get("MH1", {}).get("hole_diameter_mm"), number(req["axis_tolerance_mm"], "axis tolerance"), "trusted mounting-hole diameter")
    expected_refs = {"Q1", "Q2", "Q3", "J1", "J2", "MH1", "MH2", "MH3", "MH4"}
    if set(board["footprints"]) != expected_refs:
        fail(f"trusted KiCad board refs mismatch: expected {sorted(expected_refs)}, got {sorted(board['footprints'])}")
    for ref, connector in connectors.items():
        footprint = board["footprints"].get(ref)
        if footprint is None:
            fail(f"trusted access {ref} is absent from the KiCad board")
        expected_height = number(footprint["height_mm"], f"{ref} height") + 2.0 * number(
            connector["vertical_margin_mm"], f"{ref} vertical margin"
        )
        close(connector["finished_height_mm"], expected_height, 1e-6, f"{ref} finished height")
        if number(connector["finished_width_mm"], f"{ref} finished width") <= 0:
            fail(f"trusted side access {ref} has non-positive width")
    components = req.get("component_bodies")
    if not isinstance(components, dict):
        fail("trusted requirements component_bodies must be an object")
    if set(components) != {"Q1", "Q2", "Q3", "J1", "J2"}:
        fail("trusted component_bodies must define exactly Q1, Q2, Q3, J1, and J2")
    for ref, body in components.items():
        if not isinstance(body, dict) or body.get("shape") != "box":
            fail(f"trusted component body {ref} must be a box")
        bbox = body.get("bbox_mm")
        if not isinstance(bbox, list) or len(bbox) != 3 or min(number(value, f"{ref} body") for value in bbox) <= 0:
            fail(f"trusted component body {ref} has invalid bbox_mm")
    for ref, connector in connectors.items():
        body = components[ref]["bbox_mm"]
        close(connector["body_x_mm"], body[0], tol, f"trusted {ref} body_x_mm")
        close(connector["body_y_mm"], body[1], tol, f"trusted {ref} body_y_mm")
    ribs = req["required_ribs"]
    if not isinstance(ribs, list) or {str(item.get("id")) for item in ribs if isinstance(item, dict)} != {"RIB_NEG_Y", "RIB_POS_Y"}:
        fail("trusted requirements must define RIB_NEG_Y and RIB_POS_Y")
    if any(normalized(item.get("shape")) != "SOLIDRECTANGULARPRISMFILLINGBOUNDS" for item in ribs):
        fail("trusted required ribs must be solid rectangular prisms filling their bounds")
    if set(req["rib_exclusion"].get("keepout_refs", [])) != {"Q1", "Q2", "Q3"}:
        fail("trusted rib exclusion must use Q1, Q2, and Q3")
    board_top = number(req["board_bottom_z_mm"], "board bottom") + board["thickness_mm"]
    tallest = max(number(board["footprints"][ref]["height_mm"], f"{ref} height") for ref in components)
    if number(req["lid_inner_z_mm"], "lid inner") - (board_top + tallest) + tol < number(req["minimum_top_clearance_mm"], "minimum top clearance"):
        fail("trusted contract cannot satisfy its minimum top clearance")
    return {"board": board, "requirements": req, "connectors": connectors, "paths": paths}


def check_required_files() -> None:
    for name in REQUIRED_ARTIFACTS:
        path = DESKTOP / name
        if not path.is_file():
            fail(f"missing required artifact {name}")
        size = path.stat().st_size
        if size == 0:
            fail(f"required artifact {name} is empty")
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
            if str(row.get("hole_diameter_mm", "")).strip():
                close(row.get("hole_diameter_mm"), footprint["hole_diameter_mm"], tol, f"map {ref} hole")
            elif str(row.get("keepout_radius_mm", "")).strip():
                close(2.0 * number(row.get("keepout_radius_mm"), f"map {ref} radius"), footprint["hole_diameter_mm"], tol, f"map {ref} hole")
            else:
                fail(f"mechanical map {ref} lacks mounting-hole diameter")
            if normalized(row.get("role")) != normalized("standoff_axis"):
                fail(f"mechanical map {ref} is not a standoff axis")
        else:
            close(row.get("height_mm"), footprint["height_mm"], tol, f"map {ref} height")
            close(row.get("keepout_radius_mm"), footprint["keepout_radius_mm"], tol, f"map {ref} radius")
        if ref in connectors:
            connector = connectors[ref]
            for field in (
                "body_x_mm", "body_y_mm", "finished_width_mm", "finished_height_mm",
                "vertical_margin_mm",
            ):
                if str(row.get(field, "")).strip():
                    close(row.get(field), connector[field], tol, f"map {ref} {field}")
            if str(row.get("access_type", "")).strip() and normalized(row.get("access_type")) != normalized(connector["access_type"]):
                fail(f"mechanical map {ref} access_type mismatch")
            if str(row.get("direction", "")).strip() and normalized(row.get("direction")) != normalized(connector["direction"]):
                fail(f"mechanical map {ref} direction mismatch")

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
        close_vector(item.get("body_bbox_mm"), req["component_bodies"][ref]["bbox_mm"], tol, f"export {ref} body")
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
    keepout_columns = {}
    for ref in ("Q1", "Q2", "Q3", "J1", "J2"):
        footprint = board["footprints"][ref]
        sx, sy, sz = [number(value, f"{ref} body") for value in req["component_bodies"][ref]["bbox_mm"]]
        x, y = footprint["x_mm"], footprint["y_mm"]
        bounds = [x - sx / 2.0, y - sy / 2.0, board_top, x + sx / 2.0, y + sy / 2.0, board_top + sz]
        components.append({"ref": ref, "x_mm": x, "y_mm": y, "body_bbox_mm": [sx, sy, sz], "bounds_mm": bounds})
        if ref.startswith("Q"):
            keepout_columns[ref] = [
                x, y, footprint["keepout_radius_mm"],
                number(req["base_thickness_mm"], "base thickness"),
                number(req["lid_inner_z_mm"], "lid inner"),
            ]
    accesses = []
    overcut = number(req["access_overcut_mm"], "access overcut")
    for ref in ("J1", "J2"):
        connector = spec["connectors"][ref]
        footprint = board["footprints"][ref]
        width = number(connector["finished_width_mm"], f"{ref} width")
        height = number(connector["finished_height_mm"], f"{ref} height")
        center_z = board_top + footprint["height_mm"] / 2.0
        if connector["direction"] == "X_PLUS":
            x1, x2 = footprint["x_mm"] - number(connector["body_x_mm"], f"{ref} body x") / 2.0, half_x + overcut
        else:
            x1, x2 = -half_x - overcut, footprint["x_mm"] + number(connector["body_x_mm"], f"{ref} body x") / 2.0
        bounds = [x1, footprint["y_mm"] - width / 2.0, center_z - height / 2.0, x2, footprint["y_mm"] + width / 2.0, center_z + height / 2.0]
        accesses.append({
            "ref": ref, "access_type": "side_window", "direction": connector["direction"],
            "bounds_mm": bounds, "finished_width_mm": width, "finished_height_mm": height,
            "center_y_mm": footprint["y_mm"], "center_z_mm": center_z,
        })
    ribs = []
    for item in req["required_ribs"]:
        bounds = [number(value, f"{item.get('id')} bounds") for value in item["bounds_mm"]]
        ribs.append({"id": str(item["id"]), "bounds_mm": bounds})
    standoffs = []
    for ref in ("MH1", "MH2", "MH3", "MH4"):
        footprint = board["footprints"][ref]
        standoffs.append({"ref": ref, "x_mm": footprint["x_mm"], "y_mm": footprint["y_mm"]})

    overlays = []
    for ref, cylinder in keepout_columns.items():
        overlays.append({"id": f"{ref}_projected_keepout_column", "ref": ref, "role": "projected_keepout_column", "shape": "cylinder", "cylinder_mm": cylinder})
    for rib in ribs:
        overlays.append({"id": f"{rib['id']}_geometry_review", "ref": rib["id"], "role": "rib_review", "shape": "box", "bounds_mm": rib["bounds_mm"]})
    for access in accesses:
        overlays.append({"id": f"{access['ref']}_{access['direction']}_access_corridor", "ref": access["ref"], "role": "access_corridor", "shape": "box", "direction": access["direction"], "bounds_mm": access["bounds_mm"]})
        xmin, ymin, zmin, xmax, ymax, zmax = access["bounds_mm"]
        if access["direction"] == "X_PLUS":
            start, end = [xmin + 0.8, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0], [xmax + 7.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0]
        else:
            start, end = [xmax - 0.8, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0], [xmin - 7.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0]
        overlays.append({"id": f"{access['ref']}_{access['direction']}_direction", "ref": access["ref"], "role": "direction_arrow", "shape": "arrow", "direction": access["direction"], "start_mm": start, "end_mm": end})
    return {
        "enclosure_bbox_mm": enclosure, "tray_bounds_mm": tray_bounds, "lid_bounds_mm": lid_bounds,
        "board_bounds_mm": board_bounds, "board_top_z_mm": board_top, "components": components,
        "keepout_columns": keepout_columns, "accesses": accesses, "ribs": ribs,
        "standoffs": standoffs, "overlays": overlays,
    }


def check_openscad_handoff(spec: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    req = spec["requirements"]
    tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    handoff_text = (DESKTOP / "01_kicad_parameters.scad").read_text(encoding="utf-8")
    source_text = (DESKTOP / "02_openscad_enclosure.scad").read_text(encoding="utf-8")
    uncommented = re.sub(r"/\*.*?\*/|//[^\n]*", "", handoff_text, flags=re.DOTALL)
    if len(re.findall(r"(?m)^\s*[A-Za-z_$][A-Za-z0-9_$]*\s*=", uncommented)) < 8:
        fail("01_kicad_parameters.scad is not a substantial parameter handoff")
    if re.search(r"(?im)^\s*include\s*<\s*(?:[^>]+/)?01_kicad_parameters\.scad\s*>", source_text) is None:
        fail("OpenSCAD source does not consume 01_kicad_parameters.scad")
    params = json_file(DESKTOP / "02_openscad_parameters.json")
    close_vector(params.get("board_bbox_mm"), spec["board"]["bbox_mm"], tol, "OpenSCAD board bbox")
    close_vector(params.get("enclosure_bbox_mm"), geometry["enclosure_bbox_mm"], tol, "OpenSCAD enclosure bbox")
    for field in (
        "wall_mm", "base_thickness_mm", "tray_outer_top_z_mm", "lid_inner_z_mm",
        "lid_separation_mm", "lid_thickness_mm", "board_bottom_z_mm", "standoff_height_mm",
        "standoff_outer_diameter_mm", "standoff_bore_diameter_mm", "standoff_bore_overcut_mm",
        "access_overcut_mm",
    ):
        close(params.get(field), req[field], tol, f"OpenSCAD {field}")
    close(params.get("board_top_z_mm"), geometry["board_top_z_mm"], tol, "OpenSCAD board top")
    if params.get("tray_bounds_mm") is not None:
        close_vector(params["tray_bounds_mm"], geometry["tray_bounds_mm"], tol, "OpenSCAD tray bounds")
    close_vector(params.get("lid_bounds_mm"), geometry["lid_bounds_mm"], tol, "OpenSCAD lid bounds")
    actual_ribs = {str(item.get("id")): item for item in params.get("required_ribs", []) if isinstance(item, dict)}
    for expected in geometry["ribs"]:
        actual = actual_ribs.get(expected["id"])
        if actual is None:
            fail(f"OpenSCAD parameters lack rib {expected['id']}")
        close_vector(actual.get("bounds_mm"), expected["bounds_mm"], tol, f"OpenSCAD {expected['id']} bounds")
    actual_columns = {str(item.get("ref")): item for item in params.get("rib_keepout_columns", []) if isinstance(item, dict)}
    for ref, expected in geometry["keepout_columns"].items():
        actual = actual_columns.get(ref)
        if actual is None:
            fail(f"OpenSCAD parameters lack projected keepout column {ref}")
        close_vector(
            [actual.get("x_mm"), actual.get("y_mm"), actual.get("radius_mm"), actual.get("z_min_mm"), actual.get("z_max_mm")],
            expected, tol, f"OpenSCAD {ref} projected column",
        )
    actual_standoffs = {str(item.get("ref")): item for item in params.get("standoff_axes", []) if isinstance(item, dict)}
    for expected in geometry["standoffs"]:
        actual = actual_standoffs.get(expected["ref"])
        if actual is None:
            fail(f"OpenSCAD parameters lack standoff {expected['ref']}")
        close(actual.get("x_mm"), expected["x_mm"], tol, f"OpenSCAD {expected['ref']} x")
        close(actual.get("y_mm"), expected["y_mm"], tol, f"OpenSCAD {expected['ref']} y")
    actual_accesses = []
    for key in ("side_windows", "accesses"):
        value = params.get(key)
        if isinstance(value, list):
            actual_accesses.extend(item for item in value if isinstance(item, dict))
    by_ref = {str(item.get("ref")): item for item in actual_accesses}
    for expected in geometry["accesses"]:
        actual = by_ref.get(expected["ref"])
        if actual is None:
            fail(f"OpenSCAD parameters lack access {expected['ref']}")
        if normalized(actual.get("direction")) != normalized(expected["direction"]):
            fail(f"OpenSCAD access {expected['ref']} direction mismatch")
        close_vector(actual.get("bounds_mm"), expected["bounds_mm"], tol, f"OpenSCAD {expected['ref']} bounds")
        close(actual.get("finished_width_mm"), expected["finished_width_mm"], tol, f"OpenSCAD {expected['ref']} width")
        close(actual.get("finished_height_mm"), expected["finished_height_mm"], tol, f"OpenSCAD {expected['ref']} height")
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
    except Exception as exc:
        fail(f"evaluator mesh dependencies unavailable: {exc}")
    try:
        data = path.read_bytes()
        triangles = None
        if len(data) >= 84:
            facet_count = struct.unpack_from("<I", data, 80)[0]
            if facet_count > 0 and 84 + facet_count * 50 == len(data):
                dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
                triangles = np.asarray(np.frombuffer(data, dtype=dtype, count=facet_count, offset=84)["vertices"], dtype=float)
        if triangles is None:
            values = []
            for line in data.decode("utf-8", errors="strict").splitlines():
                fields = line.strip().split()
                if fields and fields[0].lower() == "vertex" and len(fields) == 4:
                    values.append([float(value) for value in fields[1:]])
            if not values or len(values) % 3:
                fail(f"{path.name} is not a valid binary or ASCII STL triangle mesh")
            triangles = np.asarray(values, dtype=float).reshape((-1, 3, 3))
        if not np.isfinite(triangles).all():
            fail(f"{path.name} contains non-finite coordinates")

        vertex_ids = {}
        vertices = []
        faces = []
        seen_faces = set()
        for triangle in triangles:
            ids = []
            for raw in triangle:
                key = tuple(round(float(value), 8) for value in raw)
                if key not in vertex_ids:
                    vertex_ids[key] = len(vertices)
                    vertices.append(key)
                ids.append(vertex_ids[key])
            if len(set(ids)) != 3:
                continue
            points = np.asarray([vertices[index] for index in ids], dtype=float)
            if float(np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0]))) <= 1e-12:
                continue
            canonical = tuple(sorted(ids))
            if canonical not in seen_faces:
                seen_faces.add(canonical)
                faces.append(tuple(ids))
        if len(vertices) < 20 or len(faces) < 30:
            fail(f"{path.name} has implausibly little triangle geometry")

        edge_uses = {}
        for face_index, (a, b, c) in enumerate(faces):
            for start, end in ((a, b), (b, c), (c, a)):
                edge = (min(start, end), max(start, end))
                edge_uses.setdefault(edge, []).append((face_index, 1 if start < end else -1))
        if any(len(uses) != 2 for uses in edge_uses.values()):
            fail(f"{path.name} must be a watertight mesh")
        if any(uses[0][1] + uses[1][1] != 0 for uses in edge_uses.values()):
            fail(f"{path.name} must be consistently wound")

        vertex_array = np.asarray(vertices, dtype=float)
        face_array = np.asarray(faces, dtype=int)

        def calculate(face_indices):
            points = vertex_array[face_array[np.asarray(face_indices, dtype=int)]]
            cross = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
            signed = np.einsum("ij,ij->i", points[:, 0], np.cross(points[:, 1], points[:, 2])) / 6.0
            signed_volume = float(signed.sum())
            used = np.unique(face_array[np.asarray(face_indices, dtype=int)].reshape(-1))
            local_vertices = vertex_array[used]
            local_bounds = np.asarray([local_vertices.min(axis=0), local_vertices.max(axis=0)], dtype=float)
            center = ((points.sum(axis=1) / 4.0) * signed[:, None]).sum(axis=0) / signed_volume
            return local_bounds, abs(signed_volume), float((np.linalg.norm(cross, axis=1) * 0.5).sum()), center

        neighbors = [set() for _ in faces]
        for uses in edge_uses.values():
            first, second = uses[0][0], uses[1][0]
            neighbors[first].add(second)
            neighbors[second].add(first)
        groups = []
        unseen = set(range(len(faces)))
        while unseen:
            seed = unseen.pop()
            group = {seed}
            stack = [seed]
            while stack:
                adjacent = neighbors[stack.pop()] & unseen
                unseen.difference_update(adjacent)
                group.update(adjacent)
                stack.extend(adjacent)
            groups.append(sorted(group))

        bounds, volume, area, center = calculate(range(len(faces)))
        if volume <= 0 or area <= 0:
            fail(f"{path.name} must be a positive-volume mesh")
        components = []
        for group in groups:
            if len(group) < 4:
                continue
            cbounds, component_volume, _component_area, _component_center = calculate(group)
            components.append({
                "bounds": [float(value) for value in cbounds.reshape(-1)],
                "bbox": [float(value) for value in cbounds[1] - cbounds[0]],
                "volume": component_volume,
                "faces": len(group),
            })
        return {
            "bounds": [float(value) for value in bounds.reshape(-1)],
            "bbox": [float(value) for value in bounds[1] - bounds[0]],
            "volume": volume,
            "area": area,
            "center": [float(value) for value in center],
            "vertices": len(vertices),
            "faces": len(faces),
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


config = json.load(open(os.environ["ENGIWORLD_TASK04_CAD_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK04_CAD_RESULT"]


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
    doc = App.newDocument("Task04EvalAssembly")
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


def bounds_contained(actual, expected, tolerance):
    return all(actual[index] >= expected[index] - tolerance for index in range(3)) and all(
        actual[index] <= expected[index] + tolerance for index in range(3, 6)
    )


def group_by_bounds(values, expected, label, tolerance=0.25):
    matches = [value for value in values if bounds_contained(bounds(value["shape"]), expected, tolerance)]
    if not matches:
        raise RuntimeError("cannot identify " + label + " by trusted geometry")
    shape = Part.makeCompound([value["shape"] for value in matches])
    if bounds_error(shape, expected) > tolerance:
        raise RuntimeError(label + " solids do not span the trusted geometry")
    return matches, shape


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
    # The list form enables OCC's fuzzy Boolean path. A 1e-6 mm tolerance is
    # enough to handle float32 STL faces that are nominally coincident with
    # STEP faces, while remaining far below every task geometry tolerance.
    common = float(first.common((second,), 1e-6).Volume)
    return {
        "common_volume_mm3": common,
        "first_only_volume_mm3": max(0.0, float(first.Volume) - common),
        "second_only_volume_mm3": max(0.0, float(second.Volume) - common),
        "symmetric_difference_volume_mm3": max(0.0, float(first.Volume + second.Volume - 2.0 * common)),
    }


def inside(shape, x, y, z):
    return bool(shape.isInside(App.Vector(float(x), float(y), float(z)), 1e-4, False))


def export_reference(objects, path):
    doc = App.newDocument("Task04EvalReference")
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


def access_metrics(material, package, access):
    tolerance = config["interference_tolerance_mm3"]
    guard = config["minimum_access_guard_mm"]
    wall = config["wall_mm"]
    enclosure = config["enclosure_bbox_mm"]
    if access["access_type"] != "side_window":
        raise RuntimeError("task-04 only supports side_window access geometry")
    xmin, ymin, zmin, xmax, ymax, zmax = access["bounds_mm"]
    inset = min(0.05, (ymax - ymin) / 20.0, (zmax - zmin) / 20.0)
    if access["direction"] == "X_PLUS":
        x1, x2 = enclosure[0] / 2.0 - wall, enclosure[0] / 2.0
    else:
        x1, x2 = -enclosure[0] / 2.0, -enclosure[0] / 2.0 + wall
    core = box_shape([x1, ymin + inset, zmin + inset, x2, ymax - inset, zmax - inset])
    residual = float(material.common(core).Volume)
    center_y = (ymin + ymax) / 2.0
    center_z = (zmin + zmax) / 2.0
    path_probe = box_shape([xmin, center_y - 0.1, center_z - 0.1, xmax, center_y + 0.1, center_z + 0.1])
    path_residual = float(material.common(path_probe).Volume)
    gap = config["geometry_tolerance_mm"] + 0.03
    width = max(0.2, guard - gap)
    probes = [
        box_shape([x1, ymin - gap - width, zmin + inset, x2, ymin - gap, zmax - inset]),
        box_shape([x1, ymax + gap, zmin + inset, x2, ymax + gap + width, zmax - inset]),
        box_shape([x1, ymin + inset, zmin - gap - width, x2, ymax - inset, zmin - gap]),
        box_shape([x1, ymin + inset, zmax + gap, x2, ymax - inset, zmax + gap + width]),
    ]
    fractions = [float(package.common(probe).Volume) / max(float(probe.Volume), 1e-9) for probe in probes]
    guards = [ymin + enclosure[1] / 2.0, enclosure[1] / 2.0 - ymax, zmin, config["tray_outer_top_z_mm"] - zmax]
    return {
        "ref": access["ref"],
        "access_type": "side_window",
        "bounds_mm": access["bounds_mm"],
        "direction": access["direction"],
        "finished_height_mm": access["finished_height_mm"],
        "finished_width_mm": access["finished_width_mm"],
        "minimum_guard_mm": min(guards),
        "minimum_guard_material_present": min(fractions) >= 0.95,
        "residual_material_volume_mm3": residual,
        "access_path_residual_volume_mm3": path_residual,
        "guard_fill_fractions": fractions,
        "through": residual <= tolerance and path_residual <= tolerance and min(fractions) >= 0.95 and min(guards) + config["geometry_tolerance_mm"] >= guard,
    }


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


def standoff_metrics(material):
    values = {}
    base = config["base_thickness_mm"]
    height = config["standoff_height_mm"]
    outer_radius = config["standoff_outer_diameter_mm"] / 2.0
    bore_radius = config["standoff_bore_diameter_mm"] / 2.0
    geometry_tolerance = config["geometry_tolerance_mm"]
    volume_tolerance = config["interference_tolerance_mm3"]
    board_bottom = config["board_bounds_mm"][2]
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        overcut = config["standoff_bore_overcut_mm"]
        probe_radius = max(0.05, bore_radius - geometry_tolerance)
        bore = Part.makeCylinder(probe_radius, board_bottom + 2.0 * overcut, App.Vector(x, y, -overcut))
        residual = float(material.common(bore).Volume)

        section_height = 0.2
        section_z = board_bottom - 0.6
        outer_search = Part.makeCylinder(
            outer_radius + 0.5,
            section_height,
            App.Vector(x, y, section_z),
        )
        actual_section = material.common(outer_search).removeSplitter()
        expected_section_volume = math.pi * (outer_radius * outer_radius - bore_radius * bore_radius) * section_height
        fill = float(actual_section.Volume) / max(expected_section_volume, 1e-9)
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
        )
        values[hole["ref"]] = {
            "axis_error_mm": axis_error,
            "bore_center_xy_mm": measured_bore_center,
            "bore_diameter_mm": measured_bore_diameter,
            "bore_residual_mm3": residual,
            "bore_z_max_mm": board_bottom + overcut,
            "bore_z_min_mm": -overcut,
            "concentric_error_mm": concentric_error,
            "continuous_bore": residual <= volume_tolerance and dimensions_pass,
            "annulus_fill_ratio": fill,
            "outer_center_xy_mm": measured_outer_center,
            "outer_diameter_mm": measured_outer_diameter,
            "standoff_present": fill >= 0.95 and dimensions_pass,
            "x_mm": x,
            "y_mm": y,
        }
    return values


def tray_coverage(tray):
    enclosure = config["enclosure_bbox_mm"]
    wall = config["wall_mm"]
    base = config["base_thickness_mm"]
    wall_height = config["tray_outer_top_z_mm"] - base
    base_shape = Part.makeBox(enclosure[0], enclosure[1], base, App.Vector(-enclosure[0] / 2.0, -enclosure[1] / 2.0, 0.0))
    wall_shapes = [
        Part.makeBox(wall, enclosure[1], wall_height, App.Vector(-enclosure[0] / 2.0, -enclosure[1] / 2.0, base)),
        Part.makeBox(wall, enclosure[1], wall_height, App.Vector(enclosure[0] / 2.0 - wall, -enclosure[1] / 2.0, base)),
        Part.makeBox(enclosure[0] - 2.0 * wall, wall, wall_height, App.Vector(-enclosure[0] / 2.0 + wall, -enclosure[1] / 2.0, base)),
        Part.makeBox(enclosure[0] - 2.0 * wall, wall, wall_height, App.Vector(-enclosure[0] / 2.0 + wall, enclosure[1] / 2.0 - wall, base)),
    ]
    for access in config["accesses"]:
        window = box_shape(access["bounds_mm"])
        wall_shapes = [shape.cut(window) for shape in wall_shapes]
    expected_wall_volume = sum(float(shape.Volume) for shape in wall_shapes)
    covered_wall_volume = sum(float(tray.common((shape,), 1e-6).Volume) for shape in wall_shapes)
    return {
        "base_slab_coverage": float(tray.common((base_shape,), 1e-6).Volume) / float(base_shape.Volume),
        "side_wall_coverage": covered_wall_volume / expected_wall_volume,
    }


def main():
    submitted_board = read_step(config["submitted_board_step"])
    rerendered_board = read_step(config["rerendered_board_step"])
    submitted_parts, submitted_material, submitted_facets = mesh_solids(config["submitted_stl"])
    rendered_parts, rendered_material, rendered_facets = mesh_solids(config["rerendered_stl"])
    assembly = read_step(config["assembly_step"])
    _doc, objects = read_step_objects(config["assembly_step"])

    tray_obj = pick(objects, config["tray_bounds_mm"], "tray")
    lid_obj = pick(objects, config["lid_bounds_mm"], "lid")
    board_objects, board = group_by_bounds(objects, config["board_bounds_mm"], "installed PCB")
    rib_objects = {
        item["id"]: pick(objects, item["bounds_mm"], "rib " + item["id"])
        for item in config["ribs"]
    }
    component_objects = {}
    component_shapes = {}
    for component in config["components"]:
        matches, shape = group_by_bounds(objects, component["bounds_mm"], "component " + component["ref"])
        component_objects[component["ref"]] = matches
        component_shapes[component["ref"]] = shape
    physical = [tray_obj, lid_obj] + list(rib_objects.values()) + board_objects + [
        value for component in config["components"] for value in component_objects[component["ref"]]
    ]
    export_reference(physical, config["reference_bridge_obj"])

    non_carrier_ids = {id(value) for value in board_objects}
    non_carrier_ids.update(id(value) for matches in component_objects.values() for value in matches)
    carrier_objects = [value for value in objects if id(value) not in non_carrier_ids]
    if not carrier_objects:
        raise RuntimeError("assembly STEP contains no enclosure carrier solids")

    submitted_tray = pick_shape(submitted_parts, config["tray_bounds_mm"], "submitted tray")
    submitted_lid = pick_shape(submitted_parts, config["lid_bounds_mm"], "submitted lid")
    rendered_tray = pick_shape(rendered_parts, config["tray_bounds_mm"], "rerendered tray")
    rendered_lid = pick_shape(rendered_parts, config["lid_bounds_mm"], "rerendered lid")
    tray = tray_obj["shape"]
    lid = lid_obj["shape"]
    ribs = {name: value["shape"] for name, value in rib_objects.items()}
    structural = tray.copy()
    for rib in ribs.values():
        structural = structural.fuse(rib)
    structural = structural.removeSplitter()
    material = Part.makeCompound([value["shape"] for value in carrier_objects])

    board_shift = config["board_bounds_mm"][2] - submitted_board.BoundBox.ZMin
    submitted_board_installed = submitted_board.copy()
    submitted_board_installed.translate(App.Vector(0, 0, board_shift))
    rerendered_board_installed = rerendered_board.copy()
    rerendered_board_installed.translate(
        App.Vector(0, 0, config["board_bounds_mm"][2] - rerendered_board.BoundBox.ZMin)
    )

    board_z = submitted_board.BoundBox.Center.z
    board_holes = {}
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        probe = hole["diameter_mm"] / 2.0 + 0.3
        board_holes[hole["ref"]] = {
            "submitted_center_empty": not inside(submitted_board, x, y, board_z),
            "rerendered_center_empty": not inside(rerendered_board, x, y, rerendered_board.BoundBox.Center.z),
            "submitted_surrounding_material": inside(submitted_board, x + probe, y, board_z),
            "rerendered_surrounding_material": inside(rerendered_board, x + probe, y, rerendered_board.BoundBox.Center.z),
        }

    component_geometry = {}
    interference = {"carrier": {}}
    for component in config["components"]:
        ref = component["ref"]
        actual = component_shapes[ref]
        ideal = box_shape(component["bounds_mm"])
        component_geometry[ref] = {"metrics": metrics(actual), "vs_ideal": overlap(actual, ideal)}
        interference["carrier"][ref] = float(material.common(actual).Volume)
    interference["carrier"]["PCB"] = float(material.common(board).Volume)
    total_interference = sum(value for role in interference.values() for value in role.values())

    rib_checks = {}
    projected_checks = {}
    for item in config["ribs"]:
        rib = ribs[item["id"]]
        ideal = box_shape(item["bounds_mm"])
        q_checks = {}
        for ref, column_values in config["keepout_columns"].items():
            column = cylinder_shape(column_values)
            intersection = float(rib.common(column).Volume)
            separation = float(rib.distToShape(column)[0])
            q_checks[ref] = {
                "intersection_mm3": intersection,
                "passes": intersection <= config["interference_tolerance_mm3"] and separation + config["geometry_tolerance_mm"] >= config["minimum_rib_clearance_mm"],
                "separation_mm": separation,
            }
        comparison = overlap(rib, ideal)
        rib_checks[item["id"]] = {
            "bounds_mm": bounds(rib),
            "expected_volume_mm3": float(ideal.Volume),
            "measured_volume_mm3": float(rib.Volume),
            "present": comparison["symmetric_difference_volume_mm3"] <= max(config["interference_tolerance_mm3"], float(ideal.Volume) * 0.01),
            "present_material_fraction": comparison["common_volume_mm3"] / max(float(ideal.Volume), 1e-9),
            "q_keepout_checks": q_checks,
        }
    for ref, column_values in config["keepout_columns"].items():
        column = cylinder_shape(column_values)
        intersection = float(material.common(column).Volume)
        projected_checks[ref] = {
            "all_tray_structural_intersection_mm3": intersection,
            "bounds_mm": bounds(column),
            "clear": intersection <= config["interference_tolerance_mm3"],
        }

    access_by_geometry = {}
    for label, combined, tray_shape in (
        ("submitted_stl", submitted_material, submitted_tray),
        ("rerendered_stl", rendered_material, rendered_tray),
        ("assembly_step", material, material),
    ):
        access_by_geometry[label] = [access_metrics(combined, tray_shape, item) for item in config["accesses"]]

    side = {direction: side_clearance(material, board, direction) for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")}
    top_clearances = {
        ref: float(lid.BoundBox.ZMin - component_shapes[ref].BoundBox.ZMax)
        for ref in component_shapes
    }
    tray_sanity = {
        "floor": inside(tray, 0, config["enclosure_bbox_mm"][1] / 2.0 - 1.0, config["base_thickness_mm"] / 2.0),
        "cavity": not inside(tray, 0, 0, (config["base_thickness_mm"] + config["tray_outer_top_z_mm"]) / 2.0),
        "x_wall": inside(tray, config["enclosure_bbox_mm"][0] / 2.0 - config["wall_mm"] / 2.0, config["enclosure_bbox_mm"][1] / 2.0 - 2.0, 6.0),
        "y_wall": inside(tray, 0, config["enclosure_bbox_mm"][1] / 2.0 - config["wall_mm"] / 2.0, 6.0),
    }
    submitted_vs_rendered = overlap(submitted_material, rendered_material)
    assembly_vs_submitted = overlap(material, submitted_material)
    board_comparison = overlap(submitted_board_installed, rerendered_board_installed)
    assembly_board_comparison = overlap(board, submitted_board_installed)
    lid_ideal = box_shape(config["lid_bounds_mm"])
    lid_comparison = overlap(lid, lid_ideal)
    enclosure_volume = float(submitted_material.Volume)
    tray_volume = float(submitted_tray.Volume)
    lid_volume = float(submitted_lid.Volume)
    return {
        "submitted_board": metrics(submitted_board),
        "rerendered_board": metrics(rerendered_board),
        "board_holes": board_holes,
        "board_step_symmetric_difference_mm3": board_comparison["symmetric_difference_volume_mm3"],
        "assembly_board_symmetric_difference_mm3": assembly_board_comparison["symmetric_difference_volume_mm3"],
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
        "ribs": {name: metrics(shape) for name, shape in ribs.items()},
        "components": component_geometry,
        "tray_vs_submitted": overlap(structural, submitted_tray),
        "lid_vs_submitted": overlap(lid, submitted_lid),
        "tray_vs_rerendered": overlap(structural, rendered_tray),
        "lid_vs_rerendered": overlap(lid, rendered_lid),
        "lid_vs_ideal": lid_comparison,
        "lid_separation_mm": float(lid.BoundBox.ZMin - tray.BoundBox.ZMax),
        "tray_lid_intersection_mm3": float(tray.common(lid).Volume),
        "tray_sanity": tray_sanity,
        "tray_coverage": tray_coverage(tray),
        "standoff_checks": standoff_metrics(submitted_material),
        "access_by_geometry": access_by_geometry,
        "access_checks": {item["ref"]: item for item in access_by_geometry["submitted_stl"]},
        "rib_checks": rib_checks,
        "projected_keepout_checks": projected_checks,
        "interference_by_role_mm3": interference,
        "unintended_interference_volume_mm3": total_interference,
        "side_clearances_mm": side,
        "minimum_side_clearance_mm": min(value for value in side.values() if value is not None),
        "component_top_clearances_mm": top_clearances,
        "minimum_top_clearance_mm": min(top_clearances.values()),
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
    handle.flush()
    os.fsync(handle.fileno())
# FreeCAD 1.1.0 can segfault while tearing down imported Mesh properties after
# the complete result has been written. Avoid that destructor-only failure;
# the parent evaluator still parses and enforces every result field below.
os._exit(0)
'''


def run_freecad_checker(
    runtime: Path,
    spec: dict[str, Any],
    geometry: dict[str, Any],
    rerendered_board_step: Path,
    rerendered_stl: Path,
) -> dict[str, Any]:
    freecad = resolve_executable(
        "freecadcmd",
        ["/home/user/.local/bin/freecadcmd", "/usr/bin/freecadcmd", "/usr/bin/FreeCADCmd"],
    )
    req = spec["requirements"]
    board = spec["board"]
    board_bottom = number(req["board_bottom_z_mm"], "board bottom")
    board_bounds = [
        -board["bbox_mm"][0] / 2.0,
        -board["bbox_mm"][1] / 2.0,
        board_bottom,
        board["bbox_mm"][0] / 2.0,
        board["bbox_mm"][1] / 2.0,
        board_bottom + board["bbox_mm"][2],
    ]
    components = []
    for item in geometry["components"]:
        sx, sy, sz = item["body_bbox_mm"]
        components.append({
            **item,
            "bounds_mm": [
                item["x_mm"] - sx / 2.0,
                item["y_mm"] - sy / 2.0,
                geometry["board_top_z_mm"],
                item["x_mm"] + sx / 2.0,
                item["y_mm"] + sy / 2.0,
                geometry["board_top_z_mm"] + sz,
            ],
        })
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
        "submitted_board_step": str(DESKTOP / "01_kicad_board.step"),
        "rerendered_board_step": str(rerendered_board_step),
        "submitted_stl": str(DESKTOP / "02_openscad_enclosure.stl"),
        "rerendered_stl": str(rerendered_stl),
        "assembly_step": str(DESKTOP / "03_freecad_assembly.step"),
        "reference_bridge_obj": str(runtime / "assembly_reference.obj"),
        "enclosure_bbox_mm": enclosure,
        "tray_bounds_mm": geometry["tray_bounds_mm"],
        "lid_bounds_mm": geometry["lid_bounds_mm"],
        "board_bounds_mm": board_bounds,
        "ribs": geometry["ribs"],
        "keepout_columns": geometry["keepout_columns"],
        "components": components,
        "mounting_holes": mounting_holes,
        "accesses": geometry["accesses"],
        "wall_mm": number(req["wall_mm"], "wall"),
        "base_thickness_mm": number(req["base_thickness_mm"], "base"),
        "lid_thickness_mm": number(req["lid_thickness_mm"], "lid"),
        "tray_outer_top_z_mm": number(req["tray_outer_top_z_mm"], "tray top"),
        "standoff_height_mm": number(req["standoff_height_mm"], "standoff height"),
        "standoff_outer_diameter_mm": number(req["standoff_outer_diameter_mm"], "standoff OD"),
        "standoff_bore_diameter_mm": number(req["standoff_bore_diameter_mm"], "standoff bore"),
        "standoff_bore_overcut_mm": number(req["standoff_bore_overcut_mm"], "standoff bore overcut"),
        "axis_tolerance_mm": number(req["axis_tolerance_mm"], "axis tolerance"),
        "geometry_tolerance_mm": number(req["geometry_tolerance_mm"], "geometry tolerance"),
        "interference_tolerance_mm3": number(req["interference_volume_tolerance_mm3"], "interference tolerance"),
        "minimum_access_guard_mm": number(req["minimum_access_guard_mm"], "access guard"),
        "minimum_rib_clearance_mm": number(req["minimum_rib_keepout_clearance_mm"], "rib clearance"),
        "enclosure_density_g_cm3": number(req["enclosure_material_density_g_cm3"], "enclosure density"),
    }
    config_path = runtime / "cad_config.json"
    result_path = runtime / "cad_result.json"
    checker_path = runtime / "freecad_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(FREECAD_CHECKER, encoding="utf-8")
    old = (os.environ.get("ENGIWORLD_TASK04_CAD_CONFIG"), os.environ.get("ENGIWORLD_TASK04_CAD_RESULT"))
    os.environ["ENGIWORLD_TASK04_CAD_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK04_CAD_RESULT"] = str(result_path)
    try:
        run_command([freecad, str(checker_path)], cwd=runtime, timeout=300, label="FreeCAD/OCC semantic checker")
    finally:
        for key, value in zip(("ENGIWORLD_TASK04_CAD_CONFIG", "ENGIWORLD_TASK04_CAD_RESULT"), old):
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


def report_accesses(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = report.get("access_checks")
    if isinstance(raw, dict):
        return {str(ref): item for ref, item in raw.items() if isinstance(item, dict)}
    if isinstance(raw, list):
        return {str(item.get("ref")): item for item in raw if isinstance(item, dict) and item.get("ref")}
    fail("FreeCAD report access_checks must be an object or list")


def check_access_report(item: dict[str, Any], expected: dict[str, Any], tolerance: float) -> None:
    if normalized(item.get("direction", item.get("wall_direction"))) != normalized(expected["direction"]):
        fail(f"FreeCAD report {expected['ref']} access direction mismatch")
    verdicts = [item[key] for key in ("through", "continuous", "access_continuous", "continuity_pass") if key in item]
    if not verdicts or any(value is not True for value in verdicts):
        fail(f"FreeCAD report {expected['ref']} does not record a passing continuous access")
    if item.get("decision") is not None and normalized(item.get("decision")) not in {"PASS", "PASSED"}:
        fail(f"FreeCAD report {expected['ref']} decision is not pass")
    if item.get("pass") is not None and item.get("pass") is not True:
        fail(f"FreeCAD report {expected['ref']} pass flag is false")
    if item.get("center_error_mm") is not None and number(item["center_error_mm"], "access center error") > tolerance:
        fail(f"FreeCAD report {expected['ref']} center error exceeds tolerance")
    if item.get("residual_material_volume_mm3") is not None and number(item["residual_material_volume_mm3"], "access residual") > tolerance:
        fail(f"FreeCAD report {expected['ref']} access has residual material")
    if item.get("bounds_mm") is not None:
        close_vector(item["bounds_mm"], expected["bounds_mm"], tolerance, f"FreeCAD report {expected['ref']} bounds")
    for field in ("finished_width_mm", "finished_height_mm"):
        if item.get(field) is not None:
            close(item[field], expected[field], tolerance, f"FreeCAD report {expected['ref']} {field}")
    for key in ("guard_material_present", "guard_wall_material_present", "minimum_guard_material_present"):
        if key in item and item[key] is not True:
            fail(f"FreeCAD report {expected['ref']} guard check failed")


def check_cad_result(
    spec: dict[str, Any],
    geometry: dict[str, Any],
    result: dict[str, Any],
    report: dict[str, Any],
) -> None:
    req = spec["requirements"]
    geom_tol = number(req["geometry_tolerance_mm"], "geometry tolerance")
    volume_tol = number(req["interference_volume_tolerance_mm3"], "interference tolerance")
    close_vector(result["submitted_board"]["bbox_mm"], result["rerendered_board"]["bbox_mm"], 0.05, "submitted/re-exported board bbox")
    board_reference_volume = number(result["rerendered_board"]["volume_mm3"], "rerendered board volume")
    if number(result.get("board_step_symmetric_difference_mm3"), "board STEP symmetric difference") > max(0.5, board_reference_volume * 0.002):
        fail("submitted board STEP differs from the real KiCad re-export")
    if number(result.get("assembly_board_symmetric_difference_mm3"), "assembly board symmetric difference") > max(0.5, board_reference_volume * 0.002):
        fail("assembly STEP does not contain the submitted KiCad board geometry")
    if set(result.get("board_holes", {})) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("board STEP checker did not inspect all four mounting-hole axes")
    for ref, checks in result["board_holes"].items():
        if not all(bool(value) for value in checks.values()):
            fail(f"board STEP lacks real NPTH geometry at {ref}: {checks}")
    if int(result.get("submitted_stl_solid_count", 0)) < 2 or int(result.get("rerendered_stl_solid_count", 0)) < 2:
        fail("OpenSCAD geometry does not contain distinct tray and lid solids")
    close_vector(result["tray"]["bounds_mm"], geometry["tray_bounds_mm"], 0.2, "assembly tray bounds")
    close_vector(result["lid"]["bounds_mm"], geometry["lid_bounds_mm"], 0.2, "assembly lid bounds")
    for key in ("submitted_vs_rerendered", "tray_vs_submitted", "lid_vs_submitted", "tray_vs_rerendered", "lid_vs_rerendered"):
        delta = number(result[key]["symmetric_difference_volume_mm3"], f"{key} difference")
        reference_volume = number(result["submitted_stl"]["volume_mm3"], "submitted STL volume")
        if delta > max(8.0, reference_volume * 0.005):
            fail(f"geometry handoff differs materially at {key}: {delta}")
    lid_delta = number(result["lid_vs_ideal"]["symmetric_difference_volume_mm3"], "lid ideal difference")
    if lid_delta > max(1.0, number(result["lid"]["volume_mm3"], "lid volume") * 0.005):
        fail(f"installed lid is not the specified separated solid: {lid_delta}")
    if number(result.get("tray_lid_intersection_mm3"), "tray/lid intersection") > volume_tol:
        fail("tray and lid are not distinct non-overlapping solids")
    close(result.get("lid_separation_mm"), req["lid_separation_mm"], geom_tol, "tray/lid separation")
    if not all(bool(value) for value in result.get("tray_sanity", {}).values()):
        fail(f"tray lacks a real floor, cavity, or walls: {result.get('tray_sanity')}")
    if any(number(value, f"tray coverage {key}") < 0.98 for key, value in result.get("tray_coverage", {}).items()):
        fail(f"tray lacks continuous base or side-wall coverage: {result.get('tray_coverage')}")

    standoffs = result.get("standoff_checks", {})
    if set(standoffs) != {"MH1", "MH2", "MH3", "MH4"}:
        fail("FreeCAD checker did not find exactly four required standoffs")
    for ref, values in standoffs.items():
        if values.get("continuous_bore") is not True or values.get("standoff_present") is not True:
            fail(f"invalid bored standoff geometry at {ref}: {values}")
        if number(values.get("bore_residual_mm3"), f"{ref} bore residual") > volume_tol or number(values.get("annulus_fill_ratio"), f"{ref} annulus") < 0.80:
            fail(f"invalid bored standoff geometry at {ref}: {values}")
        close(values.get("outer_diameter_mm"), req["standoff_outer_diameter_mm"], geom_tol, f"{ref} outer diameter")
        close(values.get("bore_diameter_mm"), req["standoff_bore_diameter_mm"], geom_tol, f"{ref} bore diameter")

    if set(result.get("ribs", {})) != {item["id"] for item in geometry["ribs"]}:
        fail("assembly STEP does not retain both required rib solids")
    rib_checks = result.get("rib_checks", {})
    for expected in geometry["ribs"]:
        values = rib_checks.get(expected["id"])
        if not isinstance(values, dict) or values.get("present") is not True:
            fail(f"required rib {expected['id']} is absent or not the specified solid")
        close_vector(values.get("bounds_mm"), expected["bounds_mm"], geom_tol, f"rib {expected['id']} bounds")
        q_checks = values.get("q_keepout_checks", {})
        if set(q_checks) != {"Q1", "Q2", "Q3"}:
            fail(f"rib {expected['id']} was not checked against all Q keepout columns")
        for ref, check in q_checks.items():
            if check.get("passes") is not True:
                fail(f"rib {expected['id']} violates projected keepout {ref}")
            if number(check.get("intersection_mm3"), f"{expected['id']}/{ref} intersection") > volume_tol:
                fail(f"rib {expected['id']} intrudes into projected keepout {ref}")
            if number(check.get("separation_mm"), f"{expected['id']}/{ref} separation") + geom_tol < number(req["minimum_rib_keepout_clearance_mm"], "minimum rib clearance"):
                fail(f"rib {expected['id']} is too close to projected keepout {ref}")
    projected = result.get("projected_keepout_checks", {})
    if set(projected) != {"Q1", "Q2", "Q3"}:
        fail("tray structure was not checked against every projected Q keepout column")
    for ref, values in projected.items():
        if values.get("clear") is not True or number(values.get("all_tray_structural_intersection_mm3"), f"{ref} structural intersection") > volume_tol:
            fail(f"tray structural material intrudes into projected keepout {ref}")

    for ref, component in result.get("components", {}).items():
        delta = number(component["vs_ideal"]["symmetric_difference_volume_mm3"], f"{ref} proxy difference")
        if delta > max(0.5, number(component["metrics"]["volume_mm3"], f"{ref} volume") * 0.01):
            fail(f"assembly component {ref} is not a real expected body")
    if set(result.get("components", {})) != {"Q1", "Q2", "Q3", "J1", "J2"}:
        fail("assembly STEP does not retain all five expected component bodies")
    for source, values in result.get("access_by_geometry", {}).items():
        by_ref = {item.get("ref"): item for item in values if isinstance(item, dict)}
        if set(by_ref) != {"J1", "J2"}:
            fail(f"{source} did not inspect every required access")
        for expected in geometry["accesses"]:
            item = by_ref[expected["ref"]]
            if not item.get("through"):
                fail(f"{source} {expected['ref']} is not a bounded continuous access")
            if normalized(item.get("direction")) != normalized(expected["direction"]):
                fail(f"{source} {expected['ref']} is cut through the wrong wall")
            close(item.get("finished_width_mm"), expected["finished_width_mm"], geom_tol, f"{source} {expected['ref']} width")
            close(item.get("finished_height_mm"), expected["finished_height_mm"], geom_tol, f"{source} {expected['ref']} height")
            if number(item.get("minimum_guard_mm"), f"{source} {expected['ref']} guard") + geom_tol < number(req["minimum_access_guard_mm"], "minimum access guard"):
                fail(f"{source} {expected['ref']} does not retain the minimum wall guard")
    if number(result.get("unintended_interference_volume_mm3"), "unintended interference") > volume_tol:
        fail("assembly has unintended enclosure interference with PCB or components")
    side_clearances = result.get("side_clearances_mm", {})
    if set(side_clearances) != {"X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS"}:
        fail("FreeCAD checker did not measure all four PCB side clearances")
    for direction, value in side_clearances.items():
        if value is None or number(value, f"side clearance {direction}") + geom_tol < number(req["minimum_side_clearance_mm"], "minimum side clearance"):
            fail(f"insufficient geometry-derived side clearance at {direction}: {value}")
    top_clearances = result.get("component_top_clearances_mm", {})
    if set(top_clearances) != {"Q1", "Q2", "Q3", "J1", "J2"}:
        fail("FreeCAD checker did not measure every component top clearance")
    if min(number(value, f"top clearance {ref}") for ref, value in top_clearances.items()) + geom_tol < number(req["minimum_top_clearance_mm"], "minimum top clearance"):
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
    checks = report.get("checks")
    if checks is not None:
        if not isinstance(checks, dict) or not checks:
            fail("FreeCAD report checks must be a nonempty object when provided")
        failed = [key for key, value in checks.items() if value is False or normalized(value) in {"FAIL", "FAILED", "FALSE"}]
        if failed:
            fail("FreeCAD report contains failed geometry checks: " + ", ".join(sorted(failed)))
    close_vector(report.get("enclosure_bbox_mm"), geometry["enclosure_bbox_mm"], geom_tol, "FreeCAD report enclosure bbox")
    metric_contract = {
        "enclosure_volume_mm3": (result["enclosure_volume_mm3"], max(2.0, result["enclosure_volume_mm3"] * 0.01)),
        "enclosure_mass_g": (result["enclosure_mass_g"], max(0.02, result["enclosure_mass_g"] * 0.01)),
        "minimum_side_clearance_mm": (min(result["side_clearances_mm"].values()), geom_tol),
        "minimum_top_clearance_mm": (result["minimum_top_clearance_mm"], geom_tol),
        "unintended_interference_volume_mm3": (result["unintended_interference_volume_mm3"], volume_tol),
    }
    for field, (expected, tolerance) in metric_contract.items():
        if field not in report:
            fail(f"FreeCAD report is missing required metric {field}")
        close(report[field], expected, tolerance, f"FreeCAD report {field}")
    for field in ("rib_checks", "standoff_checks", "access_checks"):
        value = report.get(field)
        if not isinstance(value, (dict, list)) or not value:
            fail(f"FreeCAD report must include nonempty {field}")


BLENDER_CHECKER = r'''
import json
import math
import os
import traceback

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree


config = json.load(open(os.environ["ENGIWORLD_TASK04_BLEND_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK04_BLEND_RESULT"]


def world_bounds(objects):
    points = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    if not points:
        raise RuntimeError("cannot compute bounds of empty geometry")
    return [min(point[i] for point in points) for i in range(3)] + [max(point[i] for point in points) for i in range(3)]


def object_bounds(obj):
    return world_bounds([obj])


def bounds_error(actual, expected):
    return max(abs(float(a) - float(b)) for a, b in zip(actual, expected))


def bounds_contained(actual, expected, tolerance=0.6):
    return all(actual[index] >= expected[index] - tolerance for index in range(3)) and all(
        actual[index] <= expected[index] + tolerance for index in range(3, 6)
    )


def classify(objects, label):
    roles = {}
    used = set()
    for role, expected in config["role_bounds"].items():
        if role == "pcb" or role.startswith("component_"):
            matches = [
                obj for obj in objects
                if id(obj) not in used and bounds_contained(object_bounds(obj), expected)
            ]
            if not matches or bounds_error(world_bounds(matches), expected) > 0.6:
                raise RuntimeError(label + " cannot identify physical role " + role + " by geometry")
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
    for slot in obj.material_slots:
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


def material_alpha(material):
    alpha = float(material.diffuse_color[3])
    if material.use_nodes and material.node_tree:
        node = material.node_tree.nodes.get("Principled BSDF")
        if node is not None and node.inputs.get("Alpha") is not None:
            alpha = min(alpha, float(node.inputs["Alpha"].default_value))
    return alpha


def hit_material(obj, polygon_index):
    if obj.type != "MESH" or polygon_index < 0 or polygon_index >= len(obj.data.polygons):
        return None
    slot_index = obj.data.polygons[polygon_index].material_index
    if slot_index < 0 or slot_index >= len(obj.material_slots):
        return None
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
            ray_origin = point - camera_forward * 10000.0
            ray_direction = camera_forward
            remaining = 10000.1
        else:
            ray_origin = camera.matrix_world.translation
            offset = point - ray_origin
            ray_direction = offset.normalized()
            remaining = offset.length + 0.1
        for _ in range(32):
            hit, location, _normal, polygon_index, hit_object, _matrix = scene.ray_cast(
                depsgraph, ray_origin, ray_direction, distance=remaining,
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


def physical_material_signatures(objects, roles):
    signatures = set()
    for role, role_objects in roles.items():
        if any(obj.hide_render or obj.hide_get() for obj in role_objects):
            raise RuntimeError("physical role is hidden from the review: " + role)
        materials = [material for obj in role_objects for material in used_materials(obj)]
        if not materials:
            raise RuntimeError("physical role has no assigned material: " + role)
        signatures.update(material_signature(material) for material in materials)
    return signatures


def overlay_matches(obj, expected):
    actual = object_bounds(obj)
    if expected.get("shape") == "arrow":
        start = expected["start_mm"]
        end = expected["end_mm"]
        center_y = (start[1] + end[1]) / 2.0
        center_z = (start[2] + end[2]) / 2.0
        if abs((actual[1] + actual[4]) / 2.0 - center_y) > 0.65 or abs((actual[2] + actual[5]) / 2.0 - center_z) > 0.65:
            return False
        if actual[4] - actual[1] > 4.5 or actual[5] - actual[2] > 4.5:
            return False
        if expected.get("direction") == "X_PLUS":
            return abs(actual[0] - start[0]) <= 0.65 and abs(actual[3] - end[0]) <= 0.65
        if expected.get("direction") == "X_MINUS":
            return abs(actual[3] - start[0]) <= 0.65 and abs(actual[0] - end[0]) <= 0.65
        return False
    wanted = expected["bounds_mm"]
    if expected.get("role") == "access_corridor" and expected.get("shape") == "box":
        # A review overlay may show only the wall penetration or extend inward to
        # the connector. Its transverse opening and passage through the outer
        # wall are the semantic requirements; the cutter's full axial length is
        # an OpenSCAD implementation detail.
        if max(abs(actual[index] - wanted[index]) for index in (1, 2, 4, 5)) > 0.65:
            return False
        inner_wall = float(expected["inner_wall_x_mm"])
        if expected.get("direction") == "X_PLUS":
            return abs(actual[3] - wanted[3]) <= 0.65 and actual[0] <= inner_wall + 0.65
        if expected.get("direction") == "X_MINUS":
            return abs(actual[0] - wanted[0]) <= 0.65 and actual[3] >= inner_wall - 0.65
        return False
    if bounds_error(actual, wanted) > 0.65:
        return False
    got = object_volume(obj)
    want = float(expected["volume_mm3"])
    return abs(got - want) <= max(2.0, want * 0.08)


def overlay_materials(objects, physical_signatures, visible_only, scene=None, camera=None):
    signatures = {}
    for expected in config["overlays"]:
        matches = [obj for obj in objects if overlay_matches(obj, expected)]
        if visible_only:
            matches = [
                obj for obj in matches
                if not obj.hide_render and not obj.hide_get() and camera_visible(scene, camera, obj)
            ]
        feature_signatures = {
            material_signature(material)
            for obj in matches
            for material in used_materials(obj)
            if material_signature(material) not in physical_signatures
        }
        if not feature_signatures:
            raise RuntimeError("missing visible materially distinct overlay " + expected["id"])
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
    blender = resolve_executable("blender", ["/home/user/Applications/blender-*/blender"])
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
    for rib in geometry["ribs"]:
        role_bounds["rib_" + rib["id"]] = rib["bounds_mm"]
    overlays = []
    wall = number(req["wall_mm"], "wall thickness")
    for item in geometry["overlays"]:
        if item["shape"] == "box":
            bounds = item["bounds_mm"]
            volume = (bounds[3] - bounds[0]) * (bounds[4] - bounds[1]) * (bounds[5] - bounds[2])
        elif item["shape"] == "cylinder":
            x, y, radius, zmin, zmax = item["cylinder_mm"]
            bounds = [x - radius, y - radius, zmin, x + radius, y + radius, zmax]
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
        if item["shape"] == "arrow":
            entry["start_mm"] = item["start_mm"]
            entry["end_mm"] = item["end_mm"]
        if item["role"] == "access_corridor" and item["shape"] == "box":
            entry["inner_wall_x_mm"] = (
                enclosure[0] / 2.0 - wall
                if item.get("direction") == "X_PLUS"
                else -enclosure[0] / 2.0 + wall
            )
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
        "core_physical_material_roles": ["tray", "lid", "pcb", "component_Q1"],
        "rib_physical_roles": ["rib_RIB_NEG_Y", "rib_RIB_POS_Y"],
        "overlays": overlays,
    }
    config_path = runtime / "blend_config.json"
    result_path = runtime / "blend_result.json"
    checker_path = runtime / "blender_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(BLENDER_CHECKER, encoding="utf-8")
    old = (os.environ.get("ENGIWORLD_TASK04_BLEND_CONFIG"), os.environ.get("ENGIWORLD_TASK04_BLEND_RESULT"))
    os.environ["ENGIWORLD_TASK04_BLEND_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK04_BLEND_RESULT"] = str(result_path)
    try:
        run_command(
            [blender, "--background", "--factory-startup", "--disable-autoexec", "--python", str(checker_path)],
            cwd=runtime,
            timeout=180,
            label="Blender native/bridge/review/render checker",
        )
    finally:
        for key, value in zip(("ENGIWORLD_TASK04_BLEND_CONFIG", "ENGIWORLD_TASK04_BLEND_RESULT"), old):
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
    geometry: dict[str, Any],
    cad_result: dict[str, Any],
    blender_result: dict[str, Any],
    report: dict[str, Any],
) -> None:
    if normalized(report.get("decision")) not in {"PASS", "PASSED"}:
        fail("Blender scene report decision must be pass")
    if report.get("inputs") is not None:
        inputs = {Path(str(value)).name for value in report.get("inputs", [])}
        if not {"03_freecad_assembly.obj", "03_freecad_clearance_report.json"}.issubset(inputs):
            fail("Blender report inputs omit a required FreeCAD artifact")
    for field, expected in (
        ("native_scene", "04_blender_review.blend"),
        ("review_obj", "04_blender_review.obj"),
        ("review_mtl", "04_blender_review.mtl"),
        ("render", "04_blender_review.png"),
    ):
        if report.get(field) is not None and Path(str(report[field])).name != expected:
            fail(f"Blender report {field} mismatch")
    if report.get("active_camera") is not None and str(report["active_camera"]) != str(blender_result["active_camera"]):
        fail("Blender report active camera does not match native scene")
    visible_features = report.get("visible_features")
    if visible_features is not None and not isinstance(visible_features, list):
        fail("Blender report visible_features must be a list when provided")
    roles = report.get("object_roles")
    if roles is not None and (not isinstance(roles, dict) or not roles):
        fail("Blender report object_roles must be a nonempty object when provided")
    assignments = report.get("material_assignments")
    if assignments is not None and (not isinstance(assignments, dict) or not assignments):
        fail("Blender report material_assignments must be a nonempty object when provided")
    layout = report.get("label_layout")
    if isinstance(layout, dict):
        if layout.get("overlap_pairs") or layout.get("labels_over_physical"):
            fail("Blender report records overlapping engineering labels")
    camera = report.get("camera")
    if isinstance(camera, dict) and camera.get("framing_pass") is not True:
        fail("Blender report records a failed camera framing check")
    copied = report.get("freecad_metrics")
    if copied is None:
        return
    if not isinstance(copied, dict):
        fail("Blender report freecad_metrics must be an object when provided")
    copied_contract = {
        "enclosure_volume_mm3": cad_result["enclosure_volume_mm3"],
        "enclosure_mass_g": cad_result["enclosure_mass_g"],
        "minimum_side_clearance_mm": min(cad_result["side_clearances_mm"].values()),
        "minimum_top_clearance_mm": cad_result["minimum_top_clearance_mm"],
        "unintended_interference_volume_mm3": cad_result["unintended_interference_volume_mm3"],
    }
    for key, expected in copied_contract.items():
        if key in copied:
            close(copied[key], expected, max(0.1, abs(expected) * 0.02), f"Blender copied metric {key}")
    if copied.get("decision") is not None and normalized(copied.get("decision")) not in {"PASS", "PASSED"}:
        fail("Blender copied metrics do not retain the FreeCAD pass decision")
    copied_accesses = copied.get("access_checks")
    if copied_accesses is not None and (not isinstance(copied_accesses, dict) or not {"J1", "J2"}.issubset(copied_accesses)):
        fail("Blender copied metrics do not retain both FreeCAD access checks")
    copied_ribs = copied.get("rib_checks")
    if copied_ribs is not None and (not isinstance(copied_ribs, dict) or not {"RIB_NEG_Y", "RIB_POS_Y"}.issubset(copied_ribs)):
        fail("Blender copied metrics do not retain both FreeCAD rib checks")
    copied_standoffs = copied.get("standoff_checks")
    if copied_standoffs is not None and (not isinstance(copied_standoffs, dict) or not {"MH1", "MH2", "MH3", "MH4"}.issubset(copied_standoffs)):
        fail("Blender copied metrics do not retain all FreeCAD standoff checks")


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


def check_release_chain(cad_result: dict[str, Any]) -> None:
    log = json_file(DESKTOP / "toolchain_invocation_log.json")
    actual = log.get("actual_invocations")
    commands = actual if isinstance(actual, list) else log.get("commands")
    if not isinstance(commands, list) or len(commands) < 4:
        fail("toolchain log must contain productive commands; retries and helper calls are allowed")
    helper_entries = list(commands)
    if isinstance(log.get("preparation"), dict):
        helper_entries.append(log["preparation"])
    trusted_inputs = {"board_input.kicad_pcb", "mechanical_requirements.json", "connector_keepouts.csv", "enclosure_seed.scad"}
    derived_handoffs = {"01_kicad_board.kicad_pcb", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad", "02_openscad_enclosure.scad", "02_openscad_parameters.json"}
    preparation_inputs: set[str] = set()
    preparation_outputs: set[str] = set()
    for entry in helper_entries:
        if not isinstance(entry, dict):
            continue
        if not isinstance(entry.get("inputs", []), (str, list)) or not isinstance(entry.get("outputs", []), (str, list)):
            continue
        inputs = names_from(entry.get("inputs", []), "preparation inputs")
        outputs = names_from(entry.get("outputs", []), "preparation outputs")
        preparation_inputs.update(inputs)
        preparation_outputs.update(outputs)
    if not trusted_inputs.issubset(preparation_inputs) or not derived_handoffs.issubset(preparation_outputs):
        fail("toolchain log does not record derivation of the required handoffs from all trusted inputs")
    logged_sequence = log.get("required_software_sequence")
    if logged_sequence is not None and [normalized(value) for value in logged_sequence] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("toolchain log required software sequence mismatch")
    logged_versions = log.get("tool_versions") if isinstance(log.get("tool_versions"), dict) else {}
    expected = {
        "KiCad": ({"01_kicad_board.kicad_pcb"}, {"01_kicad_board.step"}),
        "OpenSCAD": ({"01_kicad_parameters.scad", "02_openscad_enclosure.scad"}, {"02_openscad_enclosure.stl"}),
        "FreeCAD": (
            {"01_kicad_board.step", "02_openscad_enclosure.stl", "02_openscad_parameters.json"},
            {"03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
        ),
        "Blender": (
            {"03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
            {"04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"},
        ),
    }
    tokens = {"KiCad": "kicad", "OpenSCAD": "openscad", "FreeCAD": "freecad", "Blender": "blender"}
    previous = -1
    for software in SOFTWARE_SEQUENCE:
        required_inputs, required_outputs = expected[software]
        inputs, outputs, versions = set(), set(), set()
        found = None
        for index, entry in enumerate(commands):
            if index <= previous or not isinstance(entry, dict):
                continue
            command = str(entry.get("command", ""))
            label = " ".join(str(entry.get(key, "")) for key in ("software", "stage"))
            if tokens[software] not in command.lower() and normalized(software) not in normalized(label):
                continue
            inputs.update(names_from(entry.get("inputs", []), f"{software} log inputs"))
            outputs.update(names_from(entry.get("outputs", []), f"{software} log outputs"))
            version = str(entry.get("version", entry.get("software_version", ""))).strip()
            if version:
                versions.add(version)
            if str(logged_versions.get(software, "")).strip():
                versions.add(str(logged_versions[software]).strip())
            if versions and required_inputs.issubset(inputs) and required_outputs.issubset(outputs):
                found = index
                break
        if found is None:
            fail(f"toolchain log lacks an ordered, versioned productive {software} stage")
        previous = found

    package = json_file(DESKTOP / "final_release_package.json")
    if normalized(package.get("release_decision")) not in {"PASS", "PASSED"}:
        fail("final release package decision must be pass")
    if package.get("software_sequence") is not None and [normalized(value) for value in package["software_sequence"]] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("final release package software sequence mismatch")
    listed = names_from(package.get("required_artifacts", []), "final required_artifacts")
    if not set(REQUIRED_ARTIFACTS).issubset(listed):
        fail("final package required_artifacts is incomplete")
    produced = package.get("produced_artifacts")
    if produced is not None and not set(REQUIRED_ARTIFACTS).issubset(names_from(produced, "final produced_artifacts")):
        fail("final package produced_artifacts omits a required artifact")
    stage_outputs = package.get("stage_outputs")
    if stage_outputs is not None:
        if not isinstance(stage_outputs, dict):
            fail("final package stage_outputs must be an object")
        expected_stage_outputs = {
            "KiCad": {"01_kicad_board.kicad_pcb", "01_kicad_board.step", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad"},
            "OpenSCAD": {"02_openscad_enclosure.scad", "02_openscad_enclosure.stl", "02_openscad_parameters.json"},
            "FreeCAD": {"03_freecad_assembly.step", "03_freecad_assembly.obj", "03_freecad_clearance_report.json"},
            "Blender": {"04_blender_review.blend", "04_blender_review.obj", "04_blender_review.mtl", "04_blender_review.png", "04_blender_scene_report.json"},
        }
        normalized_stage_outputs = {normalized(key): value for key, value in stage_outputs.items()}
        for software, required in expected_stage_outputs.items():
            if not required.issubset(names_from(normalized_stage_outputs.get(normalized(software), []), f"{software} stage_outputs")):
                fail(f"final package {software} stage_outputs is incomplete")
    hashes = package.get("artifact_sha256")
    if hashes is not None:
        if not isinstance(hashes, dict):
            fail("final package artifact_sha256 must be an object when provided")
        normalized_hashes = {Path(str(name)).name: value for name, value in hashes.items()}
        for name, expected_hash in normalized_hashes.items():
            if name == "final_release_package.json" or name not in REQUIRED_ARTIFACTS:
                continue
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                fail(f"final package has an invalid SHA-256 for {name}")
            if expected_hash.lower() != sha256(DESKTOP / name):
                fail(f"final package hash mismatch for {name}")
    checks = package.get("checks")
    if checks is not None:
        if not isinstance(checks, dict) or not checks:
            fail("final package checks must be a nonempty object when provided")
        failed = [key for key, value in checks.items() if value is False or normalized(value) in {"FAIL", "FAILED", "FALSE"}]
        if failed:
            fail("final package contains failed checks: " + ", ".join(sorted(failed)))
    versions = package.get("tool_versions")
    if versions is not None and (
        not isinstance(versions, dict)
        or any(not str(versions.get(software, "")).strip() for software in SOFTWARE_SEQUENCE)
    ):
        fail("final package tool_versions is incomplete")
    metrics = package.get("key_metrics")
    if metrics is None:
        return
    if not isinstance(metrics, dict):
        fail("final package key_metrics must be an object when provided")
    metric_contract = {
        "enclosure_volume_mm3": (cad_result["enclosure_volume_mm3"], max(2.0, cad_result["enclosure_volume_mm3"] * 0.01)),
        "enclosure_mass_g": (cad_result["enclosure_mass_g"], max(0.02, cad_result["enclosure_mass_g"] * 0.01)),
        "tray_volume_mm3": (cad_result["tray_volume_mm3"], max(1.0, cad_result["tray_volume_mm3"] * 0.01)),
        "tray_mass_g": (cad_result["tray_mass_g"], max(0.02, cad_result["tray_mass_g"] * 0.01)),
        "lid_volume_mm3": (cad_result["lid_volume_mm3"], max(1.0, cad_result["lid_volume_mm3"] * 0.01)),
        "lid_mass_g": (cad_result["lid_mass_g"], max(0.02, cad_result["lid_mass_g"] * 0.01)),
        "lid_separation_mm": (cad_result["lid_separation_mm"], 0.1),
        "minimum_side_clearance_mm": (min(cad_result["side_clearances_mm"].values()), 0.1),
        "minimum_top_clearance_mm": (cad_result["minimum_top_clearance_mm"], 0.1),
        "unintended_interference_volume_mm3": (cad_result["unintended_interference_volume_mm3"], 0.1),
    }
    for field, (expected_value, tolerance) in metric_contract.items():
        if field in metrics:
            close(metrics[field], expected_value, tolerance, f"final package {field}")
    if metrics.get("access_checks") is not None and (not isinstance(metrics.get("access_checks"), dict) or not {"J1", "J2"}.issubset(metrics["access_checks"])):
        fail("final package key_metrics lacks both access checks")
    if metrics.get("rib_checks") is not None and (not isinstance(metrics.get("rib_checks"), dict) or not {"RIB_NEG_Y", "RIB_POS_Y"}.issubset(metrics["rib_checks"])):
        fail("final package key_metrics lacks both rib checks")
    if metrics.get("standoff_checks") is not None and (not isinstance(metrics.get("standoff_checks"), dict) or not {"MH1", "MH2", "MH3", "MH4"}.issubset(metrics["standoff_checks"])):
        fail("final package key_metrics lacks all standoff checks")


def main() -> bool:
    check_required_files()
    spec = build_spec(trusted_input_paths())
    check_answer_board(spec)
    check_kicad_handoff(spec)
    geometry = expected_geometry(spec)
    check_openscad_handoff(spec, geometry)
    freecad_report = json_file(DESKTOP / "03_freecad_clearance_report.json")
    blender_report = json_file(DESKTOP / "04_blender_scene_report.json")

    with tempfile.TemporaryDirectory(prefix="engiworld_task04_eval_") as temp_dir:
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
        check_blender_report(geometry, cad_result, blender_result, blender_report)
        check_png(runtime / "blender_rerender.png", minimum_width=120, minimum_height=90)

    check_png(DESKTOP / "04_blender_review.png", minimum_width=320, minimum_height=240)
    check_release_chain(cad_result)
    return True


if __name__ == "__main__":
    detail_path = DESKTOP / "eval_detail.txt"
    try:
        passed = main()
        detail = "PASS: task-04 artifacts satisfy the trusted semantic, geometry, bridge, and review contract.\n"
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
