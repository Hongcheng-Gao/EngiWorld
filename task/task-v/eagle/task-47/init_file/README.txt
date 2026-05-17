task-49 — Assign specific nets to a named net class
====================================================

Open init_file/assign.sch in EAGLE's schematic editor. Its <classes>
block already defines the HSPEED class as class number 3. The five
nets (VCC, GND, CLK, DATA, RESET) all currently carry class="0".

Task: assign nets CLK and DATA to class HSPEED (class number 3).
Leave VCC, GND, and RESET unchanged on class 0.

GUI steps:
  * Right-click each of CLK and DATA -> Properties -> set Class
    to HSPEED. Save as assigned.sch.

Equivalent SCR recipe (File -> Execute Script):
    CLASS '3' CLK;
    CLASS '3' DATA;
    WRITE assigned.sch;

Deliverable: assigned.sch where <net name="CLK"/> and <net name="DATA"/>
both carry class="3" and the other nets still carry class="0".
