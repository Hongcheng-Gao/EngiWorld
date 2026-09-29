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
    AXISYMMETRIC,
    CARTESIAN,
    CAX4R,
    DEFORMABLE_BODY,
    FINER,
    INTEGRATION_POINT,
    OFF,
    ON,
    PERCENTAGE,
    QUAD,
    SINGLE,
    STANDARD,
    STRUCTURED,
    UNSET,
)
import mesh
import regionToolset
from odbAccess import openOdb


TASK_ID = "c-open-abaqus-ansys-autocad-task-16-windows"
SOFTWARE = "Abaqus/Standard Learning Edition 2025"
JOB_NAME = "gt_task_16_abaqus"
MODEL_NAME = "Model-Axisymmetric-Thick-Cylinder"
PART_NAME = "Thick-Cylinder-Cross-Section"
INSTANCE_NAME = "THICK-CYLINDER-1"
STEP_NAME = "Static-Internal-Pressure"
MATERIAL_NAME = "Steel"
SECTION_NAME = "Steel-Section"


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def close(actual, expected, rel=1.0e-8, absolute=1.0e-10):
    return finite(actual) and abs(float(actual) - float(expected)) <= max(
        absolute, rel * max(abs(float(actual)), abs(float(expected)))
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
    return {
        "name": os.path.basename(path),
        "size": os.path.getsize(path),
        "sha256": sha256(path),
    }


def repository_item(repository, name):
    target = str(name).upper()
    for key in repository.keys():
        if str(key).upper() == target:
            return repository[key]
    raise KeyError(name)


def select_edge(part_or_instance, x_min, x_max, y_min, y_max, label):
    edges = part_or_instance.edges.getByBoundingBox(
        xMin=x_min,
        xMax=x_max,
        yMin=y_min,
        yMax=y_max,
        zMin=-1.0e-6,
        zMax=1.0e-6,
    )
    if len(edges) != 1:
        raise RuntimeError("expected one %s edge, got %s" % (label, len(edges)))
    return edges


def keyword_blocks(text, keyword):
    wanted = keyword.upper()
    lines = text.replace("\r\n", "\n").split("\n")
    blocks = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("*") and not stripped.startswith("**"):
            header = stripped.upper()
            key = header[1:].split(",", 1)[0].strip()
            if key == wanted:
                data = []
                index += 1
                while index < len(lines):
                    row = lines[index].strip()
                    if row.startswith("*"):
                        break
                    if row and not row.startswith("**"):
                        data.append(row)
                    index += 1
                blocks.append({"header": header, "data": data})
                continue
        index += 1
    return blocks


def inspect_input_deck(path):
    with open(path, "r", errors="replace") as stream:
        text = stream.read()

    element_types = []
    element_count = 0
    for block in keyword_blocks(text, "ELEMENT"):
        match = re.search(r"(?:^|,)\s*TYPE\s*=\s*([^,\s]+)", block["header"])
        if match:
            element_types.append(match.group(1).upper())
        for row in block["data"]:
            if row.split(",", 1)[0].strip().isdigit():
                element_count += 1

    boundary_dofs = {}
    boundary_rows = []
    for block in keyword_blocks(text, "BOUNDARY"):
        for row in block["data"]:
            fields = [value.strip() for value in row.split(",")]
            if len(fields) < 2:
                continue
            try:
                first_dof = int(fields[1])
                last_dof = int(fields[2]) if len(fields) > 2 and fields[2] else first_dof
                magnitude = float(fields[3]) if len(fields) > 3 and fields[3] else 0.0
            except Exception:
                continue
            set_name = fields[0].upper()
            boundary_rows.append(
                {
                    "set": set_name,
                    "first_dof": first_dof,
                    "last_dof": last_dof,
                    "magnitude": magnitude,
                }
            )
            boundary_dofs.setdefault(set_name, [])
            boundary_dofs[set_name].extend(range(first_dof, last_dof + 1))
    boundary_dofs = dict(
        (key, sorted(set(values))) for key, values in boundary_dofs.items()
    )

    pressure_rows = []
    for keyword in ("DSLOAD", "DLOAD"):
        for block in keyword_blocks(text, keyword):
            for row in block["data"]:
                fields = [value.strip() for value in row.split(",")]
                if len(fields) < 3:
                    continue
                try:
                    magnitude = float(fields[2])
                except Exception:
                    continue
                pressure_rows.append(
                    {
                        "keyword": keyword,
                        "region": fields[0].upper(),
                        "load_type": fields[1].upper(),
                        "magnitude": magnitude,
                    }
                )

    upper = text.upper()
    bottom_sets = [
        key for key in boundary_dofs if key.endswith(".BOTTOM_NODES") or key == "BOTTOM_NODES"
    ]
    top_sets = [
        key for key in boundary_dofs if key.endswith(".TOP_NODES") or key == "TOP_NODES"
    ]
    if len(bottom_sets) != 1 or len(top_sets) != 1:
        raise RuntimeError("input deck does not contain unique top/bottom boundary sets")
    if boundary_dofs[bottom_sets[0]] != [2] or boundary_dofs[top_sets[0]] != [2]:
        raise RuntimeError("input deck constrains a radial DOF or misses axial U2")
    matching_pressure = [
        row
        for row in pressure_rows
        if "INNER_PRESSURE_SURFACE" in row["region"]
        and row["load_type"].startswith("P")
        and close(row["magnitude"], 10.0)
    ]
    if len(matching_pressure) != 1:
        raise RuntimeError("input deck does not contain exactly one 10 MPa inner pressure")
    if sorted(set(element_types)) != ["CAX4R"] or element_count != 10:
        raise RuntimeError(
            "input deck mesh mismatch: types=%r elements=%s"
            % (sorted(set(element_types)), element_count)
        )
    if "*STATIC" not in upper or "*SOLID SECTION" not in upper:
        raise RuntimeError("input deck is missing the static step or solid section")
    if "210000" not in upper or not re.search(r"210000(?:\.0*)?\s*,\s*0\.3", upper):
        raise RuntimeError("input deck elastic constants are missing")
    return {
        "sha256": sha256(path),
        "element_types": sorted(set(element_types)),
        "element_count": element_count,
        "boundary_dofs": boundary_dofs,
        "boundary_rows": boundary_rows,
        "pressure_rows": pressure_rows,
        "has_static_keyword": "*STATIC" in upper,
        "has_solid_section": "*SOLID SECTION" in upper,
        "elastic_constants_verified": True,
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
    model.setValues(
        description=(
            "Task-16 linear-static axisymmetric thick cylinder: r=25..50 mm, "
            "z=0..10 mm, internal pressure 10 MPa"
        )
    )

    sketch = model.ConstrainedSketch(name="Axisymmetric-Cross-Section", sheetSize=140.0)
    sketch.ConstructionLine(point1=(0.0, -20.0), point2=(0.0, 30.0))
    sketch.rectangle(point1=(25.0, 0.0), point2=(50.0, 10.0))
    part = model.Part(name=PART_NAME, dimensionality=AXISYMMETRIC, type=DEFORMABLE_BODY)
    part.BaseShell(sketch=sketch)
    del model.sketches["Axisymmetric-Cross-Section"]
    if len(part.faces) != 1 or len(part.edges) != 4 or len(part.vertices) != 4:
        raise RuntimeError("axisymmetric cross-section is not one rectangular face")

    steel = model.Material(name=MATERIAL_NAME)
    steel.Elastic(table=((210000.0, 0.3),))
    model.HomogeneousSolidSection(
        name=SECTION_NAME,
        material=MATERIAL_NAME,
        thickness=None,
    )
    part.SectionAssignment(
        region=regionToolset.Region(faces=part.faces),
        sectionName=SECTION_NAME,
    )

    tolerance = 1.0e-6
    inner_edges = select_edge(
        part, 25.0 - tolerance, 25.0 + tolerance, -tolerance, 10.0 + tolerance, "inner"
    )
    outer_edges = select_edge(
        part, 50.0 - tolerance, 50.0 + tolerance, -tolerance, 10.0 + tolerance, "outer"
    )
    bottom_edges = select_edge(
        part, 25.0 - tolerance, 50.0 + tolerance, -tolerance, tolerance, "bottom"
    )
    top_edges = select_edge(
        part, 25.0 - tolerance, 50.0 + tolerance, 10.0 - tolerance, 10.0 + tolerance, "top"
    )
    part.seedEdgeByNumber(edges=inner_edges, number=2, constraint=FINER)
    part.seedEdgeByNumber(edges=outer_edges, number=2, constraint=FINER)
    part.seedEdgeByNumber(edges=bottom_edges, number=5, constraint=FINER)
    part.seedEdgeByNumber(edges=top_edges, number=5, constraint=FINER)
    part.setMeshControls(regions=part.faces, elemShape=QUAD, technique=STRUCTURED)
    part.setElementType(
        regions=(part.faces,),
        elemTypes=(mesh.ElemType(elemCode=CAX4R, elemLibrary=STANDARD),),
    )
    part.generateMesh()

    node_rows = [
        (int(node.label), tuple(float(value) for value in node.coordinates[:2]))
        for node in part.nodes
    ]
    element_types = sorted(set(str(element.type).upper() for element in part.elements))
    unique_r = sorted(set(round(row[1][0], 8) for row in node_rows))
    unique_z = sorted(set(round(row[1][1], 8) for row in node_rows))
    if len(part.nodes) != 18 or len(part.elements) != 10:
        raise RuntimeError(
            "expected 18 nodes and 10 elements, got %s and %s"
            % (len(part.nodes), len(part.elements))
        )
    if element_types != ["CAX4R"]:
        raise RuntimeError("mesh is not exclusively CAX4R: %r" % element_types)
    if unique_r != [25.0, 30.0, 35.0, 40.0, 45.0, 50.0] or unique_z != [0.0, 5.0, 10.0]:
        raise RuntimeError("structured grid coordinates are wrong: %r %r" % (unique_r, unique_z))

    inner_nodes = part.nodes.getByBoundingBox(
        xMin=25.0 - tolerance,
        xMax=25.0 + tolerance,
        yMin=-tolerance,
        yMax=10.0 + tolerance,
        zMin=-tolerance,
        zMax=tolerance,
    )
    outer_nodes = part.nodes.getByBoundingBox(
        xMin=50.0 - tolerance,
        xMax=50.0 + tolerance,
        yMin=-tolerance,
        yMax=10.0 + tolerance,
        zMin=-tolerance,
        zMax=tolerance,
    )
    bottom_nodes = part.nodes.getByBoundingBox(
        xMin=25.0 - tolerance,
        xMax=50.0 + tolerance,
        yMin=-tolerance,
        yMax=tolerance,
        zMin=-tolerance,
        zMax=tolerance,
    )
    top_nodes = part.nodes.getByBoundingBox(
        xMin=25.0 - tolerance,
        xMax=50.0 + tolerance,
        yMin=10.0 - tolerance,
        yMax=10.0 + tolerance,
        zMin=-tolerance,
        zMax=tolerance,
    )
    if len(inner_nodes) != 3 or len(outer_nodes) != 3:
        raise RuntimeError("inner/outer mesh boundary does not contain three nodes")
    if len(bottom_nodes) != 6 or len(top_nodes) != 6:
        raise RuntimeError("top/bottom mesh boundary does not contain six nodes")
    part.Set(name="INNER_NODES", nodes=inner_nodes)
    part.Set(name="OUTER_NODES", nodes=outer_nodes)
    part.Set(name="BOTTOM_NODES", nodes=bottom_nodes)
    part.Set(name="TOP_NODES", nodes=top_nodes)

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    instance = assembly.Instance(name=INSTANCE_NAME, part=part, dependent=ON)
    inner_instance_edges = select_edge(
        instance,
        25.0 - tolerance,
        25.0 + tolerance,
        -tolerance,
        10.0 + tolerance,
        "instance inner",
    )
    inner_surface = assembly.Surface(
        name="INNER_PRESSURE_SURFACE",
        side1Edges=inner_instance_edges,
    )

    model.StaticStep(
        name=STEP_NAME,
        previous="Initial",
        nlgeom=OFF,
        description="Linear static internal-pressure load step",
    )
    model.DisplacementBC(
        name="BC-Bottom-Axial",
        createStepName="Initial",
        region=instance.sets["BOTTOM_NODES"],
        u1=UNSET,
        u2=0.0,
    )
    model.DisplacementBC(
        name="BC-Top-Axial",
        createStepName="Initial",
        region=instance.sets["TOP_NODES"],
        u1=UNSET,
        u2=0.0,
    )
    model.Pressure(
        name="Internal-Pressure-10MPa",
        createStepName=STEP_NAME,
        region=inner_surface,
        magnitude=10.0,
    )
    assembly.regenerate()

    job = database.Job(
        name=JOB_NAME,
        model=MODEL_NAME,
        type=ANALYSIS,
        description="Task-16 Abaqus 2025 LE native ground truth",
        explicitPrecision=SINGLE,
        nodalOutputPrecision=SINGLE,
        memory=90,
        memoryUnits=PERCENTAGE,
        numCpus=1,
        numDomains=1,
    )
    database.saveAs(pathName=cae_path)
    job.writeInput(consistencyChecking=ON)
    input_checks = inspect_input_deck(inp_path)
    job.submit(consistencyChecking=ON)
    job.waitForCompletion()
    database.saveAs(pathName=cae_path)

    if not os.path.isfile(odb_path) or os.path.getsize(odb_path) == 0:
        raise RuntimeError("Abaqus job did not create a nonempty ODB")
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        status = str(getattr(odb.diagnosticData, "jobStatus", "")).upper()
        if "COMPLETED" not in status:
            raise RuntimeError("Abaqus ODB job status is not completed: %s" % status)
        odb_instance = repository_item(odb.rootAssembly.instances, INSTANCE_NAME)
        odb_step = repository_item(odb.steps, STEP_NAME)
        if not odb_step.frames:
            raise RuntimeError("Abaqus ODB static step has no frames")
        frame = odb_step.frames[-1]
        if "U" not in frame.fieldOutputs or "S" not in frame.fieldOutputs:
            raise RuntimeError("Abaqus ODB is missing U or S field output")

        displacement_rows = [
            value
            for value in frame.fieldOutputs["U"].values
            if str(value.instance.name).upper() == INSTANCE_NAME
        ]
        if len(displacement_rows) != len(odb_instance.nodes):
            raise RuntimeError("final U field is incomplete")
        radial_values = [float(value.data[0]) for value in displacement_rows]
        if not radial_values or any(not finite(value) for value in radial_values):
            raise RuntimeError("final radial displacement field is empty or nonfinite")
        radial_displacement = builtins.max(radial_values)
        minimum_radial_displacement = builtins.min(radial_values)
        if not 1.0e-4 < radial_displacement < 2.0e-2:
            raise RuntimeError(
                "maximum outward radial displacement is implausible: %s"
                % radial_displacement
            )
        if minimum_radial_displacement <= 0.0:
            raise RuntimeError(
                "positive inner pressure did not move every radius outward: min U1=%s"
                % minimum_radial_displacement
            )

        stress_rows = frame.fieldOutputs["S"].getSubset(position=INTEGRATION_POINT).values
        mises_values = [
            float(value.mises)
            for value in stress_rows
            if str(value.instance.name).upper() == INSTANCE_NAME and finite(value.mises)
        ]
        if not mises_values:
            raise RuntimeError("final integration-point Mises field is empty")
        max_stress = builtins.max(mises_values)
        if not 10.0 < max_stress < 100.0:
            raise RuntimeError("maximum Mises stress is implausible: %s" % max_stress)

        odb_node_rows = [
            tuple(float(value) for value in node.coordinates[:2])
            for node in odb_instance.nodes
        ]
        odb_bounds = {
            "r": [
                builtins.min(row[0] for row in odb_node_rows),
                builtins.max(row[0] for row in odb_node_rows),
            ],
            "z": [
                builtins.min(row[1] for row in odb_node_rows),
                builtins.max(row[1] for row in odb_node_rows),
            ],
        }
        result_audit = {
            "job_status": status,
            "step_name": str(odb_step.name),
            "final_time": float(frame.frameValue),
            "frame_count": len(odb_step.frames),
            "odb_node_count": len(odb_instance.nodes),
            "odb_element_count": len(odb_instance.elements),
            "odb_element_types": sorted(
                set(str(element.type).upper() for element in odb_instance.elements)
            ),
            "odb_bounds_mm": odb_bounds,
            "u_value_count": len(radial_values),
            "minimum_u1_mm": minimum_radial_displacement,
            "maximum_u1_mm": radial_displacement,
            "mises_value_count": len(mises_values),
            "maximum_mises_mpa": max_stress,
        }
    finally:
        odb.close()

    metrics = {
        "radial_displacement": radial_displacement,
        "max_stress": max_stress,
    }
    write_json(metrics_path, metrics)

    native_counts = {
        "face_count": len(part.faces),
        "edge_count": len(part.edges),
        "vertex_count": len(part.vertices),
        "node_count": len(part.nodes),
        "element_count": len(part.elements),
        "inner_node_count": len(inner_nodes),
        "outer_node_count": len(outer_nodes),
        "bottom_node_count": len(bottom_nodes),
        "top_node_count": len(top_nodes),
        "inner_pressure_edge_count": len(inner_instance_edges),
    }

    bounds_mm = {
        "r": [
            builtins.min(row[1][0] for row in node_rows),
            builtins.max(row[1][0] for row in node_rows),
        ],
        "z": [
            builtins.min(row[1][1] for row in node_rows),
            builtins.max(row[1][1] for row in node_rows),
        ],
    }
    database.close()
    database = None
    audit = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "software": SOFTWARE,
        "units": "N-mm-MPa",
        "ok": True,
        "model": {
            "name": MODEL_NAME,
            "part_name": PART_NAME,
            "instance_name": INSTANCE_NAME,
            "analysis": "linear_static_axisymmetric",
            "part_dimensionality": "AXISYMMETRIC",
            "geometry": {
                "face_count": native_counts["face_count"],
                "edge_count": native_counts["edge_count"],
                "vertex_count": native_counts["vertex_count"],
                "bounds_mm": bounds_mm,
            },
            "material": {
                "name": MATERIAL_NAME,
                "youngs_modulus_mpa": 210000.0,
                "poisson_ratio": 0.3,
            },
            "section": {
                "name": SECTION_NAME,
                "class": "HomogeneousSolidSection",
                "material": MATERIAL_NAME,
                "assigned_face_count": native_counts["face_count"],
            },
            "mesh": {
                "nominal_size_mm": 5.0,
                "technique": "STRUCTURED",
                "shape": "QUAD",
                "radial_divisions": 5,
                "axial_divisions": 2,
                "node_count": native_counts["node_count"],
                "element_count": native_counts["element_count"],
                "element_types": element_types,
                "unique_r_mm": unique_r,
                "unique_z_mm": unique_z,
            },
            "sets": {
                "INNER_NODES": native_counts["inner_node_count"],
                "OUTER_NODES": native_counts["outer_node_count"],
                "BOTTOM_NODES": native_counts["bottom_node_count"],
                "TOP_NODES": native_counts["top_node_count"],
            },
            "boundary_conditions": {
                "BC-Bottom-Axial": {
                    "class": "DisplacementBC",
                    "create_step": "Initial",
                    "region": "BOTTOM_NODES",
                    "u1": "UNSET",
                    "u2": 0.0,
                },
                "BC-Top-Axial": {
                    "class": "DisplacementBC",
                    "create_step": "Initial",
                    "region": "TOP_NODES",
                    "u1": "UNSET",
                    "u2": 0.0,
                },
            },
            "pressure": {
                "name": "Internal-Pressure-10MPa",
                "class": "Pressure",
                "create_step": STEP_NAME,
                "region": "INNER_PRESSURE_SURFACE",
                "edge_count": native_counts["inner_pressure_edge_count"],
                "radius_mm": 25.0,
                "axial_extent_mm": [0.0, 10.0],
                "magnitude_mpa": 10.0,
                "direction": "positive radial displacement from the inner wall",
            },
            "step": {
                "name": STEP_NAME,
                "class": "StaticStep",
                "previous": "Initial",
                "nlgeom": False,
            },
        },
        "result": result_audit,
        "metrics": metrics,
        "input_checks": input_checks,
        "artifacts": {
            JOB_NAME + ".cae": artifact(cae_path),
            JOB_NAME + ".odb": artifact(odb_path),
            JOB_NAME + ".inp": artifact(inp_path),
            "metrics.json": artifact(metrics_path),
        },
    }
    write_json(os.path.join(output_dir, "native_audit.json"), audit)


if __name__ == "__main__":
    output = os.path.abspath(sys.argv[-1]) if len(sys.argv) > 1 else os.getcwd()
    try:
        if len(sys.argv) < 2:
            raise RuntimeError(
                "usage: abaqus cae noGUI=generate_task16_abaqus.py -- OUTPUT_DIR"
            )
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
