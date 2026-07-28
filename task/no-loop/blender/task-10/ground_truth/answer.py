import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.5),
    scale=(30.0,15.0,1.5))
base = bpy.context.object
base.name = "SensorChip_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(6):
    bpy.ops.mesh.primitive_cube_add(
        location=(0,0,3.5+index*0.8), scale=(10,6,0.3))
    bpy.context.object.name = f"Channels_{index:02d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "SensorChip"
scene["feature_type"] = "channels"
scene["feature_count"] = 6
output = Path(__file__).resolve().with_name("SensorChip.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
