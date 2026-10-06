"""Build `ground_truth/output/scene.usda` for task IH03 - USD preview surface.

Opens `init_file/scene.blend` (two cubes Cube_A/Cube_B with Principled
BSDF materials Mat_A/Mat_B) and exports a USD scene via Blender 4.1's
`bpy.ops.wm.usd_export` with `generate_preview_surface=True` so the
resulting USDA contains `UsdPreviewSurface` shaders for each material.

Exporter parameters:
  filepath                 = ground_truth/output/scene.usda
  selected_objects_only    = False
  export_materials         = True
  export_mesh_colors       = False
  generate_preview_surface = True

The .usda suffix tells Blender to write ASCII USD (as opposed to .usdc
which would be binary Crate). The pure-Python evaluator at eval.py
parses the resulting text directly.

Also saves `ground_truth/answer.blend` (may be identical to init) and a
reference solution script `ground_truth/answer.py`.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os
import sys

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_DIR    = os.path.join(TASK_DIR, "ground_truth", "output")
OUT_USDA   = os.path.join(OUT_DIR, "scene.usda")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
REF_PY     = os.path.join(TASK_DIR, "ground_truth", "answer.py")

os.makedirs(OUT_DIR, exist_ok=True)


# -------------------------------------------------------------------------
# Open init scene and verify expected objects/materials are present.
# -------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
for name in ("Cube_A", "Cube_B"):
    if bpy.data.objects.get(name) is None:
        raise RuntimeError(f"init_file/scene.blend missing '{name}'")
for name in ("Mat_A", "Mat_B"):
    if bpy.data.materials.get(name) is None:
        raise RuntimeError(f"init_file/scene.blend missing material '{name}'")


# -------------------------------------------------------------------------
# Export USD (ASCII, because filepath suffix is .usda).
# -------------------------------------------------------------------------
bpy.ops.wm.usd_export(
    filepath=OUT_USDA,
    selected_objects_only=False,
    export_materials=True,
    export_mesh_colors=False,
    generate_preview_surface=True,
)
print(f"  saved -> {OUT_USDA}")


# -------------------------------------------------------------------------
# Save answer.blend (copy of init) for completeness.
# -------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, copy=True)
print(f"  saved -> {OUT_BLEND}")


# -------------------------------------------------------------------------
# Header dump for sanity.
# -------------------------------------------------------------------------
size = os.path.getsize(OUT_USDA)
print(f"  usda size   = {size} bytes")
print("  first 25 lines of scene.usda:")
with open(OUT_USDA, "r", encoding="utf-8", errors="replace") as fh:
    head = fh.readlines()[:25]
for l in head:
    print("    " + l.rstrip())


# -------------------------------------------------------------------------
# Reference script the testee could plausibly write.
# -------------------------------------------------------------------------
REF = '''\
"""Reference solution for task IH03 - USD preview surface export."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/scene.blend")
OUT   = "output/scene.usda"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.usd_export(
    filepath=OUT,
    selected_objects_only=False,
    export_materials=True,
    export_mesh_colors=False,
    generate_preview_surface=True,
)
# Writes ASCII USD at output/scene.usda with UsdPreviewSurface shaders.
'''
with open(REF_PY, "w", encoding="utf-8") as fh:
    fh.write(REF)
print(f"  saved -> {REF_PY}")


# -------------------------------------------------------------------------
# Self-check: run the evaluator against our fresh ground-truth USDA.
# -------------------------------------------------------------------------
sys.dont_write_bytecode = True
sys.path.insert(0, TASK_DIR)
try:
    import eval as eval_mod  # noqa: E402
    card = eval_mod._run_eval(OUT_USDA)
    print(card.render())
except Exception as exc:
    print(f"  [warn] eval self-check failed: {exc}")
