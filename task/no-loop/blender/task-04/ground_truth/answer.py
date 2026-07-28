import bpy
from math import pi, cos, sin
from pathlib import Path

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add(location=(0,0,1.0),
    scale=(20.0,20.0,1.0))
base = bpy.context.object
base.name = "WireBondPackage_Base"
material = bpy.data.materials.new("Silicon")
material.diffuse_color = (0.08,0.18,0.22,1.0)
base.data.materials.append(material)
for index in range(16):
    angle = 2*pi*index/16
    curve = bpy.data.curves.new("BondCurve", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.15
    spline = curve.splines.new("POLY")
    spline.points.add(2)
    for point, co in zip(spline.points, ((8*cos(angle),8*sin(angle),2.0,1),
        (13*cos(angle),13*sin(angle),8.0,1),
        (18*cos(angle),18*sin(angle),2.0,1))):
        point.co = co
    bond = bpy.data.objects.new("Bond_{:02d}".format(index), curve)
    bpy.context.collection.objects.link(bond)
scene = bpy.context.scene
scene["semiconductor_asset"] = "WireBondPackage"
scene["feature_type"] = "bonds"
scene["feature_count"] = 16
output = Path(__file__).resolve().with_name("WireBondPackage.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
