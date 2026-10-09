# Ground Truth Reference

This is a feasible reference solution for `quant-cli-openstudio-task-01-ubuntu`, not a unique optimum. The evaluator does not compare submissions byte-for-byte with this reference; it reparses the submitted IDF, reruns it in an evaluator-owned OpenStudio 3.11.0 OSW workflow, independently verifies native EnergyPlus 25.2 material, geometry, infiltration, lighting, equipment, people, SQL, ERR, CSV, and JSON evidence, and computes a continuous score.

Generation on the pinned `OpenStudio-1.11.0` snapshot:

1. OpenStudio SDK 3.11.0 loaded the original seed IDF.
2. The SDK corrected the baseline so its envelope R values, WWR geometry, infiltration coefficients, daylight controls, and constrained internal loads are represented by real EnergyPlus objects, then saved `baseline.idf` natively.
3. The corrected baseline was rerun through `openstudio run -w /home/user/Desktop/workflow.osw` to calibrate the baseline metrics in `constraints.json`.
4. OpenStudio SDK 3.11.0 loaded the corrected baseline, applied the feasible reference variables, and natively saved `optimized.idf`.
5. The supplied OSW and `use_optimized_idf` EnergyPlus Measure invoked bundled EnergyPlus 25.2.0 to create `run/eplusout.sql` and `run/eplusout.err`.
6. `energy_report.csv` and `design_summary.json` were derived from that workflow-produced SQL, not written from a self-reported metric table.

Native verification found 0 fatal and 0 severe EnergyPlus errors. Standard SQLite tables contained native report data, R-5.5 wall material, R-8.0 roof material, approximately U-1.2 glazing construction, 17.28 m2 window area, nonzero infiltration design flow, 330 W lighting with a replaceable fraction of 1.0, 360 W equipment, and preserved zone/space semantics. The pinned EnergyPlus 25.2 build left the legacy `Simulations.Completed` and `CompletedSuccessfully` text flags as `FALSE` even though `Errors` contained no severe entries, `ReportData` was populated, the process returned 0, and `eplusout.err` contained `EnergyPlus Completed Successfully-- ... 0 Severe Errors`; the evaluator therefore uses this independent evidence chain rather than trusting either the flags alone or the footer alone.
