#!/usr/bin/env python3
import re
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop")
SPEC={'task': 'BONSAI-CLI-02', 'counts': {'IfcProject': 1, 'IfcSite': 1, 'IfcBuilding': 1, 'IfcBuildingStorey': 1, 'IfcSpace': 3, 'IfcWall': 6, 'IfcSlab': 1, 'IfcDoor': 3, 'IfcWindow': 3, 'IfcOpeningElement': 6, 'IfcRelVoidsElement': 6, 'IfcRelFillsElement': 6, 'IfcWallType': 1, 'IfcSlabType': 1, 'IfcMaterial': 3, 'IfcMaterialLayerSet': 2}, 'names': {'IfcBuildingStorey': ['CLINIC_LEVEL_00'], 'IfcSpace': ['Consult 1', 'Consult 2', 'Corridor'], 'IfcWall': ['South Wall', 'East Wall', 'North Wall', 'West Wall', 'Corridor Partition', 'Room Split'], 'IfcSlab': ['Clinic Slab']}, 'space_refs': {'Consult 1': ('C-101', 'Clinical'), 'Consult 2': ('C-102', 'Clinical'), 'Corridor': ('COR-100', 'Circulation')}, 'groups': [], 'slab_marker': True, 'wall_type': ('ClinicWallType', 'ClinicWall-200mm', [('Masonry', 0.15), ('Gypsum Board', 0.05)]), 'slab_type': ('ClinicSlabType', 'ClinicSlab-200mm', [('Concrete', 0.2)])}
def finish(ok): print("True" if ok else "False"); raise SystemExit(0)
def norm(v): return re.sub(r"\s+"," ",str(v or "").strip()).lower()
def eq(a,b): return norm(a)==norm(b)
def approx(a,b,t=0.035):
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
def has_props(e, props): return all(eq(prop(e,k),v) for k,v in props.items())
def typ(e):
    try: return ifcopenshell.util.element.get_type(e)
    except Exception: return None
def mat(e):
    try: return ifcopenshell.util.element.get_material(e, should_skip_usage=True, should_inherit=True)
    except Exception: return None
def layer_match(m, name, layers):
    if m is None: return False
    if m.is_a('IfcMaterialLayerSetUsage'): m=m.ForLayerSet
    if not m.is_a('IfcMaterialLayerSet'): return False
    if not eq(getattr(m,'LayerSetName',None) or getattr(m,'Name',None), name): return False
    got=list(getattr(m,'MaterialLayers',None) or [])
    if len(got)!=len(layers): return False
    rem=[(norm(a),float(b)) for a,b in layers]
    for layer in got:
        mn=norm(getattr(getattr(layer,'Material',None),'Name',None)); th=getattr(layer,'LayerThickness',None)
        hit=None
        for i,(n,t) in enumerate(rem):
            if n in mn and approx(th,t): hit=i; break
        if hit is None: return False
        rem.pop(hit)
    return not rem
def container(e):
    if e.is_a('IfcSpace'):
        for rel in getattr(e,'Decomposes',None) or []:
            p=getattr(rel,'RelatingObject',None)
            if p and p.is_a('IfcBuildingStorey'): return p
    try: return ifcopenshell.util.element.get_container(e, should_get_direct=True)
    except Exception: return None
def geometry_exists(e):
    if e.is_a('IfcOpeningElement'): return True
    settings=ifcopenshell.geom.settings()
    try: settings.set(settings.USE_WORLD_COORDS, True)
    except Exception: pass
    try:
        shape = ifcopenshell.geom.create_shape(settings, e)
        return bool(shape.geometry.verts)
    except Exception: return False
def evaluate():
    path=DESKTOP/'result.ifc'
    if not path.is_file() or path.stat().st_size<1000: return False
    m=ifcopenshell.open(str(path))
    if not str(m.schema).upper().startswith('IFC4'): return False
    gids=[e.GlobalId for e in m.by_type('IfcRoot') if getattr(e,'GlobalId',None)]
    if len(gids)!=len(set(gids)): return False
    for cls,n in SPEC['counts'].items():
        if len(m.by_type(cls))!=n: return False
    for cls in ['IfcBuildingElementProxy','IfcFurniture']:
        if len(m.by_type(cls)): return False
    for cls,names in SPEC.get('names',{}).items():
        if {str(getattr(e,'Name',None) or '') for e in m.by_type(cls)} != set(names): return False
    marker={'TaskCode':SPEC['task'],'AutomationStatus':'CLI_UPDATED'}
    spaces={sp.Name:sp for sp in m.by_type('IfcSpace')}
    for name,vals in SPEC.get('space_refs',{}).items():
        sp=spaces.get(name)
        if not sp or not eq(prop(sp,'Reference'),vals[0]) or not eq(prop(sp,'OccupancyType'),vals[1]) or not has_props(sp,marker): return False
    for w in m.by_type('IfcWall'):
        if not has_props(w, marker): return False
    if SPEC.get('slab_marker'):
        for s in m.by_type('IfcSlab'):
            if not has_props(s, marker): return False
    if 'wall_type' in SPEC:
        ids={typ(w).id() if typ(w) else None for w in m.by_type('IfcWall')}
        if len(ids)!=1 or None in ids: return False
        wt=m.by_id(next(iter(ids))); tn,ls,layers=SPEC['wall_type']
        if not wt.is_a('IfcWallType') or not eq(wt.Name,tn) or not has_props(wt,marker) or not layer_match(mat(wt),ls,layers): return False
    if 'slab_type' in SPEC:
        ids={typ(s).id() if typ(s) else None for s in m.by_type('IfcSlab')}
        if len(ids)!=1 or None in ids: return False
        st=m.by_id(next(iter(ids))); tn,ls,layers=SPEC['slab_type']
        if not st.is_a('IfcSlabType') or not eq(st.Name,tn) or not has_props(st,marker) or not layer_match(mat(st),ls,layers): return False
    for gname,members in SPEC.get('groups',[]):
        groups=[g for g in m.by_type('IfcGroup') if eq(g.Name,gname)]
        if len(groups)!=1 or not has_props(groups[0],marker): return False
        assigned=set()
        for rel in getattr(groups[0],'IsGroupedBy',None) or []:
            for obj in getattr(rel,'RelatedObjects',None) or []: assigned.add(getattr(obj,'Name',None))
        if assigned!=set(members): return False
    for wall_name,props in SPEC.get('extra_wall_props',{}).items():
        walls=[w for w in m.by_type('IfcWall') if eq(w.Name,wall_name)]
        if len(walls)!=1 or not has_props(walls[0],props): return False
    storey_ids={s.id() for s in m.by_type('IfcBuildingStorey')}
    for prod in m.by_type('IfcWall')+m.by_type('IfcSlab')+m.by_type('IfcDoor')+m.by_type('IfcWindow')+m.by_type('IfcSpace'):
        c=container(prod)
        if c is None or c.id() not in storey_ids or not geometry_exists(prod): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
