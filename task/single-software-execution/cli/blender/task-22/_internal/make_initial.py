"""Build `init_file/scene.blend` for task EH04 - Shape-key smile morph + bone driver.

Scene:
  - Mesh `Face`: a subdivided plane (5x5 verts, 16 quad faces) acting as
    a simple "face" canvas.
  - Two shape keys on Face:
      * Basis -- identity.
      * smile -- vertices with |x| >= 0.5 get a +Z bump scaled by |x| so
        the outer corners lift, simulating mouth corners lifting.
  - Armature object `Rig` at origin with a single bone `ctrl_jaw`
    (head=(0,0,0), tail=(0,0,0.5)).
  - NO driver yet on the smile shape key (value stays at 0).
  - Face is NOT parented to Rig.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.armatures, bpy.data.actions,
                bpy.data.materials, bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def make_face_mesh():
    """Create a 2x2 BU subdivided plane (5x5 verts, 16 quad faces)."""
    bm = bmesh.new()
    size = 2.0
    subdivs = 4  # => 5 x 5 = 25 verts
    half = size / 2.0
    verts = []
    for j in range(subdivs + 1):
        row = []
        for i in range(subdivs + 1):
            x = -half + (size * i / subdivs)
            y = -half + (size * j / subdivs)
            row.append(bm.verts.new((x, y, 0.0)))
        verts.append(row)
    bm.verts.ensure_lookup_table()
    for j in range(subdivs):
        for i in range(subdivs):
            bm.faces.new((verts[j][i], verts[j][i + 1],
                          verts[j + 1][i + 1], verts[j + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    me  = bpy.data.meshes.new("FaceMesh")
    obj = bpy.data.objects.new("Face", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj


def add_smile_shape_key(obj):
    """Add Basis + `smile` shape keys.

    `smile` deforms verts with |x| >= 0.5 so they lift in +Z by an amount
    proportional to |x|, simulating mouth corners lifting.
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    basis = obj.shape_key_add(name="Basis", from_mix=False)

    smile = obj.shape_key_add(name="smile", from_mix=False)
    for i, v in enumerate(obj.data.vertices):
        ax = abs(v.co.x)
        if ax >= 0.5:
            smile.data[i].co = (v.co.x, v.co.y, v.co.z + 0.5 * ax)
        else:
            smile.data[i].co = (v.co.x, v.co.y, v.co.z)

    smile.slider_min = 0.0
    smile.slider_max = 1.0
    smile.value = 0.0
    return basis, smile


def build_rig():
    arm_data = bpy.data.armatures.new("RigData")
    rig      = bpy.data.objects.new("Rig", arm_data)
    bpy.context.collection.objects.link(rig)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    eb = arm_data.edit_bones.new("ctrl_jaw")
    eb.head = (0.0, 0.0, 0.0)
    eb.tail = (0.0, 0.0, 0.5)

    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


clean_scene()

# Camera
cam_data = bpy.data.cameras.new("Camera")
cam      = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location       = (7.36, -6.93, 4.96)
cam.rotation_euler = (1.1093, 0.0, 0.8149)

# Light
light_data = bpy.data.lights.new("Light", type="POINT")
light      = bpy.data.objects.new("Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (4.08, 1.0, 5.9)

face = make_face_mesh()
basis, smile = add_smile_shape_key(face)
rig = build_rig()

# Position the rig off to the side so the Face isn't visually covered.
rig.location = (3.0, 0.0, 0.0)

# Set ctrl_jaw rotation_mode on the pose bone to XYZ so the evaluator can
# poke rotation_euler later without it being ignored as quaternion-only.
bpy.context.view_layer.objects.active = rig
rig.pose.bones["ctrl_jaw"].rotation_mode = "XYZ"

# Deliberately do NOT add a driver here.

bpy.context.view_layer.update()

# Diagnostics
print("  Initial scene objects:")
for o in bpy.data.objects:
    print(f"    {o.name}  type={o.type}  loc={tuple(o.location)}")
print(f"  Face verts={len(face.data.vertices)} faces={len(face.data.polygons)}")
print(f"  Face shape keys = "
      f"{[k.name for k in face.data.shape_keys.key_blocks]}")
print(f"  smile.value = {smile.value}, slider=[{smile.slider_min}, "
      f"{smile.slider_max}]")
print(f"  Rig bones:")
for b in rig.data.bones:
    print(f"    {b.name} head={tuple(b.head_local)} tail={tuple(b.tail_local)}")
print(f"  ctrl_jaw pose rotation_mode = "
      f"{rig.pose.bones['ctrl_jaw'].rotation_mode}")
ad = face.data.shape_keys.animation_data
print(f"  shape_keys animation_data = {ad}  (should be None in init)")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
