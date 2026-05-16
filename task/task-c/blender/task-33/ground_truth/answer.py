"""Reference solution for task IH01 - OBJ scale-and-axis cleanup.

Reads init_file/scan.obj (mm, Y-up, off-centre), writes
output/clean.obj (m, Z-up, centred) and output/report.json.
"""
import json
import math
import os

import bpy


IN_OBJ  = os.environ.get("SCAN_OBJ", "init_file/scan.obj")
OUT_DIR = os.environ.get("OUT_DIR",  "output")
OUT_OBJ = os.path.join(OUT_DIR, "clean.obj")
OUT_JSON = os.path.join(OUT_DIR, "report.json")

os.makedirs(OUT_DIR, exist_ok=True)

# Start from an empty scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete()
for blk in (bpy.data.meshes, bpy.data.objects):
    for d in list(blk):
        try: blk.remove(d)
        except Exception: pass

# 1. Import the scan, keeping axes as-authored.
bpy.ops.wm.obj_import(filepath=IN_OBJ, forward_axis="Y", up_axis="Z")
obj = [o for o in bpy.data.objects if o.type == "MESH"][0]
bpy.context.view_layer.objects.active = obj

# 2. Apply transforms: scale (mm -> m), rotate X +90 deg, then centre.
obj.scale = (0.001, 0.001, 0.001)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

obj.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

# Compute the bbox centre in world space and translate by its negative.
from mathutils import Vector
corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
lo = Vector((min(c.x for c in corners), min(c.y for c in corners),
             min(c.z for c in corners)))
hi = Vector((max(c.x for c in corners), max(c.y for c in corners),
             max(c.z for c in corners)))
centre = (lo + hi) * 0.5
translation = -centre
obj.location = translation
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# 3. Write clean.obj directly from the transformed mesh so the axis
#    labels in the file match the actual Blender coordinates.
me = obj.data
with open(OUT_OBJ, "w") as f:
    for v in me.vertices:
        f.write(f"v {v.co.x:.6f} {v.co.y:.6f} {v.co.z:.6f}\n")
    for p in me.polygons:
        f.write("f " + " ".join(str(i + 1) for i in p.vertices) + "\n")

# 4. Write report.json.
report = {
    "scale":          0.001,
    "rotation_euler": [math.pi / 2.0, 0.0, 0.0],
    "translation":    [translation.x, translation.y, translation.z],
}
with open(OUT_JSON, "w") as f:
    json.dump(report, f, indent=2)
