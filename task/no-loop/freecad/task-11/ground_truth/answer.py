import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("WireBondFixture")
base = Part.makeBox(70, 50, 5.0)
features = [Part.makeCylinder(1.5, 8,
    App.Vector(8+i*10, 25.0, 5.0)) for i in range(6)]
assembly = Part.makeCompound([base] + features) if "WireBondFixture" == "ChipletInterposer" else base
if "WireBondFixture" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "WireBondFixture")
result.Label = "Wire-bond fixture plate"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "WireBondFixture.FCStd"))
Part.export([result], str(output_dir / "WireBondFixture.step"))
