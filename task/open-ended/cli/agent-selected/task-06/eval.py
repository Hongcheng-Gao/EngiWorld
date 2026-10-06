#!/usr/bin/env python3
"""Evaluate one open-choice task from its final STEP geometry only.

This file is copied verbatim into each generated task.  The trusted JSON spec
contains the task-specific geometry contract; no software identity, command
history, intermediate artifact, or reference-geometry match is evaluated.
"""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", "/home/user/Desktop"))
OUTPUT_ROOT = Path(os.environ.get("OUTPUT_ROOT", str(DESKTOP / "result")))
SPEC_PATH = Path(
    os.environ.get("ENGIWORLD_OPEN_SPEC", str(DESKTOP / "_eval_open_choice_spec.json"))
)


class EvaluationError(RuntimeError):
    pass


class EvaluationDependencyError(RuntimeError):
    """The evaluator cannot run because its software dependency is unavailable."""


def fail(message: str) -> None:
    raise EvaluationError(message)


def number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        fail(f"{label} is not numeric: {value!r}")
    if not math.isfinite(result):
        fail(f"{label} is not finite")
    return result


def mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        fail(f"{label} is missing or is not an object")
    return value


def load_spec() -> dict:
    try:
        value = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"cannot read trusted open-choice spec: {exc}")
    return mapping(value, "trusted open-choice spec")


def find_submission() -> Path:
    if not OUTPUT_ROOT.is_dir():
        fail("result directory is missing")
    candidates = sorted(
        path
        for path in OUTPUT_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".step", ".stp"}
    )
    if len(candidates) != 1:
        fail(
            "result directory must contain exactly one non-empty STEP/STP file; "
            f"found {len(candidates)}"
        )
    if candidates[0].stat().st_size <= 1000:
        fail("the submitted STEP/STP file is empty or implausibly small")
    return candidates[0]


def require_minimum(actual: Any, minimum: Any, label: str, epsilon: float = 1e-6) -> None:
    got = number(actual, label)
    want = number(minimum, label + " minimum")
    if got + epsilon < want:
        fail(f"{label} is {got}, below {want}")


def require_maximum(actual: Any, maximum: Any, label: str, epsilon: float = 1e-6) -> None:
    got = number(actual, label)
    want = number(maximum, label + " maximum")
    if got - epsilon > want:
        fail(f"{label} is {got}, above {want}")


def validate_bounds(actual: Any, expected: Any, tolerance: float, label: str) -> None:
    if not isinstance(actual, list) or not isinstance(expected, list) or len(actual) != 6 or len(expected) != 6:
        fail(f"{label} must contain six coordinates")
    if any(abs(number(got, label) - number(want, label)) > tolerance + 1e-9 for got, want in zip(actual, expected)):
        fail(f"{label} differs from the required envelope: {actual} vs {expected}")


def validate_critical(contract: dict, measurements: dict, volume_tolerance: float) -> None:
    kind = str(contract.get("kind", "none"))
    if str(measurements.get("kind", "none")) != kind:
        fail(f"critical measurement kind is not {kind}")
    if kind == "none":
        return
    if kind == "creepage_web":
        require_minimum(
            measurements.get("length_mm"), contract["minimum_length_mm"], "web length"
        )
        require_maximum(
            measurements.get("probe_missing_volume_mm3"),
            contract["maximum_probe_missing_volume_mm3"],
            "web probe missing volume",
        )
        if contract.get("must_be_single_connected_material") and not measurements.get(
            "single_connected_material"
        ):
            fail("creepage web is not one connected carrier-material region")
        return
    if kind == "heater_exposure":
        require_minimum(
            measurements.get("opening_edge_gap_mm"),
            contract["minimum_opening_edge_gap_mm"],
            "heater opening edge gap",
        )
        if "minimum_gap_web_coverage_ratio" in contract:
            require_minimum(
                measurements.get("gap_web_coverage_ratio"),
                contract["minimum_gap_web_coverage_ratio"],
                "heater gap web coverage",
            )
        if contract.get("gap_web_must_be_single_connected") and not measurements.get(
            "gap_web_single_connected"
        ):
            fail("heater gap web is not one connected material region")
        if contract.get("openings_must_be_distinct_voids") and not measurements.get(
            "openings_are_distinct_voids"
        ):
            fail("heater openings are not distinct connected voids")
        measured_heaters = mapping(measurements.get("heaters"), "heater measurements")
        for ref in contract["refs"]:
            item = mapping(measured_heaters.get(ref), f"heater {ref}")
            require_minimum(
                item.get("open_area_ratio"),
                contract["minimum_open_area_ratio"],
                f"heater {ref} open area",
            )
            require_maximum(
                item.get("carrier_intersection_mm3"),
                contract["maximum_carrier_intersection_per_ref_mm3"],
                f"heater {ref} carrier intersection",
            )
        return
    if kind in {
        "reserved_volume", "optical_corridor", "fuse_keepout",
        "component_radial_keepout", "radial_cavity_clearance",
    }:
        require_maximum(
            measurements.get("carrier_intersection_mm3"),
            contract.get("maximum_carrier_intersection_mm3", volume_tolerance),
            f"{kind} carrier intersection",
        )
        if "maximum_non_target_component_intersection_mm3" in contract:
            require_maximum(
                measurements.get("non_target_component_intersection_mm3"),
                contract["maximum_non_target_component_intersection_mm3"],
                f"{kind} non-target component intersection",
            )
        if kind == "radial_cavity_clearance":
            require_minimum(
                measurements.get("clearance_mm"),
                contract["minimum_clearance_mm"],
                "radial cavity clearance",
            )
        return
    if kind == "thermal_contact_keepout":
        require_minimum(
            measurements.get("contact_coverage_ratio"),
            contract["minimum_contact_coverage_ratio"],
            "thermal contact coverage",
        )
        require_maximum(
            measurements.get("contact_gap_mm"),
            contract["maximum_contact_gap_mm"],
            "thermal contact gap",
        )
        require_maximum(
            measurements.get("contact_missing_volume_mm3"),
            contract.get("maximum_contact_missing_volume_mm3", volume_tolerance),
            "thermal contact missing volume",
        )
        if contract.get("contact_must_be_single_connected") and not measurements.get(
            "contact_single_connected"
        ):
            fail("thermal contact connected material requirement is not satisfied")
        require_maximum(
            measurements.get("keepout_carrier_intersection_mm3"),
            contract["maximum_keepout_carrier_intersection_mm3"],
            "L1 keepout carrier intersection",
        )
        return
    if kind == "rf_shield":
        if not measurements.get("distinct_installed_solid"):
            fail("RF shield is not a distinct installed solid")
        require_minimum(
            measurements.get("shield_coverage_ratio"),
            contract["minimum_shield_coverage_ratio"],
            "RF shield coverage",
        )
        require_maximum(
            measurements.get("shield_package_overlap_mm3"),
            contract["maximum_shield_package_overlap_mm3"],
            "RF shield/package overlap",
        )
        require_maximum(
            measurements.get("shield_missing_volume_mm3"),
            contract["maximum_shield_missing_volume_mm3"],
            "RF shield missing volume",
        )
        require_maximum(
            measurements.get("shield_excess_volume_mm3"),
            contract["maximum_shield_excess_volume_mm3"],
            "RF shield excess volume",
        )
        if "shield_density_g_cm3" in contract:
            expected_mass = number(measurements.get("shield_volume_mm3"), "RF shield volume") * number(
                contract["shield_density_g_cm3"], "RF shield density"
            ) / 1000.0
            if abs(number(measurements.get("shield_mass_g"), "RF shield mass") - expected_mass) > 1e-6:
                fail("RF shield mass is not derived from measured volume and required density")
        return
    if kind == "protected_volume":
        contained = mapping(measurements.get("contained_keepouts"), "contained keepouts")
        for ref in contract.get("contain_keepouts", {}):
            item = mapping(contained.get(ref), f"contained keepout {ref}")
            require_maximum(
                item.get("missing_volume_mm3"),
                contract["maximum_missing_contained_volume_mm3"],
                f"protected volume {ref} containment missing volume",
            )
        excluded = mapping(measurements.get("excluded_keepouts"), "excluded keepouts")
        for ref in contract.get("exclude_keepouts", {}):
            item = mapping(excluded.get(ref), f"excluded keepout {ref}")
            require_maximum(
                item.get("intersection_mm3"),
                contract["maximum_excluded_intersection_mm3"],
                f"protected volume {ref} excluded intersection",
            )
            require_minimum(
                item.get("separation_mm"),
                contract["minimum_excluded_separation_mm"],
                f"protected volume {ref} separation",
            )
        return
    if kind == "required_ribs":
        ribs = mapping(measurements.get("ribs"), "rib measurements")
        for expected in contract["ribs"]:
            rib_id = expected["id"]
            item = mapping(ribs.get(rib_id), f"rib {rib_id}")
            if contract.get("distinct_installed_solids_required") and not item.get(
                "distinct_installed_solid"
            ):
                fail(f"rib {rib_id} is not a distinct installed solid")
            require_minimum(
                item.get("coverage_ratio"),
                contract["minimum_rib_coverage_ratio"],
                f"rib {rib_id} coverage",
            )
            require_maximum(
                item.get("missing_volume_mm3"),
                contract.get("maximum_rib_missing_volume_mm3", volume_tolerance),
                f"rib {rib_id} missing volume",
            )
            if contract.get("ribs_must_be_single_connected") and not item.get(
                "single_connected_material"
            ):
                fail(f"rib {rib_id} connected material requirement is not satisfied")
            require_maximum(
                item.get("maximum_keepout_intersection_mm3"),
                volume_tolerance,
                f"rib {rib_id} keepout intersection",
            )
            require_minimum(
                item.get("minimum_keepout_separation_mm"),
                contract["minimum_keepout_separation_mm"],
                f"rib {rib_id} keepout separation",
            )
        return
    fail(f"unsupported critical semantic rule {kind!r}")


def validate_measurements(spec: dict, measurements: dict) -> None:
    contract = mapping(spec.get("semantic_contract"), "semantic contract")
    result = mapping(measurements, "geometry measurements")
    if not result.get("shape_valid") and "shape_valid" in result:
        fail("final STEP contains invalid geometry")

    tolerance = number(contract.get("geometry_tolerance_mm", 0.1), "geometry tolerance")
    volume_tolerance = number(
        contract.get("volume_tolerance_mm3", 0.1), "volume tolerance"
    )

    structure_contract = contract.get("structure")
    if structure_contract is not None:
        structure_contract = mapping(structure_contract, "structure contract")
        structure = mapping(result.get("structure"), "structure measurement")
        regions = mapping(
            structure.get("required_material_regions"), "required material regions"
        )
        for expected in structure_contract.get("required_material_regions", []):
            region_id = expected["id"]
            item = mapping(regions.get(region_id), f"structure region {region_id}")
            require_minimum(
                item.get("coverage_ratio"),
                structure_contract["minimum_region_coverage_ratio"],
                f"{region_id} coverage",
            )
            require_maximum(
                item.get("missing_volume_mm3"),
                structure_contract["maximum_region_missing_volume_mm3"],
                f"{region_id} missing volume",
            )
            if structure_contract.get("material_regions_must_be_single_connected") and not item.get(
                "single_connected_material"
            ):
                fail(f"{region_id} connected material requirement is not satisfied")
        if structure_contract.get("required_void_regions"):
            void_regions = mapping(structure.get("required_void_regions"), "required void regions")
            for expected in structure_contract["required_void_regions"]:
                region_id = expected["id"]
                item = mapping(void_regions.get(region_id), f"void region {region_id}")
                require_minimum(
                    item.get("void_ratio"), expected["minimum_void_ratio"],
                    f"{region_id} void ratio",
                )
        if structure_contract.get("required_connection_regions"):
            connection_regions = mapping(
                structure.get("required_connection_regions"), "required connection regions"
            )
            for expected in structure_contract["required_connection_regions"]:
                region_id = expected["id"]
                item = mapping(connection_regions.get(region_id), f"connection {region_id}")
                require_minimum(
                    item.get("coverage_ratio"),
                    structure_contract["minimum_connection_coverage_ratio"],
                    f"{region_id} connection coverage",
                )
                require_maximum(
                    item.get("missing_volume_mm3"),
                    structure_contract["maximum_connection_missing_volume_mm3"],
                    f"{region_id} connection missing volume",
                )
                if structure_contract.get("connection_regions_must_be_single_connected") and not item.get(
                    "single_connected_material"
                ):
                    fail(f"{region_id} connection connected material requirement is not satisfied")
        if structure_contract.get("tray_regions_must_share_carrier_component"):
            tray_ids = [
                mapping(regions.get(region_id), f"structure region {region_id}").get(
                    "primary_carrier_component_id"
                )
                for region_id in structure_contract.get("tray_region_ids", [])
            ]
            if not tray_ids or any(value is None or number(value, "tray carrier component") < 0 for value in tray_ids):
                fail("tray carrier component is missing")
            if len(set(tray_ids)) != 1:
                fail("tray carrier component is not shared by base and walls")
            lid_id = mapping(
                regions.get(structure_contract.get("lid_region_id")), "structure region lid"
            ).get("primary_carrier_component_id")
            if structure_contract.get("lid_component_must_differ_from_tray") and lid_id == tray_ids[0]:
                fail("lid carrier component is not separate from tray")
        if structure_contract.get("separate_tray_lid"):
            if not structure.get("tray_present") or not structure.get("lid_present"):
                fail("separate tray/lid geometry is incomplete")
            require_maximum(
                structure.get("seam_material_mm3"),
                structure_contract["maximum_seam_material_mm3"],
                "seam material",
            )
            if structure.get("single_solid_spans_seam"):
                fail("separate tray/lid requirement is violated by one solid spanning the seam")

    minimum_role_coverage = number(
        contract.get("minimum_role_coverage_ratio", 0.98), "minimum role coverage"
    )
    axis_tolerance = number(contract.get("axis_tolerance_mm", tolerance), "axis tolerance")

    def validate_role(item: dict, label: str) -> None:
        require_minimum(item.get("coverage_ratio"), minimum_role_coverage, f"{label} coverage")
        if "bounds_error_mm" in item:
            require_maximum(item.get("bounds_error_mm"), tolerance, f"{label} bounds error")
        if "role_boundary_tolerance_mm" in contract:
            if contract.get("role_geometry_measurement_version") == 2:
                require_maximum(
                    item.get("eroded_ideal_missing_volume_mm3"), volume_tolerance,
                    f"{label} eroded ideal missing volume",
                )
                require_maximum(
                    item.get("outside_dilated_volume_mm3"), volume_tolerance,
                    f"{label} outside dilated ideal volume",
                )
            else:
                boundary_allowance = (
                    number(item.get("ideal_surface_area_mm2"), f"{label} ideal surface area")
                    * number(contract["role_boundary_tolerance_mm"], "role boundary tolerance")
                    + volume_tolerance
                )
                require_maximum(item.get("missing_volume_mm3"), boundary_allowance, f"{label} missing volume")
                require_maximum(item.get("excess_volume_mm3"), boundary_allowance, f"{label} excess volume")
            require_maximum(item.get("center_error_mm"), axis_tolerance, f"{label} center error")
            require_maximum(item.get("size_error_mm"), tolerance, f"{label} size error")

    if "board" in contract or "required_components" in contract:
        pcb = mapping(result.get("pcb"), "PCB measurement")
        if not pcb.get("matched"):
            fail("PCB geometry is missing")
        validate_role(pcb, "PCB")
        if "role_boundary_tolerance_mm" in contract:
            require_maximum(
                pcb.get("hole_core_intersection_mm3")
                if contract.get("role_geometry_measurement_version") == 2
                else pcb.get("hole_intersection_mm3"),
                volume_tolerance,
                "PCB mounting hole cores"
                if contract.get("role_geometry_measurement_version") == 2
                else "PCB mounting holes",
            )

        components = mapping(result.get("components"), "component measurements")
        for ref in contract.get("required_components", []):
            item = mapping(components.get(ref), f"component {ref}")
            if not item.get("matched"):
                fail(f"component {ref} geometry is missing")
            validate_role(item, f"component {ref}")

    if "carrier_bounds_mm" in contract:
        carrier = mapping(result.get("carrier"), "carrier measurement")
        validate_bounds(
            carrier.get("bounds_mm"), contract["carrier_bounds_mm"], tolerance, "carrier bounds"
        )
        require_minimum(carrier.get("volume_mm3"), 0.01, "carrier volume")
        if "minimum_structure_coverage_ratio" in contract:
            require_minimum(
                carrier.get("structure_coverage_ratio"),
                contract["minimum_structure_coverage_ratio"],
                "carrier structure coverage",
            )
        if "enclosure_density_g_cm3" in contract:
            expected_mass = number(carrier.get("volume_mm3"), "carrier volume") * number(
                contract["enclosure_density_g_cm3"], "enclosure density"
            ) / 1000.0
            if abs(number(carrier.get("mass_g"), "carrier mass") - expected_mass) > 1e-6:
                fail("carrier mass is not derived from measured volume and required density")

        standoffs = mapping(result.get("standoffs"), "standoff measurements")
        cross_section_ids = []
        for ref in contract.get("required_mounts", []):
            item = mapping(standoffs.get(ref), f"standoff {ref}")
            if contract.get("standoff_measurement_version", 1) >= 2:
                cross_section_ids.append(item.get("cross_section_component_id"))
            if contract.get("standoff_measurement_version") == 3:
                require_minimum(
                    item.get("core_slice_minimum_coverage_ratio"),
                    contract.get("minimum_standoff_core_slice_coverage_ratio", 0.995),
                    f"standoff {ref} core slice coverage",
                )
                require_minimum(
                    item.get("full_height_core_coverage_ratio"),
                    contract.get("minimum_standoff_full_height_core_coverage_ratio", 0.999),
                    f"standoff {ref} full-height core coverage",
                )
                require_maximum(
                    item.get("full_height_core_missing_volume_mm3"), volume_tolerance,
                    f"standoff {ref} full-height core missing volume",
                )
                if not item.get("core_single_connected"):
                    fail(f"standoff {ref} core connectivity is not satisfied")
                require_maximum(
                    item.get("bore_diameter_error_mm"), tolerance,
                    f"standoff {ref} bore diameter",
                )
                require_maximum(
                    item.get("bore_axis_error_mm"), axis_tolerance,
                    f"standoff {ref} bore axis",
                )
                require_maximum(
                    item.get("bore_cutter_core_intersection_mm3"), volume_tolerance,
                    f"standoff {ref} bore cutter core",
                )
                require_maximum(
                    item.get("outer_dilated_intersection_mm3"), volume_tolerance,
                    f"standoff {ref} outer dilated envelope",
                )
            else:
                require_minimum(
                    item.get("effective_ring_coverage_ratio", item.get("ring_coverage_ratio")),
                    contract.get("minimum_standoff_ring_coverage_ratio", 0.99)
                    if contract.get("standoff_measurement_version") == 2 else 0.90,
                    f"standoff {ref} effective ring coverage",
                )
            if contract.get("standoff_measurement_version", 1) >= 2:
                require_maximum(
                    item.get("bore_core_intersection_mm3"), volume_tolerance,
                    f"standoff {ref} bore core intersection",
                )
                require_maximum(
                    item.get("outer_diameter_error_mm"), tolerance,
                    f"standoff {ref} outer diameter",
                )
                require_maximum(
                    item.get("axis_error_mm"), axis_tolerance,
                    f"standoff {ref} axis",
                )
            else:
                require_maximum(
                    item.get("bore_intersection_mm3"), volume_tolerance,
                    f"standoff {ref} bore",
                )
        if cross_section_ids and len(set(cross_section_ids)) != len(cross_section_ids):
            fail("standoff cross-sections are not distinct")

        accesses = mapping(result.get("accesses"), "access measurements")
        for expected in contract.get("accesses", []):
            ref = expected["ref"]
            item = mapping(accesses.get(ref), f"access {ref}")
            require_minimum(
                item.get("open_ratio"), expected.get("minimum_open_ratio", 0.99), f"access {ref} open ratio"
            )
            require_maximum(
                item.get("carrier_intersection_mm3"),
                expected.get("maximum_carrier_intersection_mm3", volume_tolerance),
                f"access {ref} carrier intersection",
            )
            require_minimum(
                item.get("guard_coverage_ratio"),
                expected.get("minimum_guard_coverage_ratio", 0.80),
                f"access {ref} guard coverage",
            )
            guard_regions = mapping(item.get("guard_regions"), f"access {ref} guard regions")
            for region_id in expected.get("guard_region_ids", []):
                guard = mapping(guard_regions.get(region_id), f"access {ref} guard {region_id}")
                require_minimum(
                    guard.get("coverage_ratio"), expected["minimum_guard_coverage_ratio"],
                    f"access {ref} guard {region_id} coverage",
                )
                require_maximum(
                    guard.get("missing_volume_mm3"), expected["maximum_guard_missing_volume_mm3"],
                    f"access {ref} guard {region_id} missing volume",
                )
                if expected.get("guard_regions_must_be_connected") and not guard.get(
                    "single_connected_material"
                ):
                    fail(f"access {ref} guard {region_id} connected material requirement is not satisfied")

        if contract.get("minimum_side_clearance_mm") is not None:
            require_minimum(
                result.get("minimum_side_clearance_mm"),
                contract["minimum_side_clearance_mm"],
                "side clearance",
            )
        if contract.get("minimum_top_clearance_mm") is not None:
            require_minimum(
                result.get("minimum_top_clearance_mm"),
                contract["minimum_top_clearance_mm"],
                "top clearance",
            )
        top_clearances = mapping(result.get("top_clearances", {}), "top clearances")
        for expected in contract.get("top_clearance_regions", []):
            ref = expected["ref"]
            item = mapping(top_clearances.get(ref), f"top clearance {ref}")
            if not item.get("covering_material_present"):
                fail(f"top clearance {ref} covering material is missing")
            require_maximum(
                item.get("carrier_intersection_mm3"),
                expected["maximum_carrier_intersection_mm3"],
                f"top clearance {ref} carrier intersection",
            )
            require_minimum(
                item.get("clearance_mm"), expected["minimum_clearance_mm"],
                f"top clearance {ref}",
            )
        require_maximum(
            result.get("unintended_interference_mm3"),
            volume_tolerance,
            "unintended interference",
        )

    if "critical_rules" in contract:
        measured_rules = result.get("critical_rules")
        if not isinstance(measured_rules, list):
            fail("critical rule measurements are missing or are not a list")
        measured_by_kind = {
            str(item.get("kind")): mapping(item, "critical rule measurement")
            for item in measured_rules
        }
        for rule in contract["critical_rules"]:
            kind = str(rule.get("kind"))
            if kind not in measured_by_kind:
                fail(f"critical rule measurement {kind} is missing")
            validate_critical(mapping(rule, f"critical rule {kind}"), measured_by_kind[kind], volume_tolerance)
    else:
        validate_critical(
            mapping(contract.get("critical", {"kind": "none"}), "critical contract"),
            mapping(result.get("critical", {"kind": "none"}), "critical measurements"),
            volume_tolerance,
        )


FREECAD_CHECKER = r'''
from __future__ import annotations

import json
import math
import os
import traceback

import FreeCAD
import Part


candidate_path = os.environ["ENGIWORLD_OPEN_CANDIDATE"]
spec_path = os.environ["ENGIWORLD_OPEN_SPEC"]
result_path = os.environ["ENGIWORLD_OPEN_RESULT"]


def bounds(shape):
    box = shape.BoundBox
    return [box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax]


def bounds_error(shape, expected):
    return max(abs(a - b) for a, b in zip(bounds(shape), expected))


def box_shape(values):
    x1, y1, z1, x2, y2, z2 = [float(value) for value in values]
    return Part.makeBox(x2 - x1, y2 - y1, z2 - z1, FreeCAD.Vector(x1, y1, z1))


def z_cylinder(values):
    x1, y1, z1, x2, y2, z2 = [float(value) for value in values]
    radius = min(x2 - x1, y2 - y1) / 2.0
    return Part.makeCylinder(radius, z2 - z1, FreeCAD.Vector((x1 + x2) / 2.0, (y1 + y2) / 2.0, z1))


def finite_cylinder(start, end, radius):
    a = FreeCAD.Vector(*[float(value) for value in start])
    b = FreeCAD.Vector(*[float(value) for value in end])
    direction = b.sub(a)
    return Part.makeCylinder(float(radius), direction.Length, a, direction)


def compound(shapes):
    useful = [shape for shape in shapes if not shape.isNull() and float(shape.Volume) > 0.000001]
    return Part.makeCompound(useful) if useful else Part.Shape()


def overlap_ratio(actual, ideal):
    volume = float(ideal.Volume)
    return float(actual.common(ideal).Volume) / volume if volume > 0 else 0.0


def ideal_board(contract):
    board = contract["board"]
    shape = box_shape(board["bounds_mm"])
    z1, z2 = board["bounds_mm"][2], board["bounds_mm"][5]
    for hole in board.get("mount_holes", []):
        cutter = Part.makeCylinder(
            float(hole["diameter_mm"]) / 2.0,
            float(z2 - z1) + 0.4,
            FreeCAD.Vector(float(hole["x_mm"]), float(hole["y_mm"]), float(z1) - 0.2),
        )
        shape = shape.cut(cutter)
    return shape


def board_role_envelopes(contract, tolerance):
    board = contract["board"]
    values = [float(value) for value in board["bounds_mm"]]
    eroded = box_shape([
        values[0] + tolerance, values[1] + tolerance, values[2] + tolerance,
        values[3] - tolerance, values[4] - tolerance, values[5] - tolerance,
    ])
    dilated = box_shape([
        values[0] - tolerance, values[1] - tolerance, values[2] - tolerance,
        values[3] + tolerance, values[4] + tolerance, values[5] + tolerance,
    ])
    for hole in board.get("mount_holes", []):
        center = FreeCAD.Vector(float(hole["x_mm"]), float(hole["y_mm"]), values[2] - tolerance - 0.2)
        height = values[5] - values[2] + 2.0 * tolerance + 0.4
        eroded = eroded.cut(Part.makeCylinder(float(hole["diameter_mm"]) / 2.0 + tolerance, height, center))
        dilated = dilated.cut(Part.makeCylinder(max(0.01, float(hole["diameter_mm"]) / 2.0 - tolerance), height, center))
    return eroded, dilated


def ideal_component(item):
    x, y = float(item["x_mm"]), float(item["y_mm"])
    sx, sy, sz = [float(value) for value in item["bbox_mm"]]
    z = float(item["z_min_mm"])
    if item.get("shape") == "cylinder":
        return Part.makeCylinder(min(sx, sy) / 2.0, sz, FreeCAD.Vector(x, y, z))
    return Part.makeBox(sx, sy, sz, FreeCAD.Vector(x - sx / 2.0, y - sy / 2.0, z))


def component_role_envelopes(item, tolerance):
    x, y = float(item["x_mm"]), float(item["y_mm"])
    sx, sy, sz = [float(value) for value in item["bbox_mm"]]
    z = float(item["z_min_mm"])
    if item.get("shape") == "cylinder":
        radius = min(sx, sy) / 2.0
        eroded_height = max(0.01, sz - 2.0 * tolerance)
        eroded = Part.makeCylinder(
            max(0.01, radius - tolerance), eroded_height,
            FreeCAD.Vector(x, y, z + (sz - eroded_height) / 2.0),
        )
        dilated = Part.makeCylinder(
            radius + tolerance, sz + 2.0 * tolerance,
            FreeCAD.Vector(x, y, z - tolerance),
        )
        return eroded, dilated
    eroded_size = [max(0.01, value - 2.0 * tolerance) for value in (sx, sy, sz)]
    eroded = Part.makeBox(*eroded_size, FreeCAD.Vector(
        x - eroded_size[0] / 2.0,
        y - eroded_size[1] / 2.0,
        z + (sz - eroded_size[2]) / 2.0,
    ))
    dilated = Part.makeBox(
        sx + 2.0 * tolerance, sy + 2.0 * tolerance, sz + 2.0 * tolerance,
        FreeCAD.Vector(x - sx / 2.0 - tolerance, y - sy / 2.0 - tolerance, z - tolerance),
    )
    return eroded, dilated


def select_role_group(solids, used, ideal, maximum_error):
    expected = bounds(ideal)
    matches = []
    for index, solid in enumerate(solids):
        if index in used:
            continue
        actual = bounds(solid)
        contained = all(
            actual[position] >= expected[position] - maximum_error
            for position in (0, 1, 2)
        ) and all(
            actual[position] <= expected[position] + maximum_error
            for position in (3, 4, 5)
        )
        if contained and float(solid.common(ideal).Volume) > 0.001:
            matches.append((index, solid))
    if not matches:
        return [], None
    indices = [index for index, _solid in matches]
    used.update(indices)
    return indices, compound([solid for _index, solid in matches])


def role_measurement(solid, ideal, eroded=None, dilated=None):
    if solid is None:
        return {
            "matched": False, "coverage_ratio": 0.0, "bounds_error_mm": 1e9,
            "missing_volume_mm3": float(ideal.Volume), "excess_volume_mm3": 0.0,
            "ideal_surface_area_mm2": float(ideal.Area),
            "center_error_mm": 1e9, "size_error_mm": 1e9,
            "eroded_ideal_missing_volume_mm3": float(eroded.Volume) if eroded is not None else float(ideal.Volume),
            "outside_dilated_volume_mm3": 0.0,
        }
    actual_bounds = bounds(solid)
    ideal_bounds = bounds(ideal)
    actual_center = [(actual_bounds[index] + actual_bounds[index + 3]) / 2.0 for index in range(3)]
    ideal_center = [(ideal_bounds[index] + ideal_bounds[index + 3]) / 2.0 for index in range(3)]
    actual_size = [actual_bounds[index + 3] - actual_bounds[index] for index in range(3)]
    ideal_size = [ideal_bounds[index + 3] - ideal_bounds[index] for index in range(3)]
    return {
        "matched": True,
        "coverage_ratio": overlap_ratio(solid, ideal),
        "bounds_error_mm": bounds_error(solid, ideal_bounds),
        "missing_volume_mm3": float(ideal.cut(solid).Volume),
        "excess_volume_mm3": float(solid.cut(ideal).Volume),
        "ideal_surface_area_mm2": float(ideal.Area),
        "center_error_mm": max(abs(actual_center[index] - ideal_center[index]) for index in (0, 1)),
        "size_error_mm": max(abs(actual_size[index] - ideal_size[index]) for index in range(3)),
        "eroded_ideal_missing_volume_mm3": float(eroded.cut(solid).Volume) if eroded is not None else 0.0,
        "outside_dilated_volume_mm3": float(solid.cut(dilated).Volume) if dilated is not None else 0.0,
    }


def access_shape(item, key):
    values = item[key]
    if item["shape"] == "cylinder":
        return z_cylinder(values)
    return box_shape(values)


def expanded_access_shape(item, key, margin):
    values = [float(value) for value in item[key]]
    values = [
        values[0] - margin, values[1] - margin, values[2] - margin,
        values[3] + margin, values[4] + margin, values[5] + margin,
    ]
    return z_cylinder(values) if item["shape"] == "cylinder" else box_shape(values)


def access_guard_regions(item, contract):
    guard = float(item.get("minimum_guard_mm", 0.25))
    tolerance = float(contract["geometry_tolerance_mm"])
    guard_core = max(0.05, guard - tolerance)
    direction = item["direction"]
    outer = contract["carrier_bounds_mm"]
    cavity = contract["cavity_bounds_mm"]
    cutter = [float(value) for value in item["cutter_bounds_mm"]]
    if direction == "Z_PLUS":
        center_x = (cutter[0] + cutter[3]) / 2.0
        center_y = (cutter[1] + cutter[4]) / 2.0
        radius = min(cutter[3] - cutter[0], cutter[4] - cutter[1]) / 2.0
        z1 = float(contract["lid_inner_z_mm"]) + tolerance
        z2 = outer[5] - tolerance
        expanded = Part.makeCylinder(radius + tolerance + guard_core, z2 - z1, FreeCAD.Vector(center_x, center_y, z1))
        inner = Part.makeCylinder(radius + tolerance, z2 - z1, FreeCAD.Vector(center_x, center_y, z1))
        return {"annular_guard": expanded.cut(inner)}
    if direction in {"X_MINUS", "X_PLUS"}:
        normal_min, normal_max = (
            (outer[0] + tolerance, cavity[0] - tolerance)
            if direction == "X_MINUS"
            else (cavity[3] + tolerance, outer[3] - tolerance)
        )
        return {
            "tangent_minus": box_shape([normal_min, cutter[1] - tolerance - guard_core, cutter[2] - tolerance, normal_max, cutter[1] - tolerance, cutter[5] + tolerance]),
            "tangent_plus": box_shape([normal_min, cutter[4] + tolerance, cutter[2] - tolerance, normal_max, cutter[4] + tolerance + guard_core, cutter[5] + tolerance]),
            "vertical_minus": box_shape([normal_min, cutter[1] - tolerance - guard_core, cutter[2] - tolerance - guard_core, normal_max, cutter[4] + tolerance + guard_core, cutter[2] - tolerance]),
            "vertical_plus": box_shape([normal_min, cutter[1] - tolerance - guard_core, cutter[5] + tolerance, normal_max, cutter[4] + tolerance + guard_core, cutter[5] + tolerance + guard_core]),
        }
    else:
        normal_min, normal_max = (
            (outer[1] + tolerance, cavity[1] - tolerance)
            if direction == "Y_MINUS"
            else (cavity[4] + tolerance, outer[4] - tolerance)
        )
        return {
            "tangent_minus": box_shape([cutter[0] - tolerance - guard_core, normal_min, cutter[2] - tolerance, cutter[0] - tolerance, normal_max, cutter[5] + tolerance]),
            "tangent_plus": box_shape([cutter[3] + tolerance, normal_min, cutter[2] - tolerance, cutter[3] + tolerance + guard_core, normal_max, cutter[5] + tolerance]),
            "vertical_minus": box_shape([cutter[0] - tolerance - guard_core, normal_min, cutter[2] - tolerance - guard_core, cutter[3] + tolerance + guard_core, normal_max, cutter[2] - tolerance]),
            "vertical_plus": box_shape([cutter[0] - tolerance - guard_core, normal_min, cutter[5] + tolerance, cutter[3] + tolerance + guard_core, normal_max, cutter[5] + tolerance + guard_core]),
        }


def structure_measurements(contract, carrier, carrier_solids):
    structure = contract["structure"]
    regions = {}
    for item in structure["required_material_regions"]:
        probe = compound([box_shape(values) for values in item["boxes_mm"]])
        for access in contract.get("accesses", []):
            probe = probe.cut(expanded_access_shape(access, "cutter_bounds_mm", float(contract["geometry_tolerance_mm"])))
        for mount in contract.get("mounts", []):
            tolerance = float(contract["geometry_tolerance_mm"])
            bore = Part.makeCylinder(
                float(mount["bore_diameter_mm"]) / 2.0 + tolerance,
                float(mount["bore_cutter_z_max_mm"] - mount["bore_cutter_z_min_mm"]),
                FreeCAD.Vector(
                    float(mount["x_mm"]), float(mount["y_mm"]),
                    float(mount["bore_cutter_z_min_mm"]),
                ),
            )
            probe = probe.cut(bore)
        covered = float(carrier.common(probe).Volume)
        material = carrier.common(probe)
        component_overlaps = [
            (float(solid.common(probe).Volume), index)
            for index, solid in enumerate(carrier_solids)
        ]
        component_ids = [index for overlap, index in component_overlaps if overlap > 0.0001]
        primary_component_id = (
            max(component_overlaps)[1] if component_ids else -1
        )
        regions[item["id"]] = {
            "coverage_ratio": covered / float(probe.Volume) if float(probe.Volume) > 0 else 1.0,
            "missing_volume_mm3": max(0.0, float(probe.Volume) - covered),
            "single_connected_material": len([solid for solid in material.Solids if float(solid.Volume) > 0.0001]) == 1,
            "carrier_component_ids": component_ids,
            "primary_carrier_component_id": primary_component_id,
        }
    void_regions = {}
    for item in structure.get("required_void_regions", []):
        probe = compound([box_shape(values) for values in item["boxes_mm"]])
        occupied = float(carrier.common(probe).Volume)
        void_regions[item["id"]] = {
            "void_ratio": max(0.0, 1.0 - occupied / float(probe.Volume)),
            "carrier_intersection_mm3": occupied,
        }
    connection_regions = {}
    for item in structure.get("required_connection_regions", []):
        probe = compound([box_shape(values) for values in item["boxes_mm"]])
        for access in contract.get("accesses", []):
            probe = probe.cut(expanded_access_shape(
                access, "cutter_bounds_mm", float(contract["geometry_tolerance_mm"])
            ))
        material = carrier.common(probe)
        covered = float(material.Volume)
        connection_regions[item["id"]] = {
            "coverage_ratio": covered / float(probe.Volume) if float(probe.Volume) > 0 else 1.0,
            "missing_volume_mm3": max(0.0, float(probe.Volume) - covered),
            "single_connected_material": len([
                solid for solid in material.Solids if float(solid.Volume) > 0.0001
            ]) == 1,
        }
    result = {
        "required_material_regions": regions,
        "required_void_regions": void_regions,
        "required_connection_regions": connection_regions,
    }
    if structure.get("separate_tray_lid"):
        tray_probe = box_shape(structure["tray_bounds_mm"])
        lid_probe = box_shape(structure["lid_bounds_mm"])
        seam_probe = box_shape(structure["seam_bounds_mm"])
        result.update({
            "tray_present": float(carrier.common(tray_probe).Volume) > 0.01,
            "lid_present": float(carrier.common(lid_probe).Volume) > 0.01,
            "seam_material_mm3": float(carrier.common(seam_probe).Volume),
            "single_solid_spans_seam": any(
                float(solid.common(tray_probe).Volume) > 0.01
                and float(solid.common(lid_probe).Volume) > 0.01
                for solid in carrier_solids
            ),
        })
    return result


def clearance_measurements(contract, carrier):
    board = contract["board"]["bounds_mm"]
    required_side = contract.get("minimum_side_clearance_mm")
    minimum_side = None
    if required_side is not None:
        distance = float(required_side)
        side_probes = [
            box_shape([board[0] - distance, board[1], board[2], board[0], board[4], board[5]]),
            box_shape([board[3], board[1], board[2], board[3] + distance, board[4], board[5]]),
            box_shape([board[0], board[1] - distance, board[2], board[3], board[1], board[5]]),
            box_shape([board[0], board[4], board[2], board[3], board[4] + distance, board[5]]),
        ]
        intrusion = max(float(carrier.common(probe).Volume) for probe in side_probes)
        minimum_side = distance if intrusion <= float(contract["volume_tolerance_mm3"]) else 0.0

    top_clearances = {}
    for item in contract.get("top_clearance_regions", []):
        probe = z_cylinder(item["bounds_mm"]) if item["shape"] == "cylinder" else box_shape(item["bounds_mm"])
        intersection = float(carrier.common(probe).Volume)
        required = float(item["minimum_clearance_mm"])
        search_bounds = list(item["bounds_mm"])
        search_bounds[5] = float(item["search_z_max_mm"])
        search = z_cylinder(search_bounds) if item["shape"] == "cylinder" else box_shape(search_bounds)
        covering = carrier.common(search)
        clearance = (
            max(0.0, float(covering.BoundBox.ZMin) - float(search_bounds[2]))
            if not covering.isNull() else 1e9
        )
        top_clearances[item["ref"]] = {
            "covering_material_present": not covering.isNull() and float(covering.Volume) > 0.0001,
            "carrier_intersection_mm3": intersection,
            "clearance_mm": clearance,
        }
    minimum_top = min(
        (item["clearance_mm"] for item in top_clearances.values()),
        default=None,
    )
    return minimum_side, minimum_top, top_clearances


def critical_measurement(critical, contract, carrier, carrier_solids, component_shapes):
    kind = critical.get("kind", "none")
    if kind == "none":
        return {"kind": "none"}
    if kind == "creepage_web":
        probe = box_shape(critical["probe_bounds_mm"])
        material = carrier.common(probe)
        return {
            "kind": kind,
            "length_mm": float(material.BoundBox.XLength) if not material.isNull() else 0.0,
            "probe_missing_volume_mm3": max(0.0, float(probe.Volume) - float(material.Volume)),
            "single_connected_material": len([solid for solid in material.Solids if solid.Volume > 0.0001]) == 1,
        }
    if kind == "heater_exposure":
        values = {}
        for ref in critical["refs"]:
            item = next(value for value in contract["accesses"] if value["ref"] == ref)
            probe = access_shape(item, "projected_bounds_mm")
            intersection = float(carrier.common(probe).Volume)
            values[ref] = {
                "carrier_intersection_mm3": intersection,
                "open_area_ratio": max(0.0, 1.0 - intersection / float(probe.Volume)),
            }
        gap_probe = box_shape(critical["minimum_gap_probe_bounds_mm"])
        gap_material = carrier.common(gap_probe)
        gap_connected = len([solid for solid in gap_material.Solids if solid.Volume > 0.0001]) == 1
        coverage = float(gap_material.Volume) / float(gap_probe.Volume)
        lid_region = next(item for item in contract["structure"]["required_material_regions"] if item["id"] == "lid")
        lid_probe = compound([box_shape(values) for values in lid_region["boxes_mm"]])
        lid_void = lid_probe.cut(carrier)
        void_solids = [solid for solid in lid_void.Solids if float(solid.Volume) > 0.0001]
        opening_solids = []
        for ref in critical["refs"]:
            item = next(value for value in contract["accesses"] if value["ref"] == ref)
            seed = access_shape(item, "projected_bounds_mm").common(lid_probe)
            ranked = sorted(
                ((float(void.common(seed).Volume), index, void) for index, void in enumerate(void_solids)),
                reverse=True,
                key=lambda row: row[0],
            )
            opening_solids.append(ranked[0] if ranked and ranked[0][0] > 0.001 else (0.0, -1, Part.Shape()))
        distinct_voids = len({item[1] for item in opening_solids}) == len(critical["refs"]) and all(item[1] >= 0 for item in opening_solids)
        opening_gap = (
            min(float(a[2].distToShape(b[2])[0]) for index, a in enumerate(opening_solids) for b in opening_solids[index + 1:])
            if distinct_voids else 0.0
        )
        return {
            "kind": kind,
            "opening_edge_gap_mm": opening_gap,
            "gap_web_coverage_ratio": coverage,
            "gap_web_single_connected": gap_connected,
            "openings_are_distinct_voids": distinct_voids,
            "heaters": values,
        }
    if kind in {"reserved_volume", "fuse_keepout", "component_radial_keepout", "radial_cavity_clearance"}:
        probe = z_cylinder(critical["bounds_mm"])
        intersection = float(carrier.common(probe).Volume)
        result = {
            "kind": kind,
            "carrier_intersection_mm3": intersection,
        }
        if "target_ref" in critical:
            other_shapes = [shape for ref, shape in component_shapes.items() if ref != critical["target_ref"]]
            other = compound(other_shapes)
            result["non_target_component_intersection_mm3"] = (
                float(other.common(probe).Volume) if not other.isNull() else 0.0
            )
        if kind == "radial_cavity_clearance":
            result["clearance_mm"] = (
                float(critical["minimum_clearance_mm"])
                if intersection <= float(critical["maximum_carrier_intersection_mm3"])
                else 0.0
            )
        return result
    if kind == "optical_corridor":
        probe = finite_cylinder(critical["start_mm"], critical["end_mm"], critical["radius_mm"])
        return {"kind": kind, "carrier_intersection_mm3": float(carrier.common(probe).Volume)}
    if kind == "thermal_contact_keepout":
        contact = box_shape(critical["contact_bounds_mm"])
        actual = carrier.common(contact)
        keepout = z_cylinder(critical["keepout_bounds_mm"])
        gap = max(0.0, float(actual.BoundBox.ZMin) - float(critical["contact_bounds_mm"][2])) if not actual.isNull() else 1e9
        return {
            "kind": kind,
            "contact_coverage_ratio": float(actual.Volume) / float(contact.Volume),
            "contact_missing_volume_mm3": max(0.0, float(contact.Volume) - float(actual.Volume)),
            "contact_single_connected": len([
                solid for solid in actual.Solids if float(solid.Volume) > 0.0001
            ]) == 1,
            "contact_gap_mm": gap,
            "keepout_carrier_intersection_mm3": float(carrier.common(keepout).Volume),
        }
    if kind == "rf_shield":
        outer = box_shape(critical["outer_bounds_mm"])
        inner = box_shape(critical["inner_bounds_mm"])
        ideal = outer.cut(inner)
        matches = [solid for solid in carrier_solids if bounds_error(solid, critical["outer_bounds_mm"]) <= 0.3]
        actual = matches[0] if len(matches) == 1 else Part.Shape()
        package_shapes = [solid for solid in carrier_solids if solid not in matches]
        package = compound(package_shapes)
        return {
            "kind": kind,
            "distinct_installed_solid": len(matches) == 1,
            "shield_coverage_ratio": overlap_ratio(actual, ideal) if len(matches) == 1 else 0.0,
            "shield_package_overlap_mm3": float(actual.common(package).Volume) if len(matches) == 1 and not package.isNull() else 0.0,
            "shield_missing_volume_mm3": float(ideal.cut(actual).Volume) if len(matches) == 1 else float(ideal.Volume),
            "shield_excess_volume_mm3": float(actual.cut(ideal).Volume) if len(matches) == 1 else 0.0,
            "shield_volume_mm3": float(actual.Volume) if len(matches) == 1 else 0.0,
            "shield_mass_g": float(actual.Volume) * float(critical["shield_density_g_cm3"]) / 1000.0 if len(matches) == 1 else 0.0,
        }
    if kind == "protected_volume":
        protected = box_shape(critical["bounds_mm"])
        contained = {}
        for ref, values in critical.get("contain_keepouts", {}).items():
            keepout = z_cylinder(values)
            contained[ref] = {
                "missing_volume_mm3": float(keepout.cut(protected).Volume),
            }
        excluded = {}
        for ref, values in critical.get("exclude_keepouts", {}).items():
            keepout = z_cylinder(values)
            excluded[ref] = {
                "intersection_mm3": float(keepout.common(protected).Volume),
                "separation_mm": float(keepout.distToShape(protected)[0]),
            }
        return {
            "kind": kind,
            "contained_keepouts": contained,
            "excluded_keepouts": excluded,
        }
    if kind == "required_ribs":
        keepouts = [z_cylinder(item["bounds_mm"]) for item in critical["keepouts"]]
        results = {}
        for item in critical["ribs"]:
            ideal = box_shape(item["bounds_mm"])
            intersection = carrier.common(ideal)
            distinct = [
                solid for solid in carrier_solids
                if bounds_error(solid, item["bounds_mm"]) <= float(contract["geometry_tolerance_mm"])
            ]
            results[item["id"]] = {
                "distinct_installed_solid": len(distinct) == 1,
                "coverage_ratio": float(intersection.Volume) / float(ideal.Volume),
                "missing_volume_mm3": max(0.0, float(ideal.Volume) - float(intersection.Volume)),
                "single_connected_material": len([
                    solid for solid in intersection.Solids if float(solid.Volume) > 0.0001
                ]) == 1,
                "maximum_keepout_intersection_mm3": max(float(intersection.common(shape).Volume) for shape in keepouts),
                "minimum_keepout_separation_mm": min(float(intersection.distToShape(shape)[0]) for shape in keepouts),
            }
        return {"kind": kind, "ribs": results}
    raise RuntimeError("unsupported critical semantic rule: " + str(kind))


def evaluate():
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    contract = spec["semantic_contract"]
    candidate = Part.read(candidate_path)
    if candidate.isNull() or not candidate.isValid():
        raise RuntimeError("candidate STEP is empty or invalid")
    solids = [solid for solid in candidate.Solids if float(solid.Volume) > 0.001]
    if not solids:
        raise RuntimeError("candidate STEP contains no solid geometry")

    used = set()
    board_ideal = ideal_board(contract)
    role_tolerance = float(contract.get("role_boundary_tolerance_mm", contract["geometry_tolerance_mm"]))
    board_eroded, board_dilated = board_role_envelopes(contract, role_tolerance)
    _indices, board_actual = select_role_group(solids, used, board_ideal, 0.3)
    pcb_metrics = role_measurement(board_actual, board_ideal, board_eroded, board_dilated)
    hole_shapes = []
    board_bounds = contract["board"]["bounds_mm"]
    for hole in contract["board"].get("mount_holes", []):
        hole_shapes.append(Part.makeCylinder(
            float(hole["diameter_mm"]) / 2.0,
            float(board_bounds[5] - board_bounds[2]),
            FreeCAD.Vector(float(hole["x_mm"]), float(hole["y_mm"]), float(board_bounds[2])),
        ))
    holes = compound(hole_shapes)
    pcb_metrics["hole_intersection_mm3"] = (
        float(board_actual.common(holes).Volume)
        if board_actual is not None and not holes.isNull() else 0.0
    )
    hole_core_shapes = []
    hole_core_height = max(0.01, float(board_bounds[5] - board_bounds[2]) - 2.0 * role_tolerance)
    for hole in contract["board"].get("mount_holes", []):
        hole_core_shapes.append(Part.makeCylinder(
            max(0.01, float(hole["diameter_mm"]) / 2.0 - role_tolerance),
            hole_core_height,
            FreeCAD.Vector(
                float(hole["x_mm"]), float(hole["y_mm"]),
                float(board_bounds[2]) + (float(board_bounds[5] - board_bounds[2]) - hole_core_height) / 2.0,
            ),
        ))
    hole_cores = compound(hole_core_shapes)
    pcb_metrics["hole_core_intersection_mm3"] = (
        float(board_actual.common(hole_cores).Volume)
        if board_actual is not None and not hole_cores.isNull() else 0.0
    )

    component_ideals = {}
    component_shapes = {}
    component_metrics = {}
    for item in contract.get("components", []):
        ideal = ideal_component(item)
        eroded, dilated = component_role_envelopes(item, role_tolerance)
        component_ideals[item["ref"]] = ideal
        _indices, actual = select_role_group(solids, used, ideal, 0.3)
        if actual is not None:
            component_shapes[item["ref"]] = actual
        component_metrics[item["ref"]] = role_measurement(actual, ideal, eroded, dilated)

    carrier_solids = [solid for index, solid in enumerate(solids) if index not in used]
    carrier = compound(carrier_solids)
    if carrier.isNull() or float(carrier.Volume) <= 0.01:
        raise RuntimeError("cannot identify carrier/enclosure geometry")

    structure = structure_measurements(contract, carrier, carrier_solids)
    standoffs = {}
    mount_items = contract.get("mounts", [])
    cross_solids = []
    if mount_items:
        first = mount_items[0]
        slice_center = (float(first["z_min_mm"]) + float(first["z_max_mm"])) / 2.0
        slice_height = min(0.1, (float(first["z_max_mm"]) - float(first["z_min_mm"])) / 4.0)
        outer_bounds = contract["carrier_bounds_mm"]
        section_slab = box_shape([
            outer_bounds[0], outer_bounds[1], slice_center - slice_height / 2.0,
            outer_bounds[3], outer_bounds[4], slice_center + slice_height / 2.0,
        ])
        cross_solids = [solid for solid in carrier.common(section_slab).Solids if float(solid.Volume) > 0.0001]
    for item in mount_items:
        z1, z2 = float(item["z_min_mm"]), float(item["z_max_mm"])
        tolerance = float(contract["geometry_tolerance_mm"])
        radial_tolerance = float(contract.get("standoff_radial_tolerance_mm", tolerance / 2.0))
        outer_radius = float(item["outer_diameter_mm"]) / 2.0
        bore_radius = float(item["bore_diameter_mm"]) / 2.0
        core_height = max(0.01, z2 - z1 - 2.0 * tolerance)
        core_outer = Part.makeCylinder(outer_radius - radial_tolerance, core_height, FreeCAD.Vector(item["x_mm"], item["y_mm"], z1 + tolerance))
        core_inner = Part.makeCylinder(bore_radius + radial_tolerance, core_height, FreeCAD.Vector(item["x_mm"], item["y_mm"], z1 + tolerance))
        ring_core = core_outer.cut(core_inner)
        bore_core = Part.makeCylinder(max(0.01, bore_radius - radial_tolerance), core_height, FreeCAD.Vector(item["x_mm"], item["y_mm"], z1 + tolerance))
        bore_cutter_core = Part.makeCylinder(
            max(0.01, bore_radius - radial_tolerance),
            float(item["bore_cutter_z_max_mm"] - item["bore_cutter_z_min_mm"]),
            FreeCAD.Vector(item["x_mm"], item["y_mm"], item["bore_cutter_z_min_mm"]),
        )
        outer_allowed = Part.makeCylinder(
            outer_radius + radial_tolerance, core_height,
            FreeCAD.Vector(item["x_mm"], item["y_mm"], z1 + tolerance),
        )
        outer_search = Part.makeCylinder(
            outer_radius + 2.0 * tolerance, core_height,
            FreeCAD.Vector(item["x_mm"], item["y_mm"], z1 + tolerance),
        )
        outer_excess_probe = outer_search.cut(outer_allowed)
        for rule in contract.get("critical_rules", []):
            if rule.get("kind") != "required_ribs":
                continue
            for rib in rule.get("ribs", []):
                values = [float(value) for value in rib["bounds_mm"]]
                rib_allowance = box_shape([
                    values[0] - tolerance, values[1] - tolerance, values[2] - tolerance,
                    values[3] + tolerance, values[4] + tolerance, values[5] + tolerance,
                ])
                outer_excess_probe = outer_excess_probe.cut(rib_allowance)
        ranked = sorted(
            ((float(solid.common(ring_core).Volume), index, solid) for index, solid in enumerate(cross_solids)),
            reverse=True,
            key=lambda row: row[0],
        )
        matched = ranked[0] if ranked and ranked[0][0] > 0.0001 else (0.0, -1, Part.Shape())
        slice_height = min(0.05, max(0.01, (z2 - z1) / 12.0))
        slice_centers = [z1 + tolerance, (z1 + z2) / 2.0, z2 - tolerance]
        slice_centers = sorted(set(max(z1 + slice_height, min(z2 - slice_height, value)) for value in slice_centers))
        slice_coverages = []
        diameter_errors = []
        axis_errors = []
        bore_diameter_errors = []
        bore_axis_errors = []
        slice_component_ids = []
        for slice_center in slice_centers:
            slice_z = slice_center - slice_height / 2.0
            slice_core_outer = Part.makeCylinder(
                outer_radius - radial_tolerance, slice_height,
                FreeCAD.Vector(item["x_mm"], item["y_mm"], slice_z),
            )
            slice_core_inner = Part.makeCylinder(
                bore_radius + radial_tolerance, slice_height,
                FreeCAD.Vector(item["x_mm"], item["y_mm"], slice_z),
            )
            slice_core = slice_core_outer.cut(slice_core_inner)
            slice_coverages.append(float(carrier.common(slice_core).Volume) / float(slice_core.Volume))
            carrier_ranked = sorted(
                ((float(solid.common(slice_core).Volume), index) for index, solid in enumerate(carrier_solids)),
                reverse=True, key=lambda row: row[0],
            )
            slice_component_ids.append(
                carrier_ranked[0][1] if carrier_ranked and carrier_ranked[0][0] > 0.0001 else -1
            )

            slab = box_shape([
                contract["carrier_bounds_mm"][0], contract["carrier_bounds_mm"][1], slice_z,
                contract["carrier_bounds_mm"][3], contract["carrier_bounds_mm"][4], slice_z + slice_height,
            ])
            slice_solids = [solid for solid in carrier.common(slab).Solids if float(solid.Volume) > 0.0001]
            slice_ranked = sorted(
                ((float(solid.common(slice_core).Volume), solid) for solid in slice_solids),
                reverse=True, key=lambda row: row[0],
            )
            actual = slice_ranked[0][1] if slice_ranked and slice_ranked[0][0] > 0.0001 else Part.Shape()
            if not actual.isNull():
                actual_bounds = bounds(actual)
                center_x = (actual_bounds[0] + actual_bounds[3]) / 2.0
                center_y = (actual_bounds[1] + actual_bounds[4]) / 2.0
                axis_errors.append(math.hypot(center_x - float(item["x_mm"]), center_y - float(item["y_mm"])))
                diameter_errors.append(max(
                    abs((actual_bounds[3] - actual_bounds[0]) - float(item["outer_diameter_mm"])),
                    abs((actual_bounds[4] - actual_bounds[1]) - float(item["outer_diameter_mm"])),
                ))
            else:
                axis_errors.append(1e9)
                diameter_errors.append(1e9)

            bore_search = Part.makeCylinder(
                (outer_radius + bore_radius) / 2.0, slice_height,
                FreeCAD.Vector(item["x_mm"], item["y_mm"], slice_z),
            )
            bore_void = bore_search.cut(carrier)
            axis_probe = Part.makeCylinder(
                max(0.05, bore_radius / 4.0), slice_height,
                FreeCAD.Vector(item["x_mm"], item["y_mm"], slice_z),
            )
            void_ranked = sorted(
                ((float(solid.common(axis_probe).Volume), solid) for solid in bore_void.Solids),
                reverse=True, key=lambda row: row[0],
            )
            actual_bore = void_ranked[0][1] if void_ranked and void_ranked[0][0] > 0.0001 else Part.Shape()
            if not actual_bore.isNull():
                bore_bounds = bounds(actual_bore)
                bore_center_x = (bore_bounds[0] + bore_bounds[3]) / 2.0
                bore_center_y = (bore_bounds[1] + bore_bounds[4]) / 2.0
                bore_axis_errors.append(math.hypot(
                    bore_center_x - float(item["x_mm"]), bore_center_y - float(item["y_mm"])
                ))
                bore_diameter_errors.append(max(
                    abs((bore_bounds[3] - bore_bounds[0]) - float(item["bore_diameter_mm"])),
                    abs((bore_bounds[4] - bore_bounds[1]) - float(item["bore_diameter_mm"])),
                ))
            else:
                bore_axis_errors.append(1e9)
                bore_diameter_errors.append(1e9)
        full_height_core_covered = float(carrier.common(ring_core).Volume)
        standoffs[item["ref"]] = {
            "cross_section_component_id": matched[1],
            "core_slice_minimum_coverage_ratio": min(slice_coverages),
            "full_height_core_coverage_ratio": full_height_core_covered / float(ring_core.Volume),
            "full_height_core_missing_volume_mm3": max(0.0, float(ring_core.Volume) - full_height_core_covered),
            "core_single_connected": len(set(slice_component_ids)) == 1 and slice_component_ids[0] >= 0,
            "bore_core_intersection_mm3": float(carrier.common(bore_core).Volume),
            "bore_cutter_core_intersection_mm3": float(carrier.common(bore_cutter_core).Volume),
            "outer_dilated_intersection_mm3": float(carrier.common(outer_excess_probe).Volume),
            "outer_diameter_error_mm": max(diameter_errors),
            "axis_error_mm": max(axis_errors),
            "bore_diameter_error_mm": max(bore_diameter_errors),
            "bore_axis_error_mm": max(bore_axis_errors),
        }

    accesses = {}
    for item in contract.get("accesses", []):
        path = access_shape(item, "path_bounds_mm")
        intersection = float(carrier.common(path).Volume)
        guard_shapes = access_guard_regions(item, contract)
        guard_metrics = {}
        for region_id, guard in guard_shapes.items():
            material = carrier.common(guard)
            covered = float(material.Volume)
            guard_metrics[region_id] = {
                "coverage_ratio": covered / float(guard.Volume),
                "missing_volume_mm3": max(0.0, float(guard.Volume) - covered),
                "single_connected_material": len([solid for solid in material.Solids if float(solid.Volume) > 0.0001]) == 1,
            }
        accesses[item["ref"]] = {
            "open_ratio": max(0.0, 1.0 - intersection / float(path.Volume)),
            "carrier_intersection_mm3": intersection,
            "guard_coverage_ratio": min(metric["coverage_ratio"] for metric in guard_metrics.values()),
            "guard_regions": guard_metrics,
        }

    side_clearance, top_clearance, top_clearances = clearance_measurements(contract, carrier)
    physical_roles = ([board_actual] if board_actual is not None else []) + list(component_shapes.values())
    interference = sum(float(carrier.common(shape).Volume) for shape in physical_roles)
    critical_rules = [
        critical_measurement(rule, contract, carrier, carrier_solids, component_shapes)
        for rule in contract.get("critical_rules", [])
    ]
    density = float(contract["enclosure_density_g_cm3"])
    return {
        "shape_valid": True,
        "carrier": {
            "bounds_mm": bounds(carrier),
            "volume_mm3": float(carrier.Volume),
            "mass_g": float(carrier.Volume) * density / 1000.0,
        },
        "structure": structure,
        "pcb": pcb_metrics,
        "components": component_metrics,
        "standoffs": standoffs,
        "accesses": accesses,
        "minimum_side_clearance_mm": side_clearance,
        "minimum_top_clearance_mm": top_clearance,
        "top_clearances": top_clearances,
        "unintended_interference_mm3": interference,
        "critical_rules": critical_rules,
    }


try:
    payload = {"ok": True, "result": evaluate()}
except Exception as exc:
    payload = {"ok": False, "error": str(exc), "traceback": traceback.format_exc()}
with open(result_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
'''


def resolve_freecad() -> str:
    configured = os.environ.get("ENGIWORLD_FREECADCMD")
    candidates = [configured] if configured else []
    candidates.extend(shutil.which(name) for name in ("freecadcmd", "FreeCADCmd", "freecadcmd-python3"))
    candidates.extend((
        "/home/user/.local/bin/freecadcmd",
        "/usr/bin/freecadcmd",
        "/usr/bin/FreeCADCmd",
        "/usr/lib/freecad/bin/freecadcmd-python3",
        "/usr/lib/freecad/bin/FreeCADCmd",
        "/usr/local/bin/freecadcmd",
    ))
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise EvaluationDependencyError(
        "FreeCADCmd is unavailable to the evaluator; install FreeCAD or set ENGIWORLD_FREECADCMD to its executable"
    )


def measure_geometry(candidate: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="engiworld_open_eval_") as temp_dir:
        runtime = Path(temp_dir)
        checker = runtime / "geometry_checker.py"
        result_path = runtime / "geometry_result.json"
        checker.write_text(FREECAD_CHECKER, encoding="utf-8")
        env = {
            **os.environ,
            "PYTHONPATH": "",
            "ENGIWORLD_OPEN_CANDIDATE": str(candidate),
            "ENGIWORLD_OPEN_SPEC": str(SPEC_PATH),
            "ENGIWORLD_OPEN_RESULT": str(result_path),
        }
        completed = subprocess.run(
            [resolve_freecad(), str(checker)],
            cwd=str(runtime),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
            env=env,
        )
        output = completed.stdout + completed.stderr
        shutdown_crash = (
            completed.returncode == 1
            and result_path.is_file()
            and "Program received signal SIGSEGV" in output
            and "closeAllDocuments" in output
        )
        if completed.returncode != 0 and not shutdown_crash:
            fail(f"geometry evaluator failed: {output[-3000:]}")
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"geometry evaluator returned no readable result: {exc}")
        if not payload.get("ok"):
            fail(f"geometry evaluator rejected the final STEP: {payload.get('error')}")
        return mapping(payload.get("result"), "geometry result")


def evaluate() -> bool:
    spec = load_spec()
    candidate = find_submission()
    measurements = measure_geometry(candidate)
    validate_measurements(spec, measurements)
    return True


if __name__ == "__main__":
    try:
        passed = evaluate()
        detail = "PASS: final STEP geometry satisfies the open semantic contract."
    except EvaluationDependencyError as exc:
        print(f"EVAL_DEPENDENCY_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        passed = False
        detail = f"FAIL: {type(exc).__name__}: {exc}"
    if not passed:
        print(detail, file=sys.stderr)
    print("True" if passed else "False")
