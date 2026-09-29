"""Build `init_file/character.blend` for task CH01 -- Three-Point Lighting.

Scene:
  - A simple humanoid stand-in at the origin built from primitives:
      * Torso  : cube scaled 0.8 x 0.4 x 1.2, center at (0, 0, 1.0)
      * Head   : UV sphere r=0.25 at (0, 0, 1.8)
      * L/R arms : cylinders (r=0.12, depth=1.0) at (+-0.5, 0, 1.1)
                   oriented downward
      * L/R legs : cylinders (r=0.15, depth=1.2) at (+-0.2, 0, -0.2)
                   oriented downward
  - All parts: Principled BSDF, base color (0.6, 0.55, 0.5) roughness 0.6
  - Large gray ground plane at Z = -0.8
  - Camera at (0, -3.0, 1.0) aimed at torso (0, 0, 1.0). Resolution 512x512.
  - No strong lights — one very dim area light at (0, -4, 0.5) so the init
    render is dim but not pitch-black.
  - World: neutral gray background strength 0.05.
  - Cycles, 64 samples, denoise ON, view_transform='Standard'.

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
OUT_PATH = os.path.join(TASK_DIR, "init_file", "character.blend")
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


def make_skin_material():
    """Plain Principled BSDF with a skin-ish diffuse color."""
    mat = bpy.data.materials.new("SkinMat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.6, 0.55, 0.5, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.6
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def make_ground_material():
    mat = bpy.data.materials.new("GroundMat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        # Very dark ground so key light doesn't bounce into fill side.
        bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 1.0
    return mat


def add_torso(skin_mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 1.0))
    obj = bpy.context.active_object
    obj.name = "Torso"
    # scale 0.8 x 0.4 x 1.2 around its center
    obj.scale = (0.4, 0.2, 0.6)  # half-extents (cube size=1 means +-0.5)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(skin_mat)
    return obj


def add_head(skin_mat):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=0.25, location=(0.0, 0.0, 1.8),
        segments=24, ring_count=12)
    obj = bpy.context.active_object
    obj.name = "Head"
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(skin_mat)
    return obj


def add_arm(side, skin_mat):
    x = 0.5 * side
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.12, depth=1.0, location=(x, 0.0, 1.1),
        vertices=20)
    obj = bpy.context.active_object
    obj.name = f"Arm_{'R' if side > 0 else 'L'}"
    # cylinders default axis is Z; cylinders pointed downward means their
    # Z axis is aligned with world -Z. Since the cylinder is symmetric
    # about its local origin, leaving it Z-up is equivalent for rendering.
    # We keep it vertical.
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(skin_mat)
    return obj


def add_leg(side, skin_mat):
    x = 0.2 * side
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.15, depth=1.2, location=(x, 0.0, -0.2),
        vertices=20)
    obj = bpy.context.active_object
    obj.name = f"Leg_{'R' if side > 0 else 'L'}"
    for p in obj.data.polygons:
        p.use_smooth = True
    obj.data.materials.append(skin_mat)
    return obj


def add_ground(ground_mat):
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, -0.8))
    obj = bpy.context.active_object
    obj.name = "Ground"
    obj.data.materials.append(ground_mat)
    return obj


def add_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -3.0, 1.0)
    # Aim camera at torso center (0, 0, 1.0). Blender cam forward is -Z.
    target = Vector((0.0, 0.0, 1.0))
    direction = target - Vector(cam_obj.location)
    cam_obj.rotation_mode = 'QUATERNION'
    cam_obj.rotation_quaternion = direction.to_track_quat('-Z', 'Y')
    bpy.context.scene.camera = cam_obj
    return cam_obj


def add_weak_ambient_light():
    """A very dim area light to avoid pitch-black. Not enough to satisfy
    the key/fill/rim pass conditions."""
    light_data = bpy.data.lights.new(name="WeakAmbient", type='AREA')
    light_data.shape = 'SQUARE'
    light_data.size = 5.0
    light_data.energy = 20.0
    light_data.color = (1.0, 1.0, 1.0)
    obj = bpy.data.objects.new("WeakAmbient", light_data)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.0, -4.0, 0.5)
    # Point roughly at the subject.
    direction = Vector((0.0, 0.0, 1.0)) - Vector(obj.location)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('-Z', 'Y')
    return obj


def make_gray_world():
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg  = nt.nodes.new("ShaderNodeBackground")
    out.location = (300, 0)
    bg.location  = (0, 0)
    bg.inputs["Color"].default_value    = (0.15, 0.15, 0.15, 1.0)
    bg.inputs["Strength"].default_value = 0.1
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w
    return w


def apply_render_settings(scene):
    scene.render.engine        = "CYCLES"
    scene.cycles.samples       = 64
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.device        = "CPU"
    # Limit bounces to make key/fill asymmetry more dramatic (less
    # indirect illumination on the fill side from ground/subject bounce).
    scene.cycles.max_bounces         = 1
    scene.cycles.diffuse_bounces     = 1
    scene.cycles.glossy_bounces      = 1
    scene.cycles.transmission_bounces = 1
    scene.cycles.transparent_max_bounces = 1
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


clean_scene()

skin   = make_skin_material()
ground = make_ground_material()

torso  = add_torso(skin)
head   = add_head(skin)
arm_r  = add_arm(+1, skin)
arm_l  = add_arm(-1, skin)
leg_r  = add_leg(+1, skin)
leg_l  = add_leg(-1, skin)
grnd   = add_ground(ground)

cam    = add_camera()
world  = make_gray_world()
ambient = add_weak_ambient_light()

scene = bpy.context.scene
apply_render_settings(scene)

print("-" * 60)
print(f"  Subject parts     : {[o.name for o in bpy.data.objects if o.type=='MESH']}")
print(f"  Lights            : {[(o.name, o.data.type, o.data.energy) for o in bpy.data.objects if o.type=='LIGHT']}")
print(f"  Camera            : {cam.name} loc={tuple(cam.location)}")
print(f"  Render engine     : {scene.render.engine}")
print(f"  Samples           : {scene.cycles.samples}")
print(f"  Resolution        : {scene.render.resolution_x}x{scene.render.resolution_y}")
print(f"  view_transform    : {scene.view_settings.view_transform}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
