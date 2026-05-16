"""Reference solution for task IM02 — STL for 3D Print."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/scene.blend")
OUT   = "output/part.stl"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

obj = bpy.data.objects["Part"]
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

bpy.ops.wm.stl_export(
    filepath=OUT,
    ascii_format=False,
    forward_axis="Y",
    up_axis="Z",
    global_scale=1000.0,
    apply_modifiers=True,
    export_selected_objects=True,
)
