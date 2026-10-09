"""Build `ground_truth/answer.blend` for task JH02 - Append asset-library
material.

Steps:
  1. Open `init_file/scene.blend`.
  2. Append the material `StudioBrass` from `init_file/materials.blend`
     using `bpy.data.libraries.load(filepath, link=False)` - this copies
     the datablock into the current file (append semantics).
  3. Assert that `bpy.data.materials['StudioBrass'].library is None`
     (i.e. it is a local datablock, not a linked reference).
  4. Assign the appended material to `Target.material_slots[0]` by
     appending it to the mesh's material list.
  5. Save `ground_truth/answer.blend`.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INIT_DIR   = os.path.join(TASK_DIR, "init_file")
MATS_PATH  = os.path.abspath(os.path.join(INIT_DIR, "materials.blend"))
SCENE_PATH = os.path.abspath(os.path.join(INIT_DIR, "scene.blend"))
OUT_DIR    = os.path.join(TASK_DIR, "ground_truth")
OUT_PATH   = os.path.abspath(os.path.join(OUT_DIR, "answer.blend"))
os.makedirs(OUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Open the scene.
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=SCENE_PATH)
print(f"  opened scene      : {SCENE_PATH}")

target = bpy.data.objects.get("Target")
assert target is not None, "Target cube not found in scene.blend"
assert target.type == "MESH", f"Target is not a mesh (type={target.type})"
print(f"  target            : {target.name} (type={target.type})")
print(f"  target.slots before: {[s.material for s in target.material_slots]}")

# ---------------------------------------------------------------------------
# Append (link=False) the StudioBrass material from materials.blend.
# ---------------------------------------------------------------------------
with bpy.data.libraries.load(MATS_PATH, link=False) as (data_from, data_to):
    assert "StudioBrass" in data_from.materials, (
        f"'StudioBrass' not in lib; have {list(data_from.materials)}")
    data_to.materials = [n for n in data_from.materials if n == "StudioBrass"]

mat = bpy.data.materials.get("StudioBrass")
assert mat is not None, "StudioBrass not in bpy.data.materials after append"
assert mat.library is None, (
    f"StudioBrass unexpectedly linked (library={mat.library}); "
    f"expected local (append, not link)")
print(f"  appended material : {mat.name} (library={mat.library})")

# Verify Principled BSDF properties survived the append.
bsdf = None
for n in mat.node_tree.nodes:
    if n.type == "BSDF_PRINCIPLED":
        bsdf = n
        break
assert bsdf is not None, "StudioBrass has no Principled BSDF"
bc = tuple(bsdf.inputs["Base Color"].default_value)
metallic  = bsdf.inputs["Metallic"].default_value
roughness = bsdf.inputs["Roughness"].default_value
print(f"  base color        : {bc}")
print(f"  metallic          : {metallic}")
print(f"  roughness         : {roughness}")

# ---------------------------------------------------------------------------
# Assign to Target.material_slots[0] via mesh.materials.append.
# ---------------------------------------------------------------------------
target.data.materials.append(mat)

assert len(target.material_slots) >= 1, (
    f"Target has no material slots after append; "
    f"mesh.materials={list(target.data.materials)}")
assigned = target.material_slots[0].material
assert assigned is not None, "Target slot 0 still empty"
assert assigned.name == "StudioBrass", (
    f"Target slot 0 is '{assigned.name}', expected 'StudioBrass'")
print(f"  target.slot[0]    : {assigned.name} (library={assigned.library})")

bpy.context.view_layer.update()

# ---------------------------------------------------------------------------
# Save answer.blend.
# ---------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
