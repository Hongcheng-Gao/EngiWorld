"""Build `ground_truth/answer.blend` and `ground_truth/wood.png` for task GH01.

Open init_file/scene.blend, rebuild `WoodMat` as a procedural wood shader
(noise-warped UV driving a BANDS wave texture piped through a 3-stop brown
color ramp, then into the Principled BSDF Base Color), bake DIFFUSE COLOR
into `WoodBake`, save the PNG, and save the .blend.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
OUT_PNG    = os.path.join(TASK_DIR, "ground_truth", "wood.png")
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)


# Three-stop brown color ramp: dark/medium/light brown. These are the 3
# distinct color clusters the eval looks for.
RAMP_STOPS = [
    (0.00, (0.015, 0.008, 0.004, 1.0)),  # very dark brown (linear)
    (0.50, (0.25,  0.12,  0.05,  1.0)),  # medium brown
    (1.00, (0.80,  0.60,  0.38,  1.0)),  # light brown
]


def rebuild_wood_material(mat, bake_img):
    """Rebuild WoodMat as a procedural wood shader. Keep the bake image
    texture node so `bpy.ops.object.bake` writes into it."""
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    # --- Node creation ---------------------------------------------------
    n_out   = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf  = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_ramp  = nt.nodes.new("ShaderNodeValToRGB")          # Color Ramp
    n_wave  = nt.nodes.new("ShaderNodeTexWave")
    n_vmul  = nt.nodes.new("ShaderNodeVectorMath")        # multiply X
    n_vadd  = nt.nodes.new("ShaderNodeVectorMath")        # add warp
    n_noise = nt.nodes.new("ShaderNodeTexNoise")
    n_uv    = nt.nodes.new("ShaderNodeTexCoord")
    n_bake  = nt.nodes.new("ShaderNodeTexImage")          # bake target

    n_out.location   = (1400,   0)
    n_bsdf.location  = (1100,   0)
    n_ramp.location  = ( 800,   0)
    n_wave.location  = ( 500,   0)
    n_vmul.location  = ( 250,   0)
    n_vadd.location  = (   0,   0)
    n_noise.location = (-350,-200)
    n_uv.location    = (-700,   0)
    n_bake.location  = ( 500, -400)

    # --- Configure ------------------------------------------------------
    # Noise texture that warps the UV.
    n_noise.inputs["Scale"].default_value  = 3.0
    n_noise.inputs["Detail"].default_value = 4.0
    try:
        n_noise.inputs["Distortion"].default_value = 0.5
    except KeyError:
        pass

    # Vector Add: warp + original UV.
    n_vadd.operation = 'ADD'

    # Vector Multiply: amplify the X component so the ring direction is
    # visible (8 cycles of the wave across the 2 BU plane).
    n_vmul.operation = 'MULTIPLY'
    n_vmul.inputs[1].default_value = (8.0, 1.0, 1.0)

    # Wave texture: BANDS, scale 8 (along X after the multiply).
    n_wave.wave_type         = 'BANDS'
    n_wave.bands_direction   = 'X'
    n_wave.inputs["Scale"].default_value      = 1.0
    try:
        n_wave.inputs["Distortion"].default_value = 0.0
    except KeyError:
        pass
    try:
        n_wave.inputs["Detail"].default_value = 0.0
    except KeyError:
        pass

    # Color ramp — 3 brown stops (default interpolation: LINEAR -> smooth
    # gradient between stops; that still yields 3 dominant clusters when
    # quantized).
    ramp = n_ramp.color_ramp
    ramp.interpolation = 'LINEAR'
    # Default ramp has 2 stops at 0.0 and 1.0; we need 3 total.
    existing = sorted(e.position for e in ramp.elements)
    for target_pos in (0.5,):
        if not any(abs(p - target_pos) < 1e-5 for p in existing):
            ramp.elements.new(target_pos)
    # Sort + assign in position order.
    indexed = sorted(range(len(ramp.elements)),
                     key=lambda i: ramp.elements[i].position)
    if len(indexed) != len(RAMP_STOPS):
        raise RuntimeError(
            f"unexpected ramp element count: {len(indexed)} "
            f"(expected {len(RAMP_STOPS)})")
    for k, idx in enumerate(indexed):
        pos, col = RAMP_STOPS[k]
        el = ramp.elements[idx]
        el.position = pos
        el.color = col

    # Principled BSDF defaults.
    if "Roughness" in n_bsdf.inputs:
        n_bsdf.inputs["Roughness"].default_value = 0.7
    if "Metallic" in n_bsdf.inputs:
        n_bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular" in n_bsdf.inputs:
        n_bsdf.inputs["Specular"].default_value = 0.3
    elif "Specular IOR Level" in n_bsdf.inputs:
        n_bsdf.inputs["Specular IOR Level"].default_value = 0.3

    # Bake target image texture node — must be the ACTIVE node.
    n_bake.image = bake_img
    n_bake.name  = "WoodBakeNode"

    # --- Wire -----------------------------------------------------------
    nt.links.new(n_uv.outputs["UV"],        n_noise.inputs["Vector"])
    nt.links.new(n_uv.outputs["UV"],        n_vadd.inputs[0])
    nt.links.new(n_noise.outputs["Color"],  n_vadd.inputs[1])
    nt.links.new(n_vadd.outputs["Vector"],  n_vmul.inputs[0])
    nt.links.new(n_vmul.outputs["Vector"],  n_wave.inputs["Vector"])
    nt.links.new(n_wave.outputs["Fac"],     n_ramp.inputs["Fac"])
    nt.links.new(n_ramp.outputs["Color"],   n_bsdf.inputs["Base Color"])
    nt.links.new(n_bsdf.outputs["BSDF"],    n_out.inputs["Surface"])

    # Make the bake image node the active one.
    for n in nt.nodes:
        n.select = False
    n_bake.select = True
    nt.nodes.active = n_bake

    return mat


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene  = bpy.context.scene
board  = bpy.data.objects["Board"]
bake_img = bpy.data.images["WoodBake"]
mat    = bpy.data.materials["WoodMat"]

rebuild_wood_material(mat, bake_img)

# Make sure Board is the active+selected object before bake.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = board
board.select_set(True)

# Bake settings.
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 4     # low samples OK for a flat shader
scene.cycles.use_denoising = False
scene.cycles.seed = 0
scene.render.threads_mode = "FIXED"
scene.render.threads = 1
scene.cycles.bake_type = 'DIFFUSE'

try:
    scene.render.bake.use_pass_direct   = False
    scene.render.bake.use_pass_indirect = False
    scene.render.bake.use_pass_color    = True
    scene.render.bake.use_clear         = True
    scene.render.bake.margin            = 4
except AttributeError:
    pass

print("  running DIFFUSE/COLOR bake ...")
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'},
                    save_mode='INTERNAL', margin=4, use_clear=True)

# Save the baked image as PNG.
bake_img.filepath_raw = OUT_PNG
bake_img.file_format = 'PNG'
bake_img.save()

# Quick stats.
px = list(bake_img.pixels)
w, h = bake_img.size
n_pixels = w * h
R_mean = sum(px[i * 4 + 0] for i in range(n_pixels)) / n_pixels
G_mean = sum(px[i * 4 + 1] for i in range(n_pixels)) / n_pixels
B_mean = sum(px[i * 4 + 2] for i in range(n_pixels)) / n_pixels
print("-" * 60)
print(f"  baked image      : {w}x{h}")
print(f"  mean RGB         : ({R_mean:.4f}, {G_mean:.4f}, {B_mean:.4f})")
print(f"  saved PNG        : {OUT_PNG}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
