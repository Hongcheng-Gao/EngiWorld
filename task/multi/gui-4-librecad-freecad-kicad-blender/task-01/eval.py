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

SPEC = {'case_id': 'multi-gui-4-librecad-freecad-kicad-blender-task-01-ubuntu',
 'owner': 'taozhuo',
 'title': 'DIN rail sensor node enclosure with USB and LED windows',
 'domain': 'industrial_iot_enclosure',
 'software_chain': ['librecad', 'freecad', 'kicad', 'blender'],
 'token': 'EW4G01',
 'required_files': ['stage1_sensor_node_enclosure.dxf',
                    'stage2_sensor_node_enclosure.stl',
                    'stage2_sensor_node_enclosure_handoff_outline.dxf',
                    'stage3_sensor_node_enclosure_board.kicad_pcb',
                    'stage3_sensor_node_enclosure_board_profile.svg',
                    'stage4_sensor_node_enclosure.glb'],
 'dxf': {'file': 'stage1_sensor_node_enclosure.dxf',
         'bbox': [92.0, 58.0],
         'bbox_tol': 1.5,
         'circle_tol': 1.0,
         'radius_tol': 0.5,
         'layers': ['OUTLINE', 'PORT', 'HOLE', 'LABEL'],
         'circles': [[8.0, 8.0, 2.2],
                     [84.0, 8.0, 2.2],
                     [8.0, 50.0, 2.2],
                     [84.0, 50.0, 2.2],
                     [72.0, 29.0, 1.6],
                     [80.0, 29.0, 1.6]],
         'texts': ['EW4G01', 'USB-C', 'LED-A', 'LED-B'],
         'min_lines': 4,
         'no_layers': ['GUIDE']},
 'stl': {'file': 'stage2_sensor_node_enclosure.stl',
         'bbox': [92.0, 58.0, 22.0],
         'bbox_tol': 4.0,
         'min_triangles': 100,
         'max_bbox_fill_ratio': 0.8},
 'kicad': {'outline': {'dimensions': [92.0, 58.0],
                       'edge_count': 4,
                       'closed': True,
                       'edge_text_count': 0},
           'components': {'U1': 'MCU Sensor Controller',
                          'J1': 'USB-C Receptacle',
                          'J2': 'Sensor Header',
                          'LED1': 'Status LED A',
                          'LED2': 'Status LED B'},
           'min_pads': 20,
           'require_all_inside_outline': True,
           'tokens': ['EW4G01', 'MCU-U1', 'USB-C-J1', 'LED1', 'LED2', 'SENSOR-J2']},
 'glb': {'file': 'stage4_sensor_node_enclosure.glb',
         'tokens': [],
         'min_nodes': 4,
         'min_materials': 1,
         'nodes': ['stage2_sensor_node_enclosure', 'stage3_sensor_node_enclosure_board_profile.svg'],
         'lens_nodes': ['LED_A_Lens', 'LED_B_Lens'],
         'lens_alpha_max': 0.99,
         'min_meshes': 4,
         'gui_export': True,
         'accepted_import_evidence': {'stage2_stl_object': 'stage2_sensor_node_enclosure',
                                      'stage3_svg_object': 'stage3_sensor_node_enclosure_board_profile.svg'}},
 'diversity_notes': {'geometry': 'DIN rail sensor node enclosure with USB and LED windows',
                     'electronic_focus': 'a sensor-node PCB with USB-C connector, MCU, sensor '
                                         'header, and two LED footprints',
                     'visualization_focus': 'an assembled enclosure with visible USB window and '
                                            'two translucent LED lenses'},
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
 'seed': {'file': 'seed_sensor_node_enclosure.dxf',
          'desktop_path': '/home/user/Desktop/seed_sensor_node_enclosure.dxf'},
 'generated_by': {'workflow': 'real_snapshot_software',
                  'versions': {'librecad': '2.2.0.2',
                               'freecad': '0.21.2',
                               'kicad': '10.0.2',
                               'blender': '4.2.3 LTS'}},
 'handoff': {'file': 'stage2_sensor_node_enclosure_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_sensor_node_enclosure_board_profile.svg',
                   'dimensions': [92.0, 58.0],
                   'closed': True,
                   'painted': True,
                   'equivalent_to': ['stage2_sensor_node_enclosure_handoff_outline.dxf',
                                     'stage3_sensor_node_enclosure_board.kicad_pcb:Edge.Cuts']},
 'intermediate_outputs': [{'stage': 'librecad',
                           'file': 'stage1_sensor_node_enclosure.dxf',
                           'type': 'dxf',
                           'consumed_by': 'freecad',
                           'eval_check': 'check_stage1_dxf'},
                          {'stage': 'freecad',
                           'file': 'stage2_sensor_node_enclosure.stl',
                           'type': 'stl',
                           'consumed_by': 'blender',
                           'eval_check': 'check_stl'},
                          {'stage': 'freecad',
                           'file': 'stage2_sensor_node_enclosure_handoff_outline.dxf',
                           'type': 'dxf',
                           'consumed_by': 'kicad',
                           'eval_check': 'check_handoff_dxf'},
                          {'stage': 'kicad',
                           'file': 'stage3_sensor_node_enclosure_board.kicad_pcb',
                           'type': 'kicad_pcb',
                           'consumed_by': 'blender',
                           'eval_check': 'check_kicad_board_file'},
                          {'stage': 'kicad',
                           'file': 'stage3_sensor_node_enclosure_board_profile.svg',
                           'type': 'svg',
                           'consumed_by': 'blender',
                           'eval_check': 'check_board_profile_svg'}],
 'board_file': {'file': 'stage3_sensor_node_enclosure_board.kicad_pcb'}}
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


def closed_layer_regions(name, layer):
    doc = ezdxf.readfile(str(ROOT / name))
    regions = []
    for entity in doc.modelspace():
        if str(entity.dxf.layer).upper() != layer.upper():
            continue
        if entity.dxftype() == 'LWPOLYLINE' and bool(entity.closed):
            points = [(float(point[0]), float(point[1])) for point in entity.get_points('xy')]
        elif entity.dxftype() == 'POLYLINE' and bool(entity.is_closed):
            points = [(float(vertex.dxf.location.x), float(vertex.dxf.location.y)) for vertex in entity.vertices]
        else:
            continue
        if len(points) >= 3:
            area = 0.5 * abs(sum(
                left[0] * right[1] - right[0] * left[1]
                for left, right in zip(points, points[1:] + points[:1])
            ))
            if area > 1e-6:
                regions.append((points, area))
    return regions


def mesh_contains_points(mesh, points):
    """Dependency-free ray parity test for a small evaluator sample set."""
    triangles = np.asarray(mesh.triangles, dtype=float)
    direction = np.asarray([1.0, 0.371, 0.217], dtype=float)
    direction /= np.linalg.norm(direction)
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    h = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
    determinant = np.einsum('ij,ij->i', edge1, h)
    valid_det = np.abs(determinant) > 1e-10
    inside = []
    for point in np.asarray(points, dtype=float):
        s = point - triangles[:, 0]
        inverse = np.zeros_like(determinant)
        inverse[valid_det] = 1.0 / determinant[valid_det]
        u = inverse * np.einsum('ij,ij->i', s, h)
        q = np.cross(s, edge1)
        v = inverse * np.dot(q, direction)
        distance = inverse * np.einsum('ij,ij->i', edge2, q)
        hits = distance[(valid_det & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1.0 + 1e-9) & (distance > 1e-8))]
        inside.append(len(np.unique(np.round(hits, 8))) % 2 == 1)
    return np.asarray(inside, dtype=bool)


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
    doc = ezdxf.readfile(str(ROOT / name))
    label_texts = [entity_text(entity) for entity in doc.modelspace()
                   if entity.dxftype() in {'TEXT', 'MTEXT'} and
                   str(entity.dxf.layer).upper() == 'LABEL']
    text_blob = norm(' '.join(label_texts))
    for token in SPEC['dxf'].get('texts', []):
        if norm(token) not in text_blob:
            return fail('Stage1 DXF missing text token: ' + token)
    port_regions = closed_layer_regions(name, 'PORT')
    if len(port_regions) != 1 or port_regions[0][1] <= 1.0:
        return fail('Stage1 PORT must contain one nondegenerate closed USB window region')
    return ok('Stage1 LibreCAD DXF passed ezdxf geometry/layer/text checks')


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
    try:
        regions = closed_layer_regions(SPEC['dxf']['file'], 'PORT')
        if len(regions) != 1:
            raise ValueError('port region')
        polygon = np.asarray(regions[0][0], dtype=float)
        port_min, port_max = polygon.min(axis=0), polygon.max(axis=0)
        drawing_dims = np.asarray(SPEC['dxf']['bbox'], dtype=float)
        axis_order = min(
            itertools.permutations(range(3)),
            key=lambda order: sum(abs(dims[order[index]] - expected) for index, expected in enumerate((*drawing_dims, SPEC['stl']['bbox'][2]))),
        )
        x_axis, y_axis, depth_axis = axis_order
        touches = [
            (0, 0, port_min[0]), (0, 1, drawing_dims[0] - port_max[0]),
            (1, 0, port_min[1]), (1, 1, drawing_dims[1] - port_max[1]),
        ]
        planar_axis, side, boundary_distance = min(touches, key=lambda item: abs(item[2]))
        samples = []
        if abs(boundary_distance) <= SPEC['dxf'].get('bbox_tol', 1.5):
            normal_axis = x_axis if planar_axis == 0 else y_axis
            tangent_axis = y_axis if planar_axis == 0 else x_axis
            tangent_coord = float(np.mean(polygon[:, 1 - planar_axis]))
            normal_coord = float(bounds[0, normal_axis] + 1.0 if side == 0 else bounds[1, normal_axis] - 1.0)
            low = float(port_min[1 - planar_axis]); high = float(port_max[1 - planar_axis])
            margin = max(1.5, (high - low) * 0.2)
            adjacent = [max(0.5, low - margin), min(drawing_dims[1 - planar_axis] - 0.5, high + margin)]
            for depth in np.linspace(bounds[0, depth_axis] + dims[depth_axis] * 0.2, bounds[1, depth_axis] - dims[depth_axis] * 0.2, 13):
                port_point = np.mean(bounds, axis=0)
                port_point[[normal_axis, tangent_axis, depth_axis]] = [normal_coord, tangent_coord, depth]
                neighbors = []
                for tangent in adjacent:
                    point = port_point.copy(); point[tangent_axis] = bounds[0, tangent_axis] + tangent
                    neighbors.append(point)
                samples.append((port_point, neighbors))
            flat = [point for port, neighbors in samples for point in [port, *neighbors]]
            occupancy = mesh_contains_points(mesh, flat).reshape(len(samples), 3)
            visible_levels = np.count_nonzero((~occupancy[:, 0]) & occupancy[:, 1] & occupancy[:, 2])
            if visible_levels < 2:
                return fail('STL does not contain a real side-wall opening at the submitted USB PORT region')
        else:
            center = np.mean(polygon, axis=0)
            points = []
            for depth in np.linspace(bounds[0, depth_axis] + 0.5, bounds[1, depth_axis] - 0.5, 9):
                point = np.mean(bounds, axis=0)
                point[[x_axis, y_axis, depth_axis]] = [center[0], center[1], depth]
                points.append(point)
            if np.count_nonzero(mesh_contains_points(mesh, points)) > 1:
                return fail('STL does not carry the submitted USB PORT as a through opening')
    except Exception as exc:
        return fail('Could not cross-check the submitted USB PORT against the STL: ' + str(exc))
    return ok('FreeCAD STL is detailed, watertight, volumetric, and matches the required envelope')


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
    text_blob = norm(' '.join(data['texts']))
    if norm('FREECAD_TO_KICAD') not in text_blob or norm(SPEC['token']) not in text_blob:
        return fail('Stage2 handoff DXF missing FREECAD_TO_KICAD/token label')
    if data['line_like_count'] < 4:
        return fail('Stage2 handoff DXF does not contain a usable outline')
    return ok('Stage2 FreeCAD-to-KiCad handoff DXF matches upstream geometry')


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


def rectangle_from_edges(edges, expected=(92.0, 58.0), tol=0.05):
    if len(edges) != 4:
        return None
    points = [point for edge in edges for point in edge]
    xs = sorted(set(round(point[0], 4) for point in points))
    ys = sorted(set(round(point[1], 4) for point in points))
    if len(xs) != 2 or len(ys) != 2:
        return None
    if not close(xs[1] - xs[0], expected[0], tol) or not close(ys[1] - ys[0], expected[1], tol):
        return None
    expected_edges = {
        tuple(sorted(((xs[0], ys[0]), (xs[0], ys[1])))),
        tuple(sorted(((xs[0], ys[1]), (xs[1], ys[1])))),
        tuple(sorted(((xs[1], ys[1]), (xs[1], ys[0])))),
        tuple(sorted(((xs[1], ys[0]), (xs[0], ys[0])))),
    }
    got = {tuple(sorted(((round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))))) for a, b in edges}
    return (xs[0], ys[0], xs[1], ys[1]) if got == expected_edges else None


def inside_rect(point, rect, margin=0.0):
    return (rect[0] + margin <= point[0] <= rect[2] - margin and
            rect[1] + margin <= point[1] <= rect[3] - margin)


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
    if len(footprint_blocks) != 5 or pad_count < 20:
        return fail('KiCad board needs exactly five real component footprints and sufficient pads (got %d footprints, %d pads)' % (len(footprint_blocks), pad_count))
    edges = kicad_outline(text)
    rect = rectangle_from_edges(edges, tuple(SPEC['dxf']['bbox']), 0.05)
    if rect is None:
        return fail('KiCad Edge.Cuts must be exactly four connected lines forming one closed 92 x 58 rectangle')
    for block in balanced_blocks(text, 'gr_text'):
        if re.search(r'\(layer\s+"Edge\.Cuts"\)', block):
            return fail('KiCad Edge.Cuts must not contain text')
    expected = {
        'U1': 'MCU Sensor Controller',
        'J1': 'USB-C Receptacle',
        'J2': 'Sensor Header',
        'LED1': 'Status LED A',
        'LED2': 'Status LED B',
    }
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
        if not inside_rect(origin, rect, 0.01):
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
        if not all(inside_rect(point, rect, -0.02) for point in footprint_points):
            return fail('KiCad footprint/pad graphics extend outside Edge.Cuts: ' + ref)
    if found != expected:
        return fail('KiCad references/values mismatch: got %s expected %s' % (found, expected))
    blob = norm(text)
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file'], SPEC['token']] + SPEC.get('kicad', {}).get('tokens', []):
        if norm(token) not in blob:
            return fail('KiCad board file missing required token: ' + token)
    token_blocks = [block for block in balanced_blocks(text, 'gr_text') if norm('KICAD_TO_BLENDER') in norm(block)]
    if len(token_blocks) != 1 or not re.search(r'\(layer\s+"F\.SilkS"\)', token_blocks[0]):
        return fail('Required transfer token block must exist once on F.SilkS')
    anchor = first_xy(token_blocks[0], 'at')
    size_match = re.search(r'\(size\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', token_blocks[0])
    text_match = re.search(r'^\(gr_text\s+"((?:[^"\\]|\\.)*)"', token_blocks[0], re.DOTALL)
    if not anchor or not size_match or not text_match:
        return fail('Could not measure the required F.SilkS transfer token block')
    lines = bytes(text_match.group(1), 'utf-8').decode('unicode_escape').splitlines()
    font_x, font_y = map(float, size_match.groups())
    # KiCad stroke-font glyphs occupy less than one font width; this conservative box
    # accounts for line spacing and the left/bottom justification used by the GT.
    token_box = (anchor[0], anchor[1] - len(lines) * font_y * 1.55,
                 anchor[0] + max(map(len, lines)) * font_x * 0.82, anchor[1])
    if not (inside_rect((token_box[0], token_box[1]), rect, 0.01) and inside_rect((token_box[2], token_box[3]), rect, 0.01)):
        return fail('Required F.SilkS token block extends outside Edge.Cuts')
    return ok('Native KiCad board has semantic references/values, pads, footprints, silkscreen, and one closed Edge.Cuts outline fully inside the board')


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
        if entity.dxftype() == 'LINE':
            edges.append(((float(entity.dxf.start.x), float(entity.dxf.start.y)),
                          (float(entity.dxf.end.x), float(entity.dxf.end.y))))
    rect = rectangle_from_edges(edges, tuple(SPEC['dxf']['bbox']), 0.05)
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
    view_box = root.attrib.get('viewBox') or root.attrib.get('viewbox')
    dims = []
    if view_box:
        nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', view_box)]
        if len(nums) >= 4:
            dims = [abs(nums[2]), abs(nums[3])]
    if not dims:
        width = parse_svg_number(root.attrib.get('width'))
        height = parse_svg_number(root.attrib.get('height'))
        if width is not None and height is not None:
            dims = [width, height]
    if not dims:
        return fail('Stage3 SVG profile missing readable width/height or viewBox')
    handoff = read_dxf_summary(SPEC['handoff']['file'])
    if not dims_match(dims, handoff['bbox'], SPEC['dxf'].get('bbox_tol', 1.5)):
        return fail('Stage3 SVG profile size %s does not match stage2 handoff bbox %s' % (dims, handoff['bbox']))
    svg_edges = svg_painted_edges(root)
    svg_rect = rectangle_from_edges(svg_edges, tuple(SPEC['dxf']['bbox']), 0.05)
    if svg_rect is None:
        return fail('Stage3 SVG must contain exactly four actually painted segments forming one closed 92 x 58 outline')
    handoff_edges, handoff_rect, _ = handoff_outline_edges()
    board_text = (ROOT / SPEC['board_file']['file']).read_text(encoding='utf-8', errors='ignore')
    board_edges = kicad_outline(board_text)
    if handoff_rect is None or rectangle_from_edges(board_edges, tuple(SPEC['dxf']['bbox']), 0.05) is None:
        return fail('Cannot establish a closed upstream handoff/Edge.Cuts outline')
    canonical = normalized_edges(handoff_edges)
    if normalized_edges(board_edges) != canonical or normalized_edges(svg_edges) != canonical:
        return fail('FreeCAD handoff, KiCad Edge.Cuts, and plotted SVG are not the same normalized closed outline')
    return ok('Stage3 KiCad SVG is visibly painted and its closed outline equals the FreeCAD handoff and KiCad Edge.Cuts')


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


def canonical_points(points, expected_dims):
    points = np.asarray(points, dtype=float)
    dims = np.ptp(points, axis=0)
    best = None
    for order in itertools.permutations(range(3)):
        error = sum(abs(dims[order[i]] - expected_dims[i]) for i in range(3))
        if best is None or error < best[0]:
            best = (error, order)
    ordered = points[:, best[1]]
    ordered -= ordered.min(axis=0)
    return ordered, best[0]


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
    if set(stl_nodes) & set(svg_nodes):
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
    source_canonical, source_error = canonical_points(source_points, np.asarray(SPEC['stl']['bbox'], dtype=float))
    glb_canonical, glb_error = canonical_points(stl_points, np.asarray(SPEC['stl']['bbox'], dtype=float))
    if source_error > 0.5 or glb_error > 0.8:
        return fail('GLB enclosure world-space dimensions do not match source STL after node transforms')
    source_set = unique_quantized(source_canonical, 0.02)
    best_overlap = 0.0
    expected = np.asarray(SPEC['stl']['bbox'], dtype=float)
    for flips in itertools.product((False, True), repeat=3):
        candidate = glb_canonical.copy()
        for axis, flip in enumerate(flips):
            if flip:
                candidate[:, axis] = expected[axis] - candidate[:, axis]
        candidate_set = unique_quantized(candidate, 0.02)
        if source_set and candidate_set:
            best_overlap = max(best_overlap, len(source_set & candidate_set) / min(len(source_set), len(candidate_set)))
    if best_overlap < 0.75:
        return fail('GLB enclosure vertex shape is not equivalent to the source STL (overlap %.3f)' % best_overlap)

    svg_dims = np.sort(np.ptp(svg_points, axis=0))
    if not (svg_dims[0] <= 0.8 and close(svg_dims[1], 58.0, 0.8) and close(svg_dims[2], 92.0, 0.8)):
        return fail('GLB SVG evidence does not preserve the thin 92 x 58 profile after node transforms: %s' % svg_dims.tolist())
    axes = np.argsort(np.ptp(svg_points, axis=0))[-2:]
    projected = svg_points[:, axes]
    projected -= projected.min(axis=0)
    project_dims = np.ptp(projected, axis=0)
    boundary_tol = 0.7
    if not all(np.count_nonzero(np.abs(projected[:, axis] - bound) <= boundary_tol) >= 4
               for axis in (0, 1) for bound in (0.0, project_dims[axis])):
        return fail('GLB SVG profile vertices do not cover all four sides of the plotted closed outline')

    lens_nodes = {}
    for lens_name in ('LED_A_Lens', 'LED_B_Lens'):
        matches = [index for index, node in enumerate(nodes) if node.name == lens_name]
        if len(matches) != 1 or (scene_roots and matches[0] not in reachable):
            return fail('GLB must contain one reachable mesh node named ' + lens_name)
        points, material_indices = transformed_mesh_positions(gltf, matches[0], world_matrices)
        if len(points) < 50 or np.count_nonzero(np.ptp(points, axis=0) > 0.2) < 3:
            return fail('GLB lens is missing nondegenerate visible 3D geometry: ' + lens_name)
        transparent = False
        for material_index in material_indices:
            if material_index is None or not (0 <= material_index < len(materials)):
                continue
            material = materials[material_index]
            factor = getattr(getattr(material, 'pbrMetallicRoughness', None), 'baseColorFactor', None) or [1, 1, 1, 1]
            if (len(factor) >= 4 and float(factor[3]) < 0.99 and
                    str(getattr(material, 'alphaMode', '') or '').upper() in {'BLEND', 'MASK'}):
                transparent = True
        if not transparent:
            return fail('GLB lens must use an alpha material exported as BLEND or MASK: ' + lens_name)
        lens_nodes[lens_name] = matches[0]
    if nodes[lens_nodes['LED_A_Lens']].mesh == nodes[lens_nodes['LED_B_Lens']].mesh:
        return fail('The two visible LED lenses must be distinct mesh-bound objects')

    # Match the lenses to the two small LED apertures from the submitted stage 1,
    # allowing glTF axis permutation/reflection instead of freezing GT coordinates.
    stage1 = ezdxf.readfile(str(ROOT / SPEC['dxf']['file']))
    led_centers = np.asarray([
        (float(entity.dxf.center.x), float(entity.dxf.center.y))
        for entity in stage1.modelspace()
        if entity.dxftype() == 'CIRCLE' and str(entity.dxf.layer).upper() == 'HOLE' and
        close(float(entity.dxf.radius), 1.6, SPEC['dxf'].get('radius_tol', 0.45))
    ], dtype=float)
    lens_centers = np.asarray([
        np.mean(transformed_mesh_positions(gltf, lens_nodes[name], world_matrices)[0], axis=0)
        for name in ('LED_A_Lens', 'LED_B_Lens')
    ], dtype=float)
    body_bounds = np.asarray([stl_points.min(axis=0), stl_points.max(axis=0)])
    aligned = False
    for planar_axes in itertools.permutations(range(3), 2):
        depth_axis = next(axis for axis in range(3) if axis not in planar_axes)
        planar = lens_centers[:, planar_axes]
        lo = body_bounds[0, list(planar_axes)]
        hi = body_bounds[1, list(planar_axes)]
        planar = planar - lo
        planar_dims = hi - lo
        for flips in itertools.product((False, True), repeat=2):
            candidate = planar.copy()
            for axis, flip in enumerate(flips):
                if flip:
                    candidate[:, axis] = planar_dims[axis] - candidate[:, axis]
            if min(sum(np.linalg.norm(candidate[list(order)] - led_centers, axis=1))
                   for order in itertools.permutations(range(2))) > 3.0:
                continue
            depth = lens_centers[:, depth_axis]
            if (np.all(depth >= body_bounds[0, depth_axis] - 4.0) and
                    np.all(depth <= body_bounds[1, depth_axis] + 4.0)):
                aligned = True
                break
        if aligned:
            break
    if len(led_centers) != 2 or not aligned:
        return fail('The two lens meshes are not aligned over the submitted stage-1 LED apertures and body')

    strings = []
    collect_glb_strings(gltf.to_dict(), strings)
    blob = '\n'.join(strings).upper()
    if 'BLENDER' not in blob:
        return fail('GLB metadata should indicate Blender GUI export/generation')
    return ok('Blender GLB preserves transformed STL/SVG geometry and contains two distinct visible alpha-material LED lenses')


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
