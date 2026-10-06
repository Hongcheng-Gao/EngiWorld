# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import sys

from abaqus import mdb
from abaqusConstants import (
    AXISYMMETRIC,
    CAX4,
    CAX4R,
    CARTESIAN,
    COMPLETED,
    DEFORMABLE_BODY,
    OFF,
    ON,
    QUAD,
    STANDARD,
    STRUCTURED,
    UNSET,
)
from caeModules import *
from mesh import ElemType
from odbAccess import openOdb


MODEL_NAME = "Model-Cylinder"
PART_NAME = "Cylinder"
INSTANCE_NAME = "CYLINDER-1"
STEP_NAME = "Step-Pressure"
JOB_NAME = "Job-Cylinder"
PRESSURE = 10.0
INNER_RADIUS = 50.0


def write_json(path, payload):
    with open(path, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)


def clean_job_files(output_dir):
    for name in os.listdir(output_dir):
        lower = name.lower()
        if lower.startswith(JOB_NAME.lower() + ".") or lower in (
            "metrics.json",
            "native_audit.json",
        ):
            path = os.path.join(output_dir, name)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                except Exception:
                    pass


def require_close(actual, expected, rel=1.0e-8, abs_tol=1.0e-8):
    if not math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol):
        raise RuntimeError("value mismatch: %r != %r" % (actual, expected))


def build_and_solve(output_dir, element_code_name="CAX4"):
    output_dir = os.path.abspath(output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    clean_job_files(output_dir)
    os.chdir(output_dir)

    if MODEL_NAME in mdb.models:
        del mdb.models[MODEL_NAME]
    model = mdb.Model(name=MODEL_NAME)
    for name in list(mdb.models.keys()):
        if name != MODEL_NAME:
            del mdb.models[name]

    sketch = model.ConstrainedSketch(name="Cylinder-Profile", sheetSize=250.0)
    sketch.ConstructionLine(point1=(0.0, -20.0), point2=(0.0, 30.0))
    sketch.rectangle(point1=(50.0, 0.0), point2=(100.0, 10.0))
    part = model.Part(name=PART_NAME, dimensionality=AXISYMMETRIC, type=DEFORMABLE_BODY)
    part.BaseShell(sketch=sketch)
    del model.sketches["Cylinder-Profile"]

    steel = model.Material(name="Steel")
    steel.Elastic(table=((210000.0, 0.3),))
    model.HomogeneousSolidSection(name="Cylinder-Section", material="Steel")
    region = part.Set(name="CYLINDER-REGION", faces=part.faces[:])
    part.SectionAssignment(region=region, sectionName="Cylinder-Section")

    part.setMeshControls(regions=part.faces[:], elemShape=QUAD, technique=STRUCTURED)
    part.seedPart(size=5.0, deviationFactor=0.1, minSizeFactor=0.1)
    element_code = CAX4R if element_code_name == "CAX4R" else CAX4
    expected_ip = 1 if element_code_name == "CAX4R" else 4
    part.setElementType(
        regions=(part.faces[:],),
        elemTypes=(ElemType(elemCode=element_code, elemLibrary=STANDARD),),
    )
    part.generateMesh()

    tol = 1.0e-6
    all_nodes = part.nodes[:]
    inner_nodes = part.nodes.getByBoundingBox(
        xMin=50.0 - tol, xMax=50.0 + tol, yMin=-tol, yMax=10.0 + tol
    )
    outer_nodes = part.nodes.getByBoundingBox(
        xMin=100.0 - tol, xMax=100.0 + tol, yMin=-tol, yMax=10.0 + tol
    )
    zmin_nodes = part.nodes.getByBoundingBox(
        xMin=50.0 - tol, xMax=100.0 + tol, yMin=-tol, yMax=tol
    )
    zmax_nodes = part.nodes.getByBoundingBox(
        xMin=50.0 - tol, xMax=100.0 + tol, yMin=10.0 - tol, yMax=10.0 + tol
    )
    for name, nodes in (
        ("ALLNODES", all_nodes),
        ("INNER", inner_nodes),
        ("OUTER", outer_nodes),
        ("ZMIN", zmin_nodes),
        ("ZMAX", zmax_nodes),
    ):
        part.Set(name=name, nodes=nodes)

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    instance = assembly.Instance(name=INSTANCE_NAME, part=part, dependent=ON)
    model.DisplacementBC(
        name="BC-PlaneStrain",
        createStepName="Initial",
        region=instance.sets["ALLNODES"],
        u1=UNSET,
        u2=0.0,
    )
    model.StaticStep(name=STEP_NAME, previous="Initial")
    for name in list(model.fieldOutputRequests.keys()):
        del model.fieldOutputRequests[name]
    model.FieldOutputRequest(
        name="F-Output-Task02",
        createStepName=STEP_NAME,
        variables=("U", "RF", "S"),
    )

    inner = sorted(instance.sets["INNER"].nodes, key=lambda node: node.coordinates[1])
    if len(inner) < 2:
        raise RuntimeError("INNER set has too few nodes")
    load_rows = []
    for index, node in enumerate(inner):
        axial = float(node.coordinates[1])
        if index == 0:
            delta_z = 0.5 * (float(inner[1].coordinates[1]) - axial)
        elif index == len(inner) - 1:
            delta_z = 0.5 * (axial - float(inner[index - 1].coordinates[1]))
        else:
            delta_z = 0.5 * (
                float(inner[index + 1].coordinates[1])
                - float(inner[index - 1].coordinates[1])
            )
        force = PRESSURE * 2.0 * math.pi * INNER_RADIUS * delta_z
        load_set = assembly.Set(
            name="INNER-LOAD-%03d" % int(node.label),
            nodes=instance.nodes.sequenceFromLabels((int(node.label),)),
        )
        model.ConcentratedForce(
            name="Load-Inner-%03d" % int(node.label),
            createStepName=STEP_NAME,
            region=load_set,
            cf1=force,
        )
        load_rows.append(
            {
                "node_label": int(node.label),
                "r_mm": float(node.coordinates[0]),
                "z_mm": axial,
                "delta_z_mm": delta_z,
                "cf1_n": force,
            }
        )

    expected_total = PRESSURE * 2.0 * math.pi * INNER_RADIUS * 10.0
    require_close(builtins.sum(row["cf1_n"] for row in load_rows), expected_total)
    if len(part.nodes) != 33 or len(part.elements) != 20:
        raise RuntimeError("unexpected axisymmetric mesh size")

    job = mdb.Job(
        name=JOB_NAME,
        model=MODEL_NAME,
        description="CLI task-02 axisymmetric thick-walled cylinder",
        numCpus=1,
        numDomains=1,
    )
    mdb.saveAs(pathName=os.path.join(output_dir, JOB_NAME + ".cae"))
    job.writeInput(consistencyChecking=ON)
    job.submit(consistencyChecking=ON)
    job.waitForCompletion()
    sta_path = os.path.join(output_dir, JOB_NAME + ".sta")
    sta_text = ""
    if os.path.isfile(sta_path):
        with open(sta_path, "r") as stream:
            sta_text = stream.read()
    completed_by_status = job.status == COMPLETED
    completed_by_sta = "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta_text.upper()
    if not completed_by_status and not completed_by_sta:
        raise RuntimeError("Abaqus job did not complete: %s" % job.status)
    mdb.save()

    odb = openOdb(path=os.path.join(output_dir, JOB_NAME + ".odb"), readOnly=True)
    try:
        if str(getattr(odb.diagnosticData, "jobStatus", "")).upper() != "JOB_STATUS_COMPLETED_SUCCESSFULLY":
            raise RuntimeError("ODB does not report completed successfully")
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            raise RuntimeError("ODB has too few frames")
        frame = step.frames[-1]
        odb_instance = odb.rootAssembly.instances[INSTANCE_NAME]
        required_fields = ("U", "RF", "S")
        for field_name in required_fields:
            if field_name not in frame.fieldOutputs.keys():
                raise RuntimeError("missing ODB field: " + field_name)

        inner_labels = set(int(node.label) for node in odb_instance.nodeSets["INNER"].nodes)
        midpoint_label = None
        for node in odb_instance.nodeSets["INNER"].nodes:
            if abs(float(node.coordinates[1]) - 5.0) <= tol:
                midpoint_label = int(node.label)
                break
        if midpoint_label is None:
            raise RuntimeError("INNER midpoint node not found")
        radial_displacement = None
        for value in frame.fieldOutputs["U"].values:
            if int(value.nodeLabel) == midpoint_label:
                radial_displacement = float(value.data[0])
                break
        if radial_displacement is None:
            raise RuntimeError("INNER midpoint displacement not found")

        mises_values = []
        stress_element_labels = set()
        stress_counts = {}
        for value in frame.fieldOutputs["S"].values:
            if str(getattr(value, "position", "")).upper().endswith("INTEGRATION_POINT"):
                element_label = int(value.elementLabel)
                stress_element_labels.add(element_label)
                stress_counts[element_label] = stress_counts.get(element_label, 0) + 1
                try:
                    mises = float(value.mises)
                    if math.isfinite(mises):
                        mises_values.append(mises)
                except Exception:
                    pass
        if (
            not mises_values
            or len(stress_element_labels) != len(part.elements)
            or any(stress_counts.get(int(element.label)) != expected_ip for element in part.elements)
        ):
            raise RuntimeError("integration-point stress does not cover all elements")
        max_mises = max(mises_values)
        if not (0.0044 < radial_displacement < 0.0047 and 18.0 < max_mises < 26.0):
            raise RuntimeError("native result is outside physical sanity bounds")

        metrics = {
            "radial_displacement": radial_displacement,
            "max_mises": max_mises,
        }
        write_json(os.path.join(output_dir, "metrics.json"), metrics)
        write_json(
            os.path.join(output_dir, "native_audit.json"),
            {
                "software": "Abaqus/Standard Learning Edition 2025",
                "model_name": MODEL_NAME,
                "job_name": JOB_NAME,
                "job_status": str(job.status),
                "odb_job_status": str(getattr(odb.diagnosticData, "jobStatus", "")),
                "completed_by_status": completed_by_status,
                "completed_by_sta": completed_by_sta,
                "step_name": STEP_NAME,
                "frames": len(step.frames),
                "nodes": len(part.nodes),
                "elements": len(part.elements),
                "element_types": sorted(set(str(element.type) for element in part.elements)),
                "expected_integration_points_per_element": expected_ip,
                "sets": {
                    name: sorted(int(node.label) for node in part.sets[name].nodes)
                    for name in ("ALLNODES", "INNER", "OUTER", "ZMIN", "ZMAX")
                },
                "field_counts": {
                    name: len(frame.fieldOutputs[name].values) for name in required_fields
                },
                "stress_element_coverage": sorted(stress_element_labels),
                "stress_integration_points_per_element": stress_counts,
                "inner_midpoint_label": midpoint_label,
                "inner_labels": sorted(inner_labels),
                "loads": load_rows,
                "total_cf1_n": builtins.sum(row["cf1_n"] for row in load_rows),
                "expected_total_cf1_n": expected_total,
                "metrics": metrics,
            },
        )
    finally:
        odb.close()

    print("TASK02_ABAQUS_GENERATION_OK")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[-1] in ("CAX4", "CAX4R"):
        build_and_solve(sys.argv[-2], sys.argv[-1])
    else:
        build_and_solve(sys.argv[-1])
