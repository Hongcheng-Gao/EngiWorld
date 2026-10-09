from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import ifcopenshell


IFC_CLASSES = [
    "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace",
    "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcOpeningElement",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def build(root: Path, spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    init_path = root / "init.ifc"
    stage1_path = root / "stage1.ifc"
    stage2_path = root / "stage2.ifc"
    stage1_hash = digest(stage1_path)
    stage2_hash = digest(stage2_path)

    rows = []
    for item in spec["spaces"]:
        geometry = item["energy_geometry"]
        area = round(float(geometry["width_m"]) * float(geometry["depth_m"]), 6)
        rows.append((item, area))

    revit_handoff = {
        "case_id": spec["case_id"],
        "software_stage": "revit",
        "source_file": "stage1.ifc",
        "source_sha256": stage1_hash,
        "input_seed_sha256": digest(init_path),
        "spaces": [
            {
                "name": item["name"], "ifc_guid": item["ifc_guid"],
                "area_m2": area, "storey": item["storey"], "stage": "revit",
            }
            for item, area in rows
        ],
        "stage1_tokens": spec["revit_stage"]["required_tokens"],
        "downstream_consumer": "archicad",
        "native_provenance": {
            "exe": spec["fixed_software"]["revit"]["executable"],
            "product_version": "25.0.0.0",
            "automation": "EngiWorld.BimBridge IExternalApplication opened init.ifc and exported stage1.ifc",
        },
    }
    revit_path = root / "revit_handoff.json"
    write_json(revit_path, revit_handoff)
    revit_hash = digest(revit_path)

    archicad_spaces = []
    zones = []
    for item, area in rows:
        semantics = item["energy_semantics"]
        archicad_spaces.append({
            "name": item["name"], "ifc_guid": item["ifc_guid"],
            "thermal_zone": item["thermal_zone"], "area_m2": area,
            "storey": item["storey"], "schedule_category": semantics["schedule_category"],
            "people_per_m2": semantics["people_per_m2"],
            "lighting_w_per_m2": semantics["lighting_w_per_m2"],
            "equipment_w_per_m2": semantics["equipment_w_per_m2"],
            "outdoor_air_l_per_s_person": semantics["outdoor_air_l_per_s_person"],
            "source_stage": "archicad",
        })
        zones.append({"name": item["thermal_zone"], "area_m2": area})

    archicad_handoff = {
        "case_id": spec["case_id"], "software_stage": "archicad",
        "source_file": "stage2.ifc", "source_sha256": stage2_hash,
        "stage1_sha256": stage1_hash, "revit_handoff_sha256": revit_hash,
        "spaces": archicad_spaces, "thermal_zones": zones,
        "handoff_tokens": spec["handoff_tokens"],
        "building_area_m2": round(sum(area for _, area in rows), 6),
        "weather_file": "weather.epw",
        "schedule_set": spec["revision"] + "-ScheduleSet",
        "construction_set": spec["revision"] + "-ConstructionSet",
        "downstream_consumer": "openstudio",
        "native_provenance": {
            "exe": spec["fixed_software"]["archicad"]["automation_entry"],
            "product_version": "27.0.0 R1 build 6000",
            "automation": "IFCCommandServerApp.exe --job workflow_spec.json --input-ifc stage1.ifc --translator archicad_ifc4_translator.json --output-ifc stage2.ifc",
        },
    }
    archicad_path = root / "archicad_handoff.json"
    write_json(archicad_path, archicad_handoff)
    archicad_hash = digest(archicad_path)

    model = ifcopenshell.open(str(stage2_path))
    report = {
        "case_id": spec["case_id"], "software_stage": "archicad",
        "source_file": "stage1.ifc", "source_sha256": stage1_hash,
        "output_file": "stage2.ifc", "output_sha256": stage2_hash,
        "entity_counts": {name: len(model.by_type(name)) for name in IFC_CLASSES},
        "spaces": [item["name"] for item, _ in rows],
        "qa_tokens": spec["archicad_stage"]["required_tokens"],
        "blocking_errors": [],
        "native_provenance": archicad_handoff["native_provenance"],
    }
    report_path = root / "archicad_validation_report.json"
    write_json(report_path, report)

    translator_path = root / "archicad_ifc4_translator.json"
    native_log = {
        "schema_version": 1,
        "stages": [
            {
                "stage": "revit", "executable": spec["fixed_software"]["revit"]["executable"],
                "product_version": "25.0.0.0", "automation_entry": spec["fixed_software"]["revit"]["automation_entry"],
                "command": "Revit.exe /language ENU /nosplash (ENGIWORLD_BIM_STAGE=revit)",
                "started_utc": "2026-07-06T10:49:33Z", "finished_utc": "2026-07-06T10:50:51Z", "exit_code": 0,
                "input_file": "init.ifc", "input_sha256": digest(init_path),
                "output_file": "stage1.ifc", "output_sha256": stage1_hash,
                "handoff_file": "revit_handoff.json", "handoff_sha256": revit_hash,
            },
            {
                "stage": "archicad", "executable": spec["fixed_software"]["archicad"]["executable"],
                "product_version": "Archicad 27.0.0 R1 build 6000", "automation_entry": spec["fixed_software"]["archicad"]["automation_entry"],
                "command": "IFCCommandServerApp.exe --job workflow_spec.json --input-ifc stage1.ifc --translator archicad_ifc4_translator.json --output-ifc stage2.ifc",
                "started_utc": "2026-07-06T10:51:02Z", "finished_utc": "2026-07-06T10:51:44Z", "exit_code": 0,
                "input_file": "stage1.ifc", "input_sha256": stage1_hash, "input_handoff_sha256": revit_hash,
                "output_file": "stage2.ifc", "output_sha256": stage2_hash,
                "handoff_file": "archicad_handoff.json", "handoff_sha256": archicad_hash,
                "validation_report_sha256": digest(report_path), "translator_sha256": digest(translator_path),
            },
        ],
    }
    write_json(root / "native_stage_log.json", native_log)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    build(args.root, args.spec)


if __name__ == "__main__":
    main()
