# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os

from abaqus import mdb, openMdb
from caeModules import *


DESKTOP = r"C:\Users\user\Desktop"


def attrs(obj, names):
    result = {"class": obj.__class__.__name__}
    for name in names:
        try:
            result[name] = repr(getattr(obj, name))
        except Exception as exc:
            result[name] = "ERROR: " + str(exc)
    return result


def methods(obj):
    result = {}
    for name, arguments in (
        ("getValues", {}),
        ("getValuesInStep", {"stepName": "ContactStep"}),
    ):
        try:
            result[name] = repr(getattr(obj, name)(**arguments))
        except Exception as exc:
            result[name] = "ERROR: " + str(exc)
    try:
        result["members"] = repr(obj.__members__)
    except Exception as exc:
        result["members"] = "ERROR: " + str(exc)
    return result


openMdb(pathName=os.path.join(DESKTOP, "Task08_BlockPlate_GT.cae"))
model = mdb.models["BlockPlate3D"]
evidence = {
    "steps": {name: attrs(model.steps[name], ["nlgeom", "timePeriod", "initialInc", "maxNumInc"]) for name in model.steps.keys()},
    "interactions": {name: dict(attrs(model.interactions[name], ["main", "secondary", "interactionProperty", "sliding"]), **methods(model.interactions[name])) for name in model.interactions.keys()},
    "properties": {name: attrs(model.interactionProperties[name], ["normalBehavior", "normalBehavior.pressureOverclosure", "tangentialBehavior", "tangentialBehavior.formulation"]) for name in model.interactionProperties.keys()},
    "normal": attrs(model.interactionProperties["FrictionlessHard"].normalBehavior, ["pressureOverclosure", "allowSeparation"]),
    "tangential": attrs(model.interactionProperties["FrictionlessHard"].tangentialBehavior, ["formulation"]),
    "loads": {name: dict(attrs(model.loads[name], ["magnitude", "createStepName", "region"]), **methods(model.loads[name])) for name in model.loads.keys()},
    "bcs": {name: dict(attrs(model.boundaryConditions[name], ["u1", "u2", "u3", "createStepName", "region"]), **methods(model.boundaryConditions[name])) for name in model.boundaryConditions.keys()},
    "jobs": {name: attrs(mdb.jobs[name], ["model", "type"]) for name in mdb.jobs.keys()},
}
with open(os.path.join(DESKTOP, "task08_model_probe.json"), "w") as handle:
    json.dump(evidence, handle, indent=2, sort_keys=True)
print(json.dumps(evidence, sort_keys=True))
