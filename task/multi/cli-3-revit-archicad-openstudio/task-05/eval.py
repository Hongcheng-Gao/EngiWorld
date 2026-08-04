from __future__ import annotations
import sys
from pathlib import Path
COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))
from eval_three_stage import run

CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-05-windows",
    "mode": "three_stage", "software_chain": ["revit", "archicad", "openstudio"],
    "required_files": ["init.ifc", "stage1.ifc", "revit_handoff.json", "stage2.ifc", "archicad_handoff.json", "archicad_validation_report.json", "result.osm", "in.idf", "flow_report.json", "model_summary.csv", "energy_report.csv", "workflow_spec.json", "archicad_ifc4_translator.json", "weather.epw", "native_stage_log.json", "workflow.osw", "run/eplusout.sql", "run/eplusout.err"],
    "required_spaces": ["GROUND-PUBLIC", "UPPER-ACTIVITY", "UPPER-READING"],
    "required_zones": ["GROUND-PUBLIC-ZN", "UPPER-ACTIVITY-ZN", "UPPER-READING-ZN"],
    "stage1_tokens": ["EW3B05", "GROUND-PUBLIC", "UPPER-ACTIVITY", "UPPER-READING", "STAIR-OPENING", "TWO-STOREY", "multi-cli-3-revit-archicad-openstudio-task-05-windows"],
    "stage2_tokens": ["ARCHICAD-QA-PASS", "STOREY-CONTAINMENT", "STAIR-OPENING-RELATION", "UPPER-READING-BOUNDARY", "GROUND-PUBLIC", "UPPER-ACTIVITY", "UPPER-READING", "multi-cli-3-revit-archicad-openstudio-task-05-windows"],
    "handoff_tokens": ["GROUND-PUBLIC-SCHEDULE", "UPPER-ACTIVITY-SCHEDULE", "READING-LOW-LIGHTING", "MULTI-STOREY-HANDOFF"],
    "osm_tokens": ["GroundPublicSchedule", "UpperActivitySchedule", "ReadingLowLighting", "BuildingStory:Level 2"],
    "summary_tokens": ["GROUND-PUBLIC", "UPPER-ACTIVITY", "UPPER-READING"],
    "min_windows": 3, "min_doors": 3, "min_roofs": 1, "min_storeys": 2,
    "require_opening_geometry": True,
    "expected_stage": "revit", "expected_archicad_stage": "archicad",
}

if __name__ == "__main__":
    run(CASE_SPEC)
