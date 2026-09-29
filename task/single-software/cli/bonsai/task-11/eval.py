#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
import ifcopenshell.geom
DESKTOP=Path("/home/user/Desktop")
SPEC={'task': 'BONSAI-CLI-11', 'counts': {'IfcSpace': 4, 'IfcWall': 7, 'IfcDoor': 4, 'IfcWindow': 2, 'IfcGroup': 1, 'IfcWallType': 1}, 'groups': {'Residential Unit R-11': ['Living', 'Kitchen', 'Bedroom', 'Bath']}, 'types': {'IfcWall': 'ApartmentWallType'}, 'markers': {'IfcSpace': ['Living', 'Kitchen', 'Bedroom', 'Bath'], 'IfcWall': ['South Wall', 'East Wall', 'North Wall', 'West Wall', 'Partition 1', 'Partition 2', 'Partition 3'], 'IfcDoor': ['Main Entrance', 'Door Bedroom', 'Door Kitchen', 'Door Bath'], 'IfcWindow': ['North Window', 'East Window']}}
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
    if not baseline_preserved(m): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
