"""Build `ground_truth/answer.blend` + `output/combined.exr` for CH03.

Open `init_file/scene.blend`. For each sphere material:
  - Add a `ShaderNodeOutputAOV` whose `.name` is `'custom_col'`.
  - Wire the BSDF's Base Color RGBA value into the AOV's `Color` input via
    a `ShaderNodeRGB` node (so the AOV pass pixels equal the Base Color
    over the sphere's silhouette, with no shading modulation).

Add a scene-level AOV declaration:
  `aov = view_layer.aovs.add(); aov.name = 'custom_col'; aov.type = 'COLOR'`.

Enable view-layer passes: Combined, Depth (Z), Normal.
Set render format to OPEN_EXR_MULTILAYER (RGBA, 32-bit float).
Set scene.render.filepath to `<ground_truth>/output/combined.exr` and render.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
GT_DIR     = os.path.join(TASK_DIR, "ground_truth")
OUT_BLEND  = os.path.join(GT_DIR, "answer.blend")
OUT_DIR    = os.path.join(GT_DIR, "output")
# OPEN_EXR_MULTILAYER uses whatever extension Blender appends; we want the
# produced filename to be exactly `combined.exr`. Blender resolves
# render.filepath + ".exr" when file_format is OPEN_EXR_MULTILAYER, so set
# filepath without the extension.
OUT_EXR_BASE = os.path.join(OUT_DIR, "combined")
OUT_EXR      = OUT_EXR_BASE + ".exr"

os.makedirs(OUT_DIR, exist_ok=True)


# AOV name used throughout this task.
AOV_NAME = "custom_col"


def apply_render_settings(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.cycles.seed = 0
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    # MultiLayer EXR, RGBA, 32-bit float.
    scene.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '32'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_start = 1
    scene.frame_end   = 1
    scene.frame_current = 1


def enable_passes(view_layer):
    view_layer.use_pass_combined = True
    view_layer.use_pass_z = True
    view_layer.use_pass_normal = True


def declare_aov(view_layer, name):
    # Remove any existing AOV with the same name so this is idempotent.
    for existing in list(view_layer.aovs):
        if existing.name == name:
            try:
                view_layer.aovs.remove(existing)
            except Exception:
                pass
    aov = view_layer.aovs.add()
    aov.name = name
    aov.type = 'COLOR'
    return aov


def wire_material_aov(mat, aov_name):
    """Ensure the material's node tree has:
      - a ShaderNodeRGB holding the Principled BSDF's Base Color RGBA
      - a ShaderNodeOutputAOV named `aov_name`
      - RGB.Color -> AOV.Color (so the pass is pure Base Color)
    """
    if mat is None or not mat.use_nodes:
        return None
    nt = mat.node_tree

    bsdf = next((n for n in nt.nodes
                 if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        return None
    base_color_rgba = tuple(bsdf.inputs["Base Color"].default_value)

    # Clean any previous AOV nodes on this material so re-runs are idempotent.
    for n in list(nt.nodes):
        if n.bl_idname == "ShaderNodeOutputAOV":
            nt.nodes.remove(n)

    rgb_node = nt.nodes.new("ShaderNodeRGB")
    rgb_node.name = f"RGB_{aov_name}"
    rgb_node.label = f"RGB_{aov_name}"
    rgb_node.outputs["Color"].default_value = base_color_rgba
    rgb_node.location = (-300, -300)

    aov_node = nt.nodes.new("ShaderNodeOutputAOV")
    aov_node.name = aov_name
    # The AOV output node's `.name` is ALSO the AOV channel name.
    # Set it explicitly in case Blender auto-uniqued the attribute.
    try:
        aov_node.name = aov_name
    except Exception:
        pass
    aov_node.location = (0, -300)

    nt.links.new(rgb_node.outputs["Color"], aov_node.inputs["Color"])
    return aov_node


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene = bpy.context.scene
apply_render_settings(scene)

# Enable passes and declare the AOV on the active view layer.
vl = scene.view_layers[0]
enable_passes(vl)
aov = declare_aov(vl, AOV_NAME)

# Wire AOV on each sphere material.
sphere_names = ("Sphere_R", "Sphere_G", "Sphere_B")
wired = []
for name in sphere_names:
    obj = bpy.data.objects.get(name)
    if obj is None or not obj.data.materials:
        continue
    mat = obj.data.materials[0]
    node = wire_material_aov(mat, AOV_NAME)
    wired.append((name, mat.name,
                  node.name if node else None,
                  node.bl_idname if node else None))

# Set render output path (no extension; Blender appends .exr).
scene.render.filepath = OUT_EXR_BASE

# Save the .blend first.
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")

# Render once -- writes MultiLayer EXR to OUT_EXR.
bpy.ops.render.render(write_still=True)

print("-" * 60)
print(f"  engine/samples     = {scene.render.engine}/{scene.cycles.samples}")
print(f"  file_format        = {scene.render.image_settings.file_format}")
print(f"  color_mode/depth   = "
      f"{scene.render.image_settings.color_mode}/"
      f"{scene.render.image_settings.color_depth}")
print(f"  use_pass_combined  = {vl.use_pass_combined}")
print(f"  use_pass_z         = {vl.use_pass_z}")
print(f"  use_pass_normal    = {vl.use_pass_normal}")
print(f"  aovs (vl0)         = {[(a.name, a.type) for a in vl.aovs]}")
for name, matname, node, idname in wired:
    print(f"  {name}.material={matname} AOV_node={node} ({idname})")
print(f"  exr exists         = {os.path.isfile(OUT_EXR)}")
if os.path.isfile(OUT_EXR):
    print(f"  exr size bytes     = {os.path.getsize(OUT_EXR)}")
print("-" * 60)
