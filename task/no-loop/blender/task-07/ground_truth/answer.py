import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.0),
    scale=(60.0,60.0,1.0))
base = bpy.context.object
base.name = "FOUP_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(10):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=45, depth=0.8,
        location=(0,0,4.0+index*3.0))
    bpy.context.object.name = f"Wafer_{index:02d}"
scene = bpy.context.scene
scene["semiconductor_asset"] = "FOUP"
scene["feature_type"] = "wafers"
scene["feature_count"] = 10
output = Path(__file__).resolve().with_name("FOUP.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
