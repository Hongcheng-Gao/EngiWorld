# Task 02 ground-truth generation record

## Scope and provenance

This record applies only to `multi-cli-2-archicad-openstudio-task-02-windows` on snapshot `cli2-archicad27-openstudio310-win`. The checked-in native artifacts were generated in that Windows instance; the 2026-08-12 audit reran the evaluator against fresh copies and did not regenerate or alter those native artifacts.

Stage 1 used `C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe`, product version `27.0.0 R1 (6000)`, SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`. The recorded native stage ran from `2026-08-11T15:04:47.0137851+00:00` through `2026-08-11T15:05:12.9378205Z`. Its successful JSON-RPC records load `init.ifc`, rename only IfcSpace GlobalId `0V92O_gT1AyODVhuvEhgNC` from `CONSULT-1` to `CONSULT`, add project revision `EW2A02`, and save `stage1.ifc`.

The seed and stage-1 IFC contain the same 95 IfcRoot GlobalIds. The seed is the nine-space L-shaped clinic; the relevant preserved counts are 9 spaces, 36 walls, 2 slabs, 2 roofs, 1 door, and 0 windows. The seed hash is `d789e6dad3d9b817036a0e90ee39c9b814a1de0301ab72123a105888935d94da`; the stage-1 hash is `843c2e94b1e1ac3aaf66211423333653e1fc5434719b9875a8d5aebe785b7730`; the derived handoff hash is `b78296aa47cb9e7e0309605d94887883ca77dfa02280be36fb736a8c1df62cfa`.

Stage 2 used `C:\openstudio-3.10.0\bin\openstudio.exe`, version `3.10.0+86d7e215a1`, SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`. The OSM contains exactly the required WAITING/WAITING-ZN and CONSULT/CONSULT-ZN Space/ThermalZone pairs, areas 12 and 9 square metres, closed shells, reversed matched interior surfaces and separating-door subsurfaces, distinct weekday occupancy profiles, and linked loads, outdoor air, thermostats, constructions, and ideal loads.

The weather-period run was performed with EnergyPlus `25.1.0-1c11a3d85f` at `C:\openstudio-3.10.0\EnergyPlus\energyplus.exe`, SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`. The final direct verification run began `2026-08-11T15:41:12.318151+00:00` and completed `2026-08-11T15:41:15.302429+00:00`, exit code 0. SQLite integrity is `ok`; all 12 required hourly series contain 8760 rows; ERR and END say 10 warnings and 0 severe errors. The SQL's observed `Simulations.Completed` and `CompletedSuccessfully` values are both `FALSE`; acceptance is tied to this exact 25.1 build plus native exit, stable files, successful ERR/END, annual environment, and complete series evidence, not to those flags alone.

## Deliverables and dependency chain

The formal candidate surface remains exactly these 12 files: `init.ifc`, `stage1.ifc`, `handoff.json`, `result.osm`, `workflow.osw`, `weather.epw`, `run/eplusout.sql`, `run/eplusout.err`, `run/eplusout.end`, `native_stage_log.json`, `flow_report.json`, and `model_summary.csv`. The dependency chain is seed IFC -> Archicad stage IFC -> handoff -> OpenStudio model/workflow/weather -> EnergyPlus outputs -> report and summary. Audit documents and the manifest are not candidate requirements and are not uploaded by task config.

## Version-specific official sources

- Archicad 27 IFC guide: https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- Graphisoft JSON interface documentation used by the Archicad 27 command-server stage: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0 `Space`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- OpenStudio 3.10.0 `ThermalZone`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_thermal_zone.html
- OpenStudio 3.10.0 `ZoneHVACIdealLoadsAirSystem`: https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_zone_h_v_a_c_ideal_loads_air_system.html
- EnergyPlus 25.1 API finalization source: https://raw.githubusercontent.com/NREL/EnergyPlus/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc (relevant finalization block: lines 358-398)

All six URLs returned HTTP 200 during the task-specific audit on 2026-08-12 UTC.
