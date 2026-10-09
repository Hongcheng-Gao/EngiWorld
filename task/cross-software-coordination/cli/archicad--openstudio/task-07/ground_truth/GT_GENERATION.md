# Task 07 ground-truth generation record

This record applies only to `multi-cli-2-archicad-openstudio-task-07-windows` on snapshot `cli2-archicad27-openstudio310-win`. The delivered IFC, OSM, simulation, reports, scripts, and transaction records were generated in that Windows instance. This audit did not rewrite any ground-truth artifact to cure the formal failure.

The Archicad stage used IFC Command Server version `27.0.0 R1 (6000)`, executable SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`. Init SHA-256 is `41ddc5e8676624a8bd7612e0b01f4bfd9a472e142bd04e99b7bdc835ac54f5b9`; stage1 is `bf3db9092469b249f26687fd9f7e732b8127335a695b451e615e0fe4270a7c1d`; handoff is `bbc7f36bac97f7e7acda32bc0280aebd1fb742be69b9fa5be14340672198f834`. The native log binds the seed load, three space renames, revision metadata, four openings, containment update, and stage1 save.

The OpenStudio stage used OpenStudio 3.10.0 executable SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361` and EnergyPlus 25.1 executable SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`. The simulation transaction records six stable samples and binds the delivered OSM, OSW, EPW, SQL, ERR, and END hashes. The postprocess transaction binds the native Ruby script, Python helper, result OSM, flow report, model summary, and SQL hashes.

The pre-fix formal evaluator rejected two valid native transaction records because Python `datetime.fromisoformat` cannot parse the seven fractional-second digits emitted by Windows/.NET `DateTimeOffset`. The evaluator now truncates only fractional precision beyond Python microseconds before parsing, while retaining timezone, strict ordering, stable size/hash/mtime checks, and both script hash checks. With all ground-truth bytes unchanged, the fixed evaluator passes locally and on Windows.

The later candidate-boundary review found that the standalone simulation transaction duplicates `flow_report.json.openstudio_cli_transactions[0]` exactly, while the postprocess transaction and its Python/Ruby scripts identify only this GT's chosen implementation. They are retained as generation evidence but no longer required from candidates. The evaluator now validates the embedded OpenStudio execution record and recomputes CSV energy/peak values from SQL without comparing GT-specific script names or hashes. `BOUNDARY_REVALIDATION.json` confirms that a helper-free candidate passes and removal of embedded native execution evidence is rejected.

Version-specific sources, each returning HTTP 200 during this audit:

- https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_space.html
- https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_thermal_zone.html
- https://raw.githubusercontent.com/NREL/EnergyPlus/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc

The unrelated Revit source was removed.
