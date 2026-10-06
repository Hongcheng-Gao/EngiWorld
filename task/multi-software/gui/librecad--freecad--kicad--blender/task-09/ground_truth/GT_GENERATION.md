# Ground Truth Generation: task-09

All six GT artifacts were generated on 2026-08-13 in snapshot instance `i-yeslqxefpc4c5qx3440g`, using LibreCAD 2.2.0.2, FreeCAD 0.21.2, KiCad PCB Editor 10.0.2, and Blender 4.2.3. No package-generated or synthetic artifact is used as GT.

## Native Workflow

1. LibreCAD opened the supplied seed DXF. The GUIDE entities were removed and the final drawing was saved as `stage1_wearable_charger_cradle.dxf`: one closed 105 x 48 OUTLINE, two separate closed STRAP_SLOT rectangles, six exact HOLE circles, and four LABEL texts.
2. FreeCAD imported that DXF. Its real model contains a 105 x 48 x 20 cradle, a recessed 61 x 30 x 14 cavity, six cylindrical through-holes, and two rectangular through slots. FreeCAD exported the selected body to STL and separately exported four connected outline lines plus `FREECAD_TO_KICAD` and `EW4G09` as the handoff DXF.
3. KiCad 10.0.2 loaded the handoff outline and saved a native board. Six native footprints (`POGO-P1`, `POGO-P2`, `CHG-U1`, `MAGNET-M1`, `USB-J1`, `NTC-R1`) carry 12 pads and the six required functional nets. PCBNEW Plot generated the Edge.Cuts SVG.
4. Blender imported the STL with its STL importer and the PCBNEW SVG with its SVG importer. The scene includes the full-scale imported artifacts, two gold metallic pogo cylinders, and two red strap-slot highlights. A validation pass found the initially imported SVG displaced from the cradle; it was realigned in Blender and the corrected scene was exported again through Blender's glTF Binary exporter.

Post-generation evaluator hardening did not change any frozen GT artifact. An isolated rerun accepted the real GT and a stage-1 label-placement equivalent, while a board whose exact `VBAT` pad-net assignments were renamed to the substring lookalike `NOTVBAT` was rejected. This confirms KiCad 10 exact net-name handling.

## Artifact Hashes

```text
787af8849b1cda1dcd63f86d37f794426f6cab9e2b80301697c5e12436eaff45  stage1_wearable_charger_cradle.dxf
b6e822e5c15530905d65b95f9625cb963a26e61fe587999b5ea1cb1b1e3061cf  stage2_wearable_charger_cradle.stl
14aa0f7b33ab70c571a149f9911ae16dd0439657a1254247840e960e4830bbb0  stage2_wearable_charger_cradle_handoff_outline.dxf
502269513da86f91f66ba148c5faf618c4134d7050fc5d7689bb3450ee859e6e  stage3_wearable_charger_cradle_board.kicad_pcb
f101e1b79df3f0d4c468a33bc900df5e2a83d61b06dd08bbb2ff88217b321e4a  stage3_wearable_charger_cradle_board_profile.svg
f9394c1cff2e7329442e18d994416ea7e6fd3109e0043c6331abe5f12d440ef2  stage4_wearable_charger_cradle.glb
```

## Official References

- LibreCAD 2.2.0.2 release: https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- LibreCAD 2.2 manual: https://docs.librecad.org/en/2.2.0_a/
- FreeCAD 0.21.2 release: https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- FreeCAD Draft DXF and mesh export: https://wiki.freecad.org/Draft_DXF and https://wiki.freecad.org/Mesh_Export
- KiCad 10.0.2 release: https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/
- KiCad 10 footprints, board outlines, and plotting: https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#working-with-footprints, https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#board-outlines, and https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- Blender 4.2 STL, SVG, and glTF: https://docs.blender.org/manual/en/4.2/files/import_export/stl.html, https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html, and https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
