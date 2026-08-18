# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
ABAQUS = Path(r"C:\SIMULIA\Commands\abaqus.bat")
INIT_CAE = DESKTOP / "task18_punch_plate_init.cae"
GT_CAE = DESKTOP / "Task18_PunchPlate_GT.cae"
ODB = DESKTOP / "Task18_PunchPlate.odb"
METRICS = DESKTOP / "metrics.json"
CHECKER = DESKTOP / "__task18_abaqus_checker.py"
RESULT = DESKTOP / "__task18_abaqus_result.txt"
DETAIL = DESKTOP / "__task18_abaqus_detail.txt"
EVIDENCE = DESKTOP / "__task18_abaqus_evidence.json"


CHECKER_SOURCE = r'''# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import math
import os
import re
import traceback

from abaqus import mdb, openMdb
from abaqusConstants import OFF
from caeModules import *
from odbAccess import openOdb


DESKTOP = r"C:\Users\user\Desktop"
INIT_CAE = os.path.join(DESKTOP, "task18_punch_plate_init.cae")
GT_CAE = os.path.join(DESKTOP, "Task18_PunchPlate_GT.cae")
ODB_PATH = os.path.join(DESKTOP, "Task18_PunchPlate.odb")
METRICS_PATH = os.path.join(DESKTOP, "metrics.json")
RESULT_PATH = os.path.join(DESKTOP, "__task18_abaqus_result.txt")
DETAIL_PATH = os.path.join(DESKTOP, "__task18_abaqus_detail.txt")
EVIDENCE_PATH = os.path.join(DESKTOP, "__task18_abaqus_evidence.json")
JOB_NAME = "Task18_PunchPlate"
MODEL_NAME = "PunchPlate2D"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
DETAILS = []
RECOMPUTED = {}
INIT_PLATE_SIGNATURE = None
INIT_PUNCH_EDGE_SIGNATURE = None
CAE_PLATE_SIGNATURE = None


def log(message):
    DETAILS.append(str(message))


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def close(actual, expected, rel=1.0e-6, abs_tol=1.0e-9):
    try:
        actual = float(actual)
        expected = float(expected)
        return math.isfinite(actual) and abs(actual - expected) <= max(abs_tol, rel * abs(expected))
    except Exception:
        return False


def point3(values):
    result = [float(value) for value in values]
    while len(result) < 3:
        result.append(0.0)
    return tuple(result[:3])


def node_bounds(nodes):
    xyz = [point3(node.coordinates) for node in nodes]
    if not xyz:
        return None
    return tuple((min(point[i] for point in xyz), max(point[i] for point in xyz)) for i in range(3))


def bounds_match(observed, expected, tolerance=1.0e-6):
    if observed is None:
        return False
    return all(
        abs(observed[axis][end] - expected[axis][end]) <= tolerance
        for axis in range(3)
        for end in range(2)
    )


def vertex_coordinates(vertices):
    return sorted(tuple(round(value, 6) for value in point3(vertex.pointOn[0])) for vertex in vertices)


def analytical_edge_signature(edges):
    return sorted(tuple(round(value, 6) for value in point3(edge.pointOn[0])) for edge in edges)


def mesh_signature(nodes, elements):
    node_list = list(nodes)
    node_coordinates = [
        tuple(round(value, 8) for value in point3(node.coordinates))
        for node in node_list
    ]
    coordinates_by_label = {
        int(node.label): coordinates for node, coordinates in zip(node_list, node_coordinates)
    }
    element_list = list(elements)
    connectivity_is_indexed = any(
        int(value) == 0
        for element in element_list
        for value in element.connectivity
    )
    element_signature = []
    for element in element_list:
        if connectivity_is_indexed:
            connected = [node_coordinates[int(value)] for value in element.connectivity]
        else:
            connected = [coordinates_by_label[int(value)] for value in element.connectivity]
        element_signature.append((str(element.type).upper(), tuple(sorted(connected))))
    return sorted(node_coordinates), sorted(element_signature)


def node_region_signature(region):
    return sorted(
        (
            str(node.instanceName).upper(),
            int(node.label),
            tuple(round(value, 8) for value in point3(node.coordinates)),
        )
        for node in region.nodes
    )


def reference_point_signature(region):
    return sorted(repr(point) for point in region.referencePoints)


def keyword_data(text, keyword):
    result = []
    collecting = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("**"):
            continue
        if line.startswith("*"):
            collecting = line.split(",", 1)[0].strip() == keyword
            continue
        if collecting and line:
            result.append(tuple(item.strip() for item in line.split(",")))
    return result


def named_keyword_data(text, keyword, name):
    headers = []
    result = []
    collecting = False
    expected_name = "NAME=" + name
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("**"):
            continue
        if line.startswith("*"):
            fields = [item.strip() for item in line.split(",")]
            collecting = (
                fields[0] == keyword
                and expected_name in [item.replace(" ", "") for item in fields[1:]]
            )
            if collecting:
                headers.append(line)
            continue
        if collecting and line:
            result.append(tuple(item.strip() for item in line.split(",")))
    return headers, result


def check_base_model(model):
    if set(model.parts.keys()) != {"Plate", "Punch"}:
        log("part names mismatch: %s" % list(model.parts.keys()))
        return False
    plate = model.parts["Plate"]
    punch = model.parts["Punch"]
    if not bounds_match(node_bounds(plate.nodes), ((-20.0, 20.0), (-12.0, 0.0), (0.0, 0.0))):
        log("plate geometry mismatch: %s" % (node_bounds(plate.nodes),))
        return False
    if len(plate.nodes) != 533 or len(plate.elements) != 480:
        log("plate mesh count mismatch: nodes=%s elements=%s" % (len(plate.nodes), len(plate.elements)))
        return False
    if len(plate.nodes) + 1 > 1000:
        log("Learning Edition node limit exceeded")
        return False
    if set(str(element.type).upper() for element in plate.elements) != {"CPE4R"}:
        log("plate must use CPE4R plane-strain elements")
        return False
    if set(model.sections.keys()) != {"PlateSection"}:
        log("section repository mismatch")
        return False
    if str(model.sections["PlateSection"].material) != "EngineeringPolymer":
        log("PlateSection material binding mismatch")
        return False
    if len(plate.sectionAssignments) != 1 or str(plate.sectionAssignments[0].sectionName) != "PlateSection":
        log("plate section assignment mismatch")
        return False
    if set(plate.surfaces.keys()) != {"PLATE_TOP"} or set(plate.sets.keys()) != {"PLATE_BOTTOM"}:
        log("plate init surfaces/sets mismatch")
        return False
    if len(punch.nodes) or len(punch.elements) or len(punch.edges) != 2 or len(punch.referencePoints) != 1:
        log("analytical rigid punch topology mismatch")
        return False
    expected_vertices = [(-5.0, 0.0, 0.0), (0.0, -5.0, 0.0), (5.0, 0.0, 0.0)]
    if vertex_coordinates(punch.vertices) != expected_vertices:
        log("punch radius/geometry mismatch: %s" % (vertex_coordinates(punch.vertices),))
        return False
    expected_edge_signature = [(-4.619398, -1.913417, 0.0), (1.913417, -4.619398, 0.0)]
    if analytical_edge_signature(punch.edges) != expected_edge_signature:
        log("punch analytical edge geometry mismatch: %s" % (analytical_edge_signature(punch.edges),))
        return False
    if set(punch.surfaces.keys()) != {"PUNCH_CONTACT"} or set(punch.sets.keys()) != {"PUNCH_RP"}:
        log("punch init surface/reference-point set mismatch")
        return False
    try:
        elastic = model.materials["EngineeringPolymer"].elastic.table[0]
    except Exception:
        log("EngineeringPolymer elastic material missing")
        return False
    if not close(elastic[0], 2100.0) or not close(elastic[1], 0.35):
        log("EngineeringPolymer elastic values mismatch: %s" % (elastic,))
        return False
    assembly = model.rootAssembly
    if set(assembly.instances.keys()) != {"Plate-1", "Punch-1"}:
        log("assembly instance names mismatch: %s" % list(assembly.instances.keys()))
        return False
    if not bounds_match(node_bounds(assembly.instances["Plate-1"].nodes), ((-20.0, 20.0), (-12.0, 0.0), (0.0, 0.0))):
        log("plate instance placement mismatch")
        return False
    expected_instance_vertices = [(-5.0, 5.0, 0.0), (0.0, 0.0, 0.0), (5.0, 5.0, 0.0)]
    if vertex_coordinates(assembly.instances["Punch-1"].vertices) != expected_instance_vertices:
        log("punch instance placement mismatch")
        return False
    return True


def check_init():
    global INIT_PLATE_SIGNATURE, INIT_PUNCH_EDGE_SIGNATURE
    openMdb(pathName=INIT_CAE)
    if MODEL_NAME not in mdb.models:
        log("init model missing")
        return False
    model = mdb.models[MODEL_NAME]
    if not check_base_model(model):
        log("init base model invalid")
        return False
    if set(model.steps.keys()) != {"Initial"}:
        log("init must contain only Initial step")
        return False
    if (
        model.interactions.keys()
        or model.loads.keys()
        or model.boundaryConditions.keys()
        or model.rootAssembly.sets.keys()
        or mdb.jobs.keys()
    ):
        log("init is already completed")
        return False
    plate = model.rootAssembly.instances["Plate-1"]
    INIT_PLATE_SIGNATURE = mesh_signature(plate.nodes, plate.elements)
    INIT_PUNCH_EDGE_SIGNATURE = analytical_edge_signature(model.parts["Punch"].edges)
    return True


def write_input_and_check_cae():
    global CAE_PLATE_SIGNATURE
    openMdb(pathName=GT_CAE)
    if MODEL_NAME not in mdb.models:
        log("GT model missing")
        return False
    model = mdb.models[MODEL_NAME]
    if not check_base_model(model):
        return False
    assembly = model.rootAssembly
    CAE_PLATE_SIGNATURE = mesh_signature(
        assembly.instances["Plate-1"].nodes,
        assembly.instances["Plate-1"].elements,
    )
    if CAE_PLATE_SIGNATURE != INIT_PLATE_SIGNATURE:
        log("init/GT plate node-coordinate or element-connectivity signature mismatch")
        return False
    if analytical_edge_signature(model.parts["Punch"].edges) != INIT_PUNCH_EDGE_SIGNATURE:
        log("init/GT analytical punch edge signature mismatch")
        return False
    if set(model.steps.keys()) != {"Initial", "IndentationStep"}:
        log("analysis steps mismatch: %s" % list(model.steps.keys()))
        return False
    step = model.steps["IndentationStep"]
    if step.__class__.__name__ != "StaticStep" or str(step.nlgeom).upper() != "ON":
        log("nonlinear StaticStep missing")
        return False
    if (
        not close(step.initialInc, 0.01)
        or not close(step.minInc, 1.0e-6)
        or not close(step.maxInc, 0.05)
        or int(step.maxNumInc) != 300
    ):
        log("step increment controls mismatch")
        return False
    if set(model.interactions.keys()) != {"PunchPlateContact"}:
        log("contact interaction mismatch")
        return False
    interaction = model.interactions["PunchPlateContact"]
    if (
        interaction.__class__.__name__ != "SurfaceToSurfaceStd"
        or str(interaction.sliding).upper() != "FINITE"
        or bool(interaction.suppressed)
    ):
        log("surface-to-surface finite-sliding contact missing")
        return False
    if "PUNCH_CONTACT" not in repr(interaction.main).upper() or "PLATE_TOP" not in repr(interaction.secondary).upper():
        log("contact surfaces mismatch")
        return False
    try:
        prop = model.interactionProperties["FrictionlessHard"]
        if str(prop.normalBehavior.pressureOverclosure).upper() != "HARD":
            raise ValueError("normal behavior")
        if str(prop.normalBehavior.allowSeparation).upper() != "ON":
            raise ValueError("separation behavior")
        if str(prop.tangentialBehavior.formulation).upper() != "FRICTIONLESS":
            raise ValueError("tangential behavior")
    except Exception:
        log("hard frictionless contact property missing")
        return False
    if model.loads.keys():
        log("unexpected external load repository")
        return False
    if set(model.boundaryConditions.keys()) != {"PlateBottomFixed", "PunchMotion"}:
        log("boundary-condition repository mismatch")
        return False
    if set(assembly.sets.keys()) != {"PLATE_BOTTOM_NODES", "PUNCH_RP_NODE"}:
        log("result-extraction assembly sets mismatch")
        return False
    if node_region_signature(assembly.sets["PLATE_BOTTOM_NODES"]) != node_region_signature(
        assembly.instances["Plate-1"].sets["PLATE_BOTTOM"]
    ):
        log("PLATE_BOTTOM_NODES members do not match Plate-1.PLATE_BOTTOM")
        return False
    if reference_point_signature(assembly.sets["PUNCH_RP_NODE"]) != reference_point_signature(
        assembly.instances["Punch-1"].sets["PUNCH_RP"]
    ):
        log("PUNCH_RP_NODE members do not match Punch-1.PUNCH_RP")
        return False
    if (
        set(mdb.jobs.keys()) != {JOB_NAME}
        or mdb.jobs[JOB_NAME].model != MODEL_NAME
        or int(mdb.jobs[JOB_NAME].numCpus) != 1
    ):
        log("job/model association mismatch")
        return False
    os.chdir(DESKTOP)
    mdb.jobs[JOB_NAME].writeInput(consistencyChecking=OFF)
    input_path = os.path.join(DESKTOP, JOB_NAME + ".inp")
    text = open(input_path, "r").read().upper()
    required_fragments = (
        "*ELEMENT, TYPE=CPE4R",
        "*RIGID BODY, REF NODE=PUNCH-1-REFPT_, ANALYTICAL SURFACE=PUNCH_CONTACT",
        "*SURFACE INTERACTION, NAME=FRICTIONLESSHARD",
        "*FRICTION\n0.",
        "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD",
        "*STEP, NAME=INDENTATIONSTEP, NLGEOM=YES, INC=300",
    )
    for fragment in required_fragments:
        if fragment not in text:
            log("generated input missing semantic fragment: " + fragment)
            return False
    surface_headers, surface_data = named_keyword_data(text, "*SURFACE", "PUNCH_CONTACT")
    expected_surface_header = "*SURFACE, TYPE=SEGMENTS, NAME=PUNCH_CONTACT"
    if surface_headers != [expected_surface_header] or len(surface_data) != 3:
        log("PUNCH_CONTACT must be one analytical TYPE=SEGMENTS surface")
        return False
    if (
        surface_data[0][0] != "START"
        or surface_data[1][0] != "CIRCL"
        or surface_data[2][0] != "CIRCL"
        or len(surface_data[0]) != 3
        or len(surface_data[1]) != 5
        or len(surface_data[2]) != 5
    ):
        log("PUNCH_CONTACT must contain START followed by two CIRCL arcs and no LINE segments")
        return False
    try:
        start = tuple(float(value) for value in surface_data[0][1:])
        first_end = tuple(float(value) for value in surface_data[1][1:3])
        first_center = tuple(float(value) for value in surface_data[1][3:5])
        second_end = tuple(float(value) for value in surface_data[2][1:3])
        second_center = tuple(float(value) for value in surface_data[2][3:5])
    except Exception:
        log("PUNCH_CONTACT analytical segment coordinates are invalid")
        return False
    expected_points = (
        (start, (5.0, 0.0)),
        (first_end, (0.0, -5.0)),
        (first_center, (0.0, 0.0)),
        (second_end, (-5.0, 0.0)),
        (second_center, (0.0, 0.0)),
    )
    if any(not all(close(actual, wanted) for actual, wanted in zip(observed, expected)) for observed, expected in expected_points):
        log("PUNCH_CONTACT CIRCL endpoint or common-center geometry mismatch")
        return False
    arc_points = (start, first_end, second_end)
    if any(not close(math.hypot(point[0], point[1]), 5.0) for point in arc_points):
        log("PUNCH_CONTACT CIRCL radius must be 5")
        return False
    contact_lines = re.findall(r"(?m)^\*CONTACT PAIR[^\n]*", text)
    expected_contact = "*CONTACT PAIR, INTERACTION=FRICTIONLESSHARD, TYPE=SURFACE TO SURFACE"
    first_step = text.find("*STEP")
    contact_position = text.find(expected_contact)
    if (
        contact_lines != [expected_contact]
        or contact_position < 0
        or first_step < 0
        or contact_position >= first_step
        or keyword_data(text, "*CONTACT PAIR") != [
            ("PLATE-1.PLATE_TOP", "PUNCH-1.PUNCH_CONTACT")
        ]
    ):
        log("contact-pair count mismatch")
        return False
    expected_boundaries = sorted([
        ("PLATE-1.PLATE_BOTTOM", "ENCASTRE"),
        ("PUNCH-1.PUNCH_RP", "1", "1"),
        ("PUNCH-1.PUNCH_RP", "2", "2", "-0.1"),
        ("PUNCH-1.PUNCH_RP", "6", "6"),
    ])
    if sorted(keyword_data(text, "*BOUNDARY")) != expected_boundaries:
        log("generated input boundary-condition DOFs mismatch")
        return False
    static_data = keyword_data(text, "*STATIC")
    if (
        len(static_data) != 1
        or len(static_data[0]) != 4
        or not all(
            close(actual, expected)
            for actual, expected in zip(static_data[0], (0.01, 1.0, 1.0e-6, 0.05))
        )
    ):
        log("generated input Static increment controls mismatch")
        return False
    if re.search(r"(?m)^\*(?:CLOAD|DLOAD|DSLOAD)\b", text):
        log("unexpected force/pressure load keyword")
        return False
    displacement = re.search(
        r"(?m)^\s*PUNCH-1\.PUNCH_RP\s*,\s*2\s*,\s*2\s*,\s*(" + FLOAT + r")\s*$",
        text,
    )
    if not displacement or not close(displacement.group(1), -0.1):
        log("-0.1 mm punch displacement missing from generated input")
        return False
    return True


def field_by_prefix(frame, prefix):
    matches = [name for name in frame.fieldOutputs.keys() if str(name).strip().upper().startswith(prefix)]
    if len(matches) != 1:
        raise ValueError("field prefix %s matched %s" % (prefix, matches))
    return matches[0], frame.fieldOutputs[matches[0]]


def scalar(value):
    try:
        return float(value.data)
    except Exception:
        return float(value.data[0])


def check_odb_and_metrics():
    odb = openOdb(path=ODB_PATH, readOnly=True)
    try:
        status = str(odb.diagnosticData.jobStatus).upper()
        if status != "JOB_STATUS_COMPLETED_SUCCESSFULLY":
            log("ODB job status mismatch: " + status)
            return False
        if set(odb.steps.keys()) != {"IndentationStep"}:
            log("ODB step names mismatch")
            return False
        step = odb.steps["IndentationStep"]
        if len(step.frames) < 2:
            log("ODB has too few converged frames")
            return False
        frame = step.frames[-1]
        if not close(frame.frameValue, 1.0, rel=1.0e-5):
            log("analysis did not reach full step time")
            return False
        instances = odb.rootAssembly.instances
        if set(instances.keys()) != {"PLATE-1", "PUNCH-1"}:
            log("ODB instance names mismatch")
            return False
        plate = instances["PLATE-1"]
        punch = instances["PUNCH-1"]
        if len(plate.nodes) != 533 or len(plate.elements) != 480:
            log("ODB plate mesh mismatch")
            return False
        if not bounds_match(node_bounds(plate.nodes), ((-20.0, 20.0), (-12.0, 0.0), (0.0, 0.0))):
            log("ODB plate bounds mismatch")
            return False
        if mesh_signature(plate.nodes, plate.elements) != CAE_PLATE_SIGNATURE:
            log("CAE/ODB plate node-coordinate or element-connectivity signature mismatch")
            return False
        if len(punch.nodes) != 1 or len(punch.elements) != 0:
            log("ODB analytical rigid punch topology mismatch")
            return False
        punch_coordinate = point3(punch.nodes[0].coordinates)
        if any(abs(punch_coordinate[index] - (0.0, 5.0, 0.0)[index]) > 1.0e-6 for index in range(3)):
            log("ODB punch reference-point location mismatch: %s" % (punch_coordinate,))
            return False
        for set_name in ("PLATE_BOTTOM_NODES", "PUNCH_RP_NODE"):
            if set_name not in odb.rootAssembly.nodeSets:
                log("ODB node set missing: " + set_name)
                return False
        for field_name in ("U", "S", "RF"):
            if field_name not in frame.fieldOutputs:
                log("ODB field missing: " + field_name)
                return False
        cpress_name, cpress = field_by_prefix(frame, "CPRESS")
        copen_name, copen = field_by_prefix(frame, "COPEN")
        for field_name in (cpress_name, copen_name):
            normalized = str(field_name).upper()
            if "PLATE-1_PLATE_TOP" not in normalized or "PUNCH-1_PUNCH_CONTACT" not in normalized:
                log("contact output belongs to unexpected surfaces: " + normalized)
                return False
        pressure_values = [scalar(value) for value in cpress.values if finite(scalar(value))]
        positive_pressures = [value for value in pressure_values if value > 1.0e-8]
        if len(positive_pressures) < 2:
            log("insufficient active contact pressure values")
            return False
        opening_values = [
            scalar(value) for value in copen.values
            if finite(scalar(value)) and scalar(value) > -1.0e30
        ]
        if (
            len(opening_values) < 3
            or min(opening_values) < -0.02
            or max(opening_values) > 0.5
            or min(opening_values) > 0.0
        ):
            log("COPEN values are missing or inconsistent with punch contact")
            return False
        max_contact_pressure = max(positive_pressures)
        bottom = odb.rootAssembly.nodeSets["PLATE_BOTTOM_NODES"]
        punch_rp = odb.rootAssembly.nodeSets["PUNCH_RP_NODE"]
        bottom_reaction = math.fsum(
            float(value.data[1])
            for value in frame.fieldOutputs["RF"].getSubset(region=bottom).values
        )
        rp_reaction = math.fsum(
            float(value.data[1])
            for value in frame.fieldOutputs["RF"].getSubset(region=punch_rp).values
        )
        displacement_values = frame.fieldOutputs["U"].getSubset(region=punch_rp).values
        if len(displacement_values) != 1:
            log("punch reference-point displacement cardinality mismatch")
            return False
        punch_displacement = float(displacement_values[0].data[1])
        max_mises = max(
            [float(value.mises) for value in frame.fieldOutputs["S"].values if finite(value.mises)]
            or [0.0]
        )
        punch_reaction = abs(rp_reaction)
        if not (5.0 < max_contact_pressure < 500.0):
            log("contact pressure outside physical range")
            return False
        if not close(punch_displacement, -0.1, rel=1.0e-5, abs_tol=1.0e-6):
            log("ODB punch displacement mismatch: %s" % punch_displacement)
            return False
        if not (1.0 < punch_reaction < 1000.0):
            log("punch reaction outside physical range")
            return False
        if bottom_reaction * rp_reaction >= 0.0:
            log("bottom and punch raw reactions must have opposite signs")
            return False
        if not close(abs(bottom_reaction), abs(rp_reaction), rel=0.002, abs_tol=1.0):
            log("opposing reaction-force imbalance: bottom=%s punch=%s" % (bottom_reaction, punch_reaction))
            return False
        if not (1.0 < max_mises < 500.0):
            log("stress outside physical range")
            return False
        recomputed = {
            "max_contact_pressure": max_contact_pressure,
            "punch_vertical_displacement": punch_displacement,
            "punch_reaction_force": punch_reaction,
            "max_mises_stress": max_mises,
        }
        metrics = json.load(open(METRICS_PATH, "r"))
        if set(metrics.keys()) != set(recomputed.keys()):
            log("metrics fields mismatch")
            return False
        for name, expected in recomputed.items():
            if not finite(metrics[name]) or not close(metrics[name], expected, rel=2.0e-6, abs_tol=1.0e-10):
                log("metrics/ODB mismatch for %s" % name)
                return False
        RECOMPUTED.update(recomputed)
        return True
    finally:
        odb.close()


def main():
    ok = False
    try:
        ok = check_init() and write_input_and_check_cae() and check_odb_and_metrics()
    except Exception:
        log(traceback.format_exc())
        ok = False
    with open(RESULT_PATH, "w") as handle:
        handle.write("True\n" if ok else "False\n")
    with open(DETAIL_PATH, "w") as handle:
        handle.write("\n".join(DETAILS) + "\n")
    with open(EVIDENCE_PATH, "w") as handle:
        json.dump({"passed": ok, "recomputed_metrics": RECOMPUTED, "details": DETAILS}, handle, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
'''


def is_nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def evaluate() -> bool:
    required = (INIT_CAE, GT_CAE, ODB, METRICS)
    if not ABAQUS.is_file() or any(not is_nonempty(path) for path in required):
        return False
    for stale in (RESULT, DETAIL, EVIDENCE):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass
    try:
        CHECKER.write_text(CHECKER_SOURCE, encoding="utf-8")
        completed = subprocess.run(
            [str(ABAQUS), "cae", "noGUI=" + str(CHECKER)],
            cwd=str(DESKTOP),
            text=True,
            capture_output=True,
            timeout=120,
            shell=False,
        )
        if completed.returncode != 0 or not is_nonempty(RESULT):
            return False
        return RESULT.read_text(encoding="utf-8", errors="ignore") == "True\n"
    except Exception:
        return False


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
