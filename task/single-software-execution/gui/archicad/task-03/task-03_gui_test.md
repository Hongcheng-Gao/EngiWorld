# GUI Test Report

Result: PASS-GUI

Task JSON: `task-03.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-03/eval/result.json`

## Reproducible GUI Procedure

1. Create a fresh `ArchiCAD-27` Windows instance and run the task config.
2. Dismiss Windows startup dialogs and launch Archicad 27.
3. Click New, accept the EULA if shown, and create a project from the default template.
4. In Floor Plan, draw a compact outer wall rectangle about 9 m by 5 m.
5. Draw two real internal partition walls to create three rooms.
6. Draw one slab covering the footprint.
7. Place three real Door elements and two real Window elements on wall segments.
8. Use the Zone Tool in manual polygon mode to create:
   - `OFFICE`, with Zone Name and Zone No. both set to `OFFICE`.
   - `STORAGE`, with Zone Name and Zone No. both set to `STORAGE`.
   - `WC`, with Zone Name and Zone No. both set to `WC`.
9. Save As `C:\Users\user\Desktop\result.ifc`.
10. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save.
11. Run eval with `--skip-config --evaluate`.

## Notes

Zone No. must match each required room name because this becomes the exported IFC space `Name`.
