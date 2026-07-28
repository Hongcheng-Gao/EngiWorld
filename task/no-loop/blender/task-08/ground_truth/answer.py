import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,2.5),
    scale=(50.0,50.0,2.5))
base = bpy.context.object
base.name = "CMPScene_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(14):
    bpy.ops.mesh.primitive_torus_add(major_radius=8+index*2.5,
        minor_radius=0.3, location=(0,0,5.3))
    bpy.context.object.name = f"Groove_{index:02d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "CMPScene"
scene["feature_type"] = "grooves"
scene["feature_count"] = 14
output = Path(__file__).resolve().with_name("CMPScene.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
