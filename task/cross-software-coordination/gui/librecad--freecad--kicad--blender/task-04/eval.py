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

SPEC = {'case_id': 'multi-gui-4-librecad-freecad-kicad-blender-task-04-ubuntu',
 'owner': 'taozhuo',
 'title': 'Round instrument gauge bezel with OLED and encoder board',
 'domain': 'instrument_display_bezel',
 'software_chain': ['librecad', 'freecad', 'kicad', 'blender'],
 'token': 'EW4G04',
 'required_files': ['stage1_round_gauge_bezel.dxf',
                    'stage2_round_gauge_bezel.stl',
                    'stage2_round_gauge_bezel_handoff_outline.dxf',
                    'stage3_round_gauge_bezel_board.kicad_pcb',
                    'stage3_round_gauge_bezel_board_profile.svg',
                    'stage4_round_gauge_bezel.glb'],
 'dxf': {'file': 'stage1_round_gauge_bezel.dxf',
         'bbox': [118.0, 118.0],
         'bbox_tol': 1.5,
         'circle_tol': 1.0,
         'radius_tol': 0.5,
         'layers': ['OUTLINE', 'WINDOW', 'HOLE', 'LABEL'],
         'circles': [[59.0, 59.0, 59.0],
                     [59.0, 59.0, 34.0],
                     [59.0, 12.0, 2.1],
                     [106.0, 59.0, 2.1],
                     [59.0, 106.0, 2.1],
                     [12.0, 59.0, 2.1]],
         'texts': ['EW4G04', 'OLED', 'ENCODER', 'BEZEL'],
         'no_layers': ['GUIDE']},
 'stl': {'file': 'stage2_round_gauge_bezel.stl',
         'bbox': [118.0, 118.0, 18.0],
         'bbox_tol': 4.0,
         'min_triangles': 3000,
         'fill_ratio': [0.08, 0.28],
         'min_height_levels': 4},
 'kicad': {'tokens': ['EW4G04', 'OLED-DS1', 'ENCODER-SW1', 'BUZZER-BZ1', 'BTN-MODE', 'I2C-J1'],
           'components': {'DS1': ['OLED Display', 4],
                          'SW1': ['Rotary Encoder', 5],
                          'BZ1': ['Gauge Buzzer', 2],
                          'SW2': ['Mode Button', 2],
                          'J1': ['I2C Header', 4]},
           'min_pads': 17},
 'glb': {'file': 'stage4_round_gauge_bezel.glb',
         'tokens': [],
         'min_nodes': 4,
         'min_materials': 1,
         'min_meshes': 4,
         'gui_export': True},
 'diversity_notes': {'geometry': 'Round instrument gauge bezel with OLED and encoder board',
                     'electronic_focus': 'a circular gauge PCB carrying an OLED display, encoder, '
                                         'buzzer, mode button, and I2C header',
                     'visualization_focus': 'an instrument front view with smoky display lens and '
                                            'a raised encoder knob'},
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
 'seed': {'file': 'seed_round_gauge_bezel.dxf',
          'desktop_path': '/home/user/Desktop/seed_round_gauge_bezel.dxf'},
 'generated_by': {'method': 'real_snapshot_software',
                  'versions': ['LibreCAD 2.2.0.2', 'FreeCAD 0.21.2', 'KiCad 10.0.2', 'Blender 4.2.3']},
 'handoff': {'file': 'stage2_round_gauge_bezel_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_round_gauge_bezel_board_profile.svg'},
 'intermediate_outputs': [{'stage': 'librecad',
                           'file': 'stage1_round_gauge_bezel.dxf',
                           'type': 'dxf',
                           'consumed_by': 'freecad',
                           'eval_check': 'check_stage1_dxf'},
                          {'stage': 'freecad',
                           'file': 'stage2_round_gauge_bezel.stl',
                           'type': 'stl',
                           'consumed_by': 'blender',
                           'eval_check': 'check_stl'},
                          {'stage': 'freecad',
                           'file': 'stage2_round_gauge_bezel_handoff_outline.dxf',
                           'type': 'dxf',
                           'consumed_by': 'kicad',
                           'eval_check': 'check_handoff_dxf'},
                          {'stage': 'kicad',
                           'file': 'stage3_round_gauge_bezel_board.kicad_pcb',
                           'type': 'kicad_pcb',
                           'consumed_by': 'blender',
                           'eval_check': 'check_kicad_board_file'},
                          {'stage': 'kicad',
                           'file': 'stage3_round_gauge_bezel_board_profile.svg',
                           'type': 'svg',
                           'consumed_by': 'blender',
                           'eval_check': 'check_board_profile_svg'}],
 'board_file': {'file': 'stage3_round_gauge_bezel_board.kicad_pcb'}}
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
    if not dims_match(data['bbox'], SPEC['dxf']['bbox'], SPEC['dxf'].get('bbox_tol', 1.2)):
        return fail('Stage1 DXF bbox mismatch got %s expected %s' % (data['bbox'], SPEC['dxf']['bbox']))
    if len(data['circles']) != len(SPEC['dxf']['circles']):
        return fail('Stage1 requires exactly six task circles')
    for index, req in enumerate(SPEC['dxf'].get('circles', [])):
        expected_layer = ('OUTLINE' if index == 0 else 'WINDOW' if index == 1 else 'HOLE')
        found = [circle for circle in data['circles'] if
            close(circle['x'], req[0], SPEC['dxf'].get('circle_tol', 0.9)) and
            close(circle['y'], req[1], SPEC['dxf'].get('circle_tol', 0.9)) and
            close(circle['r'], req[2], SPEC['dxf'].get('radius_tol', 0.45)) and
            circle['layer'] == expected_layer]
        if len(found) != 1:
            return fail('Stage1 DXF missing circle near (%s, %s) radius %s' % (req[0], req[1], req[2]))
    doc = ezdxf.readfile(str(ROOT / name))
    label_texts = [entity_text(entity) for entity in doc.modelspace()
                   if entity.dxftype() in {'TEXT', 'MTEXT'} and str(entity.dxf.layer).upper() == 'LABEL']
    text_blob = norm(' '.join(label_texts))
    for token in SPEC['dxf'].get('texts', []):
        if norm(token) not in text_blob:
            return fail('Stage1 DXF missing text token: ' + token)
    return ok('Stage1 LibreCAD DXF has the exact circular outline, window, four holes, and labels')


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
    if not mesh.is_watertight:
        return fail('STL must be a watertight manufactured bezel')
    fill = abs(float(mesh.volume)) / max(float(np.prod(np.asarray(dims))), 1e-9)
    if not (SPEC['stl']['fill_ratio'][0] <= fill <= SPEC['stl']['fill_ratio'][1]):
        return fail('STL fill ratio does not describe an open circular bezel: %.4f' % fill)
    points = np.asarray(mesh.vertices, dtype=float)
    height_axis = int(np.argmin(np.abs(np.ptp(points, axis=0) - 18.0)))
    levels = np.unique(np.round(points[:, height_axis], 1))
    if len(levels) < SPEC['stl']['min_height_levels']:
        return fail('STL lacks distinct base, bezel/rim, and raised-control height levels')
    top = points[points[:, height_axis] >= points[:, height_axis].max() - 0.25]
    planar_axes = [axis for axis in range(3) if axis != height_axis]
    if (len(top) < 12 or max(np.ptp(top[:, planar_axes], axis=0)) > 35.0 or
            min(np.ptp(top[:, planar_axes], axis=0)) < 5.0):
        return fail('STL lacks a localized substantial raised encoder-control region')
    centered_radius = np.hypot(points[:, 0] - 59.0, points[:, 1] - 59.0)
    if np.count_nonzero(np.abs(centered_radius - 59.0) < 0.25) < 100 or np.count_nonzero(np.abs(centered_radius - 34.0) < 0.25) < 100:
        return fail('STL lacks substantial outer bezel and central window circumference geometry')
    return ok('FreeCAD STL is a full-size watertight open circular bezel with raised encoder geometry')


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
    circles = [entity for entity in entities if entity.dxftype() == 'CIRCLE']
    inserts = [entity for entity in entities if entity.dxftype() == 'INSERT']
    if len(circles) != 5 or len(inserts) != 2:
        return fail('Handoff requires one circular board outline, four holes, and two ShapeString labels')
    required = SPEC['dxf']['circles'][:1] + SPEC['dxf']['circles'][2:]
    for req in required:
        if not any(close(c.dxf.center.x, req[0], 0.1) and close(c.dxf.center.y, req[1], 0.1) and close(c.dxf.radius, req[2], 0.1) for c in circles):
            return fail('Handoff is missing an exact circular interface feature: ' + repr(req))
    if any(len(doc.blocks.get(entity.dxf.name)) < 6 for entity in inserts):
        return fail('Handoff ShapeString geometry is empty or trivial')
    return ok('FreeCAD handoff has the exact circular outline, four holes, and two real ShapeString exports')


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
    if len(footprints) != len(SPEC['kicad']['components']) or len(pads) < SPEC['kicad']['min_pads']:
        return fail('Board lacks the five native gauge footprints or required pads')
    found = {}
    for block in footprints:
        ref = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        value = re.search(r'\(property\s+"Value"\s+"([^"]+)"', block)
        at = first_xy(block, 'at')
        if not ref or not value or at is None:
            return fail('A native footprint lacks Reference, Value, or placement')
        if math.hypot(at[0] - 59.0, at[1] - 59.0) > 55.0:
            return fail('A gauge footprint is outside the circular board: ' + ref.group(1))
        found[ref.group(1)] = [value.group(1), len(balanced_blocks(block, 'pad'))]
    if found != SPEC['kicad']['components']:
        return fail('Gauge footprint identities/pad counts mismatch: ' + repr(found))
    circles = [block for block in balanced_blocks(text, 'gr_circle') if re.search(r'\(layer\s+"Edge\.Cuts"\)', block)]
    if len(circles) != 1 or first_xy(circles[0], 'center') != (59.0, 59.0) or first_xy(circles[0], 'end') != (118.0, 59.0):
        return fail('KiCad Edge.Cuts must be the exact FreeCAD r59 circle')
    silk = ' '.join(block for block in balanced_blocks(text, 'gr_text') if re.search(r'\(layer\s+"F\.SilkS"\)', block))
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file']] + SPEC['kicad']['tokens']:
        if norm(token) not in norm(silk):
            return fail('Required transfer token is not native F.SilkS text: ' + token)
    return ok('KiCad board has the exact circular Edge.Cuts, five real gauge footprints, pads, and silkscreen')


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
    circles = []
    def css(value):
        return {k.strip().lower(): v.strip().lower() for k, v in (part.split(':', 1) for part in str(value or '').split(';') if ':' in part)}
    def opacity(value, default=1.0):
        try:
            item = str(value).strip()
            return float(item.rstrip('%')) / (100.0 if '%' in item else 1.0)
        except Exception:
            return default
    def visit(element, inherited):
        style = dict(inherited); style.update(css(element.attrib.get('style')))
        for key in ('display', 'visibility', 'stroke', 'opacity', 'stroke-opacity'):
            if key in element.attrib: style[key] = element.attrib[key].strip().lower()
        hidden = style.get('display') == 'none' or style.get('visibility') in {'hidden', 'collapse'} or opacity(style.get('opacity'), 1.0) <= 0.001
        tag = element.tag.rsplit('}', 1)[-1].lower()
        if tag == 'circle' and not hidden and style.get('stroke', 'none') not in {'none', 'transparent'} and opacity(style.get('stroke-opacity'), 1.0) > 0.001:
            circles.append((float(element.attrib.get('cx', 0)), float(element.attrib.get('cy', 0)), float(element.attrib.get('r', 0))))
        for child in list(element): visit(child, style)
    visit(root, {})
    if len(circles) != 1 or not close(circles[0][0], 59, 0.1) or not close(circles[0][1], 59, 0.1) or not close(circles[0][2], 59, 0.1):
        return fail('Stage3 SVG needs one actually painted r59 circular profile')
    return ok('KiCad SVG has one visible r59 circle equal to the FreeCAD handoff and Edge.Cuts')


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
    return np.asarray([struct.unpack_from('<3f', blob, offset + index * stride) for index in range(accessor.count)], dtype=float)


def node_matrix(node):
    if node.matrix and len(node.matrix) == 16:
        return np.asarray(node.matrix, dtype=float).reshape((4, 4), order='F')
    translation = np.asarray(node.translation or [0, 0, 0], dtype=float)
    scale = np.asarray(node.scale or [1, 1, 1], dtype=float)
    x, y, z, w = [float(value) for value in (node.rotation or [0, 0, 0, 1])]
    rotation = np.asarray([[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w],
                           [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w],
                           [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation @ np.diag(scale)
    matrix[:3, 3] = translation
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
        return np.empty((0, 3), dtype=float), []
    chunks, material_ids = [], []
    for primitive in gltf.meshes[node.mesh].primitives or []:
        points = gltf_accessor_positions(gltf, getattr(primitive.attributes, 'POSITION', None))
        if len(points):
            homogeneous = np.column_stack((points, np.ones(len(points))))
            transformed = np.sum(homogeneous[:, None, :] * matrices[node_index][None, :, :], axis=2)
            chunks.append(transformed[:, :3])
        material_ids.append(primitive.material)
    return (np.vstack(chunks) if chunks else np.empty((0, 3), dtype=float)), material_ids


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
        if nodes[index].mesh is None or not (0 <= nodes[index].mesh < len(meshes)):
            continue
        points, material_ids = transformed_positions(gltf, index, matrices)
        if len(points) < 20 or not np.all(np.isfinite(points)):
            continue
        records.append({'index': index, 'mesh': nodes[index].mesh, 'points': points,
                        'dims': np.sort(np.ptp(points, axis=0)), 'center': np.mean(points, axis=0),
                        'materials': {item for item in material_ids if item is not None}})
    # Verify the Blender body against the actual stage2 STL, allowing axis order
    # and reflection differences introduced by the glTF coordinate convention.
    source = trimesh.load_mesh(str(ROOT / SPEC['stl']['file']), file_type='stl', force='mesh', process=True)
    source_points = np.asarray(source.vertices, dtype=float)
    source_dims = np.ptp(source_points, axis=0)
    best_overlap = 0.0
    body = None
    source_zero = source_points - source_points.min(axis=0)
    source_set = {tuple(row) for row in np.round(source_zero / 0.05).astype(int)}
    for record in records:
        if len(record['points']) < 500 or not dims_match(record['dims'], sorted(source_dims), 0.8):
            continue
        for order in itertools.permutations(range(3)):
            candidate = record['points'][:, order].copy()
            if np.max(np.abs(np.ptp(candidate, axis=0) - source_dims)) > 0.8: continue
            candidate -= candidate.min(axis=0)
            for flips in itertools.product((False, True), repeat=3):
                transformed = candidate.copy()
                for axis, flip in enumerate(flips):
                    if flip: transformed[:, axis] = source_dims[axis] - transformed[:, axis]
                candidate_set = {tuple(row) for row in np.round(transformed / 0.05).astype(int)}
                overlap = len(source_set & candidate_set) / max(1, min(len(source_set), len(candidate_set)))
                if overlap > best_overlap:
                    best_overlap, body = overlap, record
    if body is None or best_overlap < 0.70:
        return fail('GLB lacks a reachable bezel vertex-equivalent to source STL')

    profile_candidates = [record for record in records if record is not body and
                          record['dims'][0] <= 1.5 and close(record['dims'][1], 118.0, 2.0) and
                          close(record['dims'][2], 118.0, 2.0)]
    if not profile_candidates:
        return fail('GLB lacks a distinct full-scale thin circular SVG-derived profile')
    profile = min(profile_candidates, key=lambda item: item['dims'][0])
    profile_points = profile['points']
    profile_dims = np.sort(np.ptp(profile_points, axis=0))
    if not (profile_dims[0] <= 1.2 and close(profile_dims[1], 118.0, 1.5) and close(profile_dims[2], 118.0, 1.5)):
        return fail('SVG-derived circular profile is missing or remains at Blender 1/1000 scale: ' + repr(profile_dims.tolist()))
    axes = np.argsort(np.ptp(profile_points, axis=0))[-2:]
    projected = profile_points[:, axes]
    center = (projected.min(axis=0) + projected.max(axis=0)) / 2.0
    radial = np.linalg.norm(projected - center, axis=1)
    if np.percentile(np.abs(radial - 59.0), 90) > 1.2:
        return fail('SVG-derived visible profile is not circular radius 59')
    smoky_materials = set()
    for index, material in enumerate(materials):
        pbr = getattr(material, 'pbrMetallicRoughness', None)
        factor = getattr(pbr, 'baseColorFactor', None)
        if (factor and max(factor[:3]) < 0.15 and float(factor[3]) < 0.85 and
                str(material.alphaMode).upper() in {'BLEND', 'MASK'}):
            smoky_materials.add(index)
    lens_candidates = [record for record in records if record is not body and record is not profile and
                       record['materials'] & smoky_materials and record['dims'][0] <= 3.0 and
                       35.0 <= record['dims'][1] <= 75.0 and 35.0 <= record['dims'][2] <= 75.0]
    knob_candidates = [record for record in records if record is not body and record is not profile and
                       5.0 <= record['dims'][0] <= 18.0 and 10.0 <= record['dims'][1] <= 30.0 and
                       10.0 <= record['dims'][2] <= 30.0 and
                       abs(record['dims'][1] - record['dims'][2]) <= 3.0]
    if len(lens_candidates) != 1:
        return fail('GLB requires one substantial dark translucent lens geometry')
    if not knob_candidates:
        return fail('GLB requires a substantial raised approximately cylindrical encoder knob')
    lens = lens_candidates[0]
    knob = min(knob_candidates, key=lambda item: abs(item['dims'][1] - item['dims'][2]))
    if len({body['mesh'], profile['mesh'], lens['mesh'], knob['mesh']}) != 4:
        return fail('Body, profile, lens, and knob must be distinct mesh objects')

    body_bounds = np.asarray([body['points'].min(axis=0), body['points'].max(axis=0)])
    height_axis = int(np.argmin(np.ptp(body['points'], axis=0)))
    planar_axes = [axis for axis in range(3) if axis != height_axis]
    for record, label in ((lens, 'smoky lens'), (knob, 'encoder knob'), (profile, 'SVG profile')):
        center = record['center']
        if (any(center[axis] < body_bounds[0, axis] - 3.0 or center[axis] > body_bounds[1, axis] + 3.0
                for axis in planar_axes) or
                center[height_axis] < body_bounds[0, height_axis] - 5.0 or
                center[height_axis] > body_bounds[1, height_axis] + 8.0):
            return fail('GLB %s is not spatially assembled with the bezel body' % label)
    body_center = (body_bounds[0] + body_bounds[1]) / 2.0
    if np.linalg.norm(lens['center'][planar_axes] - body_center[planar_axes]) > 12.0:
        return fail('Smoky lens is not positioned across the central display window')
    return ok('Blender GLB preserves source STL/SVG geometry and has a smoky lens plus raised encoder knob')


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
