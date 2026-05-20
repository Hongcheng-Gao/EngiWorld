task-20 — 10-pin CONN10 symbol in a new library
================================================

Deliverable: conn10.lbr

Create a fresh EAGLE library. In the library editor:

  1. File -> New -> Library (or open the library editor directly).
  2. Edit -> Symbol -> create a new symbol named "CONN10".
  3. Use the PIN command ten times to place pins 1..10. A typical
     layout is five pins down the left edge (1..5) and five pins
     down the right edge (6..10), on a 0.1 inch / 2.54 mm grid.
  4. Each pin must have direction="pas" (passive) — that is the
     default for the PIN command.
  5. Add a rectangle body on layer 94 (Symbols) and the standard
     >NAME / >VALUE placeholder texts on layers 95 / 96.
  6. (Optional) Wrap the symbol in a <deviceset> so the library is
     usable in a schematic.
  7. File -> Save As -> conn10.lbr

The grader checks structurally:
  * exactly 1 <symbol> in the library
  * symbol name == CONN10
  * exactly 10 <pin> children
  * pin names are the literal strings "1".."10"
  * every pin has direction="pas"
