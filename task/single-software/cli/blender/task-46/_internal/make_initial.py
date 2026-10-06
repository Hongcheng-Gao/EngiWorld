"""Build `init_file/scene.blend` for task LH02.

Scene:
  - `Body`: a 2x2x2 cube with TWO modifiers in the wrong order:
      index 0: Boolean (DIFFERENCE, object=Cutter)
      index 1: Subdivision Surface (viewport levels=2, render levels=2)
    This order causes the Boolean to cut the crude cube and then Subsurf
    smooths the cut mesh — which produces jagged / non-manifold topology
    around the boolean intersection because Subsurf operates on the
    already-cut cage.
  - `Cutter`: a 0.8 x 0.8 x 3.0 cube along Z used as the boolean operand,
    hidden from viewport and render.

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


def make_cube(name, sx, sy, sz):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=list(bm.verts))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    return obj


clean_scene()

body   = make_cube("Body",   2.0, 2.0, 2.0)
cutter = make_cube("Cutter", 0.8, 0.8, 3.0)
body.location   = (0.0, 0.0, 0.0)
cutter.location = (0.0, 0.0, 0.0)

cutter.hide_viewport = True
cutter.hide_render   = True

# Add modifiers in the WRONG order: Boolean first, Subsurf second.
bool_mod = body.modifiers.new("Boolean", "BOOLEAN")
bool_mod.operation = "DIFFERENCE"
bool_mod.object    = cutter
# keep solver at default (EXACT)

sub_mod = body.modifiers.new("Subsurf", "SUBSURF")
sub_mod.levels        = 3
sub_mod.render_levels = 3

# Sanity dump.
print(f"  Body modifiers (wrong order):")
for i, m in enumerate(body.modifiers):
    print(f"    [{i}] {m.name} ({m.type})")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
