# task-15 GUI Test Report

## Summary

- Result: PASS-GUI
- Task: `v-bonsai-simple-task-15-ubuntu`
- Instance: `i-yenj0dxjwg4c5quze96p`
- Host: `124.174.99.195`
- Snapshot: `Bonsai-0.8.5`
- Final evaluator: `exact_match: True`
- Final eval log: `/Users/leiyu/workspace/OSWorld/logs/bonsai_simple/task-15/eval-round2/result.json`

## GUI Workflow

1. Ran the OSWorld setup for `task-15`, which uploaded `/home/user/Desktop/init.ifc` and launched Blender/Bonsai.
2. In Blender/Bonsai, used the GUI search command to open `Open IFC Project`, selected `/home/user/Desktop/init.ifc`, and loaded the IFC project.
3. Used Bonsai's Spatial Tool and `Generate Space from Cursor` to create five room spaces inside the existing row office shell.
4. Renamed the generated `IfcSpace` objects in the Outliner to:
   - `Office A`
   - `Office B`
   - `Office C`
   - `Shared`
   - `WC`
5. Unlocked the spatial decomposition in the Bonsai Spatial panel and deleted the original seed `Office Shell` space, leaving only the five required target spaces.
6. Verified the seed model already contained the required shell structure: 9 `IfcWall` elements and 1 `IfcSlab`.
7. Used Bonsai's Door Tool to create an `IfcDoorType`, then added door occurrences through the GUI `Add Type Occurrence` flow with `No Geometry` selected. The UI created several internal representation errors, but accepted the door occurrences.
8. Used Bonsai's Window Tool to create an `IfcWindowType`, then added window occurrences through the same GUI `Add Type Occurrence` flow with `No Geometry`.
9. Saved the project with `Save IFC Project As` to `/home/user/Desktop/result.ifc`.

## Issues Encountered

- The first space-generation pass created only four spaces because the rightmost click landed outside a detected polygon. I adjusted the cursor position and generated the fifth space.
- Door and window creation in Bonsai repeatedly opened `Add Type Occurrence` confirmation dialogs and internal error messages. These errors matched earlier Bonsai behavior: the occurrence was created even though the representation assignment errored.
- A normal save did not overwrite `result.ifc` after additional doors were added. I reopened `Save IFC Project As`, confirmed the Desktop path and `result.ifc` filename in the GUI file dialog, and clicked `Save IFC` to force the overwrite.

## Verification

Before the final eval, I performed a read-only parse of the saved IFC to check the authored element counts:

- `IfcSpace`: 5, names `Office A`, `Office B`, `Office C`, `Shared`, `WC`
- `IfcWall`: 9
- `IfcSlab`: 1
- `IfcDoor`: 7
- `IfcWindow`: 6

Final evaluator command:

```bash
python scripts/python/sanity_check_remote_osworld.py \
  --host 124.174.99.195 \
  --task-json /Users/leiyu/workspace/Engiworld/task/task-v/bonsai_simple/task-15/task-15.json \
  --skip-config --evaluate \
  --out-dir logs/bonsai_simple/task-15/eval-round2 \
  --result-json logs/bonsai_simple/task-15/eval-round2/result.json
```

Final evaluator output:

```text
[eval] actual  : 'True\n'
[eval] expected: 'True\n'
[eval] exact_match: True
```

