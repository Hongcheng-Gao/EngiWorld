# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os

from abaqus import mdb, openMdb
from caeModules import *


DESKTOP = r"C:\Users\user\Desktop"
OUTPUT = os.path.join(DESKTOP, "final_evaluator_attribute_probe.json")


def attribute(obj, name):
    try:
        return repr(getattr(obj, name))
    except Exception as exc:
        return "ERROR: " + str(exc)


def nodes(region):
    result = []
    try:
        sequence = region.nodes
    except Exception:
        sequence = ()
    for node in sequence:
        result.append({
            "label": int(node.label),
            "coordinates": [round(float(value), 8) for value in node.coordinates],
            "instanceName": attribute(node, "instanceName"),
        })
    return result


def reference_points(region):
    try:
        return [repr(item) for item in region.referencePoints]
    except Exception as exc:
        return ["ERROR: " + str(exc)]


def summarize(path, model_name):
    openMdb(pathName=path)
    model = mdb.models[model_name]
    assembly = model.rootAssembly
    return {
        "path": path,
        "sections": {
            name: {"material": attribute(model.sections[name], "material")}
            for name in model.sections.keys()
        },
        "assignments": {
            part_name: [
                {
                    "sectionName": attribute(item, "sectionName"),
                    "region": repr(item.region),
                }
                for item in model.parts[part_name].sectionAssignments
            ]
            for part_name in model.parts.keys()
        },
        "steps": {
            name: {
                key: attribute(model.steps[name], key)
                for key in ("nlgeom", "timePeriod", "initialInc", "minInc", "maxInc", "maxNumInc")
            }
            for name in model.steps.keys()
        },
        "interactions": {
            name: {
                key: attribute(model.interactions[name], key)
                for key in (
                    "createStepName",
                    "interactionProperty",
                    "sliding",
                    "suppressed",
                    "main",
                    "secondary",
                )
            }
            for name in model.interactions.keys()
        },
        "properties": {
            name: {
                "normal_pressureOverclosure": attribute(
                    model.interactionProperties[name].normalBehavior,
                    "pressureOverclosure",
                ),
                "normal_allowSeparation": attribute(
                    model.interactionProperties[name].normalBehavior,
                    "allowSeparation",
                ),
                "tangential_formulation": attribute(
                    model.interactionProperties[name].tangentialBehavior,
                    "formulation",
                ),
            }
            for name in model.interactionProperties.keys()
        },
        "assembly_sets": {
            name: {
                "repr": repr(assembly.sets[name]),
                "nodes": nodes(assembly.sets[name]),
                "referencePoints": reference_points(assembly.sets[name]),
            }
            for name in assembly.sets.keys()
        },
        "instance_sets": {
            instance_name: {
                set_name: {
                    "repr": repr(assembly.instances[instance_name].sets[set_name]),
                    "nodes": nodes(assembly.instances[instance_name].sets[set_name]),
                    "referencePoints": reference_points(
                        assembly.instances[instance_name].sets[set_name]
                    ),
                }
                for set_name in assembly.instances[instance_name].sets.keys()
            }
            for instance_name in assembly.instances.keys()
        },
        "jobs": {
            name: {
                key: attribute(mdb.jobs[name], key)
                for key in ("model", "numCpus", "multiprocessingMode", "numDomains")
            }
            for name in mdb.jobs.keys()
        },
    }


data = {
    "task08": summarize(
        os.path.join(DESKTOP, "Task08_BlockPlate_GT.cae"),
        "BlockPlate3D",
    ),
    "task18": summarize(
        os.path.join(DESKTOP, "Task18_PunchPlate_GT.cae"),
        "PunchPlate2D",
    ),
}
with open(OUTPUT, "w") as handle:
    json.dump(data, handle, indent=2, sort_keys=True)
print(json.dumps(data, sort_keys=True))
