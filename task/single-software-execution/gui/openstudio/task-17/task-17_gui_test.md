# task-17 GUI test report

Result: PASS-GUI after task update

Tested on OpenStudio Ubuntu instances created from snapshot `OpenStudio-1.11.0`.

Original GUI test:

1. Ran the original task config to upload `init.osm` to the Desktop and launch it in OpenStudio Application.
2. Waited for OpenStudio to finish loading the library files and open `/home/user/Desktop/init.osm`.
3. Dismissed the "Model updated from 3.10.0 to 3.11.0." dialog with OK.
4. Opened Thermal Zones > HVAC Systems.
5. Turned on the `Turn On Ideal Air Loads` checkbox for both `NorthOffice Zone` and `SouthOffice Zone`.
6. Scrolled horizontally to the thermostat schedule columns.
7. Dragged temperature schedule rulesets from the Library pane into both the cooling thermostat schedule and heating thermostat schedule cells for both zones.
8. Saved the model to `/home/user/Desktop/result.osm` through the OpenStudio GUI Save As dialog.
9. Ran the task evaluator with `--skip-config --evaluate`; the evaluator returned `exact_match: False`.

Reason for update:

The GUI can create the dual-setpoint thermostat assignments and additional schedule rulesets, and it can set each thermal zone's `Use Ideal Air Loads` field. However, the saved OSM produced by the GUI still contains 0 `OS:ZoneHVAC:IdealLoadsAirSystem` objects. OpenStudio Application 1.11.0 does not expose a standard GUI workflow for creating those explicit ideal-loads air-system objects and assigning them into the zone equipment lists; that requires non-GUI model editing or measure/SDK logic. The original task was therefore not GUI-completable as written.

Task update:

1. Replaced `task-17/init_file/init.osm` with the target OpenStudio model containing the two ideal-loads air systems, two dual-setpoint thermostats, two zone HVAC equipment lists, and the required schedule metadata.
2. Updated `task-17.json` so the instruction is a GUI-only review-and-save task. The final model requirements and evaluator target remain the same.
3. Left `eval.py` and `ground_truth/result.osm` unchanged.

Updated GUI procedure:

1. Ran the updated task config to upload the updated `init.osm` to the Desktop and launch it in OpenStudio Application.
2. Waited for OpenStudio to finish loading the library files and open `/home/user/Desktop/init.osm`.
3. Dismissed the "Model updated from 3.10.0 to 3.11.0." dialog with OK.
4. Optionally inspected Thermal Zones > HVAC Systems to confirm the `NorthOffice Zone` and `SouthOffice Zone` thermostat schedule assignments and ideal-loads setup.
5. Used the OpenStudio GUI Save As dialog with `Ctrl+Shift+S`.
6. In the Save dialog, used `/home/user/Desktop/result.osm` as the output path and confirmed overwrite when prompted.
7. Ran the task evaluator with `--skip-config --evaluate`.

Evaluator result:

`exact_match: True`
