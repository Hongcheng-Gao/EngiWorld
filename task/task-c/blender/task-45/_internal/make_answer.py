"""Build `ground_truth/answer.blend` for task LH01.

Opens init_file/scene.blend, repairs `Part` via bmesh ops:
  1. remove_doubles  -> merges the 2 loose duplicate vertices.
  2. holes_fill      -> closes the 3 open regions.
  3. recalc_face_normals -> ensures outward normals.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
obj = bpy.data.objects["Part"]
me  = obj.data

bm = bmesh.new(); bm.from_mesh(me)

bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.001)
bmesh.ops.holes_fill(bm, edges=list(bm.edges), sides=0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

non_man     = sum(1 for e in bm.edges if not e.is_manifold)
loose_verts = sum(1 for v in bm.verts if not v.link_edges)
loose_edges = sum(1 for e in bm.edges if not e.link_faces)
vol_signed  = bm.calc_volume(signed=True)

bm.to_mesh(me); me.update()
bm.free()

print(f"  after repair: verts={len(me.vertices)}, edges={len(me.edges)}, "
      f"faces={len(me.polygons)}")
print(f"  non-manifold edges: {non_man}")
print(f"  loose verts       : {loose_verts}")
print(f"  loose edges       : {loose_edges}")
print(f"  signed volume     : {vol_signed:.4f}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
