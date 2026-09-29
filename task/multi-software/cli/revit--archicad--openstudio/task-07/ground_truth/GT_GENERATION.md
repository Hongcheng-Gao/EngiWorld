# Task-07 native ground-truth generation

This bundle was regenerated independently for task-07 in the matching
`cli3-revit2025-archicad27-openstudio310-win` instance. It does not reuse a
task-06 model or offline-authored IFC/OSM/SQL output.

## Native chain

1. Revit 2025 `25.1.0.44` opened the authoritative `init.ifc`, rebuilt the five
   native Rooms, five seed-guid walls and slab, created a represented pitched
   roof, and placed five hosted `M_Door-Single-Panel` doors and three hosted
   fixed windows. Its native IFC4 exporter wrote `stage1.ifc`.
2. Archicad 27 build 6000 loaded the Revit IFC with
   `Model.LoadFile`, ran `Macro.ValidateIfcModel`, queried the live entities and
   space attributes, and wrote `stage2.ifc` with `Model.SaveFile`.
3. OpenStudio `3.10.0+86d7e215a1` consumed the Archicad handoff, created five
   geometric Spaces, five separate ThermalZones, loads, outdoor air, five
   schedules, thermostats and constructions, then forward-translated `in.idf`.
4. EnergyPlus `25.1.0-1c11a3d85f` ran the annual simulation and wrote the SQL.

The Revit IFC4 open warning (IFC4 is partially supported by Open IFC) was
accepted because Revit subsequently authored and exported the requested native
objects. OpenStudio noted that the EPW omits optional design conditions and
ground-temperature depths; EnergyPlus used its documented defaults and
completed with 7 warnings and 0 severe errors.

## Verified semantics

- Space areas are `31.20`, `45.24`, `31.20`, `18.24`, and `11.40 m2`, totaling
  `137.28 m2`.
- Reading and Staff retain seed GUIDs `0aVENBQ497bg_zKWR$4g_S` and
  `0aVENBQ497bg_zKWR$4g_Q`. All five seed wall GUIDs and the slab GUID are also
  retained with matching world bounds.
- Both IFC stages contain one represented pitched roof and exactly 5 doors,
  3 windows, 8 represented openings, 8 void relations, and 8 fill relations.
  Every host-opening and opening-filling endpoint pair is unchanged by Archicad.
- Revit emitted no `IfcRelSpaceBoundary` or second-level boundary relationship.
  Archicad preserved this observed state; no relationships were fabricated.
- Archicad reported no validation issue and preserved all 276 upstream root
  GUIDs with no duplicates.
- EnergyPlus completed successfully with `18686.111 kWh` total site energy and
  `136.1168 kWh/m2` EUI.

## Evaluator verification

The standalone evaluator compares no generated artifact to a GT byte hash.
Immutable task inputs and launchers are hash-pinned; outputs are checked from
their parsed IFC graph and mesh, handoff values, complete OSM handle graph,
per-space surface vertices, CSV rows, provenance hash chain, and EnergyPlus
SQLite tables. On the pinned Windows image it loads `result.osm` through the
OpenStudio 3.10 VersionTranslator, independently forward-translates it, compares
the canonical IDF to the submitted `in.idf`, then reruns EnergyPlus 25.1 from a
temporary copy of the IDF and EPW. The rerun is reconciled against submitted SQL
zones, surfaces, nominal loads/ventilation, 8760-hour meter series, and total
site energy; the submitted directory remains read-only during this check.
This evaluator repair was required because a counterexample showed that the
earlier name/count checks accepted a LOBBY-to-READING thermal-zone handle
rewire whenever the old `in.idf` and SQL were left unchanged.

Validation matrix:

- Native positive bundle: pass locally and on the matching Windows snapshot,
  including native OpenStudio forward translation and EnergyPlus rerun.
- Equivalent fresh bundle with a new valid runtime GUID for non-seed LOBBY,
  consistently propagated through both IFCs and all handoffs/hashes: pass.
- Missing stage2, tampered spec, removed door, removed fill relation, rewired
  opening, wrong room area, dropped stage2 root, broken OSM zone, broken OSM
  schedule, zero energy CSV, and fake SQL: all fail as intended (11 negatives).
- A second targeted matrix passes 1 positive and rejects 9 independent
  counterexamples: OSM zone rewire, orphaned People load, wrong Lights schedule,
  changed lighting density, changed outdoor air, changed surface vertex, copied
  stage1 masquerading as the Archicad save, forged JEMI attribute response, and
  a SQL zone-area mutation. All OSM mutations also produce an independently
  translated IDF mismatch on Windows.
- The final topology matrix extends that set with three valid-IFC geometry
  counterexamples while preserving outer bounds: an open roof shell, a seed
  wall with an internal profile void, and the seed slab with an internal
  profile void. Canonical coplanar-face boundaries, indexed edge closure,
  surface area, triangle count, and nonzero signed volume reject all three,
  while allowing Archicad's equivalent change of a coplanar face diagonal.

## Instance cleanup

After all native stages, validation, and the Windows evaluator rerun, the
task-local directories `C:\Users\user\Documents\EngiWorld-task-07-work`,
`C:\Users\user\Documents\EngiWorld-task-07-build`, and the evaluator-only
`C:\Users\user\Documents\EngiWorld-task-07-eval` were recursively removed.
The temporary global Revit manifest and `EngiWorld.BimBridge` add-in directory
under `C:\ProgramData\Autodesk\Revit\Addins\2025` were also removed. A final
PowerShell check confirmed both task directories and both add-in paths absent,
no Revit, Archicad/IFCCommandServer, OpenStudio, or EnergyPlus process running,
and no listener on task-local port 19739.

## Official references

- Revit 2025 IFC export API:
  https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_Advanced_Topics_Export_IFC_Export_html
- Revit 2025 Room boundaries:
  https://help.autodesk.com/cloudhelp/2025/ENU/Revit-API-MainReference/files/html/cd40f8d3-e6cf-355e-d3c4-b3296e261485.htm
- Archicad 27 IFC:
  https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-3.htm
- Archicad JSON Interface:
  https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0 release:
  https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- OpenStudio CLI:
  https://natlabrockies.github.io/OpenStudio-user-documentation/reference/command_line_interface/
- EnergyPlus 25.1 SQLite output:
  https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html
