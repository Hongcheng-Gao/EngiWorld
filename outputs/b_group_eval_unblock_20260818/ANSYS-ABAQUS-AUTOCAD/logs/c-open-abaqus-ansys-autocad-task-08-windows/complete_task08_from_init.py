# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import json
import math
import os
import traceback

from abaqus import mdb, openMdb
from abaqusConstants import ANALYSIS, FINITE, FRICTIONLESS, HARD, OFF, ON, SINGLE, UNSET
from caeModules import *
from odbAccess import openOdb


DESKTOP = r"C:\Users\user\Desktop"
INIT_PATH = os.path.join(DESKTOP, "task08_block_plate_init.cae")
GT_PATH = os.path.join(DESKTOP, "Task08_BlockPlate_GT.cae")
ODB_PATH = os.path.join(DESKTOP, "Task08_BlockPlate.odb")
METRICS_PATH = os.path.join(DESKTOP, "metrics.json")
JOB_NAME = "Task08_BlockPlate"


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
    data = value.data
    try:
        return float(data)
    except Exception:
        return float(data[0])


def main():
    os.chdir(DESKTOP)
    opened_init_sha256 = sha256(INIT_PATH)
    openMdb(pathName=INIT_PATH)
    model = mdb.models["BlockPlate3D"]
    assembly = model.rootAssembly
    plate_instance = assembly.instances["Plate-1"]
    block_instance = assembly.instances["Block-1"]

    model.StaticStep(
        name="ContactStep",
        previous="Initial",
        nlgeom=ON,
        initialInc=0.05,
        minInc=1.0e-6,
        maxInc=0.1,
        maxNumInc=200,
    )
    contact_property = model.ContactProperty("FrictionlessHard")
    contact_property.NormalBehavior(pressureOverclosure=HARD, allowSeparation=ON)
    contact_property.TangentialBehavior(formulation=FRICTIONLESS)
    model.SurfaceToSurfaceContactStd(
        name="BlockPlateContact",
        createStepName="Initial",
        main=plate_instance.surfaces["PLATE_TOP"],
        secondary=block_instance.surfaces["BLOCK_BOTTOM"],
        sliding=FINITE,
        interactionProperty="FrictionlessHard",
    )
    model.EncastreBC(
        name="PlateBottomFixed",
        createStepName="Initial",
        region=plate_instance.sets["PLATE_BOTTOM"],
    )
    model.DisplacementBC(
        name="BlockAnchorXY",
        createStepName="Initial",
        region=block_instance.sets["BLOCK_ANCHOR"],
        u1=0.0,
        u2=0.0,
        u3=UNSET,
    )
    model.DisplacementBC(
        name="BlockGuideY",
        createStepName="Initial",
        region=block_instance.sets["BLOCK_GUIDE"],
        u1=UNSET,
        u2=0.0,
        u3=UNSET,
    )
    model.Pressure(
        name="BlockTopPressure",
        createStepName="ContactStep",
        region=block_instance.surfaces["BLOCK_TOP"],
        magnitude=2.0,
    )
    assembly.Set(name="PLATE_BOTTOM_NODES", nodes=plate_instance.sets["PLATE_BOTTOM"].nodes)
    assembly.Set(name="BLOCK_TOP_NODES", nodes=block_instance.sets["BLOCK_TOP_NODES"].nodes)
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
        step = odb.steps["ContactStep"]
        frame = step.frames[-1]
        field_names = list(frame.fieldOutputs.keys())
        contact_pressure = max([scalar(value) for value in frame.fieldOutputs["CPRESS"].values] or [0.0])
        block_top = odb.rootAssembly.nodeSets["BLOCK_TOP_NODES"]
        vertical_displacement = min(
            [float(value.data[2]) for value in frame.fieldOutputs["U"].getSubset(region=block_top).values] or [0.0]
        )
        plate_bottom = odb.rootAssembly.nodeSets["PLATE_BOTTOM_NODES"]
        reaction_force = abs(
            math.fsum(
                float(value.data[2])
                for value in frame.fieldOutputs["RF"].getSubset(region=plate_bottom).values
            )
        )
        max_mises = max(
            [float(value.mises) for value in frame.fieldOutputs["S"].values if hasattr(value, "mises")]
            or [0.0]
        )
        metrics = {
            "max_contact_pressure": float(contact_pressure),
            "vertical_displacement": float(vertical_displacement),
            "reaction_force": float(reaction_force),
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
            "block_nodes": len(model.parts["Block"].nodes),
            "block_elements": len(model.parts["Block"].elements),
            "total_nodes": len(model.parts["Plate"].nodes) + len(model.parts["Block"].nodes),
            "metrics": metrics,
        }
    finally:
        odb.close()

    with open(METRICS_PATH, "w") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)
    with open(os.path.join(DESKTOP, "task08_generation_evidence.json"), "w") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(os.path.join(DESKTOP, "task08_generation_error.txt"), "w") as handle:
            handle.write(traceback.format_exc())
        raise
