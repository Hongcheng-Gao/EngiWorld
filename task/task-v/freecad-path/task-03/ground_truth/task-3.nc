(Exported by FreeCAD)
(Post Processor: linuxcnc_post)
(Output Time:2026-08-14 20:39:12.427492)
(begin preamble)
G17 G54 G40 G49 G80 G90
G21
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: T1 90 degree spot drill S8000 F250)
(machine units: mm/min)
(T1 90 degree spot drill S8000 F250) 
M5
M6 T1 
G43 H1 
M3 S8000 
(finish operation: T1 90 degree spot drill S8000 F250)
(begin operation: T1 90 degree spot drilling at four marks)
(machine units: mm/min)
(T1 90 degree spot drilling at four marks) 
(T1 90 degree spot drilling at four marks) 
(Begin Drilling) 
G0 Z5.000 
G90 
G98 
G0 X-25.000 Y-15.000 
G81 X-25.000 Y-15.000 Z-1.500 F250.000 R1.000 
G0 X-25.000 Y15.000 
G81 X-25.000 Y15.000 Z-1.500 F250.000 R1.000 
G0 X25.000 Y15.000 
G81 X25.000 Y15.000 Z-1.500 F250.000 R1.000 
G0 X25.000 Y-15.000 
G81 X25.000 Y-15.000 Z-1.500 F250.000 R1.000 
G80 
G0 Z2.000 
G0 Z5.000 
(finish operation: T1 90 degree spot drilling at four marks)
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: T2 D5 drill S5000 F180)
(machine units: mm/min)
(T2 D5 drill S5000 F180) 
M5
M6 T2 
G43 H2 
M3 S5000 
(finish operation: T2 D5 drill S5000 F180)
(begin operation: T2 D5 through drilling one millimeter beyond bottom)
(machine units: mm/min)
(T2 D5 through drilling one millimeter beyond bottom) 
(T2 D5 through drilling one millimeter beyond bottom) 
(Begin Drilling) 
G0 Z5.000 
G90 
G98 
G0 X-25.000 Y-15.000 
G81 X-25.000 Y-15.000 Z-14.473 F180.000 R1.000 
G0 X-25.000 Y15.000 
G81 X-25.000 Y15.000 Z-14.473 F180.000 R1.000 
G0 X25.000 Y15.000 
G81 X25.000 Y15.000 Z-14.473 F180.000 R1.000 
G0 X25.000 Y-15.000 
G81 X25.000 Y-15.000 Z-14.473 F180.000 R1.000 
G80 
G0 Z2.000 
G0 Z5.000 
(finish operation: T2 D5 through drilling one millimeter beyond bottom)
(begin postamble)
M05
G17 G54 G90 G80 G40
M2
