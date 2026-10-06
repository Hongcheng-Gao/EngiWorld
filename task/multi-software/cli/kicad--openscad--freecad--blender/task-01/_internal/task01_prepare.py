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
    board = params["board_bbox_mm"]
    enclosure = params["enclosure_bbox_mm"]
    cavity = params["cavity_bbox_mm"]
    holes = [row for row in map_rows if row["role"] == "standoff_axis"]
    windows = [row for row in map_rows if row["role"] == "connector_window"]
    lines = [
        "// Task 01 enclosure generated from 01_kicad_mechanical_map.csv.",
        f"// Input map SHA-256: {params['input_mechanical_map_sha256']}",
        "$fn = 64;",
        f"board = [{board[0]:.3f}, {board[1]:.3f}, {board[2]:.3f}];",
        f"enclosure = [{enclosure[0]:.3f}, {enclosure[1]:.3f}, {enclosure[2]:.3f}];",
        f"cavity = [{cavity[0]:.3f}, {cavity[1]:.3f}, {cavity[2]:.3f}];",
        f"wall = {params['wall_mm']:.3f};",
        f"base_thickness = {params['base_thickness_mm']:.3f};",
        f"lid_thickness = {params['lid_thickness_mm']:.3f};",
        f"board_bottom_z = {params['board_bottom_z_mm']:.3f};",
        f"standoff_height = {params['standoff_height_mm']:.3f};",
        f"standoff_od = {params['standoff_outer_diameter_mm']:.3f};",
        f"standoff_bore = {params['standoff_bore_diameter_mm']:.3f};",
        f"overcut = {params['aperture_overcut_mm']:.3f};",
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
        "module enclosure_with_standoffs() {",
        "  union() {",
        "    shell();",
    ]
    for hole in holes:
        lines.append(f"    standoff({hole['x_mm']:.3f}, {hole['y_mm']:.3f}); // {hole['ref']}")
    lines.extend(["  }", "}", "", "difference() {", "  enclosure_with_standoffs();"])
    for window in windows:
        xmin, ymin, zmin, xmax, ymax, zmax = window["aperture_bounds_mm"]
        lines.extend(
            [
                f"  // {window['ref']} {window['wall_direction']} through-aperture",
                f"  translate([{xmin:.3f}, {ymin:.3f}, {zmin:.3f}])",
                f"    cube([{xmax - xmin:.3f}, {ymax - ymin:.3f}, {zmax - zmin:.3f}]);",
            ]
        )
    for hole in holes:
        lines.append(f"  screw_bore({hole['x_mm']:.3f}, {hole['y_mm']:.3f}); // {hole['ref']}")
    lines.extend(["}", ""])
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
                body = [float(value) for value in requirements["component_bodies_mm"][ref]]
            components.append(
                {
                    "body_bbox_mm": body,
                    "height_mm": float(footprint["height_mm"]),
                    "keepout_radius_mm": float(footprint["keepout_radius_mm"]),
                    "kind": footprint["kind"],
                    "ref": ref,
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
                raise ValueError(f"unsupported task-01 wall direction: {direction}")
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
        "task": "task-01",
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
        "critical_requirement": requirements["critical_requirement"],
        "enclosure_bbox_mm": enclosure,
        "input_mechanical_map": "01_kicad_mechanical_map.csv",
        "input_mechanical_map_sha256": sha256(map_path),
        "lid_inner_z_mm": enclosure[2] - lid,
        "lid_thickness_mm": lid,
        "mesh": "02_openscad_enclosure.stl",
        "minimum_side_clearance_mm": requirements["minimum_side_clearance_mm"],
        "minimum_u1_lid_clearance_mm": requirements["minimum_u1_lid_clearance_mm"],
        "software_stage": "OpenSCAD",
        "source": "02_openscad_enclosure.scad",
        "standoff_bore_diameter_mm": requirements["standoff_bore_diameter_mm"],
        "standoff_count": len(mounting_holes),
        "standoff_height_mm": requirements["standoff_height_mm"],
        "standoff_outer_diameter_mm": requirements["standoff_outer_diameter_mm"],
        "task": "task-01",
        "wall_mm": wall,
        "window_count": len(connector_rows),
    }
    json_dump(work / "02_openscad_parameters.json", params)
    (work / "02_openscad_enclosure.scad").write_text(format_scad(params, map_rows), encoding="utf-8")


if __name__ == "__main__":
    main()
