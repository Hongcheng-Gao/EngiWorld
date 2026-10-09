# Task-10 cleanup record

This record is finalized after the r2 formal, alternate-equivalent, and 13-case isolated matrix runs. Cleanup uses `task_config/cleanup_task.py`, whose targets are limited to the task-10 Desktop artifact allowlist, `C:\EW10*` task directories, evaluator disposable `ew10-*` roots, and `Documents\ew10-*` scripts, logs, and archives.

## 2026-08-12 timestamp revalidation cleanup

The pre-run probe at `2026-08-12T20:12:04.1200756Z` found zero `EW_AUDIT_TASK10_*` paths. Cleanup from `2026-08-12T20:18:11.0886207Z` through `2026-08-12T20:18:11.1516181Z` removed exactly the task-10 audit input and run roots with zero failures. The independent probe at `2026-08-12T20:18:32.9899021Z` found zero matching paths, zero Archicad/OpenStudio/EnergyPlus processes, and zero port-12347 listeners; `zero_residual=true`. No task-09 or unrelated Desktop content was targeted.

The independent verification checks:

- task Archicad IFC Command Server, OpenStudio, and EnergyPlus processes;
- the task listener on port 12347;
- `C:\EW10*`, `C:\ew10-*`, the task Desktop allowlist, and `Documents\ew10-*` residual paths.

The first r2 cleanup ran at `2026-08-12T18:21:57.203139+00:00`, removed 28 paths, and had zero failures. The independent probe found six specifically named r2 stdout/stderr/PID files. Those exact names were added to the allowlist; the second pass at `2026-08-12T18:22:45.353774+00:00` removed seven paths (the six records and cleanup script) with zero failures.

The final independent read-only verification at `2026-08-12T18:23:00.501267+00:00` found zero task processes, zero listeners on port 12347, zero `C:\EW10*`/`C:\ew10-*` roots, zero task Desktop artifacts, and zero `Documents\ew10-*` paths. The cleanup did not target unrelated task state or generic Desktop baselines.

The 2026-08-14 candidate-boundary revalidation used two independently created local `/tmp/ew10-boundary.*` copies only and did not reconnect to the Windows instance. After recording `BOUNDARY_REVALIDATION.json`, the resolved temporary root was moved to macOS Trash. No evaluator output, bytecode/cache, or SQLite sidecar remains under task-10.
