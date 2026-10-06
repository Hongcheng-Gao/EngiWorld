# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import hashlib
import json
import math
import os
import re
import sys
import traceback

from abaqus import Mdb
from abaqusConstants import (
    ANALYSIS,
    CARTESIAN,
    C3D8R,
    CONSTANT_THROUGH_THICKNESS,
    DEFORMABLE_BODY,
    FINER,
    HEX,
    INTEGRATION_POINT,
    ISOTROPIC,
    OFF,
    ON,
    PERCENTAGE,
    SINGLE,
    STANDARD,
    STRUCTURED,
    THREE_D,
    UNIFORM,
    UNSET,
)
import mesh
import regionToolset
from odbAccess import openOdb


TASK_ID = "c-open-abaqus-ansys-autocad-task-17-windows"
SOFTWARE = "Abaqus/Standard Learning Edition 2025"
JOB_NAME = "gt_task_17_abaqus"
MODEL_NAME = "Model-Restrained-Thermal-Bar"
PART_NAME = "Steel-Bar"
INSTANCE_NAME = "STEEL-BAR-1"
STEP_NAME = "Static-Thermal-Strain"
MATERIAL_NAME = "Steel"
SECTION_NAME = "Steel-Section"


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def close(actual, expected, rel=1.0e-8, absolute=1.0e-10):
    return finite(actual) and abs(float(actual) - float(expected)) <= builtins.max(
        absolute, rel * builtins.max(abs(float(actual)), abs(float(expected)))
    )


def write_json(path, payload):
    with open(path, "w") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def artifact(path):
    return {"name": os.path.basename(path), "size": os.path.getsize(path), "sha256": sha256(path)}


def repository_item(repository, name):
    target = str(name).upper()
    for key in repository.keys():
        if str(key).upper() == target:
            return repository[key]
    raise KeyError(name)


def node_rows(nodes):
    rows = []
    for node in nodes:
        coordinates = tuple(float(value) for value in node.coordinates[:3])
        rows.append((int(node.label), coordinates))
    return rows


def select_nodes(container, x_min, x_max, y_min, y_max, z_min, z_max, expected, label):
    nodes = container.nodes.getByBoundingBox(
        xMin=x_min, xMax=x_max, yMin=y_min, yMax=y_max, zMin=z_min, zMax=z_max
    )
    if len(nodes) != expected:
        raise RuntimeError("expected %s %s nodes, got %s" % (expected, label, len(nodes)))
    return nodes


def parse_input(path):
    with open(path, "r", errors="replace") as stream:
        text = stream.read()
    upper = text.upper()
    element_types = sorted(set(re.findall(r"\*ELEMENT\s*,[^\n]*TYPE\s*=\s*([^,\s]+)", upper)))
    element_count = 0
    in_element = False
    for line in upper.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            in_element = stripped.startswith("*ELEMENT")
            continue
        if in_element and stripped and stripped.split(",", 1)[0].strip().isdigit():
            element_count += 1
    boundary_rows = []
    in_boundary = False
    for line in upper.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            in_boundary = stripped.startswith("*BOUNDARY")
            continue
        if not in_boundary or not stripped:
            continue
        fields = [value.strip() for value in stripped.split(",")]
        if len(fields) < 2:
            continue
        first_dof = int(fields[1])
        last_dof = int(fields[2]) if len(fields) > 2 and fields[2] else first_dof
        magnitude = float(fields[3]) if len(fields) > 3 and fields[3] else 0.0
        boundary_rows.append({"set": fields[0], "first_dof": first_dof, "last_dof": last_dof, "magnitude": magnitude})
    forbidden_keywords = []
    for keyword in ("*CLOAD", "*DLOAD", "*DSLOAD", "*BODY FORCE", "*GRAVITY", "*INITIAL CONDITIONS, TYPE=STRESS", "*INCLUDE", "*USER MATERIAL", "*EQUATION", "*COUPLING", "*CONTACT PAIR"):
        if keyword in upper:
            forbidden_keywords.append(keyword)
    if element_types != ["C3D8R"] or element_count != 80:
        raise RuntimeError("Abaqus input mesh mismatch: %r %s" % (element_types, element_count))
    if forbidden_keywords:
        raise RuntimeError("Abaqus input contains forbidden keywords: %r" % forbidden_keywords)
    if "*STATIC" not in upper or "*SOLID SECTION" not in upper:
        raise RuntimeError("Abaqus input lacks static step or solid section")
    if not re.search(r"210000(?:\.0*)?\s*,\s*0\.3", upper):
        raise RuntimeError("Abaqus input lacks the required elastic constants")
    if not re.search(r"\*EXPANSION[^\n]*ZERO\s*=\s*20(?:\.0*)?", upper) or "1.5E-05" not in upper:
        raise RuntimeError("Abaqus input lacks alpha=1.5e-5 and zero=20 expansion")
    if "20." not in upper or "100." not in upper or "*TEMPERATURE" not in upper:
        raise RuntimeError("Abaqus input lacks the 20 to 100 C prescribed temperature history")
    expected_dofs = sorted([(1, 1), (2, 2), (3, 3), (3, 3)])
    actual_dofs = sorted((row["first_dof"], row["last_dof"]) for row in boundary_rows)
    if actual_dofs != expected_dofs or any(abs(row["magnitude"]) > 1.0e-12 for row in boundary_rows):
        raise RuntimeError("Abaqus input boundary rows are not one U1 region plus U2/U3/U3 anchors: %r" % boundary_rows)
    return {
        "sha256": sha256(path),
        "element_types": element_types,
        "element_count": element_count,
        "boundary_rows": boundary_rows,
        "forbidden_keywords": forbidden_keywords,
        "has_static_keyword": True,
        "has_solid_section": True,
        "elastic_constants_verified": True,
        "thermal_expansion_verified": True,
        "temperature_history_verified": True,
    }


def create_and_solve(output_dir):
    if os.path.exists(output_dir):
        if not os.path.isdir(output_dir) or os.listdir(output_dir):
            raise RuntimeError("output directory must be absent or empty: %s" % output_dir)
    else:
        os.makedirs(output_dir)
    os.chdir(output_dir)
    cae_path = os.path.join(output_dir, JOB_NAME + ".cae")
    odb_path = os.path.join(output_dir, JOB_NAME + ".odb")
    inp_path = os.path.join(output_dir, JOB_NAME + ".inp")
    metrics_path = os.path.join(output_dir, "metrics.json")

    database = Mdb()
    database.models.changeKey(fromName="Model-1", toName=MODEL_NAME)
    model = database.models[MODEL_NAME]
    model.setValues(description="Task-17 3D steel bar with fully restrained axial thermal expansion")

    sketch = model.ConstrainedSketch(name="Bar-Profile", sheetSize=160.0)
    sketch.rectangle(point1=(0.0, 0.0), point2=(100.0, 10.0))
    part = model.Part(name=PART_NAME, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sketch, depth=10.0)
    del model.sketches["Bar-Profile"]
    if len(part.cells) != 1:
        raise RuntimeError("bar geometry is not one solid cell")

    steel = model.Material(name=MATERIAL_NAME)
    steel.Elastic(table=((210000.0, 0.3),))
    steel.Expansion(type=ISOTROPIC, zero=20.0, table=((1.5e-5,),))
    model.HomogeneousSolidSection(name=SECTION_NAME, material=MATERIAL_NAME)
    part.SectionAssignment(region=regionToolset.Region(cells=part.cells), sectionName=SECTION_NAME)

    part.seedPart(size=5.0, deviationFactor=0.1, minSizeFactor=0.1)
    part.setMeshControls(regions=part.cells, elemShape=HEX, technique=STRUCTURED)
    part.setElementType(regions=(part.cells,), elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
    part.generateMesh()
    rows = node_rows(part.nodes)
    element_types = sorted(set(str(element.type).upper() for element in part.elements))
    unique_x = sorted(set(round(row[1][0], 8) for row in rows))
    unique_y = sorted(set(round(row[1][1], 8) for row in rows))
    unique_z = sorted(set(round(row[1][2], 8) for row in rows))
    if len(part.nodes) != 189 or len(part.elements) != 80 or element_types != ["C3D8R"]:
        raise RuntimeError("expected 189-node/80-element C3D8R mesh")
    if unique_x != [float(value) for value in range(0, 101, 5)] or unique_y != [0.0, 5.0, 10.0] or unique_z != [0.0, 5.0, 10.0]:
        raise RuntimeError("structured 5 mm mesh coordinates are wrong")

    tolerance = 1.0e-6
    left_nodes = select_nodes(part, -tolerance, tolerance, -tolerance, 10.0 + tolerance, -tolerance, 10.0 + tolerance, 9, "left-end")
    right_nodes = select_nodes(part, 100.0 - tolerance, 100.0 + tolerance, -tolerance, 10.0 + tolerance, -tolerance, 10.0 + tolerance, 9, "right-end")
    anchor_a_nodes = select_nodes(part, -tolerance, tolerance, -tolerance, tolerance, -tolerance, tolerance, 1, "anchor-A")
    anchor_b_nodes = select_nodes(part, -tolerance, tolerance, 10.0 - tolerance, 10.0 + tolerance, -tolerance, tolerance, 1, "anchor-B")
    part.Set(name="ALL_BAR_NODES", nodes=part.nodes)
    part.Set(name="LEFT_END_NODES", nodes=left_nodes)
    part.Set(name="RIGHT_END_NODES", nodes=right_nodes)
    part.Set(name="BOTH_END_NODES", nodes=left_nodes + right_nodes)
    part.Set(name="ANCHOR_A", nodes=anchor_a_nodes)
    part.Set(name="ANCHOR_B", nodes=anchor_b_nodes)

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    instance = assembly.Instance(name=INSTANCE_NAME, part=part, dependent=ON)
    model.StaticStep(name=STEP_NAME, previous="Initial", nlgeom=OFF, description="Static response to prescribed uniform temperature rise")
    model.DisplacementBC(name="BC-End-Faces-U1", createStepName="Initial", region=instance.sets["BOTH_END_NODES"], u1=0.0, u2=UNSET, u3=UNSET)
    model.DisplacementBC(name="BC-Anchor-A-U2", createStepName="Initial", region=instance.sets["ANCHOR_A"], u1=UNSET, u2=0.0, u3=UNSET)
    model.DisplacementBC(name="BC-Anchor-A-U3", createStepName="Initial", region=instance.sets["ANCHOR_A"], u1=UNSET, u2=UNSET, u3=0.0)
    model.DisplacementBC(name="BC-Anchor-B-U3", createStepName="Initial", region=instance.sets["ANCHOR_B"], u1=UNSET, u2=UNSET, u3=0.0)
    temperature = model.Temperature(
        name="Uniform-Bar-Temperature",
        createStepName="Initial",
        region=instance.sets["ALL_BAR_NODES"],
        distributionType=UNIFORM,
        crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
        magnitudes=(20.0,),
    )
    temperature.setValuesInStep(stepName=STEP_NAME, magnitudes=(100.0,))
    assembly.regenerate()

    job = database.Job(
        name=JOB_NAME,
        model=MODEL_NAME,
        type=ANALYSIS,
        description="Task-17 Abaqus 2025 LE native ground truth",
        explicitPrecision=SINGLE,
        nodalOutputPrecision=SINGLE,
        memory=90,
        memoryUnits=PERCENTAGE,
        numCpus=1,
        numDomains=1,
    )
    database.saveAs(pathName=cae_path)
    job.writeInput(consistencyChecking=ON)
    input_checks = parse_input(inp_path)
    job.submit(consistencyChecking=ON)
    job.waitForCompletion()
    database.saveAs(pathName=cae_path)

    if not os.path.isfile(odb_path) or os.path.getsize(odb_path) == 0:
        raise RuntimeError("Abaqus job did not create a nonempty ODB")
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        status = str(getattr(odb.diagnosticData, "jobStatus", "")).upper()
        if "COMPLETED" not in status:
            raise RuntimeError("Abaqus ODB job did not complete: %s" % status)
        odb_instance = repository_item(odb.rootAssembly.instances, INSTANCE_NAME)
        odb_step = repository_item(odb.steps, STEP_NAME)
        if not odb_step.frames:
            raise RuntimeError("Abaqus static step has no frames")
        frame = odb_step.frames[-1]
        if any(name not in frame.fieldOutputs for name in ("S", "U", "RF")):
            raise RuntimeError("Abaqus ODB lacks S, U, or RF")
        stress_values = frame.fieldOutputs["S"].getSubset(position=INTEGRATION_POINT).values
        s11_values = [float(value.data[0]) for value in stress_values if str(value.instance.name).upper() == INSTANCE_NAME and finite(value.data[0])]
        mises_values = [float(value.mises) for value in stress_values if str(value.instance.name).upper() == INSTANCE_NAME and finite(value.mises)]
        if len(s11_values) != 80 or len(mises_values) != 80:
            raise RuntimeError("Abaqus integration-point stress field is incomplete")
        thermal_stress = builtins.max(abs(value) for value in s11_values)
        if not close(thermal_stress, 252.0, rel=1.0e-5, absolute=1.0e-4):
            raise RuntimeError("Abaqus thermal stress is wrong: %s" % thermal_stress)

        coordinate_by_label = dict((int(node.label), tuple(float(value) for value in node.coordinates[:3])) for node in odb_instance.nodes)
        left_labels = set(label for label, point in coordinate_by_label.items() if abs(point[0]) <= tolerance)
        right_labels = set(label for label, point in coordinate_by_label.items() if abs(point[0] - 100.0) <= tolerance)
        rf_values = [value for value in frame.fieldOutputs["RF"].values if str(value.instance.name).upper() == INSTANCE_NAME]
        rf1_by_label = dict((int(value.nodeLabel), float(value.data[0])) for value in rf_values)
        left_reaction = builtins.sum([rf1_by_label.get(label, 0.0) for label in left_labels])
        right_reaction = builtins.sum([rf1_by_label.get(label, 0.0) for label in right_labels])
        reaction_force = builtins.max(abs(left_reaction), abs(right_reaction))
        if not close(reaction_force, 25200.0, rel=1.0e-5, absolute=1.0e-2):
            raise RuntimeError("Abaqus end reaction is wrong: %s" % reaction_force)
        if not close(left_reaction + right_reaction, 0.0, rel=0.0, absolute=1.0e-2):
            raise RuntimeError("Abaqus end reactions are not balanced")

        displacement_values = [value for value in frame.fieldOutputs["U"].values if str(value.instance.name).upper() == INSTANCE_NAME]
        max_abs_u1 = builtins.max(abs(float(value.data[0])) for value in displacement_values)
        max_abs_u2 = builtins.max(abs(float(value.data[1])) for value in displacement_values)
        max_abs_u3 = builtins.max(abs(float(value.data[2])) for value in displacement_values)
        if max_abs_u1 > 1.0e-8 or not close(max_abs_u2, 0.0156, rel=1.0e-4, absolute=1.0e-6) or not close(max_abs_u3, 0.0156, rel=1.0e-4, absolute=1.0e-6):
            raise RuntimeError("Abaqus displacement field is inconsistent with free lateral thermal expansion")
        result_audit = {
            "job_status": status,
            "step_name": str(odb_step.name),
            "frame_count": len(odb_step.frames),
            "final_time": float(frame.frameValue),
            "odb_node_count": len(odb_instance.nodes),
            "odb_element_count": len(odb_instance.elements),
            "odb_element_types": sorted(set(str(element.type).upper() for element in odb_instance.elements)),
            "s11_min_mpa": builtins.min(s11_values),
            "s11_max_mpa": builtins.max(s11_values),
            "mises_max_mpa": builtins.max(mises_values),
            "left_sum_rf1_n": left_reaction,
            "right_sum_rf1_n": right_reaction,
            "max_abs_u1_mm": max_abs_u1,
            "max_abs_u2_mm": max_abs_u2,
            "max_abs_u3_mm": max_abs_u3,
        }
    finally:
        odb.close()

    metrics = {"thermal_stress": thermal_stress, "reaction_force": reaction_force}
    write_json(metrics_path, metrics)
    audit = {
        "schema_version": 2,
        "task_id": TASK_ID,
        "software": SOFTWARE,
        "units": "N-mm-MPa-degC",
        "ok": True,
        "model": {
            "name": MODEL_NAME,
            "part_name": PART_NAME,
            "instance_name": INSTANCE_NAME,
            "analysis": "static_structural_with_prescribed_uniform_temperature",
            "geometry": {"cell_count": len(part.cells), "bounds_mm": {"x": [0.0, 100.0], "y": [0.0, 10.0], "z": [0.0, 10.0]}},
            "material": {"name": MATERIAL_NAME, "youngs_modulus_mpa": 210000.0, "poisson_ratio": 0.3, "alpha_per_c": 1.5e-5, "expansion_zero_c": 20.0},
            "section": {"name": SECTION_NAME, "material": MATERIAL_NAME, "assigned_cell_count": 1},
            "mesh": {"nominal_size_mm": 5.0, "technique": "STRUCTURED", "shape": "HEX", "node_count": len(part.nodes), "element_count": len(part.elements), "element_types": element_types, "unique_x_mm": unique_x, "unique_y_mm": unique_y, "unique_z_mm": unique_z},
            "sets": {"ALL_BAR_NODES": len(part.nodes), "LEFT_END_NODES": len(left_nodes), "RIGHT_END_NODES": len(right_nodes), "BOTH_END_NODES": len(left_nodes) + len(right_nodes), "ANCHOR_A": len(anchor_a_nodes), "ANCHOR_B": len(anchor_b_nodes)},
            "boundary": "U1=0 on all 18 end nodes; U2=U3=0 at (0,0,0); U3=0 at (0,10,0)",
            "initial_temperature_c": 20.0,
            "final_uniform_temperature_c": 100.0,
            "extra_mechanical_load_count": len(model.loads),
            "step": {"name": STEP_NAME, "class": "StaticStep", "previous": "Initial", "nlgeom": False},
        },
        "result": result_audit,
        "metrics": metrics,
        "input_checks": input_checks,
        "artifacts": {},
    }
    database.close()
    database = None
    audit["artifacts"] = {
        JOB_NAME + ".cae": artifact(cae_path),
        JOB_NAME + ".odb": artifact(odb_path),
        JOB_NAME + ".inp": artifact(inp_path),
        "metrics.json": artifact(metrics_path),
    }
    write_json(os.path.join(output_dir, "native_audit.json"), audit)


if __name__ == "__main__":
    output = os.path.abspath(sys.argv[-1]) if len(sys.argv) > 1 else os.getcwd()
    try:
        if len(sys.argv) < 2:
            raise RuntimeError("usage: abaqus cae noGUI=generate_task17_abaqus.py -- OUTPUT_DIR")
        create_and_solve(output)
    except Exception:
        try:
            if not os.path.isdir(output):
                os.makedirs(output)
            with open(os.path.join(output, "generation_error.txt"), "w") as stream:
                stream.write(traceback.format_exc())
        except Exception:
            pass
        raise
