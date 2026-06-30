from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BLEND_PATH = "/home/user/Desktop/answer.blend"
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")


def _inspect(blend_path, obj_name):
    import bmesh
    import bpy
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
    if obj_name not in bpy.data.objects:
        return {"object_exists": False, "mesh_count": len(mesh_objs)}
    obj = bpy.data.objects[obj_name]
    if obj.type != "MESH":
        return {"object_exists": False, "mesh_count": len(mesh_objs)}
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    loose_edges = sum(1 for e in bm.edges if not e.link_faces)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    bbox_dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    signed_vol = bm.calc_volume(signed=True)
    unsigned_vol = bm.calc_volume(signed=False)
    bm.free()
    return {
        "object_exists": True,
        "mesh_count": len(mesh_objs),
        "location": tuple(obj.location),
        "verts": len(me.vertices),
        "edges": len(me.edges),
        "faces": len(me.polygons),
        "non_man": non_man,
        "loose_verts": loose_verts,
        "loose_edges": loose_edges,
        "bbox_dims": bbox_dims,
        "signed_vol": signed_vol,
        "unsigned_vol": unsigned_vol,
    }


def eval_outputs(blend_path, expected=None, postconfig=None):
    import bpy
    init_path = os.path.join(os.path.dirname(__file__), "init_file", "scene.blend")
    if not os.path.isfile(blend_path):
        return False
    init = _inspect(init_path, "Part")
    sub = _inspect(blend_path, "Part")
    if not sub.get("object_exists"):
        return False
    if sub["mesh_count"] != 1:
        return False
    if max(abs(a - b) for a, b in zip(sub["location"], init["location"])) >= 1e-5:
        return False
    if sub["non_man"] != 0 or sub["loose_verts"] != 0 or sub["loose_edges"] != 0:
        return False
    if sub["signed_vol"] <= 0:
        return False
    for i, s in zip(init["bbox_dims"], sub["bbox_dims"]):
        if abs(s - i) / max(abs(i), 1e-9) >= 0.01:
            return False
    init_aabb_vol = init["bbox_dims"][0] * init["bbox_dims"][1] * init["bbox_dims"][2]
    if abs(sub["unsigned_vol"] - init_aabb_vol) / max(init_aabb_vol, 1e-9) >= 0.02:
        return False
    return True


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender() -> bool:
    proc = subprocess.run(
        [BLENDER_PATH, "--background", "--factory-startup", "--python", __file__],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return proc.returncode == 0


def main():
    passed = eval_outputs(BLEND_PATH) if _have_bpy() else _run_via_blender()
    print("True" if passed else "False")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
