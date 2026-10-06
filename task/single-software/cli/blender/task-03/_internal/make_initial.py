"""Build init_file/scene.blend for task AH03 -- Menger Sponge via Geometry Nodes.

An empty scene with a single mesh object named `Sponge` at the world origin.
`Sponge.data` is an empty mesh (0 verts, 0 edges, 0 faces). No modifiers.
The testee will add a Geometry Nodes modifier that uses a Repeat Zone to
build a depth-3 Menger sponge.

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
    """Remove every object and purge common data-blocks for a minimal file."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.node_groups, bpy.data.materials,
                bpy.data.armatures, bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


clean_scene()

# Create empty mesh data-block and an object referencing it.
me  = bpy.data.meshes.new("SpongeMesh")
obj = bpy.data.objects.new("Sponge", me)
bpy.context.collection.objects.link(obj)
obj.location = (0.0, 0.0, 0.0)
obj.rotation_euler = (0.0, 0.0, 0.0)
obj.scale = (1.0, 1.0, 1.0)

# Sanity prints.
print(f"  vertices in Sponge.data: {len(me.vertices)} (expect 0)")
print(f"  modifiers on Sponge:     {len(obj.modifiers)} (expect 0)")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
