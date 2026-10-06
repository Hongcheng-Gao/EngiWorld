# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import json
import math
import os
import sys

from abaqus import mdb
from abaqusConstants import (
    CARTESIAN,
    COMPLETED,
    DEFORMABLE_BODY,
    FINER,
    FREE,
    GENERAL,
    OFF,
    ON,
    QUAD_DOMINATED,
    S3,
    S4R,
    SIMPSON,
    STANDARD,
    THREE_D,
    UNIFORM,
    UNSET,
)
from caeModules import *
from mesh import ElemType
from odbAccess import openOdb


MODEL_NAME = "Model-FlangeHole"
PART_NAME = "FlangeHolePlate"
INSTANCE_NAME = "PLATE-1"
SECTION_NAME = "Plate-Section"
STEP_NAME = "Step-HoleTension"
JOB_NAME = "Job-FlangeHole"
EDGE_LOAD = 8.0
THICKNESS = 1.0


def write_json(path, payload):
    with open(path, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)


def clean_output(output_dir):
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


def coordinates(node):
    values = tuple(float(value) for value in node.coordinates)
    if len(values) == 2:
        values = values + (0.0,)
    return values[:3]


def close(actual, expected, rel=1.0e-7, abs_tol=1.0e-7):
    return math.isclose(float(actual), float(expected), rel_tol=rel, abs_tol=abs_tol)


def require_vertices(part, name, x, y, tol=1.0e-6):
    vertices = part.vertices.getByBoundingBox(
        xMin=x - tol,
        xMax=x + tol,
        yMin=y - tol,
        yMax=y + tol,
        zMin=-tol,
        zMax=tol,
    )
    if len(vertices) != 1:
        raise RuntimeError("%s vertex lookup returned %d vertices" % (name, len(vertices)))
    part.Set(name=name, vertices=vertices)


def build_and_solve(output_dir):
    output_dir = os.path.abspath(output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    clean_output(output_dir)
    os.chdir(output_dir)

    if MODEL_NAME in mdb.models:
        del mdb.models[MODEL_NAME]
    model = mdb.Model(name=MODEL_NAME)
    for name in list(mdb.models.keys()):
        if name != MODEL_NAME:
            del mdb.models[name]

    sketch = model.ConstrainedSketch(name="Plate-Profile", sheetSize=400.0)
    sketch.rectangle(point1=(0.0, 0.0), point2=(120.0, 240.0))
    sketch.CircleByCenterPerimeter(center=(60.0, 120.0), point1=(66.0, 120.0))
    part = model.Part(name=PART_NAME, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseShell(sketch=sketch)
    del model.sketches["Plate-Profile"]

    tol = 1.0e-5
    left_edges = part.edges.getByBoundingBox(
        xMin=-tol, xMax=tol, yMin=-tol, yMax=240.0 + tol, zMin=-tol, zMax=tol
    )
    right_edges = part.edges.getByBoundingBox(
        xMin=120.0 - tol,
        xMax=120.0 + tol,
        yMin=-tol,
        yMax=240.0 + tol,
        zMin=-tol,
        zMax=tol,
    )
    hole_edges = part.edges.getByBoundingBox(
        xMin=54.0 - tol,
        xMax=66.0 + tol,
        yMin=114.0 - tol,
        yMax=126.0 + tol,
        zMin=-tol,
        zMax=tol,
    )
    if len(left_edges) != 1 or len(right_edges) != 1 or not hole_edges:
        raise RuntimeError("plate edge classification failed")
    part.Set(name="LEFT_EDGE", edges=left_edges)
    part.Set(name="RIGHT_EDGE", edges=right_edges)
    part.Set(name="HOLE_EDGE", edges=hole_edges)
    part.Surface(name="LEFT_EDGE_SURFACE", side1Edges=left_edges)
    part.Surface(name="RIGHT_EDGE_SURFACE", side1Edges=right_edges)
    require_vertices(part, "BOTTOM_LEFT", 0.0, 0.0)
    require_vertices(part, "BOTTOM_RIGHT", 120.0, 0.0)
    require_vertices(part, "TOP_LEFT", 0.0, 240.0)

    steel = model.Material(name="Steel")
    steel.Elastic(table=((210000.0, 0.3),))
    model.HomogeneousShellSection(
        name=SECTION_NAME,
        material="Steel",
        thickness=THICKNESS,
        integrationRule=SIMPSON,
        numIntPts=5,
    )
    all_faces = part.Set(name="PLATE_REGION", faces=part.faces[:])
    part.SectionAssignment(region=all_faces, sectionName=SECTION_NAME)

    part.setMeshControls(regions=part.faces[:], elemShape=QUAD_DOMINATED, technique=FREE)
    part.seedPart(size=10.0, deviationFactor=0.1, minSizeFactor=0.1)
    part.seedEdgeBySize(
        edges=hole_edges,
        size=2.4,
        deviationFactor=0.1,
        minSizeFactor=0.1,
        constraint=FINER,
    )
    part.setElementType(
        regions=(part.faces[:],),
        elemTypes=(
            ElemType(elemCode=S4R, elemLibrary=STANDARD),
            ElemType(elemCode=S3, elemLibrary=STANDARD),
        ),
    )
    part.generateMesh()

    left_nodes = part.nodes.getByBoundingBox(
        xMin=-tol, xMax=tol, yMin=-tol, yMax=240.0 + tol, zMin=-tol, zMax=tol
    )
    right_nodes = part.nodes.getByBoundingBox(
        xMin=120.0 - tol,
        xMax=120.0 + tol,
        yMin=-tol,
        yMax=240.0 + tol,
        zMin=-tol,
        zMax=tol,
    )
    hole_node_labels = []
    for node in part.nodes:
        point = coordinates(node)
        if abs(math.hypot(point[0] - 60.0, point[1] - 120.0) - 6.0) <= 1.0e-3:
            hole_node_labels.append(int(node.label))
    if len(left_nodes) < 3 or len(right_nodes) < 3 or len(hole_node_labels) < 12:
        raise RuntimeError("edge-node classification failed")
    part.Set(name="LEFT_EDGE_NODES", nodes=left_nodes)
    part.Set(name="RIGHT_EDGE_NODES", nodes=right_nodes)
    part.Set(
        name="HOLE_EDGE_NODES",
        nodes=part.nodes.sequenceFromLabels(tuple(hole_node_labels)),
    )
    hole_label_set = set(hole_node_labels)
    hole_elements = [
        int(element.label)
        for element in part.elements
        if any(int(label) in hole_label_set for label in element.connectivity)
    ]
    if not hole_elements:
        raise RuntimeError("hole-adjacent elements were not found")
    part.Set(
        name="HOLE_ADJACENT_ELEMENTS",
        elements=part.elements.sequenceFromLabels(tuple(hole_elements)),
    )

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    instance = assembly.Instance(name=INSTANCE_NAME, part=part, dependent=ON)

    model.StaticStep(name=STEP_NAME, previous="Initial", nlgeom=OFF)
    for name in list(model.fieldOutputRequests.keys()):
        del model.fieldOutputRequests[name]
    model.FieldOutputRequest(
        name="F-Output-Task03",
        createStepName=STEP_NAME,
        variables=("U", "RF", "S"),
        sectionPoints=(1, 2, 3, 4, 5),
    )
    model.ShellEdgeLoad(
        name="Load-Left",
        createStepName=STEP_NAME,
        region=instance.surfaces["LEFT_EDGE_SURFACE"],
        magnitude=EDGE_LOAD,
        distributionType=UNIFORM,
        traction=GENERAL,
        directionVector=((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
        follower=OFF,
    )
    model.ShellEdgeLoad(
        name="Load-Right",
        createStepName=STEP_NAME,
        region=instance.surfaces["RIGHT_EDGE_SURFACE"],
        magnitude=EDGE_LOAD,
        distributionType=UNIFORM,
        traction=GENERAL,
        directionVector=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        follower=OFF,
    )
    model.DisplacementBC(
        name="BC-BottomLeft",
        createStepName="Initial",
        region=instance.sets["BOTTOM_LEFT"],
        u1=0.0,
        u2=0.0,
        u3=0.0,
    )
    model.DisplacementBC(
        name="BC-BottomRight",
        createStepName="Initial",
        region=instance.sets["BOTTOM_RIGHT"],
        u1=UNSET,
        u2=0.0,
        u3=0.0,
    )
    model.DisplacementBC(
        name="BC-TopLeft",
        createStepName="Initial",
        region=instance.sets["TOP_LEFT"],
        u1=UNSET,
        u2=UNSET,
        u3=0.0,
    )

    job = mdb.Job(
        name=JOB_NAME,
        model=MODEL_NAME,
        description="CLI task-03 shell plate with a central hole under edge tension",
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

    odb_path = os.path.join(output_dir, JOB_NAME + ".odb")
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        odb_status = str(getattr(odb.diagnosticData, "jobStatus", ""))
        if odb_status.upper() != "JOB_STATUS_COMPLETED_SUCCESSFULLY":
            raise RuntimeError("ODB does not report completed successfully")
        step = odb.steps[STEP_NAME]
        if len(step.frames) < 2:
            raise RuntimeError("ODB has too few frames")
        frame = step.frames[-1]
        odb_instance = odb.rootAssembly.instances[INSTANCE_NAME]
        for field_name in ("U", "S"):
            if field_name not in frame.fieldOutputs.keys():
                raise RuntimeError("missing ODB field: " + field_name)

        displacement_by_label = {}
        for value in frame.fieldOutputs["U"].values:
            displacement_by_label[int(value.nodeLabel)] = tuple(
                float(component) for component in value.data
            )
        left_labels = [
            int(node.label) for node in odb_instance.nodeSets["LEFT_EDGE_NODES"].nodes
        ]
        right_labels = [
            int(node.label) for node in odb_instance.nodeSets["RIGHT_EDGE_NODES"].nodes
        ]
        if not left_labels or not right_labels:
            raise RuntimeError("loaded edge node sets are empty")
        left_mean_u1 = builtins.sum(displacement_by_label[label][0] for label in left_labels) / float(
            len(left_labels)
        )
        right_mean_u1 = builtins.sum(
            displacement_by_label[label][0] for label in right_labels
        ) / float(len(right_labels))
        edge_displacement = right_mean_u1 - left_mean_u1

        mises_values = []
        stress_element_labels = set()
        section_points = set()
        stress_count_by_element = {}
        for value in frame.fieldOutputs["S"].values:
            element_label = int(value.elementLabel)
            stress_element_labels.add(element_label)
            stress_count_by_element[element_label] = stress_count_by_element.get(element_label, 0) + 1
            section_point = getattr(value, "sectionPoint", None)
            if section_point is not None:
                section_points.add(int(section_point.number))
            try:
                mises = float(value.mises)
                if math.isfinite(mises):
                    mises_values.append(mises)
            except Exception:
                pass
        if not mises_values or len(stress_element_labels) != len(part.elements):
            raise RuntimeError("stress output does not cover the complete shell mesh")
        if not section_points:
            raise RuntimeError("stress output does not identify shell section points")
        max_mises = max(mises_values)
        stress_concentration_proxy = max_mises / (EDGE_LOAD / THICKNESS)
        if not (
            1.5 < stress_concentration_proxy < 6.0
            and 12.0 < max_mises < 60.0
            and 0.002 < edge_displacement < 0.02
        ):
            raise RuntimeError("native result is outside physical sanity bounds")

        metrics = {
            "stress_concentration_proxy": stress_concentration_proxy,
            "max_mises": max_mises,
            "edge_displacement": edge_displacement,
        }
        write_json(os.path.join(output_dir, "metrics.json"), metrics)
        write_json(
            os.path.join(output_dir, "native_audit.json"),
            {
                "software": "Abaqus/Standard Learning Edition 2025",
                "model_name": MODEL_NAME,
                "part_name": PART_NAME,
                "instance_name": INSTANCE_NAME,
                "dependent_instance": True,
                "job_name": JOB_NAME,
                "job_status": str(job.status),
                "odb_job_status": odb_status,
                "completed_by_status": completed_by_status,
                "completed_by_sta": completed_by_sta,
                "step_name": STEP_NAME,
                "frames": len(step.frames),
                "geometry_mm": {
                    "x_bounds": [0.0, 120.0],
                    "y_bounds": [0.0, 240.0],
                    "hole_center": [60.0, 120.0],
                    "hole_radius": 6.0,
                },
                "material": {"name": "Steel", "youngs_modulus_mpa": 210000.0, "poissons_ratio": 0.3},
                "section": {
                    "name": SECTION_NAME,
                    "thickness_mm": THICKNESS,
                    "integration_rule": "SIMPSON",
                    "through_thickness_points": 5,
                },
                "loads": {
                    "left": {"magnitude_n_per_mm": EDGE_LOAD, "direction": [-1.0, 0.0, 0.0], "resultant_n": -1920.0},
                    "right": {"magnitude_n_per_mm": EDGE_LOAD, "direction": [1.0, 0.0, 0.0], "resultant_n": 1920.0},
                },
                "boundary_conditions": {
                    "bottom_left": {"coordinates": [0.0, 0.0, 0.0], "fixed": ["U1", "U2", "U3"]},
                    "bottom_right": {"coordinates": [120.0, 0.0, 0.0], "fixed": ["U2", "U3"]},
                    "top_left": {"coordinates": [0.0, 240.0, 0.0], "fixed": ["U3"]},
                },
                "mesh": {
                    "global_seed_mm": 10.0,
                    "hole_edge_seed_mm": 2.4,
                    "nodes": len(part.nodes),
                    "elements": len(part.elements),
                    "element_types": sorted(set(str(element.type) for element in part.elements)),
                    "left_edge_nodes": len(left_labels),
                    "right_edge_nodes": len(right_labels),
                    "hole_edge_nodes": len(hole_node_labels),
                    "hole_adjacent_elements": sorted(hole_elements),
                },
                "result": {
                    "section_points": sorted(section_points),
                    "stress_element_coverage": sorted(stress_element_labels),
                    "stress_values_per_element": stress_count_by_element,
                    "left_mean_u1_mm": left_mean_u1,
                    "right_mean_u1_mm": right_mean_u1,
                },
                "metrics": metrics,
            },
        )
    finally:
        odb.close()

    print("TASK03_ABAQUS_GENERATION_OK")


if __name__ == "__main__":
    build_and_solve(sys.argv[-1])
