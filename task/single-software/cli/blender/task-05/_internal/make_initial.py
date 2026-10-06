"""Build init_file/scene.blend for task AH05 - Proximity Vertex Group.

Creates two mesh objects:
  - `Skin`: a 4x4 BU plane in XY, centered at origin, subdivided 40x40
    (1681 verts, 1600 quads), flat at z = 0. No modifiers.
  - `Bone`: a UV sphere with radius 0.3 positioned at world (0, 0, 0.5),
    sitting above the center of the skin.

Neither object carries an `Influence` attribute.

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

# Skin parameters (part of the task spec).
SKIN_SIDE   = 4.0   # 4 BU x 4 BU plane
SKIN_N_SUB  = 40    # 40x40 quads -> 41x41 = 1681 verts

# Bone parameters.
BONE_LOC    = (0.0, 0.0, 0.5)
BONE_RADIUS = 0.3


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.node_groups, bpy.data.materials,
                bpy.data.armatures):
        for d in list(blk):
            blk.remove(d)


def build_skin():
    """Return a mesh object `Skin`: 4x4 BU plane centered at origin,
    subdivided 40x40, flat at z=0."""
    bm = bmesh.new()
    step = SKIN_SIDE / SKIN_N_SUB
    half = SKIN_SIDE / 2.0
    verts = []
    for j in range(SKIN_N_SUB + 1):
        for i in range(SKIN_N_SUB + 1):
            x = -half + i * step
            y = -half + j * step
            verts.append(bm.verts.new((x, y, 0.0)))
    bm.verts.ensure_lookup_table()

    for j in range(SKIN_N_SUB):
        for i in range(SKIN_N_SUB):
            v00 = verts[j * (SKIN_N_SUB + 1) + i]
            v10 = verts[j * (SKIN_N_SUB + 1) + i + 1]
            v11 = verts[(j + 1) * (SKIN_N_SUB + 1) + i + 1]
            v01 = verts[(j + 1) * (SKIN_N_SUB + 1) + i]
            bm.faces.new((v00, v10, v11, v01))
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    me  = bpy.data.meshes.new("SkinMesh")
    obj = bpy.data.objects.new("Skin", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj


def build_bone():
    """Return a mesh object `Bone`: a UV sphere at (0, 0, 0.5) with
    radius 0.3. Object's `location` holds the world position; the mesh
    data itself is centered at the local origin."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16,
                              radius=BONE_RADIUS)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    me  = bpy.data.meshes.new("BoneMesh")
    obj = bpy.data.objects.new("Bone", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()
    obj.location = tuple(BONE_LOC)
    return obj


def main():
    clean_scene()
    bpy.context.scene.unit_settings.scale_length = 1.0

    skin = build_skin()
    bone = build_bone()

    n_sv = len(skin.data.vertices)
    n_sf = len(skin.data.polygons)
    n_bv = len(bone.data.vertices)
    n_bf = len(bone.data.polygons)
    print(f"  Skin verts: {n_sv} (expect {(SKIN_N_SUB + 1) ** 2})")
    print(f"  Skin faces: {n_sf} (expect {SKIN_N_SUB * SKIN_N_SUB})")
    print(f"  Skin modifiers: {len(skin.modifiers)} (expect 0)")
    print(f"  Bone verts: {n_bv}")
    print(f"  Bone faces: {n_bf}")
    print(f"  Bone location: {tuple(bone.location)}")

    # No Influence attribute yet.
    assert not any(a.name == "Influence" for a in skin.data.attributes), \
        "init must not already contain Influence attribute"

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
