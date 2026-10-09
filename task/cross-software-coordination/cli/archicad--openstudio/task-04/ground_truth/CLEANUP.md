# Task 04 instance cleanup record

Cleanup was restricted to `EW_AUDIT_TASK04_*` paths created by this audit on snapshot `cli2-archicad27-openstudio310-win`. No task-05-or-later path and no generic Desktop content was targeted.

The pre-run read-only probe at `2026-08-12T19:06:29.807958+00:00` found zero matching paths. After the main matrix and corrected lighting-negative rerun, cleanup ran from `2026-08-12T19:10:14.107604+00:00` through `2026-08-12T19:10:14.138856+00:00`. It removed exactly:

- `C:\Users\user\Desktop\EW_AUDIT_TASK04_RUN_20260812T190752264224Z`
- `C:\Users\user\Desktop\EW_AUDIT_TASK04_INPUT`

Removed count was 2, failure count was 0, and no `EW_AUDIT_TASK04_*` path remained. A separately launched read-only probe at `2026-08-12T19:10:14.939601+00:00` found zero matching paths, zero processes with the task-04 audit prefix in their command line, and zero listening TCP ports owned by such processes. Probe stderr was empty and `zero_residual=true`.

The downloaded task-04 main Windows receipt SHA-256 is `df20d2cfefc8b15df487c3b4dd193630a87d5cd9d30e7a9869e67af6f8475366`. Receipt and runners lived inside the removed input directory, so none remained on the instance.
