#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector


TASK = "task-03"
REQUIRED_METRICS = [
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "shield_volume_mm3",
    "shield_mass_g",
    "minimum_side_clearance_mm",
    "u1_keepout_contained",
    "j1_protected_volume_intersection_mm3",
    "j1_protected_volume_separation_mm",
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
    alpha: float = 1.0,
    emission: float = 0.0,
) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    node = value.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = color
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = 0.34
    node.inputs["Alpha"].default_value = alpha
    if emission > 0.0:
        node.inputs["Emission Color"].default_value = color
        node.inputs["Emission Strength"].default_value = emission
    if alpha < 1.0:
        value.surface_render_method = "DITHERED"
    return value


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def create_box(
    name: str,
    bounds: list[float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    role: str,
    ref: str,
) -> bpy.types.Object:
    xmin, ymin, zmin, xmax, ymax, zmax = (float(value) for value in bounds)
    if xmax <= xmin or ymax <= ymin or zmax <= zmin:
        raise ValueError(f"invalid bounds for {name}: {bounds}")
    bpy.ops.mesh.primitive_cube_add(
        location=((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0),
        scale=((xmax - xmin) / 2.0, (ymax - ymin) / 2.0, (zmax - zmin) / 2.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj["engiworld_role"] = role
    obj["reference"] = ref
    obj["source"] = "FreeCAD geometry report or authoritative handoff parameters"
    obj.show_in_front = True
    move_to_collection(obj, collection)
    return obj


def create_cylinder(
    name: str,
    volume: list[float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    role: str,
    ref: str,
) -> bpy.types.Object:
    x, y, radius, zmin, zmax = (float(value) for value in volume)
    if radius <= 0.0 or zmax <= zmin:
        raise ValueError(f"invalid cylinder for {name}: {volume}")
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=radius,
        depth=zmax - zmin,
        location=(x, y, (zmin + zmax) / 2.0),
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    obj["engiworld_role"] = role
    obj["reference"] = ref
    obj["source"] = "FreeCAD geometry report or authoritative handoff parameters"
    obj.show_in_front = True
    move_to_collection(obj, collection)
    return obj


def add_label(
    text: str,
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
    mat: bpy.types.Material,
    size: float = 1.8,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=location)
    obj = bpy.context.object
    obj.name = "Label_" + text.replace(" ", "_")
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.04
    obj.data.materials.append(mat)
    move_to_collection(obj, collection)
    return obj


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def normalize(value: object) -> str:
    return "_".join(str(value).upper().replace(".", "_").replace("-", "_").split())


def canonical_role(value: object) -> str | None:
    role = normalize(value)
    if any(token in role for token in ("PACKAGE", "ENCLOSURE", "SHELL", "HOUSING")):
        return "package"
    if any(token in role for token in ("SHIELD", "RF_CAN", "SHIELDCAN")):
        return "shield"
    if any(token in role for token in ("PCB", "BOARD", "KICAD")):
        return "pcb"
    if any(token in role for token in ("COMPONENT", "PART", "DEVICE")):
        return "component"
    return None


def report_role_hints(report: dict[str, Any]) -> dict[str, str]:
    hints: dict[str, str] = {}
    raw = report.get("object_roles", {})
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, str):
                role = canonical_role(value)
                if role:
                    hints[normalize(key)] = role
            elif isinstance(value, dict):
                role = canonical_role(value.get("role"))
                name = value.get("name", key)
                if role:
                    hints[normalize(name)] = role
            elif isinstance(value, list):
                role = canonical_role(key)
                if role:
                    for name in value:
                        if isinstance(name, str):
                            hints[normalize(name)] = role
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                role = canonical_role(item.get("role"))
                name = item.get("name") or item.get("object")
                if role and name:
                    hints[normalize(name)] = role
    return hints


def classify_object(
    name: str,
    hints: dict[str, str],
    component_refs: set[str],
) -> tuple[str, str]:
    normalized = normalize(name)
    for hinted_name, hinted_role in hints.items():
        if normalized == hinted_name or normalized.startswith(hinted_name + "_"):
            return hinted_role, "freecad_report"
    if any(token in normalized for token in ("PROTECTED_VOLUME", "KEEPOUT", "ACCESS")):
        return "source_overlay", "freecad_validation_object"
    heuristic = canonical_role(normalized)
    if heuristic:
        return heuristic, "object_name"
    if any(
        normalized == ref
        or normalized.startswith(ref + "_")
        or normalized.endswith("_" + ref)
        or ("COMPONENT" in normalized and ref in normalized.split("_"))
        for ref in component_refs
    ):
        return "component", "kicad_reference"
    return "unclassified", "unclassified"


def coerce_bounds(value: object) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 6:
        try:
            result = [float(item) for item in value]
        except (TypeError, ValueError):
            return None
        if result[3] > result[0] and result[4] > result[1] and result[5] > result[2]:
            return result
    if isinstance(value, dict):
        for key in ("bounds_mm", "cut_bounds_mm", "opening_bounds_mm", "volume_bounds_mm", "bbox_mm"):
            result = coerce_bounds(value.get(key))
            if result:
                return result
        keys = ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax")
        if all(key in value for key in keys):
            return coerce_bounds([value[key] for key in keys])
    return None


def coerce_cylinder(value: object) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 5:
        try:
            result = [float(item) for item in value]
        except (TypeError, ValueError):
            return None
        if result[2] > 0.0 and result[4] > result[3]:
            return result
    if isinstance(value, dict):
        for key in ("volume_mm", "cylinder_mm", "keepout_volume_mm", "bore_volume_mm"):
            result = coerce_cylinder(value.get(key))
            if result:
                return result
        required = ("x_mm", "y_mm", "radius_mm", "z_min_mm", "z_max_mm")
        if all(key in value for key in required):
            return coerce_cylinder([value[key] for key in required])
    return None


def access_entry(report: dict[str, Any], ref: str) -> dict[str, Any]:
    raw = report.get("access_checks", {})
    if isinstance(raw, dict):
        item = raw.get(ref)
        if isinstance(item, dict):
            return item
        for key, value in raw.items():
            if normalize(key) == ref and isinstance(value, dict):
                return value
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and normalize(item.get("ref")) == ref:
                return item
    return {}


def protected_bounds(
    report: dict[str, Any],
    requirements: dict[str, Any],
    components: dict[str, dict[str, Any]],
    board_top_z: float,
) -> list[float]:
    for key in ("protected_volume_bounds_mm", "protected_volume"):
        bounds = coerce_bounds(report.get(key))
        if bounds:
            return bounds
    protected = requirements["protected_volume"]
    center = components[str(protected["center_ref"])]
    width, height = (float(value) for value in protected["inner_bbox_xy_mm"])
    x = float(center["x_mm"])
    y = float(center["y_mm"])
    return [x - width / 2.0, y - height / 2.0, board_top_z, x + width / 2.0, y + height / 2.0, float(protected["z_max_mm"])]


def keepout_volume(
    report: dict[str, Any],
    ref: str,
    component: dict[str, Any],
    board_top_z: float,
) -> list[float]:
    for key in ("keepout_volumes", "component_metrics", "components"):
        raw = report.get(key)
        if isinstance(raw, dict):
            volume = coerce_cylinder(raw.get(ref))
            if volume:
                return volume
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and normalize(item.get("ref")) == ref:
                    volume = coerce_cylinder(item)
                    if volume:
                        return volume
    return [
        float(component["x_mm"]),
        float(component["y_mm"]),
        float(component["keepout_radius_mm"]),
        board_top_z,
        board_top_z + float(component["height_mm"]),
    ]


def fallback_access_bounds(
    ref: str,
    connector: dict[str, str],
    component: dict[str, Any],
    enclosure_bbox: list[float],
    board_top_z: float,
    requirements: dict[str, Any],
) -> list[float]:
    direction = connector["direction"]
    overcut = float(requirements["access_overcut_mm"])
    wall = float(requirements["wall_mm"])
    half_x = float(enclosure_bbox[0]) / 2.0
    half_y = float(enclosure_bbox[1]) / 2.0
    width = float(connector["finished_width_mm"])
    height = float(connector["finished_height_mm"])
    margin = float(connector["vertical_margin_mm"])
    x = float(component["x_mm"])
    y = float(component["y_mm"])
    zmin = board_top_z - margin
    zmax = board_top_z + float(component["height_mm"]) + margin
    if direction == "X_PLUS":
        return [half_x - wall - overcut, y - width / 2.0, zmin, half_x + overcut, y + width / 2.0, zmax]
    if direction == "X_MINUS":
        return [-half_x - overcut, y - width / 2.0, zmin, -half_x + wall + overcut, y + width / 2.0, zmax]
    if direction == "Y_PLUS":
        return [x - width / 2.0, half_y - wall - overcut, zmin, x + width / 2.0, half_y + overcut, zmax]
    if direction == "Y_MINUS":
        return [x - width / 2.0, -half_y - overcut, zmin, x + width / 2.0, -half_y + wall + overcut, zmax]
    raise ValueError(f"{ref} is not a side access: {direction}")


def fallback_bore_volume(
    connector: dict[str, str],
    component: dict[str, Any],
    enclosure_bbox: list[float],
    requirements: dict[str, Any],
) -> list[float]:
    diameter = float(connector["finished_diameter_mm"])
    overcut = float(requirements["access_overcut_mm"])
    lid = float(requirements["lid_thickness_mm"])
    top = float(enclosure_bbox[2])
    return [
        float(component["x_mm"]),
        float(component["y_mm"]),
        diameter / 2.0,
        top - lid - overcut,
        top + overcut,
    ]


def nonmanifold_edge_count(obj: bpy.types.Object) -> int:
    if obj.type != "MESH":
        return 0
    mesh = bmesh.new()
    try:
        mesh.from_mesh(obj.data)
        return sum(1 for edge in mesh.edges if not edge.is_manifold)
    finally:
        mesh.free()


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    work = Path(argv[0] if argv else ".").resolve()
    report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    params = json.loads((work / "02_openscad_parameters.json").read_text(encoding="utf-8"))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    kicad = json.loads((work / "01_kicad_export.json").read_text(encoding="utf-8"))
    components = {str(item["ref"]): item for item in kicad["components"]}

    import csv

    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connectors = {row["ref"]: row for row in csv.DictReader(handle)}

    missing_metrics = [key for key in REQUIRED_METRICS if key not in report]
    if missing_metrics:
        raise RuntimeError("FreeCAD report is missing metrics: " + ", ".join(missing_metrics))

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

    collections = {
        name: bpy.data.collections.new(name)
        for name in [
            "KiCad_board",
            "OpenSCAD_package",
            "FreeCAD_shield",
            "FreeCAD_components",
            "FreeCAD_clearance_overlays",
            "critical_keepouts",
        ]
    }
    for collection in collections.values():
        bpy.context.scene.collection.children.link(collection)

    mats = {
        "package_translucent": material("package_translucent", (0.10, 0.32, 0.47, 0.28), alpha=0.28),
        "shield_steel": material("shield_steel", (0.62, 0.67, 0.72, 1.0), metallic=0.9),
        "pcb_green": material("pcb_green", (0.03, 0.38, 0.12, 1.0), metallic=0.05),
        "component_neutral": material("component_neutral", (0.33, 0.36, 0.40, 1.0), metallic=0.18),
        "source_overlay_neutral": material("source_overlay_neutral", (0.45, 0.48, 0.52, 0.18), alpha=0.18),
        "unclassified_magenta": material("unclassified_magenta", (0.70, 0.05, 0.40, 1.0), emission=0.5),
        "protected_volume_blue": material("protected_volume_blue", (0.05, 0.55, 1.0, 0.22), alpha=0.22, emission=0.4),
        "u1_inclusion_green": material("u1_inclusion_green", (0.05, 0.95, 0.24, 0.72), alpha=0.72, emission=1.6),
        "j1_exclusion_red": material("j1_exclusion_red", (1.0, 0.04, 0.02, 0.72), alpha=0.72, emission=1.8),
        "j1_access_orange": material("j1_access_orange", (1.0, 0.30, 0.01, 0.78), alpha=0.78, emission=1.6),
        "j2_access_yellow": material("j2_access_yellow", (1.0, 0.88, 0.03, 0.78), alpha=0.78, emission=1.4),
        "tp1_bore_cyan": material("tp1_bore_cyan", (0.02, 0.95, 0.95, 0.78), alpha=0.78, emission=1.6),
    }

    role_hints = report_role_hints(report)
    role_counts = {
        "package": 0,
        "shield": 0,
        "pcb": 0,
        "component": 0,
        "source_overlay": 0,
        "unclassified": 0,
    }
    role_sources: dict[str, str] = {}
    role_targets = {
        "package": (collections["OpenSCAD_package"], mats["package_translucent"]),
        "shield": (collections["FreeCAD_shield"], mats["shield_steel"]),
        "pcb": (collections["KiCad_board"], mats["pcb_green"]),
        "component": (collections["FreeCAD_components"], mats["component_neutral"]),
        "source_overlay": (collections["FreeCAD_clearance_overlays"], mats["source_overlay_neutral"]),
        "unclassified": (collections["FreeCAD_components"], mats["unclassified_magenta"]),
    }
    for obj in imported:
        role, source = classify_object(obj.name, role_hints, set(components))
        target, mat = role_targets[role]
        obj["engiworld_role"] = role
        obj["role_source"] = source
        role_counts[role] += 1
        role_sources[obj.name] = source
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        if role == "source_overlay":
            obj.hide_render = True
        move_to_collection(obj, target)

    board_bbox = [float(value) for value in kicad["board_bbox_mm"]]
    board_bottom_z = float(requirements["board_bottom_z_mm"])
    board_top_z = board_bottom_z + board_bbox[2]
    enclosure_bbox = [float(value) for value in report.get("enclosure_bbox_mm", params["enclosure_bbox_mm"])]
    protected = protected_bounds(report, requirements, components, board_top_z)

    overlays: list[bpy.types.Object] = []
    overlay_specs: list[tuple[str, str, str]] = []
    protected_obj = create_box(
        "Protected_Volume_U1",
        protected,
        mats["protected_volume_blue"],
        collections["FreeCAD_clearance_overlays"],
        "protected_volume_overlay",
        "U1",
    )
    overlays.append(protected_obj)
    overlay_specs.append((protected_obj.name, "protected_volume", mats["protected_volume_blue"].name))

    for ref, name, material_name, role in [
        ("U1", "U1_Keepout_Inclusion", "u1_inclusion_green", "contained_keepout_overlay"),
        ("J1", "J1_Keepout_Exclusion", "j1_exclusion_red", "excluded_keepout_overlay"),
    ]:
        obj = create_cylinder(
            name,
            keepout_volume(report, ref, components[ref], board_top_z),
            mats[material_name],
            collections["critical_keepouts"],
            role,
            ref,
        )
        overlays.append(obj)
        overlay_specs.append((obj.name, role, mats[material_name].name))

    for ref, name, material_name in [
        ("J1", "J1_X_PLUS_Access", "j1_access_orange"),
        ("J2", "J2_X_MINUS_Access", "j2_access_yellow"),
    ]:
        entry = access_entry(report, ref)
        bounds = coerce_bounds(entry) or fallback_access_bounds(
            ref,
            connectors[ref],
            components[ref],
            enclosure_bbox,
            board_top_z,
            requirements,
        )
        obj = create_box(
            name,
            bounds,
            mats[material_name],
            collections["critical_keepouts"],
            "access_overlay",
            ref,
        )
        obj["access_direction"] = connectors[ref]["direction"]
        overlays.append(obj)
        overlay_specs.append((obj.name, "access_overlay", mats[material_name].name))

    tp1_entry = access_entry(report, "TP1")
    tp1_volume = coerce_cylinder(tp1_entry) or fallback_bore_volume(
        connectors["TP1"],
        components["TP1"],
        enclosure_bbox,
        requirements,
    )
    tp1_obj = create_cylinder(
        "TP1_Z_PLUS_Lid_Bore",
        tp1_volume,
        mats["tp1_bore_cyan"],
        collections["critical_keepouts"],
        "access_overlay",
        "TP1",
    )
    tp1_obj["access_direction"] = connectors["TP1"]["direction"]
    overlays.append(tp1_obj)
    overlay_specs.append((tp1_obj.name, "access_overlay", mats["tp1_bore_cyan"].name))

    label_specs = [
        ("PROTECTED VOLUME", (-14.0, 9.0, 25.0), mats["protected_volume_blue"]),
        ("U1 INSIDE", (8.0, -2.0, 21.0), mats["u1_inclusion_green"]),
        ("J1 OUTSIDE", (25.0, 10.0, 25.0), mats["j1_exclusion_red"]),
        ("J1 X+ WINDOW", (54.0, -5.0, 19.0), mats["j1_access_orange"]),
        ("J2 X- WINDOW", (-42.0, -25.0, 20.0), mats["j2_access_yellow"]),
        ("TP1 TOP BORE", (8.0, -25.0, 23.0), mats["tp1_bore_cyan"]),
    ]
    labels = [
        add_label(text, location, collections["critical_keepouts"], mat, size=1.7)
        for text, location, mat in label_specs
    ]

    bpy.ops.object.camera_add(location=(104.0, -116.0, 86.0))
    camera = bpy.context.object
    camera.name = "release_review_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 118.0
    look_at(camera, (0.0, 0.0, 6.0))
    bpy.context.scene.camera = camera
    for label in labels:
        label.rotation_euler = (camera.location - label.location).to_track_quat("Z", "Y").to_euler()

    for name, location, energy, size in [
        ("Key_Area", (40.0, -35.0, 90.0), 2200.0, 60.0),
        ("Fill_Area", (-55.0, 35.0, 65.0), 1600.0, 48.0),
        ("Rim_Area", (0.0, 55.0, 40.0), 1100.0, 38.0),
    ]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, (0.0, 0.0, 6.0))

    required_roles_present = all(role_counts[role] >= 1 for role in ("package", "shield", "pcb", "component"))
    required_overlay_roles = {
        "protected_volume_overlay",
        "contained_keepout_overlay",
        "excluded_keepout_overlay",
    }
    overlay_roles = {str(obj.get("engiworld_role", "")) for obj in overlays}
    overlay_refs = {str(obj.get("reference", "")) for obj in overlays}
    required_overlays_present = (
        len(overlays) == 6
        and required_overlay_roles.issubset(overlay_roles)
        and {"U1", "J1", "J2", "TP1"}.issubset(overlay_refs)
    )
    decision = "pass" if report.get("decision") == "pass" and required_roles_present and required_overlays_present else "fail"

    scene = bpy.context.scene
    scene["engiworld_task"] = TASK
    scene["release_decision"] = decision
    scene["freecad_decision"] = str(report.get("decision", "missing"))
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(work / "04_blender_review.png")
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 1.1
    world = bpy.data.worlds.new("Task03_ReviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035, 0.045, 0.055, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.75
    scene.world = world

    blend_path = work / "04_blender_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    bpy.ops.render.render(write_still=True)

    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [obj for obj in scene.objects if obj.type == "MESH"]
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
    mesh_qc = {
        "missing_material_slots": sum(1 for obj in export_objects if not material_assignments[obj.name]),
        "nonmanifold_edges": sum(nonmanifold_edge_count(obj) for obj in export_objects),
        "unlabeled_overlays": sum(1 for obj in overlays if not obj.get("reference")),
    }
    copied_metrics = {key: report[key] for key in REQUIRED_METRICS}
    scene_report = {
        "active_camera": camera.name,
        "camera": {
            "location_mm": [round(float(value), 6) for value in camera.location],
            "name": camera.name,
            "ortho_scale_mm": float(camera.data.ortho_scale),
            "projection": "orthographic",
            "view": "top_oblique",
        },
        "collections": sorted(collections),
        "decision": decision,
        "freecad_metrics": copied_metrics,
        "inputs": ["03_freecad_assembly.obj", "03_freecad_clearance_report.json"],
        "material_assignments": material_assignments,
        "materials": sorted(mats),
        "mesh_qc": mesh_qc,
        "metrics_source": "03_freecad_clearance_report.json",
        "native_scene": "04_blender_review.blend",
        "object_roles": {obj.name: obj.get("engiworld_role", "") for obj in export_objects},
        "overlay_materials": {name: mat for name, _role, mat in overlay_specs},
        "real_object_roles": {obj.name: obj.get("engiworld_role", "") for obj in imported},
        "render": "04_blender_review.png",
        "review_mtl": "04_blender_review.mtl",
        "review_obj": "04_blender_review.obj",
        "role_counts": {**role_counts, "enclosure": role_counts["package"]},
        "role_sources": role_sources,
        "software_stage": "Blender",
        "task": TASK,
        "visible_features": [
            "protected_volume",
            "U1_inclusion",
            "J1_exclusion",
            "J1_X_PLUS_access",
            "J2_X_MINUS_access",
            "TP1_Z_PLUS_lid_bore",
        ],
        "visible_keepouts": ["U1", "J1", "J2", "TP1"],
        "visible_overlays": [obj.name for obj in overlays],
    }
    json_dump(work / "04_blender_scene_report.json", scene_report)
    if decision != "pass":
        raise RuntimeError(
            f"{TASK} Blender scene contract failed: roles={role_counts}, "
            f"overlay_count={len(overlays)}, freecad_decision={report.get('decision')!r}"
        )


if __name__ == "__main__":
    main()
