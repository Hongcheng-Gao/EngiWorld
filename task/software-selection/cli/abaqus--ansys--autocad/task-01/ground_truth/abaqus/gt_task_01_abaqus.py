# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import traceback

from abaqus import mdb
from caeModules import *
from abaqusConstants import (
    AXISYMMETRIC,
    CAX6,
    CAX8R,
    CARTESIAN,
    COMPLETED,
    DEFORMABLE_BODY,
    OFF,
    ON,
    QUAD,
    STANDARD,
    STRUCTURED,
    UNIFORM,
    UNSET,
)
from mesh import ElemType
from odbAccess import openOdb


DESKTOP = r"C:\Users\user\Desktop"
MODEL_NAME = "Model-Plate"
PART_NAME = "Plate"
INSTANCE_NAME = "PLATE-1"
STEP_NAME = "Step-Pressure"
JOB_NAME = "Job-Plate"
PRESSURE = 0.1


def write_json(name, payload):
    path = os.path.join(DESKTOP, name)
    with open(path, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)


def clean_previous_job_files():
    for name in os.listdir(DESKTOP):
        lower = name.lower()
        if lower.startswith(JOB_NAME.lower() + ".") or lower in (
            "metrics.json",
            "cli_task01_abaqus_audit.json",
        ):
            path = os.path.join(DESKTOP, name)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


def build_and_solve():
    os.chdir(DESKTOP)
    clean_previous_job_files()

    if MODEL_NAME in mdb.models:
        del mdb.models[MODEL_NAME]
    model = mdb.Model(name=MODEL_NAME)

    sketch = model.ConstrainedSketch(name="Plate-Profile", sheetSize=120.0)
    sketch.ConstructionLine(point1=(0.0, -10.0), point2=(0.0, 10.0))
    sketch.rectangle(point1=(0.0, 0.0), point2=(50.0, 1.0))
    part = model.Part(
        name=PART_NAME,
        dimensionality=AXISYMMETRIC,
        type=DEFORMABLE_BODY,
    )
    part.BaseShell(sketch=sketch)
    del model.sketches["Plate-Profile"]

    steel = model.Material(name="Steel")
    steel.Elastic(table=((210000.0, 0.3),))
    model.HomogeneousSolidSection(name="Plate-Section", material="Steel")
    region = part.Set(name="PLATE-REGION", faces=part.faces[:])
    part.SectionAssignment(region=region, sectionName="Plate-Section")

    part.setMeshControls(regions=part.faces[:], elemShape=QUAD, technique=STRUCTURED)
    radial_edges = part.edges.findAt(
        ((25.0, 0.0, 0.0),),
        ((25.0, 1.0, 0.0),),
    )
    thickness_edges = part.edges.findAt(
        ((0.0, 0.5, 0.0),),
        ((50.0, 0.5, 0.0),),
    )
    part.seedEdgeByNumber(edges=radial_edges, number=25)
    part.seedEdgeByNumber(edges=thickness_edges, number=1)
    part.setElementType(
        regions=(part.faces[:],),
        elemTypes=(
            ElemType(elemCode=CAX8R, elemLibrary=STANDARD),
            ElemType(elemCode=CAX6, elemLibrary=STANDARD),
        ),
    )
    part.generateMesh()

    tol = 1.0e-6
    axis_nodes = part.nodes.getByBoundingBox(
        xMin=-tol, xMax=tol, yMin=-tol, yMax=1.0 + tol
    )
    outer_nodes = part.nodes.getByBoundingBox(
        xMin=50.0 - tol, xMax=50.0 + tol, yMin=-tol, yMax=1.0 + tol
    )
    top_nodes = part.nodes.getByBoundingBox(
        xMin=-tol, xMax=50.0 + tol, yMin=1.0 - tol, yMax=1.0 + tol
    )
    part.Set(name="AXIS", nodes=axis_nodes)
    part.Set(name="OUTER", nodes=outer_nodes)
    part.Set(name="TOP", nodes=top_nodes)

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    instance = assembly.Instance(name=INSTANCE_NAME, part=part, dependent=ON)

    model.DisplacementBC(
        name="BC-AXIS",
        createStepName="Initial",
        region=instance.sets["AXIS"],
        u1=0.0,
        u2=UNSET,
    )
    model.DisplacementBC(
        name="BC-OUTER",
        createStepName="Initial",
        region=instance.sets["OUTER"],
        u1=0.0,
        u2=0.0,
    )
    model.StaticStep(name=STEP_NAME, previous="Initial")
    model.FieldOutputRequest(
        name="F-Output-Task01",
        createStepName=STEP_NAME,
        variables=("U", "RF", "S")
    )

    top = sorted(instance.sets["TOP"].nodes, key=lambda node: node.coordinates[0])
    total_force = 0.0
    force_rows = []
    for index, node in enumerate(top):
        radius = float(node.coordinates[0])
        if index == 0:
            delta_r = 0.5 * (float(top[1].coordinates[0]) - radius)
        elif index == len(top) - 1:
            delta_r = 0.5 * (radius - float(top[index - 1].coordinates[0]))
        else:
            delta_r = 0.5 * (
                float(top[index + 1].coordinates[0])
                - float(top[index - 1].coordinates[0])
            )
        force = -PRESSURE * 2.0 * math.pi * radius * delta_r
        force_rows.append(
            {
                "node_label": int(node.label),
                "radius_mm": radius,
                "delta_r_mm": delta_r,
                "cf2_n": force,
            }
        )
        total_force += force
        if abs(force) > 0.0:
            load_set = assembly.Set(
                name="TOP-LOAD-%03d" % int(node.label),
                nodes=instance.nodes.sequenceFromLabels((node.label,)),
            )
            model.ConcentratedForce(
                name="Load-Top-%03d" % int(node.label),
                createStepName=STEP_NAME,
                region=load_set,
                cf2=force,
            )

    job = mdb.Job(
        name=JOB_NAME,
        model=MODEL_NAME,
        description="CLI open-choice task-01 axisymmetric circular plate",
        numCpus=1,
        numDomains=1,
    )
    mdb.saveAs(pathName=os.path.join(DESKTOP, JOB_NAME + ".cae"))
    job.submit(consistencyChecking=OFF)
    job.waitForCompletion()
    sta_path = os.path.join(DESKTOP, JOB_NAME + ".sta")
    sta_text = ""
    if os.path.isfile(sta_path):
        with open(sta_path, "r") as stream:
            sta_text = stream.read()
    completed_by_status = job.status == COMPLETED
    completed_by_sta = "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta_text.upper()
    if not completed_by_status and not completed_by_sta:
        raise RuntimeError("Abaqus job did not complete: %s" % job.status)
    mdb.save()

    odb_path = os.path.join(DESKTOP, JOB_NAME + ".odb")
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            raise RuntimeError("ODB has too few frames")
        frame = step.frames[-1]
        odb_instance = odb.rootAssembly.instances[INSTANCE_NAME]
        center_label = None
        for node in odb_instance.nodes:
            coords = node.coordinates
            if abs(float(coords[0])) <= tol and abs(float(coords[1]) - 1.0) <= tol:
                center_label = int(node.label)
                break
        if center_label is None:
            raise RuntimeError("center top node was not found in ODB")

        center_deflection = None
        for value in frame.fieldOutputs["U"].values:
            if int(value.nodeLabel) == center_label:
                center_deflection = float(value.data[1])
                break
        mises_values = []
        for value in frame.fieldOutputs["S"].values:
            try:
                mises = float(value.mises)
                if math.isfinite(mises):
                    mises_values.append(mises)
            except Exception:
                pass
        if center_deflection is None or not mises_values:
            raise RuntimeError("required U/S values were not found in ODB")
        max_mises = max(mises_values)

        support_rf2 = 0.0
        outer_labels = set(int(node.label) for node in odb_instance.nodeSets["OUTER"].nodes)
        for value in frame.fieldOutputs["RF"].values:
            if int(value.nodeLabel) in outer_labels:
                support_rf2 += float(value.data[1])

        metrics = {
            "center_deflection": center_deflection,
            "max_mises": max_mises,
        }
        write_json("metrics.json", metrics)
        write_json(
            "cli_task01_abaqus_audit.json",
            {
                "software": "Abaqus/Standard Learning Edition 2025",
                "model_name": MODEL_NAME,
                "job_name": JOB_NAME,
                "job_status": str(job.status),
                "completed_by_status": completed_by_status,
                "completed_by_sta": completed_by_sta,
                "step_name": STEP_NAME,
                "frames": len(step.frames),
                "nodes": len(part.nodes),
                "elements": len(part.elements),
                "element_types": sorted(
                    set(str(element.type) for element in part.elements)
                ),
                "axis_nodes": len(axis_nodes),
                "outer_nodes": len(outer_nodes),
                "top_nodes": len(top_nodes),
                "nonzero_top_loads": builtins.sum(
                    1 for row in force_rows if abs(row["cf2_n"]) > 0.0
                ),
                "total_cf2_n": total_force,
                "expected_total_cf2_n": -PRESSURE * math.pi * 50.0 ** 2,
                "support_rf2_n": support_rf2,
                "center_node_label": center_label,
                "metrics": metrics,
                "top_loads": force_rows,
            },
        )
    finally:
        odb.close()


if __name__ == "__main__":
    try:
        build_and_solve()
        print("TASK01_ABAQUS_OK")
    except Exception:
        write_json(
            "cli_task01_abaqus_audit.json",
            {"status": "failed", "traceback": traceback.format_exc()},
        )
        traceback.print_exc()
        raise
