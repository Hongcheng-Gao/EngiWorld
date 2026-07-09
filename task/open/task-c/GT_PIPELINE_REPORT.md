# CAE Open-Choice GT Pipeline Report

Generated on 2026-07-04 for `task/task-c/cae-commercial-open-choice`.

## Implemented

- Added `tools/cae_open_choice_gt_pipeline.py`.
- Added the planned per-task layout:
  - `ground_truth/abaqus/`
  - `ground_truth/ansys/`
  - `ground_truth/generation/`
  - `ground_truth/validation/`
- Bootstrapped existing `source_original` artifacts into the original solver branch:
  - `task-01` through `task-10`: Abaqus `.cae/.odb` plus `metrics.json` and `GT_MANIFEST.json`.
  - `task-11` through `task-20`: ANSYS `.db/.rst/.rth/.wbpj` as applicable plus `metrics.json` and `GT_MANIFEST.json`.
- Implemented remote OSWorld operations against `http://124.174.37.103:5000`:
  - upload local files to `C:\Users\user\Desktop`
  - launch long-running PowerShell jobs without blocking `/setup/execute`
  - poll done files
  - download artifacts through `/file`
  - validate each solver variant independently
  - run negative checks

## Commands Used

```bash
python3 tools/cae_open_choice_gt_pipeline.py --mode bootstrap-existing --tasks 1-20 --force
python3 tools/cae_open_choice_gt_pipeline.py --mode validate --tasks 1 --solvers abaqus --remote-timeout 600
python3 tools/cae_open_choice_gt_pipeline.py --mode validate --tasks 11 --solvers ansys --remote-timeout 600
python3 tools/cae_open_choice_gt_pipeline.py --mode negative --tasks 1 --remote-timeout 300
```

## Representative Validation Results

- `task-01/abaqus`: failed current eval.
  - Eval detail: Abaqus branch ran, but checker reported `field has no numeric data: U`.
  - Local evidence: `task-01/ground_truth/validation/abaqus/`.
- `task-11/ansys`: failed current eval.
  - Eval detail: PyMAPDL failed to create a gRPC client; MAPDL process died before connecting to `127.0.0.1:50052`.
  - Local evidence: `task-11/ground_truth/validation/ansys/`.
- Negative checks for `task-01` passed:
  - empty Desktop -> `False`
  - `metrics.json` only -> `False`

## Current Blockers

- Generic ANSYS generation is implemented but not yet usable on this remote host:
  - `ANSYS261.exe -b` and `MAPDL.exe -b` both started a process but did not produce a log or native result artifact before manual termination.
  - The ANSYS eval branch also fails via PyMAPDL gRPC startup, so this appears to be an ANSYS launch/runtime configuration issue on the remote machine, not only an APDL input issue.
- Full alternative-solver GT generation should be resumed after MAPDL batch startup is fixed, likely by calibrating the required product/license flags or PyMAPDL launch arguments for this Windows image.

## Notes

- The generated `metrics.json` files contain all required numeric fields because the current eval checks field presence before inspecting solver artifacts. The solver-native artifacts remain the actual evidence used by eval.
- Existing `source_original` files were not modified.
