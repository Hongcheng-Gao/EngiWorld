# Task-08 Instance Cleanup

Cleanup was performed after the local isolated evaluator and the Windows-side evaluator both returned `ok=true` with no errors.

## 2026-08-12 time-compatibility revalidation

The new audit is restricted to Desktop paths named `EW_AUDIT_TASK08_*` on snapshot `cli2-archicad27-openstudio310-win`. The pre-run probe at `2026-08-12T19:43:52.4428542Z` found zero matching paths.

Cleanup ran from `2026-08-12T19:47:41.3964968Z` through `2026-08-12T19:47:41.4594114Z`. It removed exactly `EW_AUDIT_TASK08_INPUT_V2` and `EW_AUDIT_TASK08_RUN_V2_20260812T194509778921Z`, with zero failures. An independent probe at `2026-08-12T19:47:52.6017383Z` found zero matching paths, zero related processes, and zero related listening ports; `zero_residual=true`. The probe excluded its own process and parent. No task-09-or-later path or generic Desktop content was targeted. The Windows receipt SHA-256 is `10d010554655afc7f817c565f3ef959a57b5f0f1de5294dc48b0297b078e0fd1`.

Removed task-created paths included the Desktop seed/stage/handoff/model/report/workflow/weather/transaction/evaluator files and `run` directory; Documents scripts `ew08-native.ps1`, `ew08-build.rb`, `ew08-sim.ps1`, `ew08-post.py`, and `ew08-post.rb`; database `C:\EW08`; and temporary `C:\EW08-package.zip` and `C:\EW08-package-final.zip`.

After the final isolated Windows matrix, `C:\EW08-VERIFY` was removed recursively. It had contained only the uploaded matrix archive and six independent evaluator directories: formal, reasonable-equivalent, manifest tamper, missing Ideal Loads, shared schedule, and contradictory SQL completion flags.

The final equivalence-boundary matrix used `C:\EW08-FINAL-MATRIX` for three independently rebuilt native variants and `C:\EW08-FINAL-RERUN` for the nine-case final evaluator run. After verification, both directories and the task-created Desktop/Documents variant scripts and artifacts were removed. The three native variants were alternate valid EPW metadata, one additional stage1-preserved space/zone, and zero OpenStudio windows; each was rerun through OpenStudio 3.10.0 and EnergyPlus 25.1 before evaluation.

The final provenance and set-closure audit used `C:\EW08-SCHEDULE-NATIVE` to rebuild the schedule-equivalent model and rerun OpenStudio 3.10.0, EnergyPlus 25.1, and native postprocessing. `C:\EW08-11-FINAL` then held the fixed eleven-case package: five positives and six negatives, including unzoned-space and orphan-zone corruption. After the final formal check, both directories and their task-created Desktop/Documents working files were removed.

The exact post-clean PowerShell result was:

```json
{"remaining":[],"processes":[],"port12345":[]}
```

Local evaluator outputs and `__pycache__` files under task-08 were also removed. Task-09 was not started.
