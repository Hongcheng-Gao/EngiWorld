#!/usr/bin/env python3
import re
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
DESKTOP=Path("/home/user/Desktop")
SPEC={'task': 'BONSAI-CLI-05', 'counts': {'IfcProject': 1, 'IfcSite': 1, 'IfcBuilding': 1, 'IfcBuildingStorey': 1, 'IfcSpace': 4, 'IfcWall': 8, 'IfcSlab': 1, 'IfcDoor': 2, 'IfcWindow': 4, 'IfcOpeningElement': 6, 'IfcRelVoidsElement': 6, 'IfcRelFillsElement': 6, 'IfcWallType': 1, 'IfcGroup': 2, 'IfcMaterial': 2, 'IfcMaterialLayerSet': 1}, 'names': {'IfcBuildingStorey': ['DUPLEX_LEVEL_00'], 'IfcSpace': ['A Living', 'A Bed', 'B Living', 'B Bed'], 'IfcWall': ['South Wall West', 'South Wall East', 'East Wall', 'North Wall', 'West Wall', 'Party Wall', 'Partition A', 'Partition B'], 'IfcSlab': ['Duplex Slab']}, 'space_refs': {'A Living': ('A-LIV', 'Residential'), 'A Bed': ('A-BED', 'Residential'), 'B Living': ('B-LIV', 'Residential'), 'B Bed': ('B-BED', 'Residential')}, 'groups': [('Unit A', ['A Living', 'A Bed']), ('Unit B', ['B Living', 'B Bed'])], 'slab_marker': False, 'wall_type': ('DuplexWallType', 'DuplexWall-200mm', [('Masonry', 0.15), ('Gypsum Board', 0.05)]), 'extra_wall_props': {'Party Wall': {'AcousticRating': 'STC-55'}}}
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
# ENGIWORLD_BASELINE_PRESERVATION_V1
PRESERVED_CLASSES = (
    'IfcSpace', 'IfcWall', 'IfcSlab', 'IfcRoof', 'IfcDoor', 'IfcWindow',
    'IfcColumn', 'IfcBeam', 'IfcDuctSegment', 'IfcDuctFitting', 'IfcAirTerminal',
)


def _safe_by_type(model, class_name):
    try:
        return model.by_type(class_name)
    except RuntimeError:
        return []


def _root_key(entity):
    gid = str(getattr(entity, 'GlobalId', '') or '').strip()
    if gid:
        return ('gid', gid)
    return ('name', entity.is_a(), str(getattr(entity, 'Name', '') or ''))


def _name_key(entity):
    return ('name', entity.is_a(), str(getattr(entity, 'Name', '') or ''))


def _product_index(model):
    result = {}
    for class_name in PRESERVED_CLASSES:
        for entity in _safe_by_type(model, class_name):
            result.setdefault(_root_key(entity), []).append(entity)
            result.setdefault(_name_key(entity), []).append(entity)
    return result


def _container_key(entity):
    try:
        container = ifcopenshell.util.element.get_container(entity)
    except Exception:
        container = None
    return _root_key(container) if container is not None else None


def _geometry_signature(settings, entity):
    if not getattr(entity, 'Representation', None):
        return None
    try:
        shape = ifcopenshell.geom.create_shape(settings, entity)
    except Exception:
        return None
    coordinates = shape.geometry.verts
    points = [
        tuple(round(float(coordinates[index + offset]), 5) for offset in range(3))
        for index in range(0, len(coordinates), 3)
    ]
    faces = shape.geometry.faces
    triangles = []
    for index in range(0, len(faces), 3):
        triangles.append(tuple(sorted((
            points[faces[index]], points[faces[index + 1]], points[faces[index + 2]],
        ))))
    return tuple(sorted(triangles))


def _relation_keys(model, class_name):
    relationships = set()
    for relation in _safe_by_type(model, class_name):
        if class_name == 'IfcRelVoidsElement':
            relationships.add((_root_key(relation.RelatingBuildingElement), _root_key(relation.RelatedOpeningElement)))
        elif class_name == 'IfcRelFillsElement':
            relationships.add((_root_key(relation.RelatingOpeningElement), _root_key(relation.RelatedBuildingElement)))
        elif class_name == 'IfcRelNests':
            relationships.update((_root_key(relation.RelatingObject), _root_key(item)) for item in relation.RelatedObjects)
    return relationships


def baseline_preserved(result_model):
    roots = _safe_by_type(result_model, 'IfcRoot')
    gids = [str(getattr(entity, 'GlobalId', '') or '').strip() for entity in roots]
    if any(not gid for gid in gids) or len(gids) != len(set(gids)):
        return False
    init_path = DESKTOP / 'init.ifc'
    if not init_path.is_file() or init_path.stat().st_size < 1000:
        return False
    baseline = ifcopenshell.open(str(init_path))
    result_index = _product_index(result_model)
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    for class_name in PRESERVED_CLASSES:
        for source in _safe_by_type(baseline, class_name):
            candidates = result_index.get(_root_key(source), [])
            if len(candidates) != 1:
                candidates = result_index.get(_name_key(source), [])
            if len(candidates) != 1:
                return False
            target = candidates[0]
            source_geometry = _geometry_signature(settings, source)
            if source_geometry is not None and source_geometry != _geometry_signature(settings, target):
                return False
            if _container_key(source) != _container_key(target):
                return False
    for class_name in ('IfcRelVoidsElement', 'IfcRelFillsElement', 'IfcRelNests'):
        if not _relation_keys(baseline, class_name).issubset(_relation_keys(result_model, class_name)):
            return False
    return True

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
    if not baseline_preserved(m): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
