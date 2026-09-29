# Task 04 ground-truth generation record

## Scope and native provenance

This record applies only to `multi-cli-2-archicad-openstudio-task-04-windows` on snapshot `cli2-archicad27-openstudio310-win`. The native artifacts were generated in that Windows instance. The 2026-08-12 audit reran the evaluator against fresh copies; it did not regenerate or modify the formal native artifacts.

Stage 1 used Archicad 27 IFC Command Server `C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe`, version `27.0.0 R1 (6000)`, SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`. The recorded stage ran from `2026-08-12T03:59:47.8423429+00:00` through `2026-08-12T03:59:49.1928232+00:00` in task database `C:\EW04R2`.

The init IFC SHA-256 is `86995fe99436f189809f7db46a7132df388cc8ba8769200e9422c8c3468a61f5`; stage1 IFC is `4565f535fe661a5385c5a4e0ec0a66df0c417dce2d857a8f12aea250d8c66e81`; handoff is `7b03499e8f5a0013a05a44c6fd9cdd304dfc470afc8d0393db2c2e7c0716c4ec`. Stage 1 preserves the shell counts of 6 spaces, 24 walls, 1 slab, 4 roofs, zero windows/openings, renames GlobalIds `1G6nPejgHAEO7LI0O2lCv8` and `1rAy78PnX5mP3F_rPXF0GL` to WORKSHOP and PARCEL-PICKUP, adds SERVICE-DOOR GlobalId `2vgFqpPvP2Qht3q6cPN$C_` with 1.0 m by 2.1 m dimensions and task-specific containment, and records revision `EW2A04`.

Stage 2 used OpenStudio `3.10.0+86d7e215a1` at `C:\openstudio-3.10.0\bin\openstudio.exe`, SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`. The OSM contains the 30 square metre WORKSHOP and 16 square metre PARCEL-PICKUP spaces with distinct zones, 12 surfaces, one SERVICE-DOOR subsurface, two each of People/Lights/ElectricEquipment/outdoor-air/thermostat/ideal-load objects, and one positive parcel-pickup infiltration object. Parcel-pickup total design lighting is lower than workshop lighting.

The final OpenStudio workflow transaction ran from `2026-08-12T05:35:57.126995+00:00` through `2026-08-12T05:36:05.898680+00:00`, exit code 0. It used EnergyPlus build `25.1.0-1c11a3d85f`, executable SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`. The SQL has 12 required series, each with 8760 rows and 8760 distinct TimeIndexes; ERR/END report 10 warnings and 0 severe errors.

## Candidate boundary

The formal candidate surface remains exactly 12 artifacts: `init.ifc`, `stage1.ifc`, `handoff.json`, `native_stage_log.json`, `result.osm`, `workflow.osw`, `weather.epw`, `flow_report.json`, `model_summary.csv`, `run/eplusout.sql`, `run/eplusout.err`, and `run/eplusout.end`. Audit documents and the manifest are repository provenance only; task config uploads only init and evaluator postconfig uploads only eval.

## Version-specific official sources

- Archicad 27 IFC guide: https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- Graphisoft JSON interface documentation used by the Archicad 27 stage: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0 `Space`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- OpenStudio 3.10.0 `ThermalZone`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_thermal_zone.html
- EnergyPlus 25.1 API source: https://raw.githubusercontent.com/NREL/EnergyPlus/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc

All five URLs returned HTTP 200 during this task-specific audit on 2026-08-12 UTC. The unrelated Revit link formerly present in task source was removed.
