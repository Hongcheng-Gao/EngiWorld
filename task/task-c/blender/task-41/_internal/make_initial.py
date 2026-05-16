"""Build initial assets for task KH03 - BVH -> IK switch -> bake -> Alembic.

Creates:
  - `init_file/walk.bvh`       : a 30-frame BVH motion capture file in
                                 pure ASCII (no bpy dependency). Hips
                                 translate ~0.5 BU along +Y over the clip
                                 and the left leg knee bends smoothly so
                                 there is real IK fodder post-retarget.
                                 Joint names use a `mixamorig_` prefix so
                                 they differ from Character bone names.
  - `init_file/character.blend`: a Character armature with bones
                                   Hip -> UpperLeg.L -> LowerLeg.L -> Foot.L
                                 plus a simple low-poly `Body` mesh parented
                                 to the rig with automatic weights.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import math
import os

import bpy

HERE      = os.path.dirname(os.path.abspath(__file__))
TASK_DIR  = os.path.dirname(HERE)
INIT_DIR  = os.path.join(TASK_DIR, "init_file")
BVH_PATH  = os.path.join(INIT_DIR, "walk.bvh")
CHAR_PATH = os.path.join(INIT_DIR, "character.blend")
os.makedirs(INIT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1: write walk.bvh (pure text)
# ---------------------------------------------------------------------------
def write_bvh(path):
    """Write a 30-frame BVH describing Hip -> LeftUpLeg -> LeftLeg.

    * Hip Y-position ramps from 0 -> 0.5 over the clip (gives hip travel).
    * Knee (LeftLeg) rotates around X to provide IK-relevant bend.
    """
    n_frames    = 30
    frame_time  = 0.033333
    y_total     = 0.55         # slightly over 0.5 so eval has margin.
    knee_amp_deg = 30.0         # degrees, oscillating bend.

    lines = []
    lines += [
        "HIERARCHY",
        "ROOT mixamorig_Hips",
        "{",
        "\tOFFSET 0.00 0.00 0.00",
        "\tCHANNELS 6 Xposition Yposition Zposition "
        "Zrotation Xrotation Yrotation",
        "\tJOINT mixamorig_LeftUpLeg",
        "\t{",
        "\t\tOFFSET 0.00 -1.00 0.00",
        "\t\tCHANNELS 3 Zrotation Xrotation Yrotation",
        "\t\tJOINT mixamorig_LeftLeg",
        "\t\t{",
        "\t\t\tOFFSET 0.00 -1.00 0.00",
        "\t\t\tCHANNELS 3 Zrotation Xrotation Yrotation",
        "\t\t\tEnd Site",
        "\t\t\t{",
        "\t\t\t\tOFFSET 0.00 -0.50 0.00",
        "\t\t\t}",
        "\t\t}",
        "\t}",
        "}",
        "MOTION",
        f"Frames: {n_frames}",
        f"Frame Time: {frame_time:.6f}",
    ]

    # Per-frame channel floats (12 per frame):
    #   Hips:       X_pos Y_pos Z_pos Z_rot X_rot Y_rot
    #   LeftUpLeg:                    Z_rot X_rot Y_rot
    #   LeftLeg:                      Z_rot X_rot Y_rot
    for f in range(n_frames):
        t = f / max(n_frames - 1, 1)            # 0..1
        # Hip Y translation ramps smoothly 0 -> y_total.
        hy = y_total * t
        # Subtle side-to-side X sway so retarget has richer signal.
        hx = 0.05 * math.sin(2.0 * math.pi * t)
        hz = 0.0
        # Hip rotation: small yaw wobble so root has rotation fodder too.
        hrz = 0.0
        hrx = 0.0
        hry = 3.0 * math.sin(2.0 * math.pi * t)

        # Upper leg: mild forward swing (+X rotation).
        ul_rz = 0.0
        ul_rx = 10.0 * math.sin(2.0 * math.pi * t)
        ul_ry = 0.0

        # Lower leg (knee): bend oscillates. Always positive so knee
        # doesn't hyperextend.
        ll_rz = 0.0
        ll_rx = knee_amp_deg * (0.5 - 0.5 * math.cos(2.0 * math.pi * t))
        ll_ry = 0.0

        vals = (
            hx, hy, hz,
            hrz, hrx, hry,
            ul_rz, ul_rx, ul_ry,
            ll_rz, ll_rx, ll_ry,
        )
        lines.append(" ".join(f"{v:.6f}" for v in vals))

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


# Character bone layout: runs along +Z upward is typical, but we want the
# leg to hang downward to match the BVH (legs go -Y in BVH source, which
# after the importer's axis remap becomes roughly -Z in Blender world).
# For simplicity and to mirror the BVH structure cleanly we build the
# chain going downward along -Z, starting from Hip at the origin.
BONE_LAYOUT = [
    # (name, head, tail)
    ("Hip",         (0.0, 0.0, 2.0),   (0.0, 0.0, 1.5)),
    ("UpperLeg.L",  (0.0, 0.0, 1.5),   (0.0, 0.0, 0.8)),
    ("LowerLeg.L",  (0.0, 0.0, 0.8),   (0.0, 0.0, 0.2)),
    ("Foot.L",      (0.0, 0.0, 0.2),   (0.0, 0.2, 0.0)),
]


def build_character():
    arm_data = bpy.data.armatures.new("CharacterData")
    char     = bpy.data.objects.new("Character", arm_data)
    bpy.context.collection.objects.link(char)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = char
    char.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    created = []
    for name, head, tail in BONE_LAYOUT:
        eb = arm_data.edit_bones.new(name)
        eb.head = head
        eb.tail = tail
        created.append(eb)
    # Parent chain.
    for i in range(1, len(created)):
        created[i].parent      = created[i - 1]
        created[i].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")

    # Set XYZ rotation mode on every pose bone so retarget's
    # rotation_euler channels are unambiguous.
    for name, *_ in BONE_LAYOUT:
        pb = char.pose.bones.get(name)
        if pb is not None:
            pb.rotation_mode = "XYZ"

    return char


def build_body_mesh(rig):
    """A simple low-poly body: a stretched cube parented to the rig.

    The mesh is deliberately positioned so its vertical extent roughly
    matches the bone chain Hip (Z=2.0) down to Foot (Z=0.0). Automatic
    weights will bind the top half to Hip/UpperLeg and the bottom half
    to LowerLeg/Foot.
    """
    # Low-poly block: 8 verts cube, scaled to roughly 0.3 x 0.3 x 2.0.
    verts = []
    faces = []
    # Build a vertical stack of cubes (actually 4 segments) so it deforms
    # when the chain bends. 5 rings of 4 verts each -> 5*4 = 20 verts.
    z_positions = [0.0, 0.5, 1.0, 1.5, 2.0]
    for z in z_positions:
        verts += [
            (-0.15, -0.15, z),
            ( 0.15, -0.15, z),
            ( 0.15,  0.15, z),
            (-0.15,  0.15, z),
        ]
    # Side quads connecting consecutive rings.
    for ring in range(len(z_positions) - 1):
        b = ring * 4
        n = b + 4
        faces += [
            (b + 0, b + 1, n + 1, n + 0),
            (b + 1, b + 2, n + 2, n + 1),
            (b + 2, b + 3, n + 3, n + 2),
            (b + 3, b + 0, n + 0, n + 3),
        ]
    # Cap top and bottom.
    faces.append((0, 3, 2, 1))
    t = (len(z_positions) - 1) * 4
    faces.append((t + 0, t + 1, t + 2, t + 3))

    mesh = bpy.data.meshes.new("BodyMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)

    body = bpy.data.objects.new("Body", mesh)
    bpy.context.collection.objects.link(body)

    # Parent with automatic weights so the mesh deforms with the bones.
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        auto_ok = True
    except Exception as exc:
        print(f"  [warn] ARMATURE_AUTO failed ({exc!r}); "
              f"falling back to ARMATURE_NAME")
        auto_ok = False

    if not auto_ok:
        # Fallback: parent with empty groups then assign weights manually
        # so each ring's verts fully follow the nearest bone.
        bpy.ops.object.parent_set(type="ARMATURE_NAME")
        # Explicit vertex groups: assign by Z range.
        #   z>=1.5 -> Hip
        #   1.0..<1.5 -> UpperLeg.L
        #   0.5..<1.0 -> LowerLeg.L
        #   <0.5 -> Foot.L
        for vg in body.vertex_groups:
            pass
        mapping = (
            ("Hip",         lambda z: z >= 1.5),
            ("UpperLeg.L",  lambda z: 1.0 <= z < 1.5),
            ("LowerLeg.L",  lambda z: 0.5 <= z < 1.0),
            ("Foot.L",      lambda z: z < 0.5),
        )
        for grp_name, cond in mapping:
            vg = body.vertex_groups.get(grp_name)
            if vg is None:
                vg = body.vertex_groups.new(name=grp_name)
            idxs = [i for i, v in enumerate(mesh.vertices) if cond(v.co.z)]
            if idxs:
                vg.add(idxs, 1.0, "REPLACE")

    bpy.ops.object.select_all(action="DESELECT")
    return body


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
write_bvh(BVH_PATH)
print(f"  wrote BVH -> {BVH_PATH}")

clean_scene()

# Lightweight scene furniture (camera/light are for visual inspection;
# they are not load-bearing for the eval).
cam_data = bpy.data.cameras.new("Camera")
cam      = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location       = (6.0, -6.0, 4.0)
cam.rotation_euler = (1.1093, 0.0, 0.8149)

light_data = bpy.data.lights.new("Light", type="POINT")
light      = bpy.data.objects.new("Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (4.0, 1.0, 5.9)

char = build_character()
body = build_body_mesh(char)

# Scene frame range 1..30 matches the BVH clip.
scene = bpy.context.scene
scene.frame_start   = 1
scene.frame_end     = 30
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
print(f"  Body vertex groups: {[vg.name for vg in body.vertex_groups]}")
print(f"  Body modifier stack: "
      f"{[(m.name, m.type) for m in body.modifiers]}")
print(f"  Character animation_data = {char.animation_data}")

bpy.ops.wm.save_as_mainfile(filepath=CHAR_PATH)
print(f"  saved -> {CHAR_PATH}")
