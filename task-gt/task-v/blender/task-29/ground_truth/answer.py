"""Reference solution for task IM01 - FBX for Unity."""
import os
import bpy

BLEND = os.environ.get("SCENE_BLEND", "init_file/scene.blend")
OUT   = "output/part.fbx"

bpy.ops.wm.open_mainfile(filepath=BLEND)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.export_scene.fbx(
    filepath=OUT,
    use_selection=False,
    object_types={"MESH", "ARMATURE", "EMPTY"},
    apply_scale_options="FBX_SCALE_UNITS",
    axis_forward="-Z",
    axis_up="Y",
    bake_anim=True,
    bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True,
)
