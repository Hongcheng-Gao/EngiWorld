# GUI Test Report

Result: PASS-GUI

Task JSON: `task-07.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-07/eval/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload and open `init.ifc` in Archicad.
2. Accept the IFC import library-parts dialog with the default Embedded Library option.
3. In Floor Plan, select the Door Tool and place one real Door element in an exterior wall.
4. Select the Window Tool and place one real Window element in an exterior wall.
5. Complete the opening orientation prompts by clicking the room side.
6. Save As `C:\Users\user\Desktop\result.ifc`.
7. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save.
8. Run eval with `--skip-config --evaluate`.

## Notes

The init model already preserves the `ROOM 101` space and shell. The passing GUI edit only needed to add a real door and a real window.
