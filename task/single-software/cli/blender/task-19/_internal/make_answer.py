"""Build `ground_truth/answer.blend` for task EH01 - Spine IK Bend.

Opens init_file/scene.blend and scripts the full spine IK rig:
  - Armature `Spine` with 6 connected bones `Bone01..Bone06` along +Z,
    each length 0.5 BU, total 3 BU tall.
  - Empty `IK_Goal` at (0, 0, 3).
  - IK constraint on pose bone `Bone06` targeting `IK_Goal`, chain_count=6.
  - Keyframed animation on `IK_Goal.location` at frames 1, 15, 30 tracing
    forward/backward bend path.
  - All 3 location fcurves set to LINEAR extrapolation.

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


# Bone specification: 6 bones, each 0.5 BU tall, stacked along +Z.
BONE_ENDPOINTS = [
    ("Bone01", (0.0, 0.0, 0.0), (0.0, 0.0, 0.5)),
    ("Bone02", (0.0, 0.0, 0.5), (0.0, 0.0, 1.0)),
    ("Bone03", (0.0, 0.0, 1.0), (0.0, 0.0, 1.5)),
    ("Bone04", (0.0, 0.0, 1.5), (0.0, 0.0, 2.0)),
    ("Bone05", (0.0, 0.0, 2.0), (0.0, 0.0, 2.5)),
    ("Bone06", (0.0, 0.0, 2.5), (0.0, 0.0, 3.0)),
]

# IK_Goal keyframes: (frame, (x, y, z)).
GOAL_KEYFRAMES = [
    (1,   (0.0,  0.0, 3.0)),
    (15,  (1.5,  0.0, 2.5)),
    (30,  (-1.5, 0.0, 2.5)),
]


def build_rig():
    arm_data = bpy.data.armatures.new("SpineData")
    rig      = bpy.data.objects.new("Spine", arm_data)
    bpy.context.collection.objects.link(rig)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    created = []
    for name, head, tail in BONE_ENDPOINTS:
        eb = arm_data.edit_bones.new(name)
        eb.head = head
        eb.tail = tail
        created.append(eb)
    # Parent chain with physical connection.
    for i in range(1, len(created)):
        created[i].parent      = created[i - 1]
        created[i].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def build_ik_goal():
    empty = bpy.data.objects.new("IK_Goal", None)  # None -> EMPTY
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.5
    empty.location = (0.0, 0.0, 3.0)
    bpy.context.collection.objects.link(empty)
    return empty


def add_ik_constraint(rig, target_empty):
    pb = rig.pose.bones["Bone06"]
    con = pb.constraints.new("IK")
    con.name        = "IK"
    con.target      = target_empty
    con.chain_count = 6
    return con


def keyframe_goal(target_empty):
    """Keyframe IK_Goal.location at the specified frames, then set all
    3 location fcurves to LINEAR extrapolation."""
    # Ensure current frame is clean before keyframing.
    scene = bpy.context.scene
    for frame, loc in GOAL_KEYFRAMES:
        scene.frame_set(frame)
        target_empty.location = loc
        # Insert keyframe on full location vector -> 3 fcurves.
        target_empty.keyframe_insert(data_path="location", frame=frame)

    # Set extrapolation to LINEAR on all 3 location fcurves.
    action = target_empty.animation_data.action
    for fc in action.fcurves:
        if fc.data_path == "location":
            fc.extrapolation = "LINEAR"
    return action


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

# Pin scene frame range so the eval and ground truth agree.
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = 30

rig          = build_rig()
target_empty = build_ik_goal()
ik_con       = add_ik_constraint(rig, target_empty)
action       = keyframe_goal(target_empty)

# Reset current frame and force an evaluation so IK solves at frame 1.
scene.frame_set(1)
bpy.context.view_layer.update()

# Diagnostics.
print("  Spine bones:")
for b in rig.data.bones:
    parent_name = b.parent.name if b.parent else None
    print(f"    {b.name} parent={parent_name} "
          f"head={tuple(b.head_local)} tail={tuple(b.tail_local)}")
print(f"  IK_Goal location = {tuple(target_empty.location)}")
print(f"  Bone06 constraints:")
for c in rig.pose.bones["Bone06"].constraints:
    tgt_name = c.target.name if c.target else None
    print(f"    {c.name} ({c.type}) target={tgt_name} "
          f"chain_count={getattr(c, 'chain_count', None)}")

print(f"  Action fcurves on IK_Goal:")
for fc in action.fcurves:
    kfs = [(int(round(kp.co.x)), float(kp.co.y)) for kp in fc.keyframe_points]
    print(f"    {fc.data_path}[{fc.array_index}] extrap={fc.extrapolation} "
          f"kfs={kfs}")

# Sample world tip position at each keyframe to verify IK reaches the goal.
depsgraph = bpy.context.evaluated_depsgraph_get()
for frame, expected in GOAL_KEYFRAMES:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rig_eval = rig.evaluated_get(depsgraph)
    pb = rig_eval.pose.bones["Bone06"]
    tail_world = rig_eval.matrix_world @ pb.tail
    print(f"  frame={frame} tip_world={tuple(round(v, 3) for v in tail_world)} "
          f"expected={expected}")

# Final frame reset.
scene.frame_set(1)
bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
