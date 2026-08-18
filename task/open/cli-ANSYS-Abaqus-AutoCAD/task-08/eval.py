# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
ABAQUS = Path(r"C:\SIMULIA\Commands\abaqus.bat")
INIT_CAE = DESKTOP / "task08_block_plate_init.cae"
GT_CAE = DESKTOP / "Task08_BlockPlate_GT.cae"
ODB = DESKTOP / "Task08_BlockPlate.odb"
METRICS = DESKTOP / "metrics.json"
CHECKER = DESKTOP / "__task08_abaqus_checker.py"
RESULT = DESKTOP / "__task08_abaqus_result.txt"
DETAIL = DESKTOP / "__task08_abaqus_detail.txt"
EVIDENCE = DESKTOP / "__task08_abaqus_evidence.json"


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
INIT_CAE = os.path.join(DESKTOP, "task08_block_plate_init.cae")
GT_CAE = os.path.join(DESKTOP, "Task08_BlockPlate_GT.cae")
ODB_PATH = os.path.join(DESKTOP, "Task08_BlockPlate.odb")
METRICS_PATH = os.path.join(DESKTOP, "metrics.json")
RESULT_PATH = os.path.join(DESKTOP, "__task08_abaqus_result.txt")
DETAIL_PATH = os.path.join(DESKTOP, "__task08_abaqus_detail.txt")
EVIDENCE_PATH = os.path.join(DESKTOP, "__task08_abaqus_evidence.json")
JOB_NAME = "Task08_BlockPlate"
MODEL_NAME = "BlockPlate3D"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
DETAILS = []
RECOMPUTED = {}
INIT_SIGNATURES = {}
CAE_SIGNATURES = {}


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


def bounds(nodes):
    xyz = [tuple(float(value) for value in node.coordinates) for node in nodes]
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


def mesh_signature(nodes, elements):
    node_list = list(nodes)
    node_coordinates = [
        tuple(round(float(value), 8) for value in node.coordinates)
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
    node_signature = sorted(node_coordinates)
    element_signature.sort()
    return node_signature, element_signature


def node_region_signature(region):
    return sorted(
        (
            str(node.instanceName).upper(),
            int(node.label),
            tuple(round(float(value), 8) for value in node.coordinates),
        )
        for node in region.nodes
    )


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


def check_base_model(model):
    if set(model.parts.keys()) != {"Plate", "Block"}:
        log("part names mismatch: %s" % list(model.parts.keys()))
        return False
    plate = model.parts["Plate"]
    block = model.parts["Block"]
    if not bounds_match(bounds(plate.nodes), ((0.0, 24.0), (0.0, 24.0), (0.0, 3.0))):
        log("plate geometry mismatch: %s" % (bounds(plate.nodes),))
        return False
    if not bounds_match(bounds(block.nodes), ((0.0, 8.0), (0.0, 8.0), (0.0, 8.0))):
        log("block geometry mismatch: %s" % (bounds(block.nodes),))
        return False
    if len(plate.nodes) != 162 or len(plate.elements) != 64:
        log("plate mesh count mismatch: nodes=%s elements=%s" % (len(plate.nodes), len(plate.elements)))
        return False
    if len(block.nodes) != 125 or len(block.elements) != 64:
        log("block mesh count mismatch: nodes=%s elements=%s" % (len(block.nodes), len(block.elements)))
        return False
    if len(plate.nodes) + len(block.nodes) > 1000:
        log("Learning Edition node limit exceeded")
        return False
    element_types = set(str(element.type).upper() for part in (plate, block) for element in part.elements)
    if element_types != {"C3D8R"}:
        log("element types mismatch: %s" % sorted(element_types))
        return False
    if set(model.sections.keys()) != {"SteelSection"}:
        log("section repository mismatch")
        return False
    if str(model.sections["SteelSection"].material) != "Steel":
        log("SteelSection material binding mismatch")
        return False
    if any(
        len(part.sectionAssignments) != 1
        or str(part.sectionAssignments[0].sectionName) != "SteelSection"
        for part in (plate, block)
    ):
        log("part section assignment mismatch")
        return False
    if set(plate.surfaces.keys()) != {"PLATE_TOP"} or set(plate.sets.keys()) != {"PLATE_BOTTOM"}:
        log("plate init surfaces/sets mismatch")
        return False
    if set(block.surfaces.keys()) != {"BLOCK_BOTTOM", "BLOCK_TOP"}:
        log("block init surfaces mismatch")
        return False
    if set(block.sets.keys()) != {"BLOCK_ANCHOR", "BLOCK_GUIDE", "BLOCK_TOP_NODES"}:
        log("block init node sets mismatch")
        return False
    try:
        elastic = model.materials["Steel"].elastic.table[0]
    except Exception:
        log("Steel elastic material missing")
        return False
    if not close(elastic[0], 210000.0) or not close(elastic[1], 0.3):
        log("Steel elastic values mismatch: %s" % (elastic,))
        return False
    assembly = model.rootAssembly
    if set(assembly.instances.keys()) != {"Plate-1", "Block-1"}:
        log("assembly instance names mismatch: %s" % list(assembly.instances.keys()))
        return False
    if not bounds_match(bounds(assembly.instances["Plate-1"].nodes), ((0.0, 24.0), (0.0, 24.0), (0.0, 3.0))):
        log("plate instance placement mismatch")
        return False
    if not bounds_match(bounds(assembly.instances["Block-1"].nodes), ((8.0, 16.0), (8.0, 16.0), (3.0, 11.0))):
        log("block instance placement mismatch")
        return False
    return True


def check_init():
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
    for instance_name in ("Plate-1", "Block-1"):
        instance = model.rootAssembly.instances[instance_name]
        INIT_SIGNATURES[instance_name] = mesh_signature(instance.nodes, instance.elements)
    return True


def write_input_and_check_cae():
    openMdb(pathName=GT_CAE)
    if MODEL_NAME not in mdb.models:
        log("GT model missing")
        return False
    model = mdb.models[MODEL_NAME]
    if not check_base_model(model):
        return False
    assembly = model.rootAssembly
    for instance_name in ("Plate-1", "Block-1"):
        instance = assembly.instances[instance_name]
        signature = mesh_signature(instance.nodes, instance.elements)
        if signature != INIT_SIGNATURES.get(instance_name):
            log("init/GT node-coordinate or element-connectivity signature mismatch: " + instance_name)
            return False
        CAE_SIGNATURES[instance_name] = signature
    if set(model.steps.keys()) != {"Initial", "ContactStep"}:
        log("analysis steps mismatch: %s" % list(model.steps.keys()))
        return False
    step = model.steps["ContactStep"]
    if step.__class__.__name__ != "StaticStep" or str(step.nlgeom).upper() != "ON":
        log("nonlinear StaticStep missing")
        return False
    if (
        not close(step.initialInc, 0.05)
        or not close(step.minInc, 1.0e-6)
        or not close(step.maxInc, 0.1)
        or int(step.maxNumInc) != 200
    ):
        log("step increment controls mismatch")
        return False
    if set(model.interactions.keys()) != {"BlockPlateContact"}:
        log("contact interaction mismatch")
        return False
    interaction = model.interactions["BlockPlateContact"]
    if (
        interaction.__class__.__name__ != "SurfaceToSurfaceStd"
        or str(interaction.sliding).upper() != "FINITE"
        or bool(interaction.suppressed)
    ):
        log("surface-to-surface finite-sliding contact missing")
        return False
    if "PLATE_TOP" not in repr(interaction.main).upper() or "BLOCK_BOTTOM" not in repr(interaction.secondary).upper():
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
    if set(model.loads.keys()) != {"BlockTopPressure"}:
        log("pressure load repository mismatch")
        return False
    if "BLOCK_TOP" not in repr(model.loads["BlockTopPressure"].region).upper():
        log("pressure region mismatch")
        return False
    if set(model.boundaryConditions.keys()) != {"PlateBottomFixed", "BlockAnchorXY", "BlockGuideY"}:
        log("boundary-condition repository mismatch")
        return False
    if set(assembly.sets.keys()) != {"PLATE_BOTTOM_NODES", "BLOCK_TOP_NODES"}:
        log("result-extraction assembly sets mismatch")
        return False
    if node_region_signature(assembly.sets["PLATE_BOTTOM_NODES"]) != node_region_signature(
        assembly.instances["Plate-1"].sets["PLATE_BOTTOM"]
    ):
        log("PLATE_BOTTOM_NODES members do not match Plate-1.PLATE_BOTTOM")
        return False
    if node_region_signature(assembly.sets["BLOCK_TOP_NODES"]) != node_region_signature(
        assembly.instances["Block-1"].sets["BLOCK_TOP_NODES"]
    ):
        log("BLOCK_TOP_NODES members do not match Block-1.BLOCK_TOP_NODES")
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
        "*ELEMENT, TYPE=C3D8R",
        "*SURFACE INTERACTION, NAME=FRICTIONLESSHARD",
        "*FRICTION\n0.",
        "*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD",
        "*STEP, NAME=CONTACTSTEP, NLGEOM=YES, INC=200",
    )
    for fragment in required_fragments:
        if fragment not in text:
            log("generated input missing semantic fragment: " + fragment)
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
            ("BLOCK-1.BLOCK_BOTTOM", "PLATE-1.PLATE_TOP")
        ]
    ):
        log("contact-pair count mismatch")
        return False
    expected_boundaries = sorted([
        ("BLOCK-1.BLOCK_ANCHOR", "1", "1"),
        ("BLOCK-1.BLOCK_ANCHOR", "2", "2"),
        ("BLOCK-1.BLOCK_GUIDE", "2", "2"),
        ("PLATE-1.PLATE_BOTTOM", "ENCASTRE"),
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
            for actual, expected in zip(static_data[0], (0.05, 1.0, 1.0e-6, 0.1))
        )
    ):
        log("generated input Static increment controls mismatch")
        return False
    if len(re.findall(r"(?m)^\*DSLOAD\b", text)) != 1 or re.search(r"(?m)^\*(?:CLOAD|DLOAD)\b", text):
        log("unexpected load keyword count")
        return False
    pressure = re.search(
        r"(?ms)^\*DSLOAD[^\n]*\n\s*BLOCK-1\.BLOCK_TOP\s*,\s*P\s*,\s*(" + FLOAT + r")",
        text,
    )
    if not pressure or not close(pressure.group(1), 2.0):
        log("2 MPa pressure missing from generated input")
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
        if set(odb.steps.keys()) != {"ContactStep"}:
            log("ODB step names mismatch")
            return False
        step = odb.steps["ContactStep"]
        if len(step.frames) < 2:
            log("ODB has too few converged frames")
            return False
        frame = step.frames[-1]
        if not close(frame.frameValue, 1.0, rel=1.0e-5):
            log("analysis did not reach full load time")
            return False
        instances = odb.rootAssembly.instances
        if set(instances.keys()) != {"PLATE-1", "BLOCK-1"}:
            log("ODB instance names mismatch")
            return False
        if len(instances["PLATE-1"].nodes) != 162 or len(instances["PLATE-1"].elements) != 64:
            log("ODB plate mesh mismatch")
            return False
        if len(instances["BLOCK-1"].nodes) != 125 or len(instances["BLOCK-1"].elements) != 64:
            log("ODB block mesh mismatch")
            return False
        if not bounds_match(bounds(instances["PLATE-1"].nodes), ((0.0, 24.0), (0.0, 24.0), (0.0, 3.0))):
            log("ODB plate bounds mismatch")
            return False
        if not bounds_match(bounds(instances["BLOCK-1"].nodes), ((8.0, 16.0), (8.0, 16.0), (3.0, 11.0))):
            log("ODB block bounds mismatch")
            return False
        for cae_name, odb_name in (("Plate-1", "PLATE-1"), ("Block-1", "BLOCK-1")):
            if mesh_signature(instances[odb_name].nodes, instances[odb_name].elements) != CAE_SIGNATURES.get(cae_name):
                log("CAE/ODB node-coordinate or element-connectivity signature mismatch: " + cae_name)
                return False
        for field_name in ("U", "S", "RF"):
            if field_name not in frame.fieldOutputs:
                log("ODB field missing: " + field_name)
                return False
        cpress_name, cpress = field_by_prefix(frame, "CPRESS")
        copen_name, copen = field_by_prefix(frame, "COPEN")
        for field_name in (cpress_name, copen_name):
            normalized = str(field_name).upper()
            if "BLOCK-1_BLOCK_BOTTOM" not in normalized or "PLATE-1_PLATE_TOP" not in normalized:
                log("contact output belongs to unexpected surfaces: " + normalized)
                return False
        pressure_values = [scalar(value) for value in cpress.values if finite(scalar(value))]
        positive_pressures = [value for value in pressure_values if value > 1.0e-8]
        if len(positive_pressures) < 9:
            log("insufficient active contact pressure values")
            return False
        opening_values = [scalar(value) for value in copen.values if finite(scalar(value))]
        if not opening_values or min(opening_values) < -1.0e-5 or max(opening_values) > 0.01:
            log("COPEN values are missing or inconsistent with closed contact")
            return False
        max_contact_pressure = max(positive_pressures)
        block_top = odb.rootAssembly.nodeSets["BLOCK_TOP_NODES"]
        displacement_values = frame.fieldOutputs["U"].getSubset(region=block_top).values
        vertical_displacement = min(float(value.data[2]) for value in displacement_values)
        plate_bottom = odb.rootAssembly.nodeSets["PLATE_BOTTOM_NODES"]
        reaction_values = frame.fieldOutputs["RF"].getSubset(region=plate_bottom).values
        reaction_force = abs(math.fsum(float(value.data[2]) for value in reaction_values))
        mises_values = []
        for value in frame.fieldOutputs["S"].values:
            try:
                mises_values.append(float(value.mises))
            except Exception:
                pass
        max_mises = max(mises_values or [0.0])
        expected_force = 2.0 * 8.0 * 8.0
        if not (1.5 < max_contact_pressure < 4.0):
            log("contact pressure outside physical range")
            return False
        if not (-0.01 < vertical_displacement < -1.0e-6):
            log("vertical displacement outside physical range")
            return False
        if not close(reaction_force, expected_force, rel=0.01, abs_tol=0.25):
            log("reaction/load imbalance: reaction=%s expected=%s" % (reaction_force, expected_force))
            return False
        if not (0.1 < max_mises < 20.0):
            log("stress outside physical range")
            return False
        recomputed = {
            "max_contact_pressure": max_contact_pressure,
            "vertical_displacement": vertical_displacement,
            "reaction_force": reaction_force,
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
            timeout=90,
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
