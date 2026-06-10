# GUI Test Report

Result: PASS-GUI

Task JSON: `task-13.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-13/eval/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If another project is open, close it without saving, then accept the IFC import library-parts dialog for the uploaded `init.ifc` using the default Embedded Library option.
3. In Floor Plan, select the Door Tool from the toolbox.
4. Place an additional real Door element in the left internal wall so the rooms and corridor have enough door openings.
5. Click the side/orientation prompt to complete the door placement.
6. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
7. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`.
8. Confirm replacement of any previous `result.ifc`.
9. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains the `CORRIDOR`, `ROOM 1`, and `ROOM 2` spaces, slab, walls, and windows. The passing GUI edit adds the missing real door count.
