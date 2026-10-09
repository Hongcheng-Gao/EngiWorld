"""Build `init_file/scene.blend` for task FH02 - Rigid Body Bake to Keyframes.

Scene:
  - A static `Ground` plane (20x20 BU top face at z=0) with PASSIVE rigid
    body using MESH collision shape.
  - 10 cubes `Cube_00..Cube_09` of size 1 BU, stacked vertically above the
    ground at Z = 0.5, 2.0, 3.5, 5.0, ..., leaving air gaps between them so
    the stack collapses when the simulation runs. Each is ACTIVE
    rigid body with MESH collision and mass=1.0.
  - Scene frame range: 1..120. Rigid body world exists but has NOT been
    baked.

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


CUBE_COUNT   = 10
CUBE_SIZE    = 1.0
CUBE_SPACING = 1.5    # center-to-center vertical spacing (leaves 0.5 BU gap)
CUBE_FIRST_Z = 0.5    # first cube sits with bottom on ground (top at z=1)

GROUND_DIMS  = (20.0, 20.0, 0.2)
GROUND_TOP_Z = 0.0     # top face of ground sits at z=0


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.materials, bpy.data.actions):
        for d in list(blk):
            blk.remove(d)
    if bpy.context.scene.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()


def make_box_mesh(name, sx, sy, sz):
    """Create a box mesh with given XYZ dimensions."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    return obj


def make_ground():
    """Ground: 20 x 20 x 0.2, top face at z = 0."""
    obj = make_box_mesh("Ground", GROUND_DIMS[0], GROUND_DIMS[1], GROUND_DIMS[2])
    obj.location = (0.0, 0.0, GROUND_TOP_Z - GROUND_DIMS[2] / 2.0)  # -0.1
    return obj


def make_cube(i):
    name = f"Cube_{i:02d}"
    obj  = make_box_mesh(name, CUBE_SIZE, CUBE_SIZE, CUBE_SIZE)
    z = CUBE_FIRST_Z + i * CUBE_SPACING
    obj.location = (0.0, 0.0, z)
    return obj


def add_rigid_body(obj, body_type, mass=1.0, friction=0.5, restitution=0.1,
                   shape="MESH"):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.rigidbody.object_add(type=body_type)
    rb = obj.rigid_body
    rb.mass            = mass
    rb.friction        = friction
    rb.restitution     = restitution
    rb.collision_shape = shape


def main():
    clean_scene()

    # Create rigid body world before adding rigid body objects.
    bpy.ops.rigidbody.world_add()
    rbw = bpy.context.scene.rigidbody_world
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end   = 120

    ground = make_ground()
    add_rigid_body(ground, body_type="PASSIVE", mass=1.0, friction=0.5,
                   restitution=0.1, shape="MESH")

    cubes = []
    for i in range(CUBE_COUNT):
        c = make_cube(i)
        # BOX collision shape is the stable choice for cuboid meshes; MESH
        # shape on small fast-moving boxes tends to tunnel through itself.
        add_rigid_body(c, body_type="ACTIVE", mass=1.0, friction=0.5,
                       restitution=0.1, shape="BOX")
        cubes.append(c)

    # Tighten solver parameters so the tall stack doesn't tunnel through
    # itself or the ground during the 120-frame bake.
    rbw.substeps_per_frame = 10
    rbw.solver_iterations  = 20

    scene = bpy.context.scene
    scene.frame_start   = 1
    scene.frame_end     = 120
    scene.frame_current = 1
    scene.gravity       = (0.0, 0.0, -9.81)

    # Sanity dump.
    print(f"  Ground: dims={tuple(ground.dimensions)} "
          f"loc={tuple(ground.location)} rb_type={ground.rigid_body.type} "
          f"shape={ground.rigid_body.collision_shape}")
    for c in cubes:
        print(f"  {c.name}: dims={tuple(c.dimensions)} "
              f"loc=({c.location.x:.2f},{c.location.y:.2f},{c.location.z:.2f}) "
              f"rb_type={c.rigid_body.type} shape={c.rigid_body.collision_shape}")
    print(f"  rigidbody_world = {scene.rigidbody_world}")
    print(f"  frame_start={scene.frame_start} frame_end={scene.frame_end}")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


main()
