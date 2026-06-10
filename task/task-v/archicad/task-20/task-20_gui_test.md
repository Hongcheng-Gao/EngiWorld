# GUI Test Report

Result: PASS-GUI

Task JSON: `task-20.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-20/eval-gui-final/20260601-194951/`

## Reproducible GUI Procedure

1. Run the task config to upload `init.ifc` and launch Archicad.
2. Dismiss Windows startup dialogs if present, accept the Archicad EULA if shown, then accept the IFC import library-parts dialog using the default Embedded Library option.
3. In Floor Plan on `0. Ground Floor`, use the Door Tool to place one additional real Door in an exterior wall.
4. Use the Window Tool to place one additional real Window in an exterior wall.
5. Use the Roof Tool with the rectangular hip-roof construction method to draw a roof over the building footprint.
6. Use the Zone Tool in manual polygon mode to create lower-storey Zones with both Zone Name and Zone No. set to `LOBBY` and `STAIR`.
7. Switch to `1. Level 2` in the Navigator and use the Zone Tool in manual polygon mode to create a Zone with both Zone Name and Zone No. set to `UPPER ROOM`.
8. Return to `0. Ground Floor`, select the Stair Tool, and draw a straight stair baseline inside the building from the lower storey to `1. Level 2`.
9. Use File > Save As and save to `C:\Users\user\Desktop\result.ifc`.
10. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`.
11. Confirm replacement of any previous `result.ifc`.
12. Run eval with `--skip-config --evaluate`.

## Notes

The init model already contains two storeys, two slabs, eight walls, two doors, two windows, and `LOWER`/`UPPER` spaces. The passing GUI edit adds the required named Zones, roof, real Stair, and enough real Door/Window elements. The final remote eval returned `True`.
