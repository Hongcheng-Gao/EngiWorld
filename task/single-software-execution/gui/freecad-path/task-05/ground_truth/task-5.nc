(Exported by FreeCAD)
(Post Processor: linuxcnc_post)
(Output Time:2026-08-14 22:32:06.829733)
(begin preamble)
G17 G54 G40 G49 G80 G90
G21
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: T2 90 Degree Chamfer S7000 F500)
(machine units: mm/min)
(T2 90 Degree Chamfer S7000 F500) 
M5
M6 T2 
G43 H2 
M3 S7000 
(finish operation: T2 90 Degree Chamfer S7000 F500)
(begin operation: Deburr 0.5 mm outer contour and four hole mouths)
(machine units: mm/min)
(Deburr 0.5 mm outer contour and four hole mouths) 
(Native Deburr Width 0.5 mm on one outside contour and four D5 hole mouths) 
G0 Z17.000 
G0 X60.100 Y40.000 
G0 Z15.000 
G1 X60.100 Y40.000 Z11.500 F250.000 
G1 X60.100 Y-40.000 Z11.500 F500.000 
G2 X60.000 Y-40.100 Z11.500 I-0.100 J-0.000 F500.000 
G1 X-60.000 Y-40.100 Z11.500 F500.000 
G2 X-60.100 Y-40.000 Z11.500 I-0.000 J0.100 F500.000 
G1 X-60.100 Y40.000 Z11.500 F500.000 
G2 X-60.000 Y40.100 Z11.500 I0.100 J0.000 F500.000 
G1 X60.000 Y40.100 Z11.500 F500.000 
G2 X60.100 Y40.000 Z11.500 I0.000 J-0.100 F500.000 
G0 Z17.000 
G0 Z17.000 
G0 X-22.600 Y-15.000 
G0 Z15.000 
G1 X-22.600 Y-15.000 Z11.500 F250.000 
G3 X-22.600 Y-15.000 Z11.500 I-2.400 J0.000 F500.000 
G0 Z17.000 
G0 Z17.000 
G0 X27.400 Y-15.000 
G0 Z15.000 
G1 X27.400 Y-15.000 Z11.500 F250.000 
G3 X27.400 Y-15.000 Z11.500 I-2.400 J0.000 F500.000 
G0 Z17.000 
G0 Z17.000 
G0 X-22.600 Y15.000 
G0 Z15.000 
G1 X-22.600 Y15.000 Z11.500 F250.000 
G3 X-22.600 Y15.000 Z11.500 I-2.400 J0.000 F500.000 
G0 Z17.000 
G0 Z17.000 
G0 X27.400 Y15.000 
G0 Z15.000 
G1 X27.400 Y15.000 Z11.500 F250.000 
G3 X27.400 Y15.000 Z11.500 I-2.400 J0.000 F500.000 
G0 Z17.000 
G0 Z17.000 
(finish operation: Deburr 0.5 mm outer contour and four hole mouths)
(begin postamble)
M05
G17 G54 G90 G80 G40
M2
