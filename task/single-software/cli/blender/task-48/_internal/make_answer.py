"""Build `ground_truth/answer.blend` for task LH04.

Opens init_file/scene.blend, purges orphan materials & images, and saves
to ground_truth/answer.blend.

The init datablocks are kept alive only by `use_fake_user = True`; their
`users` count is 1 purely from the fake-user flag. The canonical answer:
for every material / image, inspect its real-user count (`users` minus
the fake-user sentinel) and remove it if nothing real is linking to it.
In practice: strip fake-user, then remove anything at users==0.

Run:
    blender --background --python _internal/make_answer.py
"""
from __future__ import annotations

import os

import bpy

HERE       = os.path.dirname(os.path.abspath(__file__))
TASK_DIR   = os.path.dirname(HERE)
INPUT_PATH = os.path.join(TASK_DIR, "init_file", "scene.blend")
OUT_PATH   = os.path.join(TASK_DIR, "ground_truth", "answer.blend")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=INPUT_PATH)
print(f"  after open: materials={len(bpy.data.materials)}, "
      f"images={len(bpy.data.images)}")


def purge_orphans(collection):
    """Strip fake-user flag, then repeatedly remove any zero-user IDs.

    `users` counts the fake-user sentinel, so we clear `use_fake_user`
    first to reveal the true user count. Then remove anything with no
    real users. Repeat -- removing a material may drop an image's user
    count and free more IDs.
    """
    for d in collection:
        d.use_fake_user = False
    removed = 0
    while True:
        victims = [d for d in collection
                   if d.users == 0 and not d.use_fake_user]
        if not victims:
            break
        for d in victims:
            collection.remove(d)
            removed += 1
    return removed

n_mat_removed = purge_orphans(bpy.data.materials)
n_img_removed = purge_orphans(bpy.data.images)

print(f"  purged materials : {n_mat_removed}")
print(f"  purged images    : {n_img_removed}")
print(f"  materials left   : {len(bpy.data.materials)}")
print(f"  images left      : {len(bpy.data.images)}")
print(f"  material names   : {[m.name for m in bpy.data.materials]}")
print(f"  image names      : {[i.name for i in bpy.data.images]}")

bpy.ops.wm.save_as_mainfile(filepath=OUT_PATH)
print(f"  saved -> {OUT_PATH}")
