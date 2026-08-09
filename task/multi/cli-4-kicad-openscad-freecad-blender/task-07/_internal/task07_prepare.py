#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


TASK = "task-07"
COMPONENT_REFS = ("U1", "LED1", "PD1", "J1", "FID1")
HOLE_REFS = ("MH1", "MH2", "MH3", "MH4")
ACCESS_REFS = ("J1",)


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            raise ValueError(f"unterminated KiCad block beginning with {marker!r}")


def property_value(block: str, name: str) -> str | None:
    match = re.search(rf'\(property\s+"{re.escape(name)}"\s+"([^"]+)"', block)
    return match.group(1) if match else None


def parse_board(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    thickness_match = re.search(r"\((?:thickness|board_thickness)\s+([-+0-9.]+)\)", text)
    outline_match = re.search(
        r'\(gr_rect\s+\(start\s+([-+0-9.]+)\s+([-+0-9.]+)\)\s+'
        r'\(end\s+([-+0-9.]+)\s+([-+0-9.]+)\)\s+\(layer\s+"Edge\.Cuts"\)',
        text,
    )
    if not thickness_match or not outline_match:
        raise ValueError("KiCad board lacks thickness or rectangular Edge.Cuts")
    x0, y0, x1, y1 = (float(value) for value in outline_match.groups())
    footprints: dict[str, dict[str, Any]] = {}
    for block in sexpr_blocks(text, "(footprint"):
        ref = property_value(block, "Reference")
        at_match = re.search(r"\(at\s+([-+0-9.]+)\s+([-+0-9.]+)", block)
        if not ref or not at_match:
            continue
        if ref in footprints:
            raise ValueError(f"duplicate footprint reference {ref}")
        footprints[ref] = {
            "ref": ref,
            "x_mm": float(at_match.group(1)),
            "y_mm": float(at_match.group(2)),
            "height_mm": float(property_value(block, "HEIGHT_MM") or 0.0),
            "keepout_radius_mm": float(property_value(block, "KEEPOUT_RADIUS_MM") or 0.0),
            "hole_diameter_mm": float(property_value(block, "HOLE_DIA_MM") or 0.0),
        }
    expected = set(COMPONENT_REFS) | set(HOLE_REFS)
    if set(footprints) != expected:
        raise ValueError(f"KiCad reference mismatch: expected {sorted(expected)}, got {sorted(footprints)}")
    return {
        "bbox_mm": [abs(x1 - x0), abs(y1 - y0), float(thickness_match.group(1))],
        "center_xy_mm": [(x0 + x1) / 2.0, (y0 + y1) / 2.0],
        "footprints": footprints,
    }


def parse_accesses(path: Path) -> list[dict[str, Any]]:
    numeric_fields = {
        "finished_width_mm",
        "finished_height_mm",
        "finished_diameter_mm",
        "vertical_margin_mm",
        "cutter_x_min_mm",
        "cutter_y_min_mm",
        "cutter_z_min_mm",
        "cutter_x_max_mm",
        "cutter_y_max_mm",
        "cutter_z_max_mm",
        "path_x_min_mm",
        "path_y_min_mm",
        "path_z_min_mm",
        "path_x_max_mm",
        "path_y_max_mm",
        "path_z_max_mm",
    }
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if {row.get("ref") for row in rows} != set(ACCESS_REFS):
        raise ValueError("connector_keepouts.csv must define exactly J1")
    result: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        for field in numeric_fields:
            item[field] = float(row[field])
        item["cutter_bounds_mm"] = [
            item["cutter_x_min_mm"], item["cutter_y_min_mm"], item["cutter_z_min_mm"],
            item["cutter_x_max_mm"], item["cutter_y_max_mm"], item["cutter_z_max_mm"],
        ]
        item["path_bounds_mm"] = [
            item["path_x_min_mm"], item["path_y_min_mm"], item["path_z_min_mm"],
            item["path_x_max_mm"], item["path_y_max_mm"], item["path_z_max_mm"],
        ]
        result.append(item)
    return result


def fmt(value: float) -> str:
    return f"{float(value):.6f}"


def scad_string(value: str) -> str:
    return json.dumps(value)


def scad_array(values: list[Any]) -> str:
    parts = []
    for value in values:
        if isinstance(value, str):
            parts.append(scad_string(value))
        elif isinstance(value, (list, tuple)):
            parts.append(scad_array(list(value)))
        else:
            parts.append(fmt(float(value)))
    return "[" + ", ".join(parts) + "]"


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    board_input = work / "board_input.kicad_pcb"
    requirements_path = work / "mechanical_requirements.json"
    accesses_path = work / "connector_keepouts.csv"
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    if requirements.get("task") != TASK or int(requirements.get("schema_version", 0)) != 2:
        raise ValueError("task-07 requires the frozen schema_version 2 contract")
    board = parse_board(board_input)
    accesses = parse_accesses(accesses_path)
    footprints = board["footprints"]
    component_bodies = requirements["component_bodies"]
    component_kind = {
        "U1": "OPTICAL_ASIC",
        "LED1": "EMITTER",
        "PD1": "PHOTODIODE",
        "J1": "FLEX",
        "FID1": "FIDUCIAL",
    }
    access_by_ref = {str(item["ref"]): item for item in accesses}
    optical = requirements["optical_corridor"]
    optical_start = [float(value) for value in optical["start_endpoint_mm"]]
    optical_end = [float(value) for value in optical["end_endpoint_mm"]]
    if optical["start_ref"] != "LED1" or optical["end_ref"] != "PD1":
        raise ValueError("optical corridor endpoints must be LED1 to PD1")
    if optical_start[:2] != [footprints["LED1"]["x_mm"], footprints["LED1"]["y_mm"]]:
        raise ValueError("optical start XY does not match KiCad LED1")
    if optical_end[:2] != [footprints["PD1"]["x_mm"], footprints["PD1"]["y_mm"]]:
        raise ValueError("optical end XY does not match KiCad PD1")

    board_output = work / "01_kicad_board.kicad_pcb"
    shutil.copyfile(board_input, board_output)
    components = []
    for ref in COMPONENT_REFS:
        source = footprints[ref]
        body = component_bodies[ref]
        access = access_by_ref.get(ref)
        item = {
            "body_bbox_mm": [float(value) for value in body["bbox_mm"]],
            "height_mm": source["height_mm"],
            "keepout_radius_mm": source["keepout_radius_mm"],
            "kind": component_kind[ref],
            "ref": ref,
            "shape": body["shape"],
            "x_mm": source["x_mm"],
            "y_mm": source["y_mm"],
        }
        if access:
            item.update({"access_type": access["access_type"], "direction": access["direction"]})
        components.append(item)
    holes = [
        {
            "diameter_mm": footprints[ref]["hole_diameter_mm"],
            "ref": ref,
            "x_mm": footprints[ref]["x_mm"],
            "y_mm": footprints[ref]["y_mm"],
        }
        for ref in HOLE_REFS
    ]
    board_hash = sha256(board_input)
    export = {
        "board_bbox_mm": board["bbox_mm"],
        "board_center_xy_mm": board["center_xy_mm"],
        "board_step": "01_kicad_board.step",
        "components": components,
        "coordinate_system": requirements["coordinate_system"],
        "corrected_board": "01_kicad_board.kicad_pcb",
        "critical_requirement": requirements["critical_requirement"],
        "input_board": "board_input.kicad_pcb",
        "input_board_sha256": board_hash,
        "max_component_height_mm": max(item["height_mm"] for item in components),
        "mechanical_map": "01_kicad_mechanical_map.csv",
        "mounting_holes": holes,
        "optical_corridor": {
            "end_endpoint_mm": optical_end,
            "end_ref": optical["end_ref"],
            "radius_mm": float(optical["radius_mm"]),
            "shape": optical["shape"],
            "start_endpoint_mm": optical_start,
            "start_ref": optical["start_ref"],
        },
        "openscad_parameter_handoff": "01_kicad_parameters.scad",
        "software_stage": "KiCad",
        "task": TASK,
    }
    json_dump(work / "01_kicad_export.json", export)

    map_fields = [
        "ref", "kind", "x_mm", "y_mm", "height_mm", "keepout_radius_mm", "role",
        "body_x_mm", "body_y_mm", "body_z_mm", "shape", "access_type", "direction",
        "finished_width_mm", "finished_height_mm", "finished_diameter_mm", "cutter_bounds_mm", "path_bounds_mm",
        "optical_endpoint_role", "optical_endpoint_z_mm",
    ]
    with (work / "01_kicad_mechanical_map.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=map_fields, lineterminator="\n")
        writer.writeheader()
        for component in components:
            ref = str(component["ref"])
            access = access_by_ref.get(ref)
            writer.writerow({
                "ref": ref,
                "kind": component["kind"],
                "x_mm": fmt(component["x_mm"]),
                "y_mm": fmt(component["y_mm"]),
                "height_mm": fmt(component["height_mm"]),
                "keepout_radius_mm": fmt(component["keepout_radius_mm"]),
                "role": "access" if access else "component_keepout",
                "body_x_mm": fmt(component["body_bbox_mm"][0]),
                "body_y_mm": fmt(component["body_bbox_mm"][1]),
                "body_z_mm": fmt(component["body_bbox_mm"][2]),
                "shape": component["shape"],
                "access_type": "" if access is None else access["access_type"],
                "direction": "" if access is None else access["direction"],
                "finished_width_mm": "" if access is None else fmt(access["finished_width_mm"]),
                "finished_height_mm": "" if access is None else fmt(access["finished_height_mm"]),
                "finished_diameter_mm": "" if access is None else fmt(access["finished_diameter_mm"]),
                "cutter_bounds_mm": "" if access is None else ";".join(fmt(v) for v in access["cutter_bounds_mm"]),
                "path_bounds_mm": "" if access is None else ";".join(fmt(v) for v in access["path_bounds_mm"]),
                "optical_endpoint_role": "start" if ref == "LED1" else "end" if ref == "PD1" else "",
                "optical_endpoint_z_mm": fmt(optical_start[2]) if ref == "LED1" else fmt(optical_end[2]) if ref == "PD1" else "",
            })
        for hole in holes:
            writer.writerow({
                "ref": hole["ref"], "kind": "MOUNTING_HOLE", "x_mm": fmt(hole["x_mm"]),
                "y_mm": fmt(hole["y_mm"]), "height_mm": "0.000000",
                "keepout_radius_mm": fmt(hole["diameter_mm"] / 2.0), "role": "standoff_axis",
                "body_x_mm": "", "body_y_mm": "", "body_z_mm": "", "shape": "",
                "access_type": "", "direction": "", "finished_width_mm": "",
                "finished_height_mm": "", "finished_diameter_mm": "", "cutter_bounds_mm": "", "path_bounds_mm": "",
                "optical_endpoint_role": "", "optical_endpoint_z_mm": "",
            })

    package = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    cavity = [float(value) for value in requirements["inner_cavity_xy_bounds_mm"]]
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + float(board["bbox_mm"][2])
    standoff_axes = [[item["ref"], item["x_mm"], item["y_mm"]] for item in holes]
    component_rows = [
        [item["ref"], item["kind"], item["x_mm"], item["y_mm"], item["height_mm"],
         item["keepout_radius_mm"], *item["body_bbox_mm"], item["shape"]]
        for item in components
    ]
    side_rows = [
        [item["ref"], item["direction"], *item["cutter_bounds_mm"], item["finished_width_mm"], item["finished_height_mm"]]
        for item in accesses if item["access_type"] == "side_window"
    ]
    parameter_text = f"""// Generated from task-07 KiCad and frozen mechanical contract.
// source_mechanical_map = 01_kicad_mechanical_map.csv
// input_board_sha256 = {board_hash}
board_bbox = {scad_array(board['bbox_mm'])};
package_bbox = {scad_array(package)};
cavity_bounds = {scad_array(cavity)};
wall_mm = {fmt(requirements['wall_mm'])};
base_mm = {fmt(requirements['base_thickness_mm'])};
tray_top_z = {fmt(requirements['tray_outer_top_z_mm'])};
lid_inner_z = {fmt(requirements['lid_inner_z_mm'])};
lid_thickness = {fmt(requirements['lid_thickness_mm'])};
board_bottom_z = {fmt(board_bottom)};
board_top_z = {fmt(board_top)};
standoff_outer_diameter = {fmt(requirements['standoff_outer_diameter_mm'])};
standoff_bore_diameter = {fmt(requirements['standoff_bore_diameter_mm'])};
standoff_height = {fmt(requirements['standoff_height_mm'])};
standoff_bore_z = {scad_array(requirements['standoff_bore_cutter_z_bounds_mm'])};
standoff_axes = {scad_array(standoff_axes)};
mechanical_features = {scad_array(component_rows)};
interface_features = {scad_array(side_rows)};
side_windows = {scad_array(side_rows)};
optical_start = {scad_array(optical_start)};
optical_end = {scad_array(optical_end)};
optical_radius = {fmt(optical['radius_mm'])};
"""
    (work / "01_kicad_parameters.scad").write_text(parameter_text, encoding="utf-8")

    scad_text = """// Task 07 real carrier geometry driven by the KiCad parameter handoff.
include <01_kicad_parameters.scad>;
$fn = 96;

module bounds_box(b) {
  translate([b[0], b[1], b[2]]) cube([b[3]-b[0], b[4]-b[1], b[5]-b[2]]);
}

module tray() {
  difference() {
    union() {
      difference() {
        translate([-package_bbox[0]/2, -package_bbox[1]/2, 0])
          cube([package_bbox[0], package_bbox[1], tray_top_z]);
        translate([cavity_bounds[0], cavity_bounds[1], base_mm])
          cube([cavity_bounds[2]-cavity_bounds[0], cavity_bounds[3]-cavity_bounds[1], tray_top_z-base_mm+0.5]);
      }
      for (axis = standoff_axes)
        translate([axis[1], axis[2], base_mm])
          cylinder(d=standoff_outer_diameter, h=standoff_height);
    }
    for (axis = standoff_axes)
      translate([axis[1], axis[2], standoff_bore_z[0]])
        cylinder(d=standoff_bore_diameter, h=standoff_bore_z[1]-standoff_bore_z[0]);
    for (window = side_windows)
      bounds_box([window[2],window[3],window[4],window[5],window[6],window[7]]);
  }
}

module lid() {
  translate([-package_bbox[0]/2, -package_bbox[1]/2, lid_inner_z])
    cube([package_bbox[0], package_bbox[1], lid_thickness]);
}

union() {
  tray();
  lid();
}
"""
    (work / "02_openscad_enclosure.scad").write_text(scad_text, encoding="utf-8")

    access_records = []
    for item in accesses:
        ref = str(item["ref"])
        record = {
            "access_type": item["access_type"],
            "cutter_bounds_mm": item["cutter_bounds_mm"],
            "direction": item["direction"],
            "finished_diameter_mm": item["finished_diameter_mm"],
            "finished_height_mm": item["finished_height_mm"],
            "finished_width_mm": item["finished_width_mm"],
            "path_bounds_mm": item["path_bounds_mm"],
            "ref": ref,
            "vertical_margin_mm": item["vertical_margin_mm"],
            "x_mm": footprints[ref]["x_mm"],
            "y_mm": footprints[ref]["y_mm"],
        }
        access_records.append(record)
    params = {
        "accesses": access_records,
        "board_bbox_mm": board["bbox_mm"],
        "board_bottom_z_mm": board_bottom,
        "board_top_z_mm": board_top,
        "cavity_bbox_mm": [cavity[2] - cavity[0], cavity[3] - cavity[1], requirements["tray_outer_top_z_mm"] - requirements["base_thickness_mm"]],
        "cavity_bounds_mm": cavity,
        "critical_requirement": requirements["critical_requirement"],
        "enclosure_bbox_mm": package,
        "input_mechanical_map_sha256": sha256(work / "01_kicad_mechanical_map.csv"),
        "input_parameter_handoff": "01_kicad_parameters.scad",
        "lid_clearance_mm": requirements["minimum_top_clearance_mm"],
        "lid_inner_z_mm": requirements["lid_inner_z_mm"],
        "lid_separation_mm": requirements["lid_separation_mm"],
        "lid_thickness_mm": requirements["lid_thickness_mm"],
        "mesh": "02_openscad_enclosure.stl",
        "minimum_access_guard_mm": requirements["minimum_access_guard_mm"],
        "optical_corridor": {
            "end_endpoint_mm": optical_end,
            "end_ref": optical["end_ref"],
            "endpoint_tolerance_mm": optical["endpoint_tolerance_mm"],
            "maximum_carrier_intersection_mm3": optical["maximum_carrier_intersection_mm3"],
            "radius_mm": optical["radius_mm"],
            "radius_tolerance_mm": optical["radius_tolerance_mm"],
            "shape": optical["shape"],
            "start_endpoint_mm": optical_start,
            "start_ref": optical["start_ref"],
        },
        "side_windows": [item for item in access_records if item["access_type"] == "side_window"],
        "software_stage": "OpenSCAD",
        "source": "02_openscad_enclosure.scad",
        "source_mechanical_map": "01_kicad_mechanical_map.csv",
        "standoff_bore_z_bounds_mm": requirements["standoff_bore_cutter_z_bounds_mm"],
        "standoff_count": len(holes),
        "standoffs": [
            {"bore_diameter_mm": requirements["standoff_bore_diameter_mm"], "height_mm": requirements["standoff_height_mm"],
             "outer_diameter_mm": requirements["standoff_outer_diameter_mm"], **item}
            for item in holes
        ],
        "task": TASK,
        "top_openings": [],
        "tray_outer_top_z_mm": requirements["tray_outer_top_z_mm"],
        "wall_mm": requirements["wall_mm"],
        "window_count": 1,
    }
    json_dump(work / "02_openscad_parameters.json", params)


if __name__ == "__main__":
    main()
