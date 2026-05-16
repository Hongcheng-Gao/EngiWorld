"""Build `init_file/scene.blend` for task EH02 - FK/IK Switch via Driver.

Creates a scene with:
  - Armature object `Rig` at origin with 3 connected bones
    `Upper -> Lower -> Tip` along +Z, each length 1 BU.
  - Empty object `IKTarget` at (1, 0, 2.5) - offset off-axis so FK and IK
    tip positions will differ noticeably.
  - Custom property `ik_blend` on the Rig object (armature), float in [0, 1],
    default 0.0.
  - Plus a camera + light for visual inspection.

No IK constraint is wired yet and no driver exists; the testee is expected
to add those.

Run:
    blender --background --python _internal/make_initial.py
"""
from __future__ import annotations

import os

import bpy

HERE     = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.dirname(HERE)
OUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)


BONE_ENDPOINTS = [
    ("Upper", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("Lower", (0.0, 0.0, 1.0), (0.0, 0.0, 2.0)),
    ("Tip",   (0.0, 0.0, 2.0), (0.0, 0.0, 3.0)),
]


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


def build_rig():
    arm_data = bpy.data.armatures.new("RigData")
    rig      = bpy.data.objects.new("Rig", arm_data)
    bpy.context.collection.objects.link(rig)

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
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
    return rig


def build_ik_target():
    empty = bpy.data.objects.new("IKTarget", None)  # None -> EMPTY
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.3
    empty.location = (1.0, 0.0, 2.5)
    bpy.context.collection.objects.link(empty)
    return empty


def add_ik_blend_custom_prop(rig):
    rig["ik_blend"] = 0.0
    # In Blender 4.x use id_properties_ui to set UI range/default.
    try:
        rig.id_properties_ui("ik_blend").update(
            min=0.0, max=1.0,
            soft_min=0.0, soft_max=1.0,
            default=0.0,
            description="FK/IK blend (0 = FK, 1 = IK)",
        )
    except Exception as ex:
        # Fallback for older Blender: RNA UI dict.
        print(f"  id_properties_ui not available ({ex}); "
              "using _RNA_UI fallback")
        ui = rig.get("_RNA_UI")
        if ui is None:
            rig["_RNA_UI"] = {}
            ui = rig["_RNA_UI"]
        ui["ik_blend"] = {
            "min": 0.0, "max": 1.0,
            "soft_min": 0.0, "soft_max": 1.0,
            "default": 0.0,
            "description": "FK/IK blend (0 = FK, 1 = IK)",
        }


clean_scene()

# Camera
cam_data = bpy.data.cameras.new("Camera")
cam      = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
cam.location       = (7.36, -6.93, 4.96)
cam.rotation_euler = (1.1093, 0.0, 0.8149)

# Light
light_data = bpy.data.lights.new("Light", type="POINT")
light      = bpy.data.objects.new("Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (4.08, 1.0, 5.9)

rig          = build_rig()
target_empty = build_ik_target()
add_ik_blend_custom_prop(rig)

# Diagnostics
print("  Initial scene objects:")
for o in bpy.data.objects:
    print(f"    {o.name}  type={o.type}  loc={tuple(o.location)}")
print("  Rig bones:")
for b in rig.data.bones:
    parent_name = b.parent.name if b.parent else None
    print(f"    {b.name} parent={parent_name} "
          f"head={tuple(b.head_local)} tail={tuple(b.tail_local)}")
print(f"  Rig['ik_blend'] = {rig['ik_blend']}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
