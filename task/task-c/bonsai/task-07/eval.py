#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop"); TASK="BONSAI-CLI-07"; PRODUCTS=['Main Segment', 'Branch Spine', 'Riser Segment', 'Transition', 'Bend', 'Terminal East', 'Terminal North']
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
    if len(m.by_type('IfcDistributionSystem'))!=1 or len(m.by_type('IfcDistributionPort'))!=12 or len(m.by_type('IfcRelConnectsPorts'))!=12: return False
    if len(m.by_type('IfcDuctSegment'))!=3 or len(m.by_type('IfcDuctFitting'))!=2 or len(m.by_type('IfcAirTerminal'))!=2: return False
    s=m.by_type('IfcDistributionSystem')[0]
    if not eq(s.Name,'Supply Air Verified') or not marker(s): return False
    assigned=set()
    for rel in getattr(s,'IsGroupedBy',None) or []:
        for o in rel.RelatedObjects: assigned.add(o.Name)
    if assigned!=set(PRODUCTS): return False
    for o in m.by_type('IfcDuctSegment')+m.by_type('IfcDuctFitting')+m.by_type('IfcAirTerminal'):
        if not marker(o): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
