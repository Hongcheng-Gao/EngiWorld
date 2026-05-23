Net-class cleanup plan for assign.sch

Use the net classes already defined in the schematic:
  SIG: class 1
  PWR: class 2
  HSPEED: class 3

Assign the nets as follows and save the schematic as answer.sch:
  VCC -> PWR
  GND -> PWR
  CLK -> HSPEED
  DATA -> HSPEED
  RESET -> SIG
