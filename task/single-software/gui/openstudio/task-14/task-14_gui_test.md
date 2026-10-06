# GUI Test Report: task-14

Result: PASS-GUI after task update

The task now validates one people load and one lighting load attached to `OfficeType`, inherited by both spaces.

## Environment

- Snapshot: OpenStudio-1.11.0
- Instance IP: 124.174.65.28
- Output file: `/home/user/Desktop/result.osm`

## GUI Procedure

1. Ran the task setup and opened `init.osm` in OpenStudio Application.
2. Opened Space Types and created a new space type, then renamed it to `OfficeType`.
3. Opened Spaces > Properties and assigned `OfficeType` to both `Office1` and `Office2` by dragging the model space type into each Space Type cell.
4. Returned to Space Types > Loads.
5. Switched the right panel to Library, expanded People Definitions, and dragged one people definition into the `OfficeType` load table.
6. Expanded Lights Definitions and dragged one lights definition into the `OfficeType` load table, then assigned a different valid ruleset from the People load.
7. Saved the model as `/home/user/Desktop/result.osm` through the OpenStudio GUI.

## Verification

Downloaded `result.osm` and confirmed object counts:

- `OS:Space`: 2
- `OS:People`: 1, attached to `OfficeType`
- `OS:Lights`: 1, attached to `OfficeType`
- `OS:ElectricEquipment`: 0
- `OS:Schedule:Ruleset`: 2
- `OS:SpaceType`: 1
- The People and Lights instances reference their respective definitions and distinct valid rulesets.

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
