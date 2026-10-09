"""Build `init_file/scene.blend` for task IH03 - USD preview surface export.

Produces a scene containing:
  - `Cube_A` at (-1.5, 0, 0) with Principled BSDF material `Mat_A`
    (Base Color = (0.8, 0.2, 0.2, 1.0), Roughness = 0.3).
  - `Cube_B` at (+1.5, 0, 0) with Principled BSDF material `Mat_B`
    (Base Color = (0.2, 0.8, 0.2, 1.0), Roughness = 0.7).
  - Camera at (0, -5, 2) looking at the origin.
  - Area light above the scene.
  - Renderer = Cycles.
  - Units: METRIC / METERS / scale 1.0.

No USDA export is produced here - `init_file/` deliberately contains no
`.usda` output file, so the evaluator (which expects a USDA at
`output/scene.usda`) naturally FAILs at `file_exists` for the init case.

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
                bpy.data.lights, bpy.data.images, bpy.data.materials):
        for d in list(blk):
            blk.remove(d)


def make_material(name, base_color_rgba, roughness):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    principled = None
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            principled = n
            break
    if principled is None:
        principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Base Color"].default_value = base_color_rgba
    principled.inputs["Roughness"].default_value  = roughness
    # Also set viewport display color so the material is identifiable in UIs.
    mat.diffuse_color = base_color_rgba
    mat.roughness     = roughness
    return mat


def make_cube(name, location, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name      = name
    obj.data.name = name + "Mesh"
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj


def make_camera():
    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, -5.0, 2.0)
    # Aim at origin: compute rotation using track-to-like math.
    # Vector from camera -> target (0,0,0).
    tx, ty, tz = -cam.location.x, -cam.location.y, -cam.location.z
    # Convert to (rx, ry, rz) pointing +Y from camera. Blender cameras look
    # down -Z, so aim by pointing -Z at the origin.
    # Simple formula: use Track To via a constraint would be cleaner, but
    # we set an approximate Euler angle that looks at the origin.
    yaw = 0.0  # camera on Y axis, so no yaw needed
    pitch = math.atan2(-tz, math.sqrt(tx * tx + ty * ty))
    cam.rotation_euler = (math.pi / 2.0 + pitch, 0.0, 0.0)
    bpy.context.scene.camera = cam
    return cam


def make_light():
    lt = bpy.data.lights.new("AreaLight", type="AREA")
    lt.energy = 1000.0
    lt.size   = 3.0
    obj = bpy.data.objects.new("AreaLight", lt)
    bpy.context.collection.objects.link(obj)
    obj.location       = (0.0, -3.0, 4.0)
    obj.rotation_euler = (math.radians(30.0), 0.0, 0.0)
    return obj


clean_scene()

# --- Scene units / renderer ---------------------------------------------
scene = bpy.context.scene
scene.unit_settings.system       = "METRIC"
scene.unit_settings.length_unit  = "METERS"
scene.unit_settings.scale_length = 1.0
scene.render.engine              = "CYCLES"

# --- Materials -----------------------------------------------------------
mat_a = make_material("Mat_A", (0.8, 0.2, 0.2, 1.0), 0.3)
mat_b = make_material("Mat_B", (0.2, 0.8, 0.2, 1.0), 0.7)

# --- Cubes ---------------------------------------------------------------
make_cube("Cube_A", (-1.5, 0.0, 0.0), mat_a)
make_cube("Cube_B", ( 1.5, 0.0, 0.0), mat_b)

# --- Camera + Light ------------------------------------------------------
make_camera()
make_light()

# Sanity dump.
for name in ("Cube_A", "Cube_B"):
    ob = bpy.data.objects[name]
    mats = [m.name for m in ob.data.materials]
    print(f"  {name}: loc={tuple(ob.location)}, mats={mats}, "
          f"verts={len(ob.data.vertices)}, polys={len(ob.data.polygons)}")
for name in ("Mat_A", "Mat_B"):
    m = bpy.data.materials[name]
    bsdf = next((n for n in m.node_tree.nodes
                 if n.type == "BSDF_PRINCIPLED"), None)
    bc = tuple(bsdf.inputs["Base Color"].default_value) if bsdf else None
    r  = bsdf.inputs["Roughness"].default_value if bsdf else None
    print(f"  {name}: base_color={bc}, roughness={r}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
print("  (no USDA written - init_file has no scene.usda by design)")
