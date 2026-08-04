from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-03-windows",
    "mode": "three_stage",
    "software_chain": ["revit", "archicad", "openstudio"],
    "required_files": ["init.ifc", "stage1.ifc", "revit_handoff.json", "stage2.ifc", "archicad_handoff.json", "archicad_validation_report.json", "result.osm", "in.idf", "flow_report.json", "model_summary.csv", "energy_report.csv", "workflow_spec.json", "archicad_ifc4_translator.json", "weather.epw", "native_stage_log.json", "workflow.osw", "run/eplusout.sql", "run/eplusout.err"],
    "required_spaces": ["WAITING", "EXAM-ROOM", "RECORDS-ROOM"],
    "required_zones": ["WAITING-ZN", "EXAM-ROOM-ZN", "RECORDS-ROOM-ZN"],
    "stage1_tokens": ["EW3B03", "WAITING", "EXAM-ROOM", "RECORDS-ROOM", "CLINIC-OUTLINE-PRESERVED", "multi-cli-3-revit-archicad-openstudio-task-03-windows"],
    "stage2_tokens": ["ARCHICAD-QA-PASS", "CLINICAL-CONTAINMENT", "WAITING-VENT-CATEGORY", "RECORDS-VENT-CATEGORY", "WAITING", "EXAM-ROOM", "RECORDS-ROOM", "multi-cli-3-revit-archicad-openstudio-task-03-windows"],
    "handoff_tokens": ["WAITING-VENTILATION", "EXAM-VENTILATION", "RECORDS-LOW-VENTILATION", "CLINIC-SCHEDULE"],
    "osm_tokens": ["WaitingVentilationCategory", "ExamRoomVentilationCategory", "RecordsLowVentilation", "ClinicOperatingSchedule"],
    "summary_tokens": ["WAITING", "EXAM-ROOM", "RECORDS-ROOM"],
    "min_windows": 1, "min_doors": 3, "min_roofs": 1, "min_storeys": 1,
    "expected_stage": "revit", "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
