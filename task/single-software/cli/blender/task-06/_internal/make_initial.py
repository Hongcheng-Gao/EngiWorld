"""Build init_file/scene.blend for task AH06 - Field-Driven Instance Rotation.

A scene with two mesh objects:

  1. `Globe` - a UV sphere at the origin, radius 1.5, 32 segments * 16 rings.
     No modifiers.

  2. `Spike` - a cone (radius = 0.05, depth = 0.3) whose BASE sits at its
     own origin (local z = 0) and whose TIP is at local z = +0.3. When
     instanced with +Z aligned to a surface normal, the spike points
     outward from the surface.

Scene units are set to meters.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

# Globe parameters.
GLOBE_RADIUS   = 1.5
GLOBE_SEGMENTS = 32
GLOBE_RINGS    = 16

# Spike parameters.
SPIKE_RADIUS = 0.05
SPIKE_DEPTH  = 0.30


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.node_groups, bpy.data.materials,
                bpy.data.armatures):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def build_globe():
    """Create a UV sphere at the origin with radius=1.5, 32 segments,
    16 rings. Use bmesh.ops.create_uvsphere to build the geometry."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(
        bm,
        u_segments=GLOBE_SEGMENTS,
        v_segments=GLOBE_RINGS,
        radius=GLOBE_RADIUS,
        matrix=Matrix.Identity(4),
        calc_uvs=False,
    )
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    me  = bpy.data.meshes.new("GlobeMesh")
    obj = bpy.data.objects.new("Globe", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()
    obj.location = (0.0, 0.0, 0.0)
    return obj


def build_spike():
    """Create a cone (radius=0.05, depth=0.3) whose base sits at local
    z = 0 and whose tip is at local z = +0.3.

    bmesh.ops.create_cone generates a cone centered at the origin with
    z in [-depth/2, +depth/2]. We then translate every vertex by
    (0, 0, +depth/2) INSIDE the bmesh, so that in local coordinates the
    base sits at z = 0 and the tip is at z = +depth. The object origin
    remains at (0, 0, 0) so that when instanced at a point with +Z
    aligned to the normal, the instance's local z = 0 plane coincides
    with the point and the tip points outward along the normal.
    """
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=16,
        radius1=SPIKE_RADIUS,   # base radius
        radius2=0.0,            # apex
        depth=SPIKE_DEPTH,
        matrix=Matrix.Identity(4),
        calc_uvs=False,
    )

    # Shift all verts +Z by depth/2 so the base sits at local z = 0.
    for v in bm.verts:
        v.co.z += SPIKE_DEPTH * 0.5

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))

    me  = bpy.data.meshes.new("SpikeMesh")
    obj = bpy.data.objects.new("Spike", me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me)
    bm.free()
    # Keep the object origin at the world origin — the Spike is a
    # passive source object for Object Info in the GN tree on Globe.
    obj.location = (0.0, 0.0, 0.0)
    return obj


def main():
    clean_scene()

    # Scene units: meters.
    scn = bpy.context.scene
    scn.unit_settings.system         = "METRIC"
    scn.unit_settings.length_unit    = "METERS"
    scn.unit_settings.scale_length   = 1.0

    globe = build_globe()
    spike = build_spike()

    # Sanity prints.
    gme = globe.data
    sme = spike.data
    gxs = [v.co.x for v in gme.vertices]
    gys = [v.co.y for v in gme.vertices]
    gzs = [v.co.z for v in gme.vertices]
    szs = [v.co.z for v in sme.vertices]

    print(f"  Globe verts: {len(gme.vertices)}, faces: {len(gme.polygons)}")
    print(f"  Globe bbox X: [{min(gxs):+.4f}, {max(gxs):+.4f}]  "
          f"(expect ~[-{GLOBE_RADIUS}, +{GLOBE_RADIUS}])")
    print(f"  Globe bbox Y: [{min(gys):+.4f}, {max(gys):+.4f}]")
    print(f"  Globe bbox Z: [{min(gzs):+.4f}, {max(gzs):+.4f}]")
    print(f"  Globe location: {tuple(globe.location)}")
    print(f"  Globe modifiers: {len(globe.modifiers)} (expect 0)")
    print(f"  Spike verts: {len(sme.vertices)}, faces: {len(sme.polygons)}")
    print(f"  Spike local Z range: [{min(szs):+.4f}, {max(szs):+.4f}]  "
          f"(expect [0.0, +{SPIKE_DEPTH}])")
    print(f"  Spike location: {tuple(spike.location)}")
    print(f"  Scene unit system: {scn.unit_settings.system} / "
          f"{scn.unit_settings.length_unit}")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
    print(f"  saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
