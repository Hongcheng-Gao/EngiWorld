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

SPEC = {'case_id': 'multi-gui-4-librecad-freecad-kicad-blender-task-02-ubuntu',
 'owner': 'taozhuo',
 'title': 'Hexagonal air quality wall badge with vent grille',
 'domain': 'environmental_sensor_badge',
 'software_chain': ['librecad', 'freecad', 'kicad', 'blender'],
 'token': 'EW4G02',
 'required_files': ['stage1_hex_air_quality_badge.dxf',
                    'stage2_hex_air_quality_badge.stl',
                    'stage2_hex_air_quality_badge_handoff_outline.dxf',
                    'stage3_hex_air_quality_badge_board.kicad_pcb',
                    'stage3_hex_air_quality_badge_board_profile.svg',
                    'stage4_hex_air_quality_badge.glb'],
 'dxf': {'file': 'stage1_hex_air_quality_badge.dxf',
         'bbox': [110.0, 96.0],
         'bbox_tol': 1.5,
         'circle_tol': 1.0,
         'radius_tol': 0.5,
         'layers': ['OUTLINE', 'VENT', 'HOLE', 'LABEL'],
         'circles': [[55.0, 82.0, 2.5], [20.0, 22.0, 2.5],
                     [90.0, 22.0, 2.5], [55.0, 48.0, 18.0]],
         'texts': ['EW4G02', 'VOC', 'CO2', 'VENT-7'],
         'outline_vertices': [[0.0, 48.0], [27.5, 0.0], [82.5, 0.0],
                              [110.0, 48.0], [82.5, 96.0], [27.5, 96.0]],
         'min_lines': 13,
         'no_layers': ['GUIDE']},
 'stl': {'file': 'stage2_hex_air_quality_badge.stl',
         'bbox': [110.0, 96.0, 12.0],
         'bbox_tol': 4.0,
         'min_triangles': 100,
         'max_bbox_fill_ratio': 0.8},
 'kicad': {'outline': {'dimensions': [110.0, 96.0],
                       'edge_count': 6,
                       'closed': True,
                       'edge_text_count': 0},
           'components': {'U1': 'VOC Sensor',
                          'U2': 'CO2 Sensor',
                          'J1': 'Battery Input',
                          'J2': 'I2C Header'},
           'min_pads': 22,
           'require_all_inside_outline': True,
           'tokens': ['EW4G02', 'VOC-U1', 'CO2-U2', 'BAT-J1', 'VENT-KEEP', 'I2C-J2']},
 'glb': {'file': 'stage4_hex_air_quality_badge.glb',
         'tokens': [],
         'min_nodes': 7,
         'min_materials': 1,
         'nodes': ['stage2_hex_air_quality_badge', 'stage3_hex_air_quality_badge_board_profile.svg'],
         'scene_nodes': ['Standoff_1', 'Standoff_2', 'Standoff_3', 'VOC_U1', 'CO2_U2'],
         'min_meshes': 7,
         'gui_export': True,
         'accepted_import_evidence': {'stage2_stl_object': 'stage2_hex_air_quality_badge',
                                      'stage3_svg_object': 'stage3_hex_air_quality_badge_board_profile.svg'}},
 'diversity_notes': {'geometry': 'Hexagonal air quality wall badge with vent grille',
                     'electronic_focus': 'a hex PCB with VOC and CO2 sensor locations, battery connector, and a vent keepout',
                     'visualization_focus': 'a wall-mounted badge scene showing the grille, three standoffs, and sensor PCB'},
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
 'seed': {'file': 'seed_hex_air_quality_badge.dxf',
          'desktop_path': '/home/user/Desktop/seed_hex_air_quality_badge.dxf'},
 'generated_by': {'workflow': 'real_snapshot_software',
                  'versions': {'librecad': '2.2.0.2',
                               'freecad': '0.21.2',
                               'kicad': '10.0.2',
                               'blender': '4.2.3 LTS'}},
 'handoff': {'file': 'stage2_hex_air_quality_badge_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_hex_air_quality_badge_board_profile.svg',
                   'dimensions': [110.0, 96.0],
                   'closed': True,
                   'painted': True,
                   'equivalent_to': ['stage2_hex_air_quality_badge_handoff_outline.dxf',
                                     'stage3_hex_air_quality_badge_board.kicad_pcb:Edge.Cuts']},
 'intermediate_outputs': [{'stage': 'librecad',
                           'file': 'stage1_hex_air_quality_badge.dxf',
                           'type': 'dxf',
                           'consumed_by': 'freecad',
                           'eval_check': 'check_stage1_dxf'},
                          {'stage': 'freecad',
                           'file': 'stage2_hex_air_quality_badge.stl',
                           'type': 'stl',
                           'consumed_by': 'blender',
                           'eval_check': 'check_stl'},
                          {'stage': 'freecad',
                           'file': 'stage2_hex_air_quality_badge_handoff_outline.dxf',
                           'type': 'dxf',
                           'consumed_by': 'kicad',
                           'eval_check': 'check_handoff_dxf'},
                          {'stage': 'kicad',
                           'file': 'stage3_hex_air_quality_badge_board.kicad_pcb',
                           'type': 'kicad_pcb',
                           'consumed_by': 'blender',
                           'eval_check': 'check_kicad_board_file'},
                          {'stage': 'kicad',
                           'file': 'stage3_hex_air_quality_badge_board_profile.svg',
                           'type': 'svg',
                           'consumed_by': 'blender',
                           'eval_check': 'check_board_profile_svg'}],
 'board_file': {'file': 'stage3_hex_air_quality_badge_board.kicad_pcb'}}
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


def entity_edges(entity):
    typ = entity.dxftype()
    if typ == 'LINE':
        return [((float(entity.dxf.start.x), float(entity.dxf.start.y)),
                 (float(entity.dxf.end.x), float(entity.dxf.end.y)))]
    if typ == 'LWPOLYLINE':
        points = [(float(point[0]), float(point[1])) for point in entity.get_points('xy')]
        edges = list(zip(points, points[1:]))
        if entity.closed and len(points) > 2:
            edges.append((points[-1], points[0]))
        return edges
    if typ == 'POLYLINE':
        points = [(float(vertex.dxf.location.x), float(vertex.dxf.location.y)) for vertex in entity.vertices]
        edges = list(zip(points, points[1:]))
        if entity.is_closed and len(points) > 2:
            edges.append((points[-1], points[0]))
        return edges
    return []


def canonical_hex_edges(tol=0.02):
    vertices = [tuple(point) for point in SPEC['dxf']['outline_vertices']]
    return normalized_edges(list(zip(vertices, vertices[1:] + vertices[:1])), tol)


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
    if data['line_like_count'] < SPEC['dxf'].get('min_lines', 4):
        return fail('Stage1 DXF has too few line/polyline entities')
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
    text_blob = norm(' '.join(data['texts']))
    for token in SPEC['dxf'].get('texts', []):
        if norm(token) not in text_blob:
            return fail('Stage1 DXF missing text token: ' + token)
    doc = ezdxf.readfile(str(ROOT / name))
    entities = list(doc.modelspace())
    outline_edges = [edge for entity in entities if str(entity.dxf.layer).upper() == 'OUTLINE'
                     for edge in entity_edges(entity)]
    if len(outline_edges) != 6 or normalized_edges(outline_edges) != canonical_hex_edges():
        return fail('Stage1 OUTLINE must be exactly the connected six-edge task hexagon')
    grille = []
    for entity in entities:
        if str(entity.dxf.layer).upper() != 'VENT':
            continue
        for start, end in entity_edges(entity):
            length = math.hypot(end[0] - start[0], end[1] - start[1])
            if length > 1.0 and close(start[1], end[1], 0.02):
                grille.append((start, end))
    if len(grille) != 7:
        return fail('Stage1 VENT must contain seven nondegenerate horizontal grille lines')
    grille_y = [round((start[1] + end[1]) / 2.0, 3) for start, end in grille]
    if len(set(grille_y)) != 7:
        return fail('Stage1 VENT grille bars must be seven independent horizontal lines')
    vent_center = np.asarray([55.0, 48.0])
    for start, end in grille:
        if any(np.linalg.norm(np.asarray(point) - vent_center) > 19.0 for point in (start, end)):
            return fail('A Stage1 VENT grille bar extends outside the radius-18 vent circle')
    for entity in entities:
        if entity.dxftype() == 'CIRCLE':
            center = entity.dxf.center
            expected_layer = 'VENT' if close(entity.dxf.radius, 18.0, 0.1) else 'HOLE'
            if str(entity.dxf.layer).upper() != expected_layer:
                return fail('Stage1 circular feature is on the wrong semantic layer')
        if entity.dxftype() in {'TEXT', 'MTEXT'} and str(entity.dxf.layer).upper() != 'LABEL':
            return fail('Stage1 required labels must be on LABEL')
    return ok('Stage1 LibreCAD DXF has the exact closed hexagon, semantic circles, seven grille bars, and LABEL text')


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
    got = sorted(abs(x) for x in dims)
    exp = sorted(abs(x) for x in SPEC['stl']['bbox'])
    tol = SPEC['stl'].get('bbox_tol', 4.0)
    if any(abs(g - e) > tol for g, e in zip(got, exp)):
        return fail('STL bbox mismatch got %s expected %s' % (dims, SPEC['stl']['bbox']))
    if not bool(getattr(mesh, 'is_watertight', False)):
        return fail('STL enclosure must be a watertight solid')
    volume = abs(float(getattr(mesh, 'volume', 0.0)))
    bbox_volume = float(np.prod(np.maximum(bounds[1] - bounds[0], 0.0)))
    if volume <= 1.0 or bbox_volume <= 1.0:
        return fail('STL enclosure has no positive solid volume')
    fill_ratio = volume / bbox_volume
    if fill_ratio >= SPEC['stl'].get('max_bbox_fill_ratio', 0.8):
        return fail('STL is too close to a featureless full-bounding-box solid (fill ratio %.4f)' % fill_ratio)
    if len(np.unique(np.round(np.asarray(mesh.vertices), 4), axis=0)) < 40:
        return fail('STL has insufficient geometric detail for the enclosure openings/rails')
    orientation = stage1_stl_orientation(mesh)
    if orientation is None:
        return fail('STL does not realize the seven Stage1 vent bars/open gaps and three drilled raised standoffs')
    return ok('FreeCAD STL matches the envelope and realizes the Stage1 grille and drilled raised standoffs')


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
    wire_edges = [edge for entity in entities if str(entity.dxf.layer).upper() == 'WIRE'
                  for edge in entity_edges(entity)]
    if len(wire_edges) != 6 or normalized_edges(wire_edges) != canonical_hex_edges():
        return fail('Stage2 handoff Wire layer must contain the exact closed six-edge task hexagon')
    vent = [entity for entity in entities if entity.dxftype() == 'CIRCLE' and
            close(entity.dxf.center.x, 55.0, 0.05) and close(entity.dxf.center.y, 48.0, 0.05) and
            close(entity.dxf.radius, 18.0, 0.05)]
    if len(vent) != 1:
        return fail('Stage2 handoff must contain one exact vent circle from the FreeCAD model')
    # FreeCAD's modern DXF exporter converts Draft ShapeString labels to geometric
    # outline layers rather than TEXT entities; require two substantial, distinct layers.
    label_layers = {}
    for entity in entities:
        layer = str(entity.dxf.layer)
        if layer.upper().startswith('SHAPESTRING'):
            label_layers[layer] = label_layers.get(layer, 0) + len(entity_edges(entity)) + (1 if entity.dxftype() == 'SPLINE' else 0)
    if len(label_layers) < 2 or sorted(label_layers.values())[-2] < 20:
        return fail('Stage2 handoff is missing two substantial FreeCAD ShapeString label outlines')
    return ok('Stage2 FreeCAD handoff has the exact hexagon, vent circle, and two exported ShapeString labels')


def balanced_blocks(text, head):
    blocks = []
    for match in re.finditer(r'\(' + re.escape(head) + r'(?=\s)', text):
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


def first_xy(block, head='at'):
    match = re.search(r'\(' + re.escape(head) + r'\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', block)
    return (float(match.group(1)), float(match.group(2))) if match else None


def rotate_translate(point, origin, degrees):
    radians = math.radians(float(degrees or 0.0))
    x, y = point
    return (
        origin[0] + x * math.cos(radians) - y * math.sin(radians),
        origin[1] + x * math.sin(radians) + y * math.cos(radians),
    )


def kicad_outline(text):
    edges = []
    for block in balanced_blocks(text, 'gr_line'):
        if not re.search(r'\(layer\s+"Edge\.Cuts"\)', block):
            continue
        start = first_xy(block, 'start')
        end = first_xy(block, 'end')
        if start and end:
            edges.append((start, end))
    return edges


def normalized_edges(edges, tol=0.02):
    points = [point for edge in edges for point in edge]
    if not points:
        return set()
    min_x = min(point[0] for point in points)
    min_y = min(point[1] for point in points)
    quant = lambda point: (round((point[0] - min_x) / tol), round((point[1] - min_y) / tol))
    return {tuple(sorted((quant(start), quant(end)))) for start, end in edges}


def hexagon_from_edges(edges, tol=0.05):
    if len(edges) != 6 or normalized_edges(edges, tol) != canonical_hex_edges(tol):
        return None
    points = [point for edge in edges for point in edge]
    return (min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points))


def inside_rect(point, rect, margin=0.0):
    return (rect[0] + margin <= point[0] <= rect[2] - margin and
            rect[1] + margin <= point[1] <= rect[3] - margin)


def inside_hex(point, margin=0.0):
    x, y = point
    vertices = [tuple(item) for item in SPEC['dxf']['outline_vertices']]
    sign = None
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        cross = (end[0] - start[0]) * (y - start[1]) - (end[1] - start[1]) * (x - start[0])
        if abs(cross) <= margin:
            continue
        current = cross > 0
        if sign is None:
            sign = current
        elif current != sign:
            return False
    return True


def check_kicad_board_file():
    name = SPEC['board_file']['file']
    if not required_file(name, 200):
        return False
    try:
        text = (ROOT / name).read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        return fail('Could not read KiCad board file: ' + str(exc))
    if not re.search(r'\(generator\s+"?pcbnew"?\)', text, flags=re.IGNORECASE):
        return fail('KiCad board is not a native pcbnew-generated board')
    if not text.lstrip().startswith('(kicad_pcb'):
        return fail('KiCad board is not a kicad_pcb S-expression')
    footprint_blocks = balanced_blocks(text, 'footprint')
    pad_count = len(balanced_blocks(text, 'pad'))
    expected = SPEC['kicad']['components']
    if len(footprint_blocks) != len(expected) or pad_count < SPEC['kicad']['min_pads']:
        return fail('KiCad board needs four real task footprints and at least 22 pads (got %d footprints, %d pads)' % (len(footprint_blocks), pad_count))
    edges = kicad_outline(text)
    rect = hexagon_from_edges(edges, 0.05)
    if rect is None:
        return fail('KiCad Edge.Cuts must be exactly six connected lines forming the task hexagon')
    for block in balanced_blocks(text, 'gr_text'):
        if re.search(r'\(layer\s+"Edge\.Cuts"\)', block):
            return fail('KiCad Edge.Cuts must not contain text')
    found = {}
    for block in footprint_blocks:
        ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        value_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
        at_match = re.search(r'^\s*\(at\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)(?:\s+(-?\d+(?:\.\d+)?))?', block, re.MULTILINE)
        if not ref_match or not value_match or not at_match:
            return fail('A KiCad footprint is missing a native reference, value, or placement')
        ref = ref_match.group(1)
        origin = (float(at_match.group(1)), float(at_match.group(2)))
        angle = float(at_match.group(3) or 0.0)
        found[ref] = value_match.group(1)
        if not inside_hex(origin):
            return fail('KiCad footprint origin is outside Edge.Cuts: ' + ref)
        footprint_points = [origin]
        for item_head in ('pad', 'fp_line', 'fp_rect', 'fp_arc', 'fp_circle', 'fp_poly'):
            for item in balanced_blocks(block, item_head):
                for point_head in ('at', 'start', 'end', 'mid', 'center'):
                    point = first_xy(item, point_head)
                    if point is not None:
                        footprint_points.append(rotate_translate(point, origin, angle))
                if item_head == 'pad':
                    pad_at = first_xy(item, 'at') or (0.0, 0.0)
                    size_match = re.search(r'\(size\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', item)
                    if size_match:
                        radius = math.hypot(float(size_match.group(1)), float(size_match.group(2))) / 2.0
                        center = rotate_translate(pad_at, origin, angle)
                        for dx, dy in ((radius, 0), (-radius, 0), (0, radius), (0, -radius)):
                            footprint_points.append((center[0] + dx, center[1] + dy))
        if not all(inside_hex(point) for point in footprint_points):
            return fail('KiCad footprint/pad graphics extend outside Edge.Cuts: ' + ref)
    if found != expected:
        return fail('KiCad references/values mismatch: got %s expected %s' % (found, expected))
    blob = norm(text)
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file'], SPEC['token']] + SPEC.get('kicad', {}).get('tokens', []):
        if norm(token) not in blob:
            return fail('KiCad board file missing required token: ' + token)
    silk_blocks = [block for block in balanced_blocks(text, 'gr_text') if re.search(r'\(layer\s+"F\.SilkS"\)', block)]
    silk_blob = norm(' '.join(silk_blocks))
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file'], SPEC['token']] + SPEC['kicad']['tokens']:
        if norm(token) not in silk_blob:
            return fail('Required token is not carried by native F.SilkS text: ' + token)
    if any(not inside_hex(first_xy(block, 'at')) for block in silk_blocks if first_xy(block, 'at')):
        return fail('A required F.SilkS text anchor is outside the hex board')
    vent_circles = [block for block in balanced_blocks(text, 'gr_circle')
                    if re.search(r'\(layer\s+"Dwgs\.User"\)', block) and first_xy(block, 'center') == (55.0, 48.0)]
    if len(vent_circles) != 1:
        return fail('KiCad board must carry one native vent marker circle on Dwgs.User')
    return ok('Native KiCad board has the exact hex Edge.Cuts, semantic footprints/pads, F.SilkS transfer text, and vent marker')


def parse_svg_number(value):
    match = re.search(r'-?\d+(?:\.\d+)?', str(value or ''))
    return float(match.group(0)) if match else None


def css_map(value):
    result = {}
    for declaration in str(value or '').split(';'):
        if ':' in declaration:
            key, item = declaration.split(':', 1)
            result[key.strip().lower()] = item.strip().lower()
    return result


def opacity(value, default=1.0):
    try:
        return max(0.0, min(1.0, float(str(value).strip().rstrip('%')) / (100.0 if '%' in str(value) else 1.0)))
    except Exception:
        return default


def svg_path_edges(data):
    tokens = re.findall(r'[MmLlHhVvZz]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', data or '')
    edges = []
    cursor = (0.0, 0.0)
    subpath = None
    command = None
    index = 0
    while index < len(tokens):
        if re.fullmatch(r'[MmLlHhVvZz]', tokens[index]):
            command = tokens[index]
            index += 1
            if command in 'Zz' and subpath is not None and cursor != subpath:
                edges.append((cursor, subpath))
                cursor = subpath
            continue
        if command in ('M', 'L', 'm', 'l') and index + 1 < len(tokens):
            point = (float(tokens[index]), float(tokens[index + 1]))
            if command in ('m', 'l'):
                point = (cursor[0] + point[0], cursor[1] + point[1])
            if command in ('M', 'm'):
                cursor = point
                subpath = point
                command = 'L' if command == 'M' else 'l'
            else:
                edges.append((cursor, point))
                cursor = point
            index += 2
        elif command in ('H', 'h'):
            x = float(tokens[index]) + (cursor[0] if command == 'h' else 0.0)
            point = (x, cursor[1])
            edges.append((cursor, point))
            cursor = point
            index += 1
        elif command in ('V', 'v'):
            y = float(tokens[index]) + (cursor[1] if command == 'v' else 0.0)
            point = (cursor[0], y)
            edges.append((cursor, point))
            cursor = point
            index += 1
        else:
            return []
    return edges


def svg_painted_edges(root):
    edges = []
    geometry_tags = {'path', 'line', 'polyline', 'polygon', 'rect'}

    def visit(element, inherited):
        style = dict(inherited)
        style.update(css_map(element.attrib.get('style')))
        for key in ('display', 'visibility', 'fill', 'stroke', 'opacity', 'fill-opacity', 'stroke-opacity'):
            if key in element.attrib:
                style[key] = element.attrib[key].strip().lower()
        hidden = style.get('display') == 'none' or style.get('visibility') in {'hidden', 'collapse'} or opacity(style.get('opacity'), 1.0) <= 0.001
        tag = element.tag.rsplit('}', 1)[-1].lower()
        if tag in geometry_tags and not hidden:
            stroke = style.get('stroke', element.attrib.get('stroke', 'none')).lower()
            fill = style.get('fill', element.attrib.get('fill', 'black')).lower()
            stroke_visible = stroke not in {'none', 'transparent'} and opacity(style.get('stroke-opacity'), 1.0) > 0.001
            fill_visible = fill not in {'none', 'transparent'} and opacity(style.get('fill-opacity'), 1.0) > 0.001
            if stroke_visible or fill_visible:
                if tag == 'path':
                    edges.extend(svg_path_edges(element.attrib.get('d')))
                elif tag == 'line':
                    edges.append(((float(element.attrib.get('x1', 0)), float(element.attrib.get('y1', 0))),
                                  (float(element.attrib.get('x2', 0)), float(element.attrib.get('y2', 0)))))
                elif tag in {'polyline', 'polygon'}:
                    nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', element.attrib.get('points', ''))]
                    points = list(zip(nums[0::2], nums[1::2]))
                    edges.extend(zip(points, points[1:]))
                    if tag == 'polygon' and len(points) > 2:
                        edges.append((points[-1], points[0]))
                elif tag == 'rect':
                    x, y = float(element.attrib.get('x', 0)), float(element.attrib.get('y', 0))
                    w, h = float(element.attrib.get('width', 0)), float(element.attrib.get('height', 0))
                    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                    edges.extend(zip(corners, corners[1:] + corners[:1]))
        for child in list(element):
            visit(child, style)

    visit(root, {})
    return list(edges)


def handoff_outline_edges():
    data = read_dxf_summary(SPEC['handoff']['file'])
    edges = []
    doc = ezdxf.readfile(str(ROOT / SPEC['handoff']['file']))
    for entity in doc.modelspace():
        if str(entity.dxf.layer).upper() == 'WIRE':
            edges.extend(entity_edges(entity))
    rect = hexagon_from_edges(edges, 0.05)
    return edges, rect, data


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
    svg_edges = svg_painted_edges(root)
    if len(svg_edges) != 6 or normalized_edges(svg_edges) != canonical_hex_edges():
        return fail('Stage3 SVG must contain exactly six actually painted segments forming the task hexagon')
    handoff_edges, handoff_rect, _ = handoff_outline_edges()
    board_text = (ROOT / SPEC['board_file']['file']).read_text(encoding='utf-8', errors='ignore')
    board_edges = kicad_outline(board_text)
    if handoff_rect is None or hexagon_from_edges(board_edges, 0.05) is None:
        return fail('Cannot establish a closed upstream handoff/Edge.Cuts outline')
    canonical = normalized_edges(handoff_edges)
    if normalized_edges(board_edges) != canonical or normalized_edges(svg_edges) != canonical:
        return fail('FreeCAD handoff, KiCad Edge.Cuts, and plotted SVG are not the same normalized closed outline')
    return ok('Stage3 KiCad SVG has six visible paths and equals the FreeCAD handoff and native Edge.Cuts hexagon')


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
    accessors = gltf.accessors or []
    views = gltf.bufferViews or []
    if accessor_index is None or not (0 <= accessor_index < len(accessors)):
        return np.empty((0, 3), dtype=float)
    accessor = accessors[accessor_index]
    if accessor.bufferView is None or accessor.componentType != 5126 or accessor.type != 'VEC3':
        return np.empty((0, 3), dtype=float)
    view = views[accessor.bufferView]
    blob = gltf.binary_blob()
    offset = int(view.byteOffset or 0) + int(accessor.byteOffset or 0)
    stride = int(view.byteStride or 12)
    count = int(accessor.count or 0)
    if offset < 0 or count <= 0 or offset + (count - 1) * stride + 12 > len(blob):
        return np.empty((0, 3), dtype=float)
    return np.asarray([struct.unpack_from('<3f', blob, offset + index * stride) for index in range(count)], dtype=float)


def node_matrix(node):
    if node.matrix and len(node.matrix) == 16:
        return np.asarray(node.matrix, dtype=float).reshape((4, 4), order='F')
    translation = np.asarray(node.translation or [0.0, 0.0, 0.0], dtype=float)
    scale = np.asarray(node.scale or [1.0, 1.0, 1.0], dtype=float)
    x, y, z, w = [float(value) for value in (node.rotation or [0.0, 0.0, 0.0, 1.0])]
    rotation = np.asarray([
        [1 - 2*y*y - 2*z*z, 2*x*y - 2*z*w, 2*x*z + 2*y*w],
        [2*x*y + 2*z*w, 1 - 2*x*x - 2*z*z, 2*y*z - 2*x*w],
        [2*x*z - 2*y*w, 2*y*z + 2*x*w, 1 - 2*x*x - 2*y*y],
    ])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation @ np.diag(scale)
    matrix[:3, 3] = translation
    return matrix


def gltf_world_matrices(gltf):
    nodes = gltf.nodes or []
    parents = {}
    for parent_index, node in enumerate(nodes):
        for child in node.children or []:
            parents[child] = parent_index
    result = {}
    for index in range(len(nodes)):
        chain = []
        current = index
        seen = set()
        while current not in seen:
            seen.add(current)
            chain.append(current)
            if current not in parents:
                break
            current = parents[current]
        matrix = np.eye(4)
        for item in reversed(chain):
            matrix = matrix @ node_matrix(nodes[item])
        result[index] = matrix
    return result


def transformed_mesh_positions(gltf, node_index, world_matrices):
    node = gltf.nodes[node_index]
    if node.mesh is None or not (0 <= node.mesh < len(gltf.meshes or [])):
        return np.empty((0, 3), dtype=float), []
    chunks = []
    materials = []
    for primitive in gltf.meshes[node.mesh].primitives or []:
        accessor_index = getattr(primitive.attributes, 'POSITION', None) if primitive.attributes is not None else None
        points = gltf_accessor_positions(gltf, accessor_index)
        if len(points):
            homogeneous = np.column_stack((points, np.ones(len(points))))
            transformed = np.sum(homogeneous[:, None, :] * world_matrices[node_index][None, :, :], axis=2)
            chunks.append(transformed[:, :3])
        materials.append(primitive.material)
    return (np.vstack(chunks) if chunks else np.empty((0, 3), dtype=float)), materials


def canonical_frame(points, expected_dims):
    points = np.asarray(points, dtype=float)
    dims = np.ptp(points, axis=0)
    best = None
    for order in itertools.permutations(range(3)):
        error = sum(abs(dims[order[i]] - expected_dims[i]) for i in range(3))
        if best is None or error < best[0]:
            best = (error, order)
    ordered = points[:, best[1]]
    minimum = ordered.min(axis=0)
    return ordered - minimum, best[0], best[1], minimum


def canonical_points(points, expected_dims):
    ordered, error, _, _ = canonical_frame(points, expected_dims)
    return ordered, error


def stage1_mechanical_features():
    doc = ezdxf.readfile(str(ROOT / SPEC['dxf']['file']))
    grille = []
    holes = []
    for entity in doc.modelspace():
        layer = str(entity.dxf.layer).upper()
        if layer == 'VENT':
            for start, end in entity_edges(entity):
                if math.hypot(end[0] - start[0], end[1] - start[1]) > 1.0 and close(start[1], end[1], 0.02):
                    grille.append((np.asarray(start, dtype=float), np.asarray(end, dtype=float)))
        if layer == 'HOLE' and entity.dxftype() == 'CIRCLE':
            holes.append((float(entity.dxf.center.x), float(entity.dxf.center.y), float(entity.dxf.radius)))
    grille.sort(key=lambda edge: (edge[0][1] + edge[1][1]) / 2.0)
    return grille, holes


def solid_at(triangles, point):
    """Odd/even ray test along +Z without trimesh's optional spatial-index dependency."""
    point = np.asarray(point, dtype=float)
    projected = triangles[:, :, :2]
    ax, ay = projected[:, 0, 0], projected[:, 0, 1]
    bx, by = projected[:, 1, 0], projected[:, 1, 1]
    cx, cy = projected[:, 2, 0], projected[:, 2, 1]
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    usable = np.abs(denominator) > 1e-10
    first = np.zeros(len(triangles), dtype=float)
    second = np.zeros(len(triangles), dtype=float)
    first[usable] = ((by[usable] - cy[usable]) * (point[0] - cx[usable]) +
                     (cx[usable] - bx[usable]) * (point[1] - cy[usable])) / denominator[usable]
    second[usable] = ((cy[usable] - ay[usable]) * (point[0] - cx[usable]) +
                      (ax[usable] - cx[usable]) * (point[1] - cy[usable])) / denominator[usable]
    usable &= first >= -1e-8
    usable &= second >= -1e-8
    usable &= first + second <= 1.0 + 1e-8
    heights = (first * triangles[:, 0, 2] + second * triangles[:, 1, 2] +
               (1.0 - first - second) * triangles[:, 2, 2])
    intersections = np.sort(heights[usable & (heights > point[2] + 1e-7)])
    unique = []
    for value in intersections:
        if not unique or abs(float(value) - unique[-1]) > 1e-5:
            unique.append(float(value))
    return len(unique) % 2 == 1


def stage1_stl_orientation(mesh):
    grille, holes = stage1_mechanical_features()
    if len(grille) != 7 or len(holes) != 3:
        return None
    vertices, error, order, _ = canonical_frame(np.asarray(mesh.vertices, dtype=float),
                                                 np.asarray(SPEC['stl']['bbox'], dtype=float))
    if error > SPEC['stl'].get('bbox_tol', 4.0):
        return None
    faces = np.asarray(mesh.faces, dtype=int)
    triangles = vertices[faces]
    width, height, depth = [float(value) for value in SPEC['stl']['bbox']]

    def mapped(point, flips):
        x, y = float(point[0]), float(point[1])
        return np.asarray([width - x if flips[0] else x,
                           height - y if flips[1] else y], dtype=float)

    for flips in itertools.product((False, True), repeat=2):
        bar_midpoints = [mapped((start + end) / 2.0, flips) for start, end in grille]
        gap_midpoints = [(bar_midpoints[index] + bar_midpoints[index + 1]) / 2.0
                         for index in range(len(bar_midpoints) - 1)]
        if not all(solid_at(triangles, [point[0], point[1], depth / 6.0]) for point in bar_midpoints):
            continue
        if not all(not solid_at(triangles, [point[0], point[1], depth / 6.0]) for point in gap_midpoints):
            continue
        standoffs_ok = True
        for x, y, radius in holes:
            center = mapped((x, y), flips)
            top_depth = depth * 0.9
            if solid_at(triangles, [center[0], center[1], top_depth]):
                standoffs_ok = False
                break
            annulus_found = False
            for delta in np.linspace(0.25, 5.0, 20):
                ring = [center + (radius + delta) * np.asarray([math.cos(angle), math.sin(angle)])
                        for angle in np.linspace(0.0, 2.0 * math.pi, 8, endpoint=False)]
                if sum(solid_at(triangles, [point[0], point[1], top_depth]) for point in ring) >= 6:
                    annulus_found = True
                    break
            if not annulus_found:
                standoffs_ok = False
                break
        if standoffs_ok:
            return {'flips': flips, 'order': order}
    return None


def unique_quantized(points, step=0.02):
    return {tuple(row) for row in np.round(np.asarray(points) / step).astype(int)}


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
    scene_roots = []
    if gltf.scenes:
        scene_index = gltf.scene if gltf.scene is not None else 0
        if 0 <= scene_index < len(gltf.scenes):
            scene_roots = list(gltf.scenes[scene_index].nodes or [])
    reachable = set()
    stack = list(scene_roots)
    while stack:
        node_index = stack.pop()
        if node_index in reachable or node_index < 0 or node_index >= len(nodes):
            continue
        reachable.add(node_index)
        stack.extend(nodes[node_index].children or [])
    if scene_roots and len(reachable) < 2:
        return fail('GLB active scene does not expose both imported artifacts')

    world_matrices = gltf_world_matrices(gltf)

    def descendant_nodes(node_index):
        found = []
        pending = [node_index]
        visited = set()
        while pending:
            current = pending.pop()
            if current in visited or current < 0 or current >= len(nodes):
                continue
            visited.add(current)
            node = nodes[current]
            if node.mesh is not None:
                found.append(current)
            pending.extend(node.children or [])
        return found

    evidence_nodes = {}
    for label, token in SPEC['glb'].get('accepted_import_evidence', {}).items():
        matches = [i for i, node in enumerate(nodes) if norm(token) in norm(node.name)]
        if not matches:
            return fail('GLB missing named import evidence %s: %s' % (label, token))
        if scene_roots and not any(i in reachable for i in matches):
            return fail('GLB evidence node is not reachable from the active scene: ' + token)
        mesh_nodes = []
        for node_index in matches:
            mesh_nodes.extend(descendant_nodes(node_index))
        mesh_nodes = sorted(set(mesh_nodes))
        if not mesh_nodes:
            return fail('GLB evidence node has no bound mesh geometry: ' + token)
        evidence_nodes[label] = mesh_nodes
    stl_nodes = evidence_nodes.get('stage2_stl_object', [])
    svg_nodes = evidence_nodes.get('stage3_svg_object', [])
    stl_meshes = {nodes[index].mesh for index in stl_nodes}
    svg_meshes = {nodes[index].mesh for index in svg_nodes}
    if stl_meshes & svg_meshes:
        return fail('GLB STL and SVG evidence must bind to distinct meshes')
    stl_chunks = [transformed_mesh_positions(gltf, index, world_matrices)[0] for index in stl_nodes]
    svg_chunks = [transformed_mesh_positions(gltf, index, world_matrices)[0] for index in svg_nodes]
    stl_points = np.vstack([chunk for chunk in stl_chunks if len(chunk)]) if any(len(chunk) for chunk in stl_chunks) else np.empty((0, 3))
    svg_points = np.vstack([chunk for chunk in svg_chunks if len(chunk)]) if any(len(chunk) for chunk in svg_chunks) else np.empty((0, 3))
    if len(stl_points) < 100 or len(svg_points) < 20:
        return fail('GLB imported STL/SVG nodes must both bind to substantial vertex geometry')

    try:
        source_mesh = trimesh.load_mesh(str(ROOT / SPEC['stl']['file']), file_type='stl', force='mesh', process=False)
        source_points = np.asarray(source_mesh.vertices, dtype=float)
    except Exception as exc:
        return fail('Could not compare GLB enclosure to source STL: ' + str(exc))
    source_canonical, source_error, _, _ = canonical_frame(source_points, np.asarray(SPEC['stl']['bbox'], dtype=float))
    glb_canonical, glb_error, glb_order, glb_minimum = canonical_frame(stl_points, np.asarray(SPEC['stl']['bbox'], dtype=float))
    if source_error > 0.5 or glb_error > 0.8:
        return fail('GLB enclosure world-space dimensions do not match source STL after node transforms')
    source_set = unique_quantized(source_canonical, 0.02)
    best_overlap = 0.0
    best_body_flips = None
    expected = np.asarray(SPEC['stl']['bbox'], dtype=float)
    for flips in itertools.product((False, True), repeat=3):
        candidate = glb_canonical.copy()
        for axis, flip in enumerate(flips):
            if flip:
                candidate[:, axis] = expected[axis] - candidate[:, axis]
        candidate_set = unique_quantized(candidate, 0.02)
        if source_set and candidate_set:
            overlap = len(source_set & candidate_set) / min(len(source_set), len(candidate_set))
            if overlap > best_overlap:
                best_overlap = overlap
                best_body_flips = flips
    if best_overlap < 0.75:
        return fail('GLB enclosure vertex shape is not equivalent to the source STL (overlap %.3f)' % best_overlap)

    svg_dims = np.sort(np.ptp(svg_points, axis=0))
    if not (svg_dims[0] <= 0.8 and close(svg_dims[1], 96.0, 0.8) and close(svg_dims[2], 110.0, 0.8)):
        return fail('GLB SVG evidence does not preserve a thin full-scale 110 x 96 profile: %s' % svg_dims.tolist())
    thin_axis = int(np.argmin(np.ptp(svg_points, axis=0)))
    axes = [axis for axis in range(3) if axis != thin_axis]
    projected = svg_points[:, axes]
    projected -= projected.min(axis=0)
    if np.ptp(projected, axis=0)[0] < np.ptp(projected, axis=0)[1]:
        projected = projected[:, ::-1]
    expected_vertices = np.asarray(SPEC['dxf']['outline_vertices'], dtype=float)
    corner_tol = 0.8
    for vertex in expected_vertices:
        if np.min(np.linalg.norm(projected - vertex, axis=1)) > corner_tol:
            return fail('GLB SVG profile does not preserve all six task-hex corners')
    for start, end in zip(expected_vertices, np.roll(expected_vertices, -1, axis=0)):
        vector = end - start
        length = float(np.linalg.norm(vector))
        offsets = projected - start
        distances = np.abs(vector[0] * offsets[:, 1] - vector[1] * offsets[:, 0]) / length
        parameters = np.dot(projected - start, vector) / (length * length)
        on_edge = (distances <= 0.45) & (parameters >= -0.01) & (parameters <= 1.01)
        if np.count_nonzero(on_edge) < 8:
            return fail('GLB SVG profile does not contain substantial geometry along every hex edge')

    scene_object_indices = {}
    for object_name in SPEC['glb']['scene_nodes']:
        matches = [index for index, node in enumerate(nodes) if node.name == object_name]
        if len(matches) != 1 or (scene_roots and matches[0] not in reachable):
            return fail('GLB must contain one reachable task scene object: ' + object_name)
        points, material_indices = transformed_mesh_positions(gltf, matches[0], world_matrices)
        if len(points) < 8 or np.count_nonzero(np.ptp(points, axis=0) > 0.2) < 3:
            return fail('GLB task scene object has no nondegenerate 3D mesh: ' + object_name)
        if not any(index is not None and 0 <= index < len(materials) for index in material_indices):
            return fail('GLB task scene object has no exported material: ' + object_name)
        scene_object_indices[object_name] = matches[0]
    if len({nodes[index].mesh for index in scene_object_indices.values()}) != len(scene_object_indices):
        return fail('The standoffs and sensor modules must be distinct mesh-bound objects')
    all_task_meshes = stl_meshes | svg_meshes | {nodes[index].mesh for index in scene_object_indices.values()}
    if len(all_task_meshes) != 7:
        return fail('All seven task scene objects must bind to distinct exported meshes')

    body_bounds = np.asarray([stl_points.min(axis=0), stl_points.max(axis=0)])
    body_dims = np.ptp(stl_points, axis=0)
    depth_axis = int(np.argmin(np.abs(body_dims - 12.0)))
    planar_axes = [axis for axis in range(3) if axis != depth_axis]
    for object_name, node_index in scene_object_indices.items():
        points, _ = transformed_mesh_positions(gltf, node_index, world_matrices)
        center = np.mean(points, axis=0)
        if (any(center[axis] < body_bounds[0, axis] - 2.0 or center[axis] > body_bounds[1, axis] + 2.0
                for axis in planar_axes) or
                center[depth_axis] < body_bounds[0, depth_axis] - 10.0 or
                center[depth_axis] > body_bounds[1, depth_axis] + 10.0):
            return fail('GLB task scene object is not reasonably assembled with the badge body: ' + object_name)

    source_orientation = stage1_stl_orientation(source_mesh)
    if source_orientation is None or best_body_flips is None:
        return fail('Could not establish the Stage1-to-STL-to-GLB mechanical alignment')
    _, holes = stage1_mechanical_features()
    width, height, _ = [float(value) for value in SPEC['stl']['bbox']]
    expected_centers = []
    for x, y, _ in holes:
        expected_centers.append(np.asarray([
            width - x if source_orientation['flips'][0] else x,
            height - y if source_orientation['flips'][1] else y,
        ], dtype=float))
    actual_centers = []
    for object_name in ('Standoff_1', 'Standoff_2', 'Standoff_3'):
        points, _ = transformed_mesh_positions(gltf, scene_object_indices[object_name], world_matrices)
        world_center = (points.min(axis=0) + points.max(axis=0)) / 2.0
        canonical_center = world_center[list(glb_order)] - glb_minimum
        for axis, flip in enumerate(best_body_flips):
            if flip:
                canonical_center[axis] = expected[axis] - canonical_center[axis]
        actual_centers.append(canonical_center[:2])
    best_alignment_error = min(
        max(float(np.linalg.norm(actual_centers[index] - expected_centers[target]))
            for index, target in enumerate(permutation))
        for permutation in itertools.permutations(range(3))
    )
    if best_alignment_error > 2.0:
        return fail('GLB standoffs do not align with the three Stage1 mounting holes (error %.3f mm)' % best_alignment_error)

    strings = []
    collect_glb_strings(gltf.to_dict(), strings)
    blob = '\n'.join(strings).upper()
    if 'BLENDER' not in blob:
        return fail('GLB metadata should indicate Blender GUI export/generation')
    return ok('Blender GLB preserves full-scale artifacts and aligns three standoffs to the Stage1 mounting holes')


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
