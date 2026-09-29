# Task 03 instance cleanup record

Cleanup was restricted to the `EW_AUDIT_TASK03_*` paths created by this audit on snapshot `cli2-archicad27-openstudio310-win`. No task-04-or-later path and no generic Desktop content was targeted.

The pre-run read-only probe at `2026-08-12T18:59:33.644276+00:00` found zero matching paths and zero matching processes. After evaluator execution, cleanup ran from `2026-08-12T19:02:17.650762+00:00` through `2026-08-12T19:02:17.666798+00:00`. It removed exactly:

- `C:\Users\user\Desktop\EW_AUDIT_TASK03_RUN_20260812T190133884324Z`
- `C:\Users\user\Desktop\EW_AUDIT_TASK03_INPUT`

Removed count was 2, failure count was 0, and no `EW_AUDIT_TASK03_*` path remained.

A separately launched read-only probe ran at `2026-08-12T19:02:18.482748+00:00`. It found zero matching paths, zero processes whose command line contained `EW_AUDIT_TASK03`, and zero listening TCP ports owned by such processes. Probe stderr was empty and `zero_residual=true`.

The task-03 Windows evaluator receipt was downloaded before cleanup and had SHA-256 `b701dc02547edfa90203904406d7bd228910fa5af6b27b6896ba8a53c9aa643a`. No receipt or runner was left on the instance because the receipt and runner lived inside the removed input directory.
