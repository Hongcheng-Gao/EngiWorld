import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.0),
    scale=(30.0,20.0,1.0))
base = bpy.context.object
base.name = "ProbeArray_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(20):
    row, column = divmod(index, 4)
    x_pos = (column-(4-1)/2)*4.5
    y_pos = (row-(4-1)/2)*4.5
    bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=4.0, location=(x_pos,y_pos,3.0))
    bpy.context.object.name = "Probes_{index:03d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "ProbeArray"
scene["feature_type"] = "probes"
scene["feature_count"] = 20
output = Path(__file__).resolve().with_name("ProbeArray.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
