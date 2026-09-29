"""Build `init_file/scene.blend` for task CH02 -- Compositor multi-output.

Scene:
  - Three cubes at Y=1, Y=3, Y=5 (different X offsets so their screen-space
    projections do not overlap, allowing per-cube depth sampling):
        Cube_Y1 at (-2, 1, 0)
        Cube_Y3 at ( 0, 3, 0)
        Cube_Y5 at ( 2, 5, 0)
  - Camera at (0, -5, 0) looking at +Y (camera sees cubes at increasing depth)
  - Sun light at (4, -4, 6) pointing at origin
  - Render engine: BLENDER_EEVEE at 256x256 (samples 16)
  - Depth pass enabled on the active view layer (view_layer.use_pass_z = True)
  - scene.use_nodes = False (compositor NOT built yet; agent must build it)

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
    if bpy.context.scene.objects:
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.worlds, bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_cubes():
    cubes = []
    # (x, y) per cube. x is staggered so the cubes don't occlude each
    # other in the rendered image; y is the "depth along camera axis".
    for x, y in ((-2.0, 1), (0.0, 3), (2.0, 5)):
        bpy.ops.mesh.primitive_cube_add(size=1.0,
                                         location=(x, float(y), 0.0))
        obj = bpy.context.active_object
        obj.name = f"Cube_Y{y}"
        cubes.append(obj)
    return cubes


def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -5.0, 0.0)
    # Point camera at +Y direction. Camera forward is -Z, so we need
    # to rotate 90 degrees around X so -Z points to +Y.
    cam_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    bpy.context.scene.camera = cam_obj
    return cam_obj


def make_sun_light():
    light_data = bpy.data.lights.new("Sun", type='SUN')
    light_data.energy = 3.0
    light_obj  = bpy.data.objects.new("Sun", light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = (4.0, -4.0, 6.0)
    # Aim roughly toward cubes area.
    direction = Vector((0.0, 3.0, 0.0)) - light_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    light_obj.rotation_euler = rot_quat.to_euler()
    return light_obj


def make_plain_world():
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg  = nt.nodes.new("ShaderNodeBackground")
    out.location = (300, 0)
    bg.location  = (0, 0)
    bg.inputs["Color"].default_value    = (0.05, 0.05, 0.05, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w
    return w


def apply_render_settings(scene):
    scene.render.engine        = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x  = 256
    scene.render.resolution_y  = 256
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_start = 1
    scene.frame_end   = 1
    # Enable Z (depth) pass on active view layer.
    for vl in scene.view_layers:
        vl.use_pass_z = True
    # Compositor NOT built yet: scene.use_nodes = False.
    scene.use_nodes = False


clean_scene()

cubes = make_cubes()
cam   = make_camera()
sun   = make_sun_light()
world = make_plain_world()

scene = bpy.context.scene
apply_render_settings(scene)

print("-" * 60)
for c in cubes:
    print(f"  {c.name}.location = {tuple(c.location)}")
print(f"  camera.location    = {tuple(cam.location)}")
print(f"  camera.rotation    = {tuple(cam.rotation_euler)}")
print(f"  sun.location       = {tuple(sun.location)}")
print(f"  render.engine      = {scene.render.engine}")
print(f"  resolution         = "
      f"{scene.render.resolution_x}x{scene.render.resolution_y}")
print(f"  use_nodes          = {scene.use_nodes}")
print(f"  use_pass_z(vl0)    = {scene.view_layers[0].use_pass_z}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
