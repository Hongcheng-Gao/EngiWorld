"""Build `ground_truth/{answer.blend, output/character.glb, output/verify.blend}`
for task IH02 - glTF roundtrip with PBR.

Steps:
  1. Open `init_file/ch.blend` and save an `answer.blend` copy.
  2. Export the scene as a binary GLB to
     `ground_truth/output/character.glb` using
     `bpy.ops.export_scene.gltf(export_format='GLB', export_apply=True,
     export_materials='EXPORT')`.
  3. Clear the current blend (read factory settings with use_empty=True),
     re-import the GLB back into a fresh scene, and save as
     `ground_truth/output/verify.blend`.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os
import sys

import bpy


HERE         = os.path.dirname(os.path.abspath(__file__))
TASK_DIR     = os.path.dirname(HERE)
INPUT_PATH   = os.path.join(TASK_DIR, "init_file", "ch.blend")
OUT_ANSWER   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
OUT_GLB      = os.path.join(TASK_DIR, "ground_truth", "output", "character.glb")
OUT_VERIFY   = os.path.join(TASK_DIR, "ground_truth", "output", "verify.blend")
REF_PY       = os.path.join(TASK_DIR, "ground_truth", "answer.py")

os.makedirs(os.path.dirname(OUT_ANSWER), exist_ok=True)
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)


# -------------------------------------------------------------------------
# 1. Open init scene, save `answer.blend` sibling copy.
# -------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

# Sanity: confirm the scene has what we expect.
for name in ("Body", "Head", "Arms"):
    if bpy.data.objects.get(name) is None:
        raise RuntimeError(f"init_file/ch.blend missing object '{name}'")
for mat_name in ("Mat_Body", "Mat_Head", "Mat_Arms"):
    if bpy.data.materials.get(mat_name) is None:
        raise RuntimeError(
            f"init_file/ch.blend missing material '{mat_name}'")

# Save `answer.blend` (exact copy of the init scene).
bpy.ops.wm.save_as_mainfile(filepath=OUT_ANSWER, copy=True)
print(f"  saved -> {OUT_ANSWER}")


# -------------------------------------------------------------------------
# 2. Export GLB (binary glTF 2.0) with materials + baked geometry.
# -------------------------------------------------------------------------
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format="GLB",
    export_apply=True,
    export_materials="EXPORT",
)
glb_size = os.path.getsize(OUT_GLB)
print(f"  saved -> {OUT_GLB}  ({glb_size} bytes)")

# Quick GLB header sanity dump.
import struct as _st
with open(OUT_GLB, "rb") as fh:
    header = fh.read(12)
magic   = header[:4]
version = _st.unpack("<I", header[4:8])[0]
length  = _st.unpack("<I", header[8:12])[0]
print(f"  glb magic   = {magic!r}")
print(f"  glb version = {version}")
print(f"  glb length  = {length} (file size={glb_size})")


# -------------------------------------------------------------------------
# 3. Clear the current blend and re-import the GLB into a fresh scene.
# -------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

# Belt-and-braces: remove any residual datablocks that a fresh empty
# Blender may still carry (it should be empty with use_empty=True but we
# want to be defensive so the reimport is a truly clean slate).
for blk in (bpy.data.objects, bpy.data.meshes, bpy.data.curves,
            bpy.data.cameras, bpy.data.lights, bpy.data.images,
            bpy.data.materials, bpy.data.actions, bpy.data.armatures,
            bpy.data.collections):
    for d in list(blk):
        try:
            blk.remove(d)
        except Exception:
            pass

bpy.ops.import_scene.gltf(filepath=OUT_GLB)

# Dump imported objects + materials so we can eyeball the result.
print("--- reimported objects ---")
for ob in bpy.data.objects:
    mats = [m.name for m in ob.data.materials] if (
        ob.type == "MESH" and ob.data) else []
    print(f"  obj '{ob.name}' type={ob.type} mats={mats}")
print("--- reimported materials ---")
for mat in bpy.data.materials:
    nt = mat.node_tree
    p = None
    if mat.use_nodes and nt is not None:
        p = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    bc = tuple(p.inputs["Base Color"].default_value) if p else None
    print(f"  mat '{mat.name}': base_color={bc}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_VERIFY)
print(f"  saved -> {OUT_VERIFY}")


# -------------------------------------------------------------------------
# 4. Reference script the testee could plausibly write.
# -------------------------------------------------------------------------
REF = '''\
"""Reference solution for task IH02 - glTF roundtrip with PBR."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/ch.blend")
OUT_GLB    = "output/character.glb"
OUT_VERIFY = "output/verify.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)

# Export GLB.
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format="GLB",
    export_apply=True,
    export_materials="EXPORT",
)

# Fresh scene, then re-import to verify.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)
bpy.ops.wm.save_as_mainfile(filepath=OUT_VERIFY)
'''
with open(REF_PY, "w", encoding="utf-8") as fh:
    fh.write(REF)
print(f"  saved -> {REF_PY}")


# -------------------------------------------------------------------------
# 5. Self-check: run the evaluator against our fresh ground-truth files.
# -------------------------------------------------------------------------
sys.dont_write_bytecode = True
sys.path.insert(0, TASK_DIR)
try:
    import eval as eval_mod  # noqa: E402
    card = eval_mod._run_eval(
        answer_blend=OUT_ANSWER,
        glb_path=OUT_GLB,
        verify_blend=OUT_VERIFY,
    )
    print(card.render())
except Exception as exc:
    import traceback
    print(f"  [warn] eval self-check failed: {exc}")
    traceback.print_exc()
