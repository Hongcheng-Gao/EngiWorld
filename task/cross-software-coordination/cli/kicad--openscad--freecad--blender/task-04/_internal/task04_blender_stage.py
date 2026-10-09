#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector


TASK = "task-04"
REQUIRED_METRICS = [
    "enclosure_volume_mm3",
    "enclosure_mass_g",
    "minimum_side_clearance_mm",
    "minimum_top_clearance_mm",
    "standoff_checks",
    "rib_checks",
    "access_checks",
    "unintended_interference_volume_mm3",
    "decision",
]
REQUIRED_COMPONENT_REFS = {"Q1", "Q2", "Q3", "J1", "J2"}
REQUIRED_RIB_REFS = {"RIB_NEG_Y", "RIB_POS_Y"}


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize(value: object) -> str:
    return "_".join(str(value).upper().replace(".", "_").replace("-", "_").split())


def material(
    name: str,
    color: tuple[float, float, float, float],
    *,
    metallic: float = 0.0,
    roughness: float = 0.34,
    alpha: float = 1.0,
    emission: float = 0.0,
) -> bpy.types.Material:
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    node = value.node_tree.nodes.get("Principled BSDF")
    if node is None:
        raise RuntimeError(f"material {name} has no Principled BSDF node")
    node.inputs["Base Color"].default_value = color
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    node.inputs["Alpha"].default_value = alpha
    if emission > 0.0:
        emission_color = node.inputs.get("Emission Color") or node.inputs.get("Emission")
        emission_strength = node.inputs.get("Emission Strength")
        if emission_color is not None:
            emission_color.default_value = color
        if emission_strength is not None:
            emission_strength.default_value = emission
    if alpha < 1.0:
        if hasattr(value, "surface_render_method"):
            value.surface_render_method = "DITHERED"
        elif hasattr(value, "blend_method"):
            value.blend_method = "BLEND"
    return value


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def assign_material(obj: bpy.types.Object, value: bpy.types.Material) -> None:
    if obj.type not in {"MESH", "FONT"}:
        return
    obj.data.materials.clear()
    obj.data.materials.append(value)


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
    assign_material(obj, mat)
    obj["engiworld_role"] = role
    obj["reference"] = ref
    obj["source"] = "trusted task-04 geometry contract"
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
    assign_material(obj, mat)
    obj["engiworld_role"] = role
    obj["reference"] = ref
    obj["source"] = "trusted task-04 geometry contract"
    obj.show_in_front = True
    move_to_collection(obj, collection)
    return obj


def create_direction_arrow(
    name: str,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    mat: bpy.types.Material,
    collection: bpy.types.Collection,
    ref: str,
    direction_name: str,
) -> bpy.types.Object:
    start_vec = Vector(start)
    end_vec = Vector(end)
    delta = end_vec - start_vec
    length = delta.length
    if length <= 4.0:
        raise ValueError(f"direction arrow is too short: {name}")
    unit = delta.normalized()
    tip_length = min(3.5, length * 0.3)
    shaft_length = length - tip_length
    rotation = unit.to_track_quat("Z", "Y")

    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=0.72,
        depth=shaft_length,
        location=start_vec + unit * (shaft_length / 2.0),
        rotation=rotation.to_euler(),
    )
    shaft = bpy.context.object
    assign_material(shaft, mat)
    bpy.ops.mesh.primitive_cone_add(
        vertices=32,
        radius1=1.8,
        radius2=0.0,
        depth=tip_length,
        location=end_vec - unit * (tip_length / 2.0),
        rotation=rotation.to_euler(),
    )
    tip = bpy.context.object
    assign_material(tip, mat)

    bpy.ops.object.select_all(action="DESELECT")
    shaft.select_set(True)
    tip.select_set(True)
    bpy.context.view_layer.objects.active = shaft
    bpy.ops.object.join()
    arrow = bpy.context.object
    arrow.name = name
    assign_material(arrow, mat)
    arrow["engiworld_role"] = "access_direction_overlay"
    arrow["reference"] = ref
    arrow["access_direction"] = direction_name
    arrow["source"] = "trusted task-04 access direction"
    arrow.show_in_front = True
    move_to_collection(arrow, collection)
    return arrow


def add_label(
    text: str,
    location: Vector,
    collection: bpy.types.Collection,
    mat: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.object.text_add(location=location)
    obj = bpy.context.object
    obj.name = "Label_" + normalize(text)
    obj.data.body = text
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = 1.85
    obj.data.extrude = 0.035
    assign_material(obj, mat)
    obj["engiworld_role"] = "review_label"
    move_to_collection(obj, collection)
    return obj


def look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


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
    return max(abs(left - right) for left, right in zip(actual, expected))


def canonical_role(value: object) -> str | None:
    role = normalize(value)
    if any(token in role for token in ("KEEPOUT", "ACCESS", "VALIDATION", "OVERLAY")):
        return "source_overlay"
    if "RIB" in role:
        return "rib"
    if any(token in role for token in ("LID", "COVER")):
        return "lid"
    if any(token in role for token in ("TRAY", "BASE", "PACKAGE", "ENCLOSURE", "SHELL", "HOUSING")):
        return "tray"
    if any(token in role for token in ("PCB", "BOARD", "KICAD")):
        return "pcb"
    if any(token in role for token in ("COMPONENT", "PART", "DEVICE", "MOSFET", "TERMINAL", "SENSOR")):
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
            if not isinstance(item, dict):
                continue
            role = canonical_role(item.get("role"))
            name = item.get("name") or item.get("object")
            if role and name:
                hints[normalize(name)] = role
    return hints


def reference_from_name(name: str, refs: set[str]) -> str | None:
    normalized = normalize(name)
    tokens = set(normalized.split("_"))
    for ref in sorted(refs, key=len, reverse=True):
        # FreeCAD's OBJ exporter commonly appends a numeric object suffix, for
        # example Q1 -> Q1001 and RIB_NEG_Y -> RIB_NEG_Y001.
        bounded = re.search(r"(?:^|_)" + re.escape(ref) + r"(?:_|\d*$)", normalized)
        if normalized == ref or ref in tokens or normalized.startswith(ref + "_") or normalized.endswith("_" + ref) or bounded:
            return ref
    return None


def load_components(
    work: Path,
    report: dict[str, Any],
    requirements: dict[str, Any],
) -> tuple[dict[str, dict[str, float]], list[float]]:
    components: dict[str, dict[str, float]] = {}
    board_bbox = [float(value) for value in report.get("board_bbox_mm", [128.0, 86.0, 1.6])]
    export_path = work / "01_kicad_export.json"
    if export_path.is_file():
        export = json.loads(export_path.read_text(encoding="utf-8"))
        board_bbox = [float(value) for value in export.get("board_bbox_mm", board_bbox)]
        for item in export.get("components", []):
            if not isinstance(item, dict) or "ref" not in item:
                continue
            ref = normalize(item["ref"])
            components[ref] = {
                key: float(item[key])
                for key in ("x_mm", "y_mm", "height_mm", "keepout_radius_mm")
                if key in item
            }

    map_path = work / "01_kicad_mechanical_map.csv"
    if map_path.is_file():
        with map_path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                ref = normalize(row.get("ref", ""))
                if ref not in REQUIRED_COMPONENT_REFS:
                    continue
                values = components.setdefault(ref, {})
                for key in ("x_mm", "y_mm", "height_mm", "keepout_radius_mm"):
                    if row.get(key) not in (None, ""):
                        values.setdefault(key, float(row[key]))

    keepouts = report.get("keepout_volumes", {})
    if isinstance(keepouts, dict):
        for raw_ref, raw in keepouts.items():
            ref = normalize(raw_ref)
            if ref not in REQUIRED_COMPONENT_REFS or not isinstance(raw, dict):
                continue
            values = components.setdefault(ref, {})
            aliases = {
                "x_mm": ("x_mm", "x"),
                "y_mm": ("y_mm", "y"),
                "keepout_radius_mm": ("radius_mm", "keepout_radius_mm", "radius"),
            }
            for target, source_keys in aliases.items():
                for source in source_keys:
                    if raw.get(source) is not None:
                        values.setdefault(target, float(raw[source]))
                        break

    bodies = requirements.get("component_bodies", {})
    for ref, body in bodies.items():
        canonical = normalize(ref)
        if not isinstance(body, dict):
            continue
        bbox = body.get("bbox_mm")
        if isinstance(bbox, list) and len(bbox) == 3:
            components.setdefault(canonical, {}).setdefault("height_mm", float(bbox[2]))

    missing: list[str] = []
    for ref in sorted(REQUIRED_COMPONENT_REFS):
        required = {"x_mm", "y_mm", "height_mm"}
        if ref.startswith("Q"):
            required.add("keepout_radius_mm")
        absent = sorted(required - set(components.get(ref, {})))
        if absent:
            missing.append(f"{ref} ({', '.join(absent)})")
    if missing:
        raise RuntimeError("cannot locate authoritative component geometry: " + "; ".join(missing))
    return components, board_bbox


def expected_geometry(
    requirements: dict[str, Any],
    components: dict[str, dict[str, float]],
    board_bbox: list[float],
) -> dict[str, list[float]]:
    enclosure = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    half_x = enclosure[0] / 2.0
    half_y = enclosure[1] / 2.0
    board_bottom = float(requirements["board_bottom_z_mm"])
    board_top = board_bottom + board_bbox[2]
    result = {
        "tray": [-half_x, -half_y, 0.0, half_x, half_y, float(requirements["tray_outer_top_z_mm"])],
        "lid": [-half_x, -half_y, float(requirements["lid_inner_z_mm"]), half_x, half_y, enclosure[2]],
        "pcb": [
            -board_bbox[0] / 2.0,
            -board_bbox[1] / 2.0,
            board_bottom,
            board_bbox[0] / 2.0,
            board_bbox[1] / 2.0,
            board_top,
        ],
    }
    for rib in requirements["required_ribs"]:
        result[normalize(rib["id"])] = [float(value) for value in rib["bounds_mm"]]
    for ref, body in requirements["component_bodies"].items():
        canonical = normalize(ref)
        x, y = components[canonical]["x_mm"], components[canonical]["y_mm"]
        dx, dy, dz = (float(value) for value in body["bbox_mm"])
        result[canonical] = [x - dx / 2.0, y - dy / 2.0, board_top, x + dx / 2.0, y + dy / 2.0, board_top + dz]
    return result


def geometric_role(
    bounds: list[float],
    expected: dict[str, list[float]],
    tolerance: float,
) -> tuple[str | None, str | None]:
    matches = sorted(
        ((bounds_error(bounds, candidate), key) for key, candidate in expected.items()),
        key=lambda item: item[0],
    )
    if not matches or matches[0][0] > tolerance:
        return None, None
    key = matches[0][1]
    if key in {"tray", "lid", "pcb"}:
        return key, None
    if key in REQUIRED_RIB_REFS:
        return "rib", key
    if key in REQUIRED_COMPONENT_REFS:
        return "component", key
    return None, None


def classify_object(
    obj: bpy.types.Object,
    hints: dict[str, str],
    expected: dict[str, list[float]],
    tolerance: float,
) -> tuple[str, str, str | None]:
    name = normalize(obj.name)
    all_refs = REQUIRED_COMPONENT_REFS | REQUIRED_RIB_REFS
    ref = reference_from_name(name, all_refs)
    for hinted_name, hinted_role in hints.items():
        if name == hinted_name or name.startswith(hinted_name + "_"):
            return hinted_role, "freecad_report", ref
    named_role = canonical_role(name)
    if named_role:
        return named_role, "object_name", ref
    role, geometry_ref = geometric_role(object_bounds(obj), expected, tolerance)
    if role:
        return role, "world_bounds", geometry_ref or ref
    return "unclassified", "unclassified", ref


def keepout_column(
    ref: str,
    component: dict[str, float],
    requirements: dict[str, Any],
) -> list[float]:
    return [
        component["x_mm"],
        component["y_mm"],
        component["keepout_radius_mm"],
        float(requirements["base_thickness_mm"]),
        float(requirements["lid_inner_z_mm"]),
    ]


def access_bounds(
    connector: dict[str, str],
    component: dict[str, float],
    enclosure_bbox: list[float],
    board_top_z: float,
    requirements: dict[str, Any],
) -> list[float]:
    direction = normalize(connector["direction"])
    overcut = float(requirements["access_overcut_mm"])
    width = float(connector["finished_width_mm"])
    height = float(connector["finished_height_mm"])
    body_x = float(connector["body_x_mm"])
    body_y = float(connector["body_y_mm"])
    x = component["x_mm"]
    y = component["y_mm"]
    z_center = board_top_z + component["height_mm"] / 2.0
    zmin = z_center - height / 2.0
    zmax = z_center + height / 2.0
    half_x = enclosure_bbox[0] / 2.0
    half_y = enclosure_bbox[1] / 2.0
    if direction == "X_PLUS":
        return [x + body_x / 2.0, y - width / 2.0, zmin, half_x + overcut, y + width / 2.0, zmax]
    if direction == "X_MINUS":
        return [-half_x - overcut, y - width / 2.0, zmin, x - body_x / 2.0, y + width / 2.0, zmax]
    if direction == "Y_PLUS":
        return [x - width / 2.0, y + body_y / 2.0, zmin, x + width / 2.0, half_y + overcut, zmax]
    if direction == "Y_MINUS":
        return [x - width / 2.0, -half_y - overcut, zmin, x + width / 2.0, y - body_y / 2.0, zmax]
    raise ValueError(f"unsupported side access direction: {direction}")


def arrow_endpoints(bounds: list[float], direction: str) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    center_y = (ymin + ymax) / 2.0
    center_z = (zmin + zmax) / 2.0
    center_x = (xmin + xmax) / 2.0
    if direction == "X_PLUS":
        return (xmin + 0.8, center_y, center_z), (xmax + 7.0, center_y, center_z)
    if direction == "X_MINUS":
        return (xmax - 0.8, center_y, center_z), (xmin - 7.0, center_y, center_z)
    if direction == "Y_PLUS":
        return (center_x, ymin + 0.8, center_z), (center_x, ymax + 7.0, center_z)
    if direction == "Y_MINUS":
        return (center_x, ymax - 0.8, center_z), (center_x, ymin - 7.0, center_z)
    raise ValueError(f"unsupported arrow direction: {direction}")


def nonmanifold_edge_count(obj: bpy.types.Object) -> int:
    if obj.type != "MESH":
        return 0
    mesh = bmesh.new()
    try:
        mesh.from_mesh(obj.data)
        return sum(1 for edge in mesh.edges if not edge.is_manifold)
    finally:
        mesh.free()


def projected_bounds(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    obj: bpy.types.Object,
) -> list[float]:
    points = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
    return [
        min(point.x for point in points),
        min(point.y for point in points),
        max(point.x for point in points),
        max(point.y for point in points),
    ]


def boxes_overlap(first: list[float], second: list[float], padding: float = 0.004) -> bool:
    return not (
        first[2] + padding <= second[0]
        or second[2] + padding <= first[0]
        or first[3] + padding <= second[1]
        or second[3] + padding <= first[1]
    )


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    work = Path(argv[0] if argv else ".").resolve()
    report = json.loads((work / "03_freecad_clearance_report.json").read_text(encoding="utf-8"))
    requirements = json.loads((work / "mechanical_requirements.json").read_text(encoding="utf-8"))
    with (work / "connector_keepouts.csv").open(newline="", encoding="utf-8") as handle:
        connectors = {normalize(row["ref"]): row for row in csv.DictReader(handle)}

    missing_metrics = [key for key in REQUIRED_METRICS if key not in report]
    if missing_metrics:
        raise RuntimeError("FreeCAD report is missing metrics: " + ", ".join(missing_metrics))
    if set(connectors) != {"J1", "J2"}:
        raise RuntimeError(f"connector contract must contain exactly J1 and J2, got {sorted(connectors)}")

    components, board_bbox = load_components(work, report, requirements)
    enclosure_bbox = [float(value) for value in requirements["expected_enclosure_bbox_mm"]]
    board_top_z = float(requirements["board_bottom_z_mm"]) + board_bbox[2]
    geometry = expected_geometry(requirements, components, board_bbox)
    role_tolerance = max(0.35, float(requirements["geometry_tolerance_mm"]) * 4.0)

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

    collection_names = [
        "KiCad_board",
        "OpenSCAD_tray",
        "OpenSCAD_lid",
        "FreeCAD_components",
        "FreeCAD_ribs",
        "FreeCAD_source_overlays",
        "critical_keepouts",
        "rib_review",
        "access_review",
        "review_labels",
    ]
    collections = {name: bpy.data.collections.new(name) for name in collection_names}
    for collection in collections.values():
        bpy.context.scene.collection.children.link(collection)

    mats = {
        "tray_asa": material("tray_asa", (0.24, 0.34, 0.42, 0.72), roughness=0.48, alpha=0.72),
        "lid_translucent": material("lid_translucent", (0.62, 0.76, 0.82, 0.22), roughness=0.25, alpha=0.22),
        "pcb_green": material("pcb_green", (0.03, 0.34, 0.12, 1.0), metallic=0.06, roughness=0.42),
        "component_neutral": material("component_neutral", (0.35, 0.38, 0.42, 1.0), metallic=0.22),
        "rib_physical": material("rib_physical", (0.52, 0.58, 0.62, 1.0), metallic=0.58),
        "source_overlay_neutral": material("source_overlay_neutral", (0.42, 0.44, 0.47, 0.15), alpha=0.15),
        "unclassified_magenta": material("unclassified_magenta", (0.72, 0.03, 0.42, 1.0), emission=0.7),
        "q1_keepout_red": material("q1_keepout_red", (1.0, 0.05, 0.03, 0.34), alpha=0.34, emission=1.15),
        "q2_keepout_amber": material("q2_keepout_amber", (1.0, 0.54, 0.02, 0.34), alpha=0.34, emission=1.15),
        "q3_keepout_magenta": material("q3_keepout_magenta", (0.95, 0.05, 0.64, 0.34), alpha=0.34, emission=1.15),
        "rib_neg_review_cyan": material("rib_neg_review_cyan", (0.02, 0.88, 0.92, 0.58), alpha=0.58, emission=1.35),
        "rib_pos_review_lime": material("rib_pos_review_lime", (0.45, 0.95, 0.05, 0.58), alpha=0.58, emission=1.35),
        "j1_access_orange": material("j1_access_orange", (1.0, 0.24, 0.01, 0.62), alpha=0.62, emission=1.55),
        "j2_access_blue": material("j2_access_blue", (0.03, 0.42, 1.0, 0.62), alpha=0.62, emission=1.55),
    }

    role_hints = report_role_hints(report)
    role_counts = {role: 0 for role in ("tray", "lid", "pcb", "component", "rib", "source_overlay", "unclassified")}
    role_sources: dict[str, str] = {}
    physical_refs = {"component": set(), "rib": set()}
    role_targets = {
        "tray": (collections["OpenSCAD_tray"], mats["tray_asa"]),
        "lid": (collections["OpenSCAD_lid"], mats["lid_translucent"]),
        "pcb": (collections["KiCad_board"], mats["pcb_green"]),
        "component": (collections["FreeCAD_components"], mats["component_neutral"]),
        "rib": (collections["FreeCAD_ribs"], mats["rib_physical"]),
        "source_overlay": (collections["FreeCAD_source_overlays"], mats["source_overlay_neutral"]),
        "unclassified": (collections["FreeCAD_source_overlays"], mats["unclassified_magenta"]),
    }
    for obj in imported:
        role, source, ref = classify_object(obj, role_hints, geometry, role_tolerance)
        target, mat = role_targets[role]
        obj["engiworld_role"] = role
        obj["role_source"] = source
        if ref:
            obj["reference"] = ref
        role_counts[role] += 1
        role_sources[obj.name] = source
        if role in physical_refs and ref:
            physical_refs[role].add(ref)
        assign_material(obj, mat)
        if role == "source_overlay":
            obj.hide_render = True
        move_to_collection(obj, target)

    overlays: list[bpy.types.Object] = []
    overlay_specs: list[dict[str, Any]] = []
    q_materials = {"Q1": "q1_keepout_red", "Q2": "q2_keepout_amber", "Q3": "q3_keepout_magenta"}
    for ref in ("Q1", "Q2", "Q3"):
        volume = keepout_column(ref, components[ref], requirements)
        obj = create_cylinder(
            f"{ref}_Projected_Keepout_Column",
            volume,
            mats[q_materials[ref]],
            collections["critical_keepouts"],
            "projected_keepout_column_overlay",
            ref,
        )
        overlays.append(obj)
        overlay_specs.append(
            {"name": obj.name, "role": obj["engiworld_role"], "ref": ref, "cylinder_mm": volume, "material": q_materials[ref]}
        )

    rib_materials = {"RIB_NEG_Y": "rib_neg_review_cyan", "RIB_POS_Y": "rib_pos_review_lime"}
    for rib in requirements["required_ribs"]:
        ref = normalize(rib["id"])
        bounds = [float(value) for value in rib["bounds_mm"]]
        obj = create_box(
            f"{ref}_Geometry_Review",
            bounds,
            mats[rib_materials[ref]],
            collections["rib_review"],
            "rib_review_overlay",
            ref,
        )
        overlays.append(obj)
        overlay_specs.append(
            {"name": obj.name, "role": obj["engiworld_role"], "ref": ref, "bounds_mm": bounds, "material": rib_materials[ref]}
        )

    access_materials = {"J1": "j1_access_orange", "J2": "j2_access_blue"}
    for ref in ("J1", "J2"):
        connector = connectors[ref]
        direction = normalize(connector["direction"])
        measured_access = report.get("access_checks", {}).get(ref, {})
        reported_bounds = measured_access.get("bounds_mm") if isinstance(measured_access, dict) else None
        bounds = (
            [float(value) for value in reported_bounds]
            if isinstance(reported_bounds, list) and len(reported_bounds) == 6
            else access_bounds(connector, components[ref], enclosure_bbox, board_top_z, requirements)
        )
        access_obj = create_box(
            f"{ref}_{direction}_Access_Corridor",
            bounds,
            mats[access_materials[ref]],
            collections["access_review"],
            "access_corridor_overlay",
            ref,
        )
        access_obj["access_direction"] = direction
        overlays.append(access_obj)
        overlay_specs.append(
            {
                "name": access_obj.name,
                "role": access_obj["engiworld_role"],
                "ref": ref,
                "direction": direction,
                "bounds_mm": bounds,
                "material": access_materials[ref],
            }
        )
        start, end = arrow_endpoints(bounds, direction)
        arrow = create_direction_arrow(
            f"{ref}_{direction}_Direction_Arrow",
            start,
            end,
            mats[access_materials[ref]],
            collections["access_review"],
            ref,
            direction,
        )
        overlays.append(arrow)
        overlay_specs.append(
            {
                "name": arrow.name,
                "role": arrow["engiworld_role"],
                "ref": ref,
                "direction": direction,
                "start_mm": list(start),
                "end_mm": list(end),
                "material": access_materials[ref],
            }
        )

    target = (0.0, 0.0, 10.0)
    bpy.ops.object.camera_add(location=(180.0, -210.0, 155.0))
    camera = bpy.context.object
    camera.name = "release_review_camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 255.0
    look_at(camera, target)
    bpy.context.scene.camera = camera
    bpy.context.view_layer.update()

    camera_rotation = camera.rotation_euler.to_quaternion()
    camera_right = camera_rotation @ Vector((1.0, 0.0, 0.0))
    camera_up = camera_rotation @ Vector((0.0, 1.0, 0.0))
    label_specs = [
        ("Q1 KEEPOUT", mats["q1_keepout_red"]),
        ("Q2 KEEPOUT", mats["q2_keepout_amber"]),
        ("Q3 KEEPOUT", mats["q3_keepout_magenta"]),
        ("RIB -Y", mats["rib_neg_review_cyan"]),
        ("RIB +Y", mats["rib_pos_review_lime"]),
        ("J1 X+ ACCESS", mats["j1_access_orange"]),
        ("J2 X- ACCESS", mats["j2_access_blue"]),
    ]
    label_offsets = (-105.0, -70.0, -35.0, 0.0, 35.0, 70.0, 105.0)
    labels: list[bpy.types.Object] = []
    for (text, mat), offset in zip(label_specs, label_offsets):
        location = Vector(target) + camera_right * offset + camera_up * -80.0
        label = add_label(text, location, collections["review_labels"], mat)
        label.rotation_euler = (camera.location - label.location).to_track_quat("Z", "Y").to_euler()
        labels.append(label)

    for name, location, energy, size in [
        ("Key_Area", (55.0, -45.0, 125.0), 2600.0, 72.0),
        ("Fill_Area", (-75.0, 45.0, 90.0), 1900.0, 62.0),
        ("Rim_Area", (10.0, 85.0, 70.0), 1300.0, 50.0),
    ]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        look_at(light, target)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(work / "04_blender_review.png")
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.9
    world = bpy.data.worlds.new("Task04_ReviewWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.06, 0.065, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.72
    scene.world = world
    bpy.context.view_layer.update()

    label_boxes = {label.name: projected_bounds(scene, camera, label) for label in labels}
    label_overlap_pairs = [
        [left.name, right.name]
        for index, left in enumerate(labels)
        for right in labels[index + 1 :]
        if boxes_overlap(label_boxes[left.name], label_boxes[right.name])
    ]
    physical_objects = [obj for obj in imported if obj.get("engiworld_role") not in {"source_overlay", "unclassified"}]
    physical_boxes = [projected_bounds(scene, camera, obj) for obj in physical_objects]
    labels_over_physical = [
        label.name
        for label in labels
        if any(boxes_overlap(label_boxes[label.name], physical_box, padding=0.008) for physical_box in physical_boxes)
    ]
    framed_objects = physical_objects + overlays + labels
    frame_boxes = [projected_bounds(scene, camera, obj) for obj in framed_objects]
    camera_frame_bounds = [
        min(box[0] for box in frame_boxes),
        min(box[1] for box in frame_boxes),
        max(box[2] for box in frame_boxes),
        max(box[3] for box in frame_boxes),
    ]
    camera_frame_ok = (
        camera_frame_bounds[0] >= 0.01
        and camera_frame_bounds[1] >= 0.01
        and camera_frame_bounds[2] <= 0.99
        and camera_frame_bounds[3] <= 0.99
    )

    required_roles_present = (
        role_counts["tray"] >= 1
        and role_counts["lid"] >= 1
        and role_counts["pcb"] >= 1
        and role_counts["component"] >= len(REQUIRED_COMPONENT_REFS)
        and role_counts["rib"] >= len(REQUIRED_RIB_REFS)
        and REQUIRED_COMPONENT_REFS.issubset(physical_refs["component"])
        and REQUIRED_RIB_REFS.issubset(physical_refs["rib"])
    )
    overlay_roles = {str(obj.get("engiworld_role", "")) for obj in overlays}
    overlay_refs = {str(obj.get("reference", "")) for obj in overlays}
    required_overlays_present = (
        len(overlays) == 9
        and {
            "projected_keepout_column_overlay",
            "rib_review_overlay",
            "access_corridor_overlay",
            "access_direction_overlay",
        }.issubset(overlay_roles)
        and (REQUIRED_COMPONENT_REFS | REQUIRED_RIB_REFS).issubset(overlay_refs)
    )

    export_objects = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_render]
    material_assignments = {
        obj.name: [slot.material.name for slot in obj.material_slots if slot.material]
        for obj in export_objects
    }
    used_materials = {name for names in material_assignments.values() for name in names}
    required_overlay_materials = set(q_materials.values()) | set(rib_materials.values()) | set(access_materials.values())
    required_physical_materials = {"tray_asa", "lid_translucent", "pcb_green", "component_neutral", "rib_physical"}
    missing_required_materials = sorted((required_overlay_materials | required_physical_materials) - used_materials)
    materials_ok = not missing_required_materials and all(material_assignments.values())
    layout_ok = not label_overlap_pairs and not labels_over_physical and camera_frame_ok
    decision = (
        "pass"
        if report.get("decision") == "pass"
        and required_roles_present
        and required_overlays_present
        and materials_ok
        and layout_ok
        else "fail"
    )

    scene["engiworld_task"] = TASK
    scene["release_decision"] = decision
    scene["freecad_decision"] = str(report.get("decision", "missing"))
    scene["required_roles_present"] = required_roles_present
    scene["required_overlays_present"] = required_overlays_present
    scene["camera_frame_ok"] = camera_frame_ok

    blend_path = work / "04_blender_review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    bpy.ops.render.render(write_still=True)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objects:
        obj.select_set(True)
    if not export_objects:
        raise RuntimeError("review scene has no renderable mesh objects")
    bpy.context.view_layer.objects.active = export_objects[0]
    bpy.ops.wm.obj_export(
        filepath=str(work / "04_blender_review.obj"),
        export_selected_objects=True,
        export_materials=True,
        export_triangulated_mesh=True,
        forward_axis="Y",
        up_axis="Z",
    )

    mesh_qc = {
        "missing_material_slots": sum(1 for obj in export_objects if not material_assignments[obj.name]),
        "nonmanifold_edges": sum(nonmanifold_edge_count(obj) for obj in export_objects),
        "unlabeled_overlays": sum(1 for obj in overlays if not obj.get("reference")),
        "unused_required_materials": missing_required_materials,
    }
    copied_metrics = {key: report[key] for key in REQUIRED_METRICS}
    scene_report = {
        "active_camera": camera.name,
        "camera": {
            "frame_bounds_normalized": [round(value, 6) for value in camera_frame_bounds],
            "framing_pass": camera_frame_ok,
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
        "label_layout": {
            "labels_over_physical": labels_over_physical,
            "normalized_bounds": {name: [round(value, 6) for value in bounds] for name, bounds in label_boxes.items()},
            "overlap_pairs": label_overlap_pairs,
        },
        "material_assignments": material_assignments,
        "materials": sorted(used_materials),
        "mesh_qc": mesh_qc,
        "metrics_source": "03_freecad_clearance_report.json",
        "native_scene": "04_blender_review.blend",
        "object_roles": {obj.name: obj.get("engiworld_role", "") for obj in export_objects},
        "overlay_geometry": overlay_specs,
        "overlay_materials": {item["name"]: item["material"] for item in overlay_specs},
        "real_object_roles": {obj.name: obj.get("engiworld_role", "") for obj in imported},
        "render": "04_blender_review.png",
        "review_mtl": "04_blender_review.mtl",
        "review_obj": "04_blender_review.obj",
        "role_counts": role_counts,
        "role_references": {role: sorted(refs) for role, refs in physical_refs.items()},
        "role_sources": role_sources,
        "software_stage": "Blender",
        "task": TASK,
        "visible_accesses": ["J1_X_PLUS", "J2_X_MINUS"],
        "visible_features": [
            "Q1_projected_keepout_column",
            "Q2_projected_keepout_column",
            "Q3_projected_keepout_column",
            "RIB_NEG_Y_geometry_review",
            "RIB_POS_Y_geometry_review",
            "J1_X_PLUS_access_corridor",
            "J1_X_PLUS_direction",
            "J2_X_MINUS_access_corridor",
            "J2_X_MINUS_direction",
        ],
        "visible_keepouts": ["Q1", "Q2", "Q3"],
        "visible_overlays": [obj.name for obj in overlays],
        "visible_ribs": ["RIB_NEG_Y", "RIB_POS_Y"],
    }
    json_dump(work / "04_blender_scene_report.json", scene_report)
    if decision != "pass":
        raise RuntimeError(
            f"{TASK} Blender scene contract failed: roles={role_counts}, refs="
            f"{ {role: sorted(refs) for role, refs in physical_refs.items()} }, "
            f"overlays={len(overlays)}, missing_materials={missing_required_materials}, "
            f"label_overlaps={label_overlap_pairs}, labels_over_physical={labels_over_physical}, "
            f"camera_frame={camera_frame_bounds}, freecad_decision={report.get('decision')!r}"
        )


if __name__ == "__main__":
    main()
