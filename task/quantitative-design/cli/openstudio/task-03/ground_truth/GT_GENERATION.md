# Ground Truth Reference

This is a feasible reference solution for `quant-cli-openstudio-task-03-ubuntu`, not a unique optimum. It contains the required optimized IDF, native EnergyPlus SQL/ERR output, CSV report, design summary, and score.json. The evaluator does not compare submissions to these files; it recomputes continuous score from the submitted artifacts.

The corrected baseline and reference IDFs were opened and saved by OpenStudio SDK 3.11.0. Both were executed only through `openstudio run -w /home/user/Desktop/workflow.osw`, which invoked bundled EnergyPlus 25.2 and retained `run/eplusout.sql` and `run/eplusout.err`. CSV/JSON metrics were derived from standard SQLite tables after the native run.

The rebuilt model binds all constrained values to real IDF objects: three Space-to-Zone assignments, occupied setpoint and load schedules, a separate HVAC availability schedule, lower STACKS/SERVICE load profiles, three effective infiltration objects, six windows, true material/glazing values, and three daylight controls. EnergyPlus 25.2 reported successful completion with zero severe and zero fatal errors. Its legacy `Simulations.Completed` fields remained `FALSE/FALSE`; the evaluator therefore requires the successful ERR footer, zero SQL severe errors, populated standard tables, submitted-to-rerun metric agreement, and native IDF bindings together.
