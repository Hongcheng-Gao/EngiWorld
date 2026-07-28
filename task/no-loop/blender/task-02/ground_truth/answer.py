import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.0),
    scale=(15.0,10.0,1.0))
base = bpy.context.object
base.name = "FinFETArray_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(12):
    bpy.ops.mesh.primitive_cube_add(
        location=((index-(12-1)/2)*2,0,5.0), scale=(0.3,6,3))
    bpy.context.object.name = f"Fin_{index:02d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "FinFETArray"
scene["feature_type"] = "fins"
scene["feature_count"] = 12
output = Path(__file__).resolve().with_name("FinFETArray.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
