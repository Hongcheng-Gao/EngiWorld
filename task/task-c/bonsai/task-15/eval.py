#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop")
SPEC={'task': 'BONSAI-CLI-15', 'counts': {'IfcSpace': 1, 'IfcWall': 4, 'IfcSlab': 1, 'IfcRoof': 1, 'IfcDoor': 1, 'IfcWindow': 4, 'IfcOpeningElement': 5, 'IfcRoofType': 1}, 'types': {'IfcRoof': 'EntranceCanopyType'}, 'markers': {'IfcSpace': ['Lobby'], 'IfcWall': ['South Wall', 'East Wall', 'North Wall', 'West Wall'], 'IfcSlab': ['Base Slab'], 'IfcRoof': ['Entrance Canopy'], 'IfcDoor': ['Accessible Entrance Door'], 'IfcWindow': ['North Window A', 'North Window B', 'East Window A', 'West Window A']}, 'props': {'IfcWindow': {'North Window A': {'GlazingStatus': 'UPGRADED', 'RegisterCode': 'BONSAI-CLI-15'}, 'North Window B': {'GlazingStatus': 'UPGRADED', 'RegisterCode': 'BONSAI-CLI-15'}, 'East Window A': {'GlazingStatus': 'UPGRADED', 'RegisterCode': 'BONSAI-CLI-15'}, 'West Window A': {'GlazingStatus': 'UPGRADED', 'RegisterCode': 'BONSAI-CLI-15'}}}}
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
def marker(e): return eq(prop(e,'TaskCode'),SPEC['task']) and eq(prop(e,'AutomationStatus'),'CLI_UPDATED')
def typ(e):
    try: return ifcopenshell.util.element.get_type(e)
    except Exception: return None
def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if not str(m.schema).upper().startswith('IFC4'): return False
    for cls,n in SPEC['counts'].items():
        if len(m.by_type(cls))!=n: return False
    if len(m.by_type('IfcBuildingElementProxy')): return False
    for cls,names in SPEC.get('names',{}).items():
        if {str(o.Name or '') for o in m.by_type(cls)} != set(names): return False
    for cls,names in SPEC.get('markers',{}).items():
        for name in names:
            objs=[o for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1 or not marker(objs[0]): return False
    for gname,members in SPEC.get('groups',{}).items():
        groups=[g for g in m.by_type('IfcGroup') if eq(g.Name,gname)]
        if len(groups)!=1 or not marker(groups[0]): return False
        got=set()
        for rel in getattr(groups[0],'IsGroupedBy',None) or []:
            for o in rel.RelatedObjects: got.add(o.Name)
        if got!=set(members): return False
    for cls, type_name in SPEC.get('types',{}).items():
        ids={typ(o).id() if typ(o) else None for o in m.by_type(cls)}
        if len(ids)!=1 or None in ids: return False
        t=m.by_id(next(iter(ids)))
        if not eq(t.Name,type_name) or not marker(t): return False
    for cls, props in SPEC.get('props',{}).items():
        for name, pmap in props.items():
            objs=[o for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1: return False
            for k,v in pmap.items():
                if not eq(prop(objs[0],k),v): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
