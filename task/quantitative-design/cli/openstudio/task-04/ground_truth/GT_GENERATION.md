# Ground Truth Reference

This is a feasible reference solution for `quant-cli-openstudio-task-04-ubuntu`, not a unique optimum. It contains the required optimized IDF, native EnergyPlus SQL/ERR output, CSV report, design summary, and score.json. The evaluator does not compare submissions to these files; it recomputes continuous score from the submitted artifacts.

The corrected baseline and reference IDFs were opened and saved by OpenStudio SDK 3.11.0 and executed only through `openstudio run -w /home/user/Desktop/workflow.osw` with bundled EnergyPlus 25.2. A fixed native summer `SizingPeriod:DesignDay` was added because the supplied EPW produced zero cooling throughout the annual run, making the instructed peak-cooling objective unmeasurable. The evaluator freezes that design day and derives peak cooling from the simultaneous hourly sum of both classrooms' Ideal Loads variables.

The rebuilt model also binds precooling to the real cooling-setpoint schedule, thermal mass to the floor material density/specific heat, two Space-to-Zone assignments, occupied/activity schedules, four windows, two daylight controls, effective infiltration, and true material/glazing/load objects. Native DesignDay plus Annual execution completed with zero severe and zero fatal errors; CSV/JSON were derived from the standard SQLite tables.
