"""Build `init_file/scene.blend` for task LH06 — Shader Colorspace Corruption.

Scene:
  - A UV-mapped 2x2 BU plane `Plate` at the origin with a Principled BSDF
    material `PlateMat`. The material has two Image Texture nodes:
      - `basecolor.png` feeding Base Color.
      - `normalmap.png` -> Normal Map -> Normal input.
  - Both images are generated in-process (procedurally), packed into the
    .blend via `bpy.ops.image.pack()` so the file is self-contained.
  - Colorspaces are deliberately WRONG in this init file:
      - `basecolor.png`   : colorspace_settings.name = 'Non-Color'   (wrong)
      - `normalmap.png`   : colorspace_settings.name = 'sRGB'        (wrong)
    The correct values would be 'sRGB' for basecolor and 'Non-Color' for
    the normal map.
  - One area light and one camera pointed straight down at the plate so
    Cycles CPU renders the scene deterministically.
  - Render engine: CYCLES, CPU, 1 thread, samples=32, 128x128, seed=0,
    denoiser off.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os
import tempfile

import bmesh
import bpy


HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

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


def make_plate():
    """Create a 2x2 BU plane called `Plate`, UV-unwrapped to [0,1]x[0,1]."""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new("PlateMesh")
    obj = bpy.data.objects.new("Plate", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (0.0, 0.0, 0.0)

    # Guarantee a UV layer in [0,1]x[0,1]. Blender's create_grid + to_mesh
    # does not necessarily produce a uv layer, so build one explicitly.
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    for loop in me.loops:
        v_co = me.vertices[loop.vertex_index].co
        u = (v_co.x + 1.0) * 0.5
        v = (v_co.y + 1.0) * 0.5
        uv[loop.index].uv = (u, v)

    return obj


def write_basecolor_png(path, w=128, h=128):
    """Red->white horizontal gradient written as an 8-bit PNG.

    The PNG bytes themselves are sRGB-intent (they look like a pretty
    gradient on a normal viewer). The colorspace mis-tagging lives on the
    image DATABLOCK, not on the encoded bytes.
    """
    img = bpy.data.images.new(name="_tmp_basecolor",
                              width=w, height=h,
                              alpha=True, float_buffer=False)
    # Blender image pixels: bottom-up row-major RGBA floats in [0, 1].
    pix = [0.0] * (w * h * 4)
    for y in range(h):
        for x in range(w):
            t = x / (w - 1)
            r = 1.0
            g = t
            b = t
            i = (y * w + x) * 4
            pix[i + 0] = r
            pix[i + 1] = g
            pix[i + 2] = b
            pix[i + 3] = 1.0
    img.pixels = pix
    img.file_format = 'PNG'
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)


def write_normalmap_png(path, w=128, h=128):
    """Mostly-neutral tangent-space normal map (~128,128,255) with a subtle
    dome bump so the colorspace mis-tag has an observable (but bounded)
    impact on the rendered result."""
    img = bpy.data.images.new(name="_tmp_normalmap",
                              width=w, height=h,
                              alpha=True, float_buffer=False)
    pix = [0.0] * (w * h * 4)
    for y in range(h):
        for x in range(w):
            u = (x / (w - 1)) * 2.0 - 1.0
            v = (y / (h - 1)) * 2.0 - 1.0
            bump = math.exp(-(u * u + v * v) * 3.0)
            nx = -u * 0.4 * bump
            ny = -v * 0.4 * bump
            nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))
            # Encode tangent-space normal: n -> (n*0.5+0.5).
            r = nx * 0.5 + 0.5
            g = ny * 0.5 + 0.5
            b = nz * 0.5 + 0.5
            i = (y * w + x) * 4
            pix[i + 0] = r
            pix[i + 1] = g
            pix[i + 2] = b
            pix[i + 3] = 1.0
    img.pixels = pix
    img.file_format = 'PNG'
    img.filepath_raw = path
    img.save()
    bpy.data.images.remove(img)


def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    # Look straight down at the plate from above so the centre ROI samples
    # the plate's centre pixels directly.
    cam_obj.location = (0.0, 0.0, 3.0)
    cam_obj.rotation_euler = (0.0, 0.0, 0.0)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 2.0
    bpy.context.scene.camera = cam_obj
    return cam_obj


def make_area_light():
    light_data = bpy.data.lights.new("Light", type="AREA")
    light_data.energy = 500.0
    light_data.size = 3.0
    light_obj  = bpy.data.objects.new("Light", light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = (0.0, 0.0, 3.0)
    light_obj.rotation_euler = (0.0, 0.0, 0.0)
    return light_obj


def build_material(basecolor_img, normal_img):
    mat = bpy.data.materials.new(name="PlateMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out   = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf  = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_bcTex = nt.nodes.new("ShaderNodeTexImage")
    n_nmTex = nt.nodes.new("ShaderNodeTexImage")
    n_nmap  = nt.nodes.new("ShaderNodeNormalMap")

    n_out.location   = ( 600,   0)
    n_bsdf.location  = ( 300,   0)
    n_bcTex.location = (-400, 200)
    n_nmTex.location = (-400, -200)
    n_nmap.location  = (   0, -200)

    n_bcTex.image = basecolor_img
    n_nmTex.image = normal_img

    nt.links.new(n_bcTex.outputs["Color"], n_bsdf.inputs["Base Color"])
    nt.links.new(n_nmTex.outputs["Color"], n_nmap.inputs["Color"])
    nt.links.new(n_nmap.outputs["Normal"], n_bsdf.inputs["Normal"])
    nt.links.new(n_bsdf.outputs["BSDF"],   n_out.inputs["Surface"])

    # Keep shading predictable so the rendered output is driven by the
    # albedo texture + gentle normal bump.
    if "Roughness" in n_bsdf.inputs:
        n_bsdf.inputs["Roughness"].default_value = 0.5
    if "Metallic" in n_bsdf.inputs:
        n_bsdf.inputs["Metallic"].default_value = 0.0
    for spec_name in ("Specular", "Specular IOR Level"):
        if spec_name in n_bsdf.inputs:
            n_bsdf.inputs[spec_name].default_value = 0.0

    return mat


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

# Write the two PNGs to a temp directory so we can load and pack them.
tmp_dir = tempfile.mkdtemp(prefix="lh06_init_")
bc_path = os.path.join(tmp_dir, "basecolor.png")
nm_path = os.path.join(tmp_dir, "normalmap.png")
write_basecolor_png(bc_path)
write_normalmap_png(nm_path)

# Load the images from disk as Image datablocks.
bc_img = bpy.data.images.load(bc_path)
bc_img.name = "basecolor.png"
nm_img = bpy.data.images.load(nm_path)
nm_img.name = "normalmap.png"

# Pack the image data into the .blend so the file is self-contained even if
# the /tmp dir is cleaned up.
bc_img.pack()
nm_img.pack()

# Intentionally WRONG colorspace assignments (the bug the testee must
# diagnose). Correct values would be:
#   basecolor.png  -> 'sRGB'
#   normalmap.png  -> 'Non-Color'
bc_img.colorspace_settings.name = 'Non-Color'   # WRONG
nm_img.colorspace_settings.name = 'sRGB'        # WRONG

# Build plate + material.
plate = make_plate()
mat   = build_material(bc_img, nm_img)
plate.data.materials.append(mat)

make_camera()
make_area_light()

# Render settings: deterministic Cycles CPU.
scene = bpy.context.scene
scene.render.engine       = "CYCLES"
scene.cycles.device       = "CPU"
scene.cycles.samples      = 32
scene.cycles.use_denoising = False
scene.cycles.seed         = 0
scene.render.resolution_x = 128
scene.render.resolution_y = 128
scene.render.resolution_percentage = 100
scene.render.threads_mode = "FIXED"
scene.render.threads      = 1
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode  = 'RGBA'
scene.render.image_settings.color_depth = '8'

# Sanity dump.
print("-" * 60)
print(f"  plate         = {plate.name} ({plate.type})")
print(f"  material      = {plate.data.materials[0].name}")
print(f"  bc.colorspace = {bc_img.colorspace_settings.name} "
      f"(WRONG — should be sRGB)")
print(f"  nm.colorspace = {nm_img.colorspace_settings.name} "
      f"(WRONG — should be Non-Color)")
print(f"  bc packed     = {bc_img.packed_file is not None}")
print(f"  nm packed     = {nm_img.packed_file is not None}")
print(f"  render        = {scene.render.engine} device={scene.cycles.device} "
      f"samples={scene.cycles.samples} "
      f"res={scene.render.resolution_x}x{scene.render.resolution_y} "
      f"seed={scene.cycles.seed}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
