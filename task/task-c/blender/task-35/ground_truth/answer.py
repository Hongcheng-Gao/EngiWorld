"""Reference solution for task IH03 - USD preview surface export."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/scene.blend")
OUT   = "output/scene.usda"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.usd_export(
    filepath=OUT,
    selected_objects_only=False,
    export_materials=True,
    export_mesh_colors=False,
    generate_preview_surface=True,
)
# Writes ASCII USD at output/scene.usda with UsdPreviewSurface shaders.
