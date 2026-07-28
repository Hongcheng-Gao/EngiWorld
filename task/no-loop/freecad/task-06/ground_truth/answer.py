import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("HeatSpreader")
base = Part.makeBox(50, 50, 2.0)
features = [Part.makeBox(1.5, 46, 10,
    App.Vector(4+i*6.5, 2, 2.0)) for i in range(7)]
assembly = Part.makeCompound([base] + features) if "HeatSpreader" == "ChipletInterposer" else base
if "HeatSpreader" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "HeatSpreader")
result.Label = "Copper heat spreader fin field"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "HeatSpreader.FCStd"))
Part.export([result], str(output_dir / "HeatSpreader.step"))
