import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("ChipletInterposer")
base = Part.makeBox(30, 24, 0.8)
features = []
for index in range(25):
    row, column = divmod(index, 5)
    features.append(Part.makeCylinder(0.4, 0.8,
        App.Vector(5+column*5, 4+row*4, 0)))
perforated_base = base
for via_shape in features:
    perforated_base = perforated_base.cut(via_shape)
assembly = Part.makeCompound([perforated_base] + features)
result = document.addObject("PartDesign::Feature", "ChipletInterposer")
result.Label = "Chiplet interposer TSV array"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "ChipletInterposer.FCStd"))
Part.export([result], str(output_dir / "ChipletInterposer.step"))
