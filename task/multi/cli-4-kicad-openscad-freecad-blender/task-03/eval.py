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
    "01_kicad_export.json": 200,
    "01_kicad_mechanical_map.csv": 200,
    "01_kicad_parameters.scad": 200,
    "02_openscad_enclosure.scad": 300,
    "02_openscad_enclosure.stl": 1000,
    "02_openscad_parameters.json": 200,
    "03_freecad_assembly.step": 1000,
    "03_freecad_assembly.obj": 1000,
    "03_freecad_clearance_report.json": 500,
    "04_blender_review.blend": 1000,
    "04_blender_review.obj": 1000,
    "04_blender_review.mtl": 100,
    "04_blender_review.png": 1000,
    "04_blender_scene_report.json": 500,
    "toolchain_invocation_log.json": 500,
    "final_release_package.json": 500,
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
    override = os.environ.get("ENGIWORLD_TASK03_SPEC_DIR")
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
            "board": DESKTOP / "_eval_task03_board_input.kicad_pcb",
            "requirements": DESKTOP / "_eval_task03_mechanical_requirements.json",
            "connectors": DESKTOP / "_eval_task03_connector_keepouts.csv",
            "seed": DESKTOP / "_eval_task03_enclosure_seed.scad",
            "notes": DESKTOP / "_eval_task03_handoff_notes.md",
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
        "finished_width_mm", "finished_height_mm", "finished_diameter_mm", "vertical_margin_mm",
    }
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        if not required.issubset(row):
            fail("trusted connector CSV lacks required columns")
        ref = str(row["ref"]).strip()
        if not ref or ref in result:
            fail(f"trusted connector CSV has invalid or duplicate ref {ref!r}")
        result[ref] = row
    if not {"J1", "J2", "TP1"}.issubset(result):
        fail("trusted connector CSV must define J1, J2, and TP1")
    return result


def build_spec(paths: dict[str, Path]) -> dict[str, Any]:
    board = parse_board(paths["board"])
    req = json_file(paths["requirements"])
    connectors = read_connectors(paths["connectors"])
    if int(req.get("schema_version", 0)) < 2:
        fail("trusted mechanical requirements schema_version must be at least 2")
    for ref, connector in connectors.items():
        footprint = board["footprints"].get(ref)
        if footprint is None:
            fail(f"trusted access {ref} is absent from the KiCad board")
        access_type = connector["access_type"]
        direction = connector["direction"]
        if access_type == "side_window":
            if direction not in {"X_MINUS", "X_PLUS"}:
                fail(f"trusted side access {ref} has unsupported direction {direction}")
            expected_height = number(footprint["height_mm"], f"{ref} height") + 2.0 * number(
                connector["vertical_margin_mm"], f"{ref} vertical margin"
            )
            close(connector["finished_height_mm"], expected_height, 1e-6, f"{ref} finished height")
            if number(connector["finished_width_mm"], f"{ref} finished width") <= 0:
                fail(f"trusted side access {ref} has non-positive width")
        elif access_type == "top_bore":
            if direction != "Z_PLUS" or number(connector["finished_diameter_mm"], f"{ref} diameter") <= 0:
                fail(f"trusted top access {ref} must be a positive Z_PLUS bore")
        else:
            fail(f"trusted access {ref} has unsupported type {access_type}")
    components = req.get("component_bodies")
    if not isinstance(components, dict):
        fail("trusted requirements component_bodies must be an object")
    for ref in board["footprints"]:
        if not ref.startswith("MH") and ref not in components:
            fail(f"trusted requirements lack a component body for {ref}")
    return {"board": board, "requirements": req, "connectors": connectors, "paths": paths}


def check_required_files() -> None:
    for name in REQUIRED_ARTIFACTS:
        path = DESKTOP / name
        if not path.is_file():
            fail(f"missing required artifact {name}")
        size = path.stat().st_size
        if size < MIN_FILE_SIZE[name]:
            fail(f"required artifact {name} is too small ({size} bytes)")
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
            close(row.get("hole_diameter_mm"), footprint["hole_diameter_mm"], tol, f"map {ref} hole")
            if normalized(row.get("role")) != normalized("standoff_axis"):
                fail(f"mechanical map {ref} is not a standoff axis")
        else:
            close(row.get("height_mm"), footprint["height_mm"], tol, f"map {ref} height")
            close(row.get("keepout_radius_mm"), footprint["keepout_radius_mm"], tol, f"map {ref} radius")
        if ref in connectors:
            connector = connectors[ref]
            for field in (
                "body_x_mm", "body_y_mm", "finished_width_mm", "finished_height_mm",
                "finished_diameter_mm", "vertical_margin_mm",
            ):
                close(row.get(field), connector[field], tol, f"map {ref} {field}")
            if normalized(row.get("access_type")) != normalized(connector["access_type"]):
                fail(f"mechanical map {ref} access_type mismatch")
            if normalized(row.get("direction")) != normalized(connector["direction"]):
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
    connectors = spec["connectors"]
    enclosure = [number(value, "enclosure bbox") for value in req["expected_enclosure_bbox_mm"]]
    board_top = number(req["board_bottom_z_mm"], "board bottom") + number(board["thickness_mm"], "board thickness")
    overcut = number(req["access_overcut_mm"], "access overcut")
    accesses = []
    for ref, connector in connectors.items():
        footprint = board["footprints"][ref]
        x = number(footprint["x_mm"], f"{ref} x")
        y = number(footprint["y_mm"], f"{ref} y")
        height = number(footprint["height_mm"], f"{ref} height")
        if connector["access_type"] == "side_window":
            width = number(connector["finished_width_mm"], f"{ref} width")
            finished_height = number(connector["finished_height_mm"], f"{ref} finished height")
            z1 = board_top + height / 2.0 - finished_height / 2.0
            z2 = board_top + height / 2.0 + finished_height / 2.0
            body_x = number(connector["body_x_mm"], f"{ref} body x")
            if connector["direction"] == "X_PLUS":
                x1, x2 = x - body_x / 2.0, enclosure[0] / 2.0 + overcut
            else:
                x1, x2 = -enclosure[0] / 2.0 - overcut, x + body_x / 2.0
            accesses.append({
                "ref": ref,
                "access_type": "side_window",
                "direction": connector["direction"],
                "bounds_mm": [x1, y - width / 2.0, z1, x2, y + width / 2.0, z2],
                "finished_width_mm": width,
                "finished_height_mm": finished_height,
            })
        else:
            diameter = number(connector["finished_diameter_mm"], f"{ref} diameter")
            accesses.append({
                "ref": ref,
                "access_type": "top_bore",
                "direction": connector["direction"],
                "bore_volume_mm": [x, y, diameter / 2.0, board_top + height, enclosure[2] + overcut],
                "finished_diameter_mm": diameter,
            })
    protected_spec = req["protected_volume"]
    center = board["footprints"][str(protected_spec["center_ref"])]
    sx, sy = (number(value, "protected XY") for value in protected_spec["inner_bbox_xy_mm"])
    cx, cy = number(center["x_mm"], "protected center x"), number(center["y_mm"], "protected center y")
    protected_bounds = [cx - sx / 2.0, cy - sy / 2.0, board_top, cx + sx / 2.0, cy + sy / 2.0, number(protected_spec["z_max_mm"], "protected z max")]
    shield = req["shield"]
    wall = number(shield["wall_thickness_mm"], "shield wall")
    shield_bounds = [cx - sx / 2.0 - wall, cy - sy / 2.0 - wall, board_top, cx + sx / 2.0 + wall, cy + sy / 2.0 + wall, number(shield["outer_top_z_mm"], "shield outer top")]
    keepouts = {}
    components = []
    for ref, footprint in board["footprints"].items():
        if ref.startswith("MH"):
            continue
        body = [number(value, f"{ref} body") for value in req["component_bodies"][ref]["bbox_mm"]]
        x, y = number(footprint["x_mm"], f"{ref} x"), number(footprint["y_mm"], f"{ref} y")
        components.append({"ref": ref, "x_mm": x, "y_mm": y, "body_bbox_mm": body})
        keepouts[ref] = [x, y, number(footprint["keepout_radius_mm"], f"{ref} radius"), board_top, board_top + number(footprint["height_mm"], f"{ref} height")]
    overlays = [
        {"id": "protected_volume", "shape": "box", "bounds_mm": protected_bounds},
        {"id": "U1_inclusion", "shape": "cylinder", "cylinder_mm": keepouts["U1"]},
        {"id": "J1_exclusion", "shape": "cylinder", "cylinder_mm": keepouts["J1"]},
    ]
    for access in accesses:
        feature = "lid_bore" if access["access_type"] == "top_bore" else "access"
        overlays.append({
            "id": f"{access['ref']}_{access['direction']}_{feature}",
            "shape": "box" if access["access_type"] == "side_window" else "cylinder",
            "semantic": "access",
            "direction": access["direction"],
            "bounds_mm": access.get("bounds_mm"),
            "cylinder_mm": access.get("bore_volume_mm"),
        })
    return {
        "enclosure_bbox_mm": enclosure,
        "board_top_z_mm": board_top,
        "protected_bounds_mm": protected_bounds,
        "shield_bounds_mm": shield_bounds,
        "keepouts": keepouts,
        "components": components,
        "accesses": accesses,
        "overlays": overlays,
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
        "wall_mm", "base_thickness_mm", "lid_thickness_mm", "board_bottom_z_mm",
        "standoff_height_mm", "standoff_outer_diameter_mm", "standoff_bore_diameter_mm", "access_overcut_mm",
    ):
        close(params.get(field), req[field], tol, f"OpenSCAD {field}")
    close(params.get("board_top_z_mm"), geometry["board_top_z_mm"], tol, "OpenSCAD board top")
    protected = params.get("protected_volume")
    if not isinstance(protected, dict):
        fail("OpenSCAD parameters lack protected_volume")
    close_vector(protected.get("bounds_mm"), geometry["protected_bounds_mm"], tol, "OpenSCAD protected volume")
    shield = params.get("shield")
    if not isinstance(shield, dict):
        fail("OpenSCAD parameters lack installed shield data")
    close_vector(shield.get("inner_bbox_xy_mm"), req["shield"]["inner_bbox_xy_mm"], tol, "shield inner XY")
    for field in ("wall_thickness_mm", "inner_top_z_mm", "outer_top_z_mm"):
        close(shield.get(field), req["shield"][field], tol, f"shield {field}")
    actual_accesses = []
    for key in ("side_windows", "top_bores", "accesses"):
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
        if expected["access_type"] == "side_window":
            close_vector(actual.get("bounds_mm"), expected["bounds_mm"], tol, f"OpenSCAD {expected['ref']} bounds")
        else:
            actual_volume = actual.get("bore_volume_mm")
            if actual_volume is None and actual.get("center_xy_mm") is not None:
                actual_volume = [*actual["center_xy_mm"], number(actual.get("finished_diameter_mm"), "bore diameter") / 2.0, actual.get("z_min_mm"), actual.get("z_max_mm")]
            close_vector(actual_volume, expected["bore_volume_mm"], tol, f"OpenSCAD {expected['ref']} bore")
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
        import struct

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
        fill = metrics["volume"] / math.prod(expected_bbox)
        if not 0.10 <= fill <= 0.70:
            fail(f"{label} has an implausible package/shield fill ratio: {fill}")
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


config = json.load(open(os.environ["ENGIWORLD_TASK03_CAD_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK03_CAD_RESULT"]


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
    doc = App.newDocument("Task03EvalAssembly")
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
    if not solids:
        raise RuntimeError("STL contains no valid solids: " + path)
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
    doc = App.newDocument("Task03EvalReference")
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
    if access["access_type"] == "side_window":
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
    else:
        core = cylinder_shape(access["bore_volume_mm"])
        residual = float(material.common(core).Volume)
        path_residual = residual
        x, y, radius, _, _ = access["bore_volume_mm"]
        lid_inner = enclosure[2] - config["lid_thickness_mm"]
        outer = Part.makeCylinder(radius + guard, enclosure[2] - lid_inner, App.Vector(x, y, lid_inner))
        inner = Part.makeCylinder(radius + 0.05, enclosure[2] - lid_inner, App.Vector(x, y, lid_inner))
        annulus = outer.cut(inner)
        fractions = [float(package.common(annulus).Volume) / max(float(annulus.Volume), 1e-9)]
    return {
        "ref": access["ref"],
        "direction": access["direction"],
        "residual_material_volume_mm3": residual,
        "access_path_residual_volume_mm3": path_residual,
        "guard_fill_fractions": fractions,
        "through": residual <= tolerance and path_residual <= tolerance and min(fractions) >= 0.95,
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


def standoff_metrics(package):
    values = {}
    base = config["base_thickness_mm"]
    height = config["standoff_height_mm"]
    outer_radius = config["standoff_outer_diameter_mm"] / 2.0
    bore_radius = config["standoff_bore_diameter_mm"] / 2.0
    for hole in config["mounting_holes"]:
        x, y = hole["x_mm"], hole["y_mm"]
        bore = Part.makeCylinder(bore_radius, base + height + 0.4, App.Vector(x, y, -0.2))
        outer = Part.makeCylinder(outer_radius, height, App.Vector(x, y, base))
        inner = Part.makeCylinder(bore_radius + 0.03, height, App.Vector(x, y, base))
        ring = outer.cut(inner)
        values[hole["ref"]] = {
            "bore_residual_mm3": float(package.common(bore).Volume),
            "annulus_fill_ratio": float(package.common(ring).Volume) / max(float(ring.Volume), 1e-9),
        }
    return values


def package_coverage(package):
    enclosure = config["enclosure_bbox_mm"]
    wall = config["wall_mm"]
    base = config["base_thickness_mm"]
    lid = config["lid_thickness_mm"]
    wall_height = enclosure[2] - base - lid
    base_shape = Part.makeBox(enclosure[0], enclosure[1], base, App.Vector(-enclosure[0] / 2.0, -enclosure[1] / 2.0, 0.0))
    lid_shape = Part.makeBox(enclosure[0], enclosure[1], lid, App.Vector(-enclosure[0] / 2.0, -enclosure[1] / 2.0, enclosure[2] - lid))
    wall_shapes = [
        Part.makeBox(wall, enclosure[1], wall_height, App.Vector(-enclosure[0] / 2.0, -enclosure[1] / 2.0, base)),
        Part.makeBox(wall, enclosure[1], wall_height, App.Vector(enclosure[0] / 2.0 - wall, -enclosure[1] / 2.0, base)),
        Part.makeBox(enclosure[0] - 2.0 * wall, wall, wall_height, App.Vector(-enclosure[0] / 2.0 + wall, -enclosure[1] / 2.0, base)),
        Part.makeBox(enclosure[0] - 2.0 * wall, wall, wall_height, App.Vector(-enclosure[0] / 2.0 + wall, enclosure[1] / 2.0 - wall, base)),
    ]
    expected_walls = wall_shapes[0].fuse(wall_shapes[1]).fuse(wall_shapes[2]).fuse(wall_shapes[3])
    for access in config["accesses"]:
        if access["access_type"] == "side_window":
            expected_walls = expected_walls.cut(box_shape(access["bounds_mm"]))
        else:
            lid_shape = lid_shape.cut(cylinder_shape(access["bore_volume_mm"]))
    return {
        "base_slab_coverage": float(package.common(base_shape).Volume) / float(base_shape.Volume),
        "lid_slab_coverage": float(package.common(lid_shape).Volume) / float(lid_shape.Volume),
        "side_wall_coverage": float(package.common(expected_walls).Volume) / float(expected_walls.Volume),
    }


def main():
    submitted_board = read_step(config["submitted_board_step"])
    rerendered_board = read_step(config["rerendered_board_step"])
    submitted_parts, submitted_material, submitted_facets = mesh_solids(config["submitted_stl"])
    rendered_parts, rendered_material, rendered_facets = mesh_solids(config["rerendered_stl"])
    assembly = read_step(config["assembly_step"])
    _doc, objects = read_step_objects(config["assembly_step"])

    board_objects, board = group_by_bounds(objects, config["board_bounds_mm"], "installed PCB")
    component_objects = {}
    component_shapes = {}
    for component in config["components"]:
        matches, shape = group_by_bounds(objects, component["bounds_mm"], "component " + component["ref"])
        component_objects[component["ref"]] = matches
        component_shapes[component["ref"]] = shape
    non_carrier_ids = {id(value) for value in board_objects}
    non_carrier_ids.update(id(value) for matches in component_objects.values() for value in matches)
    carrier_objects = [value for value in objects if id(value) not in non_carrier_ids]
    if not carrier_objects:
        raise RuntimeError("assembly STEP contains no enclosure or shield carrier solids")

    shield_outer = box_shape(config["shield_bounds_mm"])
    inner_bounds = list(config["protected_bounds_mm"])
    ideal_shield = shield_outer.cut(box_shape(inner_bounds)).removeSplitter()

    def partition_carrier(values, label, require_shield):
        shield_values = []
        package_values = []
        for value in values:
            shape = value["shape"] if isinstance(value, dict) else value
            overlap_volume = float(shape.common(ideal_shield).Volume)
            if overlap_volume >= float(shape.Volume) * 0.95:
                shield_values.append(value)
            else:
                package_values.append(value)
        if not package_values:
            raise RuntimeError(label + " contains no package material")
        if require_shield and not shield_values:
            raise RuntimeError(label + " contains no installed shield")
        shield_shape = Part.makeCompound([value["shape"] if isinstance(value, dict) else value for value in shield_values]) if shield_values else None
        package_shape = Part.makeCompound([value["shape"] if isinstance(value, dict) else value for value in package_values])
        return package_values, package_shape, shield_values, shield_shape

    package_objects, package, shield_objects, shield = partition_carrier(carrier_objects, "assembly STEP", True)
    _, submitted_package, _, submitted_shield = partition_carrier(submitted_parts, "submitted STL", False)
    _, rendered_package, _, rendered_shield = partition_carrier(rendered_parts, "rerendered STL", False)
    if (submitted_shield is None) != (rendered_shield is None):
        raise RuntimeError("submitted and rerendered OpenSCAD geometry disagree about shield presence")
    physical = package_objects + shield_objects + board_objects + [
        value for component in config["components"] for value in component_objects[component["ref"]]
    ]
    export_reference(physical, config["reference_bridge_obj"])
    material = Part.makeCompound([value["shape"] for value in carrier_objects])

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

    protected = box_shape(config["protected_bounds_mm"])
    u1_keepout = cylinder_shape(config["keepouts"]["U1"])
    j1_keepout = cylinder_shape(config["keepouts"]["J1"])
    u1_outside = float(u1_keepout.cut(protected).Volume)
    u1_carrier_intersection = float(material.common(u1_keepout).Volume)
    j1_intersection = float(j1_keepout.common(protected).Volume)
    j1_separation = float(j1_keepout.distToShape(protected)[0])

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

    access_by_geometry = {}
    for label, combined, package_shape in (
        ("submitted_stl", submitted_material, submitted_package),
        ("rerendered_stl", rendered_material, rendered_package),
        ("assembly_step", material, package),
    ):
        access_by_geometry[label] = [access_metrics(combined, package_shape, item) for item in config["accesses"]]

    side = {direction: side_clearance(material, board, direction) for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")}
    package_sanity = {
        "floor": inside(package, 0, config["enclosure_bbox_mm"][1] / 2.0 - 1.0, config["base_thickness_mm"] / 2.0),
        "lid": inside(package, 0, config["enclosure_bbox_mm"][1] / 2.0 - 1.0, config["enclosure_bbox_mm"][2] - config["lid_thickness_mm"] / 2.0),
        "cavity": not inside(package, 0, 0, (config["base_thickness_mm"] + config["enclosure_bbox_mm"][2] - config["lid_thickness_mm"]) / 2.0),
        "x_wall": inside(package, config["enclosure_bbox_mm"][0] / 2.0 - config["wall_mm"] / 2.0, config["enclosure_bbox_mm"][1] / 2.0 - 2.0, 6.0),
        "y_wall": inside(package, 0, config["enclosure_bbox_mm"][1] / 2.0 - config["wall_mm"] / 2.0, 6.0),
    }
    return {
        "submitted_board": metrics(submitted_board),
        "rerendered_board": metrics(rerendered_board),
        "submitted_board_vs_rerendered": overlap(submitted_board, rerendered_board),
        "board_holes": board_holes,
        "submitted_stl": metrics(submitted_material),
        "rerendered_stl": metrics(rendered_material),
        "submitted_stl_facets": submitted_facets,
        "rerendered_stl_facets": rendered_facets,
        "submitted_stl_solid_count": len(submitted_parts),
        "rerendered_stl_solid_count": len(rendered_parts),
        "submitted_vs_rerendered": overlap(submitted_material, rendered_material),
        "assembly": metrics(assembly),
        "assembly_object_count": len(objects),
        "package": metrics(package),
        "shield": metrics(shield),
        "board": metrics(board),
        "components": component_geometry,
        "package_vs_submitted": overlap(package, submitted_package),
        "shield_vs_submitted": overlap(shield, submitted_shield) if submitted_shield is not None else None,
        "package_vs_rerendered": overlap(package, rendered_package),
        "shield_vs_rerendered": overlap(shield, rendered_shield) if rendered_shield is not None else None,
        "submitted_stl_contains_shield": submitted_shield is not None,
        "shield_vs_ideal": overlap(shield, ideal_shield),
        "package_shield_intersection_mm3": float(package.common(shield).Volume),
        "package_sanity": package_sanity,
        "package_coverage": package_coverage(package),
        "standoffs": standoff_metrics(package),
        "access_by_geometry": access_by_geometry,
        "u1_keepout_outside_mm3": u1_outside,
        "u1_keepout_contained": u1_outside <= config["interference_tolerance_mm3"],
        "u1_carrier_intersection_mm3": u1_carrier_intersection,
        "j1_protected_intersection_mm3": j1_intersection,
        "j1_protected_separation_mm": j1_separation,
        "interference_by_role_mm3": interference,
        "unintended_interference_volume_mm3": total_interference,
        "side_clearances_mm": side,
        "enclosure_volume_mm3": float(package.Volume),
        "enclosure_mass_g": float(package.Volume) * config["enclosure_density_g_cm3"] / 1000.0,
        "shield_volume_mm3": float(shield.Volume),
        "shield_mass_g": float(shield.Volume) * config["shield_density_g_cm3"] / 1000.0,
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
        "package_bounds_mm": [-enclosure[0] / 2.0, -enclosure[1] / 2.0, 0.0, enclosure[0] / 2.0, enclosure[1] / 2.0, enclosure[2]],
        "shield_bounds_mm": geometry["shield_bounds_mm"],
        "protected_bounds_mm": geometry["protected_bounds_mm"],
        "board_bounds_mm": board_bounds,
        "keepouts": geometry["keepouts"],
        "components": components,
        "mounting_holes": mounting_holes,
        "accesses": geometry["accesses"],
        "wall_mm": number(req["wall_mm"], "wall"),
        "base_thickness_mm": number(req["base_thickness_mm"], "base"),
        "lid_thickness_mm": number(req["lid_thickness_mm"], "lid"),
        "standoff_height_mm": number(req["standoff_height_mm"], "standoff height"),
        "standoff_outer_diameter_mm": number(req["standoff_outer_diameter_mm"], "standoff OD"),
        "standoff_bore_diameter_mm": number(req["standoff_bore_diameter_mm"], "standoff bore"),
        "geometry_tolerance_mm": number(req["geometry_tolerance_mm"], "geometry tolerance"),
        "interference_tolerance_mm3": number(req["interference_volume_tolerance_mm3"], "interference tolerance"),
        "minimum_access_guard_mm": number(req["minimum_access_guard_mm"], "access guard"),
        "enclosure_density_g_cm3": number(req["enclosure_material_density_g_cm3"], "enclosure density"),
        "shield_density_g_cm3": number(req["shield"]["material_density_g_cm3"], "shield density"),
    }
    config_path = runtime / "cad_config.json"
    result_path = runtime / "cad_result.json"
    checker_path = runtime / "freecad_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(FREECAD_CHECKER, encoding="utf-8")
    old = (os.environ.get("ENGIWORLD_TASK03_CAD_CONFIG"), os.environ.get("ENGIWORLD_TASK03_CAD_RESULT"))
    os.environ["ENGIWORLD_TASK03_CAD_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK03_CAD_RESULT"] = str(result_path)
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
        for key, value in zip(("ENGIWORLD_TASK03_CAD_CONFIG", "ENGIWORLD_TASK03_CAD_RESULT"), old):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    if not result_path.is_file():
        output = (completed.stdout + "\n" + completed.stderr)[-3000:]
        fail(f"FreeCAD/OCC semantic checker failed with return code {completed.returncode}: {output}")
    payload = json_file(result_path)
    if not payload.get("ok"):
        detail = str(payload.get("traceback") or "")[-3000:]
        fail(f"FreeCAD/OCC checker rejected artifacts: {payload.get('error')}\n{detail}")
    output = completed.stdout + "\n" + completed.stderr
    wrapped_shutdown_sigsegv = (
        completed.returncode == 1
        and "Program received signal SIGSEGV" in output
        and "closeAllDocuments" in output
    )
    if completed.returncode not in (0, -11) and not wrapped_shutdown_sigsegv:
        fail(f"FreeCAD/OCC semantic checker failed with return code {completed.returncode}: {output[-3000:]}")
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


def check_access_report(
    item: dict[str, Any],
    expected: dict[str, Any],
    center_tolerance_mm: float,
    residual_tolerance_mm3: float,
) -> None:
    if normalized(item.get("direction", item.get("wall_direction"))) != normalized(expected["direction"]):
        fail(f"FreeCAD report {expected['ref']} access direction mismatch")
    verdicts = [item[key] for key in ("through", "continuous", "access_continuous", "continuity_pass") if key in item]
    if not verdicts or any(normalized(value) not in {"TRUE", "PASS", "PASSED", "OK"} for value in verdicts):
        fail(f"FreeCAD report {expected['ref']} does not record a passing continuous access")
    if item.get("decision") is not None and normalized(item.get("decision")) not in {"PASS", "PASSED"}:
        fail(f"FreeCAD report {expected['ref']} decision is not pass")
    if item.get("pass") is not None and normalized(item.get("pass")) not in {"TRUE", "PASS", "PASSED", "OK"}:
        fail(f"FreeCAD report {expected['ref']} pass flag is false")
    if item.get("center_error_mm") is not None and abs(number(item["center_error_mm"], "access center error")) > center_tolerance_mm:
        fail(f"FreeCAD report {expected['ref']} center error exceeds tolerance")
    if item.get("residual_material_volume_mm3") is not None and number(item["residual_material_volume_mm3"], "access residual") > residual_tolerance_mm3:
        fail(f"FreeCAD report {expected['ref']} access has residual material")
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
    if abs(number(result["submitted_board"]["volume_mm3"], "submitted board volume") - number(result["rerendered_board"]["volume_mm3"], "rerendered board volume")) > max(0.5, number(result["rerendered_board"]["volume_mm3"], "rerendered board volume") * 0.002):
        fail("submitted board STEP differs from the real KiCad re-export")
    board_delta = number(result["submitted_board_vs_rerendered"]["symmetric_difference_volume_mm3"], "submitted/re-exported board difference")
    if board_delta > max(0.5, number(result["rerendered_board"]["volume_mm3"], "rerendered board volume") * 0.002):
        fail(f"submitted board STEP geometry differs from the real KiCad re-export: {board_delta}")
    for ref, checks in result["board_holes"].items():
        if not all(bool(value) for value in checks.values()):
            fail(f"board STEP lacks real NPTH geometry at {ref}: {checks}")
    close_vector(result["package"]["bbox_mm"], geometry["enclosure_bbox_mm"], 0.2, "assembly package bbox")
    expected_shield_bbox = [
        geometry["shield_bounds_mm"][3] - geometry["shield_bounds_mm"][0],
        geometry["shield_bounds_mm"][4] - geometry["shield_bounds_mm"][1],
        geometry["shield_bounds_mm"][5] - geometry["shield_bounds_mm"][2],
    ]
    close_vector(result["shield"]["bbox_mm"], expected_shield_bbox, 0.2, "assembly shield bbox")
    comparison_keys = ["submitted_vs_rerendered", "package_vs_submitted", "package_vs_rerendered"]
    if result.get("submitted_stl_contains_shield"):
        comparison_keys.extend(["shield_vs_submitted", "shield_vs_rerendered"])
    for key in comparison_keys:
        delta = number(result[key]["symmetric_difference_volume_mm3"], f"{key} difference")
        reference_volume = number(result["submitted_stl"]["volume_mm3"], "submitted STL volume")
        if delta > max(8.0, reference_volume * 0.005):
            fail(f"geometry handoff differs materially at {key}: {delta}")
    shield_delta = number(result["shield_vs_ideal"]["symmetric_difference_volume_mm3"], "shield ideal difference")
    if shield_delta > max(1.0, number(result["shield"]["volume_mm3"], "shield volume") * 0.005):
        fail(f"installed shield is not the specified closed-top can: {shield_delta}")
    if number(result["package_shield_intersection_mm3"], "package/shield intersection") > volume_tol:
        fail("package and installed shield are not distinct non-overlapping solids")
    if not all(bool(value) for value in result.get("package_sanity", {}).values()):
        fail(f"package lacks a real floor, lid, cavity, or walls: {result.get('package_sanity')}")
    if any(number(value, f"package coverage {key}") < 0.98 for key, value in result.get("package_coverage", {}).items()):
        fail(f"package lacks continuous base, lid, or side-wall coverage: {result.get('package_coverage')}")
    for ref, values in result.get("standoffs", {}).items():
        if number(values.get("bore_residual_mm3"), f"{ref} bore residual") > volume_tol or number(values.get("annulus_fill_ratio"), f"{ref} annulus") < 0.95:
            fail(f"invalid bored standoff geometry at {ref}: {values}")
    for ref, component in result.get("components", {}).items():
        delta = number(component["vs_ideal"]["symmetric_difference_volume_mm3"], f"{ref} proxy difference")
        if delta > max(0.5, number(component["metrics"]["volume_mm3"], f"{ref} volume") * 0.01):
            fail(f"assembly component {ref} is not a real expected body")
    for source, values in result.get("access_by_geometry", {}).items():
        by_ref = {item.get("ref"): item for item in values if isinstance(item, dict)}
        if not {"J1", "J2", "TP1"}.issubset(by_ref):
            fail(f"{source} did not inspect every required access")
        for ref, item in by_ref.items():
            if not item.get("through"):
                fail(f"{source} {ref} is not a bounded continuous access")
    if result.get("u1_keepout_contained") is not True or number(result.get("u1_keepout_outside_mm3"), "U1 outside volume") > volume_tol:
        fail("complete U1 keepout is not inside the protected volume")
    if number(result.get("u1_carrier_intersection_mm3"), "U1 carrier intersection") > volume_tol:
        fail("assembly carrier intrudes into the protected U1 keepout")
    if number(result.get("j1_protected_intersection_mm3"), "J1 protected intersection") > volume_tol:
        fail("J1 keepout intersects the protected volume")
    if number(result.get("j1_protected_separation_mm"), "J1 protected separation") <= 0:
        fail("J1 keepout is not positively separated from the protected volume")
    if number(result.get("unintended_interference_volume_mm3"), "unintended interference") > volume_tol:
        fail("assembly has unintended package/shield interference with PCB or components")
    for direction, value in result.get("side_clearances_mm", {}).items():
        if value is None or number(value, f"side clearance {direction}") + geom_tol < number(req["minimum_side_clearance_mm"], "minimum side clearance"):
            fail(f"insufficient geometry-derived side clearance at {direction}: {value}")

    if normalized(report.get("decision")) not in {"PASS", "PASSED"}:
        fail("FreeCAD report decision must be pass")
    close_vector(report.get("enclosure_bbox_mm"), geometry["enclosure_bbox_mm"], geom_tol, "FreeCAD report enclosure bbox")
    metric_contract = {
        "enclosure_volume_mm3": (result["enclosure_volume_mm3"], max(2.0, result["enclosure_volume_mm3"] * 0.01)),
        "enclosure_mass_g": (result["enclosure_mass_g"], max(0.02, result["enclosure_mass_g"] * 0.01)),
        "shield_volume_mm3": (result["shield_volume_mm3"], max(1.0, result["shield_volume_mm3"] * 0.01)),
        "shield_mass_g": (result["shield_mass_g"], max(0.02, result["shield_mass_g"] * 0.01)),
        "minimum_side_clearance_mm": (min(result["side_clearances_mm"].values()), geom_tol),
        "j1_protected_volume_intersection_mm3": (result["j1_protected_intersection_mm3"], volume_tol),
        "j1_protected_volume_separation_mm": (result["j1_protected_separation_mm"], geom_tol),
        "unintended_interference_volume_mm3": (result["unintended_interference_volume_mm3"], volume_tol),
    }
    for field, (expected, tolerance) in metric_contract.items():
        if field not in report:
            fail(f"FreeCAD report is missing required metric {field}")
        close(report[field], expected, tolerance, f"FreeCAD report {field}")
    if report.get("u1_keepout_contained") is not True:
        fail("FreeCAD report does not record U1 containment")
    access_report = report_accesses(report)
    for expected in geometry["accesses"]:
        item = access_report.get(expected["ref"])
        if item is None:
            fail(f"FreeCAD report lacks access check {expected['ref']}")
        check_access_report(
            item,
            expected,
            number(req["access_center_tolerance_mm"], "access center tolerance"),
            volume_tol,
        )


BLENDER_CHECKER = r'''
import json
import math
import os
import traceback

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree


config = json.load(open(os.environ["ENGIWORLD_TASK03_BLEND_CONFIG"], "r"))
result_path = os.environ["ENGIWORLD_TASK03_BLEND_RESULT"]


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


def boundary_hits(actual, expected, tolerance=0.6):
    return sum(abs(actual[index] - expected[index]) <= tolerance for index in range(6))


def classify(objects, label):
    roles = {}
    used = set()
    ordered_roles = sorted(
        config["role_bounds"],
        key=lambda role: (role == "package", math.prod(config["role_bounds"][role][index + 3] - config["role_bounds"][role][index] for index in range(3))),
    )
    for role in ordered_roles:
        expected = config["role_bounds"][role]
        matches = [
            obj for obj in objects
            if id(obj) not in used
            and bounds_contained(object_bounds(obj), expected)
            and boundary_hits(object_bounds(obj), expected) >= 2
        ]
        if not matches or bounds_error(world_bounds(matches), expected) > 0.6:
            raise RuntimeError(label + " cannot identify physical role " + role + " by geometry")
        roles[role] = matches
        used.update(id(obj) for obj in matches)
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
    color = tuple(float(value) for value in material.diffuse_color)
    metallic = 0.0
    if material.use_nodes:
        node = material.node_tree.nodes.get("Principled BSDF")
        if node is not None:
            color = tuple(float(value) for value in node.inputs["Base Color"].default_value)
            metallic = float(node.inputs["Metallic"].default_value)
    return tuple(round(value, 2) for value in color) + (round(metallic, 2),)


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


def overlay_matches(obj, expected):
    actual = object_bounds(obj)
    wanted = expected["bounds_mm"]
    if expected.get("semantic") == "access" and expected.get("shape") == "box":
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
    physical_signatures = set()
    for role, objects in native_roles.items():
        if any(obj.hide_render or obj.hide_get() for obj in objects):
            raise RuntimeError("physical role is hidden from the review: " + role)
        materials = [material for obj in objects for material in used_materials(obj)]
        if not materials:
            raise RuntimeError("physical role has no assigned material: " + role)
        physical_signatures.update(material_signature(material) for material in materials)
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

    native_render_resolution = [
        int(scene.render.resolution_x * scene.render.resolution_percentage / 100),
        int(scene.render.resolution_y * scene.render.resolution_percentage / 100),
    ]
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
    review_physical_signatures = {
        material_signature(material)
        for role in ("package", "shield", "pcb")
        for obj in review_roles[role]
        for material in used_materials(obj)
    }
    review_overlays = overlay_materials(review_objects, review_physical_signatures, False)
    return {
        "active_camera": native_camera,
        "native_bounds_mm": native_bounds,
        "native_object_count": len(native),
        "native_overlay_material_counts": native_overlays,
        "review_overlay_material_counts": review_overlays,
        "role_collections": sorted(collections),
        "render_similarity": similarity,
        "native_render_resolution": native_render_resolution,
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
    blender = resolve_executable(
        "/snap/bin/blender",
        ["/home/user/Applications/blender-*/blender", "/usr/bin/blender"],
    )
    req = spec["requirements"]
    board = spec["board"]
    board_bottom = number(req["board_bottom_z_mm"], "board bottom")
    board_top = geometry["board_top_z_mm"]
    enclosure = geometry["enclosure_bbox_mm"]
    role_bounds = {
        "package": [-enclosure[0] / 2.0, -enclosure[1] / 2.0, 0.0, enclosure[0] / 2.0, enclosure[1] / 2.0, enclosure[2]],
        "shield": geometry["shield_bounds_mm"],
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
        else:
            x, y, radius, zmin, zmax = item["cylinder_mm"]
            bounds = [x - radius, y - radius, zmin, x + radius, y + radius, zmax]
            volume = math.pi * radius * radius * (zmax - zmin)
        entry = {
            "id": item["id"],
            "bounds_mm": bounds,
            "volume_mm3": volume,
            "shape": item["shape"],
            "semantic": item.get("semantic"),
            "direction": item.get("direction"),
        }
        if item.get("semantic") == "access" and item["shape"] == "box":
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
        "overlays": overlays,
    }
    config_path = runtime / "blend_config.json"
    result_path = runtime / "blend_result.json"
    checker_path = runtime / "blender_checker.py"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    checker_path.write_text(BLENDER_CHECKER, encoding="utf-8")
    old = (os.environ.get("ENGIWORLD_TASK03_BLEND_CONFIG"), os.environ.get("ENGIWORLD_TASK03_BLEND_RESULT"))
    os.environ["ENGIWORLD_TASK03_BLEND_CONFIG"] = str(config_path)
    os.environ["ENGIWORLD_TASK03_BLEND_RESULT"] = str(result_path)
    try:
        run_command(
            [blender, "--background", "--factory-startup", "--disable-autoexec", "--python", str(checker_path)],
            cwd=runtime,
            timeout=180,
            label="Blender native/bridge/review/render checker",
        )
    finally:
        for key, value in zip(("ENGIWORLD_TASK03_BLEND_CONFIG", "ENGIWORLD_TASK03_BLEND_RESULT"), old):
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
    submitted_png_size: tuple[int, int],
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
    similarity = number(blender_result.get("render_similarity"), "Blender submitted/rerendered image similarity")
    if similarity < MIN_RENDER_SIMILARITY:
        fail(
            f"Blender review PNG does not match the native scene rerender: "
            f"similarity {similarity:.4f} < {MIN_RENDER_SIMILARITY:.2f}"
        )
    close_vector(
        list(submitted_png_size),
        blender_result.get("native_render_resolution"),
        0,
        "Blender submitted PNG/native scene render resolution",
    )
    visible_features = report.get("visible_features")
    if visible_features is not None and not isinstance(visible_features, list):
        fail("Blender report visible_features must be a list when provided")
    roles = report.get("object_roles")
    if roles is not None and (not isinstance(roles, dict) or not roles):
        fail("Blender report object_roles must be a nonempty object when provided")
    assignments = report.get("material_assignments")
    if assignments is not None and (not isinstance(assignments, dict) or not assignments):
        fail("Blender report material_assignments must be a nonempty object when provided")
    copied = report.get("freecad_metrics")
    if copied is None:
        return
    if not isinstance(copied, dict):
        fail("Blender report freecad_metrics must be an object when provided")
    copied_contract = {
        "enclosure_volume_mm3": cad_result["enclosure_volume_mm3"],
        "enclosure_mass_g": cad_result["enclosure_mass_g"],
        "shield_volume_mm3": cad_result["shield_volume_mm3"],
        "shield_mass_g": cad_result["shield_mass_g"],
        "minimum_side_clearance_mm": min(cad_result["side_clearances_mm"].values()),
        "j1_protected_volume_intersection_mm3": cad_result["j1_protected_intersection_mm3"],
        "j1_protected_volume_separation_mm": cad_result["j1_protected_separation_mm"],
        "unintended_interference_volume_mm3": cad_result["unintended_interference_volume_mm3"],
    }
    for key, expected in copied_contract.items():
        if key in copied:
            close(copied[key], expected, max(0.1, abs(expected) * 0.02), f"Blender copied metric {key}")
    if copied.get("u1_keepout_contained") is not None and copied.get("u1_keepout_contained") is not True:
        fail("Blender copied metrics say U1 is not contained")
    if copied.get("decision") is not None and normalized(copied.get("decision")) not in {"PASS", "PASSED"}:
        fail("Blender copied metrics do not retain the FreeCAD containment/pass decision")
    if copied.get("access_checks") is not None and not isinstance(copied.get("access_checks"), (dict, list)):
        fail("Blender copied access_checks must be an object or list")


def check_png(path: Path, *, minimum_width: int = 160, minimum_height: int = 120) -> tuple[int, int]:
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
    return width, height


def names_from(value: Any, label: str) -> set[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        fail(f"{label} must be a list or string")
    return {Path(str(item)).name for item in value}


def productive_argv_matches(software: str, argv: list[Any]) -> bool:
    values = [str(value) for value in argv]
    names = [Path(value).name.lower() for value in values]
    if not values:
        return False
    if software == "KiCad":
        try:
            stage = next(index for index in range(len(values) - 2) if [value.lower() for value in values[index:index + 3]] == ["pcb", "export", "step"])
            output_index = values.index("--output", stage + 3)
        except (StopIteration, ValueError):
            return False
        return (
            any("kicad" in name for name in names[:stage])
            and output_index + 1 < len(values)
            and Path(values[output_index + 1]).name == "01_kicad_board.step"
            and any(Path(value).name == "01_kicad_board.kicad_pcb" for value in values[stage + 3:])
        )
    if software == "OpenSCAD":
        try:
            output_index = values.index("-o")
        except ValueError:
            return False
        return (
            "openscad" in names[0]
            and output_index + 1 < len(values)
            and Path(values[output_index + 1]).name == "02_openscad_enclosure.stl"
            and any(Path(value).name == "02_openscad_enclosure.scad" for value in values[output_index + 2:])
        )
    if software == "FreeCAD":
        return (
            "freecad" in names[0]
            and any(Path(value).suffix.lower() == ".py" for value in values[1:])
            and not any(value in {"--version", "-v"} for value in values[1:])
        )
    if software == "Blender":
        try:
            script_index = values.index("--python")
            separator_index = values.index("--", script_index + 2)
        except ValueError:
            return False
        return (
            "blender" in names[0]
            and "--background" in values[1:]
            and script_index + 1 < len(values)
            and Path(values[script_index + 1]).suffix.lower() == ".py"
            and separator_index + 1 < len(values)
            and Path(values[separator_index + 1]).resolve() == PRODUCTIVE_DESKTOP
        )
    return False


def installed_tool_versions() -> dict[str, str]:
    executables = {
        "KiCad": resolve_executable("kicad-cli", ["/home/user/Applications/kicad-*/kicad-*-x86_64.AppImage"]),
        "OpenSCAD": resolve_executable("openscad", ["/usr/bin/openscad"]),
        "FreeCAD": resolve_executable("freecadcmd", ["/home/user/.local/bin/freecadcmd", "/usr/bin/freecadcmd"]),
        "Blender": resolve_executable(
            "/snap/bin/blender",
            ["/home/user/Applications/blender-*/blender", "/usr/bin/blender"],
        ),
    }
    kicad_version_command = (
        [executables["KiCad"], "--appimage-extract-and-run", "kicad-cli", "--version"]
        if Path(executables["KiCad"]).suffix.lower() == ".appimage"
        else [executables["KiCad"], "--version"]
    )
    commands = {
        "KiCad": kicad_version_command,
        "OpenSCAD": [executables["OpenSCAD"], "--version"],
        "FreeCAD": [executables["FreeCAD"], "--version"],
        "Blender": [executables["Blender"], "--background", "--version"],
    }
    results: dict[str, str] = {}
    for software, command in commands.items():
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=30, check=False, env={**os.environ, "PYTHONPATH": ""})
        except Exception as exc:
            fail(f"cannot query installed {software} version: {exc}")
        output = (completed.stdout + "\n" + completed.stderr).strip()
        if completed.returncode != 0 or not version_matches(software, output):
            fail(f"installed {software} version does not match this snapshot: {output[-1000:]}")
        results[software] = output
    return results


def check_release_chain(spec: dict[str, Any], geometry: dict[str, Any], cad_result: dict[str, Any]) -> None:
    log = json_file(DESKTOP / "toolchain_invocation_log.json")
    actual = log.get("actual_invocations")
    commands = actual if isinstance(actual, list) else log.get("commands")
    if not isinstance(commands, list) or len(commands) < 4:
        fail("toolchain log must contain productive commands; retries and helper calls are allowed")
    def valid_execution(
        entry: dict[str, Any],
        expected_inputs: set[str],
        expected_outputs: set[str],
        software: str | None,
        trusted_inputs: dict[str, Path] | None = None,
    ) -> str | None:
        if type(entry.get("exit_code")) is not int or entry["exit_code"] != 0:
            return None
        if Path(str(entry.get("cwd", ""))).resolve() != PRODUCTIVE_DESKTOP:
            return None
        argv = entry.get("argv")
        command = str(entry.get("command", ""))
        if not isinstance(argv, list) or not argv or shlex.split(command) != argv:
            return None
        inputs = names_from(entry.get("inputs", []), "recorded inputs")
        outputs = names_from(entry.get("outputs", []), "recorded outputs")
        if not expected_inputs.issubset(inputs) or not expected_outputs.issubset(outputs):
            return None
        if any(Path(str(value)).parent != Path(".") for value in entry.get("outputs", [])):
            return None
        try:
            started = datetime.fromisoformat(str(entry["started_at_utc"]).replace("Z", "+00:00"))
            finished = datetime.fromisoformat(str(entry["finished_at_utc"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            return None
        if started.tzinfo is None or finished.tzinfo is None or finished < started:
            return None
        input_hashes = entry.get("input_sha256")
        output_hashes = entry.get("output_sha256")
        if not isinstance(input_hashes, dict) or not expected_inputs.issubset(input_hashes):
            return None
        if not isinstance(output_hashes, dict) or not expected_outputs.issubset(output_hashes):
            return None
        trusted_inputs = trusted_inputs or {}
        for name in expected_inputs:
            path = trusted_inputs.get(name, DESKTOP / name)
            if not path.is_file() or input_hashes.get(name) != sha256(path):
                return None
        for name in expected_outputs:
            path = DESKTOP / name
            if not path.is_file() or output_hashes.get(name) != sha256(path):
                return None
        version = str(entry.get("version", "")).strip()
        if software is not None:
            token = {"KiCad": "kicad", "OpenSCAD": "openscad", "FreeCAD": "freecad", "Blender": "blender"}[software]
            if token not in Path(argv[0]).name.lower() or not productive_argv_matches(software, argv) or not version_matches(software, version):
                return None
        return version

    trusted = trusted_input_paths()
    prep_inputs = {"board_input.kicad_pcb", "mechanical_requirements.json", "connector_keepouts.csv", "enclosure_seed.scad", "handoff_notes.md"}
    prep_outputs = {"01_kicad_board.kicad_pcb", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "01_kicad_parameters.scad", "02_openscad_enclosure.scad", "02_openscad_parameters.json"}
    preparation_index = next(
        (
            index for index, entry in enumerate(commands)
            if isinstance(entry, dict) and valid_execution(
                entry,
                prep_inputs,
                prep_outputs,
                None,
                {
                    "board_input.kicad_pcb": trusted["board"],
                    "mechanical_requirements.json": trusted["requirements"],
                    "connector_keepouts.csv": trusted["connectors"],
                    "enclosure_seed.scad": trusted["seed"],
                    "handoff_notes.md": trusted["notes"],
                },
            ) is not None
        ),
        None,
    )
    if preparation_index is None:
        fail("toolchain log lacks a valid recorded handoff preparation")
    logged_sequence = log.get("required_software_sequence")
    if logged_sequence is not None and [normalized(value) for value in logged_sequence] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("toolchain log required software sequence mismatch")
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
    previous = preparation_index
    stage_versions: dict[str, str] = {}
    for software in SOFTWARE_SEQUENCE:
        required_inputs, required_outputs = expected[software]
        found: int | None = None
        for index, entry in enumerate(commands):
            if index <= previous or not isinstance(entry, dict):
                continue
            version = valid_execution(entry, required_inputs, required_outputs, software)
            if version is not None:
                found = index
                stage_versions[software] = version
                break
        if found is None:
            fail(f"toolchain log lacks an ordered, versioned productive {software} stage")
        previous = found

    installed_versions = installed_tool_versions()
    for software, recorded in stage_versions.items():
        if recorded not in installed_versions[software]:
            fail(f"recorded {software} version does not match the installed executable")

    package = json_file(DESKTOP / "final_release_package.json")
    if normalized(package.get("release_decision")) not in {"PASS", "PASSED"}:
        fail("final release package decision must be pass")
    if not isinstance(package.get("software_sequence"), list) or [normalized(value) for value in package["software_sequence"]] != [normalized(value) for value in SOFTWARE_SEQUENCE]:
        fail("final release package software sequence mismatch")
    listed = names_from(package.get("required_artifacts", []), "final required_artifacts")
    if not set(REQUIRED_ARTIFACTS).issubset(listed):
        fail("final package required_artifacts is incomplete")
    produced = package.get("produced_artifacts")
    if produced is not None and not set(REQUIRED_ARTIFACTS).issubset(names_from(produced, "final produced_artifacts")):
        fail("final package produced_artifacts omits a required artifact")
    stage_outputs = package.get("stage_outputs")
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
    hashed_artifacts = set(REQUIRED_ARTIFACTS) - {"final_release_package.json"}
    if not isinstance(hashes, dict) or not hashed_artifacts.issubset(hashes):
        fail("final package artifact_sha256 is incomplete")
    for name in hashed_artifacts:
        expected_hash = hashes[name]
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            fail(f"final package has an invalid SHA-256 for {name}")
        if expected_hash.lower() != sha256(DESKTOP / name):
            fail(f"final package hash mismatch for {name}")
    checks = package.get("checks")
    if not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()):
        fail("final package contains a failed release check")
    versions = package.get("tool_versions")
    if not isinstance(versions, dict) or any(not str(versions.get(software, "")).strip() for software in SOFTWARE_SEQUENCE):
        fail("final package tool_versions is incomplete")
    for software in SOFTWARE_SEQUENCE:
        package_version = str(versions[software]).strip()
        if not version_matches(software, package_version) or package_version != stage_versions[software]:
            fail(f"final package {software} version does not match the recorded stage")
    metrics = package.get("key_metrics")
    required_metrics = {
        "access_checks", "board_bbox_mm", "enclosure_bbox_mm", "enclosure_mass_g",
        "enclosure_volume_mm3", "j1_protected_volume_intersection_mm3",
        "j1_protected_volume_separation_mm", "minimum_side_clearance_mm",
        "shield_mass_g", "shield_volume_mm3", "u1_keepout_contained",
        "unintended_interference_volume_mm3",
    }
    if not isinstance(metrics, dict) or not required_metrics.issubset(metrics):
        fail("final package key_metrics is incomplete")
    metric_contract = {
        "enclosure_volume_mm3": (cad_result["enclosure_volume_mm3"], max(2.0, cad_result["enclosure_volume_mm3"] * 0.01)),
        "enclosure_mass_g": (cad_result["enclosure_mass_g"], max(0.02, cad_result["enclosure_mass_g"] * 0.01)),
        "shield_volume_mm3": (cad_result["shield_volume_mm3"], max(1.0, cad_result["shield_volume_mm3"] * 0.01)),
        "shield_mass_g": (cad_result["shield_mass_g"], max(0.02, cad_result["shield_mass_g"] * 0.01)),
        "minimum_side_clearance_mm": (min(cad_result["side_clearances_mm"].values()), 0.1),
        "j1_protected_volume_intersection_mm3": (cad_result["j1_protected_intersection_mm3"], 0.1),
        "j1_protected_volume_separation_mm": (cad_result["j1_protected_separation_mm"], 0.1),
        "unintended_interference_volume_mm3": (cad_result["unintended_interference_volume_mm3"], 0.1),
    }
    for field, (expected_value, tolerance) in metric_contract.items():
        close(metrics[field], expected_value, tolerance, f"final package {field}")
    close_vector(metrics["board_bbox_mm"], spec["board"]["bbox_mm"], 0.05, "final package board bbox")
    close_vector(metrics["enclosure_bbox_mm"], geometry["enclosure_bbox_mm"], 0.1, "final package enclosure bbox")
    if metrics.get("u1_keepout_contained") is not True:
        fail("final package key_metrics says U1 is not contained")
    package_accesses = report_accesses({"access_checks": metrics.get("access_checks")})
    cad_accesses = {
        str(item.get("ref")): item
        for item in cad_result.get("access_by_geometry", {}).get("assembly_step", [])
        if isinstance(item, dict) and item.get("ref")
    }
    req = spec["requirements"]
    for expected in geometry["accesses"]:
        ref = expected["ref"]
        item = package_accesses.get(ref)
        actual = cad_accesses.get(ref)
        if item is None or actual is None:
            fail(f"final package access_checks lacks geometry-derived {ref}")
        check_access_report(
            item,
            expected,
            number(req["access_center_tolerance_mm"], "access center tolerance"),
            number(req["interference_volume_tolerance_mm3"], "interference tolerance"),
        )
        if expected["access_type"] == "side_window":
            close_vector(item.get("bounds_mm"), expected["bounds_mm"], 0.1, f"final package {ref} bounds")
            close(item.get("finished_width_mm"), expected["finished_width_mm"], 0.05, f"final package {ref} width")
            close(item.get("finished_height_mm"), expected["finished_height_mm"], 0.05, f"final package {ref} height")
        else:
            close_vector(item.get("bore_volume_mm"), expected["bore_volume_mm"], 0.1, f"final package {ref} bore")
            close(item.get("finished_diameter_mm"), expected["finished_diameter_mm"], 0.05, f"final package {ref} diameter")
        close(
            item.get("residual_material_volume_mm3"),
            actual.get("residual_material_volume_mm3"),
            max(0.001, number(req["interference_volume_tolerance_mm3"], "interference tolerance") * 0.1),
            f"final package {ref} residual",
        )


def main() -> bool:
    check_required_files()
    spec = build_spec(trusted_input_paths())
    check_answer_board(spec)
    check_kicad_handoff(spec)
    geometry = expected_geometry(spec)
    check_openscad_handoff(spec, geometry)
    freecad_report = json_file(DESKTOP / "03_freecad_clearance_report.json")
    blender_report = json_file(DESKTOP / "04_blender_scene_report.json")

    with tempfile.TemporaryDirectory(prefix="engiworld_task03_eval_") as temp_dir:
        runtime = Path(temp_dir)
        rerendered_board_step = runtime / "kicad_board_rerender.step"
        rerendered_stl = runtime / "openscad_rerender.stl"
        run_kicad_export(DESKTOP / "01_kicad_board.kicad_pcb", rerendered_board_step, runtime)
        openscad = resolve_executable("openscad", ["/usr/bin/openscad"])
        run_command(
            [openscad, "-o", str(rerendered_stl), str(DESKTOP / "02_openscad_enclosure.scad")],
            cwd=runtime,
            timeout=150,
            label="OpenSCAD package/shield rerender",
        )
        if not rerendered_stl.is_file() or rerendered_stl.stat().st_size < 1000:
            fail("OpenSCAD rerender did not produce a substantial STL")
        submitted_mesh = load_mesh_metrics(DESKTOP / "02_openscad_enclosure.stl")
        rendered_mesh = load_mesh_metrics(rerendered_stl)
        compare_meshes(submitted_mesh, rendered_mesh, geometry)
        cad_result = run_freecad_checker(runtime, spec, geometry, rerendered_board_step, rerendered_stl)
        check_cad_result(spec, geometry, cad_result, freecad_report)
        blender_result = run_blender_checker(runtime, spec, geometry)
        submitted_png_size = check_png(DESKTOP / "04_blender_review.png", minimum_width=320, minimum_height=240)
        check_blender_report(geometry, cad_result, blender_result, blender_report, submitted_png_size)
        check_png(runtime / "blender_rerender.png", minimum_width=120, minimum_height=90)

    check_release_chain(spec, geometry, cad_result)
    return True


if __name__ == "__main__":
    detail_path = DESKTOP / "eval_detail.txt"
    try:
        passed = main()
        detail = "PASS: task-03 artifacts satisfy the trusted semantic, geometry, bridge, and review contract.\n"
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
