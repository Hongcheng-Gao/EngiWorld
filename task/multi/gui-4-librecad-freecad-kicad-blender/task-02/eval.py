from __future__ import annotations
import json
import os
import re
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
         'circles': [[55.0, 82.0, 2.5], [20.0, 22.0, 2.5], [90.0, 22.0, 2.5], [55.0, 48.0, 18.0]],
         'texts': ['EW4G02', 'VOC', 'CO2', 'VENT-7'],
         'min_lines': 4,
         'no_layers': ['GUIDE']},
 'stl': {'file': 'stage2_hex_air_quality_badge.stl',
         'bbox': [110.0, 96.0, 12.0],
         'bbox_tol': 4.0,
         'min_triangles': 20,
         'max_bbox_fill_ratio': 0.995,
         'require_watertight': True},
 'kicad': {'min_footprints': 4, 'min_pads': 4,
           'tokens': ['EW4G02', 'VOC-U1', 'CO2-U2', 'BAT-J1', 'VENT-KEEP', 'I2C-J2']},
 'glb': {'file': 'stage4_hex_air_quality_badge.glb',
         'tokens': [],
         'min_nodes': 2,
         'min_materials': 0,
         'nodes': ['stage2_hex_air_quality_badge', 'stage3_hex_air_quality_badge_board_profile.svg'],
         'min_meshes': 1,
         'gui_export': True,
         'accepted_import_evidence': {'stage2_stl_object': 'stage2_hex_air_quality_badge',
                                      'stage3_svg_object': 'stage3_hex_air_quality_badge_board_profile.svg'}},
 'diversity_notes': {'geometry': 'Hexagonal air quality wall badge with vent grille',
                     'electronic_focus': 'a hex PCB with VOC and CO2 sensor locations, battery '
                                         'connector, and a vent keepout',
                     'visualization_focus': 'a wall-mounted badge scene showing the grille, three '
                                            'standoffs, and sensor PCB'},
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
 'generated_by': {'script': 'generate_assets.py',
                  'packages': ['ezdxf', 'trimesh', 'pygltflib', 'numpy', 'xml.sax.saxutils']},
 'handoff': {'file': 'stage2_hex_air_quality_badge_handoff_outline.dxf'},
 'board_profile': {'file': 'stage3_hex_air_quality_badge_board_profile.svg'},
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
    if SPEC['stl'].get('require_watertight') and not bool(getattr(mesh, 'is_watertight', False)):
        return fail('STL is not a watertight FreeCAD body mesh')
    bounds = np.asarray(mesh.bounds, dtype=float)
    dims = (bounds[1] - bounds[0]).tolist()
    got = sorted(abs(x) for x in dims)
    exp = sorted(abs(x) for x in SPEC['stl']['bbox'])
    tol = SPEC['stl'].get('bbox_tol', 4.0)
    if any(abs(g - e) > tol for g, e in zip(got, exp)):
        return fail('STL bbox mismatch got %s expected %s' % (dims, SPEC['stl']['bbox']))
    bbox_volume = float(np.prod(np.asarray(dims, dtype=float)))
    if bbox_volume <= 0.0:
        return fail('STL has a zero-volume bounding box')
    fill_ratio = abs(float(getattr(mesh, 'volume', 0.0))) / bbox_volume
    if fill_ratio >= float(SPEC['stl'].get('max_bbox_fill_ratio', 1.0)):
        return fail('STL fills its entire bounding box and lacks the required holes/windows/slots: ratio %.6f' % fill_ratio)
    return ok('FreeCAD STL parsed by trimesh and dimensions passed')


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
    if 'FREECAD_HANDOFF' not in data['layers']:
        return fail('Stage2 handoff DXF missing FREECAD_HANDOFF layer')
    return ok('Stage2 FreeCAD-to-KiCad handoff DXF matches upstream geometry')


def check_kicad_board_file():
    name = SPEC['board_file']['file']
    if not required_file(name, 200):
        return False
    try:
        text = (ROOT / name).read_text(encoding='utf-8', errors='ignore')
    except Exception as exc:
        return fail('Could not read KiCad board file: ' + str(exc))
    if not re.search(r'\(generator\s+["\']?pcbnew["\']?\s*\)', text, re.IGNORECASE):
        return fail('KiCad board was not saved by the native pcbnew editor')
    footprint_count = len(re.findall(r'(?m)^\s*\(footprint(?:\s|$)', text))
    pad_count = len(re.findall(r'(?m)^\s*\(pad(?:\s|$)', text))
    if footprint_count < int(SPEC.get('kicad', {}).get('min_footprints', 0)):
        return fail('KiCad board has too few native footprints: got %s' % footprint_count)
    if pad_count < int(SPEC.get('kicad', {}).get('min_pads', 0)):
        return fail('KiCad board has too few native pads: got %s' % pad_count)
    blob = norm(text)
    for token in ['KICAD_TO_BLENDER', 'EDGE_FROM_STAGE2_HANDOFF', SPEC['handoff']['file'], SPEC['token']] + SPEC.get('kicad', {}).get('tokens', []):
        if norm(token) not in blob:
            return fail('KiCad board file missing required token: ' + token)
    if norm('Edge.Cuts') not in blob:
        return fail('KiCad board file missing Edge.Cuts outline evidence')
    if norm('F.SilkS') not in blob:
        return fail('KiCad board file missing F.SilkS silkscreen evidence')
    return ok('Native KiCad board carries footprints, pads, Edge.Cuts, and required silkscreen tokens')


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
    return ok('Stage3 KiCad-to-Blender SVG profile is parseable and matches stage2 handoff size')


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
    strings = []
    collect_glb_strings(gltf.to_dict(), strings)
    blob = '\n'.join(strings).upper()
    if 'BLENDER' not in blob:
        return fail('GLB metadata should indicate Blender GUI export/generation')
    def node_has_mesh(index, seen=None):
        if seen is None: seen = set()
        if index in seen or index < 0 or index >= len(nodes): return False
        seen.add(index)
        node = nodes[index]
        if getattr(node, 'mesh', None) is not None: return True
        for child in (getattr(node, 'children', None) or []):
            if node_has_mesh(int(child), seen): return True
        return False
    evidence = SPEC['glb'].get('accepted_import_evidence', {})
    for label, token in evidence.items():
        if str(token).upper() not in blob:
            return fail('GLB missing Blender import evidence %s: %s' % (label, token))
        matching = [index for index, node in enumerate(nodes)
                    if str(token).upper() in str(getattr(node, 'name', '') or '').upper()]
        if not matching or not any(node_has_mesh(index) for index in matching):
            return fail('GLB import evidence is not visible mesh geometry for %s: %s' % (label, token))
    return ok('Blender GLB contains visible mesh geometry from both stage2 STL and stage3 SVG')


def main():
    checks = [
        check_dependencies,
        check_required_files,
        check_intermediate_outputs,
        check_no_script_artifacts,
        check_no_command_bypass,
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
