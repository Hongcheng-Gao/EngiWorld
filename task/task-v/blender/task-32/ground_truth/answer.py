"""Reference solution for task IM04 — OBJ with material library."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/scene.blend")
OUT   = "output/scene.obj"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.obj_export(
    filepath=OUT,
    export_materials=True,
    export_triangulated_mesh=False,
    up_axis="Z",
    forward_axis="Y",
)
# Produces both output/scene.obj AND output/scene.mtl.
