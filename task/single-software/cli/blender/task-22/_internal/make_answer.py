"""Build `ground_truth/answer.blend` for task EH04.

Opens init_file/scene.blend and attaches a driver to the Face mesh's
`smile` shape key value, reading the X-rotation (LOCAL_SPACE) of the
`ctrl_jaw` pose bone on `Rig`:

    smile = max(0, min(1, rx * 2))

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

face = bpy.data.objects["Face"]
rig  = bpy.data.objects["Rig"]

key = face.data.shape_keys
assert key is not None, "Face has no shape keys"
assert "smile" in key.key_blocks, "smile key block missing"

smile_kb = key.key_blocks["smile"]

# Add the driver on the `smile` key block's value.
fcurve = smile_kb.driver_add("value")
drv = fcurve.driver
drv.type       = "SCRIPTED"
drv.expression = "max(0, min(1, rx * 2))"

var = drv.variables.new()
var.name = "rx"
var.type = "TRANSFORMS"
tgt = var.targets[0]
tgt.id             = rig
tgt.bone_target    = "ctrl_jaw"
tgt.transform_type = "ROT_X"
tgt.transform_space = "LOCAL_SPACE"
# rotation_mode on a TRANSFORMS target controls how the driver converts
# the bone's quaternion into euler components before reading ROT_X.
# 'AUTO' (swing-twist) is fine here; be explicit for clarity.
try:
    tgt.rotation_mode = "AUTO"
except Exception:
    pass

# Make sure the bone itself is in XYZ mode so rotation_euler cleanly maps
# to ROT_X.
rig.pose.bones["ctrl_jaw"].rotation_mode = "XYZ"
rig.pose.bones["ctrl_jaw"].rotation_euler = (0.0, 0.0, 0.0)

# Force depsgraph refresh so the driver resolves before save.
rig.update_tag()
face.update_tag()
bpy.context.view_layer.update()
bpy.context.evaluated_depsgraph_get().update()

print(f"  driver type       = {drv.type}")
print(f"  driver expression = {drv.expression!r}")
print(f"  driver var[0].name            = {drv.variables[0].name!r}")
print(f"  driver var[0].type            = {drv.variables[0].type!r}")
print(f"  driver var[0].targets[0].id   = "
      f"{drv.variables[0].targets[0].id.name}")
print(f"  driver var[0].targets[0].bone = "
      f"{drv.variables[0].targets[0].bone_target!r}")
print(f"  driver var[0].targets[0].ttyp = "
      f"{drv.variables[0].targets[0].transform_type!r}")
print(f"  driver var[0].targets[0].tspc = "
      f"{drv.variables[0].targets[0].transform_space!r}")

# Sample the driven value at several rx values as a sanity check.
for rx in (-0.3, 0.0, 0.1, 0.5, 0.9):
    rig.pose.bones["ctrl_jaw"].rotation_euler = (rx, 0.0, 0.0)
    rig.update_tag()
    bpy.context.view_layer.update()
    bpy.context.evaluated_depsgraph_get().update()
    v = face.data.shape_keys.key_blocks["smile"].value
    print(f"  rx={rx:+.2f}  smile.value = {v:.4f}")

# Reset bone to neutral for the saved file.
rig.pose.bones["ctrl_jaw"].rotation_euler = (0.0, 0.0, 0.0)
rig.update_tag()
bpy.context.view_layer.update()
bpy.context.evaluated_depsgraph_get().update()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
