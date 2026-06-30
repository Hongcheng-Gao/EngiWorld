from __future__ import annotations

import argparse
import os
import subprocess
import sys


EXPECTED_BONE_NAMES = {"Bone.Root", "Bone.A", "Bone.B", "Bone.Tip"}
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

    rig = bpy.data.objects.get("Rig")
    if rig is None or rig.type != "ARMATURE":
        return False
    bones = list(rig.data.bones)
    if len(bones) != 4:
        return False
    bone_names = {b.name for b in bones}
    if bone_names != EXPECTED_BONE_NAMES:
        return False
    by_name = {b.name: b for b in bones}
    if not (by_name["Bone.Root"].parent is None and by_name["Bone.A"].parent and by_name["Bone.A"].parent.name == "Bone.Root" and by_name["Bone.B"].parent and by_name["Bone.B"].parent.name == "Bone.A" and by_name["Bone.Tip"].parent and by_name["Bone.Tip"].parent.name == "Bone.B"):
        return False

    skin = bpy.data.objects.get("Skin")
    if skin is None or skin.type != "MESH":
        return False
    arm_mods = [m for m in skin.modifiers if m.type == "ARMATURE"]
    if len(arm_mods) != 1 or arm_mods[0].object is None or arm_mods[0].object.name != "Rig":
        return False
    vg_names = {vg.name for vg in skin.vertex_groups}
    if vg_names != EXPECTED_BONE_NAMES:
        return False
    return all(name in bone_names for name in vg_names)


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(blend_path: str) -> bool:
    proc = subprocess.run(
        [BLENDER_PATH, "--background", "--factory-startup", "--python", __file__],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return proc.returncode == 0


def eval_outputs(blend_path, expected=None, postconfig=None):
    return _run_eval(blend_path) if _have_bpy() else _run_via_blender(blend_path)


def main():
    passed = eval_outputs(BLEND_PATH)
    print("True" if passed else "False")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
