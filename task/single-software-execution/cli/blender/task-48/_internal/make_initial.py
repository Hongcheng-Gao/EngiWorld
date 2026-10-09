"""Build `init_file/scene.blend` for task LH04.

Creates a scene with:
  - One mesh object `Cube` using a material `Mat_InUse`.
  - `Mat_InUse` uses an Image Texture node referencing an image `Img_InUse`.
  - 20 orphan materials named `Mat_Orphan_00` .. `Mat_Orphan_19`
    (datablocks with zero object users; `use_fake_user = True` is set so
    the IDs persist through save/open -- Blender drops users=0+no-fake-user
    datablocks on save).
  - 5 orphan images named `Img_Orphan_0` .. `Img_Orphan_4`
    (generated 64x64, never assigned; also carry `use_fake_user = True`
    for the same persistence reason).

These 25 datablocks are "orphans" in the sense that nothing in the scene
actually uses them -- only the fake-user flag keeps them alive. A proper
purge must clear that flag (or use an op like outliner.orphans_purge with
do_local_ids=True / bpy.data.<coll>.remove(d)).

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.textures):
        for d in list(blk):
            blk.remove(d)


clean_scene()

# --- Build the lone mesh object `Cube` ------------------------------------
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
me  = bpy.data.meshes.new("CubeMesh")
obj = bpy.data.objects.new("Cube", me)
bpy.context.collection.objects.link(obj)
bm.to_mesh(me); bm.free()
obj.location = (0.0, 0.0, 0.0)

# --- Create in-use image and material -------------------------------------
img_in_use = bpy.data.images.new(
    name="Img_InUse", width=64, height=64, alpha=True, float_buffer=False)
# Paint a solid gray so it's not a degenerate zero image.
pix = [0.5, 0.5, 0.5, 1.0] * (64 * 64)
img_in_use.pixels = pix
img_in_use.pack()

mat_in_use = bpy.data.materials.new(name="Mat_InUse")
mat_in_use.use_nodes = True
nt = mat_in_use.node_tree
# Clear default nodes and build a tiny shader with an Image Texture.
for n in list(nt.nodes):
    nt.nodes.remove(n)
n_out   = nt.nodes.new("ShaderNodeOutputMaterial")
n_bsdf  = nt.nodes.new("ShaderNodeBsdfPrincipled")
n_tex   = nt.nodes.new("ShaderNodeTexImage")
n_tex.image = img_in_use
nt.links.new(n_tex.outputs["Color"], n_bsdf.inputs["Base Color"])
nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

# Assign Mat_InUse to Cube's first slot.
if not obj.data.materials:
    obj.data.materials.append(mat_in_use)
else:
    obj.data.materials[0] = mat_in_use

# --- Create 20 orphan materials -------------------------------------------
# Fake user = True so the datablock persists across save/open.
# The agent must clear the fake-user flag (or otherwise force-remove) to
# make them purgeable.
for i in range(20):
    m = bpy.data.materials.new(name=f"Mat_Orphan_{i:02d}")
    m.use_fake_user = True

# --- Create 5 orphan images -----------------------------------------------
for i in range(5):
    im = bpy.data.images.new(
        name=f"Img_Orphan_{i}", width=64, height=64,
        alpha=True, float_buffer=False)
    # Paint a distinct gray per image so they carry real pixel data.
    v = 0.1 + 0.15 * i
    im.pixels = [v, v, v, 1.0] * (64 * 64)
    im.pack()
    im.use_fake_user = True

bpy.context.view_layer.update()

# --- Audit ----------------------------------------------------------------
n_mats   = len(bpy.data.materials)
n_imgs   = len(bpy.data.images)
orph_mats = [m for m in bpy.data.materials if m.name.startswith("Mat_Orphan_")]
orph_imgs = [i for i in bpy.data.images   if i.name.startswith("Img_Orphan_")]
print(f"  materials total    : {n_mats}  (expected 21)")
print(f"  orphan materials   : {len(orph_mats)}  (expected 20)")
print(f"  images total       : {n_imgs}  (expected 6)")
print(f"  orphan images      : {len(orph_imgs)}  (expected 5)")
print(f"  Mat_InUse users    : {bpy.data.materials['Mat_InUse'].users}")
print(f"  Img_InUse users    : {bpy.data.images['Img_InUse'].users}")
for m in orph_mats[:2]:
    print(f"    {m.name}: users={m.users} fake={m.use_fake_user}")
for i in orph_imgs[:2]:
    print(f"    {i.name}: users={i.users} fake={i.use_fake_user}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
