from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
SPEC = {'bbox': [52, 32, 3], 'bbox_tol': 0.25, 'volume_range': [4200, 4600], 'min_triangles': 500, 'required_tokens': ['module microfluidic_lid', 'module channel']}
SOLID_SAMPLES = [(0, -10, 2.5, False), (0, -5, 2.5, False), (0, 0, 2.5, False), (0, 5, 2.5, False), (0, 10, 2.5, False), (0, -10, 1.2, True), (0, -5, 1.2, True), (0, 0, 1.2, True), (0, 5, 1.2, True), (0, 10, 1.2, True), (0, -8.6, 2.5, True), (0, -3.6, 2.5, True), (0, 1.4, 2.5, True), (0, 6.4, 2.5, True), (0, 11.4, 2.5, True), (20, -7.5, 2.5, False), (-20, -2.5, 2.5, False), (20, 2.5, 2.5, False), (-20, 7.5, 2.5, False), (-20, -7.5, 2.5, True), (20, -2.5, 2.5, True), (-20, 2.5, 2.5, True), (20, 7.5, 2.5, True), (-20, -10, 0.8, False), (20, 10, 0.8, False), (-18, -10, 0.8, True), (18, 10, 0.8, True)]


def triangles(path):
    data = path.read_bytes()
    result = []
    if len(data) >= 84:
        count = struct.unpack("<I", data[80:84])[0]
        if 84 + count * 50 == len(data):
            for index in range(count):
                values = struct.unpack("<12fH", data[84 + index * 50:134 + index * 50])
                c = values[3:12]
                result.append(tuple((c[i], c[i + 1], c[i + 2]) for i in range(0, 9, 3)))
            return result
    vertices = []
    for line in data.decode("utf-8", errors="ignore").splitlines():
        fields = line.strip().split()
        if len(fields) == 4 and fields[0].lower() == "vertex":
            vertices.append(tuple(float(v) for v in fields[1:]))
            if len(vertices) == 3:
                result.append(tuple(vertices))
                vertices = []
    return result


def mesh_volume(faces):
    signed = 0.0
    for (a, b, c) in faces:
        signed += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
    return abs(signed)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _ray_triangle_distance(origin, face):
    direction = (1.0, 0.371390676, 0.217186234)
    edge1 = _sub(face[1], face[0])
    edge2 = _sub(face[2], face[0])
    h = _cross(direction, edge2)
    determinant = _dot(edge1, h)
    if abs(determinant) < 1e-10:
        return None
    inverse = 1.0 / determinant
    s = _sub(origin, face[0])
    u = inverse * _dot(s, h)
    if u < -1e-9 or u > 1.0 + 1e-9:
        return None
    q = _cross(s, edge1)
    v = inverse * _dot(direction, q)
    if v < -1e-9 or u + v > 1.0 + 1e-9:
        return None
    distance = inverse * _dot(edge2, q)
    return distance if distance > 1e-8 else None


def point_inside_mesh(point, faces):
    hits = sorted(
        distance
        for face in faces
        if (distance := _ray_triangle_distance(point, face)) is not None
    )
    unique_hits = []
    for distance in hits:
        if not unique_hits or abs(distance - unique_hits[-1]) > 1e-6:
            unique_hits.append(distance)
    return len(unique_hits) % 2 == 1

def run():
    answer = OUTPUT_ROOT / "answer.scad"
    openscad = shutil.which("openscad") or "/usr/bin/openscad"
    if not answer.is_file() or answer.stat().st_size < 100 or not Path(openscad).exists():
        return False
    source = answer.read_text(encoding="utf-8", errors="ignore")
    if not all(token in source for token in SPEC["required_tokens"]):
        return False
    with tempfile.TemporaryDirectory(prefix="reverse_scad_eval_") as tmp:
        mesh = Path(tmp) / "answer.stl"
        proc = subprocess.run([openscad, "-o", str(mesh), str(answer)], capture_output=True, text=True, timeout=120)
        if proc.returncode != 0 or not mesh.exists():
            return False
        faces = triangles(mesh)
    if len(faces) < SPEC["min_triangles"]:
        return False
    points = [point for face in faces for point in face]
    mins = [min(point[axis] for point in points) for axis in range(3)]
    maxs = [max(point[axis] for point in points) for axis in range(3)]
    extents = [maxs[i] - mins[i] for i in range(3)]
    if any(abs(a - b) > SPEC.get("bbox_tol", 0.25) for a, b in zip(extents, SPEC["bbox"])):
        return False
    volume = mesh_volume(faces)
    lo, hi = SPEC["volume_range"]
    if not (lo <= volume <= hi):
        return False
    for x, y, z, expected_solid in SOLID_SAMPLES:
        if point_inside_mesh((x, y, z), faces) != expected_solid:
            return False
    return True


if __name__ == "__main__":
    try:
        print("True" if run() else "False")
    except Exception:
        print("False")
