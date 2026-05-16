"""Build `init_file/sphere.blend` + `init_file/textures/*.png` for task DH02.

Creates:
  - `init_file/textures/albedo.png`    (512x512, flat (0.7, 0.3, 0.2, 1.0))
  - `init_file/textures/normal.png`    (512x512, flat (0.5, 0.5, 1.0, 1.0))
  - `init_file/textures/roughness.png` (512x512, flat (0.4, 0.4, 0.4, 1.0))
  - `init_file/textures/metallic.png`  (512x512, flat (0.0, 0.0, 0.0, 1.0))
  - A sphere mesh `Sphere` at origin with a bare Principled BSDF material.
  - A camera at (0, -3, 0) pointing at origin and a sun light at (2, -2, 3).
  - Render engine: Blender Eevee (CPU-friendly headless) 512x512, 16 samples.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Euler, Vector

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
INIT_DIR = os.path.join(TASK_DIR, "init_file")
TEX_DIR  = os.path.join(INIT_DIR, "textures")
OUT_PATH = os.path.join(INIT_DIR, "sphere.blend")

os.makedirs(TEX_DIR, exist_ok=True)

TEXTURES = [
    # name, color (R,G,B,A), colorspace
    ("albedo",    (0.7, 0.3, 0.2, 1.0), "sRGB"),
    ("normal",    (0.5, 0.5, 1.0, 1.0), "Non-Color"),
    ("roughness", (0.4, 0.4, 0.4, 1.0), "Non-Color"),
    ("metallic",  (0.0, 0.0, 0.0, 1.0), "Non-Color"),
]


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.textures, bpy.data.node_groups):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def write_solid_png(abs_path, color_rgba, width=512, height=512):
    """Write a solid-color PNG via Blender's image save (no PIL/numpy).

    We treat the PNG as non-color for writing so the stored pixel values
    match the requested floats without gamma warp.  The colorspace the
    agent uses when the image is *re-loaded* is what eval cares about.
    """
    img = bpy.data.images.new(name="_scratch_png",
                              width=width, height=height,
                              alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels = list(color_rgba) * (width * height)
    img.file_format = 'PNG'
    img.filepath_raw = abs_path
    img.save()
    bpy.data.images.remove(img)


def build_sphere():
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=1.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = "Sphere"
    # Shade smooth for a nicer preview.
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def build_bare_principled_material():
    """Material with nodes enabled but NO texture wiring."""
    mat = bpy.data.materials.new(name="SphereMat")
    mat.use_nodes = True
    nt = mat.node_tree
    # Keep the default Principled BSDF + Material Output layout.
    # Make sure the default Base Color is not accidentally set to the
    # albedo color — keep whatever Blender's default is.
    return mat


def add_camera_and_light():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -3.0, 0.0)
    # Look at origin: -Y is forward in Blender's default cam orient.
    # Rotate cam so that its -Z axis points from (0,-3,0) toward (0,0,0),
    # i.e. point along +Y.  That is rotation (90deg about X).
    cam_obj.rotation_euler = Euler((math.radians(90.0), 0.0, 0.0), 'XYZ')
    bpy.context.scene.camera = cam_obj

    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    # A bright, nearly-white sun so the sphere center reproduces the
    # albedo color within the +-0.18 tolerance even under shading.
    light_data.energy = 5.0
    light_obj = bpy.data.objects.new("Sun", light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = (2.0, -2.0, 3.0)
    # Aim the sun at the origin: compute rotation so the sun's local
    # -Z axis points from its location toward (0, 0, 0).  Without this
    # the default sun points straight down (-Z world) and misses the
    # camera-facing front of the sphere.
    direction = (Vector((0.0, 0.0, 0.0)) - Vector(light_obj.location))
    direction.normalize()
    light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return cam_obj, light_obj


def set_render_settings(scene):
    """Eevee headless, 512x512, 16 samples, Standard view transform so the
    rendered pixel values are a linear encoding of the shaded albedo
    (required for the render-color check in eval).
    """
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    try:
        scene.eevee.taa_render_samples = 16
    except AttributeError:
        pass
    # Disable tone mapping (default in 4.1 is AgX which compresses
    # mid-tones) so pixel values track the material's base color.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

# --- 1. Write the 4 solid-color PNGs on disk -----------------------------
png_paths = {}
for name, color, _cs in TEXTURES:
    path = os.path.join(TEX_DIR, f"{name}.png")
    write_solid_png(path, color)
    assert os.path.isfile(path), f"failed to write {path}"
    png_paths[name] = path
    print(f"  wrote texture {path}  exists={os.path.isfile(path)}")

# Drop any image datablocks the writer leaked so the init blend has
# no stray images.
for im in list(bpy.data.images):
    bpy.data.images.remove(im)

# --- 2. Build the sphere with a bare Principled BSDF material ------------
sphere = build_sphere()
mat = build_bare_principled_material()
sphere.data.materials.append(mat)

# --- 3. Camera + light ----------------------------------------------------
cam, sun = add_camera_and_light()

# --- 4. Render settings ---------------------------------------------------
set_render_settings(bpy.context.scene)

# --- Audit ---------------------------------------------------------------
print("-" * 60)
print(f"  Sphere verts/faces : {len(sphere.data.vertices)}/"
      f"{len(sphere.data.polygons)}")
print(f"  Materials          : {[m.name for m in bpy.data.materials]}")
nt = mat.node_tree
tex_nodes = [n for n in nt.nodes if n.type == 'TEX_IMAGE']
nmap_nodes = [n for n in nt.nodes if n.type == 'NORMAL_MAP']
print(f"  Material nodes     : {[n.bl_idname for n in nt.nodes]}")
print(f"  TexImage count     : {len(tex_nodes)}  (should be 0 in init)")
print(f"  NormalMap count    : {len(nmap_nodes)} (should be 0 in init)")
print(f"  Camera             : {cam.name} loc={tuple(cam.location)}")
print(f"  Light              : {sun.name} loc={tuple(sun.location)}")
print(f"  Engine             : {bpy.context.scene.render.engine}")
print(f"  Resolution         : "
      f"{bpy.context.scene.render.resolution_x}x"
      f"{bpy.context.scene.render.resolution_y}")
print(f"  Textures on disk   : {list(png_paths.keys())}")
print("-" * 60)

# Save WITHOUT forcing path relativization; the init blend has no
# image datablocks loaded yet — those are loaded in the answer stage.
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
