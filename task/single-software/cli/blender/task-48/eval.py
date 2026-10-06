from __future__ import annotations

import argparse
import os
import subprocess
import sys


AUTO_IMAGE_NAMES = {"Render Result", "Viewer Node"}
BLEND_PATH = "/home/user/Desktop/answer.blend"
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")


def _run_eval(blend_path):
    import bpy

    if not os.path.isfile(blend_path):
        return False
    try:
        bpy.ops.wm.open_mainfile(filepath=blend_path)
    except Exception:
        return False

    cube = bpy.data.objects.get("Cube")
    if cube is None or cube.type != "MESH":
        return False
    if len(cube.data.materials) < 1 or cube.data.materials[0] is None or cube.data.materials[0].name != "Mat_InUse":
        return False
    if bpy.data.materials.get("Mat_InUse") is None:
        return False
    if bpy.data.images.get("Img_InUse") is None:
        return False
    if any(m.name.startswith("Mat_Orphan_") for m in bpy.data.materials):
        return False
    if any(i.name.startswith("Img_Orphan_") for i in bpy.data.images):
        return False
    if len(bpy.data.materials) != 1:
        return False
    user_images = [i for i in bpy.data.images if i.name not in AUTO_IMAGE_NAMES]
    return len(user_images) == 1


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
