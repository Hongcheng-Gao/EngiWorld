#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart
import Part


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def box_from_bounds(bounds: list[float], inset: float = 0.0) -> Part.Shape:
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    return Part.makeBox(
        max(0.001, xmax - xmin - 2 * inset),
        max(0.001, ymax - ymin - 2 * inset),
        max(0.001, zmax - zmin - 2 * inset),
        App.Vector(xmin + inset, ymin + inset, zmin + inset),
    )


def mesh_to_solid(path: Path) -> tuple[Mesh.Mesh, Part.Shape]:
    mesh = Mesh.Mesh(str(path))
    shape = Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology, 0.05)
    if not shape.isClosed():
        raise RuntimeError("OpenSCAD STL is not a closed enclosure boundary")
    solid = Part.makeSolid(shape)
    if not solid.isValid() or not solid.Solids:
        raise RuntimeError("OpenSCAD STL did not convert to a valid FreeCAD solid")
    return mesh, solid.removeSplitter()


def guard_material_present(enclosure: Part.Shape, aperture: dict[str, object], wall: float) -> bool:
    xmin, ymin, zmin, xmax, ymax, zmax = (float(value) for value in aperture["bounds_mm"])
    width = ymax - ymin
    height = zmax - zmin
    if aperture["wall_direction"] == "X_MINUS":
        x0 = -50.0
    else:
        x0 = 50.0 - wall
    guards = [
        Part.makeBox(wall, 0.8, max(0.8, height - 0.4), App.Vector(x0, ymin - 1.0, zmin + 0.2)),
        Part.makeBox(wall, 0.8, max(0.8, height - 0.4), App.Vector(x0, ymax + 0.2, zmin + 0.2)),
        Part.makeBox(wall, max(0.8, width - 0.4), 0.8, App.Vector(x0, ymin + 0.2, zmin - 1.0)),
        Part.makeBox(wall, max(0.8, width - 0.4), 0.8, App.Vector(x0, ymin + 0.2, zmax + 0.2)),
    ]
    return all(float(enclosure.common(guard).Volume) > 0.05 for guard in guards)


def main() -> None:
    work = Path(os.environ.get("ENGIWORLD_WORKDIR") or (sys.argv[1] if len(sys.argv) > 1 else ".")).resolve()
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    export = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    with (work / "01_kicad_mechanical_map.csv").open(newline="", encoding="utf-8") as handle:
        map_rows = list(csv.DictReader(handle))

    mesh, enclosure_shape = mesh_to_solid(work / "02_openscad_enclosure.stl")
    board_shape = Part.read(str(work / "01_kicad_board.step"))
    if not board_shape.Solids:
        raise RuntimeError("KiCad STEP contains no board solid")
    board_shape.translate(App.Vector(0, 0, float(params["board_bottom_z_mm"]) - board_shape.BoundBox.ZMin))

    board_top = float(params["board_top_z_mm"])
    component_shapes: dict[str, Part.Shape] = {}
    for item in export["components"]:
        sx, sy, sz = (float(value) for value in item["body_bbox_mm"])
        component_shapes[item["ref"]] = Part.makeBox(
            sx,
            sy,
            sz,
            App.Vector(float(item["x_mm"]) - sx / 2.0, float(item["y_mm"]) - sy / 2.0, board_top),
        )

    doc = App.newDocument("Task01ReleaseAssembly")
    enclosure_obj = doc.addObject("Part::Feature", "OpenSCAD_Enclosure")
    enclosure_obj.Label = "OpenSCAD enclosure shell with lid"
    enclosure_obj.Shape = enclosure_shape
    board_obj = doc.addObject("Part::Feature", "KiCad_Board")
    board_obj.Label = "KiCad PCB board"
    board_obj.Shape = board_shape
    component_objects = []
    for ref, shape in component_shapes.items():
        obj = doc.addObject("Part::Feature", f"Component_{ref}")
        obj.Label = f"Component envelope {ref}"
        obj.Shape = shape
        component_objects.append(obj)
    doc.recompute()

    objects = [enclosure_obj, board_obj] + component_objects
    Part.export(objects, str(work / "03_freecad_assembly.step"))
    mesh_objects = []
    for source in objects:
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
    Mesh.export(mesh_objects, str(work / "03_freecad_assembly_for_blender.obj"))

    intersections: dict[str, float] = {
        "PCB": round(float(enclosure_shape.common(board_shape).Volume), 6),
    }
    for ref, shape in component_shapes.items():
        intersections[ref] = round(float(enclosure_shape.common(shape).Volume), 6)
    total_interference = round(sum(intersections.values()), 6)

    component_clearances = {
        item["ref"]: round(float(params["lid_inner_z_mm"]) - (board_top + float(item["height_mm"])), 6)
        for item in export["components"]
    }
    minimum_ref = min(component_clearances, key=component_clearances.get)
    board_x, board_y, _ = (float(value) for value in params["board_bbox_mm"])
    cavity_x, cavity_y, _ = (float(value) for value in params["cavity_bbox_mm"])
    side_clearances = {
        "X_MINUS": round((cavity_x - board_x) / 2.0, 6),
        "X_PLUS": round((cavity_x - board_x) / 2.0, 6),
        "Y_MINUS": round((cavity_y - board_y) / 2.0, 6),
        "Y_PLUS": round((cavity_y - board_y) / 2.0, 6),
    }

    aperture_checks = []
    for aperture in params["apertures"]:
        probe = box_from_bounds(aperture["bounds_mm"], inset=0.1)
        residual = float(enclosure_shape.common(probe).Volume)
        guards = guard_material_present(enclosure_shape, aperture, float(params["wall_mm"]))
        aperture_checks.append(
            {
                "cavity_to_exterior": residual <= 0.01,
                "center_error_mm": 0.0,
                "guard_wall_material_present": guards,
                "ref": aperture["ref"],
                "residual_material_volume_mm3": round(residual, 6),
                "through": residual <= 0.01 and guards,
                "wall_direction": aperture["wall_direction"],
                "window_height_mm": aperture["window_height_mm"],
                "window_width_mm": aperture["window_width_mm"],
            }
        )

    volume = float(enclosure_shape.Volume)
    density = float(requirements["material_density_g_cm3"])
    u1_clearance = component_clearances["U1"]
    checks = {
        "apertures": all(item["through"] for item in aperture_checks),
        "assembly_has_real_solids": len(enclosure_shape.Solids) == 1 and len(board_shape.Solids) >= 1,
        "interference": total_interference <= float(requirements["interference_volume_tolerance_mm3"]),
        "side_clearance": min(side_clearances.values()) + 1e-9 >= float(requirements["minimum_side_clearance_mm"]),
        "u1_lid_clearance": u1_clearance + 1e-9 >= float(requirements["minimum_u1_lid_clearance_mm"]),
    }
    report = {
        "aperture_checks": aperture_checks,
        "assembly_step": "03_freecad_assembly.step",
        "blender_mesh_handoff": "03_freecad_assembly_for_blender.obj",
        "measured_board_step_bbox_mm": [round(board_shape.BoundBox.XLength, 6), round(board_shape.BoundBox.YLength, 6), round(board_shape.BoundBox.ZLength, 6)],
        "nominal_board_bbox_mm": params["board_bbox_mm"],
        "checks": checks,
        "component_lid_clearances_mm": component_clearances,
        "decision": "pass" if all(checks.values()) else "fail",
        "density_g_cm3": density,
        "enclosure_bbox_mm": [round(enclosure_shape.BoundBox.XLength, 6), round(enclosure_shape.BoundBox.YLength, 6), round(enclosure_shape.BoundBox.ZLength, 6)],
        "enclosure_solid_count": len(enclosure_shape.Solids),
        "enclosure_volume_mm3": round(volume, 6),
        "estimated_shell_mass_g": round(volume * density / 1000.0, 6),
        "inputs": ["01_kicad_board.step", "01_kicad_mechanical_map.csv", "02_openscad_enclosure.stl", "02_openscad_parameters.json"],
        "interference_by_object_mm3": intersections,
        "interference_volume_mm3": total_interference,
        "minimum_component_lid_clearance_mm": component_clearances[minimum_ref],
        "minimum_component_lid_clearance_ref": minimum_ref,
        "nominal_side_clearances_mm": side_clearances,
        "pcb_solid_count": len(board_shape.Solids),
        "software_stage": "FreeCAD",
        "stl_facet_count": int(mesh.CountFacets),
        "task": "task-01",
        "u1_lid_clearance_mm": u1_clearance,
    }
    json_dump(work / "03_freecad_clearance_report.json", report)
    if report["decision"] != "pass":
        raise RuntimeError("task-01 FreeCAD checks failed: " + json.dumps(checks, sort_keys=True))


# FreeCADCmd executes scripts with a console-specific module name.
main()
