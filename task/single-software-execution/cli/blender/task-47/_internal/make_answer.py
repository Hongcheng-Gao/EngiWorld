"""Build `ground_truth/answer.blend` for task LH03.

Opens init_file/scene.blend, fixes the broken driver on Driven.location.y:
  - Finds the driver FCurve on Driven.animation_data.drivers whose
    data_path == "location" and array_index == 1.
  - Repairs variable `var`'s target data_path so it resolves to
    `location.x` on `Source` (the init ships with a typo'd path).
  - Forces a scene re-evaluation and asserts Driven.location.y tracks
    Source.location.x.

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

driven = bpy.data.objects["Driven"]
source = bpy.data.objects["Source"]

ad = driven.animation_data
assert ad is not None, "Driven has no animation_data"

target_fcurve = None
for fc in ad.drivers:
    if fc.data_path == "location" and fc.array_index == 1:
        target_fcurve = fc
        break

assert target_fcurve is not None, \
    "no driver found on Driven.location[1]"

drv = target_fcurve.driver
fixed_any = False
for v in drv.variables:
    for t in v.targets:
        # Repair any broken path so that the variable resolves to
        # Source.location.x. In init the path is misspelled ("locaton.x").
        try:
            ok = t.id is not None \
                and t.id.path_resolve(t.data_path) is not None
        except Exception:
            ok = False
        if not ok:
            t.data_path = "location.x"
            fixed_any = True

assert fixed_any, "no broken data_path found to fix"

# Force a full re-evaluation so the driver picks up the corrected path.
scn = bpy.context.scene
bpy.context.view_layer.update()
scn.frame_set(scn.frame_current)

print(f"  Source.location.x = {source.location.x}")
print(f"  Driven.location.y = {driven.location.y}")
print(f"  driver expr       = {drv.expression!r}")
print(f"  driver var path   = "
      f"{drv.variables[0].targets[0].data_path!r}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
