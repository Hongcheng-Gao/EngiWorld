"""Build init_file/scene.blend for task BH04.

An empty scene with a single mesh object named `Array` at the world origin.
`Array.data` is an empty mesh (0 verts, 0 edges, 0 faces). No modifiers.

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
    # Remove all objects.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    # Purge data-blocks so the .blend is truly minimal.
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.node_groups, bpy.data.materials,
                bpy.data.armatures):
        for d in list(blk):
            blk.remove(d)


clean_scene()

# Create empty mesh data-block and an object referencing it.
me  = bpy.data.meshes.new("ArrayMesh")      # starts with 0 verts / faces
obj = bpy.data.objects.new("Array", me)
bpy.context.collection.objects.link(obj)
obj.location = (0.0, 0.0, 0.0)

# Sanity prints.
print(f"  vertices in Array.data: {len(me.vertices)}")
print(f"  modifiers on Array:     {len(obj.modifiers)}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
