from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-07-windows",
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
    "required_spaces": [
        "LOBBY", "READING-ROOM", "BOOK-STACK", "STAFF-OFFICE",
        "TOILET-SUPPORT",
    ],
    "required_zones": [
        "LOBBY-ZN", "READING-ROOM-ZN", "BOOK-STACK-ZN",
        "STAFF-OFFICE-ZN", "TOILET-SUPPORT-ZN",
    ],
    "stage1_tokens": [
        "EW3B07", "LOBBY", "READING-ROOM", "BOOK-STACK",
        "STAFF-OFFICE", "TOILET-SUPPORT", "GEOMETRIC-FILLINGS",
        "multi-cli-3-revit-archicad-openstudio-task-07-windows",
    ],
    "stage2_tokens": [
        "ARCHICAD-QA-PASS", "FIVE-NAMED-SPACES",
        "PUBLIC-SCHEDULE-CATEGORY", "STAFF-SCHEDULE-CATEGORY",
        "SUPPORT-SCHEDULE-CATEGORY", "LOBBY", "READING-ROOM",
        "BOOK-STACK", "STAFF-OFFICE", "TOILET-SUPPORT",
        "multi-cli-3-revit-archicad-openstudio-task-07-windows",
    ],
    "handoff_tokens": [
        "PUBLIC-LOAD-CURVE", "READING-LOAD-CURVE",
        "STACK-LOW-LIGHTING", "STAFF-OFFICE-SCHEDULE",
        "SUPPORT-LOW-LOAD",
    ],
    "osm_tokens": [
        "LibraryPublicLoadCurve", "ReadingRoomLoadCurve",
        "BookStackLowLighting", "StaffOfficeSchedule",
        "ToiletSupportLowLoad",
    ],
    "summary_tokens": [
        "LOBBY", "READING-ROOM", "BOOK-STACK", "STAFF-OFFICE",
        "TOILET-SUPPORT",
    ],
    "min_windows": 3,
    "min_doors": 5,
    "min_roofs": 1,
    "min_storeys": 1,
    "require_roof_geometry": True,
    "require_filling_relations": True,
    "expected_stage": "revit",
    "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
