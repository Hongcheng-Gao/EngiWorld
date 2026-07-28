import FreeCAD as App
import Part
from math import cos, sin, pi
from pathlib import Path

document = App.newDocument("WaferCarrier")
base = Part.makeBox(120, 120, 3.0)
features = [Part.makeCylinder(50.0, 0.8,
    App.Vector(60.0, 60.0, 3.0))]
assembly = Part.makeCompound([base] + features) if "WaferCarrier" == "ChipletInterposer" else base
if "WaferCarrier" != "ChipletInterposer":
    for feature_shape in features:
        assembly = assembly.fuse(feature_shape)
result = document.addObject("PartDesign::Feature", "WaferCarrier")
result.Label = "Wafer dicing carrier"
result.Shape = assembly
document.recompute()
output_dir = Path(__file__).resolve().parent
document.saveAs(str(output_dir / "WaferCarrier.FCStd"))
Part.export([result], str(output_dir / "WaferCarrier.step"))
