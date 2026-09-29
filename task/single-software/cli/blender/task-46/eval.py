from __future__ import annotations

import argparse
import os
import subprocess
import sys


FACE_MIN = 100
FACE_MAX = 5000
BLEND_PATH = "/home/user/Desktop/answer.blend"
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")


def _run_eval(blend_path):
    import bmesh
    import bpy

    if not os.path.isfile(blend_path):
        return False
    try:
        bpy.ops.wm.open_mainfile(filepath=blend_path)
    except Exception:
        return False

    body = bpy.data.objects.get("Body")
    cutter = bpy.data.objects.get("Cutter")
    guide = bpy.data.objects.get("Guide")
    if any(obj is None or obj.type != "MESH" for obj in (body, cutter, guide)):
        return False
    if not guide.hide_viewport or not guide.hide_render:
        return False
    mods = list(body.modifiers)
    if len(mods) != 2:
        return False
    if mods[0].type != "SUBSURF" or mods[1].type != "BOOLEAN":
        return False
    if not (mods[0].show_viewport and mods[0].show_render and mods[1].show_viewport and mods[1].show_render):
        return False
    if int(getattr(mods[0], "levels", 0)) < 1:
        return False
    if mods[1].operation != "DIFFERENCE" or mods[1].object is None or mods[1].object.name != "Cutter":
        return False

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    body_eval = body.evaluated_get(depsgraph)
    eval_mesh = body_eval.to_mesh()
    face_count = len(eval_mesh.polygons)
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)
    loose_edges = sum(1 for e in bm.edges if not e.link_faces)
    bm.free()
    body_eval.to_mesh_clear()

    return (
        FACE_MIN <= face_count <= FACE_MAX
        and non_man == 0
        and loose_verts == 0
        and loose_edges == 0
    )


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(blend_path: str) -> bool:
    proc = subprocess.run(
        [
            BLENDER_PATH,
            "--background",
            "--factory-startup",
            "--python",
            __file__,
            "--",
            "--blend",
            blend_path,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return proc.returncode == 0


def eval_outputs(blend_path, expected=None, postconfig=None):
    return _run_eval(blend_path) if _have_bpy() else _run_via_blender(blend_path)


def _parse_blend_path() -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--blend", default=BLEND_PATH)
    script_args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_known_args(script_args)[0].blend


def main():
    passed = eval_outputs(_parse_blend_path())
    print("True" if passed else "False")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
