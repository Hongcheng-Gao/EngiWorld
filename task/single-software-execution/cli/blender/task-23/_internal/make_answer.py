"""Build `ground_truth/answer.blend` and `output/drape.abc` for FH01.

Opens `init_file/scene.blend` (a Cloth plane above a Sphere with Cloth +
Collision modifiers), bakes the cloth simulation over frames 1..60,
exports the deformed Cloth mesh as an Alembic cache, and then freezes
the frame-60 draped geometry into the Cloth mesh data so the evaluator
can query it without needing to re-run the sim.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy


HERE        = os.path.dirname(os.path.abspath(__file__))
TASK_DIR    = os.path.dirname(HERE)
INPUT_PATH  = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_BLEND   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
OUT_ABC     = os.path.join(TASK_DIR, "ground_truth", "output", "drape.abc")
REF_PY      = os.path.join(TASK_DIR, "ground_truth", "answer.py")

os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
os.makedirs(os.path.dirname(OUT_ABC),   exist_ok=True)


FRAME_START = 1
FRAME_END   = 60


def bake_cloth(scene, cloth):
    """Bake the cloth point cache for frames 1..60."""
    mod = cloth.modifiers.get("Cloth")
    if mod is None:
        raise RuntimeError("Cloth object has no Cloth modifier")
    pc = mod.point_cache
    pc.frame_start = FRAME_START
    pc.frame_end   = FRAME_END

    # Make Cloth the active + selected object so ptcache ops target it.
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = cloth
    cloth.select_set(True)

    # Clear any stale cache and bake.
    try:
        bpy.ops.ptcache.free_bake_all()
    except Exception as exc:
        print(f"  (ptcache.free_bake_all raised {exc!r}, continuing)")

    try:
        with bpy.context.temp_override(scene=scene, point_cache=pc):
            bpy.ops.ptcache.bake_all(bake=True)
        print("  ptcache.bake_all: succeeded")
    except Exception as exc:
        print(f"  ptcache.bake_all raised {exc!r}; will rely on frame-step")

    # Also step through frames - this forces the modifier stack to
    # evaluate and populate any in-memory cache even if bake_all is a
    # no-op in headless mode.
    center_zs = []
    for f in range(FRAME_START, FRAME_END + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        obj_eval = cloth.evaluated_get(deps)
        me = obj_eval.to_mesh()
        mw = obj_eval.matrix_world
        if len(me.vertices) > 0:
            zs = [(mw @ v.co).z for v in me.vertices]
            center_zs.append(sum(zs) / len(zs))
        else:
            center_zs.append(mw.translation.z)
        obj_eval.to_mesh_clear()
    print(f"  frame-step sim scan: f1 mean_z={center_zs[0]:.3f}, "
          f"f{FRAME_END} mean_z={center_zs[-1]:.3f}")
    return center_zs


def export_alembic(scene, cloth, out_path):
    """Export the Cloth object as an Alembic cache over frames 1..60."""
    # Select only the Cloth so `selected=True` picks just it.
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = cloth
    cloth.select_set(True)
    # Ensure frame cursor at start for deterministic export start.
    scene.frame_set(FRAME_START)
    bpy.context.view_layer.update()

    bpy.ops.wm.alembic_export(
        filepath=out_path,
        start=FRAME_START,
        end=FRAME_END,
        selected=True,
        visible_objects_only=False,
        uvs=True,
        normals=True,
        vcolors=False,
        face_sets=False,
        flatten=False,
        apply_subdiv=False,
        packuv=True,
    )


def freeze_frame_60(scene, cloth):
    """At frame 60, replace cloth.data with the evaluated (draped) mesh.

    This bakes the simulation result into plain geometry, so the
    evaluator can query frame-60 cloth state without re-baking the sim
    (cloth point caches are not embedded in saved .blend files).
    """
    scene.frame_set(FRAME_END)
    bpy.context.view_layer.update()

    deps = bpy.context.evaluated_depsgraph_get()
    obj_eval = cloth.evaluated_get(deps)
    me_eval = obj_eval.to_mesh()

    # Copy the evaluated mesh into a fresh mesh datablock, then swap it
    # onto the Cloth object and remove the Cloth modifier (so the base
    # mesh is already in the draped state).
    new_mesh = bpy.data.meshes.new_from_object(obj_eval, preserve_all_data_layers=False)
    obj_eval.to_mesh_clear()

    old_mesh = cloth.data
    cloth.data = new_mesh

    # Remove the cloth modifier entirely - its effect is now baked.
    mod = cloth.modifiers.get("Cloth")
    if mod is not None:
        cloth.modifiers.remove(mod)

    # Remove the old mesh datablock if no longer in use.
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)

    # Diagnostics: compute world-space centroid and vertex-radius stats.
    mw = cloth.matrix_world
    verts = [mw @ v.co for v in cloth.data.vertices]
    mean_z = sum(v.z for v in verts) / len(verts)
    radii = [((v.x) ** 2 + (v.y) ** 2 + (v.z) ** 2) ** 0.5 for v in verts]
    min_r = min(radii)
    max_r = max(radii)
    below_0_95 = sum(1 for r in radii if r < 0.95)
    below_0_93 = sum(1 for r in radii if r < 0.93)
    print(f"  frozen frame-{FRAME_END} stats: verts={len(cloth.data.vertices)}, "
          f"mean_z={mean_z:.4f}, min_r={min_r:.4f}, max_r={max_r:.4f}")
    print(f"     verts with |pos| < 0.95: {below_0_95}/{len(verts)}")
    print(f"     verts with |pos| < 0.93: {below_0_93}/{len(verts)}")


def main():
    bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end   = FRAME_END
    scene.frame_set(FRAME_START)

    cloth  = bpy.data.objects["Cloth"]
    sphere = bpy.data.objects["Sphere"]
    if sphere.modifiers.get("Collision") is None:
        sphere.modifiers.new("Collision", "COLLISION")

    # 1. Bake + frame-step the simulation.
    bake_cloth(scene, cloth)

    # 2. Export Alembic cache over frames 1..60.
    export_alembic(scene, cloth, OUT_ABC)
    print(f"  exported ABC -> {OUT_ABC}")
    if os.path.isfile(OUT_ABC):
        size = os.path.getsize(OUT_ABC)
        with open(OUT_ABC, "rb") as fh:
            head = fh.read(16)
        print(f"  abc size = {size} bytes, head = {head.hex()}")

    # 3. Freeze frame-60 draped geometry into Cloth.data, remove modifier.
    freeze_frame_60(scene, cloth)

    # 4. Set scene cursor to frame 60 and save.
    scene.frame_set(FRAME_END)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print(f"  saved -> {OUT_BLEND}")

    # 5. Emit reference answer script.
    ref = '''\
"""Reference solution for task FH01 - Cloth Drape Alembic."""
import os
import bpy

INPUT = "init_file/scene.blend"
OUT_ABC = "output/drape.abc"

bpy.ops.wm.open_mainfile(filepath=INPUT)
scene = bpy.context.scene
cloth = bpy.data.objects["Cloth"]
mod = cloth.modifiers.get("Cloth")
pc  = mod.point_cache
pc.frame_start = 1
pc.frame_end   = 60

bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.objects.active = cloth
cloth.select_set(True)

with bpy.context.temp_override(scene=scene, point_cache=pc):
    bpy.ops.ptcache.bake_all(bake=True)

for f in range(1, 61):
    scene.frame_set(f)
    bpy.context.view_layer.update()

os.makedirs(os.path.dirname(OUT_ABC), exist_ok=True)
bpy.ops.wm.alembic_export(
    filepath=OUT_ABC,
    start=1,
    end=60,
    selected=True,
    visible_objects_only=False,
)
'''
    with open(REF_PY, "w", encoding="utf-8") as fh:
        fh.write(ref)
    print(f"  saved -> {REF_PY}")


main()
