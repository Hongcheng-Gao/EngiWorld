import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("PhotodiodeHousing")
base = Part.makeBox(24, 24, 10.0)
cutter = Part.makeCylinder(5.0, 12.0,
    App.Vector(12.0, 12.0, -1))
base = base.cut(cutter)
features = []
assembly = Part.makeCompound([base] + features) if "PhotodiodeHousing" == "ChipletInterposer" else base
if "PhotodiodeHousing" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "PhotodiodeHousing")
result.Label = "Photodiode package housing"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "PhotodiodeHousing.FCStd"))
Part.export([result], str(output_dir / "PhotodiodeHousing.step"))
