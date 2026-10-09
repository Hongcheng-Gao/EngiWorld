#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def number_property(block: str, name: str, default: float | None = None) -> float | None:
    match = re.search(rf'\(property\s+"{re.escape(name)}"\s+"([^"]+)"', block)
    if match:
        return float(match.group(1))
    return default


def parse_board(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    thickness_match = re.search(r"\((?:board_thickness|thickness)\s+([-+0-9.]+)\)", text)
    outline_match = re.search(
        r'\(gr_rect\s+\(start\s+([-+0-9.]+)\s+([-+0-9.]+)\)\s+'
        r'\(end\s+([-+0-9.]+)\s+([-+0-9.]+)\)\s+\(layer\s+"Edge.Cuts"\)',
        text,
    )
    if not thickness_match or not outline_match:
        raise ValueError("board thickness or rectangular Edge.Cuts outline is missing")
    x1, y1, x2, y2 = (float(value) for value in outline_match.groups())
    footprints: list[dict[str, object]] = []
    for block in sexpr_blocks(text, "(footprint "):
        name_match = re.search(r'\(footprint\s+"([^"]+)"', block)
        at_match = re.search(r"\(at\s+([-+0-9.]+)\s+([-+0-9.]+)", block)
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not name_match or not at_match or not ref_match:
            continue
        footprints.append(
            {
                "footprint": name_match.group(1),
                "kind": name_match.group(1).split(":")[-1],
                "ref": ref_match.group(1),
                "x_mm": float(at_match.group(1)),
                "y_mm": float(at_match.group(2)),
                "height_mm": number_property(block, "HEIGHT_MM", 0.0),
                "keepout_radius_mm": number_property(block, "KEEPOUT_RADIUS_MM", 0.0),
                "hole_diameter_mm": number_property(block, "HOLE_DIA_MM"),
            }
        )
    return {
        "text": text,
        "thickness_mm": float(thickness_match.group(1)),
        "bounds_mm": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
        "footprints": footprints,
    }


def format_scad(params: dict[str, object], map_rows: list[dict[str, object]]) -> str:
    return "\n".join(
        [
            "// Task 02 clamp generated from the KiCad parameter handoff.",
            f"// Input map SHA-256: {params['input_mechanical_map_sha256']}",
            "include <01_kicad_parameters.scad>;",
            "",
            "module shell() {",
            "  difference() {",
            "    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);",
            "    translate([-cavity[0]/2, -cavity[1]/2, base_thickness]) cube(cavity);",
            "  }",
            "}",
            "",
            "module standoff(x, y) {",
            "  translate([x, y, base_thickness]) cylinder(d=standoff_od, h=standoff_height);",
            "}",
            "",
            "module screw_bore(x, y) {",
            "  translate([x, y, -overcut]) cylinder(d=standoff_bore, h=board_bottom_z + 2*overcut);",
            "}",
            "",
            "module u1_contact_pad() {",
            "  translate([u1_contact[0] - u1_contact[2]/2, u1_contact[1] - u1_contact[3]/2, u1_contact[4]])",
            "    cube([u1_contact[2], u1_contact[3], u1_contact[5] - u1_contact[4]]);",
            "}",
            "",
            "module installed_clamp() {",
            "  union() {",
            "    shell();",
            "    u1_contact_pad();",
            "    for (axis = standoff_axes) standoff(axis[1], axis[2]);",
            "  }",
            "}",
            "",
            "difference() {",
            "  installed_clamp();",
            "  for (aperture = apertures)",
            "    translate([aperture[2], aperture[3], aperture[4]])",
            "      cube([aperture[5]-aperture[2], aperture[6]-aperture[3], aperture[7]-aperture[4]]);",
            "  for (axis = standoff_axes) screw_bore(axis[1], axis[2]);",
            "  translate([l1_keepout[0], l1_keepout[1], l1_keepout[3]])",
            "    cylinder(r=l1_keepout[2], h=l1_keepout[4]-l1_keepout[3]);",
            "  translate([c1_clearance[0], c1_clearance[1], c1_clearance[3]])",
            "    cylinder(r=c1_clearance[2], h=c1_clearance[4]-c1_clearance[3]);",
            "}",
            "",
        ]
    )


def format_parameter_handoff(params: dict[str, object]) -> str:
    def vector(values: list[float]) -> str:
        return "[" + ", ".join(f"{float(value):.6f}" for value in values) + "]"

    lines = [
        "// KiCad-derived Task 02 OpenSCAD parameter handoff.",
        f"// Source map SHA-256: {params['input_mechanical_map_sha256']}",
        "$fn = 64;",
        f"board = {vector(params['board_bbox_mm'])};",
        f"enclosure = {vector(params['enclosure_bbox_mm'])};",
        f"cavity = {vector(params['cavity_bbox_mm'])};",
        f"wall = {params['wall_mm']:.6f};",
        f"base_thickness = {params['base_thickness_mm']:.6f};",
        f"lid_thickness = {params['lid_thickness_mm']:.6f};",
        f"board_bottom_z = {params['board_bottom_z_mm']:.6f};",
        f"board_top_z = {params['board_top_z_mm']:.6f};",
        f"lid_inner_z = {params['lid_inner_z_mm']:.6f};",
        f"standoff_height = {params['standoff_height_mm']:.6f};",
        f"standoff_od = {params['standoff_outer_diameter_mm']:.6f};",
        f"standoff_bore = {params['standoff_bore_diameter_mm']:.6f};",
        f"overcut = {params['aperture_overcut_mm']:.6f};",
        "standoff_axes = [",
    ]
    for item in params["standoff_axes"]:
        lines.append(f'  ["{item["ref"]}", {item["x_mm"]:.6f}, {item["y_mm"]:.6f}],')
    lines.extend(["];", "apertures = ["])
    for item in params["apertures"]:
        bounds = item["bounds_mm"]
        lines.append(
            f'  ["{item["ref"]}", "{item["wall_direction"]}", '
            + ", ".join(f"{float(value):.6f}" for value in bounds)
            + "],"
        )
    lines.extend(
        [
            "];",
            f"l1_keepout = {vector(params['l1_keepout']['volume_mm'])};",
            f"c1_clearance = {vector(params['c1_clearance']['volume_mm'])};",
            f"u1_contact = {vector(params['u1_contact']['volume_mm'])};",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    board_path = work / "board_input.kicad_pcb"
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connector_rows = {row["ref"]: row for row in csv.DictReader(handle)}
    parsed = parse_board(board_path)
    xmin, ymin, xmax, ymax = parsed["bounds_mm"]
    thickness = float(parsed["thickness_mm"])
    board_bbox = [xmax - xmin, ymax - ymin, thickness]
    enclosure = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    wall = float(requirements["wall_mm"])
    base = float(requirements["base_thickness_mm"])
    lid = float(requirements["lid_thickness_mm"])
    cavity = [enclosure[0] - 2 * wall, enclosure[1] - 2 * wall, enclosure[2] - base - lid]
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + thickness
    overcut = float(requirements["aperture_overcut_mm"])

    map_rows: list[dict[str, object]] = []
    components: list[dict[str, object]] = []
    mounting_holes: list[dict[str, object]] = []
    for footprint in parsed["footprints"]:
        ref = str(footprint["ref"])
        if ref.startswith("MH"):
            role = "standoff_axis"
            body = [0.0, 0.0, 0.0]
            mounting_holes.append(
                {
                    "diameter_mm": float(footprint["hole_diameter_mm"]),
                    "ref": ref,
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                }
            )
        else:
            connector = connector_rows.get(ref)
            role = "connector_window" if connector else "component_keepout"
            if connector:
                body = [float(connector["body_x_mm"]), float(connector["body_y_mm"]), float(footprint["height_mm"])]
            else:
                body_spec = requirements["component_bodies"][ref]
                body = [float(value) for value in body_spec["bbox_mm"]]
            components.append(
                {
                    "body_bbox_mm": body,
                    "height_mm": float(footprint["height_mm"]),
                    "keepout_radius_mm": float(footprint["keepout_radius_mm"]),
                    "kind": footprint["kind"],
                    "ref": ref,
                    "shape": requirements.get("component_bodies", {}).get(ref, {}).get("shape", "box"),
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                }
            )

        row: dict[str, object] = {
            "ref": ref,
            "kind": footprint["kind"] if not ref.startswith("MH") else "MOUNTING_HOLE",
            "x_mm": float(footprint["x_mm"]),
            "y_mm": float(footprint["y_mm"]),
            "height_mm": float(footprint["height_mm"]),
            "keepout_radius_mm": float(footprint["keepout_radius_mm"]),
            "body_x_mm": body[0],
            "body_y_mm": body[1],
            "role": role,
            "wall_direction": "",
            "window_width_mm": 0.0,
            "window_height_mm": 0.0,
            "vertical_margin_mm": 0.0,
            "hole_diameter_mm": float(footprint["hole_diameter_mm"] or 0.0),
            "through_margin_mm": 0.0,
            "alignment_tolerance_mm": 0.0,
            "aperture_bounds_mm": [],
        }
        connector = connector_rows.get(ref)
        if connector:
            direction = connector["wall_direction"]
            width = float(connector["window_width_mm"])
            height = float(connector["window_height_mm"])
            component_height = float(footprint["height_mm"])
            vertical_margin = float(connector["vertical_margin_mm"])
            if abs(height - (component_height + 2.0 * vertical_margin)) > 1e-9:
                raise ValueError(f"{ref} window_height_mm must equal KiCad HEIGHT_MM + 2 * vertical_margin_mm")
            center_z = board_top + component_height / 2.0
            y1, y2 = float(footprint["y_mm"]) - width / 2.0, float(footprint["y_mm"]) + width / 2.0
            z1, z2 = center_z - height / 2.0, center_z + height / 2.0
            if direction == "X_MINUS":
                x1 = -enclosure[0] / 2.0 - overcut
                x2 = -enclosure[0] / 2.0 + wall + overcut
            elif direction == "X_PLUS":
                x1 = enclosure[0] / 2.0 - wall - overcut
                x2 = enclosure[0] / 2.0 + overcut
            else:
                raise ValueError(f"unsupported task-02 wall direction: {direction}")
            row.update(
                {
                    "wall_direction": direction,
                    "window_width_mm": width,
                    "window_height_mm": height,
                    "vertical_margin_mm": float(connector["vertical_margin_mm"]),
                    "through_margin_mm": overcut,
                    "alignment_tolerance_mm": float(requirements["aperture_center_tolerance_mm"]),
                    "aperture_bounds_mm": [round(value, 6) for value in [x1, y1, z1, x2, y2, z2]],
                }
            )
        map_rows.append(row)

    shutil.copyfile(board_path, work / "01_kicad_board.kicad_pcb")
    export = {
        "board_bbox_mm": board_bbox,
        "board_bounds_xy_mm": [xmin, ymin, xmax, ymax],
        "components": components,
        "coordinate_system": requirements["coordinate_system"],
        "corrected_board": "01_kicad_board.kicad_pcb",
        "critical_requirement": requirements["critical_requirement"],
        "input_board": "board_input.kicad_pcb",
        "input_board_sha256": sha256(board_path),
        "max_component_height_mm": max(float(item["height_mm"]) for item in components),
        "mechanical_map": "01_kicad_mechanical_map.csv",
        "mounting_holes": mounting_holes,
        "software_stage": "KiCad",
        "openscad_parameter_handoff": "01_kicad_parameters.scad",
        "task": "task-02",
    }
    json_dump(work / "01_kicad_export.json", export)

    fieldnames = [
        "ref", "kind", "x_mm", "y_mm", "height_mm", "keepout_radius_mm", "body_x_mm", "body_y_mm",
        "hole_diameter_mm", "role", "wall_direction", "window_width_mm", "window_height_mm",
        "vertical_margin_mm", "through_margin_mm", "alignment_tolerance_mm",
    ]
    with (work / "01_kicad_mechanical_map.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in map_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    map_path = work / "01_kicad_mechanical_map.csv"
    params = {
        "aperture_overcut_mm": overcut,
        "apertures": [
            {
                "bounds_mm": row["aperture_bounds_mm"],
                "centerline_xy_mm": [row["x_mm"], row["y_mm"]],
                "ref": row["ref"],
                "wall_direction": row["wall_direction"],
                "window_height_mm": row["window_height_mm"],
                "window_width_mm": row["window_width_mm"],
            }
            for row in map_rows
            if row["role"] == "connector_window"
        ],
        "base_thickness_mm": base,
        "board_bbox_mm": board_bbox,
        "board_bottom_z_mm": board_bottom,
        "board_top_z_mm": board_top,
        "cavity_bbox_mm": cavity,
        "c1_clearance": {},
        "critical_requirement": requirements["critical_requirement"],
        "enclosure_bbox_mm": enclosure,
        "input_mechanical_map": "01_kicad_mechanical_map.csv",
        "input_mechanical_map_sha256": sha256(map_path),
        "input_parameter_handoff": "01_kicad_parameters.scad",
        "lid_inner_z_mm": enclosure[2] - lid,
        "lid_thickness_mm": lid,
        "mesh": "02_openscad_enclosure.stl",
        "minimum_side_clearance_mm": requirements["minimum_side_clearance_mm"],
        "l1_keepout": {},
        "maximum_u1_contact_gap_mm": requirements["maximum_u1_contact_gap_mm"],
        "minimum_c1_clamp_clearance_mm": requirements["minimum_c1_clamp_clearance_mm"],
        "minimum_aperture_guard_mm": requirements["minimum_aperture_guard_mm"],
        "software_stage": "OpenSCAD",
        "source": "02_openscad_enclosure.scad",
        "source_mechanical_map": "01_kicad_mechanical_map.csv",
        "standoff_bore_diameter_mm": requirements["standoff_bore_diameter_mm"],
        "standoff_count": len(mounting_holes),
        "standoff_height_mm": requirements["standoff_height_mm"],
        "standoff_outer_diameter_mm": requirements["standoff_outer_diameter_mm"],
        "task": "task-02",
        "u1_contact": {},
        "wall_mm": wall,
        "window_count": len(connector_rows),
    }
    component_by_ref = {item["ref"]: item for item in components}
    l1 = component_by_ref["L1"]
    c1 = component_by_ref["C1"]
    u1 = component_by_ref["U1"]
    lid_inner = float(params["lid_inner_z_mm"])
    c1_top = board_top + float(c1["body_bbox_mm"][2])
    u1_top = board_top + float(u1["body_bbox_mm"][2])
    params["standoff_axes"] = mounting_holes
    params["l1_keepout"] = {
        "ref": "L1",
        "shape": "cylinder",
        "volume_mm": [float(l1["x_mm"]), float(l1["y_mm"]), float(l1["keepout_radius_mm"]), board_top, lid_inner],
    }
    params["c1_clearance"] = {
        "ref": "C1",
        "shape": "cylinder",
        "minimum_mm": float(requirements["minimum_c1_clamp_clearance_mm"]),
        "volume_mm": [float(c1["x_mm"]), float(c1["y_mm"]), float(c1["keepout_radius_mm"]), c1_top, lid_inner],
    }
    contact_x, contact_y = (float(value) for value in requirements["u1_contact"]["xy_size_mm"])
    params["u1_contact"] = {
        "ref": "U1",
        "shape": "box",
        "volume_mm": [float(u1["x_mm"]), float(u1["y_mm"]), contact_x, contact_y, u1_top, lid_inner],
    }
    json_dump(work / "02_openscad_parameters.json", params)
    (work / "01_kicad_parameters.scad").write_text(format_parameter_handoff(params), encoding="utf-8")
    (work / "02_openscad_enclosure.scad").write_text(format_scad(params, map_rows), encoding="utf-8")


if __name__ == "__main__":
    main()
