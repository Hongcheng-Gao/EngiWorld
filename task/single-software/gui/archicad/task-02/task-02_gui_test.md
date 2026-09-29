# GUI Test Report

Result: PASS-GUI

Task JSON: `task-02.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-02/eval-02/result.json`

## Reproducible GUI Procedure

1. Create a fresh `ArchiCAD-27` Windows instance and run the task config.
2. Dismiss Shutdown Event Tracker if present, then launch Archicad 27 from the desktop shortcut.
3. Click New, accept the EULA if shown, and create a new project from the default template.
4. In Floor Plan, draw an outer rectangular wall loop about 8 m by 4 m. At the initial zoom, about 60 px by 32 px fit the eval tolerance.
5. Draw one internal partition wall through the middle, creating two rooms.
6. Draw one rectangular slab covering the whole footprint.
7. Place two real Door elements on exterior wall segments.
8. Place two real Window elements on exterior wall segments.
9. Use the Zone Tool in manual polygon mode to create two zones:
   - `WAITING`: set both Zone Name and Zone No. to `WAITING`.
   - `CONSULT`: set both Zone Name and Zone No. to `CONSULT`.
10. Save As `C:\Users\user\Desktop\result.ifc`.
11. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save.
12. Run eval with `--skip-config --evaluate`.

## Notes

The Zone No. must match the required space name because Archicad exports it as the IFC space `Name`.
