"""Build `init_file/bricks.csv` and `init_file/template.blend` for task BH02.

- `bricks.csv`: 100 rows laying out a 10x10 axis-aligned brick wall.
  Each brick is 0.2 x 0.1 x 0.05 m, arranged on a grid in the X-Z plane
  with a half-brick stagger every other row (pattern only; rotations are
  all zero). Header: `x,y,z,rx,ry,rz,sx,sy,sz`.
- `template.blend`: an empty Blender scene — no objects, no cameras,
  no lights.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
CSV_PATH   = os.path.join(TASK_DIR, "init_file", "bricks.csv")
BLEND_PATH = os.path.join(TASK_DIR, "init_file", "template.blend")

os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)

# Brick dimensions (meters) — x along length, y along depth, z along height.
SX = 0.2
SY = 0.1
SZ = 0.05

# Grid: 10 columns (i) x 10 rows (j).
COLS = 10
ROWS = 10


def row(i: int, j: int) -> tuple[float, float, float,
                                 float, float, float,
                                 float, float, float]:
    # Half-brick stagger every other row so the pattern reads as a brick
    # wall rather than a grid. Still axis-aligned; rotations stay zero.
    stagger = 0.0 if j % 2 == 0 else SX * 0.5
    x = SX * i + stagger
    y = 0.0
    z = SZ * j
    return (x, y, z, 0.0, 0.0, 0.0, SX, SY, SZ)


rows = [row(i, j) for j in range(ROWS) for i in range(COLS)]
assert len(rows) == 100, f"expected 100 rows, got {len(rows)}"

with open(CSV_PATH, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("x,y,z,rx,ry,rz,sx,sy,sz\n")
    for (x, y, z, rx, ry, rz, sx, sy, sz) in rows:
        fh.write(
            f"{x:.6f},{y:.6f},{z:.6f},"
            f"{rx:.6f},{ry:.6f},{rz:.6f},"
            f"{sx:.6f},{sy:.6f},{sz:.6f}\n"
        )
print(f"  saved -> {CSV_PATH}  ({len(rows)} bricks)")


# ---------------------------------------------------------------------------
# Empty template.blend (no objects, no cameras, no lights).
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
            bpy.data.lights, bpy.data.objects):
    for d in list(blk):
        blk.remove(d)

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"  saved -> {BLEND_PATH}  (empty scene)")
