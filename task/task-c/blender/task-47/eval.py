from __future__ import annotations

import os
import subprocess
import tempfile


BLEND_PATH = "/home/user/Desktop/answer.blend"
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")
TOL = 1e-3


def _full_update():
    import bpy
    scn = bpy.context.scene
    bpy.context.view_layer.update()
    scn.frame_set(scn.frame_current)


def _find_y_driver(obj):
    ad = obj.animation_data
    if ad is None:
        return None
    for fc in ad.drivers:
        if fc.data_path == "location" and fc.array_index == 1:
            return fc
    return None


def _check_driver_paths(fc):
    invalid_paths = []
    try:
        for v in fc.driver.variables:
            for t in v.targets:
                dp = getattr(t, "data_path", "")
                if dp and t.id is not None:
                    try:
                        t.id.path_resolve(dp)
                    except Exception as ex:
                        invalid_paths.append(f"{v.name}:{dp} ({ex})")
    except Exception as ex:
        invalid_paths.append(f"(traversal error: {ex})")
    return invalid_paths


def _run_eval(blend_path: str) -> bool:
    import bpy

    if not os.path.isfile(blend_path):
        return False

    try:
        bpy.ops.wm.open_mainfile(filepath=blend_path)
    except Exception:
        return False

    source = bpy.data.objects.get("Source")
    anchor = bpy.data.objects.get("Anchor")
    driven = bpy.data.objects.get("Driven")
    if any(obj is None or obj.type != "MESH" for obj in (source, anchor, driven)):
        return False

    fc = _find_y_driver(driven)
    if fc is None:
        return False

    if _check_driver_paths(fc):
        return False

    if not bool(getattr(fc.driver, "is_valid", True)):
        return False

    scn = bpy.context.scene

    scn.frame_set(1)
    _full_update()
    if abs(driven.location.y - (source.location.x - anchor.location.z)) >= TOL:
        return False

    source.location.x = 5.0
    _full_update()
    if abs(driven.location.y - 4.0) >= TOL:
        return False

    anchor.location.z = 2.0
    _full_update()
    if abs(driven.location.y - 3.0) >= TOL:
        return False

    return True


def _write_result(result_file: str | None, passed: bool):
    print("True" if passed else "False")


def _run_in_blender(blend_path: str, result_file: str | None) -> bool:
    passed = _run_eval(blend_path)
    _write_result(result_file, passed)
    return passed


def _run_via_blender(blend_path: str) -> bool:
    cmd = [
        BLENDER_PATH,
        "--background",
        "--factory-startup",
        "--python",
        __file__,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return proc.returncode == 0


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def main() -> int:
    passed = _run_in_blender(BLEND_PATH, None) if _have_bpy() else _run_via_blender(BLEND_PATH)
    print("True" if passed else "False")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
