"""Build init_file/scene.blend for task HH02.

A 2x2x2 cube named `Block` with an edge-domain `bevel_weight_edge` attribute
set to 1.0 on the 4 vertical edges, 0.0 elsewhere.

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


clean_scene()

bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
me  = bpy.data.meshes.new("BlockMesh")
obj = bpy.data.objects.new("Block", me)
bpy.context.collection.objects.link(obj)
bm.to_mesh(me); bm.free()
obj.location = (0.0, 0.0, 0.0)

attr = me.attributes.get("bevel_weight_edge") or \
       me.attributes.new(name="bevel_weight_edge", type="FLOAT", domain="EDGE")
for i, e in enumerate(me.edges):
    v0 = me.vertices[e.vertices[0]].co
    v1 = me.vertices[e.vertices[1]].co
    is_vertical = abs(v0.x - v1.x) < 1e-5 and abs(v0.y - v1.y) < 1e-5
    attr.data[i].value = 1.0 if is_vertical else 0.0
me.update()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
