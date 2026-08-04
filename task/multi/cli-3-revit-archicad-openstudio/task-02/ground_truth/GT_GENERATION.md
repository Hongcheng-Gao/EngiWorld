# Ground-truth generation notes

The Revit 2025 and Archicad 27 intermediates were produced through the pinned
native stage entries recorded in `native_stage_log.json`. Revit retained the
37.24 m2 retail space and split the 17.64 m2 back-of-house bay into a 10.44 m2
prep kitchen and 7.20 m2 dry storage room. Every delivered space has geometry,
storey containment, base quantities, and an `EngiWorld_EnergyHandoff` property
set. Archicad retained all three space GlobalIds in its IFC4 export.

The workflow is reproducible on the Windows task image:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

The OpenStudio 3.10.0 converter verifies the `stage2.ifc` hash and each handed
off `IfcSpace` GlobalId, consumes the per-space load and outdoor-air fields,
creates three separate spaces and thermal zones, forward-translates `in.idf`,
and runs the bundled EnergyPlus 25.1.0 with `weather.epw`.

Validation with `eval.py` parsed the IFC semantic graph, compared the Archicad
entity report to the actual IFC, opened standard EnergyPlus SQLite tables,
cross-checked all zone areas and reported energy, and reran `in.idf`
independently. The result was `True` with no errors.
