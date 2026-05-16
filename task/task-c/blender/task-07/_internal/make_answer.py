"""Build `ground_truth/answer.blend` for task BH01.

Opens `init_file/template.blend`, decodes `init_file/height.png` using only
the Python stdlib (`zlib` + `struct`), builds a 64x64 heightmap mesh named
`Terrain`, and saves the result.

Mesh construction rules (matching the prompt):
  - 1 vertex per pixel: `(x, y, pixel_value / 255 * 0.5)` in object space.
  - Faces connect adjacent 2x2 pixel neighborhoods, left as quads.
  - Object `Terrain` sits at world origin.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os
import struct
import zlib

import bpy


HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
TEMPLATE    = os.path.join(TASK_DIR, "init_file", "template.blend")
PNG_PATH    = os.path.join(TASK_DIR, "init_file", "height.png")
OUT_BLEND   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")

Z_SCALE     = 0.5
OBJ_NAME    = "Terrain"

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)


# ---------------------------------------------------------------------------
# Minimal PNG decoder for 8-bit grayscale (color_type=0) with filters 0..4.
# This is sufficient for files we generated in make_initial.py.
# ---------------------------------------------------------------------------
def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_grayscale_png(path: str) -> tuple[int, int, list[list[int]]]:
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG file"
    i = 8
    width = height = bit_depth = color_type = 0
    idat = bytearray()
    while i < len(data):
        (length,) = struct.unpack(">I", data[i:i + 4])
        tag = data[i + 4:i + 8]
        chunk = data[i + 8:i + 8 + length]
        i += 8 + length + 4  # skip CRC
        if tag == b"IHDR":
            (width, height, bit_depth, color_type, _, _, _) = struct.unpack(
                ">IIBBBBB", chunk)
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            break
    assert bit_depth == 8 and color_type == 0, (
        f"expected 8-bit grayscale PNG (bit_depth=8, color_type=0); "
        f"got bit_depth={bit_depth}, color_type={color_type}")

    raw = zlib.decompress(bytes(idat))
    bpp = 1  # bytes per pixel for 8-bit grayscale
    stride = width * bpp
    pixels = []
    prev = bytearray(stride)
    p = 0
    for _ in range(height):
        filt = raw[p]; p += 1
        scan = bytearray(raw[p:p + stride]); p += stride
        if filt == 0:
            row = scan
        elif filt == 1:  # Sub
            row = bytearray(stride)
            for x in range(stride):
                left = row[x - bpp] if x >= bpp else 0
                row[x] = (scan[x] + left) & 0xFF
        elif filt == 2:  # Up
            row = bytearray(stride)
            for x in range(stride):
                row[x] = (scan[x] + prev[x]) & 0xFF
        elif filt == 3:  # Average
            row = bytearray(stride)
            for x in range(stride):
                left = row[x - bpp] if x >= bpp else 0
                row[x] = (scan[x] + ((left + prev[x]) >> 1)) & 0xFF
        elif filt == 4:  # Paeth
            row = bytearray(stride)
            for x in range(stride):
                left = row[x - bpp] if x >= bpp else 0
                up = prev[x]
                ul = prev[x - bpp] if x >= bpp else 0
                row[x] = (scan[x] + _paeth(left, up, ul)) & 0xFF
        else:
            raise ValueError(f"unsupported PNG filter {filt}")
        pixels.append([row[x] for x in range(width)])
        prev = row
    return width, height, pixels


# ---------------------------------------------------------------------------
# Build the terrain mesh
# ---------------------------------------------------------------------------
w, h, pixels = read_grayscale_png(PNG_PATH)
assert w == h, f"expected square PNG, got {w}x{h}"
N = w
print(f"  read {PNG_PATH}: {N}x{N}, max pixel = "
      f"{max(max(r) for r in pixels)}")

bpy.ops.wm.open_mainfile(filepath=TEMPLATE)

# Build verts (N*N) and quad faces ((N-1)*(N-1)).
verts = []
for y in range(N):
    for x in range(N):
        z = pixels[y][x] / 255.0 * Z_SCALE
        verts.append((float(x), float(y), z))

faces = []
for y in range(N - 1):
    for x in range(N - 1):
        i00 = y * N + x
        i10 = y * N + (x + 1)
        i11 = (y + 1) * N + (x + 1)
        i01 = (y + 1) * N + x
        faces.append((i00, i10, i11, i01))

me = bpy.data.meshes.new(OBJ_NAME + "Mesh")
me.from_pydata(verts, [], faces)
me.update()

obj = bpy.data.objects.new(OBJ_NAME, me)
obj.location = (0.0, 0.0, 0.0)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.update()

print(f"  mesh: verts={len(me.vertices)}, edges={len(me.edges)}, "
      f"faces={len(me.polygons)}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"  saved -> {OUT_BLEND}")
