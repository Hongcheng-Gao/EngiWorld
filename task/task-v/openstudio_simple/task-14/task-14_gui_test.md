# GUI Test Report: task-14

Result: PASS-GUI

No task package files were modified.

## Environment

- Snapshot: OpenStudio-1.11.0
- Instance IP: 124.174.65.28
- Output file: `/home/user/Desktop/result.osm`

## GUI Procedure

1. Ran the task setup and opened `init.osm` in OpenStudio Application.
2. Opened Space Types and created a new space type, then renamed it to `OfficeType`.
3. Opened Spaces > Properties and assigned `OfficeType` to both `Office1` and `Office2` by dragging the model space type into each Space Type cell.
4. Returned to Space Types > Loads.
5. Switched the right panel to Library, expanded People Definitions, and dragged two people definitions into the `OfficeType` load table.
6. Expanded Lights Definitions and dragged two lights definitions into the `OfficeType` load table.
7. Saved the model as `/home/user/Desktop/result.osm` through the OpenStudio GUI.

## Verification

Downloaded `result.osm` and confirmed object counts:

- `OS:Space`: 2
- `OS:People`: 2
- `OS:Lights`: 2
- `OS:ElectricEquipment`: 0
- `OS:Schedule:Ruleset`: 2
- `OS:SpaceType`: 1

Evaluator command:

```bash
python scripts/python/sanity_check_remote_osworld.py \
  --host 124.174.65.28 \
  --task-json /Users/leiyu/workspace/Engiworld/task/task-v/openstudio_simple/task-14/task-14.json \
  --skip-config \
  --out-dir /Users/leiyu/workspace/logs/openstudio_simple_gui/task-14/eval1 \
  --evaluate
```

Evaluator result: `True`
