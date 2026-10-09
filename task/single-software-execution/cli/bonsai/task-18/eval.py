#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
import ifcopenshell.geom
DESKTOP=Path("/home/user/Desktop")
SPEC={'task': 'BONSAI-CLI-18', 'schema': 'IFC4', 'counts': {'IfcBuildingStorey': 2, 'IfcSpace': 2, 'IfcWall': 8, 'IfcSlab': 2, 'IfcRoof': 1, 'IfcWallType': 1, 'IfcSlabType': 1, 'IfcGroup': 1}, 'types': {'IfcWall': 'ExtWallType-A', 'IfcSlab': 'SlabType-A'}, 'markers': {'IfcSpace': ['GF Office', 'UF Office'], 'IfcWall': ['W-S', 'W-S-UP', 'W-N', 'W-N-UP', 'W-W', 'W-W-UP', 'W-E', 'W-E-UP'], 'IfcSlab': ['GF Slab', 'UF Slab'], 'IfcRoof': ['Roof']}, 'props': {'IfcSpace': {'GF Office': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'UF Office': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}}, 'IfcWall': {'W-S': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-S-UP': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-N': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-N-UP': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-W': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-W-UP': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-E': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'W-E-UP': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}}, 'IfcSlab': {'GF Slab': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}, 'UF Slab': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}}, 'IfcRoof': {'Roof': {'MigrationStatus': 'IFC4_NORMALIZED', 'SourceSchema': 'IFC2X3'}}}, 'groups': {'IFC4 Migration Set 18': ['W-S', 'W-S-UP', 'W-N', 'W-N-UP', 'W-W', 'W-W-UP', 'W-E', 'W-E-UP', 'GF Slab', 'UF Slab', 'Roof']}}
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

def schema_serialization_valid(model, path):
    if str(model.schema).upper()!='IFC4': return False
    header=path.read_text(encoding='utf-8',errors='ignore')[:1000].upper()
    if "FILE_SCHEMA(('IFC4'))" not in header: return False
    try:
        for entity in model:
            for index in range(len(entity)):
                entity[index]
    except Exception:
        return False
    return all(len(layer)==7 for layer in model.by_type('IfcMaterialLayer'))

def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if not schema_serialization_valid(m,p): return False
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
    if not baseline_preserved(m): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
