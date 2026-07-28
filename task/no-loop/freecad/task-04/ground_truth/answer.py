import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("PellicleFrame")
base = Part.makeBox(152, 152, 6.0)
inner = Part.makeBox(120.0, 120.0, 8.0,
    App.Vector((152-120.0)/2, (152-120.0)/2, -1))
base = base.cut(inner)
features = []
assembly = Part.makeCompound([base] + features) if "PellicleFrame" == "ChipletInterposer" else base
if "PellicleFrame" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "PellicleFrame")
result.Label = "Reticle pellicle frame"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "PellicleFrame.FCStd"))
Part.export([result], str(output_dir / "PellicleFrame.step"))
