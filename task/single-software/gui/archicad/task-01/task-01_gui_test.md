# GUI Test Report

Result: PASS-GUI

Task JSON: `task-01.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-01/fresh-eval-02/result.json`

## Reproducible GUI Procedure

1. Create a fresh `ArchiCAD-27` Windows instance and run the task config.
2. If Windows shows Shutdown Event Tracker, type a short comment in the Comment field and click OK.
3. Launch Archicad 27 from the taskbar or desktop shortcut.
4. On the Archicad start screen, click New.
5. Accept the EULA if shown, then create a new project with the default Archicad 27 template.
6. In Floor Plan, use the Wall Tool to draw four wall segments forming a small rectangle. At the initial template zoom, a rectangle around 40 px by 32 px produced an exported span of about 5.5 m by 4.5 m, within the task tolerance.
7. Use the Slab Tool to draw one rectangular slab covering the room.
8. Use the Door Tool to place one door on the top wall.
9. Use the Window Tool to place one window on the right wall.
10. Use the Zone Tool with manual polygon construction:
    - Set Zone Name to `OFFICE 101`.
    - Set Zone No. also to `OFFICE 101`.
    - Draw a zone polygon inside the room and click inside it to place the zone label.
11. Use Save As, set file name to `C:\Users\user\Desktop\result.ifc`.
12. Set Save as type to `IFC Files (*.ifc)`.
13. Set Translator to `IFC4 Design Transfer View-based Export`.
14. Click Save.
15. Run eval with `--skip-config --evaluate`.

## Notes

The Zone No. field must contain `OFFICE 101`. Archicad exports the IFC space `Name` from the Zone No. field and the IFC space `LongName` from the Zone Name field; this task's eval checks `Name` first.
