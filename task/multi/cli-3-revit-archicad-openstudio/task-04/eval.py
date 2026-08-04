from __future__ import annotations
import sys
from pathlib import Path
COMMON = Path(__file__).resolve().parent.parent / "_common"
if COMMON.is_dir():
    sys.path.insert(0, str(COMMON))
from eval_three_stage import run

CASE_SPEC = {
    "case_id": "multi-cli-3-revit-archicad-openstudio-task-04-windows",
    "mode": "three_stage", "software_chain": ["revit", "archicad", "openstudio"],
    "required_files": ["init.ifc", "stage1.ifc", "revit_handoff.json", "stage2.ifc", "archicad_handoff.json", "archicad_validation_report.json", "result.osm", "in.idf", "flow_report.json", "model_summary.csv", "energy_report.csv", "workflow_spec.json", "archicad_ifc4_translator.json", "weather.epw", "native_stage_log.json", "workflow.osw", "run/eplusout.sql", "run/eplusout.err"],
    "required_spaces": ["GARDEN-GALLERY", "ENTRY-NICHE"],
    "required_zones": ["GARDEN-GALLERY-ZN", "ENTRY-NICHE-ZN"],
    "stage1_tokens": ["EW3B04", "GARDEN-GALLERY", "ENTRY-NICHE", "PITCHED-ROOF", "ROOF-SLOPE-MODERATE", "multi-cli-3-revit-archicad-openstudio-task-04-windows"],
    "stage2_tokens": ["ARCHICAD-QA-PASS", "ROOF-CLASSIFIED", "SLAB-CLASSIFIED", "WALL-CLASSIFIED", "GALLERY-ENVELOPE-QA", "GARDEN-GALLERY", "ENTRY-NICHE", "multi-cli-3-revit-archicad-openstudio-task-04-windows"],
    "handoff_tokens": ["PITCHED-ROOF-CONSTRUCTION", "GALLERY-DAYLIGHT", "ROOF-EXPOSURE", "GARDEN-GALLERY-SCHEDULE"],
    "osm_tokens": ["PitchedRoofConstruction", "GalleryDaylightAssumption", "RoofExposureSurface", "GardenGallerySchedule"],
    "summary_tokens": ["GARDEN-GALLERY", "ENTRY-NICHE"],
    "min_windows": 2, "min_doors": 1, "min_roofs": 1, "min_storeys": 1,
    "require_roof_geometry": True,
    "expected_stage": "revit", "expected_archicad_stage": "archicad",
}

if __name__ == "__main__":
    run(CASE_SPEC)
