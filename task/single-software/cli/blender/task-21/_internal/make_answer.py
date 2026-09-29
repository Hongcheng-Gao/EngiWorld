"""Build ground_truth/answer.blend for task EH03 - BVH Retarget + Bake.

Workflow:
  1. Open init_file/character.blend (rig `Character` with bones Root/Spine/Head).
  2. Import init_file/walk.bvh (creates a side armature object named `walk`
     with bones Hips/Spine/Head and an action `walk`).
  3. Retarget: copy the BVH action's fcurves to a new action on the
     Character rig, remapping source bone names to target bone names via
     the embedded MAPPING.  Hip location channels are copied onto the
     Root bone's `location` so the character physically walks forward.
  4. Bake the new action with NLA bake (visual-key) to produce a clean
     pose-only action on `Character`.
  5. Remove the BVH import artifact (armature object + its data + its
     action if unused).
  6. Save to ground_truth/answer.blend.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy


HERE      = os.path.dirname(os.path.abspath(__file__))
TASK_DIR  = os.path.dirname(HERE)
INIT_DIR  = os.path.join(TASK_DIR, "init_file")
GT_DIR    = os.path.join(TASK_DIR, "ground_truth")
CHAR_PATH = os.path.join(INIT_DIR, "character.blend")
BVH_PATH  = os.path.join(INIT_DIR, "walk.bvh")
OUT_PATH  = os.path.join(GT_DIR, "answer.blend")

os.makedirs(GT_DIR, exist_ok=True)

# The embedded mapping table the task prompt asks the model to honor.
# source (BVH bone)  ->  target (Character bone).
MAPPING = {
    "Hips":  "Root",
    "Spine": "Spine",
    "Head":  "Head",
}

# Root of the BVH hierarchy on the source side. Its `location` fcurves
# carry the forward translation, which we copy onto the mapped target
# bone so the character actually walks.
SOURCE_ROOT = "Hips"


# ---------------------------------------------------------------------------
# 1. open character.blend
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=CHAR_PATH)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 60

char = bpy.data.objects["Character"]
assert char.type == "ARMATURE"


# ---------------------------------------------------------------------------
# 2. import the BVH.  Use axis_forward="Y", axis_up="Z" so the BVH's
#    forward (+Z in its own space) becomes Blender world +Y (matches eval).
# ---------------------------------------------------------------------------
pre_objs = set(bpy.data.objects.keys())
bpy.ops.import_anim.bvh(filepath=BVH_PATH, axis_forward="Y", axis_up="Z")
new_objs = [o for n, o in bpy.data.objects.items() if n not in pre_objs]
assert len(new_objs) == 1 and new_objs[0].type == "ARMATURE", \
    f"expected one new armature from BVH import, got {new_objs}"
bvh_arm = new_objs[0]
print(f"  BVH armature: {bvh_arm.name}")

bvh_action = bvh_arm.animation_data.action
assert bvh_action is not None, "no action on imported BVH"
print(f"  BVH action: {bvh_action.name} with "
      f"{len(bvh_action.fcurves)} fcurves")


# ---------------------------------------------------------------------------
# 3. Retarget: build a fresh action on the Character rig, copy fcurves
#    with the source->target bone name rewrite.
# ---------------------------------------------------------------------------
char_action = bpy.data.actions.new(name="CharacterWalk")
if char.animation_data is None:
    char.animation_data_create()
char.animation_data.action = char_action

# Make target pose bones use XYZ Euler so rotation_euler is the right
# channel to key.
for tgt_name in MAPPING.values():
    pb = char.pose.bones.get(tgt_name)
    if pb is not None:
        pb.rotation_mode = "XYZ"


def _copy_fcurve(src_fc, new_data_path):
    new_fc = char_action.fcurves.new(
        data_path=new_data_path,
        index=src_fc.array_index,
        action_group=src_fc.group.name if src_fc.group else "",
    )
    # Keyframe points.
    n = len(src_fc.keyframe_points)
    new_fc.keyframe_points.add(count=n)
    for i, kp in enumerate(src_fc.keyframe_points):
        nkp = new_fc.keyframe_points[i]
        nkp.co            = kp.co
        nkp.interpolation = kp.interpolation
        nkp.handle_left   = kp.handle_left
        nkp.handle_right  = kp.handle_right
        nkp.handle_left_type  = kp.handle_left_type
        nkp.handle_right_type = kp.handle_right_type
    new_fc.update()
    return new_fc


copied = 0
skipped = 0
for src_fc in bvh_action.fcurves:
    dp = src_fc.data_path or ""
    # We only care about pose.bones[...] channels.
    if not dp.startswith('pose.bones["'):
        skipped += 1
        continue
    # Parse source bone name.
    try:
        src_name = dp.split('"', 2)[1]
    except IndexError:
        skipped += 1
        continue
    if src_name not in MAPPING:
        skipped += 1
        continue
    tgt_name = MAPPING[src_name]
    suffix = dp.split('"]', 1)[1]  # e.g. '.rotation_euler' or '.location'
    # Only keep rotation_euler for all bones, and location for the root.
    if suffix == ".rotation_euler":
        new_dp = f'pose.bones["{tgt_name}"].rotation_euler'
    elif suffix == ".location" and src_name == SOURCE_ROOT:
        new_dp = f'pose.bones["{tgt_name}"].location'
    else:
        skipped += 1
        continue
    _copy_fcurve(src_fc, new_dp)
    copied += 1

print(f"  retarget: copied {copied} fcurves, skipped {skipped}")


# ---------------------------------------------------------------------------
# 4. Bake the action via NLA bake (visual keying) so we end up with a
#    clean per-frame keyframed action on the Character armature, and so
#    downstream tools see concrete keyframes rather than channel-copy.
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = char
char.select_set(True)
bpy.ops.object.mode_set(mode="POSE")

bpy.ops.nla.bake(
    frame_start=scene.frame_start,
    frame_end=scene.frame_end,
    step=1,
    only_selected=False,
    visual_keying=True,
    clear_constraints=True,
    clear_parents=False,
    use_current_action=True,
    bake_types={"POSE"},
)
bpy.ops.object.mode_set(mode="OBJECT")

baked_action = char.animation_data.action
print(f"  baked action: {baked_action.name} with "
      f"{len(baked_action.fcurves)} fcurves")
kf_total = sum(len(fc.keyframe_points) for fc in baked_action.fcurves)
print(f"    total keyframes summed over fcurves: {kf_total}")


# ---------------------------------------------------------------------------
# 5. Strip the BVH import artifact.
# ---------------------------------------------------------------------------
bvh_arm_data = bvh_arm.data
bvh_action_name = bvh_action.name
bpy.data.objects.remove(bvh_arm, do_unlink=True)
if bvh_arm_data.users == 0:
    bpy.data.armatures.remove(bvh_arm_data)
# Remove the BVH-only action if nothing else is using it.
leftover = bpy.data.actions.get(bvh_action_name)
if leftover is not None and leftover.users == 0:
    bpy.data.actions.remove(leftover)
print("  removed BVH artifact armature + data + action")

# ---------------------------------------------------------------------------
# 6. Sanity: evaluate hip travel on the remaining character rig.
# ---------------------------------------------------------------------------
for f in (scene.frame_start, scene.frame_end):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = char.evaluated_get(deps)
    root_pb = ev.pose.bones.get("Root")
    h = ev.matrix_world @ root_pb.head
    print(f"  f={f}  Root head world = "
          f"({h.x:.3f}, {h.y:.3f}, {h.z:.3f})")

scene.frame_set(scene.frame_start)

# ---------------------------------------------------------------------------
# 7. Save.
# ---------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
