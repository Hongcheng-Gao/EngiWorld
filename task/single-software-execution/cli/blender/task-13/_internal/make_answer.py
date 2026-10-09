"""Build `ground_truth/answer.blend` + beauty_0001.png + depth_0001.png for CH02.

Open init_file/scene.blend. Enable the compositor, add a Render Layers node,
a File Output node (two slots: beauty_ and depth_), and a Map Range node
(depth 0..20 -> 0..1 clamped). Wire:

  Render Layers.Image -> File Output.beauty_
  Render Layers.Depth -> Map Range.Value
  Map Range.Result    -> File Output.depth_

Set file_out.base_path = ground_truth/output/. Render frame 1
(bpy.ops.render.render(write_still=True)). Save answer.blend.

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
    scene.render.engine        = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.render.resolution_x  = 256
    scene.render.resolution_y  = 256
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode  = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.frame_start = 1
    scene.frame_end   = 1
    for vl in scene.view_layers:
        vl.use_pass_z = True


def build_compositor(scene, output_dir):
    scene.use_nodes = True
    tree = scene.node_tree
    # Clear any default nodes.
    for n in list(tree.nodes):
        tree.nodes.remove(n)

    # Render Layers source.
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    render_layers.location = (-400, 0)

    # Map Range for depth normalization (0..20 -> 0..1, clamped).
    map_range = tree.nodes.new("CompositorNodeMapRange")
    map_range.location = (-100, -200)
    map_range.inputs["From Min"].default_value = 0.0
    map_range.inputs["From Max"].default_value = 20.0
    map_range.inputs["To Min"].default_value   = 0.0
    map_range.inputs["To Max"].default_value   = 1.0
    map_range.use_clamp = True

    # File Output node with two slots.
    file_out = tree.nodes.new("CompositorNodeOutputFile")
    file_out.location = (300, 0)
    file_out.base_path = output_dir
    file_out.format.file_format = 'PNG'
    file_out.format.color_mode  = 'RGBA'
    file_out.format.color_depth = '8'

    # Rename the default "Image" slot to "beauty_".
    file_out.file_slots[0].path = "beauty_"
    # Add a second slot for depth.
    file_out.file_slots.new("depth_")

    # Wire: Render Layers.Image -> File Output.beauty_ (index 0).
    tree.links.new(render_layers.outputs["Image"], file_out.inputs[0])
    # Wire: Render Layers.Depth -> Map Range.Value.
    tree.links.new(render_layers.outputs["Depth"], map_range.inputs["Value"])
    # Wire: Map Range.Result -> File Output.depth_ (index 1).
    tree.links.new(map_range.outputs["Value"], file_out.inputs[1])

    return tree, render_layers, map_range, file_out


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

scene = bpy.context.scene
apply_render_settings(scene)

tree, rl, mr, fo = build_compositor(scene, OUT_DIR)

# Still set scene.render.filepath to a dummy temp (File Output handles real files).
scene.render.filepath = os.path.join(OUT_DIR, "render_dummy_")

# Save the .blend first.
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")

# Render once to trigger File Output.
bpy.ops.render.render(write_still=True)

beauty_path = os.path.join(OUT_DIR, "beauty_0001.png")
depth_path  = os.path.join(OUT_DIR, "depth_0001.png")

print("-" * 60)
print(f"  use_nodes          = {scene.use_nodes}")
print(f"  compositor nodes   = {[n.bl_idname for n in tree.nodes]}")
print(f"  file_out.base_path = {fo.base_path}")
print(f"  file_out.slots     = {[s.path for s in fo.file_slots]}")
print(f"  beauty exists      = {os.path.isfile(beauty_path)}")
print(f"  depth exists       = {os.path.isfile(depth_path)}")
print("-" * 60)
