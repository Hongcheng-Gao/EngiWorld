import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,0.5),
    scale=(50.0,50.0,0.5))
base = bpy.context.object
base.name = "WaferMap_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(36):
    row, column = divmod(index, 6)
    x_pos = (column-(6-1)/2)*4.5
    y_pos = (row-(6-1)/2)*4.5
    bpy.ops.mesh.primitive_cube_add(scale=(2.0,2.0,0.3), location=(x_pos,y_pos,2.0))
    bpy.context.object.name = "Dies_{index:03d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "WaferMap"
scene["feature_type"] = "dies"
scene["feature_count"] = 36
output = Path(__file__).resolve().with_name("WaferMap.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
