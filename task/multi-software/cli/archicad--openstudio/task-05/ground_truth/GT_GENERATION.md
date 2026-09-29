# Task 05 native ground-truth regeneration

This record applies only to `multi/cli-2-archicad-openstudio/task-05` on snapshot `cli2-archicad27-openstudio310-win`. The repair was performed on 2026-08-22 in the real Windows instance. No artifact from another Task or offline industrial-output substitute was used.

## Defect repaired

The old `stage1.ifc` contained native `Qto_SpaceBaseQuantities/NetFloorArea` values of 96, 16, and 12 square metres for `MAIN-STUDIO`, `STORAGE`, and `FINISHING-BOOTH`. The old handoff, OSM, flow report, and model summary instead used 31.78, 15.44, and 27 square metres. Because Stage 2 is required to consume the Archicad handoff derived from `stage1.ifc`, this was a real cross-stage conflict rather than a missing-detail preference.

The repaired evaluator now verifies both links explicitly:

- each handoff area must equal the matching IFC `NetFloorArea` quantity;
- each OSM floor polygon area must equal the matching handoff area.

## Stage 1: Archicad 27

The formal seed hash remained `6ea42757b6dfc875df89ab031f470e12c9511e8f412f00ddf742d3aa87f07b46`. The real instance ran `IFCCommandServerApp.exe` version `27.0.0 R1 (6000)`, executable SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`.

From `2026-08-22T22:10:55.0064159+08:00` through `2026-08-22T22:10:56.1370167+08:00`, `archicad_replay.ps1` executed exactly 12 native JEMI transactions: load the formal seed; rename the three target spaces; set the project revision; create `BOOTH-DOOR` and `HIGH-VENT-WINDOW`; query and update storey containment with the current `Entity.Create` references; verify both openings; and save `stage1.ifc`. All 27 seed IfcRoot GlobalIds were preserved and only the two requested opening GlobalIds were added.

The native outputs are:

- `stage1.ifc`: SHA-256 `d86146fa75a1b93b1568a5990400d362d3e29f06edbc4f69bb45e1a3547ab710`;
- `handoff.json`: SHA-256 `44f980d4aaed1bcb8487ac83f6caeb34d5ba77c0c1c2082923962a793833bed0`;
- `native_stage_log.json`: SHA-256 `7fb4b5016c9ca303b872fd5874667f37121c87fe3c070f224a4d16ac58b9c8e8`.

The handoff areas are 96, 16, and 12 square metres, for a target-space total of 124 square metres.

## Stage 2: OpenStudio 3.10 and EnergyPlus 25.1

The real instance used OpenStudio CLI 3.10.0, executable SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`, and EnergyPlus 25.1.0, executable SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`.

The OpenStudio Ruby API rebuilt all 18 Surface vertex sets from the IFC-derived areas while retaining a 4.5 m depth and 3.0 m height. The resulting X boundaries are 0, 21.333333333333332, 24.888888888888886, and 27.555555555555554 m. It restored the two reciprocal interior boundaries, repositioned the booth door and high vent window strictly inside the booth south wall, preserved the main-studio daylight window, and updated the building/space AdditionalProperties with current stage hashes and areas.

The final native simulation ran from `2026-08-22T14:23:09.1993896Z` through `2026-08-22T14:23:17.6201578Z`. OpenStudio exited with code 0. Six successive samples reported stable SQL/ERR/END sizes and timestamps. EnergyPlus reported `11 Warning; 0 Severe Errors`; the SQL is 9,850,880 bytes, passes `PRAGMA integrity_check`, and contains 19 required hourly series with 8,760 unique time indexes each.

Final key hashes are:

- `result.osm`: `e6a8dc9f9423d6e0117122fc8578503c3474365e51d04ff23d3c2343869373de`;
- `run/eplusout.sql`: `a10484538de94b4f234da32ca2d6da7da3eb43c775523ea0d8fa20af459151ff`;
- `flow_report.json`: `445cad79ca47841045707909e7eee1296004e8bc6e59b6b4e7cf74c13d0cfceb`;
- `model_summary.csv`: `420b30aaf886e8a7179b8cba9a1081ea035181dd6e5b89f89ea0bf1c6a6af7de`.

The formal evaluator returned `True` in the instance and again from the downloaded bytes. `EVAL_MATRIX.json` records an independently copied five-case matrix: formal and JSON-key-order-equivalent candidates pass; old handoff areas, OSM floor-area mismatch, and a fake OSM fail.

## Reproduction assets

- `archicad_replay.ps1` is the exact Stage-1 replay script used for the successful native run.
- `openstudio_postprocess.rb` is the exact OpenStudio script used for the successful native run; its hash is bound by `openstudio_postprocess_transaction.json`.
- `openstudio_postprocess.py` is the exact SQL-driven postprocessor used by that run.
- `openstudio_base_result.osm` preserves the same-Task pre-repair native OpenStudio model used as the Stage-2 API baseline; it is a generation input, not a candidate output.
- `openstudio_rebuild_hardened.rb` is the post-run reproducibility wrapper. It reads that named baseline, locks the current repository evaluator bytes, and writes the candidate `result.osm`.

The evaluator uploaded for the instance run had SHA-256 `5f9726ae717326acba8d483b812ae187afc1923d91815040b82271cd3087b53e`; the repository copy was subsequently normalized from mixed Windows line endings to LF and has SHA-256 `e0a3ee68b776042af08fc37d525c5975e95cc39d9f2b3720f0501c685fcda0b9`. Its Python tokens and behavior are unchanged. The exact executed Ruby script binds the uploaded hash, while the hardened replay script binds the normalized repository hash.

## Official sources checked

- Archicad 27 IFC data conversion, base quantities, containment, and space boundaries: https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-42.htm
- Archicad JSON Interface command/response format and SI-unit handling: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0 AdditionalProperties API: https://openstudio-sdk-documentation.s3.amazonaws.com/cpp/OpenStudio-3.10.0-doc/model/html/classopenstudio_1_1model_1_1_additional_properties.html
- OpenStudio 3.10.0 release: https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- EnergyPlus 25.1 Ideal Loads Air System: https://bigladdersoftware.com/epx/docs/25-1/engineering-reference/ideal-loads-air-system.html
- EnergyPlus 25.1 zone equipment, including `Fan:ZoneExhaust` and `ZoneHVAC:IdealLoadsAirSystem`: https://bigladdersoftware.com/epx/docs/25-1/input-output-reference/group-zone-equipment.html
