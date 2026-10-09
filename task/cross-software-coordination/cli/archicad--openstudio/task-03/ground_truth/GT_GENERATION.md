# Task 03 ground-truth generation record

## Scope and native provenance

This record applies only to `multi-cli-2-archicad-openstudio-task-03-windows` on snapshot `cli2-archicad27-openstudio310-win`. The checked-in native artifacts were generated in that Windows instance. The 2026-08-12 audit reran the evaluator on fresh copies; it did not regenerate or alter the formal native artifacts.

Stage 1 used Archicad 27 IFC Command Server `C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe`, product version `27.0.0 R1 (6000)`, SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`. The recorded stage ran from `2026-08-11T18:09:57.7017030+00:00` through `2026-08-11T18:11:37.5927277Z` in task-specific database `C:\EW03`.

The init IFC SHA-256 is `02ab8c2df6a8c458f86c70116caf4eb1b6973c733a9ec89a4384ecf0ffd5eb3f`; stage1 IFC is `db5904b9fc8e19c37e1419e4ddda7b943376ee96504bb1468d246dccbbf3163e`; handoff is `7032aebb4b2504096101d56d183d14d73a6b6fc3c6111b1e6c12798b91328179`. All 52 seed IfcRoot GlobalIds are preserved. The four GlobalId-specific renames are G-READING -> READING, 1-GALLERY -> GALLERY, 1-STUDY-1 -> QUIET-POD-01, and 1-STUDY-2 -> QUIET-POD-02. The seed counts remain 7 spaces, 2 storeys, 2 slabs, 1 roof, 1 stair, and zero walls, doors, windows, and openings; revision is `EW2A03`.

Stage 2 used OpenStudio `3.10.0+86d7e215a1` at `C:\openstudio-3.10.0\bin\openstudio.exe`, SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`. The OSM contains four Space/ThermalZone pairs totaling 81 square metres, 26 surfaces, zero subsurfaces, four each of People, Lights, ElectricEquipment, outdoor-air specifications, thermostats, and ideal-load systems. Both quiet pods share matched interior surfaces with GALLERY, use lighting densities below READING and GALLERY, and have different effective Monday-Friday reservation profiles.

The weather-period output was produced through the OpenStudio workflow with EnergyPlus build `25.1.0-1c11a3d85f`, executable SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`. The final recorded delivery transaction ran from `2026-08-11T18:55:54.4994178+00:00` through `2026-08-11T18:56:00.6544012+00:00`, exit code 0. SQLite integrity is `ok`; all 24 required hourly series have 8760 distinct hourly TimeIndexes; ERR/END report 10 warnings and 0 severe errors. As recorded in the report, the exact 25.1 build exposes `FALSE/FALSE` Simulations flags despite the successful native exit and complete stable outputs; those flags are accepted only with the surrounding native and annual-series evidence.

## Candidate boundary

The formal candidate surface remains exactly 12 artifacts: `init.ifc`, `stage1.ifc`, `handoff.json`, `native_stage_log.json`, `result.osm`, `workflow.osw`, `weather.epw`, `flow_report.json`, `model_summary.csv`, `run/eplusout.sql`, `run/eplusout.err`, and `run/eplusout.end`. Audit documents and `gt_manifest.json` are repository provenance only and are not candidate-required files or task uploads.

## Version-specific official sources

- Archicad 27 IFC guide: https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- Graphisoft JSON interface documentation used by the Archicad 27 command-server stage: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0 `Space`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- OpenStudio 3.10.0 `ThermalZone`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_thermal_zone.html
- EnergyPlus 25.1 API source: https://raw.githubusercontent.com/NREL/EnergyPlus/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc (relevant finalization block: lines 358-398)

All five version-specific URLs returned HTTP 200 during this task-specific audit on 2026-08-12 UTC.
