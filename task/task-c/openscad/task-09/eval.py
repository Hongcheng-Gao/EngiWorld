from __future__ import annotations

import os
import struct
from pathlib import Path


OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
OUTPUT_NAME = "task-029_output.stl"
TAB_CENTERS_X = [-42.0 + 12.0 * index for index in range(8)]
EXPECTED_BOUNDS = [[-48.0, -26.0, 0.0], [48.0, 26.0, 8.0]]
EXPECTED_VOLUME_MM3 = 25712.0
GEOMETRY_TOL = 0.15


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
    return tuple(round(float(value), 4) for value in point)


class Mesh:
    def __init__(self, triangles):
        self.triangles = triangles
        unique = {}
        for triangle in triangles:
            for point in triangle:
                unique[_vertex_key(point)] = tuple(float(value) for value in point)
        self.vertices = list(unique.values())
        self.mins = [min(point[axis] for point in self.vertices) for axis in range(3)]
        self.maxs = [max(point[axis] for point in self.vertices) for axis in range(3)]

    @property
    def extents(self):
        return [self.maxs[axis] - self.mins[axis] for axis in range(3)]


def _close(actual, expected, tolerance=GEOMETRY_TOL):
    return abs(float(actual) - float(expected)) <= tolerance


def _near_vertex(mesh: Mesh, target, tolerance=GEOMETRY_TOL):
    return any(
        all(abs(point[axis] - target[axis]) <= tolerance for axis in range(3))
        for point in mesh.vertices
    )


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _signed_volume(mesh: Mesh):
    total = 0.0
    for a, b, c in mesh.triangles:
        cross = _cross(b, c)
        total += a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]
    return total / 6.0


def _topology_ok(mesh: Mesh):
    vertex_ids = {}
    indexed_faces = []
    for triangle in mesh.triangles:
        face = []
        for point in triangle:
            key = _vertex_key(point)
            if key not in vertex_ids:
                vertex_ids[key] = len(vertex_ids)
            face.append(vertex_ids[key])
        if len(set(face)) != 3:
            return False
        indexed_faces.append(face)

    parent = list(range(len(indexed_faces)))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(first, second):
        root_first, root_second = find(first), find(second)
        if root_first != root_second:
            parent[root_second] = root_first

    edge_owners = {}
    for face_index, (a, b, c) in enumerate(indexed_faces):
        for edge in ((a, b), (b, c), (c, a)):
            key = tuple(sorted(edge))
            edge_owners.setdefault(key, []).append(face_index)
    if any(len(owners) != 2 for owners in edge_owners.values()):
        return False
    for owners in edge_owners.values():
        union(owners[0], owners[1])
    return len({find(index) for index in range(len(indexed_faces))}) == 1


def _ray_hit_x(y, z, triangle):
    a, b, c = triangle
    v0 = (c[1] - a[1], c[2] - a[2])
    v1 = (b[1] - a[1], b[2] - a[2])
    v2 = (y - a[1], z - a[2])
    denominator = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(denominator) < 1e-10:
        return None
    u = (v2[0] * v1[1] - v1[0] * v2[1]) / denominator
    v = (v0[0] * v2[1] - v2[0] * v0[1]) / denominator
    if u < -1e-9 or v < -1e-9 or u + v > 1.0 + 1e-9:
        return None
    return a[0] + u * (c[0] - a[0]) + v * (b[0] - a[0])


def _point_inside(mesh: Mesh, point):
    x, y, z = point
    hits = []
    for triangle in mesh.triangles:
        hit = _ray_hit_x(y, z, triangle)
        if hit is None or hit <= x + 1e-7:
            continue
        if all(abs(hit - previous) > 1e-6 for previous in hits):
            hits.append(hit)
    return len(hits) % 2 == 1


def _box_corners_present(mesh: Mesh, x_bounds, y_bounds, z_bounds):
    return all(
        _near_vertex(mesh, (x, y, z))
        for x in x_bounds
        for y in y_bounds
        for z in z_bounds
    )


def _tab_and_slot_ok(mesh: Mesh, center_x):
    tab_x = [center_x - 4.0, center_x + 4.0]
    slot_x = [center_x - 2.5, center_x + 2.5]
    if not _box_corners_present(mesh, tab_x, [20.0, 26.0], [5.0, 8.0]):
        return False
    if not _box_corners_present(mesh, slot_x, [22.0, 24.0], [0.0, 5.0]):
        return False

    tab_solid_probes = [
        (center_x + x_offset, y, z)
        for x_offset in (-3.5, 0.0, 3.5)
        for y in (20.5, 23.0, 25.5)
        for z in (5.5, 6.5, 7.5)
    ]
    if not all(_point_inside(mesh, probe) for probe in tab_solid_probes):
        return False

    tab_outside_probes = [
        (center_x - 4.5, 23.0, 6.5),
        (center_x + 4.5, 23.0, 6.5),
        (center_x, 19.5, 6.5),
        (center_x, 26.5, 6.5),
    ]
    if any(_point_inside(mesh, probe) for probe in tab_outside_probes):
        return False

    slot_void_probes = [
        (center_x + x_offset, y, z)
        for x_offset in (-2.0, 0.0, 2.0)
        for y in (22.25, 23.0, 23.75)
        for z in (0.25, 2.5, 4.75)
    ]
    if any(_point_inside(mesh, probe) for probe in slot_void_probes):
        return False

    slot_surround_probes = [
        (center_x - 3.0, 23.0, 2.5),
        (center_x + 3.0, 23.0, 2.5),
        (center_x, 21.5, 2.5),
        (center_x, 24.5, 2.5),
    ]
    return all(_point_inside(mesh, probe) for probe in slot_surround_probes)


def evaluate() -> bool:
    path = OUTPUT_ROOT / OUTPUT_NAME
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    triangles = _parse_stl(path)
    if len(triangles) < 80:
        return False
    mesh = Mesh(triangles)
    if len(mesh.vertices) < 32:
        return False
    if any(
        not _close(mesh.mins[axis], EXPECTED_BOUNDS[0][axis])
        or not _close(mesh.maxs[axis], EXPECTED_BOUNDS[1][axis])
        for axis in range(3)
    ):
        return False
    if not _topology_ok(mesh):
        return False
    if abs(abs(_signed_volume(mesh)) - EXPECTED_VOLUME_MM3) > 5.0:
        return False
    if not _point_inside(mesh, (0.0, 0.0, 2.5)):
        return False
    return all(_tab_and_slot_ok(mesh, center_x) for center_x in TAB_CENTERS_X)


if __name__ == "__main__":
    try:
        result = evaluate()
    except Exception:
        result = False
    print("True" if result else "False")
