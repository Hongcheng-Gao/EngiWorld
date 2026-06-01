# GUI Test Report

Result: PASS-GUI

Task JSON: `task-16.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-16/eval-fixed/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If needed, accept the IFC import library-parts dialog using the default Embedded Library option.
3. In Floor Plan, select the Door Tool and place additional real doors in the internal partition walls.
4. Select the Zone Tool and create named zones with both Zone Name and Zone No. set to `OPEN OFFICE`, `MEETING`, `STORAGE`, and `WC`.
5. Accept overlapping-zone warnings when placing the new zone stamps over the existing rooms.
6. Select the Window Tool and add one additional exterior window so the model has at least three windows.
7. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
8. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`.
9. Confirm replacement of any previous `result.ifc`.
10. Run eval with `--skip-config --evaluate`.

## Notes

The passing export preserves the init shell and adds the missing named zones, door count, and window count.
