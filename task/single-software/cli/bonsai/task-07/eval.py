#!/usr/bin/env python3
from pathlib import Path
import re, ifcopenshell, ifcopenshell.util.element
import ifcopenshell.geom
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

def network_valid(model):
    products=model.by_type('IfcDuctSegment')+model.by_type('IfcDuctFitting')+model.by_type('IfcAirTerminal')
    owner={}
    for product in products:
        ports=[]
        for rel in getattr(product,'IsNestedBy',None) or []:
            ports.extend(port for port in rel.RelatedObjects if port.is_a('IfcDistributionPort'))
        expected=1 if product.is_a('IfcAirTerminal') else 2
        if len(ports)!=expected: return False
        for port in ports:
            if port.id() in owner or not str(getattr(port,'Name','') or '').strip(): return False
            owner[port.id()]=product
    if len(owner)!=12: return False
    port_pairs=set(); product_edges=set(); degree={port_id:0 for port_id in owner}
    for rel in model.by_type('IfcRelConnectsPorts'):
        a,b=rel.RelatingPort.id(),rel.RelatedPort.id()
        if a not in owner or b not in owner or a==b or owner[a].id()==owner[b].id(): return False
        pair=tuple(sorted((a,b)))
        if pair in port_pairs: return False
        port_pairs.add(pair); degree[a]+=1; degree[b]+=1
        product_edges.add(tuple(sorted((owner[a].id(),owner[b].id()))))
    if len(port_pairs)!=6 or any(value!=1 for value in degree.values()): return False
    graph={product.id():set() for product in products}
    for a,b in product_edges: graph[a].add(b); graph[b].add(a)
    seen=set(); stack=[products[0].id()]
    while stack:
        current=stack.pop()
        if current in seen: continue
        seen.add(current); stack.extend(graph[current]-seen)
    return len(seen)==len(products)

def evaluate():
    p=DESKTOP/'result.ifc'
    if not p.is_file() or p.stat().st_size<1000: return False
    m=ifcopenshell.open(str(p))
    if len(m.by_type('IfcDistributionSystem'))!=1 or len(m.by_type('IfcDistributionPort'))!=12 or len(m.by_type('IfcRelConnectsPorts'))!=6: return False
    if len(m.by_type('IfcDuctSegment'))!=3 or len(m.by_type('IfcDuctFitting'))!=2 or len(m.by_type('IfcAirTerminal'))!=2: return False
    s=m.by_type('IfcDistributionSystem')[0]
    if not eq(s.Name,'Supply Air Verified') or not marker(s): return False
    assigned=set()
    for rel in getattr(s,'IsGroupedBy',None) or []:
        for o in rel.RelatedObjects: assigned.add(o.Name)
    if assigned!=set(PRODUCTS): return False
    for o in m.by_type('IfcDuctSegment')+m.by_type('IfcDuctFitting')+m.by_type('IfcAirTerminal'):
        if not marker(o): return False
    if not network_valid(m): return False
    if not baseline_preserved(m): return False
    return True
def main():
    try: finish(evaluate())
    except SystemExit: raise
    except Exception: finish(False)
if __name__=='__main__': main()
