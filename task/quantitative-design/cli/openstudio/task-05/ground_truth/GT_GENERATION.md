# Ground Truth Reference

This is a feasible reference solution for `quant-cli-openstudio-task-05-ubuntu`, not a unique optimum. It contains the required optimized IDF, native EnergyPlus SQL/ERR output, CSV report, design summary, and score.json. The evaluator does not compare submissions to these files; it recomputes continuous score from the submitted artifacts.

The corrected baseline and reference IDFs were opened and saved by OpenStudio SDK 3.11.0 and executed only through `openstudio run -w /home/user/Desktop/workflow.osw` with bundled EnergyPlus 25.2. Each zone has a real minimum-outdoor-air object tied to the occupied schedule and an independent `ZoneVentilation:DesignFlowRate` economizer object. The economizer fraction never scales the minimum outdoor-air field, so staff ventilation cannot be traded away to improve energy.

The rebuild also binds three Space-to-Zone assignments, occupied/activity and HVAC schedules, effective infiltration, six windows, three daylight controls, true constructions/glazing/loads and standard hourly/annual output variables. The native run completed with zero severe and zero fatal errors; all CSV/JSON metrics were derived from the standard SQLite tables.
