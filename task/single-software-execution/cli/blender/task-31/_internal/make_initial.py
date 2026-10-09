"""Build `init_file/scene.blend` for task HH04.

A dense, closed-manifold icosphere mesh `HighPoly` (subdivisions=5, radius=1.0)
at the world origin. The face count is ~20480 quadruple-subdivided triangles,
enough to require decimation to reach a 1000-face target.

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
bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
me  = bpy.data.meshes.new("HighPolyMesh")
obj = bpy.data.objects.new("HighPoly", me)
bpy.context.collection.objects.link(obj)
bm.to_mesh(me); bm.free()
obj.location = (0.0, 0.0, 0.0)
obj.rotation_euler = (0.0, 0.0, 0.0)
obj.scale = (1.0, 1.0, 1.0)

# Report stats for audit.
bm = bmesh.new(); bm.from_mesh(me)
non_man = sum(1 for e in bm.edges if not e.is_manifold)
xs = [v.co.x for v in bm.verts]
ys = [v.co.y for v in bm.verts]
zs = [v.co.z for v in bm.verts]
bbox = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
vol = bm.calc_volume(signed=False)
bm.free()

print(f"  HighPoly: verts={len(me.vertices)}, edges={len(me.edges)}, "
      f"faces={len(me.polygons)}")
print(f"  non-manifold edges: {non_man}")
print(f"  bbox dims: ({bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f})")
print(f"  volume   : {vol:.6f}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
