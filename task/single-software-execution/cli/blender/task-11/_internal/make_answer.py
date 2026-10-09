"""Build `ground_truth/answer.blend` for task BH05.

Opens init_file/scene.blend and scripts a small rigged chain end-to-end:
  - Armature `Rig` with 3 connected bones `BoneA -> BoneB -> BoneC`
    along +Y, each length 1 BU.
  - Empty `IK_Target` at (0, 3, 0).
  - IK constraint on pose bone `BoneC` targeting `IK_Target`,
    chain_count=3.
  - COPY_LOCATION constraint on pose bone `BoneB` targeting `IK_Target`,
    with a SCRIPTED driver on its `.influence` property reading
    `IK_Target.location.x`.

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


BONE_ENDPOINTS = [
    ("BoneA", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ("BoneB", (0.0, 1.0, 0.0), (0.0, 2.0, 0.0)),
    ("BoneC", (0.0, 2.0, 0.0), (0.0, 3.0, 0.0)),
]


def build_rig():
    arm_data = bpy.data.armatures.new("RigData")
    rig      = bpy.data.objects.new("Rig", arm_data)
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
    for i in range(1, len(created)):
        created[i].parent      = created[i - 1]
        created[i].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def build_ik_target():
    empty = bpy.data.objects.new("IK_Target", None)  # None -> EMPTY
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.5
    empty.location = (0.0, 3.0, 0.0)
    bpy.context.collection.objects.link(empty)
    return empty


def add_ik_constraint(rig, target_empty):
    pb = rig.pose.bones["BoneC"]
    con = pb.constraints.new("IK")
    con.name        = "IK"
    con.target      = target_empty
    con.chain_count = 3
    return con


def add_driven_copyloc(rig, target_empty):
    """COPY_LOCATION on BoneB; driver on influence reads IK_Target.location.x."""
    pb  = rig.pose.bones["BoneB"]
    con = pb.constraints.new("COPY_LOCATION")
    con.name    = "CopyLoc"
    con.target  = target_empty
    con.influence = 0.0

    # Add driver on the constraint's .influence. The FCurve lives on
    # rig.animation_data.drivers with data_path pointing at the pose bone
    # constraint chain.
    fcurve = con.driver_add("influence")
    drv = fcurve.driver
    drv.type       = "SCRIPTED"
    drv.expression = "max(0, min(1, x))"

    var = drv.variables.new()
    var.name = "x"
    var.type = "SINGLE_PROP"
    tgt = var.targets[0]
    tgt.id_type   = "OBJECT"
    tgt.id        = target_empty
    tgt.data_path = "location.x"
    return con, fcurve


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

rig          = build_rig()
target_empty = build_ik_target()
ik_con       = add_ik_constraint(rig, target_empty)
cp_con, fc   = add_driven_copyloc(rig, target_empty)

# Force re-evaluation so drivers resolve before save.
bpy.context.view_layer.update()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)

# Diagnostics.
print("  Rig bones:")
for b in rig.data.bones:
    parent_name = b.parent.name if b.parent else None
    print(f"    {b.name} parent={parent_name} "
          f"head={tuple(b.head_local)} tail={tuple(b.tail_local)}")
print(f"  IK_Target location = {tuple(target_empty.location)}")
print(f"  BoneC constraints:")
for c in rig.pose.bones["BoneC"].constraints:
    tgt_name = c.target.name if c.target else None
    print(f"    {c.name} ({c.type}) target={tgt_name} "
          f"chain_count={getattr(c, 'chain_count', None)}")
print(f"  BoneB constraints:")
for c in rig.pose.bones["BoneB"].constraints:
    tgt_name = c.target.name if c.target else None
    print(f"    {c.name} ({c.type}) target={tgt_name} "
          f"influence={c.influence}")
print(f"  driver expression = {fc.driver.expression!r}")
print(f"  driver var[0] path = "
      f"{fc.driver.variables[0].targets[0].data_path!r} on "
      f"{fc.driver.variables[0].targets[0].id.name}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
