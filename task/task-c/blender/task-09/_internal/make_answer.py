"""Build `ground_truth/answer.blend` for task BH03.

Strategy: open parts.blend, pick Part01 as the accumulator. For every other
Part, add a Boolean UNION modifier (solver=EXACT) pointing at it, apply the
modifier, then delete the cutter. At the end we have one welded object.
Rename the accumulator to `Welded`. Recalc normals, remove doubles, clean
any loose geometry left by the solver. Verify the modifier stack is empty.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
INPUT_PATH  = os.path.join(TASK_DIR, "init_file", "parts.blend")
OUTPUT_PATH = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)


def boolean_union(target, cutter, mod_name):
    """Add a Boolean UNION modifier to `target` against `cutter`, apply,
    then delete the cutter object."""
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    mod = target.modifiers.new(mod_name, "BOOLEAN")
    mod.operation = "UNION"
    mod.object    = cutter
    if hasattr(mod, "solver"):
        mod.solver = "EXACT"
    bpy.ops.object.modifier_apply(modifier=mod_name)
    bpy.data.objects.remove(cutter, do_unlink=True)


bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)

# Collect the 12 parts in numerical order. Part01 becomes the accumulator.
part_names = sorted(o.name for o in bpy.data.objects
                    if o.name.startswith("Part") and o.type == "MESH")
assert len(part_names) == 12, f"expected 12 Part objects, got {len(part_names)}"

accumulator = bpy.data.objects[part_names[0]]
for i, nm in enumerate(part_names[1:], start=1):
    cutter = bpy.data.objects[nm]
    boolean_union(accumulator, cutter, f"Weld{i:02d}")

# Rename to Welded.
accumulator.name      = "Welded"
accumulator.data.name = "WeldedMesh"

# Tidy the final mesh: remove tiny doubles, drop any stray loose geometry,
# recompute outward normals.
bm = bmesh.new()
bm.from_mesh(accumulator.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
loose_edges = [e for e in bm.edges if not e.link_faces]
if loose_edges:
    bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
loose_verts = [v for v in bm.verts if not v.link_edges]
if loose_verts:
    bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(accumulator.data); bm.free()
accumulator.data.update()

# Sanity: modifier stack must be empty.
assert len(accumulator.modifiers) == 0, \
    f"modifier stack not empty: {[m.name for m in accumulator.modifiers]}"

# Report final stats (world-space).
me = accumulator.data
mw = accumulator.matrix_world
world_coords = [mw @ v.co for v in me.vertices]
xs = [c.x for c in world_coords]
ys = [c.y for c in world_coords]
zs = [c.z for c in world_coords]
print(f"  Welded: verts={len(me.vertices)}, edges={len(me.edges)}, "
      f"faces={len(me.polygons)}")
print(f"  obj location: ({accumulator.location.x:.4f}, "
      f"{accumulator.location.y:.4f}, {accumulator.location.z:.4f})")
print(f"  WORLD AABB x: [{min(xs):.6f}, {max(xs):.6f}]")
print(f"  WORLD AABB y: [{min(ys):.6f}, {max(ys):.6f}]")
print(f"  WORLD AABB z: [{min(zs):.6f}, {max(zs):.6f}]")

# Confirm no mesh objects remain other than Welded.
mesh_names = [o.name for o in bpy.data.objects if o.type == "MESH"]
print(f"  mesh objects remaining: {mesh_names}")

bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_PATH)
print(f"  saved -> {OUTPUT_PATH}")
