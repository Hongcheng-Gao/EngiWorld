"""Build `ground_truth/answer.blend` for task FH02 - Rigid Body Bake to Keyframes.

Opens the init scene with 10 stacked rigid body cubes above a ground, runs
the rigid body simulation for frames 1..120, bakes the transforms to
keyframes on every cube, then removes the rigid body world so the motion is
driven purely by keyframes.

`bpy.ops.rigidbody.bake_to_keyframes` internally uses
`bpy.ops.anim.keyframe_insert_by_name` whose poll() fails in headless mode
(no VIEW_3D area). So we replicate the operator's effect by hand: bake the
point cache, sample `matrix_world` every frame, insert loc + rot_euler
keyframes, remove rigid body from each object, then remove the rigid body
world.

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


CUBE_COUNT     = 10
SIM_FRAME_END  = 120
BAKE_FRAME_END = 120


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
    scene = bpy.context.scene

    scene.frame_start = 1
    scene.frame_end   = SIM_FRAME_END
    scene.frame_set(1)

    rbw = scene.rigidbody_world
    if rbw is None:
        bpy.ops.rigidbody.world_add()
        rbw = scene.rigidbody_world
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end   = SIM_FRAME_END

    cubes = [bpy.data.objects[f"Cube_{i:02d}"] for i in range(CUBE_COUNT)]
    ground = bpy.data.objects.get("Ground")

    # Free any stale cache then bake the rigid body simulation.
    try:
        bpy.ops.ptcache.free_bake_all()
    except Exception as exc:
        print(f"  (ptcache.free_bake_all raised {exc!r}, continuing)")

    with bpy.context.temp_override(scene=scene, point_cache=rbw.point_cache):
        bpy.ops.ptcache.bake_all(bake=True)

    for c in cubes:
        c.rotation_mode = "XYZ"

    # Snapshot world matrices for every frame 1..BAKE_FRAME_END.
    snapshots = {}
    for f in range(1, BAKE_FRAME_END + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        snapshots[f] = [c.matrix_world.copy() for c in cubes]

    # Write loc + rot_euler keyframes on each cube for every frame.
    for f in range(1, BAKE_FRAME_END + 1):
        scene.frame_set(f)
        mats = snapshots[f]
        for c, mat in zip(cubes, mats):
            loc = mat.to_translation()
            euler = mat.to_euler("XYZ", c.rotation_euler)
            c.location       = loc
            c.rotation_euler = euler
            c.keyframe_insert(data_path="location",       frame=f)
            c.keyframe_insert(data_path="rotation_euler", frame=f)

    # Use LINEAR interpolation so baked motion reproduces faithfully.
    for c in cubes:
        action = c.animation_data.action
        for fcu in action.fcurves:
            for kp in fcu.keyframe_points:
                kp.interpolation = "LINEAR"

    # Remove rigid body from all objects, then remove the world entirely so
    # the motion is purely keyframe-driven. This matches the effect of
    # `bpy.ops.rigidbody.bake_to_keyframes` followed by removing the world.
    bpy.ops.object.select_all(action="DESELECT")
    for c in cubes:
        c.select_set(True)
    if ground is not None:
        ground.select_set(True)
    bpy.context.view_layer.objects.active = cubes[0]
    try:
        bpy.ops.rigidbody.objects_remove()
    except Exception as exc:
        print(f"  (rigidbody.objects_remove raised {exc!r}, continuing)")

    try:
        bpy.ops.rigidbody.world_remove()
    except Exception as exc:
        print(f"  (rigidbody.world_remove raised {exc!r}, trying attr set)")
        scene.rigidbody_world = None

    # Sanity dump: Z positions at frames 1 and BAKE_FRAME_END.
    scene.frame_set(1)
    bpy.context.view_layer.update()
    print("  --- frame 1 ---")
    for c in cubes:
        z = c.matrix_world.translation.z
        print(f"    {c.name}: z = {z:.4f}")

    scene.frame_set(BAKE_FRAME_END)
    bpy.context.view_layer.update()
    print(f"  --- frame {BAKE_FRAME_END} ---")
    for c in cubes:
        z = c.matrix_world.translation.z
        print(f"    {c.name}: z = {z:.4f}")

    scene.frame_set(1)

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  rigidbody_world = {scene.rigidbody_world}")
    print(f"  saved -> {OUT_PATH}")


main()
