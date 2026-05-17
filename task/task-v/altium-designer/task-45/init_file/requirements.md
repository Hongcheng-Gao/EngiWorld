# Draftsman Release Requirements (task-46)

This document describes the deliverable Draftsman file `release.PCBDwf`
for the `ready_to_release.PcbDoc` board. The file must contain **two
sheets** (pages) with the following mandatory elements.

## Sheet 1 — Fabrication (`SheetName=Fabrication`)

Place the following objects on Sheet 1:

| Qty  | Type                | Notes                                               |
| ---- | ------------------- | --------------------------------------------------- |
| 1    | BoardView           | Top view of the fabrication drawing                 |
| 1    | DrillTable          | Grouped by hole diameter                            |
| 1    | LayerStackLegend    | Layer / copper thickness / dielectric / Dk columns  |
| 1    | FabricationNotes    | Text block: finished thickness, soldermask, silk, surface finish |
| 1    | TitleBlock          | Must carry AT LEAST 10 `Parameter` child objects    |
| 4 +  | DimensionAnnotation | Board-frame linear dimensions                       |
| 2 +  | RadiusAnnotation    | Corner / hole-to-hole radii                         |

## Sheet 2 — Assembly (`SheetName=Assembly`)

Place the following objects on Sheet 2:

| Qty | Type               | Notes                                        |
| --- | ------------------ | -------------------------------------------- |
| 2   | BoardAssemblyView  | One with `Side=Top`, one with `Side=Bottom`  |
| 1   | BOMTable           | BOM table (qty + supplier columns)           |
| 1   | AssemblyNotes      | Text block with assembly notes               |
| 1   | RevisionTable      | Revision history                             |
| 1   | TitleBlock         | Assembly-sheet title block                   |

## File format

The `.PCBDwf` text serialisation used here is an INI-style document.
Each sheet starts with a `[SheetN]` header declaring `SheetName=` and
`ObjectCount=` (plus sheet-size metadata). Each object on that sheet
lives in its own section `[SheetN.ObjectM]` with a `Type=` field and
whatever object-specific attributes apply.

TitleBlock's Parameter children are declared inside the TitleBlock
section as numbered sub-entries `ParameterN.Name=` / `ParameterN.Value=`.

## Output

Write the final Draftsman file to `output/release.PCBDwf`.
