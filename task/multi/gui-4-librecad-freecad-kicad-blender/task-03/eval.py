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

SPEC = {'case_id': 'multi-gui-4-librecad-freecad-kicad-blender-task-03-ubuntu',
 'owner': 'taozhuo',
 'title': 'Motor driver carrier plate with heatsink and terminal zones',
 'domain': 'power_electronics_mount',
 'software_chain': ['librecad', 'freecad', 'kicad', 'blender'],
 'token': 'EW4G03',
 'required_files': ['stage1_motor_driver_heatsink_carrier.dxf',
                    'stage2_motor_driver_heatsink_carrier.stl',
                    'stage2_motor_driver_heatsink_carrier_handoff_outline.dxf',
                    'stage3_motor_driver_heatsink_carrier_board.kicad_pcb',
                    'stage3_motor_driver_heatsink_carrier_board_profile.svg',
                    'stage4_motor_driver_heatsink_carrier.glb'],
 'dxf': {'file': 'stage1_motor_driver_heatsink_carrier.dxf',
         'bbox': [125.0, 78.0],
         'bbox_tol': 1.5,
         'circle_tol': 1.0,
         'radius_tol': 0.5,
         'layers': ['OUTLINE', 'SLOT', 'HOLE', 'LABEL'],
         'circles': [[10.0, 10.0, 2.4],
                     [115.0, 10.0, 2.4],
                     [10.0, 68.0, 2.4],
                     [115.0, 68.0, 2.4],
                     [62.5, 39.0, 3.0]],
         'texts': ['EW4G03', 'MOTOR-A', 'MOTOR-B', 'VIN'],
         'min_lines': 4,
         'no_layers': ['GUIDE'],
         'closed_slot_zones': 3,
         'fin_guide_count': 7},
 'stl': {'file': 'stage2_motor_driver_heatsink_carrier.stl',
         'bbox': [125.0, 78.0, 16.0],
         'bbox_tol': 4.0,
         'min_triangles': 1000},
 'kicad': {'tokens': ['EW4G03',
                      'MOSFET-Q1',
                      'MOSFET-Q2',
                      'MOTOR-A-J1',
                      'MOTOR-B-J2',
                      'VIN-J3',
                      'HEATSINK-KEEP'],
           'components': {'Q1': ['Power MOSFET A', 4],
                          'Q2': ['Power MOSFET B', 4],
                          'J1': ['Motor A Output', 3],
                          'J2': ['Motor B Output', 3],
                          'J3': ['VIN Terminal', 2]},
           'heatsink_keepout': [40.0, 22.0, 85.0, 56.0]},
 'glb': {'file': 'stage4_motor_driver_heatsink_carrier.glb',
         'tokens': [],
         'min_nodes': 14,
         'min_materials': 2,
         'min_meshes': 14,
         'gui_export': True,
         'heatsink_fins': 7,
         'blue_terminals': 3,
         'mosfets': 2,
         'visible_profile': True},
 'diversity_notes': {'geometry': 'Motor driver carrier plate with heatsink and terminal zones',
                     'electronic_focus': 'a motor-driver PCB with MOSFETs, two motor outputs, VIN '
                                         'terminal, and heatsink keepout',
                     'visualization_focus': 'a power carrier assembly with visible heatsink fins '
                                            'and blue terminal blocks'},
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
 'seed': {'file': 'seed_motor_driver_heatsink_carrier.dxf',
          'desktop_path': '/home/user/Desktop/seed_motor_driver_heatsink_carrier.dxf'},
 'generated_by': {'method': 'real_snapshot_software',
                  'versions': ['LibreCAD 2.2.0.2', 'FreeCAD 0.21.2', 'KiCad 10.0.2', 'Blender 4.2.3']},
 'handoff': {'file': 'stage2_motor_driver_heatsink_carrier_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_motor_driver_heatsink_carrier_board_profile.svg'},
 'intermediate_outputs': [{'stage': 'librecad',
                           'file': 'stage1_motor_driver_heatsink_carrier.dxf',
                           'type': 'dxf',
                           'consumed_by': 'freecad',
                           'eval_check': 'check_stage1_dxf'},
                          {'stage': 'freecad',
                           'file': 'stage2_motor_driver_heatsink_carrier.stl',
                           'type': 'stl',
                           'consumed_by': 'blender',
                           'eval_check': 'check_stl'},
                          {'stage': 'freecad',
                           'file': 'stage2_motor_driver_heatsink_carrier_handoff_outline.dxf',
                           'type': 'dxf',
                           'consumed_by': 'kicad',
                           'eval_check': 'check_handoff_dxf'},
                          {'stage': 'kicad',
                           'file': 'stage3_motor_driver_heatsink_carrier_board.kicad_pcb',
                           'type': 'kicad_pcb',
                           'consumed_by': 'blender',
                           'eval_check': 'check_kicad_board_file'},
                          {'stage': 'kicad',
                           'file': 'stage3_motor_driver_heatsink_carrier_board_profile.svg',
                           'type': 'svg',
                           'consumed_by': 'blender',
                           'eval_check': 'check_board_profile_svg'}],
 'board_file': {'file': 'stage3_motor_driver_heatsink_carrier_board.kicad_pcb'}}
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
    for layer in SPEC['dxf'].get('no_layers', []):
        if layer.upper() in data['layers']:
            return fail('Stage1 DXF still contains forbidden construction layer: ' + layer)
    doc = ezdxf.readfile(str(ROOT / name))
    entities = list(doc.modelspace())
    outlines = [e for e in entities if str(e.dxf.layer).upper() == 'OUTLINE' and e.dxftype() == 'LWPOLYLINE' and bool(e.closed)]
    slot_polys = [e for e in entities if str(e.dxf.layer).upper() == 'SLOT' and e.dxftype() == 'LWPOLYLINE' and bool(e.closed)]
    slot_lines = [e for e in entities if str(e.dxf.layer).upper() == 'SLOT' and e.dxftype() == 'LINE']
    if (len(outlines) != 1 or len(slot_polys) != SPEC['dxf']['closed_slot_zones'] or
            len(slot_lines) != SPEC['dxf']['fin_guide_count']):
        return fail('Stage1 requires one closed outline, three closed terminal/heatsink zones, and seven fin guides')
    if not dims_match(data['bbox'], SPEC['dxf']['bbox'], SPEC['dxf'].get('bbox_tol', 1.2)):
        return fail('Stage1 DXF bbox mismatch got %s expected %s' % (data['bbox'], SPEC['dxf']['bbox']))
    for req in SPEC['dxf'].get('circles', []):
        found = any(
            close(circle['x'], req[0], SPEC['dxf'].get('circle_tol', 0.9)) and
            close(circle['y'], req[1], SPEC['dxf'].get('circle_tol', 0.9)) and
            close(circle['r'], req[2], SPEC['dxf'].get('radius_tol', 0.45))
            for circle in data['circles']
        )
        if not found:
            return fail('Stage1 DXF missing circle near (%s, %s) radius %s' % (req[0], req[1], req[2]))
    label_texts = [entity_text(entity) for entity in entities
                   if entity.dxftype() in {'TEXT', 'MTEXT'} and
                   str(entity.dxf.layer).upper() == 'LABEL']
    text_blob = norm(' '.join(label_texts))
    for token in SPEC['dxf'].get('texts', []):
        if norm(token) not in text_blob:
            return fail('Stage1 DXF missing text token: ' + token)
    zone_records = []
    for entity in slot_polys:
        points = np.asarray([(float(p[0]), float(p[1])) for p in entity.get_points('xy')], dtype=float)
        area = abs(sum(points[i, 0] * points[(i + 1) % len(points), 1] -
                       points[(i + 1) % len(points), 0] * points[i, 1]
                       for i in range(len(points))) / 2.0)
        if area <= 20.0 or np.any(points < -0.1) or np.any(points > np.asarray(SPEC['dxf']['bbox']) + 0.1):
            return fail('Stage1 SLOT zones must be nondegenerate closed regions inside the carrier')
        zone_records.append((area, points.min(axis=0), points.max(axis=0), points.mean(axis=0)))
    zone_records.sort(key=lambda item: item[0])
    center_x = SPEC['dxf']['bbox'][0] / 2.0
    if (zone_records[-1][0] <= 1.25 * zone_records[-2][0] or
            not (zone_records[-1][1][0] < center_x < zone_records[-1][2][0]) or
            not (zone_records[0][3][0] < center_x < zone_records[1][3][0])):
        return fail('Stage1 SLOT regions must describe two separated terminal zones and one larger central heatsink zone')
    guide_vectors = []
    guide_midpoints = []
    for entity in slot_lines:
        start = np.asarray([float(entity.dxf.start.x), float(entity.dxf.start.y)])
        end = np.asarray([float(entity.dxf.end.x), float(entity.dxf.end.y)])
        vector = end - start
        length = float(np.linalg.norm(vector))
        if length <= 2.0:
            return fail('Stage1 fin guides must be nonzero manufactured-layout lines')
        vector /= length
        if vector[0] < 0 or (close(vector[0], 0.0, 1e-9) and vector[1] < 0):
            vector = -vector
        guide_vectors.append(vector)
        guide_midpoints.append((start + end) / 2.0)
    if any(abs(float(np.dot(guide_vectors[0], vector))) < 0.98 for vector in guide_vectors[1:]):
        return fail('Stage1 seven fin guides must be mutually parallel')
    central_lo, central_hi = zone_records[-1][1], zone_records[-1][2]
    if any(np.any(point < central_lo - 5.0) or np.any(point > central_hi + 5.0) for point in guide_midpoints):
        return fail('Stage1 fin guides must remain associated with the central heatsink zone')
    normal = np.asarray([-guide_vectors[0][1], guide_vectors[0][0]])
    offsets = {round(float(np.dot(point, normal)), 2) for point in guide_midpoints}
    if len(offsets) != SPEC['dxf']['fin_guide_count']:
        return fail('Stage1 fin guides must be seven spatially distinct parallel lines')
    return ok('Stage1 LibreCAD DXF has the exact outline, zones, fins, holes, layers, and labels')


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
    if len(getattr(mesh, 'faces', [])) < SPEC['stl']['min_triangles']:
        return fail('STL has too few triangles')
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = (bounds[1] - bounds[0]).tolist()
    got = sorted(abs(x) for x in dims)
    exp = sorted(abs(x) for x in SPEC['stl']['bbox'])
    tol = SPEC['stl'].get('bbox_tol', 4.0)
    if any(abs(g - e) > tol for g, e in zip(got, exp)):
        return fail('STL bbox mismatch got %s expected %s' % (dims, SPEC['stl']['bbox']))
    if not bool(mesh.is_watertight):
        return fail('FreeCAD STL must be a watertight manufactured carrier')
    bbox_volume = float(np.prod(np.maximum(bounds[1] - bounds[0], 1e-9)))
    fill = abs(float(mesh.volume)) / bbox_volume
    if not (0.15 <= fill <= 0.55):
        return fail('STL volume/bounding-box ratio does not describe an open finned carrier: %.4f' % fill)
    z_levels = np.unique(np.round(np.asarray(mesh.vertices)[:, 2], 2))
    if len(z_levels) < 4:
        return fail('STL lacks the multiple plate/base/fin height levels')
    return ok('FreeCAD STL is watertight, full-size, perforated, and materially finned')


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
    lines = [e for e in entities if e.dxftype() == 'LINE']
    circles = [e for e in entities if e.dxftype() == 'CIRCLE']
    inserts = [e for e in entities if e.dxftype() == 'INSERT']
    if len(lines) != 4 or len(circles) != 5 or len(inserts) != 2:
        return fail('Handoff must contain four outline lines, five interface holes, and two exported ShapeString labels')
    expected_edges = {tuple(sorted((a, b))) for a, b in [((0.0, 0.0), (125.0, 0.0)), ((125.0, 0.0), (125.0, 78.0)), ((125.0, 78.0), (0.0, 78.0)), ((0.0, 78.0), (0.0, 0.0))]}
    got_edges = {tuple(sorted(((round(e.dxf.start.x, 2), round(e.dxf.start.y, 2)), (round(e.dxf.end.x, 2), round(e.dxf.end.y, 2))))) for e in lines}
    if got_edges != expected_edges:
        return fail('FreeCAD handoff outline is not the exact 125 x 78 rectangle')
    if any(len(doc.blocks.get(e.dxf.name)) < 6 for e in inserts):
        return fail('FreeCAD ShapeString label geometry is empty or trivial')
    return ok('FreeCAD handoff has the exact interface outline, holes, and two real ShapeString exports')


def balanced_blocks(text, head):
    blocks = []
    pattern = re.compile(r'\(' + re.escape(head) + r'(?=\s|\")')
    for match in pattern.finditer(text):
        depth = 0
        quoted = False
        escaped = False
        for index in range(match.start(), len(text)):
            char = text[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    blocks.append(text[match.start():index + 1])
                    break
    return blocks


def first_xy(block, head):
    match = re.search(r'\(' + re.escape(head) + r'\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', block)
    return (float(match.group(1)), float(match.group(2))) if match else None


def check_kicad_board_file():
    name = SPEC['board_file']['file']
    if not required_file(name, 200):
        return False
    try:
        text = (ROOT / name).read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        return fail('Could not read KiCad board file: ' + str(exc))
    if not text.lstrip().startswith('(kicad_pcb') or not re.search(r'\(generator\s+"pcbnew"\)', text, re.I):
        return fail('Board is not a native pcbnew kicad_pcb document')
    footprints = balanced_blocks(text, 'footprint')
    pads = balanced_blocks(text, 'pad')
    if len(footprints) != 5 or len(pads) != 16:
        return fail('Board requires exactly five native footprints and sixteen pads')
    found = {}
    for block in footprints:
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        value = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
        if not ref or not value:
            return fail('A native footprint lacks Reference or Value')
        found[ref.group(1)] = (value.group(1), len(balanced_blocks(block, 'pad')))
    expected = {'Q1': ('Power MOSFET A', 4), 'Q2': ('Power MOSFET B', 4), 'J1': ('Motor A Output', 3), 'J2': ('Motor B Output', 3), 'J3': ('VIN Terminal', 2)}
    if found != expected:
        return fail('Native footprint identities/pad counts mismatch: ' + repr(found))
    edges = []
    for block in balanced_blocks(text, 'gr_line'):
        if re.search(r'\(layer\s+"Edge\.Cuts"\)', block):
            edges.append((first_xy(block, 'start'), first_xy(block, 'end')))
    canonical = {tuple(sorted(x)) for x in [((0.0, 0.0), (125.0, 0.0)), ((125.0, 0.0), (125.0, 78.0)), ((125.0, 78.0), (0.0, 78.0)), ((0.0, 78.0), (0.0, 0.0))]}
    if len(edges) != 4 or {tuple(sorted(x)) for x in edges} != canonical:
        return fail('KiCad Edge.Cuts must be exactly the four handoff rectangle edges')
    keepouts = [b for b in balanced_blocks(text, 'gr_rect') if re.search(r'\(layer\s+"Dwgs\.User"\)', b)]
    if len(keepouts) != 1 or first_xy(keepouts[0], 'start') != (40.0, 22.0) or first_xy(keepouts[0], 'end') != (85.0, 56.0):
        return fail('KiCad board lacks the native 40,22 to 85,56 heatsink keepout')
    silk = ' '.join(b for b in balanced_blocks(text, 'gr_text') if re.search(r'\(layer\s+"F\.SilkS"\)', b))
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file']] + SPEC['kicad']['tokens']:
        if norm(token) not in norm(silk):
            return fail('Required token is not native F.SilkS text: ' + token)
    return ok('KiCad board has the exact handoff outline, semantic footprints/pads, keepout, and native silkscreen')


def parse_svg_number(value):
    match = re.search(r'-?\d+(?:\.\d+)?', str(value or ''))
    return float(match.group(0)) if match else None


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
    paths = []
    def css(value):
        return {k.strip().lower(): v.strip().lower() for k, v in (part.split(':', 1) for part in str(value or '').split(';') if ':' in part)}
    def visible_opacity(value, default=1.0):
        try:
            text = str(value).strip()
            return float(text.rstrip('%')) / (100.0 if '%' in text else 1.0)
        except Exception:
            return default
    def visit(element, inherited):
        style = dict(inherited)
        style.update(css(element.attrib.get('style')))
        for key in ('display', 'visibility', 'stroke', 'opacity', 'stroke-opacity'):
            if key in element.attrib:
                style[key] = element.attrib[key].strip().lower()
        hidden = (style.get('display') == 'none' or style.get('visibility') in {'hidden', 'collapse'} or
                  visible_opacity(style.get('opacity'), 1.0) <= 0.001)
        tag = element.tag.rsplit('}', 1)[-1].lower()
        if tag == 'path' and not hidden and style.get('stroke', 'none') not in {'none', 'transparent'} and visible_opacity(style.get('stroke-opacity'), 1.0) > 0.001:
            nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', element.attrib.get('d', ''))]
            if len(nums) >= 4:
                paths.append(((nums[0], nums[1]), (nums[2], nums[3])))
        for child in list(element):
            visit(child, style)
    visit(root, {})
    canonical = {tuple(sorted(x)) for x in [((0.0, 0.0), (125.0, 0.0)), ((125.0, 0.0), (125.0, 78.0)), ((125.0, 78.0), (0.0, 78.0)), ((0.0, 78.0), (0.0, 0.0))]}
    rounded = {tuple(sorted(((round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))))) for a, b in paths}
    if len(paths) != 4 or rounded != canonical:
        return fail('Stage3 SVG needs four actually painted paths forming the exact handoff rectangle')
    return ok('KiCad SVG has four visible paths equal to handoff and Edge.Cuts geometry')


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
    stride = int(view.byteStride or 12)
    blob = gltf.binary_blob()
    if accessor.count <= 0 or offset + (accessor.count - 1) * stride + 12 > len(blob):
        return np.empty((0, 3), dtype=float)
    return np.asarray([struct.unpack_from('<3f', blob, offset + i * stride) for i in range(accessor.count)], dtype=float)


def node_matrix(node):
    if node.matrix and len(node.matrix) == 16:
        return np.asarray(node.matrix, dtype=float).reshape((4, 4), order='F')
    t = np.asarray(node.translation or [0, 0, 0], dtype=float)
    s = np.asarray(node.scale or [1, 1, 1], dtype=float)
    x, y, z, w = [float(v) for v in (node.rotation or [0, 0, 0, 1])]
    r = np.asarray([[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w], [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w], [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]])
    m = np.eye(4); m[:3, :3] = r @ np.diag(s); m[:3, 3] = t
    return m


def gltf_world_matrices(gltf):
    parents = {child: parent for parent, node in enumerate(gltf.nodes or []) for child in (node.children or [])}
    result = {}
    for index in range(len(gltf.nodes or [])):
        chain, current, seen = [], index, set()
        while current not in seen:
            seen.add(current); chain.append(current)
            if current not in parents: break
            current = parents[current]
        m = np.eye(4)
        for item in reversed(chain): m = m @ node_matrix(gltf.nodes[item])
        result[index] = m
    return result


def transformed_positions(gltf, index, matrices):
    node = gltf.nodes[index]
    if node.mesh is None or not (0 <= node.mesh < len(gltf.meshes or [])):
        return np.empty((0, 3), dtype=float)
    chunks = []
    for primitive in gltf.meshes[node.mesh].primitives or []:
        points = gltf_accessor_positions(gltf, getattr(primitive.attributes, 'POSITION', None))
        if len(points):
            homogeneous = np.column_stack((points, np.ones(len(points))))
            transformed = np.sum(homogeneous[:, None, :] * matrices[index][None, :, :], axis=2)
            chunks.append(transformed[:, :3])
    return np.vstack(chunks) if chunks else np.empty((0, 3), dtype=float)


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
    if len(nodes) < SPEC['glb']['min_nodes']:
        return fail('GLB has too few reachable assembly objects')
    if len(meshes) < SPEC['glb']['min_meshes']:
        return fail('GLB has too few meshes for the requested assembly')
    if len(materials) < SPEC['glb']['min_materials']:
        return fail('GLB has too few materials')
    strings = []
    collect_glb_strings(gltf.to_dict(), strings)
    blob = '\n'.join(strings).upper()
    if 'BLENDER' not in blob:
        return fail('GLB metadata should indicate Blender GUI export/generation')
    roots = (gltf.scenes[gltf.scene or 0].nodes or []) if gltf.scenes else []
    reachable = set()
    stack = list(roots)
    while stack:
        index = stack.pop()
        if index in reachable or not (0 <= index < len(nodes)):
            continue
        reachable.add(index)
        stack.extend(nodes[index].children or [])
    matrices = gltf_world_matrices(gltf)
    records = []
    for index in reachable:
        if nodes[index].mesh is None or not (0 <= nodes[index].mesh < len(meshes)):
            continue
        points = transformed_positions(gltf, index, matrices)
        if len(points) < 8 or not np.all(np.isfinite(points)):
            continue
        dims = np.sort(np.ptp(points, axis=0))
        if np.count_nonzero(dims > 0.2) < 2:
            continue
        material_ids = {primitive.material for primitive in meshes[nodes[index].mesh].primitives
                        if primitive.material is not None}
        records.append({'index': index, 'mesh': nodes[index].mesh, 'points': points,
                        'dims': dims, 'center': np.mean(points, axis=0), 'materials': material_ids})

    source = trimesh.load_mesh(str(ROOT / SPEC['stl']['file']), file_type='stl', force='mesh', process=True)
    source_points = np.asarray(source.vertices, dtype=float)
    source_dims = np.ptp(source_points, axis=0)
    body_candidates = [record for record in records if len(record['points']) >= 500 and
                       dims_match(record['dims'], sorted(source_dims), 0.8)]
    best_body = None
    best_overlap = 0.0
    source_zero = source_points - source_points.min(axis=0)
    source_set = {tuple(row) for row in np.round(source_zero / 0.05).astype(int)}
    for record in body_candidates:
        for order in itertools.permutations(range(3)):
            candidate = record['points'][:, order].copy()
            if np.max(np.abs(np.ptp(candidate, axis=0) - source_dims)) > 0.8:
                continue
            candidate -= candidate.min(axis=0)
            for flips in itertools.product((False, True), repeat=3):
                transformed = candidate.copy()
                for axis, flip in enumerate(flips):
                    if flip:
                        transformed[:, axis] = source_dims[axis] - transformed[:, axis]
                candidate_set = {tuple(row) for row in np.round(transformed / 0.05).astype(int)}
                overlap = len(source_set & candidate_set) / max(1, min(len(source_set), len(candidate_set)))
                if overlap > best_overlap:
                    best_overlap, best_body = overlap, record
    if best_body is None or best_overlap < 0.70:
        return fail('GLB lacks one reachable body vertex-equivalent to the source STL')

    single_profiles = [record for record in records if record is not best_body and
                       record['dims'][0] <= 1.2 and close(record['dims'][1], 78.0, 1.2) and
                       close(record['dims'][2], 125.0, 1.2)]
    profile_edges = [record for record in records if record is not best_body and
                     record['dims'][0] <= 1.2 and record['dims'][1] <= 1.2 and
                     (close(record['dims'][2], 125.0, 1.2) or close(record['dims'][2], 78.0, 1.2))]
    if single_profiles:
        profile_records = [single_profiles[0]]
    elif (sum(close(record['dims'][2], 125.0, 1.2) for record in profile_edges) >= 2 and
          sum(close(record['dims'][2], 78.0, 1.2) for record in profile_edges) >= 2 and
          len({record['mesh'] for record in profile_edges}) >= 4):
        profile_records = profile_edges
    else:
        return fail('GLB lacks a full-scale thin 125 x 78 SVG-derived profile')

    blue_materials = set()
    dark_materials = set()
    for material_index, material in enumerate(materials):
        factor = getattr(getattr(material, 'pbrMetallicRoughness', None), 'baseColorFactor', None)
        if factor and factor[2] >= 0.55 and factor[2] >= factor[0] * 2 and factor[2] >= factor[1] * 2:
            blue_materials.add(material_index)
        if factor and max(float(value) for value in factor[:3]) < 0.12:
            dark_materials.add(material_index)

    terminals = [record for record in records if record['materials'] & blue_materials and
                 record['dims'][0] >= 5.0 and record['dims'][2] >= 8.0]
    mosfets = [record for record in records if record['materials'] & dark_materials and
               record['dims'][0] >= 3.0 and 7.0 <= record['dims'][2] <= 25.0]
    fins = [record for record in records if record is not best_body and
            record['dims'][0] <= 3.0 and 5.0 <= record['dims'][1] <= 15.0 and
            18.0 <= record['dims'][2] <= 45.0]
    if len(terminals) != 3 or len({record['mesh'] for record in terminals}) != 3:
        return fail('GLB requires three distinct substantial blue terminal-block meshes')
    if len(mosfets) != 2 or len({record['mesh'] for record in mosfets}) != 2:
        return fail('GLB requires two distinct substantial dark MOSFET-module meshes')
    if len(fins) != 7 or len({record['mesh'] for record in fins}) != 7:
        return fail('GLB requires seven distinct narrow heatsink-fin meshes')

    body_bounds = np.asarray([best_body['points'].min(axis=0), best_body['points'].max(axis=0)])
    depth_axis = int(np.argmin(np.ptp(best_body['points'], axis=0)))
    planar_axes = [axis for axis in range(3) if axis != depth_axis]
    for record in terminals + mosfets + fins:
        center = record['center']
        if (any(center[axis] < body_bounds[0, axis] - 3.0 or center[axis] > body_bounds[1, axis] + 3.0
                for axis in planar_axes) or
                center[depth_axis] < body_bounds[0, depth_axis] - 12.0 or
                center[depth_axis] > body_bounds[1, depth_axis] + 12.0):
            return fail('A fin, MOSFET, or terminal mesh is not spatially assembled with the carrier')
    profile_points = np.vstack([record['points'] for record in profile_records])
    profile_center = np.mean(profile_points, axis=0)
    if (any(profile_center[axis] < body_bounds[0, axis] - 3.0 or
            profile_center[axis] > body_bounds[1, axis] + 3.0 for axis in planar_axes) or
            profile_center[depth_axis] < body_bounds[0, depth_axis] - 5.0 or
            profile_center[depth_axis] > body_bounds[1, depth_axis] + 5.0):
        return fail('The SVG profile is not spatially assembled with the carrier')
    return ok('Blender GLB has reachable real STL/profile meshes, seven fins, two MOSFETs, and three blue terminals')


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
