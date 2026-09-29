"""Build `init_file/scene.blend` for task HH05.

A 4.0 x 2.0 x 0.2 rectangular plate named `Plate`, centred on the world
origin so its z extent is [-0.1, +0.1].

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


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights):
        for d in list(blk):
            blk.remove(d)


def new_cube(name, dims, location=(0.0, 0.0, 0.0)):
    sx, sy, sz = dims
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = location
    bpy.context.view_layer.update()
    return obj


clean_scene()
new_cube("Plate", dims=(4.0, 2.0, 0.2), location=(0.0, 0.0, 0.0))

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
