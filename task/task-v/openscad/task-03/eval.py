from __future__ import annotations

import math
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
OUTPUT_NAME = "task-020_output.3mf"
EXPECTED_BOUNDS = ((-65.0, -45.0, 0.0), (65.0, 45.0, 64.0))
EXPECTED_VOLUME_MM3 = 128974.910
POST_CENTERS = ((-52.0, -32.0), (-52.0, 32.0), (52.0, -32.0), (52.0, 32.0))
MOUNTING_HOLE_CENTERS = ((-45.0, 0.0), (45.0, 0.0), (0.0, -28.0), (0.0, 28.0))
SLOT_CENTERS = ((-25.0, 0.0), (25.0, 0.0))
GEOMETRY_TOL = 0.18


def _parse_3mf(path: Path):
    with zipfile.ZipFile(path) as archive:
        model_names = [name for name in archive.namelist() if name.lower().endswith(".model")]
        if not model_names:
            return []
        root = ET.fromstring(archive.read(model_names[0]))
    if root.attrib.get("unit", "millimeter").lower() not in {"millimeter", "millimetre"}:
        return []
    triangles = []
    for mesh_element in (element for element in root.iter() if element.tag.split("}")[-1] == "mesh"):
        vertices = []
        for element in mesh_element.iter():
            tag = element.tag.split("}")[-1]
            if tag == "vertex":
                vertices.append(tuple(float(element.attrib[axis]) for axis in ("x", "y", "z")))
            elif tag == "triangle":
                ids = tuple(int(element.attrib[key]) for key in ("v1", "v2", "v3"))
                if max(ids, default=-1) >= len(vertices):
                    return []
                triangles.append(tuple(vertices[index] for index in ids))
    return triangles


def _vertex_key(point):
    return tuple(round(float(value), 5) for value in point)


class Mesh:
    def __init__(self, triangles):
        self.triangles = triangles
        unique = {}
        for triangle in triangles:
            for point in triangle:
                unique[_vertex_key(point)] = tuple(float(value) for value in point)
        self.vertices = list(unique.values())
        self.mins = tuple(min(point[axis] for point in self.vertices) for axis in range(3))
        self.maxs = tuple(max(point[axis] for point in self.vertices) for axis in range(3))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _signed_volume(mesh: Mesh):
    return sum(_dot(a, _cross(b, c)) for a, b, c in mesh.triangles) / 6.0


def _topology_components(mesh: Mesh):
    vertex_ids = {}
    faces = []
    for triangle in mesh.triangles:
        face = []
        for point in triangle:
            key = _vertex_key(point)
            vertex_ids.setdefault(key, len(vertex_ids))
            face.append(vertex_ids[key])
        if len(set(face)) != 3:
            return None
        faces.append(face)
    parent = list(range(len(faces)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    owners = {}
    for face_index, (a, b, c) in enumerate(faces):
        for edge in ((a, b), (b, c), (c, a)):
            owners.setdefault(tuple(sorted(edge)), []).append(face_index)
    if any(len(items) != 2 for items in owners.values()):
        return None
    for items in owners.values():
        union(items[0], items[1])
    return len({find(index) for index in range(len(faces))})


RAY_DIRECTION = (1.0, 0.371390676, 0.529113147)


def _ray_distance(origin, triangle):
    a, b, c = triangle
    edge1, edge2 = _sub(b, a), _sub(c, a)
    h = _cross(RAY_DIRECTION, edge2)
    determinant = _dot(edge1, h)
    if abs(determinant) < 1e-10:
        return None
    inverse = 1.0 / determinant
    s = _sub(origin, a)
    u = inverse * _dot(s, h)
    if u < -1e-9 or u > 1.0 + 1e-9:
        return None
    q = _cross(s, edge1)
    v = inverse * _dot(RAY_DIRECTION, q)
    if v < -1e-9 or u + v > 1.0 + 1e-9:
        return None
    distance = inverse * _dot(edge2, q)
    return distance if distance > 1e-7 else None


def _point_inside(mesh: Mesh, point):
    hits = []
    for triangle in mesh.triangles:
        distance = _ray_distance(point, triangle)
        if distance is not None and all(abs(distance - prior) > 1e-6 for prior in hits):
            hits.append(distance)
    return len(hits) % 2 == 1


def _circle_vertex_bins(mesh: Mesh, center, radius, z, tolerance=GEOMETRY_TOL):
    cx, cy = center
    bins = set()
    for x, y, point_z in mesh.vertices:
        if abs(point_z - z) > tolerance:
            continue
        if abs(math.hypot(x - cx, y - cy) - radius) <= tolerance:
            angle = math.atan2(y - cy, x - cx) % (2.0 * math.pi)
            bins.add(int(angle / (2.0 * math.pi) * 64) % 64)
    return len(bins)


def _circles_ok(mesh: Mesh, centers, radius, z_values):
    return all(
        _circle_vertex_bins(mesh, center, radius, z) >= 28
        for center in centers
        for z in z_values
    )


def _near_vertex(mesh: Mesh, target, tolerance=GEOMETRY_TOL):
    return any(
        all(abs(point[axis] - target[axis]) <= tolerance for axis in range(3))
        for point in mesh.vertices
    )


def _slots_ok(mesh: Mesh):
    for cx, cy in SLOT_CENTERS:
        for z in (0.0, 6.0):
            required = (
                (cx - 14.0, cy, z),
                (cx + 14.0, cy, z),
                (cx - 10.0, cy - 4.0, z),
                (cx - 10.0, cy + 4.0, z),
                (cx + 10.0, cy - 4.0, z),
                (cx + 10.0, cy + 4.0, z),
            )
            if not all(_near_vertex(mesh, point) for point in required):
                return False
        void_probes = tuple(
            (x, cy, z)
            for z in (0.4, 3.0, 5.6)
            for x in (cx, cx - 13.5, cx + 13.5)
        )
        solid_probes = tuple(
            point
            for z in (0.4, 3.0, 5.6)
            for point in (
                (cx, cy + 4.4, z),
                (cx, cy - 4.4, z),
                (cx - 14.4, cy, z),
                (cx + 14.4, cy, z),
            )
        )
        if any(_point_inside(mesh, point) for point in void_probes):
            return False
        if not all(_point_inside(mesh, point) for point in solid_probes):
            return False
    return True


def _material_and_voids_ok(mesh: Mesh):
    base_solid = ((0.0, 20.0, 3.0), (-60.0, -40.0, 3.0), (60.0, 40.0, 3.0))
    top_solid = ((0.0, 20.0, 62.0), (-60.0, -40.0, 62.0), (60.0, 40.0, 62.0))
    if not all(_point_inside(mesh, point) for point in base_solid + top_solid):
        return False
    for cx, cy in MOUNTING_HOLE_CENTERS:
        for z in (0.4, 3.0, 5.6):
            if _point_inside(mesh, (cx, cy, z)):
                return False
            if not _point_inside(mesh, (cx + 3.9, cy, z)):
                return False
    for cx, cy in POST_CENTERS:
        if not _point_inside(mesh, (cx, cy, 30.0)):
            return False
        if not _point_inside(mesh, (cx + 4.7, cy, 30.0)):
            return False
        if _point_inside(mesh, (cx + 5.3, cy, 30.0)):
            return False
        for z in (60.3, 62.0, 63.7):
            if _point_inside(mesh, (cx, cy, z)):
                return False
            if not _point_inside(mesh, (cx + 5.9, cy, z)):
                return False
    return True


def evaluate() -> bool:
    path = OUTPUT_ROOT / OUTPUT_NAME
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    triangles = _parse_3mf(path)
    if len(triangles) < 500:
        return False
    mesh = Mesh(triangles)
    if len(mesh.vertices) < 250:
        return False
    if any(
        abs(mesh.mins[axis] - EXPECTED_BOUNDS[0][axis]) > GEOMETRY_TOL
        or abs(mesh.maxs[axis] - EXPECTED_BOUNDS[1][axis]) > GEOMETRY_TOL
        for axis in range(3)
    ):
        return False
    topology_components = _topology_components(mesh)
    if topology_components is None or topology_components not in (1, 2):
        return False
    if abs(abs(_signed_volume(mesh)) - EXPECTED_VOLUME_MM3) > 80.0:
        return False
    if not _circles_ok(mesh, MOUNTING_HOLE_CENTERS, 3.5, (0.0, 6.0)):
        return False
    if not _circles_ok(mesh, POST_CENTERS, 5.5, (60.0, 64.0)):
        return False
    return _slots_ok(mesh) and _material_and_voids_ok(mesh)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
