"""Reference solution for task IH02 - glTF roundtrip with PBR."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/ch.blend")
OUT_GLB    = "output/character.glb"
OUT_VERIFY = "output/verify.blend"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)

# Export GLB.
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format="GLB",
    export_apply=True,
    export_materials="EXPORT",
)

# Fresh scene, then re-import to verify.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=OUT_GLB)
bpy.ops.wm.save_as_mainfile(filepath=OUT_VERIFY)
