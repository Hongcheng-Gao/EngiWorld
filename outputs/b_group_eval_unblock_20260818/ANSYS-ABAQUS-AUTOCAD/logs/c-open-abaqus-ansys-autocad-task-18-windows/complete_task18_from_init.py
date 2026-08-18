# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import json
import math
import os
import traceback

from abaqus import mdb, openMdb
from abaqusConstants import ANALYSIS, FINITE, FRICTIONLESS, HARD, OFF, ON, SINGLE
from caeModules import *
from odbAccess import openOdb


DESKTOP = r"C:\Users\user\Desktop"
INIT_PATH = os.path.join(DESKTOP, "task18_punch_plate_init.cae")
GT_PATH = os.path.join(DESKTOP, "Task18_PunchPlate_GT.cae")
ODB_PATH = os.path.join(DESKTOP, "Task18_PunchPlate.odb")
METRICS_PATH = os.path.join(DESKTOP, "metrics.json")
JOB_NAME = "Task18_PunchPlate"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def scalar(value):
    try:
        return float(value.data)
    except Exception:
        return float(value.data[0])


def main():
    os.chdir(DESKTOP)
    opened_init_sha256 = sha256(INIT_PATH)
    openMdb(pathName=INIT_PATH)
    model = mdb.models["PunchPlate2D"]
    assembly = model.rootAssembly
    plate_instance = assembly.instances["Plate-1"]
    punch_instance = assembly.instances["Punch-1"]

    model.StaticStep(
        name="IndentationStep",
        previous="Initial",
        nlgeom=ON,
        initialInc=0.01,
        minInc=1.0e-6,
        maxInc=0.05,
        maxNumInc=300,
    )
    prop = model.ContactProperty("FrictionlessHard")
    prop.NormalBehavior(pressureOverclosure=HARD, allowSeparation=ON)
    prop.TangentialBehavior(formulation=FRICTIONLESS)
    model.SurfaceToSurfaceContactStd(
        name="PunchPlateContact",
        createStepName="Initial",
        main=punch_instance.surfaces["PUNCH_CONTACT"],
        secondary=plate_instance.surfaces["PLATE_TOP"],
        sliding=FINITE,
        interactionProperty="FrictionlessHard",
    )
    model.EncastreBC(
        name="PlateBottomFixed",
        createStepName="Initial",
        region=plate_instance.sets["PLATE_BOTTOM"],
    )
    model.DisplacementBC(
        name="PunchMotion",
        createStepName="IndentationStep",
        region=punch_instance.sets["PUNCH_RP"],
        u1=0.0,
        u2=-0.1,
        ur3=0.0,
    )
    assembly.Set(name="PLATE_BOTTOM_NODES", nodes=plate_instance.sets["PLATE_BOTTOM"].nodes)
    rp_keys = list(punch_instance.referencePoints.keys())
    assembly.Set(
        name="PUNCH_RP_NODE",
        referencePoints=(punch_instance.referencePoints[rp_keys[0]],),
    )
    model.fieldOutputRequests["F-Output-1"].setValues(
        variables=("S", "U", "RF", "CSTRESS", "CDISP")
    )

    mdb.saveAs(pathName=GT_PATH)
    job = mdb.Job(
        name=JOB_NAME,
        model=model.name,
        type=ANALYSIS,
        explicitPrecision=SINGLE,
        nodalOutputPrecision=SINGLE,
        numCpus=1,
    )
    job.submit(consistencyChecking=OFF)
    job.waitForCompletion()
    mdb.saveAs(pathName=GT_PATH)

    odb = openOdb(path=ODB_PATH, readOnly=True)
    try:
        step = odb.steps["IndentationStep"]
        frame = step.frames[-1]
        field_names = list(frame.fieldOutputs.keys())
        pressure_key = [name for name in field_names if str(name).strip().upper().startswith("CPRESS")][0]
        max_contact_pressure = max([scalar(value) for value in frame.fieldOutputs[pressure_key].values] or [0.0])
        rp_set = odb.rootAssembly.nodeSets["PUNCH_RP_NODE"]
        rp_u = frame.fieldOutputs["U"].getSubset(region=rp_set).values
        punch_displacement = float(rp_u[0].data[1])
        rp_rf = frame.fieldOutputs["RF"].getSubset(region=rp_set).values
        punch_reaction = abs(math.fsum(float(value.data[1]) for value in rp_rf))
        max_mises = max(
            [float(value.mises) for value in frame.fieldOutputs["S"].values if hasattr(value, "mises")]
            or [0.0]
        )
        metrics = {
            "max_contact_pressure": float(max_contact_pressure),
            "punch_vertical_displacement": float(punch_displacement),
            "punch_reaction_force": float(punch_reaction),
            "max_mises_stress": float(max_mises),
        }
        evidence = {
            "status": str(odb.diagnosticData.jobStatus),
            "opened_init": INIT_PATH,
            "opened_init_sha256": opened_init_sha256,
            "gt_cae": GT_PATH,
            "odb": ODB_PATH,
            "frames": len(step.frames),
            "field_outputs": field_names,
            "plate_nodes": len(model.parts["Plate"].nodes),
            "plate_elements": len(model.parts["Plate"].elements),
            "punch_edges": len(model.parts["Punch"].edges),
            "metrics": metrics,
        }
    finally:
        odb.close()

    with open(METRICS_PATH, "w") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)
    with open(os.path.join(DESKTOP, "task18_generation_evidence.json"), "w") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(os.path.join(DESKTOP, "task18_generation_error.txt"), "w") as handle:
            handle.write(traceback.format_exc())
        raise
