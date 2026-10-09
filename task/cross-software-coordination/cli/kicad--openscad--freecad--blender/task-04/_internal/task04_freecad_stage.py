#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart
import Part


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def positive_solids(shape: Part.Shape, volume_tolerance: float) -> list[Part.Shape]:
    if shape.isNull():
        return []
    return [solid for solid in shape.Solids if float(solid.Volume) > volume_tolerance]


def mesh_to_material(path: Path, volume_tolerance: float) -> tuple[Mesh.Mesh, Part.Shape]:
    mesh = Mesh.Mesh(str(path))
    raw = Part.Shape()
    raw.makeShapeFromMesh(mesh.Topology, 0.05)

    solids: list[Part.Shape] = []
    for shell in raw.Shells:
        if not shell.isClosed():
            continue
        solid = Part.makeSolid(shell).removeSplitter()
        if solid.isValid() and float(solid.Volume) > volume_tolerance:
            solids.append(solid)
    if not solids:
        raise RuntimeError("OpenSCAD STL contains no valid closed material solid")
    return mesh, Part.makeCompound(solids)


def box_from_bounds(bounds: list[float], inset: float = 0.0) -> Part.Shape:
    xmin, ymin, zmin, xmax, ymax, zmax = (float(value) for value in bounds)
    return Part.makeBox(
        max(0.001, xmax - xmin - 2.0 * inset),
        max(0.001, ymax - ymin - 2.0 * inset),
        max(0.001, zmax - zmin - 2.0 * inset),
        App.Vector(xmin + inset, ymin + inset, zmin + inset),
    )


def shape_bounds(shape: Part.Shape) -> list[float]:
    bbox = shape.BoundBox
    return [bbox.XMin, bbox.YMin, bbox.ZMin, bbox.XMax, bbox.YMax, bbox.ZMax]


def component_index(
    export: dict[str, object],
    requirements: dict[str, object],
    map_rows: list[dict[str, str]],
) -> dict[str, dict[str, object]]:
    rows_by_ref = {row["ref"]: row for row in map_rows}
    body_specs = requirements["component_bodies"]
    result: dict[str, dict[str, object]] = {}
    for raw_item in export["components"]:
        item = dict(raw_item)
        ref = str(item["ref"])
        row = rows_by_ref.get(ref, {})
        body = item.get("body_bbox_mm") or body_specs.get(ref, {}).get("bbox_mm")
        if body is None:
            body = [
                float(row.get("body_x_mm") or 0.0),
                float(row.get("body_y_mm") or 0.0),
                float(item.get("height_mm") or row.get("height_mm") or 0.0),
            ]
        item["body_bbox_mm"] = [float(value) for value in body]
        if len(item["body_bbox_mm"]) != 3 or min(item["body_bbox_mm"]) <= 0.0:
            raise ValueError(f"component {ref} lacks a positive XYZ body envelope")
        result[ref] = item
    return result


def component_box(item: dict[str, object], board_top: float) -> Part.Shape:
    sx, sy, sz = (float(value) for value in item["body_bbox_mm"])
    return Part.makeBox(
        sx,
        sy,
        sz,
        App.Vector(float(item["x_mm"]) - sx / 2.0, float(item["y_mm"]) - sy / 2.0, board_top),
    )


def projected_keepout_column(
    item: dict[str, object],
    z_min: float,
    z_max: float,
) -> Part.Shape:
    return Part.makeCylinder(
        float(item["keepout_radius_mm"]),
        z_max - z_min,
        App.Vector(float(item["x_mm"]), float(item["y_mm"]), z_min),
    )


def side_window_specs(
    params: dict[str, object],
    requirements: dict[str, object],
    components: dict[str, dict[str, object]],
    access_rows: list[dict[str, str]],
    board_top: float,
) -> list[dict[str, object]]:
    parameter_windows: dict[str, dict[str, object]] = {}
    for key in ("side_windows", "accesses"):
        for raw_item in params.get(key, []):
            item = dict(raw_item)
            if item.get("access_type", "side_window") == "side_window" and item.get("ref"):
                parameter_windows[str(item["ref"])] = item

    enclosure_x = float(requirements["expected_enclosure_bbox_mm"][0])
    overcut = float(requirements["access_overcut_mm"])
    result: list[dict[str, object]] = []
    for row in access_rows:
        if row["access_type"] != "side_window":
            raise ValueError(f"task-04 only supports side windows, got {row['access_type']} for {row['ref']}")
        ref = row["ref"]
        item = components[ref]
        cx, cy = float(item["x_mm"]), float(item["y_mm"])
        body_x, _, body_z = (float(value) for value in item["body_bbox_mm"])
        width = float(row["finished_width_mm"])
        height = float(row["finished_height_mm"])
        direction = row["direction"]
        center_z = board_top + body_z / 2.0
        y_min, y_max = cy - width / 2.0, cy + width / 2.0
        z_min, z_max = center_z - height / 2.0, center_z + height / 2.0

        parameter_item = parameter_windows.get(ref, {})
        if parameter_item.get("bounds_mm"):
            bounds = [float(value) for value in parameter_item["bounds_mm"]]
        elif direction == "X_PLUS":
            bounds = [cx - body_x / 2.0, y_min, z_min, enclosure_x / 2.0 + overcut, y_max, z_max]
        elif direction == "X_MINUS":
            bounds = [-enclosure_x / 2.0 - overcut, y_min, z_min, cx + body_x / 2.0, y_max, z_max]
        else:
            raise ValueError(f"unsupported side-window direction for {ref}: {direction}")

        if len(bounds) != 6 or bounds[3] <= bounds[0] or bounds[4] <= bounds[1] or bounds[5] <= bounds[2]:
            raise ValueError(f"invalid side-window bounds for {ref}")
        result.append(
            {
                "access_type": "side_window",
                "bounds_mm": bounds,
                "center_y_mm": cy,
                "center_z_mm": center_z,
                "direction": direction,
                "finished_height_mm": height,
                "finished_width_mm": width,
                "ref": ref,
            }
        )
    return result


def side_guard_material(
    material: Part.Shape,
    window: dict[str, object],
    enclosure_bbox: list[float],
    wall: float,
    guard: float,
) -> tuple[bool, dict[str, float]]:
    _, y_min, z_min, _, y_max, z_max = (float(value) for value in window["bounds_mm"])
    direction = str(window["direction"])
    outer_x = enclosure_bbox[0] / 2.0
    x0 = outer_x - wall if direction == "X_PLUS" else -outer_x
    inset = min(0.05, guard / 10.0)
    y_span = max(0.05, y_max - y_min - 2.0 * inset)
    z_span = max(0.05, z_max - z_min - 2.0 * inset)
    probes = {
        "y_minus": Part.makeBox(wall, max(0.05, guard - inset), z_span, App.Vector(x0, y_min - guard, z_min + inset)),
        "y_plus": Part.makeBox(wall, max(0.05, guard - inset), z_span, App.Vector(x0, y_max + inset, z_min + inset)),
        "z_minus": Part.makeBox(wall, y_span, max(0.05, guard - inset), App.Vector(x0, y_min + inset, z_min - guard)),
        "z_plus": Part.makeBox(wall, y_span, max(0.05, guard - inset), App.Vector(x0, y_min + inset, z_max + inset)),
    }
    fractions = {
        name: float(material.common(probe).Volume) / max(float(probe.Volume), 1e-9)
        for name, probe in probes.items()
    }
    return all(value >= 0.75 for value in fractions.values()), {
        name: round(value, 6) for name, value in fractions.items()
    }


def measured_wall_window(
    material: Part.Shape,
    window: dict[str, object],
    enclosure_bbox: list[float],
    wall: float,
    tray_top: float,
    volume_tolerance: float,
) -> dict[str, float] | None:
    enclosure_x, enclosure_y, _ = enclosure_bbox
    x0 = enclosure_x / 2.0 - wall if window["direction"] == "X_PLUS" else -enclosure_x / 2.0
    # Stay away from coincident STL/Part faces. Tiny tessellation slivers at the
    # exact wall boundaries can otherwise connect every exterior void and make
    # its bounding box look like the complete wall.
    inset = min(0.2, wall / 4.0)
    nominal_wall = Part.makeBox(
        wall - 2.0 * inset,
        enclosure_y,
        tray_top,
        App.Vector(x0 + inset, -enclosure_y / 2.0, 0.0),
    )
    voids = positive_solids(nominal_wall.cut(material), volume_tolerance)
    center_y = float(window["center_y_mm"])
    center_z = float(window["center_z_mm"])
    candidates = [
        shape
        for shape in voids
        if shape.BoundBox.YMin - 1e-6 <= center_y <= shape.BoundBox.YMax + 1e-6
        and shape.BoundBox.ZMin - 1e-6 <= center_z <= shape.BoundBox.ZMax + 1e-6
    ]
    if not candidates:
        return None
    aperture = max(candidates, key=lambda shape: float(shape.Volume))
    bbox = aperture.BoundBox
    return {
        "center_y_mm": float(bbox.Center.y),
        "center_z_mm": float(bbox.Center.z),
        "height_mm": float(bbox.ZLength),
        "width_mm": float(bbox.YLength),
    }


def build_access_checks(
    material: Part.Shape,
    windows: list[dict[str, object]],
    requirements: dict[str, object],
) -> tuple[dict[str, dict[str, object]], dict[str, Part.Shape]]:
    enclosure_bbox = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    wall = float(requirements["wall_mm"])
    tray_top = float(requirements["tray_outer_top_z_mm"])
    guard = float(requirements["minimum_access_guard_mm"])
    center_tolerance = float(requirements["access_center_tolerance_mm"])
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    checks: dict[str, dict[str, object]] = {}
    overlays: dict[str, Part.Shape] = {}

    for window in windows:
        ref = str(window["ref"])
        bounds = [float(value) for value in window["bounds_mm"]]
        probe = box_from_bounds(bounds, inset=min(0.05, geometry_tolerance / 2.0))
        residual = float(material.common(probe).Volume)
        guards_present, guard_fractions = side_guard_material(
            material, window, enclosure_bbox, wall, guard
        )
        measured = measured_wall_window(
            material, window, enclosure_bbox, wall, tray_top, volume_tolerance
        )
        if measured is None:
            center_error = None
            width_error = None
            height_error = None
            measured_ok = False
        else:
            center_error = math.hypot(
                measured["center_y_mm"] - float(window["center_y_mm"]),
                measured["center_z_mm"] - float(window["center_z_mm"]),
            )
            width_error = abs(measured["width_mm"] - float(window["finished_width_mm"]))
            height_error = abs(measured["height_mm"] - float(window["finished_height_mm"]))
            measured_ok = (
                center_error <= center_tolerance + geometry_tolerance
                and width_error <= geometry_tolerance
                and height_error <= geometry_tolerance
            )

        _, y_min, z_min, _, y_max, z_max = bounds
        analytic_guards = {
            "y_minus_mm": y_min + enclosure_bbox[1] / 2.0,
            "y_plus_mm": enclosure_bbox[1] / 2.0 - y_max,
            "z_minus_mm": z_min,
            "z_plus_to_tray_top_mm": tray_top - z_max,
        }
        minimum_guard = min(analytic_guards.values())
        through = residual <= volume_tolerance and measured_ok and guards_present
        checks[ref] = {
            "access_type": "side_window",
            "bounds_mm": [round(value, 6) for value in bounds],
            "center_error_mm": None if center_error is None else round(center_error, 6),
            "direction": window["direction"],
            "finished_height_mm": float(window["finished_height_mm"]),
            "finished_width_mm": float(window["finished_width_mm"]),
            "guard_distances_mm": {name: round(value, 6) for name, value in analytic_guards.items()},
            "guard_material_fractions": guard_fractions,
            "height_error_mm": None if height_error is None else round(height_error, 6),
            "measured_wall_opening": None
            if measured is None
            else {name: round(value, 6) for name, value in measured.items()},
            "minimum_guard_material_present": guards_present and minimum_guard + geometry_tolerance >= guard,
            "minimum_guard_mm": round(minimum_guard, 6),
            "residual_material_volume_mm3": round(residual, 6),
            "through": through and minimum_guard + geometry_tolerance >= guard,
            "width_error_mm": None if width_error is None else round(width_error, 6),
        }
        overlays[ref] = box_from_bounds(bounds)
    return checks, overlays


def side_clearance(
    tray: Part.Shape,
    board: Part.Shape,
    direction: str,
    enclosure_bbox: list[float],
) -> float | None:
    epsilon = 0.02
    z_height = max(0.05, min(0.2, board.BoundBox.ZLength / 2.0))
    z0 = board.BoundBox.Center.z - z_height / 2.0
    x_outer = enclosure_bbox[0] / 2.0 + 1.0
    y_outer = enclosure_bbox[1] / 2.0 + 1.0

    if direction == "X_PLUS":
        reference = Part.makeBox(epsilon, board.BoundBox.YLength, z_height, App.Vector(board.BoundBox.XMax - epsilon, board.BoundBox.YMin, z0))
        search = Part.makeBox(x_outer - board.BoundBox.XMax, board.BoundBox.YLength, z_height, App.Vector(board.BoundBox.XMax, board.BoundBox.YMin, z0))
    elif direction == "X_MINUS":
        reference = Part.makeBox(epsilon, board.BoundBox.YLength, z_height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMin, z0))
        search = Part.makeBox(board.BoundBox.XMin + x_outer, board.BoundBox.YLength, z_height, App.Vector(-x_outer, board.BoundBox.YMin, z0))
    elif direction == "Y_PLUS":
        reference = Part.makeBox(board.BoundBox.XLength, epsilon, z_height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMax - epsilon, z0))
        search = Part.makeBox(board.BoundBox.XLength, y_outer - board.BoundBox.YMax, z_height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMax, z0))
    elif direction == "Y_MINUS":
        reference = Part.makeBox(board.BoundBox.XLength, epsilon, z_height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMin, z0))
        search = Part.makeBox(board.BoundBox.XLength, board.BoundBox.YMin + y_outer, z_height, App.Vector(board.BoundBox.XMin, -y_outer, z0))
    else:
        raise ValueError(f"unsupported side direction: {direction}")

    side_material = tray.common(search)
    if side_material.isNull() or float(side_material.Volume) <= 0.0:
        return None
    return max(0.0, float(reference.distToShape(side_material)[0]))


def add_shape(doc: App.Document, name: str, label: str, shape: Part.Shape) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    return obj


def main() -> None:
    work = Path(os.environ.get("ENGIWORLD_WORKDIR") or (sys.argv[1] if len(sys.argv) > 1 else ".")).resolve()
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    export = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    with (work / "01_kicad_mechanical_map.csv").open(newline="", encoding="utf-8") as handle:
        map_rows = list(csv.DictReader(handle))
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        access_rows = list(csv.DictReader(handle))

    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    expected_bbox = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    wall = float(requirements["wall_mm"])
    base = float(requirements["base_thickness_mm"])
    board_bottom = float(params.get("board_bottom_z_mm", requirements["board_bottom_z_mm"]))
    board_thickness = float(export["board_bbox_mm"][2])
    board_top = float(params.get("board_top_z_mm", board_bottom + board_thickness))
    tray_top = float(requirements["tray_outer_top_z_mm"])
    lid_inner_z = float(requirements["lid_inner_z_mm"])
    lid_thickness = float(requirements["lid_thickness_mm"])
    density = float(requirements["enclosure_material_density_g_cm3"])

    mesh, submitted_material = mesh_to_material(work / "02_openscad_enclosure.stl", volume_tolerance)
    components = component_index(export, requirements, map_rows)
    windows = side_window_specs(params, requirements, components, access_rows, board_top)

    full_tray_region = Part.makeBox(
        expected_bbox[0], expected_bbox[1], tray_top, App.Vector(-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, 0.0)
    )
    ideal_lid = Part.makeBox(
        expected_bbox[0], expected_bbox[1], lid_thickness, App.Vector(-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, lid_inner_z)
    )
    tray_shape = submitted_material.common(full_tray_region).removeSplitter()
    lid_shape = submitted_material.common(ideal_lid).removeSplitter()
    if not positive_solids(tray_shape, volume_tolerance):
        raise RuntimeError("submitted OpenSCAD geometry contains no tray material")
    if not positive_solids(lid_shape, volume_tolerance):
        raise RuntimeError("submitted OpenSCAD geometry contains no separate lid material")

    cavity = Part.makeBox(
        expected_bbox[0] - 2.0 * wall,
        expected_bbox[1] - 2.0 * wall,
        tray_top - base,
        App.Vector(-expected_bbox[0] / 2.0 + wall, -expected_bbox[1] / 2.0 + wall, base),
    )
    ideal_tray_shell = full_tray_region.cut(cavity)
    for window in windows:
        ideal_tray_shell = ideal_tray_shell.cut(box_from_bounds(window["bounds_mm"]))

    bore_diameter = float(requirements["standoff_bore_diameter_mm"])
    bore_overcut = float(requirements["standoff_bore_overcut_mm"])
    standoff_od = float(requirements["standoff_outer_diameter_mm"])
    standoff_height = float(requirements["standoff_height_mm"])
    axis_tolerance = float(requirements["axis_tolerance_mm"])
    standoff_checks: dict[str, dict[str, object]] = {}
    for hole in export["mounting_holes"]:
        ref = str(hole["ref"])
        x, y = float(hole["x_mm"]), float(hole["y_mm"])
        outer = Part.makeCylinder(standoff_od / 2.0, standoff_height, App.Vector(x, y, base))
        local_bore = Part.makeCylinder(bore_diameter / 2.0, standoff_height, App.Vector(x, y, base))
        annulus = outer.cut(local_bore)
        actual_annulus = submitted_material.common(annulus)
        material_fraction = float(actual_annulus.Volume) / max(float(annulus.Volume), 1e-9)
        probe_radius = max(0.05, bore_diameter / 2.0 - geometry_tolerance)
        probe = Part.makeCylinder(
            probe_radius,
            board_bottom + 2.0 * bore_overcut,
            App.Vector(x, y, -bore_overcut),
        )
        residual = float(submitted_material.common(probe).Volume)
        # Measure an actual cross-section above the ribs and below the PCB.
        # Shrinking the bore search inside the nominal OD avoids exterior voids
        # becoming connected through coincident mesh boundaries.
        section_height = 0.2
        section_z = board_bottom - 0.6
        outer_search = Part.makeCylinder(
            standoff_od / 2.0 + 0.5,
            section_height,
            App.Vector(x, y, section_z),
        )
        actual_section = submitted_material.common(outer_search).removeSplitter()
        section_bbox = actual_section.BoundBox
        measured_outer_diameter = (float(section_bbox.XLength) + float(section_bbox.YLength)) / 2.0
        measured_outer_center = (float(section_bbox.Center.x), float(section_bbox.Center.y))
        restricted = Part.makeCylinder(
            max(bore_diameter / 2.0 + 0.25, standoff_od / 2.0 - 0.2),
            section_height,
            App.Vector(x, y, section_z),
        )
        bore_voids = positive_solids(restricted.cut(submitted_material), min(volume_tolerance, 0.01))
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
            bore_bbox = bore_void.BoundBox
            measured_bore_diameter = (float(bore_bbox.XLength) + float(bore_bbox.YLength)) / 2.0
            measured_bore_center = (float(bore_bbox.Center.x), float(bore_bbox.Center.y))
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
            and abs(measured_bore_diameter - bore_diameter) <= geometry_tolerance
            and abs(measured_outer_diameter - standoff_od) <= geometry_tolerance
            and axis_error is not None
            and axis_error <= axis_tolerance
            and concentric_error is not None
            and concentric_error <= axis_tolerance
        )
        standoff_checks[ref] = {
            "axis_error_mm": None if axis_error is None else round(axis_error, 6),
            "bore_center_xy_mm": None
            if measured_bore_center is None
            else [round(value, 6) for value in measured_bore_center],
            "bore_diameter_mm": None
            if measured_bore_diameter is None
            else round(measured_bore_diameter, 6),
            "bore_z_max_mm": board_bottom + bore_overcut,
            "bore_z_min_mm": -bore_overcut,
            "concentric_error_mm": None if concentric_error is None else round(concentric_error, 6),
            "continuous_bore": residual <= volume_tolerance and dimensions_pass,
            "outer_center_xy_mm": [round(value, 6) for value in measured_outer_center],
            "outer_diameter_mm": round(measured_outer_diameter, 6),
            "present_material_fraction": round(material_fraction, 6),
            "residual_bore_material_volume_mm3": round(residual, 6),
            "standoff_present": material_fraction >= 0.95 and dimensions_pass,
            "x_mm": x,
            "y_mm": y,
        }
        ideal_tray_shell = ideal_tray_shell.cut(probe)

    tray_shell_present_fraction = float(submitted_material.common(ideal_tray_shell).Volume) / max(
        float(ideal_tray_shell.Volume), 1e-9
    )
    lid_present_fraction = float(lid_shape.Volume) / max(float(ideal_lid.Volume), 1e-9)
    lid_separation = float(tray_shape.distToShape(lid_shape)[0])

    required_ribs = requirements["required_ribs"]
    rib_shapes: dict[str, Part.Shape] = {}
    rib_checks: dict[str, dict[str, object]] = {}
    for rib_spec in required_ribs:
        rib_id = str(rib_spec["id"])
        ideal_rib = box_from_bounds(rib_spec["bounds_mm"])
        actual_rib = submitted_material.common(ideal_rib).removeSplitter()
        present_fraction = float(actual_rib.Volume) / max(float(ideal_rib.Volume), 1e-9)
        rib_shapes[rib_id] = actual_rib
        rib_checks[rib_id] = {
            "bounds_mm": [float(value) for value in rib_spec["bounds_mm"]],
            "expected_volume_mm3": round(float(ideal_rib.Volume), 6),
            "measured_volume_mm3": round(float(actual_rib.Volume), 6),
            "present": present_fraction >= 0.98,
            "present_material_fraction": round(present_fraction, 6),
            "q_keepout_checks": {},
        }

    q_refs = [str(ref) for ref in requirements["rib_exclusion"]["keepout_refs"]]
    keepout_columns = {
        ref: projected_keepout_column(components[ref], base, lid_inner_z) for ref in q_refs
    }
    minimum_rib_clearance = float(requirements["minimum_rib_keepout_clearance_mm"])
    q_structural_checks: dict[str, dict[str, object]] = {}
    for ref, column in keepout_columns.items():
        structural_intersection = float(submitted_material.common(column).Volume)
        q_structural_checks[ref] = {
            "all_tray_structural_intersection_mm3": round(structural_intersection, 6),
            "clear": structural_intersection <= volume_tolerance,
            "radius_mm": float(components[ref]["keepout_radius_mm"]),
            "x_mm": float(components[ref]["x_mm"]),
            "y_mm": float(components[ref]["y_mm"]),
            "z_max_mm": lid_inner_z,
            "z_min_mm": base,
        }
        for rib_id, rib_shape in rib_shapes.items():
            intersection = float(rib_shape.common(column).Volume)
            separation = None if not positive_solids(rib_shape, volume_tolerance) else float(rib_shape.distToShape(column)[0])
            rib_checks[rib_id]["q_keepout_checks"][ref] = {
                "intersection_mm3": round(intersection, 6),
                "minimum_required_separation_mm": minimum_rib_clearance,
                "passes": intersection <= volume_tolerance
                and separation is not None
                and separation + geometry_tolerance >= minimum_rib_clearance,
                "separation_mm": None if separation is None else round(separation, 6),
            }

    board_shape = Part.read(str(work / "01_kicad_board.step"))
    if not positive_solids(board_shape, volume_tolerance):
        raise RuntimeError("KiCad STEP contains no board solid")
    board_shape.translate(
        App.Vector(
            -board_shape.BoundBox.Center.x,
            -board_shape.BoundBox.Center.y,
            board_bottom - board_shape.BoundBox.ZMin,
        )
    )
    component_shapes = {ref: component_box(item, board_top) for ref, item in components.items()}

    side_clearances = {
        direction: side_clearance(tray_shape, board_shape, direction, expected_bbox)
        for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")
    }
    finite_side_clearances = [
        value for value in side_clearances.values() if value is not None and math.isfinite(value)
    ]
    minimum_side_clearance = min(finite_side_clearances) if len(finite_side_clearances) == 4 else None

    component_top_clearances = {
        ref: float(lid_shape.BoundBox.ZMin - shape.BoundBox.ZMax)
        for ref, shape in component_shapes.items()
    }
    minimum_top_clearance = min(component_top_clearances.values())
    access_checks, access_overlays = build_access_checks(submitted_material, windows, requirements)

    physical_targets = {"PCB": board_shape, **component_shapes}
    interference_by_object = {
        name: round(float(submitted_material.common(shape).Volume), 6)
        for name, shape in physical_targets.items()
    }
    total_interference = round(sum(interference_by_object.values()), 6)

    actual_bbox = [
        float(submitted_material.BoundBox.XLength),
        float(submitted_material.BoundBox.YLength),
        float(submitted_material.BoundBox.ZLength),
    ]
    measured_board_bbox = [
        float(board_shape.BoundBox.XLength),
        float(board_shape.BoundBox.YLength),
        float(board_shape.BoundBox.ZLength),
    ]
    board_bbox_ok = all(
        abs(actual - float(expected)) <= geometry_tolerance
        for actual, expected in zip(measured_board_bbox, export["board_bbox_mm"])
    )
    board_placement_ok = (
        abs(board_shape.BoundBox.Center.x) <= float(requirements["axis_tolerance_mm"])
        and abs(board_shape.BoundBox.Center.y) <= float(requirements["axis_tolerance_mm"])
        and abs(board_shape.BoundBox.ZMin - board_bottom) <= geometry_tolerance
    )

    non_null_ribs = [shape for shape in rib_shapes.values() if positive_solids(shape, volume_tolerance)]
    ribs_union = Part.makeCompound(non_null_ribs) if non_null_ribs else Part.Shape()
    tray_core = tray_shape.cut(ribs_union).removeSplitter() if non_null_ribs else tray_shape

    doc = App.newDocument("Task04ReleaseAssembly")
    tray_obj = add_shape(doc, "OpenSCAD_Tray_Enclosure", "ASA enclosure tray", tray_core)
    lid_obj = add_shape(doc, "OpenSCAD_Lid", "Separate ASA enclosure lid", lid_shape)
    rib_objects = [
        add_shape(doc, f"Rib_{rib_id}", f"Structural tray rib {rib_id}", shape)
        for rib_id, shape in rib_shapes.items()
        if positive_solids(shape, volume_tolerance)
    ]
    board_obj = add_shape(doc, "KiCad_PCB", "KiCad PCB board", board_shape)
    component_objects = [
        add_shape(doc, f"Component_{ref}", f"Physical component proxy {ref}", shape)
        for ref, shape in component_shapes.items()
    ]
    keepout_objects = [
        add_shape(doc, f"Projected_Keepout_{ref}", f"Projected MOSFET keepout column {ref}", shape)
        for ref, shape in keepout_columns.items()
    ]
    assembly_region = Part.makeBox(
        expected_bbox[0],
        expected_bbox[1],
        expected_bbox[2],
        App.Vector(-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, 0.0),
    )
    access_objects = [
        add_shape(
            doc,
            f"Access_{ref}",
            f"Validation overlay for {ref} side access",
            shape.common(assembly_region).removeSplitter(),
        )
        for ref, shape in access_overlays.items()
    ]
    doc.recompute()

    physical_objects = [tray_obj, lid_obj] + rib_objects + [board_obj] + component_objects
    Part.export(physical_objects, str(work / "03_freecad_assembly.step"))
    mesh_objects = []
    for source in physical_objects + keepout_objects + access_objects:
        mesh_obj = doc.addObject("Mesh::Feature", source.Name + "_BlenderMesh")
        # Natural-language labels containing Q1/J1 are renumbered by FreeCAD's
        # OBJ exporter (for example Q1 -> Q004). Use the stable internal name so
        # downstream tools retain a delimiter-bounded engineering reference.
        mesh_obj.Label = source.Name + "_mesh"
        mesh_obj.Mesh = MeshPart.meshFromShape(
            Shape=source.Shape,
            LinearDeflection=0.1,
            AngularDeflection=0.35,
            Relative=False,
        )
        mesh_objects.append(mesh_obj)
    doc.recompute()
    Mesh.export(mesh_objects, str(work / "03_freecad_assembly.obj"))

    all_ribs_present = len(rib_checks) == 2 and all(bool(item["present"]) for item in rib_checks.values())
    all_rib_exclusions = all(
        bool(check["passes"])
        for item in rib_checks.values()
        for check in item["q_keepout_checks"].values()
    ) and all(bool(item["clear"]) for item in q_structural_checks.values())
    expected_directions = {"J1": "X_PLUS", "J2": "X_MINUS"}
    accesses_ok = set(access_checks) == set(expected_directions) and all(
        item["through"] and item["direction"] == expected_directions[ref]
        for ref, item in access_checks.items()
    )
    enclosure_bbox_ok = all(
        abs(actual - expected) <= geometry_tolerance for actual, expected in zip(actual_bbox, expected_bbox)
    )
    lid_separation_expected = float(requirements["lid_separation_mm"])
    checks = {
        "accesses": accesses_ok,
        "assembly_has_real_solids": bool(positive_solids(tray_shape, volume_tolerance))
        and bool(positive_solids(lid_shape, volume_tolerance))
        and bool(positive_solids(board_shape, volume_tolerance)),
        "board_bbox": board_bbox_ok,
        "board_placement": board_placement_ok,
        "enclosure_bbox": enclosure_bbox_ok,
        "interference": total_interference <= volume_tolerance,
        "lid_present": lid_present_fraction >= 0.98,
        "lid_separation": abs(lid_separation - lid_separation_expected) <= geometry_tolerance,
        "ribs_present": all_ribs_present,
        "ribs_respect_projected_keepouts": all_rib_exclusions,
        "side_clearance": minimum_side_clearance is not None
        and minimum_side_clearance + geometry_tolerance >= float(requirements["minimum_side_clearance_mm"]),
        "standoff_bores": len(standoff_checks) == 4
        and all(item["continuous_bore"] and item["standoff_present"] for item in standoff_checks.values()),
        "top_clearance": minimum_top_clearance + geometry_tolerance >= float(requirements["minimum_top_clearance_mm"]),
        "tray_present": tray_shell_present_fraction >= 0.98,
    }

    enclosure_volume = float(submitted_material.Volume)
    tray_volume = float(tray_shape.Volume)
    lid_volume = float(lid_shape.Volume)
    report = {
        "access_checks": access_checks,
        "assembly_mesh": "03_freecad_assembly.obj",
        "assembly_step": "03_freecad_assembly.step",
        "board_bbox_mm": [round(float(value), 6) for value in export["board_bbox_mm"]],
        "board_bottom_z_mm": round(board_shape.BoundBox.ZMin, 6),
        "board_top_z_mm": round(board_shape.BoundBox.ZMax, 6),
        "checks": checks,
        "component_top_clearances_mm": {
            ref: round(value, 6) for ref, value in component_top_clearances.items()
        },
        "critical_requirement": requirements["critical_requirement"],
        "decision": "pass" if all(checks.values()) else "fail",
        "density_g_cm3": density,
        "detected_rib_count": sum(bool(item["present"]) for item in rib_checks.values()),
        "enclosure_bbox_mm": [round(value, 6) for value in actual_bbox],
        "enclosure_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "enclosure_material": requirements["enclosure_material"],
        "enclosure_solid_count": len(positive_solids(submitted_material, volume_tolerance)),
        "enclosure_volume_mm3": round(enclosure_volume, 6),
        "estimated_shell_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "inputs": [
            "01_kicad_board.kicad_pcb",
            "01_kicad_board.step",
            "01_kicad_export.json",
            "01_kicad_mechanical_map.csv",
            "02_openscad_enclosure.stl",
            "02_openscad_parameters.json",
        ],
        "interference_by_object_mm3": interference_by_object,
        "interference_volume_mm3": total_interference,
        "keepout_count": len(components),
        "lid_bounds_mm": [round(value, 6) for value in shape_bounds(lid_shape)],
        "lid_mass_g": round(lid_volume * density / 1000.0, 6),
        "lid_present_material_fraction": round(lid_present_fraction, 6),
        "lid_separation_mm": round(lid_separation, 6),
        "lid_solid_count": len(positive_solids(lid_shape, volume_tolerance)),
        "lid_volume_mm3": round(lid_volume, 6),
        "measured_board_step_bbox_mm": [round(value, 6) for value in measured_board_bbox],
        "minimum_side_clearance_mm": None if minimum_side_clearance is None else round(minimum_side_clearance, 6),
        "minimum_top_clearance_mm": round(minimum_top_clearance, 6),
        "object_roles": {
            "OpenSCAD_Tray_Enclosure": "tray",
            "OpenSCAD_Lid": "lid",
            "KiCad_PCB": "pcb",
            **{f"Rib_{rib_id}": "rib" for rib_id in rib_shapes},
            **{f"Component_{ref}": "component" for ref in component_shapes},
            **{f"Projected_Keepout_{ref}": "projected_keepout" for ref in keepout_columns},
            **{f"Access_{ref}": "access_overlay" for ref in access_overlays},
        },
        "package_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "package_volume_mm3": round(enclosure_volume, 6),
        "pcb_solid_count": len(positive_solids(board_shape, volume_tolerance)),
        "projected_keepout_checks": q_structural_checks,
        "required_rib_count": len(required_ribs),
        "rib_checks": rib_checks,
        "side_clearances_mm": {
            direction: None if value is None else round(value, 6)
            for direction, value in side_clearances.items()
        },
        "software_stage": "FreeCAD",
        "standoff_checks": standoff_checks,
        "stl_facet_count": int(mesh.CountFacets),
        "task": "task-04",
        "tray_bounds_mm": [round(value, 6) for value in shape_bounds(tray_shape)],
        "tray_mass_g": round(tray_volume * density / 1000.0, 6),
        "tray_present_material_fraction": round(tray_shell_present_fraction, 6),
        "tray_solid_count": len(positive_solids(tray_shape, volume_tolerance)),
        "tray_volume_mm3": round(tray_volume, 6),
        "unintended_interference_volume_mm3": total_interference,
    }
    json_dump(work / "03_freecad_clearance_report.json", report)
    if report["decision"] != "pass":
        raise RuntimeError("task-04 FreeCAD checks failed: " + json.dumps(checks, sort_keys=True))


# FreeCADCmd executes scripts with a console-specific module name.
main()
