# task-18 GUI test report

Result: PASS-GUI

Tested on a fresh Bonsai Ubuntu instance created from snapshot `Bonsai-0.8.5`.

Procedure:

1. Ran the task config to upload `init.ifc` to `/home/user/Desktop/init.ifc` and launch Blender with Bonsai.
2. Waited for Blender 4.2.3 LTS and Bonsai v0.8.5 to finish opening.
3. Used Blender's GUI operator search with `F3`, searched for `Open IFC Project`, and selected it.
4. In the Blender file view, loaded `/home/user/Desktop/init.ifc` with the `Load Project` button.
5. Visually confirmed the seed daycare shell contained the rectangular wall/slab shell, with 9 walls, 1 slab, and the original shell space visible in the Outliner.
6. Activated the Spatial Tool with `Shift+Space`, then `Alt+2`.
7. For each compartment, moved the 3D cursor into the room with shift-right-click and used `Generate Space from Cursor`.
8. Renamed the generated spaces in the Outliner with `F2`:
   - `IfcSpace/Play`
   - `IfcSpace/Sleep`
   - `IfcSpace/Staff Room`
   - `IfcSpace/Storage`
   - `IfcSpace/WC`
9. The original `IfcSpace/Daycare Shell` remained as an extra locked space. After the first evaluator attempts failed, used the Spatial panel lock toggle in Project Overview to unlock the spatial tree and deleted `IfcSpace/Daycare Shell` through the GUI, leaving only the five required named spaces.
10. Activated the Door Tool from the toolbar and used `Quick Create IfcDoorType`. Bonsai showed an internal representation error, but it still created `IfcDoorType/Unnamed`.
11. Used the Door Tool's `Add` button five times. For each occurrence, clicked a plausible wall location, accepted the `Add Type Occurrence` dialog with `No Geometry`, and confirmed that `IfcDoor/Door` through `IfcDoor/Door.004` appeared in the Outliner.
12. Activated the Window Tool with `Shift+Space`, then `Shift+3`, and used `Quick Create IfcWindowType`. Bonsai showed the same internal representation error, but it still created `IfcWindowType/Unnamed`.
13. Used the Window Tool's `Add` button six times. For each occurrence, clicked an exterior wall location, accepted the `Add Type Occurrence` dialog with `No Geometry`, and confirmed that `IfcWindow/Window` through `IfcWindow/Window.005` appeared in the Outliner.
14. Removed two accidentally created unused type objects, `IfcRampFlightType/Unnamed` and `IfcWallType/Unnamed`, from the Outliner using GUI delete.
15. Used Blender's GUI operator search with `F3`, searched for `Save IFC Project As`, and selected it.
16. In the IFC save dialog, changed the location to `/home/user/Desktop`, changed the filename to `result.ifc`, and clicked `Save IFC`.
17. Confirmed the Bonsai Project Info panel showed the saved file path `/home/user/Desktop/result.ifc`.
18. Ran the task evaluator with `--skip-config --evaluate`. A failed run revealed the visible space name had been misspelled as `Slep`; corrected it to `Sleep` in the Outliner with `F2`, saved again with the GUI, and reran the evaluator.

Evaluator result:

`exact_match: True`

No task files were modified.
