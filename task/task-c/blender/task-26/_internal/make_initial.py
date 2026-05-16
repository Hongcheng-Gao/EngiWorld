"""Build `init_file/scene.blend` for task GH02 - Car Paint Shader.

Scene:
  - A UV sphere `PaintBall` at origin, radius 1.0, 64x32 segments, shade
    smooth, with a basic Principled BSDF material `CarPaint` with a dark
    blue base color (0.1, 0.1, 0.3). No Coat/Sheen yet - the testee must
    rebuild this into a two-lobe car-paint shader.
  - Camera at (0, -4, 0.8) looking at the origin.
  - Three-point area lights: KEY@(2,-2,3)/E=400, FILL@(-2,-2,1)/E=150,
    RIM@(0,1,2)/E=200.
  - Gray world background (0.1, 0.1, 0.1).
  - Cycles, 128 samples, denoise ON, view transform Standard.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector


HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.textures, bpy.data.node_groups, bpy.data.worlds):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_paintball():
    """UV sphere at origin, 64x32 segments, smooth-shaded, named PaintBall."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=64, ring_count=32, radius=1.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = "PaintBall"
    obj.data.name = "PaintBallMesh"
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def build_basic_material():
    """Default Principled BSDF with dark blue base color. No Coat/Sheen."""
    mat = bpy.data.materials.new(name="CarPaint")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_out.location  = (400, 0)
    n_bsdf.location = (100, 0)

    if "Base Color" in n_bsdf.inputs:
        n_bsdf.inputs["Base Color"].default_value = (0.1, 0.1, 0.3, 1.0)
    # Everything else left at defaults - no Coat/Sheen/Metallic changes.

    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
    return mat


def add_camera(scene):
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -4.0, 0.8)
    # Aim camera at the origin.
    direction = (Vector((0.0, 0.0, 0.0)) - Vector(cam_obj.location))
    direction.normalize()
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam_obj
    return cam_obj


def add_area_light(name, location, energy, size=2.0):
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.energy = energy
    light_data.size = size
    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    # Aim at origin.
    direction = (Vector((0.0, 0.0, 0.0)) - Vector(light_obj.location))
    direction.normalize()
    light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return light_obj


def make_world():
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    n_out = nt.nodes.new("ShaderNodeOutputWorld")
    n_bg  = nt.nodes.new("ShaderNodeBackground")
    n_bg.inputs["Color"].default_value = (0.1, 0.1, 0.1, 1.0)
    n_bg.inputs["Strength"].default_value = 1.0
    nt.links.new(n_bg.outputs["Background"], n_out.inputs["Surface"])
    bpy.context.scene.world = world
    return world


def set_render_settings(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.cycles.seed = 0
    scene.render.threads_mode = "AUTO"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    # Standard view transform - do not compress highlights with AgX/Filmic.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    # Dial exposure down a stop-and-a-half so the three-point rig doesn't
    # clip the clearcoat peak to pure white (and so the full-image mean
    # luma lands in the eval's [0.05, 0.35] band).
    scene.view_settings.exposure = -1.5
    scene.view_settings.gamma = 1.0
    scene.render.image_settings.file_format = 'PNG'


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

sphere = make_paintball()
mat    = build_basic_material()
sphere.data.materials.append(mat)

cam = add_camera(bpy.context.scene)

key  = add_area_light("KEY",  ( 2.0, -2.0, 3.0), energy=400.0)
fill = add_area_light("FILL", (-2.0, -2.0, 1.0), energy=150.0)
rim  = add_area_light("RIM",  ( 0.0,  1.0, 2.0), energy=200.0)

make_world()
set_render_settings(bpy.context.scene)

# Ensure PaintBall is the active+selected object at save-time.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = sphere
sphere.select_set(True)

# --- Audit --------------------------------------------------------------
print("-" * 60)
print(f"  Sphere         : {sphere.name} verts={len(sphere.data.vertices)}")
print(f"  Material       : {mat.name}")
print(f"  Camera         : {cam.name} loc={tuple(cam.location)}")
print(f"  Lights         : KEY={key.data.energy} FILL={fill.data.energy} "
      f"RIM={rim.data.energy}")
print(f"  Engine/samples : {bpy.context.scene.render.engine}/"
      f"{bpy.context.scene.cycles.samples}")
print(f"  Resolution     : {bpy.context.scene.render.resolution_x}x"
      f"{bpy.context.scene.render.resolution_y}")
print(f"  View transform : {bpy.context.scene.view_settings.view_transform}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
