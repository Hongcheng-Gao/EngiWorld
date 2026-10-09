#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


TASK = "task-05"
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
        if not name_match or not at_match or not ref_match:
            continue
        rotation = float(at_match.group(3) or 0.0)
        if abs(rotation) > 1e-9:
            raise ValueError(f"footprint {ref_match.group(1)} is rotated")
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


def format_parameter_handoff(params: dict[str, object], map_rows: list[dict[str, object]]) -> str:
    lines = [
        "// KiCad-derived Task 05 OpenSCAD parameter handoff.",
        f"// Source map SHA-256: {params['input_mechanical_map_sha256']}",
        "$fn = 96;",
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
        f"lid_thickness = {float(params['lid_thickness_mm']):.6f};",
        f"lid_separation = {float(params['lid_separation_mm']):.6f};",
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
    lines.extend([" ];", "", "// [ref, x, y, board_hole_diameter]", "standoff_axes = ["])
    for item in params["standoff_axes"]:
        lines.append(
            f'  ["{item["ref"]}", {float(item["x_mm"]):.6f}, {float(item["y_mm"]):.6f}, '
            f'{float(item["diameter_mm"]):.6f}],'
        )
    lines.extend([" ];", "", "// [ref, x, y, diameter, cutter_zmin, cutter_zmax, path_zmin, path_zmax]", "top_bores = ["])
    for item in params["top_bores"]:
        lines.append(
            f'  ["{item["ref"]}", {float(item["x_mm"]):.6f}, {float(item["y_mm"]):.6f}, '
            f'{float(item["finished_diameter_mm"]):.6f}, {float(item["cutter_z_bounds_mm"][0]):.6f}, '
            f'{float(item["cutter_z_bounds_mm"][1]):.6f}, {float(item["path_z_bounds_mm"][0]):.6f}, '
            f'{float(item["path_z_bounds_mm"][1]):.6f}],'
        )
    lines.extend([" ];", "", "// [ref, direction, xmin, ymin, zmin, xmax, ymax, zmax]", "side_windows = ["])
    for item in params["side_windows"]:
        lines.append(
            f'  ["{item["ref"]}", "{item["direction"]}", '
            + ", ".join(f"{float(value):.6f}" for value in item["bounds_mm"])
            + "],"
        )
    lines.extend([" ];", ""])
    return "\n".join(lines)


def format_scad(params: dict[str, object]) -> str:
    return "\n".join(
        [
            "// Task 05 tray/lid generated from the trusted KiCad parameter handoff.",
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
            "module structural_tray() {",
            "  union() {",
            "    tray_shell();",
            "    for (axis = standoff_axes) standoff(axis);",
            "  }",
            "}",
            "",
            "module mounting_bores() {",
            "  for (axis = standoff_axes)",
            "    translate([axis[1], axis[2], base_thickness-standoff_bore_overcut])",
            "      cylinder(d=standoff_bore, h=standoff_height+2*standoff_bore_overcut);",
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
            "module lid_bores() {",
            "  for (access = top_bores)",
            "    translate([access[1], access[2], access[4]])",
            "      cylinder(d=access[3], h=access[5]-access[4]);",
            "}",
            "",
            "module separate_lid() {",
            "  difference() {",
            "    translate([-package_bbox[0]/2, -package_bbox[1]/2, lid_inner_z])",
            "      cube([package_bbox[0], package_bbox[1], lid_thickness]);",
            "    lid_bores();",
            "  }",
            "}",
            "",
            "installed_tray();",
            "separate_lid();",
            "",
        ]
    )


def csv_number(row: dict[str, str], key: str) -> float:
    value = row.get(key, "").strip()
    if not value:
        raise ValueError(f"connector row {row.get('ref', '?')} lacks {key}")
    return float(value)


def main() -> None:
    work = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    missing = [name for name in TRUSTED_INPUTS if not (work / name).is_file()]
    if missing:
        raise FileNotFoundError("missing trusted task-05 inputs: " + ", ".join(missing))
    trusted_hashes = {name: sha256(work / name) for name in TRUSTED_INPUTS}
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    seed_text = (work / "enclosure_seed.scad").read_text(encoding="utf-8")
    handoff_text = (work / "handoff_notes.md").read_text(encoding="utf-8")
    if requirements.get("task") != TASK or int(requirements.get("schema_version", 0)) < 2:
        raise ValueError("mechanical_requirements.json is not the frozen task-05 v2 contract")
    if "01_kicad_parameters.scad" not in seed_text or "separate lid" not in handoff_text.lower():
        raise ValueError("seed or handoff notes do not describe the frozen parameter chain")

    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connector_rows = {row["ref"]: row for row in csv.DictReader(handle)}
    expected_access_refs = {"TP1", "TP2", "TP3", "TP4", "J1"}
    if set(connector_rows) != expected_access_refs:
        raise ValueError("connector_keepouts.csv must define exactly TP1-TP4 and J1")

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
    cavity_xy = [board_bbox[0] + 2.0 * side_requirement, board_bbox[1] + 2.0 * side_requirement]
    cavity_bbox = [cavity_xy[0], cavity_xy[1], tray_top - base]
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
        or abs(board_bottom - (base + standoff_height)) > tolerance
    ):
        raise ValueError("tray/lid/board Z contract is inconsistent")

    footprints = {str(item["ref"]): item for item in parsed["footprints"]}
    component_specs = requirements["component_bodies"]
    component_refs = {ref for ref in footprints if not ref.startswith("MH")}
    if component_refs != set(component_specs) or component_refs != expected_access_refs:
        raise ValueError("KiCad component refs do not exactly match the access contract")

    map_rows: list[dict[str, object]] = []
    components: list[dict[str, object]] = []
    mounting_holes: list[dict[str, object]] = []
    standoff_axes: list[dict[str, object]] = []
    top_bores: list[dict[str, object]] = []
    side_windows: list[dict[str, object]] = []
    for footprint in parsed["footprints"]:
        ref = str(footprint["ref"])
        is_hole = ref.startswith("MH")
        access = connector_rows.get(ref)
        if is_hole:
            hole_diameter = float(footprint["hole_diameter_mm"] or 0.0)
            if abs(hole_diameter - float(requirements["mount_hole_diameter_mm"])) > tolerance:
                raise ValueError(f"{ref} hole diameter differs from the frozen contract")
            body = [0.0, 0.0, 0.0]
            role = "standoff_axis"
            hole = {
                "diameter_mm": hole_diameter,
                "ref": ref,
                "x_mm": float(footprint["x_mm"]),
                "y_mm": float(footprint["y_mm"]),
            }
            mounting_holes.append(hole)
            standoff_axes.append(dict(hole))
        else:
            spec = component_specs[ref]
            body = [float(value) for value in spec["bbox_mm"]]
            if len(body) != 3 or min(body) <= 0.0:
                raise ValueError(f"component {ref} body bbox is invalid")
            if abs(body[2] - float(footprint["height_mm"])) > tolerance:
                raise ValueError(f"component {ref} HEIGHT_MM differs from its body contract")
            hole_diameter = 0.0
            role = "access_bore" if access["access_type"] == "top_bore" else "connector_window"
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

        map_rows.append(
            {
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
                "x_mm": float(footprint["x_mm"]),
                "y_mm": float(footprint["y_mm"]),
            }
        )

        if not access:
            continue
        if access["access_type"] == "top_bore":
            if access["direction"] != "Z_PLUS":
                raise ValueError(f"{ref} top bore must use Z_PLUS")
            diameter = csv_number(access, "finished_diameter_mm")
            if abs(diameter - 2.0 * float(footprint["keepout_radius_mm"])) > tolerance:
                raise ValueError(f"{ref} bore diameter does not match its KiCad keepout diameter")
            cutter_z = [csv_number(access, "cutter_z_min_mm"), csv_number(access, "cutter_z_max_mm")]
            path_z = [csv_number(access, "path_z_min_mm"), csv_number(access, "path_z_max_mm")]
            if cutter_z != [float(value) for value in requirements["pogo_access"]["lid_bore_cutter_z_bounds_mm"]]:
                raise ValueError(f"{ref} cutter Z bounds differ from the frozen contract")
            if path_z != [float(value) for value in requirements["pogo_access"]["continuous_path_z_bounds_mm"]]:
                raise ValueError(f"{ref} path Z bounds differ from the frozen contract")
            top_bores.append(
                {
                    "access_type": "top_bore",
                    "cutter_z_bounds_mm": cutter_z,
                    "direction": "Z_PLUS",
                    "finished_diameter_mm": diameter,
                    "path_z_bounds_mm": path_z,
                    "ref": ref,
                    "x_mm": float(footprint["x_mm"]),
                    "y_mm": float(footprint["y_mm"]),
                }
            )
        elif access["access_type"] == "side_window":
            if ref != "J1" or access["direction"] != "Y_PLUS":
                raise ValueError("only J1 may define the Y_PLUS side window")
            bounds = [
                csv_number(access, "cutter_x_min_mm"),
                csv_number(access, "cutter_y_min_mm"),
                csv_number(access, "cutter_z_min_mm"),
                csv_number(access, "cutter_x_max_mm"),
                csv_number(access, "cutter_y_max_mm"),
                csv_number(access, "cutter_z_max_mm"),
            ]
            width = csv_number(access, "finished_width_mm")
            height = csv_number(access, "finished_height_mm")
            if abs((bounds[3] - bounds[0]) - width) > tolerance or abs((bounds[5] - bounds[2]) - height) > tolerance:
                raise ValueError("J1 cutter bounds do not match its finished dimensions")
            if bounds[1] > cavity_xy[1] / 2.0 or bounds[4] < enclosure[1] / 2.0:
                raise ValueError("J1 cutter does not cross the complete Y_PLUS wall")
            guards = {
                "x_minus_mm": bounds[0] + enclosure[0] / 2.0,
                "x_plus_mm": enclosure[0] / 2.0 - bounds[3],
                "z_minus_mm": bounds[2],
                "z_plus_to_tray_top_mm": tray_top - bounds[5],
            }
            if min(guards.values()) + tolerance < float(requirements["minimum_access_guard_mm"]):
                raise ValueError("J1 side window lacks the required guard")
            side_windows.append(
                {
                    "access_type": "side_window",
                    "bounds_mm": bounds,
                    "direction": "Y_PLUS",
                    "finished_height_mm": height,
                    "finished_width_mm": width,
                    "nominal_guard_mm": guards,
                    "ref": ref,
                }
            )
        else:
            raise ValueError(f"unsupported access type for {ref}: {access['access_type']}")

    if len(standoff_axes) != 4 or {item["ref"] for item in top_bores} != {"TP1", "TP2", "TP3", "TP4"} or len(side_windows) != 1:
        raise ValueError("task-05 requires four standoffs, four top bores, and one side window")
    maximum_component_height = max(float(item["height_mm"]) for item in components)
    minimum_top_clearance = lid_inner - (board_top + maximum_component_height)
    if minimum_top_clearance + tolerance < float(requirements["minimum_top_clearance_mm"]):
        raise ValueError("installed component stack lacks the required top clearance")

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
        "finished_diameter_mm", "alignment_tolerance_mm",
    ]
    with (work / "01_kicad_mechanical_map.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in map_rows:
            writer.writerow({name: row[name] for name in fieldnames})

    map_path = work / "01_kicad_mechanical_map.csv"
    params: dict[str, object] = {
        "access_center_tolerance_mm": requirements["access_center_tolerance_mm"],
        "access_overcut_mm": requirements["access_overcut_mm"],
        "accesses": [*top_bores, *side_windows],
        "base_thickness_mm": base,
        "board_bbox_mm": board_bbox,
        "board_bottom_z_mm": board_bottom,
        "board_top_z_mm": board_top,
        "cavity_bbox_mm": cavity_bbox,
        "cavity_bounds_mm": [-cavity_xy[0] / 2.0, -cavity_xy[1] / 2.0, base, cavity_xy[0] / 2.0, cavity_xy[1] / 2.0, tray_top],
        "critical_requirement": requirements["critical_requirement"],
        "enclosure_bbox_mm": enclosure,
        "enclosure_material": requirements["enclosure_material"],
        "enclosure_material_density_g_cm3": requirements["enclosure_material_density_g_cm3"],
        "input_mechanical_map": "01_kicad_mechanical_map.csv",
        "input_mechanical_map_sha256": sha256(map_path),
        "input_parameter_handoff": "01_kicad_parameters.scad",
        "lid_bounds_mm": [-enclosure[0] / 2.0, -enclosure[1] / 2.0, lid_inner, enclosure[0] / 2.0, enclosure[1] / 2.0, enclosure[2]],
        "lid_inner_z_mm": lid_inner,
        "lid_separation_mm": lid_separation,
        "lid_thickness_mm": lid,
        "minimum_side_clearance_mm": side_requirement,
        "minimum_top_clearance_mm": requirements["minimum_top_clearance_mm"],
        "nominal_minimum_top_clearance_mm": minimum_top_clearance,
        "side_windows": side_windows,
        "source": "02_openscad_enclosure.scad",
        "source_mechanical_map": "01_kicad_mechanical_map.csv",
        "standoff_axes": standoff_axes,
        "standoff_bore_diameter_mm": requirements["standoff_bore_diameter_mm"],
        "standoff_bore_overcut_mm": requirements["standoff_bore_overcut_mm"],
        "standoff_bore_z_bounds_mm": [
            base - float(requirements["standoff_bore_overcut_mm"]),
            board_bottom + float(requirements["standoff_bore_overcut_mm"]),
        ],
        "standoff_count": len(standoff_axes),
        "standoff_height_mm": standoff_height,
        "standoff_outer_diameter_mm": requirements["standoff_outer_diameter_mm"],
        "task": TASK,
        "top_bore_count": len(top_bores),
        "top_bores": top_bores,
        "tray_bounds_mm": [-enclosure[0] / 2.0, -enclosure[1] / 2.0, 0.0, enclosure[0] / 2.0, enclosure[1] / 2.0, tray_top],
        "tray_outer_top_z_mm": tray_top,
        "wall_mm": wall,
        "window_count": len(side_windows),
        "mesh": "02_openscad_enclosure.stl",
        "software_stage": "OpenSCAD",
    }
    parameter_path = work / "01_kicad_parameters.scad"
    parameter_path.write_text(format_parameter_handoff(params, map_rows), encoding="utf-8")
    params["input_parameter_handoff_sha256"] = sha256(parameter_path)
    (work / "02_openscad_enclosure.scad").write_text(format_scad(params), encoding="utf-8")
    params["source_sha256"] = sha256(work / "02_openscad_enclosure.scad")
    json_dump(work / "02_openscad_parameters.json", params)


if __name__ == "__main__":
    main()
