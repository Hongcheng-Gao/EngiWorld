# GUI Test Report

Result: PASS-GUI

Task JSON: `task-18.json`
Test log: `/Users/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-18/eval-gui-final/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If Windows shows Shutdown Event Tracker, enter a short comment and click OK. If Archicad shows the EULA, choose `I accept` and continue.
3. When the IFC import library-parts dialog appears, keep the default Embedded Library option and click OK.
4. In Floor Plan, use the Door Tool to add one additional real Door in an internal partition wall.
5. Use the Window Tool to add one additional real Window in an exterior wall.
6. Use `Design > Architectural Tools > Zone` to select the Zone Tool.
7. For each required Zone, set both `Zone Name` and `No.` in the Info Box to the same value, click in the corresponding room area, confirm overlapping-zone warnings with `Yes`, and place the zone stamp when prompted:
   - `CLASS-1`
   - `CLASS-2`
   - `CORRIDOR`
   - `WC`
8. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
9. Set `Save as type` to `IFC Files (*.ifc)`.
10. Set `Translator` to `IFC4 Design Transfer View-based Export`.
11. Click Save and confirm replacement of any previous `result.ifc`.
12. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains the main shell, slab, walls, and most openings. The passing GUI edit adds the missing real door/window counts and exports named IFC4 spaces for `CLASS-1`, `CLASS-2`, `CORRIDOR`, and `WC`.
