# Ground Truth Generation: task-02

All six ground-truth deliverables were generated in the assigned `freecad-librecad-kicad-blender` snapshot, not by dataset package writers. The init seed was not modified.

## Snapshot Software

- LibreCAD 2.2.0.2
- FreeCAD 0.21.2 revision 33771
- KiCad PCB Editor 10.0.2
- Blender 4.2.3 LTS

## Real Application Chain

1. LibreCAD opened the uploaded seed and saved a closed six-edge hex outline, three mounting circles, the central vent circle, seven grille bars, and four labels as `stage1_hex_air_quality_badge.dxf`.
2. FreeCAD imported that exact DXF. The model produced a detailed watertight badge STL with grille ribs and three drilled raised standoffs. The same document exported the closed hex, vent circle, and two ShapeString label outlines as the KiCad handoff DXF.
3. KiCad 10.0.2 created a native pcbnew board with six Edge.Cuts lines, four real footprints and 22 pads, a Dwgs.User vent marker, and F.SilkS transfer text. KiCad's native plot operation produced the six-path SVG.
4. Blender 4.2.3 imported the STL and SVG, converted the SVG to a visible mesh, corrected the import's meter scale to a full-size 110 x 96 mm profile, added three distinct standoff meshes and two sensor-module meshes, and exported the active scene as GLB.

The evaluator treats the seven GT grille Y positions as this artifact's implementation, not mandatory coordinates: other independent horizontal bars wholly inside the radius-18 vent are reasonable equivalents.

## Frozen Hashes

| Artifact | SHA-256 |
|---|---|
| `stage1_hex_air_quality_badge.dxf` | `e99069cab70169b2b778ec4501d99b290cf582f3156ee5883a3913b16a24ffe3` |
| `stage2_hex_air_quality_badge.stl` | `02ea7025dd60e70fa20cd692a5d8433c7f465fe384468ffe50670dc1fec70769` |
| `stage2_hex_air_quality_badge_handoff_outline.dxf` | `f9d426db4aabb4a275fa9f4b0d5b01411de31af00ee28dd73eac1c968a4c6b62` |
| `stage3_hex_air_quality_badge_board.kicad_pcb` | `c4a49ebbce98895bca732d44268677d4c1f104d8175b380b45c23557b69f2c4e` |
| `stage3_hex_air_quality_badge_board_profile.svg` | `b045ddfb958b53c1ef9456265475f65cde0cce5e7aad429de2c81d70ee704555` |
| `stage4_hex_air_quality_badge.glb` | `d9638707f1db6842c735017de00b67795832bf38a0c0b4819d377f0d0d4ad4bb` |

Init seed SHA-256: `f7118819615369c4ee362a6c5ac908872ef9deb78bf43e76109ddf1574d00929`.

## Official References

- LibreCAD release and tools: https://github.com/LibreCAD/LibreCAD/releases/tag/2.2.0.2 and https://docs.librecad.org/en/2.2.0_a/ref/tools.html
- FreeCAD release, DXF, and mesh export: https://github.com/FreeCAD/FreeCAD/releases/tag/0.21.2, https://wiki.freecad.org/Draft_DXF, and https://wiki.freecad.org/Mesh_Export
- KiCad release, graphics import, footprints, board outlines, and plotting: https://www.kicad.org/blog/2026/05/KiCad-10.0.2-Release/ and https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html
- Blender 4.2 STL, SVG, and glTF: https://docs.blender.org/manual/en/4.2/files/import_export/stl.html, https://docs.blender.org/manual/en/4.2/addons/import_export/curve_svg.html, and https://docs.blender.org/manual/en/4.2/addons/import_export/scene_gltf2.html
