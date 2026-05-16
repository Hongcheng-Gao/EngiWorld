"""Build `ground_truth/answer.blend` for task LH02.

Open init_file/scene.blend, reorder modifier stack so Subsurf is index 0 and
Boolean is index 1 (without applying either), save.

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

body = bpy.data.objects["Body"]
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = body
body.select_set(True)

# Find the Subsurf modifier and move it to index 0.
names = [m.name for m in body.modifiers]
types = [m.type for m in body.modifiers]
subsurf_idx = types.index("SUBSURF")

# Move Subsurf (currently at index 1) to index 0.
bpy.ops.object.modifier_move_to_index(
    modifier=body.modifiers[subsurf_idx].name,
    index=0,
)

print("  Body modifiers after reorder:")
for i, m in enumerate(body.modifiers):
    print(f"    [{i}] {m.name} ({m.type})")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
