"""Build `ground_truth/answer.blend` for task IH04 - Texture-Link Repair.

Opens `init_file/scene.blend` (three broken image links) and repoints each
image's filepath to the correct PNG in `init_file/textures/`.  Strategy:

  1. Copy the three PNGs into `ground_truth/textures/` so that answer.blend
     has locally-resolvable texture files next to it.
  2. Save-as ground_truth/answer.blend first (so `//` anchors at
     ground_truth/).
  3. For each image datablock, use the image-name (e.g. `red_diffuse`) to
     determine which colour it wants, repoint filepath to
     `//textures/<color>.png`, reload, then pack so the pixels survive the
     resave reliably in background mode.
  4. Resave.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os
import shutil

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INIT_BLEND = os.path.join(TASK_DIR, "init_file", "scene.blend")
INIT_TEXDIR = os.path.join(TASK_DIR, "init_file", "textures")

OUT_DIR    = os.path.join(TASK_DIR, "ground_truth")
OUT_TEXDIR = os.path.join(OUT_DIR, "textures")
OUT_PATH   = os.path.join(OUT_DIR, "answer.blend")

os.makedirs(OUT_TEXDIR, exist_ok=True)

# --- Copy textures next to the answer .blend so `//textures/<c>.png` resolves
for fn in ("red.png", "green.png", "blue.png"):
    src = os.path.join(INIT_TEXDIR, fn)
    dst = os.path.join(OUT_TEXDIR, fn)
    shutil.copyfile(src, dst)
    print(f"  copied {src} -> {dst}")


def color_for_image(img_name):
    """Infer the target colour from the image's name."""
    low = img_name.lower()
    if "red" in low:
        return "red"
    if "green" in low:
        return "green"
    if "blue" in low:
        return "blue"
    return None


# --- Open init and repair every broken image ------------------------------
bpy.ops.wm.open_mainfile(filepath=INIT_BLEND)

print("  BEFORE repair:")
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    print(f"    - {im.name:14s}  filepath={im.filepath!r}  "
          f"has_data={im.has_data}")

# Save-as so `//` anchors at the ground_truth/ directory before we rewrite
# paths.
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH, relative_remap=False)

# --- Repair --------------------------------------------------------------
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    color = color_for_image(im.name)
    if color is None:
        print(f"  SKIP {im.name}: cannot infer colour from name")
        continue
    rel = f"//textures/{color}.png"
    im.filepath     = rel
    im.filepath_raw = rel
    im.source       = 'FILE'
    # Reload from the newly-correct path.
    try:
        im.reload()
    except Exception as ex:
        print(f"  WARN reload({im.name}): {ex}")
    # Pack so `has_data` survives save-close-reopen in background mode.
    try:
        im.pack()
    except Exception as ex:
        print(f"  WARN pack({im.name}): {ex}")

print("  AFTER repair:")
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    resolved = os.path.normpath(bpy.path.abspath(im.filepath))
    exists = os.path.isfile(resolved)
    print(f"    - {im.name:14s}  filepath={im.filepath!r}  "
          f"has_data={im.has_data}  size={tuple(im.size)}  "
          f"resolved={resolved}  exists={exists}")

# Final save.
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
