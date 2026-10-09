"""Build `init_file/scene.blend` for task LH05.

Scene:
  - `Rig`: an ARMATURE object with a 4-bone chain. The bones were intended
    to be named `Bone.Root`, `Bone.A`, `Bone.B`, `Bone.Tip` (root-to-tip),
    but the rig was "imported" poorly so every bone was given the same
    base name — Blender auto-numbered them into `Bone`, `Bone.001`,
    `Bone.002`, `Bone.003`. The topology (head/tail positions, parent
    relations) is correct.
  - `Skin`: a MESH object (thin subdivided box along Z) with 4 vertex
    groups named `Bone.Root`, `Bone.A`, `Bone.B`, `Bone.Tip`. Each vertex
    group holds the vertices of one of the four segments along Z. An
    ARMATURE modifier points to `Rig`.

Because the vertex groups reference semantic names the rig doesn't have,
the Armature modifier silently fails to deform those vertices. The testee
must rename the bones along the chain to match the vertex-group names.

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


# Root-to-tip bone chain. Each bone occupies a 1-unit segment along +Z.
# The intended semantic names (in order) — used only on the mesh side.
SEMANTIC_NAMES = ["Bone.Root", "Bone.A", "Bone.B", "Bone.Tip"]

# Head/tail positions for the 4-bone chain.
BONE_ENDPOINTS = [
    ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)),  # Root
    ((0.0, 0.0, 1.0), (0.0, 0.0, 2.0)),  # A
    ((0.0, 0.0, 2.0), (0.0, 0.0, 3.0)),  # B
    ((0.0, 0.0, 3.0), (0.0, 0.0, 4.0)),  # Tip
]


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.curves,
                bpy.data.cameras, bpy.data.lights, bpy.data.objects):
        for d in list(blk):
            try:
                blk.remove(d)
            except Exception:
                pass


def build_rig():
    arm_data = bpy.data.armatures.new("RigData")
    rig      = bpy.data.objects.new("Rig", arm_data)
    bpy.context.collection.objects.link(rig)

    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    created = []
    for (head, tail) in BONE_ENDPOINTS:
        # Name every new bone the same base string; Blender auto-suffixes
        # to `Bone`, `Bone.001`, `Bone.002`, `Bone.003` to keep names
        # unique. This reproduces the "broken import" state.
        eb = arm_data.edit_bones.new("Bone")
        eb.head = head
        eb.tail = tail
        created.append(eb)

    # Parent chain: child.parent = previous, with connected=True so the
    # bones form a single continuous chain.
    for i in range(1, len(created)):
        created[i].parent = created[i - 1]
        created[i].use_connect = True

    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def build_skin(rig):
    # A tall thin box along Z, subdivided into 4 segments so each segment
    # can be assigned to one of the four vertex groups.
    verts = []
    faces = []
    # 5 z-slices, each a 0.4x0.4 square -> 20 verts.
    hx, hy = 0.2, 0.2
    zs = [0.0, 1.0, 2.0, 3.0, 4.0]
    for z in zs:
        verts.append((-hx, -hy, z))
        verts.append(( hx, -hy, z))
        verts.append(( hx,  hy, z))
        verts.append((-hx,  hy, z))
    # Side quads per segment (4 per segment, 16 total).
    for s in range(4):
        a = s * 4
        b = (s + 1) * 4
        faces.append((a + 0, a + 1, b + 1, b + 0))
        faces.append((a + 1, a + 2, b + 2, b + 1))
        faces.append((a + 2, a + 3, b + 3, b + 2))
        faces.append((a + 3, a + 0, b + 0, b + 3))
    # Bottom and top caps.
    faces.append((0, 1, 2, 3)[::-1])          # bottom (facing -Z)
    faces.append((16, 17, 18, 19))            # top (facing +Z)

    me  = bpy.data.meshes.new("SkinMesh")
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new("Skin", me)
    bpy.context.collection.objects.link(obj)

    # Vertex groups named with the SEMANTIC bone names.
    # Segment s contains verts [s*4 .. s*4+3] and [(s+1)*4 .. (s+1)*4+3].
    # Assign each vertex to the group whose segment it belongs to — for
    # the shared slice z=1,2,3 we assign to the lower segment so every
    # vertex gets exactly one group.
    segment_verts = {
        "Bone.Root": list(range(0, 4)),
        "Bone.A":    list(range(4, 8)),
        "Bone.B":    list(range(8, 12)),
        "Bone.Tip":  list(range(12, 20)),  # includes top cap slice
    }
    for name, vids in segment_verts.items():
        vg = obj.vertex_groups.new(name=name)
        vg.add(vids, 1.0, "REPLACE")

    # Armature modifier pointing to Rig, uses vertex groups.
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object           = rig
    mod.use_vertex_groups = True
    mod.use_bone_envelopes = False

    # Parent the mesh to the rig (object parent only; the modifier does
    # the deformation).
    obj.parent = rig

    return obj


clean_scene()
rig  = build_rig()
skin = build_skin(rig)

# Diagnostic dump.
print("  Rig bones (broken/auto-numbered names):")
for b in rig.data.bones:
    parent_name = b.parent.name if b.parent else None
    print(f"    {b.name}  parent={parent_name}  "
          f"head={tuple(b.head_local)} tail={tuple(b.tail_local)}")

print("  Skin vertex groups (semantic names):")
for vg in skin.vertex_groups:
    print(f"    {vg.name}")

print("  Skin modifiers:")
for m in skin.modifiers:
    obj_name = m.object.name if m.object else None
    print(f"    {m.name} ({m.type})  object={obj_name}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
