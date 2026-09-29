"""Build `init_file/scene.blend` for task CH03 -- AOV output -> MultiLayer EXR.

Scene:
  - Three UV spheres named `Sphere_R`, `Sphere_G`, `Sphere_B` at
    X = -2, 0, +2, all Y=0 Z=0. Radius 0.8.
  - Each sphere has a Principled BSDF material with a distinct Base Color:
        Sphere_R  -> (0.9, 0.1, 0.1)
        Sphere_G  -> (0.1, 0.9, 0.1)
        Sphere_B  -> (0.1, 0.1, 0.9)
  - Camera at (0, -5, 1) looking at origin, resolution 512x512.
  - Area light at (0, -3, 3), energy 500.
  - Render engine: Cycles, 16 samples, denoiser OFF (for determinism).
  - No AOV, no Depth/Normal passes enabled, no MultiLayer EXR format set.

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


SPHERE_SPECS = (
    # (name, x, base_color RGBA)
    ("Sphere_R", -2.0, (0.9, 0.1, 0.1, 1.0)),
    ("Sphere_G",  0.0, (0.1, 0.9, 0.1, 1.0)),
    ("Sphere_B",  2.0, (0.1, 0.1, 0.9, 1.0)),
)


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


def build_material(name, base_color_rgba):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_out.location  = (300, 0)
    n_bsdf.location = (0, 0)

    n_bsdf.inputs["Base Color"].default_value = base_color_rgba
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
    return mat


def make_spheres():
    created = []
    for name, x, color in SPHERE_SPECS:
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.8,
            location=(x, 0.0, 0.0),
        )
        obj = bpy.context.active_object
        obj.name = name
        mat = build_material(f"Mat_{name}", color)
        # Replace any default material slot or append.
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        created.append(obj)
    return created


def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -5.0, 1.0)
    # Point camera at origin.
    direction = Vector((0.0, 0.0, 0.0)) - Vector(cam_obj.location)
    rot_quat  = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    bpy.context.scene.camera = cam_obj
    return cam_obj


def make_area_light():
    ldata = bpy.data.lights.new("KeyLight", type='AREA')
    ldata.energy = 500.0
    ldata.size = 2.0
    lobj  = bpy.data.objects.new("KeyLight", ldata)
    bpy.context.collection.objects.link(lobj)
    lobj.location = (0.0, -3.0, 3.0)
    # Aim light at origin.
    direction = Vector((0.0, 0.0, 0.0)) - Vector(lobj.location)
    rot_quat  = direction.to_track_quat('-Z', 'Y')
    lobj.rotation_euler = rot_quat.to_euler()
    return lobj


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
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.cycles.seed = 0
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    # Initial state: plain PNG format, no multilayer EXR yet.
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_start = 1
    scene.frame_end   = 1
    scene.frame_current = 1
    # IMPORTANT (init): no AOV on any view layer, no depth/normal passes.
    for vl in scene.view_layers:
        vl.use_pass_combined = True   # combined is always on by default
        vl.use_pass_z = False
        vl.use_pass_normal = False
        # Remove any AOV entries that may be present by default.
        while len(vl.aovs) > 0:
            try:
                vl.aovs.remove(vl.aovs[0])
            except Exception:
                break
    scene.use_nodes = False


clean_scene()

spheres = make_spheres()
cam     = make_camera()
light   = make_area_light()
world   = make_plain_world()

scene = bpy.context.scene
apply_render_settings(scene)

print("-" * 60)
for s in spheres:
    mat = s.data.materials[0]
    bsdf = next((n for n in mat.node_tree.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    base = tuple(bsdf.inputs["Base Color"].default_value) if bsdf else None
    print(f"  {s.name}.location = {tuple(s.location)}  base_color={base}")
print(f"  camera.location    = {tuple(cam.location)}")
print(f"  light.location     = {tuple(light.location)} energy={light.data.energy}")
print(f"  render.engine      = {scene.render.engine}")
print(f"  cycles.samples     = {scene.cycles.samples}")
print(f"  cycles.denoising   = {scene.cycles.use_denoising}")
print(f"  resolution         = "
      f"{scene.render.resolution_x}x{scene.render.resolution_y}")
print(f"  file_format        = {scene.render.image_settings.file_format}")
print(f"  use_pass_z(vl0)    = {scene.view_layers[0].use_pass_z}")
print(f"  use_pass_normal0   = {scene.view_layers[0].use_pass_normal}")
print(f"  aovs (vl0)         = {[a.name for a in scene.view_layers[0].aovs]}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
