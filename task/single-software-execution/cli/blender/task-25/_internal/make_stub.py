"""Create a 512x512 all-0.5-gray PNG at `init_file/stub_gray.png`.

Purpose: the stub is a plain gray image that the evaluator should REJECT
(it has no banding, no brown hue, no dark/light regions). Used by the
pipeline to confirm that the evaluator correctly fails non-wood outputs.

Run:
    blender --background --python _internal/make_stub.py
"""
from __future__ import annotations

import os

import bpy


HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PNG  = os.path.join(TASK_DIR, "init_file", "stub_gray.png")
os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)


img = bpy.data.images.new(
    name="StubGray", width=512, height=512,
    alpha=True, float_buffer=False,
)
img.generated_color = (0.5, 0.5, 0.5, 1.0)
img.pixels = [0.5, 0.5, 0.5, 1.0] * (512 * 512)
img.filepath_raw = OUT_PNG
img.file_format = 'PNG'
img.save()
print(f"  saved -> {OUT_PNG}")
