# Task-08 native ground-truth record

## Scope and outcome

This task was repaired independently on snapshot
`cli3-revit2025-archicad27-openstudio310-win`. The native chain was executed in
the required order: Revit 2025, Archicad 27, OpenStudio 3.10.0, EnergyPlus
25.1.0. The final IFC contains four geometric spaces: `L1-LAB` 47.60 m2,
`L1-PREP` 19.04 m2, `L2-LAB` 47.60 m2 and `L2-PREP` 19.04 m2, totaling
133.28 m2. Each has the required storey, quantities and energy handoff. The two
LAB spaces retain their init GlobalIds.

No candidate stage output is accepted merely because it matches a GT hash. The
evaluator checks IFC geometry/semantics/relations, Archicad RPC evidence, OSM
object references and parameters, standard EnergyPlus SQLite contents, and
independent OpenStudio/EnergyPlus regeneration.

## Native stages

- Revit: `Revit.exe` 25.1.0.44, build `20240516_1515(x64)`, PID 984. Started
  `2026-08-12T13:22:53.0972150Z`, finished
  `2026-08-12T13:30:10.8323399Z`. The temporary add-in compiled with 0 errors
  and produced `stage1.ifc` SHA-256
  `6d04acbfc6908e98eed860716eebbf7124e12c1ff0ca4249102c6bcb32d5b088`.
  The native UI decisions were `Unsigned Add-in: Load Once` and
  `IFC4 Open warning: OK`.
  The outer OSWorld `/execute` launcher request reached its 120-second HTTP
  timeout before Revit finished. Revit continued under the same PID and
  completed the stage. Because the launcher did not write a final log, the
  Revit entry in `native_stage_log.json` is explicitly marked
  `reconstructed_after_launcher_http_timeout`; its evidence is limited to the
  same continuing PID 984, `journal.0033.txt`, the executable version/build,
  observed output and handoff hashes, timestamps and those two UI decisions.
  It does not claim that a completed launcher log existed.
- Archicad: Archicad 27 build 6000 through the real IFCCommandServer/JEMI
  endpoint. Its 30-entry RPC transcript is Load, Validate, 15 entity queries,
  12 live space attribute queries and Save. It produced `stage2.ifc` SHA-256
  `6c5c84c9b726e8a33a6231400d41dc1a9f6dec759774700e8a32bc94d88d2f47`.
  All 312 IfcRoot GlobalIds were retained; live/saved counts and host-opening
  graphs reconcile, with no blocking validation errors.
- OpenStudio/EnergyPlus: OpenStudio `3.10.0+86d7e215a1` forward-translated the
  OSM and invoked EnergyPlus `25.1.0-1c11a3d85f`. Before model construction,
  task-local `extract_ifc_space_geometry.py` used IfcOpenShell to parse the real
  `stage2.ifc` and derive every space name, GUID, storey GUID/name, world bbox,
  dimensions, floor area, volume and closedness. The converter used those IFC
  facts for geometry and containment; `workflow_spec.json` supplied and checked
  energy semantics only. The full 2006 annual run
  completed with 0 severe errors, 7 non-blocking warnings, 43,847.222 kWh total
  site energy and 6.426 kW peak load. The warnings concern missing EPW design
  condition/ground-temperature fields and unused resource objects.

The authoritative hashes and timestamps for every stage are in
`native_stage_log.json`; `gt_manifest.json` inventories the final file set.

## Reproduction

On the pinned Windows snapshot, upload every task-local `init_file` item and run:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
python C:\Users\user\Desktop\eval.py
```

## Validation

- Local formal evaluation: `True`, no errors.
- Windows formal evaluation: `True`, no errors. This run executed the independent
  OpenStudio 3.10 ForwardTranslator and EnergyPlus 25.1 annual rerun.
- Local and Windows validation matrices: 20/20 expected outcomes on each
  platform. The native model, semantically equivalent OSM reordering and a
  provenance-coherent IFC coplanar roof retriangulation all passed. Seventeen
  targeted mutations were rejected: retained LAB GlobalId, wrong stage1 space
  geometry, stage1 and stage2 storey containment, missing stage2 Representation,
  open roof, host-opening graph, Archicad Save RPC, schedule, equipment load,
  outdoor air, shared zone, dangling OSM handle, hand-edited IDF, truncated SQL,
  nonannual/zero-energy SQL and a coherent-looking forged Revit reconstruction
  log.

## Cleanup

After the task and validation matrix, the instance directories
`EngiWorld-task-08-work`, `EngiWorld-task-08-build` and
`EngiWorld-task-08-eval` were removed. The temporary Revit add-in file/directory,
the Archicad database and the task-local extractor JSON/archive/log caches were
removed with the work directory. Final checks reported zero Revit, Archicad
Starter, IFCCommandServerApp, OpenStudio and EnergyPlus processes; TCP port
19740 was not listening.

## Sources

- Revit 2025 API Developers Guide:
  https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html
- Archicad 27 IFC documentation:
  https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-3.htm
- OpenStudio 3.10.0 official release:
  https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- EnergyPlus 25.1 `eplusout.sql` documentation:
  https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html

The supplied audit workbook was treated only as directional context. Its
task-specific row could not be extracted in this environment because the
required workspace dependency loader and `@oai/artifact-tool` runtime were not
available; no alternate spreadsheet library was installed or used. The final
decision instead rests on direct inspection of this task's instruction, init,
native artifacts, evaluator and independent Snapshot validation.
