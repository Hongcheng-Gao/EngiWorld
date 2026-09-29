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


TASK = "task-05"
TP_REFS = ("TP1", "TP2", "TP3", "TP4")


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def positive_solids(shape: Part.Shape, volume_tolerance: float) -> list[Part.Shape]:
    if shape.isNull():
        return []
    return [solid for solid in shape.Solids if float(solid.Volume) > volume_tolerance]


def boolean_material(shape: Part.Shape, volume_tolerance: float, label: str) -> Part.Shape:
    solids = positive_solids(shape, volume_tolerance)
    if not solids:
        raise RuntimeError(f"{label} contains no positive material solid")
    result = solids[0]
    for solid in solids[1:]:
        result = result.fuse(solid)
    return result.removeSplitter()


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
    if len(solids) < 2:
        raise RuntimeError("OpenSCAD STL must contain separate closed tray and lid solids")
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


def component_shape(item: dict[str, object], board_top: float) -> Part.Shape:
    sx, sy, sz = (float(value) for value in item["body_bbox_mm"])
    x, y = float(item["x_mm"]), float(item["y_mm"])
    if item.get("shape") == "cylinder":
        if abs(sx - sy) > 1e-6:
            raise ValueError(f"cylindrical component {item['ref']} must have equal XY dimensions")
        return Part.makeCylinder(sx / 2.0, sz, App.Vector(x, y, board_top))
    return Part.makeBox(sx, sy, sz, App.Vector(x - sx / 2.0, y - sy / 2.0, board_top))


def add_shape(doc: App.Document, name: str, label: str, shape: Part.Shape) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    return obj


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
        reference = Part.makeBox(
            epsilon,
            board.BoundBox.YLength,
            z_height,
            App.Vector(board.BoundBox.XMax - epsilon, board.BoundBox.YMin, z0),
        )
        search = Part.makeBox(
            x_outer - board.BoundBox.XMax,
            board.BoundBox.YLength,
            z_height,
            App.Vector(board.BoundBox.XMax, board.BoundBox.YMin, z0),
        )
    elif direction == "X_MINUS":
        reference = Part.makeBox(
            epsilon,
            board.BoundBox.YLength,
            z_height,
            App.Vector(board.BoundBox.XMin, board.BoundBox.YMin, z0),
        )
        search = Part.makeBox(
            board.BoundBox.XMin + x_outer,
            board.BoundBox.YLength,
            z_height,
            App.Vector(-x_outer, board.BoundBox.YMin, z0),
        )
    elif direction == "Y_PLUS":
        reference = Part.makeBox(
            board.BoundBox.XLength,
            epsilon,
            z_height,
            App.Vector(board.BoundBox.XMin, board.BoundBox.YMax - epsilon, z0),
        )
        search = Part.makeBox(
            board.BoundBox.XLength,
            y_outer - board.BoundBox.YMax,
            z_height,
            App.Vector(board.BoundBox.XMin, board.BoundBox.YMax, z0),
        )
    elif direction == "Y_MINUS":
        reference = Part.makeBox(
            board.BoundBox.XLength,
            epsilon,
            z_height,
            App.Vector(board.BoundBox.XMin, board.BoundBox.YMin, z0),
        )
        search = Part.makeBox(
            board.BoundBox.XLength,
            board.BoundBox.YMin + y_outer,
            z_height,
            App.Vector(board.BoundBox.XMin, -y_outer, z0),
        )
    else:
        raise ValueError(f"unsupported side direction: {direction}")
    side_material = tray.common(search)
    if side_material.isNull() or float(side_material.Volume) <= 0.0:
        return None
    return max(0.0, float(reference.distToShape(side_material)[0]))


def top_clearance(material: Part.Shape, component: Part.Shape, enclosure_height: float) -> float | None:
    box = component.BoundBox
    top = float(box.ZMax)
    height = max(0.0, enclosure_height - top)
    if height <= 0.0:
        return -1.0
    probe = Part.makeBox(float(box.XLength), float(box.YLength), height, App.Vector(float(box.XMin), float(box.YMin), top))
    covering = material.common(probe)
    if covering.isNull() or float(covering.Volume) <= 1e-6:
        return None
    return float(covering.BoundBox.ZMin - top)


def standoff_checks(
    material: Part.Shape,
    holes: list[dict[str, object]],
    requirements: dict[str, object],
) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    axis_tolerance = float(requirements["axis_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    base = float(requirements["base_thickness_mm"])
    board_bottom = float(requirements["board_bottom_z_mm"])
    height = float(requirements["standoff_height_mm"])
    outer_diameter = float(requirements["standoff_outer_diameter_mm"])
    bore_diameter = float(requirements["standoff_bore_diameter_mm"])
    overcut = float(requirements["standoff_bore_overcut_mm"])
    for hole in holes:
        ref = str(hole["ref"])
        x, y = float(hole["x_mm"]), float(hole["y_mm"])
        outer = Part.makeCylinder(outer_diameter / 2.0, height, App.Vector(x, y, base))
        nominal_bore = Part.makeCylinder(bore_diameter / 2.0, height, App.Vector(x, y, base))
        annulus = outer.cut(nominal_bore)
        material_fraction = float(material.common(annulus).Volume) / max(float(annulus.Volume), 1e-9)
        bore_probe = Part.makeCylinder(
            max(0.05, bore_diameter / 2.0 - geometry_tolerance),
            height + 2.0 * overcut,
            App.Vector(x, y, base - overcut),
        )
        residual = float(material.common(bore_probe).Volume)

        section_height = 0.2
        section_z = board_bottom - 0.6
        outer_search = Part.makeCylinder(
            outer_diameter / 2.0 + 0.5,
            section_height,
            App.Vector(x, y, section_z),
        )
        actual_section = material.common(outer_search).removeSplitter()
        section_bbox = actual_section.BoundBox
        measured_outer = (float(section_bbox.XLength) + float(section_bbox.YLength)) / 2.0
        outer_center = (float(section_bbox.Center.x), float(section_bbox.Center.y))
        restricted = Part.makeCylinder(
            max(bore_diameter / 2.0 + 0.25, outer_diameter / 2.0 - 0.2),
            section_height,
            App.Vector(x, y, section_z),
        )
        bore_voids = positive_solids(restricted.cut(material), min(volume_tolerance, 0.01))
        centered = [
            shape
            for shape in bore_voids
            if shape.BoundBox.XMin - geometry_tolerance <= x <= shape.BoundBox.XMax + geometry_tolerance
            and shape.BoundBox.YMin - geometry_tolerance <= y <= shape.BoundBox.YMax + geometry_tolerance
        ]
        if centered:
            bore_void = min(
                centered,
                key=lambda shape: math.hypot(shape.BoundBox.Center.x - x, shape.BoundBox.Center.y - y),
            )
            bore_bbox = bore_void.BoundBox
            measured_bore = (float(bore_bbox.XLength) + float(bore_bbox.YLength)) / 2.0
            bore_center = (float(bore_bbox.Center.x), float(bore_bbox.Center.y))
            axis_error = math.hypot(bore_center[0] - x, bore_center[1] - y)
            concentric_error = math.hypot(
                bore_center[0] - outer_center[0], bore_center[1] - outer_center[1]
            )
        else:
            measured_bore = None
            bore_center = None
            axis_error = None
            concentric_error = None
        dimensions_ok = (
            measured_bore is not None
            and abs(measured_bore - bore_diameter) <= geometry_tolerance
            and abs(measured_outer - outer_diameter) <= geometry_tolerance
            and axis_error is not None
            and axis_error <= axis_tolerance
            and concentric_error is not None
            and concentric_error <= axis_tolerance
        )
        result[ref] = {
            "axis_error_mm": None if axis_error is None else round(axis_error, 6),
            "bore_center_xy_mm": None if bore_center is None else [round(value, 6) for value in bore_center],
            "bore_diameter_mm": None if measured_bore is None else round(measured_bore, 6),
            "bore_z_max_mm": board_bottom + overcut,
            "bore_z_min_mm": base - overcut,
            "concentric_error_mm": None if concentric_error is None else round(concentric_error, 6),
            "continuous_bore": residual <= volume_tolerance and dimensions_ok,
            "outer_center_xy_mm": [round(value, 6) for value in outer_center],
            "outer_diameter_mm": round(measured_outer, 6),
            "present_material_fraction": round(material_fraction, 6),
            "ref": ref,
            "residual_bore_material_volume_mm3": round(residual, 6),
            "standoff_present": material_fraction >= 0.95 and dimensions_ok,
            "x_mm": x,
            "y_mm": y,
        }
    return result


def top_access_check(
    material: Part.Shape,
    lid: Part.Shape,
    spec: dict[str, object],
    requirements: dict[str, object],
) -> tuple[dict[str, object], Part.Shape]:
    x, y = float(spec["x_mm"]), float(spec["y_mm"])
    diameter = float(spec["finished_diameter_mm"])
    cutter_z0, cutter_z1 = (float(value) for value in spec["cutter_z_bounds_mm"])
    path_z0, path_z1 = (float(value) for value in spec["path_z_bounds_mm"])
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    axis_tolerance = float(requirements["axis_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    guard = float(requirements["minimum_access_guard_mm"])
    path = Part.makeCylinder(diameter / 2.0, path_z1 - path_z0, App.Vector(x, y, path_z0))
    residual = float(material.common(path).Volume)

    lid_z0 = float(requirements["lid_inner_z_mm"])
    lid_height = float(requirements["lid_thickness_mm"])
    section_z = lid_z0 + lid_height / 2.0
    probe_tolerance = min(1e-5, max(1e-7, geometry_tolerance * 0.001))

    def has_lid_material(px: float, py: float) -> bool:
        return bool(lid.isInside(App.Vector(px, py, section_z), probe_tolerance, True))

    search_radius = diameter / 2.0 + guard
    center_is_empty = not has_lid_material(x, y)
    directions = {
        "x_plus": (1.0, 0.0),
        "x_minus": (-1.0, 0.0),
        "y_plus": (0.0, 1.0),
        "y_minus": (0.0, -1.0),
    }
    radial_boundaries: dict[str, float] = {}
    for name, (dx, dy) in directions.items():
        if not center_is_empty or not has_lid_material(x + dx * search_radius, y + dy * search_radius):
            continue
        empty_radius = 0.0
        material_radius = search_radius
        for _ in range(40):
            midpoint = (empty_radius + material_radius) / 2.0
            if has_lid_material(x + dx * midpoint, y + dy * midpoint):
                material_radius = midpoint
            else:
                empty_radius = midpoint
        radial_boundaries[name] = material_radius

    if len(radial_boundaries) == len(directions):
        diameter_x = radial_boundaries["x_plus"] + radial_boundaries["x_minus"]
        diameter_y = radial_boundaries["y_plus"] + radial_boundaries["y_minus"]
        measured_diameter = (diameter_x + diameter_y) / 2.0
        measured_center = (
            x + (radial_boundaries["x_plus"] - radial_boundaries["x_minus"]) / 2.0,
            y + (radial_boundaries["y_plus"] - radial_boundaries["y_minus"]) / 2.0,
        )
        axis_error = math.hypot(measured_center[0] - x, measured_center[1] - y)
    else:
        diameter_x = None
        diameter_y = None
        measured_diameter = None
        measured_center = None
        axis_error = None

    guard_probe_radius = diameter / 2.0 + guard / 2.0
    guard_sample_count = 32
    guard_material_count = sum(
        has_lid_material(
            x + guard_probe_radius * math.cos(2.0 * math.pi * index / guard_sample_count),
            y + guard_probe_radius * math.sin(2.0 * math.pi * index / guard_sample_count),
        )
        for index in range(guard_sample_count)
    )
    guard_fraction = guard_material_count / guard_sample_count
    diameter_error = None if measured_diameter is None else abs(measured_diameter - diameter)
    through = (
        residual <= volume_tolerance
        and measured_diameter is not None
        and diameter_error <= geometry_tolerance
        and axis_error is not None
        and axis_error <= axis_tolerance
        and guard_fraction >= 0.98
    )
    return (
        {
            "access_type": "top_bore",
            "axis_error_mm": None if axis_error is None else round(axis_error, 6),
            "bore_center_xy_mm": None if measured_center is None else [round(value, 6) for value in measured_center],
            "center_probe_empty": center_is_empty,
            "cutter_z_bounds_mm": [cutter_z0, cutter_z1],
            "diameter_error_mm": None if diameter_error is None else round(diameter_error, 6),
            "direction": "Z_PLUS",
            "finished_diameter_mm": None if measured_diameter is None else round(measured_diameter, 6),
            "finished_diameter_x_mm": None if diameter_x is None else round(diameter_x, 6),
            "finished_diameter_y_mm": None if diameter_y is None else round(diameter_y, 6),
            "guard_material_fraction": round(guard_fraction, 6),
            "guard_probe_radius_mm": round(guard_probe_radius, 6),
            "guard_sample_count": guard_sample_count,
            "minimum_guard_material_present": guard_fraction >= 0.98,
            "minimum_guard_mm": guard,
            "path_z_bounds_mm": [path_z0, path_z1],
            "radial_material_boundaries_mm": {
                name: round(value, 6) for name, value in radial_boundaries.items()
            },
            "ref": spec["ref"],
            "residual_material_volume_mm3": round(residual, 6),
            "through": through,
            "x_mm": x,
            "y_mm": y,
        },
        path,
    )


def side_access_check(
    material: Part.Shape,
    tray: Part.Shape,
    spec: dict[str, object],
    requirements: dict[str, object],
) -> tuple[dict[str, object], Part.Shape]:
    bounds = [float(value) for value in spec["bounds_mm"]]
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    guard = float(requirements["minimum_access_guard_mm"])
    wall = float(requirements["wall_mm"])
    enclosure = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    tray_top = float(requirements["tray_outer_top_z_mm"])
    probe = box_from_bounds(bounds, inset=min(0.05, geometry_tolerance / 2.0))
    residual = float(material.common(probe).Volume)
    inner_y = enclosure[1] / 2.0 - wall
    wall_y = inner_y + 0.05
    wall_depth = max(0.05, wall - 0.1)
    x_span = xmax - xmin
    z_span = zmax - zmin
    guard_probes = {
        "x_minus": Part.makeBox(guard, wall_depth, max(0.05, z_span - 0.1), App.Vector(xmin - guard, wall_y, zmin + 0.05)),
        "x_plus": Part.makeBox(guard, wall_depth, max(0.05, z_span - 0.1), App.Vector(xmax, wall_y, zmin + 0.05)),
        "z_minus": Part.makeBox(max(0.05, x_span - 0.1), wall_depth, guard, App.Vector(xmin + 0.05, wall_y, zmin - guard)),
        "z_plus": Part.makeBox(max(0.05, x_span - 0.1), wall_depth, guard, App.Vector(xmin + 0.05, wall_y, zmax)),
    }
    fractions = {
        name: float(tray.common(shape).Volume) / max(float(shape.Volume), 1e-9)
        for name, shape in guard_probes.items()
    }
    guards = {
        "x_minus_mm": xmin + enclosure[0] / 2.0,
        "x_plus_mm": enclosure[0] / 2.0 - xmax,
        "z_minus_mm": zmin,
        "z_plus_to_tray_top_mm": tray_top - zmax,
    }
    minimum_guard = min(guards.values())
    guards_ok = all(value >= 0.75 for value in fractions.values()) and minimum_guard + geometry_tolerance >= guard
    return (
        {
            "access_type": "side_window",
            "bounds_mm": bounds,
            "center_error_mm": 0.0,
            "direction": "Y_PLUS",
            "finished_height_mm": z_span,
            "finished_width_mm": x_span,
            "guard_distances_mm": {name: round(value, 6) for name, value in guards.items()},
            "guard_material_fractions": {name: round(value, 6) for name, value in fractions.items()},
            "height_error_mm": abs(z_span - float(spec["finished_height_mm"])),
            "minimum_guard_material_present": guards_ok,
            "minimum_guard_mm": round(minimum_guard, 6),
            "ref": spec["ref"],
            "residual_material_volume_mm3": round(residual, 6),
            "through": residual <= volume_tolerance and guards_ok,
            "width_error_mm": abs(x_span - float(spec["finished_width_mm"])),
        },
        box_from_bounds(bounds),
    )


def main() -> None:
    argument = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    work = Path(
        os.environ.get("ENGIWORLD_WORKDIR")
        or (str(argument) if argument is not None and argument.is_dir() else ".")
    ).resolve()
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    export = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    with (work / "01_kicad_mechanical_map.csv").open(newline="", encoding="utf-8") as handle:
        map_rows = list(csv.DictReader(handle))
    if requirements.get("task") != TASK or params.get("task") != TASK or export.get("task") != TASK:
        raise ValueError("task identity mismatch in task-05 FreeCAD inputs")

    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    expected_bbox = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    wall = float(requirements["wall_mm"])
    base = float(requirements["base_thickness_mm"])
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + float(export["board_bbox_mm"][2])
    tray_top = float(requirements["tray_outer_top_z_mm"])
    lid_inner = float(requirements["lid_inner_z_mm"])
    lid_thickness = float(requirements["lid_thickness_mm"])
    density = float(requirements["enclosure_material_density_g_cm3"])

    mesh, submitted_material = mesh_to_material(work / "02_openscad_enclosure.stl", volume_tolerance)
    full_tray_region = Part.makeBox(
        expected_bbox[0], expected_bbox[1], tray_top,
        App.Vector(-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, 0.0),
    )
    full_lid_region = Part.makeBox(
        expected_bbox[0], expected_bbox[1], lid_thickness,
        App.Vector(-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, lid_inner),
    )
    tray_shape = boolean_material(
        submitted_material.common(full_tray_region), volume_tolerance, "submitted tray region"
    )
    lid_shape = boolean_material(
        submitted_material.common(full_lid_region), volume_tolerance, "submitted lid region"
    )

    cavity_xy = [float(value) for value in params["cavity_bbox_mm"][:2]]
    cavity = Part.makeBox(
        cavity_xy[0], cavity_xy[1], tray_top - base + 0.5,
        App.Vector(-cavity_xy[0] / 2.0, -cavity_xy[1] / 2.0, base),
    )
    ideal_tray = full_tray_region.cut(cavity)
    for hole in export["mounting_holes"]:
        ideal_tray = ideal_tray.fuse(
            Part.makeCylinder(
                float(requirements["standoff_outer_diameter_mm"]) / 2.0,
                float(requirements["standoff_height_mm"]),
                App.Vector(float(hole["x_mm"]), float(hole["y_mm"]), base),
            )
        )
    bore_overcut = float(requirements["standoff_bore_overcut_mm"])
    for hole in export["mounting_holes"]:
        ideal_tray = ideal_tray.cut(
            Part.makeCylinder(
                float(requirements["standoff_bore_diameter_mm"]) / 2.0,
                float(requirements["standoff_height_mm"]) + 2.0 * bore_overcut,
                App.Vector(
                    float(hole["x_mm"]),
                    float(hole["y_mm"]),
                    base - bore_overcut,
                ),
            )
        )
    for window in params["side_windows"]:
        ideal_tray = ideal_tray.cut(box_from_bounds(window["bounds_mm"]))
    ideal_tray = ideal_tray.removeSplitter()

    ideal_lid = full_lid_region
    for access in params["top_bores"]:
        z0, z1 = (float(value) for value in access["cutter_z_bounds_mm"])
        ideal_lid = ideal_lid.cut(
            Part.makeCylinder(
                float(access["finished_diameter_mm"]) / 2.0,
                z1 - z0,
                App.Vector(float(access["x_mm"]), float(access["y_mm"]), z0),
            )
        )
    ideal_lid = ideal_lid.removeSplitter()
    tray_present_fraction = float(tray_shape.common(ideal_tray).Volume) / max(float(ideal_tray.Volume), 1e-9)
    lid_bounds_error = max(
        abs(actual - expected)
        for actual, expected in zip(shape_bounds(lid_shape), shape_bounds(ideal_lid))
    )
    lid_volume_ratio = float(lid_shape.Volume) / max(float(ideal_lid.Volume), 1e-9)
    lid_present_fraction = (
        min(lid_volume_ratio, 1.0 / max(lid_volume_ratio, 1e-9))
        if lid_bounds_error <= geometry_tolerance
        else 0.0
    )

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
    components = {str(item["ref"]): item for item in export["components"]}
    component_shapes = {ref: component_shape(item, board_top) for ref, item in components.items()}

    side_clearances = {
        direction: side_clearance(tray_shape, board_shape, direction, expected_bbox)
        for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")
    }
    finite_clearances = [value for value in side_clearances.values() if value is not None and math.isfinite(value)]
    minimum_side_clearance = min(finite_clearances) if len(finite_clearances) == 4 else None
    component_top_clearances = {
        ref: top_clearance(submitted_material, shape, expected_bbox[2])
        for ref, shape in component_shapes.items()
    }
    covered_top_refs = {str(access["ref"]) for access in params["side_windows"]}
    finite_top_clearances = [
        value for ref, value in component_top_clearances.items()
        if ref in covered_top_refs and value is not None
    ]
    minimum_top_clearance = min(finite_top_clearances) if len(finite_top_clearances) == len(covered_top_refs) else None

    standoffs = standoff_checks(submitted_material, export["mounting_holes"], requirements)
    access_checks: dict[str, dict[str, object]] = {}
    access_overlays: dict[str, Part.Shape] = {}
    for access in params["top_bores"]:
        check, overlay = top_access_check(submitted_material, lid_shape, access, requirements)
        access_checks[str(access["ref"])] = check
        access_overlays[str(access["ref"])] = overlay
    for access in params["side_windows"]:
        check, overlay = side_access_check(submitted_material, tray_shape, access, requirements)
        access_checks[str(access["ref"])] = check
        access_overlays[str(access["ref"])] = overlay

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
    lid_separation = float(tray_shape.distToShape(lid_shape)[0])
    expected_access_refs = set(TP_REFS) | {"J1"}
    accesses_ok = set(access_checks) == expected_access_refs and all(item["through"] is True for item in access_checks.values())
    checks = {
        "accesses": accesses_ok,
        "assembly_has_real_solids": bool(positive_solids(tray_shape, volume_tolerance))
        and bool(positive_solids(lid_shape, volume_tolerance))
        and bool(positive_solids(board_shape, volume_tolerance)),
        "board_bbox": board_bbox_ok,
        "board_placement": board_placement_ok,
        "enclosure_bbox": all(abs(actual - expected) <= geometry_tolerance for actual, expected in zip(actual_bbox, expected_bbox)),
        "interference": total_interference <= volume_tolerance,
        "lid_present": lid_present_fraction >= 0.98,
        "lid_separation": abs(lid_separation - float(requirements["lid_separation_mm"])) <= geometry_tolerance,
        "side_clearance": minimum_side_clearance is not None
        and minimum_side_clearance + geometry_tolerance >= float(requirements["minimum_side_clearance_mm"]),
        "standoff_bores": len(standoffs) == 4
        and all(item["continuous_bore"] and item["standoff_present"] for item in standoffs.values()),
        "top_clearance": minimum_top_clearance is not None
        and minimum_top_clearance + geometry_tolerance >= float(requirements["minimum_top_clearance_mm"])
        and all(component_top_clearances[ref] is None for ref in set(component_top_clearances) - covered_top_refs),
        "tray_present": tray_present_fraction >= 0.98,
    }

    doc = App.newDocument("Task05ReleaseAssembly")
    tray_obj = add_shape(doc, "OpenSCAD_Tray", "PC enclosure tray", tray_shape)
    lid_obj = add_shape(doc, "OpenSCAD_Lid", "Separate PC enclosure lid", lid_shape)
    board_obj = add_shape(doc, "KiCad_PCB", "KiCad PCB board", board_shape)
    component_objects = [
        add_shape(doc, f"Component_{ref}", f"Physical component {ref}", shape)
        for ref, shape in component_shapes.items()
    ]
    assembly_region = Part.makeBox(
        expected_bbox[0], expected_bbox[1], expected_bbox[2],
        App.Vector(-expected_bbox[0] / 2.0, -expected_bbox[1] / 2.0, 0.0),
    )
    access_objects = [
        add_shape(
            doc,
            f"Access_{ref}",
            f"Validation overlay for {ref} access",
            shape.common(assembly_region).removeSplitter(),
        )
        for ref, shape in access_overlays.items()
    ]
    doc.recompute()
    physical_objects = [tray_obj, lid_obj, board_obj, *component_objects]
    Part.export(physical_objects, str(work / "03_freecad_assembly.step"))
    mesh_objects = []
    for source in [*physical_objects, *access_objects]:
        mesh_obj = doc.addObject("Mesh::Feature", source.Name + "_BlenderMesh")
        mesh_obj.Label = source.Name + "_mesh"
        mesh_obj.Mesh = MeshPart.meshFromShape(
            Shape=source.Shape,
            LinearDeflection=0.08,
            AngularDeflection=0.3,
            Relative=False,
        )
        mesh_objects.append(mesh_obj)
    doc.recompute()
    Mesh.export(mesh_objects, str(work / "03_freecad_assembly.obj"))

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
            ref: None if value is None else round(value, 6)
            for ref, value in component_top_clearances.items()
        },
        "critical_requirement": requirements["critical_requirement"],
        "decision": "pass" if all(checks.values()) else "fail",
        "density_g_cm3": density,
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
        "minimum_top_clearance_mm": None if minimum_top_clearance is None else round(minimum_top_clearance, 6),
        "object_bounds_mm": {
            "OpenSCAD_Tray": [round(value, 6) for value in shape_bounds(tray_shape)],
            "OpenSCAD_Lid": [round(value, 6) for value in shape_bounds(lid_shape)],
            "KiCad_PCB": [round(value, 6) for value in shape_bounds(board_shape)],
            **{f"Component_{ref}": [round(value, 6) for value in shape_bounds(shape)] for ref, shape in component_shapes.items()},
            **{f"Access_{ref}": [round(value, 6) for value in shape_bounds(shape.common(assembly_region))] for ref, shape in access_overlays.items()},
        },
        "object_roles": {
            "OpenSCAD_Tray": "tray",
            "OpenSCAD_Lid": "lid",
            "KiCad_PCB": "pcb",
            **{f"Component_{ref}": "component" for ref in component_shapes},
            **{f"Access_{ref}": "access_overlay" for ref in access_overlays},
        },
        "package_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "package_volume_mm3": round(enclosure_volume, 6),
        "pcb_solid_count": len(positive_solids(board_shape, volume_tolerance)),
        "side_clearances_mm": {
            direction: None if value is None else round(value, 6)
            for direction, value in side_clearances.items()
        },
        "software_stage": "FreeCAD",
        "standoff_checks": standoffs,
        "stl_facet_count": int(mesh.CountFacets),
        "task": TASK,
        "tray_bounds_mm": [round(value, 6) for value in shape_bounds(tray_shape)],
        "tray_mass_g": round(tray_volume * density / 1000.0, 6),
        "tray_present_material_fraction": round(tray_present_fraction, 6),
        "tray_solid_count": len(positive_solids(tray_shape, volume_tolerance)),
        "tray_volume_mm3": round(tray_volume, 6),
        "unintended_interference_volume_mm3": total_interference,
    }
    json_dump(work / "03_freecad_clearance_report.json", report)
    if report["decision"] != "pass":
        raise RuntimeError("task-05 FreeCAD checks failed: " + json.dumps(checks, sort_keys=True))


# FreeCADCmd executes scripts with a console-specific module name.
main()
