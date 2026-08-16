# Task-05 ground-truth generation and validation

## Independent task decision

The seed was inspected independently. It contains two storeys, three geometric
spaces, nine walls, two 300 mm slabs, fifteen first-level boundary relations,
and no opening or `IfcRelVoidsElement`. The old instruction's demand to retain
an opening therefore conflicted with the init. The repaired instruction asks
Revit to create the opening. It also asks Archicad to preserve the actually
observed native boundary state instead of requiring fabricated second-level
relations. Output space and opening GlobalIds are runtime values, not input
answers.

The Ground Floor rooms have a combined 9.8 x 6.8 m interior footprint. The
Level 2 seed room has the same footprint. The repaired workflow removes only
the original Ground Floor partition, splits Level 2 at x=7.1 m, and retains the
two-storey exterior massing. It does not invent a roof, door, or window.

## Native workflow

The task-local launchers ran in exact order on the mapped Windows snapshot:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

The Revit bridge was compiled on that instance against Revit 2025 and its IFC
export assemblies. Observed versions were Revit `25.1.0.44`, Archicad 27 build
`6000`, OpenStudio `3.10.0+86d7e215a1`, and EnergyPlus
`25.1.0-1c11a3d85f`.

The first native Revit attempt proved the opening workflow but selected a
default 152.4 mm FloorType. That output was rejected because the seed slab was
300 mm. Its artifacts were deleted. The bridge was repaired to duplicate and
adjust a native Revit FloorType to exactly 300 mm, recompiled, and rerun before
Archicad was started.

## IFC findings

The accepted Revit export has two 300 mm slabs and the following spaces:

| Space | IFC GlobalId | Area (m2) | Storey |
| --- | --- | ---: | --- |
| GROUND-PUBLIC | `2Nu6lW7sLE7P7Wl$0XgzdD` | 66.64 | Ground Floor |
| UPPER-ACTIVITY | `2Nu6lW7sLE7P7Wl$0XgzdF` | 47.60 | Level 2 |
| UPPER-READING | `2Nu6lW7sLE7P7Wl$0Xgzd9` | 19.04 | Level 2 |

The sole `IfcOpeningElement` is `18fjt0IrS3GwyZ8F9VdAng`. Its world bounds are
x=4.0..6.0, y=2.4..4.4, z=2.7..3.0 m. Exactly one
`IfcRelVoidsElement` connects it to slab `3Wgih0yJ93kwR5eUsrhi_H`.

Archicad loaded the actual stage 1, ran `Macro.ValidateIfcModel`, queried live
entities and space attributes, and saved stage 2. Stage 1 and stage 2 each have
187 unique IfcRoot objects; all 187 GlobalIds and classes are retained. Both
files have three spaces, two storeys, eight walls, two slabs, one opening and
one void relation. The real Revit export contained zero boundary relations,
and Archicad preserved that 0 -> 0 state without synthesis.

## Energy findings

OpenStudio consumed stage 2 and the keyed Archicad handoff. It created three
separate stories/spaces/zones with their handed-off schedules, densities,
outdoor air, dual-setpoint thermostats and ideal air loads, then
forward-translated the IDF and launched its exact EnergyPlus build.

The SQL has 8,760 hourly records and nonzero electricity data. Total site
energy is 18,597.222 kWh for 133.28 m2, and peak load is 1.266 kW.
`eplusout.err` reports seven warnings, zero severe errors, and successful
completion. The exact build writes FALSE/FALSE completion flags in SQLite, so
the evaluator instead requires the exact build, clean ERR, annual SQL coverage,
nonzero energy, and its own EnergyPlus rerun.

## Validation

The final Windows evaluator returned `True`, including an independent
EnergyPlus 25.1 rerun. After independent review exposed a host-identity gap,
the unchanged real Revit stage 1 was passed through Archicad 27 and OpenStudio
3.10/EnergyPlus 25.1 again at `2026-08-12T08:58Z`; the regenerated Archicad
handoff and validation report now carry the opening geometry as structured
fields. An equivalent result with only the explanatory boundary note reworded
and its provenance hash updated still returned `True`.

Negative tests independently rejected a broken void relationship, a
reading-room lighting density changed to 99 W/m2, and a modified immutable
workflow spec. The final matrix also rejected (1) a fully hash-coordinated
attack that attached the unique opening to the Ground Floor slab and (2) a
report-only false host GlobalId. The host test binds the void relation to the
configured original Level 2 slab GlobalId, checks its 0..10 m by 0..7 m world
footprint and 2.7..3.0 m elevation, verifies its 300 mm thickness, geometric
net volume, and gross/net IFC quantities, and reconciles the Revit and
Archicad opening metadata with both real IFC files.

The evaluator additionally checks immutable inputs, seed element and spatial
container retention, two-storey space geometry, the sole removed partition,
the exact original 300 mm Level 2 host slab and opening geometry, IFC
Psets/Qtos, Archicad live/saved
count reconciliation and transcript, OSM/IDF object references and stories,
CSV/hash reconciliation, SQL integrity, annual coverage, and native process
provenance.

## Research sources

- Revit 2025 API and IFC export:
  <https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html>
- Revit 2025 `NewOpening(Element, CurveArray, Boolean)`:
  <https://www.revitapidocs.com/2025/ab1718f9-45fb-b3d3-827e-32ff81cf929c.htm>
- Archicad 27 IFC:
  <https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm>
- Archicad JSON Interface:
  <https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/>
- OpenStudio 3.10.0 release:
  <https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0>
- OpenStudio CLI:
  <https://natlabrockies.github.io/OpenStudio-user-documentation/reference/command_line_interface/>
- EnergyPlus 25.1 SQLite output:
  <https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html>
- EnergyPlus 25.1 native completion path:
  <https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc#L358-L398>

## Instance cleanup receipt

After all accepted artifacts and validation evidence were downloaded, the
task-05 Desktop inputs, outputs, logs, evaluator files, run directory, probe
directories, Archicad task database, Revit build directory, temporary shared
parameter file, and Revit add-in registration were removed. Read-only cleanup
checks at `2026-08-12T08:24:57.6097235Z`,
`2026-08-12T08:28:47.3505647Z`, and after the final host-validation matrix
found only `desktop.ini` and
`Microsoft Edge.lnk` on the Desktop, no task-05 Desktop or Documents entries,
no Revit, IFCCommandServerApp, OpenStudio, or EnergyPlus process, no listener
on port 19739, and no task add-in manifest, add-in directory, or temporary
shared-parameter file.
