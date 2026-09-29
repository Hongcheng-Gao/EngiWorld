#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop"); TASK="BONSAI-CLI-10"; REFS={'IfcWall': {'South Wall': ('23-13 21 13', 'Exterior Walls'), 'East Wall': ('23-13 21 13', 'Exterior Walls'), 'North Wall': ('23-13 21 13', 'Exterior Walls'), 'West Wall': ('23-13 21 13', 'Exterior Walls')}, 'IfcSlab': {'Shell Slab': ('23-13 31 13', 'Floor Slabs')}, 'IfcDoor': {'Shell Door': ('23-17 11 00', 'Doors')}}
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
def refs_of(e):
    out=set()
    for rel in getattr(e,'HasAssociations',None) or []:
        r=getattr(rel,'RelatingClassification',None)
        if r: out.add((getattr(r,'Identification',None),getattr(r,'Name',None)))
    return out
def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if len(m.by_type('IfcWall'))!=4 or len(m.by_type('IfcSlab'))!=1 or len(m.by_type('IfcDoor'))!=1: return False
    if len(m.by_type('IfcClassification'))!=1 or len(m.by_type('IfcClassificationReference'))!=3: return False
    classification=m.by_type('IfcClassification')[0]
    if not eq(classification.Name,'OmniClass') or not eq(classification.Edition,'2012'): return False
    if len(m.by_type('IfcBuildingElementProxy')): return False
    for cls, items in REFS.items():
        for name, ref in items.items():
            objs=[o for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1 or not marker(objs[0]) or ref not in refs_of(objs[0]): return False
    d=m.by_type('IfcDoor')[0]
    if not eq(prop(d,'FireRating'),'60min') or norm(prop(d,'IsExternal')) not in ('true','1'): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
