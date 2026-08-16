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


def component_index(export: dict[str, object], map_rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    rows_by_ref = {row["ref"]: row for row in map_rows}
    result: dict[str, dict[str, object]] = {}
    for raw_item in export["components"]:
        item = dict(raw_item)
        ref = str(item["ref"])
        row = rows_by_ref.get(ref, {})
        if "body_bbox_mm" not in item:
            item["body_bbox_mm"] = [
                float(row.get("body_x_mm") or 0.0),
                float(row.get("body_y_mm") or 0.0),
                float(item.get("height_mm") or row.get("height_mm") or 0.0),
            ]
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


def keepout_cylinder(item: dict[str, object], board_top: float) -> Part.Shape:
    return Part.makeCylinder(
        float(item["keepout_radius_mm"]),
        float(item["height_mm"]),
        App.Vector(float(item["x_mm"]), float(item["y_mm"]), board_top),
    )


def shield_regions(
    requirements: dict[str, object],
    components: dict[str, dict[str, object]],
    board_top: float,
) -> tuple[Part.Shape, Part.Shape]:
    shield = requirements["shield"]
    protected = requirements["protected_volume"]
    center = components[str(protected["center_ref"])]
    cx, cy = float(center["x_mm"]), float(center["y_mm"])
    inner_x, inner_y = (float(value) for value in shield["inner_bbox_xy_mm"])
    wall = float(shield["wall_thickness_mm"])
    inner_top = float(shield["inner_top_z_mm"])
    outer_top = float(shield["outer_top_z_mm"])

    outer = Part.makeBox(
        inner_x + 2.0 * wall,
        inner_y + 2.0 * wall,
        outer_top - board_top,
        App.Vector(cx - inner_x / 2.0 - wall, cy - inner_y / 2.0 - wall, board_top),
    )
    inner = Part.makeBox(
        inner_x,
        inner_y,
        inner_top - board_top,
        App.Vector(cx - inner_x / 2.0, cy - inner_y / 2.0, board_top),
    )
    protected_shape = Part.makeBox(
        float(protected["inner_bbox_xy_mm"][0]),
        float(protected["inner_bbox_xy_mm"][1]),
        float(protected["z_max_mm"]) - board_top,
        App.Vector(
            cx - float(protected["inner_bbox_xy_mm"][0]) / 2.0,
            cy - float(protected["inner_bbox_xy_mm"][1]) / 2.0,
            board_top,
        ),
    )
    return outer.cut(inner).removeSplitter(), protected_shape


def side_clearance(
    package: Part.Shape,
    board: Part.Shape,
    direction: str,
    enclosure_bbox: list[float],
) -> float | None:
    epsilon = 0.02
    z_height = max(0.05, min(0.2, board.BoundBox.ZLength / 2.0))
    z0 = board.BoundBox.Center.z - z_height / 2.0
    x_outer, y_outer = enclosure_bbox[0] / 2.0 + 1.0, enclosure_bbox[1] / 2.0 + 1.0

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
        raise ValueError(f"unsupported side-clearance direction: {direction}")

    side_material = package.common(search)
    if side_material.isNull() or float(side_material.Volume) <= 0.0:
        return None
    return max(0.0, float(reference.distToShape(side_material)[0]))


def side_guard_material(
    package: Part.Shape,
    direction: str,
    outer_x: float,
    wall: float,
    y_min: float,
    y_max: float,
    z_min: float,
    z_max: float,
    guard: float,
) -> tuple[bool, dict[str, float]]:
    inset = min(0.05, guard / 10.0)
    x0 = outer_x - wall if direction == "X_PLUS" else outer_x
    x_length = wall
    y_span = max(0.05, y_max - y_min - 2.0 * inset)
    z_span = max(0.05, z_max - z_min - 2.0 * inset)
    probes = {
        "y_minus": Part.makeBox(x_length, max(0.05, guard - inset), z_span, App.Vector(x0, y_min - guard, z_min + inset)),
        "y_plus": Part.makeBox(x_length, max(0.05, guard - inset), z_span, App.Vector(x0, y_max + inset, z_min + inset)),
        "z_minus": Part.makeBox(x_length, y_span, max(0.05, guard - inset), App.Vector(x0, y_min + inset, z_min - guard)),
        "z_plus": Part.makeBox(x_length, y_span, max(0.05, guard - inset), App.Vector(x0, y_min + inset, z_max + inset)),
    }
    fractions: dict[str, float] = {}
    for name, probe in probes.items():
        fractions[name] = float(package.common(probe).Volume) / max(float(probe.Volume), 1e-9)
    return all(value >= 0.75 for value in fractions.values()), {name: round(value, 6) for name, value in fractions.items()}


def build_access_checks(
    material: Part.Shape,
    package: Part.Shape,
    requirements: dict[str, object],
    components: dict[str, dict[str, object]],
    board_top: float,
    lid_inner_z: float,
    access_rows: list[dict[str, str]],
) -> tuple[dict[str, dict[str, object]], dict[str, Part.Shape]]:
    enclosure_x, _, enclosure_z = (float(value) for value in requirements["expected_enclosure_bbox_mm"])
    wall = float(requirements["wall_mm"])
    overcut = float(requirements["access_overcut_mm"])
    guard = float(requirements["minimum_access_guard_mm"])
    tolerance = float(requirements["interference_volume_tolerance_mm3"])
    checks: dict[str, dict[str, object]] = {}
    overlays: dict[str, Part.Shape] = {}

    for row in access_rows:
        ref = row["ref"]
        item = components[ref]
        cx, cy = float(item["x_mm"]), float(item["y_mm"])
        body_x, _, body_z = (float(value) for value in item["body_bbox_mm"])
        access_type = row["access_type"]
        direction = row["direction"]
        if access_type == "side_window":
            width = float(row["finished_width_mm"])
            height = float(row["finished_height_mm"])
            center_z = board_top + body_z / 2.0
            y_min, y_max = cy - width / 2.0, cy + width / 2.0
            z_min, z_max = center_z - height / 2.0, center_z + height / 2.0
            if direction == "X_PLUS":
                x_min, x_max = cx - body_x / 2.0, enclosure_x / 2.0 + overcut
                wall_outer_x = enclosure_x / 2.0
            elif direction == "X_MINUS":
                x_min, x_max = -enclosure_x / 2.0 - overcut, cx + body_x / 2.0
                wall_outer_x = -enclosure_x / 2.0
            else:
                raise ValueError(f"unsupported side-window direction for {ref}: {direction}")
            probe = Part.makeBox(x_max - x_min, width, height, App.Vector(x_min, y_min, z_min))
            residual = float(material.common(probe).Volume)
            guards_ok, guard_fractions = side_guard_material(
                package, direction, wall_outer_x, wall, y_min, y_max, z_min, z_max, guard
            )
            through = residual <= tolerance and guards_ok
            checks[ref] = {
                "access_type": access_type,
                "bounds_mm": [round(value, 6) for value in [x_min, y_min, z_min, x_max, y_max, z_max]],
                "center_error_mm": 0.0 if residual <= tolerance else None,
                "direction": direction,
                "finished_height_mm": height,
                "finished_width_mm": width,
                "guard_material_fractions": guard_fractions,
                "minimum_guard_material_present": guards_ok,
                "residual_material_volume_mm3": round(residual, 6),
                "through": through,
            }
        elif access_type == "top_bore":
            diameter = float(row["finished_diameter_mm"])
            z_min = board_top + body_z
            z_max = enclosure_z + overcut
            probe = Part.makeCylinder(diameter / 2.0, z_max - z_min, App.Vector(cx, cy, z_min))
            residual = float(material.common(probe).Volume)
            outer_guard = Part.makeCylinder(diameter / 2.0 + guard, enclosure_z - lid_inner_z, App.Vector(cx, cy, lid_inner_z))
            inner_guard = Part.makeCylinder(diameter / 2.0 + min(0.05, guard / 10.0), enclosure_z - lid_inner_z, App.Vector(cx, cy, lid_inner_z))
            annulus = outer_guard.cut(inner_guard)
            guard_fraction = float(package.common(annulus).Volume) / max(float(annulus.Volume), 1e-9)
            guards_ok = guard_fraction >= 0.95
            through = residual <= tolerance and guards_ok
            checks[ref] = {
                "access_type": access_type,
                "bore_volume_mm": [cx, cy, diameter / 2.0, z_min, z_max],
                "center_error_mm": 0.0 if residual <= tolerance else None,
                "direction": direction,
                "finished_diameter_mm": diameter,
                "guard_material_fraction": round(guard_fraction, 6),
                "minimum_guard_material_present": guards_ok,
                "residual_material_volume_mm3": round(residual, 6),
                "through": through,
            }
        else:
            raise ValueError(f"unsupported access type for {ref}: {access_type}")
        overlays[ref] = probe
    return checks, overlays


def add_shape(doc: App.Document, name: str, label: str, shape: Part.Shape) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    return obj


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
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        access_rows = list(csv.DictReader(handle))

    volume_tolerance = float(requirements["interference_volume_tolerance_mm3"])
    geometry_tolerance = float(requirements["geometry_tolerance_mm"])
    expected_enclosure_bbox = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    board_bottom = float(params.get("board_bottom_z_mm", requirements["board_bottom_z_mm"]))
    board_thickness = float(export["board_bbox_mm"][2])
    board_top = float(params.get("board_top_z_mm", board_bottom + board_thickness))
    lid_inner_z = float(params.get("lid_inner_z_mm", expected_enclosure_bbox[2] - float(requirements["lid_thickness_mm"])))

    mesh, submitted_material = mesh_to_material(work / "02_openscad_enclosure.stl", volume_tolerance)
    components = component_index(export, map_rows)
    ideal_shield, protected_shape = shield_regions(requirements, components, board_top)
    shield_shape = submitted_material.common(ideal_shield).removeSplitter()
    package_shape = submitted_material.cut(shield_shape).removeSplitter()
    if not positive_solids(shield_shape, volume_tolerance):
        raise RuntimeError("submitted OpenSCAD geometry contains no installed RF shield material")
    if not positive_solids(package_shape, volume_tolerance):
        raise RuntimeError("submitted OpenSCAD geometry contains no covering package material")

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
    keepouts = {ref: keepout_cylinder(item, board_top) for ref, item in components.items()}

    u1_outside_volume = float(keepouts["U1"].cut(protected_shape).Volume)
    u1_contained = u1_outside_volume <= volume_tolerance
    j1_intersection = float(protected_shape.common(keepouts["J1"]).Volume)
    j1_separation = float(protected_shape.distToShape(keepouts["J1"])[0])
    access_checks, access_overlays = build_access_checks(
        submitted_material,
        package_shape,
        requirements,
        components,
        board_top,
        lid_inner_z,
        access_rows,
    )

    side_clearances = {
        direction: side_clearance(package_shape, board_shape, direction, expected_enclosure_bbox)
        for direction in ("X_MINUS", "X_PLUS", "Y_MINUS", "Y_PLUS")
    }
    finite_clearances = [value for value in side_clearances.values() if value is not None and math.isfinite(value)]
    minimum_side_clearance = min(finite_clearances) if len(finite_clearances) == 4 else None

    interference_by_role: dict[str, dict[str, float]] = {"package": {}, "shield": {}}
    physical_targets = {"PCB": board_shape, **component_shapes}
    for role, material in (("package", package_shape), ("shield", shield_shape)):
        for name, target in physical_targets.items():
            interference_by_role[role][name] = round(float(material.common(target).Volume), 6)
    total_interference = round(
        sum(value for role_values in interference_by_role.values() for value in role_values.values()), 6
    )

    package_volume = float(package_shape.Volume)
    shield_volume = float(shield_shape.Volume)
    package_density = float(requirements["enclosure_material_density_g_cm3"])
    shield_density = float(requirements["shield"]["material_density_g_cm3"])
    enclosure_bbox = [package_shape.BoundBox.XLength, package_shape.BoundBox.YLength, package_shape.BoundBox.ZLength]
    shield_missing_volume = float(ideal_shield.cut(shield_shape).Volume)
    minimum_top_clearance = min(
        lid_inner_z - (board_top + float(item["height_mm"])) for item in components.values()
    )

    doc = App.newDocument("Task03ReleaseAssembly")
    package_obj = add_shape(doc, "OpenSCAD_Package", "OpenSCAD ABS-ESD covering package", package_shape)
    shield_obj = add_shape(doc, "Installed_RF_Shield", "Installed closed-top RF shield", shield_shape)
    board_obj = add_shape(doc, "KiCad_Board", "KiCad PCB board", board_shape)
    component_objects = [
        add_shape(doc, f"Component_{ref}", f"Physical component proxy {ref}", shape)
        for ref, shape in component_shapes.items()
    ]
    protected_obj = add_shape(doc, "Protected_Volume", "Validation overlay: RF protected volume", protected_shape)
    u1_keepout_obj = add_shape(doc, "Keepout_U1", "Validation overlay: included U1 keepout", keepouts["U1"])
    j1_keepout_obj = add_shape(doc, "Keepout_J1", "Validation overlay: excluded J1 keepout", keepouts["J1"])
    access_objects = [
        add_shape(doc, f"Access_{ref}", f"Validation overlay: {ref} access", shape)
        for ref, shape in access_overlays.items()
    ]
    doc.recompute()

    physical_objects = [package_obj, shield_obj, board_obj] + component_objects
    Part.export(physical_objects, str(work / "03_freecad_assembly.step"))
    obj_sources = physical_objects + [protected_obj, u1_keepout_obj, j1_keepout_obj] + access_objects
    mesh_objects = []
    for source in obj_sources:
        mesh_obj = doc.addObject("Mesh::Feature", source.Name + "_BlenderMesh")
        mesh_obj.Label = source.Label
        mesh_obj.Mesh = MeshPart.meshFromShape(
            Shape=source.Shape,
            LinearDeflection=0.1,
            AngularDeflection=0.35,
            Relative=False,
        )
        mesh_objects.append(mesh_obj)
    doc.recompute()
    Mesh.export(mesh_objects, str(work / "03_freecad_assembly.obj"))

    bbox_ok = all(
        abs(actual - expected) <= geometry_tolerance
        for actual, expected in zip(enclosure_bbox, expected_enclosure_bbox)
    )
    checks = {
        "accesses": set(access_checks) == {"J1", "J2", "TP1"} and all(item["through"] for item in access_checks.values()),
        "assembly_has_real_solids": bool(positive_solids(package_shape, volume_tolerance))
        and bool(positive_solids(shield_shape, volume_tolerance))
        and bool(positive_solids(board_shape, volume_tolerance)),
        "enclosure_bbox": bbox_ok,
        "interference": total_interference <= volume_tolerance,
        "j1_excluded": j1_intersection <= volume_tolerance and j1_separation > geometry_tolerance,
        "shield_geometry": shield_missing_volume <= volume_tolerance,
        "side_clearance": minimum_side_clearance is not None
        and minimum_side_clearance + geometry_tolerance >= float(requirements["minimum_side_clearance_mm"]),
        "u1_contained": u1_contained,
    }
    rounded_side_clearances = {
        direction: None if value is None else round(value, 6) for direction, value in side_clearances.items()
    }
    report = {
        "access_checks": access_checks,
        "assembly_mesh": "03_freecad_assembly.obj",
        "assembly_step": "03_freecad_assembly.step",
        "board_bbox_mm": [round(value, 6) for value in export["board_bbox_mm"]],
        "checks": checks,
        "decision": "pass" if all(checks.values()) else "fail",
        "enclosure_bbox_mm": [round(value, 6) for value in enclosure_bbox],
        "enclosure_mass_g": round(package_volume * package_density / 1000.0, 6),
        "enclosure_solid_count": len(positive_solids(package_shape, volume_tolerance)),
        "enclosure_volume_mm3": round(package_volume, 6),
        "estimated_shell_mass_g": round(package_volume * package_density / 1000.0, 6),
        "inputs": [
            "01_kicad_board.kicad_pcb",
            "01_kicad_board.step",
            "01_kicad_export.json",
            "01_kicad_mechanical_map.csv",
            "02_openscad_enclosure.stl",
            "02_openscad_parameters.json",
        ],
        "interference_by_role_mm3": interference_by_role,
        "interference_volume_mm3": total_interference,
        "j1_protected_volume_intersection_mm3": round(j1_intersection, 6),
        "j1_protected_volume_separation_mm": round(j1_separation, 6),
        "keepout_count": len(keepouts),
        "measured_board_step_bbox_mm": [
            round(board_shape.BoundBox.XLength, 6),
            round(board_shape.BoundBox.YLength, 6),
            round(board_shape.BoundBox.ZLength, 6),
        ],
        "minimum_side_clearance_mm": None if minimum_side_clearance is None else round(minimum_side_clearance, 6),
        "minimum_top_clearance_mm": round(minimum_top_clearance, 6),
        "object_roles": {
            "OpenSCAD_Package": "package",
            "Installed_RF_Shield": "shield",
            "KiCad_Board": "pcb",
            **{f"Component_{ref}": "component" for ref in component_shapes},
        },
        "package_mass_g": round(package_volume * package_density / 1000.0, 6),
        "package_volume_mm3": round(package_volume, 6),
        "pcb_solid_count": len(positive_solids(board_shape, volume_tolerance)),
        "shield_mass_g": round(shield_volume * shield_density / 1000.0, 6),
        "shield_missing_ideal_material_volume_mm3": round(shield_missing_volume, 6),
        "shield_solid_count": len(positive_solids(shield_shape, volume_tolerance)),
        "shield_volume_mm3": round(shield_volume, 6),
        "side_clearances_mm": rounded_side_clearances,
        "software_stage": "FreeCAD",
        "stl_facet_count": int(mesh.CountFacets),
        "task": "task-03",
        "protected_volume_bounds_mm": [
            round(protected_shape.BoundBox.XMin, 6),
            round(protected_shape.BoundBox.YMin, 6),
            round(protected_shape.BoundBox.ZMin, 6),
            round(protected_shape.BoundBox.XMax, 6),
            round(protected_shape.BoundBox.YMax, 6),
            round(protected_shape.BoundBox.ZMax, 6),
        ],
        "keepout_volumes": {
            ref: {
                "radius_mm": float(components[ref]["keepout_radius_mm"]),
                "x_mm": float(components[ref]["x_mm"]),
                "y_mm": float(components[ref]["y_mm"]),
                "z_max_mm": board_top + float(components[ref]["height_mm"]),
                "z_min_mm": board_top,
            }
            for ref in keepouts
        },
        "u1_keepout_contained": u1_contained,
        "u1_keepout_outside_protected_volume_mm3": round(u1_outside_volume, 6),
        "unintended_interference_volume_mm3": total_interference,
    }
    json_dump(work / "03_freecad_clearance_report.json", report)
    if report["decision"] != "pass":
        raise RuntimeError("task-03 FreeCAD checks failed: " + json.dumps(checks, sort_keys=True))


# FreeCADCmd executes scripts with a console-specific module name.
main()
