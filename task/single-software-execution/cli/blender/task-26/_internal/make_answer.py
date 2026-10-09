"""Build `ground_truth/answer.blend` + `ground_truth/output/render.png` for
task GH02 - Car Paint Shader.

Opens `init_file/scene.blend`, rebuilds the CarPaint material with an
explicit multi-lobe Principled BSDF structure (Metallic + Coat + Sheen),
renders the scene at 512x512, and saves both outputs.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_DIR    = os.path.join(TASK_DIR, "ground_truth")
OUT_BLEND  = os.path.join(OUT_DIR, "answer.blend")
OUT_PNG    = os.path.join(OUT_DIR, "output", "render.png")
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


def set_if_present(inputs, name, value):
    """Set a Principled input by name, if present in this Blender build."""
    if name in inputs:
        inputs[name].default_value = value
        return True
    return False


def rebuild_car_paint(mat):
    """Rebuild CarPaint as a multi-lobe Principled BSDF:
        - Metallic   = 0.9
        - Roughness  = 0.3   (broad 'metal flake' lobe)
        - Coat       = 1.0   (sharp clearcoat lobe)
        - Coat Rough = 0.03
        - Coat IOR   = 1.5
        - Sheen      = 0.2
    """
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_out.location  = (400, 0)
    n_bsdf.location = (100, 0)

    # Base color - dark metallic blue.
    set_if_present(n_bsdf.inputs, "Base Color", (0.1, 0.1, 0.3, 1.0))

    # Core metallic lobe.
    set_if_present(n_bsdf.inputs, "Metallic",  0.9)
    set_if_present(n_bsdf.inputs, "Roughness", 0.3)

    # Clearcoat lobe (Blender 4.1 uses "Coat Weight" etc.).
    if not set_if_present(n_bsdf.inputs, "Coat Weight", 1.0):
        set_if_present(n_bsdf.inputs, "Coat", 1.0)            # older name
        set_if_present(n_bsdf.inputs, "Clearcoat", 1.0)       # legacy
    if not set_if_present(n_bsdf.inputs, "Coat Roughness", 0.03):
        set_if_present(n_bsdf.inputs, "Clearcoat Roughness", 0.03)
    set_if_present(n_bsdf.inputs, "Coat IOR", 1.5)

    # Sheen lobe.
    if not set_if_present(n_bsdf.inputs, "Sheen Weight", 0.2):
        set_if_present(n_bsdf.inputs, "Sheen", 0.2)
    set_if_present(n_bsdf.inputs, "Sheen Roughness", 0.5)
    set_if_present(n_bsdf.inputs, "Sheen Tint", (1.0, 1.0, 1.0, 1.0))

    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

    # Dump for audit.
    print("-" * 60)
    print("  Principled inputs:")
    for i, sock in enumerate(n_bsdf.inputs):
        try:
            v = sock.default_value
            if isinstance(v, float):
                v_str = f"{v:.3f}"
            else:
                try:
                    v_str = str(list(v))
                except TypeError:
                    v_str = str(v)
            print(f"    [{i:>2}] {sock.name:<24} = {v_str}")
        except Exception as ex:
            print(f"    [{i:>2}] {sock.name:<24} = <err: {ex}>")
    print("-" * 60)
    return mat


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene  = bpy.context.scene
sphere = bpy.data.objects["PaintBall"]
mat    = bpy.data.materials["CarPaint"]

rebuild_car_paint(mat)

# Render settings (preserve whatever the init set + enforce the important
# ones explicitly, since the eval is sensitive to specular peaks).
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
# Same exposure as the init - see init_file/scene.blend rationale.
scene.view_settings.exposure = -1.5
scene.view_settings.gamma = 1.0
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT_PNG

print(f"  rendering 512x512 Cycles -> {OUT_PNG} ...")
bpy.ops.render.render(write_still=True)
assert os.path.isfile(OUT_PNG), f"render did not produce {OUT_PNG}"
print(f"  render written -> {OUT_PNG}  size={os.path.getsize(OUT_PNG)} bytes")

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
