from __future__ import annotations
import itertools
import json
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = json.loads(r'''{
  "case_id": "multi-gui-4-librecad-freecad-kicad-blender-task-06-ubuntu",
  "token": "EW4G06",
  "required_files": ["stage1_fan_control_panel.dxf", "stage2_fan_control_panel.stl", "stage2_fan_control_panel_handoff_outline.dxf", "stage3_fan_control_panel_board.kicad_pcb", "stage3_fan_control_panel_board_profile.svg", "stage4_fan_control_panel.glb"],
  "dxf": {"file": "stage1_fan_control_panel.dxf", "bbox": [145.0, 95.0], "bbox_tol": 1.5, "circle_tol": 1.0, "radius_tol": 0.5, "layers": ["OUTLINE", "GRILLE", "HOLE", "LABEL"], "circles": [[72.5,47.5,32.0],[12,12,2.4],[133,12,2.4],[12,83,2.4],[133,83,2.4],[116,47.5,5.5]], "texts": ["EW4G06","PWM","RPM","FAN"], "min_grille_spokes": 8, "no_layers": ["GUIDE"]},
  "stl": {"file": "stage2_fan_control_panel.stl", "bbox": [145.0,95.0,10.0], "bbox_tol": 4.0, "min_triangles": 200, "max_fill_ratio": 0.72},
  "handoff": {"file": "stage2_fan_control_panel_handoff_outline.dxf"},
  "board_file": {"file": "stage3_fan_control_panel_board.kicad_pcb"},
  "board_profile": {"file": "stage3_fan_control_panel_board_profile.svg"},
  "kicad": {"components": {"J1":"fan header","SW1":"rotary encoder","DS1":"OLED display","SW2":"button up","SW3":"button down","SW4":"button mode","SW5":"button set"}, "tokens": ["EW4G06","FAN-J1","ENCODER-SW1","BTN-UP","BTN-DN","BTN-MODE","BTN-SET","OLED-DS1"]},
  "glb": {"file": "stage4_fan_control_panel.glb", "min_nodes": 7, "min_materials": 2, "min_meshes": 7}
}''')
DETAILS = []
ROOT = Path(os.environ.get('OUTPUT_ROOT', '/home/user/Desktop'))

try:
    import ezdxf
    import numpy as np
    import trimesh
    from pygltflib import GLTF2
except Exception as exc:
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def log(message): DETAILS.append(str(message))
def fail(message): log('[FAIL] ' + str(message)); return False
def ok(message): log('[PASS] ' + str(message)); return True
def close(a, b, tol): return abs(float(a) - float(b)) <= float(tol)
def norm(value): return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())
def dims_match(got, expected, tol): return len(got) == len(expected) and all(close(a, b, tol) for a, b in zip(got, expected))


def finish(value):
    valid = bool(value)
    payload = {'case_id': SPEC['case_id'], 'valid': valid, 'score': 1.0 if valid else 0.0,
               'metric_name': 'four_gui_transfer_completion', 'output_field': 'score', 'details': DETAILS}
    try:
        (ROOT / 'eval_detail.txt').write_text('\n'.join(DETAILS) + '\n', encoding='utf-8')
        (ROOT / 'eval_result.txt').write_text(('True' if valid else 'False') + '\n', encoding='utf-8')
        for name in ('score.json', 'quant_metrics.json'):
            (ROOT / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    except Exception: pass
    print(valid); raise SystemExit(0)


def check_dependencies():
    return fail('Missing evaluator dependency: ' + repr(IMPORT_ERROR)) if IMPORT_ERROR else ok('Evaluator dependencies imported')


def required_file(name, size=32):
    path = ROOT / name
    return fail('Missing or too-small required file: ' + name) if not path.is_file() or path.stat().st_size < size else True


def check_required_files():
    return all(required_file(name) for name in SPEC['required_files']) and ok('All six required deliverables exist')


def entity_text(entity):
    if entity.dxftype() == 'TEXT': return str(entity.dxf.text)
    if entity.dxftype() == 'MTEXT':
        try: return entity.plain_text()
        except Exception: return str(entity.text)
    return ''


def polyline_points(entity):
    if entity.dxftype() == 'LWPOLYLINE': return [(float(p[0]), float(p[1])) for p in entity.get_points('xy')]
    if entity.dxftype() == 'POLYLINE': return [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
    return []


def polygon_area(points):
    return abs(sum(points[i][0] * points[(i+1) % len(points)][1] - points[(i+1) % len(points)][0] * points[i][1] for i in range(len(points))) / 2) if len(points) >= 3 else 0


def polygon_dims(points):
    arr = np.asarray(points, dtype=float); return (arr.max(axis=0) - arr.min(axis=0)).tolist() if len(arr) else []


def closed_rectangle(entity, expected=(145.0, 95.0), tol=1.5):
    points = polyline_points(entity)
    if not points or not bool(entity.is_closed) or not dims_match(polygon_dims(points), expected, tol): return False
    dims = polygon_dims(points); return close(polygon_area(points), dims[0] * dims[1], max(dims) * tol)


def read_dxf(name): return ezdxf.readfile(str(ROOT / name))


def check_stage1_dxf():
    try: doc = read_dxf(SPEC['dxf']['file']); entities = list(doc.modelspace())
    except Exception as exc: return fail('ezdxf could not parse stage1 DXF: ' + str(exc))
    layers = {str(e.dxf.layer).upper() for e in entities}
    for layer in SPEC['dxf']['layers']:
        if layer not in layers: return fail('Stage1 missing layer: ' + layer)
    for layer in SPEC['dxf']['no_layers']:
        if any(str(e.dxf.layer).upper() == layer for e in entities): return fail('Stage1 retains GUIDE entities')
    outlines = [e for e in entities if str(e.dxf.layer).upper() == 'OUTLINE' and e.dxftype() in {'LWPOLYLINE','POLYLINE'}]
    if not any(closed_rectangle(e) for e in outlines): return fail('Stage1 lacks one closed 145 x 95 OUTLINE rectangle')
    from ezdxf import bbox as ezdxf_bbox
    try:extent=ezdxf_bbox.extents(entities,fast=False)
    except Exception as exc:return fail('Could not determine complete stage1 geometry envelope: '+str(exc))
    if not extent.has_data:return fail('Stage1 has no bounded geometry')
    minimum=np.asarray([extent.extmin.x,extent.extmin.y]);maximum=np.asarray([extent.extmax.x,extent.extmax.y])
    if np.max(np.abs(minimum))>.2 or np.max(maximum-[145,95])>.2:
        return fail('Stage1 contains geometry outside the 145 x 95 drawing envelope')
    circles = []
    for e in entities:
        if e.dxftype() == 'CIRCLE':
            circles.append((str(e.dxf.layer).upper(), float(e.dxf.center.x), float(e.dxf.center.y), float(e.dxf.radius)))
    if len(circles) != 6: return fail('Stage1 must contain exactly six task circles')
    for index, req in enumerate(SPEC['dxf']['circles']):
        expected_layer = 'GRILLE' if index == 0 else 'HOLE'
        matches = [c for c in circles if c[0] == expected_layer and close(c[1],req[0],1.0) and close(c[2],req[1],1.0) and close(c[3],req[2],.5)]
        if len(matches) != 1: return fail('Stage1 circle missing or on wrong layer: ' + str(req))
    spoke_angles=[]; center = np.asarray([72.5,47.5])
    for e in entities:
        if e.dxftype() != 'LINE' or str(e.dxf.layer).upper() != 'GRILLE': continue
        a = np.asarray([float(e.dxf.start.x),float(e.dxf.start.y)]); b = np.asarray([float(e.dxf.end.x),float(e.dxf.end.y)])
        radii = sorted((np.linalg.norm(a-center), np.linalg.norm(b-center)))
        if radii[0] <= 0.8 and 31.0 <= radii[1] <= 33.0:
            outer=b if np.linalg.norm(b-center)>np.linalg.norm(a-center) else a
            spoke_angles.append(math.atan2(outer[1]-center[1],outer[0]-center[0])%(2*math.pi))
    distinct=[]
    for angle in sorted(spoke_angles):
        if all(min(abs(angle-other),2*math.pi-abs(angle-other))>math.radians(2) for other in distinct):distinct.append(angle)
    if len(distinct) < SPEC['dxf']['min_grille_spokes']: return fail('Stage1 requires at least eight distinct center-to-r32 GRILLE spokes')
    labels = [entity_text(e) for e in entities if e.dxftype() in {'TEXT','MTEXT'} and str(e.dxf.layer).upper() == 'LABEL']
    blob = norm(' '.join(labels))
    for token in SPEC['dxf']['texts']:
        if norm(token) not in blob: return fail('Stage1 LABEL missing token: ' + token)
    return ok('Stage1 has exact circles, closed outline, at least eight distinct radial spokes, and LABEL text')


def mesh_local(mesh):
    bounds = np.asarray(mesh.bounds,float); return np.asarray(mesh.vertices,float)-bounds[0], bounds[1]-bounds[0]


def ring_evidence(vertices, x, y, radius, min_hits=12, radial_tol=.7):
    radial = np.hypot(vertices[:,0]-x, vertices[:,1]-y); near = vertices[np.abs(radial-radius) <= radial_tol]
    return len(near) >= min_hits and np.ptp(near[:,2]) >= 3.0


def check_stl():
    try: mesh = trimesh.load_mesh(str(ROOT / SPEC['stl']['file']), file_type='stl', force='mesh', process=True)
    except Exception as exc: return fail('trimesh could not parse STL: ' + str(exc))
    if len(mesh.faces) < SPEC['stl']['min_triangles']: return fail('STL has too few triangles')
    vertices, dims = mesh_local(mesh)
    if not dims_match(dims.tolist(), SPEC['stl']['bbox'], SPEC['stl']['bbox_tol']): return fail('STL bbox mismatch: ' + str(dims.tolist()))
    if not mesh.is_watertight: return fail('STL must be watertight')
    fill = abs(float(mesh.volume)) / max(float(np.prod(dims)),1e-9)
    if not (.08 <= fill <= SPEC['stl']['max_fill_ratio']): return fail('STL is empty or box-like: fill %.4f' % fill)
    for x,y,r in SPEC['dxf']['circles'][1:]:
        if not ring_evidence(vertices,x,y,r,12,.75): return fail('STL lacks through-opening evidence near %s' % ([x,y,r],))
    radial = np.hypot(vertices[:,0]-72.5,vertices[:,1]-47.5)
    opening = vertices[(radial >= 27) & (radial <= 33)]
    if len(opening) < 120 or np.ptp(opening[:,2]) < 4.0: return fail('STL lacks a substantial r32 fan opening/rim')
    centers = np.asarray(mesh.triangles_center, dtype=float) - np.r_[np.asarray(mesh.bounds[0,:2]), 0.0]
    normals = np.asarray(mesh.face_normals, dtype=float)
    angular_hits=[]
    for angle in np.linspace(0,2*np.pi,144,endpoint=False):
        axis = np.asarray([math.cos(angle),math.sin(angle)])
        delta = centers[:,:2]-np.asarray([72.5,47.5]); along=delta@axis
        cross=np.abs(delta[:,0]*axis[1]-delta[:,1]*axis[0])
        near=centers[(along>=4)&(along<=31)&(cross<=3.0)&(np.abs(centers[:,2]-4.0)<.15)&(normals[:,2]>.9)]
        angular_hits.append(len(near)>=7 and np.ptp(near[:,:2]@axis)>=8)
    # Count circular runs of hit angles, so arbitrary radial layouts are
    # accepted rather than sampling only the GT's twelve 30-degree axes.
    spoke_hits=sum(bool(hit) and not bool(angular_hits[index-1]) for index,hit in enumerate(angular_hits))
    if spoke_hits < 8: return fail('STL lacks at least eight substantial grille spoke structures')
    if vertices[:,2].max() < 9.8 or np.count_nonzero(vertices[:,2] > 9.5) < 40: return fail('STL lacks raised rim/boss geometry')
    return ok('FreeCAD STL is watertight, non-box, opened, and retains manufactured grille geometry')


def check_handoff_dxf():
    try: doc=read_dxf(SPEC['handoff']['file']); entities=list(doc.modelspace())
    except Exception as exc: return fail('Could not parse handoff DXF: '+str(exc))
    outlines=[e for e in entities if e.dxftype() in {'LWPOLYLINE','POLYLINE'} and closed_rectangle(e)]
    if len(outlines)!=1: return fail('Handoff must contain one closed 145 x 95 interface outline')
    inserts=[e for e in entities if e.dxftype()=='INSERT']
    texts=[e for e in entities if e.dxftype() in {'TEXT','MTEXT'}]
    text_blob=norm(' '.join(entity_text(e) for e in texts))
    plain_ok=(norm('FREECAD_TO_KICAD') in text_blob and norm(SPEC['token']) in text_blob and
              all(0<=float(e.dxf.insert.x)<=145 and 0<=float(e.dxf.insert.y)<=95 for e in texts))
    def shape_signature(insert):
        block=list(doc.blocks.get(insert.dxf.name)); points=[]; segments=[]
        for item in block:
            if item.dxftype()=='LINE':
                a=(float(item.dxf.start.x),float(item.dxf.start.y));b=(float(item.dxf.end.x),float(item.dxf.end.y));points.extend((a,b));segments.append((a,b))
            elif item.dxftype() in {'LWPOLYLINE','POLYLINE'}:
                item_points=polyline_points(item);points.extend(item_points);segments.extend(zip(item_points,item_points[1:]));
                if bool(item.is_closed) and len(item_points)>2:segments.append((item_points[-1],item_points[0]))
        if len(points)<12:return None
        def key(point):return tuple(round(v,3) for v in point)
        adjacency={}
        for a,b in segments:
            adjacency.setdefault(key(a),set()).add(key(b));adjacency.setdefault(key(b),set()).add(key(a))
        components=0;remaining=set(adjacency)
        while remaining:
            components+=1;stack=[remaining.pop()]
            while stack:
                for neighbor in adjacency[stack.pop()]:
                    if neighbor in remaining:remaining.remove(neighbor);stack.append(neighbor)
        dims=polygon_dims(points);length=sum(math.dist(a,b) for a,b in segments)
        return len(segments),dims,components,length
    signatures=[shape_signature(e) for e in inserts];signatures=[x for x in signatures if x]
    insert_bounds=[]
    for insert in inserts:
        points=[]
        for item in insert.virtual_entities():
            if item.dxftype()=='LINE':points.extend(((float(item.dxf.start.x),float(item.dxf.start.y)),(float(item.dxf.end.x),float(item.dxf.end.y))))
            elif item.dxftype() in {'LWPOLYLINE','POLYLINE'}:points.extend(polyline_points(item))
        if points:insert_bounds.append(np.asarray(points,float))
    # The two real ShapeStrings are independently outlined glyph groups.  Keep
    # font variation possible, but reject a pair of arbitrary line blocks that
    # only imitates a wide bounding box.
    shapes=(len(signatures)==2 and min(x[0] for x in signatures)>=45 and
            min(x[2] for x in signatures)>=5 and min(x[3] for x in signatures)>=80 and
            all(x[1][0]>=20 and 4<=x[1][1]<=9 and x[1][0]/x[1][1]>=4 for x in signatures) and
            max(x[1][0] for x in signatures)/min(x[1][0] for x in signatures)>=1.6 and len(insert_bounds)==2 and
            all(np.all(a.min(axis=0)>=0) and a[:,0].max()<=145 and a[:,1].max()<=95 for a in insert_bounds))
    if not (plain_ok or shapes): return fail('Handoff lacks two substantial text-shaped label representations')
    return ok('FreeCAD handoff has one closed interface outline and two ShapeString labels')


def balanced_blocks(text, head):
    result=[]
    for match in re.finditer(r'\('+re.escape(head)+r'(?=\s|\")',text):
        depth=0; quoted=False; escaped=False
        for i in range(match.start(),len(text)):
            ch=text[i]
            if quoted:
                if escaped: escaped=False
                elif ch=='\\': escaped=True
                elif ch=='"': quoted=False
            elif ch=='"': quoted=True
            elif ch=='(': depth+=1
            elif ch==')':
                depth-=1
                if depth==0: result.append(text[match.start():i+1]); break
    return result


def first_xy(block, head):
    m=re.search(r'\('+re.escape(head)+r'\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)',block)
    return (float(m.group(1)),float(m.group(2))) if m else None


def closed_cycle(segments,tol=.2):
    def key(p): return tuple(int(round(v/tol)) for v in p)
    adj={}; coords={}
    for a,b in segments:
        ka,kb=key(a),key(b); coords[ka]=a;coords[kb]=b;adj.setdefault(ka,[]).append(kb);adj.setdefault(kb,[]).append(ka)
    if len(adj)<4 or any(len(v)!=2 for v in adj.values()): return []
    start=next(iter(adj)); prev=None; cur=start; cycle=[]
    while True:
        cycle.append(coords[cur]); choices=[x for x in adj[cur] if x!=prev]
        if not choices:return []
        nxt=choices[0]
        if nxt==start: break
        if nxt in [key(x) for x in cycle]: return []
        prev,cur=cur,nxt
        if len(cycle)>len(adj):return []
    return cycle if len(cycle)==len(adj) else []


def point_in_bounds(point,minimum,maximum): return all(minimum[i]-.2<=point[i]<=maximum[i]+.2 for i in range(2))


def dxf_handoff_segments():
    doc=read_dxf(SPEC['handoff']['file']);segments=[]
    def collect(entity):
        if entity.dxftype()=='LINE':segments.append(((float(entity.dxf.start.x),float(entity.dxf.start.y)),(float(entity.dxf.end.x),float(entity.dxf.end.y))))
        elif entity.dxftype() in {'LWPOLYLINE','POLYLINE'}:
            points=polyline_points(entity);segments.extend(zip(points,points[1:]));
            if bool(entity.is_closed) and len(points)>2:segments.append((points[-1],points[0]))
    for entity in doc.modelspace():
        if entity.dxftype()=='INSERT':
            for item in entity.virtual_entities():collect(item)
        else:collect(entity)
    return segments


def normalized_segment_set(segments,quantum=.01):
    points=np.asarray([point for segment in segments for point in segment],float);minimum=points.min(axis=0);dims=np.ptp(points,axis=0);best=[]
    for order in ((0,1),(1,0)):
        candidate=points[:,order].copy();candidate-=candidate.min(axis=0);candidate_dims=dims[list(order)]
        for flips in itertools.product((False,True),repeat=2):
            transformed=candidate.copy()
            for axis,flip in enumerate(flips):
                if flip:transformed[:,axis]=candidate_dims[axis]-transformed[:,axis]
            pairs=[]
            for index in range(0,len(transformed),2):
                a=tuple(np.round(transformed[index]/quantum).astype(int));b=tuple(np.round(transformed[index+1]/quantum).astype(int));pairs.append(tuple(sorted((a,b))))
            best.append(frozenset(pairs))
    return best


def check_kicad_board_file():
    try: text=(ROOT/SPEC['board_file']['file']).read_text(encoding='utf-8',errors='ignore')
    except Exception as exc:return fail('Could not read board: '+str(exc))
    if not text.lstrip().startswith('(kicad_pcb') or not re.search(r'\(generator\s+"?pcbnew"?\)',text,re.I): return fail('Board is not native pcbnew')
    edge=[]
    for block in balanced_blocks(text,'gr_line'):
        if '(layer "Edge.Cuts")' in block:
            a,b=first_xy(block,'start'),first_xy(block,'end')
            if a and b:edge.append((a,b))
    cycle=closed_cycle(edge)
    if len(edge)!=4 or len(cycle)!=4 or not dims_match(polygon_dims(cycle),[145,95],.5) or not close(polygon_area(cycle),145*95,5): return fail('Edge.Cuts must be one closed 145 x 95 rectangle with four segments')
    edge_points=np.asarray(cycle,float);edge_min=edge_points.min(axis=0);edge_max=edge_points.max(axis=0)
    footprints=balanced_blocks(text,'footprint'); found={}
    for block in footprints:
        ref=re.search(r'\(property\s+"Reference"\s+"([^"]+)"',block); value=re.search(r'\(property\s+"Value"\s+"([^"]+)"',block); at=first_xy(block,'at')
        if ref and value and at: found[ref.group(1)]=(value.group(1),len(balanced_blocks(block,'pad')),at)
    semantic={'J1':('FAN','HEADER'),'SW1':('ROTARY','ENCODER'),'DS1':('OLED','DISPLAY'),'SW2':('BUTTON','UP'),'SW3':('BUTTON','DOWN'),'SW4':('BUTTON','MODE'),'SW5':('BUTTON','SET')}
    for ref,words in semantic.items():
        if ref not in found or found[ref][1] < 2 or not all(word in found[ref][0].upper() for word in words): return fail('Missing semantic padded footprint: '+ref)
        if not point_in_bounds(found[ref][2],edge_min,edge_max): return fail('Footprint outside board: '+ref)
    drawings=[b for head in ('gr_line','gr_arc','gr_poly','gr_text_box') for b in balanced_blocks(text,head) if '(layer "Dwgs.User")' in b]
    source_segments=dxf_handoff_segments()
    if len(drawings)<max(4,int(len(source_segments)*.9)): return fail('Complete Dwgs.User FreeCAD handoff evidence is missing')
    drawing_points=[]
    for block in drawings:
        for tag in ('start','end','center','mid','xy'):
            drawing_points.extend((float(m.group(1)),float(m.group(2))) for m in re.finditer(r'\('+tag+r'\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)',block))
    if len(drawing_points)<8:return fail('Dwgs.User handoff geometry has too few parseable vertices')
    handoff_bounds=np.asarray(drawing_points,float)
    if not dims_match(np.ptp(handoff_bounds,axis=0),[145,95],1.0) or np.max(np.abs(handoff_bounds.min(axis=0)-edge_min))>1.0:
        return fail('Dwgs.User handoff geometry is not aligned to the 145 x 95 Edge.Cuts')
    board_segments=[]
    for block in drawings:
        a,b=first_xy(block,'start'),first_xy(block,'end')
        if a and b:board_segments.append((a,b))
    source_variants=normalized_segment_set(source_segments);board_variant=normalized_segment_set(board_segments)[0]
    overlap=max(len(board_variant & source)/max(1,len(source)) for source in source_variants)
    if overlap<.97:return fail('Dwgs.User geometry is not a complete transformed copy of the FreeCAD handoff')
    source_doc=read_dxf(SPEC['handoff']['file']);source_text=norm(' '.join(entity_text(e) for e in source_doc.modelspace() if e.dxftype() in {'TEXT','MTEXT'}))
    if source_text:
        board_user_text=norm(' '.join(b for b in balanced_blocks(text,'gr_text') if '(layer "Dwgs.User")' in b))
        for token in ('FREECAD_TO_KICAD',SPEC['token']):
            if norm(token) in source_text and norm(token) not in board_user_text:return fail('Dwgs.User import dropped handoff text: '+token)
    silk=' '.join(b for b in balanced_blocks(text,'gr_text') if '(layer "F.SilkS")' in b)
    for token in ['KICAD_TO_BLENDER','EDGE_FROM_STAGE2_HANDOFF',SPEC['handoff']['file']]+SPEC['kicad']['tokens']:
        if norm(token) not in norm(silk): return fail('Required token is not native F.SilkS: '+token)
    return ok('KiCad board has native padded components, closed Edge.Cuts, imported handoff, and silkscreen')


def svg_matrix(raw):
    matrix=np.eye(3)
    for name,vals in re.findall(r'([A-Za-z]+)\s*\(([^)]*)\)',str(raw or '')):
        v=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',vals,re.I)]; item=np.eye(3);name=name.lower()
        if name=='translate' and v:item[0,2]=v[0];item[1,2]=v[1] if len(v)>1 else 0
        elif name=='scale' and v:item[0,0]=v[0];item[1,1]=v[1] if len(v)>1 else v[0]
        elif name=='matrix' and len(v)==6:a,b,c,d,e,f=v;item=np.asarray([[a,c,e],[b,d,f],[0,0,1.]])
        else:return None
        matrix=matrix@item
    return matrix


def check_board_profile_svg():
    try: root=ET.parse(ROOT/SPEC['board_profile']['file']).getroot()
    except Exception as exc:return fail('Could not parse SVG: '+str(exc))
    segments=[]
    def visit(e,parent,style):
        own=svg_matrix(e.attrib.get('transform'))
        if own is None:return
        matrix=parent@own; current=dict(style)
        for part in str(e.attrib.get('style','')).split(';'):
            if ':' in part:k,v=part.split(':',1);current[k.strip().lower()]=v.strip().lower()
        current.update({k:e.attrib[k].lower() for k in ('stroke','fill','display','visibility') if k in e.attrib})
        painted=current.get('stroke','none') not in {'none','transparent'} or current.get('fill','none') not in {'none','transparent'}
        if painted and current.get('display')!='none' and current.get('visibility')!='hidden' and e.tag.rsplit('}',1)[-1].lower()=='path':
            raw=e.attrib.get('d',''); nums=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',raw)]
            if len(nums)==4 and not re.search(r'[CSQTAZ]',raw,re.I):
                arr=np.column_stack((np.asarray([(nums[0],nums[1]),(nums[2],nums[3])]),np.ones(2))); pts=(matrix@arr.T).T[:,:2];segments.append((tuple(pts[0]),tuple(pts[1])))
        for child in list(e):visit(child,matrix,current)
    visit(root,np.eye(3),{})
    cycle=closed_cycle(segments,.001)
    if len(segments)!=4 or len(cycle)!=4 or not dims_match(polygon_dims(cycle),[145,95],.5) or not close(polygon_area(cycle),145*95,5): return fail('SVG painted geometry is not one closed 145 x 95 rectangle')
    desc=' '.join((root.findtext('.//{*}desc') or '',root.findtext('.//{*}title') or ''))
    if 'PCBNEW' not in desc.upper(): return fail('SVG lacks KiCad pcbnew plot provenance')
    return ok('KiCad SVG has actual painted closed 145 x 95 Edge.Cuts geometry')


def accessor_positions(gltf,index):
    if index is None:return np.empty((0,3))
    a=gltf.accessors[index];v=gltf.bufferViews[a.bufferView];off=int(v.byteOffset or 0)+int(a.byteOffset or 0);stride=int(v.byteStride or 12);blob=gltf.binary_blob()
    if a.componentType!=5126 or a.type!='VEC3':return np.empty((0,3))
    return np.asarray([struct.unpack_from('<3f',blob,off+i*stride) for i in range(a.count)],float)


def accessor_indices(gltf,index):
    if index is None:return np.empty(0,dtype=np.int64)
    a=gltf.accessors[index];v=gltf.bufferViews[a.bufferView];formats={5121:('B',1),5123:('H',2),5125:('I',4)}
    if a.componentType not in formats or a.type!='SCALAR':return np.empty(0,dtype=np.int64)
    fmt,size=formats[a.componentType];off=int(v.byteOffset or 0)+int(a.byteOffset or 0);stride=int(v.byteStride or size);blob=gltf.binary_blob()
    return np.asarray([struct.unpack_from('<'+fmt,blob,off+i*stride)[0] for i in range(a.count)],dtype=np.int64)


def triangle_count(gltf,node_index):
    node=gltf.nodes[node_index]
    if node.mesh is None:return 0
    total=0
    for primitive in gltf.meshes[node.mesh].primitives:
        position_index=getattr(primitive.attributes,'POSITION',None)
        if (primitive.mode not in (None,4)) or position_index is None:return 0
        positions=accessor_positions(gltf,position_index);indices=accessor_indices(gltf,primitive.indices)
        if len(positions)<3 or len(indices)<3 or len(indices)%3 or indices.min()<0 or indices.max()>=len(positions):return 0
        triangles=indices.reshape(-1,3);vertices=positions[triangles]
        distinct=np.logical_and.reduce((triangles[:,0]!=triangles[:,1],triangles[:,1]!=triangles[:,2],triangles[:,0]!=triangles[:,2]))
        areas=np.linalg.norm(np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=1)
        total+=int(np.count_nonzero(distinct & (areas>1e-10)))
    return total


def referenced_vertex_coverage(gltf,node_index):
    node=gltf.nodes[node_index]
    if node.mesh is None:return 0.0
    referenced=set();available=0
    for primitive in gltf.meshes[node.mesh].primitives:
        position_index=getattr(primitive.attributes,'POSITION',None)
        if position_index is None or primitive.indices is None:continue
        positions=accessor_positions(gltf,position_index);indices=accessor_indices(gltf,primitive.indices);available+=len(positions)
        if len(indices) and indices.min()>=0 and indices.max()<len(positions):referenced.update(int(value) for value in indices)
    return len(referenced)/max(1,available)


def node_matrix(node):
    t=np.asarray(node.translation or [0,0,0],float);s=np.asarray(node.scale or [1,1,1],float);x,y,z,w=node.rotation or [0,0,0,1]
    r=np.asarray([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])
    m=np.eye(4);m[:3,:3]=r@np.diag(s);m[:3,3]=t;return m


def world_matrices(gltf):
    parents={c:p for p,n in enumerate(gltf.nodes or []) for c in (n.children or [])};result={}
    for i in range(len(gltf.nodes or [])):
        chain=[];cur=i
        while True:
            chain.append(cur)
            if cur not in parents:break
            cur=parents[cur]
        m=np.eye(4)
        for item in reversed(chain):m=m@node_matrix(gltf.nodes[item])
        result[i]=m
    return result


def node_points(gltf,index,matrices):
    node=gltf.nodes[index]
    if node.mesh is None:return np.empty((0,3))
    chunks=[]
    for primitive in gltf.meshes[node.mesh].primitives:
        pts=accessor_positions(gltf,getattr(primitive.attributes,'POSITION',None))
        if len(pts):chunks.append((matrices[index]@np.column_stack((pts,np.ones(len(pts)))).T).T[:,:3])
    return np.vstack(chunks) if chunks else np.empty((0,3))


def node_has_visible_material(gltf, index):
    node = gltf.nodes[index]
    if node.mesh is None:
        return False
    materials = gltf.materials or []
    for primitive in gltf.meshes[node.mesh].primitives:
        material_index = primitive.material
        if material_index is None or not (0 <= material_index < len(materials)):
            continue
        material = materials[material_index]
        pbr = material.pbrMetallicRoughness
        factor = (pbr.baseColorFactor if pbr else None) or [1, 1, 1, 1]
        alpha = float(factor[3] if len(factor) > 3 else 1)
        if material.alphaMode == 'MASK':
            visible = alpha >= float(material.alphaCutoff if material.alphaCutoff is not None else .5)
        elif material.alphaMode == 'BLEND':
            visible = alpha >= .05
        else:
            visible = True
        if visible:
            return True
    return False


def vertex_overlap(source,candidate,quantum=.09):
    sd=np.ptp(source,axis=0);ss={tuple(x) for x in np.round((source-source.min(axis=0))/quantum).astype(int)};best=(0,0)
    for order in itertools.permutations(range(3)):
        c=candidate[:,order].copy()
        if np.max(np.abs(np.ptp(c,axis=0)-sd))>1:continue
        c-=c.min(axis=0)
        for flips in itertools.product((False,True),repeat=3):
            x=c.copy()
            for a,f in enumerate(flips):
                if f:x[:,a]=sd[a]-x[:,a]
            cs={tuple(v) for v in np.round(x/quantum).astype(int)};common=len(ss&cs);score=(common/max(1,len(ss)),common/max(1,len(cs)))
            if min(score)>min(best):best=score
    return best


def record_box(record): return np.ptp(record[2],axis=0)


def stage_transforms(body_points):
    bounds=np.asarray([body_points.min(axis=0),body_points.max(axis=0)]);expected=np.asarray([145.,95.,10.])
    for order in itertools.permutations(range(3)):
        if np.max(np.abs(np.ptp(body_points[:,order],axis=0)-expected))>1.5:continue
        for flips in itertools.product((False,True),repeat=3):
            def transform(points,order=order,flips=flips):
                result=np.asarray(points,float)[:,order].copy()
                for target,(source,flip) in enumerate(zip(order,flips)):
                    result[:,target]=(bounds[1,source]-result[:,target]) if flip else (result[:,target]-bounds[0,source])
                return result
            yield transform


def board_button_positions():
    text=(ROOT/SPEC['board_file']['file']).read_text(encoding='utf-8',errors='ignore');result=[]
    for ref in ('SW2','SW3','SW4','SW5'):
        matches=[]
        for block in balanced_blocks(text,'footprint'):
            found=re.search(r'\(property\s+"Reference"\s+"([^"]+)"',block)
            if found and found.group(1)==ref:
                point=first_xy(block,'at')
                if point:matches.append(point)
        if len(matches)!=1:return np.empty((0,2))
        result.append(matches[0])
    return np.asarray(result,float)


def check_glb():
    try:gltf=GLTF2().load_binary(str(ROOT/SPEC['glb']['file']))
    except Exception as exc:return fail('Could not parse GLB: '+str(exc))
    if len(gltf.nodes or [])<SPEC['glb']['min_nodes'] or len(gltf.meshes or [])<SPEC['glb']['min_meshes'] or len(gltf.materials or [])<SPEC['glb']['min_materials']:return fail('GLB lacks required scene complexity')
    if 'BLENDER' not in str(gltf.asset.generator or '').upper():return fail('GLB is not Blender-generated')
    scene=gltf.scene or 0;roots=list(gltf.scenes[scene].nodes or []);reachable=set();stack=roots[:]
    while stack:
        i=stack.pop()
        if i in reachable:continue
        reachable.add(i);stack.extend(gltf.nodes[i].children or [])
    matrices=world_matrices(gltf);records=[]
    for i in reachable:
        p=node_points(gltf,i,matrices)
        if len(p)>=8 and np.all(np.isfinite(p)):records.append((i,str(gltf.nodes[i].name or ''),p))
    bodies=[r for r in records if 'stage2_fan_control_panel' in r[1].lower()]
    profiles=[r for r in records if 'stage3_fan_control_panel_board_profile.svg' in r[1].lower()]
    if not bodies or len(profiles)<4:return fail('Reachable mesh-bound native STL or four SVG import objects are missing')
    body=max(bodies,key=lambda r:len(r[2]));source=trimesh.load_mesh(str(ROOT/SPEC['stl']['file']),file_type='stl',force='mesh',process=True);coverage=vertex_overlap(np.asarray(source.vertices,float),body[2])
    body_triangles=triangle_count(gltf,body[0])
    if body_triangles<max(200,int(len(source.faces)*.65)) or referenced_vertex_coverage(gltf,body[0])<.65:
        return fail('GLB body does not render most of the indexed STL triangle/vertex geometry')
    if min(coverage)<.65:return fail('GLB body is not vertex-equivalent to stage2 STL: '+str(coverage))
    profile_dims=[]; profile_points=[]
    for r in profiles:
        if triangle_count(gltf,r[0])<2:return fail('SVG profile object is not an indexed TRIANGLES mesh')
        if not node_has_visible_material(gltf,r[0]):return fail('SVG profile object has no visible bound material')
        d=np.sort(record_box(r));profile_dims.append(d);profile_points.append(r[2])
        if d[-1]<90 or d[-1]>146 or d[-2]>.9 or d[0]>.9:return fail('SVG profile segment is underscaled or not a thin full-scale edge')
    if not any(close(d[-1],145,1.5) for d in profile_dims) or not any(close(d[-1],95,1.5) for d in profile_dims):return fail('SVG import lacks 145 and 95 mm profile edges')
    profile_all=np.vstack(profile_points); body_min=body[2].min(axis=0); body_max=body[2].max(axis=0)
    # The thin SVG plane must be co-located with the full panel footprint, not
    # merely full-sized somewhere else in the scene.
    aligned=False
    for flat_axis in range(3):
        other=[axis for axis in range(3) if axis!=flat_axis]
        if np.ptp(profile_all[:,flat_axis])<=1.0 and all(abs(profile_all[:,a].min()-body_min[a])<=2 and abs(profile_all[:,a].max()-body_max[a])<=2 for a in other) and body_min[flat_axis]-2<=np.mean(profile_all[:,flat_axis])<=body_max[flat_axis]+6:
            aligned=True
    if not aligned:return fail('Full-scale SVG profile is not aligned to the stage2 panel footprint')
    knobs=[r for r in records if 'encoder_sw1_raised_knob' in r[1].lower()]
    if len(knobs)!=1:return fail('GLB needs one distinct encoder knob mesh')
    knob=knobs[0];kd=np.sort(record_box(knob));kc=(knob[2].min(axis=0)+knob[2].max(axis=0))/2
    if triangle_count(gltf,knob[0])<12:return fail('Encoder knob is not an indexed TRIANGLES mesh')
    if not node_has_visible_material(gltf,knob[0]):return fail('Encoder knob has no visible bound material')
    if kd[-1]<14 or kd[-2]<14 or kd[0]<5:return fail('Encoder knob is not visibly raised/substantial')
    buttons=[]
    for ref in ('sw2','sw3','sw4','sw5'):
        matches=[r for r in records if ref in r[1].lower() and 'button' in r[1].lower()]
        if len(matches)!=1:return fail('Missing one independent button mesh for '+ref)
        if triangle_count(gltf,matches[0][0])<12:return fail('Button is not an indexed TRIANGLES mesh: '+ref)
        if not node_has_visible_material(gltf,matches[0][0]):return fail('Button has no visible bound material: '+ref)
        d=np.sort(record_box(matches[0]));
        if d[-1]<7 or d[-2]<7 or d[0]<3:return fail('Button geometry too small/flat: '+ref)
        buttons.append(matches[0])
    if len({r[0] for r in buttons})!=4:return fail('Four button labels reuse one mesh node')
    centers=np.asarray([(r[2].min(axis=0)+r[2].max(axis=0))/2 for r in buttons])
    body_dims=np.sort(record_box(body));
    if not dims_match(body_dims,[10,95,145],1.5):return fail('GLB body full scale was not preserved')
    expected=board_button_positions()
    if len(expected)!=4 or min(np.ptp(expected,axis=0))>1.5 or max(np.ptp(expected,axis=0))<20:return fail('PCB SW2-SW5 footprints are not one distinct row')
    expected=expected[np.argsort(expected[:,int(np.argmax(np.ptp(expected,axis=0)))])]
    scene_aligned=False
    for transform in stage_transforms(body[2]):
        mapped_buttons=transform(centers);mapped_buttons=mapped_buttons[np.argsort(mapped_buttons[:,int(np.argmax(np.ptp(mapped_buttons[:,:2],axis=0)))])]
        mapped_knob=transform(kc.reshape(1,3))[0];mapped_profile=transform(profile_all)
        profile_min= mapped_profile.min(axis=0);profile_max=mapped_profile.max(axis=0)
        profile_ok=(np.max(np.abs(profile_min[:2]))<=2 and np.max(np.abs(profile_max[:2]-[145,95]))<=2 and
                    10<=np.mean(mapped_profile[:,2])<=19 and np.ptp(mapped_profile[:,2])<=1.1)
        buttons_ok=(np.max(abs(mapped_buttons[:,:2]-expected))<=2 and np.min(mapped_buttons[:,2])>=10 and np.max(mapped_buttons[:,2])<=18)
        knob_ok=np.max(abs(mapped_knob[:2]-[116,47.5]))<=2 and 10<=mapped_knob[2]<=19
        if profile_ok and buttons_ok and knob_ok:scene_aligned=True;break
    if not scene_aligned:return fail('SVG profile, knob, and four buttons do not share one valid panel-coordinate transform')
    return ok('Blender GLB preserves STL and full-scale SVG, with real knob and four aligned button meshes')


def main():
    for check in (check_dependencies,check_required_files,check_stage1_dxf,check_stl,check_handoff_dxf,check_kicad_board_file,check_board_profile_svg,check_glb):
        if not check():finish(False)
    finish(True)


if __name__=='__main__':main()
