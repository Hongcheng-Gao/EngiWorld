from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-09-windows",
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
    "required_spaces": ["LOBBY", "CLASSROOM-A", "CLASSROOM-B", "STORAGE"],
    "required_zones": [
        "LOBBY-ZN", "CLASSROOM-A-ZN", "CLASSROOM-B-ZN", "STORAGE-ZN",
    ],
    "stage1_tokens": [
        "EW3B09", "LOBBY", "CLASSROOM-A", "CLASSROOM-B", "STORAGE",
        "BAR-BUILDING", "GEOMETRIC-FILLINGS",
        "multi-cli-3-revit-archicad-openstudio-task-09-windows",
    ],
    "stage2_tokens": [
        "ARCHICAD-QA-PASS", "CLASSROOM-STORAGE-SEPARATION",
        "TEACHING-SCHEDULE-CATEGORY", "SUPPORT-SCHEDULE-CATEGORY",
        "LOBBY", "CLASSROOM-A", "CLASSROOM-B", "STORAGE",
        "multi-cli-3-revit-archicad-openstudio-task-09-windows",
    ],
    "handoff_tokens": [
        "CLASSROOM-TEACHING-SCHEDULE", "LOBBY-SHORT-OCCUPANCY",
        "STORAGE-LOW-LOAD", "TWO-CLASSROOMS",
    ],
    "osm_tokens": [
        "ClassroomTeachingSchedule", "LobbyShortOccupancy",
        "StorageLowLoad", "TwoClassrooms",
    ],
    "summary_tokens": ["LOBBY", "CLASSROOM-A", "CLASSROOM-B", "STORAGE"],
    "min_windows": 3,
    "min_doors": 4,
    "min_roofs": 1,
    "min_storeys": 1,
    "require_roof_geometry": True,
    "require_filling_relations": True,
    "expected_stage": "revit",
    "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
