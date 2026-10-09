# CLI task-08 completion record

- Snapshot `kicad-openscad-freecad-blender`, `10.0.6.56`; evaluated 2026-08-13 with KiCad 10.0.4, OpenSCAD 2021.01, FreeCAD 1.1.0 revision 20260325, Blender 5.2.0 LTS.
- Repair: productive cwd is checked against `/home/user/Desktop`, not the isolated submission directory. GT/init unchanged.
- Checks: real GT `True`; optional package metadata equivalent `True`; forged FreeCAD `1.1.00` `False` because no valid ordered/hashed/direct FreeCAD stage remained.
- Cleanup: base/equivalent/forged directories and upload removed; audit path, Desktop entry, and related CAD process counts all zero.
- Sources: https://docs.kicad.org/10.0/en/cli/cli.html ; https://github.com/openscad/openscad/releases/tag/openscad-2021.01 ; https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.0 ; https://www.blender.org/releases/5-2/
