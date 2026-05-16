"""Diagnostic script for task KH04 - Broken Scene Repair.

Opens a .blend and prints a JSON report of all issues detected.  The
agent is expected to run this, read the JSON, fix everything, and
re-run it to confirm the scene is clean.

Usage (standalone):
    blender --background --python _internal/inspect.py -- --blend <path.blend>

Usage (with already-open file):
    blender --background --python _internal/inspect.py
"""
from __future__ import annotations

import json
import os
import sys


def main():
    import bpy

    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]

    if argv and argv[0] == "--blend":
        bpy.ops.wm.open_mainfile(filepath=argv[1])

    issues = []

    # 1. Hidden meshes
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.hide_viewport:
            issues.append({
                "type": "hidden",
                "object": o.name,
                "fix": "set hide_viewport=False",
            })

    # 2. Broken image paths (filepath set but file not on disk and not packed)
    _BUILTIN_IMGS = {"Render Result", "Viewer Node"}
    for img in bpy.data.images:
        if img.name in _BUILTIN_IMGS:
            continue
        abs_path = bpy.path.abspath(img.filepath) if img.filepath else ""
        if (img.filepath
                and not os.path.isfile(abs_path)
                and not img.packed_file):
            issues.append({
                "type": "broken_image",
                "image": img.name,
                "path": img.filepath,
                "fix": "point filepath at a valid file and reload (or pack)",
            })

    # 3. Offset transforms (only flag MainMesh if it has a non-zero origin)
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        if o.name != "MainMesh":
            continue
        if (abs(o.location.x) > 0.01
                or abs(o.location.y) > 0.01
                or abs(o.location.z) > 0.01):
            issues.append({
                "type": "offset_origin",
                "object": o.name,
                "location": [o.location.x, o.location.y, o.location.z],
                "fix": "reset location to (0, 0, 0)",
            })

    # 4. Materials with use_nodes = False
    for m in bpy.data.materials:
        if not m.use_nodes:
            issues.append({
                "type": "no_nodes",
                "material": m.name,
                "fix": "set use_nodes=True and build a Principled BSDF graph",
            })

    # 5. Extra / redundant collections
    for c in bpy.data.collections:
        is_extra_name = c.name.startswith("Extra")
        is_empty = (len(c.objects) == 0 and len(c.children) == 0)
        if is_extra_name or (c.name != "Collection" and is_empty):
            issues.append({
                "type": "extra_collection",
                "name": c.name,
                "fix": "unlink from scene root and remove collection",
            })

    report = {"issue_count": len(issues), "issues": issues}
    print("INSPECT_REPORT:" + json.dumps(report))


if __name__ == "__main__":
    main()
