(Exported by FreeCAD)
(Post Processor: linuxcnc_post)
(Output Time:2026-08-14 02:42:58.314712)
(begin preamble)
G17 G54 G40 G49 G80 G90
G21
(begin operation: Fixture)
(machine units: mm/min)
G54 
(finish operation: Fixture)
(begin operation: ToolController T1 D3 Spot Drill Holder D12)
(machine units: mm/min)
(ToolController T1 D3 Spot Drill Holder D12) 
M5
M6 T1 
G43 H1 
M3 S7000 
(finish operation: ToolController T1 D3 Spot Drill Holder D12)
(begin operation: T1 spot drill 13 safe holes after Collision Filter)
(machine units: mm/min)
(T1 spot drill 13 safe holes after Collision Filter) 
(T1 spot drill 13 safe holes after Collision Filter) 
(Begin Drilling) 
G0 Z23.000 
G90 
G98 
G0 X-15.000 Y-9.000 
G81 X-15.000 Y-9.000 Z17.000 F500.000 R20.000 
G0 X-15.000 Y-27.000 
G81 X-15.000 Y-27.000 Z17.000 F500.000 R20.000 
G0 X15.000 Y-27.000 
G81 X15.000 Y-27.000 Z17.000 F500.000 R20.000 
G0 X15.000 Y-9.000 
G81 X15.000 Y-9.000 Z17.000 F500.000 R20.000 
G0 X15.000 Y9.000 
G81 X15.000 Y9.000 Z17.000 F500.000 R20.000 
G0 X15.000 Y27.000 
G81 X15.000 Y27.000 Z17.000 F500.000 R20.000 
G0 X-15.000 Y27.000 
G81 X-15.000 Y27.000 Z17.000 F500.000 R20.000 
G0 X-15.000 Y9.000 
G81 X-15.000 Y9.000 Z17.000 F500.000 R20.000 
G0 X-45.000 Y9.000 
G81 X-45.000 Y9.000 Z17.000 F500.000 R20.000 
G0 X-45.000 Y-9.000 
G81 X-45.000 Y-9.000 Z17.000 F500.000 R20.000 
G0 X-45.000 Y-27.000 
G81 X-45.000 Y-27.000 Z17.000 F500.000 R20.000 
G0 X45.000 Y-9.000 
G81 X45.000 Y-9.000 Z17.000 F500.000 R20.000 
G0 X45.000 Y9.000 
G81 X45.000 Y9.000 Z17.000 F500.000 R20.000 
G80 
G0 Z20.000 
G0 Z23.000 
(finish operation: T1 spot drill 13 safe holes after Collision Filter)
(begin operation: ToolController T2 D5 Twist Drill Holder D12)
(machine units: mm/min)
(ToolController T2 D5 Twist Drill Holder D12) 
M5
M6 T2 
G43 H2 
M3 S7000 
(finish operation: ToolController T2 D5 Twist Drill Holder D12)
(begin operation: T2 drill 13 safe holes to Z8 after Collision Filter)
(machine units: mm/min)
(T2 drill 13 safe holes to Z8 after Collision Filter) 
(T2 drill 13 safe holes to Z8 after Collision Filter) 
(Begin Drilling) 
G0 Z23.000 
G90 
G98 
G0 X-15.000 Y-9.000 
G81 X-15.000 Y-9.000 Z8.000 F500.000 R20.000 
G0 X-15.000 Y-27.000 
G81 X-15.000 Y-27.000 Z8.000 F500.000 R20.000 
G0 X15.000 Y-27.000 
G81 X15.000 Y-27.000 Z8.000 F500.000 R20.000 
G0 X15.000 Y-9.000 
G81 X15.000 Y-9.000 Z8.000 F500.000 R20.000 
G0 X15.000 Y9.000 
G81 X15.000 Y9.000 Z8.000 F500.000 R20.000 
G0 X15.000 Y27.000 
G81 X15.000 Y27.000 Z8.000 F500.000 R20.000 
G0 X-15.000 Y27.000 
G81 X-15.000 Y27.000 Z8.000 F500.000 R20.000 
G0 X-15.000 Y9.000 
G81 X-15.000 Y9.000 Z8.000 F500.000 R20.000 
G0 X-45.000 Y9.000 
G81 X-45.000 Y9.000 Z8.000 F500.000 R20.000 
G0 X-45.000 Y-9.000 
G81 X-45.000 Y-9.000 Z8.000 F500.000 R20.000 
G0 X-45.000 Y-27.000 
G81 X-45.000 Y-27.000 Z8.000 F500.000 R20.000 
G0 X45.000 Y-9.000 
G81 X45.000 Y-9.000 Z8.000 F500.000 R20.000 
G0 X45.000 Y9.000 
G81 X45.000 Y9.000 Z8.000 F500.000 R20.000 
G80 
G0 Z20.000 
G0 Z23.000 
(finish operation: T2 drill 13 safe holes to Z8 after Collision Filter)
(begin postamble)
M05
G17 G54 G90 G80 G40
M2
