"""Build `ground_truth/answer.blend` + `ground_truth/output/beauty.png` for CH01.

Opens `init_file/character.blend`, removes the weak ambient light (if any),
adds three AREA lights following classic three-point-lighting convention:

    Key  : bright, front-right,  (2, -3, 2.5), energy 800, size 1.5, white
    Fill : softer, front-left,   (-2, -3, 1.5), energy 250, size 2.0, warm
    Rim  : behind subject, up,   (0, 2.5, 2.5),  energy 500, size 0.8, cool

Each light aims at the subject's torso center (0, 0, 1.0) via track-quat
alignment.

Renders 512x512 RGBA PNG to ground_truth/output/beauty.png.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy
from mathutils import Vector

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INIT_BLEND = os.path.join(TASK_DIR, "init_file", "character.blend")
GT_DIR     = os.path.join(TASK_DIR, "ground_truth")
OUT_BLEND  = os.path.join(GT_DIR, "answer.blend")
OUT_DIR    = os.path.join(GT_DIR, "output")
OUT_PNG    = os.path.join(OUT_DIR, "beauty.png")
os.makedirs(OUT_DIR, exist_ok=True)

TARGET = Vector((0.0, 0.0, 1.0))  # aim all lights at subject's torso center


def aim_at(obj, target=TARGET):
    direction = target - Vector(obj.location)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('-Z', 'Y')


def add_area_light(name, location, energy, size, color):
    ldata = bpy.data.lights.new(name=name, type='AREA')
    ldata.shape  = 'SQUARE'
    ldata.size   = size
    ldata.energy = energy
    ldata.color  = color
    obj = bpy.data.objects.new(name, ldata)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim_at(obj)
    return obj


def remove_weak_ambient():
    """Remove any pre-existing non-three-point lights from the scene."""
    to_remove = []
    for obj in bpy.data.objects:
        if obj.type != 'LIGHT':
            continue
        if obj.name in ("Key", "Fill", "Rim"):
            continue
        to_remove.append(obj)
    for obj in to_remove:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        try:
            bpy.data.lights.remove(data)
        except Exception:
            pass


def apply_render_settings(scene):
    scene.render.engine        = "CYCLES"
    scene.cycles.samples       = 64
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.device        = "CPU"
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


# --- Main ---------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INIT_BLEND)

remove_weak_ambient()

key = add_area_light(
    name="Key",
    location=(5.0, 0.0, 1.5),  # strong side lighting from +X (90deg)
    energy=1500.0,
    size=1.5,
    color=(1.0, 1.0, 1.0),
)
fill = add_area_light(
    name="Fill",
    location=(-5.0, 0.0, 1.5),  # opposite side, very dim
    energy=5.0,
    size=2.0,
    color=(1.0, 0.95, 0.85),
)
rim = add_area_light(
    name="Rim",
    location=(0.0, 1.5, 3.5),  # above and slightly behind
    energy=500.0,
    size=0.8,
    color=(0.9, 0.95, 1.0),
)

scene = bpy.context.scene
apply_render_settings(scene)
scene.render.filepath = OUT_PNG

# Save blend first so its state reflects the final scene.
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")

# Render the beauty.
print("  rendering 512x512 Cycles (64 samples) ...")
bpy.ops.render.render(write_still=True)
print(f"  render written -> {OUT_PNG}")

# --- Audit ---------------------------------------------------------------
print("-" * 60)
lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
print(f"  Lights        : {len(lights)}")
for o in lights:
    print(f"    {o.name:<6} type={o.data.type:<5} "
          f"shape={o.data.shape:<7} size={o.data.size:.2f} "
          f"energy={o.data.energy:.1f} "
          f"color=({o.data.color[0]:.2f},{o.data.color[1]:.2f},{o.data.color[2]:.2f}) "
          f"loc=({o.location.x:.2f},{o.location.y:.2f},{o.location.z:.2f})")
print(f"  beauty.png exists : {os.path.isfile(OUT_PNG)}")
print("-" * 60)
