from __future__ import annotations
import json
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = {'case_id': 'multi-gui-4-librecad-freecad-kicad-blender-task-09-ubuntu',
 'owner': 'taozhuo',
 'title': 'Wearable charger cradle with pogo pins and strap slots',
 'domain': 'wearable_charging_cradle',
 'software_chain': ['librecad', 'freecad', 'kicad', 'blender'],
 'token': 'EW4G09',
 'required_files': ['stage1_wearable_charger_cradle.dxf',
                    'stage2_wearable_charger_cradle.stl',
                    'stage2_wearable_charger_cradle_handoff_outline.dxf',
                    'stage3_wearable_charger_cradle_board.kicad_pcb',
                    'stage3_wearable_charger_cradle_board_profile.svg',
                    'stage4_wearable_charger_cradle.glb'],
 'dxf': {'file': 'stage1_wearable_charger_cradle.dxf',
         'bbox': [105.0, 48.0],
         'bbox_tol': 0.15,
         'circle_tol': 0.05,
         'radius_tol': 0.03,
         'layers': ['OUTLINE', 'STRAP_SLOT', 'HOLE', 'LABEL'],
         'circles': [[18.0, 24.0, 2.0], [87.0, 24.0, 2.0],
                     [48.0, 24.0, 1.2], [57.0, 24.0, 1.2],
                     [52.5, 10.0, 2.8], [52.5, 38.0, 2.8]],
         'texts': ['EW4G09', 'POGO+', 'POGO-', 'STRAP'],
         'slot_count': 2,
         'no_layers': ['GUIDE']},
 'stl': {'file': 'stage2_wearable_charger_cradle.stl',
         'bbox': [105.0, 48.0, 20.0],
         'bbox_tol': 0.08,
         'min_triangles': 100,
         'watertight': True,
         'non_box_fill_range': [0.05, 0.8],
         'through_holes': 6,
         'strap_slots': 2},
 'kicad': {'tokens': ['EW4G09', 'POGO-P1', 'POGO-P2', 'CHG-U1',
                      'MAGNET-M1', 'USB-J1', 'NTC-R1'],
           'nets': ['VBUS', 'VBAT', 'GND', 'NTC', 'POGO_POS', 'POGO_NEG']},
 'glb': {'file': 'stage4_wearable_charger_cradle.glb',
         'tokens': [],
         'min_nodes': 2,
         'min_materials': 0,
         'nodes': ['stage2_wearable_charger_cradle', 'stage3_wearable_charger_cradle_board_profile.svg'],
         'min_meshes': 1,
         'pogo_centers': [[48.0, 24.0], [57.0, 24.0]],
         'gold_metallic_pogo_count': 2,
         'strap_highlight_count': 2,
         'gui_export': True,
         'accepted_import_evidence': {'stage2_stl_object': 'stage2_wearable_charger_cradle',
                                      'stage3_svg_object': 'stage3_wearable_charger_cradle_board_profile.svg'}},
 'eval_dependencies': {'pip_packages': ['ezdxf', 'trimesh', 'pygltflib', 'numpy'],
                       'vm_preinstalled': True,
                       'usage': {'ezdxf': 'parse and validate DXF geometry, layers, circles, and '
                                          'text',
                                 'trimesh': 'parse and validate STL mesh dimensions and triangle '
                                            'count',
                                 'pygltflib': 'parse and validate Blender-exported GLB scene, '
                                              'nodes, materials, and metadata',
                                 'numpy': 'numeric array and bounding-box comparisons for CAD '
                                          'geometry checks'}},
 'seed': {'file': 'seed_wearable_charger_cradle.dxf',
          'desktop_path': '/home/user/Desktop/seed_wearable_charger_cradle.dxf',
          'sha256': 'fdbb723af3e6865854350e20fe7f6cb47899e862a0e2a65147d0c2ca26cacde0'},
 'gt_provenance': {'instance': 'i-yeslqxefpc4c5qx3440g',
                   'date': '2026-08-13',
                   'software_versions': ['LibreCAD 2.2.0.2', 'FreeCAD 0.21.2',
                                         'KiCad 10.0.2', 'Blender 4.2.3'],
                   'real_software_generated': True},
 'handoff': {'file': 'stage2_wearable_charger_cradle_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_wearable_charger_cradle_board_profile.svg'},
 'intermediate_outputs': [{'stage': 'librecad',
                           'file': 'stage1_wearable_charger_cradle.dxf',
                           'type': 'dxf',
                           'consumed_by': 'freecad',
                           'eval_check': 'check_stage1_dxf'},
                          {'stage': 'freecad',
                           'file': 'stage2_wearable_charger_cradle.stl',
                           'type': 'stl',
                           'consumed_by': 'blender',
                           'eval_check': 'check_stl'},
                          {'stage': 'freecad',
                           'file': 'stage2_wearable_charger_cradle_handoff_outline.dxf',
                           'type': 'dxf',
                           'consumed_by': 'kicad',
                           'eval_check': 'check_handoff_dxf'},
                          {'stage': 'kicad',
                           'file': 'stage3_wearable_charger_cradle_board.kicad_pcb',
                           'type': 'kicad_pcb',
                           'consumed_by': 'blender',
                           'eval_check': 'check_kicad_board_file'},
                          {'stage': 'kicad',
                           'file': 'stage3_wearable_charger_cradle_board_profile.svg',
                           'type': 'svg',
                           'consumed_by': 'blender',
                           'eval_check': 'check_board_profile_svg'}],
 'board_file': {'file': 'stage3_wearable_charger_cradle_board.kicad_pcb'}}
DETAILS = []
ROOT = Path(os.environ.get('OUTPUT_ROOT', '/home/user/Desktop'))

FORBIDDEN_SCRIPT_EXTENSIONS = {
    '.py', '.pyw', '.ipynb', '.sh', '.bash', '.zsh', '.bat', '.cmd', '.ps1',
    '.psm1', '.vbs', '.js', '.mjs', '.ts', '.rb', '.lua', '.tcl', '.ahk', '.scr'
}
ALLOWED_SCRIPT_NAMES = {'eval.py'}
COMMAND_TOKENS = (
    'python', 'python3', 'py ', 'bash', ' sh ', 'zsh', 'node', 'ruby', 'perl',
    'freecadcmd', 'blender --background', 'kicad-cli', 'ezdxf', 'trimesh',
    'cadquery', 'cat ', 'tee ', 'set-content', 'out-file', 'new-item'
)
OUTPUT_TOKENS = (
    '.dxf', '.stl', '.glb', '.svg', '.kicad_pcb', 'stage1_', 'stage2_', 'stage3_', 'stage4_'
)

try:
    import ezdxf
    import numpy as np
    import trimesh
    from pygltflib import GLTF2
except Exception as exc:
    ezdxf = None
    np = None
    trimesh = None
    GLTF2 = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def log(message):
    DETAILS.append(str(message))


def fail(message):
    log('[FAIL] ' + str(message))
    return False


def ok(message):
    log('[PASS] ' + str(message))
    return True


def finish(value):
    valid = bool(value)
    result = 'True\n' if valid else 'False\n'
    score_payload = {
        'case_id': SPEC.get('case_id'),
        'valid': valid,
        'score': 1.0 if valid else 0.0,
        'metric_name': 'four_gui_transfer_completion',
        'output_field': 'score',
        'details': DETAILS,
    }
    try:
        (ROOT / 'eval_detail.txt').write_text('\n'.join(DETAILS) + '\n', encoding='utf-8')
        (ROOT / 'eval_result.txt').write_text(result, encoding='utf-8')
        for name in ('score.json', 'quant_metrics.json'):
            (ROOT / name).write_text(json.dumps(score_payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    except Exception:
        pass
    sys.stdout.write(result)
    sys.stdout.flush()
    raise SystemExit(0)


def norm(value):
    return str(value or '').upper().replace(' ', '').replace('_', '').replace('-', '').replace(':', '').replace('.', '')


def close(a, b, tol):
    return abs(float(a) - float(b)) <= float(tol)


def dims_match(got, exp, tol):
    return len(got) == len(exp) and all(close(a, b, tol) for a, b in zip(got, exp))


def check_dependencies():
    if IMPORT_ERROR is not None:
        return fail('Missing evaluator dependency: ' + repr(IMPORT_ERROR))
    versions = {
        'ezdxf': getattr(ezdxf, '__version__', 'unknown'),
        'trimesh': getattr(trimesh, '__version__', 'unknown'),
        'pygltflib': 'imported',
        'numpy': getattr(np, '__version__', 'unknown'),
        'xml.etree': 'stdlib',
    }
    return ok('Evaluator dependencies imported: ' + json.dumps(versions, sort_keys=True))


def required_file(name, min_size=1):
    path = ROOT / name
    if not path.is_file():
        return fail('Missing required file: ' + name)
    if path.stat().st_size < min_size:
        return fail('Required file is too small: ' + name)
    return ok('Found required file: ' + name)


def check_required_files():
    for name in SPEC['required_files']:
        if not required_file(name, 32):
            return False
    return True


def check_intermediate_outputs():
    expected = SPEC.get('intermediate_outputs', [])
    expected_files = [item.get('file') for item in expected]
    required = [
        SPEC['dxf']['file'],
        SPEC['stl']['file'],
        SPEC['handoff']['file'],
        SPEC['board_file']['file'],
        SPEC['board_profile']['file'],
    ]
    if expected_files != required:
        return fail('Intermediate output manifest mismatch: got %s expected %s' % (expected_files, required))
    seen_stages = {item.get('stage') for item in expected}
    if not {'librecad', 'freecad', 'kicad'}.issubset(seen_stages):
        return fail('Intermediate output manifest missing one or more producing stages')
    consumers = {item.get('consumed_by') for item in expected}
    for consumer in ['freecad', 'kicad', 'blender']:
        if consumer not in consumers:
            return fail('Intermediate output manifest missing consumer: ' + consumer)
    for item in expected:
        name = item.get('file')
        if not name or not (ROOT / name).is_file():
            return fail('Intermediate output listed but missing on disk: ' + str(name))
        if not item.get('type') or not item.get('eval_check'):
            return fail('Intermediate output missing type/eval_check metadata: ' + str(item))
    return ok('Intermediate output manifest lists all stage artifacts and consumers')


def check_no_script_artifacts():
    if not ROOT.exists() or not ROOT.is_dir():
        return fail('Output root does not exist: ' + str(ROOT))
    candidates = []
    try:
        for path in ROOT.iterdir():
            candidates.append(path)
            if path.is_dir() and path.name not in {'__pycache__', '_runtime'}:
                candidates.extend(path.iterdir())
    except Exception as exc:
        return fail('Cannot list output root: ' + str(exc))
    for path in candidates:
        if not path.is_file():
            continue
        if path.name in ALLOWED_SCRIPT_NAMES:
            continue
        if path.suffix.lower() in FORBIDDEN_SCRIPT_EXTENSIONS:
            return fail('Forbidden script-like artifact left in output tree: ' + path.name)
    return ok('No forbidden script-like artifacts')


def check_no_command_bypass():
    if os.environ.get('OUTPUT_ROOT'):
        return ok('History bypass check skipped for non-default OUTPUT_ROOT validation')
    home = Path.home()
    for path in [home / '.bash_history', home / '.zsh_history', home / '.python_history', ROOT / '.bash_history', ROOT / '.zsh_history']:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='ignore').lower()
        except Exception:
            continue
        for line in text.splitlines():
            if 'eval.py' in line:
                continue
            touches_output = any(token in line for token in OUTPUT_TOKENS)
            runs_command = any(token in line for token in COMMAND_TOKENS)
            writes_file = any(token in line for token in ('>', 'tee ', 'cat ', 'set-content', 'out-file', 'new-item'))
            if touches_output and (runs_command or writes_file):
                return fail('Shell history suggests scripted deliverable generation: ' + line[:160])
    return ok('No shell-history bypass evidence')


def entity_text(entity):
    if entity.dxftype() == 'TEXT':
        return str(entity.dxf.text)
    if entity.dxftype() == 'MTEXT':
        try:
            return entity.plain_text()
        except Exception:
            return str(entity.text)
    return ''


def dxf_points(entity):
    typ = entity.dxftype()
    pts = []
    if typ == 'LINE':
        pts.extend([entity.dxf.start, entity.dxf.end])
    elif typ == 'LWPOLYLINE':
        pts.extend([(p[0], p[1], 0.0) for p in entity.get_points('xy')])
    elif typ == 'POLYLINE':
        pts.extend([v.dxf.location for v in entity.vertices])
    elif typ == 'CIRCLE':
        c = entity.dxf.center
        r = float(entity.dxf.radius)
        pts.extend([(c.x - r, c.y, 0.0), (c.x + r, c.y, 0.0), (c.x, c.y - r, 0.0), (c.x, c.y + r, 0.0)])
    elif typ == 'ARC':
        c = entity.dxf.center
        r = float(entity.dxf.radius)
        pts.extend([(c.x - r, c.y, 0.0), (c.x + r, c.y, 0.0), (c.x, c.y - r, 0.0), (c.x, c.y + r, 0.0)])
    return [(float(p[0]), float(p[1])) for p in pts]


def poly_points(entity):
    if entity.dxftype() == 'LWPOLYLINE':
        return [(float(p[0]), float(p[1])) for p in entity.get_points('xy')]
    if entity.dxftype() == 'POLYLINE':
        return [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
    return []


def polygon_area(points):
    if len(points) < 3:
        return 0.0
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1] -
                   points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points))) / 2.0)


def polygon_dims(points):
    arr = np.asarray(points, dtype=float)
    return (arr.max(axis=0) - arr.min(axis=0)).tolist() if len(arr) else []


def point_key(point, digits=3):
    return tuple(round(float(value), digits) for value in point)


def cross_2d(u, v):
    return float(u[0] * v[1] - u[1] * v[0])


def point_on_segment(point, a, b, tol=.01):
    p, a, b = map(lambda value: np.asarray(value, float), (point, a, b))
    return abs(cross_2d(b - a, p - a)) <= tol and np.dot(p - a, p - b) <= tol


def segments_intersect(a, b, c, d, tol=.01):
    def orient(p, q, r):
        return cross_2d(np.asarray(q, float) - p, np.asarray(r, float) - p)
    values = (orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b))
    if values[0] * values[1] < -tol and values[2] * values[3] < -tol:
        return True
    return ((abs(values[0]) <= tol and point_on_segment(c, a, b, tol)) or
            (abs(values[1]) <= tol and point_on_segment(d, a, b, tol)) or
            (abs(values[2]) <= tol and point_on_segment(a, c, d, tol)) or
            (abs(values[3]) <= tol and point_on_segment(b, c, d, tol)))


def simple_cycle(segments, dims, tol=.2, digits=3):
    normalized = [(point_key(a, digits), point_key(b, digits)) for a, b in segments]
    if any(a == b for a, b in normalized):
        return False
    if len({tuple(sorted((a, b))) for a, b in normalized}) != len(normalized):
        return False
    adjacency = {}
    for a, b in normalized:
        adjacency.setdefault(a, set()).add(b); adjacency.setdefault(b, set()).add(a)
    if len(adjacency) < 4 or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        return False
    start = next(iter(adjacency)); ordered = [start]; previous = None; current = start
    while True:
        following = next(iter(adjacency[current] - ({previous} if previous is not None else set())))
        if following == start:
            break
        if following in ordered:
            return False
        ordered.append(following); previous, current = current, following
    if len(ordered) != len(adjacency):
        return False
    points = np.asarray(ordered, float); envelope = points.max(0) - points.min(0)
    if np.max(np.abs(envelope - dims)) > tol or polygon_area(ordered) < .5 * dims[0] * dims[1]:
        return False
    for i, (a, b) in enumerate(normalized):
        for c, d in normalized[i + 1:]:
            if len({a, b} & {c, d}) == 1:
                continue
            if segments_intersect(a, b, c, d):
                return False
    return True


def closed_rect(entity, dims, tol=.15):
    points = poly_points(entity)
    return (bool(getattr(entity, 'is_closed', False)) and
            dims_match(polygon_dims(points), dims, tol) and
            close(polygon_area(points), dims[0] * dims[1], max(1.0, tol * sum(dims))))


def read_dxf_summary(name):
    path = ROOT / name
    doc = ezdxf.readfile(str(path))
    entities = list(doc.modelspace())
    layers = {str(entity.dxf.layer).upper() for entity in entities if hasattr(entity.dxf, 'layer')}
    points = []
    circles = []
    texts = []
    line_like_count = 0
    for entity in entities:
        points.extend(dxf_points(entity))
        if entity.dxftype() in {'LINE', 'LWPOLYLINE', 'POLYLINE'}:
            line_like_count += 1
        if entity.dxftype() == 'CIRCLE':
            c = entity.dxf.center
            circles.append({'x': float(c.x), 'y': float(c.y), 'r': float(entity.dxf.radius), 'layer': str(entity.dxf.layer).upper()})
        if entity.dxftype() in {'TEXT', 'MTEXT'}:
            texts.append(entity_text(entity))
    if len(points) >= 2:
        arr = np.asarray(points, dtype=float)
        bbox = (arr.max(axis=0) - arr.min(axis=0)).tolist()
    else:
        bbox = []
    return {'layers': layers, 'points': points, 'bbox': bbox, 'circles': circles, 'texts': texts, 'line_like_count': line_like_count}


def check_stage1_dxf():
    name = SPEC['dxf']['file']
    if not required_file(name, 200):
        return False
    try:
        doc = ezdxf.readfile(str(ROOT / name)); entities = list(doc.modelspace())
    except Exception as exc:
        return fail('ezdxf could not parse stage1 DXF: ' + str(exc))
    layers = {str(e.dxf.layer).upper() for e in entities}
    for layer in SPEC['dxf']['layers']:
        if layer.upper() not in layers:
            return fail('Stage1 DXF missing required layer: ' + layer)
    for layer in SPEC['dxf'].get('no_layers', []):
        if layer.upper() in layers:
            return fail('Stage1 DXF still contains forbidden construction layer: ' + layer)
    outlines = [e for e in entities if str(e.dxf.layer).upper() == 'OUTLINE' and
                e.dxftype() in {'LWPOLYLINE', 'POLYLINE'} and closed_rect(e, SPEC['dxf']['bbox'])]
    if len(outlines) != 1:
        return fail('Stage1 needs exactly one closed 105 x 48 OUTLINE')
    slots = [e for e in entities if str(e.dxf.layer).upper() == 'STRAP_SLOT' and
             e.dxftype() in {'LWPOLYLINE', 'POLYLINE'} and bool(e.is_closed) and
             polygon_area(poly_points(e)) > 10]
    if len(slots) != 2:
        return fail('Stage1 needs two distinct closed positive-area STRAP_SLOT regions')
    boxes = []
    for entity in slots:
        pts = np.asarray(poly_points(entity), float); lo, hi = pts.min(axis=0), pts.max(axis=0)
        if np.any(hi - lo < [3, 8]) or np.any(hi - lo > [18, 35]):
            return fail('A STRAP_SLOT is degenerate or implausibly large')
        if np.any(lo < 0) or np.any(hi > SPEC['dxf']['bbox']):
            return fail('A STRAP_SLOT lies outside the cradle outline')
        boxes.append((lo, hi))
    boxes.sort(key=lambda item: item[0][0])
    if boxes[0][1][0] >= boxes[1][0][0]:
        return fail('Stage1 STRAP_SLOT regions overlap')
    circles = [e for e in entities if e.dxftype() == 'CIRCLE']
    task_circles = [e for e in circles if str(e.dxf.layer).upper() == 'HOLE']
    if len(task_circles) != len(SPEC['dxf']['circles']):
        return fail('Stage1 needs exactly six HOLE circles')
    for req in SPEC['dxf'].get('circles', []):
        found = [circle for circle in circles if
            str(circle.dxf.layer).upper() == 'HOLE' and
            close(circle.dxf.center.x, req[0], .05) and close(circle.dxf.center.y, req[1], .05) and
            close(circle.dxf.radius, req[2], .03)]
        if len(found) != 1:
            return fail('Stage1 DXF needs one task circle near (%s, %s) radius %s' % (req[0], req[1], req[2]))
    labels = [entity_text(e) for e in entities if e.dxftype() in {'TEXT', 'MTEXT'} and str(e.dxf.layer).upper() == 'LABEL']
    normalized_labels = [norm(x) for x in labels]
    if any(normalized_labels.count(norm(required)) != 1 for required in SPEC['dxf']['texts']):
        return fail('Stage1 requires one of each task LABEL text')
    return ok('LibreCAD DXF has one outline, two closed strap slots, six exact holes, required labels, and no GUIDE')


def check_stl():
    name = SPEC['stl']['file']
    if not required_file(name, 200):
        return False
    try:
        mesh = trimesh.load_mesh(str(ROOT / name), file_type='stl', force='mesh', process=True)
    except Exception as exc:
        return fail('trimesh could not parse STL: ' + str(exc))
    if mesh is None or getattr(mesh, 'vertices', None) is None or len(mesh.vertices) == 0:
        return fail('STL has no readable vertices')
    if len(mesh.faces) < SPEC['stl']['min_triangles']:
        return fail('STL lacks substantial manufactured geometry')
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        return fail('STL must be watertight and consistently wound')
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = (bounds[1] - bounds[0]).tolist()
    if not dims_match(dims, SPEC['stl']['bbox'], SPEC['stl']['bbox_tol']):
        return fail('STL bbox mismatch got %s expected %s' % (dims, SPEC['stl']['bbox']))
    fill = abs(float(mesh.volume)) / float(np.prod(dims))
    if not SPEC['stl']['non_box_fill_range'][0] <= fill <= SPEC['stl']['non_box_fill_range'][1]:
        return fail('STL is empty or box-like: fill %.4f' % fill)
    vertices = np.asarray(mesh.vertices, float) - bounds[0]
    centers = np.asarray(mesh.triangles_center, float) - bounds[0]
    normals = np.asarray(mesh.face_normals, float)
    for x, y, r in SPEC['dxf']['circles']:
        radial = np.hypot(vertices[:, 0] - x, vertices[:, 1] - y)
        ring = vertices[np.abs(radial - r) < .45]
        cap = centers[(np.hypot(centers[:, 0] - x, centers[:, 1] - y) < r * .55) &
                      (np.abs(normals[:, 2]) > .8)]
        if len(ring) < 12 or np.ptp(ring[:, 2]) < max(3.0, r * 2) or len(cap):
            return fail('STL lacks a real cylindrical through-hole at %s' % [x, y])
    stage1 = ezdxf.readfile(str(ROOT / SPEC['dxf']['file']))
    slot_boxes = []
    for entity in stage1.modelspace():
        if str(entity.dxf.layer).upper() == 'STRAP_SLOT' and entity.dxftype() in {'LWPOLYLINE','POLYLINE'} and bool(entity.is_closed):
            pts=np.asarray(poly_points(entity),float); slot_boxes.append((pts.min(0),pts.max(0)))
    if len(slot_boxes) != 2:
        return fail('Cannot derive the two strap slots from stage1')
    for index,(lo,hi) in enumerate(sorted(slot_boxes,key=lambda b:b[0][0]),1):
        margin=np.minimum((hi-lo)*.22,[1.2,2.0])
        caps=centers[(centers[:,0]>lo[0]+margin[0])&(centers[:,0]<hi[0]-margin[0])&
                     (centers[:,1]>lo[1]+margin[1])&(centers[:,1]<hi[1]-margin[1])&
                     (np.abs(normals[:,2])>.8)]
        wall=vertices[(vertices[:,0]>=lo[0]-.5)&(vertices[:,0]<=hi[0]+.5)&
                      (vertices[:,1]>=lo[1]-.5)&(vertices[:,1]<=hi[1]+.5)]
        if len(caps) or len(wall)<8 or np.ptp(wall[:,2]) < dims[2] * .8:
            return fail('STL lacks real through-slot geometry for strap slot %d' % index)
    return ok('FreeCAD STL is watertight, non-box, and carries six bores plus two through strap slots')


def check_handoff_dxf():
    name = SPEC['handoff']['file']
    if not required_file(name, 200):
        return False
    try:
        doc = ezdxf.readfile(str(ROOT / name)); entities = list(doc.modelspace())
    except Exception as exc:
        return fail('ezdxf could not parse stage2 handoff DXF: ' + str(exc))
    outlines = [e for e in entities if e.dxftype() in {'LWPOLYLINE', 'POLYLINE'} and closed_rect(e, SPEC['dxf']['bbox'])]
    lines = [(tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]) for e in entities if e.dxftype() == 'LINE']
    pending = set(range(len(lines))); line_cycles = 0
    while pending:
        component = {pending.pop()}; changed = True
        while changed:
            changed = False; vertices = {point_key(point) for index in component for point in lines[index]}
            for index in list(pending):
                if any(point_key(point) in vertices for point in lines[index]):
                    pending.remove(index); component.add(index); changed = True
        if simple_cycle([lines[index] for index in component], SPEC['dxf']['bbox'], .15):
            line_cycles += 1
    if len(outlines) + line_cycles != 1:
        return fail('Handoff needs exactly one simple closed 105 x 48 interface outline')
    direct = {norm(entity_text(e)) for e in entities if e.dxftype() in {'TEXT', 'MTEXT'}}
    if {'FREECADTOKICAD', norm(SPEC['token'])}.issubset(direct):
        return ok('FreeCAD handoff has one closed interface and two directly parseable labels')
    return fail('Handoff lacks exact TEXT/MTEXT labels FREECAD_TO_KICAD and ' + SPEC['token'])


def balanced_blocks(text, head):
    blocks = []
    for match in re.finditer(r'\(' + re.escape(head) + r'(?=\s|\")', text):
        depth = 0; quoted = False; escaped = False
        for index in range(match.start(), len(text)):
            char = text[index]
            if quoted:
                if escaped: escaped = False
                elif char == '\\': escaped = True
                elif char == '"': quoted = False
            elif char == '"': quoted = True
            elif char == '(': depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    blocks.append(text[match.start():index + 1]); break
    return blocks


def first_xy(block, head):
    match = re.search(r'\(' + re.escape(head) + r'\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', block)
    return (float(match.group(1)), float(match.group(2))) if match else None


def edge_cut_segments(text):
    segments = []
    for block in balanced_blocks(text, 'gr_line'):
        if '(layer "Edge.Cuts")' not in block:
            continue
        a, b = first_xy(block, 'start'), first_xy(block, 'end')
        if a and b:
            segments.append((a, b))
    for block in balanced_blocks(text, 'gr_rect'):
        if '(layer "Edge.Cuts")' not in block:
            continue
        a, b = first_xy(block, 'start'), first_xy(block, 'end')
        if a and b:
            x0, y0 = a; x1, y1 = b
            corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            segments.extend(zip(corners, corners[1:] + corners[:1]))
    for block in balanced_blocks(text, 'gr_arc'):
        if '(layer "Edge.Cuts")' not in block:
            continue
        start, mid, end = first_xy(block, 'start'), first_xy(block, 'mid'), first_xy(block, 'end')
        if not (start and mid and end):
            continue
        a, b, c = np.asarray(start), np.asarray(mid), np.asarray(end)
        cross = cross_2d(b - a, c - a)
        if abs(cross) < 1e-9:
            continue
        # Tessellate the KiCad three-point arc only for topology, envelope, and
        # self-intersection checks; the native board remains untouched.
        matrix = np.asarray([[2 * (b[0] - a[0]), 2 * (b[1] - a[1])],
                             [2 * (c[0] - a[0]), 2 * (c[1] - a[1])]])
        rhs = np.asarray([np.dot(b, b) - np.dot(a, a), np.dot(c, c) - np.dot(a, a)])
        center = np.linalg.solve(matrix, rhs)
        angles = np.unwrap(np.arctan2(np.asarray([a[1], b[1], c[1]]) - center[1],
                                      np.asarray([a[0], b[0], c[0]]) - center[0]))
        if not (min(angles[0], angles[2]) <= angles[1] <= max(angles[0], angles[2])):
            angles[2] += 2 * math.pi * (1 if cross > 0 else -1)
        radius = np.linalg.norm(a - center); sweep = abs(angles[2] - angles[0])
        # Bound chord sagitta below 0.02 mm so envelope and intersection checks
        # remain tighter than the board-outline tolerance even for large arcs.
        max_step = 2 * math.acos(max(-1, 1 - .02 / max(radius, .02)))
        count = max(2, int(math.ceil(sweep / max(max_step, 1e-6))) + 1)
        points = [tuple(center + radius * np.asarray([math.cos(t), math.sin(t)]))
                  for t in np.linspace(angles[0], angles[2], count)]
        segments.extend(zip(points, points[1:]))
    return list(segments)


def check_kicad_board_file():
    name = SPEC['board_file']['file']
    if not required_file(name, 200):
        return False
    try:
        text = (ROOT / name).read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        return fail('Could not read KiCad board file: ' + str(exc))
    if not text.lstrip().startswith('(kicad_pcb') or not re.search(r'\(generator\s+"?pcbnew"?\)', text, re.I):
        return fail('Board is not a native pcbnew document')
    edge_segments = edge_cut_segments(text)
    if len(edge_segments)<4: return fail('Board has too little Edge.Cuts geometry')
    if not simple_cycle(edge_segments, SPEC['dxf']['bbox'], .2, 2):
        return fail('Board Edge.Cuts is not one simple closed 105 x 48 outline matching the handoff')
    dwgs_text='\n'.join(b for b in balanced_blocks(text,'gr_text') if '(layer "Dwgs.User")' in b)
    retained = {norm(x) for x in re.findall(r'\(gr_text\s+"([^"]+)',dwgs_text)}
    if not {'FREECADTOKICAD',norm(SPEC['token'])}.issubset(retained):
        return fail('Board does not retain exact FreeCAD handoff text on Dwgs.User')
    footprints = balanced_blocks(text, 'footprint'); got = {}
    for block in footprints:
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if ref: got[ref.group(1)] = len(balanced_blocks(block, 'pad'))
    required_refs = SPEC['kicad']['tokens'][1:]
    if any(got.get(ref, 0) < 2 for ref in required_refs):
        return fail('Board needs each named native component with at least two pads: ' + str(got))
    if sum(got.values()) < 12:
        return fail('Board needs at least 12 native pads: ' + str(got))
    pad_blob = '\n'.join(balanced_blocks(text, 'pad'))
    # KiCad 10 serializes the assigned native net name directly in each pad.
    pad_nets = set(re.findall(r'\(net\s+"([^"]+)"\)', pad_blob))
    for token in SPEC['kicad']['nets']:
        if token not in pad_nets:
            return fail('Required electrical token is not bound to native pads/nets: ' + token)
    silk = '\n'.join(b for b in balanced_blocks(text, 'gr_text') if '(layer "F.SilkS")' in b)
    for token in ['KICAD_TO_BLENDER','EDGE_FROM_STAGE2_HANDOFF',SPEC['handoff']['file'],SPEC['token']] + SPEC['kicad']['tokens']:
        if norm(token) not in norm(silk): return fail('Required token is not actual F.SilkS text: ' + token)
    for block in footprints:
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if not ref or ref.group(1) not in required_refs:
            continue
        at = first_xy(block, 'at')
        if not at or not (0 <= at[0] <= 105 and 0 <= at[1] <= 48):
            return fail('A required native component is outside the board: ' + ref.group(1))
    return ok('KiCad board retains the handoff and has six named padded components, six functional nets, outline, and silk')


def parse_svg_number(value):
    match = re.search(r'-?\d+(?:\.\d+)?', str(value or ''))
    return float(match.group(0)) if match else None


def visible_svg_stroke(value):
    stroke = str(value or '').strip().lower().replace(' ', '')
    if stroke in {'', 'none', 'transparent'}:
        return False
    rgba = re.fullmatch(r'rgba\([^,]+,[^,]+,[^,]+,([^)]+)\)', stroke)
    if rgba and (parse_svg_number(rgba.group(1)) or 0) <= 0:
        return False
    if re.fullmatch(r'#[0-9a-f]{8}', stroke) and stroke[-2:] == '00':
        return False
    if re.fullmatch(r'#[0-9a-f]{4}', stroke) and stroke[-1] == '0':
        return False
    return True


def svg_matrix(value):
    matrix = np.eye(3)
    for name,args in re.findall(r'(matrix|translate|scale)\s*\(([^)]*)\)', value or '', re.I):
        nums=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',args)]
        part=np.eye(3)
        if name.lower()=='translate' and nums:
            part[:2,2]=[nums[0],nums[1] if len(nums)>1 else 0]
        elif name.lower()=='scale' and nums:
            part[0,0]=nums[0]; part[1,1]=nums[1] if len(nums)>1 else nums[0]
        elif name.lower()=='matrix' and len(nums)>=6:
            a,b,c,d,e,f=nums[:6]; part=np.asarray([[a,c,e],[b,d,f],[0,0,1]],float)
        matrix=matrix @ part
    return matrix


def svg_element_segments(element, parent_matrix, inherited=None):
    matrix=parent_matrix @ svg_matrix(element.attrib.get('transform','')); tag=element.tag.lower().split('}')[-1]; points=[]; segments=[]
    parent = inherited or {'stroke':'none','visibility':'visible','stroke-opacity':'1',
                           '_displayed':True,'_opacity':1.0}
    style=dict(parent); local={}
    for item in element.attrib.get('style','').split(';'):
        if ':' in item:
            key,value=item.split(':',1); local[key.strip().lower()]=value.strip().lower()
    for key in ('stroke','display','visibility','opacity','stroke-opacity'):
        if key in element.attrib: local[key]=element.attrib[key].strip().lower()
    for key in ('stroke','visibility','stroke-opacity'):
        if key in local: style[key]=local[key]
    style['_displayed'] = bool(parent.get('_displayed', True) and local.get('display','inline') != 'none')
    opacity = parse_svg_number(local.get('opacity','1'))
    style['_opacity'] = float(parent.get('_opacity',1)) * (opacity if opacity is not None else 1)
    hidden=(not style['_displayed'] or style.get('visibility')=='hidden' or not visible_svg_stroke(style.get('stroke')) or
            style['_opacity'] <= 0 or parse_svg_number(style.get('stroke-opacity','1')) == 0)
    if tag in {'polyline','polygon'}:
        nums=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',element.attrib.get('points',''))]; points=list(zip(nums[::2],nums[1::2]))
        if tag=='polygon' and points: points.append(points[0])
    elif tag=='line':
        points=[(parse_svg_number(element.attrib.get('x1')) or 0,parse_svg_number(element.attrib.get('y1')) or 0),(parse_svg_number(element.attrib.get('x2')) or 0,parse_svg_number(element.attrib.get('y2')) or 0)]
    elif tag=='rect':
        x=parse_svg_number(element.attrib.get('x')) or 0; y=parse_svg_number(element.attrib.get('y')) or 0; w=parse_svg_number(element.attrib.get('width')) or 0; h=parse_svg_number(element.attrib.get('height')) or 0
        points=[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
    elif tag=='path':
        tokens=re.findall(r'[MmLlHhVvZz]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',element.attrib.get('d','')); cursor=np.zeros(2); start=None; i=0; cmd=None
        while i<len(tokens):
            if tokens[i].isalpha(): cmd=tokens[i]; i+=1
            if cmd in {'Z','z'}:
                if start is not None: points.append(tuple(start)); cursor=start.copy()
                cmd=None; continue
            if cmd in {'M','m','L','l'} and i+1<len(tokens):
                value=np.asarray([float(tokens[i]),float(tokens[i+1])]); i+=2
                cursor=value if cmd.isupper() else cursor+value
                if cmd in {'M','m'} and start is None: start=cursor.copy()
                points.append(tuple(cursor)); cmd='L' if cmd=='M' else ('l' if cmd=='m' else cmd)
            elif cmd in {'H','h'} and i<len(tokens):
                value=float(tokens[i]); i+=1; cursor[0]=value if cmd=='H' else cursor[0]+value; points.append(tuple(cursor))
            elif cmd in {'V','v'} and i<len(tokens):
                value=float(tokens[i]); i+=1; cursor[1]=value if cmd=='V' else cursor[1]+value; points.append(tuple(cursor))
            else: break
    if len(points)>=2 and not hidden:
        transformed=[tuple((matrix @ [x,y,1])[:2]) for x,y in points]; segments.extend(zip(transformed,transformed[1:]))
    for child in element: segments.extend(svg_element_segments(child,matrix,style))
    return segments


def check_board_profile_svg():
    name = SPEC['board_profile']['file']
    if not required_file(name, 100):
        return False
    try:
        tree = ET.parse(ROOT / name)
        root = tree.getroot()
    except Exception as exc:
        return fail('Could not parse KiCad-to-Blender SVG profile: ' + str(exc))
    if not root.tag.lower().endswith('svg'):
        return fail('Stage3 profile is not an SVG document')
    raw = (ROOT / name).read_text(encoding='utf-8', errors='ignore')
    if 'Image generated by PCBNEW' not in raw:
        return fail('SVG lacks PCBNEW provenance')
    segments = svg_element_segments(root,np.eye(3))
    if len(segments)<4: return fail('SVG has too little painted geometry for a board outline')
    segments=[(a,b) for a,b in segments if np.linalg.norm(np.asarray(a)-np.asarray(b))>.01]
    if not simple_cycle(segments, SPEC['dxf']['bbox'], .2, 2):
        return fail('SVG painted geometry is not one simple closed 105 x 48 board profile')
    return ok('KiCad SVG has PCBNEW provenance and painted closed 105 x 48 geometry')


def glb_json_and_bin(path):
    data = path.read_bytes()
    if data[:4] != b'glTF': raise ValueError('not binary glTF')
    json_len = struct.unpack_from('<I', data, 12)[0]
    doc = json.loads(data[20:20 + json_len].decode('utf-8').rstrip(' \x00'))
    offset = 20 + json_len; bin_len = struct.unpack_from('<I', data, offset)[0]
    return doc, data[offset + 8:offset + 8 + bin_len]


def accessor_array(doc, blob, index):
    acc = doc['accessors'][index]; view = doc['bufferViews'][acc['bufferView']]
    component = {5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}[acc['componentType']]
    width = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[acc['type']]
    start = view.get('byteOffset',0) + acc.get('byteOffset',0); stride = view.get('byteStride',width * component[1])
    return np.asarray([struct.unpack_from('<' + component[0] * width, blob, start + i * stride) for i in range(acc['count'])])


def node_matrix(node):
    if 'matrix' in node: return np.asarray(node['matrix'],float).reshape(4,4).T
    matrix=np.eye(4); t=np.asarray(node.get('translation',[0,0,0]),float); s=np.asarray(node.get('scale',[1,1,1]),float); x,y,z,w=node.get('rotation',[0,0,0,1])
    rotation=np.asarray([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]],float)
    matrix[:3,:3]=rotation @ np.diag(s); matrix[:3,3]=t; return matrix


def scene_world_matrices(doc):
    nodes=doc.get('nodes',[]); scene_index=doc.get('scene',0); roots=doc.get('scenes',[{}])[scene_index].get('nodes',[]); world={}
    def visit(index,parent):
        current=parent @ node_matrix(nodes[index]); world[index]=current
        for child in nodes[index].get('children',[]): visit(child,current)
    for root in roots: visit(root,np.eye(4))
    return world


def bidirectional_cover(a,b,tol=.08):
    def covered(source,target):
        for start in range(0,len(source),256):
            dist=np.linalg.norm(source[start:start+256,None,:]-target[None,:,:],axis=2)
            if np.max(np.min(dist,axis=1))>tol: return False
        return True
    return covered(a,b) and covered(b,a)


def check_glb():
    name = SPEC['glb']['file']
    if not required_file(name, 120):
        return False
    try:
        doc, blob = glb_json_and_bin(ROOT / name)
    except Exception as exc:
        return fail('pygltflib could not parse GLB: ' + str(exc))
    try:
        if 'Blender' not in str(doc.get('asset',{}).get('generator','')): return fail('GLB lacks Blender exporter provenance')
        nodes, meshes = doc.get('nodes',[]), doc.get('meshes',[]); world=scene_world_matrices(doc); named = {n.get('name',''):n for i,n in enumerate(nodes) if i in world}
    except Exception as exc: return fail('GLB scene graph is malformed: '+str(exc))
    indices={id(node):i for i,node in enumerate(nodes)}
    stl = [(k,n) for k,n in named.items() if 'stage2_wearable_charger_cradle' in k and isinstance(n.get('mesh'),int)]
    svg = [(k,n) for k,n in named.items() if 'stage3_wearable_charger_cradle_board_profile.svg' in k and isinstance(n.get('mesh'),int)]
    if len(stl) != 1 or len(svg) < 1: return fail('Active GLB scene lacks mesh-bound real STL or imported SVG profile geometry')
    def geometry(node):
        vertices=[]; faces=[]; mats=[]; offset=0
        for primitive in meshes[node['mesh']].get('primitives',[]):
            if primitive.get('mode',4)!=4: raise ValueError('non-TRIANGLES primitive')
            pos=accessor_array(doc,blob,primitive['attributes']['POSITION']); vertices.append(pos)
            inds=accessor_array(doc,blob,primitive['indices']).reshape(-1) if 'indices' in primitive else np.arange(len(pos))
            if len(inds)%3 or len(inds)==0 or np.any(inds<0) or np.any(inds>=len(pos)): raise ValueError('invalid triangle indices')
            faces.append(inds.reshape(-1,3)+offset); offset+=len(pos); mats.append(primitive.get('material'))
        return np.vstack(vertices), np.vstack(faces), mats
    def world_geometry(node):
        vertices,faces,mats=geometry(node); matrix=world[indices[id(node)]]
        with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
            transformed=(matrix @ np.c_[vertices,np.ones(len(vertices))].T).T[:,:3]
        if not np.all(np.isfinite(transformed)): raise ValueError('non-finite transformed vertices')
        tri=transformed[faces]; areas=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2; valid=areas>1e-8
        if not np.any(valid) or np.count_nonzero(valid)<max(1,int(len(valid)*.7)): raise ValueError('mostly degenerate triangles')
        return transformed,faces[valid],mats,areas[valid]
    materials = doc.get('materials',[])
    def visible_materials(indices, allow_unbound=True):
        for index in indices:
            if index is None and allow_unbound:
                continue
            if not isinstance(index,int) or index < 0 or index >= len(materials):
                return False
            material=materials[index]; pbr=material.get('pbrMetallicRoughness',{}); factor=pbr.get('baseColorFactor') or [1,1,1,1]
            alpha=float(factor[3]) if len(factor)>3 else 1.0; mode=material.get('alphaMode','OPAQUE')
            if (mode == 'BLEND' and alpha < .05) or (mode == 'MASK' and alpha < float(material.get('alphaCutoff',.5))):
                return False
        return True
    try: stlv, stlf, stlm, stla = world_geometry(stl[0][1])
    except Exception as exc: return fail('GLB imported STL geometry is malformed: '+str(exc))
    try:
        reference=trimesh.load_mesh(str(ROOT / SPEC['stl']['file']),force='mesh',process=True); rv=np.asarray(reference.vertices,float)
        # Blender's Y-up glTF exporter maps source (x,y,z) to (x,z,-y).
        expected=np.c_[rv[:,0],rv[:,2],-rv[:,1]]
    except Exception as exc: return fail('Cannot compare GLB with stage2 STL: '+str(exc))
    glb_centers=stlv[stlf].mean(1); source_tri=np.asarray(reference.triangles,float); expected_tri=source_tri[:,:,[0,2,1]]; expected_tri[:,:,2]*=-1; expected_centers=expected_tri.mean(1); expected_areas=np.linalg.norm(np.cross(expected_tri[:,1]-expected_tri[:,0],expected_tri[:,2]-expected_tri[:,0]),axis=1)/2
    if (len(stlf)<SPEC['stl']['min_triangles'] or not bidirectional_cover(np.unique(np.round(stlv,5),axis=0),np.unique(np.round(expected,5),axis=0),.12) or
            not bidirectional_cover(glb_centers,expected_centers,.2) or abs(float(stla.sum())-float(expected_areas.sum()))>2):
        return fail('GLB STL mesh does not bidirectionally preserve the stage2 STL geometry')
    if not stlm or any(not isinstance(i,int) or i < 0 or i >= len(materials) for i in stlm):
        return fail('Imported STL has no valid bound material')
    if not visible_materials(stlm, allow_unbound=False):
        return fail('Imported STL material is hidden or invalid')
    svg_world=[]
    for _,node in svg:
        try: v,f,mats,areas=world_geometry(node)
        except Exception as exc: return fail('An SVG edge mesh is malformed: '+str(exc))
        if len(f)<2 or areas.sum()<.1 or not visible_materials(mats): return fail('An SVG edge is not substantial visible geometry')
        svg_world.append(v)
    sv=np.vstack(svg_world); dims=sv.max(0)-sv.min(0)
    if (np.max(np.abs(dims[[0,2]] - SPEC['dxf']['bbox'])) > 1.0 or
            sv[:,1].min() < 19 or sv[:,1].max() > 25 or
            abs(float((sv[:,0].min()+sv[:,0].max())/2) - 52.5) > 1 or
            abs(float((sv[:,2].min()+sv[:,2].max())/2) + 24) > 1):
        return fail('GLB SVG profile is not full-scale and aligned above the STL: dims=%s min=%s max=%s' %
                    (np.round(dims, 3).tolist(), np.round(sv.min(0), 3).tolist(), np.round(sv.max(0), 3).tolist()))
    candidates=[]
    for name,node in named.items():
        if node in [item[1] for item in stl + svg] or not isinstance(node.get('mesh'),int):
            continue
        try: v,f,mats,areas=world_geometry(node)
        except Exception as exc: return fail('A scene feature mesh is malformed: '+str(exc))
        if not visible_materials(mats, allow_unbound=False):
            continue
        candidates.append((name,node,v,f,mats,areas))
    def material_values(mat_indices):
        values=[]
        for index in set(mat_indices):
            pbr=materials[index].get('pbrMetallicRoughness',{})
            color=(pbr.get('baseColorFactor') or [1,1,1,1])
            values.append((np.asarray(color[:3],float),float(color[3] if len(color)>3 else 1),
                           float(pbr.get('metallicFactor',1))))
        return values
    pogo=[]
    for item in candidates:
        _,_,v,f,mats,areas=item; extent=v.max(0)-v.min(0); center=(v.min(0)+v.max(0))/2
        gold=any(alpha>.2 and metal>=.5 and color[0]>.55 and color[1]>.25 and color[2]<.3
                 for color,alpha,metal in material_values(mats))
        if len(f)>=16 and areas.sum()>.5 and 1.5<=extent[0]<=5 and 1.5<=extent[2]<=5 and extent[1]>=3 and gold:
            pogo.append((item,center))
    if len(pogo) != 2:
        return fail('GLB needs exactly two substantial visible gold metallic pogo-pin meshes')
    pogo_centers=sorted([center for _,center in pogo],key=lambda c:c[0])
    for center,x in zip(pogo_centers,[48,57]):
        if abs(center[0]-x)>1 or abs(center[2]+24)>1 or center[1]<19:
            return fail('A gold pogo-pin mesh is misaligned to its required cradle location')
    slots=[]
    for item in candidates:
        if any(item is pogo_item for pogo_item,_ in pogo):
            continue
        _,_,v,f,mats,areas=item; extent=v.max(0)-v.min(0); center=(v.min(0)+v.max(0))/2
        highlight=any(alpha>.2 and max(color)-min(color)>.35 and max(color)>.65
                      for color,alpha,_ in material_values(mats))
        if len(f)>=8 and areas.sum()>8 and extent[0]>=3 and extent[2]>=8 and extent[1]>=.3 and highlight:
            slots.append((item,center))
    if len(slots) != 2:
        return fail('GLB needs exactly two substantial visible saturated strap-slot highlight meshes')
    slot_centers=sorted([center for _,center in slots],key=lambda c:c[0])
    stage1=ezdxf.readfile(str(ROOT / SPEC['dxf']['file'])); expected=[]
    for entity in stage1.modelspace():
        if (str(entity.dxf.layer).upper() == 'STRAP_SLOT' and
                entity.dxftype() in {'LWPOLYLINE','POLYLINE'} and bool(entity.is_closed)):
            pts=np.asarray(poly_points(entity),float); expected.append((pts.min(0)+pts.max(0))/2)
    expected=sorted(expected,key=lambda c:c[0])
    if len(expected) != 2:
        return fail('Cannot derive two strap-slot centers from stage1 for GLB alignment')
    for center,target in zip(slot_centers,expected):
        if abs(center[0]-target[0])>2 or abs(center[2]+target[1])>2 or center[1]<19:
            return fail('A strap-slot highlight mesh is misaligned to its stage1 slot')
    return ok('Blender GLB preserves active STL/SVG geometry and has aligned gold pogo pins plus two visible strap-slot highlights')


def main():
    checks = [
        check_dependencies,
        check_required_files,
        check_intermediate_outputs,
        check_stage1_dxf,
        check_stl,
        check_handoff_dxf,
        check_kicad_board_file,
        check_board_profile_svg,
        check_glb,
    ]
    for check in checks:
        try:
            valid = check()
        except Exception as exc:
            finish(fail('%s rejected malformed input: %s' % (check.__name__, exc)))
        if not valid:
            finish(False)
    finish(True)


if __name__ == '__main__':
    main()
