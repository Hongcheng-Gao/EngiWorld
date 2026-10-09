"""Build init_file/scene.blend for task AH01 - GN Cable Sag.

Creates:
  - Empty `A` at (-3, 0, 2).
  - Empty `B` at (+3, 0, 2).
  - Mesh object `Cable` at origin with an empty mesh (0 verts, 0 faces).

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

# Scene settings: unit scale = 1, no camera/light.
bpy.context.scene.unit_settings.scale_length = 1.0

# Empty A at (-3, 0, 2).
empty_a = bpy.data.objects.new("A", None)
empty_a.empty_display_type = "PLAIN_AXES"
empty_a.location = (-3.0, 0.0, 2.0)
bpy.context.collection.objects.link(empty_a)

# Empty B at (+3, 0, 2).
empty_b = bpy.data.objects.new("B", None)
empty_b.empty_display_type = "PLAIN_AXES"
empty_b.location = (3.0, 0.0, 2.0)
bpy.context.collection.objects.link(empty_b)

# Cable mesh object (empty mesh, at origin).
cable_mesh = bpy.data.meshes.new("CableMesh")
cable_obj = bpy.data.objects.new("Cable", cable_mesh)
cable_obj.location = (0.0, 0.0, 0.0)
bpy.context.collection.objects.link(cable_obj)

print(f"  A location:     {tuple(empty_a.location)}")
print(f"  B location:     {tuple(empty_b.location)}")
print(f"  Cable verts:    {len(cable_mesh.vertices)} (expect 0)")
print(f"  Cable faces:    {len(cable_mesh.polygons)} (expect 0)")
print(f"  Cable modifiers: {len(cable_obj.modifiers)} (expect 0)")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
