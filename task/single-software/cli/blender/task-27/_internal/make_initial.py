"""Build `init_file/scene.blend` for task GH03 — Triplanar Projection.

Scene:
  - A torus mesh object `TorusTri` at origin (major=1.0, minor=0.35,
    major_segments=48, minor_segments=24 -> ~1152 verts) with NO UV layer.
  - A flat grey Principled BSDF material `TriplanarMat` (no triplanar shader;
    the testee must build it).
  - A Camera at (0, -4, 2) pointing at origin.
  - An Area light at (3, -2, 4) pointing at origin.
  - Render engine: CYCLES, CPU, 64 samples, denoising ON, 512x512.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bmesh
import bpy
from mathutils import Euler, Vector


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


def make_torus():
    """Create a torus named `TorusTri` with NO UV layers.

    Build the torus by hand with bmesh so we avoid the operator's
    auto-generated UV layer entirely.  Vert count = 48 * 24 = 1152.
    """
    major_radius   = 1.0
    minor_radius   = 0.35
    major_segments = 48
    minor_segments = 24

    bm = bmesh.new()

    # --- Generate the vertex ring grid ----------------------------------
    verts = []
    for i in range(major_segments):
        theta = (i / major_segments) * 2.0 * math.pi
        cx = math.cos(theta) * major_radius
        cy = math.sin(theta) * major_radius
        row = []
        for j in range(minor_segments):
            phi = (j / minor_segments) * 2.0 * math.pi
            # Offset along the tube cross-section.  The minor ring lives
            # in the plane containing (radial, +Z).
            radial = math.cos(phi) * minor_radius
            z      = math.sin(phi) * minor_radius
            x = (major_radius + radial) * math.cos(theta) / major_radius * 1.0
            y = (major_radius + radial) * math.sin(theta) / major_radius * 1.0
            # Simpler: recompute directly.
            x = math.cos(theta) * (major_radius + radial)
            y = math.sin(theta) * (major_radius + radial)
            row.append(bm.verts.new((x, y, z)))
        verts.append(row)

    bm.verts.ensure_lookup_table()

    # --- Connect faces (quads) around both ring directions --------------
    for i in range(major_segments):
        i2 = (i + 1) % major_segments
        for j in range(minor_segments):
            j2 = (j + 1) % minor_segments
            v00 = verts[i ][j ]
            v10 = verts[i2][j ]
            v11 = verts[i2][j2]
            v01 = verts[i ][j2]
            try:
                bm.faces.new((v00, v10, v11, v01))
            except ValueError:
                # Duplicate face (shouldn't happen, but guard anyway).
                pass

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    mesh = bpy.data.meshes.new("TorusTriMesh")
    obj  = bpy.data.objects.new("TorusTri", mesh)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(mesh)
    bm.free()
    obj.location = (0.0, 0.0, 0.0)

    # Explicitly remove any UV layers (manual bmesh build should not have
    # created any, but be defensive).
    for uv in list(mesh.uv_layers):
        mesh.uv_layers.remove(uv)

    # Shade smooth for nicer rendering.
    for p in mesh.polygons:
        p.use_smooth = True

    return obj


def build_flat_material():
    """Plain flat grey Principled BSDF material, no triplanar stuff."""
    mat = bpy.data.materials.new(name="TriplanarMat")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)

    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_out.location  = (400, 0)
    n_bsdf.location = (100, 0)

    if "Base Color" in n_bsdf.inputs:
        n_bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    if "Roughness" in n_bsdf.inputs:
        n_bsdf.inputs["Roughness"].default_value = 0.5
    if "Metallic" in n_bsdf.inputs:
        n_bsdf.inputs["Metallic"].default_value = 0.0

    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
    return mat


def add_camera_and_light():
    cam_data = bpy.data.cameras.new("Camera")
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (0.0, -4.0, 2.0)
    # Aim the camera at the origin.
    direction = Vector((0.0, 0.0, 0.0)) - Vector(cam_obj.location)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam_obj

    light_data = bpy.data.lights.new(name="AreaLight", type='AREA')
    light_data.energy = 500.0
    light_data.size   = 2.0
    light_obj = bpy.data.objects.new("AreaLight", light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = (3.0, -2.0, 4.0)
    direction = Vector((0.0, 0.0, 0.0)) - Vector(light_obj.location)
    light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    return cam_obj, light_obj


def set_render_settings(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.seed = 0
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    # Standard view transform for deterministic color math.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------

clean_scene()

torus = make_torus()
mat   = build_flat_material()
torus.data.materials.append(mat)

cam, light = add_camera_and_light()
set_render_settings(bpy.context.scene)

# Make torus active + selected.
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.objects.active = torus
torus.select_set(True)

# --- Audit --------------------------------------------------------------
print("-" * 60)
print(f"  Torus object   : {torus.name} ({torus.type})")
print(f"  Torus verts    : {len(torus.data.vertices)}  "
      f"polys={len(torus.data.polygons)}")
print(f"  UV layers      : "
      f"{[l.name for l in torus.data.uv_layers]} "
      f"(count={len(torus.data.uv_layers)})")
print(f"  Material       : {torus.data.materials[0].name}")
mat_nodes = [n.bl_idname for n in mat.node_tree.nodes]
print(f"  Material nodes : {mat_nodes}")
print(f"  Camera         : {cam.name} loc={tuple(cam.location)}")
print(f"  Light          : {light.name} loc={tuple(light.location)}")
print(f"  Engine/samples : {bpy.context.scene.render.engine}/"
      f"{bpy.context.scene.cycles.samples}")
print(f"  Resolution     : "
      f"{bpy.context.scene.render.resolution_x}x"
      f"{bpy.context.scene.render.resolution_y}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
