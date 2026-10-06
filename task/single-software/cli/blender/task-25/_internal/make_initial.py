"""Build `init_file/scene.blend` for task GH01 — Procedural Wood Material.

Scene:
  - A UV-unwrapped plane `Board` at origin, 2x2 BU, with a 512x512 blank RGBA
    image `WoodBake` set as the active image texture in a grey Principled
    material `WoodMat`. The testee must rebuild `WoodMat` as a procedural
    wood shader and bake into `WoodBake`.
  - Render engine: CYCLES, CPU, deterministic seed, low thread count.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bpy


HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.textures, bpy.data.node_groups):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_board():
    """Create a UV-unwrapped 2x2 BU plane named `Board` at the origin."""
    bpy.ops.mesh.primitive_plane_add(size=2.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = "Board"
    obj.data.name = "BoardMesh"

    # Ensure a UV layer exists (the primitive_plane_add operator already
    # creates one, but we force a clean unwrap for reproducibility).
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')

    return obj


def make_wood_bake_image():
    """Create a blank 512x512 RGBA image named `WoodBake`."""
    img = bpy.data.images.new(
        name="WoodBake", width=512, height=512,
        alpha=True, float_buffer=False,
    )
    img.generated_color = (0.5, 0.5, 0.5, 1.0)
    img.generated_type = 'BLANK'
    # Force pixel buffer to materialize.
    blank = [0.5, 0.5, 0.5, 1.0] * (512 * 512)
    img.pixels = blank
    return img


def build_wood_material(bake_img):
    """Plain grey Principled BSDF with the bake image texture wired as an
    Image Texture node and marked active/selected. The testee must rebuild
    the node tree into a procedural wood shader; the bake target node will
    remain the `WoodBake` image texture."""
    mat = bpy.data.materials.new(name="WoodMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_tex  = nt.nodes.new("ShaderNodeTexImage")
    n_out.location  = ( 400, 0)
    n_bsdf.location = ( 100, 0)
    n_tex.location  = (-300, 0)

    n_tex.image = bake_img
    n_tex.name  = "WoodBakeNode"

    if "Base Color" in n_bsdf.inputs:
        n_bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    if "Roughness" in n_bsdf.inputs:
        n_bsdf.inputs["Roughness"].default_value = 0.7
    if "Metallic" in n_bsdf.inputs:
        n_bsdf.inputs["Metallic"].default_value = 0.0

    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

    # Bake writes into the active Image Texture node on the active
    # material slot. Select & activate the bake node so the scene is
    # already "ready to bake".
    for n in nt.nodes:
        n.select = False
    n_tex.select = True
    nt.nodes.active = n_tex

    return mat


def set_render_settings(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
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


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

board  = make_board()
img    = make_wood_bake_image()
mat    = build_wood_material(img)
board.data.materials.append(mat)

# Ensure Board is the active+selected object at save-time.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = board
board.select_set(True)

set_render_settings(bpy.context.scene)

# --- Audit --------------------------------------------------------------
print("-" * 60)
print(f"  Board object   : {board.name} ({board.type})")
print(f"  Board verts    : {len(board.data.vertices)}  polys={len(board.data.polygons)}")
print(f"  UV layers      : {[l.name for l in board.data.uv_layers]}")
print(f"  Material       : {board.data.materials[0].name}")
print(f"  WoodBake image : size={tuple(img.size)}")
active = mat.node_tree.nodes.active
print(f"  Active node    : {active.name if active else 'None'} (type={getattr(active, 'type', None)})")
print(f"  Engine/samples : {bpy.context.scene.render.engine}/{bpy.context.scene.cycles.samples}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
