import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("DieTray")
base = Part.makeBox(100, 80, 6.0)
cutters = [Part.makeBox(12.0, 12.0, 5.0, App.Vector(5+(i%5)*18, 8+(i//5)*22, 2)) for i in range(15)]
for cutter in cutters:
    base = base.cut(cutter)
features = []
assembly = Part.makeCompound([base] + features) if "DieTray" == "ChipletInterposer" else base
if "DieTray" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "DieTray")
result.Label = "JEDEC die shipping tray"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "DieTray.FCStd"))
Part.export([result], str(output_dir / "DieTray.step"))
