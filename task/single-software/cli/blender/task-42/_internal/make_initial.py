"""Build `init_file/scene.blend` for task KH04 - Broken Scene Repair.

Creates a scene with five concrete, common Blender issues the agent must fix:

  1. `HiddenMesh` (UV sphere at Z=3) with `show_viewport = False` — hidden.
  2. `MainMesh` (cube) whose mesh geometry is authored at the origin, but
     whose object `location` has been offset to (3, 0, 0) — needs origin
     reset.
  3. `TexturedPlane` (plane) with material `Mat_Broken`.  The material has
     an Image Texture node pointing at a `bpy.data.images` datablock whose
     `filepath = "//missing.png"` — the file does not exist on disk.
  4. `PrincipledBall` (UV sphere) with material `Mat_NoNodes`.  The
     material has `use_nodes = False` and uses the legacy viewport diffuse
     color instead.
  5. `Extra_Collection` — an empty, redundant collection that should be
     removed.

Also creates:
  - `init_file/textures/good_texture.png` — a valid 64x64 solid-color PNG
    that the agent can repoint the broken image at.
  - A camera and a sun light so the scene is renderable after fixes.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy
from mathutils import Vector

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
INIT_DIR = os.path.join(TASK_DIR, "init_file")
TEX_DIR  = os.path.join(INIT_DIR, "textures")
OUT_PATH = os.path.join(INIT_DIR, "scene.blend")

os.makedirs(TEX_DIR, exist_ok=True)


# ------------------------- utilities ----------------------------------------

def clean_scene():
    """Nuke every datablock so we get a deterministic starting state."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.textures, bpy.data.collections):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def write_solid_png(abs_path, color_rgba, size=64):
    """Write a solid-color PNG via Blender's image save (no PIL/numpy)."""
    img = bpy.data.images.new(name="_scratch_png",
                              width=size, height=size,
                              alpha=True, float_buffer=False)
    pixels = list(color_rgba) * (size * size)
    img.pixels = pixels
    img.file_format = 'PNG'
    img.filepath_raw = abs_path
    img.save()
    bpy.data.images.remove(img)


# ------------------------- object builders ----------------------------------

def build_uv_sphere(name, location=(0.0, 0.0, 0.0), radius=0.6):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=radius)
    me  = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, me)
    bm.to_mesh(me); bm.free()
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    return obj


def build_cube_at_origin_geometry(name, object_location=(0.0, 0.0, 0.0),
                                  size=1.0):
    """Build a cube whose vertices are authored at the origin, then place
    the OBJECT at a (possibly non-zero) location.  This simulates an
    object with an offset transform relative to its geometry."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    me  = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, me)
    bm.to_mesh(me); bm.free()
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(object_location)
    return obj


def build_plane(name, location=(0.0, 0.0, 0.0), size=1.2):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            lp[uv_layer].uv = ((co.x + size) / (2.0 * size),
                               (co.y + size) / (2.0 * size))
    me  = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, me)
    bm.to_mesh(me); bm.free()
    bpy.context.collection.objects.link(obj)
    obj.location = Vector(location)
    return obj


# ------------------------- material builders --------------------------------

def build_material_with_broken_image(mat_name, img_name, broken_path):
    """Build a material with an Image Texture node pointing to an image
    datablock whose filepath does not exist on disk."""
    # Create an image datablock by loading a temp PNG, then break its path.
    # We cannot use bpy.data.images.load for a missing file in a robust
    # way, so instead we create an empty generated image and flip it to
    # source='FILE' with the broken filepath.
    img = bpy.data.images.new(name=img_name, width=4, height=4, alpha=True)
    # Populate pixels with something, then switch to FILE source.
    img.pixels = [0.5, 0.5, 0.5, 1.0] * (4 * 4)
    img.source = 'FILE'
    img.filepath     = broken_path
    img.filepath_raw = broken_path

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_tex  = nt.nodes.new("ShaderNodeTexImage")
    n_tex.image = img
    nt.links.new(n_tex.outputs["Color"], n_bsdf.inputs["Base Color"])
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
    return mat, img


def build_material_no_nodes(mat_name, legacy_color=(0.8, 0.2, 0.2, 1.0)):
    """Build a material with use_nodes = False, using only the legacy
    viewport diffuse color."""
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = False
    mat.diffuse_color = legacy_color
    return mat


# ------------------------- scene-level builders -----------------------------

def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (6.0, -7.0, 6.0)
    direction = Vector((0.0, 0.0, 1.0)) - Vector(cam.location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def make_sun():
    light_data = bpy.data.lights.new(name="Sun", type="SUN")
    light_data.energy = 3.0
    light = bpy.data.objects.new("Sun", light_data)
    light.location = (3.0, -3.0, 5.0)
    direction = Vector((0.0, 0.0, 0.0)) - Vector(light.location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    light.rotation_euler = rot_quat.to_euler()
    bpy.context.collection.objects.link(light)
    return light


def apply_render_settings(scene):
    scene.render.engine        = "BLENDER_EEVEE"
    scene.render.resolution_x  = 256
    scene.render.resolution_y  = 256
    scene.render.resolution_percentage = 100
    scene.render.threads_mode  = "FIXED"
    scene.render.threads       = 1
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGB'
    scene.render.image_settings.color_depth = '8'


# ------------------------- main ---------------------------------------------

clean_scene()

# --- Write the valid "good_texture.png" that the agent should repair to. ---
good_png_path = os.path.join(TEX_DIR, "good_texture.png")
write_solid_png(good_png_path, (0.2, 0.6, 0.9, 1.0), size=64)
assert os.path.isfile(good_png_path), f"Failed to write {good_png_path}"
print(f"  wrote valid texture {good_png_path}  "
      f"exists={os.path.isfile(good_png_path)}")

# Drop any scratch image datablocks left over from write_solid_png.
for im in list(bpy.data.images):
    bpy.data.images.remove(im)

# --- Issue 1: hidden mesh (UV sphere at Z=3, show_viewport=False) ---------
hidden = build_uv_sphere("HiddenMesh", location=(0.0, 0.0, 3.0), radius=0.6)
hidden.hide_viewport = True
print(f"  built HiddenMesh at {tuple(hidden.location)}  "
      f"hide_viewport={hidden.hide_viewport}")

# --- Issue 3: offset transform on MainMesh (cube at origin + offset) ------
# Vertices are authored at the origin; the OBJECT is translated to (3,0,0)
# to simulate an accidentally-offset transform.
main_mesh = build_cube_at_origin_geometry(
    "MainMesh", object_location=(3.0, 0.0, 0.0), size=1.0)
print(f"  built MainMesh at {tuple(main_mesh.location)}  "
      f"(geometry authored at origin)")

# --- Issue 2: broken image path on TexturedPlane / Mat_Broken -------------
textured_plane = build_plane(
    "TexturedPlane", location=(-2.0, 2.0, 0.0), size=1.0)
mat_broken, broken_img = build_material_with_broken_image(
    "Mat_Broken", "broken_texture", "//missing.png")
if not textured_plane.data.materials:
    textured_plane.data.materials.append(mat_broken)
else:
    textured_plane.data.materials[0] = mat_broken
print(f"  built TexturedPlane  material={mat_broken.name}  "
      f"image={broken_img.name}  filepath={broken_img.filepath!r}")

# --- Issue 4: Mat_NoNodes on PrincipledBall (use_nodes=False) -------------
principled_ball = build_uv_sphere(
    "PrincipledBall", location=(2.0, 2.0, 0.5), radius=0.6)
mat_no_nodes = build_material_no_nodes(
    "Mat_NoNodes", legacy_color=(0.8, 0.2, 0.2, 1.0))
if not principled_ball.data.materials:
    principled_ball.data.materials.append(mat_no_nodes)
else:
    principled_ball.data.materials[0] = mat_no_nodes
print(f"  built PrincipledBall  material={mat_no_nodes.name}  "
      f"use_nodes={mat_no_nodes.use_nodes}")

# --- Issue 5: Extra_Collection (empty redundant collection) ---------------
extra_coll = bpy.data.collections.new("Extra_Collection")
bpy.context.scene.collection.children.link(extra_coll)
print(f"  created empty collection: {extra_coll.name}  "
      f"objects={len(extra_coll.objects)}  children={len(extra_coll.children)}")

# --- Camera, light, render settings --------------------------------------
make_camera()
make_sun()
apply_render_settings(bpy.context.scene)
bpy.context.view_layer.update()

# --- Save WITHOUT relative-remap so our broken "//missing.png" stays as-is.
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH, relative_remap=False)

# --- Reopen and audit --------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=OUT_PATH)
print("-" * 60)
print("  AFTER save + reopen:")
print(f"    objects      = {[o.name for o in bpy.data.objects]}")
print(f"    materials    = {[m.name for m in bpy.data.materials]}")
print(f"    collections  = {[c.name for c in bpy.data.collections]}")
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    resolved = bpy.path.abspath(im.filepath) if im.filepath else ""
    exists = os.path.isfile(resolved) if resolved else False
    print(f"    image {im.name!r}  filepath={im.filepath!r}  "
          f"resolved_exists={exists}  packed={bool(im.packed_file)}")
for o in bpy.data.objects:
    if o.type == 'MESH':
        print(f"    mesh obj {o.name!r}  loc={tuple(round(v,3) for v in o.location)}  "
              f"hide_viewport={o.hide_viewport}")
for m in bpy.data.materials:
    print(f"    material {m.name!r}  use_nodes={m.use_nodes}")
print(f"  saved -> {OUT_PATH}")
