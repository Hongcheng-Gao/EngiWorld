"""Build initial assets for task EH03 - BVH Retarget + Bake to Action.

Creates:
  - `init_file/walk.bvh`       : a small BVH motion capture file (written
                                 from pure-Python text; no bpy dependency
                                 for this step). 3 joints Hips->Spine->Head
                                 with 60 frames of walking motion (Hips
                                 translates forward along Y and the spine
                                 bounces while the head nods).
  - `init_file/character.blend`: a character armature with bones named
                                 `Root -> Spine -> Head` (note: `Hips`
                                 renamed to `Root` so the name-mapping is
                                 non-trivial but still 1:1).
  - `init_file/scene.blend`    : a copy of character.blend so the eval
                                 harness has a consistent entry point.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os
import shutil

import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
INIT_DIR = os.path.join(TASK_DIR, "init_file")
BVH_PATH = os.path.join(INIT_DIR, "walk.bvh")
CHAR_PATH = os.path.join(INIT_DIR, "character.blend")
SCENE_PATH = os.path.join(INIT_DIR, "scene.blend")
os.makedirs(INIT_DIR, exist_ok=True)


# Character armature bones: different names from the BVH joints so the
# retarget requires an explicit mapping. Bones run +Z.
BONE_ENDPOINTS = [
    ("Root",  (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ("Spine", (0.0, 1.0, 0.0), (0.0, 2.0, 0.0)),
    ("Head",  (0.0, 2.0, 0.0), (0.0, 2.5, 0.0)),
]


# ---------------------------------------------------------------------------
# Step 1: write walk.bvh directly (stdlib text, no bpy needed)
# ---------------------------------------------------------------------------
def write_bvh(path):
    import math

    n_frames    = 60
    frame_time  = 0.033333
    fwd_per_f   = 0.05  # Y translation per frame => 3.0 BU over 60 frames.

    lines = []
    # HIERARCHY: Hips (6ch) -> Spine (3ch) -> Head (3ch) -> End Site.
    lines += [
        "HIERARCHY",
        "ROOT Hips",
        "{",
        "\tOFFSET 0.00 0.00 0.00",
        "\tCHANNELS 6 Xposition Yposition Zposition "
        "Zrotation Xrotation Yrotation",
        "\tJOINT Spine",
        "\t{",
        "\t\tOFFSET 0.00 1.00 0.00",
        "\t\tCHANNELS 3 Zrotation Xrotation Yrotation",
        "\t\tJOINT Head",
        "\t\t{",
        "\t\t\tOFFSET 0.00 1.00 0.00",
        "\t\t\tCHANNELS 3 Zrotation Xrotation Yrotation",
        "\t\t\tEnd Site",
        "\t\t\t{",
        "\t\t\t\tOFFSET 0.00 0.50 0.00",
        "\t\t\t}",
        "\t\t}",
        "\t}",
        "}",
        "MOTION",
        f"Frames: {n_frames}",
        f"Frame Time: {frame_time:.6f}",
    ]

    # Per-frame channel values.
    # Channel order (15 floats / frame):
    #   Hips:  X_pos Y_pos Z_pos    Z_rot X_rot Y_rot
    #   Spine:                     Z_rot X_rot Y_rot
    #   Head:                      Z_rot X_rot Y_rot
    for f in range(n_frames):
        # Forward walk translation. BVH convention is Y-up, forward is +Z
        # (by Blender's BVH importer axis remap). Writing Zposition gives
        # us world-+Y motion in Blender (which is what the eval checks).
        hx, hy, hz = 0.0, 0.0, f * fwd_per_f
        # Root orientation: flat.
        hrz, hrx, hry = 0.0, 0.0, 0.0
        # Spine subtle bounce: small X rotation oscillating.
        bounce = 3.0 * math.sin(2.0 * math.pi * f / 20.0)  # degrees
        srz, srx, sry = 0.0, bounce, 0.0
        # Head subtle nod: small X rotation oscillating.
        nod = 2.0 * math.sin(2.0 * math.pi * f / 30.0)     # degrees
        hdrz, hdrx, hdry = 0.0, nod, 0.0

        vals = (
            hx, hy, hz,
            hrz, hrx, hry,
            srz, srx, sry,
            hdrz, hdrx, hdry,
        )
        lines.append(" ".join(f"{v:.6f}" for v in vals))

    # BVH expects trailing newline.
    text = "\n".join(lines) + "\n"
    with open(path, "w") as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------------------
# Step 2: build character.blend
# ---------------------------------------------------------------------------
def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras,
                bpy.data.lights, bpy.data.armatures, bpy.data.actions,
                bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def build_character():
    arm_data = bpy.data.armatures.new("CharacterData")
    char     = bpy.data.objects.new("Character", arm_data)
    bpy.context.collection.objects.link(char)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = char
    char.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    created = []
    for name, head, tail in BONE_ENDPOINTS:
        eb = arm_data.edit_bones.new(name)
        eb.head = head
        eb.tail = tail
        created.append(eb)
    for i in range(1, len(created)):
        created[i].parent      = created[i - 1]
        created[i].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")

    # Ensure pose bones have XYZ rotation_mode so rotation_euler keyframes
    # are unambiguous after retarget.
    for pb_name in ("Root", "Spine", "Head"):
        char.pose.bones[pb_name].rotation_mode = "XYZ"

    return char


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
write_bvh(BVH_PATH)
print(f"  wrote BVH -> {BVH_PATH}")

clean_scene()

# Camera + light (for visual inspection; not load-bearing).
cam_data = bpy.data.cameras.new("Camera")
cam      = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location       = (7.36, -6.93, 4.96)
cam.rotation_euler = (1.1093, 0.0, 0.8149)

light_data = bpy.data.lights.new("Light", type="POINT")
light      = bpy.data.objects.new("Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (4.08, 1.0, 5.9)

char = build_character()

# Scene frame range 1..60 so eval, make-answer, and the BVH all agree.
scene = bpy.context.scene
scene.frame_start   = 1
scene.frame_end     = 60
scene.frame_current = 1

# Diagnostics.
print("  Initial scene objects:")
for o in bpy.data.objects:
    print(f"    {o.name}  type={o.type}")
print("  Character bones:")
for b in char.data.bones:
    parent = b.parent.name if b.parent else None
    print(f"    {b.name} parent={parent} "
          f"head={tuple(b.head_local)} tail={tuple(b.tail_local)}")
print(f"  Character animation_data = {char.animation_data}")

bpy.ops.wm.save_as_mainfile(filepath=CHAR_PATH)
print(f"  saved -> {CHAR_PATH}")

# Copy character.blend as scene.blend so eval has a consistent entry point.
shutil.copyfile(CHAR_PATH, SCENE_PATH)
print(f"  copied -> {SCENE_PATH}")
