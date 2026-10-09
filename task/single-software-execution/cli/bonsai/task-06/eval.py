#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop")
TASK="BONSAI-CLI-06"
def finish(ok): print("True" if ok else "False"); raise SystemExit(0)
def norm(v): return re.sub(r"\s+"," ",str(v or "").strip()).lower()
def eq(a,b): return norm(a)==norm(b)
def approx(a,b,t=0.001):
    try: return abs(float(a)-float(b))<=t
    except Exception: return False
def psets(e):
    try: return ifcopenshell.util.element.get_psets(e, should_inherit=True)
    except Exception: return {}
def prop(e,k):
    nk=norm(k)
    for ps in psets(e).values():
        for key,val in ps.items():
            if key!='id' and norm(key)==nk: return val
    return None
def has_marker(e): return eq(prop(e,'TaskCode'),TASK) and eq(prop(e,'AutomationStatus'),'CLI_UPDATED')
def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if not str(m.schema).upper().startswith('IFC4'): return False
    if len(m.by_type('IfcProjectedCRS'))!=1 or len(m.by_type('IfcMapConversion'))!=1: return False
    if len(m.by_type('IfcSpace'))!=2 or len(m.by_type('IfcWall'))!=5 or len(m.by_type('IfcSlab'))!=1: return False
    if len(m.by_type('IfcBuildingElementProxy')): return False
    if not eq(m.by_type('IfcBuildingStorey')[0].Name,'GEO_LEVEL_00'): return False
    crs=m.by_type('IfcProjectedCRS')[0]; conv=m.by_type('IfcMapConversion')[0]
    if not eq(crs.Name,'EPSG:3857'): return False
    if not (approx(conv.Eastings,501234.0) and approx(conv.Northings,6843210.0) and approx(conv.OrthogonalHeight,35.0) and approx(conv.XAxisAbscissa,1.0) and approx(conv.XAxisOrdinate,0.0) and approx(conv.Scale,1.0)): return False
    for o in m.by_type('IfcSpace')+m.by_type('IfcWall')+m.by_type('IfcSlab'):
        if not has_marker(o): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
