# GUI Test Report: task-11

Result: PASS-GUI

No task package files were modified.

## Environment

- Snapshot: OpenStudio-1.11.0
- Instance IP: 124.174.65.28
- Output file: `/home/user/Desktop/result.osm`

## GUI Procedure

1. Ran the task setup and opened `init.osm` in OpenStudio Application.
2. Dismissed the model update dialog.
3. Opened Spaces > Loads.
4. Switched the right panel to Library, expanded People Definitions, and dragged one people definition into the `ScheduledOffice` Definition cell.
5. Switched the right panel to My Model, expanded Schedules > Ruleset Schedules, and dragged `ScheduledOffice Occupied Schedule` into the load Schedule cell.
6. Saved the model as `/home/user/Desktop/result.osm` through the OpenStudio GUI.

## Verification

Downloaded `result.osm` and confirmed object counts:

- `OS:BuildingStory`: 1
- `OS:Space`: 1
- `OS:ThermalZone`: 1
- `OS:Surface`: 6
- `OS:People`: 1
- `OS:Lights`: 0
- `OS:ElectricEquipment`: 0
- `OS:Schedule:Ruleset`: 1
- `OS:SpaceType`: 0

Evaluator command:

```bash
python scripts/python/sanity_check_remote_osworld.py \
  --host 124.174.65.28 \
  --task-json /Users/leiyu/workspace/Engiworld/task/task-v/openstudio_simple/task-11/task-11.json \
  --skip-config \
  --out-dir /Users/leiyu/workspace/logs/openstudio_simple_gui/task-11/eval1 \
  --evaluate
```

Evaluator result: `True`
