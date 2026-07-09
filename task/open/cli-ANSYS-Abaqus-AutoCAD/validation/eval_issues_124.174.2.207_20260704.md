# Eval issues for 124.174.2.207 on 2026-07-04

Remote: `124.174.2.207:5000`

Scope:
- `task-01` to `task-10`: existing `abaqus` GT variants only.
- `task-11` to `task-20`: existing `ansys` GT variants only.
- Negative checks: `task-01` empty desktop and metrics-only cases.

Run artifacts:
- Abaqus validation: `validation/runs/124.174.2.207_20260704-173807_validate/`
- ANSYS validation before license pre-run: `validation/runs/124.174.2.207_20260704-174019_validate/`
- ANSYS validation with license pre-run and robust cleanup: `validation/runs/124.174.2.207_20260704-184612_validate/`
- ANSYS validation after thermal `.rth` packaging fix: `validation/runs/124.174.2.207_20260704-190635_validate/`
- Full Abaqus+ANSYS matrix after evaluator/generator fixes: `validation/runs/124.174.2.207_20260704-201518_validate/`
- Negative checks: `validation/runs/124.174.2.207_20260704-174931_negative/`

Top-level reports:
- `validation/remote_eval_124.174.2.207_20260704-173807_validate.md`
- `validation/remote_eval_124.174.2.207_20260704-174019_validate.md`
- `validation/remote_eval_124.174.2.207_20260704-184612_validate.md`
- `validation/remote_eval_124.174.2.207_20260704-190635_validate.md`
- `validation/remote_eval_124.174.2.207_20260704-201518_validate.md`
- `validation/remote_eval_124.174.2.207_20260704-174931_negative.md`

## Summary

- Abaqus branch: 0/10 passed.
- ANSYS branch before running `license.py`: 0/10 passed.
- ANSYS branch after running `C:\Users\user\Desktop\license.py` before each task and cleaning MAPDL processes between tasks: 9/10 passed.
- ANSYS branch after removing the active thermal compatibility `.rst` from `task-20`: 10/10 passed.
- Final full matrix after adding missing alternative solver GT variants and fixing Abaqus evaluator checks: 40/40 passed.
  - Abaqus: 20/20.
  - ANSYS: 20/20.
- Negative checks: 2/2 passed.
- Cleanup: the final remote Desktop residual list was empty for the configured trace patterns. Robust cleanup now stops eval-owned ANSYS/MPI processes before removing artifacts.
- Manual probes were also run on the new image and cleaned afterward. Probe artifacts are saved under `validation/manual_inspect_124.174.2.207_20260704/`.

## Abaqus branch issues

Initial Abaqus validation failed 0/10 before evaluator fixes. After patching the Abaqus checker logic and adding generated Abaqus variants for `task-11` to `task-20`, the final full matrix passes 20/20 for Abaqus.

| Task | Status | Recorded reason |
| --- | --- | --- |
| task-01 | fail | `field has no numeric data: U` |
| task-02 | fail | `field has no numeric data: U` |
| task-03 | fail | `field has no numeric data: U` |
| task-04 | fail | `field has no numeric data: U` |
| task-05 | fail | `field has no numeric data: U` |
| task-06 | fail | `no load/predefined/interactions/constraints evidence found` |
| task-07 | fail | `field has no numeric data: U` |
| task-08 | fail | `span mismatch z obs=5.0 target=35.0 tol=3.5` |
| task-09 | fail | `field has no numeric data: U` |
| task-10 | fail | `field has no numeric data: U` |

Interpretation:
- The initial Abaqus failures were mixed evaluator/GT coverage issues rather than solver impossibility.
- Fixed evaluator issues:
  - ODB field data is now iterated by index instead of slicing `field.values[:50]`.
  - Thermal Abaqus models with valid temperature boundary conditions are accepted.
  - Geometry bbox checks prefer assembly instance nodes and fall back to part nodes.
- Added generated Abaqus noGUI variants for `task-11` to `task-20`.
- Generator fixes needed for Abaqus alternatives:
  - Heat-transfer steps use explicit `deltmx`.
  - Generated mesh size is coarser to stay under Abaqus Learning Edition's 1,000-node limit.
- Current final status: Abaqus passes 20/20 on the new image.

## ANSYS branch issues

Before running `C:\Users\user\Desktop\license.py`, all ANSYS validations failed before model/content checks because PyMAPDL could not create a working MAPDL gRPC client. Each task showed the same failure class:

`Failed to create MAPDL client: Unable to connect to MAPDL gRPC instance at dns:///127.0.0.1:50052. Reached either maximum amount of connection attempts (5) or timeout (45 s). The MAPDL process has died.`

After running `license.py` before each task and then fixing the active thermal artifact package for `task-20`:

| Task | Status | License | Class / reason |
| --- | --- | --- | --- |
| task-11 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-12 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-13 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-14 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-15 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-16 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-17 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-18 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-19 | pass | `license_ok`, `exitcode=0` | eval returned `True` |
| task-20 | pass | `license_ok`, `exitcode=0` | eval returned `True` |

Interpretation:
- The original ANSYS failure was license initialization related. Running `license.py` fixed PyMAPDL/MAPDL startup for most tasks.
- The first license-gated run exposed a cleanup issue: `task-11` left eval-owned ANSYS/MPI processes and `eval_open_choice_*` files, causing later tasks to fail on `C:\Users\user\Desktop\.__tmp__.inp`. The pipeline cleanup now stops matching eval-owned processes and removes `.__tmp__.*`.
- `task-20` originally failed after license initialization because its active ANSYS GT directory contained both `wb_conduction.rst` and `wb_conduction.rth`; the eval selected the `.rst` first and rejected it for a thermal task. The active GT package now excludes `wb_conduction.rst` and uses `wb_conduction.rth` as the thermal result artifact, while `source_original` still preserves the original compatibility copy for audit.
- Added generated ANSYS PyMAPDL variants for `task-01` to `task-10`; the old MAPDL batch generation path was replaced because it did not reliably execute the uploaded input file on this image.
- Current final status: ANSYS passes 20/20 on the new image.

## Negative checks

- `task-01/empty_desktop`: passed; eval returned `False`.
- `task-01/metrics_only`: passed; eval returned `False`.

This confirms the new image does reject the two representative invalid cases tested in this run.
