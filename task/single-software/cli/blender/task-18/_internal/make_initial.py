"""Build `init_file/scene.blend` for task DH03 - UV Pack + Bake AO.

Scene:
  - One mesh object `BumpyMesh`: a subdivided cube with noise-driven
    surface displacement. The displacement produces distinct bumps and
    pockets so that AO baking yields visible contrast between exposed
    peaks and sheltered valleys.
  - A single pre-existing UV layer `UVMap` where every face is collapsed
    to the unit square via `bpy.ops.uv.reset()` (heavy overlap, clearly
    unusable -- the "bad" UVs the testee must replace).
  - Seams pre-marked on a deliberate pattern: the 4 vertical edges of
    the cube, giving a clean unwrap into 3 islands (top + bottom + a
    single side strip that wraps around all four side faces).
  - A 512x512 blank image `BakeAO` filled with pure black, assigned to
    an Image Texture node on material `BumpyMat`. The Image Texture node
    is selected and is the active node of the material so Cycles baking
    targets it.
  - Cycles CPU, deterministic, low thread count.

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
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

EPS = 1e-4


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


def _bump_noise(x, y, z):
    """Smooth deterministic pseudo-noise in roughly [-1, 1].

    Mixes a handful of sinusoids along the three axes so the output
    surface has both gentle ridges and a few pronounced lumps.
    """
    return (
        math.sin(3.2 * x + 0.7) * math.sin(3.1 * y + 1.9)
        + 0.7 * math.sin(5.1 * y + 0.3) * math.sin(4.7 * z - 0.5)
        + 0.6 * math.sin(4.3 * z + 2.1) * math.sin(4.9 * x - 1.3)
        + 0.35 * math.sin(8.0 * x - 0.4) * math.sin(8.0 * y + 0.8)
            * math.sin(8.0 * z + 1.1)
    )


def make_bumpy_mesh():
    """Subdivided 2x2x2 cube (half-extent 1.0) with noise-based surface
    displacement along each vertex's outward normal. Also marks seams on
    the pristine geometry BEFORE displacement (doing it post-displacement
    would miss edges because the corners no longer sit at exactly
    (+/-1, +/-1, +/-1)).

    Seam pattern (gives exactly 2 UV islands after unwrap):
      - Top ring: the 4*8 = 32 edges forming the boundary of the +Z face,
        separating it from the 4 side faces.
    Total seams: 32. With only the top ring seamed, a fresh unwrap
    produces:
      1. The +Z face alone (flattened into a square).
      2. The bottom + 4 sides joined together (topologically a disk with
         a hole; angle-based unwrap will add internal cuts to flatten
         it, but no additional seam-driven island boundaries).

    Face count: 6 * (8 * 8) = 384 quads.
    Vertex count: ~386.
    """
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)  # half-extent 1.0
    for _ in range(3):
        bmesh.ops.subdivide_edges(
            bm,
            edges=list(bm.edges),
            cuts=1,
            use_grid_fill=True,
        )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    def _on_top(co):    return abs(co.z - 1.0) < EPS

    # --- Mark seams while geometry is still pristine ---------------------
    # Mark the 32 top-ring edges (the 4 sides * 8 subdivided edges each)
    # of the +Z face. Both endpoints must lie on z=+1 AND one of (x, y)
    # must be +/-1 on both endpoints (i.e. the edge runs along one of
    # the 4 sides of the top square).
    n_seams = 0
    for e in bm.edges:
        a = e.verts[0].co
        b = e.verts[1].co
        if not (_on_top(a) and _on_top(b)):
            continue
        both_xp1 = abs(a.x - 1.0) < EPS and abs(b.x - 1.0) < EPS
        both_xm1 = abs(a.x + 1.0) < EPS and abs(b.x + 1.0) < EPS
        both_yp1 = abs(a.y - 1.0) < EPS and abs(b.y - 1.0) < EPS
        both_ym1 = abs(a.y + 1.0) < EPS and abs(b.y + 1.0) < EPS
        if both_xp1 or both_xm1 or both_yp1 or both_ym1:
            e.seam = True
            n_seams += 1

    # --- Displace each vertex along its normal using smooth noise ---------
    for v in bm.verts:
        p = v.co.copy()
        n = v.normal.copy()
        if n.length < 1e-6:
            continue
        n.normalize()
        d = 0.20 * _bump_noise(p.x, p.y, p.z)
        v.co = p + n * d

    me = bpy.data.meshes.new("BumpyMeshData")
    obj = bpy.data.objects.new("BumpyMesh", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj, n_seams


def make_bad_uv_layer(obj):
    """Create a single UV layer with every face collapsed to the unit
    square via `bpy.ops.uv.reset()`. This produces heavy overlap (and
    trivially satisfies the "bad UV" premise).
    """
    # Ensure a UV layer exists; create one if needed.
    me = obj.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")

    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    try:
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='SELECT')
        # Reset maps every face's UVs to the unit square (heavy overlap).
        bpy.ops.uv.reset()
    finally:
        bpy.ops.object.mode_set(mode='OBJECT')


def make_bake_image():
    """Create a blank 512x512 image `BakeAO` filled with pure black."""
    img = bpy.data.images.new(
        name="BakeAO", width=512, height=512,
        alpha=False, float_buffer=False,
    )
    img.generated_color = (0.0, 0.0, 0.0, 1.0)
    img.generated_type = 'BLANK'
    # Force the pixel buffer to exist.
    blank = [0.0, 0.0, 0.0, 1.0] * (512 * 512)
    img.pixels = blank
    # Keep as non-color so the baked AO is not gamma-warped.
    img.colorspace_settings.name = 'Non-Color'
    return img


def build_material(bake_img):
    mat = bpy.data.materials.new(name="BumpyMat")
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
    """Cycles CPU, deterministic, low thread count."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.cycles.seed = 0
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 1
    scene.cycles.bake_type = 'AO'


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

bumpy, n_seams = make_bumpy_mesh()

# Select + activate so operators can run in the script's headless context.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = bumpy
bumpy.select_set(True)

# Create a single overlapping UV layer ("bad" initial UVs).
make_bad_uv_layer(bumpy)

bake_img = make_bake_image()
mat      = build_material(bake_img)
bumpy.data.materials.append(mat)

# BumpyMesh starts active+selected so the init scene is "ready to
# unwrap + bake".
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = bumpy
bumpy.select_set(True)

set_render_settings(bpy.context.scene)

# --- Audit ----------------------------------------------------------------
me = bumpy.data
uvs = me.uv_layers.active.data if me.uv_layers.active else []
u_vals = [uv.uv.x for uv in uvs]
v_vals = [uv.uv.y for uv in uvs]
if u_vals:
    u_rng = (min(u_vals), max(u_vals))
    v_rng = (min(v_vals), max(v_vals))
else:
    u_rng = v_rng = (0.0, 0.0)

print("-" * 60)
print(f"  BumpyMesh verts/faces: {len(me.vertices)}/{len(me.polygons)}")
print(f"  UV layers            : {[l.name for l in me.uv_layers]}")
print(f"  U range (bad UVs)    : [{u_rng[0]:.3f}, {u_rng[1]:.3f}]")
print(f"  V range (bad UVs)    : [{v_rng[0]:.3f}, {v_rng[1]:.3f}]")
print(f"  Seams marked         : {n_seams}")
print(f"  Material             : {me.materials[0].name}")
print(f"  BakeAO image         : size={tuple(bake_img.size)} "
      f"colorspace={bake_img.colorspace_settings.name}")
active = mat.node_tree.nodes.active
print(f"  Material active node : {active.name if active else 'None'} "
      f"(type={getattr(active, 'type', None)})")
print(f"  Engine/samples       : {bpy.context.scene.render.engine}/"
      f"{bpy.context.scene.cycles.samples}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
