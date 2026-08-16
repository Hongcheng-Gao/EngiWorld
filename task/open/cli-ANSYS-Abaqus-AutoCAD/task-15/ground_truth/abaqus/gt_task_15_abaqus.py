# -*- coding: utf-8 -*-
from __future__ import print_function

import builtins
import hashlib
import json
import math
import os
import sys
import traceback

from abaqus import Mdb
from abaqusConstants import (
    B31,
    CARTESIAN,
    DEFAULT,
    DEFORMABLE_BODY,
    DURING_ANALYSIS,
    FINER,
    FROM_SECTION,
    LINEAR,
    MIDDLE_SURFACE,
    N1_COSINES,
    OFF,
    ON,
    PERCENTAGE,
    SINGLE,
    STANDARD,
    THREE_D,
)
import mesh
from odbAccess import openOdb


TASK_ID = "c-open-abaqus-ansys-autocad-task-15-windows"
MODEL_NAME = "Model-Fixed-Fixed-Beam"
PART_NAME = "Beam"
INSTANCE_NAME = "BEAM-1"
PROFILE_NAME = "Profile-10x10"
SECTION_NAME = "Section-10x10"
MATERIAL_NAME = "Steel"
STEP_NAME = "Step-Frequency"
JOB_NAME = "gt_task_15_abaqus"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def primitive(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return dict((str(key), primitive(item)) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return [primitive(item) for item in value]
    try:
        return float(value)
    except Exception:
        return str(value)


def repository_item(repository, name):
    target = str(name).upper()
    for key in repository.keys():
        if str(key).upper() == target:
            return repository[key]
    raise KeyError(name)


def artifact(path):
    return {
        "name": os.path.basename(path),
        "size": os.path.getsize(path),
        "sha256": sha256(path),
    }


def node_rows(nodes):
    return [
        (int(node.label), tuple(float(value) for value in node.coordinates[:3]))
        for node in nodes
    ]


def bounds(rows):
    if not rows:
        return None
    coordinates = [row[1] for row in rows]
    return {
        axis: [
            min(values[index] for values in coordinates),
            max(values[index] for values in coordinates),
        ]
        for index, axis in enumerate(("x", "y", "z"))
    }


def close(actual, expected, rel_tol=1.0e-10, abs_tol=1.0e-12):
    return math.isclose(
        float(actual), float(expected), rel_tol=rel_tol, abs_tol=abs_tol
    )


def create_and_solve(output_dir):
    os.makedirs(output_dir)
    os.chdir(output_dir)
    audit_path = os.path.join(output_dir, "native_audit.json")
    audit = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "software": "Abaqus/Standard Learning Edition 2025",
        "ok": False,
    }
    database = None
    odb = None
    try:
        database = Mdb()
        database.models.changeKey(fromName="Model-1", toName=MODEL_NAME)
        model = database.models[MODEL_NAME]
        model.setValues(description="Task-15 fixed-fixed 10x10 beam modal analysis")

        sketch = model.ConstrainedSketch(name="Beam-Line", sheetSize=600.0)
        sketch.Line(point1=(0.0, 0.0), point2=(500.0, 0.0))
        part = model.Part(
            name=PART_NAME, dimensionality=THREE_D, type=DEFORMABLE_BODY
        )
        part.BaseWire(sketch=sketch)
        del model.sketches["Beam-Line"]
        if len(part.edges) != 1 or len(part.vertices) != 2:
            raise RuntimeError("beam geometry is not one straight wire")

        steel = model.Material(name=MATERIAL_NAME)
        steel.Elastic(table=((210000.0, 0.3),))
        steel.Density(table=((7.85e-9,),))
        model.RectangularProfile(name=PROFILE_NAME, a=10.0, b=10.0)
        model.BeamSection(
            name=SECTION_NAME,
            integration=DURING_ANALYSIS,
            poissonRatio=0.3,
            profile=PROFILE_NAME,
            material=MATERIAL_NAME,
            temperatureVar=LINEAR,
            consistentMassMatrix=False,
        )
        all_edges = part.Set(name="SET-BEAM", edges=part.edges)
        part.SectionAssignment(
            region=all_edges,
            sectionName=SECTION_NAME,
            offset=0.0,
            offsetType=MIDDLE_SURFACE,
            offsetField="",
            thicknessAssignment=FROM_SECTION,
        )
        part.assignBeamSectionOrientation(
            region=all_edges, method=N1_COSINES, n1=(0.0, 1.0, 0.0)
        )

        part.seedEdgeByNumber(edges=part.edges, number=20, constraint=FINER)
        part.setElementType(
            regions=(part.edges,),
            elemTypes=(mesh.ElemType(elemCode=B31, elemLibrary=STANDARD),),
        )
        part.generateMesh()
        if len(part.nodes) != 21 or len(part.elements) != 20:
            raise RuntimeError(
                "expected 21 B31 nodes and 20 elements, got %s and %s"
                % (len(part.nodes), len(part.elements))
            )
        element_types = sorted(
            set(str(element.type).upper() for element in part.elements)
        )
        if element_types != ["B31"]:
            raise RuntimeError("mesh is not exclusively B31: %r" % element_types)

        rows = node_rows(part.nodes)
        part_node_list = list(part.nodes)
        expected_x = [float(value) for value in range(0, 501, 25)]
        observed_x = sorted(round(row[1][0], 9) for row in rows)
        if observed_x != expected_x or any(
            abs(row[1][1]) > 1.0e-9 or abs(row[1][2]) > 1.0e-9 for row in rows
        ):
            raise RuntimeError("beam mesh is not 20 equal divisions on global X")
        lengths = []
        for element in part.elements:
            connectivity = [int(value) for value in element.connectivity]
            if not all(0 <= value < len(part_node_list) for value in connectivity):
                raise RuntimeError("Part mesh connectivity cannot be resolved")
            first = tuple(float(value) for value in part_node_list[connectivity[0]].coordinates[:3])
            second = tuple(float(value) for value in part_node_list[connectivity[1]].coordinates[:3])
            lengths.append(
                math.sqrt(builtins.sum((second[i] - first[i]) ** 2 for i in range(3)))
            )
        if len(lengths) != 20 or any(not close(value, 25.0) for value in lengths):
            raise RuntimeError("beam elements are not uniformly 25 mm long")

        assembly = model.rootAssembly
        assembly.DatumCsysByDefault(CARTESIAN)
        instance = assembly.Instance(name=INSTANCE_NAME, part=part, dependent=ON)
        tolerance = 1.0e-6
        left_vertices = instance.vertices.getByBoundingBox(
            xMin=-tolerance,
            xMax=tolerance,
            yMin=-tolerance,
            yMax=tolerance,
            zMin=-tolerance,
            zMax=tolerance,
        )
        right_vertices = instance.vertices.getByBoundingBox(
            xMin=500.0 - tolerance,
            xMax=500.0 + tolerance,
            yMin=-tolerance,
            yMax=tolerance,
            zMin=-tolerance,
            zMax=tolerance,
        )
        if len(left_vertices) != 1 or len(right_vertices) != 1:
            raise RuntimeError("endpoint vertex selection is not unique")
        assembly.Set(name="SET-X0", vertices=left_vertices)
        assembly.Set(name="SET-X500", vertices=right_vertices)
        for name, region_name in (("BC-X0-Fixed", "SET-X0"), ("BC-X500-Fixed", "SET-X500")):
            model.DisplacementBC(
                name=name,
                createStepName="Initial",
                region=assembly.sets[region_name],
                u1=0.0,
                u2=0.0,
                u3=0.0,
                ur1=0.0,
                ur2=0.0,
                ur3=0.0,
            )
        model.FrequencyStep(
            name=STEP_NAME,
            previous="Initial",
            numEigen=3,
            description="Extract the first three fixed-fixed beam modes",
        )
        assembly.regenerate()

        job = database.Job(
            name=JOB_NAME,
            model=MODEL_NAME,
            description="Task-15 Abaqus 2025 LE native ground truth",
            memory=90,
            memoryUnits=PERCENTAGE,
            explicitPrecision=SINGLE,
            nodalOutputPrecision=SINGLE,
            multiprocessingMode=DEFAULT,
            numCpus=1,
            numDomains=1,
        )
        cae_path = os.path.join(output_dir, JOB_NAME + ".cae")
        odb_path = os.path.join(output_dir, JOB_NAME + ".odb")
        inp_path = os.path.join(output_dir, JOB_NAME + ".inp")
        metrics_path = os.path.join(output_dir, "metrics.json")
        database.saveAs(pathName=cae_path)
        job.writeInput(consistencyChecking=OFF)
        if not os.path.isfile(inp_path):
            raise RuntimeError("Abaqus did not write the native input deck")
        job.submit(consistencyChecking=OFF)
        job.waitForCompletion()
        log_path = os.path.join(output_dir, JOB_NAME + ".log")
        sta_path = os.path.join(output_dir, JOB_NAME + ".sta")
        log_text = ""
        sta_text = ""
        if os.path.isfile(log_path):
            with open(log_path, "r") as stream:
                log_text = stream.read()
        if os.path.isfile(sta_path):
            with open(sta_path, "r") as stream:
                sta_text = stream.read()
        completed = (
            str(job.status).upper() == "COMPLETED"
            or "ABAQUS JOB GT_TASK_15_ABAQUS COMPLETED" in log_text.upper()
            or "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in sta_text.upper()
        )
        if not completed or not os.path.isfile(odb_path):
            raise RuntimeError("Abaqus modal job did not complete: %s" % job.status)
        database.saveAs(pathName=cae_path)

        odb = openOdb(path=odb_path, readOnly=True)
        step = repository_item(odb.steps, STEP_NAME)
        odb_instance = repository_item(odb.rootAssembly.instances, INSTANCE_NAME)
        odb_rows = node_rows(odb_instance.nodes)
        odb_element_types = sorted(
            set(str(element.type).upper() for element in odb_instance.elements)
        )
        if len(odb_rows) != 21 or len(odb_instance.elements) != 20 or odb_element_types != ["B31"]:
            raise RuntimeError("ODB topology is not 21 nodes / 20 B31 elements")
        if bounds(odb_rows) != bounds(rows):
            raise RuntimeError("CAE and ODB mesh bounds do not match")
        modal_frames = []
        for frame in step.frames:
            frequency = float(getattr(frame, "frequency", 0.0) or 0.0)
            if frequency > 0.0:
                field = repository_item(frame.fieldOutputs, "U")
                values = list(field.values)
                if not values:
                    raise RuntimeError("modal frame has no displacement field")
                maximum = max(
                    math.sqrt(builtins.sum(float(component) ** 2 for component in value.data))
                    for value in values
                )
                if not math.isfinite(maximum) or maximum <= 0.0:
                    raise RuntimeError("modal displacement field is empty")
                modal_frames.append((frequency, maximum, len(values)))
        if len(modal_frames) != 3:
            raise RuntimeError(
                "ODB must contain exactly three positive modal frames, got %s"
                % len(modal_frames)
            )
        frequencies = [row[0] for row in modal_frames]
        if any(
            not math.isfinite(value) or value <= 0.0 for value in frequencies
        ) or any(frequencies[index] > frequencies[index + 1] for index in range(2)):
            raise RuntimeError("ODB modal frequencies are invalid")
        if not all(100.0 < value < 1000.0 for value in frequencies):
            raise RuntimeError("ODB modal frequencies are outside the physical range")
        metrics = {
            "first_frequency": frequencies[0],
            "frequency_list": frequencies,
        }
        with open(metrics_path, "w") as stream:
            json.dump(metrics, stream, indent=2, sort_keys=True)
            stream.write("\n")

        profile = repository_item(model.profiles, PROFILE_NAME)
        section = repository_item(model.sections, SECTION_NAME)
        elastic = repository_item(model.materials, MATERIAL_NAME).elastic.table
        density = repository_item(model.materials, MATERIAL_NAME).density.table
        boundary_conditions = {}
        for name in model.boundaryConditions.keys():
            condition = model.boundaryConditions[name]
            boundary_conditions[str(name)] = {
                "class": condition.__class__.__name__,
                "members": primitive(list(getattr(condition, "__members__", ()))),
            }
        with open(inp_path, "r") as stream:
            input_text = stream.read().upper()
        for token in (
            "*ELEMENT, TYPE=B31",
            "*BEAM SECTION",
            "SECTION=RECT",
            "*FREQUENCY",
        ):
            if token not in input_text:
                raise RuntimeError("native input deck lacks %s" % token)
        input_boundary_dofs = {"SET-X0": set(), "SET-X500": set()}
        in_boundary = False
        for raw_line in input_text.splitlines():
            line = raw_line.strip()
            if line.startswith("*"):
                in_boundary = line.startswith("*BOUNDARY")
                continue
            if not in_boundary or not line or line.startswith("**"):
                continue
            fields = [value.strip() for value in line.split(",")]
            if len(fields) < 2:
                continue
            matched_region = None
            for region_name in input_boundary_dofs:
                if region_name in fields[0]:
                    matched_region = region_name
                    break
            if matched_region is None:
                continue
            start = int(fields[1])
            finish = int(fields[2]) if len(fields) > 2 and fields[2] else start
            value = float(fields[3]) if len(fields) > 3 and fields[3] else 0.0
            if value != 0.0:
                raise RuntimeError("endpoint boundary value is not zero")
            input_boundary_dofs[matched_region].update(range(start, finish + 1))
        if any(input_boundary_dofs[name] != set(range(1, 7)) for name in input_boundary_dofs):
            raise RuntimeError("native input deck does not fix DOFs 1-6 at both endpoints")
        audit.update(
            {
                "ok": True,
                "model": {
                    "model_name": MODEL_NAME,
                    "job_name": JOB_NAME,
                    "job_model": str(job.model),
                    "part_name": PART_NAME,
                    "instance_name": INSTANCE_NAME,
                    "geometry": {
                        "edge_count": len(part.edges),
                        "vertex_count": len(part.vertices),
                        "bounds_mm": bounds(rows),
                    },
                    "mesh": {
                        "node_count": len(part.nodes),
                        "element_count": len(part.elements),
                        "element_types": element_types,
                        "element_lengths_mm": lengths,
                    },
                    "profile": {
                        "class": profile.__class__.__name__,
                        "a_mm": float(profile.a),
                        "b_mm": float(profile.b),
                    },
                    "section": {
                        "class": section.__class__.__name__,
                        "profile": str(section.profile),
                        "material": str(section.material),
                    },
                    "material": {
                        "elastic": primitive(elastic),
                        "density": primitive(density),
                    },
                    "boundary_conditions": boundary_conditions,
                    "boundary_regions": {"BC-X0-Fixed": "SET-X0", "BC-X500-Fixed": "SET-X500"},
                    "frequency_step": {
                        "class": model.steps[STEP_NAME].__class__.__name__,
                        "num_eigen": int(model.steps[STEP_NAME].numEigen),
                    },
                },
                "result": {
                    "odb_path": os.path.basename(odb_path),
                    "release": primitive(getattr(odb, "release", None)),
                    "step_names": sorted(str(key) for key in odb.steps.keys()),
                    "positive_modal_frame_count": len(modal_frames),
                    "frequency_hz": frequencies,
                    "mode_shape_maximum_u": [row[1] for row in modal_frames],
                    "mode_shape_value_counts": [row[2] for row in modal_frames],
                    "odb_mesh": {
                        "node_count": len(odb_rows),
                        "element_count": len(odb_instance.elements),
                        "element_types": odb_element_types,
                        "bounds_mm": bounds(odb_rows),
                    },
                },
                "metrics": metrics,
                "input_checks": {
                    "b31_element_count": input_text.count("*ELEMENT, TYPE=B31"),
                    "beam_section_count": input_text.count("*BEAM SECTION"),
                    "frequency_keyword_count": input_text.count("*FREQUENCY"),
                    "boundary_dofs": dict(
                        (name, sorted(values))
                        for name, values in input_boundary_dofs.items()
                    ),
                },
            }
        )
        odb.close()
        odb = None
        database.close()
        database = None
        required = (
            cae_path,
            odb_path,
            inp_path,
            log_path,
            sta_path,
            metrics_path,
        )
        audit["artifacts"] = []
        for path in required:
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise RuntimeError("native Abaqus artifact missing: %s" % path)
            audit["artifacts"].append(artifact(path))
    except Exception as exc:
        audit["ok"] = False
        audit["error"] = repr(exc)
        audit["traceback"] = traceback.format_exc()
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass
        try:
            if database is not None:
                database.close()
        except Exception:
            pass
    with open(audit_path, "w") as stream:
        json.dump(audit, stream, indent=2, sort_keys=True)
        stream.write("\n")
    if not audit.get("ok"):
        raise RuntimeError(audit.get("error"))


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("usage: abaqus cae noGUI=script.py -- OUTPUT_DIR")
    create_and_solve(os.path.abspath(sys.argv[-1]))


if __name__ == "__main__":
    main()
