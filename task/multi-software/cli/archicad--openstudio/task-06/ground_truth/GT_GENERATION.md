# Task 06 ground-truth generation record

This record applies only to `multi-cli-2-archicad-openstudio-task-06-windows` on snapshot `cli2-archicad27-openstudio310-win`. The checked-in artifacts were generated in that instance; this audit only reran the evaluator on fresh copies.

Archicad stage used IFC Command Server version `27.0.0 R1 (6000)`, executable SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`, from `2026-08-12T08:29:57.8721291+00:00` through `2026-08-12T08:29:59.3948286+00:00` in `C:\EW06`. Init hash is `8169323b872a16966099d9dbf21986637a2cdcab2dc247c09359b0dbb691a25c`; stage1 is `c7cd05711eb4edb12fee98eed454a52c02716e6ae19e9952118a1d9de41f1d8b`; handoff is `e9a34ffdec47aba183cc432f8fc8b48462b6f4fd8d7fafea43619b71f7d5edbe`. Seed roots are preserved and four opening roots are added: three named doors and PLAYROOM-DAYLIGHT-WINDOW. The handoff maps PLAYROOM, SICK-BAY, CALM-ROOM, STAFF-SUPPORT to four 22.5 square metre zones with revision EW2A06.

OpenStudio 3.10.0 executable SHA-256 is `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`. The model has four spaces/zones, 24 surfaces, four subsurfaces, sick-bay low occupancy, calm-room comfort schedule, conservative thermostats, and staff-supervised support semantics. The native workflow ran `2026-08-12T08:58:04.7763969+00:00` through `2026-08-12T08:58:14.3087834+00:00`, exit 0, using EnergyPlus `25.1.0-1c11a3d85f`, executable SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`. SQL integrity is `ok`; all 24 report-bound series have 8760 rows and distinct TimeIndexes; ERR/END report 11 warnings and zero severe errors. Simulation and native postprocess transaction JSON files bind the delivered hashes.

The formal candidate boundary is the 12 instruction-facing staged artifacts. The standalone simulation transaction duplicates `flow_report.json.openstudio_cli_transactions[0]` exactly; the postprocess transaction and its Python/Ruby files bind this GT's particular implementation rather than an instruction-level result. All four are retained as generation evidence but are not candidate-required. The evaluator reads the embedded simulation transaction, verifies its executable/output bindings, and independently recomputes model-summary values from SQL.

`BOUNDARY_REVALIDATION.json` records isolated helper-free and missing-native-evidence cases after this correction. The helper-free candidate passes; deleting the embedded OpenStudio transaction evidence is rejected. Native GT artifacts were unchanged.

Version-specific sources (all HTTP 200 during audit):

- https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_thermal_zone.html
- https://raw.githubusercontent.com/NREL/EnergyPlus/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc

The unrelated Revit source was removed.
