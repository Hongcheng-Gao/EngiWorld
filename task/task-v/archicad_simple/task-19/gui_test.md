# GUI Test Report

Result: PASS-GUI

Task JSON: `task-19.json`
Test log: `/Users/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-19/eval-gui-ifc4/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If Windows shows Shutdown Event Tracker, enter a short comment and click OK. If Archicad shows the EULA, choose `I accept` and continue.
3. When the IFC import library-parts dialog appears, keep the default Embedded Library option and click OK.
4. In Floor Plan, use the Door Tool to add two additional real Doors in internal partition walls.
5. Use `Design > Architectural Tools > Zone` to select the Zone Tool.
6. For each required Zone, set both `Zone Name` and `No.` in the Info Box to the same value, then click in the corresponding room area. Confirm overlapping-zone warnings with `Yes` and place the zone stamp when prompted:
   - `LOBBY`
   - `READING`
   - `STACKS`
   - `OFFICE`
7. Use `Design > Architectural Tools > Window` to select the Window Tool and add one additional real Window in an exterior wall.
8. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
9. Set `Save as type` to `IFC Files (*.ifc)`.
10. Set `Translator` to `IFC4 Design Transfer View-based Export`.
11. Click Save and confirm replacement of any previous `result.ifc`.
12. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains the required shell, slab, and enough walls. The passing GUI edit adds enough real doors/windows and creates the required IFC4 spaces named `LOBBY`, `READING`, `STACKS`, and `OFFICE`. Exporting with `Exact Geometry Export` produced IFC2X3 and failed; the passing export used the IFC4 Design Transfer translator.
