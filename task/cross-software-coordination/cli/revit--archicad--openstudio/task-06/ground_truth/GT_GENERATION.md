# Task-06 ground-truth generation and verification

This task was inspected and regenerated independently on the Windows instance
for `cli3-revit2025-archicad27-openstudio310-win`. The starting IFC was checked
before any software run. Its SHA-256 is
`2fcb86b2fdcea10bcc06c0d151d9017594a167a0255f22e8660699c4b7dca53a`.
It contains six columns, four exterior walls, one slab, one storey, and one
space. It contains no `IfcGrid` or `IfcGridAxis`; no such entities were added.

## Native software chain

The supplied task-local stages were run in this exact order:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

The resulting `native_stage_log.json` records the actual executables, commands,
versions, timestamps, input hashes, and output hashes:

- Revit 2025 `25.1.0.44`, with a bridge compiled against the installed Revit
  2025 API assemblies.
- Archicad 27 build `6000`, driven through its IFC Command Server/JEMI API.
- OpenStudio `3.10.0+86d7e215a1`.
- EnergyPlus `25.1.0-1c11a3d85f`.

Revit preserved the seed project, site, building, storey, six column, four wall,
and slab GlobalIds and world locations. The imported single room could not be
split while preserving that room object's identity. It was therefore replaced
with three real native Revit rooms and exported with the actual runtime IFC
GlobalIds:

| Space | IFC GlobalId | Area (m2) |
|---|---|---:|
| MAKER-WORKSHOP | `2Nwtmlr4bCNAujkCYRnfEz` | 77.775875 |
| OFFICE | `2Nwtmlr4bCNAujkCYRnfE$` | 15.600000 |
| TOOL-ROOM | `2Nwtmlr4bCNAujkCYRnfE_` | 13.983625 |

The areas total `107.3595 m2`, equal to the seed space area. Revit's room
calculation assigns the column-edge areas to the adjacent rooms, so the
MAKER-WORKSHOP and TOOL-ROOM quantities differ slightly from their simple
rectangular extents.

Archicad loaded `stage1.ifc`, queried live entities, ran
`Macro.ValidateIfcModel`, and saved `stage2.ifc`. It preserved all 194 upstream
IfcRoot GlobalIds. The observed space-boundary relationship state is honestly
`0 -> 0`; second-level boundary relations were not fabricated. Archicad reports
six `IfcMaterialProfileSetUsage.AssociatedTo` inverse observations. They are
accepted only after the live six-column count, six profile usages, explicit
`IfcRelAssociatesMaterial` relations, retained GlobalIds, and unchanged world
locations all reconcile. GUID comparisons in the launcher are ordinal and
case-sensitive because two valid runtime GlobalIds differ only by `B`/`b`.

OpenStudio consumed `stage2.ifc` and the keyed handoff, created three spaces and
three independent thermal zones with the requested loads, schedules, outdoor
air, dual-setpoint thermostats, and ideal air loads, then forward-translated and
ran EnergyPlus. The annual simulation produced 8,760 hourly rows, a building
area of `107.36 m2`, total site energy of `34841.667 kWh`, and a peak of
`4.571 kW`. `eplusout.err` records successful completion, seven warnings, and
zero severe errors. On this exact EnergyPlus build, the two SQL completion flags
are `FALSE/FALSE`; validation therefore uses the exact version, clean ERR,
annual SQL tables and signatures, nonzero energy, and an independent EnergyPlus
rerun rather than treating those flags alone as authoritative.

## Evaluator closure

The final evaluator parses the actual IFC entity graph, geometry, quantities,
properties, containment, and retained IDs; reconciles the Archicad live-query
evidence; validates OSM/IDF/CSV/SQL consistency; and independently reruns
EnergyPlus. It does not compare a submission to the GT artifact hashes.

The complete GT returned `True` on the Windows instance. A reasonable equivalent
with only untracked documentation wording changed also returned `True`. Focused
negative cases returned `False` for moved structural geometry/inconsistent
stage1 evidence, a fabricated `IfcGrid`, a 50 W/m2 equipment tamper, truncated
SQL, fake Archicad executable provenance, a fabricated second-level-boundary
claim, and an incorrect stage2 space GlobalId.

## Instance cleanup

The post-task cleanup check completed at `2026-08-12T10:37:21.4206760Z`.
Desktop and Documents contained only the instance baseline after cleanup. The
structured check found zero remaining task directories or task-created files,
zero matching Revit, Archicad/IFCCommandServer, OpenStudio, EnergyPlus, or task
validation processes, no listener on task-local TCP port 19739, and zero
temporary Revit add-in manifest/directory remnants. The later local audit also
removed its evaluator output; the task directory currently contains no
`multi_metrics.json`, Python bytecode/cache, or SQLite sidecar file.

## Research sources

- Revit 2025 API developer guide: https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html
- Revit 2025 room API: https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API-MainReference/files/html/cd40f8d3-e6cf-355e-d3c4-b3296e261485.htm
- Revit 2025 IFC export API: https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_Advanced_Topics_Export_IFC_Export_html
- Archicad 27 IFC: https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- Graphisoft JSON/JEMI API: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10 release: https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- OpenStudio CLI reference: https://natlabrockies.github.io/OpenStudio-user-documentation/reference/command_line_interface/
- EnergyPlus 25.1 SQL output: https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html
