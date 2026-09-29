"""Build init_file assets for task KH02 - CSV -> GN -> Shader -> Anim -> Render.

Creates two files:

  1. `init_file/bricks.csv` - 100 rows, each row (x, y, z, hue) laying out a
     10x10 grid on the XY plane at z=0.5 with monotonically-increasing hue in
     [0, 1]. The hue column is the per-brick color key that the downstream
     make_answer.py uses to drive the brick shader.

  2. `init_file/scene.blend` - an (intentionally) empty-of-bricks scene with
     only a Camera at (0, -15, 10) aimed at the origin, a Sun light, black
     world, and scene.frame_end = 30. No bricks, no GN, no turntable pivot
     yet. The render engine is pre-configured (Cycles, 256x256, 16 samples)
     so that if someone does `bpy.ops.render.render(animation=True)` over
     this blend the init-file fails the frame/geometry eval checks but still
     renders cleanly.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import csv
import os
import random

import bpy
from mathutils import Vector

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
CSV_PATH    = os.path.join(TASK_DIR, "init_file", "bricks.csv")
BLEND_PATH  = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)


def write_bricks_csv():
    """Write a 100-row CSV with the (x, y, z, hue) columns. Uses a
    10x10 grid at z=0.5 with hue=i/100 monotonically along row index
    (so a horizontal row of 10 bricks sees hue sweep linearly)."""
    random.seed(42)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x", "y", "z", "hue"])
        for i in range(100):
            xi, yi = i % 10, i // 10
            x = (xi - 4.5) * 1.2
            y = (yi - 4.5) * 1.2
            z = 0.5
            hue = i / 100.0
            w.writerow([f"{x:.3f}", f"{y:.3f}", f"{z:.3f}", f"{hue:.3f}"])


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.node_groups, bpy.data.materials,
                bpy.data.armatures, bpy.data.actions):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_camera():
    """Camera at (0, -15, 10) aimed at the world origin. No parent."""
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (0.0, -15.0, 10.0)
    direction = Vector((0.0, 0.0, 0.0)) - Vector(cam.location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def make_sun():
    """Sun light at (5, -5, 10) aimed roughly at origin."""
    light_data = bpy.data.lights.new(name="Sun", type="SUN")
    light_data.energy = 3.0
    light = bpy.data.objects.new("Sun", light_data)
    light.location = (5.0, -5.0, 10.0)
    direction = Vector((0.0, 0.0, 0.0)) - Vector(light.location)
    rot_quat = direction.to_track_quat('-Z', 'Y')
    light.rotation_euler = rot_quat.to_euler()
    bpy.context.collection.objects.link(light)
    return light


def apply_render_settings(scene):
    scene.render.engine        = "CYCLES"
    scene.cycles.device        = "CPU"
    scene.cycles.samples       = 16
    scene.cycles.use_denoising = True
    scene.cycles.seed          = 0
    scene.render.resolution_x  = 256
    scene.render.resolution_y  = 256
    scene.render.resolution_percentage = 100
    scene.render.threads_mode  = "FIXED"
    scene.render.threads       = 2
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'


def main():
    # 1. CSV (stdlib; no bpy needed for the file itself).
    write_bricks_csv()

    # 2. Scene .blend.
    clean_scene()

    scene = bpy.context.scene
    # Dark-but-not-transparent world so silhouette check on alpha is
    # determined by geometry, not by the world color.
    scene.world = scene.world or bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        bg.inputs["Strength"].default_value = 1.0

    cam = make_camera()
    sun = make_sun()

    # Scene units and frame range.
    scene.unit_settings.system       = "METRIC"
    scene.unit_settings.length_unit  = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.frame_start   = 1
    scene.frame_end     = 30
    scene.frame_current = 1

    apply_render_settings(scene)

    # Diagnostics.
    print("-" * 60)
    print(f"  CSV written -> {CSV_PATH}")
    with open(CSV_PATH) as f:
        n_lines = sum(1 for _ in f)
    print(f"  CSV rows (incl. header): {n_lines} (expect 101)")
    print("  Objects:")
    for o in bpy.data.objects:
        print(f"    {o.name}  type={o.type}  "
              f"loc={tuple(round(v, 3) for v in o.location)}")
    print(f"  scene.frame_start/end  = {scene.frame_start}/{scene.frame_end}")
    print(f"  render.engine          = {scene.render.engine}")
    print(f"  render.resolution      = "
          f"{scene.render.resolution_x}x{scene.render.resolution_y}")
    print(f"  cycles.samples         = {scene.cycles.samples}")
    print("-" * 60)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"  saved -> {BLEND_PATH}")


if __name__ == "__main__":
    main()
