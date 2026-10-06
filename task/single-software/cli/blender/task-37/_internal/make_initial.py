"""Build `init_file/lib/characters.blend` and `init_file/scene.blend` for
task JH01.

Produces:
  - `init_file/lib/characters.blend`: a Blender library file containing a
    Collection named `Hero` with one mesh object `HeroMesh` (a 2x2x2 cube).
    `HeroMesh` has a material `HeroMaterial` with a Principled BSDF whose
    Base Color is blue (0.1, 0.3, 0.8, 1.0). This is the ORIGINAL lib
    material; the lib is expected to remain byte-identical after the agent
    performs link + override + material change.
  - `init_file/lib/characters.blend.sha256`: sha256 of the above file,
    written as a hex digest + newline. The evaluator reads this to verify
    the lib was not mutated.
  - `init_file/scene.blend`: an empty scene — only the default Scene
    Collection, no objects, no meshes, no materials.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import hashlib
import os

import bmesh
import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
INIT_DIR = os.path.join(TASK_DIR, "init_file")
LIB_DIR  = os.path.join(INIT_DIR, "lib")
LIB_PATH = os.path.join(LIB_DIR, "characters.blend")
SHA_PATH = os.path.join(LIB_DIR, "characters.blend.sha256")
SCENE_PATH = os.path.join(INIT_DIR, "scene.blend")

os.makedirs(LIB_DIR, exist_ok=True)


def wipe_blend():
    """Remove every datablock so we get a clean slate."""
    # Delete objects via ops first (handles active selection quirks).
    if bpy.context.selected_objects or list(bpy.data.objects):
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=True)
    # Then purge datablocks explicitly.
    for blk in (bpy.data.objects, bpy.data.meshes, bpy.data.curves,
                bpy.data.cameras, bpy.data.lights, bpy.data.materials,
                bpy.data.images, bpy.data.textures, bpy.data.armatures):
        for d in list(blk):
            blk.remove(d)
    # Remove every non-master collection.
    master = bpy.context.scene.collection
    for c in list(bpy.data.collections):
        # Unlink from master if linked
        if c.name in master.children:
            master.children.unlink(c)
        bpy.data.collections.remove(c)


def build_lib():
    """Populate the current .blend with the Hero collection + HeroMesh cube +
    blue HeroMaterial."""
    wipe_blend()

    # Build the cube mesh via bmesh so we control the name precisely.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new("HeroMeshData")
    bm.to_mesh(me)
    bm.free()

    obj = bpy.data.objects.new("HeroMesh", me)

    # Create the Hero collection and link the object into it.
    hero_coll = bpy.data.collections.new("Hero")
    bpy.context.scene.collection.children.link(hero_coll)
    hero_coll.objects.link(obj)

    # Blue Principled BSDF material.
    mat = bpy.data.materials.new("HeroMaterial")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    n_out = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_bsdf.inputs["Base Color"].default_value = (0.1, 0.3, 0.8, 1.0)
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

    # Assign material to slot 0 of the mesh datablock (so linking copies it).
    me.materials.append(mat)

    bpy.context.view_layer.update()
    return hero_coll, obj, mat


def build_empty_scene():
    """Empty scene: only Scene Collection, no objects/meshes/materials."""
    wipe_blend()


# ---------------------------------------------------------------------------
# Stage 1: library file
# ---------------------------------------------------------------------------
hero_coll, hero_obj, hero_mat = build_lib()

print("  --- library file ---")
print(f"  collection        : {hero_coll.name}")
print(f"  object            : {hero_obj.name} (type={hero_obj.type})")
print(f"  mesh data         : {hero_obj.data.name} "
      f"(verts={len(hero_obj.data.vertices)})")
print(f"  material          : {hero_mat.name}")
bsdf = hero_mat.node_tree.nodes["Principled BSDF"]
print(f"  base color        : "
      f"{tuple(bsdf.inputs['Base Color'].default_value)}")

bpy.ops.wm.save_as_mainfile(filepath=LIB_PATH)
print(f"  saved -> {LIB_PATH}")

# Compute SHA256 of the lib AFTER save.
with open(LIB_PATH, "rb") as fh:
    digest = hashlib.sha256(fh.read()).hexdigest()
with open(SHA_PATH, "w", encoding="utf-8") as fh:
    fh.write(digest + "\n")
print(f"  sha256            : {digest}")
print(f"  saved -> {SHA_PATH}")

# ---------------------------------------------------------------------------
# Stage 2: empty scene
# ---------------------------------------------------------------------------
build_empty_scene()

scene = bpy.context.scene
objs_in_scene = [o.name for o in scene.collection.all_objects]
print("  --- scene file ---")
print(f"  scene             : {scene.name}")
print(f"  objects in scene  : {objs_in_scene}")
print(f"  data.objects      : {[o.name for o in bpy.data.objects]}")
print(f"  data.meshes       : {[m.name for m in bpy.data.meshes]}")
print(f"  data.materials    : {[m.name for m in bpy.data.materials]}")
print(f"  data.collections  : {[c.name for c in bpy.data.collections]}")

bpy.ops.wm.save_as_mainfile(filepath=SCENE_PATH)
print(f"  saved -> {SCENE_PATH}")
