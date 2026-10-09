# GUI Test Report

Result: PASS-GUI

Task JSON: `task-12.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-12/eval-fixed-dirty/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If another project is open, close it without saving, then accept the IFC import library-parts dialog for the uploaded `init.ifc` using the default Embedded Library option.
3. In Floor Plan on `0. Ground Floor`, select the Stair Tool from the toolbox.
4. Draw a stair baseline inside the building footprint from the lower-left room area toward the upper central area.
5. Double-click the stair endpoint to complete the stair baseline and leave the generated real Stair element in the model.
6. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
7. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`.
8. Confirm replacement of any previous `result.ifc`.
9. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains two storeys, two slabs, walls, doors, windows, and the `LOWER ROOM` and `UPPER ROOM` spaces. The passing GUI edit adds one real Archicad Stair element exported as `IfcStair`.
