"""Build `init_file/scene.blend` for task KH05 -- Camera Silhouette Optimization.

Scene:
  - `Target` -- a single mesh object centered at the origin whose bounding box
    is roughly 3.0 (X) x 0.5 (Y) x 2.0 (Z). It is built by joining an
    axis-aligned box (3.0 x 0.5 x 2.0) with a small bump on one side to
    break symmetry.
  - `Camera` -- orthographic (ortho_scale = 5.0) at distance 5.0 from the
    origin at a deliberately sub-optimal angle (azimuth 30 deg, elevation
    15 deg). It is NOT pointing from the optimum direction (which is along
    the +/-Y axis).
  - World: pure white background (does not actually matter for the
    silhouette-via-alpha test because `scene.render.film_transparent = True`;
    the background is never written to the rendered RGBA PNG).
  - Cycles CPU, 4 samples, denoising off, 256x256 RGBA PNG,
    `film_transparent = True`, View Transform = Standard.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bpy
from mathutils import Vector

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    """Wipe every datablock so we build from a known state."""
    if bpy.context.scene.objects:
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.images,
                bpy.data.worlds, bpy.data.objects, bpy.data.node_groups):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_target():
    """Build the asymmetric Target mesh.

    Main body: axis-aligned box with half-extents (1.5, 0.25, 1.0) centered
    at origin -- so total dims are 3.0 x 0.5 x 2.0. Widest in X, narrowest
    in Y, tall in Z. That makes the optimum viewing direction along +/-Y
    (silhouette area ~ 3.0 * 2.0 = 6 units^2).

    Bump: small cube offset on +X/+Z corner to break perfect symmetry so
    the optimum is not equally good from any one of the 8 axis directions.
    """
    # Main body: a unit cube scaled to (3, 0.5, 2).
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    body = bpy.context.active_object
    body.name = "Target"
    body.scale = (3.0, 0.5, 2.0)
    # Apply the scale so verts sit at the correct world coordinates and the
    # bounding-box dims are literal.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Bump: small cube on the +X/+Z face to break symmetry.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(1.2, 0.0, 0.8))
    bump = bpy.context.active_object
    bump.name = "TargetBump"
    bump.scale = (0.4, 0.6, 0.3)  # slightly wider in Y than the main body
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Join bump into body so we have a single `Target` object.
    bpy.ops.object.select_all(action="DESELECT")
    bump.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()

    target = bpy.context.active_object
    target.name = "Target"

    # Give it an opaque gray material. Silhouette testing works on alpha,
    # but a nonblack material helps visual inspection of the PNG.
    mat = bpy.data.materials.new("TargetMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1.0)
    if target.data.materials:
        target.data.materials[0] = mat
    else:
        target.data.materials.append(mat)
    return target


def place_camera_on_sphere(cam, az_deg, el_deg, radius=5.0):
    """Place `cam` at spherical coords (az, el) at `radius` from the origin,
    then orient it to look at the origin. Azimuth 0 deg is +X, 90 deg is +Y.
    Elevation 0 is the equator (z=0); +90 deg is +Z (top-down).
    """
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    x = radius * math.cos(el) * math.cos(az)
    y = radius * math.cos(el) * math.sin(az)
    z = radius * math.sin(el)
    cam.location = (x, y, z)

    direction = Vector((0.0, 0.0, 0.0)) - Vector(cam.location)
    cam.rotation_mode = 'QUATERNION'
    cam.rotation_quaternion = direction.to_track_quat('-Z', 'Y')


def make_camera(az_deg=30.0, el_deg=15.0, radius=5.0, ortho_scale=5.0):
    """Create an orthographic Camera at the given spherical angle."""
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = ortho_scale
    cam_obj  = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    place_camera_on_sphere(cam_obj, az_deg, el_deg, radius=radius)
    bpy.context.scene.camera = cam_obj
    return cam_obj


def make_white_world():
    w = bpy.data.worlds.new("World")
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg  = nt.nodes.new("ShaderNodeBackground")
    out.location = (300, 0)
    bg.location  = (0, 0)
    bg.inputs["Color"].default_value    = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bpy.context.scene.world = w
    return w


def apply_render_settings(scene):
    scene.render.engine        = "CYCLES"
    scene.cycles.samples       = 4
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.device        = "CPU"
    scene.render.resolution_x  = 256
    scene.render.resolution_y  = 256
    scene.render.resolution_percentage = 100
    # Transparent film so alpha = 0 where the object is not visible. This is
    # how we measure silhouette area.
    scene.render.film_transparent = True
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


clean_scene()

target = make_target()
cam    = make_camera(az_deg=30.0, el_deg=15.0, radius=5.0, ortho_scale=5.0)
world  = make_white_world()

scene = bpy.context.scene
apply_render_settings(scene)

print("-" * 60)
print(f"  target.name           = {target.name}")
print(f"  target.location       = {tuple(target.location)}")
# Bounding box in world space (approx, using local bb * scale).
bb_local = [Vector(c) for c in target.bound_box]
bb_world = [target.matrix_world @ v for v in bb_local]
xs = [v.x for v in bb_world]; ys = [v.y for v in bb_world]; zs = [v.z for v in bb_world]
print(f"  target.bb_dims        = "
      f"({max(xs)-min(xs):.3f}, {max(ys)-min(ys):.3f}, {max(zs)-min(zs):.3f})")
print(f"  camera.type           = {cam.data.type}")
print(f"  camera.ortho_scale    = {cam.data.ortho_scale}")
print(f"  camera.location       = "
      f"({cam.location.x:+.3f}, {cam.location.y:+.3f}, {cam.location.z:+.3f})")
print(f"  camera.distance       = {cam.location.length:.3f}")
print(f"  render.engine         = {scene.render.engine}")
print(f"  cycles.samples        = {scene.cycles.samples}")
print(f"  resolution            = "
      f"{scene.render.resolution_x}x{scene.render.resolution_y}")
print(f"  film_transparent      = {scene.render.film_transparent}")
print("-" * 60)

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
