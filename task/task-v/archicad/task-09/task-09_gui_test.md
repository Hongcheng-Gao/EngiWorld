# GUI Test Report

Result: PASS-GUI

Task JSON: `task-09.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-09/eval/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. If Archicad is already open on another project, close that project without saving, then accept the IFC import library-parts dialog for the uploaded `init.ifc` using the default Embedded Library option.
3. In Floor Plan, select the Zone Tool.
4. Set both Zone Name and Zone No. to `OFFICE`.
5. Click inside the left room to create the zone, accept the overlapping-zone warning if shown, and click inside the room again to place the zone stamp.
6. Set both Zone Name and Zone No. to `STORAGE`.
7. Click inside the right room, accept the overlap warning if shown, and place the zone stamp.
8. Set both Zone Name and Zone No. to `WC`.
9. Click inside the right room/lower area, accept the overlap warning if shown, and place the zone stamp.
10. Use File > Save As, save to `C:\Users\user\Desktop\result.ifc`.
11. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save and overwrite any previous `result.ifc`.
12. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains the required building shell, slab, doors, and windows. The passing GUI edit adds correctly named Archicad Zones so the IFC4 export includes `IfcSpace` entries named `OFFICE`, `STORAGE`, and `WC`.
