task-22 — Add a zero-ohm net-tie between AGND and DGND
=======================================================

GOAL
----
Open `mixed.sch` (a minimal schematic with four parts, C1/C2 on AGND and
R1/R2 on DGND). ADD a 0 ohm resistor named `R_TIE` (deviceset `R-EU_`,
device `R0402`, package R0402, from `rcl.lbr`), then use NAME to connect
its pin 1 to AGND and pin 2 to DGND, establishing a single controlled
tie-point between the two ground nets. Save the result as `tied.sch`.

WHAT THE GRADER CHECKS
----------------------
1. `tied.sch` is well-formed XML.
2. A <part name="R_TIE"> element is present under <schematic>/<parts>.
3. The AGND net contains a <pinref part="R_TIE" pin="1"/>.
4. The DGND net contains a <pinref part="R_TIE" pin="2"/>.
5. C1 and C2 remain connected to AGND (their pinrefs are preserved).
6. R1 and R2 remain connected to DGND (their pinrefs are preserved).
7. AGND and DGND remain as separate <net> elements (not merged).

FILES
-----
- mixed.sch : the starter schematic with 4 parts and 2 grounds.
- rcl.lbr   : EAGLE's bundled rcl.lbr for resolving R-EU_ R0402 in the
              GUI via `USE rcl.lbr; ADD R-EU_R0402@rcl 'R_TIE' ...`.

HINTS
-----
Typical EAGLE GUI command sequence (in the schematic editor):

    USE rcl.lbr;
    ADD R-EU_R0402@rcl 'R_TIE' (90 40);
    VALUE R_TIE 0R;
    NAME AGND (85 40);   # R_TIE pin 1 is at (x - 5.08, y) from placement
    NAME DGND (95 40);   # R_TIE pin 2 is at (x + 5.08, y)
    WRITE tied.sch;

(Exact coordinates may vary; the grader only inspects the XML structure,
not geometry.)
