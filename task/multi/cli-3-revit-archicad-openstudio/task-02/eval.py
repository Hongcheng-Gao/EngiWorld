from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-02-windows",
    "mode": "three_stage",
    "software_chain": ["revit", "archicad", "openstudio"],
    "required_files": [
        "init.ifc",
        "stage1.ifc",
        "revit_handoff.json",
        "stage2.ifc",
        "archicad_handoff.json",
        "archicad_validation_report.json",
        "result.osm",
        "in.idf",
        "flow_report.json",
        "model_summary.csv",
        "energy_report.csv",
        "workflow_spec.json",
        "archicad_ifc4_translator.json",
        "weather.epw",
        "native_stage_log.json",
        "workflow.osw",
        "run/eplusout.sql",
        "run/eplusout.err",
    ],
    "required_spaces": ["RETAIL-SALES", "PREP-KITCHEN", "DRY-STORAGE"],
    "required_zones": ["RETAIL-SALES-ZN", "PREP-KITCHEN-ZN", "DRY-STORAGE-ZN"],
    "stage1_tokens": [
        "EW3B02",
        "RETAIL-SALES",
        "PREP-KITCHEN",
        "DRY-STORAGE",
        "BACK-OF-HOUSE",
        "multi-cli-3-revit-archicad-openstudio-task-02-windows",
    ],
    "stage2_tokens": [
        "ARCHICAD-QA-PASS",
        "PUBLIC-SERVICE-SEPARATION",
        "PREP-BOUNDARY",
        "STORAGE-BOUNDARY",
        "RETAIL-SALES",
        "PREP-KITCHEN",
        "DRY-STORAGE",
        "multi-cli-3-revit-archicad-openstudio-task-02-windows",
    ],
    "handoff_tokens": [
        "RETAIL-PUBLIC-SCHEDULE",
        "PREP-HIGH-EQUIPMENT",
        "STORAGE-LOW-OCCUPANCY",
        "SERVICE-BOUNDARY",
    ],
    "osm_tokens": [
        "RetailPublicSchedule",
        "PrepKitchenHighEquipment",
        "DryStorageLowOccupancy",
        "ServiceBoundaryTag",
    ],
    "summary_tokens": ["RETAIL-SALES", "PREP-KITCHEN", "DRY-STORAGE"],
    "min_windows": 1,
    "min_doors": 3,
    "min_roofs": 1,
    "min_storeys": 1,
    "expected_stage": "revit",
    "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
