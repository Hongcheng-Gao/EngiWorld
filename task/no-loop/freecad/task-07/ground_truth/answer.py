import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("MicrofluidicChip")
base = Part.makeBox(60, 30, 4.0)
cutters = [Part.makeBox(50, 2.0, 4.0, App.Vector(5, 4+i*6, 1)) for i in range(4)]
for cutter in cutters:
    base = base.cut(cutter)
features = []
assembly = Part.makeCompound([base] + features) if "MicrofluidicChip" == "ChipletInterposer" else base
if "MicrofluidicChip" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "MicrofluidicChip")
result.Label = "Microfluidic semiconductor test chip"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "MicrofluidicChip.FCStd"))
Part.export([result], str(output_dir / "MicrofluidicChip.step"))
