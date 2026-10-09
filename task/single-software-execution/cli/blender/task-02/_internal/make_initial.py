"""Build init_file/scene.blend for task AH02 - Simulation Zone Confetti.

Creates:
  - Mesh object `Emitter` at (0, 0, 5), XY scale = 2 (spans a 4 BU square at z=5).
  - Mesh object `Ground`  at (0, 0, 0), XY scale = 5 (visual ground plane).
  - Scene frame range [1, 60], fps = 24.
  - Emitter has NO geometry nodes modifier yet.

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
                bpy.data.lights, bpy.data.node_groups):
        for d in list(blk):
            blk.remove(d)


clean_scene()

# Scene settings.
bpy.context.scene.unit_settings.scale_length = 1.0
bpy.context.scene.render.fps = 24
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 60
bpy.context.scene.frame_set(1)


def _add_plane(name, location, xy_scale):
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.name = name + "Mesh"
    obj.scale = (xy_scale, xy_scale, 1.0)
    # Apply scale so the mesh vertices are at the final scale.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


# Emitter plane: centered at (0, 0, 5), spans 4x4 BU (xy_scale = 2 on
# size=2 plane -> 4 BU edge length).
emitter = _add_plane("Emitter", (0.0, 0.0, 5.0), 2.0)

# Ground plane: centered at (0, 0, 0), spans 10x10 BU.
ground = _add_plane("Ground", (0.0, 0.0, 0.0), 5.0)

print(f"  Emitter location:   {tuple(emitter.location)}")
print(f"  Emitter verts:      {len(emitter.data.vertices)}")
print(f"  Emitter modifiers:  {len(emitter.modifiers)} (expect 0)")
print(f"  Ground  location:   {tuple(ground.location)}")
print(f"  Ground  verts:      {len(ground.data.vertices)}")
print(f"  Frame range:        [{bpy.context.scene.frame_start}, "
      f"{bpy.context.scene.frame_end}]  fps={bpy.context.scene.render.fps}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
