"""Build `ground_truth/answer.blend` for task EH02 - FK/IK Switch via Driver.

Opens init_file/scene.blend and wires up a FK/IK switch:
  - Adds an IK constraint on pose bone `Tip` targeting the `IKTarget` empty,
    chain_count=3, influence=0.0 initially.
  - Adds a SCRIPTED driver on the IK constraint's `influence` property that
    reads the armature object's `ik_blend` custom property (expression `var`).
  - Sets a FK rotation on the `Upper` pose bone so FK tip position is
    clearly distinguishable from IK tip position (rotation_quaternion
    derived from Euler (0, 0.5, 0)).

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy
from mathutils import Euler

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def add_ik_constraint(rig, target_empty):
    pb = rig.pose.bones["Tip"]
    con = pb.constraints.new("IK")
    con.name        = "IK"
    con.target      = target_empty
    con.chain_count = 3
    con.influence   = 0.0  # driver will drive this.
    return con


def add_driver_on_influence(rig, ik_constraint):
    """Scripted driver on ik_constraint.influence reading rig['ik_blend']."""
    fcurve = ik_constraint.driver_add("influence")
    drv = fcurve.driver
    drv.type       = "SCRIPTED"
    drv.expression = "var"

    var = drv.variables.new()
    var.name = "var"
    var.type = "SINGLE_PROP"
    tgt = var.targets[0]
    tgt.id_type   = "OBJECT"
    tgt.id        = rig
    tgt.data_path = '["ik_blend"]'
    return fcurve


def set_fk_rotation(rig):
    """Apply a FK rotation to `Upper` pose bone so FK tip position
    differs from IK tip position.

    Pose-bone quaternions are in the bone's local rest-pose space. `Upper`
    runs along +Z in world, but its local Y-axis runs along the bone. So
    to visibly deflect the tip we rotate around the bone-local X-axis
    (i.e. euler (pitch, roll, yaw) = (0.5, 0, 0))."""
    pb = rig.pose.bones["Upper"]
    pb.rotation_mode = "QUATERNION"
    euler = Euler((0.5, 0.0, 0.0), "XYZ")
    pb.rotation_quaternion = euler.to_quaternion()
    # Keyframe on frame 1 so the FK baseline is stored in the file.
    pb.keyframe_insert(data_path="rotation_quaternion", frame=1)
    return pb


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

rig          = bpy.data.objects["Rig"]
target_empty = bpy.data.objects["IKTarget"]

ik_con = add_ik_constraint(rig, target_empty)
fcurve = add_driver_on_influence(rig, ik_con)
upper_pb = set_fk_rotation(rig)

# Leave ik_blend at 0 by default.
rig["ik_blend"] = 0.0

# Force re-evaluation so drivers resolve before save.
rig.update_tag()
bpy.context.view_layer.update()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)

# Diagnostics.
print("  Rig bones:")
for b in rig.data.bones:
    parent_name = b.parent.name if b.parent else None
    print(f"    {b.name} parent={parent_name} "
          f"head={tuple(b.head_local)} tail={tuple(b.tail_local)}")
print(f"  IKTarget location = {tuple(target_empty.location)}")
print(f"  Rig['ik_blend'] = {rig['ik_blend']}")

print(f"  Tip constraints:")
for c in rig.pose.bones["Tip"].constraints:
    tgt_name = c.target.name if c.target else None
    print(f"    {c.name} ({c.type}) target={tgt_name} "
          f"chain_count={getattr(c, 'chain_count', None)} "
          f"influence={c.influence}")

print(f"  Upper pose rotation_quaternion = {tuple(upper_pb.rotation_quaternion)}")
print(f"  driver expression = {fcurve.driver.expression!r}")
print(f"  driver var[0] path = "
      f"{fcurve.driver.variables[0].targets[0].data_path!r} on "
      f"{fcurve.driver.variables[0].targets[0].id.name}")

# Sample tip positions at each ik_blend value for sanity.
import mathutils
for b in (0.0, 0.5, 1.0):
    rig["ik_blend"] = float(b)
    rig.update_tag()
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    deps.update()
    rig_eval = rig.evaluated_get(deps)
    pb = rig_eval.pose.bones["Tip"]
    tail_world = rig_eval.matrix_world @ pb.tail
    print(f"  ik_blend={b} tip_world=({tail_world.x:.3f}, "
          f"{tail_world.y:.3f}, {tail_world.z:.3f})")

# Reset to default.
rig["ik_blend"] = 0.0
rig.update_tag()
bpy.context.view_layer.update()

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
