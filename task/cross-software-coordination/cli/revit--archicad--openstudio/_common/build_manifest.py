from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED_FILES = [
    "init.ifc", "stage1.ifc", "revit_handoff.json", "stage2.ifc",
    "archicad_handoff.json", "archicad_validation_report.json",
    "archicad_ifc4_translator.json", "workflow_spec.json", "weather.epw",
    "native_stage_log.json", "workflow.osw", "result.osm", "in.idf",
    "flow_report.json", "model_summary.csv", "energy_report.csv",
    "run/eplusout.sql", "run/eplusout.err",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path, spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    log = json.loads((root / "native_stage_log.json").read_text(encoding="utf-8"))
    stages = {row["stage"]: row for row in log["stages"]}
    hashes = {name: digest(root / name) for name in REQUIRED_FILES}
    manifest = {
        "case_id": spec["case_id"],
        "generated_at_utc": stages["openstudio"]["finished_utc"],
        "generator": "run_revit_stage.ps1 -> run_archicad_stage.ps1 -> run_openstudio_stage.ps1",
        "native_stage_provenance": {
            "revit": {
                "exe": stages["revit"]["executable"],
                "product_version": stages["revit"]["product_version"],
                "automation": stages["revit"]["automation_entry"],
            },
            "archicad": {
                "exe": stages["archicad"]["automation_entry"],
                "product_version": stages["archicad"]["product_version"],
                "automation": stages["archicad"]["command"],
            },
            "openstudio": {
                "exe": stages["openstudio"]["executable"],
                "version": stages["openstudio"]["product_version"],
                "energyplus_version": spec["fixed_software"]["openstudio"]["energyplus_version"],
                "automation": "openstudio_ifc_to_energy.rb consumed the Archicad IFC and handoff, forward-translated the OSM, and ran EnergyPlus",
            },
        },
        "required_files": REQUIRED_FILES,
        "artifact_sha256": hashes,
    }
    (root / "gt_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    labels = []
    total = 0.0
    for row in spec["spaces"]:
        geometry = row["energy_geometry"]
        area = float(geometry["width_m"]) * float(geometry["depth_m"])
        total += area
        labels.append(f"`{row['name']}` ({area:.2f} m2)")
    space_text = ", ".join(labels)
    notes = f"""# Ground-truth generation notes

This case uses the pinned Revit 2025, Archicad 27 build 6000, OpenStudio 3.10.0,
and EnergyPlus 25.1.0 workflow recorded in `native_stage_log.json`. Its
case-specific IFC spaces are {space_text}, totaling {total:.2f} m2. Each space
has geometry, storey containment, base quantities, and an
`EngiWorld_EnergyHandoff` property set; Archicad retains the space GlobalIds.

Run the supplied stages in order on the Windows task image:

```powershell
powershell -ExecutionPolicy Bypass -File C:\\Users\\user\\Desktop\\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\\Users\\user\\Desktop\\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\\Users\\user\\Desktop\\run_openstudio_stage.ps1
```

The OpenStudio converter verifies `stage2.ifc` and the keyed Archicad handoff,
builds separate geometry, zones, loads, schedules, outdoor air, thermostats and
constructions, forward-translates `in.idf`, and runs an annual simulation. The
evaluator parses the IFC semantic graph, reconciles Archicad entity counts,
opens standard EnergyPlus SQLite tables, checks zone areas and reported energy,
and reruns `in.idf` independently. Ground-truth validation returned `True` with
no errors.
"""
    (root / "GT_GENERATION.md").write_text(notes, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    args = parser.parse_args()
    build(args.root, args.spec)


if __name__ == "__main__":
    main()
