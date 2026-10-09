[English](README.txt) | [简体中文](README_CN.txt)

task-46 – Class the schematic nets
==================================

Open init_file/board.sch in EAGLE and save the result as
`classed.sch`.

Add these net classes:

    class 1  name=SIG     width=0.15 mm
    class 2  name=PWR     width=0.4  mm
    class 3  name=HSPEED  width=0.2  mm

Class the nets as follows:

  - `SIG`: `N$1`, `N$2`, `N$3`, `N$4`
  - `PWR`: `GND`, `VCC`, `+12V`
  - `HSPEED`: `A0` through `A4`, and `B0` through `B7`

Equivalent SCR recipe:

    CLASS SIG 0.15mm;
    CLASS PWR 0.4mm;
    CLASS HSPEED 0.2mm;
    WRITE;

Do not change any parts, wires, or pin connections.
