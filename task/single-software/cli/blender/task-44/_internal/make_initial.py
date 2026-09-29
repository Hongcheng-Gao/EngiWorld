"""Build `init_file/scene.blend` for task KH06 - procedural city.

Produces a scene containing:
  - A ground `Plane` at Z=0, 20 x 20 BU, grey Principled BSDF material
    (`Mat_Ground`).
  - Camera at (15, -15, 20) looking at the origin.
  - A sun light overhead.
  - Scene units: METRIC / METERS.
  - Renderer: Cycles.

No buildings are added here. The ground-truth script (make_answer.py)
adds the 10 Building_00..Building_09 objects and their materials, then
exports the USDA.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bpy


HERE      = os.path.dirname(os.path.abspath(__file__))
TASK_DIR  = os.path.dirname(HERE)
OUT_BLEND = os.path.join(TASK_DIR, "init_file", "scene.blend")

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.images, bpy.data.materials,
                bpy.data.node_groups):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_ground_material():
    mat = bpy.data.materials.new(name="Mat_Ground")
    mat.use_nodes = True
    nt = mat.node_tree
    principled = None
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            principled = n
            break
    if principled is None:
        principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    grey = (0.35, 0.35, 0.35, 1.0)
    principled.inputs["Base Color"].default_value = grey
    principled.inputs["Roughness"].default_value  = 0.8
    mat.diffuse_color = grey
    return mat


def make_ground(mat):
    """A 20x20 BU plane at Z=0."""
    bpy.ops.mesh.primitive_plane_add(size=20.0, location=(0.0, 0.0, 0.0))
    obj = bpy.context.active_object
    obj.name = "Ground"
    obj.data.name = "GroundMesh"
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (15.0, -15.0, 20.0)
    # Aim at origin. Blender cameras look down -Z; use a Track-To
    # approximation via Euler angles. We compute angles that point the
    # camera's local -Z at the origin.
    # Vector from camera -> origin.
    dx, dy, dz = -cam.location.x, -cam.location.y, -cam.location.z
    # Yaw around Z, then pitch around X.
    yaw   = math.atan2(dx, -dy)   # 0 when looking along +Y
    horiz = math.sqrt(dx * dx + dy * dy)
    pitch = math.atan2(horiz, -dz)  # 0 when looking straight down
    cam.rotation_euler = (pitch, 0.0, yaw)
    bpy.context.scene.camera = cam
    return cam


def make_sun_light():
    lt = bpy.data.lights.new("Sun", type="SUN")
    lt.energy = 3.0
    obj = bpy.data.objects.new("Sun", lt)
    bpy.context.collection.objects.link(obj)
    obj.location       = (5.0, -5.0, 15.0)
    obj.rotation_euler = (math.radians(45.0), math.radians(15.0), 0.0)
    return obj


clean_scene()

# --- Scene units / renderer ---------------------------------------------
scene = bpy.context.scene
scene.unit_settings.system       = "METRIC"
scene.unit_settings.length_unit  = "METERS"
scene.unit_settings.scale_length = 1.0
scene.render.engine              = "CYCLES"

# --- Ground --------------------------------------------------------------
ground_mat = make_ground_material()
ground     = make_ground(ground_mat)

# --- Camera + sun light --------------------------------------------------
make_camera()
make_sun_light()

# --- Audit ---------------------------------------------------------------
print("-" * 60)
print(f"  Ground object        : {ground.name} ({ground.type})")
print(f"  Ground verts/polys   : {len(ground.data.vertices)}/{len(ground.data.polygons)}")
print(f"  Ground material      : {[m.name for m in ground.data.materials]}")
print(f"  #Buildings           : "
      f"{sum(1 for o in bpy.data.objects if o.name.startswith('Building_'))} "
      f"(expect 0)")
print(f"  Scene unit length    : {scene.unit_settings.length_unit}")
print(f"  Renderer             : {scene.render.engine}")
print("-" * 60)

assert sum(1 for o in bpy.data.objects if o.name.startswith("Building_")) == 0, \
    "init must have no buildings"

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
print("  (no USDA written - init_file has no city.usda by design)")
