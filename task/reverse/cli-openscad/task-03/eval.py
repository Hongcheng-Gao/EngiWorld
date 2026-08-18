from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
SPEC = {'bbox': [60, 45, 26], 'bbox_tol': 0.25, 'volume_range': [28000, 28800], 'min_triangles': 250, 'required_tokens': ['module heatsink']}


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
    return True


if __name__ == "__main__":
    try:
        print("True" if run() else "False")
    except Exception:
        print("False")
