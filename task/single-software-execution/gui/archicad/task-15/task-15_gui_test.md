# GUI Test Report

Result: PASS-GUI

Task JSON: `task-15.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-15/eval-fixed/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If another project is open, close it without saving, then accept the IFC import library-parts dialog for the uploaded `init.ifc` using the default Embedded Library option.
3. In Floor Plan, select the Door Tool and place real Door elements in the internal partition walls until the model has at least five doors.
4. Select the Zone Tool and set both Zone Name and Zone No. to `CHAIR`.
5. Click inside one clinic room, accept any overlapping-zone warning, and place the zone stamp.
6. Set both Zone Name and Zone No. to `STERILIZATION`.
7. Click inside another clinic room, accept any overlapping-zone warning, and place the zone stamp.
8. Select the Window Tool and add one real window in an exterior wall so the model has at least two windows.
9. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
10. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`.
11. Confirm replacement of any previous `result.ifc`.
12. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains `RECEPTION`, `EXAM`, `STAFF`, and `WC` spaces. The passing GUI edit adds named `CHAIR` and `STERILIZATION` zones, enough real doors, and the missing window count.
