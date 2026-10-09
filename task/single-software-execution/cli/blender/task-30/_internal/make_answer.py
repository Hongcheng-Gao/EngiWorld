"""Build `ground_truth/answer.blend` for task HH03.

Strategy: 5 equispaced through-bores along X, equal end-margins. For plate
length Lx, the 5 bores and 2 end-gaps divide X into 6 equal segments:
bore k (k=1..5) sits at x = x_min + k * Lx / 6.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
INPUT_PATH  = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUTPUT_PATH = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


def make_cyl(name, radius, depth, location, rotation=(0, 0, 0), segments=48):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    me  = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location       = location
    obj.rotation_euler = rotation
    bpy.context.view_layer.update()
    return obj


def boolean_diff(target, cutter, mod_name):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new(mod_name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object    = cutter
    bpy.ops.object.modifier_apply(modifier=mod_name)
    bpy.data.objects.remove(cutter, do_unlink=True)


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

plate = bpy.data.objects["Plate"]
Lx    = plate.dimensions.x
x_min = plate.location.x - Lx / 2
step  = Lx / 6
for k in range(5):
    xk = x_min + (k + 1) * step
    cutter = make_cyl(f"_Bore{k}",
                      radius=0.10,
                      depth=plate.dimensions.z + 0.2,
                      location=(xk, plate.location.y, plate.location.z))
    boolean_diff(plate, cutter, f"Bore{k}")

bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_PATH)
print(f"  saved -> {OUTPUT_PATH}")
