import os
from pathlib import Path

import numpy as np
import trimesh

OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", "/home/user/Desktop"))
TARGET = "out.stl"
BBOX_TOL = 1.0
POINT_TOL = 1e-7

SPEC = {'bbox': [130, 80, 50], 'solid': [(5, 5, 5), (11, 11, 35), (119, 69, 35)], 'empty': [(65, 40, 35), (65, 0, 25)]}


def _load_mesh():
    path = OUTPUT_ROOT / TARGET
    if not path.exists() or path.stat().st_size <= 0:
        raise ValueError("missing STL output")
    mesh = trimesh.load(str(path), force="mesh")
    if getattr(mesh, "is_empty", True) or len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise ValueError("invalid STL output")
    return mesh


def _close_list(actual, expected, tol=BBOX_TOL):
    return all(abs(float(a) - float(b)) <= tol for a, b in zip(actual, expected))


def _ray_intersections(point, triangles, direction):
    origin = np.asarray(point, dtype=float)
    direction = np.asarray(direction, dtype=float)
    direction = direction / np.linalg.norm(direction)
    hits = []
    for tri in triangles:
        v0, v1, v2 = tri
        edge1 = v1 - v0
        edge2 = v2 - v0
        h = np.cross(direction, edge2)
        a = float(np.dot(edge1, h))
        if abs(a) < POINT_TOL:
            continue
        f = 1.0 / a
        s = origin - v0
        u = f * float(np.dot(s, h))
        if u < -POINT_TOL or u > 1.0 + POINT_TOL:
            continue
        q = np.cross(s, edge1)
        v = f * float(np.dot(direction, q))
        if v < -POINT_TOL or u + v > 1.0 + POINT_TOL:
            continue
        t = f * float(np.dot(edge2, q))
        if t > POINT_TOL:
            hits.append(round(t, 6))
    # Several triangles can meet at the same crossing. Count coincident hits once.
    hits = sorted(set(hits))
    return len(hits)


def _inside(point, triangles):
    dirs = [(1.0, 0.173, 0.097), (0.117, 1.0, 0.193), (0.071, 0.149, 1.0)]
    votes = 0
    for direction in dirs:
        if _ray_intersections(point, triangles, direction) % 2 == 1:
            votes += 1
    return votes >= 2


def evaluate():
    mesh = _load_mesh()
    extents = [float(v) for v in mesh.extents]
    if not _close_list(extents, SPEC["bbox"]):
        return False
    triangles = np.asarray(mesh.triangles, dtype=float)
    for point in SPEC.get("solid", []):
        if not _inside(point, triangles):
            return False
    for point in SPEC.get("empty", []):
        if _inside(point, triangles):
            return False
    return True


if __name__ == "__main__":
    try:
        ok = evaluate()
    except Exception:
        ok = False
    print("True" if ok else "False")
