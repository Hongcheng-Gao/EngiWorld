"""Build `ground_truth/answer.blend` for task BH02.

Opens `init_file/template.blend`, parses `init_file/bricks.csv`, creates
one cube per row transformed into position, then joins all cubes into a
single mesh object `Wall` whose per-brick geometry is baked into mesh
coordinates (Wall itself has identity transform).

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import csv
import os

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
TEMPLATE   = os.path.join(TASK_DIR, "init_file", "template.blend")
CSV_PATH   = os.path.join(TASK_DIR, "init_file", "bricks.csv")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")

OBJ_NAME   = "Wall"

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)


def read_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        for r in rdr:
            rows.append((
                float(r["x"]),  float(r["y"]),  float(r["z"]),
                float(r["rx"]), float(r["ry"]), float(r["rz"]),
                float(r["sx"]), float(r["sy"]), float(r["sz"]),
            ))
    return rows


def brick_to_bm(bm, row):
    """Append a size-(sx,sy,sz) cuboid at (x,y,z) rotated (rx,ry,rz) to `bm`.

    Geometry is pushed as a disjoint island — no verts are shared with
    existing geometry. Uses bmesh.ops.create_cube with size=1 (so verts are
    at +/- 0.5), scales to (sx, sy, sz), rotates, then translates.
    """
    x, y, z, rx, ry, rz, sx, sy, sz = row
    # Create a fresh sub-bmesh to build the cube, then push it into `bm`.
    sub = bmesh.new()
    bmesh.ops.create_cube(sub, size=1.0)

    # Scale so local verts occupy [-sx/2, sx/2] x [-sy/2, sy/2] x [-sz/2, sz/2].
    S = Matrix.Diagonal((sx, sy, sz, 1.0))
    R = Euler((rx, ry, rz), "XYZ").to_matrix().to_4x4()
    T = Matrix.Translation((x, y, z))
    M = T @ R @ S
    bmesh.ops.transform(sub, matrix=M, verts=sub.verts)

    # Copy sub-bmesh geometry into bm (new verts + faces, no merging).
    vert_map = {}
    for v in sub.verts:
        nv = bm.verts.new(v.co.copy())
        vert_map[v] = nv
    bm.verts.ensure_lookup_table()
    for f in sub.faces:
        bm.faces.new([vert_map[v] for v in f.verts])

    sub.free()


def main():
    rows = read_csv(CSV_PATH)
    assert len(rows) == 100, f"expected 100 bricks, got {len(rows)}"

    bpy.ops.wm.open_mainfile(filepath=TEMPLATE)

    bm = bmesh.new()
    for r in rows:
        brick_to_bm(bm, r)

    me = bpy.data.meshes.new(OBJ_NAME + "Mesh")
    bm.to_mesh(me)
    bm.free()
    me.update()

    obj = bpy.data.objects.new(OBJ_NAME, me)
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.update()

    print(f"  Wall: verts={len(me.vertices)}, edges={len(me.edges)}, "
          f"faces={len(me.polygons)}")

    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"  saved -> {OUT_BLEND}")


if __name__ == "__main__":
    main()
