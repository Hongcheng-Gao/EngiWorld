# task-20 GUI test report

Result: PASS-GUI

Tested on a fresh OpenStudio Ubuntu instance created from snapshot `OpenStudio-1.11.0`.

Procedure:

1. Ran the task config to upload `init.osm` to the Desktop and launch it in OpenStudio Application.
2. Waited for OpenStudio to finish loading the library files and open `/home/user/Desktop/init.osm`.
3. Dismissed the "Model updated from 3.10.0 to 3.11.0." dialog with OK.
4. Used the OpenStudio GUI save dialog via `Ctrl+Shift+S`.
5. In the Save dialog, kept the location as `/home/user/Desktop`, changed the file name from `init.osm` to `result.osm`, and clicked Save.
6. Ran the task evaluator with `--skip-config --evaluate`.

Evaluator result:

`exact_match: True`

No task files were modified.
