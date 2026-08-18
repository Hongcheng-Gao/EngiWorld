# Task-09 ground-truth generation and validation

This GT was rebuilt on 2026-08-18 in the assigned `cli3-revit2025-archicad27-openstudio310-win` image (`10.0.8.246`). The three supplied stages ran in the required order from `C:\Users\user\Desktop`.

## Native generation

- Revit `25.1.0.44`, build `20240516_1515(x64)`, loaded the task-local `EngiWorld.BimBridge` add-in. The bridge compiled against the installed Revit 2025 API with zero errors; the resulting DLL is 69,120 bytes with SHA-256 `c6a2dd54cf131396905daeeb3d3544c991947df7fa7ead477d591b4802b3b5cb`. Revit produced `stage1.ifc` and `revit_handoff.json` with exit code 0.
- Archicad 27 build 6000 ran `IFCCommandServerApp.exe` on model `EW3B09-RUN`. Its 30-entry JEMI transcript records `Model.LoadFile`, `Macro.ValidateIfcModel`, typed `Entity.Get` / `Entity.GetAttribute` inspection, and `Model.SaveFile`. It produced `stage2.ifc`, `archicad_handoff.json`, and `archicad_validation_report.json` with exit code 0.
- OpenStudio `3.10.0+86d7e215a1` consumed the Archicad IFC and handoff, created four separate thermal zones, forward-translated `result.osm` to `in.idf`, and invoked EnergyPlus `25.1.0-1c11a3d85f` for an annual run. EnergyPlus completed successfully with 7 warnings and 0 severe errors.

The four IFC spaces are `LOBBY` (23.40 m2), `CLASSROOM-A` (46.02 m2), `CLASSROOM-B` (46.02 m2), and `STORAGE` (37.44 m2), totaling 152.88 m2. The delivered IFCs contain five retained walls, one retained slab, one closed pitched roof, four doors, three windows, seven geometric openings, seven void relations, and seven fill relations. `stage1.ifc` and `stage2.ifc` each contain 280 unique `IfcRoot` GlobalIds, all preserved across the Archicad stage.

Run the supplied stages in order on the task image:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

## Evaluator closure

The annual simulation contains 8,760 hourly meter rows, 24,444.444 kWh total site energy, a 1.737 kW peak, and a 159.893 kWh/m2 EUI. The evaluator parses IFC geometry and topology, verifies retained identities and hosted-opening relationships, reconciles Archicad live entity counts and RPC provenance, checks the four OpenStudio schedules and loads, opens standard EnergyPlus SQLite tables, independently forward-translates the OSM, and independently reruns EnergyPlus.

The original evaluator returned `True` in the target image after the final rebuild. The 18 collected GT files were downloaded through the environment API and matched their remote SHA-256 values 18/18 before being copied into `ground_truth`.

## Cleanup

After collection and validation, task-specific files staged on the Desktop and task-specific runtime directories are removed. The base image files and installed applications are left unchanged.
