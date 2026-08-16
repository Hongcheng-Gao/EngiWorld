# Task-04 Ground Truth Generation

Generated independently on 2026-08-12 in the designated `freecad-librecad-kicad-blender` snapshot. No package-generated or offline replacement artifact is used.

- LibreCAD 2.2.0.2 opened the provided seed, removed GUIDE, and saved the stage-1 DXF with one OUTLINE circle, one WINDOW circle, four HOLE circles, and four LABEL texts.
- FreeCAD 0.21.2 imported stage 1. A real circular bezel with a center opening, four mounting holes, raised rim, encoder boss, and 18 mm total-height knob was exported by FreeCAD's mesh exporter. The same document exported one r59 interface circle, four holes, and two ShapeString label blocks through FreeCAD's DXF exporter.
- KiCad 10.0.2 created a native pcbnew board with one circular Edge.Cuts item, five semantic footprints, 17 pads, and native F.SilkS transfer text. The exact KiCad AppImage exporter plotted the Edge.Cuts SVG.
- Blender 4.2.3 imported the real stage-2 STL and stage-3 SVG, corrected SVG millimetre scale, retained the native import objects, added a dark translucent OLED lens and raised encoder knob, and exported the GLB. A full-scale beveled circular curve derived inside Blender keeps the open SVG profile visible in glTF.

The GT's internal 4 mm and 8 mm levels and Blender object names are implementation details, not hidden requirements. Equivalent multi-level 18 mm bezels and renamed scene objects pass when their geometry, materials, source handoffs, and spatial assembly satisfy the instruction.

Frozen artifact SHA-256:

```text
480812f17d824cd87d549d6b1dcfdc8a1b8bd6ed2ec4af296efc2bf3f627fe30  stage1_round_gauge_bezel.dxf
dcb0ae73d6c6bf776a6db1815c2b7153706b5190f3529b44b7c3368045348f26  stage2_round_gauge_bezel.stl
62bf47eab678911405cc3abffad66b2bad3bf40917170ce10cd261ef84420988  stage2_round_gauge_bezel_handoff_outline.dxf
d0c2052926f8110d814067f8925a94e502c669e03cd47b682a8bc6af7858d7e0  stage3_round_gauge_bezel_board.kicad_pcb
4710a9af4fc6381897aac7393f3daa3aefa0f0aa35a20a6f7e2a30cd62e44815  stage3_round_gauge_bezel_board_profile.svg
6f5c59a73607e56c369769be0e7d4731e476191d7bdc285c5f5e6302dbb9aa13  stage4_round_gauge_bezel.glb
```

The unchanged init seed SHA-256 is `4baa03a16239e89d81e2bb9dcbd89f8204a9864add9310b6549f0a588df3df43`.

Official references:

- https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2
- https://docs.librecad.org/en/2.2.0_a/
- https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2
- https://wiki.freecad.org/Draft_DXF
- https://wiki.freecad.org/Mesh_Export
- https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#board-outlines
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#working-with-footprints
- https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html#plotting
- https://docs.blender.org/manual/en/4.2/files/import_export/stl.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html
- https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
