"""Build `ground_truth/normal_bake.png` and `ground_truth/answer.blend`
for task DH01 — Normal Bake high->low.

Opens init_file/hi_low.blend, configures a Cycles selected-to-active
tangent-space normal bake with cage extrusion 0.08, bakes into the
`BakeNormal` image, saves the image as ground_truth/normal_bake.png,
and saves the blend as ground_truth/answer.blend.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "hi_low.blend")
OUT_PNG    = os.path.join(TASK_DIR, "ground_truth", "normal_bake.png")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene    = bpy.context.scene
highpoly = bpy.data.objects["HighPoly"]
lowpoly  = bpy.data.objects["LowPoly"]

# --- Selection: HighPoly selected, LowPoly ACTIVE ------------------------
bpy.ops.object.select_all(action='DESELECT')
highpoly.select_set(True)
lowpoly.select_set(True)
bpy.context.view_layer.objects.active = lowpoly

# --- Ensure the BakeNormal image texture node is the active node on the
#     LowPoly material's node tree. ---------------------------------------
mat = lowpoly.data.materials[0]
nt  = mat.node_tree
bake_img = bpy.data.images["BakeNormal"]
tex_node = None
for n in nt.nodes:
    n.select = False
    if n.type == "TEX_IMAGE" and n.image is not None and \
            n.image.name == "BakeNormal":
        tex_node = n
if tex_node is None:
    raise RuntimeError(
        "No Image Texture node referencing 'BakeNormal' found on LowPolyMat"
    )
tex_node.select = True
nt.nodes.active = tex_node

# --- Bake settings --------------------------------------------------------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.bake_type = 'NORMAL'
scene.cycles.samples = 8
scene.cycles.use_denoising = False
scene.cycles.seed = 0

bake = scene.render.bake
bake.use_selected_to_active = True
bake.use_cage = False
bake.cage_extrusion = 0.08
bake.normal_space = 'TANGENT'
bake.normal_r = 'POS_X'
bake.normal_g = 'POS_Y'
bake.normal_b = 'POS_Z'
try:
    bake.use_clear = True
    bake.margin = 4
except AttributeError:
    pass

print("  running NORMAL bake (selected-to-active) ...")
bpy.ops.object.bake(
    type='NORMAL',
    use_selected_to_active=True,
    cage_extrusion=0.08,
    normal_space='TANGENT',
)

# --- Save the baked image out to PNG -------------------------------------
bake_img.filepath_raw = OUT_PNG
bake_img.file_format = 'PNG'
bake_img.save()

# --- Audit quick stats on the baked pixels -------------------------------
px = list(bake_img.pixels)
n_pixels = len(px) // 4
sum_r = sum(px[i * 4 + 0] for i in range(n_pixels))
sum_g = sum(px[i * 4 + 1] for i in range(n_pixels))
sum_b = sum(px[i * 4 + 2] for i in range(n_pixels))
mean_r = sum_r / n_pixels
mean_g = sum_g / n_pixels
mean_b = sum_b / n_pixels
var_r = sum((px[i*4+0] - mean_r) ** 2 for i in range(n_pixels)) / n_pixels
var_g = sum((px[i*4+1] - mean_g) ** 2 for i in range(n_pixels)) / n_pixels
blue_strong = sum(1 for i in range(n_pixels)
                  if px[i * 4 + 2] > (100.0 / 255.0)) / n_pixels

print(f"  baked image size    : {tuple(bake_img.size)}")
print(f"  mean R              : {mean_r:.4f}")
print(f"  mean G              : {mean_g:.4f}")
print(f"  mean B              : {mean_b:.4f}")
print(f"  std  R              : {var_r ** 0.5:.4f}")
print(f"  std  G              : {var_g ** 0.5:.4f}")
print(f"  frac B > 100/255    : {blue_strong:.4f}")
print(f"  png written         : {OUT_PNG}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
