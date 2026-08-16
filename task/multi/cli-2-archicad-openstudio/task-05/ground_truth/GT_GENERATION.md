# Task 05 ground-truth generation record

This record applies only to `multi-cli-2-archicad-openstudio-task-05-windows` on snapshot `cli2-archicad27-openstudio310-win`. The checked-in native artifacts were generated in that Windows instance; the 2026-08-12 audit only reran the evaluator against fresh copies.

Stage 1 used Archicad 27 IFC Command Server `C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe`, version `27.0.0 R1 (6000)`, SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`. It ran from `2026-08-12T05:58:25.3474394+00:00` through `2026-08-12T05:58:26.6343787+00:00` in `C:\EW05`. Init hash is `6ea42757b6dfc875df89ab031f470e12c9511e8f412f00ddf742d3aa87f07b46`; stage1 is `ff8b3e5f36605f80a53f68a95d0cfb918d555e1825b947df6c67c3f9d1e73e7d`; handoff is `a4f2b1f293aa077a1da744c0f9df1d449002bc024316578151301532eb4902ea`. Seed identities are preserved; BOOTH-DOOR and HIGH-VENT-WINDOW are the two added roots. Output counts are 5 spaces, 1 slab, 2 roofs, 1 door, 1 window, and zero walls/openings. Revision is `EW2A05`.

Stage 2 used OpenStudio 3.10.0 at `C:\openstudio-3.10.0\bin\openstudio.exe`, SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`. The OSM has MAIN-STUDIO, STORAGE, and FINISHING-BOOTH with separate zones and areas 31.78, 15.44, and 27.0 square metres; 18 surfaces; BOOTH-DOOR, HIGH-VENT-WINDOW, and the preserved main-studio daylight window; positive loads/outdoor air; linked thermostats and ideal loads; and a positive-flow finishing-booth zone exhaust fan. Geometry-derived window area, gross outdoor wall area, and WWR are recorded in flow_report.

The final OpenStudio workflow ran from `2026-08-12T06:04:43.3450897+00:00` through `2026-08-12T06:04:53.8420864+00:00`, exit code 0, with EnergyPlus `25.1.0-1c11a3d85f`, executable SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`. SQL integrity is `ok`; the report binds 19 hourly series, each with 8760 rows and distinct TimeIndexes. ERR/END report 11 warnings and 0 severe errors.

Native postprocessing was invoked with OpenStudio 3.10.0 from `2026-08-12T06:58:45.3998350Z` through `2026-08-12T06:58:46.1726430Z`, exit code 0. `openstudio_postprocess_transaction.json` binds the Ruby script hash, Python postprocessor hash, OSM/report/summary hashes, and native SQL hash.

The candidate surface is the 12 instruction-facing staged artifacts. `openstudio_postprocess_transaction.json`, `openstudio_postprocess.py`, and `openstudio_postprocess.rb` document how this GT was generated, but are not candidate outputs: requiring their GT-specific path and hashes would reject independently implemented valid postprocessing. The evaluator instead recomputes report/summary values from the delivered OSM and SQL and verifies native OpenStudio execution from `flow_report.json`'s embedded transaction, so removing those three helper files does not weaken the result or provenance checks.

`BOUNDARY_REVALIDATION.json` records two isolated local cases after this correction: a helper-free formal candidate passes, while removal of the genuine embedded OpenStudio execution evidence is rejected. Native IFC, OSM, EPW, SQL, ERR, END, report, and summary artifacts were not changed.

Version-specific official sources:

- https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_zone_h_v_a_c_ideal_loads_air_system.html
- https://raw.githubusercontent.com/NREL/EnergyPlus/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc

All five returned HTTP 200 during this task audit. The unrelated Revit source was removed.
