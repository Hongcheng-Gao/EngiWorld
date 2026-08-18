# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import math
import os

from abaqus import mdb, openMdb
from caeModules import *
from odbAccess import openOdb


DESKTOP = r"C:\Users\user\Desktop"


def coordinates(sequence):
    result = []
    for item in sequence:
        try:
            result.append(tuple(float(value) for value in item.pointOn[0]))
        except Exception:
            try:
                result.append(tuple(float(value) for value in item.coordinates))
            except Exception:
                result.append(repr(item))
    return result


def cae_summary(path):
    openMdb(pathName=path)
    model = mdb.models["PunchPlate2D"]
    assembly = model.rootAssembly
    punch = model.parts["Punch"]
    punch_instance = assembly.instances["Punch-1"]
    result = {
        "path": path,
        "parts": list(model.parts.keys()),
        "steps": list(model.steps.keys()),
        "interactions": list(model.interactions.keys()),
        "loads": list(model.loads.keys()),
        "boundary_conditions": list(model.boundaryConditions.keys()),
        "jobs": list(mdb.jobs.keys()),
        "plate_sets": list(model.parts["Plate"].sets.keys()),
        "plate_surfaces": list(model.parts["Plate"].surfaces.keys()),
        "punch_sets": list(punch.sets.keys()),
        "punch_surfaces": list(punch.surfaces.keys()),
        "punch_vertices": coordinates(punch.vertices),
        "punch_edge_points": coordinates(punch.edges),
        "punch_instance_vertices": coordinates(punch_instance.vertices),
        "punch_instance_edge_points": coordinates(punch_instance.edges),
        "punch_instance_reference_points": [
            repr(punch_instance.referencePoints[key])
            for key in punch_instance.referencePoints.keys()
        ],
        "assembly_sets": list(assembly.sets.keys()),
    }
    if "PunchPlateContact" in model.interactions:
        interaction = model.interactions["PunchPlateContact"]
        result["interaction"] = {
            "class": interaction.__class__.__name__,
            "main": repr(interaction.main),
            "secondary": repr(interaction.secondary),
            "sliding": str(interaction.sliding),
        }
    if "PunchMotion" in model.boundaryConditions:
        bc = model.boundaryConditions["PunchMotion"]
        result["punch_motion"] = {
            "class": bc.__class__.__name__,
            "repr": repr(bc),
        }
    return result


def scalar(value):
    try:
        return float(value.data)
    except Exception:
        return float(value.data[0])


def odb_summary(path):
    odb = openOdb(path=path, readOnly=True)
    try:
        step = odb.steps["IndentationStep"]
        frame = step.frames[-1]
        fields = list(frame.fieldOutputs.keys())
        result = {
            "status": str(odb.diagnosticData.jobStatus),
            "instances": {},
            "assembly_sets": list(odb.rootAssembly.nodeSets.keys()),
            "fields": fields,
            "frames": len(step.frames),
            "frame_value": float(frame.frameValue),
        }
        for name in odb.rootAssembly.instances.keys():
            instance = odb.rootAssembly.instances[name]
            result["instances"][name] = {
                "nodes": len(instance.nodes),
                "elements": len(instance.elements),
                "node_coordinates": [tuple(float(value) for value in node.coordinates) for node in instance.nodes[:3]],
            }
        for prefix in ("CPRESS", "COPEN"):
            matches = [name for name in fields if str(name).strip().upper().startswith(prefix)]
            result[prefix] = []
            for name in matches:
                values = [scalar(value) for value in frame.fieldOutputs[name].values]
                result[prefix].append({
                    "name": name,
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "positive": len([value for value in values if value > 1.0e-8]),
                    "defined_values": [value for value in values if value > -1.0e30],
                })
        bottom = odb.rootAssembly.nodeSets["PLATE_BOTTOM_NODES"]
        rp = odb.rootAssembly.nodeSets["PUNCH_RP_NODE"]
        result["bottom_rf2_sum"] = math.fsum(float(value.data[1]) for value in frame.fieldOutputs["RF"].getSubset(region=bottom).values)
        result["rp_rf2_sum"] = math.fsum(float(value.data[1]) for value in frame.fieldOutputs["RF"].getSubset(region=rp).values)
        result["rp_u2"] = [float(value.data[1]) for value in frame.fieldOutputs["U"].getSubset(region=rp).values]
        return result
    finally:
        odb.close()


def main():
    data = {
        "init": cae_summary(os.path.join(DESKTOP, "task18_punch_plate_init.cae")),
        "gt": cae_summary(os.path.join(DESKTOP, "Task18_PunchPlate_GT.cae")),
        "odb": odb_summary(os.path.join(DESKTOP, "Task18_PunchPlate.odb")),
    }
    path = os.path.join(DESKTOP, "task18_probe.json")
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    print(json.dumps(data, sort_keys=True))


if __name__ == "__main__":
    main()
