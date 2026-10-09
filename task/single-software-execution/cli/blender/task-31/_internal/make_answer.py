"""Build `ground_truth/answer.blend` for task HH04.

Open init, duplicate `HighPoly` as `LowPoly`, add a Decimate (COLLAPSE) modifier
with ratio = 1000/initial_face_count, apply it, remove the HighPoly object,
save. The result is a decimated, closed-manifold version at the world origin.

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

TARGET_FACES = 1000

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

hp = bpy.data.objects["HighPoly"]
src_faces = len(hp.data.polygons)
print(f"  HighPoly face count (init): {src_faces}")

# Create a new object sharing a copy of the mesh, then rename.
new_mesh = hp.data.copy()
new_mesh.name = "LowPolyMesh"
lp = bpy.data.objects.new("LowPoly", new_mesh)
bpy.context.collection.objects.link(lp)
lp.location = (0.0, 0.0, 0.0)
lp.rotation_euler = (0.0, 0.0, 0.0)
lp.scale = (1.0, 1.0, 1.0)

# Remove the original HighPoly object (and its mesh datablock).
hp_mesh = hp.data
bpy.data.objects.remove(hp, do_unlink=True)
if hp_mesh.users == 0:
    bpy.data.meshes.remove(hp_mesh)

# Apply decimation via modifier.
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = lp
lp.select_set(True)

ratio = TARGET_FACES / float(src_faces)
mod = lp.modifiers.new("Decimate", "DECIMATE")
mod.decimate_type = "COLLAPSE"
mod.ratio         = ratio
mod.use_collapse_triangulate = False
print(f"  Decimate ratio   = {ratio:.6f}")

bpy.ops.object.modifier_apply(modifier="Decimate")

# Stats after.
me = lp.data
bm = bmesh.new(); bm.from_mesh(me)
non_man     = sum(1 for e in bm.edges if not e.is_manifold)
loose_verts = sum(1 for v in bm.verts if not v.link_edges)
loose_edges = sum(1 for e in bm.edges if not e.link_faces)
xs = [v.co.x for v in bm.verts]
ys = [v.co.y for v in bm.verts]
zs = [v.co.z for v in bm.verts]
bbox = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
vol = bm.calc_volume(signed=False)
bm.free()

print(f"  LowPoly: verts={len(me.vertices)}, edges={len(me.edges)}, "
      f"faces={len(me.polygons)}")
print(f"  non-manifold edges: {non_man}")
print(f"  loose verts       : {loose_verts}")
print(f"  loose edges       : {loose_edges}")
print(f"  bbox dims: ({bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f})")
print(f"  volume   : {vol:.6f}")
print(f"  modifiers remaining: {len(lp.modifiers)}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
