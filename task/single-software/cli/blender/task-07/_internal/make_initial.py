"""Build `init_file/height.png` and `init_file/template.blend` for task BH01.

- `height.png`: a 64x64 8-bit grayscale PNG with a deterministic smooth
  pattern (sum of two sinusoids + a radial bump), written via stdlib
  `zlib` + `struct` so no external image libraries are required.
- `template.blend`: an empty Blender scene (no mesh objects, no camera,
  no light) — serves as the starting point for the testee's script.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os
import struct
import zlib

import bpy


HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
PNG_PATH    = os.path.join(TASK_DIR, "init_file", "height.png")
BLEND_PATH  = os.path.join(TASK_DIR, "init_file", "template.blend")
N           = 64  # grid resolution

os.makedirs(os.path.dirname(PNG_PATH), exist_ok=True)


# ---------------------------------------------------------------------------
# PNG writer (8-bit grayscale, no filter, one pass)
# ---------------------------------------------------------------------------
def _png_chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def write_grayscale_png(path: str, pixels: list[list[int]]) -> None:
    """Write an 8-bit grayscale PNG. `pixels[y][x]` is an int in [0, 255]."""
    h = len(pixels)
    w = len(pixels[0]) if h else 0
    # IHDR: width, height, bit_depth=8, color_type=0 (grayscale),
    #       compression=0, filter=0, interlace=0.
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    # Scanlines: filter byte 0 + row bytes.
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        raw.extend(bytes(row))
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(_png_chunk(b"IHDR", ihdr))
        fh.write(_png_chunk(b"IDAT", idat))
        fh.write(_png_chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Deterministic height field in [0, 255]
# ---------------------------------------------------------------------------
def make_height_pixels(n: int) -> list[list[int]]:
    pixels = []
    cx = (n - 1) / 2.0
    cy = (n - 1) / 2.0
    for y in range(n):
        row = []
        for x in range(n):
            # Two-axis sinusoid + radial bump, normalized to [0, 1].
            s = 0.5 + 0.25 * math.sin(x * math.pi / 8.0)
            s += 0.15 * math.cos(y * math.pi / 6.0)
            r = math.hypot(x - cx, y - cy) / max(cx, cy)
            s += 0.20 * max(0.0, 1.0 - r)
            s = max(0.0, min(1.0, s))
            row.append(int(round(s * 255)))
        pixels.append(row)
    return pixels


pixels = make_height_pixels(N)
write_grayscale_png(PNG_PATH, pixels)
print(f"  saved -> {PNG_PATH}  ({N}x{N} grayscale)")
print(f"    min pixel = {min(min(r) for r in pixels)}, "
      f"max pixel = {max(max(r) for r in pixels)}")


# ---------------------------------------------------------------------------
# Empty template.blend (no objects, no cameras, no lights)
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
# Make absolutely sure nothing lingers from factory defaults.
for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
            bpy.data.lights, bpy.data.objects):
    for d in list(blk):
        blk.remove(d)

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print(f"  saved -> {BLEND_PATH}  (empty scene)")
