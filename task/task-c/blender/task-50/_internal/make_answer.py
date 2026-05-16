"""Build `ground_truth/answer.blend` for task LH06 — Shader Colorspace Fix.

Open init_file/scene.blend, toggle the (wrongly-tagged) colorspaces on the
two packed images so that:

    basecolor.png  .colorspace_settings.name = 'sRGB'
    normalmap.png  .colorspace_settings.name = 'Non-Color'

and save to ground_truth/answer.blend. Then render the same scene (Cycles
CPU, seed=0, samples=32, 128x128, denoiser off) to a tmp PNG and compute the
centre ROI mean R / G / B so those numbers can be baked into eval.py.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os
import tempfile

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


# Matching constants — keep in sync with eval.py.
ROI_X0, ROI_Y0 = 32, 32
ROI_X1, ROI_Y1 = 96, 96


def fix_colorspaces():
    bc = bpy.data.images.get("basecolor.png")
    nm = bpy.data.images.get("normalmap.png")
    assert bc is not None, "basecolor.png not found in .blend"
    assert nm is not None, "normalmap.png not found in .blend"
    bc.colorspace_settings.name = 'sRGB'
    nm.colorspace_settings.name = 'Non-Color'
    return bc, nm


def apply_render_settings(scene):
    """Deterministic Cycles CPU render settings — match eval.py."""
    scene.render.engine        = "CYCLES"
    scene.cycles.device        = "CPU"
    scene.cycles.samples       = 32
    scene.cycles.use_denoising = False
    scene.cycles.seed          = 0
    scene.render.resolution_x  = 128
    scene.render.resolution_y  = 128
    scene.render.resolution_percentage = 100
    scene.render.threads_mode  = "FIXED"
    scene.render.threads       = 1
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'


def render_and_mean_roi(tmp_dir):
    scene = bpy.context.scene
    apply_render_settings(scene)

    out_png = os.path.join(tmp_dir, "gt_render.png")
    scene.render.filepath = out_png
    bpy.ops.render.render(write_still=True)

    # Re-load the rendered PNG from disk to get the final displayed pixels
    # (after the view transform). This matches exactly what eval.py does.
    img = bpy.data.images.load(out_png)
    try:
        w, h = img.size[0], img.size[1]
        px = list(img.pixels)   # flat RGBA, bottom-up row-major, floats.
    finally:
        bpy.data.images.remove(img)

    assert (w, h) == (128, 128), f"unexpected render size {w}x{h}"

    rs, gs, bs = [], [], []
    for y in range(ROI_Y0, ROI_Y1):
        for x in range(ROI_X0, ROI_X1):
            i = (y * w + x) * 4
            rs.append(px[i + 0])
            gs.append(px[i + 1])
            bs.append(px[i + 2])
    n = len(rs)
    return (sum(rs) / n, sum(gs) / n, sum(bs) / n)


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

bc, nm = fix_colorspaces()

# Save the ground-truth .blend BEFORE rendering, so the saved file matches
# exactly what eval.py will open.
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")

# Now render from the in-memory scene (which matches what was just saved)
# and report the centre-ROI mean.
tmp_dir = tempfile.mkdtemp(prefix="lh06_gt_render_")
try:
    mean_r, mean_g, mean_b = render_and_mean_roi(tmp_dir)
finally:
    pass

print("-" * 60)
print(f"  bc.colorspace = {bc.colorspace_settings.name}")
print(f"  nm.colorspace = {nm.colorspace_settings.name}")
print(f"  ROI mean R    = {mean_r:.6f}")
print(f"  ROI mean G    = {mean_g:.6f}")
print(f"  ROI mean B    = {mean_b:.6f}")
print(f"  ROI window    = x[{ROI_X0},{ROI_X1}) y[{ROI_Y0},{ROI_Y1})")
# A single line, easy to grep from stdout when baking constants.
print(f"ROI_MEAN_RGB={mean_r:.6f},{mean_g:.6f},{mean_b:.6f}")
print("-" * 60)
