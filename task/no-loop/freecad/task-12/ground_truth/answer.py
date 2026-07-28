import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("MaskFrame")
base = Part.makeBox(160, 160, 8.0)
inner = Part.makeBox(130.0, 130.0, 10.0,
    App.Vector((160-130.0)/2, (160-130.0)/2, -1))
base = base.cut(inner)
features = []
assembly = Part.makeCompound([base] + features) if "MaskFrame" == "ChipletInterposer" else base
if "MaskFrame" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "MaskFrame")
result.Label = "Lithography mask storage frame"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "MaskFrame.FCStd"))
Part.export([result], str(output_dir / "MaskFrame.step"))
