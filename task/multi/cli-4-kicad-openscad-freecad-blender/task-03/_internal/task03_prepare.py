#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
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

    refs = [str(item["ref"]) for item in footprints]
    if len(refs) != len(set(refs)):
        raise ValueError("KiCad board contains duplicate reference designators")
    return {
        "bounds_mm": [min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)],
        "footprints": footprints,
        "text": text,
        "thickness_mm": float(thickness_match.group(1)),
    }


def vector(values: list[float]) -> str:
    return "[" + ", ".join(f"{float(value):.6f}" for value in values) + "]"


def format_parameter_handoff(params: dict[str, object], map_rows: list[dict[str, object]]) -> str:
    lines = [
        "// KiCad-derived Task 03 OpenSCAD parameter handoff.",
        f"// Source map SHA-256: {params['input_mechanical_map_sha256']}",
        "$fn = 64;",
        f"board = {vector(params['board_bbox_mm'])};",
        f"enclosure = {vector(params['enclosure_bbox_mm'])};",
        f"cavity = {vector(params['cavity_bbox_mm'])};",
        f"wall = {float(params['wall_mm']):.6f};",
        f"base_thickness = {float(params['base_thickness_mm']):.6f};",
        f"lid_thickness = {float(params['lid_thickness_mm']):.6f};",
        f"board_bottom_z = {float(params['board_bottom_z_mm']):.6f};",
        f"board_top_z = {float(params['board_top_z_mm']):.6f};",
        f"lid_inner_z = {float(params['lid_inner_z_mm']):.6f};",
        f"standoff_height = {float(params['standoff_height_mm']):.6f};",
        f"standoff_od = {float(params['standoff_outer_diameter_mm']):.6f};",
        f"standoff_bore = {float(params['standoff_bore_diameter_mm']):.6f};",
        f"access_overcut = {float(params['access_overcut_mm']):.6f};",
        f"shield_center = {vector(params['shield']['center_xy_mm'])};",
        f"shield_inner_xy = {vector(params['shield']['inner_bbox_xy_mm'])};",
        f"shield_wall = {float(params['shield']['wall_thickness_mm']):.6f};",
        f"shield_inner_top_z = {float(params['shield']['inner_top_z_mm']):.6f};",
        f"shield_outer_top_z = {float(params['shield']['outer_top_z_mm']):.6f};",
        f"protected_volume = {vector(params['protected_volume']['bounds_mm'])};",
        "",
        "// [ref, kind, x, y, height, keepout_radius, body_x, body_y, role]",
        "mechanical_features = [",
    ]
    for row in map_rows:
        lines.append(
            f'  ["{row["ref"]}", "{row["kind"]}", {float(row["x_mm"]):.6f}, '
            f'{float(row["y_mm"]):.6f}, {float(row["height_mm"]):.6f}, '
            f'{float(row["keepout_radius_mm"]):.6f}, {float(row["body_x_mm"]):.6f}, '
            f'{float(row["body_y_mm"]):.6f}, "{row["role"]}"],'
        )
    lines.extend(["];", "// [ref, x, y]", "standoff_axes = ["])
    for item in params["standoff_axes"]:
        lines.append(f'  ["{item["ref"]}", {item["x_mm"]:.6f}, {item["y_mm"]:.6f}],')

    lines.extend(["];", "// [ref, direction, xmin, ymin, zmin, xmax, ymax, zmax]", "side_accesses = ["])
    for item in params["side_windows"]:
        bounds = item["bounds_mm"]
        lines.append(
            f'  ["{item["ref"]}", "{item["direction"]}", '
            + ", ".join(f"{float(value):.6f}" for value in bounds)
            + "],"
        )

    lines.extend(["];", "// [ref, x, y, diameter, zmin, zmax]", "top_accesses = ["])
    for item in params["top_bores"]:
        lines.append(
            f'  ["{item["ref"]}", {item["center_xy_mm"][0]:.6f}, {item["center_xy_mm"][1]:.6f}, '
            f'{item["finished_diameter_mm"]:.6f}, {item["z_min_mm"]:.6f}, {item["z_max_mm"]:.6f}],'
        )

    lines.extend(["];", "// [ref, x, y, radius, zmin, zmax]", "keepout_volumes = ["])
    for item in params["keepout_volumes"]:
        lines.append(
            f'  ["{item["ref"]}", {item["x_mm"]:.6f}, {item["y_mm"]:.6f}, '
            f'{item["radius_mm"]:.6f}, {item["z_min_mm"]:.6f}, {item["z_max_mm"]:.6f}],'
        )
    lines.extend(["];", ""])
    return "\n".join(lines)


def format_scad(params: dict[str, object]) -> str:
    return "\n".join(
        [
            "// Task 03 package and RF shield generated from the KiCad parameter handoff.",
            f"// Input map SHA-256: {params['input_mechanical_map_sha256']}",
            "include <01_kicad_parameters.scad>;",
            "",
            "module package_shell() {",
            "  difference() {",
            "    translate([-enclosure[0]/2, -enclosure[1]/2, 0]) cube(enclosure);",
            "    translate([-cavity[0]/2, -cavity[1]/2, base_thickness])",
            "      cube([cavity[0], cavity[1], lid_inner_z - base_thickness]);",
            "  }",
            "}",
            "",
            "module standoff(x, y) {",
            "  translate([x, y, base_thickness]) cylinder(d=standoff_od, h=standoff_height);",
            "}",
            "",
            "module package_with_standoffs() {",
            "  union() {",
            "    package_shell();",
            "    for (axis = standoff_axes) standoff(axis[1], axis[2]);",
            "  }",
            "}",
            "",
            "module mounting_bores() {",
            "  for (axis = standoff_axes)",
            "    translate([axis[1], axis[2], -access_overcut])",
            "      cylinder(d=standoff_bore, h=board_bottom_z + 2*access_overcut);",
            "}",
            "",
            "module side_access_cutouts() {",
            "  for (access = side_accesses)",
            "    translate([access[2], access[3], access[4]])",
            "      cube([access[5]-access[2], access[6]-access[3], access[7]-access[4]]);",
            "}",
            "",
            "module top_access_cutouts() {",
            "  for (access = top_accesses)",
            "    translate([access[1], access[2], access[4]])",
            "      cylinder(d=access[3], h=access[5]-access[4]);",
            "}",
            "",
            "module installed_package() {",
            "  difference() {",
            "    package_with_standoffs();",
            "    mounting_bores();",
            "    side_access_cutouts();",
            "    top_access_cutouts();",
            "  }",
            "}",
            "",
            "module rf_shield_can() {",
            "  shield_outer_xy = [shield_inner_xy[0] + 2*shield_wall, shield_inner_xy[1] + 2*shield_wall];",
            "  difference() {",
            "    translate([shield_center[0]-shield_outer_xy[0]/2, shield_center[1]-shield_outer_xy[1]/2, board_top_z])",
            "      cube([shield_outer_xy[0], shield_outer_xy[1], shield_outer_top_z-board_top_z]);",
            "    translate([shield_center[0]-shield_inner_xy[0]/2, shield_center[1]-shield_inner_xy[1]/2, board_top_z-access_overcut])",
            "      cube([shield_inner_xy[0], shield_inner_xy[1], shield_inner_top_z-board_top_z+access_overcut]);",
            "  }",
            "}",
            "",
            "union() {",
            "  installed_package();",
            "  rf_shield_can();",
            "}",
            "",
        ]
    )


def circle_box_separation(x: float, y: float, radius: float, bounds: list[float]) -> float:
    xmin, ymin, _, xmax, ymax, _ = bounds
    dx = max(xmin - x, 0.0, x - xmax)
    dy = max(ymin - y, 0.0, y - ymax)
    return math.hypot(dx, dy) - radius


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
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + thickness
    lid_inner = enclosure[2] - lid
    overcut = float(requirements["access_overcut_mm"])
    minimum_guard = float(requirements["minimum_access_guard_mm"])
    cavity = [enclosure[0] - 2 * wall, enclosure[1] - 2 * wall, lid_inner - base]
    if min(cavity) <= 0:
        raise ValueError("package cavity dimensions must be positive")
    if abs(board_bottom - (base + float(requirements["standoff_height_mm"]))) > 1e-9:
        raise ValueError("board_bottom_z_mm must equal base_thickness_mm + standoff_height_mm")
    side_clearances = [(cavity[0] - board_bbox[0]) / 2.0, (cavity[1] - board_bbox[1]) / 2.0]
    if min(side_clearances) + 1e-9 < float(requirements["minimum_side_clearance_mm"]):
        raise ValueError("package cavity does not provide the required PCB side clearance")

    footprint_by_ref = {str(item["ref"]): item for item in parsed["footprints"]}
    component_specs = requirements["component_bodies"]
    missing_specs = sorted(ref for ref in footprint_by_ref if not ref.startswith("MH") and ref not in component_specs)
    if missing_specs:
        raise ValueError(f"component_bodies lacks {', '.join(missing_specs)}")
    unknown_access_refs = sorted(set(connector_rows) - set(footprint_by_ref))
    if unknown_access_refs:
        raise ValueError(f"connector CSV references unknown footprints: {', '.join(unknown_access_refs)}")

    map_rows: list[dict[str, object]] = []
    components: list[dict[str, object]] = []
    mounting_holes: list[dict[str, object]] = []
    standoff_axes: list[dict[str, object]] = []
    accesses: list[dict[str, object]] = []
    keepout_volumes: list[dict[str, object]] = []

    for footprint in parsed["footprints"]:
        ref = str(footprint["ref"])
        is_hole = ref.startswith("MH")
        access = connector_rows.get(ref)
        if is_hole:
            body = [0.0, 0.0, 0.0]
            role = "standoff_axis"
            hole_diameter = float(footprint["hole_diameter_mm"] or 0.0)
            mounting_holes.append(
                {
                    "diameter_mm": hole_diameter,
                    "ref": ref,
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                }
            )
            standoff_axes.append(
                {"ref": ref, "x_mm": float(footprint["x_mm"]), "y_mm": float(footprint["y_mm"])}
            )
        else:
            spec = component_specs[ref]
            body = [float(value) for value in spec["bbox_mm"]]
            if len(body) != 3 or any(value <= 0 for value in body):
                raise ValueError(f"component body {ref} must have a positive XYZ bbox")
            if abs(body[2] - float(footprint["height_mm"])) > 1e-9:
                raise ValueError(f"component body {ref} Z must match KiCad HEIGHT_MM")
            role = "access_bore" if access and access["access_type"] == "top_bore" else (
                "connector_window" if access else "component_keepout"
            )
            components.append(
                {
                    "body_bbox_mm": body,
                    "height_mm": float(footprint["height_mm"]),
                    "keepout_radius_mm": float(footprint["keepout_radius_mm"]),
                    "kind": footprint["kind"],
                    "ref": ref,
                    "shape": spec["shape"],
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                }
            )
            keepout_volumes.append(
                {
                    "radius_mm": float(footprint["keepout_radius_mm"]),
                    "ref": ref,
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                    "z_max_mm": board_top + float(footprint["height_mm"]),
                    "z_min_mm": board_top,
                }
            )
            hole_diameter = 0.0

        row: dict[str, object] = {
            "access_type": access["access_type"] if access else "",
            "alignment_tolerance_mm": float(requirements["access_center_tolerance_mm"]) if access else 0.0,
            "body_x_mm": body[0],
            "body_y_mm": body[1],
            "direction": access["direction"] if access else "",
            "finished_diameter_mm": float(access["finished_diameter_mm"]) if access else 0.0,
            "finished_height_mm": float(access["finished_height_mm"]) if access else 0.0,
            "finished_width_mm": float(access["finished_width_mm"]) if access else 0.0,
            "height_mm": float(footprint["height_mm"]),
            "hole_diameter_mm": hole_diameter,
            "keepout_radius_mm": float(footprint["keepout_radius_mm"]),
            "kind": footprint["kind"] if not is_hole else "MOUNTING_HOLE",
            "ref": ref,
            "role": role,
            "through_margin_mm": overcut if access else 0.0,
            "vertical_margin_mm": float(access["vertical_margin_mm"]) if access else 0.0,
            "x_mm": float(footprint["x_mm"]),
            "y_mm": float(footprint["y_mm"]),
        }
        map_rows.append(row)

        if not access:
            continue
        access_type = access["access_type"]
        direction = access["direction"]
        component_height = float(footprint["height_mm"])
        if access_type == "side_window":
            if direction not in {"X_MINUS", "X_PLUS"}:
                raise ValueError(f"{ref} side window must use X_MINUS or X_PLUS")
            width = float(access["finished_width_mm"])
            height = float(access["finished_height_mm"])
            vertical_margin = float(access["vertical_margin_mm"])
            if abs(height - (component_height + 2.0 * vertical_margin)) > 1e-9:
                raise ValueError(f"{ref} height must equal KiCad height plus two vertical margins")
            center_z = board_top + component_height / 2.0
            y1 = float(footprint["y_mm"]) - width / 2.0
            y2 = float(footprint["y_mm"]) + width / 2.0
            z1, z2 = center_z - height / 2.0, center_z + height / 2.0
            if min(y1 + enclosure[1] / 2.0, enclosure[1] / 2.0 - y2, z1, enclosure[2] - z2) < minimum_guard:
                raise ValueError(f"{ref} side window does not retain the required guard material")
            if direction == "X_PLUS":
                x1 = float(footprint["x_mm"]) - body[0] / 2.0
                x2 = enclosure[0] / 2.0 + overcut
            else:
                x1 = -enclosure[0] / 2.0 - overcut
                x2 = float(footprint["x_mm"]) + body[0] / 2.0
            bounds = [round(value, 6) for value in [x1, y1, z1, x2, y2, z2]]
            accesses.append(
                {
                    "access_type": access_type,
                    "bounds_mm": bounds,
                    "centerline_xy_mm": [float(footprint["x_mm"]), float(footprint["y_mm"])],
                    "direction": direction,
                    "finished_height_mm": height,
                    "finished_width_mm": width,
                    "ref": ref,
                }
            )
        elif access_type == "top_bore":
            if direction != "Z_PLUS":
                raise ValueError(f"{ref} top bore must use Z_PLUS")
            diameter = float(access["finished_diameter_mm"])
            radius = diameter / 2.0
            cx, cy = float(footprint["x_mm"]), float(footprint["y_mm"])
            if min(cx + enclosure[0] / 2.0 - radius, enclosure[0] / 2.0 - cx - radius,
                   cy + enclosure[1] / 2.0 - radius, enclosure[1] / 2.0 - cy - radius) < minimum_guard:
                raise ValueError(f"{ref} top bore does not retain the required guard material")
            z1 = board_top + component_height
            z2 = enclosure[2] + overcut
            accesses.append(
                {
                    "access_type": access_type,
                    "center_xy_mm": [cx, cy],
                    "direction": direction,
                    "finished_diameter_mm": diameter,
                    "ref": ref,
                    "z_max_mm": z2,
                    "z_min_mm": z1,
                }
            )
        else:
            raise ValueError(f"unsupported access_type for {ref}: {access_type}")

    if len(standoff_axes) != 4:
        raise ValueError(f"expected four mounting-hole axes, found {len(standoff_axes)}")

    maximum_component_height = max(float(item["height_mm"]) for item in components)
    actual_lid_clearance = lid_inner - (board_top + maximum_component_height)
    required_lid_clearance = float(requirements["lid_clearance_above_tallest_component_mm"])
    if actual_lid_clearance + 1e-9 < required_lid_clearance:
        raise ValueError("package does not provide the required clearance above the tallest component")

    protected_spec = requirements["protected_volume"]
    shield_spec = requirements["shield"]
    center_ref = str(protected_spec["center_ref"])
    if center_ref not in footprint_by_ref:
        raise ValueError(f"protected-volume center ref {center_ref} is absent from KiCad")
    center = footprint_by_ref[center_ref]
    protected_xy = [float(value) for value in protected_spec["inner_bbox_xy_mm"]]
    if protected_xy != [float(value) for value in shield_spec["inner_bbox_xy_mm"]]:
        raise ValueError("protected and shield inner XY dimensions must agree")
    protected_bounds = [
        float(center["x_mm"]) - protected_xy[0] / 2.0,
        float(center["y_mm"]) - protected_xy[1] / 2.0,
        board_top,
        float(center["x_mm"]) + protected_xy[0] / 2.0,
        float(center["y_mm"]) + protected_xy[1] / 2.0,
        float(protected_spec["z_max_mm"]),
    ]
    if abs(protected_bounds[5] - float(shield_spec["inner_top_z_mm"])) > 1e-9:
        raise ValueError("protected z_max_mm must equal shield inner_top_z_mm")
    shield_wall = float(shield_spec["wall_thickness_mm"])
    if abs(float(shield_spec["outer_top_z_mm"]) - protected_bounds[5] - shield_wall) > 1e-9:
        raise ValueError("shield roof thickness must equal shield wall thickness")
    shield_outer_xy = [protected_xy[0] + 2 * shield_wall, protected_xy[1] + 2 * shield_wall]
    if (
        abs(float(center["x_mm"])) + shield_outer_xy[0] / 2.0 > cavity[0] / 2.0
        or abs(float(center["y_mm"])) + shield_outer_xy[1] / 2.0 > cavity[1] / 2.0
        or float(shield_spec["outer_top_z_mm"]) > lid_inner
    ):
        raise ValueError("installed RF shield does not fit inside the package cavity")

    keepout_by_ref = {item["ref"]: item for item in keepout_volumes}
    containment: dict[str, bool] = {}
    for ref in protected_spec["must_contain_keepout_refs"]:
        item = keepout_by_ref[ref]
        contained = (
            item["x_mm"] - item["radius_mm"] >= protected_bounds[0]
            and item["x_mm"] + item["radius_mm"] <= protected_bounds[3]
            and item["y_mm"] - item["radius_mm"] >= protected_bounds[1]
            and item["y_mm"] + item["radius_mm"] <= protected_bounds[4]
            and item["z_min_mm"] >= protected_bounds[2]
            and item["z_max_mm"] <= protected_bounds[5]
        )
        containment[ref] = contained
        if not contained:
            raise ValueError(f"{ref} keepout is not fully contained in the protected volume")

    exclusion_separation: dict[str, float] = {}
    for ref in protected_spec["must_exclude_keepout_refs"]:
        item = keepout_by_ref[ref]
        separation = circle_box_separation(item["x_mm"], item["y_mm"], item["radius_mm"], protected_bounds)
        exclusion_separation[ref] = round(separation, 6)
        if separation <= 0:
            raise ValueError(f"{ref} keepout is not positively separated from the protected volume")

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
        "max_component_height_mm": maximum_component_height,
        "mechanical_map": "01_kicad_mechanical_map.csv",
        "mounting_holes": mounting_holes,
        "openscad_parameter_handoff": "01_kicad_parameters.scad",
        "software_stage": "KiCad",
        "task": "task-03",
    }
    json_dump(work / "01_kicad_export.json", export)

    fieldnames = [
        "ref", "kind", "x_mm", "y_mm", "height_mm", "keepout_radius_mm", "body_x_mm", "body_y_mm",
        "hole_diameter_mm", "role", "access_type", "direction", "finished_width_mm", "finished_height_mm",
        "finished_diameter_mm", "vertical_margin_mm", "through_margin_mm", "alignment_tolerance_mm",
    ]
    with (work / "01_kicad_mechanical_map.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in map_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    map_path = work / "01_kicad_mechanical_map.csv"
    params = {
        "access_center_tolerance_mm": requirements["access_center_tolerance_mm"],
        "access_overcut_mm": overcut,
        "accesses": accesses,
        "base_thickness_mm": base,
        "board_bbox_mm": board_bbox,
        "board_bottom_z_mm": board_bottom,
        "board_top_z_mm": board_top,
        "cavity_bbox_mm": cavity,
        "critical_requirement": requirements["critical_requirement"],
        "enclosure_bbox_mm": enclosure,
        "enclosure_material": requirements["enclosure_material"],
        "enclosure_material_density_g_cm3": requirements["enclosure_material_density_g_cm3"],
        "input_mechanical_map": "01_kicad_mechanical_map.csv",
        "input_mechanical_map_sha256": sha256(map_path),
        "keepout_volumes": keepout_volumes,
        "lid_clearance_above_tallest_component_mm": actual_lid_clearance,
        "lid_inner_z_mm": lid_inner,
        "lid_thickness_mm": lid,
        "mesh": "02_openscad_enclosure.stl",
        "minimum_access_guard_mm": minimum_guard,
        "minimum_side_clearance_mm": min(side_clearances),
        "protected_volume": {
            "bounds_mm": [round(value, 6) for value in protected_bounds],
            "center_ref": center_ref,
            "excluded_keepout_separation_mm": exclusion_separation,
            "must_contain_keepout_refs": protected_spec["must_contain_keepout_refs"],
            "must_exclude_keepout_refs": protected_spec["must_exclude_keepout_refs"],
            "u1_keepout_containment": containment,
        },
        "shield": {
            "center_ref": center_ref,
            "center_xy_mm": [float(center["x_mm"]), float(center["y_mm"])],
            "inner_bbox_xy_mm": protected_xy,
            "inner_top_z_mm": float(shield_spec["inner_top_z_mm"]),
            "material": shield_spec["material"],
            "material_density_g_cm3": shield_spec["material_density_g_cm3"],
            "outer_bbox_xy_mm": shield_outer_xy,
            "outer_top_z_mm": float(shield_spec["outer_top_z_mm"]),
            "wall_thickness_mm": shield_wall,
        },
        "side_windows": [item for item in accesses if item["access_type"] == "side_window"],
        "software_stage": "OpenSCAD",
        "source": "02_openscad_enclosure.scad",
        "source_mechanical_map": "01_kicad_mechanical_map.csv",
        "standoff_axes": standoff_axes,
        "standoff_bore_diameter_mm": requirements["standoff_bore_diameter_mm"],
        "standoff_count": len(standoff_axes),
        "standoff_height_mm": requirements["standoff_height_mm"],
        "standoff_outer_diameter_mm": requirements["standoff_outer_diameter_mm"],
        "task": "task-03",
        "top_bores": [item for item in accesses if item["access_type"] == "top_bore"],
        "wall_mm": wall,
        "window_count": sum(item["access_type"] == "side_window" for item in accesses),
    }
    json_dump(work / "02_openscad_parameters.json", params)
    (work / "01_kicad_parameters.scad").write_text(format_parameter_handoff(params, map_rows), encoding="utf-8")
    (work / "02_openscad_enclosure.scad").write_text(format_scad(params), encoding="utf-8")


if __name__ == "__main__":
    main()
