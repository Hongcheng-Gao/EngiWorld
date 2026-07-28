import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,0.2),
    scale=(25.0,15.0,0.2))
base = bpy.context.object
base.name = "LithographyStack_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(8):
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,0.9+index*0.8), scale=(10,6,0.3))
    bpy.context.object.name = f"Layers_{index:02d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "LithographyStack"
scene["feature_type"] = "layers"
scene["feature_count"] = 8
output = Path(__file__).resolve().with_name("LithographyStack.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
