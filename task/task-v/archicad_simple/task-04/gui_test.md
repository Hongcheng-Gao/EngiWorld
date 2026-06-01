# GUI Test Report

Result: PASS-GUI

Task JSON: `task-04.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-04/eval-fixed/result.json`

## Reproducible GUI Procedure

1. Create or use an `ArchiCAD-27` Windows instance and run the task config.
2. Dismiss startup dialogs and create a blank project from the default template.
3. Draw a compact single-storey kiosk footprint about 10 m by 6 m with real Wall elements.
4. Add interior partition walls to form `RETAIL`, `BACK ROOM`, and `WC`.
5. Draw one real Slab element covering the footprint.
6. Place at least three real Door elements and at least two real Window elements.
7. Use the Zone Tool in manual polygon mode to create:
   - `RETAIL`, with Zone Name and Zone No. both set to `RETAIL`.
   - `BACK ROOM`, with Zone Name and Zone No. both set to `BACK ROOM`.
   - `WC`, with Zone Name and Zone No. both set to `WC`.
8. Use the Shell/Roof tool to add a small real roof element over the kiosk. Keep it compact and low; an oversized shell roof can make the exported overall Z span fail the evaluator.
9. Save As `C:\Users\user\Desktop\result.ifc`.
10. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save.
11. Run eval with `--skip-config --evaluate`.

## Notes

The final passing export contained `IfcRoof` and had an overall shaped span of about `10.05 m x 6.07 m x 4.12 m`.
