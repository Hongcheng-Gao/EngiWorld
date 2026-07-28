import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("ProbePlate")
base = Part.makeBox(90, 90, 5.0)
cutters = [Part.makeCylinder(1.0, 7.0, App.Vector(45.0+30*cos(2*pi*i/8), 45.0+30*sin(2*pi*i/8), -1)) for i in range(8)]
for cutter in cutters:
    base = base.cut(cutter)
features = []
assembly = Part.makeCompound([base] + features) if "ProbePlate" == "ChipletInterposer" else base
if "ProbePlate" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "ProbePlate")
result.Label = "Probe-card alignment plate"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "ProbePlate.FCStd"))
Part.export([result], str(output_dir / "ProbePlate.step"))
