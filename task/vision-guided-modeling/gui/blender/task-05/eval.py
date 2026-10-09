from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

OUTPUT_ROOT = Path(os.environ.get("EVAL_OUTPUT_ROOT", "/home/user/Desktop"))
SPEC = {'objects': {'Ground': {'type': 'MESH', 'dimensions': [20, 20, 0], 'material_min': 1}, 'Building_00': {'type': 'MESH', 'location': [-8, -4, 1.5], 'dimensions': [2, 2, 3], 'material_min': 1}, 'Building_01': {'type': 'MESH', 'location': [-4, -4, 3], 'dimensions': [2, 2, 6], 'material_min': 1}, 'Building_02': {'type': 'MESH', 'location': [0, -4, 4.5], 'dimensions': [2, 2, 9], 'material_min': 1}, 'Building_03': {'type': 'MESH', 'location': [4, -4, 6], 'dimensions': [2, 2, 12], 'material_min': 1}, 'Building_04': {'type': 'MESH', 'location': [8, -4, 2], 'dimensions': [2, 2, 4], 'material_min': 1}, 'Building_05': {'type': 'MESH', 'location': [-8, 4, 3.5], 'dimensions': [2, 2, 7], 'material_min': 1}, 'Building_06': {'type': 'MESH', 'location': [-4, 4, 5], 'dimensions': [2, 2, 10], 'material_min': 1}, 'Building_07': {'type': 'MESH', 'location': [0, 4, 2.5], 'dimensions': [2, 2, 5], 'material_min': 1}, 'Building_08': {'type': 'MESH', 'location': [4, 4, 4], 'dimensions': [2, 2, 8], 'material_min': 1}, 'Building_09': {'type': 'MESH', 'location': [8, 4, 5.5], 'dimensions': [2, 2, 11], 'material_min': 1}, 'Camera': {'type': 'CAMERA', 'location': [15, -15, 20]}, 'Sun': {'type': 'LIGHT', 'location': [5, -5, 15]}}, 'object_count_min': 13}


def close_vec(actual, expected, tol=0.04):
    return len(actual) == len(expected) and all(abs(float(a) - float(b)) <= tol for a, b in zip(actual, expected))


def run():
    answer = OUTPUT_ROOT / "answer.blend"
    blender = shutil.which("blender") or "/usr/local/bin/blender"
    if not answer.is_file() or answer.stat().st_size < 10000 or not Path(blender).exists():
        return False
    with tempfile.TemporaryDirectory(prefix="reverse_blender_eval_") as tmp:
        tmp = Path(tmp)
        report = tmp / "report.json"
        inspector = tmp / "inspect.py"
        inspector.write_text(r'''
import bpy
import json
import sys


def components(mesh):
    if not mesh.vertices:
        return 0
    adjacency = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = set()
    count = 0
    for start in range(len(adjacency)):
        if start in seen:
            continue
        count += 1
        stack = [start]
        seen.add(start)
        while stack:
            cur = stack.pop()
            for nxt in adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return count


objects = {}
for obj in bpy.context.scene.objects:
    item = {
        "type": obj.type,
        "location": list(obj.location),
        "dimensions": list(obj.dimensions),
    }
    if obj.type == "MESH":
        mesh = obj.data
        item.update({
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "polygons": len(mesh.polygons),
            "euler": len(mesh.vertices) - len(mesh.edges) + len(mesh.polygons),
            "components": components(mesh),
            "materials": [mat.name for mat in mesh.materials if mat],
        })
    objects[obj.name] = item
with open(sys.argv[-1], "w", encoding="utf-8") as handle:
    json.dump({"objects": objects}, handle)
''', encoding="utf-8")
        proc = subprocess.run(
            [blender, "--background", str(answer), "--python", str(inspector), "--", str(report)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0 or not report.exists():
            return False
        objects = json.loads(report.read_text(encoding="utf-8"))["objects"]
    for name, expected in SPEC["objects"].items():
        actual = objects.get(name)
        if actual is None or actual.get("type") != expected.get("type", actual.get("type")):
            return False
        if "dimensions" in expected and not close_vec(actual["dimensions"], expected["dimensions"]):
            return False
        if "location" in expected and not close_vec(actual["location"], expected["location"]):
            return False
        for key in ("vertices", "edges", "polygons"):
            if key + "_min" in expected and actual.get(key, 0) < expected[key + "_min"]:
                return False
        for key in ("euler", "components"):
            if key in expected and actual.get(key) != expected[key]:
                return False
        if "material_min" in expected and len(actual.get("materials", [])) < expected["material_min"]:
            return False
    if len(objects) < SPEC.get("object_count_min", len(SPEC["objects"])):
        return False
    return True


if __name__ == "__main__":
    try:
        print("True" if run() else "False")
    except Exception:
        print("False")
