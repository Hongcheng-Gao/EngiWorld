# GUI Completion Record: task-08

Status: modified to a GUI-friendly KiCad-to-Blender handoff and verified against the task evaluator.

Remote instance used for validation: `115.191.26.197` (`freecad-librecad-kicad-blender`). The final GT/eval validation result was `PASS`. After this task's validation run, Desktop clean: `yes`; related GUI processes clean: `yes`.

## Why This Task Was Modified

The original task asked Blender to import or load `stage3_*_board_profile.dxf` from KiCad. On the provided instance, Blender 4.2.3 has built-in STL, SVG, FBX, and glTF support, but no bundled DXF import add-on. That made the original KiCad-DXF-to-Blender step not reliably GUI-completable. The task logic is unchanged: LibreCAD still creates the mechanical 2D source, FreeCAD still creates the 3D body and KiCad handoff, KiCad still creates the PCB/profile handoff, and Blender still consumes the FreeCAD and KiCad artifacts. The KiCad-to-Blender handoff format was changed from DXF to SVG because Blender can import SVG through its GUI.

## Task-Specific Targets

- Token: `EW4G08`
- Design: Eight-channel terminal cover with numbered windows
- Stage 1 DXF: `stage1_terminal_cover_long.dxf`
- Stage 1 layers: OUTLINE, WINDOW, HOLE, LABEL
- Stage 1 envelope: `165 mm x 52 mm`
- Required circles: (8, 8) r=2.2; (157, 8) r=2.2; (8, 44) r=2.2; (157, 44) r=2.2
- Required LibreCAD labels: EW4G08, CH1, CH8, 24V, GND
- Stage 2 STL: `stage2_terminal_cover_long.stl` with approximate size `165 x 52 x 14 mm`
- Stage 2 handoff DXF: `stage2_terminal_cover_long_handoff_outline.dxf`
- Stage 3 KiCad board: `stage3_terminal_cover_long_board.kicad_pcb`
- Stage 3 Blender handoff SVG: `stage3_terminal_cover_long_board_profile.svg`
- Stage 3 board tokens: EW4G08, TERM1, TERM2, TERM3, TERM4, TERM5, TERM6, TERM7, TERM8, 24V, GND
- Stage 4 GLB: `stage4_terminal_cover_long.glb`
- Stage 4 GLB GUI-export evidence: Blender glTF Binary must contain `stage2_terminal_cover_long` from the imported STL and `stage3_terminal_cover_long_board_profile.svg` from the imported SVG object name; no manual material/token metadata is required. The SVG file itself is separately checked for `EDGE_FROM_STAGE2_HANDOFF`.

## Reproducible GUI Workflow

1. Run the task config so `seed_terminal_cover_long.dxf` appears on the Desktop. Open the seed DXF in LibreCAD from the GUI.
2. In LibreCAD, use the layer panel to create or activate `OUTLINE, WINDOW, HOLE, LABEL`. Use the seed GUIDE geometry as construction reference only. Redraw or convert the final outline on `OUTLINE`, create the feature lines on the task-specific feature layer, place the required circles on `HOLE` or the feature layer as appropriate, and add the listed labels on `LABEL`. Delete every `GUIDE` entity before saving. Use `File > Save As` to save `/home/user/Desktop/stage1_terminal_cover_long.dxf`.
3. Open FreeCAD from the GUI and import `stage1_terminal_cover_long.dxf`. Use Part/Draft/Part Design GUI operations to make a body matching the XY envelope, extrude it to about `14 mm`, and export the selected body with `File > Export` as `/home/user/Desktop/stage2_terminal_cover_long.stl`. From the same model, create a top-face or board-interface outline and add visible text labels `FREECAD_TO_KICAD` and `EW4G08`. Export that outline from the GUI as `/home/user/Desktop/stage2_terminal_cover_long_handoff_outline.dxf`.
4. Launch KiCad from the GUI using the installed AppImage if it is not in the launcher: `/home/user/Applications/kicad-10.0.2/kicad-10.0.2-x86_64.AppImage`. In PCB Editor, create a new board, import `stage2_terminal_cover_long_handoff_outline.dxf` as `Edge.Cuts`, and add F.SilkS text for `KICAD_TO_BLENDER`, `EDGE_FROM_STAGE2_HANDOFF`, the handoff filename, `EW4G08`, and all board tokens listed above. Save the native board as `/home/user/Desktop/stage3_terminal_cover_long_board.kicad_pcb`. Then use KiCad's GUI plot/export workflow to export the same board outline/profile as SVG to `/home/user/Desktop/stage3_terminal_cover_long_board_profile.svg`.
5. Open Blender from the GUI. Import `/home/user/Desktop/stage2_terminal_cover_long.stl` with `File > Import > STL`, then import `/home/user/Desktop/stage3_terminal_cover_long_board_profile.svg` with `File > Import > Scalable Vector Graphics (.svg)`. Keep the imported STL object and SVG curves visible in the scene; the evaluator expects Blender GUI import evidence such as `stage2_terminal_cover_long` and `stage3_terminal_cover_long_board_profile.svg`. Do not use scripts, macros, background export, or custom metadata injection. Export glTF Binary from the GUI with `File > Export > glTF 2.0` as `/home/user/Desktop/stage4_terminal_cover_long.glb`.
6. Run the task evaluator. The evaluator checks every intermediate file, parses the LibreCAD/FreeCAD DXF files with `ezdxf`, parses the STL with `trimesh`, checks the KiCad board text and SVG handoff, and parses the Blender GLB with `pygltflib`.

## Files Changed For GUI Completion

- Added the native KiCad stage file: `stage3_terminal_cover_long_board.kicad_pcb`.
- Replaced the old KiCad-to-Blender DXF handoff with the Blender-importable SVG handoff: `stage3_terminal_cover_long_board_profile.svg`.
- Updated `instruction`, `flow_spec.json`, `eval.py`, `GT_GENERATION.md`, and ground-truth artifacts so the required files and evaluator checks are consistent.

## Instance Evidence Added 2026-07-08

This task was rechecked on the provided instance `115.191.26.197` after the SVG handoff change. The evidence below validates the GUI handoff paths and the evaluator on the instance; it is not a claim that every final deliverable was manually redrawn from the seed during this pass.

1. Opened the task-specific seed DXF in the LibreCAD GUI from `/home/user/Desktop`.
2. Opened the task-specific stage-1 DXF in the FreeCAD GUI and confirmed FreeCAD imported the drawing as model objects.
3. Opened the task-specific KiCad board in KiCad PCB Editor through the KiCad GUI binaries and confirmed the PCB Editor window loaded the board.
4. Opened Blender 4.2.3 GUI, used `File > Import > Scalable Vector Graphics (.svg)`, and imported the task-specific stage-3 SVG handoff through Blender's file browser. The Blender window became modified, confirming the GUI import path consumed the SVG.
5. Ran `/home/user/Desktop/eval.py` against the Desktop artifacts. Result: `True`, with all intermediate checks passing.
6. Cleaned the instance after the task. Final check: Desktop count `0`; no LibreCAD, FreeCAD, KiCad, PCB Editor, Blender, QtWebEngine, or update-manager processes remained; only the Desktop Icons window was listed.
## Strict Blender GUI Export Evidence Added 2026-07-08

A second validation pass created `stage4_terminal_cover_long.glb` through Blender's GUI instead of uploading the package-generated GLB. For this pass, the task-specific intermediate files through stage 3 were placed on the Desktop, Blender imported `stage2_terminal_cover_long.stl` with `File > Import > STL`, imported `stage3_terminal_cover_long_board_profile.svg` with `File > Import > Scalable Vector Graphics (.svg)`, and exported `stage4_terminal_cover_long.glb` with `File > Export > glTF 2.0` in glTF Binary format. The updated evaluator returned `True` for that GUI-exported GLB, and the instance was cleaned afterward. Evidence files for this pass are under `/tmp/engiworld_gui4_blender_export_only/task-08`.


## Downloaded GUI GT Evidence Added 2026-07-08

A final validation pass generated `stage4_terminal_cover_long.glb` on the provided instance through GUI operations and downloaded that exact GLB into this task's `ground_truth` directory. The pass used Blender GUI import for `stage2_terminal_cover_long.stl` and `stage3_terminal_cover_long_board_profile.svg`, Blender GUI glTF export, and then a GUI file-manager rename when Blender's file browser kept the default `untitled.glb` name. The renamed file content is the Blender GUI export. The updated evaluator returned `True`, wrote `score.json` with `score: 1.0`, and the instance was cleaned afterward. Evidence files for this downloaded-GT pass are under `/tmp/engiworld_gui4_downloaded_gui_gt/task-08`.
