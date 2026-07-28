import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("DieCollet")
base = Part.makeBox(20, 20, 12.0)
cutter = Part.makeCylinder(4.0, 14.0,
    App.Vector(10.0, 10.0, -1))
base = base.cut(cutter)
features = []
assembly = Part.makeCompound([base] + features) if "DieCollet" == "ChipletInterposer" else base
if "DieCollet" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "DieCollet")
result.Label = "Die pickup collet"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "DieCollet.FCStd"))
Part.export([result], str(output_dir / "DieCollet.step"))
