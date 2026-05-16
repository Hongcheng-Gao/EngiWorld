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
