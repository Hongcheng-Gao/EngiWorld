"""Build `ground_truth/answer.blend` for task HH05.

Strategy: open init, create 6 cylindrical cutters (radius=0.15, tall enough
to go clean through the 0.2-thick plate) at the prescribed grid positions
and one rectangular pocket cutter (2.0 x 0.8 x 0.08) centred on the top
face. Apply a Boolean DIFFERENCE modifier for each cutter, then delete the
cutter objects and recompute normals.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
INPUT_PATH  = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUTPUT_PATH = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


def make_cylinder(name, radius, depth, location, segments=32):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                          segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    me  = bpy.data.meshes.new(name + "Mesh")
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    bm.to_mesh(me); bm.free()
    obj.location = location
    bpy.context.view_layer.update()
    return obj


def make_box(name, dims, location):
    sx, sy, sz = dims
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
    obj.location = location
    bpy.context.view_layer.update()
    return obj


def boolean_diff(target, cutter, mod_name):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    mod = target.modifiers.new(mod_name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object    = cutter
    # Default solver works fine; explicit for clarity across Blender versions.
    if hasattr(mod, "solver"):
        mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod_name)
    bpy.data.objects.remove(cutter, do_unlink=True)


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
plate = bpy.data.objects["Plate"]

# 3x2 grid of through-bores: radius 0.15, plate is 0.2 thick so depth 0.4
# guarantees complete penetration with clearance on both faces.
bore_xs = (-1.2, 0.0, +1.2)
bore_ys = (-0.4, +0.4)
bore_idx = 0
for x in bore_xs:
    for y in bore_ys:
        cutter = make_cylinder(f"_Bore{bore_idx}",
                               radius=0.15,
                               depth=0.4,
                               location=(x, y, 0.0))
        boolean_diff(plate, cutter, f"Bore{bore_idx}")
        bore_idx += 1

# Top-face pocket: effective depth 0.08, carved from z=+0.1 down to
# z=+0.02. To avoid the top cutter face being coplanar with the plate top
# (which makes the Exact solver leave a thin shell), we extend the cutter
# 0.1 above the plate top. Height becomes 0.18, centred at z=+0.11.
# Lateral dims (2.0 x 0.8) and z extent down to +0.02 are preserved.
pocket_cutter = make_box("_Pocket",
                         dims=(2.0, 0.8, 0.18),
                         location=(0.0, 0.0, 0.11))
boolean_diff(plate, pocket_cutter, "Pocket")

# Tidy up: make Plate active & selected, recalc outward normals, drop any
# loose geometry left by the solver.
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = plate
plate.select_set(True)

bm = bmesh.new()
bm.from_mesh(plate.data)
# Remove any doubles introduced by the solver.
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
# Drop loose verts/edges (edges with zero linked faces, verts with no
# linked edges).
loose_edges = [e for e in bm.edges if not e.link_faces]
if loose_edges:
    bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
loose_verts = [v for v in bm.verts if not v.link_edges]
if loose_verts:
    bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(plate.data); bm.free()
plate.data.update()

bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_PATH)
print(f"  saved -> {OUTPUT_PATH}")
