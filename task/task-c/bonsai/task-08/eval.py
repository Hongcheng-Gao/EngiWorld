#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop"); TASK="BONSAI-CLI-08"; PRODUCTS=['C1', 'C2', 'C3', 'C4', 'B1', 'B2', 'B3', 'B4', 'Deck Slab']
def finish(ok): print("True" if ok else "False"); raise SystemExit(0)
def norm(v): return re.sub(r"\s+"," ",str(v or "").strip()).lower()
def eq(a,b): return norm(a)==norm(b)
def psets(e):
    try: return ifcopenshell.util.element.get_psets(e, should_inherit=True)
    except Exception: return {}
def prop(e,k):
    for ps in psets(e).values():
        for key,val in ps.items():
            if key!='id' and eq(key,k): return val
    return None
def marker(e): return eq(prop(e,'TaskCode'),TASK) and eq(prop(e,'AutomationStatus'),'CLI_UPDATED')
def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if len(m.by_type('IfcStructuralAnalysisModel'))!=1 or len(m.by_type('IfcColumn'))!=4 or len(m.by_type('IfcBeam'))!=4 or len(m.by_type('IfcSlab'))!=1: return False
    if len(m.by_type('IfcBuildingElementProxy')): return False
    sam=m.by_type('IfcStructuralAnalysisModel')[0]
    if not eq(sam.Name,'Primary Frame CLI') or not marker(sam): return False
    assigned=set()
    for rel in getattr(sam,'IsGroupedBy',None) or []:
        for o in rel.RelatedObjects: assigned.add(o.Name)
    if assigned!=set(PRODUCTS): return False
    for o in m.by_type('IfcColumn')+m.by_type('IfcBeam')+m.by_type('IfcSlab'):
        if not marker(o): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
