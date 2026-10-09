# Task 02 instance cleanup record

Cleanup was limited to artifacts created by the 2026-08-12 evaluator audit on snapshot `cli2-archicad27-openstudio310-win`. No other task directory or generic Desktop content was targeted.

Before the matrix rerun, the exact allowlist glob `C:\Users\user\Desktop\EW_AUDIT_TASK02_RUN_*` matched zero paths. After the rerun, cleanup ran from `2026-08-12T18:52:51.800343+00:00` to `2026-08-12T18:52:51.831012+00:00` and removed exactly:

- `C:\Users\user\Desktop\EW_AUDIT_TASK02_RUN_20260812T185143447660Z`
- `C:\Users\user\Desktop\EW_AUDIT_TASK02_INPUT`

Removed count was 2, failure count was 0, and the cleanup script reported no remaining `EW_AUDIT_TASK02_*` path.

An independently launched read-only probe ran afterward at `2026-08-12T18:52:52.003873+00:00`. It found zero matching paths, zero processes whose command line contained `EW_AUDIT_TASK02`, and zero listening TCP ports owned by such processes. Probe stderr was empty and `zero_residual` was `true`.

Machine receipt SHA-256 values retained during the audit were:

- evaluator receipt: `a85ae2a2e561a5a74c2ab63844d164b153bae6db513422ae4cf50235a0227581`
- cleanup receipt: `306901b98c9c5fafb715d337bf3d7b2dbe7784144eb1606e5d8f7e01d49b2511`
- independent zero-residual probe: `64d52f6138a334b95eb863f69030adfe9f5f69ca8cd91a984f2f1f2efe3bdecf`

The two receipt files and uploaded probe runner were temporarily written under `C:\Windows\Temp` so the receipts could be downloaded after deletion of the audit directories. A second allowlisted cleanup at `2026-08-12T18:55:25.769743+00:00` removed all three exact paths with zero failures:

- `C:\Windows\Temp\engiworld_task02_cleanup_receipt.json`
- `C:\Windows\Temp\engiworld_task02_zero_residual_probe.json`
- `C:\Windows\Temp\engiworld_task02_probe_runner.py`

A new independent read-only probe at `2026-08-12T18:55:26.869423+00:00` checked both `C:\Users\user\Desktop\EW_AUDIT_TASK02_*` and those exact Temp paths. It again found zero paths, zero matching processes, and zero related listening ports, with empty stderr and `zero_residual=true`. This is the final instance state for the audit.
