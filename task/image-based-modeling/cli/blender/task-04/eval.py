from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
SPEC = {'kind': 'plate', 'version_prefix': '4.2.3', 'exact_mesh_objects': ['Plate'], 'name': 'Plate', 'dimensions': [4.0, 2.0, 0.2], 'components': 1, 'euler': -10, 'closed': True, 'volume_range': [1.37, 1.42], 'bore_centers': [(-1.2, -0.5), (0, -0.5), (1.2, -0.5), (-1.2, 0.5), (0, 0.5), (1.2, 0.5)], 'bore_diameter': 0.3, 'bore_z_fractions': [0.1, 0.5, 0.9], 'ring_solid_z_fraction': 0.25, 'void_xy_z_fractions': [(0, 0, 0.8), (-0.8, 0, 0.8), (0.8, 0, 0.8), (0, -0.3, 0.8), (0, 0.3, 0.8)], 'solid_xy_z_fractions': [(0, 0, 0.5), (1.2, 0, 0.8), (0, 0.7, 0.8)]}


def close_vec(actual, expected, tol=0.04):
    return len(actual) == len(expected) and all(abs(float(a) - float(b)) <= tol for a, b in zip(actual, expected))


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def point_inside(item, point):
    vertices = item.get("world_vertices", [])
    triangles = item.get("triangles", [])
    direction = (0.873145, 0.347231, 0.337819)
    hits = []
    epsilon = 1e-8
    for indices in triangles:
        a, b, c = (vertices[index] for index in indices)
        edge1, edge2 = _sub(b, a), _sub(c, a)
        h = _cross(direction, edge2)
        determinant = _dot(edge1, h)
        if abs(determinant) < epsilon:
            continue
        inverse = 1.0 / determinant
        s = _sub(point, a)
        u = inverse * _dot(s, h)
        if u < -epsilon or u > 1.0 + epsilon:
            continue
        q = _cross(s, edge1)
        v = inverse * _dot(direction, q)
        if v < -epsilon or u + v > 1.0 + epsilon:
            continue
        distance = inverse * _dot(edge2, q)
        if distance > epsilon:
            hits.append(distance)
    hits.sort()
    unique = []
    for value in hits:
        if not unique or abs(value - unique[-1]) > 1e-6:
            unique.append(value)
    return len(unique) % 2 == 1


def _mesh_volume(item):
    vertices = item.get("world_vertices", [])
    signed = 0.0
    for indices in item.get("triangles", []):
        a, b, c = (vertices[index] for index in indices)
        signed += _dot(a, _cross(b, c)) / 6.0
    return abs(signed)


def _validate_common_object(item, expected):
    if item is None or item.get("type") != expected.get("type", item.get("type")):
        return False
    if "dimensions" in expected and not close_vec(item.get("dimensions", []), expected["dimensions"]):
        return False
    if "location" in expected and not close_vec(item.get("location", []), expected["location"]):
        return False
    return True


def _validate_terrain(item):
    if not _validate_common_object(item, {"type": "MESH", "dimensions": SPEC["dimensions"]}):
        return False
    for key in ("vertices", "edges", "polygons", "components"):
        actual_key = "component_count" if key == "components" else key
        if item.get(actual_key) != SPEC[key]:
            return False
    quad_faces = sum(1 for face in item.get("faces", []) if len(face) == 4)
    if quad_faces != SPEC["quad_faces"]:
        return False
    vertices = item.get("world_vertices", [])
    x_values = sorted({round(point[0], 6) for point in vertices})
    y_values = sorted({round(point[1], 6) for point in vertices})
    grid_rows, grid_columns = SPEC["grid_rows"], SPEC["grid_columns"]
    if len(y_values) != grid_rows or len(x_values) != grid_columns:
        return False
    if abs(x_values[0] - SPEC["grid_origin"][0]) > 1e-5 or abs(y_values[0] - SPEC["grid_origin"][1]) > 1e-5:
        return False
    if any(abs((b - a) - 1.0) > 1e-5 for values in (x_values, y_values) for a, b in zip(values, values[1:])):
        return False
    pair_to_index = {}
    for index, point in enumerate(vertices):
        key = (round(point[0], 6), round(point[1], 6))
        if key in pair_to_index:
            return False
        pair_to_index[key] = index
    face_sets = {frozenset(face) for face in item.get("faces", [])}
    for row in range(grid_rows - 1):
        for column in range(grid_columns - 1):
            expected_face = frozenset({
                pair_to_index[(x_values[column], y_values[row])],
                pair_to_index[(x_values[column + 1], y_values[row])],
                pair_to_index[(x_values[column + 1], y_values[row + 1])],
                pair_to_index[(x_values[column], y_values[row + 1])],
            })
            if expected_face not in face_sets:
                return False
    z_values = [point[2] for point in vertices]
    relief = max(z_values) - min(z_values)
    return SPEC["relief_range"][0] <= relief <= SPEC["relief_range"][1]


def _validate_wall(item):
    if not _validate_common_object(item, {"type": "MESH", "dimensions": SPEC["dimensions"]}):
        return False
    for key in ("vertices", "edges", "polygons"):
        if item.get(key) != SPEC[key]:
            return False
    component_stats = SPEC["component_stats"]
    components = item.get("component_stats", [])
    if len(components) != SPEC["components"]:
        return False
    courses = {}
    for component in components:
        if [component.get("vertices"), component.get("edges"), component.get("polygons")] != component_stats:
            return False
        if component.get("face_sizes") != {"4": 6}:
            return False
        dimensions = [component["max"][axis] - component["min"][axis] for axis in range(3)]
        if not close_vec(dimensions, SPEC["brick_dimensions"], tol=0.002):
            return False
        center = [(component["min"][axis] + component["max"][axis]) / 2 for axis in range(3)]
        courses.setdefault(round(center[2], 4), []).append(round(center[0], 4))
    expected_z = [round(index * 0.05, 4) for index in range(10)]
    course_counts = [len(courses.get(z, [])) for z in expected_z]
    if course_counts != SPEC["course_counts"] or set(courses) != set(expected_z):
        return False
    for index, z in enumerate(expected_z):
        expected_x = [round(column * 0.2 + (0.1 if index % 2 else 0.0), 4) for column in range(10)]
        if sorted(courses[z]) != expected_x:
            return False
    return True


def _validate_plate(item):
    if not _validate_common_object(item, {"type": "MESH", "dimensions": SPEC["dimensions"]}):
        return False
    if item.get("component_count") != SPEC["components"] or item.get("euler") != SPEC["euler"]:
        return False
    if SPEC.get("closed") and (item.get("boundary_edges") != 0 or item.get("nonmanifold_edges") != 0):
        return False
    volume = _mesh_volume(item)
    if not (SPEC["volume_range"][0] <= volume <= SPEC["volume_range"][1]):
        return False
    vertices = item.get("world_vertices", [])
    if not vertices:
        return False
    z_min = min(point[2] for point in vertices)
    z_max = max(point[2] for point in vertices)
    z_span = z_max - z_min
    bore_z_samples = [z_min + z_span * fraction for fraction in SPEC["bore_z_fractions"]]
    bore_centers = SPEC["bore_centers"]
    bore_diameter = SPEC["bore_diameter"]
    radius = bore_diameter / 2.0
    for x, y in bore_centers:
        for z in bore_z_samples:
            for dx, dy in ((0, 0), (radius * 0.55, 0), (-radius * 0.55, 0), (0, radius * 0.55), (0, -radius * 0.55)):
                if point_inside(item, (x + dx, y + dy, z)):
                    return False
        solid_z = z_min + z_span * SPEC["ring_solid_z_fraction"]
        for dx, dy in ((bore_diameter * 0.75, 0), (-bore_diameter * 0.75, 0)):
            if not point_inside(item, (x + dx, y + dy, solid_z)):
                return False
    void_samples = [(x, y, z_min + z_span * fraction) for x, y, fraction in SPEC.get("void_xy_z_fractions", [])]
    solid_samples = [(x, y, z_min + z_span * fraction) for x, y, fraction in SPEC.get("solid_xy_z_fractions", [])]
    if any(point_inside(item, point) for point in void_samples):
        return False
    if any(not point_inside(item, point) for point in solid_samples):
        return False
    return True


def _validate_urban(objects):
    if set(objects) != set(SPEC["exact_objects"]):
        return False
    for name, expected in SPEC["objects"].items():
        if not _validate_common_object(objects.get(name), expected):
            return False
    if objects["Sun"].get("light_type") != SPEC["light_type"]:
        return False
    ground = objects["Ground"]
    if ground.get("component_count") != 1 or abs(ground.get("surface_area", 0.0) - 400.0) > 0.05:
        return False
    if any(abs(point[2]) > 1e-5 for point in ground.get("world_vertices", [])):
        return False
    material_names = SPEC["material_names"]
    if ground.get("materials") != [material_names["ground"]]:
        return False
    building_materials = []
    for name in sorted(key for key in SPEC["objects"] if key.startswith("Building_")):
        item = objects[name]
        if item.get("component_count") != 1 or item.get("boundary_edges") != 0 or item.get("nonmanifold_edges") != 0:
            return False
        dimensions = SPEC["objects"][name]["dimensions"]
        expected_volume = dimensions[0] * dimensions[1] * dimensions[2]
        if abs(_mesh_volume(item) - expected_volume) > max(0.02, expected_volume * 0.002):
            return False
        center = SPEC["objects"][name]["location"]
        for fx in (-0.3, 0.0, 0.3):
            for fy in (-0.3, 0.0, 0.3):
                for fz in (-0.3, 0.0, 0.3):
                    point = (center[0] + dimensions[0] * fx,
                             center[1] + dimensions[1] * fy,
                             center[2] + dimensions[2] * fz)
                    if not point_inside(item, point):
                        return False
        materials = item.get("materials", [])
        if len(materials) != 1 or materials[0] == material_names["ground"]:
            return False
        building_materials.append(materials[0])
    if material_names.get("buildings_distinct") and len(set(building_materials)) != len(building_materials):
        return False
    return True


def validate_report(report):
    if not str(report.get("blender_version", "")).startswith(SPEC["version_prefix"]):
        return False
    objects = report.get("objects", {})
    if "exact_mesh_objects" in SPEC:
        mesh_names = {name for name, item in objects.items() if item.get("type") == "MESH"}
        if mesh_names != set(SPEC["exact_mesh_objects"]):
            return False
    if SPEC["kind"] == "terrain":
        return _validate_terrain(objects.get(SPEC["name"]))
    if SPEC["kind"] == "wall":
        return _validate_wall(objects.get(SPEC["name"]))
    if SPEC["kind"] == "plate":
        return _validate_plate(objects.get(SPEC["name"]))
    if SPEC["kind"] == "urban":
        return _validate_urban(objects)
    return False


INSPECTOR = r'''import bpy
import json
import sys
from collections import Counter


def component_stats(mesh, world_vertices):
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    result = []
    seen = set()
    for start in range(len(adjacency)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        indices = []
        while stack:
            current = stack.pop()
            indices.append(current)
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        vertex_set = set(indices)
        edges = [edge for edge in mesh.edges if edge.vertices[0] in vertex_set and edge.vertices[1] in vertex_set]
        polygons = [polygon for polygon in mesh.polygons if all(index in vertex_set for index in polygon.vertices)]
        points = [world_vertices[index] for index in indices]
        result.append({
            "vertices": len(indices), "edges": len(edges), "polygons": len(polygons),
            "face_sizes": dict(Counter(str(len(p.vertices)) for p in polygons)),
            "min": [min(point[axis] for point in points) for axis in range(3)],
            "max": [max(point[axis] for point in points) for axis in range(3)],
        })
    return result


objects = {}
depsgraph = bpy.context.evaluated_depsgraph_get()
for obj in bpy.context.scene.objects:
    item = {"type": obj.type, "location": list(obj.location), "dimensions": list(obj.dimensions)}
    if obj.type == "LIGHT":
        item["light_type"] = obj.data.type
    if obj.type == "MESH":
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            world_vertices = [list(evaluated.matrix_world @ vertex.co) for vertex in mesh.vertices]
            faces = [list(polygon.vertices) for polygon in mesh.polygons]
            mesh.calc_loop_triangles()
            triangles = [list(triangle.vertices) for triangle in mesh.loop_triangles]
            edge_use = Counter()
            for face in faces:
                for index, a in enumerate(face):
                    b = face[(index + 1) % len(face)]
                    edge_use[tuple(sorted((a, b)))] += 1
            surface_area = 0.0
            for a, b, c in triangles:
                va, vb, vc = world_vertices[a], world_vertices[b], world_vertices[c]
                ab = (vb[0] - va[0], vb[1] - va[1], vb[2] - va[2])
                ac = (vc[0] - va[0], vc[1] - va[1], vc[2] - va[2])
                cross = (ab[1] * ac[2] - ab[2] * ac[1],
                         ab[2] * ac[0] - ab[0] * ac[2],
                         ab[0] * ac[1] - ab[1] * ac[0])
                surface_area += (cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2) ** 0.5 / 2.0
            stats = component_stats(mesh, world_vertices)
            item.update({
                "vertices": len(mesh.vertices), "edges": len(mesh.edges), "polygons": len(mesh.polygons),
                "euler": len(mesh.vertices) - len(mesh.edges) + len(mesh.polygons),
                "component_count": len(stats), "component_stats": stats,
                "face_sizes": dict(Counter(str(len(p.vertices)) for p in mesh.polygons)),
                "boundary_edges": sum(1 for count in edge_use.values() if count == 1),
                "nonmanifold_edges": sum(1 for count in edge_use.values() if count not in (1, 2)),
                "materials": [slot.material.name for slot in obj.material_slots if slot.material],
                "world_vertices": world_vertices, "faces": faces, "triangles": triangles,
                "surface_area": surface_area,
            })
        finally:
            evaluated.to_mesh_clear()
    objects[obj.name] = item
with open(sys.argv[-1], "w", encoding="utf-8") as handle:
    json.dump({"blender_version": bpy.app.version_string, "objects": objects}, handle)
'''


def run():
    answer = OUTPUT_ROOT / "answer.blend"
    blender = shutil.which("blender") or "/usr/local/bin/blender"
    if not answer.is_file() or answer.stat().st_size < 10000 or not Path(blender).exists():
        return False
    with tempfile.TemporaryDirectory(prefix="reverse_blender_eval_") as tmp:
        tmp = Path(tmp)
        report_path = tmp / "report.json"
        inspector_path = tmp / "inspect.py"
        inspector_path.write_text(INSPECTOR, encoding="utf-8")
        proc = subprocess.run(
            [blender, "--background", str(answer), "--python", str(inspector_path), "--", str(report_path)],
            capture_output=True, text=True, timeout=180,
        )
        if proc.returncode != 0 or not report_path.exists():
            return False
        report = json.loads(report_path.read_text(encoding="utf-8"))
    return validate_report(report)


if __name__ == "__main__":
    try:
        print("True" if run() else "False")
    except Exception:
        print("False")
