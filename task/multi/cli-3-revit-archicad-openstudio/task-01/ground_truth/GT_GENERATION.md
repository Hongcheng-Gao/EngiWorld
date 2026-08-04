# Ground-truth generation notes

The Revit 2025 and Archicad 27 intermediates were produced on the pinned Windows
image through the native stage entries recorded in `native_stage_log.json`.
`stage1.ifc` contains the two named `IfcSpace` objects with geometry, storey
containment, base quantities, and energy handoff properties. Archicad imported
that file with the supplied IFC4 Reference View translator and exported
`stage2.ifc` while retaining both space GlobalIds.

The OpenStudio stage is reproducible with OpenStudio 3.10.0 and its bundled
EnergyPlus 25.1.0:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

The third command checks the `stage2.ifc` hash and each handed-off `IfcSpace`
GlobalId, builds two separate OpenStudio spaces and thermal zones, applies the
handed-off people, lighting, equipment, outdoor-air, thermostat, construction,
and weather assumptions, forward-translates the model to `in.idf`, and runs an
annual EnergyPlus simulation. The checked-in `run/eplusout.sql` is a standard
EnergyPlus SQLite database; `run/eplusout.err` records successful completion.

Validation was run with `eval.py` and `ENGIWORLD_ENERGYPLUS_EXE` pointing to
EnergyPlus 25.1.0. The evaluator parsed the IFC semantic graph with IfcOpenShell,
opened the standard EnergyPlus SQL tables, cross-checked zone areas and reported
energy, and reran `in.idf` independently. The result was `True` with no errors.
