"""Build `ground_truth/answer.blend` for task LH05.

Open init_file/scene.blend, rename the 4 auto-numbered bones on `Rig`
to the semantic names `Bone.Root`, `Bone.A`, `Bone.B`, `Bone.Tip` by
walking the parent chain from root to tip, then save.

Strategy to avoid mid-rename name collisions: first rename every bone
to a unique temporary tag (`__tmp_0`, `__tmp_1`, ...) along the chain,
then assign the final semantic names.

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


FINAL_NAMES = ["Bone.Root", "Bone.A", "Bone.B", "Bone.Tip"]


def chain_root_to_tip(bones):
    """Return bones ordered along the parent chain from root to tip.
    Assumes a single linear chain."""
    # Root: the only bone without a parent.
    roots = [b for b in bones if b.parent is None]
    if len(roots) != 1:
        raise RuntimeError(
            f"expected exactly 1 root bone, found {len(roots)}: "
            f"{[b.name for b in roots]}")
    # Map parent.name -> [children].
    children_of = {}
    for b in bones:
        if b.parent is not None:
            children_of.setdefault(b.parent.name, []).append(b)

    ordered = []
    cur = roots[0]
    while cur is not None:
        ordered.append(cur)
        kids = children_of.get(cur.name, [])
        if len(kids) == 0:
            cur = None
        elif len(kids) == 1:
            cur = kids[0]
        else:
            raise RuntimeError(
                f"bone {cur.name} has {len(kids)} children; "
                f"expected a linear chain")
    return ordered


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

rig = bpy.data.objects["Rig"]
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = rig
rig.select_set(True)

# Order bones by topology using Object-mode bones (data.bones).
ordered_object_bones = chain_root_to_tip(list(rig.data.bones))
ordered_names = [b.name for b in ordered_object_bones]
print(f"  chain (root->tip): {ordered_names}")

# Enter edit mode to rename via edit_bones (the renames propagate to
# data.bones, pose bones, and vertex-group references on child meshes).
bpy.ops.object.mode_set(mode="EDIT")
eb = rig.data.edit_bones

# Pass 1: temporary unique tags (avoids clashing with any existing
# `Bone.Root` etc. — although in this task none of those exist yet).
for idx, name in enumerate(ordered_names):
    eb[name].name = f"__tmp_{idx}"

# Pass 2: assign final semantic names in chain order.
for idx, final in enumerate(FINAL_NAMES):
    eb[f"__tmp_{idx}"].name = final

bpy.ops.object.mode_set(mode="OBJECT")

# Diagnostics.
print("  Rig bones after rename:")
for b in rig.data.bones:
    parent_name = b.parent.name if b.parent else None
    print(f"    {b.name}  parent={parent_name}")

skin = bpy.data.objects.get("Skin")
if skin is not None:
    print("  Skin vertex groups:")
    for vg in skin.vertex_groups:
        print(f"    {vg.name}")
    for m in skin.modifiers:
        obj_name = m.object.name if m.object else None
        print(f"    modifier: {m.name} ({m.type}) object={obj_name}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
