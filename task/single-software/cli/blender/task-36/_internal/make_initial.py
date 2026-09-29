"""Build `init_file/scene.blend` plus three solid RGB PNG textures for task
IH04 - Texture-Link Repair.

Creates:
  - `init_file/textures/red.png`, `green.png`, `blue.png`  (16x16 solid colour)
  - A scene with three planes `Plane_R`, `Plane_G`, `Plane_B` at x=-2, 0, +2.
    Each plane carries a material `Plane_<C>_Mat` whose node tree contains an
    Image Texture node bound to an image datablock named
    `<color>_diffuse`.  The image datablock's `filepath` has been mutated
    AFTER-load to a BOGUS absolute path so that the texture link is broken
    (is_missing) when the blend is reopened.

  - Camera at (0, -5, 5) aimed at origin.
  - Sun light.
  - Eevee CPU, 256x256 render settings.

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

CHANNELS = [
    # name, color RGBA, x-position
    ("red",   (1.0, 0.0, 0.0, 1.0), -2.0),
    ("green", (0.0, 1.0, 0.0, 1.0),  0.0),
    ("blue",  (0.0, 0.0, 1.0, 1.0),  2.0),
]

# Per-colour bogus absolute paths that will NOT exist on disk - these are
# the broken links the agent must repair.
BROKEN_PATHS = {
    "red":   "/tmp/ih04_missing/red_WRONG.png",
    "green": "/nonexistent/path/green_broken.png",
    "blue":  "//textures/blue_WRONG_DOES_NOT_EXIST.png",
}


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.textures):
        for d in list(blk):
            blk.remove(d)


def write_solid_png(abs_path, color_rgba):
    """Write a solid-colour 16x16 PNG via Blender's image save."""
    img = bpy.data.images.new(name="_scratch_png",
                              width=16, height=16,
                              alpha=True, float_buffer=False)
    pixels = list(color_rgba) * (16 * 16)
    img.pixels = pixels
    img.file_format = 'PNG'
    img.filepath_raw = abs_path
    img.save()
    bpy.data.images.remove(img)


def build_plane(name, x):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.9)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            co = lp.vert.co
            lp[uv_layer].uv = ((co.x + 0.9) / 1.8, (co.y + 0.9) / 1.8)
    me  = bpy.data.meshes.new(f"{name}_mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (x, 0.0, 0.0)
    return obj


def build_material_with_broken_image(mat_name, img_name, correct_abs_path,
                                     broken_path):
    """Load the PNG with its correct path, then mutate the filepath to a
    broken one so that when the blend is reopened the image fails to
    resolve (is_missing=True)."""
    img = bpy.data.images.load(correct_abs_path, check_existing=False)
    img.name = img_name
    assert img.source == 'FILE'

    # Break the link: point the filepath at something that does not exist.
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


def make_camera():
    """Camera at (0, -5, 5), pointing at origin."""
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (0.0, -5.0, 5.0)
    direction = Vector((0.0, 0.0, 0.0)) - Vector(cam.location)
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


clean_scene()

# --- Write the three real PNGs to disk ------------------------------------
png_paths = {}
for name, color, _x in CHANNELS:
    path = os.path.join(TEX_DIR, f"{name}.png")
    write_solid_png(path, color)
    assert os.path.isfile(path), f"Failed to write {path}"
    png_paths[name] = path
    print(f"  wrote texture {path}  exists={os.path.isfile(path)}")

# Drop any scratch image datablocks so only the broken ones remain below.
for im in list(bpy.data.images):
    bpy.data.images.remove(im)

# --- Build planes + materials with broken images --------------------------
for name, _color, x in CHANNELS:
    obj_name = f"Plane_{name[0].upper()}"            # Plane_R / Plane_G / Plane_B
    mat_name = f"{obj_name}_Mat"
    img_name = f"{name}_diffuse"
    plane = build_plane(obj_name, x)
    mat, img = build_material_with_broken_image(
        mat_name, img_name, png_paths[name], BROKEN_PATHS[name])
    if not plane.data.materials:
        plane.data.materials.append(mat)
    else:
        plane.data.materials[0] = mat
    print(f"  {obj_name}  material={mat.name}  image={img.name}  "
          f"filepath={img.filepath!r}  has_data={img.has_data}")

make_camera()
make_sun()

scene = bpy.context.scene
apply_render_settings(scene)

bpy.context.view_layer.update()

# --- Save WITHOUT relative-remap so absolute bogus paths stay bogus. ------
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH, relative_remap=False)

# --- Reopen and audit the missing-state on load ---------------------------
bpy.ops.wm.open_mainfile(filepath=OUT_PATH)
print("-" * 60)
print("  AFTER save + reopen:")
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    resolved = bpy.path.abspath(im.filepath)
    exists = os.path.isfile(resolved)
    print(f"    - {im.name:14s}  filepath={im.filepath!r}  "
          f"has_data={im.has_data}  is_missing={getattr(im, 'is_missing', 'n/a')}  "
          f"resolved_exists={exists}")
print(f"  saved -> {OUT_PATH}")
