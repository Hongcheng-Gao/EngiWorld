"""Build ground_truth/answer.blend for task HH02.

Add a Bevel modifier with width=0.1, segments=2, profile=0.5 (circular),
limit_method='WEIGHT', then apply it so the stack is empty.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

block = bpy.data.objects["Block"]
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = block
block.select_set(True)

mod = block.modifiers.new("Bevel", "BEVEL")
mod.width        = 0.1
mod.segments     = 2
mod.profile      = 0.5
mod.limit_method = "WEIGHT"
bpy.ops.object.modifier_apply(modifier="Bevel")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
