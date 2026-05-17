task-46 — Define three net classes in a schematic
==================================================

Open init_file/board.sch in EAGLE. The <classes> block currently
contains only the default class 0. Add three more net classes:

    class 1  name=SIG     width=0.15 mm
    class 2  name=PWR     width=0.4  mm
    class 3  name=HSPEED  width=0.2  mm

GUI steps:
  1. Edit -> Net classes (opens the class editor dialog).
  2. Click in the first empty row and type name/width.
  3. Repeat for all three classes.
  4. Save as classed.sch.

Equivalent SCR recipe:
    CLASS SIG 0.15mm;
    CLASS PWR 0.4mm;
    CLASS HSPEED 0.2mm;
    WRITE;

Deliverable: classed.sch with a <classes> block containing these
three named classes with the matching widths.
