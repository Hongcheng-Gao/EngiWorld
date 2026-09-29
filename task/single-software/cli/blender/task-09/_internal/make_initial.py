"""Build `init_file/parts.blend` for task BH03.

Creates 12 cuboid mesh objects `Part01..Part12`, arranged in an overlapping
T-shaped cluster so that every part shares real volume with at least one
neighbour (so a boolean union yields a single connected, non-trivial shape).

After placement, the script prints the overall AABB of all 12 parts so it
can be pasted into eval.py as the expected bounding box.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bmesh
import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "parts.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights):
        for d in list(blk):
            blk.remove(d)


def new_cube(name, dims, location):
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


clean_scene()

# 12 overlapping cuboids forming a T-shaped cluster.
#
# Horizontal bar of the T: spans x in [-3, 3], centred at y=0.7, z=1.0
#   - 6 boxes of size (1.2, 0.9, 1.0), centres stepping by 1.0 in x so each
#     box overlaps its neighbour in the x direction by 0.2.
#   - x centres: -2.5, -1.5, -0.5, +0.5, +1.5, +2.5
#
# Vertical stem of the T: spans y in [-2, 0.7] downward, centred at x=0.0
#   - 6 boxes of size (0.9, 1.2, 1.0), centres stepping by 1.0 in y so each
#     box overlaps its neighbour in the y direction by 0.2.
#   - y centres: -1.5, -0.5, +0.5, +1.5 — only 4 needed for stem; extend.
# We use 6 stem boxes with y centres spanning -1.5..+1.5 so the stem
# connects into the horizontal bar (y=0.7 bar overlaps with y=+1.0 stem).
#
# All boxes live at z in [0.5, 1.5] so overall z bbox is [0.5, 1.5].
# Actually simpler: use z in [0, 2] by making each box span z in [0, 2]
# (dims sz=2, loc_z=1.0). That way we pin the z AABB to [0, 2] exactly.

PARTS = []  # (name, dims, location)

# Horizontal bar (6 boxes) — along +x direction at y_centre = 0.7
bar_y     = 0.7
bar_sx    = 1.2     # each box 1.2 wide in x, centres 1.0 apart → 0.2 overlap
bar_sy    = 0.9     # 0.9 wide in y, centred at 0.7 → y in [0.25, 1.15]
bar_sz    = 2.0     # full z span [0, 2] when centred at z=1
bar_z     = 1.0
bar_xs    = [-2.5, -1.5, -0.5, +0.5, +1.5, +2.5]  # 6 centres
for i, x in enumerate(bar_xs):
    PARTS.append((f"Part{i+1:02d}",
                  (bar_sx, bar_sy, bar_sz),
                  (x, bar_y, bar_z)))

# Vertical stem (6 boxes) — along -y direction at x_centre = 0.0
stem_x    = 0.0
stem_sx   = 0.9
stem_sy   = 1.2
stem_sz   = 2.0
stem_z    = 1.0
stem_ys   = [-1.5, -0.8, -0.1, +0.6, +1.3, +2.0]  # 6 centres
# Issue: stem_ys[-1]=+2.0 would put the topmost stem box centred above the
# bar (bar is at y=0.7 with sy=0.9 → y in [0.25, 1.15]). We need the stem
# to connect into the bar; y_centre must be inside the bar's y extent.
# Adjusted plan: make the stem run from y=-2 upward to y=1.0 so the top
# of the stem overlaps the bar (bar bottom y=0.25).
# Use 6 stem centres stepping by 0.6 from -2.0+0.6=−1.4 up to +1.6 is
# too high. Let's step by 0.7 from y=-1.85 upward: -1.85,-1.15,-0.45,
# +0.25,+0.95,+1.65. Boxes are sy=1.2 so they extend ±0.6. Neighbour
# overlap in y is 1.2 - 0.7 = 0.5. Top stem box centred at 1.65 has y in
# [1.05, 2.25] — extends beyond bar. That pushes overall AABB in y up.
#
# Simpler plan: make the stem 6 boxes with centres -1.65,-1.05,-0.45,
# +0.15,+0.75,+1.35 (step 0.6). Each sy=1.2 → overlap 0.6. Top centre
# 1.35 → y in [0.75, 1.95]. Bottom centre -1.65 → y in [-2.25, -1.05].
# This sets AABB y in [-2.25, +1.95]. Bar AABB y in [0.25, 1.15].
#
# To lock AABB exactly to y in [-2, +2] and x in [-3, +3]:
#   - Bar: x centres at ±2.5, sx=1.0 (not 1.2) so x extents are [-3, 3],
#     neighbour overlap is 0. That's bad — need overlap.
#   - Use sx=1.2 with x centres at ±2.4: x extents are [-3, 3], neighbour
#     overlap 0.2. Good.
#   - Bar x centres (sx=1.2, overlap 0.2, step 1.0): -2.4,-1.4,-0.4,+0.6,
#     +1.6,+2.6 — that's not symmetric (ends at -3.0, +3.2). Adjust to
#     -2.5,-1.5,-0.5,+0.5,+1.5,+2.5 with sx=1.0 gives NO overlap.
#
# OK, let's drop the "AABB exactly = [-3,3]x[-2,2]x[0,2]" constraint and
# compute the actual AABB post-placement. The only requirement is (a)
# adjacent boxes overlap, (b) stem connects to bar, (c) we print the AABB
# and hard-code it into eval.py.

PARTS = []

# Bar: 6 boxes, sx=1.2, sy=0.9, sz=2.0, z_centre=1.0, y_centre=0.7
# x centres stepping by 1.0: -2.5..+2.5 → bar x extent = [-3.1, +3.1]
# neighbour overlap in x = 1.2 - 1.0 = 0.2
bar_specs = [
    (f"Part{i+1:02d}", (1.2, 0.9, 2.0), (x, 0.7, 1.0))
    for i, x in enumerate([-2.5, -1.5, -0.5, +0.5, +1.5, +2.5])
]
PARTS.extend(bar_specs)

# Stem: 6 boxes, sx=0.9, sy=1.2, sz=2.0, z_centre=1.0, x_centre=0.0
# y centres stepping by 1.0: topmost at +1.0 overlaps bar (bar y in
# [0.25, 1.15], stem top box sy=1.2 → y in [+0.4, +1.6] — overlaps bar).
# Stem y centres: -4.0..+1.0 would be 6 boxes overlapping by 0.2 each.
# Use y centres: -4.0, -3.0, -2.0, -1.0, 0.0, +1.0. Overall y extent =
# [-4.6, +1.6]. That's too long.
# Use y centres: -1.5, -0.8, -0.1, +0.6, +1.3, +2.0 — step 0.7 → overlap
# 0.5. Extent = [-2.1, +2.6]. Top overlaps bar well.
# Actually let's cap the stem length to reasonable: 6 boxes with sy=1.2
# step 0.7 span 5*0.7 + 1.2 = 4.7 units. Centre range [-1.85, +1.65].
# Overall y extent = [-2.45, +2.25]. That's workable.
# But we want the stem going *downward* (T shape) so bulk is below bar.
# Let's use y centres: -2.0, -1.3, -0.6, +0.1, +0.8, +1.5. Top box
# centred at 1.5 with sy=1.2 → y in [0.9, 2.1]. Bar y in [0.25, 1.15].
# Overlap y in [0.9, 1.15]. Good.
# Overall y extent: bottom box at -2.0 → y in [-2.6, -1.4]; top = +2.1.
# So overall y in [-2.6, +2.1]. Acceptable.

stem_specs = [
    (f"Part{i+7:02d}", (0.9, 1.2, 2.0), (0.0, y, 1.0))
    for i, y in enumerate([-2.0, -1.3, -0.6, +0.1, +0.8, +1.5])
]
PARTS.extend(stem_specs)

for (name, dims, loc) in PARTS:
    new_cube(name, dims, loc)

# Compute overall AABB of all 12 parts.
xs_all = []
ys_all = []
zs_all = []
for obj in bpy.data.objects:
    if not obj.name.startswith("Part"):
        continue
    # world-space vert coords
    mw = obj.matrix_world
    for v in obj.data.vertices:
        co = mw @ v.co
        xs_all.append(co.x)
        ys_all.append(co.y)
        zs_all.append(co.z)

xmin, xmax = min(xs_all), max(xs_all)
ymin, ymax = min(ys_all), max(ys_all)
zmin, zmax = min(zs_all), max(zs_all)

print("  ---- BH03 initial scene ----")
print(f"  parts: {sum(1 for o in bpy.data.objects if o.name.startswith('Part'))}")
print(f"  AABB x: [{xmin:.6f}, {xmax:.6f}]")
print(f"  AABB y: [{ymin:.6f}, {ymax:.6f}]")
print(f"  AABB z: [{zmin:.6f}, {zmax:.6f}]")
print("  ---- paste into eval.py ----")
print(f"  EXPECTED_BBOX = ({xmin:.6f}, {xmax:.6f}, "
      f"{ymin:.6f}, {ymax:.6f}, {zmin:.6f}, {zmax:.6f})")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
