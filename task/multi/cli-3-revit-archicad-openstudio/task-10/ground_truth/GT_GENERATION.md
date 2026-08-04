# Ground-truth generation notes

This case uses the pinned Revit 2025, Archicad 27 build 6000, OpenStudio 3.10.0,
and EnergyPlus 25.1.0 workflow recorded in `native_stage_log.json`. Its
case-specific IFC spaces are `RECEPTION-L1` (45.24 m2), `STUDIO-L2` (45.24 m2), `ARCHIVE-L3` (45.24 m2), totaling 135.72 m2. Each space
has geometry, storey containment, base quantities, and an
`EngiWorld_EnergyHandoff` property set; Archicad retains the space GlobalIds.

Run the supplied stages in order on the Windows task image:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

The OpenStudio converter verifies `stage2.ifc` and the keyed Archicad handoff,
builds separate geometry, zones, loads, schedules, outdoor air, thermostats and
constructions, forward-translates `in.idf`, and runs an annual simulation. The
evaluator parses the IFC semantic graph, reconciles Archicad entity counts,
opens standard EnergyPlus SQLite tables, checks zone areas and reported energy,
and reruns `in.idf` independently. Ground-truth validation returned `True` with
no errors.
