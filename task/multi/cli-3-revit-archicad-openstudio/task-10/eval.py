from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-10-windows",
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
    "required_spaces": ["RECEPTION-L1", "STUDIO-L2", "ARCHIVE-L3"],
    "required_zones": ["RECEPTION-L1-ZN", "STUDIO-L2-ZN", "ARCHIVE-L3-ZN"],
    "stage1_tokens": [
        "EW3B10", "RECEPTION-L1", "STUDIO-L2", "ARCHIVE-L3",
        "THREE-STOREY-STACK", "GEOMETRIC-FILLINGS",
        "multi-cli-3-revit-archicad-openstudio-task-10-windows",
    ],
    "stage2_tokens": [
        "ARCHICAD-QA-PASS", "ONE-FUNCTION-GROUP-PER-LEVEL",
        "ARCHIVE-LOW-LIGHTING", "STUDIO-HIGH-LOAD", "RECEPTION-L1",
        "STUDIO-L2", "ARCHIVE-L3",
        "multi-cli-3-revit-archicad-openstudio-task-10-windows",
    ],
    "handoff_tokens": [
        "RECEPTION-PUBLIC-LOAD", "STUDIO-HIGH-EQUIPMENT",
        "ARCHIVE-LOW-LIGHTING", "THREE-STOREY-HANDOFF",
    ],
    "osm_tokens": [
        "ReceptionPublicLoad", "StudioHighEquipment", "ArchiveLowLighting",
        "BuildingStory:Level 3",
    ],
    "summary_tokens": ["RECEPTION-L1", "STUDIO-L2", "ARCHIVE-L3"],
    "min_windows": 3,
    "min_doors": 3,
    "min_roofs": 1,
    "min_storeys": 3,
    "require_roof_geometry": True,
    "require_filling_relations": True,
    "expected_stage": "revit",
    "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
