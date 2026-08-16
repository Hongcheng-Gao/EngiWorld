# Task-10 native ground-truth generation

The former six-file ground truth was replaced because its five areas were not present in the seed IFC and it had no auditable native simulation. The supplied seed is IFC4 with 94 IfcRoot entities, 12 spaces, 26 walls, one slab, three roofs, 12 doors, and eight windows.

## 2026-08-12 timestamp compatibility audit

The formal journal, RPC log, simulation transaction, and postprocess transaction use seven fractional-second digits emitted by Windows/.NET. Python rejected that tick precision before reaching the then-current causal checks. The compatibility repair trimmed only unsupported precision beyond Python microseconds; no GT artifact or native timestamp was changed.

The unchanged formal package passed locally and on Windows. The historical five-case Windows revalidation confirmed its timestamp parser and then-current journal/sidecar checks.

## 2026-08-14 candidate-boundary correction

The current candidate boundary contains 13 instruction-facing artifacts. `archicad_process_journal.json` is formal-runner observation evidence, while `openstudio_simulation_transaction.json` and `openstudio_postprocess_transaction.json` are receipts for this GT generation run. They are retained in ground truth for provenance but are not candidate-required, because their runner-specific schemas, timestamps, script names, and hashes are not instruction-level outcomes.

The evaluator continues to require and deeply inspect `native_stage_log.json`. In the Windows snapshot it independently replays Archicad 27 against the supplied seed, reruns OpenStudio 3.10 ForwardTranslator to verify canonical `in.idf`, and reruns EnergyPlus 25.1 to compare zones and all 30 hourly series. `BOUNDARY_REVALIDATION.json` records an isolated helper-free pass and rejection after true Archicad process/RPC evidence is removed. No native GT artifact was modified for this correction.

On the mapped Windows snapshot, Graphisoft Archicad 27.0.0 R1 build 6000 loaded the exact seed through the IFC Command Server, performed five successful space modifications plus one Project revision modification, and saved `stage1.ifc`. All 94 seed root identities and all building-product counts were preserved. `handoff.json` binds the five records to actual seed GlobalIds and actual `Pset_EngiWorld.Area` values: 14, 16, 14, 8, and 8 m2. No door or window is attributed to an individual target because the seed has no authoritative boundary, opening, or containment relationship supporting such attribution.

OpenStudio CLI 3.10.0 consumed that handoff and created five closed geometric spaces and five distinct thermal zones with separate occupancy schedules, people, lights, equipment, outdoor air, thermostats, and Ideal Loads. The installed SRRL annual EPW was bound to the model. OpenStudio's ForwardTranslator generated `in.idf`; the bundled EnergyPlus 25.1.0 ran the annual workflow successfully and produced SQLite output. The CSV was calculated from 30 hourly SQL series (six requested variables for each of five spaces), each with 8760 non-warmup rows.

The evaluator independently replays the candidate-declared valid Archicad target mapping in a disposable database, compares every seed root's direct attributes, OwnerHistory, product world geometry and host graph, reruns the OpenStudio ForwardTranslator, and reruns the full OpenStudio workflow in a disposable directory. A second full native run using alternate consultation targets and alternate flow metadata also passed. The 13-case isolated matrix accepts the formal output and rejects broken handoff state, invalid or duplicate IFC bindings, forged IFC area, false door/window attribution, offline IFC edits, missing Ideal Loads, patched IDF, same-sum/max hourly time reordering, Errors-table mutation, and completion-flag mutation.

The generation scripts used by a candidate are supplied from `init_file`; the evaluator is the only postconfig upload. Ground truth contains results and reproducibility records, not candidate authoring tooling.

Native software identities:

- Archicad IFC Command Server 27.0.0 R1 (6000), SHA-256 `594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775`
- OpenStudio CLI 3.10.0, SHA-256 `46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361`
- EnergyPlus 25.1.0-1c11a3d85f, SHA-256 `3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5`

Official research links are recorded in `REPAIR_CONTRACT.md` and the task `source` field.
