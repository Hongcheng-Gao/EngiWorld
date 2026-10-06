# GUI Test Report

Result: PASS-GUI

Task JSON: `task-14.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-14/eval/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If another project is open, close it without saving, then accept the IFC import library-parts dialog for the uploaded `init.ifc` using the default Embedded Library option.
3. In Floor Plan, select the Window Tool from the toolbox.
4. Place three real Window elements in the top exterior wall, clicking the interior side to complete each placement.
5. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
6. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`.
7. Confirm replacement of any previous `result.ifc`.
8. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains the `WORK ROOM` and `STORE` spaces, walls, slab, and doors. The passing GUI edit adds the required real exterior windows.
