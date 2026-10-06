#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


TASK = "task-08"
COMPONENT_REFS = ("U1", "J1", "J2", "TP1", "TP2")
ACCESS_REFS = ("J1", "J2", "TP1", "TP2")
REQUIRED_METRICS = (
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "standoff_checks",
    "access_checks",
    "busbar_window_separation_mm",
    "creepage_web_check",
    "unintended_interference_volume_mm3",
    "decision",
)


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.4,
    emission: float = 0.0,
) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    if hasattr(value, "surface_render_method"):
        value.surface_render_method = "DITHERED"
    if hasattr(value, "use_transparency_overlap"):
        value.use_transparency_overlap = False
    principled = value.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = roughness
        principled.inputs["Alpha"].default_value = color[3]
        if "Emission Color" in principled.inputs:
            principled.inputs["Emission Color"].default_value = color
            principled.inputs["Emission Strength"].default_value = emission
    return value


def assign_material(obj: bpy.types.Object, value: bpy.types.Material) -> None:
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(value)


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def object_bounds(obj: bpy.types.Object) -> list[float]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return [
        min(point.x for point in points), min(point.y for point in points), min(point.z for point in points),
        max(point.x for point in points), max(point.y for point in points), max(point.z for point in points),
    ]


def bounds_error(actual: list[float], expected: list[float]) -> float:
    return max(abs(a - b) for a, b in zip(actual, expected))


def classify_imported(
    imported: list[bpy.types.Object],
    expected_bounds: dict[str, list[float]],
    tolerance: float,
) -> tuple[dict[str, bpy.types.Object], list[bpy.types.Object]]:
    candidates = sorted(
        (bounds_error(object_bounds(obj), expected), key, obj.name, obj)
        for key, expected in expected_bounds.items()
        for obj in imported
    )
    used_keys: set[str] = set()
    used_objects: set[bpy.types.Object] = set()
    result: dict[str, bpy.types.Object] = {}
    for error, key, _object_name, obj in candidates:
        if error > tolerance or key in used_keys or obj in used_objects:
            continue
        result[key] = obj
        used_keys.add(key)
        used_objects.add(obj)
    missing = sorted(set(expected_bounds) - set(result))
    if missing:
        nearest = {
            key: min(bounds_error(object_bounds(obj), expected_bounds[key]) for obj in imported)
            for key in missing
        }
        raise RuntimeError(f"FreeCAD OBJ lacks expected geometry roles: {nearest}")
    return result, [obj for obj in imported if obj not in used_objects]


def nonmanifold_edge_count(obj: bpy.types.Object) -> int:
    if obj.type != "MESH":
        return 0
    mesh = obj.data.copy()
    mesh.transform(obj.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    count = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    bpy.data.meshes.remove(mesh)
    return count


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_label(
    text: str,
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
    color: tuple[float, float, float, float],
) -> bpy.types.Object:
    curve = bpy.data.curves.new(text.replace(" ", "_") + "_curve", type="FONT")
    curve.body = text
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 3.0
    curve.extrude = 0.04
    obj = bpy.data.objects.new(text.replace(" ", "_") + "_label", curve)
    collection.objects.link(obj)
    obj.location = location
    curve.materials.append(material(text.replace(" ", "_") + "_label_mat", color, roughness=0.32, emission=0.8))
    return obj


def framing_bounds(scene: bpy.types.Scene, camera: bpy.types.Object, bounds: list[float]) -> list[float]:
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    points = [Vector((x, y, z)) for x in (xmin, xmax) for y in (ymin, ymax) for z in (zmin, zmax)]
    projected = [world_to_camera_view(scene, camera, point) for point in points]
    return [
        min(point.x for point in projected), min(point.y for point in projected),
        max(point.x for point in projected), max(point.y for point in projected),
        min(point.z for point in projected),
    ]


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    work = Path(argv[0] if argv else ".").resolve()
    report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    if report.get("task") != TASK or requirements.get("task") != TASK:
        raise RuntimeError("task identity mismatch in task-08 Blender inputs")
    missing_metrics = [key for key in REQUIRED_METRICS if key not in report]
    if missing_metrics:
        raise RuntimeError("FreeCAD report is missing metrics: " + ", ".join(missing_metrics))
    expected_bounds = {
        str(key): [float(value) for value in bounds]
        for key, bounds in report.get("object_bounds_mm", {}).items()
    }
    expected_keys = {
        "OpenSCAD_Tray", "OpenSCAD_Lid", "KiCad_PCB",
        *(f"Component_{ref}" for ref in COMPONENT_REFS),
        *(f"Access_{ref}" for ref in ACCESS_REFS),
        "Creepage_Web",
    }
    if set(expected_bounds) != expected_keys:
        raise RuntimeError(f"FreeCAD object bounds contract mismatch: {sorted(expected_bounds)}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=str(work / "03_freecad_assembly.obj"),
        forward_axis="Y", up_axis="Z", use_split_objects=True, use_split_groups=True,
    )
    imported = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not imported:
        raise RuntimeError("FreeCAD OBJ handoff imported no mesh objects")
    geometry, unclassified = classify_imported(imported, expected_bounds, tolerance=0.6)

    collection_names = [
        "OpenSCAD_tray", "OpenSCAD_lid", "KiCad_board", "FreeCAD_components",
        "access_review", "creepage_review", "review_labels",
    ]
    collections = {name: bpy.data.collections.new(name) for name in collection_names}
    for collection in collections.values():
        bpy.context.scene.collection.children.link(collection)

    mats = {
        "tray_g10": material("tray_g10", (0.16, 0.28, 0.22, 0.88), roughness=0.38),
        "lid_translucent": material("lid_translucent", (0.64, 0.80, 0.86, 0.26), roughness=0.20),
        "pcb_green": material("pcb_green", (0.025, 0.32, 0.10, 1.0), metallic=0.05),
        "u1_sensor": material("u1_sensor", (0.40, 0.22, 0.62, 1.0), metallic=0.22),
        "j1_busbar": material("j1_busbar", (0.92, 0.25, 0.04, 1.0), metallic=0.42),
        "j2_busbar": material("j2_busbar", (0.04, 0.55, 0.92, 1.0), metallic=0.42),
        "tp1_probe": material("tp1_probe", (0.98, 0.72, 0.04, 1.0), metallic=0.12, emission=0.25),
        "tp2_probe": material("tp2_probe", (0.88, 0.10, 0.72, 1.0), metallic=0.12, emission=0.25),
        "j1_window_overlay": material("j1_window_overlay", (1.0, 0.12, 0.04, 0.56), emission=1.3),
        "j2_window_overlay": material("j2_window_overlay", (0.02, 0.75, 1.0, 0.56), emission=1.3),
        "tp1_bore_overlay": material("tp1_bore_overlay", (1.0, 0.82, 0.04, 0.66), emission=1.6),
        "tp2_bore_overlay": material("tp2_bore_overlay", (1.0, 0.10, 0.76, 0.66), emission=1.6),
        "creepage_web_overlay": material("creepage_web_overlay", (0.16, 1.0, 0.32, 0.88), emission=2.4),
    }
    component_materials = {
        "U1": "u1_sensor", "J1": "j1_busbar", "J2": "j2_busbar",
        "TP1": "tp1_probe", "TP2": "tp2_probe",
    }
    overlay_materials = {
        "J1": "j1_window_overlay", "J2": "j2_window_overlay",
        "TP1": "tp1_bore_overlay", "TP2": "tp2_bore_overlay",
        "creepage": "creepage_web_overlay",
    }

    tray = geometry["OpenSCAD_Tray"]
    tray.name = "OpenSCAD_Tray_Physical"
    tray["engiworld_role"] = "tray"
    assign_material(tray, mats["tray_g10"])
    move_to_collection(tray, collections["OpenSCAD_tray"])
    lid = geometry["OpenSCAD_Lid"]
    lid.name = "OpenSCAD_Lid_Physical"
    lid["engiworld_role"] = "lid"
    assign_material(lid, mats["lid_translucent"])
    move_to_collection(lid, collections["OpenSCAD_lid"])
    board = geometry["KiCad_PCB"]
    board.name = "KiCad_PCB_Physical"
    board["engiworld_role"] = "pcb"
    assign_material(board, mats["pcb_green"])
    move_to_collection(board, collections["KiCad_board"])

    component_objects: list[bpy.types.Object] = []
    for ref in COMPONENT_REFS:
        obj = geometry[f"Component_{ref}"]
        obj.name = f"Component_{ref}_Physical"
        obj["engiworld_role"] = "component"
        obj["reference"] = ref
        assign_material(obj, mats[component_materials[ref]])
        move_to_collection(obj, collections["FreeCAD_components"])
        component_objects.append(obj)

    directions = {"J1": "Y_PLUS", "J2": "Y_PLUS", "TP1": "Z_PLUS", "TP2": "Z_PLUS"}
    overlays: list[bpy.types.Object] = []
    overlay_geometry: list[dict[str, Any]] = []
    for ref in ACCESS_REFS:
        obj = geometry[f"Access_{ref}"]
        direction = directions[ref]
        obj.name = f"{ref}_{direction}_Access_Overlay"
        obj["engiworld_role"] = "access_overlay"
        obj["reference"] = ref
        obj["access_direction"] = direction
        assign_material(obj, mats[overlay_materials[ref]])
        move_to_collection(obj, collections["access_review"])
        overlays.append(obj)
        overlay_geometry.append({
            "bounds_mm": [round(value, 6) for value in object_bounds(obj)],
            "direction": direction,
            "material": overlay_materials[ref],
            "name": obj.name,
            "ref": ref,
            "role": "access_overlay",
        })

    creepage_obj = geometry["Creepage_Web"]
    creepage_obj.name = "Y_PLUS_Creepage_Web_Overlay"
    creepage_obj["engiworld_role"] = "creepage_overlay"
    assign_material(creepage_obj, mats[overlay_materials["creepage"]])
    move_to_collection(creepage_obj, collections["creepage_review"])
    creepage_bounds = object_bounds(creepage_obj)
    creepage_length = creepage_bounds[3] - creepage_bounds[0]
    creepage_report = report["creepage_web_check"]
    creepage_geometry_ok = (
        abs(creepage_length - float(creepage_report["measured_segment_length_mm"])) <= float(requirements["geometry_tolerance_mm"])
        and creepage_length + float(requirements["geometry_tolerance_mm"]) >= float(requirements["creepage_side_wall_web"]["minimum_distance_mm"])
        and bool(creepage_report["single_connected_material"])
    )

    for obj in unclassified:
        obj.hide_render = True
        obj.hide_viewport = True
    labels = [
        add_label("J1 Y+", (-54.0, 29.0, 17.0), collections["review_labels"], (1.0, 0.16, 0.04, 1.0)),
        add_label("J2 Y+", (54.0, 29.0, 17.0), collections["review_labels"], (0.04, 0.78, 1.0, 1.0)),
        add_label("TP1", (-12.0, 8.0, 24.4), collections["review_labels"], (1.0, 0.82, 0.04, 1.0)),
        add_label("TP2", (12.0, 8.0, 24.4), collections["review_labels"], (1.0, 0.10, 0.76, 1.0)),
        add_label("WEB 82", (0.0, 27.0, 14.0), collections["review_labels"], (0.16, 1.0, 0.32, 1.0)),
    ]

    scene = bpy.context.scene
    engines = {item.identifier for item in scene.bl_rna.properties["render"].fixed_type.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(work / "04_blender_review.png")
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Task08World")
    scene.world.color = (0.025, 0.032, 0.040)

    camera_data = bpy.data.cameras.new("release_review_camera")
    camera = bpy.data.objects.new("release_review_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (230.0, 270.0, 185.0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 238.0
    look_at(camera, (0.0, 0.0, 11.8))
    scene.camera = camera
    bpy.context.view_layer.update()

    key_data = bpy.data.lights.new("key_area", type="AREA")
    key_data.energy = 1450.0
    key_data.shape = "DISK"
    key_data.size = 130.0
    key = bpy.data.objects.new("key_area", key_data)
    scene.collection.objects.link(key)
    key.location = (90.0, 110.0, 180.0)
    look_at(key, (0.0, 0.0, 12.0))
    fill_data = bpy.data.lights.new("fill_area", type="AREA")
    fill_data.energy = 950.0
    fill_data.size = 110.0
    fill = bpy.data.objects.new("fill_area", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-130.0, -90.0, 120.0)
    look_at(fill, (0.0, 0.0, 12.0))

    package = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    package_bounds = [-package[0] / 2.0, -package[1] / 2.0, 0.0, package[0] / 2.0, package[1] / 2.0, package[2]]
    frame = framing_bounds(scene, camera, package_bounds)
    package_center = Vector((0.0, 0.0, package[2] / 2.0))
    camera_forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    camera_front_facing = camera_forward.dot(package_center - camera.location) > 0.0
    camera_frame_ok = (
        frame[0] >= 0.02 and frame[1] >= 0.02 and frame[2] <= 0.98 and frame[3] <= 0.98
        and camera_front_facing
    )

    export_objects = [obj for obj in [tray, lid, board, *component_objects, *overlays, creepage_obj] if obj.type == "MESH"]
    assignments = {
        obj.name: [slot.material.name for slot in obj.material_slots if slot.material]
        for obj in export_objects
    }
    mesh_qc = {
        "missing_material_slots": sum(1 for names in assignments.values() if not names),
        "nonmanifold_edges": sum(nonmanifold_edge_count(obj) for obj in export_objects),
        "unclassified_objects": len(unclassified),
        "unlabeled_overlays": sum(1 for obj in overlays if not obj.get("reference")),
    }
    role_counts = {"tray": 1, "lid": 1, "pcb": 1, "component": len(component_objects), "access_overlay": len(overlays), "creepage_overlay": 1}
    roles_ok = role_counts == {"tray": 1, "lid": 1, "pcb": 1, "component": 5, "access_overlay": 4, "creepage_overlay": 1}
    overlays_ok = len(overlays) == 4 and {str(obj["reference"]) for obj in overlays} == set(ACCESS_REFS) and creepage_geometry_ok
    overlay_materials_ok = len({overlay_materials[ref] for ref in ACCESS_REFS} | {overlay_materials["creepage"]}) == 5
    decision = (
        "pass" if report.get("decision") == "pass" and roles_ok and overlays_ok and overlay_materials_ok
        and camera_frame_ok and all(value == 0 for value in mesh_qc.values()) else "fail"
    )
    scene["engiworld_task"] = TASK
    scene["release_decision"] = decision
    scene["freecad_decision"] = str(report.get("decision", "missing"))
    scene["required_roles_present"] = roles_ok
    scene["required_overlays_present"] = overlays_ok
    scene["creepage_web_length_mm"] = creepage_length
    scene["camera_frame_ok"] = camera_frame_ok

    bpy.ops.wm.save_as_mainfile(filepath=str(work / "04_blender_review.blend"), compress=True)
    bpy.ops.render.render(write_still=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]
    bpy.ops.wm.obj_export(
        filepath=str(work / "04_blender_review.obj"), export_selected_objects=True,
        export_materials=True, export_triangulated_mesh=True, forward_axis="Y", up_axis="Z",
    )

    copied_metrics = {key: report[key] for key in REQUIRED_METRICS}
    report_out = {
        "active_camera": camera.name,
        "camera": {
            "frame_bounds_normalized": [round(value, 6) for value in frame],
            "framing_pass": camera_frame_ok,
            "front_facing": camera_front_facing,
            "location_mm": [round(float(value), 6) for value in camera.location],
            "name": camera.name,
            "ortho_scale_mm": float(camera.data.ortho_scale),
            "projection": "orthographic",
            "view": "top_oblique",
        },
        "collections": collection_names,
        "decision": decision,
        "freecad_metrics": copied_metrics,
        "inputs": ["03_freecad_assembly.obj", "03_freecad_clearance_report.json", "mechanical_requirements.json", "connector_keepouts.csv"],
        "label_names": [obj.name for obj in labels],
        "material_assignments": assignments,
        "materials": sorted({name for values in assignments.values() for name in values}),
        "mesh_qc": mesh_qc,
        "metrics_source": "03_freecad_clearance_report.json",
        "native_scene": "04_blender_review.blend",
        "object_roles": {obj.name: obj.get("engiworld_role", "") for obj in export_objects},
        "creepage_web_overlay": {
            "bounds_mm": [round(value, 6) for value in creepage_bounds],
            "independent_object": True,
            "material": overlay_materials["creepage"],
            "measured_length_mm": round(creepage_length, 6),
            "name": creepage_obj.name,
            "role": "creepage_overlay",
            "single_connected_material": bool(creepage_report["single_connected_material"]),
        },
        "overlay_geometry": overlay_geometry,
        "overlay_materials": {
            "J1_Y_PLUS": overlay_materials["J1"], "J2_Y_PLUS": overlay_materials["J2"],
            "TP1_Z_PLUS": overlay_materials["TP1"], "TP2_Z_PLUS": overlay_materials["TP2"],
            "CREEPAGE_WEB": overlay_materials["creepage"],
        },
        "real_object_roles": {obj.name: obj.get("engiworld_role", "") for obj in [tray, lid, board, *component_objects]},
        "render": "04_blender_review.png",
        "review_mtl": "04_blender_review.mtl",
        "review_obj": "04_blender_review.obj",
        "role_counts": role_counts,
        "role_references": {"access_overlay": list(ACCESS_REFS), "component": list(COMPONENT_REFS), "creepage_overlay": ["J1", "J2"]},
        "software_stage": "Blender",
        "task": TASK,
        "visible_accesses": [f"{ref}_{directions[ref]}" for ref in ACCESS_REFS],
        "visible_features": ["J1_Y_PLUS_window", "J2_Y_PLUS_window", "TP1_Z_PLUS_bore", "TP2_Z_PLUS_bore", "creepage_web"],
        "visible_keepouts": list(ACCESS_REFS),
        "visible_overlays": [obj.name for obj in [*overlays, creepage_obj]],
    }
    json_dump(work / "04_blender_scene_report.json", report_out)
    if decision != "pass":
        raise RuntimeError(
            f"task-08 Blender contract failed: roles={role_counts}, overlays={len(overlays)}, "
            f"mesh_qc={mesh_qc}, frame={frame}, front={camera_front_facing}, freecad={report.get('decision')!r}"
        )


if __name__ == "__main__":
    main()
