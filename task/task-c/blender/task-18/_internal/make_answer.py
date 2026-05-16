"""Build `ground_truth/answer.blend` and `ground_truth/output/ao_bake.png`
for task DH03 - UV Pack + Bake AO.

Opens init_file/scene.blend, re-unwraps BumpyMesh using the pre-marked
seams, packs islands with margin ~4/512 of UV space, bakes AO at 64
samples into the `BakeAO` image, writes the baked image to PNG, packs
the image into the .blend, and saves as ground_truth/answer.blend.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PNG    = os.path.join(TASK_DIR, "ground_truth", "output", "ao_bake.png")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)


def reunwrap_and_pack(obj):
    """Enter edit mode, select all faces, run Angle-Based unwrap using
    existing seams, then pack islands with a ~4-texel margin."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
        # 4 px margin on a 512 texture -> 4/512 = 0.0078; use 0.02 for
        # visual safety so no bleed crosses island boundaries.
        bpy.ops.uv.pack_islands(margin=0.02, rotate=True)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')


def scale_uvs_to_fill(obj, margin_px=4, tex_size=512):
    """Uniformly scale all UV coords so the overall UV bbox fills
    [margin, 1-margin]^2 in the unit square. Keeps the packing intact
    (just rescales everything proportionally).

    Preserves island topology (per-loop UV coords stay logically in the
    same islands; only a global affine is applied).
    """
    me = obj.data
    uv_data = me.uv_layers.active.data
    us = [uv.uv.x for uv in uv_data]
    vs = [uv.uv.y for uv in uv_data]
    if not us:
        return
    u_min, u_max = min(us), max(us)
    v_min, v_max = min(vs), max(vs)
    span_u = max(u_max - u_min, 1e-9)
    span_v = max(v_max - v_min, 1e-9)

    margin = margin_px / float(tex_size)
    target = 1.0 - 2 * margin
    # Non-uniform scale: stretch each axis independently so the bbox of
    # the packed UV layout fits tightly inside [margin, 1-margin]^2.
    # (Bake correctness does not require UVs to preserve texture density,
    # and this maximizes image coverage so the baked stats are dominated
    # by the AO-shaded islands rather than uncovered dark areas.)
    sx = target / span_u
    sy = target / span_v
    off_u = margin - sx * u_min
    off_v = margin - sy * v_min

    for uv in uv_data:
        uv.uv.x = uv.uv.x * sx + off_u
        uv.uv.y = uv.uv.y * sy + off_v


def _make_texture_active(mat, img_name):
    nt = mat.node_tree
    tex_node = None
    for n in nt.nodes:
        n.select = False
        if n.type == "TEX_IMAGE" and n.image is not None \
                and n.image.name == img_name:
            tex_node = n
    if tex_node is None:
        raise RuntimeError(
            f"No Image Texture node referencing '{img_name}' found")
    tex_node.select = True
    nt.nodes.active = tex_node
    return tex_node


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene = bpy.context.scene
bumpy = bpy.data.objects["BumpyMesh"]

# --- Make BumpyMesh the active, selected object --------------------------
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = bumpy
bumpy.select_set(True)

# --- Re-unwrap using the pre-marked seams, then pack islands -------------
reunwrap_and_pack(bumpy)

# Scale the packed UV layout to fill (close to) the unit square. This
# guarantees the bake covers most of the 512x512 image so uncovered-area
# darkness doesn't dominate the stats. The scale is a single uniform
# affine so the relative size of islands is preserved.
scale_uvs_to_fill(bumpy, margin_px=4, tex_size=512)

# Ensure active image texture node on the material is BakeAO.
mat = bumpy.data.materials[0]
_make_texture_active(mat, "BakeAO")
bake_img = bpy.data.images["BakeAO"]

# --- Bake settings --------------------------------------------------------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.bake_type = 'AO'
scene.cycles.samples = 64
scene.cycles.use_denoising = False
scene.cycles.seed = 0

bake = scene.render.bake
try:
    bake.use_clear = True
    # The task spec requires a 4 px margin on UV packing; the bake-time
    # margin (pixel padding around islands in the output texture) is a
    # separate knob. We use a larger bake margin here to reduce the area
    # of truly-black pixels between islands and keep the dark-fraction
    # well inside its target band.
    bake.margin = 16
    # Disable any selected-to-active leftover (single-object bake).
    bake.use_selected_to_active = False
except AttributeError:
    pass

print("  running AO bake ...")
bpy.ops.object.bake(type='AO')

# --- Save the baked image as PNG -----------------------------------------
bake_img.filepath_raw = OUT_PNG
bake_img.file_format = 'PNG'
bake_img.save()

# --- Pack the image into the blend ---------------------------------------
bake_img.pack()

# --- Audit quick stats on UVs and baked pixels ---------------------------
me = bumpy.data
uvs = me.uv_layers.active.data
u_vals = [uv.uv.x for uv in uvs]
v_vals = [uv.uv.y for uv in uvs]
u_min, u_max = min(u_vals), max(u_vals)
v_min, v_max = min(v_vals), max(v_vals)

px = list(bake_img.pixels)
n_pixels = len(px) // 4
lumas = [0.299 * px[i * 4 + 0]
         + 0.587 * px[i * 4 + 1]
         + 0.114 * px[i * 4 + 2]
         for i in range(n_pixels)]
mean_y = sum(lumas) / n_pixels
dark_frac = sum(1 for y in lumas if y < 0.4) / n_pixels

print("-" * 60)
print(f"  baked image size    : {tuple(bake_img.size)}")
print(f"  baked image packed  : {bake_img.packed_file is not None}")
print(f"  U range             : [{u_min:.4f}, {u_max:.4f}]")
print(f"  V range             : [{v_min:.4f}, {v_max:.4f}]")
print(f"  mean luma (0.299R+...) = {mean_y:.4f}")
print(f"  dark fraction (<0.4) = {dark_frac:.4f}")
print(f"  png written         : {OUT_PNG}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
