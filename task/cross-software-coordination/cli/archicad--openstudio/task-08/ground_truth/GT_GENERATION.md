# Task-08 Ground Truth Generation

This directory records one valid native implementation of the instruction. It is not a reference-answer template: alternative GUIDs, areas, opening layouts, load values, and schedule profiles are valid when they satisfy the instruction and all cross-file/provenance checks.

## 2026-08-12 evaluator compatibility audit

The formal package, its four native reasonable-equivalent records, and both delivered OpenStudio transaction records use seven fractional-second digits emitted by Windows/.NET `DateTimeOffset`. Python `datetime.fromisoformat` rejected that native tick precision before reaching the existing strict time and hash checks. The evaluator now trims only fractional precision beyond Python's six microsecond digits, retaining timezone requirements, strict native execution ordering, stable sample size/hash/mtime checks, and postprocessor script hash checks. No IFC, OSM, SQL, report, script, transaction, or historical matrix timestamp was rewritten for this fix.

The unchanged package passes locally and in a fresh Windows formal run. A new six-case Windows revalidation, recorded in `EVAL_MATRIX.json`, confirms that JSON key order remains irrelevant while matrix time reversal, stable-sample hash corruption, postprocess time reversal, and Ruby script byte corruption are rejected.

## Candidate boundary correction

`gt_manifest.json`, `GT_GENERATION.md`, `CLEANUP.md`, `EVAL_MATRIX.json`, both standalone OpenStudio transaction records, and the three delivered generation/postprocessing scripts are repository generation evidence, not outputs requested from an evaluated candidate. The evaluator no longer requires or parses those files. It verifies the instruction-facing Archicad/OpenStudio artifacts directly, including the native process evidence embedded in `native_stage_log.json` and `flow_report.json`, workflow/weather bindings, and the EnergyPlus SQL/ERR/END outputs. The formal GT retains all generation evidence for reproducibility.

The boundary revalidation also exposed order-dependent recursive lookup of `door_count` and `window_count`: reordering top-level JSON keys could make the evaluator read a nested space count instead of the required report total. Those two checks now read the explicit top-level fields. The isolated matrix in `BOUNDARY_REVALIDATION.json` confirms that a helper-free formal candidate and reordered JSON pass while removal of embedded native transaction evidence is rejected.

## Native software

- Graphisoft Archicad 27.0.0 R1 build 6000, `IFCCommandServerApp.exe` SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`.
- OpenStudio CLI 3.10.0 SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`.
- Bundled EnergyPlus 25.1 SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`.

## Native sequence

1. Start the Archicad IFC command server with model `EW08`, database `C:\EW08`, schema alias `new_ifc4`, and port 12345.
2. Call `Model.LoadFile` for `C:\Users\user\Desktop\init.ifc`.
3. Use successful `Entity.Modify` calls for the selected space records and project revision metadata. Use `Entity.Create` for the selected doors/windows, update spatial containment, then call `Model.SaveFile` for `stage1.ifc`.
4. Derive `handoff.json` from the saved IFC. Full parameters, results, timestamps, executable identity, and artifact hashes are in `native_stage_log.json`.
5. Run `openstudio.exe C:\Users\user\Documents\ew08-build.rb`. The delivered equivalent source is `openstudio_build.rb`; it consumes `handoff.json`, creates the three named spaces and zones with schedules, loads, outdoor air, thermostats and Ideal Loads, saves `result.osm`, and writes `workflow.osw` and the initial flow report.
6. Run `openstudio.exe run -w C:\Users\user\Desktop\workflow.osw`. EnergyPlus completed the annual run with 10 warnings and 0 severe errors. Stable SQL/ERR/END samples and executable hashes are in `openstudio_simulation_transaction.json`.
7. Run `openstudio.exe C:\Users\user\Documents\ew08-post.rb`. It invokes the delivered SQL helper, recomputes all CSV energy and peak values from 18 hourly SQL series, and records `openstudio_postprocess_transaction.json`.

## Documentation sources

- Graphisoft Archicad JSON interface: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/ . The live page exposed version 29 during review, so command shape was cross-checked there while actual behavior and version binding came from the installed Archicad 27 executable and captured responses.
- OpenStudio 3.10 `ZoneHVACIdealLoadsAirSystem` API: https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_zone_h_v_a_c_ideal_loads_air_system.html
- OpenStudio CLI reference: https://nrel.github.io/OpenStudio-user-documentation/reference/command_line_interface/
- IFC space definition: https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcSpace.htm

Artifact roles and hashes are machine-readable in `gt_manifest.json`.
