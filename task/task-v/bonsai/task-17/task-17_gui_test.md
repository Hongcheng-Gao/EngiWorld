# task-17 GUI test report

Result: PASS-GUI

Tested on a fresh Bonsai Ubuntu instance created from snapshot `Bonsai-0.8.5`.

Procedure:

1. Ran the task config to upload `init.ifc` to `/home/user/Desktop/init.ifc` and launch Blender with Bonsai.
2. Waited for Blender 4.2.3 LTS and Bonsai v0.8.5 to finish opening.
3. Used Blender's GUI operator search with `F3`, searched for `Open IFC Project`, and selected it.
4. In the Blender file view, selected `/home/user/Desktop/init.ifc` and loaded the project with the `Load Project` button.
5. Visually confirmed the seed library shell contained 8 walls, 1 slab, and the original `IfcSpace/Library Shell`.
6. Activated the Spatial Tool with `Shift+Space`, then `Alt+2`.
7. For each compartment, moved the 3D cursor inside the room with shift-right-click and used `Generate Space from Cursor`.
8. Renamed the four generated spaces in the Outliner with `F2`:
   - `IfcSpace/Reading`
   - `IfcSpace/Desk`
   - `IfcSpace/Archive`
   - `IfcSpace/WC`
9. Used the Spatial panel lock toggle in Project Overview to unlock the spatial tree, then deleted the original `IfcSpace/Library Shell` through the GUI so only the four required spaces remained.
10. Activated the Door Tool from the toolbar and used `Quick Create IfcDoorType`. Bonsai showed an internal representation error, but it still created `IfcDoorType/Unnamed`.
11. Used the Door Tool's `Add` button four times. For each occurrence, clicked a plausible wall location, accepted the `Add Type Occurrence` dialog with `No Geometry`, and confirmed that `IfcDoor/Door` through `IfcDoor/Door.003` appeared in the Outliner.
12. Activated the Window Tool with `Shift+Space`, then `Shift+3`, and used `Quick Create IfcWindowType`. Bonsai showed the same internal representation error, but it still created `IfcWindowType/Unnamed`.
13. Used the Window Tool's `Add` button five times. For each occurrence, clicked an exterior wall location, accepted the `Add Type Occurrence` dialog with `No Geometry`, and confirmed that `IfcWindow/Window` through `IfcWindow/Window.004` appeared in the Outliner.
14. Used Blender's GUI operator search with `F3`, searched for `Save IFC Project As`, and selected it.
15. In the IFC save dialog, changed the location to `/home/user/Desktop`, changed the filename to `result.ifc`, and clicked `Save IFC`.
16. Confirmed the Bonsai Project Info panel showed the saved file path `/home/user/Desktop/result.ifc`.
17. Ran the task evaluator with `--skip-config --evaluate`.

Evaluator result:

`exact_match: True`

No task files were modified.
