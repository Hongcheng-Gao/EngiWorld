"""Build `init_file/scan.obj` for task IH01 - OBJ scale-and-axis cleanup.

Emits a scan-like mesh that simulates a 3D-scanner export:
  - Coordinates are in MILLIMETRES (so naked numbers up to ~2000).
  - Y is the "up" / vertical axis (scanner convention); after import to a
    Z-up pipeline this looks lying on its side.
  - The mesh is translated away from the origin by (1200, 300, 500) mm.
  - >= 200 vertices and a valid triangle/face list.

Concretely we generate a UV-sphere of half-axes (800, 1000, 700) mm with
16 longitude segments and 16 latitude rings (2 pole caps + 15 rings ->
16*15+2 = 242 vertices), which gives:
  - bbox in mm: X in [-800, 800], Y in [-1000, 1000], Z in [-700, 700]
    (extents 1600 x 2000 x 1400 mm) BEFORE translation;
  - translated centre (1200, 300, 500) mm: bbox in mm is
    X in [ 400, 2000], Y in [-700, 1300], Z in [-200, 1200].

The longest extent is along Y (2000 mm = 2 m after mm->m), which is the
desired "vertical axis in the scanner-convention data". After the cleanup
(scale 0.001, rotate +pi/2 about X, centre) the longest extent lands on
Z, as the evaluator expects.

Run this script with any Python 3 - it does not require Blender:
    python3 _internal/make_initial.py

(Running it under `blender --background --python` also works; Blender's
Python interpreter is fine.)
"""
from __future__ import annotations

import math
import os


HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_OBJ  = os.path.join(TASK_DIR, "init_file", "scan.obj")

# --- Scan geometry parameters (millimetres) --------------------------------
# Half-axes of an ellipsoid: larger along Y makes Y the vertical axis.
HALF_X = 800.0   # mm
HALF_Y = 1000.0  # mm  <- vertical in scanner-convention (Y-up)
HALF_Z = 700.0   # mm

# Off-centre translation (mm). The evaluator verifies the cleaned mesh
# has bbox centre at the origin; the scanner's centroid being this far
# off is the "not centred" gotcha the agent must fix.
CENTRE = (1200.0, 300.0, 500.0)  # mm, (X, Y, Z)

# UV-sphere tessellation
SEGMENTS = 16   # longitude slices
RINGS    = 16   # latitude rings (inclusive of both poles as single verts)

os.makedirs(os.path.dirname(OUT_OBJ), exist_ok=True)


def _ellipsoid_uv_sphere():
    """Return (verts, faces) for a UV-sphere ellipsoid.

    verts : list of (x, y, z) in mm, already translated by `CENTRE`.
    faces : list of 1-based vertex-index tuples (each a triangle or quad).
    """
    cx, cy, cz = CENTRE
    verts = []
    # Pole caps as single vertices: top (north, +Y) and bottom (south, -Y).
    top_idx    = 1                     # 1-based
    bot_idx    = 2
    verts.append((cx,            cy + HALF_Y, cz))
    verts.append((cx,            cy - HALF_Y, cz))

    # Latitude rings (excluding the two poles).
    # theta is polar angle measured from +Y axis; theta in (0, pi).
    ring_start = 3  # 1-based index of the first non-pole vert
    for r in range(1, RINGS):
        theta = math.pi * r / RINGS                  # (0, pi)
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        for s in range(SEGMENTS):
            phi = 2.0 * math.pi * s / SEGMENTS
            x = HALF_X * sin_t * math.cos(phi)
            z = HALF_Z * sin_t * math.sin(phi)
            y = HALF_Y * cos_t
            verts.append((cx + x, cy + y, cz + z))

    # Faces.
    faces = []
    # Top cap: triangle fan between top_idx and first ring.
    for s in range(SEGMENTS):
        a = top_idx
        b = ring_start + s
        c = ring_start + (s + 1) % SEGMENTS
        faces.append((a, b, c))

    # Middle rings: quads between consecutive latitude rings.
    for r in range(RINGS - 2):
        base0 = ring_start + r * SEGMENTS
        base1 = ring_start + (r + 1) * SEGMENTS
        for s in range(SEGMENTS):
            s1 = (s + 1) % SEGMENTS
            a = base0 + s
            b = base1 + s
            c = base1 + s1
            d = base0 + s1
            faces.append((a, b, c, d))

    # Bottom cap: triangle fan.
    last_ring_start = ring_start + (RINGS - 2) * SEGMENTS
    for s in range(SEGMENTS):
        a = bot_idx
        b = last_ring_start + (s + 1) % SEGMENTS
        c = last_ring_start + s
        faces.append((a, b, c))

    return verts, faces


def write_obj(path, verts, faces):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# scan.obj - raw 3D-scanner output (Y-up, millimetres)\n")
        fh.write(f"# Ellipsoid UV-sphere, half-axes "
                 f"({HALF_X}, {HALF_Y}, {HALF_Z}) mm, "
                 f"centred at {CENTRE} mm\n")
        fh.write(f"# vertex count = {len(verts)}, face count = {len(faces)}\n")
        fh.write("o scan\n")
        for (x, y, z) in verts:
            fh.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for face in faces:
            fh.write("f " + " ".join(str(i) for i in face) + "\n")


def main():
    verts, faces = _ellipsoid_uv_sphere()

    # Sanity: compute bbox of emitted points (mm-space).
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    bbox_lo = (min(xs), min(ys), min(zs))
    bbox_hi = (max(xs), max(ys), max(zs))
    extents = tuple(hi - lo for hi, lo in zip(bbox_hi, bbox_lo))
    centre = tuple(0.5 * (lo + hi) for lo, hi in zip(bbox_lo, bbox_hi))

    write_obj(OUT_OBJ, verts, faces)

    print(f"  wrote {OUT_OBJ}")
    print(f"  verts={len(verts)}, faces={len(faces)}")
    print(f"  bbox lo (mm) = {bbox_lo}")
    print(f"  bbox hi (mm) = {bbox_hi}")
    print(f"  extents (mm) = {extents}   (X, Y, Z)")
    print(f"  bbox centre (mm) = {centre}")
    print(f"  Y-extent ({extents[1]:.0f} mm) is the largest -> Y is the "
          f"'vertical' axis in scan convention.")


if __name__ == "__main__":
    main()
