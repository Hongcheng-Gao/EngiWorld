# Ground Truth Generation: task-10

All six GT artifacts were generated on 2026-08-13 in snapshot instance `i-yeslqxefpc4c5qx3440g`, using LibreCAD 2.2.0.2, FreeCAD 0.21.2, KiCad PCB Editor 10.0.2, and Blender 4.2.3. No package-generated or synthetic artifact is used as GT.

## Native Workflow

1. LibreCAD opened the supplied seed. GUIDE entities were deleted; the saved stage1 contains one closed 135 x 85 OUTLINE, one closed 39 x 55 top-connected BEAM_SLOT, six exact HOLE circles, and four LABEL texts.
2. FreeCAD imported stage1. A real Part body was built by cutting the U opening and all six cylindrical holes from a 135 x 85 x 32 solid. FreeCAD exported a watertight 3,076-triangle STL and a four-LINE handoff with `FREECAD_TO_KICAD` and `EW4G10` TEXT.
3. KiCad 10.0.2 used an official two-pad pin-header footprint placed through Footprint Chooser, then duplicated it through KiPython's version-specific `Duplicate(False)` API. Six native footprints carry 12 pads and six named nets. Native Edge.Cuts and Dwgs.User handoff texts were saved, and PCBNEW Plot produced the Edge.Cuts SVG.
4. Blender 4.2.3 imported the STL with `bpy.ops.wm.stl_import` and the PCBNEW SVG with `bpy.ops.import_curve.svg`. It added two dark pocket-rim meshes and one red emissive beam mesh. Validation found the initial SVG origin displaced; Blender realigned the imported SVG to the U fixture and exported the corrected scene again through its glTF Binary exporter.

## Artifact Hashes

```text
f47786b36d7e52a83cfa6f3565303ae87db129b908f1fd81b95683349d70d705  stage1_optical_gate_fixture.dxf
cd3a86ddbedf1b4f753a80aca3cb039747348ca52405e39e57ef4fdd3e3abaa3  stage2_optical_gate_fixture.stl
0b10911acd95e5f1f5cd9c6e5f287534c2a2747ba4a7bf6a3bc655b05a47f930  stage2_optical_gate_fixture_handoff_outline.dxf
179610bef955f2d1729e3c197ae57a3626c9ebfd81e8e42a8020a5538ba3f8fe  stage3_optical_gate_fixture_board.kicad_pcb
52260450baf1b5517aa7107086f13e67e5ee263419ac6b6320004b518a906b32  stage3_optical_gate_fixture_board_profile.svg
25fbd016c71b74cafa043584a8f5f2400621420ba5014194479a5fc44f28ea5f  stage4_optical_gate_fixture.glb
```

## Official References

- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://docs.librecad.org/en/2.2.0_a/
- https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- https://wiki.freecad.org/Draft_DXF and https://wiki.freecad.org/Mesh_Export
- https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#working-with-footprints
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#board-outlines
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
