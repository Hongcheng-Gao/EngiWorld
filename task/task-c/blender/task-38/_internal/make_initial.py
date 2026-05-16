"""Build `init_file/materials.blend` and `init_file/scene.blend` for
task JH02 - Append asset-library material.

Produces:
  - `init_file/materials.blend`: a Blender file containing a single
    Material datablock named `StudioBrass`. The material uses nodes with
    a Principled BSDF whose Base Color = (0.8, 0.6, 0.2, 1.0),
    Metallic = 1.0, Roughness = 0.3. There are NO objects, meshes, or
    collections beyond the default Scene Collection.
  - `init_file/scene.blend`: a scene with a single cube `Target` at the
    origin whose material_slots is empty (no material assigned).

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
INIT_DIR = os.path.join(TASK_DIR, "init_file")
MATS_PATH  = os.path.join(INIT_DIR, "materials.blend")
SCENE_PATH = os.path.join(INIT_DIR, "scene.blend")

os.makedirs(INIT_DIR, exist_ok=True)


def wipe_blend():
    """Remove every datablock so we get a clean slate."""
    if bpy.context.selected_objects or list(bpy.data.objects):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=True)
    for blk in (bpy.data.objects, bpy.data.meshes, bpy.data.curves,
                bpy.data.cameras, bpy.data.lights, bpy.data.materials,
                bpy.data.images, bpy.data.textures, bpy.data.armatures):
        for d in list(blk):
            blk.remove(d)
    master = bpy.context.scene.collection
    for c in list(bpy.data.collections):
        if c.name in master.children:
            master.children.unlink(c)
        bpy.data.collections.remove(c)


def build_materials_file():
    """Create a single StudioBrass material datablock. No objects."""
    wipe_blend()

    mat = bpy.data.materials.new("StudioBrass")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_bsdf.inputs["Base Color"].default_value = (0.8, 0.6, 0.2, 1.0)
    n_bsdf.inputs["Metallic"].default_value   = 1.0
    n_bsdf.inputs["Roughness"].default_value  = 0.3
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

    # Mark the material as a fake-user datablock so it persists even
    # though no object references it in this file.
    mat.use_fake_user = True

    return mat


def build_scene_file():
    """Create a scene with a single cube `Target` and no material."""
    wipe_blend()

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new("TargetMesh")
    bm.to_mesh(me)
    bm.free()

    obj = bpy.data.objects.new("Target", me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (0.0, 0.0, 0.0)

    # Ensure mesh datablock has no materials at all.
    me.materials.clear()

    bpy.context.view_layer.update()
    return obj


# ---------------------------------------------------------------------------
# Stage 1: materials library file
# ---------------------------------------------------------------------------
mat = build_materials_file()

print("  --- materials file ---")
print(f"  material          : {mat.name}")
bsdf = mat.node_tree.nodes["Principled BSDF"]
print(f"  base color        : "
      f"{tuple(bsdf.inputs['Base Color'].default_value)}")
print(f"  metallic          : {bsdf.inputs['Metallic'].default_value}")
print(f"  roughness         : {bsdf.inputs['Roughness'].default_value}")
print(f"  data.objects      : {[o.name for o in bpy.data.objects]}")
print(f"  data.materials    : {[m.name for m in bpy.data.materials]}")
bpy.ops.wm.save_as_mainfile(filepath=MATS_PATH)
print(f"  saved -> {MATS_PATH}")

# ---------------------------------------------------------------------------
# Stage 2: scene file with Target cube, no material
# ---------------------------------------------------------------------------
target = build_scene_file()

print("  --- scene file ---")
scene = bpy.context.scene
print(f"  scene             : {scene.name}")
print(f"  object            : {target.name} (type={target.type})")
print(f"  mesh              : {target.data.name} "
      f"(verts={len(target.data.vertices)})")
print(f"  location          : {tuple(target.location)}")
print(f"  material_slots    : {list(target.material_slots)}")
print(f"  mesh.materials    : {[m.name if m else None for m in target.data.materials]}")
print(f"  data.objects      : {[o.name for o in bpy.data.objects]}")
print(f"  data.materials    : {[m.name for m in bpy.data.materials]}")

bpy.ops.wm.save_as_mainfile(filepath=SCENE_PATH)
print(f"  saved -> {SCENE_PATH}")
