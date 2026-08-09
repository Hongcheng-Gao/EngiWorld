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


TASK = "task-05"
TP_REFS = ("TP1", "TP2", "TP3", "TP4")
ACCESS_REFS = (*TP_REFS, "J1")
REQUIRED_METRICS = [
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "standoff_checks",
    "access_checks",
    "unintended_interference_volume_mm3",
    "decision",
]


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
    value.surface_render_method = "DITHERED" if color[3] < 1.0 else "DITHERED"
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
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    return [
        min(point.x for point in corners),
        min(point.y for point in corners),
        min(point.z for point in corners),
        max(point.x for point in corners),
        max(point.y for point in corners),
        max(point.z for point in corners),
    ]


def bounds_error(actual: list[float], expected: list[float]) -> float:
    return max(abs(float(a) - float(b)) for a, b in zip(actual, expected))


def classify_imported(
    imported: list[bpy.types.Object],
    expected_bounds: dict[str, list[float]],
    tolerance: float,
) -> tuple[dict[str, bpy.types.Object], list[bpy.types.Object]]:
    candidates: list[tuple[float, str, bpy.types.Object]] = []
    for key, expected in expected_bounds.items():
        for obj in imported:
            candidates.append((bounds_error(object_bounds(obj), expected), key, obj))
    candidates.sort(key=lambda item: item[0])
    assigned_keys: set[str] = set()
    assigned_objects: set[bpy.types.Object] = set()
    result: dict[str, bpy.types.Object] = {}
    for error, key, obj in candidates:
        if error > tolerance or key in assigned_keys or obj in assigned_objects:
            continue
        result[key] = obj
        assigned_keys.add(key)
        assigned_objects.add(obj)
    missing = sorted(set(expected_bounds) - set(result))
    if missing:
        details = {
            key: min(bounds_error(object_bounds(obj), expected_bounds[key]) for obj in imported)
            for key in missing
        }
        raise RuntimeError(f"FreeCAD OBJ lacks expected geometry roles: {details}")
    return result, [obj for obj in imported if obj not in assigned_objects]


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
    curve.size = 2.4
    curve.extrude = 0.035
    obj = bpy.data.objects.new(text.replace(" ", "_") + "_label", curve)
    collection.objects.link(obj)
    obj.location = location
    label_material = material(text.replace(" ", "_") + "_label_mat", color, roughness=0.35, emission=0.7)
    curve.materials.append(label_material)
    return obj


def framing_bounds(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    bounds: list[float],
) -> list[float]:
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    points = [
        Vector((x, y, z))
        for x in (xmin, xmax)
        for y in (ymin, ymax)
        for z in (zmin, zmax)
    ]
    projected = [world_to_camera_view(scene, camera, point) for point in points]
    return [
        min(point.x for point in projected),
        min(point.y for point in projected),
        max(point.x for point in projected),
        max(point.y for point in projected),
        min(point.z for point in projected),
    ]


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    work = Path(argv[0] if argv else ".").resolve()
    report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    if report.get("task") != TASK or requirements.get("task") != TASK:
        raise RuntimeError("task identity mismatch in task-05 Blender inputs")
    missing_metrics = [key for key in REQUIRED_METRICS if key not in report]
    if missing_metrics:
        raise RuntimeError("FreeCAD report is missing metrics: " + ", ".join(missing_metrics))
    expected_bounds = {
        str(key): [float(value) for value in bounds]
        for key, bounds in report.get("object_bounds_mm", {}).items()
    }
    expected_keys = {
        "OpenSCAD_Tray",
        "OpenSCAD_Lid",
        "KiCad_PCB",
        *(f"Component_{ref}" for ref in ACCESS_REFS),
        *(f"Access_{ref}" for ref in ACCESS_REFS),
    }
    if set(expected_bounds) != expected_keys:
        raise RuntimeError(f"FreeCAD object bounds contract mismatch: {sorted(expected_bounds)}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=str(work / "03_freecad_assembly.obj"),
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
    )
    imported = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if not imported:
        raise RuntimeError("FreeCAD OBJ handoff imported no mesh objects")
    geometry, unclassified = classify_imported(imported, expected_bounds, tolerance=0.6)

    collection_names = [
        "OpenSCAD_tray",
        "OpenSCAD_lid",
        "KiCad_board",
        "FreeCAD_components",
        "access_review",
        "review_labels",
    ]
    collections = {name: bpy.data.collections.new(name) for name in collection_names}
    for collection in collections.values():
        bpy.context.scene.collection.children.link(collection)

    mats = {
        "tray_pc": material("tray_pc", (0.16, 0.28, 0.38, 0.78), roughness=0.38),
        "lid_translucent": material("lid_translucent", (0.62, 0.80, 0.88, 0.28), roughness=0.22),
        "pcb_green": material("pcb_green", (0.03, 0.34, 0.12, 1.0), metallic=0.05),
        "component_neutral": material("component_neutral", (0.28, 0.31, 0.35, 1.0), metallic=0.22),
        "tp1_access_red": material("tp1_access_red", (1.0, 0.08, 0.04, 0.52), emission=1.0),
        "tp2_access_amber": material("tp2_access_amber", (1.0, 0.52, 0.02, 0.52), emission=1.0),
        "tp3_access_cyan": material("tp3_access_cyan", (0.02, 0.82, 0.92, 0.52), emission=1.0),
        "tp4_access_magenta": material("tp4_access_magenta", (0.90, 0.08, 0.66, 0.52), emission=1.0),
        "j1_access_lime": material("j1_access_lime", (0.46, 0.96, 0.04, 0.58), emission=1.15),
    }
    overlay_material_names = {
        "TP1": "tp1_access_red",
        "TP2": "tp2_access_amber",
        "TP3": "tp3_access_cyan",
        "TP4": "tp4_access_magenta",
        "J1": "j1_access_lime",
    }

    tray = geometry["OpenSCAD_Tray"]
    tray.name = "OpenSCAD_Tray_Physical"
    tray["engiworld_role"] = "tray"
    assign_material(tray, mats["tray_pc"])
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
    for ref in ACCESS_REFS:
        obj = geometry[f"Component_{ref}"]
        obj.name = f"Component_{ref}_Physical"
        obj["engiworld_role"] = "component"
        obj["reference"] = ref
        assign_material(obj, mats["component_neutral"])
        move_to_collection(obj, collections["FreeCAD_components"])
        component_objects.append(obj)

    overlays: list[bpy.types.Object] = []
    overlay_geometry: list[dict[str, Any]] = []
    for ref in ACCESS_REFS:
        obj = geometry[f"Access_{ref}"]
        direction = "Z_PLUS" if ref in TP_REFS else "Y_PLUS"
        obj.name = f"{ref}_{direction}_Access_Overlay"
        obj["engiworld_role"] = "access_overlay"
        obj["reference"] = ref
        obj["access_direction"] = direction
        material_name = overlay_material_names[ref]
        assign_material(obj, mats[material_name])
        move_to_collection(obj, collections["access_review"])
        overlays.append(obj)
        overlay_geometry.append(
            {
                "bounds_mm": [round(value, 6) for value in object_bounds(obj)],
                "direction": direction,
                "material": material_name,
                "name": obj.name,
                "ref": ref,
                "role": "access_overlay",
            }
        )

    for obj in unclassified:
        obj.hide_render = True
        obj.hide_viewport = True
    add_label("TP1 Z+", (-22.0, -15.5, 21.0), collections["review_labels"], (1.0, 0.12, 0.08, 1.0))
    add_label("TP2 Z+", (-6.0, -15.5, 21.0), collections["review_labels"], (1.0, 0.60, 0.04, 1.0))
    add_label("TP3 Z+", (10.0, -15.5, 21.0), collections["review_labels"], (0.04, 0.88, 1.0, 1.0))
    add_label("TP4 Z+", (26.0, -15.5, 21.0), collections["review_labels"], (1.0, 0.12, 0.72, 1.0))
    add_label("J1 Y+", (0.0, 45.0, 14.0), collections["review_labels"], (0.55, 1.0, 0.08, 1.0))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(work / "04_blender_review.png")
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Task05World")
    scene.world.color = (0.035, 0.045, 0.055)

    camera_data = bpy.data.cameras.new("release_review_camera")
    camera = bpy.data.objects.new("release_review_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (118.0, -142.0, 118.0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 148.0
    look_at(camera, (0.0, 0.0, 9.5))
    scene.camera = camera
    bpy.context.view_layer.update()

    key_data = bpy.data.lights.new("key_area", type="AREA")
    key_data.energy = 1150.0
    key_data.shape = "DISK"
    key_data.size = 95.0
    key = bpy.data.objects.new("key_area", key_data)
    scene.collection.objects.link(key)
    key.location = (45.0, -55.0, 105.0)
    look_at(key, (0.0, 0.0, 8.0))
    fill_data = bpy.data.lights.new("fill_area", type="AREA")
    fill_data.energy = 750.0
    fill_data.size = 80.0
    fill = bpy.data.objects.new("fill_area", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-70.0, 45.0, 75.0)
    look_at(fill, (0.0, 0.0, 8.0))

    enclosure = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    frame = framing_bounds(
        scene,
        camera,
        [-enclosure[0] / 2.0, -enclosure[1] / 2.0, 0.0, enclosure[0] / 2.0, enclosure[1] / 2.0, enclosure[2]],
    )
    enclosure_center = Vector((0.0, 0.0, enclosure[2] / 2.0))
    camera_forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    camera_front_facing = camera_forward.dot(enclosure_center - camera.location) > 0.0
    camera_frame_ok = (
        frame[0] >= 0.03
        and frame[1] >= 0.03
        and frame[2] <= 0.97
        and frame[3] <= 0.97
        and camera_front_facing
    )

    export_objects = [obj for obj in [tray, lid, board, *component_objects, *overlays] if obj.type == "MESH"]
    material_assignments = {
        obj.name: [slot.material.name for slot in obj.material_slots if slot.material]
        for obj in export_objects
    }
    mesh_qc = {
        "missing_material_slots": sum(1 for names in material_assignments.values() if not names),
        "nonmanifold_edges": sum(nonmanifold_edge_count(obj) for obj in export_objects),
        "unclassified_objects": len(unclassified),
        "unlabeled_overlays": sum(1 for obj in overlays if not obj.get("reference")),
    }
    role_counts = {"tray": 1, "lid": 1, "pcb": 1, "component": len(component_objects), "access_overlay": len(overlays)}
    required_roles_present = role_counts == {"tray": 1, "lid": 1, "pcb": 1, "component": 5, "access_overlay": 5}
    overlays_present = len(overlays) == 5 and {str(obj["reference"]) for obj in overlays} == set(ACCESS_REFS)
    materials_ok = mesh_qc["missing_material_slots"] == 0 and len({overlay_material_names[ref] for ref in ACCESS_REFS}) == 5
    decision = (
        "pass"
        if report.get("decision") == "pass"
        and required_roles_present
        and overlays_present
        and materials_ok
        and camera_frame_ok
        and all(value == 0 for value in mesh_qc.values())
        else "fail"
    )
    scene["engiworld_task"] = TASK
    scene["release_decision"] = decision
    scene["freecad_decision"] = str(report.get("decision", "missing"))
    scene["required_roles_present"] = required_roles_present
    scene["required_overlays_present"] = overlays_present
    scene["camera_frame_ok"] = camera_frame_ok

    blend_path = work / "04_blender_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    bpy.ops.render.render(write_still=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objects[0]
    bpy.ops.wm.obj_export(
        filepath=str(work / "04_blender_review.obj"),
        export_selected_objects=True,
        export_materials=True,
        export_triangulated_mesh=True,
        forward_axis="Y",
        up_axis="Z",
    )

    copied_metrics = {key: report[key] for key in REQUIRED_METRICS}
    visible_features = [
        *(f"{ref}_Z_PLUS_access_overlay" for ref in TP_REFS),
        "J1_Y_PLUS_access_overlay",
    ]
    scene_report = {
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
        "inputs": [
            "03_freecad_assembly.obj",
            "03_freecad_clearance_report.json",
            "mechanical_requirements.json",
            "connector_keepouts.csv",
        ],
        "material_assignments": material_assignments,
        "materials": sorted({name for values in material_assignments.values() for name in values}),
        "mesh_qc": mesh_qc,
        "metrics_source": "03_freecad_clearance_report.json",
        "native_scene": "04_blender_review.blend",
        "object_roles": {obj.name: obj.get("engiworld_role", "") for obj in export_objects},
        "overlay_geometry": overlay_geometry,
        "overlay_materials": {f"{ref}_{'Z_PLUS' if ref in TP_REFS else 'Y_PLUS'}": overlay_material_names[ref] for ref in ACCESS_REFS},
        "real_object_roles": {obj.name: obj.get("engiworld_role", "") for obj in [tray, lid, board, *component_objects]},
        "render": "04_blender_review.png",
        "review_mtl": "04_blender_review.mtl",
        "review_obj": "04_blender_review.obj",
        "role_counts": role_counts,
        "role_references": {
            "access_overlay": list(ACCESS_REFS),
            "component": list(ACCESS_REFS),
        },
        "software_stage": "Blender",
        "task": TASK,
        "visible_accesses": [f"{ref}_Z_PLUS" for ref in TP_REFS] + ["J1_Y_PLUS"],
        "visible_features": visible_features,
        "visible_keepouts": list(ACCESS_REFS),
        "visible_overlays": [obj.name for obj in overlays],
    }
    json_dump(work / "04_blender_scene_report.json", scene_report)
    if decision != "pass":
        raise RuntimeError(
            f"task-05 Blender contract failed: roles={role_counts}, overlays={len(overlays)}, "
            f"mesh_qc={mesh_qc}, camera_frame={frame}, freecad={report.get('decision')!r}"
        )


if __name__ == "__main__":
    main()
