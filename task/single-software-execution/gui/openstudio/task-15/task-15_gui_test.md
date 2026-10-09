# GUI Test Report: task-15

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
4. Set Load Type to People, expanded Library > People Definitions, and dragged one people definition into the Breakroom Definition cell and one into the Workroom Definition cell.
5. Set Load Type to Lights, expanded Library > Lights Definitions, and dragged one lights definition into each space's Definition cell.
6. Set Load Type to Electric Equipment, expanded Library > Electric Equipment Definitions, and dragged one electric equipment definition into each space's Definition cell.
7. Horizontally scrolled the loads table to show the Schedule column.
8. Switched the right panel to My Model > Schedules > Ruleset Schedules and dragged `Breakroom Occupied Schedule` into the Breakroom load schedule cells and `Workroom Occupied Schedule` into the Workroom load schedule cells.
9. Saved the model as `/home/user/Desktop/result.osm` through the OpenStudio GUI.

## Verification

Downloaded `result.osm` and confirmed object counts:

- `OS:Space`: 2
- `OS:People`: 2
- `OS:Lights`: 2
- `OS:ElectricEquipment`: 2
- `OS:Schedule:Ruleset`: 2
- `OS:SpaceType`: 0

Evaluator command:

```bash
python scripts/python/sanity_check_remote_osworld.py \
  --host 124.174.65.28 \
  --task-json /Users/leiyu/workspace/Engiworld/task/task-v/openstudio_simple/task-15/task-15.json \
  --out-dir logs/openstudio_simple_gui/task-15 \
  --skip-config \
  --evaluate \
  --result-json logs/openstudio_simple_gui/task-15/result_eval.json
```

Evaluator result: `True`
