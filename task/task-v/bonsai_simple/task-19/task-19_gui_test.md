# task-19 GUI test report

Result: PASS-GUI

Tested on a fresh Bonsai Ubuntu instance created from snapshot `Bonsai-0.8.5`.

Procedure:

1. Ran the task config to upload `init.ifc` to `/home/user/Desktop/init.ifc` and launch Blender with Bonsai.
2. Waited for Blender 4.2.3 LTS and Bonsai v0.8.5 to finish opening.
3. Used Blender's GUI operator search with `F3`, searched for `Open IFC Project`, and selected it.
4. In the Blender file view, entered `/home/user/Desktop/init.ifc` in the path field and loaded the project with the `Load Project` button.
5. Used `Select > None` from the viewport menu to clear the selected wall when needed, so Bonsai showed create controls instead of wall edit controls.
6. Activated the Spatial Tool with `Shift+Space`, then `Alt+2`.
7. For each room compartment, moved the 3D cursor inside the room and used `Generate Space from Cursor`.
8. Renamed the five created spaces in the Outliner with `F2`:
   - `IfcSpace/Lab`
   - `IfcSpace/Prep`
   - `IfcSpace/Office`
   - `IfcSpace/Store`
   - `IfcSpace/WC`
9. Activated the Door Tool and used `Quick Create IfcDoorType`. Bonsai showed an internal representation error, but it still created `IfcDoorType/Unnamed`.
10. Used the Door Tool's `Add` button five times. For each occurrence, clicked a plausible wall location, accepted the `Add Type Occurrence` dialog with `No Geometry`, and confirmed that `IfcDoor/Door` through `IfcDoor/Door.004` appeared in the Outliner.
11. Activated the Window Tool with `Shift+Space`, then `Shift+3`, and used `Quick Create IfcWindowType`. Bonsai showed the same internal representation error, but it still created `IfcWindowType/Unnamed`.
12. Used the Window Tool's `Add` button five times. For each occurrence, clicked a plausible exterior wall location, accepted the `Add Type Occurrence` dialog with `No Geometry`, and confirmed that `IfcWindow/Window` through `IfcWindow/Window.004` appeared in the Outliner.
13. Used Blender's GUI operator search with `F3`, searched for `Save IFC Project As`, and selected it.
14. In the IFC save dialog, changed the location to `/home/user/Desktop`, changed the filename to `result.ifc`, and clicked `Save IFC`.
15. Confirmed the Bonsai Project Info panel showed the saved file path `/home/user/Desktop/result.ifc`.
16. Ran the task evaluator with `--skip-config --evaluate`.

Evaluator result:

`exact_match: True`

No task files were modified.
