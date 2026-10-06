from __future__ import annotations
import json
import itertools
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = {'case_id': 'multi-gui-4-librecad-freecad-kicad-blender-task-05-ubuntu',
 'owner': 'taozhuo',
 'title': 'L-shaped cable strain relief bracket with tie slots',
 'domain': 'cable_management_bracket',
 'software_chain': ['librecad', 'freecad', 'kicad', 'blender'],
 'token': 'EW4G05',
 'required_files': ['stage1_l_cable_strain_bracket.dxf',
                    'stage2_l_cable_strain_bracket.stl',
                    'stage2_l_cable_strain_bracket_handoff_outline.dxf',
                    'stage3_l_cable_strain_bracket_board.kicad_pcb',
                    'stage3_l_cable_strain_bracket_board_profile.svg',
                    'stage4_l_cable_strain_bracket.glb'],
 'dxf': {'file': 'stage1_l_cable_strain_bracket.dxf',
         'bbox': [150.0, 90.0],
         'bbox_tol': 1.5,
         'circle_tol': 1.0,
         'radius_tol': 0.5,
         'layers': ['OUTLINE', 'TIE_SLOT', 'HOLE', 'LABEL'],
         'circles': [[12.0, 12.0, 2.6],
                     [138.0, 12.0, 2.6],
                     [12.0, 78.0, 2.6],
                     [52.0, 72.0, 2.0],
                     [78.0, 72.0, 2.0],
                     [104.0, 72.0, 2.0]],
         'texts': ['EW4G05', 'CABLE-IN', 'TIE1', 'TIE2'],
         'min_closed_slots': 2,
         'no_layers': ['GUIDE']},
 'stl': {'file': 'stage2_l_cable_strain_bracket.stl',
         'bbox': [150.0, 90.0, 24.0],
         'bbox_tol': 4.0,
         'min_triangles': 100,
         'max_fill_ratio': 0.75},
 'kicad': {'components': {'J1': 'JST cable input', 'D1': 'TVS diode', 'TP1': 'GND test pad'},
           'tokens': ['EW4G05', 'JST-J1', 'STRAIN-RELIEF', 'TVS-D1', 'GND-TEST', 'CLAMP-ZONE']},
 'glb': {'file': 'stage4_l_cable_strain_bracket.glb',
         'tokens': [],
         'min_nodes': 3,
         'min_materials': 1,
         'nodes': ['stage2_l_cable_strain_bracket', 'stage3_l_cable_strain_bracket_board_profile.svg'],
         'min_meshes': 1,
         'gui_export': True,
         'accepted_import_evidence': {'stage2_stl_object': 'stage2_l_cable_strain_bracket',
                                      'stage3_svg_object': 'stage3_l_cable_strain_bracket_board_profile.svg'}},
 'diversity_notes': {'geometry': 'L-shaped cable strain relief bracket with tie slots',
                     'electronic_focus': 'a small cable-entry PCB with JST input, TVS diode, '
                                         'ground test pad, and strain-relief keepout',
                     'visualization_focus': 'a bracket scene showing a black cable path through '
                                            'the inlet and tie slots'},
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
 'seed': {'file': 'seed_l_cable_strain_bracket.dxf',
          'desktop_path': '/home/user/Desktop/seed_l_cable_strain_bracket.dxf'},
 'generated_by': {'method': 'real_snapshot_software',
                  'versions': ['LibreCAD 2.2.0.2', 'FreeCAD 0.21.2', 'KiCad 10.0.2', 'Blender 4.2.3']},
 'handoff': {'file': 'stage2_l_cable_strain_bracket_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_l_cable_strain_bracket_board_profile.svg'},
 'intermediate_outputs': [{'stage': 'librecad',
                           'file': 'stage1_l_cable_strain_bracket.dxf',
                           'type': 'dxf',
                           'consumed_by': 'freecad',
                           'eval_check': 'check_stage1_dxf'},
                          {'stage': 'freecad',
                           'file': 'stage2_l_cable_strain_bracket.stl',
                           'type': 'stl',
                           'consumed_by': 'blender',
                           'eval_check': 'check_stl'},
                          {'stage': 'freecad',
                           'file': 'stage2_l_cable_strain_bracket_handoff_outline.dxf',
                           'type': 'dxf',
                           'consumed_by': 'kicad',
                           'eval_check': 'check_handoff_dxf'},
                          {'stage': 'kicad',
                           'file': 'stage3_l_cable_strain_bracket_board.kicad_pcb',
                           'type': 'kicad_pcb',
                           'consumed_by': 'blender',
                           'eval_check': 'check_kicad_board_file'},
                          {'stage': 'kicad',
                           'file': 'stage3_l_cable_strain_bracket_board_profile.svg',
                           'type': 'svg',
                           'consumed_by': 'blender',
                           'eval_check': 'check_board_profile_svg'}],
 'board_file': {'file': 'stage3_l_cable_strain_bracket_board.kicad_pcb'}}
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


def polyline_points(entity):
    if entity.dxftype() == 'LWPOLYLINE':
        return [(float(p[0]), float(p[1])) for p in entity.get_points('xy')]
    if entity.dxftype() == 'POLYLINE':
        return [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
    return []


def is_closed_polyline(entity):
    return entity.dxftype() in {'LWPOLYLINE', 'POLYLINE'} and bool(entity.is_closed)


def polygon_area(points):
    if len(points) < 3:
        return 0.0
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1] -
                   points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points))) / 2.0)


def polygon_dims(points):
    arr = np.asarray(points, dtype=float)
    return (arr.max(axis=0) - arr.min(axis=0)).tolist() if len(arr) else []


def is_l_profile(points, expected=(150.0, 90.0), tol=1.5):
    dims = polygon_dims(points)
    if not dims_match(dims, expected, tol):
        return False
    envelope = max(float(dims[0] * dims[1]), 1e-9)
    ratio = polygon_area(points) / envelope
    # A useful L profile occupies both arms but has a substantial concave cutout.
    return 0.25 <= ratio <= 0.78 and len(points) >= 6


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
        data = read_dxf_summary(name)
    except Exception as exc:
        return fail('ezdxf could not parse stage1 DXF: ' + str(exc))
    for layer in SPEC['dxf']['layers']:
        if layer.upper() not in data['layers']:
            return fail('Stage1 DXF missing required layer: ' + layer)
    doc = ezdxf.readfile(str(ROOT / name))
    entities = list(doc.modelspace())
    for layer in SPEC['dxf'].get('no_layers', []):
        if any(str(entity.dxf.layer).upper() == layer.upper() for entity in entities):
            return fail('Stage1 DXF still contains forbidden construction entities on layer: ' + layer)
    if not dims_match(data['bbox'], SPEC['dxf']['bbox'], SPEC['dxf'].get('bbox_tol', 1.2)):
        return fail('Stage1 DXF bbox mismatch got %s expected %s' % (data['bbox'], SPEC['dxf']['bbox']))
    outlines = [entity for entity in entities if str(entity.dxf.layer).upper() == 'OUTLINE' and is_closed_polyline(entity)]
    if not any(is_l_profile(polyline_points(entity), SPEC['dxf']['bbox'], SPEC['dxf']['bbox_tol']) for entity in outlines):
        return fail('Stage1 OUTLINE lacks a closed non-rectangular L profile spanning 150 x 90 mm')
    slots = [entity for entity in entities if str(entity.dxf.layer).upper() == 'TIE_SLOT' and
             is_closed_polyline(entity) and polygon_area(polyline_points(entity)) > 1.0]
    if len(slots) < SPEC['dxf'].get('min_closed_slots', 2):
        return fail('Stage1 requires at least two real closed positive-area tie-slot outlines')
    task_circles = [circle for circle in data['circles'] if circle['layer'] == 'HOLE']
    if len(task_circles) < len(SPEC['dxf']['circles']):
        return fail('Stage1 lacks one or more of the six specified HOLE circles')
    for req in SPEC['dxf'].get('circles', []):
        found = sum(
            close(circle['x'], req[0], SPEC['dxf'].get('circle_tol', 0.9)) and
            close(circle['y'], req[1], SPEC['dxf'].get('circle_tol', 0.9)) and
            close(circle['r'], req[2], SPEC['dxf'].get('radius_tol', 0.45))
            for circle in task_circles
        )
        if found != 1:
            return fail('Stage1 DXF missing circle near (%s, %s) radius %s' % (req[0], req[1], req[2]))
    label_texts = [entity_text(entity) for entity in entities if entity.dxftype() in {'TEXT', 'MTEXT'} and
                   str(entity.dxf.layer).upper() == 'LABEL']
    text_blob = norm(' '.join(label_texts))
    for token in SPEC['dxf'].get('texts', []):
        if norm(token) not in text_blob:
            return fail('Stage1 DXF missing text token: ' + token)
    return ok('Stage1 LibreCAD DXF has a closed L outline, closed tie slots, six holes, and LABEL text')


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
    if len(getattr(mesh, 'faces', [])) < SPEC['stl'].get('min_triangles', 12):
        return fail('STL has too few triangles')
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = (bounds[1] - bounds[0]).tolist()
    tol = SPEC['stl'].get('bbox_tol', 4.0)
    if any(abs(g - e) > tol for g, e in zip(dims, SPEC['stl']['bbox'])):
        return fail('STL bbox mismatch got %s expected %s' % (dims, SPEC['stl']['bbox']))
    if not mesh.is_watertight:
        return fail('STL must be a watertight manufactured bracket')
    fill = abs(float(mesh.volume)) / max(float(np.prod(np.asarray(dims))), 1e-9)
    if not (0.04 <= fill <= SPEC['stl'].get('max_fill_ratio', 0.75)):
        return fail('STL is empty or too close to a full rectangular box: fill %.4f' % fill)
    vertices = np.asarray(mesh.vertices, dtype=float)
    local = vertices - bounds[0]
    top = local[local[:, 2] > dims[2] - 0.2]
    height_levels = np.unique(np.round(local[:, 2], 1))
    if (len(height_levels) < 3 or len(top) < 4 or
            min(np.ptp(top[:, :2], axis=0)) > 0.25 * min(dims[:2]) or
            max(np.ptp(top[:, :2], axis=0)) < 0.50 * max(dims[:2])):
        return fail('STL lacks a localized raised bracket wall at its maximum height')
    for x, y, radius in SPEC['dxf']['circles']:
        radial = np.hypot(local[:, 0] - x, local[:, 1] - y)
        ring = local[np.abs(radial - radius) < 0.20]
        if len(ring) < 24 or np.ptp(ring[:, 2]) < 3.5:
            return fail('STL lacks a substantial through-hole near (%s, %s) radius %s' % (x, y, radius))
    stage1 = ezdxf.readfile(str(ROOT / SPEC['dxf']['file']))
    slots = [polyline_points(entity) for entity in stage1.modelspace() if
             str(entity.dxf.layer).upper() == 'TIE_SLOT' and is_closed_polyline(entity)]
    for points in slots:
        slot = np.asarray(points, dtype=float); lo = slot.min(axis=0); hi = slot.max(axis=0)
        near = local[(local[:, 0] >= lo[0] - .3) & (local[:, 0] <= hi[0] + .3) &
                     (local[:, 1] >= lo[1] - .3) & (local[:, 1] <= hi[1] + .3)]
        edge_hits = np.count_nonzero((np.abs(near[:, 0] - lo[0]) < .25) |
                                     (np.abs(near[:, 0] - hi[0]) < .25) |
                                     (np.abs(near[:, 1] - lo[1]) < .25) |
                                     (np.abs(near[:, 1] - hi[1]) < .25))
        if edge_hits < 8 or np.ptp(near[:, 2]) < 3.0:
            return fail('STL lacks a real opening matching a stage1 tie slot')
    return ok('FreeCAD STL is full-size, watertight, non-box geometry with base openings and a raised wall')


def check_handoff_dxf():
    name = SPEC['handoff']['file']
    if not required_file(name, 200):
        return False
    try:
        data = read_dxf_summary(name)
    except Exception as exc:
        return fail('ezdxf could not parse stage2 handoff DXF: ' + str(exc))
    expected_xy = SPEC['stl']['bbox'][:2]
    if not dims_match(data['bbox'], expected_xy, SPEC['dxf'].get('bbox_tol', 1.5)):
        return fail('Stage2 handoff DXF bbox %s does not match FreeCAD STL XY %s' % (data['bbox'], expected_xy))
    doc = ezdxf.readfile(str(ROOT / name))
    entities = list(doc.modelspace())
    outlines = [entity for entity in entities if is_closed_polyline(entity) and
                is_l_profile(polyline_points(entity), expected_xy, SPEC['dxf']['bbox_tol'])]
    if len(outlines) != 1:
        return fail('Handoff requires one closed L-shaped board-interface outline')
    inserts = [entity for entity in entities if entity.dxftype() == 'INSERT']
    plain = norm(' '.join(entity_text(entity) for entity in entities if entity.dxftype() in {'TEXT', 'MTEXT'}))
    text_labels = norm('FREECAD_TO_KICAD') in plain and norm(SPEC['token']) in plain
    shape_labels = sum(len(list(doc.blocks.get(entity.dxf.name))) >= 6 for entity in inserts) >= 2
    if not (text_labels or shape_labels):
        return fail('Handoff lacks two visible FreeCAD label representations (text or substantial ShapeString blocks)')
    return ok('Stage2 handoff has one closed L outline and two visible label exports')


def balanced_blocks(text, head):
    blocks = []
    pattern = re.compile(r'\(' + re.escape(head) + r'(?=\s|\")')
    for match in pattern.finditer(text):
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


def point_in_polygon(point, polygon):
    x, y = point; inside = False
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        x1, y1 = first; x2, y2 = second
        if min(y1, y2) <= y <= max(y1, y2) and abs(y2 - y1) < 1e-9 and min(x1, x2) <= x <= max(x1, x2):
            return True
        if min(x1, x2) <= x <= max(x1, x2) and abs(x2 - x1) < 1e-9 and min(y1, y2) <= y <= max(y1, y2):
            return True
        if (y1 > y) != (y2 > y):
            crossing = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if crossing >= x: inside = not inside
    return inside


def edge_segments(text):
    segments = []
    for block in balanced_blocks(text, 'gr_line'):
        if not re.search(r'\(layer\s+"Edge\.Cuts"\)', block): continue
        start, end = first_xy(block, 'start'), first_xy(block, 'end')
        if start and end: segments.append((start, end))
    return segments


def closed_cycle(segments, tol=0.2):
    if len(segments) < 6: return []
    def key(point): return tuple(int(round(value / tol)) for value in point)
    coordinates = {}; adjacency = {}
    for start, end in segments:
        a, b = key(start), key(end); coordinates[a] = start; coordinates[b] = end
        adjacency.setdefault(a, []).append(b); adjacency.setdefault(b, []).append(a)
    if not adjacency or any(len(items) != 2 for items in adjacency.values()): return []
    first = next(iter(adjacency)); previous = None; current = first; cycle = []
    while True:
        cycle.append(coordinates[current]); choices = [item for item in adjacency[current] if item != previous]
        if not choices: return []
        following = choices[0]
        if following == first: break
        if following in {key(item) for item in cycle}: return []
        previous, current = current, following
        if len(cycle) > len(adjacency): return []
    return cycle if len(cycle) == len(adjacency) else []


def edge_profile(text):
    segments = edge_segments(text); cycle = closed_cycle(segments)
    if cycle: return cycle
    for block in balanced_blocks(text, 'gr_poly'):
        if not re.search(r'\(layer\s+"Edge\.Cuts"\)', block): continue
        points = [(float(x), float(y)) for x, y in re.findall(
            r'\(xy\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\)', block)]
        if len(points) >= 6: return points
    return []


def is_kicad_l_profile(points):
    if len(points) < 6: return False
    dims = polygon_dims(points)
    if not dims_match(dims, SPEC['dxf']['bbox'], SPEC['dxf']['bbox_tol']): return False
    ratio = polygon_area(points) / (150.0 * 90.0)
    return 0.25 <= ratio <= 0.80


def check_kicad_board_file():
    name = SPEC['board_file']['file']
    if not required_file(name, 200):
        return False
    try:
        text = (ROOT / name).read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        return fail('Could not read KiCad board file: ' + str(exc))
    if not text.lstrip().startswith('(kicad_pcb') or not re.search(r'\(generator\s+"?pcbnew"?\)', text, re.I):
        return fail('Board is not a native pcbnew kicad_pcb document')
    profile = edge_profile(text)
    if not is_kicad_l_profile(profile):
        return fail('Native Edge.Cuts do not form one closed 150 x 90 L-shaped outline')
    user_lines = [block for block in balanced_blocks(text, 'gr_line') if
                  re.search(r'\(layer\s+"Dwgs\.User"\)', block)]
    user_circles = []
    for block in balanced_blocks(text, 'gr_circle'):
        if not re.search(r'\(layer\s+"Dwgs\.User"\)', block): continue
        center, end = first_xy(block, 'center'), first_xy(block, 'end')
        if center and end:
            user_circles.append(math.hypot(end[0] - center[0], end[1] - center[1]))
    expected_radii = [circle[2] for circle in SPEC['dxf']['circles']]
    unmatched = list(user_circles)
    for radius in expected_radii:
        match = next((index for index, value in enumerate(unmatched) if close(value, radius, .35)), None)
        if match is None:
            return fail('Dwgs.User lacks circular evidence from the imported FreeCAD handoff')
        unmatched.pop(match)
    if len(user_lines) < 24:
        return fail('Board lacks substantial Dwgs.User vector evidence from the complete imported handoff')
    footprints = balanced_blocks(text, 'footprint')
    found = {}
    for block in footprints:
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        value = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
        at = first_xy(block, 'at')
        if ref and value and at is not None:
            found[ref.group(1)] = (value.group(1), len(balanced_blocks(block, 'pad')), at)
    semantics = {'J1': ('JST', 'CABLE', 'CONN'), 'D1': ('TVS', 'DIODE'), 'TP1': ('GND', 'TEST', 'PAD')}
    for ref, words in semantics.items():
        if ref not in found or found[ref][1] < 1 or not any(word in found[ref][0].upper() for word in words):
            return fail('Board lacks a native padded semantic footprint for ' + ref)
        if not point_in_polygon(found[ref][2], profile):
            return fail('Required footprint lies outside the L board: ' + ref)
    zones = balanced_blocks(text, 'zone')
    keepouts = []
    for block in zones:
        if not re.search(r'\(keepout\b', block): continue
        points = [(float(x), float(y)) for x, y in re.findall(
            r'\(xy\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\)', block)]
        if len(points) >= 3 and polygon_area(points) > 1.0 and all(point_in_polygon(point, profile) for point in points):
            keepouts.append(block)
    if not keepouts:
        return fail('Board lacks a native positive-area rule-area keepout')
    silk = ' '.join(block for block in balanced_blocks(text, 'gr_text') if re.search(r'\(layer\s+"F\.SilkS"\)', block))
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file']] + SPEC['kicad']['tokens']:
        if norm(token) not in norm(silk):
            return fail('Required transfer token is not native F.SilkS text: ' + token)
    return ok('KiCad board has native semantic footprints/pads, a closed L Edge.Cuts, keepout, and silkscreen')


def parse_svg_number(value):
    match = re.search(r'-?\d+(?:\.\d+)?', str(value or ''))
    return float(match.group(0)) if match else None


def svg_transform_matrix(raw):
    matrix = np.eye(3)
    for name, values_raw in re.findall(r'([A-Za-z]+)\s*\(([^)]*)\)', str(raw or '')):
        values = [float(item) for item in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?', values_raw, re.I)]
        item = np.eye(3); name = name.lower()
        if name == 'translate' and values:
            item[0, 2] = values[0]; item[1, 2] = values[1] if len(values) > 1 else 0.0
        elif name == 'scale' and values:
            item[0, 0] = values[0]; item[1, 1] = values[1] if len(values) > 1 else values[0]
        elif name == 'matrix' and len(values) == 6:
            a, b, c, d, e, f = values; item = np.asarray([[a, c, e], [b, d, f], [0, 0, 1]], dtype=float)
        elif name == 'rotate' and values:
            angle = math.radians(values[0]); cosine, sine = math.cos(angle), math.sin(angle)
            rotate = np.asarray([[cosine, -sine, 0], [sine, cosine, 0], [0, 0, 1]])
            if len(values) >= 3:
                cx, cy = values[1:3]
                before = np.asarray([[1, 0, cx], [0, 1, cy], [0, 0, 1]])
                after = np.asarray([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]])
                item = before @ rotate @ after
            else: item = rotate
        else:
            return None
        matrix = matrix @ item
    return matrix


def transform_svg_points(points, matrix):
    array = np.asarray(points, dtype=float)
    homogeneous = np.column_stack((array, np.ones(len(array))))
    return (matrix @ homogeneous.T).T[:, :2].tolist()


def svg_linear_path_points(raw):
    tokens = re.findall(r'[MLHVZmlhvz]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?', raw, re.I)
    points = []; current = np.zeros(2); start = None; command = None; index = 0
    while index < len(tokens):
        if re.fullmatch(r'[MLHVZmlhvz]', tokens[index]):
            command = tokens[index]; index += 1
            if command in 'Zz':
                if start is not None: points.append(tuple(start))
                continue
        if command is None or command in 'Zz': return []
        try:
            if command in 'MmLl':
                value = np.asarray([float(tokens[index]), float(tokens[index + 1])]); index += 2
                current = current + value if command.islower() else value
                if start is None: start = current.copy()
                points.append(tuple(current))
                if command == 'M': command = 'L'
                elif command == 'm': command = 'l'
            elif command in 'Hh':
                value = float(tokens[index]); index += 1
                current[0] = current[0] + value if command == 'h' else value; points.append(tuple(current))
            elif command in 'Vv':
                value = float(tokens[index]); index += 1
                current[1] = current[1] + value if command == 'v' else value; points.append(tuple(current))
        except (ValueError, IndexError): return []
    return points


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
    painted_paths = []; painted_segments = []
    def css(value):
        return {k.strip().lower(): v.strip().lower() for k, v in
                (part.split(':', 1) for part in str(value or '').split(';') if ':' in part)}
    def opacity(value, default=1.0):
        try:
            item = str(value).strip(); return float(item.rstrip('%')) / (100.0 if '%' in item else 1.0)
        except Exception: return default
    def visit(element, inherited, parent_matrix):
        style = dict(inherited); style.update(css(element.attrib.get('style')))
        own_matrix = svg_transform_matrix(element.attrib.get('transform'))
        if own_matrix is None: return
        matrix = parent_matrix @ own_matrix
        for key in ('display', 'visibility', 'stroke', 'fill', 'opacity', 'stroke-opacity', 'fill-opacity'):
            if key in element.attrib: style[key] = element.attrib[key].strip().lower()
        hidden = style.get('display') == 'none' or style.get('visibility') in {'hidden', 'collapse'} or opacity(style.get('opacity'), 1) <= .001
        tag = element.tag.rsplit('}', 1)[-1].lower()
        painted = ((style.get('stroke', 'none') not in {'none', 'transparent'} and opacity(style.get('stroke-opacity'), 1) > .001) or
                   (style.get('fill', 'none') not in {'none', 'transparent'} and opacity(style.get('fill-opacity'), 1) > .001))
        if not hidden and painted and tag in {'path', 'polygon', 'polyline'}:
            raw = element.attrib.get('d', '') if tag == 'path' else element.attrib.get('points', '')
            nums = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?', raw, re.I)]
            closed = tag == 'polygon' or (tag == 'path' and bool(re.search(r'[zZ]', raw)))
            if closed and len(nums) >= 8:
                painted_paths.append((tag, raw, nums, matrix))
            elif tag in {'path', 'polyline'} and len(nums) == 4 and not re.search(r'[CSQTA]', raw, re.I):
                first, second = transform_svg_points(((nums[0], nums[1]), (nums[2], nums[3])), matrix)
                painted_segments.append((tuple(first), tuple(second)))
        for child in list(element): visit(child, style, matrix)
    visit(root, {}, np.eye(3))
    if not painted_paths and not painted_segments:
        return fail('Stage3 SVG has no actually painted profile geometry')
    l_evidence = False
    for tag, raw, nums, matrix in painted_paths:
        if tag == 'path':
            points = svg_linear_path_points(raw) if not re.search(r'[CSQTA]', raw, re.I) else []
        else:
            points = list(zip(nums[::2], nums[1::2]))
            if tag == 'polygon' and points: points.append(points[0])
        if points: points = transform_svg_points(points, matrix)
        if len(points) >= 7 and np.linalg.norm(np.asarray(points[0]) - np.asarray(points[-1])) < 1e-4:
            dims = polygon_dims(points[:-1]); ratio = max(dims) / max(min(dims), 1e-9)
            area_ratio = polygon_area(points[:-1]) / max(float(dims[0] * dims[1]), 1e-9)
            if dims_match(sorted(dims), [90.0, 150.0], 1.5) and close(ratio, 150.0 / 90.0, 0.08) and 0.25 <= area_ratio <= 0.80:
                l_evidence = True
    cycle = closed_cycle(painted_segments, tol=0.001)
    if cycle:
        dims = polygon_dims(cycle); ratio = max(dims) / max(min(dims), 1e-9)
        area_ratio = polygon_area(cycle) / max(float(dims[0] * dims[1]), 1e-9)
        if dims_match(sorted(dims), [90.0, 150.0], 1.5) and close(ratio, 150.0 / 90.0, 0.08) and 0.25 <= area_ratio <= 0.80:
            l_evidence = True
    if not l_evidence:
        return fail('Painted SVG geometry does not contain a closed multi-corner L-profile candidate')
    return ok('KiCad SVG contains an actually painted, closed, concave 150:90 L-profile')


def collect_glb_strings(value, out):
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            collect_glb_strings(item, out)
    elif isinstance(value, list):
        for item in value:
            collect_glb_strings(item, out)
    elif value is not None:
        out.append(str(value))


def gltf_accessor_positions(gltf, accessor_index):
    if accessor_index is None or not (0 <= accessor_index < len(gltf.accessors or [])):
        return np.empty((0, 3), dtype=float)
    accessor = gltf.accessors[accessor_index]
    if accessor.bufferView is None or accessor.componentType != 5126 or accessor.type != 'VEC3':
        return np.empty((0, 3), dtype=float)
    view = gltf.bufferViews[accessor.bufferView]
    offset = int(view.byteOffset or 0) + int(accessor.byteOffset or 0)
    stride = int(view.byteStride or 12); blob = gltf.binary_blob()
    if accessor.count <= 0 or offset + (accessor.count - 1) * stride + 12 > len(blob):
        return np.empty((0, 3), dtype=float)
    return np.asarray([struct.unpack_from('<3f', blob, offset + index * stride)
                       for index in range(accessor.count)], dtype=float)


def node_matrix(node):
    if node.matrix and len(node.matrix) == 16:
        return np.asarray(node.matrix, dtype=float).reshape((4, 4), order='F')
    translation = np.asarray(node.translation or [0, 0, 0], dtype=float)
    scale = np.asarray(node.scale or [1, 1, 1], dtype=float)
    x, y, z, w = [float(value) for value in (node.rotation or [0, 0, 0, 1])]
    rotation = np.asarray([[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w],
                           [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w],
                           [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]])
    matrix = np.eye(4); matrix[:3, :3] = rotation @ np.diag(scale); matrix[:3, 3] = translation
    return matrix


def gltf_world_matrices(gltf):
    parents = {child: parent for parent, node in enumerate(gltf.nodes or []) for child in (node.children or [])}
    result = {}
    for index in range(len(gltf.nodes or [])):
        chain, current, seen = [], index, set()
        while current not in seen:
            seen.add(current); chain.append(current)
            if current not in parents: break
            current = parents[current]
        matrix = np.eye(4)
        for item in reversed(chain): matrix = matrix @ node_matrix(gltf.nodes[item])
        result[index] = matrix
    return result


def transformed_positions(gltf, node_index, matrices):
    node = gltf.nodes[node_index]
    if node.mesh is None or not (0 <= node.mesh < len(gltf.meshes or [])):
        return np.empty((0, 3), dtype=float), [], []
    chunks, material_ids, components = [], [], []
    for primitive in gltf.meshes[node.mesh].primitives or []:
        points = gltf_accessor_positions(gltf, getattr(primitive.attributes, 'POSITION', None))
        if len(points):
            homogeneous = np.column_stack((points, np.ones(len(points))))
            with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
                transformed = (matrices[node_index] @ homogeneous.T).T[:, :3]
            chunks.append(transformed)
            components.append(primitive_components(gltf, primitive, len(points)))
        material_ids.append(primitive.material)
    return (np.vstack(chunks) if chunks else np.empty((0, 3))), material_ids, components


def gltf_accessor_indices(gltf, accessor_index):
    if accessor_index is None or not (0 <= accessor_index < len(gltf.accessors or [])):
        return np.empty(0, dtype=int)
    accessor = gltf.accessors[accessor_index]
    formats = {5121: ('<B', 1), 5123: ('<H', 2), 5125: ('<I', 4)}
    if accessor.bufferView is None or accessor.componentType not in formats or accessor.type != 'SCALAR':
        return np.empty(0, dtype=int)
    fmt, width = formats[accessor.componentType]; view = gltf.bufferViews[accessor.bufferView]
    offset = int(view.byteOffset or 0) + int(accessor.byteOffset or 0)
    stride = int(view.byteStride or width); blob = gltf.binary_blob()
    if accessor.count <= 0 or offset + (accessor.count - 1) * stride + width > len(blob):
        return np.empty(0, dtype=int)
    return np.asarray([struct.unpack_from(fmt, blob, offset + index * stride)[0]
                       for index in range(accessor.count)], dtype=int)


def primitive_components(gltf, primitive, vertex_count):
    indices = gltf_accessor_indices(gltf, primitive.indices)
    if primitive.mode not in (None, 4) or len(indices) < 3 or len(indices) % 3:
        return 0
    parent = list(range(vertex_count))
    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]; item = parent[item]
        return item
    def union(a, b):
        a, b = find(a), find(b)
        if a != b: parent[b] = a
    used = set()
    for a, b, c in indices.reshape((-1, 3)):
        if max(a, b, c) >= vertex_count: return 0
        used.update((int(a), int(b), int(c))); union(int(a), int(b)); union(int(b), int(c))
    return len({find(item) for item in used})


def vertex_overlap_allowing_axes(source_points, candidate_points, quantum=0.08):
    source_dims = np.ptp(source_points, axis=0)
    source_zero = source_points - source_points.min(axis=0)
    source_set = {tuple(row) for row in np.round(source_zero / quantum).astype(int)}
    best = (0.0, 0.0)
    for order in itertools.permutations(range(3)):
        candidate = candidate_points[:, order].copy()
        if np.max(np.abs(np.ptp(candidate, axis=0) - source_dims)) > 1.0: continue
        candidate -= candidate.min(axis=0)
        for flips in itertools.product((False, True), repeat=3):
            transformed = candidate.copy()
            for axis, flip in enumerate(flips):
                if flip: transformed[:, axis] = source_dims[axis] - transformed[:, axis]
            candidate_set = {tuple(row) for row in np.round(transformed / quantum).astype(int)}
            common = len(source_set & candidate_set)
            score = (common / max(1, len(source_set)), common / max(1, len(candidate_set)))
            best = max(best, score, key=lambda item: min(item))
    return best


def svg_segment_cycle(path):
    root = ET.parse(path).getroot(); segments = []
    def visit(element, parent_matrix):
        own = svg_transform_matrix(element.attrib.get('transform'))
        if own is None: return
        matrix = parent_matrix @ own
        if element.tag.rsplit('}', 1)[-1].lower() == 'path':
            raw = element.attrib.get('d', '')
            nums = [float(value) for value in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?', raw, re.I)]
            if len(nums) == 4 and not re.search(r'[CSQTAZ]', raw, re.I):
                points = transform_svg_points(((nums[0], nums[1]), (nums[2], nums[3])), matrix)
                segments.append((tuple(points[0]), tuple(points[1])))
        for child in list(element): visit(child, matrix)
    visit(root, np.eye(3))
    return closed_cycle(segments, tol=.001)


def planar_l_shape(points, component_counts, expected_cycle):
    dims = np.ptp(points, axis=0); axes = np.argsort(dims)[-2:]
    projected = points[:, axes]; size = np.ptp(projected, axis=0)
    if not dims_match(sorted(size), [90.0, 150.0], 3.0): return False
    normalized = (projected - projected.min(axis=0)) / np.maximum(size, 1e-9)
    # A rectangle occupies all four quadrant corners. An L profile has exactly one
    # substantially empty quadrant while spanning both full arms.
    counts = [np.count_nonzero((normalized[:, 0] < .42 if x == 0 else normalized[:, 0] > .58) &
                               (normalized[:, 1] < .42 if y == 0 else normalized[:, 1] > .58))
              for x, y in ((0, 0), (1, 0), (0, 1), (1, 1))]
    if sum(count < 3 for count in counts) != 1 or not component_counts:
        return False
    if any(count < 1 or count > len(expected_cycle) for count in component_counts):
        return False
    target = np.asarray(expected_cycle, dtype=float)
    target -= target.min(axis=0)
    for order in itertools.permutations(range(2)):
        candidate = projected[:, order].copy(); candidate -= candidate.min(axis=0)
        if np.max(np.abs(np.ptp(candidate, axis=0) - np.ptp(target, axis=0))) > 3.0: continue
        for flips in itertools.product((False, True), repeat=2):
            aligned = candidate.copy()
            for axis, flip in enumerate(flips):
                if flip: aligned[:, axis] = np.ptp(target, axis=0)[axis] - aligned[:, axis]
            if all(np.min(np.linalg.norm(aligned - corner, axis=1)) < 1.2 for corner in target):
                return True
    return False


def check_glb():
    name = SPEC['glb']['file']
    if not required_file(name, 120):
        return False
    try:
        gltf = GLTF2().load_binary(str(ROOT / name))
    except Exception as exc:
        return fail('pygltflib could not parse GLB: ' + str(exc))
    nodes = gltf.nodes or []
    meshes = gltf.meshes or []
    materials = gltf.materials or []
    if len(nodes) < SPEC['glb'].get('min_nodes', 2):
        return fail('GLB has too few named nodes')
    if len(meshes) < SPEC['glb'].get('min_meshes', 1):
        return fail('GLB has too few meshes from imported geometry')
    if len(materials) < SPEC['glb'].get('min_materials', 0):
        return fail('GLB has too few materials')
    strings = []; collect_glb_strings(gltf.to_dict(), strings)
    if 'BLENDER' not in '\n'.join(strings).upper():
        return fail('GLB metadata should indicate Blender GUI export/generation')
    scene_index = gltf.scene if gltf.scene is not None else 0
    roots = list(gltf.scenes[scene_index].nodes or []) if gltf.scenes and 0 <= scene_index < len(gltf.scenes) else []
    reachable, stack = set(), list(roots)
    while stack:
        index = stack.pop()
        if index in reachable or not (0 <= index < len(nodes)): continue
        reachable.add(index); stack.extend(nodes[index].children or [])
    matrices = gltf_world_matrices(gltf)
    records = []
    for index in reachable:
        points, material_ids, component_counts = transformed_positions(gltf, index, matrices)
        if len(points) >= 8 and np.all(np.isfinite(points)) and np.count_nonzero(np.ptp(points, axis=0) > 0.05) >= 2:
            records.append((index, str(nodes[index].name or ''), points, material_ids, component_counts))
    body_candidates = [record for record in records if 'stage2_l_cable_strain_bracket' in record[1].lower()]
    svg_candidates = [record for record in records if 'stage3_l_cable_strain_bracket_board_profile' in record[1].lower()]
    if not body_candidates or not svg_candidates:
        return fail('Reachable mesh-bound native STL or SVG import evidence is missing')
    body = max(body_candidates, key=lambda record: len(record[2]))
    source = trimesh.load_mesh(str(ROOT / SPEC['stl']['file']), file_type='stl', force='mesh', process=True)
    source_points = np.asarray(source.vertices, dtype=float)
    source_coverage, candidate_coverage = vertex_overlap_allowing_axes(source_points, body[2])
    if min(source_coverage, candidate_coverage) < 0.65:
        return fail('GLB body is not vertex-equivalent to the real stage2 STL (coverage %.3f/%.3f)' %
                    (source_coverage, candidate_coverage))
    profile = max(svg_candidates, key=lambda record: np.prod(np.sort(np.ptp(record[2], axis=0))[-2:]))
    profile_dims = np.sort(np.ptp(profile[2], axis=0))
    expected_cycle = svg_segment_cycle(ROOT / SPEC['board_profile']['file'])
    if (profile[0] == body[0] or len(expected_cycle) < 6 or
            not planar_l_shape(profile[2], profile[4], expected_cycle)):
        return fail('SVG-derived profile is not distinct, visible, full-scale concave L geometry')
    black_records = []
    for record in records:
        for material_index in record[3]:
            if material_index is None or not (0 <= material_index < len(materials)): continue
            material = materials[material_index]; pbr = getattr(material, 'pbrMetallicRoughness', None)
            factor = getattr(pbr, 'baseColorFactor', None)
            if factor and max(float(value) for value in factor[:3]) < 0.20 and float(factor[3]) > 0.8:
                black_records.append(record); break
    cable_candidates = [record for record in black_records if record[0] not in {body[0], profile[0]}]
    if not cable_candidates:
        return fail('No substantial reachable mesh is actually bound to an opaque black cable material')
    cable = max(cable_candidates, key=lambda record: float(np.linalg.norm(np.ptp(record[2], axis=0))))
    cable_dims = np.sort(np.ptp(cable[2], axis=0))
    if cable_dims[-1] < 35.0 or cable_dims[-2] < 4.0:
        return fail('Black cable geometry is too small to pass through the inlet and tie-slot region')
    if not cable[4] or any(count != 1 for count in cable[4]):
        return fail('Black cable must be a single connected mesh path')
    # Map candidate axes to the STL dimensions, then require actual cable vertices
    # in both the inlet approach and the left-arm tie-slot band.
    stage1 = ezdxf.readfile(str(ROOT / SPEC['dxf']['file']))
    slot_boxes = []
    for entity in stage1.modelspace():
        if str(entity.dxf.layer).upper() == 'TIE_SLOT' and is_closed_polyline(entity):
            points = np.asarray(polyline_points(entity), dtype=float)
            slot_boxes.append((points.min(axis=0), points.max(axis=0)))
    source_dims = np.ptp(source_points, axis=0); traverses = False
    for order in itertools.permutations(range(3)):
        body_aligned = body[2][:, order]
        if np.max(np.abs(np.ptp(body_aligned, axis=0) - source_dims)) > 1.0: continue
        cable_local = cable[2][:, order] - body_aligned.min(axis=0)
        for flips in itertools.product((False, True), repeat=3):
            candidate = cable_local.copy()
            for axis, flip in enumerate(flips):
                if flip: candidate[:, axis] = source_dims[axis] - candidate[:, axis]
            inlet_hits = np.count_nonzero((candidate[:, 0] >= -15) & (candidate[:, 0] <= 8) &
                                          (candidate[:, 1] >= 30) & (candidate[:, 1] <= 82))
            crossings = []
            for lo, hi in slot_boxes:
                near = candidate[(candidate[:, 0] >= lo[0] - 2.0) & (candidate[:, 0] <= hi[0] + 2.0) &
                                 (candidate[:, 1] >= lo[1] - 2.0) & (candidate[:, 1] <= hi[1] + 2.0)]
                crossings.append(len(near) >= 8 and near[:, 2].min() < -0.5 and near[:, 2].max() > 4.5)
            if inlet_hits >= 4 and len(crossings) >= 2 and all(crossings):
                traverses = True; break
        if traverses: break
    if not traverses:
        return fail('Black cable does not geometrically traverse the inlet and tie-slot band')
    return ok('Blender GLB preserves full-scale STL/SVG imports and includes bound black cable geometry')


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
        if not check():
            finish(False)
    finish(True)


if __name__ == '__main__':
    main()
