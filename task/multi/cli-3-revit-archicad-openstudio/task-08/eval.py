from __future__ import annotations

import sys
from pathlib import Path

COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))

from eval_three_stage import run


CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-08-windows",
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
    "required_spaces": ["L1-LAB", "L1-PREP", "L2-LAB", "L2-PREP"],
    "required_zones": [
        "L1-LAB-ZN", "L1-PREP-ZN", "L2-LAB-ZN", "L2-PREP-ZN",
    ],
    "stage1_tokens": [
        "EW3B08", "L1-LAB", "L1-PREP", "L2-LAB", "L2-PREP",
        "PITCHED-ROOF", "TWO-LEVEL-GEOMETRY",
        "multi-cli-3-revit-archicad-openstudio-task-08-windows",
    ],
    "stage2_tokens": [
        "ARCHICAD-QA-PASS", "LAB-PREP-CONTAINMENT",
        "HIGH-LOAD-LAB-TAG", "TWO-LEVEL-LAB", "L1-LAB", "L1-PREP",
        "L2-LAB", "L2-PREP",
        "multi-cli-3-revit-archicad-openstudio-task-08-windows",
    ],
    "handoff_tokens": [
        "LAB-HIGH-EQUIPMENT", "LAB-HIGH-VENTILATION",
        "PREP-MEDIUM-EQUIPMENT", "PITCHED-ROOF-CONSTRUCTION",
    ],
    "osm_tokens": [
        "LabHighEquipment", "LabHighVentilation", "PrepMediumEquipment",
        "PitchedRoofConstruction",
    ],
    "summary_tokens": ["L1-LAB", "L1-PREP", "L2-LAB", "L2-PREP"],
    "min_windows": 4,
    "min_doors": 4,
    "min_roofs": 1,
    "min_storeys": 2,
    "require_roof_geometry": True,
    "require_filling_relations": True,
    "expected_stage": "revit",
    "expected_archicad_stage": "archicad",
}


if __name__ == "__main__":
    run(CASE_SPEC)
