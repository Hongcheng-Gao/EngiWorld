"""Reference solution for task IM03 - Alembic cache export."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/scene.blend")
OUT   = "output/animated.abc"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.alembic_export(
    filepath=OUT,
    start=1,
    end=30,
    selected=False,
    uvs=True,
    normals=True,
    vcolors=False,
    face_sets=False,
    flatten=False,
    apply_subdiv=False,
    packuv=True,
)
