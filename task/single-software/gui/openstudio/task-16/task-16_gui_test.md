# task-16 GUI test report

Result: PASS-GUI

Tested on a fresh OpenStudio Ubuntu instance created from snapshot `OpenStudio-1.11.0`.

Procedure:

1. Ran the task config to upload `init.osm` to the Desktop and launch it in OpenStudio Application.
2. Waited for OpenStudio to finish loading the library files and open `/home/user/Desktop/init.osm`.
3. Dismissed the "Model updated from 3.10.0 to 3.11.0." dialog with OK.
4. Opened Thermal Zones > HVAC Systems from the left navigation.
5. Dragged temperature schedule rulesets from the Library pane into the cooling thermostat schedule and heating thermostat schedule cells for both thermal zones:
   - `ZoneA Zone` cooling thermostat schedule
   - `ZoneA Zone` heating thermostat schedule
   - `ZoneB Zone` cooling thermostat schedule
   - `ZoneB Zone` heating thermostat schedule
6. Used the OpenStudio GUI Save As dialog with `Ctrl+Shift+S`.
7. In the Save dialog, used `/home/user/Desktop/result.osm` as the output path.
8. Ran the task evaluator with `--skip-config --evaluate`.

Evaluator result:

`exact_match: True`

No task files were modified.
