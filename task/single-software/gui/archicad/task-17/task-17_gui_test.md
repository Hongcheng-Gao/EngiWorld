# GUI Test Report

Result: PASS-GUI

Task JSON: `task-17.json`
Test log: `/Users/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-17/eval-gui-final/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If Windows shows Shutdown Event Tracker, enter a short comment and click OK. If Archicad shows the EULA, choose `I accept` and continue.
3. When the IFC import library-parts dialog appears, keep the default Embedded Library option and click OK.
4. In Floor Plan, use the Door Tool to add two additional real Doors in internal partition walls.
5. Use `Design > Architectural Tools > Zone` to select the Zone Tool.
6. For each required Zone, set both `Zone Name` and `No.` in the Info Box to the same value, click in the corresponding room area, confirm overlapping-zone warnings with `Yes`, and place the zone stamp when prompted:
   - `LIVING`
   - `BEDROOM`
   - `KITCHEN`
   - `BATH`
7. Use the Window Tool to add one additional real Window in an exterior wall.
8. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
9. Set `Save as type` to `IFC Files (*.ifc)`.
10. Set `Translator` to `IFC4 Design Transfer View-based Export`.
11. Press Enter from the filename field or click Save, then click `Yes` in the overwrite confirmation dialog.
12. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains the main apartment shell, slab, walls, and some openings. The passing GUI edit adds the missing real doors/windows and creates IFC4 spaces named `LIVING`, `BEDROOM`, `KITCHEN`, and `BATH`. The overwrite confirmation defaults to `No`, so it must be explicitly confirmed with `Yes`.
