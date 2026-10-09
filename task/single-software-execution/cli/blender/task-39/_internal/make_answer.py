"""Build `ground_truth/answer.blend` + outputs for KH01 -- full chain.

Opens `init_file/scene.blend`, then executes the full flagship chain:

  1. Retopology: build a subdivided icosphere, add a ShrinkWrap modifier
     targeting the Scan, apply it, and subdivide once in bmesh so the
     vertex count lands in [300, 1200] (the evaluator's band).
  2. UV unwrap: smart-project the retopo mesh so all UVs lie in [0, 1]^2.
  3. Normal bake: Cycles selected-to-active tangent-space bake from the
     high-poly Scan onto a 512x512 Non-Color image assigned to the retopo
     material's active Image Texture node.  Saves the baked image to
     `ground_truth/output/normal_bake.png`.
  4. 3-point lighting: Key (2,-3,3) 500W, Fill (-2,-3,1.5) 200W,
     Rim (0,3,2) 300W AREA lights aimed at the origin.
  5. Camera at (0,-4,1), aimed at origin, 512x512.
  6. Hero render (Cycles 64 samples, denoise ON, Standard view transform)
     with the Scan hidden so only the baked retopo is visible. Saves to
     `ground_truth/output/hero.png`.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Vector

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INIT_BLEND = os.path.join(TASK_DIR, "init_file", "scene.blend")
GT_DIR     = os.path.join(TASK_DIR, "ground_truth")
OUT_DIR    = os.path.join(GT_DIR, "output")
OUT_BLEND  = os.path.join(GT_DIR, "answer.blend")
OUT_NORMAL = os.path.join(OUT_DIR, "normal_bake.png")
OUT_HERO   = os.path.join(OUT_DIR, "hero.png")

os.makedirs(OUT_DIR, exist_ok=True)

# Target retopo vertex band from the task spec.
VERT_MIN   = 300
VERT_MAX   = 1200

# Shrink-wrap retopo: start from a subdivisions=3 icosphere (162 verts),
# apply the ShrinkWrap to the Scan surface, then subdivide once in bmesh
# (162 -> 642 verts).  642 lies comfortably inside [300, 1200].
ICO_SUBS   = 3

# Normal bake resolution.
BAKE_W     = 512
BAKE_H     = 512


# ------------------------------------------------------------------------
# Step 0: open init
# ------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=INIT_BLEND)
scene = bpy.context.scene

scan = bpy.data.objects.get("Scan")
if scan is None or scan.type != 'MESH':
    raise RuntimeError("init scene.blend has no Scan mesh object")


# ------------------------------------------------------------------------
# Step 1: Retopology via shrink-wrap
# ------------------------------------------------------------------------
# Compute the bounding-sphere radius of the Scan so our starting
# icosphere encloses it with a small margin.
scan_bbox = [scan.matrix_world @ Vector(corner) for corner in scan.bound_box]
scan_centre = sum(scan_bbox, Vector()) / 8.0
scan_radius = max((p - scan_centre).length for p in scan_bbox)
start_radius = scan_radius * 1.25

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.mesh.primitive_ico_sphere_add(
    subdivisions=ICO_SUBS,
    radius=start_radius,
    location=tuple(scan_centre),
)
retopo = bpy.context.active_object
retopo.name = "Retopo"
retopo.data.name = "RetopoMesh"

# Shade smooth for the final render.
for p in retopo.data.polygons:
    p.use_smooth = True

# ShrinkWrap onto the Scan surface.
mod = retopo.modifiers.new(name="ShrinkWrap", type='SHRINKWRAP')
mod.target = scan
mod.wrap_method = 'NEAREST_SURFACEPOINT'
mod.offset = 0.0

# Make retopo active + selected so modifier_apply has a context to use.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = retopo
retopo.select_set(True)
bpy.ops.object.modifier_apply(modifier="ShrinkWrap")

# Subdivide once more in bmesh so the vert count lands in the eval band.
# 162 starting verts -> 642 after one subdivide_edges (use_grid_fill on
# an all-triangular icosphere quads-up the faces, but vert count is what
# eval checks).
if len(retopo.data.vertices) < VERT_MIN:
    bm = bmesh.new()
    bm.from_mesh(retopo.data)
    bmesh.ops.subdivide_edges(
        bm,
        edges=list(bm.edges),
        cuts=1,
        use_grid_fill=True,
    )
    bm.to_mesh(retopo.data)
    bm.free()
    retopo.data.update()

# If we're still somehow out of band, loop-subdivide or decimate until
# we are in band.  This is defensive; with ICO_SUBS=3 + one subdivide
# we already land at 642.
while len(retopo.data.vertices) > VERT_MAX:
    # Collapse-decimate via modifier to bring the count down.
    d = retopo.modifiers.new(name="DecimateFix", type='DECIMATE')
    d.ratio = VERT_MAX / max(1.0, float(len(retopo.data.vertices)))
    d.decimate_type = 'COLLAPSE'
    bpy.context.view_layer.objects.active = retopo
    retopo.select_set(True)
    bpy.ops.object.modifier_apply(modifier="DecimateFix")

while len(retopo.data.vertices) < VERT_MIN:
    bm = bmesh.new()
    bm.from_mesh(retopo.data)
    bmesh.ops.subdivide_edges(
        bm,
        edges=list(bm.edges),
        cuts=1,
        use_grid_fill=True,
    )
    bm.to_mesh(retopo.data)
    bm.free()
    retopo.data.update()

print(f"  Retopo vert count: {len(retopo.data.vertices)} "
      f"(band [{VERT_MIN}, {VERT_MAX}])")


# ------------------------------------------------------------------------
# Step 2: UV unwrap
# ------------------------------------------------------------------------
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = retopo
retopo.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
try:
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(
        angle_limit=math.radians(66),
        island_margin=0.02,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=True,
    )
finally:
    bpy.ops.object.mode_set(mode='OBJECT')

uv_layer = retopo.data.uv_layers.active
uv_min = (min(uv.uv[0] for uv in uv_layer.data),
          min(uv.uv[1] for uv in uv_layer.data))
uv_max = (max(uv.uv[0] for uv in uv_layer.data),
          max(uv.uv[1] for uv in uv_layer.data))
print(f"  UV bbox: min=({uv_min[0]:.4f},{uv_min[1]:.4f}) "
      f"max=({uv_max[0]:.4f},{uv_max[1]:.4f})")


# ------------------------------------------------------------------------
# Step 3: Bake normal map (Cycles selected-to-active)
# ------------------------------------------------------------------------
# Make a 512x512 Non-Color image for the bake target.
bake_img = bpy.data.images.new(
    name="NormalBake", width=BAKE_W, height=BAKE_H,
    alpha=True, float_buffer=False,
)
bake_img.generated_color = (0.5, 0.5, 1.0, 1.0)
bake_img.generated_type = 'BLANK'
bake_img.pixels = [0.5, 0.5, 1.0, 1.0] * (BAKE_W * BAKE_H)
bake_img.colorspace_settings.name = 'Non-Color'

# Retopo material: Principled BSDF + Image Texture (NormalBake) +
# Normal Map node wired into Principled.Normal.
mat = bpy.data.materials.new(name="Mat_Retopo")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)

n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
n_tex  = nt.nodes.new("ShaderNodeTexImage")
n_nmap = nt.nodes.new("ShaderNodeNormalMap")
n_out.location  = ( 600,   0)
n_bsdf.location = ( 300,   0)
n_nmap.location = (   0, -200)
n_tex.location  = (-300, -200)

n_tex.image = bake_img
# Set a neutral base color / roughness so the render mean luma doesn't
# saturate.  The retopo is a simple gray sphere-ish shape with the
# baked normal map cranking micro-detail into the shading.
n_bsdf.inputs["Base Color"].default_value = (0.55, 0.55, 0.55, 1.0)
if "Roughness" in n_bsdf.inputs:
    n_bsdf.inputs["Roughness"].default_value = 0.45
if "Metallic" in n_bsdf.inputs:
    n_bsdf.inputs["Metallic"].default_value = 0.0

nt.links.new(n_tex.outputs["Color"],  n_nmap.inputs["Color"])
nt.links.new(n_nmap.outputs["Normal"], n_bsdf.inputs["Normal"])
nt.links.new(n_bsdf.outputs["BSDF"],   n_out.inputs["Surface"])

# Bake targets the ACTIVE Image Texture node — make n_tex active + sole
# selected node before invoking bake.
for n in nt.nodes:
    n.select = False
n_tex.select = True
nt.nodes.active = n_tex

retopo.data.materials.append(mat)

# --- Cycles bake settings
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.cycles.seed = 0
scene.cycles.bake_type = 'NORMAL'

bake = scene.render.bake
bake.use_selected_to_active = True
bake.use_cage = False
bake.cage_extrusion = 0.05
bake.normal_space = 'TANGENT'
bake.normal_r = 'POS_X'
bake.normal_g = 'POS_Y'
bake.normal_b = 'POS_Z'
try:
    bake.use_clear = True
    bake.margin = 4
except AttributeError:
    pass

# --- Selection for bake: Scan SELECTED, Retopo ACTIVE
bpy.ops.object.select_all(action='DESELECT')
scan.select_set(True)
retopo.select_set(True)
bpy.context.view_layer.objects.active = retopo

print("  running NORMAL bake (selected-to-active) ...")
bpy.ops.object.bake(
    type='NORMAL',
    use_selected_to_active=True,
    cage_extrusion=0.05,
    normal_space='TANGENT',
)

# Save baked image.
bake_img.filepath_raw = OUT_NORMAL
bake_img.file_format = 'PNG'
bake_img.save()
print(f"  normal_bake png  : {OUT_NORMAL}")

# Quick bake stats for the audit log.
px = list(bake_img.pixels)
n_pixels = len(px) // 4
sum_r = sum(px[i * 4 + 0] for i in range(n_pixels))
sum_g = sum(px[i * 4 + 1] for i in range(n_pixels))
sum_b = sum(px[i * 4 + 2] for i in range(n_pixels))
mean_r = sum_r / n_pixels
mean_g = sum_g / n_pixels
mean_b = sum_b / n_pixels
var_r = sum((px[i*4+0] - mean_r) ** 2 for i in range(n_pixels)) / n_pixels
var_g = sum((px[i*4+1] - mean_g) ** 2 for i in range(n_pixels)) / n_pixels
print(f"  bake mean R/G/B  : ({mean_r:.4f}, {mean_g:.4f}, {mean_b:.4f})")
print(f"  bake std  R/G    : ({var_r**0.5:.4f}, {var_g**0.5:.4f})")


# ------------------------------------------------------------------------
# Step 4: 3-point lighting
# ------------------------------------------------------------------------
def aim_at(obj, target=Vector((0.0, 0.0, 0.0))):
    direction = target - Vector(obj.location)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('-Z', 'Y')


def add_area_light(name, location, energy, size=1.5,
                   color=(1.0, 1.0, 1.0)):
    ldata = bpy.data.lights.new(name=name, type='AREA')
    ldata.shape = 'SQUARE'
    ldata.size = size
    ldata.energy = energy
    ldata.color = color
    obj = bpy.data.objects.new(name, ldata)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim_at(obj)
    return obj


# Wipe any pre-existing lights so only the 3-point setup drives the render.
for o in [o for o in bpy.data.objects if o.type == 'LIGHT']:
    ld = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    try:
        bpy.data.lights.remove(ld)
    except Exception:
        pass

key  = add_area_light("Key",  (2.0, -3.0, 3.0),  500.0, size=1.5,
                      color=(1.0, 1.0, 1.0))
fill = add_area_light("Fill", (-2.0, -3.0, 1.5), 200.0, size=2.0,
                      color=(1.0, 0.95, 0.88))
rim  = add_area_light("Rim",  (0.0,  3.0, 2.0),  300.0, size=1.0,
                      color=(0.9, 0.95, 1.0))


# ------------------------------------------------------------------------
# Step 5: Camera (512x512, at (0,-4,1), aimed at origin)
# ------------------------------------------------------------------------
# Remove any pre-existing cameras so the scene has exactly one camera
# pointed at the retopo.
for o in [o for o in bpy.data.objects if o.type == 'CAMERA']:
    cd = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    try:
        bpy.data.cameras.remove(cd)
    except Exception:
        pass

cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location = (0.0, -4.0, 1.0)
aim_at(cam, Vector((0.0, 0.0, 0.0)))
scene.camera = cam


# ------------------------------------------------------------------------
# Step 6: Render hero.png (Scan hidden, only Retopo visible)
# ------------------------------------------------------------------------
# Hide scan from the render so only the retopo (with baked normal map)
# contributes to the beauty shot.
scan.hide_render = True
scan.hide_viewport = True

# Simple gray world so the render isn't pitch-black off-subject.
if scene.world is None:
    scene.world = bpy.data.worlds.new("World")
w = scene.world
w.use_nodes = True
wnt = w.node_tree
for n in list(wnt.nodes):
    wnt.nodes.remove(n)
w_out = wnt.nodes.new("ShaderNodeOutputWorld")
w_bg  = wnt.nodes.new("ShaderNodeBackground")
w_out.location = (300, 0); w_bg.location = (0, 0)
w_bg.inputs["Color"].default_value    = (0.12, 0.12, 0.14, 1.0)
w_bg.inputs["Strength"].default_value = 0.4
wnt.links.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

scene.render.engine        = "CYCLES"
scene.cycles.device        = "CPU"
scene.cycles.samples       = 64
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = False
scene.render.resolution_x  = 512
scene.render.resolution_y  = 512
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode  = 'RGBA'
scene.render.image_settings.color_depth = '8'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look     = 'None'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma    = 1.0
scene.frame_start = scene.frame_end = scene.frame_current = 1

scene.render.filepath = OUT_HERO

# Save the blend before rendering so the on-disk state fully describes
# the scene used for the render.
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")

print("  rendering hero 512x512 Cycles (64 samples) ...")
bpy.ops.render.render(write_still=True)
print(f"  hero png          : {OUT_HERO}")


# ------------------------------------------------------------------------
# Audit summary
# ------------------------------------------------------------------------
print("-" * 60)
print(f"  Retopo verts/faces : {len(retopo.data.vertices)}/"
      f"{len(retopo.data.polygons)}")
print(f"  Retopo UV layer    : {retopo.data.uv_layers.active.name}")
print(f"  UV bbox            : "
      f"({uv_min[0]:.3f},{uv_min[1]:.3f}) .. "
      f"({uv_max[0]:.3f},{uv_max[1]:.3f})")
print(f"  normal_bake mean B : {mean_b:.4f}")
print(f"  normal_bake mean R : {mean_r:.4f}  std R: {var_r**0.5:.4f}")
print(f"  normal_bake mean G : {mean_g:.4f}  std G: {var_g**0.5:.4f}")
print(f"  Lights             : "
      f"{[o.name for o in bpy.data.objects if o.type=='LIGHT']}")
print(f"  Camera             : {cam.name} loc={tuple(cam.location)}")
print(f"  Scan hidden render : {scan.hide_render}")
print(f"  hero.png exists    : {os.path.isfile(OUT_HERO)}")
print(f"  normal_bake exists : {os.path.isfile(OUT_NORMAL)}")
print("-" * 60)


# ------------------------------------------------------------------------
# Inline self-audit (so the ground-truth run is self-verifying).
# Replicates the evaluator's pass conditions without importing it.
# ------------------------------------------------------------------------
def _inline_audit():
    import math as _math

    VERT_BAND         = (300, 1200)
    UV_MIN            = -1e-4
    UV_MAX            = 1.0 + 1e-4
    NORMAL_MEAN_B_MIN = 0.80
    NORMAL_RG_BAND    = (0.40, 0.60)
    NORMAL_RG_STD_MIN = 0.02
    HERO_LUMA_BAND    = (0.10, 0.70)
    HERO_SIZE         = (512, 512)
    BAKE_SIZE         = (512, 512)

    def _chan_stats(px, n, c):
        if n == 0:
            return 0.0, 0.0
        s = sq = 0.0
        for i in range(n):
            v = px[i * 4 + c]; s += v; sq += v * v
        m = s / n
        return m, _math.sqrt(max(0.0, sq / n - m * m))

    def _luma(px, n):
        if n == 0:
            return 0.0
        s = 0.0
        for i in range(n):
            r = px[i * 4 + 0]
            g = px[i * 4 + 1]
            b = px[i * 4 + 2]
            s += 0.2126 * r + 0.7152 * g + 0.0722 * b
        return s / n

    results = []

    def rec(name, passed, msg):
        results.append((name, passed, msg))

    bpy.ops.wm.open_mainfile(filepath=OUT_BLEND)
    rec("file_exists", os.path.isfile(OUT_BLEND), f"blend = {OUT_BLEND}")
    rec("file_opens", True, "opened .blend")

    rt = bpy.data.objects.get("Retopo")
    rok = rt is not None and rt.type == 'MESH'
    rec("retopo_mesh_exists", rok,
        "Retopo present" if rok else "no mesh 'Retopo'")

    if rok:
        vc = len(rt.data.vertices)
        vlo, vhi = VERT_BAND
        rec("retopo_vertex_count_in_band", vlo <= vc <= vhi,
            f"vertex count = {vc} (band [{vlo}, {vhi}])")

        has_uv = (len(rt.data.uv_layers) >= 1 and
                  rt.data.uv_layers.active is not None)
        rec("retopo_has_uv_layer", has_uv,
            f"uv_layers = {[u.name for u in rt.data.uv_layers]}")

        if has_uv:
            ul = rt.data.uv_layers.active
            if len(ul.data):
                mu = min(l.uv[0] for l in ul.data)
                xu = max(l.uv[0] for l in ul.data)
                mv = min(l.uv[1] for l in ul.data)
                xv = max(l.uv[1] for l in ul.data)
                ok = (mu >= UV_MIN and xu <= UV_MAX and
                      mv >= UV_MIN and xv <= UV_MAX)
                rec("uv_bbox_in_unit_square", ok,
                    f"UV bbox=[({mu:.4f},{mv:.4f}), ({xu:.4f},{xv:.4f})]")
            else:
                rec("uv_bbox_in_unit_square", False, "UV layer empty")
        else:
            rec("uv_bbox_in_unit_square", False, "no UV layer")

    rec("normal_bake_png_exists", os.path.isfile(OUT_NORMAL),
        f"png = {OUT_NORMAL}")
    try:
        img = bpy.data.images.load(OUT_NORMAL, check_existing=False)
        img.colorspace_settings.name = 'Non-Color'
        W, H = tuple(img.size)
        if (W, H) == BAKE_SIZE:
            np_ = W * H
            pix = list(img.pixels)
            mr, sr = _chan_stats(pix, np_, 0)
            mg, sg = _chan_stats(pix, np_, 1)
            mb, _  = _chan_stats(pix, np_, 2)
            rlo, rhi = NORMAL_RG_BAND
            ok = (mb >= NORMAL_MEAN_B_MIN
                  and rlo <= mr <= rhi
                  and rlo <= mg <= rhi
                  and sr >= NORMAL_RG_STD_MIN
                  and sg >= NORMAL_RG_STD_MIN)
            rec("normal_bake_statistics", ok,
                f"meanRGB=({mr:.4f},{mg:.4f},{mb:.4f}) "
                f"stdRG=({sr:.4f},{sg:.4f})")
        else:
            rec("normal_bake_statistics", False,
                f"size {(W, H)}, expected {BAKE_SIZE}")
    except Exception as ex:
        rec("normal_bake_statistics", False, f"load failed: {ex}")

    rec("hero_png_exists", os.path.isfile(OUT_HERO),
        f"png = {OUT_HERO}")
    try:
        img = bpy.data.images.load(OUT_HERO, check_existing=False)
        W, H = tuple(img.size)
        if (W, H) == HERO_SIZE:
            np_ = W * H
            pix = list(img.pixels)
            ml = _luma(pix, np_)
            lo, hi = HERO_LUMA_BAND
            rec("hero_render_mean_luma", lo <= ml <= hi,
                f"mean luma = {ml:.4f} (band [{lo}, {hi}])")
        else:
            rec("hero_render_mean_luma", False,
                f"size {(W, H)}, expected {HERO_SIZE}")
    except Exception as ex:
        rec("hero_render_mean_luma", False, f"load failed: {ex}")

    print("=" * 78)
    print("INLINE AUDIT")
    for (n_, p, m) in results:
        mark = "PASS" if p else "FAIL"
        print(f"  [{mark}]  {n_:<34} {m}")
    all_pass = bool(results) and all(p for (_, p, _m) in results)
    print("=" * 78)
    print(f"  Audit result: {'PASS' if all_pass else 'FAIL'} "
          f"(score = {1.0 if all_pass else 0.0:.1f})")
    print("=" * 78)


_inline_audit()
