"""Build `init_file/ch.blend` for task IH02 - glTF roundtrip with PBR.

Produces a simple "character" scene with three distinct mesh objects,
each with its own Principled BSDF material:

  - `Body`: cube scaled into a torso shape, material `Mat_Body`
     base_color = (0.2, 0.3, 0.6)  (blue cloth), roughness = 0.6
  - `Head`: UV sphere above the torso, material `Mat_Head`
     base_color = (0.85, 0.7, 0.6) (skin tone), roughness = 0.5
  - `Arms`: two cylinders joined into one mesh, material `Mat_Arms`
     base_color = (0.2, 0.3, 0.6)  (blue cloth), roughness = 0.6

Also adds a simple camera and a point light.

The init file is deliberately missing the glTF output — the task is to
export the GLB and re-import it to produce a `verify.blend`.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bpy


HERE      = os.path.dirname(os.path.abspath(__file__))
TASK_DIR  = os.path.dirname(HERE)
OUT_BLEND = os.path.join(TASK_DIR, "init_file", "ch.blend")

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.images, bpy.data.materials,
                bpy.data.actions, bpy.data.armatures):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_material(name, base_color_rgb, roughness, metallic=0.0):
    """Create a Principled BSDF material with the given base_color (RGB)
    and roughness/metallic values. `base_color_rgb` is a 3-tuple; alpha
    is set to 1.0."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = bpy.data.materials.new  # keep reference to avoid lint
    nt = mat.node_tree
    principled = None
    for n in nt.nodes:
        if n.type == "BSDF_PRINCIPLED":
            principled = n
            break
    if principled is None:
        principled = nt.nodes.new("ShaderNodeBsdfPrincipled")
    r, g, b = base_color_rgb
    principled.inputs["Base Color"].default_value = (r, g, b, 1.0)
    if "Roughness" in principled.inputs:
        principled.inputs["Roughness"].default_value = roughness
    if "Metallic" in principled.inputs:
        principled.inputs["Metallic"].default_value = metallic
    # Viewport color (used by non-node paths).
    mat.diffuse_color = (r, g, b, 1.0)
    return mat


def assign_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


clean_scene()

# --- Scene units (METRIC / meters) --------------------------------------
scene = bpy.context.scene
scene.unit_settings.system       = "METRIC"
scene.unit_settings.length_unit  = "METERS"
scene.unit_settings.scale_length = 1.0

# --- Materials -----------------------------------------------------------
# IMPORTANT: base colors below are the canonical "expected" values the
# evaluator compares against. Keep them in sync with eval.py's EXPECTED
# table.
mat_body = make_material("Mat_Body", (0.2, 0.3, 0.6), roughness=0.6)
mat_head = make_material("Mat_Head", (0.85, 0.7, 0.6), roughness=0.5)
mat_arms = make_material("Mat_Arms", (0.2, 0.3, 0.6), roughness=0.6)

# --- Body: a scaled cube (torso) ----------------------------------------
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 1.0))
body = bpy.context.active_object
body.name      = "Body"
body.data.name = "BodyMesh"
body.scale     = (0.6, 0.35, 1.0)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
assign_material(body, mat_body)

# --- Head: a UV sphere --------------------------------------------------
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=0.35, location=(0.0, 0.0, 1.90), segments=24, ring_count=16)
head = bpy.context.active_object
head.name      = "Head"
head.data.name = "HeadMesh"
assign_material(head, mat_head)

# --- Arms: two cylinders joined into one mesh --------------------------
# Left cylinder
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.12, depth=0.9, location=(-0.80, 0.0, 1.0), vertices=16)
left = bpy.context.active_object
left.rotation_euler = (0.0, 0.0, 0.0)

# Right cylinder
bpy.ops.mesh.primitive_cylinder_add(
    radius=0.12, depth=0.9, location=(0.80, 0.0, 1.0), vertices=16)
right = bpy.context.active_object

# Select both + make the right one active, then join.
bpy.ops.object.select_all(action="DESELECT")
left.select_set(True)
right.select_set(True)
bpy.context.view_layer.objects.active = right
bpy.ops.object.join()
arms = bpy.context.active_object
arms.name      = "Arms"
arms.data.name = "ArmsMesh"
assign_material(arms, mat_arms)

# --- Camera --------------------------------------------------------------
bpy.ops.object.camera_add(location=(4.0, -4.5, 2.0),
                          rotation=(1.1, 0.0, 0.78))
cam = bpy.context.active_object
cam.name = "Camera"
scene.camera = cam

# --- Light ---------------------------------------------------------------
bpy.ops.object.light_add(type="POINT", location=(3.0, -2.0, 4.0))
lamp = bpy.context.active_object
lamp.name = "KeyLight"
if hasattr(lamp.data, "energy"):
    lamp.data.energy = 1000.0

# --- Sanity dump --------------------------------------------------------
print("--- scene content ---")
for name in ("Body", "Head", "Arms"):
    ob = bpy.data.objects[name]
    mats = [m.name for m in ob.data.materials]
    print(f"  {name}: loc={tuple(round(c, 3) for c in ob.location)}, "
          f"mats={mats}, verts={len(ob.data.vertices)}, "
          f"polys={len(ob.data.polygons)}")
for mat in (mat_body, mat_head, mat_arms):
    nt = mat.node_tree
    p = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    bc = tuple(p.inputs["Base Color"].default_value) if p else None
    print(f"  mat {mat.name}: base_color={bc}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
