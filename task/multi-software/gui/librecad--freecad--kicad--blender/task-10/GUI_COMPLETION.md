# GUI Completion Record: task-10

Status: real four-application GT generated and evaluator validation passed on 2026-08-13.

Instance: `i-yeslqxefpc4c5qx3440g` (`freecad-librecad-kicad-blender`). Versions: LibreCAD 2.2.0.2, FreeCAD 0.21.2, KiCad 10.0.2, Blender 4.2.3.

The init DXF remains unchanged at SHA-256 `158ca3449ddad17fdad0d071e0ad0f78898bb6b8caee21bafd4c4cfe57520a82`. It is a valid construction seed: a 135 x 85 guide rectangle, diagonals, four corner-hole references, and seed labels; the U opening and two optical pocket holes are intentionally absent.

The prior six GT files were invalid: stage1 did not encode a closed U opening, the STL was a full box, the board had zero pads and zero nets, the SVG was not PCBNEW Plot output, and the GLB lacked mesh-bound SVG/pockets/red emissive beam. All six were replaced by the native workflow recorded in `ground_truth/GT_GENERATION.md`.

The evaluator accepts equivalent label positions, plausible alternative central top-connected U openings, and native line/rectangle/arc board outlines that form the same simple 135 x 85 boundary. It rejects open/missing U geometry, solid boxes or surface-only holes, disconnected handoffs, text-only KiCad boards, missing functional nets, invisible/self-crossing SVG, inactive/malformed GLB graphs, displaced imports, missing/misaligned pockets, and absent/non-red/non-emissive beam geometry.

On first FreeCAD launch, Document Recovery exposed stale task-08/task-09 transient records not visible to the prior filename-only cleanup. They were removed through FreeCAD's own `Cleanup...` confirmation before task-10 modeling. Final task-10 cleanup is recorded in the repository-level repair report.
