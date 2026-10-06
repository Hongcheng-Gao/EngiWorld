"""Build `ground_truth/answer.blend` + `ground_truth/output/render.png` for
task GH03 — Triplanar Projection.

Open `init_file/scene.blend`, rebuild `TriplanarMat` as a triplanar-projection
shader driven by three Checker Texture samples (one per world-axis plane),
blended by the absolute value of the object-space normal raised to a small
power (for sharper masks). Render to `ground_truth/output/render.png` and save
the blend.

Graph outline:

    TexCoord.Object --> SeparateXYZ --> (y,z), (z,x), (x,y) CombineXYZ
                                              |      |      |
                                              v      v      v
                                         Checker_X Checker_Y Checker_Z
                                              |      |      |
                                              +------+------+ weighted blend
                                                     |
                                           Principled.Base Color

    NewGeometry.Normal --> SeparateXYZ --> abs(x), abs(y), abs(z)
                                            ^4 each (sharpen mask)
                                            normalise by sum
                                            -> MixRGB factors

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
OUT_PNG    = os.path.join(TASK_DIR, "ground_truth", "output", "render.png")
os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


CHECKER_SCALE   = 4.0
CHECKER_COLOR_A = (0.8, 0.1, 0.1, 1.0)   # red
CHECKER_COLOR_B = (0.9, 0.9, 0.9, 1.0)   # off-white
BLEND_SHARPNESS = 4.0                    # POWER exponent on |n|


def rebuild_triplanar_material(mat):
    """Rebuild `mat` as a triplanar projection shader."""
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    # === Core output/surface nodes ==========================================
    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    if "Roughness" in n_bsdf.inputs:
        n_bsdf.inputs["Roughness"].default_value = 0.5
    if "Metallic" in n_bsdf.inputs:
        n_bsdf.inputs["Metallic"].default_value = 0.0

    n_out.location  = (2400, 0)
    n_bsdf.location = (2100, 0)

    # === Position source: Texture Coordinate (Object space) =================
    n_tc   = nt.nodes.new("ShaderNodeTexCoord")
    n_tc.location = (-1200, 200)

    n_sepP = nt.nodes.new("ShaderNodeSeparateXYZ")
    n_sepP.location = (-900, 200)

    nt.links.new(n_tc.outputs["Object"], n_sepP.inputs["Vector"])

    # === Three combined 2D plane coords: (y,z), (z,x), (x,y) ===============
    # Each pair feeds a Checker texture (Vector input reads (u,v,w)).
    n_cmbX = nt.nodes.new("ShaderNodeCombineXYZ")  # (y, z, 0) for X plane
    n_cmbY = nt.nodes.new("ShaderNodeCombineXYZ")  # (z, x, 0) for Y plane
    n_cmbZ = nt.nodes.new("ShaderNodeCombineXYZ")  # (x, y, 0) for Z plane
    n_cmbX.location = (-600, 400)
    n_cmbY.location = (-600, 100)
    n_cmbZ.location = (-600, -200)

    # X-plane: YZ coords
    nt.links.new(n_sepP.outputs["Y"], n_cmbX.inputs["X"])
    nt.links.new(n_sepP.outputs["Z"], n_cmbX.inputs["Y"])

    # Y-plane: ZX coords
    nt.links.new(n_sepP.outputs["Z"], n_cmbY.inputs["X"])
    nt.links.new(n_sepP.outputs["X"], n_cmbY.inputs["Y"])

    # Z-plane: XY coords
    nt.links.new(n_sepP.outputs["X"], n_cmbZ.inputs["X"])
    nt.links.new(n_sepP.outputs["Y"], n_cmbZ.inputs["Y"])

    # === Three Checker textures ============================================
    def make_checker(name, x, y):
        n = nt.nodes.new("ShaderNodeTexChecker")
        n.name = name
        n.label = name
        n.location = (x, y)
        n.inputs["Color1"].default_value = CHECKER_COLOR_A
        n.inputs["Color2"].default_value = CHECKER_COLOR_B
        n.inputs["Scale"].default_value  = CHECKER_SCALE
        return n

    n_chkX = make_checker("CheckerX", -300, 400)
    n_chkY = make_checker("CheckerY", -300, 100)
    n_chkZ = make_checker("CheckerZ", -300, -200)

    nt.links.new(n_cmbX.outputs["Vector"], n_chkX.inputs["Vector"])
    nt.links.new(n_cmbY.outputs["Vector"], n_chkY.inputs["Vector"])
    nt.links.new(n_cmbZ.outputs["Vector"], n_chkZ.inputs["Vector"])

    # === Normal-based blend weights ========================================
    n_geom = nt.nodes.new("ShaderNodeNewGeometry")
    n_geom.location = (-1200, -500)

    n_sepN = nt.nodes.new("ShaderNodeSeparateXYZ")
    n_sepN.location = (-900, -500)

    nt.links.new(n_geom.outputs["Normal"], n_sepN.inputs["Vector"])

    def math_node(op, x, y, inp1_default=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.location  = (x, y)
        if inp1_default is not None:
            n.inputs[1].default_value = inp1_default
        return n

    # abs(nx), abs(ny), abs(nz)
    n_absX = math_node('ABSOLUTE', -600, -400)
    n_absY = math_node('ABSOLUTE', -600, -550)
    n_absZ = math_node('ABSOLUTE', -600, -700)
    nt.links.new(n_sepN.outputs["X"], n_absX.inputs[0])
    nt.links.new(n_sepN.outputs["Y"], n_absY.inputs[0])
    nt.links.new(n_sepN.outputs["Z"], n_absZ.inputs[0])

    # |n|^k for sharper masks
    n_powX = math_node('POWER', -400, -400, inp1_default=BLEND_SHARPNESS)
    n_powY = math_node('POWER', -400, -550, inp1_default=BLEND_SHARPNESS)
    n_powZ = math_node('POWER', -400, -700, inp1_default=BLEND_SHARPNESS)
    nt.links.new(n_absX.outputs[0], n_powX.inputs[0])
    nt.links.new(n_absY.outputs[0], n_powY.inputs[0])
    nt.links.new(n_absZ.outputs[0], n_powZ.inputs[0])

    # sum = |nx|^k + |ny|^k + |nz|^k
    n_sumXY = math_node('ADD', -200, -500)
    nt.links.new(n_powX.outputs[0], n_sumXY.inputs[0])
    nt.links.new(n_powY.outputs[0], n_sumXY.inputs[1])

    n_sumAll = math_node('ADD', 0, -500)
    nt.links.new(n_sumXY.outputs[0], n_sumAll.inputs[0])
    nt.links.new(n_powZ.outputs[0], n_sumAll.inputs[1])

    # Normalize: wX = |nx|^k / sum, etc.
    n_wX = math_node('DIVIDE', 200, -400)
    n_wY = math_node('DIVIDE', 200, -550)
    n_wZ = math_node('DIVIDE', 200, -700)
    nt.links.new(n_powX.outputs[0], n_wX.inputs[0])
    nt.links.new(n_sumAll.outputs[0], n_wX.inputs[1])
    nt.links.new(n_powY.outputs[0], n_wY.inputs[0])
    nt.links.new(n_sumAll.outputs[0], n_wY.inputs[1])
    nt.links.new(n_powZ.outputs[0], n_wZ.inputs[0])
    nt.links.new(n_sumAll.outputs[0], n_wZ.inputs[1])

    # === Weighted sum of the three checker colors =========================
    # sum = wX*colX + wY*colY + wZ*colZ
    # Use Vector Math MULTIPLY (scalar) and ADD.  Actually ShaderNodeMixRGB
    # with MIX is simplest:
    #     stage1 = mix(black, colX, wX)           # (since weights sum to 1)
    # But simpler: do the explicit weighted sum with Vector Math on RGB
    # via three Multiply and two Adds.  Use ShaderNodeMix type RGB.
    #
    # We'll do it cleanly with three Mix (type RGB, blend_type 'MIX')
    # nodes combined, but blend_type MIX does lerp, not weighted sum.
    # The cleanest is to multiply each color by its weight (ShaderNodeMixRGB
    # with MULTIPLY blend and Fac=1 against a grey? no that's for color mul).
    #
    # Simplest reliable approach: use ShaderNodeVectorMath on the RGB
    # (treating each color as a vector), SCALE by the weight, then ADD.
    def vec_math(op, x, y):
        n = nt.nodes.new("ShaderNodeVectorMath")
        n.operation = op
        n.location = (x, y)
        return n

    n_mulX = vec_math('SCALE', 600, 400)
    n_mulY = vec_math('SCALE', 600, 100)
    n_mulZ = vec_math('SCALE', 600, -200)

    # ShaderNodeVectorMath SCALE takes Vector on input[0] and a scalar on
    # input[2] ("Scale").  Hook the checker colors as vectors (RGB is a
    # Color socket but converts implicitly) and the normalized weights as
    # the scalar.
    nt.links.new(n_chkX.outputs["Color"], n_mulX.inputs[0])
    nt.links.new(n_wX.outputs[0],          n_mulX.inputs["Scale"])
    nt.links.new(n_chkY.outputs["Color"], n_mulY.inputs[0])
    nt.links.new(n_wY.outputs[0],          n_mulY.inputs["Scale"])
    nt.links.new(n_chkZ.outputs["Color"], n_mulZ.inputs[0])
    nt.links.new(n_wZ.outputs[0],          n_mulZ.inputs["Scale"])

    # Add them: sumXY = mulX + mulY; sumAll = sumXY + mulZ.
    n_addXY  = vec_math('ADD', 900, 250)
    n_addAll = vec_math('ADD', 1200, 0)
    nt.links.new(n_mulX.outputs[0], n_addXY.inputs[0])
    nt.links.new(n_mulY.outputs[0], n_addXY.inputs[1])
    nt.links.new(n_addXY.outputs[0], n_addAll.inputs[0])
    nt.links.new(n_mulZ.outputs[0], n_addAll.inputs[1])

    # Feed the Principled BSDF Base Color with the weighted sum.
    nt.links.new(n_addAll.outputs[0], n_bsdf.inputs["Base Color"])
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

    return mat


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene = bpy.context.scene
torus = bpy.data.objects["TorusTri"]
mat   = bpy.data.materials["TriplanarMat"]

rebuild_triplanar_material(mat)

# Make torus active+selected at save-time.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = torus
torus.select_set(True)

# --- Render settings ----------------------------------------------------
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.seed = 0
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT_PNG
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0

# --- Audit before render ------------------------------------------------
print("-" * 60)
print(f"  Torus verts/polys  : {len(torus.data.vertices)}/"
      f"{len(torus.data.polygons)}")
print(f"  UV layers          : {len(torus.data.uv_layers)}")
print(f"  Material nodes     : "
      f"{[n.bl_idname for n in mat.node_tree.nodes]}")
n_checker = sum(1 for n in mat.node_tree.nodes
                if n.bl_idname == 'ShaderNodeTexChecker')
print(f"  Checker nodes      : {n_checker}")
print(f"  Engine/samples     : {scene.render.engine}/"
      f"{scene.cycles.samples}")
print("-" * 60)

# --- Render -------------------------------------------------------------
print(f"  rendering -> {OUT_PNG}")
bpy.ops.render.render(write_still=True)
print(f"  render done")

# --- Save the answer blend ---------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
