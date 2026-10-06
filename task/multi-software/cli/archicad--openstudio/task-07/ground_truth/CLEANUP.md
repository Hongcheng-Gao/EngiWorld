# Task 07 instance cleanup record

Cleanup is restricted to paths named `EW_AUDIT_TASK07_*` on snapshot `cli2-archicad27-openstudio310-win`. The pre-run probe at `2026-08-12T19:33:03.2413365Z` found zero matching paths.

The first upload attempt created malformed audit input because a local shell variable was escaped into the destination name. It never produced evaluator metrics and is excluded from the matrix. The verified v2 input and five independently copied v2 cases produced the recorded matrix.

The first cleanup pass ran from `2026-08-12T19:37:21.9413351Z` through `2026-08-12T19:37:22.0199393Z`. It removed exactly four audit directories: `EW_AUDIT_TASK07_INPUT`, `EW_AUDIT_TASK07_INPUT_V2`, `EW_AUDIT_TASK07_RUN_20260812T193420852790Z`, and `EW_AUDIT_TASK07_RUN_V2_20260812T193542706122Z`, with zero failures.

An independent probe correctly found one ordinary file named `EW_AUDIT_TASK07_INPUT$name` that the directory-only first pass did not target. It was the artifact of the malformed first upload, not a candidate or execution output. A second exact cleanup ran from `2026-08-12T19:37:57.6928451Z` through `2026-08-12T19:37:57.7084939Z` and removed that single resolved file.

The final independent probe at `2026-08-12T19:38:11.7769014Z` found zero matching paths, zero related processes, and zero related listening ports; `zero_residual=true`. The probe excluded its own process and parent process. No task-08-or-later path or generic Desktop content was targeted.

The v2 machine receipt SHA-256 is `7ea80faaedba1a0a4767314b597b98a008328fadbadde081a5fc290e89134aa9`.

The 2026-08-14 candidate-boundary revalidation used two independently created local `/tmp/ew07-boundary.*` copies only and did not reconnect to the Windows instance. After recording `BOUNDARY_REVALIDATION.json`, the resolved temporary root was moved to macOS Trash. No evaluator output, bytecode/cache, or SQLite sidecar remains under task-07.
