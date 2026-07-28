import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("BGASubstrate")
base = Part.makeBox(40, 40, 1.2)
features = []
for index in range(36):
    row, column = divmod(index, 6)
    features.append(Part.makeSphere(0.9,
        App.Vector(7+column*5.2, 7+row*5.2, 1.2)))
assembly = Part.makeCompound([base] + features) if "BGASubstrate" == "ChipletInterposer" else base
if "BGASubstrate" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "BGASubstrate")
result.Label = "BGA substrate and ball array"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "BGASubstrate.FCStd"))
Part.export([result], str(output_dir / "BGASubstrate.step"))
