#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


TASK = "task-10"
COMPONENT_REFS = ("A1", "U1", "J1", "BT1", "TP1")
ACCESS_REFS = ("J1", "TP1")
REQUIRED_METRICS = (
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "standoff_checks",
    "access_checks",
    "antenna_keepout_check",
    "antenna_carrier_intersection_mm3",
    "antenna_component_intersection_mm3",
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
    curve.size = 3.2
    curve.extrude = 0.04
    obj = bpy.data.objects.new(text.replace(" ", "_") + "_label", curve)
    collection.objects.link(obj)
    obj.location = location
    curve.materials.append(material(text.replace(" ", "_") + "_label_mat", color, roughness=0.28, emission=1.0))
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
        raise RuntimeError("task identity mismatch in task-10 Blender inputs")
    missing_metrics = [key for key in REQUIRED_METRICS if key not in report]
    if missing_metrics:
        raise RuntimeError("FreeCAD report is missing metrics: " + ", ".join(missing_metrics))
    expected_bounds = {str(key): [float(value) for value in bounds] for key, bounds in report.get("object_bounds_mm", {}).items()}
    expected_keys = {
        "OpenSCAD_Tray", "OpenSCAD_Lid", "KiCad_PCB",
        *(f"Component_{ref}" for ref in COMPONENT_REFS),
        *(f"Access_{ref}" for ref in ACCESS_REFS),
        "Antenna_Keepout_A1",
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
        "KiCad_board", "OpenSCAD_enclosure", "FreeCAD_components",
        "FreeCAD_clearance_overlays", "critical_keepouts", "review_labels",
    ]
    collections = {name: bpy.data.collections.new(name) for name in collection_names}
    for collection in collections.values():
        bpy.context.scene.collection.children.link(collection)

    mats = {
        "enclosure_translucent": material("enclosure_translucent", (0.18, 0.24, 0.29, 0.82), roughness=0.34),
        "lid_translucent": material("lid_translucent", (0.42, 0.55, 0.64, 0.24), roughness=0.18),
        "pcb_green": material("pcb_green", (0.025, 0.32, 0.10, 1.0), metallic=0.05),
        "a1_patch": material("a1_patch", (0.75, 0.66, 0.20, 1.0), metallic=0.28),
        "u1_soc": material("u1_soc", (0.18, 0.22, 0.27, 1.0), metallic=0.18),
        "j1_sma": material("j1_sma", (0.75, 0.78, 0.82, 1.0), metallic=0.72),
        "bt1_cell": material("bt1_cell", (0.18, 0.48, 0.82, 1.0), metallic=0.30),
        "tp1_test": material("tp1_test", (0.92, 0.36, 0.10, 1.0), metallic=0.45),
        "j1_xplus_overlay": material("j1_xplus_overlay", (0.02, 0.78, 1.0, 0.58), emission=1.6),
        "tp1_zplus_overlay": material("tp1_zplus_overlay", (0.92, 0.18, 0.06, 0.52), emission=2.1),
        "keepout_warning": material("keepout_warning", (1.0, 0.58, 0.02, 0.40), emission=2.4),
    }
    component_materials = {
        "A1": "a1_patch", "U1": "u1_soc", "J1": "j1_sma",
        "BT1": "bt1_cell", "TP1": "tp1_test",
    }
    overlay_materials = {
        "J1": "j1_xplus_overlay", "TP1": "tp1_zplus_overlay",
    }
    directions = {"J1": "X_PLUS", "TP1": "Z_PLUS"}

    tray = geometry["OpenSCAD_Tray"]
    tray.name = "OpenSCAD_Tray_Physical"
    tray["engiworld_role"] = "tray"
    assign_material(tray, mats["enclosure_translucent"])
    move_to_collection(tray, collections["OpenSCAD_enclosure"])
    lid = geometry["OpenSCAD_Lid"]
    lid.name = "OpenSCAD_Lid_Physical"
    lid["engiworld_role"] = "lid"
    assign_material(lid, mats["lid_translucent"])
    move_to_collection(lid, collections["OpenSCAD_enclosure"])
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
        move_to_collection(obj, collections["FreeCAD_clearance_overlays"])
        overlays.append(obj)
        overlay_geometry.append({
            "bounds_mm": [round(value, 6) for value in object_bounds(obj)],
            "direction": direction,
            "material": overlay_materials[ref],
            "name": obj.name,
            "ref": ref,
            "role": obj["engiworld_role"],
        })

    antenna_overlay = geometry["Antenna_Keepout_A1"]
    antenna_overlay.name = "A1_Z_PLUS_Antenna_Reserved_Volume"
    antenna_overlay["engiworld_role"] = "antenna_volume_overlay"
    antenna_overlay["reference"] = "A1"
    antenna_overlay["access_direction"] = "Z_PLUS"
    assign_material(antenna_overlay, mats["keepout_warning"])
    move_to_collection(antenna_overlay, collections["critical_keepouts"])
    overlays.append(antenna_overlay)
    antenna_bounds = [round(value, 6) for value in object_bounds(antenna_overlay)]
    overlay_geometry.append({
        "bounds_mm": antenna_bounds,
        "direction": "Z_PLUS",
        "material": "keepout_warning",
        "name": antenna_overlay.name,
        "ref": "A1",
        "role": "antenna_volume_overlay",
    })

    for obj in unclassified:
        obj.hide_render = True
        obj.hide_viewport = True
    labels = [
        add_label("J1 X+", (62.0, -12.0, 22.0), collections["review_labels"], (0.04, 0.82, 1.0, 1.0)),
        add_label("TP1 Z+", (18.0, -30.0, 39.0), collections["review_labels"], (1.0, 0.28, 0.06, 1.0)),
        add_label("A1 RESERVED", (0.0, 16.0, 36.5), collections["review_labels"], (1.0, 0.62, 0.04, 1.0)),
    ]

    scene = bpy.context.scene
    engines = {
        item.identifier
        for item in scene.bl_rna.properties["render"].fixed_type.properties["engine"].enum_items
    }
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(work / "04_blender_review.png")
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Task10World")
    scene.world.color = (0.018, 0.024, 0.032)

    camera_data = bpy.data.cameras.new("release_review_camera")
    camera = bpy.data.objects.new("release_review_camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (190.0, -220.0, 180.0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 184.0
    look_at(camera, (0.0, -4.0, 12.5))
    scene.camera = camera
    bpy.context.view_layer.update()

    key_data = bpy.data.lights.new("key_area", type="AREA")
    key_data.energy = 1500.0
    key_data.shape = "DISK"
    key_data.size = 125.0
    key = bpy.data.objects.new("key_area", key_data)
    scene.collection.objects.link(key)
    key.location = (85.0, -80.0, 175.0)
    look_at(key, (0.0, 0.0, 13.0))
    fill_data = bpy.data.lights.new("fill_area", type="AREA")
    fill_data.energy = 1000.0
    fill_data.size = 110.0
    fill = bpy.data.objects.new("fill_area", fill_data)
    scene.collection.objects.link(fill)
    fill.location = (-120.0, 95.0, 130.0)
    look_at(fill, (0.0, 0.0, 12.0))

    package = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    package_bounds = [-package[0] / 2.0, -package[1] / 2.0, 0.0, package[0] / 2.0, package[1] / 2.0, package[2]]
    frame = framing_bounds(scene, camera, package_bounds)
    package_center = Vector((0.0, 0.0, package[2] / 2.0))
    camera_forward = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    camera_front_facing = camera_forward.dot(package_center - camera.location) > 0.0
    camera_frame_ok = frame[0] >= 0.02 and frame[1] >= 0.02 and frame[2] <= 0.98 and frame[3] <= 0.98 and camera_front_facing

    export_objects = [obj for obj in [tray, lid, board, *component_objects, *overlays] if obj.type == "MESH"]
    assignments = {obj.name: [slot.material.name for slot in obj.material_slots if slot.material] for obj in export_objects}
    mesh_qc = {
        "missing_material_slots": sum(1 for names in assignments.values() if not names),
        "nonmanifold_edges": sum(nonmanifold_edge_count(obj) for obj in export_objects),
        "unclassified_objects": len(unclassified),
        "unlabeled_overlays": sum(1 for obj in overlays if not obj.get("reference")),
        "unlabeled_keepouts": sum(1 for obj in overlays if not obj.get("reference")),
    }
    role_counts = {
        "tray": 1, "lid": 1, "pcb": 1, "component": len(component_objects),
        "access_overlay": len(ACCESS_REFS), "antenna_volume_overlay": 1,
    }
    roles_ok = role_counts == {
        "tray": 1, "lid": 1, "pcb": 1, "component": 5,
        "access_overlay": 2, "antenna_volume_overlay": 1,
    }
    overlays_ok = len(overlays) == 3 and {str(obj["reference"]) for obj in overlays} == {"A1", "J1", "TP1"}
    overlay_materials_ok = len({*overlay_materials.values(), "keepout_warning"}) == 3
    antenna_expected = [float(value) for value in requirements["antenna_keepout"]["bbox_mm"]]
    antenna_overlay_matches = bounds_error(antenna_bounds, antenna_expected) <= float(requirements["geometry_tolerance_mm"])
    antenna_non_occluded = not antenna_overlay.hide_render and not antenna_overlay.hide_viewport
    decision = (
        "pass" if report.get("decision") == "pass" and roles_ok and overlays_ok and overlay_materials_ok
        and antenna_overlay_matches and antenna_non_occluded and camera_frame_ok
        and all(value == 0 for value in mesh_qc.values()) else "fail"
    )
    scene["engiworld_task"] = TASK
    scene["release_decision"] = decision
    scene["freecad_decision"] = str(report.get("decision", "missing"))
    scene["required_roles_present"] = roles_ok
    scene["required_overlays_present"] = overlays_ok
    scene["antenna_overlay_matches_contract"] = antenna_overlay_matches
    scene["antenna_volume_non_occluded"] = antenna_non_occluded
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
        "antenna_keepout_overlay": antenna_overlay.name,
        "antenna_overlay_bounds_mm": antenna_bounds,
        "antenna_overlay_matches_contract": antenna_overlay_matches,
        "antenna_volume_non_occluded": antenna_non_occluded,
        "inputs": ["03_freecad_assembly.obj", "03_freecad_clearance_report.json", "mechanical_requirements.json", "connector_keepouts.csv"],
        "label_names": [obj.name for obj in labels],
        "material_assignments": assignments,
        "materials": sorted({name for values in assignments.values() for name in values}),
        "mesh_qc": mesh_qc,
        "metrics_source": "03_freecad_clearance_report.json",
        "native_scene": "04_blender_review.blend",
        "object_roles": {obj.name: obj.get("engiworld_role", "") for obj in export_objects},
        "overlay_geometry": overlay_geometry,
        "overlay_materials": {
            **{f"{ref}_{directions[ref]}": overlay_materials[ref] for ref in ACCESS_REFS},
            "A1_Z_PLUS": "keepout_warning",
        },
        "real_object_roles": {obj.name: obj.get("engiworld_role", "") for obj in [tray, lid, board, *component_objects]},
        "render": "04_blender_review.png",
        "review_mtl": "04_blender_review.mtl",
        "review_obj": "04_blender_review.obj",
        "role_counts": role_counts,
        "role_references": {"access_overlay": list(ACCESS_REFS), "antenna_volume_overlay": ["A1"], "component": list(COMPONENT_REFS)},
        "software_stage": "Blender",
        "task": TASK,
        "visible_accesses": [f"{ref}_{directions[ref]}" for ref in ACCESS_REFS],
        "visible_features": ["A1_Z_PLUS_reserved_volume", "J1_X_PLUS_window", "TP1_Z_PLUS_bore"],
        "visible_keepouts": ["A1", "J1", "TP1"],
        "visible_overlays": [obj.name for obj in overlays],
    }
    json_dump(work / "04_blender_scene_report.json", report_out)
    if decision != "pass":
        raise RuntimeError(
            f"task-10 Blender contract failed: roles={role_counts}, overlays={len(overlays)}, "
            f"antenna_visibility={antenna_non_occluded}, antenna_match={antenna_overlay_matches}, mesh_qc={mesh_qc}, frame={frame}, "
            f"front={camera_front_facing}, freecad={report.get('decision')!r}"
        )


if __name__ == "__main__":
    main()
