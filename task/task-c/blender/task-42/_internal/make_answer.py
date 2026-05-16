"""Build `ground_truth/answer.blend` for task KH04 - Broken Scene Repair.

Opens `init_file/scene.blend` (which contains 5 common issues) and fixes
all of them:

  1. `HiddenMesh.show_viewport = True`.
  2. The broken image's filepath is repointed to `//textures/good_texture.png`
     (copied next to the answer blend), reloaded, and packed.
  3. `MainMesh.location` is reset to (0, 0, 0).
  4. `Mat_NoNodes.use_nodes = True` with a minimal Principled BSDF +
     Material Output graph.
  5. `Extra_Collection` is unlinked from the scene root and removed.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os
import shutil

import bpy

HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
INIT_BLEND  = os.path.join(TASK_DIR, "init_file", "scene.blend")
INIT_TEXDIR = os.path.join(TASK_DIR, "init_file", "textures")

OUT_DIR     = os.path.join(TASK_DIR, "ground_truth")
OUT_TEXDIR  = os.path.join(OUT_DIR, "textures")
OUT_PATH    = os.path.join(OUT_DIR, "answer.blend")

os.makedirs(OUT_TEXDIR, exist_ok=True)

# --- Copy textures alongside the answer so `//textures/good_texture.png`
# resolves on disk (even before we pack the image).
for fn in os.listdir(INIT_TEXDIR):
    src = os.path.join(INIT_TEXDIR, fn)
    dst = os.path.join(OUT_TEXDIR, fn)
    if os.path.isfile(src):
        shutil.copyfile(src, dst)
        print(f"  copied {src} -> {dst}")

# --- Open the broken scene ----------------------------------------------
bpy.ops.wm.open_mainfile(filepath=INIT_BLEND)

print("  BEFORE repair:")
for o in bpy.data.objects:
    if o.type == 'MESH':
        print(f"    mesh obj {o.name!r}  loc={tuple(round(v,3) for v in o.location)}  "
              f"hide_viewport={o.hide_viewport}")
for m in bpy.data.materials:
    print(f"    material {m.name!r}  use_nodes={m.use_nodes}")
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    print(f"    image {im.name!r}  filepath={im.filepath!r}")
print(f"    collections = {[c.name for c in bpy.data.collections]}")

# Save-as first so `//` anchors at ground_truth/ for the repaired image path.
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH, relative_remap=False)

# --- Fix 1: HiddenMesh.hide_viewport = False ----------------------------
hidden = bpy.data.objects.get("HiddenMesh")
if hidden is not None:
    hidden.hide_viewport = False
    print(f"  [fix 1] HiddenMesh.hide_viewport -> {hidden.hide_viewport}")

# --- Fix 2: Broken image -> //textures/good_texture.png, reload, pack ---
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    # Only fix images whose current path is missing/broken.
    abs_path = bpy.path.abspath(im.filepath) if im.filepath else ""
    if im.filepath and not os.path.isfile(abs_path) and not im.packed_file:
        new_path = "//textures/good_texture.png"
        im.filepath     = new_path
        im.filepath_raw = new_path
        im.source       = 'FILE'
        try:
            im.reload()
        except Exception as ex:
            print(f"    [fix 2] WARN reload({im.name}): {ex}")
        try:
            im.pack()
        except Exception as ex:
            print(f"    [fix 2] WARN pack({im.name}): {ex}")
        print(f"  [fix 2] image {im.name!r} repointed to {im.filepath!r}  "
              f"packed={bool(im.packed_file)}  size={tuple(im.size)}")

# --- Fix 3: MainMesh.location = (0, 0, 0) -------------------------------
main_mesh = bpy.data.objects.get("MainMesh")
if main_mesh is not None:
    main_mesh.location = (0.0, 0.0, 0.0)
    print(f"  [fix 3] MainMesh.location -> {tuple(main_mesh.location)}")

# --- Fix 4: Mat_NoNodes.use_nodes = True with Principled BSDF -----------
mat_no_nodes = bpy.data.materials.get("Mat_NoNodes")
if mat_no_nodes is not None:
    mat_no_nodes.use_nodes = True
    nt = mat_no_nodes.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    n_out  = nt.nodes.new("ShaderNodeOutputMaterial")
    n_bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    n_out.location  = (300.0, 0.0)
    n_bsdf.location = (  0.0, 0.0)
    # Preserve the legacy diffuse color as the Base Color.
    try:
        n_bsdf.inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1.0)
    except Exception:
        pass
    nt.links.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
    print(f"  [fix 4] Mat_NoNodes.use_nodes -> {mat_no_nodes.use_nodes}  "
          f"nodes={[n.name for n in nt.nodes]}")

# --- Fix 5: Remove Extra_Collection -------------------------------------
extra = bpy.data.collections.get("Extra_Collection")
if extra is not None:
    # Unlink from every scene root first (Blender may refuse to remove a
    # linked collection otherwise).
    for scene in bpy.data.scenes:
        if extra.name in scene.collection.children:
            try:
                scene.collection.children.unlink(extra)
            except Exception as ex:
                print(f"    [fix 5] WARN unlink from {scene.name}: {ex}")
    try:
        bpy.data.collections.remove(extra)
        print(f"  [fix 5] removed collection 'Extra_Collection'")
    except Exception as ex:
        print(f"    [fix 5] WARN remove: {ex}")

# --- Audit after repair --------------------------------------------------
print("-" * 60)
print("  AFTER repair:")
for o in bpy.data.objects:
    if o.type == 'MESH':
        print(f"    mesh obj {o.name!r}  loc={tuple(round(v,3) for v in o.location)}  "
              f"hide_viewport={o.hide_viewport}")
for m in bpy.data.materials:
    node_types = ([n.type for n in m.node_tree.nodes]
                  if m.use_nodes and m.node_tree else [])
    print(f"    material {m.name!r}  use_nodes={m.use_nodes}  "
          f"nodes={node_types}")
for im in bpy.data.images:
    if im.name in {"Render Result", "Viewer Node"}:
        continue
    resolved = bpy.path.abspath(im.filepath) if im.filepath else ""
    exists = os.path.isfile(resolved) if resolved else False
    print(f"    image {im.name!r}  filepath={im.filepath!r}  "
          f"resolved_exists={exists}  packed={bool(im.packed_file)}  "
          f"size={tuple(im.size)}")
print(f"    collections = {[c.name for c in bpy.data.collections]}")

# --- Final save ----------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
