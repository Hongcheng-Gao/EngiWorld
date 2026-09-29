# Ground-truth generation and verification

This ground truth was regenerated on the pinned
`cli3-revit2025-archicad27-openstudio310-win` instance. No delivered IFC, OSM,
IDF, SQL, JSON, or CSV result was hand-authored. The formal commands were run in
this order:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

## Native stages

Revit 2025 file version 25.1.0.44 opened `init.ifc` through the task-local
`IExternalApplication`. The bridge source was rebuilt in Release mode on the
pinned instance with zero compile errors. The checked-in DLL has SHA-256
`46ebf17a38bbe1eaf5e50322225cab3ed5356c72c9f52398928a8eb24ba945b7`
and corresponds to the checked-in source whose SHA-256 is
`8b205a19ccf665d5b68da9afcd45e3a2b6174a95cdc9d2afd00f8eb4a8582b28`.
Revit produced two `IfcSpace` objects: `COMMUNITY-ACTIVITY` at 34.80 m2 and
`QUIET-COUNSELLING` at 16.24 m2.

Archicad 27 build 6000 used `IFCCommandServerApp.exe` and the JEMI methods
`Model.LoadFile`, `Macro.ValidateIfcModel`, `Entity.Get`,
`Entity.GetAttribute`, and `Model.SaveFile`. The live command selections and
the independently parsed saved IFC both contain two spaces, four walls, one
slab, one storey, and no doors, windows, roofs, or openings. All 105 stage-1
`IfcRoot` GlobalIds are unique and all 105 are preserved in stage 2. The input
contains no `IfcRelSpaceBoundary` or `IfcRelSpaceBoundary2ndLevel` relationship,
so stage 2 truthfully preserves and reports zero rather than inventing a
boundary relationship.

`stage2.ifc` is the output of Graphisoft's EXPRESS Data Manager save operation.
Its header therefore retains `FILE_NAME('stage1.ifc', ...)` and identifies both
the EDM writer and the upstream Autodesk Revit IFC application. The task-local
`archicad_ifc4_translator.json` is a workflow contract; it is not presented as
a Graphisoft UI translator header.

OpenStudio `3.10.0+86d7e215a1` consumed the saved stage-2 IFC and verified
Archicad handoff. It generated two separate spaces and thermal zones with the
handed-off people, lighting, equipment, outdoor-air, thermostat, schedule,
construction, and weather inputs, then forward-translated the model to IDF.
EnergyPlus `25.1.0-1c11a3d85f` ran the IDF against `weather.epw` and returned
exit code 0. The SQL contains one weather run period, exactly 8760 hourly Time
rows, zone floor areas of 34.80 and 16.24 m2, and 8055.556 kWh total site
energy. The ERR ends with `EnergyPlus Completed Successfully` and reports zero
severe errors.

## EnergyPlus 25.1 completion flags

The submitted run and an independent direct EnergyPlus run both write
`FALSE/FALSE` to the SQL `Simulations.Completed` and
`Simulations.CompletedSuccessfully` fields despite a clean exit, successful
ERR termination, populated result tables, 8760 annual hours, and no severe or
fatal SQL error record. This is a pinned 25.1 CLI finalization-order behavior:
`wrapUpEnergyPlus` releases the SQLite object before `EndEnergyPlus` attempts
the final completion update, so the null guard skips the update. The evaluator
does not accept the flags in isolation. It accepts this state only when the
submitted output and an evaluator-owned rerun reproduce the same flag pair,
clean ERR state, populated annual SQL data, matching positive energy, and the
recorded command/hash/mtime provenance. Offline flag edits are rejected by the
independent rerun comparison.

## Evaluator checks

The final evaluator result on the pinned instance was `True` with an empty
error list. It parses all IFC roots and spaces, validates JEMI provenance and
live/saved counts, checks the two IFC handoffs and all downstream hashes, parses
the OSM/IDF/CSV semantics, opens every required EnergyPlus SQLite table, checks
the annual 8760-hour run, and reruns EnergyPlus 25.1 in a fresh directory. The
two target `IfcSpace` objects are also evaluated through IfcOpenShell world
geometry: their `6.0 x 5.8 x 2.4384 m` and `2.8 x 5.8 x 2.4384 m` bounding boxes
and relative adjacency must match the immutable workflow specification, while
a common model translation remains allowed.

The final mutation matrix was run locally and again on the pinned Windows
instance with the final evaluator bytes and real EnergyPlus. All `38/38` cases
passed their expectations: three candidate baselines/equivalent representations
were accepted, 34 independently copied and mutated candidate cases were
rejected, and one evaluator-cleanup case verified removal of the owned rerun
directory after both successful and failed subprocess paths. Thus the matrix is
3 positive + 34 negative + 1 evaluator-cleanup case, not 38 candidate variants.
The rejection set includes malformed RPC envelopes,
native RPC sequence mismatch, seed/stage semantic mutations, target-space IFC
geometry mutation, workflow/handoff mapping conflicts, exact-cardinality
violations, direct-field hash shadow attacks, OSM/IDF shell and story errors,
shared or cross-wired thermostats, EnergyPlus calendar/zone/`Simulations` row
mutations, and energy/EUI changes outside the stated tolerances. The Windows
matrix left no `matrix-temp` or `_eval_energyplus_rerun` directory. The
machine-readable `validation_matrix_result.json` preserves all 17 detailed rows
that survived from the run and separately records the contemporaneous full-run
38/38 aggregate; it does not invent names or outcomes for the 21 rows whose
per-case detail was not retained.

After the immutable-input coverage patch, the formal candidate was evaluated
again on the pinned Windows instance and returned `True` with an empty error
list, including the evaluator-owned EnergyPlus 25.1 rerun. In an isolated copy,
appending a harmless comment only to `run_revit_stage.ps1` returned `False` with
the sole error `immutable_input_sha256_mismatch:run_revit_stage.ps1`.

## Official sources

- Revit 2025 API Developers Guide:
  https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html
- Autodesk Revit IFC exporter source (select the matching 2025 release):
  https://github.com/Autodesk/revit-ifc
- Graphisoft JSON interface documentation:
  https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- Archicad 27 IFC documentation:
  https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- OpenStudio 3.10.0 release:
  https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- OpenStudio 3.10.0 CLI entry point and command implementation:
  https://github.com/NatLabRockies/OpenStudio/blob/v3.10.0/src/cli/main.cpp
  https://github.com/NatLabRockies/OpenStudio/blob/v3.10.0/src/cli/RunCommand.cpp
- OpenStudio 3.10.0 ForwardTranslator API:
  https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/energyplus/html/classopenstudio_1_1energyplus_1_1_forward_translator.html
- EnergyPlus 25.1 SQLite output documentation:
  https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html#simulations-table
- EnergyPlus 25.1 SQLite F/F initialization and update statements:
  https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/SQLiteProcedures.cc#L1184-L1202
- EnergyPlus 25.1 normal completion update and successful ERR write:
  https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/UtilityRoutines.cc#L577-L647
- EnergyPlus 25.1 CLI finalization order (`sqlite.reset()` before
  `EndEnergyPlus`):
  https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc#L358-L398

## Instance cleanup

After the final artifacts and test evidence were downloaded, all task-created
desktop inputs, outputs, launchers, evaluator files, Archicad databases and
probes, Revit bridge build/install files, EnergyPlus run/direct-run/rerun
directories, mutation directories, task logs, and matching Revit journals were
removed. The final independent enumeration at `2026-08-11T19:19:54Z` returned
`clean=true`: the explicit `Documents\EngiWorld-task-01` root was absent; no
Revit, IFCCommandServer, OpenStudio, EnergyPlus, task PowerShell, VBCS
build-server, SteelConnections LocalDB, or task-spawned ADP process remained;
TCP ports 19736 and 19737 had no listener; all checked task database and Revit
add-in paths were absent; and the Desktop contained only the pre-existing
`desktop.ini` and `Microsoft Edge.lnk` items.

The post-patch formal and immutable-tamper audit was cleaned independently at
`2026-08-12T19:22:14Z`. The 26 explicitly uploaded Desktop files, formal and
tamper `multi_metrics.json` files, `run`, `_eval_energyplus_rerun`,
`matrix-temp`, and `Documents\EngiWorld-task01-immutable-audit` were removed.
The final enumeration found only `desktop.ini` and `Microsoft Edge.lnk` on the
Desktop, no task-01/evaluator/rerun residue below Desktop or Documents, no
Revit/IFCCommandServer/OpenStudio/EnergyPlus/VBCSCompiler process, no listener
on 19736 or 19737, and no EngiWorld Revit add-in file. Existing Revit journals
whose last-write times predate this audit were retained because this validation
did not launch Revit and therefore did not create them.
