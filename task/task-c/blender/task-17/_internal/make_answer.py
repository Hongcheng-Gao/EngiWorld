"""Build `ground_truth/answer.blend` + `ground_truth/render.png` for DH02.

Opens `init_file/sphere.blend`, replaces the sphere's material's default
shader graph with a full PBR wiring:

    albedo_tex (sRGB)           --> Principled.Base Color
    normal_tex (Non-Color)      --> NormalMap.Color --> Principled.Normal
    roughness_tex (Non-Color)   --> Principled.Roughness
    metallic_tex (Non-Color)    --> Principled.Metallic

Renders to `ground_truth/render.png` (512x512 Eevee) and saves the blend.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INIT_BLEND = os.path.join(TASK_DIR, "init_file", "sphere.blend")
INIT_TEXDIR = os.path.join(TASK_DIR, "init_file", "textures")

OUT_DIR    = os.path.join(TASK_DIR, "ground_truth")
OUT_BLEND  = os.path.join(OUT_DIR, "answer.blend")
OUT_PNG    = os.path.join(OUT_DIR, "render.png")

os.makedirs(OUT_DIR, exist_ok=True)

CHANNELS = [
    # texture name, colorspace, principled input name (or "Normal" via map)
    ("albedo",    "sRGB",      "Base Color",  False),
    ("normal",    "Non-Color", "Normal",      True),   # via Normal Map node
    ("roughness", "Non-Color", "Roughness",   False),
    ("metallic",  "Non-Color", "Metallic",    False),
]


def find_principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            return n
    raise RuntimeError("No Principled BSDF node in material tree")


def rebuild_pbr_graph(mat):
    """Add 4 image nodes + a Normal Map node + wire to Principled."""
    nt = mat.node_tree
    bsdf = find_principled(nt)

    # Remove any pre-existing TexImage/NormalMap nodes so re-runs are
    # idempotent (the init blend has none, but this makes the script
    # safe to re-run against a partially-wired blend).
    for n in list(nt.nodes):
        if n.type in {'TEX_IMAGE', 'NORMAL_MAP'}:
            nt.nodes.remove(n)

    # Layout helper.
    y = 600
    dy = -300

    created = {}
    for i, (name, cs, _inp, _via_nmap) in enumerate(CHANNELS):
        png_path = os.path.join(INIT_TEXDIR, f"{name}.png")
        assert os.path.isfile(png_path), f"missing {png_path}"
        img = bpy.data.images.load(png_path, check_existing=False)
        # Set colorspace BEFORE the node starts using the image so the
        # colorspace actually sticks in the shader evaluation.
        img.colorspace_settings.name = cs
        # Make the image name match the texture role so eval can
        # identify which node is which from the image filename.
        img.name = f"{name}.png"

        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.name = f"{name}_tex"
        tex.label = f"{name}_tex"
        tex.image = img
        tex.location = (-600, y + i * dy)
        created[name] = tex

    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-250, y + 1 * dy)

    # Wire everything up.
    links = nt.links
    links.new(created["albedo"].outputs["Color"],    bsdf.inputs["Base Color"])
    links.new(created["normal"].outputs["Color"],    nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"],                bsdf.inputs["Normal"])
    links.new(created["roughness"].outputs["Color"], bsdf.inputs["Roughness"])
    links.new(created["metallic"].outputs["Color"],  bsdf.inputs["Metallic"])

    return created, nmap


# --- Main ----------------------------------------------------------------

bpy.ops.wm.open_mainfile(filepath=INIT_BLEND)

sphere = bpy.data.objects["Sphere"]
assert sphere.data.materials and sphere.data.materials[0] is not None, \
    "Sphere has no material"
mat = sphere.data.materials[0]
assert mat.use_nodes, "Sphere material has no node tree"

tex_nodes, nmap = rebuild_pbr_graph(mat)

# Ensure render settings.
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
try:
    scene.eevee.taa_render_samples = 16
except AttributeError:
    pass
# Make sure the init file's Standard view transform is still in effect
# (overrides anything the init step may have missed).
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = OUT_PNG

# Render.
print("  rendering 512x512 Eevee ...")
bpy.ops.render.render(write_still=True)
print(f"  render written -> {OUT_PNG}")

# --- Audit ---------------------------------------------------------------
print("-" * 60)
nt = mat.node_tree
for n in nt.nodes:
    extra = ""
    if n.type == 'TEX_IMAGE' and n.image is not None:
        extra = (f" image={n.image.name} "
                 f"cs={n.image.colorspace_settings.name}")
    print(f"  node {n.bl_idname:<28} name={n.name:<18}{extra}")
print(f"  links:")
for l in nt.links:
    print(f"    {l.from_node.name}.{l.from_socket.name} -> "
          f"{l.to_node.name}.{l.to_socket.name}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
