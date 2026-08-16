# Task-04 ground-truth generation and validation

## Independent task decision

The old review correctly pointed toward a native rebuild, but its GT provenance
was not acceptable: the IFC had been authored by a shared IfcOpenShell script
and the OpenStudio stage was not the pinned Windows installation. Direct seed
inspection showed one Gallery space, four walls, one slab, and no roof, door,
window, or opening. The repaired task splits only that Gallery into two spaces,
adds a real geometric gable roof, and does not invent openings. The input
contract intentionally does not predeclare either output IfcSpace GlobalId:
Revit creates both identities at runtime and the handoffs bind those actual IDs.

The original instruction also required second-level space boundaries. Revit
2025 actually exported zero boundary relationships even when level 2 was
requested. The repaired instruction and evaluator therefore require Archicad to
observe and preserve the real upstream state without fabricating relationships.

## Native workflow

The task-local launchers ran in order on the mapped Windows snapshot:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

Observed native software:

- Revit `25.1.0.44`, build `20240516_1515(x64)`, through the task-local
  `EngiWorld.BimBridge` IExternalApplication.
- Archicad 27 build `6000`, through IFCCommandServer/JEMI on port `19739`,
  model `EW3B04-RUN`.
- OpenStudio `3.10.0+86d7e215a1` and its ForwardTranslator.
- Bundled EnergyPlus `25.1.0-1c11a3d85f`.

`native_stage_log.json` records exact executables, commands, timestamps, exit
codes, versions, and artifact hashes.

## IFC findings

Revit preserved all four seed wall GlobalIds, the slab GlobalId and geometry,
and all seed spatial-container GlobalIds. It produced:

| Space | IFC GlobalId | Area (m2) | Thermal zone |
| --- | --- | ---: | --- |
| GARDEN-GALLERY | `0Mc8kN16L0EgUTaiPLzpaM` | 39.44 | GARDEN-GALLERY-ZN |
| ENTRY-NICHE | `0Mc8kN16L0EgUTaiPLzpaK` | 5.80 | ENTRY-NICHE-ZN |

The two spaces are adjacent and their union exactly matches the 7.8 x 5.8 x
2.4384 m seed Gallery volume. The new `IfcRoof` has two represented slope
solids, a centered ridge, a 7.8 x 5.8 m footprint, 1.2 m ridge rise, and 0.15 m
thickness. The evaluator derives and checks these facts from geometry.

Archicad loaded stage 1, ran `Macro.ValidateIfcModel`, queried eleven IFC
classes plus GlobalId/Name/LongName for both live spaces, and saved stage 2.
Both files contain 113 unique IfcRoot objects; all 113 IDs and forward semantics
are retained. Both contain two spaces, four walls, one slab, one roof, and zero
doors, windows, openings, or space-boundary relationships.

## Energy findings

OpenStudio consumed the real Archicad IFC and keyed handoff, then created two
separate spaces and zones with loads, schedules, outdoor air, thermostats,
`PitchedRoofConstruction`, `GardenGallerySchedule`,
`GalleryDaylightAssumption`, and named outdoor roof surfaces. The daylight item
is explicitly a Gallery metadata schedule assumption, not a claim that a
daylighting-control object exists. Each zone has its own dual-setpoint
thermostat and ideal-air-loads conditioning assumption; object display names
are not part of the contract. Each named roof surface uses
`PitchedRoofConstruction` and is Outdoors, SunExposed, and WindExposed in both
the OSM and forward-translated IDF. It saved the OSM,
forward-translated the IDF, and ran an annual EnergyPlus simulation.

The SQL integrity check is `ok`; `Time`, `ReportData`, and hourly
`Electricity:Facility` each contain 8,760 rows. Zone floor areas are 39.44 and
5.80 m2. Total site energy is 6,550.0 kWh and peak load is 0.31 kW.
`eplusout.err` reports 9 warnings, 0 severe errors, and successful completion.
As observed for this exact build, the SQLite completion fields are FALSE/FALSE;
the evaluator instead requires exact build identity, the clean ERR result,
complete annual SQL data, and an evaluator-side EnergyPlus rerun.

## Validation

The Windows baseline returned `True` after its independent EnergyPlus rerun. An
equivalent result with the two `model_summary.csv` data rows reordered also
passed. High-value negative cases independently reject changed roof ridge
geometry, changed stage-2 roof GlobalId, changed handoff space area, a SQL file
replaced by text, Ground/NoSun/NoWind roof exposure, wrong roof construction,
missing Gallery daylight metadata, disabled ideal loads, and wrong thermostat
setpoints.

The evaluator also checks immutable inputs, seed retention, IFC geometry and
semantic Psets/Qtos, task-local JEMI provenance and transcript, live/saved
entity reconciliation, OSM/IDF objects and references, CSV/hash reconciliation,
SQL integrity and annual coverage, and the independent EnergyPlus rerun.

## Research sources

- Revit 2025 DirectShape API:
  <https://www.revitapidocs.com/2025/bfbd137b-c2c2-71bb-6f4a-992d0dcf6ea8.htm>
- Revit 2025 IFC space-boundary option:
  <https://rvtdocs.com/2025/Autodesk.Revit.DB.IFCExportOptions.SpaceBoundaryLevel>
- Archicad 27 IFC translator behavior:
  <https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-42.htm>
- OpenStudio 3.10 ForwardTranslator API:
  <https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/energyplus/html/classopenstudio_1_1energyplus_1_1_forward_translator.html>
- EnergyPlus 25.1 SQL output specification:
  <https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html>
- EnergyPlus 25.1 native completion path:
  <https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc#L358-L398>

## Instance cleanup receipt

After all native GT and validation evidence was downloaded, the task inputs,
outputs, console logs, evaluator artifacts, run directory, Revit parameter file,
stage-2 log, and task-04 Documents/build/eval directories were removed. The
temporary Revit add-in registration had already been removed by the launcher.
The post-cleanup read-only verification timestamp and the exact remaining state
were recorded twice. At `2026-08-12T06:47:25.3039095Z` and again at
`2026-08-12T06:47:59.2255476Z`, Desktop contained only the pre-existing
`Microsoft Edge.lnk`; no `EngiWorld-task-04*` Documents directory, Revit,
IFCCommandServerApp, OpenStudio, or EnergyPlus process, port `19739` listener,
Revit add-in manifest, or add-in directory remained.
