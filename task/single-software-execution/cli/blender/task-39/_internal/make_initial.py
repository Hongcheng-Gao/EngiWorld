"""Build `init_file/scan.obj` (stdlib) + `init_file/scene.blend` (Blender)
for task KH01 -- Scan -> Retopo -> Unwrap -> Bake -> Render.

Phase 1 (no Blender needed): write a bumpy high-poly scan as OBJ text.

    The scan is a UV-sphere (radius 1.0) tessellated at 48 longitude
    segments x 24 latitude rings, then displaced along the vertex normal
    by a sum-of-sines "noise" to give the surface clear, deterministic
    bumps. This gives roughly 48*23+2 = 1106 vertices and ~2208 faces -
    well within the "few thousand verts" specification for a scanned
    mesh.

Phase 2 (requires Blender): Import `scan.obj` into a fresh scene, name
the imported object `Scan`, place it at the origin, and save
`scene.blend`. No retopo/UV/bake/lights/camera are added here.

Run with Blender so both phases execute:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os
import sys

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
INIT_DIR = os.path.join(TASK_DIR, "init_file")
OBJ_PATH = os.path.join(INIT_DIR, "scan.obj")
BLEND_PATH = os.path.join(INIT_DIR, "scene.blend")

os.makedirs(INIT_DIR, exist_ok=True)

# --- Scan geometry parameters --------------------------------------------
RADIUS      = 1.0
SEGMENTS    = 48    # longitude slices
RINGS       = 24    # latitude rings (inclusive of both poles as single verts)

# Noise amplitude for bumpy surface detail.  Must produce visible surface
# variation along the tangent (R/G) channels of the baked normal map.
NOISE_AMP   = 0.14


def _noise3(x, y, z):
    """Deterministic smooth pseudo-noise in ~[-1, 1] from sines.

    Uses three phase-shifted harmonics over each coordinate so the
    displacement is anisotropic enough to excite both tangent axes of
    the retopo's tangent-space normal bake (keeps std R, std G above
    the evaluator's 0.02 threshold).
    """
    return (
        math.sin(5.0 * x + 1.3) * math.sin(5.0 * y + 2.1) * math.sin(5.0 * z + 0.7)
        + 0.55 * math.sin(9.0 * x - 0.3) * math.sin(9.0 * y + 1.1)
        + 0.45 * math.sin(7.0 * z + 0.9) * math.sin(7.0 * x - 0.4)
        + 0.30 * math.sin(11.0 * y + 2.0) * math.sin(11.0 * z - 0.5)
    )


def build_bumpy_sphere():
    """Return (verts, faces) for a bumpy UV-sphere ellipsoid-ish scan.

    verts : list of (x, y, z) tuples.
    faces : list of 1-based vertex-index tuples (triangles at poles,
            quads in the middle belts).
    """
    verts = []
    # Pole caps as single vertices: north (+Z) and south (-Z).
    verts.append((0.0, 0.0,  RADIUS))   # idx 1
    verts.append((0.0, 0.0, -RADIUS))   # idx 2
    top_idx, bot_idx = 1, 2

    ring_start = 3  # 1-based index of the first non-pole vert
    for r in range(1, RINGS):
        theta = math.pi * r / RINGS       # in (0, pi)
        sin_t, cos_t = math.sin(theta), math.cos(theta)
        for s in range(SEGMENTS):
            phi = 2.0 * math.pi * s / SEGMENTS
            sp, cp = math.sin(phi), math.cos(phi)
            # Base sphere point.
            nx = sin_t * cp
            ny = sin_t * sp
            nz = cos_t
            bx = RADIUS * nx
            by = RADIUS * ny
            bz = RADIUS * nz
            # Displace along normal (= base point / RADIUS) by smooth noise.
            d = NOISE_AMP * _noise3(bx, by, bz)
            x = bx + nx * d
            y = by + ny * d
            z = bz + nz * d
            verts.append((x, y, z))

    # Also displace the pole vertices so the scan has detail at the caps
    # (small outward bump along their normal axis).
    def _displace_pole(idx, normal_z):
        x, y, z = verts[idx - 1]
        d = NOISE_AMP * _noise3(x, y, z)
        verts[idx - 1] = (x, y, z + normal_z * d)

    _displace_pole(top_idx, +1.0)
    _displace_pole(bot_idx, -1.0)

    faces = []
    # Top cap: triangle fan between top pole and first ring.
    for s in range(SEGMENTS):
        a = top_idx
        b = ring_start + s
        c = ring_start + (s + 1) % SEGMENTS
        faces.append((a, b, c))
    # Middle belts: quads between consecutive rings.
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
        fh.write("# scan.obj - high-poly 3D-scanned mesh (KH01)\n")
        fh.write(f"# bumpy UV-sphere, radius={RADIUS}, "
                 f"segments={SEGMENTS}, rings={RINGS}, "
                 f"noise_amp={NOISE_AMP}\n")
        fh.write(f"# vertex count = {len(verts)}, face count = {len(faces)}\n")
        fh.write("o Scan\n")
        for (x, y, z) in verts:
            fh.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for face in faces:
            fh.write("f " + " ".join(str(i) for i in face) + "\n")


def phase1_write_obj():
    verts, faces = build_bumpy_sphere()
    write_obj(OBJ_PATH, verts, faces)

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    bbox_lo = (min(xs), min(ys), min(zs))
    bbox_hi = (max(xs), max(ys), max(zs))
    extents = tuple(hi - lo for hi, lo in zip(bbox_hi, bbox_lo))

    print(f"  wrote {OBJ_PATH}")
    print(f"  verts = {len(verts)}, faces = {len(faces)}")
    print(f"  bbox lo = {bbox_lo}")
    print(f"  bbox hi = {bbox_hi}")
    print(f"  extents = {extents}")


def phase2_build_scene():
    """Import scan.obj into a fresh Blender scene and save scene.blend."""
    import bpy  # type: ignore

    # Fresh file so we start from a known baseline (no default cube, no
    # pre-existing data).
    bpy.ops.wm.read_homefile(use_empty=True)

    # Prefer Blender 4.x's built-in `wm.obj_import`; fall back to the
    # legacy `import_scene.obj` if needed.
    try:
        bpy.ops.wm.obj_import(filepath=OBJ_PATH, forward_axis='Y', up_axis='Z')
    except AttributeError:
        bpy.ops.import_scene.obj(filepath=OBJ_PATH)

    # Identify the imported mesh and rename to "Scan".
    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    if not mesh_objs:
        raise RuntimeError(f"no mesh objects after importing {OBJ_PATH}")
    scan = mesh_objs[0]
    scan.name = "Scan"
    scan.data.name = "ScanMesh"
    scan.location = (0.0, 0.0, 0.0)
    scan.rotation_euler = (0.0, 0.0, 0.0)
    scan.scale = (1.0, 1.0, 1.0)

    print("-" * 60)
    print(f"  Scan verts/faces : {len(scan.data.vertices)}/"
          f"{len(scan.data.polygons)}")
    print(f"  Scene objects     : {[o.name for o in bpy.data.objects]}")
    print("-" * 60)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"  saved -> {BLEND_PATH}")


# --- Main ----------------------------------------------------------------
phase1_write_obj()

try:
    import bpy  # noqa: F401
    _has_bpy = True
except Exception:
    _has_bpy = False

if _has_bpy:
    phase2_build_scene()
else:
    print("  (skipping phase 2: bpy not importable; run under Blender "
          "to build scene.blend)", file=sys.stderr)
