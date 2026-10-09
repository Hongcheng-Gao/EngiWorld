"""Build ground_truth/answer.blend + answer.abc for task KH03.

Pipeline:
  1. Open init_file/character.blend.
  2. Import init_file/walk.bvh -> creates a BVH armature with bones
     mixamorig_Hips/LeftUpLeg/LeftLeg and an action.
  3. Retarget: create a new action on Character, copy fcurves from the
     BVH action remapping source-joint -> target-bone names per MAPPING.
     Copy Hip location (all 3 axes) onto Character's Hip pose bone.
  4. Add an IK constraint on LowerLeg.L (chain_length=2) targeting a new
     empty IK.Foot.L. Add a float custom property `ik_switch` (0..1,
     default 1.0) on the Character armature OBJECT (not the armature data).
     Add a SCRIPTED driver on the IK constraint's `.influence` that reads
     Character["ik_switch"].
  5. Bake visual pose (frames 1..30) to keyframes on Character.
  6. Remove the BVH import-artifact armature and any orphan actions.
  7. Export Alembic: select the Body mesh, call
     bpy.ops.wm.alembic_export covering frames 1..30.
  8. Save ground_truth/answer.blend.

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
OUT_BLEND = os.path.join(GT_DIR, "answer.blend")
OUT_ABC   = os.path.join(GT_DIR, "answer.abc")

os.makedirs(GT_DIR, exist_ok=True)


# Mapping from BVH source joint names -> Character bone names.
MAPPING = {
    "mixamorig_Hips":      "Hip",
    "mixamorig_LeftUpLeg": "UpperLeg.L",
    "mixamorig_LeftLeg":   "LowerLeg.L",
}
SOURCE_ROOT = "mixamorig_Hips"
TARGET_ROOT = MAPPING[SOURCE_ROOT]


# ---------------------------------------------------------------------------
# 1. open character.blend
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=CHAR_PATH)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 30

char = bpy.data.objects["Character"]
body = bpy.data.objects["Body"]
assert char.type == "ARMATURE"
assert body.type == "MESH"


# ---------------------------------------------------------------------------
# 2. Import BVH.
# ---------------------------------------------------------------------------
pre_objs = set(bpy.data.objects.keys())
pre_actions = set(bpy.data.actions.keys())
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

# Print fcurve data paths for diagnostics.
for fc in bvh_action.fcurves[:20]:
    print(f"    src fcurve: {fc.data_path!r} idx={fc.array_index}")


# ---------------------------------------------------------------------------
# 3. Retarget: build a new action on Character and copy fcurves.
# ---------------------------------------------------------------------------
char_action = bpy.data.actions.new(name="CharacterWalk")
if char.animation_data is None:
    char.animation_data_create()
char.animation_data.action = char_action

# Ensure target pose bones use XYZ Euler so rotation_euler is the right
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
    if not dp.startswith('pose.bones["'):
        skipped += 1
        continue
    try:
        src_name = dp.split('"', 2)[1]
    except IndexError:
        skipped += 1
        continue
    if src_name not in MAPPING:
        skipped += 1
        continue
    tgt_name = MAPPING[src_name]
    suffix = dp.split('"]', 1)[1]   # e.g. '.rotation_euler' or '.location'
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
# 4. IK constraint + FK/IK switch driver.
# ---------------------------------------------------------------------------
# Create the IK target empty. Parent it to nothing (world-space) and place
# at the approximate foot location so initial IK pose is reasonable.
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = char
ik_target = bpy.data.objects.new("IK.Foot.L", None)
ik_target.empty_display_type = "PLAIN_AXES"
ik_target.empty_display_size = 0.25
ik_target.location = (0.0, 0.2, 0.0)
bpy.context.collection.objects.link(ik_target)

# Add IK constraint on LowerLeg.L with chain_count=2.
bpy.ops.object.mode_set(mode="POSE")
pb_lower = char.pose.bones["LowerLeg.L"]
ik_con = pb_lower.constraints.new("IK")
ik_con.name        = "IK"
ik_con.target      = ik_target
ik_con.chain_count = 2
ik_con.influence   = 1.0     # driver will override at runtime.
bpy.ops.object.mode_set(mode="OBJECT")

# Custom property `ik_switch` on the armature OBJECT (not the armature data).
char["ik_switch"] = 1.0
# UI metadata so it's clamped in [0, 1].
ui = char.id_properties_ui("ik_switch")
ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
          default=1.0, description="FK/IK blend (0=FK, 1=IK)")

# Driver on the IK constraint's influence reading Character["ik_switch"].
fcurve = ik_con.driver_add("influence")
drv = fcurve.driver
drv.type       = "SCRIPTED"
drv.expression = "var"

var = drv.variables.new()
var.name = "var"
var.type = "SINGLE_PROP"
tgt = var.targets[0]
tgt.id_type   = "OBJECT"
tgt.id        = char
tgt.data_path = '["ik_switch"]'

# Force depsgraph refresh before baking so driver takes effect.
char.update_tag()
bpy.context.view_layer.update()
bpy.context.evaluated_depsgraph_get().update()


# ---------------------------------------------------------------------------
# 5. Bake the visual pose to keyframes.
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = char
char.select_set(True)
bpy.ops.object.mode_set(mode="POSE")

# NOTE: clear_constraints=False preserves the IK constraint + driver so
# they stay inspectable in the saved file (eval check #5 needs them).
bpy.ops.nla.bake(
    frame_start=scene.frame_start,
    frame_end=scene.frame_end,
    step=1,
    only_selected=False,
    visual_keying=True,
    clear_constraints=False,
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
# 6. Strip the BVH import artifact armature + orphan action.
# ---------------------------------------------------------------------------
bvh_arm_data = bvh_arm.data
bvh_action_name = bvh_action.name
bpy.data.objects.remove(bvh_arm, do_unlink=True)
if bvh_arm_data.users == 0:
    bpy.data.armatures.remove(bvh_arm_data)
leftover = bpy.data.actions.get(bvh_action_name)
if leftover is not None and leftover.users == 0:
    bpy.data.actions.remove(leftover)
print("  removed BVH artifact armature + data + action")


# ---------------------------------------------------------------------------
# 7. Export Alembic.
# ---------------------------------------------------------------------------
# Ensure the evaluated depsgraph is up to date before export.
bpy.context.view_layer.update()
bpy.context.evaluated_depsgraph_get().update()

bpy.ops.object.select_all(action="DESELECT")
body.select_set(True)
bpy.context.view_layer.objects.active = body

# NOTE: vcolors=False avoids missing-color-layer errors in headless mode.
bpy.ops.wm.alembic_export(
    filepath=OUT_ABC,
    start=scene.frame_start,
    end=scene.frame_end,
    selected=True,
    flatten=False,
    uvs=True,
    packuv=False,
    normals=True,
    vcolors=False,
    face_sets=False,
    apply_subdiv=False,
)

if os.path.isfile(OUT_ABC):
    print(f"  saved ABC -> {OUT_ABC}  ({os.path.getsize(OUT_ABC)} bytes)")
else:
    print(f"  [warn] ABC not written to {OUT_ABC}")


# ---------------------------------------------------------------------------
# 8. Sanity: sample hip travel + body vertex travel.
# ---------------------------------------------------------------------------
for f in (scene.frame_start, scene.frame_end):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = char.evaluated_get(deps)
    hip_pb = ev.pose.bones.get("Hip")
    if hip_pb is not None:
        h = ev.matrix_world @ hip_pb.head
        print(f"  f={f}  Hip head world = "
              f"({h.x:.3f}, {h.y:.3f}, {h.z:.3f})")
    body_ev = body.evaluated_get(deps)
    if body_ev.data.vertices:
        v0 = body_ev.matrix_world @ body_ev.data.vertices[0].co
        print(f"         Body v0 world = "
              f"({v0.x:.3f}, {v0.y:.3f}, {v0.z:.3f})")

scene.frame_set(scene.frame_start)


# ---------------------------------------------------------------------------
# 9. Save.
# ---------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
