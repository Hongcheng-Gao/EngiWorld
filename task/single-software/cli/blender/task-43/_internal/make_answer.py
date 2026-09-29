"""Build `ground_truth/answer.blend` + `ground_truth/output/optimal.png` for KH05.

Open init_file/scene.blend. Brute-force search over azimuth/elevation on a
sphere of radius 5.0 around the origin; for each (az, el) position the
orthographic camera, render to a temp PNG, count alpha-positive pixels
(silhouette area). Keep the argmax, place the camera there, render the
final image to ground_truth/output/optimal.png, and save answer.blend.

Strategy:
  - Coarse grid: az in [0, 360) step 15 deg (24 steps), el in [-75, +75]
    step 15 deg (11 steps), total 264 renders.
  - Refinement: 5 deg grid within +/- 15 deg of the coarse best, another
    ~49 renders.
  - All renders are 256x256 at 4 Cycles samples with `film_transparent =
    True`, so each render is very cheap (~0.2-0.5 s on CPU). Total ~1-3
    minutes.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import math
import os
import tempfile
import time

import bpy
from mathutils import Vector

HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
INPUT_PATH  = os.path.join(TASK_DIR, "init_file", "scene.blend")
GT_DIR      = os.path.join(TASK_DIR, "ground_truth")
OUT_BLEND   = os.path.join(GT_DIR, "answer.blend")
OUT_IMG_DIR = os.path.join(GT_DIR, "output")
OUT_PNG     = os.path.join(OUT_IMG_DIR, "optimal.png")

os.makedirs(OUT_IMG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Camera helpers
# ---------------------------------------------------------------------------

def place_camera_on_sphere(cam, az_deg, el_deg, radius=5.0):
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    x = radius * math.cos(el) * math.cos(az)
    y = radius * math.cos(el) * math.sin(az)
    z = radius * math.sin(el)
    cam.location = (x, y, z)
    direction = Vector((0.0, 0.0, 0.0)) - Vector(cam.location)
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = direction.to_track_quat('-Z', 'Y')


# ---------------------------------------------------------------------------
# Silhouette area: render once, count alpha-positive pixels.
# ---------------------------------------------------------------------------

def count_alpha_positive(png_path, threshold=0.5):
    """Load the PNG into a bpy image, count pixels with alpha > threshold."""
    img = bpy.data.images.load(png_path, check_existing=False)
    try:
        w, h = img.size[0], img.size[1]
        n = w * h * 4
        buf = [0.0] * n
        img.pixels.foreach_get(buf)
        # Alpha is every 4th element (index 3, 7, 11, ...).
        hits = 0
        for i in range(3, n, 4):
            if buf[i] > threshold:
                hits += 1
        return hits, (w, h)
    finally:
        bpy.data.images.remove(img)


def silhouette_area(scene, cam, az_deg, el_deg, tmp_path, radius=5.0,
                   alpha_thr=0.5):
    place_camera_on_sphere(cam, az_deg, el_deg, radius=radius)
    bpy.context.view_layer.update()
    scene.render.filepath = tmp_path
    bpy.ops.render.render(write_still=True)
    # Blender writes to <tmp_path> + '.png' if no extension, otherwise exact.
    # We pass an explicit .png path so it's exact.
    hits, size = count_alpha_positive(tmp_path, threshold=alpha_thr)
    return hits, size


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene = bpy.context.scene
cam   = bpy.data.objects.get("Camera")
target = bpy.data.objects.get("Target")
assert cam is not None and cam.type == 'CAMERA', "Camera missing or wrong type"
assert target is not None and target.type == 'MESH', "Target mesh missing"
scene.camera = cam

# Ensure orthographic + the right render settings are in place (match init).
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 5.0
scene.render.engine = "CYCLES"
scene.cycles.samples = 4
scene.cycles.use_denoising = False
scene.cycles.use_adaptive_sampling = False
scene.cycles.device = "CPU"
scene.render.resolution_x = 256
scene.render.resolution_y = 256
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'Standard'

# Scratch directory for temp renders. We overwrite the same file repeatedly.
scratch_dir = tempfile.mkdtemp(prefix="kh05_search_")
tmp_render = os.path.join(scratch_dir, "probe.png")

best_area = -1
best_az   = 0.0
best_el   = 0.0

# ---- Coarse grid search (15 deg) ----
coarse_az = range(0, 360, 15)
coarse_el = range(-75, 76, 15)  # inclusive of +75
t_start = time.time()
n_coarse = 0
for az_deg in coarse_az:
    for el_deg in coarse_el:
        area, size = silhouette_area(scene, cam, float(az_deg), float(el_deg),
                                     tmp_render)
        n_coarse += 1
        if area > best_area:
            best_area = area
            best_az = float(az_deg)
            best_el = float(el_deg)
print(f"  coarse search done: {n_coarse} renders in "
      f"{time.time() - t_start:.1f} s")
print(f"  coarse best: az={best_az:.1f} el={best_el:.1f} area={best_area}")

# ---- Refinement around the coarse best (5 deg grid, +/- 15 deg) ----
refine_az = [best_az + d for d in range(-15, 16, 5)]
refine_el = [best_el + d for d in range(-15, 16, 5)]
# Clamp elevation so we never go beyond +/- 89 (avoid pole degeneracy of
# to_track_quat: at exactly +/-90 with Y-up the track orientation is still
# valid but keeping off the exact pole is a safe habit).
refine_el = [max(-89.0, min(89.0, e)) for e in refine_el]

t_start = time.time()
n_refine = 0
for az_deg in refine_az:
    for el_deg in refine_el:
        area, size = silhouette_area(scene, cam, float(az_deg), float(el_deg),
                                     tmp_render)
        n_refine += 1
        if area > best_area:
            best_area = area
            best_az = float(az_deg)
            best_el = float(el_deg)
print(f"  refinement done: {n_refine} renders in "
      f"{time.time() - t_start:.1f} s")
print(f"  refined best: az={best_az:.3f} el={best_el:.3f} area={best_area}")

# ---- Sanity-check a few candidate axis directions (+X, -X, +Y, -Y, +Z, -Z) ----
# For our (3, 0.5, 2) box plus bump, the expected winners are +/-Y.
axis_candidates = [
    ( 0.0,   0.0),   # +X
    (180.0,  0.0),   # -X
    ( 90.0,  0.0),   # +Y
    (270.0,  0.0),   # -Y
    (  0.0, 89.0),   # +Z (top-down)
    (  0.0,-89.0),   # -Z
]
for az_deg, el_deg in axis_candidates:
    area, size = silhouette_area(scene, cam, az_deg, el_deg, tmp_render)
    print(f"    axis probe az={az_deg:6.1f} el={el_deg:6.1f}  area={area}")
    if area > best_area:
        best_area = area
        best_az = az_deg
        best_el = el_deg

print(f"  FINAL optimum: az={best_az:.3f} el={best_el:.3f} area={best_area}")

# ---- Place camera at the optimum and render the final PNG ----
place_camera_on_sphere(cam, best_az, best_el, radius=5.0)
bpy.context.view_layer.update()

scene.render.filepath = OUT_PNG
bpy.ops.render.render(write_still=True)

final_hits, final_size = count_alpha_positive(OUT_PNG, threshold=0.5)
print(f"  final render -> {OUT_PNG}")
print(f"  final size   = {final_size}")
print(f"  final alpha>0.5 pixels = {final_hits}")

# ---- Save answer.blend ----
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")

# ---- Diagnostics ----
print("-" * 60)
print(f"  cam.data.type         = {cam.data.type}")
print(f"  cam.data.ortho_scale  = {cam.data.ortho_scale}")
print(f"  cam.location          = "
      f"({cam.location.x:+.3f},{cam.location.y:+.3f},{cam.location.z:+.3f})")
print(f"  cam.distance          = {cam.location.length:.3f}")
print(f"  optimum (az, el)      = ({best_az:.3f}, {best_el:.3f})")
print(f"  optimum area          = {best_area} pixels "
      f"(of {256*256} = {100.0*best_area/(256*256):.2f}%)")
print("-" * 60)

# ---- Cleanup scratch dir ----
try:
    for entry in os.listdir(scratch_dir):
        try:
            os.remove(os.path.join(scratch_dir, entry))
        except Exception:
            pass
    os.rmdir(scratch_dir)
except Exception:
    pass
