"""Build `init_file/scene.blend` for task EH01 - Spine IK Bend.

Creates an empty scene that resembles a fresh Blender file: just a camera
and a light at reasonable positions. No armature, no `IK_Goal` empty,
no mesh objects. The testee is expected to script the whole rig + IK
animation from scratch.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.armatures, bpy.data.actions,
                bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


clean_scene()

# Camera
cam_data = bpy.data.cameras.new("Camera")
cam      = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location       = (7.36, -6.93, 4.96)
cam.rotation_euler = (1.1093, 0.0, 0.8149)

# Light
light_data = bpy.data.lights.new("Light", type="POINT")
light      = bpy.data.objects.new("Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (4.08, 1.0, 5.9)

# Diagnostics
print("  Initial scene objects:")
for o in bpy.data.objects:
    print(f"    {o.name}  type={o.type}  loc={tuple(o.location)}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
