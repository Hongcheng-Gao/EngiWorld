"""Build `ground_truth/answer.blend` for task JH01 — Library link + override.

Steps:
  1. Record SHA256 of `init_file/lib/characters.blend` before touching it.
  2. Open `init_file/scene.blend`.
  3. Link the `Hero` collection from `init_file/lib/characters.blend`
     using `bpy.data.libraries.load(link=True)`. Instance it into the
     scene by linking the collection's datablock into the active scene.
  4. Use `collection.override_hierarchy_create(scene, view_layer,
     reference=...)` to create a library override: a new local Hero
     collection whose objects override the linked ones.
  5. Create a new local material `HeroMaterial_Override` with a red
     Principled BSDF Base Color (0.9, 0.1, 0.1, 1.0).
  6. Assign the new material to slot 0 of the override HeroMesh's mesh
     data. The linked lib material remains untouched.
  7. Save `ground_truth/answer.blend`.
  8. Re-hash `init_file/lib/characters.blend` and assert it is unchanged.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import hashlib
import os
import sys

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INIT_DIR   = os.path.join(TASK_DIR, "init_file")
LIB_PATH   = os.path.abspath(os.path.join(INIT_DIR, "lib", "characters.blend"))
SCENE_PATH = os.path.abspath(os.path.join(INIT_DIR, "scene.blend"))
OUT_DIR    = os.path.join(TASK_DIR, "ground_truth")
OUT_PATH   = os.path.abspath(os.path.join(OUT_DIR, "answer.blend"))
os.makedirs(OUT_DIR, exist_ok=True)


def sha256_of(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# ---------------------------------------------------------------------------
# Snapshot the lib hash before doing anything with Blender.
# ---------------------------------------------------------------------------
lib_sha_before = sha256_of(LIB_PATH)
print(f"  lib sha256 before : {lib_sha_before}")

# ---------------------------------------------------------------------------
# Open the empty scene.
# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=SCENE_PATH)
scene      = bpy.context.scene
view_layer = bpy.context.view_layer

# ---------------------------------------------------------------------------
# Link the Hero collection from the library.
# ---------------------------------------------------------------------------
with bpy.data.libraries.load(LIB_PATH, link=True) as (src, dst):
    assert "Hero" in src.collections, (
        f"'Hero' collection not found in lib; have {list(src.collections)}")
    dst.collections = ["Hero"]

linked_hero = None
for c in bpy.data.collections:
    if c.name == "Hero" and c.library is not None:
        linked_hero = c
        break
assert linked_hero is not None, "Linked 'Hero' collection not in bpy.data"
print(f"  linked collection : {linked_hero.name} "
      f"(library={linked_hero.library.filepath!r})")

# Link the collection into the scene so it's actually referenced.
scene.collection.children.link(linked_hero)

# ---------------------------------------------------------------------------
# Override the Hero collection hierarchy. This creates local datablocks
# that override the linked ones.
# ---------------------------------------------------------------------------
override_hero = linked_hero.override_hierarchy_create(
    scene=scene,
    view_layer=view_layer,
    reference=None,
    do_fully_editable=True,
)
assert override_hero is not None, "override_hierarchy_create returned None"
assert override_hero.override_library is not None, (
    "override hero has no override_library")
assert override_hero.library is None, (
    f"override_hero unexpectedly has library={override_hero.library!r}")
print(f"  override coll     : {override_hero.name}  "
      f"(override_library.reference="
      f"{override_hero.override_library.reference.name!r})")

# The override now replaces the linked collection in the scene, but Blender
# may keep the linked collection linked as a child of the scene. Unlink the
# pure-linked one so the scene only shows the override (tidy; optional).
if linked_hero.name in scene.collection.children:
    scene.collection.children.unlink(linked_hero)

# ---------------------------------------------------------------------------
# Find the override HeroMesh object.
# ---------------------------------------------------------------------------
override_mesh_obj = None
for obj in override_hero.all_objects:
    if (obj.library is None and obj.override_library is not None
            and obj.type == "MESH"):
        override_mesh_obj = obj
        break
assert override_mesh_obj is not None, (
    f"Could not find overridden mesh object in {override_hero.name}; "
    f"children: {[(o.name, o.library, o.override_library) for o in override_hero.all_objects]}")
print(f"  override mesh obj : {override_mesh_obj.name}  "
      f"(override_library.reference="
      f"{override_mesh_obj.override_library.reference.name!r})")

# ---------------------------------------------------------------------------
# Create new local red material + assign to slot 0 of the override mesh.
# The mesh datablock on the override object is still LINKED (from the lib);
# assigning via the object's material_slots (which uses object-level slot
# overrides) lets us change the material without touching the linked mesh.
# ---------------------------------------------------------------------------
new_mat = bpy.data.materials.new("HeroMaterial_Override")
new_mat.use_nodes = True
nt = new_mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
n_bsdf.inputs["Base Color"].default_value = (0.9, 0.1, 0.1, 1.0)
nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
assert new_mat.library is None, "new material unexpectedly linked"
print(f"  new material      : {new_mat.name}  "
      f"(library={new_mat.library})")

# Set the material on the object's slot 0 with link='OBJECT' so the
# assignment lives on the object (overrideable property) rather than the
# linked mesh datablock.
assert len(override_mesh_obj.material_slots) >= 1, (
    f"override mesh has no slots; mesh.materials="
    f"{list(override_mesh_obj.data.materials)}")
override_mesh_obj.material_slots[0].link = 'OBJECT'
override_mesh_obj.material_slots[0].material = new_mat

# Verify.
assigned = override_mesh_obj.material_slots[0].material
print(f"  slot[0].link      : {override_mesh_obj.material_slots[0].link}")
print(f"  slot[0].material  : {assigned.name if assigned else None} "
      f"(library={assigned.library if assigned else None})")

bpy.context.view_layer.update()

# ---------------------------------------------------------------------------
# Save answer.blend.
# ---------------------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")

# ---------------------------------------------------------------------------
# Re-hash the lib and assert it is unchanged.
# ---------------------------------------------------------------------------
lib_sha_after = sha256_of(LIB_PATH)
print(f"  lib sha256 after  : {lib_sha_after}")
if lib_sha_after != lib_sha_before:
    print("ERROR: library file was mutated by the link/override operation!",
          file=sys.stderr)
    print(f"       before = {lib_sha_before}", file=sys.stderr)
    print(f"       after  = {lib_sha_after}",  file=sys.stderr)
    sys.exit(1)
print("  lib byte-identical: OK")
