#!/usr/bin/env python3
"""Print UUIDs for answer.kicad_pcb verification."""
import hashlib

seed = "kicad-72-seed"

def make_uuid(identifier):
    h = hashlib.md5(f"{seed}:{identifier}".encode()).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

# Footprints
print("R1:", make_uuid("R1"))
print("R2:", make_uuid("R2"))
print("C1:", make_uuid("C1"))
print("Q1:", make_uuid("Q1"))

# Segments: sx,sy,ex,ey,layer,net
# segment 1: start=10.5,10 end=19.5,10 layer=F.Cu net=2
print("seg1:", make_uuid("10.5,10,19.5,10,F.Cu,2"))
# segment 2: start=20.5,10 end=29.25,10 layer=F.Cu net=3
print("seg2:", make_uuid("20.5,10,29.25,10,F.Cu,3"))
# segment 3: start=10,10.5 end=10,20 layer=F.Cu net=1
print("seg3:", make_uuid("10,10.5,10,20,F.Cu,1"))

# Vias: at_x,at_y,layer1,layer2
print("via1:", make_uuid("10,20,F.Cu,B.Cu"))
print("via2:", make_uuid("30,15,F.Cu,B.Cu"))
