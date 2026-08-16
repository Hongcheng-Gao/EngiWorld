# Task-03 ground-truth generation and validation

## Independent task decision

The original instruction described a Revit-to-Archicad-to-OpenStudio clinic
workflow, but the old init/GT/evaluator did not prove that the files were made by
the pinned native applications and allowed self-reported handoff data to stand in
for the actual IFC, OSM, IDF, and EnergyPlus database. This task therefore
required a native rebuild (`4_native_rebuild`), not an instruction-only or
evaluator-only edit.

The repaired instruction is consistent with the deliverables and does not force
one arbitrary solution where the prompt permits equivalents. The evaluator now
derives the seed geometry and identity from `init.ifc`, accepts an equivalent
Archicad process ID, and checks the specified semantics across the native files.
It rejects fabricated provenance, boundary counts, geometry-less products,
placeholder openings, broken handoffs, and altered simulation results.

## Native workflow

The supplied launchers were run in order on the mapped
`cli3-revit2025-archicad27-openstudio310-win` instance:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

Observed native software:

- Revit `25.1.0.44`, build `20240516_1515(x64)`, through the supplied
  `EngiWorld.BimBridge` IExternalApplication.
- Archicad 27 build `6000`, through the native IFC command server/JEMI on port
  `19738`, model `EW3B03-RUN`.
- OpenStudio `3.10.0+86d7e215a1`, through its Ruby API and forward translator.
- EnergyPlus `25.1.0-1c11a3d85f`, invoked from the OpenStudio 3.10 bundle.

`native_stage_log.json` records executable paths, commands, timestamps, exit
codes, versions, and hashes. The launchers, bridge binary/manifest, translator,
converter, specification, seed, and weather file are retained as immutable
workflow inputs and included in `gt_manifest.json`.

## IFC findings

Revit preserved the real seed shell and the Exam room. It split only the seed
waiting bay and created a distinct Records room; the evaluator independently
checks the seed/final bounding boxes and volumes rather than trusting the JSON.
The resulting spaces are:

| Space | IFC GlobalId | Area (m2) | Thermal zone |
| --- | --- | ---: | --- |
| WAITING | `0zJczJsdP32QALluYBQFCI` | 20.40 | WAITING-ZN |
| EXAM-ROOM | `0zJczJsdP32QALluYBQFCS` | 29.24 | EXAM-ROOM-ZN |
| RECORDS-ROOM | `0zJczJsdP32QALluYBQFCV` | 8.84 | RECORDS-ROOM-ZN |

The Records GlobalId is new and does not reuse either seed room identity. All
seed `IfcElement` GlobalIds and semantics, all seed spatial-container GlobalIds,
and the required seed `IfcProduct` retention are independently checked.

Archicad loaded `stage1.ifc`, ran `Macro.ValidateIfcModel`, queried eleven IFC
classes, queried GlobalId/Name/LongName for every live space, and saved
`stage2.ifc`. The saved model matches the live query: three spaces, five walls,
one slab, and no roof, door, window, or opening placeholders. Stage 1 and stage 2
each contain 128 unique `IfcRoot` objects; all 128 IDs are retained and no
duplicates are present.

The actual stage 1 and stage 2 files both contain zero space-boundary
relationships and zero second-level relationships. This is reported honestly.
The repair does not synthesize relationships merely to satisfy a prior
expectation; the evaluator parses both IFC files and rejects a fabricated count.

## Energy findings

The native converter consumed the saved Archicad IFC and keyed handoff, built
separate geometry, loads, schedules, outdoor air, thermostats, and constructions
for all three zones, saved `result.osm`, forward-translated `in.idf`, and ran a
full annual simulation using `weather.epw`.

The EnergyPlus database contains one annual simulation, 8,760 unique hourly
rows, and these zone floor areas: WAITING-ZN 20.40 m2, EXAM-ROOM-ZN 29.24 m2,
and RECORDS-ROOM-ZN 8.84 m2. `eplusout.err` ends with `EnergyPlus Completed
Successfully`, seven warnings, zero severe errors, and zero fatal errors. The
standard `Simulations.Completed` and `CompletedSuccessfully` fields are both
`FALSE` in this EnergyPlus build; the evaluator therefore requires the exact
build, clean ERR/SQL evidence, complete calendar, and a matching evaluator-side
rerun instead of incorrectly rewriting the native database flags. Reported total
site energy is 11,413.889 kWh and peak load is 0.919 kW.

## Validation

The final Windows baseline returned `True` with no errors. A final isolated
11-case matrix completed at `2026-08-12T05:27:49.7421885Z` and passed 11/11
(matrix SHA-256
`1e9282a4d41f7471556903131cd6b7ba6deb3eecd75b95126e37fc3615e66733`).
It accepts an equivalent changed Archicad process ID and rejects Records seed-GUID
reuse, a propagated fabricated boundary count, wrong JEMI port, forged live
space attributes, wrong Revit/OpenStudio builds, propagated OSM load tampering,
propagated IDF zone tampering with a real rerun, SQL corruption, and immutable
launcher tampering.

The evaluator also verifies exact immutable-input hashes, seed and clinic
geometry, IFC quantities/properties/containment, full stage1-to-stage2 identity,
the JEMI transcript and live/saved reconciliation, OSM/IDF geometry and loads,
schedule/thermostat references, CSV reconciliation, EnergyPlus SQL integrity,
and an independently generated EnergyPlus rerun. `gt_manifest.json` lists the 24
actual evaluator-required delivery files and their exact hashes.

## Research sources

- Revit 2025 `IFCExportOptions.SpaceBoundaryLevel` values and energy-analysis
  intent: <https://rvtdocs.com/2025/Autodesk.Revit.DB.IFCExportOptions.SpaceBoundaryLevel>
- Autodesk Revit IFC v25.4.4 GUID implementation:
  <https://github.com/Autodesk/revit-ifc/blob/IFC_v25.4.4/Source/Revit.IFC.Export/Utility/GUIDOptions.cs>
- Archicad 27 Model View Definitions, including IFC4 Reference View:
  <https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-47.htm>
- Archicad 27 IFC translators and space-boundary add-on behavior:
  <https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-42.htm>
  and <https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-5.htm>
- OpenStudio 3.10 `ForwardTranslator` API:
  <https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/energyplus/html/classopenstudio_1_1energyplus_1_1_forward_translator.html>
- OpenStudio 3.10 CLI/run implementation:
  <https://github.com/NatLabRockies/OpenStudio/blob/v3.10.0/src/cli/main.cpp>
  and <https://github.com/NatLabRockies/OpenStudio/blob/v3.10.0/src/cli/RunCommand.cpp>
- EnergyPlus 25.1 SQL schema/output documentation:
  <https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html>
- EnergyPlus 25.1 native run/completion implementation:
  <https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc#L358-L398>

## Instance cleanup receipt

After all GT files and the final matrix had been downloaded, cleanup completed
at `2026-08-12T05:31:49.7966476Z`. It removed the 24 task inputs/outputs,
`eval.py`, evaluator metrics/matrix, `EngiWorld_EnergyHandoff_psets.txt`,
`stage2.ifc.log`, Revit launcher logs, and the complete `run` directory from the
Desktop. It also removed `C:\Users\user\Documents\EngiWorld-task-03` and
`C:\Users\user\Documents\EngiWorld-task-03-build`; the matrix directory had
already been removed by the matrix's per-case `finally` cleanup. No native
application process remained to stop, and the temporary Revit add-in registration
had already been removed by its launcher.

A second read-only verification at `2026-08-12T05:32:10.7311767Z` confirmed:

- Desktop contains exactly `desktop.ini` and `Microsoft Edge.lnk`.
- No `EngiWorld-task-03*` directory remains under Documents.
- No Revit, IFC command server, OpenStudio, EnergyPlus, or Task-03 process remains.
- No listener remains on port `19738`.
- `C:\ProgramData\Autodesk\Revit\Addins\2025\EngiWorld.BimBridge.addin` is absent.
