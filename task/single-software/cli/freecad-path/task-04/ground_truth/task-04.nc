(Exported by FreeCAD)
(Post Processor: linuxcnc_post)
(Output Time:2026-08-12 00:17:59.445748)
(begin preamble)
G17 G54 G40 G49 G80 G90
G21
(begin operation: T1 D5 Twist Drill S7000 F500)
(machine units: mm/min)
(T1 D5 Twist Drill S7000 F500) 
M5
M6 T1 
G43 H1 
M3 S7000 
(finish operation: T1 D5 Twist Drill S7000 F500)
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: D5 through drill-tip depth 13 mm)
(machine units: mm/min)
(D5 through drill-tip depth 13 mm) 
(Begin Drilling) 
G0 Z8.000 
G90 
G98 
G0 X-15.000 Y10.000 
G81 X-15.000 Y10.000 Z-13.000 F500.000 R2.000 
G0 X-45.000 Y-10.000 
G81 X-45.000 Y-10.000 Z-13.000 F500.000 R2.000 
G80 
G0 Z5.000 
G0 Z8.000 
(finish operation: D5 through drill-tip depth 13 mm)
(begin operation: D5 blind drill-tip depth 5 mm)
(machine units: mm/min)
(D5 blind drill-tip depth 5 mm) 
(Begin Drilling) 
G0 Z8.000 
G90 
G98 
G0 X15.000 Y-10.000 
G81 X15.000 Y-10.000 Z-5.000 F500.000 R2.000 
G0 X45.000 Y10.000 
G81 X45.000 Y10.000 Z-5.000 F500.000 R2.000 
G80 
G0 Z5.000 
G0 Z8.000 
(finish operation: D5 blind drill-tip depth 5 mm)
(begin operation: T2 D6 Twist Drill S7000 F500)
(machine units: mm/min)
(T2 D6 Twist Drill S7000 F500) 
M5
M6 T2 
G43 H2 
M3 S7000 
(finish operation: T2 D6 Twist Drill S7000 F500)
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: D6 through drill-tip depth 13 mm)
(machine units: mm/min)
(D6 through drill-tip depth 13 mm) 
(Begin Drilling) 
G0 Z8.000 
G90 
G98 
G0 X-5.000 Y-10.000 
G81 X-5.000 Y-10.000 Z-13.000 F500.000 R2.000 
G0 X-35.000 Y10.000 
G81 X-35.000 Y10.000 Z-13.000 F500.000 R2.000 
G80 
G0 Z5.000 
G0 Z8.000 
(finish operation: D6 through drill-tip depth 13 mm)
(begin operation: D6 blind drill-tip depth 5 mm)
(machine units: mm/min)
(D6 blind drill-tip depth 5 mm) 
(Begin Drilling) 
G0 Z8.000 
G90 
G98 
G0 X25.000 Y10.000 
G81 X25.000 Y10.000 Z-5.000 F500.000 R2.000 
G80 
G0 Z5.000 
G0 Z8.000 
(finish operation: D6 blind drill-tip depth 5 mm)
(begin operation: T3 D7 Twist Drill S7000 F500)
(machine units: mm/min)
(T3 D7 Twist Drill S7000 F500) 
M5
M6 T3 
G43 H3 
M3 S7000 
(finish operation: T3 D7 Twist Drill S7000 F500)
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: D7 through drill-tip depth 13 mm)
(machine units: mm/min)
(D7 through drill-tip depth 13 mm) 
(Begin Drilling) 
G0 Z8.000 
G90 
G98 
G0 X5.000 Y10.000 
G81 X5.000 Y10.000 Z-13.000 F500.000 R2.000 
G0 X-25.000 Y-10.000 
G81 X-25.000 Y-10.000 Z-13.000 F500.000 R2.000 
G80 
G0 Z5.000 
G0 Z8.000 
(finish operation: D7 through drill-tip depth 13 mm)
(begin operation: D7 blind drill-tip depth 5 mm)
(machine units: mm/min)
(D7 blind drill-tip depth 5 mm) 
(Begin Drilling) 
G0 Z8.000 
G90 
G98 
G0 X35.000 Y-10.000 
G81 X35.000 Y-10.000 Z-5.000 F500.000 R2.000 
G80 
G0 Z5.000 
G0 Z8.000 
(finish operation: D7 blind drill-tip depth 5 mm)
(begin postamble)
M05
G17 G54 G90 G80 G40
M2
