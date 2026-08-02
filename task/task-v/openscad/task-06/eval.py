from __future__ import annotations

import math
import os
import struct
from pathlib import Path


OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
OUTPUT_NAME = "task-001_output.stl"
EXPECTED_BOUNDS = ((-60.0, -40.0, 0.0), (60.0, 40.0, 28.0))
EXPECTED_VOLUME_MM3 = 82953.654
BOSS_CENTERS = ((-45.0, -25.0), (-45.0, 25.0), (45.0, -25.0), (45.0, 25.0))
SLOT_CENTERS_Y = (-25.0, 0.0, 25.0)
RIB_CENTERS_X = (-42.0, -28.0, -14.0, 0.0, 14.0, 28.0, 42.0)
GEOMETRY_TOL = 0.18


def _parse_stl(path: Path):
    data = path.read_bytes()
    triangles = []
    if len(data) >= 84:
        count = struct.unpack("<I", data[80:84])[0]
        if 84 + count * 50 == len(data):
            for index in range(count):
                values = struct.unpack("<12fH", data[84 + index * 50 : 134 + index * 50])
                coordinates = values[3:12]
                triangles.append(
                    tuple(
                        (coordinates[offset], coordinates[offset + 1], coordinates[offset + 2])
                        for offset in range(0, 9, 3)
                    )
                )
            return triangles
    vertices = []
    for raw_line in data.decode("utf-8", errors="ignore").splitlines():
        parts = raw_line.strip().split()
        if len(parts) == 4 and parts[0].lower() == "vertex":
            vertices.append(tuple(float(value) for value in parts[1:]))
            if len(vertices) == 3:
                triangles.append(tuple(vertices))
                vertices = []
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


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


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
    if any(len(indices) != 2 for indices in owners.values()):
        return None
    for indices in owners.values():
        union(indices[0], indices[1])
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


def _near_vertex(mesh: Mesh, target, tolerance=GEOMETRY_TOL):
    return any(
        all(abs(point[axis] - target[axis]) <= tolerance for axis in range(3))
        for point in mesh.vertices
    )


def _circle_bins(mesh: Mesh, center, radius, z):
    cx, cy = center
    bins = set()
    for x, y, point_z in mesh.vertices:
        if abs(point_z - z) > GEOMETRY_TOL:
            continue
        if abs(math.hypot(x - cx, y - cy) - radius) <= GEOMETRY_TOL:
            angle = math.atan2(y - cy, x - cx) % (2.0 * math.pi)
            bins.add(int(angle / (2.0 * math.pi) * 64) % 64)
    return len(bins)


def _bosses_ok(mesh: Mesh):
    for cx, cy in BOSS_CENTERS:
        if _circle_bins(mesh, (cx, cy), 1.8, 0.0) < 28:
            return False
        if _circle_bins(mesh, (cx, cy), 1.8, 28.0) < 28:
            return False
        if _circle_bins(mesh, (cx, cy), 4.0, 28.0) < 28:
            return False
        for z in (0.4, 3.5, 8.0, 17.0, 27.5):
            if _point_inside(mesh, (cx, cy, z)):
                return False
        for z in (5.0, 12.0, 24.0):
            if not _point_inside(mesh, (cx + 3.8, cy, z)):
                return False
            if _point_inside(mesh, (cx + 4.2, cy, z)):
                return False
    return True


def _slots_ok(mesh: Mesh):
    for cy in SLOT_CENTERS_Y:
        for z in (0.0, 4.0):
            required = (
                (-24.0, cy, z),
                (24.0, cy, z),
                (-21.0, cy - 3.0, z),
                (-21.0, cy + 3.0, z),
                (21.0, cy - 3.0, z),
                (21.0, cy + 3.0, z),
            )
            if not all(_near_vertex(mesh, point) for point in required):
                return False
        for z in (0.3, 2.0, 3.7):
            for x in (0.0, -23.5, 23.5):
                if _point_inside(mesh, (x, cy, z)):
                    return False
            for point in ((0.0, cy - 3.4, z), (0.0, cy + 3.4, z), (-24.4, cy, z), (24.4, cy, z)):
                if not _point_inside(mesh, point):
                    return False
    return True


def _ribs_ok(mesh: Mesh):
    for center_x in RIB_CENTERS_X:
        for x in (center_x - 0.7, center_x, center_x + 0.7):
            for z in (4.3, 10.0, 17.7):
                if not _point_inside(mesh, (x, 20.0, z)):
                    return False
        for x in (center_x - 1.0, center_x + 1.0):
            if _point_inside(mesh, (x, 20.0, 10.0)):
                return False
        for target in (
            (center_x - 0.8, -32.0, 4.0),
            (center_x + 0.8, 32.0, 4.0),
            (center_x - 0.8, -32.0, 18.0),
            (center_x + 0.8, 32.0, 18.0),
        ):
            if not _near_vertex(mesh, target):
                return False
    return True


def _ledge_ok(mesh: Mesh):
    for z in (18.0, 28.0):
        for x, y in ((-53.0, -33.0), (-53.0, 33.0), (53.0, -33.0), (53.0, 33.0),
                     (-51.0, -31.0), (-51.0, 31.0), (51.0, -31.0), (51.0, 31.0)):
            if not _near_vertex(mesh, (x, y, z)):
                return False
    for z in (18.3, 22.0, 27.7):
        solid = ((52.0, 0.0, z), (-52.0, 0.0, z), (0.0, 32.0, z), (0.0, -32.0, z))
        voids = ((50.5, 0.0, z), (-50.5, 0.0, z), (0.0, 30.5, z), (0.0, -30.5, z),
                 (54.0, 0.0, z), (-54.0, 0.0, z), (0.0, 34.0, z), (0.0, -34.0, z))
        if not all(_point_inside(mesh, point) for point in solid):
            return False
        if any(_point_inside(mesh, point) for point in voids):
            return False
    return True


def _shell_ok(mesh: Mesh):
    solid = ((0.0, 35.0, 2.0), (58.5, 0.0, 10.0), (-58.5, 0.0, 24.0), (0.0, -38.5, 12.0))
    voids = ((0.0, 35.0, 10.0), (55.0, 0.0, 10.0), (-55.0, 0.0, 10.0), (0.0, -35.0, 10.0))
    return all(_point_inside(mesh, point) for point in solid) and not any(
        _point_inside(mesh, point) for point in voids
    )


def evaluate() -> bool:
    path = OUTPUT_ROOT / OUTPUT_NAME
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    triangles = _parse_stl(path)
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
    if _topology_components(mesh) != 1:
        return False
    if abs(abs(_signed_volume(mesh)) - EXPECTED_VOLUME_MM3) > 80.0:
        return False
    return _shell_ok(mesh) and _bosses_ok(mesh) and _slots_ok(mesh) and _ribs_ok(mesh) and _ledge_ok(mesh)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
