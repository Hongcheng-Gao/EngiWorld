task-30 — QFN-8 package in a new library
=========================================

Deliverable: qfn8.lbr

Create a fresh EAGLE library from scratch. In the library editor, author
a single PCB <package> describing a QFN-8 part:

  * Body:      5 mm x 5 mm, centered on the origin
  * Pitch:     0.5 mm
  * Pads/side: 2 (for 8 total pads)
  * Pad size:  0.25 x 0.6 mm (the 0.6 mm dimension extends outward)
  * Numbering: IPC convention — pad 1 at top-left working CCW.

Typical pad layout (SMD command, dx/dy are the pad rectangle width/height):

    SMD 1: x=-2.35 y= 0.25 dx=0.6 dy=0.25  (left edge, upper)
    SMD 2: x=-2.35 y=-0.25 dx=0.6 dy=0.25  (left edge, lower)
    SMD 3: x=-0.25 y=-2.35 dx=0.25 dy=0.6  (bottom edge, left)
    SMD 4: x= 0.25 y=-2.35 dx=0.25 dy=0.6  (bottom edge, right)
    SMD 5: x= 2.35 y=-0.25 dx=0.6 dy=0.25  (right edge, lower)
    SMD 6: x= 2.35 y= 0.25 dx=0.6 dy=0.25  (right edge, upper)
    SMD 7: x= 0.25 y= 2.35 dx=0.25 dy=0.6  (top edge, right)
    SMD 8: x=-0.25 y= 2.35 dx=0.25 dy=0.6  (top edge, left)

Also draw a silkscreen outline on layer 21 (tPlace) with WIRE, plus a
pin-1 dot (small circle/polygon on layer 21 near pad 1).  Save as
qfn8.lbr.

The grader checks structurally:
  * exactly 1 <package> in the library
  * exactly 8 <smd> children
  * pad names are the strings "1".."8"
  * at least one <wire> or <polygon> on layer 21 (silkscreen)
