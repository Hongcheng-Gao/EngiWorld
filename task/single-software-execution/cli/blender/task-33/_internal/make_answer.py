"""Build `ground_truth/output/clean.obj` + `ground_truth/output/report.json`
for task IH01 - OBJ scale-and-axis cleanup.

Opens `init_file/scan.obj` with Blender 4.1's OBJ importer (`bpy.ops.wm.
obj_import`), applies the cleanup transforms in order:

    1. scale     = 0.001                        (mm -> m)
    2. rotation  = (pi/2, 0, 0) XYZ Euler       (Y-up scan -> Z-up pipeline)
    3. translate = -(bbox_centre_after_scale_rotate)  (centre at origin)

After each step the transform is baked into the mesh with
`bpy.ops.object.transform_apply`, so the evaluator's OBJ-parse sees the
literal post-transform vertex coordinates.

The cleaned mesh is then written by *reading back* the Blender mesh
vertices and writing vertex / face lines to the OBJ directly - this
deliberately bypasses Blender's OBJ exporter (which re-flips axes based
on up/forward flags and would defeat the "Z is vertical" check).

Finally a companion `report.json` is emitted with the transform
parameters, and the evaluator is invoked as a self-check.

Run:
    /zfspool/zangyihe/blender-4.1.0-linux-x64/blender --background \\
        --python _internal/make_answer.py
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy


HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_OBJ  = os.path.join(TASK_DIR, "init_file",    "scan.obj")
OUT_DIR    = os.path.join(TASK_DIR, "ground_truth", "output")
OUT_OBJ    = os.path.join(OUT_DIR,  "clean.obj")
OUT_REPORT = os.path.join(OUT_DIR,  "report.json")
OUT_BLEND  = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
REF_PY     = os.path.join(TASK_DIR, "ground_truth", "answer.py")

os.makedirs(OUT_DIR, exist_ok=True)


# ----------------------------------------------------------------------
# Scene helpers.
# ----------------------------------------------------------------------
def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.images, bpy.data.materials,
                bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def _object_bbox_world(obj):
    """Return (lo, hi, centre) of `obj.bound_box` in WORLD space.

    `obj.bound_box` is 8 corners in LOCAL space. We transform each corner
    by `obj.matrix_world` (which is identity after a full transform_apply)
    to get world-space corners; we use that for robustness to still-
    pending location / rotation.
    """
    from mathutils import Vector
    corners = [obj.matrix_world @ Vector(obj.bound_box[i]) for i in range(8)]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    ce = (0.5 * (lo[0] + hi[0]),
          0.5 * (lo[1] + hi[1]),
          0.5 * (lo[2] + hi[2]))
    return lo, hi, ce


# ----------------------------------------------------------------------
# The actual cleanup pipeline.
# ----------------------------------------------------------------------
def do_cleanup(input_obj, out_obj, out_report):
    clean_scene()

    # 1) Import the scan. Use `forward_axis='Y'` and `up_axis='Z'` so the
    #    importer does NOT remap axes - the numeric coordinates from the
    #    file land in Blender as-is. (The default importer remaps.)
    bpy.ops.wm.obj_import(
        filepath=input_obj,
        forward_axis="Y",
        up_axis="Z",
    )

    # Find the newly-imported mesh object.
    mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
    if not mesh_objs:
        raise RuntimeError(f"no mesh imported from {input_obj}")
    obj = mesh_objs[0]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # --- 2) Scale 0.001 (mm -> m) ---------------------------------------
    obj.scale = (0.001, 0.001, 0.001)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # --- 3) Rotate +pi/2 about X (Y-up scan -> Z-up pipeline) -----------
    obj.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)

    # --- 4) Centre at origin --------------------------------------------
    # After scale+rotate, compute the bbox centre in WORLD space (equal
    # to local space since transform has been baked and location = 0).
    _, _, ce = _object_bbox_world(obj)
    translation = (-ce[0], -ce[1], -ce[2])
    obj.location = translation
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    # --- 5) Sanity dump --------------------------------------------------
    lo, hi, ce_after = _object_bbox_world(obj)
    extents = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
    print(f"  after cleanup:")
    print(f"    vertices    = {len(obj.data.vertices)}")
    print(f"    faces       = {len(obj.data.polygons)}")
    print(f"    bbox lo (m) = {lo}")
    print(f"    bbox hi (m) = {hi}")
    print(f"    extents (m) = {extents}")
    print(f"    centre  (m) = {ce_after}")
    print(f"    translation applied = {translation}")

    # --- 6) Write `clean.obj` BY HAND, bypassing Blender's axis-flip. ---
    #     We dump the mesh's literal vertex coordinates so the evaluator
    #     sees Z as the vertical axis (which it is, in Blender's space,
    #     after our rotation).
    mesh = obj.data
    with open(out_obj, "w", encoding="utf-8") as fh:
        fh.write("# clean.obj - transformed by task IH01 ground-truth\n")
        fh.write("# scale=0.001, rotation_euler=(pi/2, 0, 0), "
                 f"translation={translation}\n")
        fh.write(f"# vertex count = {len(mesh.vertices)}, "
                 f"face count = {len(mesh.polygons)}\n")
        fh.write("o scan_clean\n")
        for v in mesh.vertices:
            fh.write(f"v {v.co.x:.6f} {v.co.y:.6f} {v.co.z:.6f}\n")
        for p in mesh.polygons:
            # OBJ face indices are 1-based.
            idx = [str(i + 1) for i in p.vertices]
            fh.write("f " + " ".join(idx) + "\n")
    print(f"  wrote {out_obj}")

    # --- 7) Write `report.json` -----------------------------------------
    report = {
        "scale":          0.001,
        "rotation_euler": [math.pi / 2.0, 0.0, 0.0],
        "translation":    [float(translation[0]),
                           float(translation[1]),
                           float(translation[2])],
    }
    with open(out_report, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(f"  wrote {out_report}")
    print(f"  report = {report}")

    return obj, report


obj, report = do_cleanup(INPUT_OBJ, OUT_OBJ, OUT_REPORT)


# Save the scene as a .blend for inspection convenience.
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, copy=True)
print(f"  saved -> {OUT_BLEND}")


# ----------------------------------------------------------------------
# Reference solution the testee could plausibly submit.
# ----------------------------------------------------------------------
REF = '''\
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
        f.write(f"v {v.co.x:.6f} {v.co.y:.6f} {v.co.z:.6f}\\n")
    for p in me.polygons:
        f.write("f " + " ".join(str(i + 1) for i in p.vertices) + "\\n")

# 4. Write report.json.
report = {
    "scale":          0.001,
    "rotation_euler": [math.pi / 2.0, 0.0, 0.0],
    "translation":    [translation.x, translation.y, translation.z],
}
with open(OUT_JSON, "w") as f:
    json.dump(report, f, indent=2)
'''
with open(REF_PY, "w", encoding="utf-8") as fh:
    fh.write(REF)
print(f"  saved -> {REF_PY}")


# ----------------------------------------------------------------------
# Self-check: run the evaluator against the fresh ground-truth outputs.
# ----------------------------------------------------------------------
sys.dont_write_bytecode = True
sys.path.insert(0, TASK_DIR)
try:
    import eval as eval_mod  # noqa: E402
    card = eval_mod._run_eval(OUT_OBJ, OUT_REPORT)
    print(card.render())
except Exception as exc:
    print(f"  [warn] eval self-check failed: {exc}")
