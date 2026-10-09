"""Build `init_file/scene.blend` for task LH01.

Creates a single mesh object `Part`:
  - Base: cube size=2.0 with each face subdivided 2x2 (24 quads).
  - 3 quad faces removed from non-adjacent locations -> 12 non-manifold edges
    (4 per hole, no hole shares an edge with another).
  - 2 duplicate loose vertices placed exactly on existing mesh vertices
    (so bbox is preserved; agent must merge-by-distance to remove them).

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


def build():
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges),
                              cuts=1, use_grid_fill=True)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.faces.ensure_lookup_table()

    to_remove = []
    for f in bm.faces:
        c = f.calc_center_median()
        if   abs(c.z - 1.0) < 0.01 and c.x > 0 and c.y > 0:
            to_remove.append(f)                         # top +x+y quadrant
        elif abs(c.z + 1.0) < 0.01 and c.x < 0 and c.y < 0:
            to_remove.append(f)                         # bottom -x-y quadrant
        elif abs(c.x - 1.0) < 0.01 and c.y < 0 and c.z < 0:
            to_remove.append(f)                         # +x face, -y-z quadrant

    assert len(to_remove) == 3, \
        f"expected 3 removable faces, got {len(to_remove)}"

    for f in to_remove:
        bm.faces.remove(f)

    # Duplicate loose vertices at two existing positions (one on +x+y edge
    # midpoint z=0, one at (0,-1,-1) a bottom-front edge midpoint).
    dup_positions = [(1.0, 1.0, 0.0), (0.0, -1.0, -1.0)]
    for p in dup_positions:
        bm.verts.new(p)

    me  = bpy.data.meshes.new("PartMesh")
    obj = bpy.data.objects.new("Part", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (0.5, 0.0, 1.0)
    bpy.context.view_layer.update()
    return obj


clean_scene()
obj = build()

# Report defects so make_initial is auditable.
me = obj.data
bm = bmesh.new(); bm.from_mesh(me)
non_man     = sum(1 for e in bm.edges if not e.is_manifold)
loose_verts = sum(1 for v in bm.verts if not v.link_edges)
loose_edges = sum(1 for e in bm.edges if not e.link_faces)
bm.free()

print(f"  Part: verts={len(me.vertices)}, edges={len(me.edges)}, "
      f"faces={len(me.polygons)}")
print(f"  non-manifold edges: {non_man}")
print(f"  loose verts       : {loose_verts}")
print(f"  loose edges       : {loose_edges}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
