"""Build `init_file/scene.blend` for task HH01.

Three box meshes Arm1 → Arm2 → Arm3 in a parent chain, all rotations zero,
stacked along +Y so Arm3 world = (0, 1, 0).

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights):
        for d in list(blk):
            blk.remove(d)


def new_box(name, dims, location=(0, 0, 0)):
    sx, sy, sz = dims
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = location
    bpy.context.view_layer.update()
    return obj


clean_scene()
arm1 = new_box("Arm1", dims=(0.30, 0.30, 0.10), location=(0.0, 0.0, 0.0))
arm2 = new_box("Arm2", dims=(0.20, 0.20, 0.10), location=(0.0, 0.5, 0.0))
arm3 = new_box("Arm3", dims=(0.20, 0.20, 0.10), location=(0.0, 1.0, 0.0))

arm2.parent = arm1
arm3.parent = arm2
arm2.matrix_parent_inverse.identity()
arm3.matrix_parent_inverse.identity()
arm2.location = (0.0, 0.5, 0.0)
arm3.location = (0.0, 0.5, 0.0)
arm2.rotation_euler = (0.0, 0.0, 0.0)
arm3.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
