from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-06-windows",
    "mode": "three_stage",
    "software_chain": ["revit", "archicad", "openstudio"],
    "required_files": [
        "init.ifc", "stage1.ifc", "revit_handoff.json", "stage2.ifc",
        "archicad_handoff.json", "archicad_validation_report.json",
        "result.osm", "in.idf", "flow_report.json", "model_summary.csv",
        "energy_report.csv", "workflow_spec.json",
        "archicad_ifc4_translator.json", "weather.epw",
        "native_stage_log.json", "workflow.osw", "run/eplusout.sql",
        "run/eplusout.err",
    ],
    "required_spaces": ["MAKER-WORKSHOP", "OFFICE", "TOOL-ROOM"],
    "required_zones": ["MAKER-WORKSHOP-ZN", "OFFICE-ZN", "TOOL-ROOM-ZN"],
    "stage1_tokens": [
        "EW3B06", "MAKER-WORKSHOP", "OFFICE", "TOOL-ROOM",
        "STRUCTURAL-GRID-PRESERVED",
        "multi-cli-3-revit-archicad-openstudio-task-06-windows",
    ],
    "stage2_tokens": [
        "ARCHICAD-QA-PASS", "WORKSHOP-EQUIPMENT-INTENSITY",
        "OFFICE-EXPOSURE", "TOOL-ROOM-EXPOSURE", "MAKER-WORKSHOP",
        "OFFICE", "TOOL-ROOM",
        "multi-cli-3-revit-archicad-openstudio-task-06-windows",
    ],
    "handoff_tokens": [
        "WORKSHOP-HIGH-EQUIPMENT", "OFFICE-PEOPLE-SCHEDULE",
        "TOOL-ROOM-LOW-OCCUPANCY", "GRID-PRESERVED",
    ],
    "osm_tokens": [
        "WorkshopHighEquipment", "OfficePeopleSchedule",
        "ToolRoomLowOccupancy", "StructuralGridPreserved",
    ],
    "summary_tokens": ["MAKER-WORKSHOP", "OFFICE", "TOOL-ROOM"],
    "min_windows": 2,
    "min_doors": 3,
    "min_roofs": 1,
    "min_storeys": 1,
    "expected_stage": "revit",
    "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
