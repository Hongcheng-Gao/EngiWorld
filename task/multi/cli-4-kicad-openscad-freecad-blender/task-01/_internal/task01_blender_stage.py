#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0, alpha: float = 1.0) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    node = value.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = color
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = 0.36
    node.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        value.surface_render_method = "DITHERED"
    return value


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def create_box(name: str, bounds: list[float], mat: bpy.types.Material, collection: bpy.types.Collection, role: str, ref: str) -> bpy.types.Object:
    xmin, ymin, zmin, xmax, ymax, zmax = (float(value) for value in bounds)
    bpy.ops.mesh.primitive_cube_add(
        location=((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0),
        scale=((xmax - xmin) / 2.0, (ymax - ymin) / 2.0, (zmax - zmin) / 2.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj["engiworld_role"] = role
    obj["reference"] = ref
    obj.display_type = "WIRE"
    obj.show_in_front = True
    move_to_collection(obj, collection)
    return obj


def add_label(
    text: str,
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
    mat: bpy.types.Material,
    size: float = 2.3,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=location)
    obj = bpy.context.object
    obj.name = "Label_" + text.replace(" ", "_")
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.05
    obj.data.materials.append(mat)
    move_to_collection(obj, collection)
    return obj


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def nonmanifold_edge_count(obj: bpy.types.Object) -> int:
    if obj.type != "MESH":
        return 0
    return sum(1 for edge in obj.data.edges if len(edge.link_faces) != 2) if hasattr(obj.data.edges[0] if obj.data.edges else None, "link_faces") else 0


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    work = Path(argv[0] if argv else ".").resolve()
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(
        filepath=str(work / "03_freecad_assembly_for_blender.obj"),
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
    )
    imported = list(bpy.context.selected_objects)
    if len(imported) < 3:
        raise RuntimeError(f"FreeCAD OBJ handoff imported only {len(imported)} objects")

    collections = {
        name: bpy.data.collections.new(name)
        for name in ["KiCad_board", "OpenSCAD_enclosure", "FreeCAD_components", "FreeCAD_clearance_overlays", "critical_keepouts"]
    }
    for collection in collections.values():
        bpy.context.scene.collection.children.link(collection)

    mats = {
        "enclosure_translucent": material("enclosure_translucent", (0.20, 0.58, 0.88, 0.18), metallic=0.05, alpha=0.18),
        "pcb_green": material("pcb_green", (0.025, 0.48, 0.12, 1.0), metallic=0.08),
        "component_neutral": material("component_neutral", (0.46, 0.50, 0.56, 1.0), metallic=0.2),
        "keepout_warning": material("keepout_warning", (1.0, 0.08, 0.015, 0.88), metallic=0.0, alpha=0.88),
        "clearance_ok": material("clearance_ok", (0.0, 0.95, 0.80, 0.82), metallic=0.0, alpha=0.82),
    }
    for key, strength in [("keepout_warning", 3.0), ("clearance_ok", 2.0)]:
        node = mats[key].node_tree.nodes["Principled BSDF"]
        node.inputs["Emission Color"].default_value = mats[key].diffuse_color
        node.inputs["Emission Strength"].default_value = strength

    role_counts = {"enclosure": 0, "pcb": 0, "component_envelope": 0}
    for obj in imported:
        normalized = obj.name.upper().replace(" ", "_")
        if "OPENSCAD" in normalized or "ENCLOSURE" in normalized:
            role = "enclosure"
            target = collections["OpenSCAD_enclosure"]
            mat = mats["enclosure_translucent"]
        elif "KICAD" in normalized or "BOARD" in normalized or "PCB" in normalized:
            role = "pcb"
            target = collections["KiCad_board"]
            mat = mats["pcb_green"]
        else:
            role = "component_envelope"
            target = collections["FreeCAD_components"]
            mat = mats["component_neutral"]
        obj["engiworld_role"] = role
        role_counts[role] += 1
        if obj.type == "MESH":
            obj.data.materials.clear()
            obj.data.materials.append(mat)
        move_to_collection(obj, target)

    overlays = []
    labels = []
    for aperture in params["apertures"]:
        overlay = create_box(
            f"{aperture['ref']}_{aperture['wall_direction']}_Aperture_Overlay",
            aperture["bounds_mm"],
            mats["keepout_warning"],
            collections["critical_keepouts"],
            "window_overlay",
            aperture["ref"],
        )
        overlays.append(overlay)
        if aperture["ref"] == "J1":
            label_location = (-48.0, -16.0, 18.0)
        else:
            y = float(aperture["centerline_xy_mm"][1])
            x = -38.0 if aperture["wall_direction"] == "X_MINUS" else 38.0
            label_location = (x, y, 16.6)
        labels.append(add_label(f"{aperture['ref']} {aperture['wall_direction']}", label_location, collections["critical_keepouts"], mats["keepout_warning"]))

    u1 = next(item for item in json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))["components"] if item["ref"] == "U1")
    u1_top = float(params["board_top_z_mm"]) + float(u1["height_mm"])
    lid_inner = float(params["lid_inner_z_mm"])
    clearance_overlay = create_box(
        "U1_Lid_Clearance_Overlay",
        [float(u1["x_mm"]) - 1.0, float(u1["y_mm"]) - 1.0, u1_top, float(u1["x_mm"]) + 1.0, float(u1["y_mm"]) + 1.0, lid_inner],
        mats["clearance_ok"],
        collections["FreeCAD_clearance_overlays"],
        "clearance_overlay",
        "U1",
    )
    clearance_overlay["measured_clearance_mm"] = float(report["u1_lid_clearance_mm"])
    labels.append(add_label(f"U1 CLEARANCE {report['u1_lid_clearance_mm']:.1f} mm", (-8.0, 8.0, 17.4), collections["FreeCAD_clearance_overlays"], mats["clearance_ok"], size=2.6))

    bpy.ops.object.camera_add(location=(112.0, -116.0, 92.0))
    camera = bpy.context.object
    camera.name = "release_review_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 135.0
    look_at(camera, (0.0, 0.0, 8.5))
    bpy.context.scene.camera = camera
    for label in labels:
        label.rotation_euler = (camera.location - label.location).to_track_quat("Z", "Y").to_euler()

    for name, location, energy, size in [
        ("Key_Area", (35.0, -30.0, 100.0), 2600.0, 65.0),
        ("Fill_Area", (-65.0, 40.0, 60.0), 1800.0, 50.0),
    ]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, (0.0, 0.0, 8.0))

    scene = bpy.context.scene
    scene["engiworld_task"] = "task-01"
    scene["release_decision"] = report["decision"]
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(work / "04_blender_review.png")
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 1.4
    world = bpy.data.worlds.new("Task01_ReviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.08, 0.10, 0.13, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    scene.world = world

    blend_path = work / "04_blender_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    bpy.ops.render.render(write_still=True)

    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
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

    material_assignments = {
        obj.name: [slot.material.name for slot in obj.material_slots if slot.material]
        for obj in export_objects
    }
    required_roles = role_counts["enclosure"] >= 1 and role_counts["pcb"] >= 1 and role_counts["component_envelope"] >= 1
    required_overlays = len(overlays) == 2 and clearance_overlay is not None
    decision = "pass" if report["decision"] == "pass" and required_roles and required_overlays else "fail"
    scene_report = {
        "active_camera": camera.name,
        "collections": sorted(collections),
        "decision": decision,
        "inputs": ["03_freecad_assembly_for_blender.obj", "03_freecad_clearance_report.json"],
        "material_assignments": material_assignments,
        "materials": sorted(mats),
        "native_scene": "04_blender_review.blend",
        "object_roles": {obj.name: obj.get("engiworld_role", "") for obj in export_objects},
        "render": "04_blender_review.png",
        "review_mtl": "04_blender_review.mtl",
        "review_obj": "04_blender_review.obj",
        "role_counts": role_counts,
        "software_stage": "Blender",
        "task": "task-01",
        "visible_keepouts": ["J1", "J2"],
        "visible_u1_clearance_mm": float(report["u1_lid_clearance_mm"]),
    }
    json_dump(work / "04_blender_scene_report.json", scene_report)
    if decision != "pass":
        raise RuntimeError("task-01 Blender scene contract failed")


if __name__ == "__main__":
    main()
