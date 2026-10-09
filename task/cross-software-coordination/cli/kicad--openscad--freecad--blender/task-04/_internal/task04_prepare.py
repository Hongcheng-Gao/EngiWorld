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


TASK = "task-04"
TRUSTED_INPUTS = (
    "board_input.kicad_pcb",
    "mechanical_requirements.json",
    "connector_keepouts.csv",
    "enclosure_seed.scad",
    "handoff_notes.md",
)


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
    return float(match.group(1)) if match else default


def parse_board(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if "(kicad_pcb" not in text:
        raise ValueError("board_input.kicad_pcb is not a KiCad PCB document")
    thickness_match = re.search(r"\((?:board_thickness|thickness)\s+([-+0-9.]+)\)", text)
    if not thickness_match:
        raise ValueError("KiCad general section has no board thickness")

    outline_points: list[tuple[float, float]] = []
    for block in sexpr_blocks(text, "(gr_rect "):
        if '"Edge.Cuts"' not in block:
            continue
        start = re.search(r"\(start\s+([-+0-9.]+)\s+([-+0-9.]+)\)", block)
        end = re.search(r"\(end\s+([-+0-9.]+)\s+([-+0-9.]+)\)", block)
        if start and end:
            outline_points.extend(
                [
                    (float(start.group(1)), float(start.group(2))),
                    (float(end.group(1)), float(end.group(2))),
                ]
            )
    if not outline_points:
        for block in sexpr_blocks(text, "(gr_line "):
            if '"Edge.Cuts"' not in block:
                continue
            start = re.search(r"\(start\s+([-+0-9.]+)\s+([-+0-9.]+)\)", block)
            end = re.search(r"\(end\s+([-+0-9.]+)\s+([-+0-9.]+)\)", block)
            if start and end:
                outline_points.extend(
                    [
                        (float(start.group(1)), float(start.group(2))),
                        (float(end.group(1)), float(end.group(2))),
                    ]
                )
    if not outline_points:
        raise ValueError("KiCad board has no rectangular Edge.Cuts geometry")

    xmin = min(point[0] for point in outline_points)
    ymin = min(point[1] for point in outline_points)
    xmax = max(point[0] for point in outline_points)
    ymax = max(point[1] for point in outline_points)
    if xmax <= xmin or ymax <= ymin:
        raise ValueError("KiCad Edge.Cuts bounds are degenerate")

    footprints: list[dict[str, object]] = []
    for block in sexpr_blocks(text, "(footprint "):
        name_match = re.search(r'\(footprint\s+"([^"]+)"', block)
        at_match = re.search(r"\(at\s+([-+0-9.]+)\s+([-+0-9.]+)(?:\s+([-+0-9.]+))?", block)
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not ref_match:
            ref_match = re.search(r'\(fp_text\s+reference\s+"?([^"\s\)]+)', block)
        if not name_match or not at_match or not ref_match:
            continue
        rotation = float(at_match.group(3) or 0.0)
        if abs(rotation) > 1e-9:
            raise ValueError(f"footprint {ref_match.group(1)} is rotated; task-04 requires unrotated coordinates")
        hole_diameter = number_property(block, "HOLE_DIA_MM")
        if hole_diameter is None:
            drill_match = re.search(r"\(drill(?:\s+oval)?\s+([-+0-9.]+)", block)
            hole_diameter = float(drill_match.group(1)) if drill_match else None
        footprints.append(
            {
                "footprint": name_match.group(1),
                "height_mm": number_property(block, "HEIGHT_MM", 0.0),
                "hole_diameter_mm": hole_diameter,
                "keepout_radius_mm": number_property(block, "KEEPOUT_RADIUS_MM", 0.0),
                "kind": name_match.group(1).split(":")[-1],
                "ref": ref_match.group(1),
                "x_mm": float(at_match.group(1)),
                "y_mm": float(at_match.group(2)),
            }
        )
    refs = [str(item["ref"]) for item in footprints]
    if not refs or len(refs) != len(set(refs)):
        raise ValueError("KiCad board has no footprints or contains duplicate references")
    return {
        "bounds_mm": [xmin, ymin, xmax, ymax],
        "footprints": footprints,
        "thickness_mm": float(thickness_match.group(1)),
    }


def vector(values: list[float]) -> str:
    return "[" + ", ".join(f"{float(value):.6f}" for value in values) + "]"


def box_separation_xy(x: float, y: float, radius: float, bounds: list[float]) -> float:
    xmin, ymin, _, xmax, ymax, _ = bounds
    dx = max(xmin - x, 0.0, x - xmax)
    dy = max(ymin - y, 0.0, y - ymax)
    return math.hypot(dx, dy) - radius


def format_parameter_handoff(params: dict[str, object], map_rows: list[dict[str, object]]) -> str:
    lines = [
        "// KiCad-derived Task 04 OpenSCAD parameter handoff.",
        f"// Source map SHA-256: {params['input_mechanical_map_sha256']}",
        "$fn = 64;",
        f"board_bbox = {vector(params['board_bbox_mm'])};",
        "board = board_bbox;",
        f"package_bbox = {vector(params['enclosure_bbox_mm'])};",
        "enclosure = package_bbox;",
        f"cavity_xy = {vector(params['cavity_bbox_mm'][:2])};",
        f"wall_mm = {float(params['wall_mm']):.6f};",
        "wall = wall_mm;",
        f"base_thickness = {float(params['base_thickness_mm']):.6f};",
        f"tray_outer_top_z = {float(params['tray_outer_top_z_mm']):.6f};",
        f"lid_inner_z = {float(params['lid_inner_z_mm']):.6f};",
        f"lid_separation = {float(params['lid_separation_mm']):.6f};",
        f"lid_thickness = {float(params['lid_thickness_mm']):.6f};",
        f"board_bottom_z = {float(params['board_bottom_z_mm']):.6f};",
        f"board_top_z = {float(params['board_top_z_mm']):.6f};",
        f"standoff_height = {float(params['standoff_height_mm']):.6f};",
        f"standoff_od = {float(params['standoff_outer_diameter_mm']):.6f};",
        f"standoff_bore = {float(params['standoff_bore_diameter_mm']):.6f};",
        f"standoff_bore_overcut = {float(params['standoff_bore_overcut_mm']):.6f};",
        f"access_overcut = {float(params['access_overcut_mm']):.6f};",
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
    lines.extend(["];", "// [ref, x, y, hole_diameter]", "standoff_axes = ["])
    for item in params["standoff_axes"]:
        lines.append(
            f'  ["{item["ref"]}", {float(item["x_mm"]):.6f}, {float(item["y_mm"]):.6f}, '
            f'{float(item["diameter_mm"]):.6f}],'
        )
    lines.extend(["];", "// [id, xmin, ymin, zmin, xmax, ymax, zmax]", "required_ribs = ["])
    for item in params["required_ribs"]:
        lines.append(
            f'  ["{item["id"]}", '
            + ", ".join(f"{float(value):.6f}" for value in item["bounds_mm"])
            + "],"
        )
    lines.extend(["];", "// [ref, direction, xmin, ymin, zmin, xmax, ymax, zmax]", "side_windows = ["])
    for item in params["side_windows"]:
        lines.append(
            f'  ["{item["ref"]}", "{item["direction"]}", '
            + ", ".join(f"{float(value):.6f}" for value in item["bounds_mm"])
            + "],"
        )
    lines.extend(["];", "// [ref, x, y, radius, zmin, zmax]", "rib_keepout_columns = ["])
    for item in params["rib_keepout_columns"]:
        lines.append(
            f'  ["{item["ref"]}", {float(item["x_mm"]):.6f}, {float(item["y_mm"]):.6f}, '
            f'{float(item["radius_mm"]):.6f}, {float(item["z_min_mm"]):.6f}, '
            f'{float(item["z_max_mm"]):.6f}],'
        )
    lines.extend(["];", ""])
    return "\n".join(lines)


def format_scad(params: dict[str, object]) -> str:
    return "\n".join(
        [
            "// Task 04 tray generated from the trusted KiCad parameter handoff.",
            f"// Input map SHA-256: {params['input_mechanical_map_sha256']}",
            f"// Input parameter SHA-256: {params['input_parameter_handoff_sha256']}",
            "include <01_kicad_parameters.scad>;",
            "",
            "module tray_shell() {",
            "  difference() {",
            "    translate([-package_bbox[0]/2, -package_bbox[1]/2, 0])",
            "      cube([package_bbox[0], package_bbox[1], tray_outer_top_z]);",
            "    translate([-cavity_xy[0]/2, -cavity_xy[1]/2, base_thickness])",
            "      cube([cavity_xy[0], cavity_xy[1], tray_outer_top_z-base_thickness+access_overcut]);",
            "  }",
            "}",
            "",
            "module standoff(axis) {",
            "  translate([axis[1], axis[2], base_thickness])",
            "    cylinder(d=standoff_od, h=standoff_height);",
            "}",
            "",
            "module required_rib(rib) {",
            "  translate([rib[1], rib[2], rib[3]])",
            "    cube([rib[4]-rib[1], rib[5]-rib[2], rib[6]-rib[3]]);",
            "}",
            "",
            "module structural_tray() {",
            "  union() {",
            "    tray_shell();",
            "    for (axis = standoff_axes) standoff(axis);",
            "    for (rib = required_ribs) required_rib(rib);",
            "  }",
            "}",
            "",
            "module mounting_bores() {",
            "  for (axis = standoff_axes)",
            "    translate([axis[1], axis[2], -standoff_bore_overcut])",
            "      cylinder(d=standoff_bore, h=board_bottom_z+2*standoff_bore_overcut);",
            "}",
            "",
            "module bounded_side_windows() {",
            "  for (access = side_windows)",
            "    translate([access[2], access[3], access[4]])",
            "      cube([access[5]-access[2], access[6]-access[3], access[7]-access[4]]);",
            "}",
            "",
            "module installed_tray() {",
            "  difference() {",
            "    structural_tray();",
            "    mounting_bores();",
            "    bounded_side_windows();",
            "  }",
            "}",
            "",
            "module separate_lid() {",
            "  translate([-package_bbox[0]/2, -package_bbox[1]/2, lid_inner_z])",
            "    cube([package_bbox[0], package_bbox[1], lid_thickness]);",
            "}",
            "",
            "installed_tray();",
            "separate_lid();",
            "",
        ]
    )


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    missing = [name for name in TRUSTED_INPUTS if not (work / name).is_file()]
    if missing:
        raise FileNotFoundError("missing trusted task-04 inputs: " + ", ".join(missing))
    trusted_hashes = {name: sha256(work / name) for name in TRUSTED_INPUTS}
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    seed_text = (work / "enclosure_seed.scad").read_text(encoding="utf-8")
    handoff_text = (work / "handoff_notes.md").read_text(encoding="utf-8")
    if requirements.get("task") != TASK or int(requirements.get("schema_version", 0)) < 2:
        raise ValueError("mechanical_requirements.json is not the frozen task-04 v2 contract")
    if "01_kicad_parameters.scad" not in seed_text or "separate" not in handoff_text.lower():
        raise ValueError("seed or handoff notes do not describe the frozen parameter chain")

    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connector_rows = {row["ref"]: row for row in csv.DictReader(handle)}
    parsed = parse_board(work / "board_input.kicad_pcb")
    xmin, ymin, xmax, ymax = (float(value) for value in parsed["bounds_mm"])
    board_thickness = float(parsed["thickness_mm"])
    board_bbox = [xmax - xmin, ymax - ymin, board_thickness]
    tolerance = float(requirements["axis_tolerance_mm"])
    if abs((xmin + xmax) / 2.0) > tolerance or abs((ymin + ymax) / 2.0) > tolerance:
        raise ValueError("KiCad board outline is not centered on the required XY origin")

    enclosure = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    wall = float(requirements["wall_mm"])
    base = float(requirements["base_thickness_mm"])
    lid = float(requirements["lid_thickness_mm"])
    tray_top = float(requirements["tray_outer_top_z_mm"])
    lid_inner = float(requirements["lid_inner_z_mm"])
    lid_separation = float(requirements["lid_separation_mm"])
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + board_thickness
    standoff_height = float(requirements["standoff_height_mm"])
    side_requirement = float(requirements["minimum_side_clearance_mm"])
    access_overcut = float(requirements["access_overcut_mm"])
    bore_overcut = float(requirements["standoff_bore_overcut_mm"])
    minimum_guard = float(requirements["minimum_access_guard_mm"])
    cavity_xy = [board_bbox[0] + 2.0 * side_requirement, board_bbox[1] + 2.0 * side_requirement]
    cavity_bbox = [cavity_xy[0], cavity_xy[1], round(tray_top - base, 6)]

    if any(
        abs(actual - expected) > tolerance
        for actual, expected in zip(
            [cavity_xy[0] + 2.0 * wall, cavity_xy[1] + 2.0 * wall], enclosure[:2]
        )
    ):
        raise ValueError("enclosure XY does not equal board + side clearances + walls")
    if (
        abs(enclosure[2] - (lid_inner + lid)) > tolerance
        or abs((lid_inner - tray_top) - lid_separation) > tolerance
        or lid_separation <= 0.0
    ):
        raise ValueError("tray/lid Z contract does not match the enclosure height")
    if abs(board_bottom - (base + standoff_height)) > tolerance:
        raise ValueError("board bottom does not match base plus standoff height")

    footprints = {str(item["ref"]): item for item in parsed["footprints"]}
    component_specs = requirements["component_bodies"]
    component_refs = {ref for ref in footprints if not ref.startswith("MH")}
    if component_refs != set(component_specs):
        raise ValueError("KiCad component refs do not exactly match component_bodies")
    if set(connector_rows) != {"J1", "J2"}:
        raise ValueError("connector_keepouts.csv must define exactly J1 and J2")

    map_rows: list[dict[str, object]] = []
    components: list[dict[str, object]] = []
    mounting_holes: list[dict[str, object]] = []
    standoff_axes: list[dict[str, object]] = []
    side_windows: list[dict[str, object]] = []
    component_keepouts: list[dict[str, object]] = []
    rib_keepout_refs = set(requirements["rib_exclusion"]["keepout_refs"])

    for footprint in parsed["footprints"]:
        ref = str(footprint["ref"])
        is_hole = ref.startswith("MH")
        access = connector_rows.get(ref)
        if is_hole:
            body = [0.0, 0.0, 0.0]
            hole_diameter = float(footprint["hole_diameter_mm"] or 0.0)
            if abs(hole_diameter - float(requirements["mount_hole_diameter_mm"])) > tolerance:
                raise ValueError(f"{ref} hole diameter does not match the mounting contract")
            role = "standoff_axis"
            mounting_holes.append(
                {
                    "diameter_mm": hole_diameter,
                    "ref": ref,
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                }
            )
            standoff_axes.append(dict(mounting_holes[-1]))
        else:
            spec = component_specs[ref]
            body = [float(value) for value in spec["bbox_mm"]]
            if len(body) != 3 or any(value <= 0.0 for value in body):
                raise ValueError(f"component {ref} must have a positive XYZ body bbox")
            if abs(body[2] - float(footprint["height_mm"])) > tolerance:
                raise ValueError(f"component {ref} body Z differs from KiCad HEIGHT_MM")
            role = "connector_window" if access else "rib_keepout"
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
            component_keepouts.append(
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
            "finished_height_mm": float(access["finished_height_mm"]) if access else 0.0,
            "finished_width_mm": float(access["finished_width_mm"]) if access else 0.0,
            "height_mm": float(footprint["height_mm"]),
            "hole_diameter_mm": hole_diameter,
            "keepout_radius_mm": float(footprint["keepout_radius_mm"]),
            "kind": footprint["kind"] if not is_hole else "MOUNTING_HOLE",
            "ref": ref,
            "role": role,
            "through_margin_mm": access_overcut if access else 0.0,
            "vertical_margin_mm": float(access["vertical_margin_mm"]) if access else 0.0,
            "x_mm": float(footprint["x_mm"]),
            "y_mm": float(footprint["y_mm"]),
        }
        map_rows.append(row)

        if not access:
            continue
        if access["access_type"] != "side_window" or access["direction"] not in {"X_MINUS", "X_PLUS"}:
            raise ValueError(f"{ref} must define an X side_window")
        if (
            abs(float(access["body_x_mm"]) - body[0]) > tolerance
            or abs(float(access["body_y_mm"]) - body[1]) > tolerance
        ):
            raise ValueError(f"{ref} CSV body XY differs from the component contract")
        width = float(access["finished_width_mm"])
        height = float(access["finished_height_mm"])
        vertical_margin = float(access["vertical_margin_mm"])
        if abs(height - (float(footprint["height_mm"]) + 2.0 * vertical_margin)) > tolerance:
            raise ValueError(f"{ref} window height does not equal component height plus margins")
        center_z = board_top + float(footprint["height_mm"]) / 2.0
        y1 = float(footprint["y_mm"]) - width / 2.0
        y2 = float(footprint["y_mm"]) + width / 2.0
        z1, z2 = center_z - height / 2.0, center_z + height / 2.0
        if access["direction"] == "X_PLUS":
            x1 = float(footprint["x_mm"]) - body[0] / 2.0
            x2 = enclosure[0] / 2.0 + access_overcut
        else:
            x1 = -enclosure[0] / 2.0 - access_overcut
            x2 = float(footprint["x_mm"]) + body[0] / 2.0
        guards = {
            "y_minus": y1 + enclosure[1] / 2.0,
            "y_plus": enclosure[1] / 2.0 - y2,
            "z_minus": z1,
            "z_plus": tray_top - z2,
        }
        if min(guards.values()) + tolerance < minimum_guard:
            raise ValueError(f"{ref} side window lacks the minimum bounded guard")
        side_windows.append(
            {
                "access_type": "side_window",
                "bounds_mm": [round(value, 6) for value in [x1, y1, z1, x2, y2, z2]],
                "centerline_xy_mm": [float(footprint["x_mm"]), float(footprint["y_mm"])],
                "direction": access["direction"],
                "finished_height_mm": height,
                "finished_width_mm": width,
                "nominal_guard_mm": {key: round(value, 6) for key, value in guards.items()},
                "ref": ref,
            }
        )

    if len(standoff_axes) != 4:
        raise ValueError(f"task-04 requires four mounting axes, found {len(standoff_axes)}")
    maximum_component_height = max(float(item["height_mm"]) for item in components)
    top_clearance = lid_inner - (board_top + maximum_component_height)
    if top_clearance + tolerance < float(requirements["minimum_top_clearance_mm"]):
        raise ValueError("installed component stack lacks the required top clearance")

    rib_columns = [
        {
            "radius_mm": float(footprints[ref]["keepout_radius_mm"]),
            "ref": ref,
            "x_mm": float(footprints[ref]["x_mm"]),
            "y_mm": float(footprints[ref]["y_mm"]),
            "z_max_mm": lid_inner,
            "z_min_mm": base,
        }
        for ref in requirements["rib_exclusion"]["keepout_refs"]
    ]
    if {item["ref"] for item in rib_columns} != rib_keepout_refs:
        raise ValueError("rib exclusion refs are absent from the KiCad board")
    required_ribs = []
    minimum_rib_clearance = float(requirements["minimum_rib_keepout_clearance_mm"])
    seen_rib_ids: set[str] = set()
    for raw_rib in requirements["required_ribs"]:
        rib_id = str(raw_rib["id"])
        bounds = [float(value) for value in raw_rib["bounds_mm"]]
        if rib_id in seen_rib_ids or len(bounds) != 6:
            raise ValueError("required rib IDs must be unique and have six bounds")
        seen_rib_ids.add(rib_id)
        if bounds[3] <= bounds[0] or bounds[4] <= bounds[1] or bounds[5] <= bounds[2]:
            raise ValueError(f"{rib_id} bounds are degenerate")
        if (
            bounds[0] < -cavity_xy[0] / 2.0
            or bounds[3] > cavity_xy[0] / 2.0
            or bounds[1] < -cavity_xy[1] / 2.0
            or bounds[4] > cavity_xy[1] / 2.0
            or bounds[2] < base
            or bounds[5] > board_bottom
        ):
            raise ValueError(f"{rib_id} is outside the permitted under-board cavity")
        separations = {
            item["ref"]: box_separation_xy(
                float(item["x_mm"]), float(item["y_mm"]), float(item["radius_mm"]), bounds
            )
            for item in rib_columns
        }
        if min(separations.values()) + tolerance < minimum_rib_clearance:
            raise ValueError(f"{rib_id} violates a projected MOSFET keepout")
        required_ribs.append(
            {
                "bounds_mm": bounds,
                "id": rib_id,
                "nominal_keepout_separation_mm": {
                    ref: round(value, 6) for ref, value in separations.items()
                },
            }
        )
    if len(required_ribs) != 2:
        raise ValueError("task-04 requires exactly two structural ribs")

    shutil.copyfile(work / "board_input.kicad_pcb", work / "01_kicad_board.kicad_pcb")
    export = {
        "board_bbox_mm": board_bbox,
        "board_bounds_xy_mm": [xmin, ymin, xmax, ymax],
        "components": components,
        "coordinate_system": requirements["coordinate_system"],
        "corrected_board": "01_kicad_board.kicad_pcb",
        "critical_requirement": requirements["critical_requirement"],
        "input_board": "board_input.kicad_pcb",
        "input_board_sha256": trusted_hashes["board_input.kicad_pcb"],
        "max_component_height_mm": maximum_component_height,
        "mechanical_map": "01_kicad_mechanical_map.csv",
        "mounting_holes": mounting_holes,
        "openscad_parameter_handoff": "01_kicad_parameters.scad",
        "software_stage": "KiCad",
        "task": TASK,
        "trusted_inputs_sha256": trusted_hashes,
    }
    json_dump(work / "01_kicad_export.json", export)

    fieldnames = [
        "ref", "kind", "x_mm", "y_mm", "height_mm", "keepout_radius_mm", "body_x_mm", "body_y_mm",
        "hole_diameter_mm", "role", "access_type", "direction", "finished_width_mm", "finished_height_mm",
        "vertical_margin_mm", "through_margin_mm", "alignment_tolerance_mm",
    ]
    with (work / "01_kicad_mechanical_map.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in map_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    map_path = work / "01_kicad_mechanical_map.csv"
    params: dict[str, object] = {
        "access_center_tolerance_mm": requirements["access_center_tolerance_mm"],
        "access_overcut_mm": access_overcut,
        "accesses": side_windows,
        "base_thickness_mm": base,
        "board_bbox_mm": board_bbox,
        "board_bottom_z_mm": board_bottom,
        "board_top_z_mm": board_top,
        "cavity_bbox_mm": cavity_bbox,
        "cavity_bounds_mm": [
            round(value, 6)
            for value in [-cavity_xy[0] / 2.0, -cavity_xy[1] / 2.0, base, cavity_xy[0] / 2.0, cavity_xy[1] / 2.0, tray_top]
        ],
        "component_keepout_volumes": component_keepouts,
        "critical_requirement": requirements["critical_requirement"],
        "enclosure_bbox_mm": enclosure,
        "enclosure_material": requirements["enclosure_material"],
        "enclosure_material_density_g_cm3": requirements["enclosure_material_density_g_cm3"],
        "input_mechanical_map": "01_kicad_mechanical_map.csv",
        "input_mechanical_map_sha256": sha256(map_path),
        "input_parameter_handoff": "01_kicad_parameters.scad",
        "lid_bounds_mm": [
            round(value, 6)
            for value in [-enclosure[0] / 2.0, -enclosure[1] / 2.0, lid_inner, enclosure[0] / 2.0, enclosure[1] / 2.0, enclosure[2]]
        ],
        "lid_inner_z_mm": lid_inner,
        "lid_separation_mm": lid_separation,
        "lid_thickness_mm": lid,
        "mesh": "02_openscad_enclosure.stl",
        "minimum_access_guard_mm": minimum_guard,
        "minimum_rib_keepout_clearance_mm": minimum_rib_clearance,
        "minimum_side_clearance_mm": side_requirement,
        "minimum_top_clearance_mm": float(requirements["minimum_top_clearance_mm"]),
        "nominal_top_clearance_mm": round(top_clearance, 6),
        "required_ribs": required_ribs,
        "rib_count": len(required_ribs),
        "rib_keepout_columns": rib_columns,
        "side_windows": side_windows,
        "software_stage": "OpenSCAD",
        "source": "02_openscad_enclosure.scad",
        "source_mechanical_map": "01_kicad_mechanical_map.csv",
        "standoff_axes": standoff_axes,
        "standoff_bore_diameter_mm": requirements["standoff_bore_diameter_mm"],
        "standoff_bore_overcut_mm": bore_overcut,
        "standoff_count": len(standoff_axes),
        "standoff_height_mm": standoff_height,
        "standoff_outer_diameter_mm": requirements["standoff_outer_diameter_mm"],
        "task": TASK,
        "tray_outer_top_z_mm": tray_top,
        "trusted_inputs_sha256": trusted_hashes,
        "wall_mm": wall,
        "window_count": len(side_windows),
    }
    parameter_text = format_parameter_handoff(params, map_rows)
    (work / "01_kicad_parameters.scad").write_text(parameter_text, encoding="utf-8")
    params["input_parameter_handoff_sha256"] = sha256(work / "01_kicad_parameters.scad")
    (work / "02_openscad_enclosure.scad").write_text(format_scad(params), encoding="utf-8")
    json_dump(work / "02_openscad_parameters.json", params)


if __name__ == "__main__":
    main()
