# GUI Test Report: task-13

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
4. Switched the right panel to Library, expanded Electric Equipment Definitions, and dragged one electric equipment definition into the `EquipmentRoom` Definition cell.
5. Switched the right panel to My Model, expanded Schedules > Ruleset Schedules, and dragged `EquipmentRoom Occupied Schedule` into the load Schedule cell.
6. Saved the model as `/home/user/Desktop/result.osm` through the OpenStudio GUI.

## Verification

Downloaded `result.osm` and confirmed object counts:

- `OS:Space`: 1
- `OS:People`: 0
- `OS:Lights`: 0
- `OS:ElectricEquipment`: 1
- `OS:Schedule:Ruleset`: 1
- `OS:SpaceType`: 0

Evaluator command:

```bash
python scripts/python/sanity_check_remote_osworld.py \
  --host 124.174.65.28 \
  --task-json /Users/leiyu/workspace/Engiworld/task/task-v/openstudio_simple/task-13/task-13.json \
  --skip-config \
  --out-dir /Users/leiyu/workspace/logs/openstudio_simple_gui/task-13/eval1 \
  --evaluate
```

Evaluator result: `True`
