import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,0.75),
    scale=(17.5,17.5,0.75))
base = bpy.context.object
base.name = "FlipChip_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(49):
    row, column = divmod(index, 7)
    x_pos = (column-(7-1)/2)*4.5
    y_pos = (row-(7-1)/2)*4.5
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(x_pos,y_pos,2.5))
    bpy.context.object.name = "Bumps_{index:03d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "FlipChip"
scene["feature_type"] = "bumps"
scene["feature_count"] = 49
output = Path(__file__).resolve().with_name("FlipChip.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
