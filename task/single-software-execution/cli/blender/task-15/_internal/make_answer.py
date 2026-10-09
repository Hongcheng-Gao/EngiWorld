"""Build `ground_truth/answer.blend` + output/{raw,glare}.png for CH04.

Open init_file/scene.blend. Enable the compositor and build:

  Render Layers.Image --+--------------------------------+--> File Output.raw
                        |                                |
                        +--> Glare (FOG_GLOW, mix=1.0) --+--> File Output.glare

A single File Output node with two slots keeps output routing simple.
The Glare node is configured as FOG_GLOW with a large size so the bright
emissive source produces a generous halo that fills the annulus ROI used
by eval.py.

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

os.makedirs(OUT_DIR, exist_ok=True)


def apply_render_settings(scene):
    scene.render.engine        = "CYCLES"
    scene.cycles.samples       = 32
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.device        = "CPU"
    scene.render.resolution_x  = 512
    scene.render.resolution_y  = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_start   = 1
    scene.frame_end     = 1
    scene.frame_current = 1


def build_compositor(scene, output_dir):
    scene.use_nodes = True
    tree = scene.node_tree
    for n in list(tree.nodes):
        tree.nodes.remove(n)

    # Source: Render Layers.
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    render_layers.location = (-500, 0)

    # Glare node (FOG_GLOW).
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.location = (-100, -150)
    glare.glare_type = 'FOG_GLOW'
    # Large size -> broad halo so the annulus 40-100 px gathers energy.
    # Valid FOG_GLOW sizes are 2..9 in Blender 4.1; 9 gives the widest glow.
    glare.size = 9
    glare.threshold = 0.5
    # mix = 1.0 means output is 100% glare component (no original image).
    # This makes the difference vs raw much larger, satisfying the 2x
    # energy-in-annulus test. (mix = 0.0 would be "glare mixed with
    # original at 50/50"; mix = -1.0 would be "original only".)
    glare.mix = 1.0
    # Quality: 0 (high) gives the best-looking FOG_GLOW.
    glare.quality = 'HIGH'

    # File Output node with two slots: raw + glare.
    file_out = tree.nodes.new("CompositorNodeOutputFile")
    file_out.location = (300, 0)
    file_out.base_path = output_dir
    file_out.format.file_format = 'PNG'
    file_out.format.color_mode  = 'RGBA'
    file_out.format.color_depth = '8'

    # Rename first slot "raw" and add a second slot "glare".
    file_out.file_slots[0].path = "raw"
    file_out.file_slots.new("glare")

    # Composite node (Blender writes this as the main render result; the
    # actual PNG outputs come from the File Output node).
    composite = tree.nodes.new("CompositorNodeComposite")
    composite.location = (300, 250)

    # Wiring:
    tree.links.new(render_layers.outputs["Image"], composite.inputs["Image"])
    tree.links.new(render_layers.outputs["Image"], file_out.inputs[0])
    tree.links.new(render_layers.outputs["Image"], glare.inputs["Image"])
    tree.links.new(glare.outputs["Image"],         file_out.inputs[1])

    return tree, render_layers, glare, file_out


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene = bpy.context.scene
apply_render_settings(scene)

tree, rl, glare, fo = build_compositor(scene, OUT_DIR)

# Set a dummy render filepath (the real PNGs come from File Output).
scene.render.filepath = os.path.join(OUT_DIR, "render_dummy_")

# Save the .blend first so it reflects the final compositor graph.
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")

# Render once to trigger File Output.
bpy.ops.render.render(write_still=True)

# File Output writes <slot_path><frame 4-digit>.png by default.
raw_src   = os.path.join(OUT_DIR, "raw0001.png")
glare_src = os.path.join(OUT_DIR, "glare0001.png")

# Normalize filenames to raw.png / glare.png (spec-required).
raw_dst   = os.path.join(OUT_DIR, "raw.png")
glare_dst = os.path.join(OUT_DIR, "glare.png")
for src, dst in ((raw_src, raw_dst), (glare_src, glare_dst)):
    if os.path.isfile(src):
        if os.path.isfile(dst):
            os.remove(dst)
        os.replace(src, dst)

# Also remove the dummy render PNG that bpy.ops.render.render(write_still=True)
# writes via scene.render.filepath; the spec-required outputs are raw.png and
# glare.png only.
dummy_png = os.path.join(OUT_DIR, "render_dummy_.png")
if os.path.isfile(dummy_png):
    os.remove(dummy_png)

print("-" * 60)
print(f"  use_nodes            = {scene.use_nodes}")
print(f"  compositor nodes     = {[n.bl_idname for n in tree.nodes]}")
print(f"  glare.glare_type     = {glare.glare_type}")
print(f"  glare.size/threshold = {glare.size} / {glare.threshold}")
print(f"  glare.mix/quality    = {glare.mix} / {glare.quality}")
print(f"  file_out.base_path   = {fo.base_path}")
print(f"  file_out.slots       = {[s.path for s in fo.file_slots]}")
print(f"  raw.png exists       = {os.path.isfile(raw_dst)}")
print(f"  glare.png exists     = {os.path.isfile(glare_dst)}")
print("-" * 60)
