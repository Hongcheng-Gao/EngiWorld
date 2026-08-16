# Ground-truth generation notes

This ground truth was regenerated end to end on the task-02 Windows instance.
Revit 2025 file version 25.1.0.44 opened the supplied IFC4 seed through the
task-local `EngiWorld.BimBridge` and exported `stage1.ifc`. Archicad 27 build
6000 loaded, queried, validated, and saved that file through its native IFC
command server. OpenStudio 3.10.0+86d7e215a1 then built and saved the OSM,
forward-translated the IDF with zero translator errors, and ran the bundled
EnergyPlus 25.1.0-1c11a3d85f annual simulation.

The seed was inspected rather than inferred from neighboring tasks. It contains
two spaces, five walls, one slab, no roof, no door, no window, ten generic
`IfcRelSpaceBoundary` rows, and no `IfcRelSpaceBoundary2ndLevel` rows. Revit
produced three geometric spaces: RETAIL-SALES at 37.24 m2, PREP-KITCHEN at
10.44 m2, and DRY-STORAGE at 7.20 m2. Revit retained all six seed IfcElement
GlobalIds, 9 of 11 seed IfcProduct GlobalIds, and all project/site/building/
storey GlobalIds. Revit 2025 placed the requested room names in
`IfcSpace.LongName` and emitted no space-boundary relationships in this actual
export, despite requesting boundary level 2.

Archicad's live JEMI queries and the saved IFC agree on every checked class and
all three spaces. Its `Model.SaveFile` output retained all 128 stage1 IfcRoot
GlobalIds with no duplicates. Both stage1 and stage2 contain zero boundary
relationships, so the validation report records that observed state and does
not fabricate or claim second-level relationships. The saved IFC retains the
internal `FILE_NAME('stage1.ifc', ...)` value and has Graphisoft's native
`The EXPRESS Data Manager Version 5.02.0100.09` save signature.

The reproducible launcher order is:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

Final evaluation returned `True` with no errors and reran `in.idf` through the
installed EnergyPlus. SQLite integrity is `ok`; `ReportData` has 8,760 rows,
`TabularDataWithStrings` has 6,692 rows, total site energy is 11,100 kWh, and
the ERR file reports successful completion with zero severe errors. This exact
EnergyPlus 25.1 build leaves `Simulations.Completed` and
`CompletedSuccessfully` at `FALSE/FALSE` after a genuine successful run. The
evaluator accepts that pair only with the exact build, clean ERR and SQL error
evidence, populated standard tables, positive energy, and a matching native
rerun; mixed flags are rejected.

The final strict evaluator was recompiled and executed on the same Windows
snapshot. A direct baseline evaluation invoked
`C:\openstudio-3.10.0\EnergyPlus\energyplus.exe`, returned `True` with an empty
error list, and removed its rerun directory. The complete isolated matrix then
ran 43 cases against the formal evaluator, using real EnergyPlus for every case
that reached the rerun step; all 43 produced the expected result in 62.889 s,
with no residual case or rerun directories.

The six accepted cases were the native baseline plus semantically equivalent
JSON member ordering, CSV row ordering, seven- and nine-digit fractional
timestamps, and an equivalent `+08:00` timezone representation. Rejected cases
covered every immutable uploaded payload; a changed seed with all downstream
hashes propagated; changed seed-element geometry in stage1; changed non-target
IfcRoot semantics in stage2; fabricated Revit GlobalId, area, and load values
propagated downstream; Archicad/Revit handoff divergence; malformed, failing,
or inconsistent JEMI responses, live counts, live space attributes, port, and
database provenance; placeholder or structurally broken OSM/IDF geometry,
references, and thermostats; duplicate SQL simulation rows, invalid 8,760-hour
calendar coverage, changed zone areas and hourly peak; mismatched flow/energy
totals, peaks, and completion state; evaluator-side rerun metric divergence;
and rerun cleanup on both success and failure.

Instance cleanup completed at `2026-08-11T18:07:46Z` after the final artifacts
had been downloaded to the task's original local directories. Every task-02
file and directory observed on `C:\Users\user\Desktop`, including evaluator
rerun output and caches, was removed by an explicit-name allowlist, and
`C:\Users\user\Documents\EngiWorld-task-02` was removed recursively. An
independent post-cleanup inventory confirmed that the Desktop contained exactly
`desktop.ini` and `Microsoft Edge.lnk`; the Documents work directory and both
temporary ProgramData add-in paths were absent; no Revit,
IFCCommandServerApp, OpenStudio, or EnergyPlus process remained; TCP port 19737
had no listener; and no Revit journal had been created since the recorded final
run start (`2026-08-11T17:54:00Z`).

The later strict-evaluator audit used only
`C:\Users\user\Documents\EngiWorld-task-02` and its explicitly named sibling
audit directory. After the 43-case Windows matrix and receipt hashes were
downloaded, both directories were removed at
`2026-08-12T03:30:38.0987492Z`. A fresh inventory at
`2026-08-12T03:30:54.2717675Z` reconfirmed the exact Desktop allowlist, no
task-02 entry in Documents, no temporary ProgramData bridge/add-in, no relevant
process, and no listener on port 19737.

A subsequent adversarial review found that the generic 80% `IfcProduct`
retention threshold alone could be bypassed by changing a seed spatial
container GlobalId and reusing the old identifier on another product. The
evaluator now requires the seed `IfcProject`, `IfcSite`, `IfcBuilding`, and
`IfcBuildingStorey` GlobalIds to remain in the corresponding stage1 IFC class,
and requires a valid Project-to-Site-to-Building-to-Storey aggregation
hierarchy. It deliberately does not freeze spatial names, descriptions,
ObjectType, LongName, elevation, world placement, relationship GlobalIds, or
the exact seed aggregation relationship, because Revit may legitimately
normalize those details while retaining identity and a valid hierarchy.

The expanded local mutation matrix passed all 45 cases. Its added reasonable
equivalence case changed storey metadata, elevation, world placement, and the
Building-to-Storey relationship GlobalId while compensating child placements
to preserve element world geometry; it passed with no errors. Its added attack
changed the storey GlobalId in stage1 and stage2, propagated every downstream
hash and audit count, and reused the original identifier on an
`IfcBuildingElementProxy`; it was rejected specifically as
`init_to_stage1:seed_spatial_globalid_not_preserved:IfcBuildingStorey`, without
falling below the generic product-retention threshold.

The final focused regression ran on the Windows snapshot with the formal
evaluator SHA-256
`71adb96a2d2861a475b3a05d656d53344ba1b82f6c7a995a866d79b65d2d34d0`.
All three isolated real-EnergyPlus cases passed their expected result: the
untouched baseline and spatial-normalization equivalent were accepted with
empty error lists, while the propagated GlobalId-reuse attack reached only the
dedicated storey error. Every evaluator rerun and per-case directory was
removed. The receipt reconfirmed the unchanged stage1, stage2, and SQL hashes.
After downloading the evidence, the task root was removed; a fresh inventory at
`2026-08-12T04:12:07.0389708Z` found no task-02 Documents entry, audit directory,
temporary ProgramData bridge/add-in, relevant process, or port 19737 listener,
and the Desktop contained exactly `desktop.ini` and `Microsoft Edge.lnk`.

Version-specific sources used during review:

- https://rvtdocs.com/2025/Autodesk.Revit.DB.IFCExportOptions.SpaceBoundaryLevel
- https://github.com/Autodesk/revit-ifc/blob/IFC_v25.4.4/Source/Revit.IFC.Export/Utility/GUIDOptions.cs
- https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-47.htm
- https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-42.htm
- https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-5.htm
- https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/energyplus/html/classopenstudio_1_1energyplus_1_1_forward_translator.html
- https://github.com/NatLabRockies/OpenStudio/blob/v3.10.0/src/cli/main.cpp
- https://github.com/NatLabRockies/OpenStudio/blob/v3.10.0/src/cli/RunCommand.cpp
- https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html
- https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc#L358-L398
