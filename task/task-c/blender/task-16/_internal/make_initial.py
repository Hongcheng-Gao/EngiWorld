"""Build `init_file/hi_low.blend` for task DH01 — Normal Bake high->low.

Scene:
  - `HighPoly`: a 2x2x2 cube, subdivided 3 times, displaced with a
    procedural noise-based Z displacement so it has clear surface detail.
  - `LowPoly`: a slightly larger 2.1x2.1x2.1 cube that encloses HighPoly,
    UV-unwrapped via Smart UV project.
  - Material on LowPoly called `LowPolyMat` with an Image Texture node
    referencing a blank 1024x1024 image `BakeNormal` (default normal color
    (0.5, 0.5, 1.0, 1.0)). The Image Texture node is selected and active.
  - Render engine: Cycles CPU with low samples for a fast, reproducible
    bake.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "hi_low.blend")
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


def _noise3(x, y, z):
    """Smooth deterministic pseudo-noise in [-1, 1] based on sines."""
    return (
        math.sin(4.0 * x + 1.3) * math.sin(4.0 * y + 2.1) * math.sin(4.0 * z + 0.7)
        + 0.5 * math.sin(8.0 * x + 0.3) * math.sin(8.0 * y - 1.1)
        + 0.3 * math.sin(6.0 * z + 0.9) * math.sin(6.0 * x - 0.4)
    )


def make_highpoly():
    """Subdivided cube (extent ~ 0.9) with noise-driven Z displacement so
    there's clear surface detail for the normal bake to capture."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.8)  # half-extent 0.9
    # Subdivide 3 times.
    for _ in range(3):
        bmesh.ops.subdivide_edges(
            bm,
            edges=list(bm.edges),
            cuts=1,
            use_grid_fill=True,
        )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    # Displace vertices along their normal using smooth noise.
    for v in bm.verts:
        p = v.co.copy()
        n = v.normal.copy()
        if n.length < 1e-6:
            continue
        n.normalize()
        d = 0.08 * _noise3(p.x, p.y, p.z)
        v.co = p + n * d

    me  = bpy.data.meshes.new("HighPolyMesh")
    obj = bpy.data.objects.new("HighPoly", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj


def make_lowpoly():
    """Low-poly cage cube slightly larger (2.1) than HighPoly extent so
    HighPoly fits inside for selected-to-active baking with a cage."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.1)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new("LowPolyMesh")
    obj = bpy.data.objects.new("LowPoly", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj


def unwrap_uvs(obj):
    """Smart UV project so every face has UVs in [0, 1]^2."""
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66),
                                 island_margin=0.02,
                                 area_weight=0.0,
                                 correct_aspect=True,
                                 scale_to_bounds=True)
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')


def make_bake_image():
    """1024x1024 image `BakeNormal` initialized to default normal color."""
    img = bpy.data.images.new(
        name="BakeNormal", width=1024, height=1024,
        alpha=True, float_buffer=False,
    )
    img.generated_color = (0.5, 0.5, 1.0, 1.0)
    img.generated_type = 'BLANK'
    # Force the pixel buffer to exist.
    blank = [0.5, 0.5, 1.0, 1.0] * (1024 * 1024)
    img.pixels = blank
    # Normal maps are baked in linear space — keep as non-color so the
    # stored normals are not gamma-warped.
    img.colorspace_settings.name = 'Non-Color'
    return img


def build_material(bake_img):
    mat = bpy.data.materials.new(name="LowPolyMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_tex  = nt.nodes.new("ShaderNodeTexImage")
    n_out.location  = ( 400,   0)
    n_bsdf.location = ( 100,   0)
    n_tex.location  = (-300,   0)

    n_tex.image = bake_img
    nt.links.new(n_tex.outputs["Color"], n_bsdf.inputs["Base Color"])
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])

    # Bake targets the ACTIVE node on the material's node tree, and that
    # node must be a selected Image Texture node.
    for n in nt.nodes:
        n.select = False
    n_tex.select = True
    nt.nodes.active = n_tex
    return mat


def set_render_settings(scene):
    """Cycles CPU, deterministic, low-thread so the bake is reproducible."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.cycles.seed = 0
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.cycles.bake_type = 'NORMAL'


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

highpoly = make_highpoly()
lowpoly  = make_lowpoly()
unwrap_uvs(lowpoly)

bake_img = make_bake_image()
mat      = build_material(bake_img)
lowpoly.data.materials.append(mat)

# LowPoly starts active+selected so the init scene is "ready to bake".
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = lowpoly
lowpoly.select_set(True)

set_render_settings(bpy.context.scene)

# --- Audit ----------------------------------------------------------------
print("-" * 60)
print(f"  HighPoly verts/faces: {len(highpoly.data.vertices)}/"
      f"{len(highpoly.data.polygons)}")
print(f"  LowPoly  verts/faces: {len(lowpoly.data.vertices)}/"
      f"{len(lowpoly.data.polygons)}")
print(f"  LowPoly UV layers   : {[l.name for l in lowpoly.data.uv_layers]}")
print(f"  Material            : {lowpoly.data.materials[0].name}")
print(f"  BakeNormal image    : size={tuple(bake_img.size)} "
      f"colorspace={bake_img.colorspace_settings.name}")
active = mat.node_tree.nodes.active
print(f"  Material active node: {active.name if active else 'None'} "
      f"(type={getattr(active, 'type', None)})")
print(f"  Engine/samples      : {bpy.context.scene.render.engine}/"
      f"{bpy.context.scene.cycles.samples}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
