#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop"); TASK="BONSAI-CLI-09"; QSPEC={'IfcSpace': {'Open Office': {'NetFloorArea': 20.0}, 'Meeting': {'NetFloorArea': 12.0}}, 'IfcWall': {'South Wall': {'NetSideArea': 18.0}, 'East Wall': {'NetSideArea': 18.0}, 'North Wall': {'NetSideArea': 18.0}, 'West Wall': {'NetSideArea': 18.0}, 'Meeting Partition': {'NetSideArea': 9.0}}, 'IfcSlab': {'Ground Slab': {'NetArea': 48.0}}}
def finish(ok): print("True" if ok else "False"); raise SystemExit(0)
def norm(v): return re.sub(r"\s+"," ",str(v or "").strip()).lower()
def eq(a,b): return norm(a)==norm(b)
def approx(a,b,t=0.05):
    try: return abs(float(a)-float(b))<=t
    except Exception: return False
def psets(e, qtos=False):
    try: return ifcopenshell.util.element.get_psets(e, should_inherit=True, qtos_only=qtos)
    except Exception: return {}
def val(e,k,qtos=False):
    for ps in psets(e,qtos).values():
        for key,v in ps.items():
            if key!='id' and eq(key,k): return v
    return None
def marker(e): return eq(val(e,'TaskCode'),TASK) and eq(val(e,'AutomationStatus'),'CLI_UPDATED')
def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if len(m.by_type('IfcSpace'))!=2 or len(m.by_type('IfcWall'))!=5 or len(m.by_type('IfcSlab'))!=1 or len(m.by_type('IfcElementQuantity'))!=8: return False
    if len(m.by_type('IfcBuildingElementProxy')): return False
    for cls, items in QSPEC.items():
        for name, props in items.items():
            objs=[o for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1 or not marker(objs[0]): return False
            for k,expected in props.items():
                if not approx(val(objs[0],k,True), expected): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
