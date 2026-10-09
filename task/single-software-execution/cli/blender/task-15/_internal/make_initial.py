"""Build `init_file/scene.blend` for task CH04 -- Compositor Glare (Fog Glow).

Scene:
  - A small emissive sphere (radius 0.1) at the origin with a Principled
    BSDF material whose Emission input is white at strength 50. This
    produces a very bright point-like source in the final render.
  - A Camera named "Camera" at (0, -3, 0) looking along +Y (cam forward
    is -Z, so rotate +90 deg around X).
  - A Point light with small energy at (0, 0, 0) (optional; the emission
    material does the heavy lifting).
  - Pitch-black world background so the only lit pixels are the emissive
    source and its scattered glare.
  - Render engine: CYCLES at 512x512, samples 32, denoising off.
  - `scene.use_nodes = False` (no compositor tree built yet; agent must
    build it).

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bpy

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
                bpy.data.worlds, bpy.data.objects, bpy.data.node_groups):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_emissive_sphere():
    """Bright tiny sphere at the origin with emission strength 50."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.1, location=(0.0, 0.0, 0.0), segments=24, ring_count=12)
    obj = bpy.context.active_object
    obj.name = "EmissiveSource"
    # Smooth shading so the silhouette is round.
    for p in obj.data.polygons:
        p.use_smooth = True

    # Emission material via Principled BSDF's Emission input (so the
    # check "emissive source exists" can match either a pure Emission
    # shader or a Principled with nonzero Emission Strength).
    mat = bpy.data.materials.new("EmissiveMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.location = (0, 0)
    emit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 50.0
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])

    obj.data.materials.append(mat)
    return obj


def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -3.0, 0.0)
    # Point camera at +Y. Camera forward is -Z, so rotate +90 deg around X.
    cam_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    bpy.context.scene.camera = cam_obj
    return cam_obj


def make_dark_world():
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg  = nt.nodes.new("ShaderNodeBackground")
    out.location = (300, 0)
    bg.location  = (0, 0)
    bg.inputs["Color"].default_value    = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w
    return w


def apply_render_settings(scene):
    scene.render.engine        = "CYCLES"
    # Cheap but enough to resolve the bright source.
    scene.cycles.samples       = 32
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    # Keep Cycles deterministic on CPU so the eval ratio is stable.
    scene.cycles.device        = "CPU"
    scene.render.resolution_x  = 512
    scene.render.resolution_y  = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_start   = 1
    scene.frame_end     = 1
    scene.frame_current = 1
    # Compositor NOT built yet.
    scene.use_nodes = False


clean_scene()

sphere = make_emissive_sphere()
cam    = make_camera()
world  = make_dark_world()

scene = bpy.context.scene
apply_render_settings(scene)

print("-" * 60)
print(f"  sphere.name     = {sphere.name}")
print(f"  sphere.loc      = {tuple(sphere.location)}")
print(f"  camera.loc      = {tuple(cam.location)}")
print(f"  camera.rot      = {tuple(cam.rotation_euler)}")
print(f"  render.engine   = {scene.render.engine}")
print(f"  cycles.samples  = {scene.cycles.samples}")
print(f"  resolution      = "
      f"{scene.render.resolution_x}x{scene.render.resolution_y}")
print(f"  use_nodes       = {scene.use_nodes}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
