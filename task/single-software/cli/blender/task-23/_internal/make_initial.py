"""Build `init_file/scene.blend` for task FH01 - Cloth Drape Alembic.

Scene:
  - A `Sphere` UV sphere at origin (radius 1.0, 32 segments x 16 rings).
    Gets a Collision modifier so cloth can collide with it.
  - A `Cloth` subdivided plane (30x30 subdivisions -> 31x31 grid ->
    961 verts) at (0, 0, 2.5), 4x4 BU in size. Gets a Cloth modifier
    with default settings (quality_steps=10) and a point cache over
    frames 1..60 (NOT baked).
  - Scene `frame_start=1`, `frame_end=60`.

The cloth simulation is intentionally NOT baked here so eval fails on
the unbaked init scene (plane stays at Z=2.5 throughout).

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


SPHERE_RADIUS       = 1.0
SPHERE_SEGMENTS     = 32
SPHERE_RINGS        = 16
CLOTH_SIZE          = 4.0       # plane is 4x4 BU
CLOTH_SUBDIVISIONS  = 30        # 30 cuts -> 31x31 verts = 961
CLOTH_START_Z       = 2.5
FRAME_END           = 60


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.actions,
                bpy.data.images):
        for d in list(blk):
            blk.remove(d)
    if bpy.context.scene.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()


def make_sphere():
    """UV sphere radius 1.0 at origin with 32 segments x 16 rings."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=SPHERE_SEGMENTS,
        v_segments=SPHERE_RINGS,
        radius=SPHERE_RADIUS,
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new("SphereMesh")
    obj = bpy.data.objects.new("Sphere", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj


def make_cloth_plane():
    """Subdivided 4x4 plane with 30x30 cuts -> 31x31 verts, at Z=2.5."""
    bm = bmesh.new()
    # `size` param in create_grid is half-edge. Use 1.0 then scale object
    # to get 4x4 size, OR use bmesh.ops.create_grid with matrix.
    # Simpler: create a plain plane at size=CLOTH_SIZE/2=2.0 then subdivide.
    bmesh.ops.create_grid(
        bm,
        x_segments=CLOTH_SUBDIVISIONS + 1,
        y_segments=CLOTH_SUBDIVISIONS + 1,
        size=CLOTH_SIZE / 2.0,  # `size` is half-edge-length in create_grid
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new("ClothMesh")
    obj = bpy.data.objects.new("Cloth", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = (0.0, 0.0, CLOTH_START_Z)
    return obj


def add_sphere_collision(sphere):
    """Add Collision modifier so cloth will collide with the sphere."""
    mod = sphere.modifiers.new("Collision", "COLLISION")
    # `collision_settings` is auto-created on the object when this modifier
    # is attached. Default thickness_outer is ~0.02.
    return mod


def add_cloth_modifier(cloth):
    """Add Cloth modifier with default settings and set cache range."""
    mod = cloth.modifiers.new("Cloth", "CLOTH")
    settings = mod.settings
    # quality_steps affects stability of the solver; 10 is a reasonable
    # default (Blender's default is 5; we bump it a bit for better
    # collision behaviour).
    settings.quality = 10
    # Leave most cloth settings at defaults - tweaking bending stiffness
    # and mass gives a cloth-like drape.
    # Collision settings live on `mod.collision_settings`.
    mod.collision_settings.use_collision = True
    mod.collision_settings.use_self_collision = False
    # Cache range.
    pc = mod.point_cache
    pc.frame_start = 1
    pc.frame_end   = FRAME_END
    return mod


def main():
    clean_scene()

    sphere = make_sphere()
    cloth  = make_cloth_plane()

    # Modifiers.
    add_sphere_collision(sphere)
    add_cloth_modifier(cloth)

    # Scene config.
    scene = bpy.context.scene
    scene.frame_start   = 1
    scene.frame_end     = FRAME_END
    scene.frame_current = 1
    scene.gravity       = (0.0, 0.0, -9.81)

    # Sanity dump.
    print(f"  Sphere: verts={len(sphere.data.vertices)} "
          f"loc={tuple(sphere.location)} "
          f"mods={[m.name for m in sphere.modifiers]}")
    print(f"  Cloth : verts={len(cloth.data.vertices)} "
          f"loc={tuple(cloth.location)} "
          f"mods={[m.name for m in cloth.modifiers]}")
    print(f"  scene.frame_start={scene.frame_start} "
          f"frame_end={scene.frame_end}")
    print("  cloth NOT baked (init state)")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


main()
