# Task-10 native ground-truth record

## Scope and outcome

This task was repaired independently on snapshot
`cli3-revit2025-archicad27-openstudio310-win`. The native chain ran in the
required order: Revit 2025, Archicad 27, OpenStudio 3.10.0, and EnergyPlus
25.1.0. The resulting IFC has three geometric spaces, one on each storey:
`RECEPTION-L1`, `STUDIO-L2`, and `ARCHIVE-L3`, each 45.24 m2 and totaling
135.72 m2. All three retain the original init GlobalIds.

The evaluator does not compare candidate stage outputs to GT hashes. It checks
IFC geometry, quantities, containment and host-opening relations; the real
Archicad RPC transcript; OSM object references, schedules, loads and outdoor
air; standard EnergyPlus SQLite content; and independent OpenStudio/EnergyPlus
regeneration.

## Native stages

- Revit: `Revit.exe` 25.1.0.44, build `20240516_1515(x64)`, ran from
  `2026-08-12T17:08:24.8892290Z` to `2026-08-12T17:12:20.1030104Z`.
  The task-local bridge compiled on the instance with 0 errors. The same Revit
  process accepted `Unsigned Add-In: Load Once` and the IFC4 open warning, then
  produced native `stage1.ifc` SHA-256
  `31baa49f2778e217263fa539f3ca37a1bc0623608f5c2ad6ec5612b08ef8013b`.
  Independent parsing found 3 storeys, 3 spaces, 12 walls, 3 slabs, 1 closed
  pitched roof, 3 doors, 3 windows, 6 openings, 6 void relations, and 6 fill
  relations. The roof bbox is `(0, 8, 0, 6, 9, 10.74)` and volume is 11.52 m3.
- Archicad: Archicad 27 build 6000 through the installed
  `IFCCommandServerApp.exe` HTTP/JEMI interface. Its transcript contains
  `Model.LoadFile`, `Macro.ValidateIfcModel`, 15 class queries, 9 live space
  attribute queries, and `Model.SaveFile`. It produced native `stage2.ifc`
  SHA-256
  `28a3bb5ab1de46bd3afc91f3280057d9dc423ee2bcb36158fab30d9c7d860e21`.
  All 356 upstream IfcRoot GlobalIds, entity counts, containment, geometry and
  hosted-opening relations were preserved without missing, extra, or duplicate
  roots. The observed upstream boundary state was 0 and remained 0; no boundary
  relation was fabricated.
- OpenStudio/EnergyPlus: OpenStudio `3.10.0+86d7e215a1` consumed the real
  stage2 IFC and handoff. The task-local extractor parsed each IFC space's GUID,
  storey and world geometry before model construction. OpenStudio created three
  separate spaces/zones with the requested schedules, loads, outdoor air,
  20/26 C dual setpoints and ideal loads, then forward-translated `in.idf` and
  invoked EnergyPlus `25.1.0-1c11a3d85f`. The full annual run completed with
  0 severe errors, 23,913.889 kWh total site energy and 2.552 kW peak demand.
  Its SQL contains 3 zones, 18 surfaces, 3 people, 3 lighting and 3 equipment
  records, plus 8,760 Time and 8,760 meter ReportData rows.

The authoritative per-stage hashes and timestamps are in
`native_stage_log.json`; `gt_manifest.json` inventories the final package.

## Reproduction

Upload every task-local `init_file` item to the pinned Windows Desktop and run:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
python C:\Users\user\Desktop\eval.py
```

## Validation

- Local formal evaluation: `True`, no errors.
- Windows formal evaluation: `True`, no errors. This run executed the
  evaluator's independent OpenStudio 3.10 ForwardTranslator and EnergyPlus
  25.1 annual rerun.
- Local matrix: 22/22 expected outcomes. Three native/equivalent positives
  passed and 19 targeted mutations were rejected, covering GlobalIds, geometry,
  containment, roof topology, filling hosts, Archicad RPC evidence, schedules,
  loads, outdoor air, zone separation, OSM handles, IDF consistency, truncated
  or nonannual/zero SQL, and forged Revit provenance.
- Windows representative negatives: a changed OSM schedule value, a truncated
  EnergyPlus SQLite file, and a forged Revit version were each rejected.

## Cleanup

After validation, all task work/build/evaluation/negative-case directories,
Archicad databases, server logs and the temporary global Revit add-in were
removed. The final check returned no remaining paths or matching TEMP entries,
no Revit/Archicad/IFCCommandServer/OpenStudio/EnergyPlus processes, and no
listener on TCP 19740. See `CLEANUP.md`.

## Sources

- Revit 2025 API Developers Guide:
  https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html
- Archicad 27 IFC documentation:
  https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-3.htm
- OpenStudio 3.10.0 official release:
  https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- OpenStudio 3.10 CLI documentation:
  https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/cli/html/index.html
- EnergyPlus 25.1 SQL documentation:
  https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html

The audit workbook was treated only as directional context. Its task-specific
row could not be extracted in this environment because the required workspace
dependency loader and `@oai/artifact-tool` runtime were unavailable. No
alternate spreadsheet library was installed or used. The final decision rests
on direct inspection of this task's instruction, init, native outputs,
evaluator, local matrix, and Windows validation.
