#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop")
SPEC={'task': 'BONSAI-CLI-17', 'schema': 'IFC4', 'counts': {'IfcDuctSegment': 3, 'IfcDuctFitting': 2, 'IfcAirTerminal': 2, 'IfcDistributionSystem': 1, 'IfcDistributionPort': 13, 'IfcRelConnectsPorts': 12}, 'markers': {'IfcDuctSegment': ['Main Segment 1', 'Main Segment 2', 'Branch Segment'], 'IfcDuctFitting': ['Bend Fitting', 'Transition Fitting'], 'IfcAirTerminal': ['Terminal East', 'Terminal North']}, 'systems': {'Supply Air': {'members': ['Bend Fitting', 'Branch Segment', 'Main Segment 1', 'Main Segment 2', 'Terminal East', 'Terminal North', 'Transition Fitting'], 'products': {'Bend Fitting': {'ports': 2, 'connections': 4}, 'Branch Segment': {'ports': 2, 'connections': 4}, 'Main Segment 1': {'ports': 2, 'connections': 2}, 'Main Segment 2': {'ports': 2, 'connections': 4}, 'Terminal East': {'ports': 1, 'connections': 2}, 'Terminal North': {'ports': 1, 'connections': 2}, 'Transition Fitting': {'ports': 3, 'connections': 6}}}}, 'props': {'IfcDuctSegment': {'Main Segment 1': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}, 'Main Segment 2': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}, 'Branch Segment': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}}, 'IfcDuctFitting': {'Bend Fitting': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}, 'Transition Fitting': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}}, 'IfcAirTerminal': {'Terminal East': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}, 'Terminal North': {'AirflowZone': 'SA-17', 'CommissioningStatus': 'BALANCED'}}}}
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
def rel_group_members(g):
    got=set()
    for rel in getattr(g,'IsGroupedBy',None) or []:
        for o in rel.RelatedObjects: got.add(str(getattr(o,'Name','') or ''))
    return got
def nested_ports(entity):
    ports=[]
    for rel in getattr(entity,'IsNestedBy',None) or []:
        for obj in getattr(rel,'RelatedObjects',None) or []:
            if obj.is_a('IfcDistributionPort'): ports.append(obj)
    return ports
def connected_count(port):
    return len({rel.id() for rel in (getattr(port,'ConnectedTo',None) or []) + (getattr(port,'ConnectedFrom',None) or [])})
def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if SPEC.get('schema') and not str(m.schema).upper().startswith(SPEC['schema']): return False
    for cls,n in SPEC.get('counts',{}).items():
        try: actual=len(m.by_type(cls))
        except Exception: actual=0
        if actual!=n: return False
    for cls in SPEC.get('forbidden',[]):
        try:
            if len(m.by_type(cls)): return False
        except Exception: pass
    for cls,names in SPEC.get('markers',{}).items():
        for name in names:
            objs=[o for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1 or not marker(objs[0]): return False
    for cls,type_name in SPEC.get('types',{}).items():
        objs=m.by_type(cls)
        if not objs: return False
        ids={typ(o).id() if typ(o) else None for o in objs}
        if len(ids)!=1 or None in ids: return False
        t=m.by_id(next(iter(ids)))
        if not eq(t.Name,type_name) or not marker(t): return False
    for cls,mapprops in SPEC.get('props',{}).items():
        for name,pmap in mapprops.items():
            objs=[o for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1: return False
            for k,v in pmap.items():
                if not eq(prop(objs[0],k),v): return False
    for gname,members in SPEC.get('groups',{}).items():
        groups=[g for g in m.by_type('IfcGroup') if eq(g.Name,gname)]
        if len(groups)!=1 or not marker(groups[0]): return False
        if rel_group_members(groups[0])!=set(members): return False
    for sname, data in SPEC.get('systems',{}).items():
        systems=[s for s in m.by_type('IfcDistributionSystem') if eq(s.Name,sname)]
        if len(systems)!=1 or not marker(systems[0]): return False
        members=set()
        for rel in m.by_type('IfcRelAssignsToGroup'):
            if getattr(rel,'RelatingGroup',None) and rel.RelatingGroup.id()==systems[0].id():
                for o in rel.RelatedObjects: members.add(str(getattr(o,'Name','') or ''))
        if members!=set(data['members']): return False
        for name in data.get('products',{}):
            objs=[o for cls in ('IfcDuctSegment','IfcDuctFitting','IfcAirTerminal') for o in m.by_type(cls) if eq(o.Name,name)]
            if len(objs)!=1 or not marker(objs[0]): return False
            ports=nested_ports(objs[0])
            exp=data['products'][name]
            if len(ports)!=exp['ports'] or sum(connected_count(p) for p in ports)!=exp['connections']: return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
