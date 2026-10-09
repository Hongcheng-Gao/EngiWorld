#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App
import Mesh
import MeshPart
import Part


TASK = "task-09"
COMPONENT_REFS = ("U1", "J1", "J2", "H1", "H2")
ACCESS_REFS = ("J1", "J2", "H1", "H2")


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def shape_bounds(shape: Part.Shape) -> list[float]:
    box = shape.BoundBox
    return [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]


def positive_solids(shape: Part.Shape, tolerance: float) -> list[Part.Shape]:
    if shape.isNull():
        return []
    return [solid for solid in shape.Solids if float(solid.Volume) > tolerance]


def fuse_solids(solids: list[Part.Shape], label: str) -> Part.Shape:
    if not solids:
        raise RuntimeError(f"{label} contains no positive solid")
    result = solids[0]
    for solid in solids[1:]:
        result = result.fuse(solid)
    return result.removeSplitter()


def mesh_to_solids(path: Path, tolerance: float) -> tuple[Mesh.Mesh, list[Part.Shape]]:
    mesh = Mesh.Mesh(str(path))
    raw = Part.Shape()
    raw.makeShapeFromMesh(mesh.Topology, 0.05)
    solids = []
    for shell in raw.Shells:
        if not shell.isClosed():
            continue
        solid = Part.makeSolid(shell).removeSplitter()
        if solid.isValid() and float(solid.Volume) > tolerance:
            solids.append(solid)
    if len(solids) < 2:
        raise RuntimeError("OpenSCAD STL must contain separate closed tray and lid solids")
    return mesh, solids


def box_from_bounds(bounds: list[float], inset: float = 0.0) -> Part.Shape:
    xmin, ymin, zmin, xmax, ymax, zmax = (float(value) for value in bounds)
    return Part.makeBox(
        max(0.001, xmax - xmin - 2.0 * inset),
        max(0.001, ymax - ymin - 2.0 * inset),
        max(0.001, zmax - zmin - 2.0 * inset),
        App.Vector(xmin + inset, ymin + inset, zmin + inset),
    )


def add_shape(doc: App.Document, name: str, label: str, shape: Part.Shape) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    return obj


def component_shape(item: dict[str, Any], board_top: float) -> Part.Shape:
    sx, sy, sz = (float(value) for value in item["body_bbox_mm"])
    x, y = float(item["x_mm"]), float(item["y_mm"])
    if item["shape"] == "cylinder":
        if abs(sx - sy) > 1e-6:
            raise ValueError(f"cylindrical component {item['ref']} has unequal XY dimensions")
        return Part.makeCylinder(sx / 2.0, sz, App.Vector(x, y, board_top))
    return Part.makeBox(sx, sy, sz, App.Vector(x - sx / 2.0, y - sy / 2.0, board_top))


def inside(shape: Part.Shape, x: float, y: float, z: float, tolerance: float) -> bool:
    return bool(shape.isInside(App.Vector(x, y, z), tolerance, True))


def empty_to_material_boundary(
    shape: Part.Shape,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    search: float,
    tolerance: float,
) -> float | None:
    ox, oy, oz = origin
    dx, dy, dz = direction
    if inside(shape, ox, oy, oz, tolerance):
        return None
    if not inside(shape, ox + dx * search, oy + dy * search, oz + dz * search, tolerance):
        return None
    empty_distance = 0.0
    material_distance = search
    for _ in range(40):
        midpoint = (empty_distance + material_distance) / 2.0
        if inside(shape, ox + dx * midpoint, oy + dy * midpoint, oz + dz * midpoint, tolerance):
            material_distance = midpoint
        else:
            empty_distance = midpoint
    return material_distance


def material_to_empty_boundary(
    shape: Part.Shape,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    search: float,
    tolerance: float,
) -> float | None:
    ox, oy, oz = origin
    dx, dy, dz = direction
    if not inside(shape, ox, oy, oz, tolerance):
        return None
    if inside(shape, ox + dx * search, oy + dy * search, oz + dz * search, tolerance):
        return None
    material_distance = 0.0
    empty_distance = search
    for _ in range(40):
        midpoint = (material_distance + empty_distance) / 2.0
        if inside(shape, ox + dx * midpoint, oy + dy * midpoint, oz + dz * midpoint, tolerance):
            material_distance = midpoint
        else:
            empty_distance = midpoint
    return empty_distance


def side_clearance(tray: Part.Shape, board: Part.Shape, direction: str, package: list[float]) -> float | None:
    epsilon = 0.02
    height = min(0.2, board.BoundBox.ZLength / 2.0)
    z0 = board.BoundBox.Center.z - height / 2.0
    outer_x = package[0] / 2.0 + 1.0
    outer_y = package[1] / 2.0 + 1.0
    if direction == "X_MINUS":
        reference = Part.makeBox(epsilon, board.BoundBox.YLength, height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMin, z0))
        search = Part.makeBox(board.BoundBox.XMin + outer_x, board.BoundBox.YLength, height, App.Vector(-outer_x, board.BoundBox.YMin, z0))
    elif direction == "X_PLUS":
        reference = Part.makeBox(epsilon, board.BoundBox.YLength, height, App.Vector(board.BoundBox.XMax - epsilon, board.BoundBox.YMin, z0))
        search = Part.makeBox(outer_x - board.BoundBox.XMax, board.BoundBox.YLength, height, App.Vector(board.BoundBox.XMax, board.BoundBox.YMin, z0))
    elif direction == "Y_MINUS":
        reference = Part.makeBox(board.BoundBox.XLength, epsilon, height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMin, z0))
        search = Part.makeBox(board.BoundBox.XLength, board.BoundBox.YMin + outer_y, height, App.Vector(board.BoundBox.XMin, -outer_y, z0))
    elif direction == "Y_PLUS":
        reference = Part.makeBox(board.BoundBox.XLength, epsilon, height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMax - epsilon, z0))
        search = Part.makeBox(board.BoundBox.XLength, outer_y - board.BoundBox.YMax, height, App.Vector(board.BoundBox.XMin, board.BoundBox.YMax, z0))
    else:
        raise ValueError(direction)
    wall = tray.common(search)
    if wall.isNull() or float(wall.Volume) <= 0.0:
        return None
    return max(0.0, float(reference.distToShape(wall)[0]))


def standoff_checks(
    tray: Part.Shape,
    holes: list[dict[str, Any]],
    requirements: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    axis_tolerance = float(requirements["axis_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    base = float(requirements["base_thickness_mm"])
    height = float(requirements["standoff_height_mm"])
    outer_diameter = float(requirements["standoff_outer_diameter_mm"])
    bore_diameter = float(requirements["standoff_bore_diameter_mm"])
    bore_z0, bore_z1 = (float(value) for value in requirements["standoff_bore_cutter_z_bounds_mm"])
    probe_tolerance = min(1e-5, max(1e-7, geometry_tolerance * 0.001))
    section_z = base + height / 2.0
    for hole in holes:
        ref = str(hole["ref"])
        x, y = float(hole["x_mm"]), float(hole["y_mm"])
        inner_search = bore_diameter / 2.0 + 0.35
        outer_origin_radius = (bore_diameter + outer_diameter) / 4.0
        outer_search = outer_diameter / 2.0 + 0.5 - outer_origin_radius
        directions = {
            "x_plus": (1.0, 0.0), "x_minus": (-1.0, 0.0),
            "y_plus": (0.0, 1.0), "y_minus": (0.0, -1.0),
        }
        inner: dict[str, float] = {}
        outer: dict[str, float] = {}
        for name, (dx, dy) in directions.items():
            boundary = empty_to_material_boundary(tray, (x, y, section_z), (dx, dy, 0.0), inner_search, probe_tolerance)
            if boundary is not None:
                inner[name] = boundary
            outside = material_to_empty_boundary(
                tray,
                (x + dx * outer_origin_radius, y + dy * outer_origin_radius, section_z),
                (dx, dy, 0.0),
                outer_search,
                probe_tolerance,
            )
            if outside is not None:
                outer[name] = outer_origin_radius + outside
        if len(inner) == 4 and len(outer) == 4:
            bore_x = inner["x_plus"] + inner["x_minus"]
            bore_y = inner["y_plus"] + inner["y_minus"]
            outer_x = outer["x_plus"] + outer["x_minus"]
            outer_y = outer["y_plus"] + outer["y_minus"]
            bore_center = (x + (inner["x_plus"] - inner["x_minus"]) / 2.0, y + (inner["y_plus"] - inner["y_minus"]) / 2.0)
            outer_center = (x + (outer["x_plus"] - outer["x_minus"]) / 2.0, y + (outer["y_plus"] - outer["y_minus"]) / 2.0)
            measured_bore = (bore_x + bore_y) / 2.0
            measured_outer = (outer_x + outer_y) / 2.0
            axis_error = math.hypot(bore_center[0] - x, bore_center[1] - y)
            concentric_error = math.hypot(bore_center[0] - outer_center[0], bore_center[1] - outer_center[1])
        else:
            bore_center = outer_center = None
            measured_bore = measured_outer = axis_error = concentric_error = None
        bore_probe = Part.makeCylinder(max(0.05, bore_diameter / 2.0 - geometry_tolerance), bore_z1 - bore_z0, App.Vector(x, y, bore_z0))
        residual = float(tray.common(bore_probe).Volume)
        probe_margin = geometry_tolerance
        probe_height = max(0.01, height - 2.0 * probe_margin)
        ideal_annulus = Part.makeCylinder(
            outer_diameter / 2.0 - probe_margin,
            probe_height,
            App.Vector(x, y, base + probe_margin),
        ).cut(
            Part.makeCylinder(
                bore_diameter / 2.0 + probe_margin,
                probe_height,
                App.Vector(x, y, base + probe_margin),
            )
        )
        present_fraction = float(tray.common(ideal_annulus).Volume) / max(float(ideal_annulus.Volume), 1e-9)
        dimensions_pass = (
            measured_bore is not None and abs(measured_bore - bore_diameter) <= geometry_tolerance
            and measured_outer is not None and abs(measured_outer - outer_diameter) <= geometry_tolerance
            and axis_error is not None and axis_error <= axis_tolerance
            and concentric_error is not None and concentric_error <= axis_tolerance
        )
        result[ref] = {
            "axis_error_mm": None if axis_error is None else round(axis_error, 6),
            "bore_center_xy_mm": None if bore_center is None else [round(v, 6) for v in bore_center],
            "bore_diameter_mm": None if measured_bore is None else round(measured_bore, 6),
            "bore_z_bounds_mm": [bore_z0, bore_z1],
            "concentric_error_mm": None if concentric_error is None else round(concentric_error, 6),
            "continuous_bore": residual <= volume_tolerance and dimensions_pass,
            "outer_center_xy_mm": None if outer_center is None else [round(v, 6) for v in outer_center],
            "outer_diameter_mm": None if measured_outer is None else round(measured_outer, 6),
            "present_material_fraction": round(present_fraction, 6),
            "ref": ref,
            "residual_bore_material_volume_mm3": round(residual, 6),
            "standoff_present": present_fraction >= 0.95 and dimensions_pass,
            "x_mm": x,
            "y_mm": y,
        }
    return result


def side_access_check(tray: Part.Shape, spec: dict[str, Any], requirements: dict[str, Any]) -> tuple[dict[str, Any], Part.Shape]:
    path = [float(value) for value in spec["path_bounds_mm"]]
    cutter = [float(value) for value in spec["cutter_bounds_mm"]]
    _xmin, ymin, zmin, _xmax, ymax, zmax = cutter
    direction = str(spec["direction"])
    package = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    center_tolerance = float(requirements["access_center_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    guard = float(requirements["minimum_access_guard_mm"])
    probe_tolerance = min(1e-5, max(1e-7, geometry_tolerance * 0.001))
    if direction not in {"X_MINUS", "X_PLUS"}:
        raise ValueError(f"task-09 side window must use X_MINUS or X_PLUS, got {direction}")
    wall_x = (-package[0] / 2.0 + float(requirements["wall_mm"]) / 2.0) if direction == "X_MINUS" else (package[0] / 2.0 - float(requirements["wall_mm"]) / 2.0)
    center_y = (ymin + ymax) / 2.0
    center_z = (zmin + zmax) / 2.0
    half_width = (ymax - ymin) / 2.0
    half_height = (zmax - zmin) / 2.0
    searches = {
        "y_plus": ((0.0, 1.0, 0.0), half_width + guard),
        "y_minus": ((0.0, -1.0, 0.0), half_width + guard),
        "z_plus": ((0.0, 0.0, 1.0), half_height + guard),
        "z_minus": ((0.0, 0.0, -1.0), half_height + guard),
    }
    boundaries: dict[str, float] = {}
    for name, (axis, search) in searches.items():
        value = empty_to_material_boundary(tray, (wall_x, center_y, center_z), axis, search, probe_tolerance)
        if value is not None:
            boundaries[name] = value
    if len(boundaries) == 4:
        measured_width = boundaries["y_plus"] + boundaries["y_minus"]
        measured_height = boundaries["z_plus"] + boundaries["z_minus"]
        measured_center_y = center_y + (boundaries["y_plus"] - boundaries["y_minus"]) / 2.0
        measured_center_z = center_z + (boundaries["z_plus"] - boundaries["z_minus"]) / 2.0
        center_error = math.hypot(measured_center_y - center_y, measured_center_z - center_z)
    else:
        measured_width = measured_height = measured_center_y = measured_center_z = center_error = None
    guard_probes = {
        "y_plus": (wall_x, ymax + guard / 2.0, center_z),
        "y_minus": (wall_x, ymin - guard / 2.0, center_z),
        "z_plus": (wall_x, center_y, zmax + guard / 2.0),
        "z_minus": (wall_x, center_y, zmin - guard / 2.0),
    }
    guard_samples = {name: inside(tray, *point, probe_tolerance) for name, point in guard_probes.items()}
    opposite_x = package[0] / 2.0 - float(requirements["wall_mm"]) / 2.0 if direction == "X_MINUS" else -package[0] / 2.0 + float(requirements["wall_mm"]) / 2.0
    opposite_wall_center_material = inside(tray, opposite_x, center_y, center_z, probe_tolerance)
    core = box_from_bounds(path, inset=min(0.04, geometry_tolerance / 3.0))
    residual = float(tray.common(core).Volume)
    width_error = None if measured_width is None else abs(measured_width - float(spec["finished_width_mm"]))
    height_error = None if measured_height is None else abs(measured_height - float(spec["finished_height_mm"]))
    through = (
        residual <= volume_tolerance
        and width_error is not None and width_error <= geometry_tolerance
        and height_error is not None and height_error <= geometry_tolerance
        and center_error is not None and center_error <= center_tolerance
        and all(guard_samples.values())
    )
    return ({
        "access_type": "side_window",
        "center_error_mm": None if center_error is None else round(center_error, 6),
        "cutter_bounds_mm": cutter,
        "direction": direction,
        "finished_height_mm": None if measured_height is None else round(measured_height, 6),
        "finished_width_mm": None if measured_width is None else round(measured_width, 6),
        "guard_material_samples": guard_samples,
        "height_error_mm": None if height_error is None else round(height_error, 6),
        "measured_center_yz_mm": None if measured_center_y is None else [round(measured_center_y, 6), round(measured_center_z, 6)],
        "minimum_guard_material_present": all(guard_samples.values()),
        "minimum_guard_mm": guard,
        "opposite_wall_center_material_present": opposite_wall_center_material,
        "path_bounds_mm": path,
        "ref": spec["ref"],
        "residual_material_volume_mm3": round(residual, 6),
        "through": through,
        "width_error_mm": None if width_error is None else round(width_error, 6),
    }, box_from_bounds(path))


def heater_access_check(
    enclosure_parts: list[Part.Shape],
    lid: Part.Shape,
    spec: dict[str, Any],
    requirements: dict[str, Any],
) -> tuple[dict[str, Any], Part.Shape]:
    x, y = float(spec["x_mm"]), float(spec["y_mm"])
    diameter = float(spec["finished_diameter_mm"])
    radius = diameter / 2.0
    path = [float(value) for value in spec["path_bounds_mm"]]
    cutter = [float(value) for value in spec["cutter_bounds_mm"]]
    exposure = requirements["heater_exposure"]
    projected_z = [float(value) for value in exposure["projected_exclusion_z_bounds_mm"]]
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    axis_tolerance = float(requirements["access_center_tolerance_mm"])
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    guard = float(requirements["minimum_access_guard_mm"])
    probe_tolerance = min(1e-5, max(1e-7, geometry_tolerance * 0.001))
    path_shape = Part.makeCylinder(radius, path[5] - path[2], App.Vector(x, y, path[2]))
    probe_radius = max(0.05, radius - geometry_tolerance)
    path_probe = Part.makeCylinder(probe_radius, path[5] - path[2], App.Vector(x, y, path[2]))
    path_residual = sum(float(part.common(path_probe).Volume) for part in enclosure_parts)
    projected = Part.makeCylinder(probe_radius, projected_z[1] - projected_z[0], App.Vector(x, y, projected_z[0]))
    projected_intersection = sum(float(part.common(projected).Volume) for part in enclosure_parts)
    section_z = float(requirements["lid_inner_z_mm"]) + float(requirements["lid_thickness_mm"]) / 2.0
    search = radius + guard
    directions = {
        "x_plus": (1.0, 0.0, 0.0), "x_minus": (-1.0, 0.0, 0.0),
        "y_plus": (0.0, 1.0, 0.0), "y_minus": (0.0, -1.0, 0.0),
    }
    boundaries: dict[str, float] = {}
    for name, axis in directions.items():
        value = empty_to_material_boundary(lid, (x, y, section_z), axis, search, probe_tolerance)
        if value is not None:
            boundaries[name] = value
    if len(boundaries) == 4:
        diameter_x = boundaries["x_plus"] + boundaries["x_minus"]
        diameter_y = boundaries["y_plus"] + boundaries["y_minus"]
        measured_diameter = (diameter_x + diameter_y) / 2.0
        measured_center = [x + (boundaries["x_plus"] - boundaries["x_minus"]) / 2.0, y + (boundaries["y_plus"] - boundaries["y_minus"]) / 2.0]
        axis_error = math.hypot(measured_center[0] - x, measured_center[1] - y)
    else:
        diameter_x = diameter_y = measured_diameter = axis_error = None
        measured_center = None
    probe_height = 0.02
    section_probe = Part.makeCylinder(radius, probe_height, App.Vector(x, y, section_z - probe_height / 2.0))
    blocked_area = float(lid.common(section_probe).Volume) / probe_height
    ideal_area = math.pi * radius * radius
    open_area_ratio = max(0.0, min(1.0, (ideal_area - blocked_area) / ideal_area))
    guard_radius = radius + guard / 2.0
    sample_count = 64
    guard_count = sum(
        inside(lid, x + guard_radius * math.cos(2.0 * math.pi * index / sample_count),
               y + guard_radius * math.sin(2.0 * math.pi * index / sample_count), section_z, probe_tolerance)
        for index in range(sample_count)
    )
    guard_fraction = guard_count / sample_count
    diameter_error = None if measured_diameter is None else abs(measured_diameter - diameter)
    through = (
        path_residual <= volume_tolerance
        and projected_intersection <= float(exposure["maximum_carrier_intersection_per_ref_mm3"])
        and open_area_ratio >= float(exposure["minimum_open_area_ratio"])
        and diameter_error is not None and diameter_error <= geometry_tolerance
        and axis_error is not None and axis_error <= axis_tolerance
        and guard_fraction >= 0.98
    )
    return ({
        "access_type": "top_keepout_opening",
        "axis_error_mm": None if axis_error is None else round(axis_error, 6),
        "carrier_intersection_volume_mm3": round(projected_intersection, 6),
        "cutter_bounds_mm": cutter,
        "diameter_error_mm": None if diameter_error is None else round(diameter_error, 6),
        "direction": "Z_PLUS",
        "finished_diameter_mm": None if measured_diameter is None else round(measured_diameter, 6),
        "finished_diameter_x_mm": None if diameter_x is None else round(diameter_x, 6),
        "finished_diameter_y_mm": None if diameter_y is None else round(diameter_y, 6),
        "guard_material_fraction": round(guard_fraction, 6),
        "maximum_carrier_intersection_mm3": float(exposure["maximum_carrier_intersection_per_ref_mm3"]),
        "measured_center_xy_mm": None if measured_center is None else [round(value, 6) for value in measured_center],
        "minimum_guard_material_present": guard_fraction >= 0.98,
        "minimum_open_area_ratio": float(exposure["minimum_open_area_ratio"]),
        "open_area_ratio": round(open_area_ratio, 6),
        "path_bounds_mm": path,
        "path_residual_material_volume_mm3": round(path_residual, 6),
        "projected_exclusion_z_bounds_mm": projected_z,
        "ref": spec["ref"],
        "through": through,
        "x_mm": x,
        "y_mm": y,
    }, path_shape)


def main() -> None:
    argument = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    work = Path(
        os.environ.get("ENGIWORLD_WORKDIR")
        or (str(argument) if argument is not None and argument.is_dir() else ".")
    ).resolve()
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    export = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    if any(value.get("task") != TASK for value in (requirements, params, export)):
        raise ValueError("task identity mismatch in task-09 FreeCAD inputs")
    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    package = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    tray_top = float(requirements["tray_outer_top_z_mm"])
    lid_inner = float(requirements["lid_inner_z_mm"])
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + float(export["board_bbox_mm"][2])
    density = float(requirements["enclosure_material_density_g_cm3"])

    mesh, mesh_solids = mesh_to_solids(work / "02_openscad_enclosure.stl", volume_tolerance)
    tray_solids = [solid for solid in mesh_solids if solid.BoundBox.ZMin < tray_top / 2.0]
    lid_solids = [solid for solid in mesh_solids if solid.BoundBox.ZMin >= lid_inner - geometry_tolerance]
    tray = fuse_solids(tray_solids, "submitted tray")
    lid = fuse_solids(lid_solids, "submitted lid")
    enclosure_parts = [tray, lid]

    board = Part.read(str(work / "01_kicad_board.step"))
    if not positive_solids(board, volume_tolerance):
        raise RuntimeError("KiCad STEP contains no board solid")
    board.translate(App.Vector(-board.BoundBox.Center.x, -board.BoundBox.Center.y, board_bottom - board.BoundBox.ZMin))
    components = {str(item["ref"]): item for item in export["components"]}
    component_shapes = {ref: component_shape(item, board_top) for ref, item in components.items()}

    side_clearances = {direction: side_clearance(tray, board, direction, package) for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")}
    finite_side = [value for value in side_clearances.values() if value is not None and math.isfinite(value)]
    minimum_side = min(finite_side) if len(finite_side) == 4 else None
    top_clearances = {
        ref: None if ref in {"H1", "H2"} else lid.BoundBox.ZMin - shape.BoundBox.ZMax
        for ref, shape in component_shapes.items()
    }
    minimum_top = min(value for value in top_clearances.values() if value is not None)
    standoffs = standoff_checks(tray, export["mounting_holes"], requirements)

    access_checks: dict[str, dict[str, Any]] = {}
    access_overlays: dict[str, Part.Shape] = {}
    for access in params["accesses"]:
        if access["access_type"] == "side_window":
            check, overlay = side_access_check(tray, access, requirements)
        elif access["access_type"] == "top_keepout_opening":
            check, overlay = heater_access_check(enclosure_parts, lid, access, requirements)
        else:
            raise ValueError(f"unexpected task-09 access type {access['access_type']!r}")
        access_checks[str(access["ref"])] = check
        access_overlays[str(access["ref"])] = overlay
    heater_checks = {ref: access_checks[ref] for ref in ("H1", "H2")}
    heater_edge_gap = float(access_overlays["H1"].distToShape(access_overlays["H2"])[0])

    physical_targets = {"PCB": board, **component_shapes}
    interference_by_object = {
        name: round(sum(float(part.common(shape).Volume) for part in enclosure_parts), 6)
        for name, shape in physical_targets.items()
    }
    total_interference = round(sum(interference_by_object.values()), 6)
    enclosure_bbox = [
        max(part.BoundBox.XMax for part in enclosure_parts) - min(part.BoundBox.XMin for part in enclosure_parts),
        max(part.BoundBox.YMax for part in enclosure_parts) - min(part.BoundBox.YMin for part in enclosure_parts),
        max(part.BoundBox.ZMax for part in enclosure_parts) - min(part.BoundBox.ZMin for part in enclosure_parts),
    ]
    measured_board_bbox = [board.BoundBox.XLength, board.BoundBox.YLength, board.BoundBox.ZLength]
    lid_separation = float(tray.distToShape(lid)[0])
    enclosure_volume = sum(float(part.Volume) for part in enclosure_parts)
    tray_volume = float(tray.Volume)
    lid_volume = float(lid.Volume)
    checks = {
        "accesses": set(access_checks) == set(ACCESS_REFS) and all(item["through"] is True for item in access_checks.values()),
        "assembly_has_real_solids": all(positive_solids(shape, volume_tolerance) for shape in [tray, lid, board, *component_shapes.values()]),
        "board_bbox": all(abs(a - float(b)) <= geometry_tolerance for a, b in zip(measured_board_bbox, export["board_bbox_mm"])),
        "board_placement": abs(board.BoundBox.Center.x) <= float(requirements["axis_tolerance_mm"])
        and abs(board.BoundBox.Center.y) <= float(requirements["axis_tolerance_mm"])
        and abs(board.BoundBox.ZMin - board_bottom) <= geometry_tolerance,
        "enclosure_bbox": all(abs(a - b) <= geometry_tolerance for a, b in zip(enclosure_bbox, package)),
        "heater_edge_gap": heater_edge_gap + geometry_tolerance >= float(requirements["heater_exposure"]["minimum_opening_edge_gap_mm"]),
        "heater_exposure": all(item["through"] is True for item in heater_checks.values()),
        "interference": total_interference <= volume_tolerance,
        "lid_separation": abs(lid_separation - float(requirements["lid_separation_mm"])) <= geometry_tolerance,
        "opposite_side_windows": access_checks["J1"]["direction"] == "X_MINUS" and access_checks["J2"]["direction"] == "X_PLUS",
        "side_clearance": minimum_side is not None and minimum_side + geometry_tolerance >= float(requirements["minimum_side_clearance_mm"]),
        "standoff_bores": len(standoffs) == 4 and all(item["continuous_bore"] and item["standoff_present"] for item in standoffs.values()),
        "top_clearance": minimum_top + geometry_tolerance >= float(requirements["minimum_top_clearance_mm"]),
    }

    doc = App.newDocument("Task09ReleaseAssembly")
    tray_obj = add_shape(doc, "OpenSCAD_Tray", "Black PA12 thermal target tray", tray)
    lid_obj = add_shape(doc, "OpenSCAD_Lid", "Separate black PA12 heater-opening lid", lid)
    board_obj = add_shape(doc, "KiCad_PCB", "KiCad thermal calibration PCB", board)
    component_objects = [add_shape(doc, f"Component_{ref}", f"Physical component {ref}", component_shapes[ref]) for ref in COMPONENT_REFS]
    access_objects = [add_shape(doc, f"Access_{ref}", f"Validation overlay for {ref}", access_overlays[ref]) for ref in ACCESS_REFS]
    doc.recompute()
    physical_objects = [tray_obj, lid_obj, board_obj, *component_objects]
    Part.export(physical_objects, str(work / "03_freecad_assembly.step"))
    mesh_objects = []
    for source in [*physical_objects, *access_objects]:
        mesh_obj = doc.addObject("Mesh::Feature", source.Name + "_BlenderMesh")
        mesh_obj.Label = source.Name + "_mesh"
        mesh_obj.Mesh = MeshPart.meshFromShape(Shape=source.Shape, LinearDeflection=0.08, AngularDeflection=0.3, Relative=False)
        mesh_objects.append(mesh_obj)
    doc.recompute()
    Mesh.export(mesh_objects, str(work / "03_freecad_assembly.obj"))

    object_bounds = {
        "OpenSCAD_Tray": [round(v, 6) for v in shape_bounds(tray)],
        "OpenSCAD_Lid": [round(v, 6) for v in shape_bounds(lid)],
        "KiCad_PCB": [round(v, 6) for v in shape_bounds(board)],
        **{f"Component_{ref}": [round(v, 6) for v in shape_bounds(shape)] for ref, shape in component_shapes.items()},
        **{f"Access_{ref}": [round(v, 6) for v in shape_bounds(shape)] for ref, shape in access_overlays.items()},
    }
    report = {
        "access_checks": access_checks,
        "assembly_mesh": "03_freecad_assembly.obj",
        "assembly_step": "03_freecad_assembly.step",
        "board_bbox_mm": [round(float(v), 6) for v in export["board_bbox_mm"]],
        "board_bottom_z_mm": round(board.BoundBox.ZMin, 6),
        "board_top_z_mm": round(board.BoundBox.ZMax, 6),
        "checks": checks,
        "component_top_clearances_mm": {ref: None if value is None else round(value, 6) for ref, value in top_clearances.items()},
        "covered_component_refs": ["U1", "J1", "J2"],
        "critical_requirement": requirements["critical_requirement"],
        "decision": "pass" if all(checks.values()) else "fail",
        "density_g_cm3": density,
        "enclosure_bbox_mm": [round(value, 6) for value in enclosure_bbox],
        "enclosure_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "enclosure_material": requirements["enclosure_material"],
        "enclosure_solid_bounds_mm": [[round(v, 6) for v in shape_bounds(solid)] for solid in mesh_solids],
        "enclosure_solid_count": len(mesh_solids),
        "enclosure_volume_mm3": round(enclosure_volume, 6),
        "estimated_shell_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "heater_exposure_checks": heater_checks,
        "heater_opening_edge_gap_mm": round(heater_edge_gap, 6),
        "inputs": ["01_kicad_board.step", "01_kicad_export.json", "01_kicad_mechanical_map.csv", "02_openscad_enclosure.stl", "02_openscad_parameters.json"],
        "interference_by_object_mm3": interference_by_object,
        "interference_volume_mm3": total_interference,
        "keepout_count": len(components),
        "lid_bounds_mm": [round(v, 6) for v in shape_bounds(lid)],
        "lid_mass_g": round(lid_volume * density / 1000.0, 6),
        "lid_separation_mm": round(lid_separation, 6),
        "lid_solid_count": len(positive_solids(lid, volume_tolerance)),
        "lid_volume_mm3": round(lid_volume, 6),
        "measured_board_step_bbox_mm": [round(value, 6) for value in measured_board_bbox],
        "minimum_side_clearance_mm": None if minimum_side is None else round(minimum_side, 6),
        "minimum_top_clearance_mm": round(minimum_top, 6),
        "object_bounds_mm": object_bounds,
        "object_roles": {
            "OpenSCAD_Tray": "tray", "OpenSCAD_Lid": "lid", "KiCad_PCB": "pcb",
            **{f"Component_{ref}": "component" for ref in COMPONENT_REFS},
            **{f"Access_{ref}": "heater_exposure_overlay" if ref in {"H1", "H2"} else "access_overlay" for ref in ACCESS_REFS},
        },
        "package_mass_g": round(enclosure_volume * density / 1000.0, 6),
        "package_volume_mm3": round(enclosure_volume, 6),
        "pcb_solid_count": len(positive_solids(board, volume_tolerance)),
        "side_clearances_mm": {key: None if value is None else round(value, 6) for key, value in side_clearances.items()},
        "software_stage": "FreeCAD",
        "standoff_checks": standoffs,
        "stl_facet_count": int(mesh.CountFacets),
        "task": TASK,
        "tray_bounds_mm": [round(v, 6) for v in shape_bounds(tray)],
        "tray_mass_g": round(tray_volume * density / 1000.0, 6),
        "tray_solid_count": len(positive_solids(tray, volume_tolerance)),
        "tray_volume_mm3": round(tray_volume, 6),
        "unintended_interference_volume_mm3": total_interference,
    }
    json_dump(work / "03_freecad_clearance_report.json", report)
    if report["decision"] != "pass":
        raise RuntimeError("task-09 FreeCAD checks failed: " + json.dumps(checks, sort_keys=True))


# FreeCADCmd executes scripts with a console-specific module name.
main()
