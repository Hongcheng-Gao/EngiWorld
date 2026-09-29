"""Build `ground_truth/answer.blend` for task HH01.

Rotate Arm2 by +30° around local Z, then solve for Arm3's local location so
that Arm3's world position equals its original value (0, 1, 0).

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import math
import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
arm2 = bpy.data.objects["Arm2"]
arm3 = bpy.data.objects["Arm3"]
bpy.context.view_layer.update()

original_arm3_world = arm3.matrix_world.translation.copy()

arm2.rotation_euler.z = math.radians(30.0)
bpy.context.view_layer.update()

arm3.location = arm2.matrix_world.inverted() @ original_arm3_world
bpy.context.view_layer.update()

print(f"  Arm3 world target: {tuple(original_arm3_world)}")
print(f"  Arm3 world actual: {tuple(arm3.matrix_world.translation)}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
