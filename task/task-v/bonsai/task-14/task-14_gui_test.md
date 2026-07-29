# task-14 GUI Test Report

## Summary

- Result: PASS-GUI
- Task: `v-bonsai-simple-task-14-ubuntu`
- Instance: `i-yenj9qb5s0wh2yt8e6nk`
- Host: `124.174.68.4`
- Snapshot: `Bonsai-0.8.5`
- Final evaluator: `exact_match: True`
- Final eval log: `/Users/leiyu/workspace/OSWorld/logs/bonsai_simple/task-14/eval-round1/result.json`

## GUI Workflow

1. Ran the OSWorld setup for `task-14`, which uploaded `/home/user/Desktop/init.ifc` and launched Blender/Bonsai.
2. In Blender/Bonsai, used the GUI search command to open `Open IFC Project`, selected `/home/user/Desktop/init.ifc`, and loaded the IFC project.
3. Used Bonsai's Spatial Tool and `Generate Space from Cursor` to create four room spaces in the cafe shell.
4. Renamed the generated `IfcSpace` objects in the Outliner to:
   - `Dining`
   - `Kitchen`
   - `Storage`
   - `WC`
5. Unlocked the spatial decomposition in the Bonsai Spatial panel and deleted the original seed `Cafe Shell` space, leaving only the four required target spaces.
6. Verified the seed model already contained the required rectangular shell structure: 8 `IfcWall` elements and 1 `IfcSlab`.
7. Used Bonsai's Door Tool to create an `IfcDoorType`, then added four door occurrences through the GUI `Add Type Occurrence` flow with `No Geometry` selected.
8. Used Bonsai's Window Tool to create an `IfcWindowType`, then added five window occurrences through the same GUI `Add Type Occurrence` flow with `No Geometry`.
9. Saved the project with `Save IFC Project As` to `/home/user/Desktop/result.ifc`.

## Issues Encountered

- The file chooser initially opened outside the target Desktop location, so I selected the Desktop entry before loading `init.ifc`.
- Door and window creation repeatedly opened `Add Type Occurrence` confirmation dialogs and displayed Bonsai internal error messages, but the Outliner showed that each confirmed occurrence was still created.
- The first save click did not produce `/home/user/Desktop/result.ifc`; the Save As dialog remained open with the correct Desktop path and `result.ifc` filename. I clicked `Save IFC` again from the GUI dialog, after which the target file existed and parsed correctly.

## Verification

Before the final eval, I performed a read-only parse of the saved IFC to check the authored element counts:

- `IfcSpace`: 4, names `Dining`, `Kitchen`, `WC`, `Storage`
- `IfcWall`: 8
- `IfcWallStandardCase`: 0
- `IfcSlab`: 1
- `IfcDoor`: 4
- `IfcWindow`: 5

Final evaluator command:

```bash
python scripts/python/sanity_check_remote_osworld.py \
  --host 124.174.68.4 \
  --task-json /Users/leiyu/workspace/Engiworld/task/task-v/bonsai_simple/task-14/task-14.json \
  --skip-config --evaluate \
  --out-dir logs/bonsai_simple/task-14/eval-round1 \
  --result-json logs/bonsai_simple/task-14/eval-round1/result.json
```

Final evaluator output:

```text
[eval] actual  : 'True\n'
[eval] expected: 'True\n'
[eval] exact_match: True
```
