# Task 06 instance cleanup record

Cleanup was restricted to `EW_AUDIT_TASK06_*` paths on snapshot `cli2-archicad27-openstudio310-win`. The pre-run probe at `2026-08-12T19:20:05.412786+00:00` found no matching paths.

The first local case build failed on a BOM before any evaluator run; its uploaded `EW_AUDIT_TASK06_INPUT` contained only unmodified copies and was never executed. A clean v2 prefix was then used. Cleanup ran from `2026-08-12T19:24:20.257212+00:00` through `2026-08-12T19:24:20.288915+00:00` and removed the old input, v2 input, and v2 run directory, three paths total, with zero failures.

An independent probe at `2026-08-12T19:24:21.088480+00:00` found zero matching paths, processes, and related listening ports; `zero_residual=true`. No task-07-or-later path or generic Desktop content was targeted.

The v2 machine receipt SHA-256 is `97b0971bdff90544ff90cd9296cccec2be95c3ec1b50b23cae19ae9dff90b1e6`.

The 2026-08-14 candidate-boundary revalidation used two independently created local `/tmp/ew06-boundary.*` copies only and did not reconnect to the Windows instance. After recording `BOUNDARY_REVALIDATION.json`, the resolved temporary root was moved to macOS Trash. No evaluator output, bytecode/cache, or SQLite sidecar remains under task-06.
