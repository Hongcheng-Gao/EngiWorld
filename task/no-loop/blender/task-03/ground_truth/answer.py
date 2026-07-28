import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.5),
    scale=(15.0,15.0,1.5))
base = bpy.context.object
base.name = "TSVArray_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(25):
    row, column = divmod(index, 5)
    x_pos = (column-(5-1)/2)*4.5
    y_pos = (row-(5-1)/2)*4.5
    bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=4.0, location=(x_pos,y_pos,4.0))
    bpy.context.object.name = "Vias_{index:03d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "TSVArray"
scene["feature_type"] = "vias"
scene["feature_count"] = 25
output = Path(__file__).resolve().with_name("TSVArray.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
