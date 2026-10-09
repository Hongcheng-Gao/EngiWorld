"""Build `init_file/stub_black.png` — a 1024x1024 all-black PNG used as a
negative-control input for the evaluator. The evaluator must fail on it.

Run:
    blender --background --python _internal/make_stub_black.py
"""
from __future__ import annotations

import os

import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "stub_black.png")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

img = bpy.data.images.new(
    name="StubBlack", width=1024, height=1024,
    alpha=True, float_buffer=False,
)
img.generated_color = (0.0, 0.0, 0.0, 1.0)
img.pixels = [0.0, 0.0, 0.0, 1.0] * (1024 * 1024)
img.colorspace_settings.name = 'Non-Color'
img.filepath_raw = OUT_PATH
img.file_format = 'PNG'
img.save()
print(f"  stub written -> {OUT_PATH}")
