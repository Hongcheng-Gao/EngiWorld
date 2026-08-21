# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Standalone hidden spec. This task does not import a shared evaluator.
TASK_SPEC = {'task_id': 'c-open-abaqus-ansys-autocad-task-01-windows', 'open_choice_id': 'cae-open-choice-001', 'source_task': 'task/task-c/abaqus/task-01', 'original_software': 'abaqus', 'alternative_software': 'ansys', 'distractor_software': 'autocad', 'interface': 'cli', 'domain': 'axisymmetric_plate_static', 'analysis_kind': 'static_structural', 'metrics': ['center_deflection', 'max_mises'], 'expected_result_fields': ['U', 'RF', 'S'], 'require_metrics_json': True, 'visible_goal': 'Build and solve an axisymmetric circular plate under uniform pressure; report center deflection and peak stress.', 'selection_reason': 'Axisymmetric static structural plate is a standard finite-element task in both commercial solvers.', 'artifact_hint': {'ground_truth_files': ['Job-Plate.cae', 'Job-Plate.odb', 'Job-Plate.db', 'Job-Plate.rst'], 'abaqus_stems': ['Job-Plate'], 'ansys_db_files': ['Job-Plate.db'], 'ansys_result_files': ['Job-Plate.rst']}, 'span_hint': {'x': 50.0, 'y': 1.0}, 'bounds_hint': {'x': [0.0, 50.0], 'y': [0.0, 1.0]}}
MODEL_RULES = {'metrics': {'center_deflection': ('signed', -2.0, -0.01), 'max_mises': ('signed', 5.0, 5000.0)}, 'bounds': {'x': [0.0, 50.0], 'y': [0.0, 1.0]}, 'abaqus_elements_any': ['CAX4', 'CAX8'], 'abaqus_repo_types': {'loads': ['CONCENTRATEDFORCE']}, 'abaqus_repo_min': {'boundaryConditions': 2}, 'abaqus_material': {'elastic': [[210000.0, 0.3]]}, 'abaqus_step_types': ['STATICSTEP'], 'ansys_elements_any': ['PLANE182', 'PLANE183'], 'ansys_material_numbers': [210000.0, 0.3], 'ansys_load_tokens_any': ['FY']}
DESKTOP_CANDIDATES = [
    Path(os.environ.get('USERPROFILE', r'C:\Users\user')) / 'Desktop',
    Path(r'C:\Users\user\Desktop'),
    Path(r'C:\Users\User\Desktop'),
]
ABAQUS_COMMAND = r'C:\SIMULIA\Commands\abaqus.bat'
ANSYS_EXEC = r'C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe'
DETAILS = []


def log(message):
    DETAILS.append(str(message))


def desktop_dir():
    for path in DESKTOP_CANDIDATES:
        if path.exists():
            return path
    return DESKTOP_CANDIDATES[1]


def is_nonempty(path):
    try:
        return path.exists() and path.is_file() and path.stat().st_size > 0
    except Exception:
        return False


def files_with_suffixes(root, suffixes):
    suffixes = tuple(s.lower() for s in suffixes)
    try:
        return sorted([p for p in root.iterdir() if p.is_file() and p.suffix.lower() in suffixes and is_nonempty(p)], key=lambda p: (p.suffix.lower(), p.name.lower()))
    except Exception:
        return []


def write_detail(root, passed):
    try:
        (root / 'eval_detail.txt').write_text('\n'.join(DETAILS) + '\n', encoding='utf-8')
        (root / 'eval_result.txt').write_text('True\n' if passed else 'False\n', encoding='utf-8')
    except Exception:
        pass


def has_solver_artifact(root):
    solver_suffixes = {'.cae', '.odb', '.db', '.rst', '.rth', '.wbpj'}
    try:
        return any(p.is_file() and p.suffix.lower() in solver_suffixes and is_nonempty(p) for p in root.iterdir())
    except Exception:
        return False


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def metric_value_is_valid(name, value):
    rule = MODEL_RULES.get('metrics', {}).get(name)
    if rule is None:
        return finite_number(value)
    kind, lower, upper = rule
    if kind == 'list':
        if not isinstance(value, list) or len(value) < int(lower):
            return False
        if any(not finite_number(item) or float(item) <= 0.0 or float(item) > float(upper) for item in value):
            return False
        return all(float(value[index]) <= float(value[index + 1]) for index in range(len(value) - 1))
    if not finite_number(value):
        return False
    checked = abs(float(value)) if kind == 'abs' else float(value)
    return float(lower) <= checked <= float(upper)


def check_cli_metrics_json(root):
    if not TASK_SPEC.get('require_metrics_json'):
        return True
    path = root / 'metrics.json'
    if not is_nonempty(path):
        log('metrics.json missing for CLI task')
        return False
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        log('metrics.json is not valid JSON: %s' % exc)
        return False
    if not isinstance(data, dict):
        log('metrics.json must contain an object')
        return False
    normalized = {str(k).lower(): v for k, v in data.items()}
    missing = [m for m in TASK_SPEC.get('metrics', []) if m.lower() not in normalized]
    if missing:
        log('metrics.json missing fields: %s' % missing)
        return False
    invalid = [m for m in TASK_SPEC.get('metrics', []) if not metric_value_is_valid(m, normalized[m.lower()])]
    if invalid:
        log('metrics.json contains invalid or implausible values: %s' % invalid)
        return False
    if 'first_frequency' in normalized and 'frequency_list' in normalized:
        frequencies = normalized['frequency_list']
        if not math.isclose(float(normalized['first_frequency']), float(frequencies[0]), rel_tol=0.02, abs_tol=1.0e-8):
            log('first_frequency does not match frequency_list[0]')
            return False
    return True


def find_abaqus_pair(root):
    caes = files_with_suffixes(root, ['.cae'])
    odbs = files_with_suffixes(root, ['.odb'])
    if not caes or not odbs:
        return None
    job_odbs = [odb for odb in odbs if odb.stem.lower() == 'job-plate']
    if len(caes) != 1:
        log('Abaqus deliverables contain an ambiguous number of CAE models: %s' % len(caes))
        return None
    if len(job_odbs) != 1:
        log('Abaqus deliverables must contain exactly one Job-Plate.odb result')
        return None
    return caes[0], job_odbs[0]


def find_ansys_artifacts(root):
    model_files = [path for path in files_with_suffixes(root, ['.db']) if path.stem.lower() == 'job-plate']
    result_files = [path for path in files_with_suffixes(root, ['.rst']) if path.stem.lower() == 'job-plate']
    if not model_files and not result_files:
        return None
    if len(model_files) != 1 or len(result_files) != 1:
        log('ANSYS deliverables must contain exactly one Job-Plate.db and one Job-Plate.rst')
        return None
    return model_files[0], result_files[0]


def read_ansys_rst_mesh_labels(result_path):
    from ansys.mapdl import reader as pymapdl_reader

    result = pymapdl_reader.read_binary(str(result_path))
    node_labels = [int(value) for value in result.mesh.nnum]
    element_labels = [int(value) for value in result.mesh.enum]
    return node_labels, element_labels, int(result.nsets)


def run_abaqus_checker(root, cae_path, odb_path):
    work_dir = Path(tempfile.mkdtemp(prefix='__task01_abaqus_eval_', dir=str(root)))
    checker = work_dir / '__open_choice_abaqus_checker.py'
    result = work_dir / '__open_choice_abaqus_result.txt'
    checker_source = r'''
# -*- coding: utf-8 -*-
from __future__ import annotations
import builtins
import math
import json
import os
import re
import shutil
import tempfile
import traceback
from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

SPEC = __SPEC__
RULES = __RULES__
CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
METRICS_PATH = __METRICS_PATH__
RESULT_PATH = __RESULT_PATH__
DETAILS = []
CAE_MESH_SIGNATURE = {}
CAE_MODEL_NAME = None
CAE_INPUT_PATH = None

def log(msg):
    DETAILS.append(str(msg))

def ci(v):
    try:
        return str(v).strip().upper()
    except Exception:
        return ''

def collect_xyz(nodes):
    out = []
    try:
        for n in nodes:
            c = tuple(float(x) for x in n.coordinates)
            if len(c) == 2:
                c = (c[0], c[1], 0.0)
            out.append(c[:3])
    except Exception:
        pass
    return out

def bbox(xyz):
    if not xyz:
        return None
    return {'x': (min(p[0] for p in xyz), max(p[0] for p in xyz)), 'y': (min(p[1] for p in xyz), max(p[1] for p in xyz)), 'z': (min(p[2] for p in xyz), max(p[2] for p in xyz))}

def primary_model():
    best = None
    best_score = -1
    for key in mdb.models.keys():
        model = mdb.models[key]
        score = 0
        try:
            score += len(model.parts.keys()) * 100
            for pk in model.parts.keys():
                p = model.parts[pk]
                score += len(p.nodes) + len(p.elements) * 2
        except Exception:
            pass
        if score > best_score:
            best = model
            best_score = score
    return best

def primary_part(model):
    best = None
    best_score = -1
    for key in model.parts.keys():
        part = model.parts[key]
        score = 0
        try:
            score += len(part.nodes) + 2 * len(part.elements)
        except Exception:
            pass
        if score > best_score:
            best = part
            best_score = score
    return best

def repo_objects(model, repo_name):
    try:
        repo = getattr(model, repo_name)
        return [repo[key] for key in repo.keys()]
    except Exception:
        return []

def object_type_text(obj):
    return ' '.join([
        ci(obj.__class__.__name__),
        ci(getattr(obj, 'name', '')),
        ci(getattr(obj, 'type', '')),
        ci(getattr(obj, 'distributionType', '')),
    ])

def close_enough(actual, expected):
    try:
        actual = float(actual)
        expected = float(expected)
        return math.isfinite(actual) and math.isclose(actual, expected, rel_tol=2.0e-3, abs_tol=max(1.0e-12, abs(expected) * 1.0e-6))
    except Exception:
        return False

def flatten_numbers(value):
    out = []
    if isinstance(value, (int, float)):
        return [float(value)]
    try:
        for item in value:
            out.extend(flatten_numbers(item))
    except Exception:
        try:
            out.append(float(value))
        except Exception:
            pass
    return out

def material_property_values(material, property_name):
    try:
        prop = getattr(material, property_name)
        return flatten_numbers(prop.table)
    except Exception:
        return []

def materials_match(materials, requirements):
    return all(
        any(
            all(any(close_enough(actual, expected) for actual in material_property_values(material, property_name)) for expected in expected_values)
            for material in materials
            for expected_values in candidates
        )
        for property_name, candidates in requirements.items()
    )

def check_abaqus_model_rules(model):
    try:
        parts = [model.parts[key] for key in model.parts.keys()]
    except Exception:
        parts = []
    if len(parts) < int(RULES.get('abaqus_min_parts', 1)):
        log('too few Abaqus parts for task semantics')
        return False
    element_types = set()
    for candidate_part in parts:
        try:
            element_types.update(ci(element.type) for element in candidate_part.elements)
        except Exception:
            pass
    required_any = [ci(token) for token in RULES.get('abaqus_elements_any', [])]
    if required_any and not any(any(element_type.startswith(token) for token in required_any) for element_type in element_types):
        log('Abaqus element family mismatch: %s' % sorted(element_types))
        return False
    for token in [ci(value) for value in RULES.get('abaqus_elements_all', [])]:
        if not any(element_type.startswith(token) for element_type in element_types):
            log('missing required Abaqus element family: ' + token)
            return False
    for repo_name, minimum in RULES.get('abaqus_repo_min', {}).items():
        if len(repo_objects(model, repo_name)) < int(minimum):
            log('too few objects in Abaqus repository: ' + repo_name)
            return False
    for repo_name, tokens in RULES.get('abaqus_repo_types', {}).items():
        texts = [object_type_text(obj) for obj in repo_objects(model, repo_name)]
        if not any(any(ci(token) in item for token in tokens) for item in texts):
            log('required Abaqus object type missing from ' + repo_name)
            return False
    try:
        materials = [model.materials[key] for key in model.materials.keys()]
    except Exception:
        materials = []
    if not materials_match(materials, RULES.get('abaqus_material', {})):
        log('Abaqus material property mismatch')
        return False
    variants = RULES.get('unit_variants', [])
    if variants:
        xyz = []
        for candidate_part in parts:
            xyz.extend(collect_xyz(candidate_part.nodes))
        bb = bbox(xyz)
        if not any(
            geometry_bbox_matches_scale(bb, float(variant['geometry_scale']))
            and materials_match(materials, variant.get('abaqus_material', {}))
            for variant in variants
        ):
            log('Abaqus geometry/material unit combination mismatch')
            return False
    step_objects = repo_objects(model, 'steps')
    step_texts = [object_type_text(step) for step in step_objects]
    step_types = [ci(token) for token in RULES.get('abaqus_step_types', [])]
    if step_types and not any(any(token in item for token in step_types) for item in step_texts):
        log('Abaqus analysis step type mismatch')
        return False
    response_tokens = [ci(token) for token in RULES.get('abaqus_step_response', [])]
    if response_tokens and not any(any(token in ci(getattr(step, 'response', '')) for token in response_tokens) for step in step_objects):
        log('Abaqus heat-transfer response type mismatch')
        return False
    expected_time = RULES.get('abaqus_step_time')
    if expected_time is not None and not any(close_enough(getattr(step, 'timePeriod', None), expected_time) for step in step_objects):
        log('Abaqus step time mismatch')
        return False
    minimum_eigen = RULES.get('abaqus_num_eigen_min')
    if minimum_eigen is not None:
        values = []
        for step in step_objects:
            try:
                values.append(int(step.numEigen))
            except Exception:
                pass
        if not values or max(values) < int(minimum_eigen):
            log('Abaqus eigenmode count is too small')
            return False
    if RULES.get('abaqus_nlgeom') and not any(ci(getattr(step, 'nlgeom', '')) in ('ON', 'TRUE', '1') for step in step_objects):
        log('Abaqus nonlinear geometry is not enabled')
        return False
    return True

def geometry_bbox_matches_scale(bb, scale):
    if bb is None:
        return False
    span_hints = SPEC.get('span_hint') or {}
    bounds = RULES.get('bounds') or SPEC.get('bounds_hint') or {}
    for axis, target in span_hints.items():
        if axis == 'min_span' or axis not in bb:
            continue
        expected = float(target) * scale
        observed = bb[axis][1] - bb[axis][0]
        tolerance = max(1.0e-5, abs(expected) * 0.02)
        if abs(observed - expected) > tolerance:
            return False
    for axis, target in bounds.items():
        if axis == 'min_span' or axis not in bb:
            continue
        expected_lo, expected_hi = [float(value) * scale for value in target]
        observed_lo, observed_hi = bb[axis]
        tolerance = max(1.0e-5, abs(expected_hi - expected_lo) * 0.02)
        if abs(observed_lo - expected_lo) > tolerance or abs(observed_hi - expected_hi) > tolerance:
            return False
    min_span = bounds.get('min_span') or span_hints.get('min_span')
    if min_span is not None and max(bb[axis][1] - bb[axis][0] for axis in bb) < float(min_span) * scale * 0.98:
        return False
    return True

def check_geometry_bbox(bb):
    if bb is None:
        log('no nodal bbox')
        return False
    for scale in RULES.get('geometry_scales', [1.0]):
        if geometry_bbox_matches_scale(bb, float(scale)):
            return True
    log('geometry bounds do not match the task')
    return False

def check_node_shape_rules(xyz):
    index = {'x': 0, 'y': 1, 'z': 2}
    hole = RULES.get('circular_hole')
    if hole:
        axes = [index[value] for value in hole.get('axes', ['x', 'y'])]
        center = [float(value) for value in hole['center']]
        radius = float(hole['radius'])
        tolerance = max(0.25, radius * 0.12)
        distances = [
            math.sqrt(sum((point[axis] - center[position]) ** 2 for position, axis in enumerate(axes)))
            for point in xyz
        ]
        if sum(abs(value - radius) <= tolerance for value in distances) < int(hole.get('min_nodes', 4)):
            log('circular-hole boundary nodes not found')
            return False
        if any(value < radius - tolerance for value in distances):
            log('mesh occupies the required circular hole')
            return False
    cylinder = RULES.get('solid_cylinder')
    if cylinder:
        axial = index[cylinder.get('axis', 'y')]
        transverse = [value for value in (0, 1, 2) if value != axial]
        center = [float(value) for value in cylinder.get('center', [0.0, 0.0])]
        radius = float(cylinder['radius'])
        tolerance = max(0.2, radius * 0.08)
        distances = [
            math.sqrt(sum((point[axis] - center[position]) ** 2 for position, axis in enumerate(transverse)))
            for point in xyz
        ]
        if max(distances or [0.0]) > radius + tolerance:
            log('shaft cross-section is not circular')
            return False
        if sum(abs(value - radius) <= tolerance for value in distances) < int(cylinder.get('min_nodes', 6)):
            log('circular shaft boundary nodes not found')
            return False
    sphere = RULES.get('sphere_surface')
    if sphere:
        center = [float(value) for value in sphere['center']]
        radius = float(sphere['radius'])
        tolerance = max(0.25, radius * 0.08)
        distances = [math.sqrt(sum((point[i] - center[i]) ** 2 for i in range(3))) for point in xyz]
        if sum(abs(value - radius) <= tolerance for value in distances) < int(sphere.get('min_nodes', 8)):
            log('spherical contact body surface nodes not found')
            return False
    return True

def step_text(step_obj):
    return ' '.join([ci(step_obj.__class__.__name__), ci(getattr(step_obj, 'procedureType', '')), ci(getattr(step_obj, 'analysis', ''))])

def check_abaqus_geometry(model, part):
    xyz = []
    try:
        asm = model.rootAssembly
        for key in asm.instances.keys():
            xyz.extend(collect_xyz(asm.instances[key].nodes))
    except Exception:
        pass
    if not xyz:
        try:
            for key in model.parts.keys():
                xyz.extend(collect_xyz(model.parts[key].nodes))
        except Exception:
            pass
    if not xyz and part is not None:
        xyz = collect_xyz(part.nodes)
    return check_geometry_bbox(bbox(xyz)) and check_node_shape_rules(xyz)

def check_abaqus_materials(model):
    try:
        if len(model.materials.keys()) < 1:
            log('no material found')
            return False
    except Exception:
        log('cannot inspect materials')
        return False
    return True

def check_abaqus_analysis_step(model):
    try:
        step_objs = [model.steps[k] for k in model.steps.keys()]
    except Exception:
        log('cannot inspect steps')
        return False
    if not step_objs:
        log('no analysis step found')
        return False
    kind = SPEC.get('analysis_kind', '')
    texts = ' '.join(step_text(s) for s in step_objs)
    if kind == 'modal' and 'FREQUENCY' not in texts:
        log('frequency step not found')
        return False
    if kind == 'buckling' and 'BUCKLE' not in texts:
        log('buckling step not found')
        return False
    if kind in ('static_structural', 'contact', 'thermal_structural') and 'STATIC' not in texts:
        log('static step not found')
        return False
    if kind == 'thermal' and ('HEAT' not in texts and 'TRANSFER' not in texts):
        log('heat transfer step not found')
        return False
    return True

def check_abaqus_boundary_loads(model):
    kind = SPEC.get('analysis_kind', '')
    try:
        bc_count = len(model.boundaryConditions.keys())
    except Exception:
        bc_count = 0
    if bc_count < 1:
        log('no boundary condition found')
        return False
    if kind in ('modal', 'thermal'):
        return True
    counts = []
    for repo_name in ('loads', 'predefinedFields', 'interactions', 'constraints'):
        try:
            counts.append(len(getattr(model, repo_name).keys()))
        except Exception:
            counts.append(0)
    if sum(counts) < 1:
        log('no load/predefined/interactions/constraints evidence found')
        return False
    return True

def _keyword_blocks(input_text):
    blocks = []
    header = None
    data = []
    for raw_line in input_text.splitlines():
        line = raw_line.strip()
        if line.startswith('**'):
            continue
        if line.startswith('*'):
            if header is not None:
                blocks.append((header, data))
            header = line
            data = []
        elif header is not None and line:
            data.append(line)
    if header is not None:
        blocks.append((header, data))
    return blocks

def _header_option(header, name):
    match = re.search(r'(?:^|,)\s*%s\s*=\s*([^,]+)' % re.escape(name), header, re.I)
    return match.group(1).strip() if match else None

def _parse_nsets(input_text):
    definitions = {}
    for header, lines in _keyword_blocks(input_text):
        is_nset = bool(re.match(r'^\*NSET(?:\s*,|$)', header, re.I))
        is_node = bool(re.match(r'^\*NODE(?:\s*,|$)', header, re.I))
        if not is_nset and not is_node:
            continue
        raw_name = _header_option(header, 'NSET')
        if not raw_name:
            continue
        key = ci(raw_name)
        values = definitions.setdefault(key, [])
        tokens = []
        for line in lines:
            for token in line.split(','):
                token = token.strip()
                if token:
                    tokens.append(token)
        if is_node:
            for line in lines:
                fields = [value.strip() for value in line.split(',') if value.strip()]
                if fields:
                    try:
                        values.append(int(fields[0]))
                    except Exception:
                        pass
        elif re.search(r'(?:^|,)\s*GENERATE(?:\s*,|$)', header, re.I):
            numbers = []
            for token in tokens:
                try:
                    numbers.append(int(token))
                except Exception:
                    pass
            for index in range(0, len(numbers) - 2, 3):
                first, last, increment = numbers[index:index + 3]
                if increment > 0:
                    values.extend(range(first, last + 1, increment))
        else:
            for token in tokens:
                try:
                    values.append(int(token))
                except Exception:
                    values.append(ci(token))

    def matching_key(name):
        key = ci(name)
        if key in definitions:
            return key
        suffix = key.split('.')[-1]
        matches = [candidate for candidate in definitions if candidate.split('.')[-1] == suffix]
        return matches[0] if len(matches) == 1 else None

    def resolve(name, stack):
        key = matching_key(name)
        if key is None or key in stack:
            return []
        labels = []
        for value in definitions.get(key, []):
            if isinstance(value, int):
                labels.append(value)
            else:
                labels.extend(resolve(value, stack | set([key])))
        return labels

    result = {}
    for name in definitions:
        result[name] = sorted(set(resolve(name, set())))
    return result

def _parse_elsets(input_text):
    definitions = {}
    for header, lines in _keyword_blocks(input_text):
        is_elset = bool(re.match(r'^\*ELSET(?:\s*,|$)', header, re.I))
        is_element = bool(re.match(r'^\*ELEMENT(?:\s*,|$)', header, re.I))
        if not is_elset and not is_element:
            continue
        raw_name = _header_option(header, 'ELSET')
        if not raw_name:
            continue
        values = []
        if is_element:
            for line in lines:
                fields = [value.strip() for value in line.split(',') if value.strip()]
                if fields:
                    try:
                        values.append(int(fields[0]))
                    except Exception:
                        pass
        elif re.search(r'(?:^|,)\s*GENERATE(?:\s*,|$)', header, re.I):
            numbers = []
            for line in lines:
                for token in line.split(','):
                    try:
                        numbers.append(int(token.strip()))
                    except Exception:
                        pass
            for index in range(0, len(numbers) - 2, 3):
                first, last, increment = numbers[index:index + 3]
                if increment > 0:
                    values.extend(range(first, last + 1, increment))
        else:
            for line in lines:
                for token in line.split(','):
                    token = token.strip()
                    if not token:
                        continue
                    try:
                        values.append(int(token))
                    except Exception:
                        values.append(ci(token))
        definitions.setdefault(ci(raw_name), []).extend(values)

    def matching_key(name):
        key = ci(name)
        if key in definitions:
            return key
        suffix = key.split('.')[-1]
        matches = [candidate for candidate in definitions if candidate.split('.')[-1] == suffix]
        return matches[0] if len(matches) == 1 else None

    def resolve(name, stack):
        key = matching_key(name)
        if key is None or key in stack:
            return []
        labels = []
        for value in definitions.get(key, []):
            if isinstance(value, int):
                labels.append(value)
            else:
                labels.extend(resolve(value, stack | set([key])))
        return labels

    result = {}
    for name in definitions:
        result[name] = sorted(set(resolve(name, set())))
    return result

def _resolve_elset_labels(token, elsets):
    key = ci(token)
    if key in elsets:
        return list(elsets[key])
    suffix = key.split('.')[-1]
    matches = [labels for name, labels in elsets.items() if name.split('.')[-1] == suffix]
    return list(matches[0]) if len(matches) == 1 else []

def _resolve_nset_labels(token, nsets):
    value = token.strip()
    try:
        return [int(value)]
    except Exception:
        pass
    key = ci(value)
    if key in nsets:
        return list(nsets[key])
    suffix = key.split('.')[-1]
    try:
        return [int(suffix)]
    except Exception:
        pass
    matches = [labels for name, labels in nsets.items() if name.split('.')[-1] == suffix]
    return list(matches[0]) if len(matches) == 1 else []

def _parse_inp_mesh(input_text):
    nodes = {}
    elements = {}
    for header, lines in _keyword_blocks(input_text):
        if re.match(r'^\*NODE(?:\s*,|$)', header, re.I):
            for line in lines:
                fields = [value.strip() for value in line.split(',') if value.strip()]
                if len(fields) < 3:
                    continue
                try:
                    label = int(fields[0])
                    coords = tuple(float(value.replace('D', 'E').replace('d', 'e')) for value in fields[1:3])
                    nodes[label] = coords
                except Exception:
                    pass
        elif re.match(r'^\*ELEMENT(?:\s*,|$)', header, re.I):
            element_type = ci(_header_option(header, 'TYPE'))
            for line in lines:
                fields = [value.strip() for value in line.split(',') if value.strip()]
                if len(fields) < 3:
                    continue
                try:
                    label = int(fields[0])
                    elements[label] = (element_type, tuple(int(value) for value in fields[1:]))
                except Exception:
                    pass
    return {'nodes': nodes, 'elements': elements}

def _named_set_nodes(model, part, name):
    matches = []
    for repo in (getattr(part, 'sets', None), getattr(model.rootAssembly, 'sets', None)):
        if repo is None:
            continue
        for key in repo.keys():
            if ci(key).split('.')[-1] != ci(name):
                continue
            try:
                nodes = list(repo[key].nodes)
            except Exception:
                nodes = []
            if nodes:
                matches.append(nodes)
    if not matches:
        raise RuntimeError('expected exactly one nonempty set named ' + name)
    signatures = []
    for nodes in matches:
        signatures.append(set(
            (int(node.label), tuple(round(float(value), 8) for value in node.coordinates[:2]))
            for node in nodes
        ))
    if any(signature != signatures[0] for signature in signatures[1:]):
        raise RuntimeError('conflicting sets named ' + name)
    return matches[0]

def _export_input(model):
    directory = os.path.dirname(RESULT_PATH)
    job_name = 'Task01EvalExport'
    input_path = os.path.join(directory, job_name + '.inp')
    try:
        if job_name in mdb.jobs:
            del mdb.jobs[job_name]
        job = mdb.Job(name=job_name, model=model.name, numCpus=1, numDomains=1)
        old_cwd = os.getcwd()
        os.chdir(directory)
        try:
            job.writeInput(consistencyChecking=ON)
        finally:
            os.chdir(old_cwd)
        with open(input_path, 'r') as stream:
            return stream.read(), input_path
    finally:
        try:
            if job_name in mdb.jobs:
                del mdb.jobs[job_name]
        except Exception:
            pass

def check_task01_cae(model, part):
    global CAE_INPUT_PATH, CAE_MESH_SIGNATURE
    try:
        element_types = set(ci(element.type) for element in part.elements)
        node_count = len(part.nodes)
        element_count = len(part.elements)
        part_coords = {
            int(node.label): tuple(float(value) for value in node.coordinates[:2])
            for node in part.nodes
        }
    except Exception:
        log('cannot inspect task-specific mesh')
        return False
    if element_count != 25 or node_count not in (52, 128):
        log('expected 25 radial elements and one element through thickness')
        return False
    if not element_types or not all(value.startswith('CAX4') or value.startswith('CAX8') for value in element_types):
        log('axisymmetric element is not a stable CAX4/CAX8 family: %s' % sorted(element_types))
        return False
    quadratic = node_count == 128
    if quadratic and not all(value.startswith('CAX8') for value in element_types):
        log('128-node mesh must use the CAX8 family throughout')
        return False
    if not quadratic and not all(value.startswith('CAX4') for value in element_types):
        log('52-node mesh must use the CAX4 family throughout')
        return False

    if quadratic:
        expected_coordinates = (
            [(float(radius), 0.0) for radius in range(51)]
            + [(float(radius), 1.0) for radius in range(51)]
            + [(float(radius), 0.5) for radius in range(0, 51, 2)]
        )
    else:
        expected_coordinates = (
            [(float(radius), 0.0) for radius in range(0, 51, 2)]
            + [(float(radius), 1.0) for radius in range(0, 51, 2)]
        )
    unmatched_coordinates = set(range(len(expected_coordinates)))
    normalized_coordinates = {}
    for label, coordinates in part_coords.items():
        matches = [
            index for index in unmatched_coordinates
            if all(abs(coordinates[axis] - expected_coordinates[index][axis]) <= 1.0e-6 for axis in range(2))
        ]
        if len(matches) != 1:
            log('Abaqus nodes do not form the required structured 2 mm by 1 element mesh')
            return False
        match = matches[0]
        unmatched_coordinates.remove(match)
        normalized_coordinates[label] = expected_coordinates[match]
    if unmatched_coordinates:
        log('Abaqus structured mesh coordinates are incomplete')
        return False

    connected_labels = set()
    seen_radial_bins = set()
    for element in part.elements:
        try:
            element_nodes = list(element.getNodes())
            node_labels = [int(node.label) for node in element_nodes]
        except Exception:
            try:
                node_labels = [int(value) for value in element.connectivity]
            except Exception:
                log('cannot inspect Abaqus element connectivity')
                return False
        expected_node_total = 8 if quadratic else 4
        if (
            len(node_labels) != expected_node_total
            or len(set(node_labels)) != expected_node_total
            or any(label not in normalized_coordinates for label in node_labels)
        ):
            log('Abaqus element connectivity is incomplete or degenerate')
            return False
        observed_coordinates = set(normalized_coordinates[label] for label in node_labels)
        matching_bins = []
        for radial_bin in range(25):
            lo = float(2 * radial_bin)
            hi = lo + 2.0
            expected_cell = {(lo, 0.0), (hi, 0.0), (hi, 1.0), (lo, 1.0)}
            if quadratic:
                mid = lo + 1.0
                expected_cell.update({(mid, 0.0), (hi, 0.5), (mid, 1.0), (lo, 0.5)})
            if observed_coordinates == expected_cell:
                matching_bins.append(radial_bin)
        if len(matching_bins) != 1 or matching_bins[0] in seen_radial_bins:
            log('Abaqus elements do not cover each structured radial cell exactly once')
            return False
        seen_radial_bins.add(matching_bins[0])
        connected_labels.update(node_labels)
    if seen_radial_bins != set(range(25)) or connected_labels != set(part_coords):
        log('Abaqus mesh has a missing radial cell or an unattached node')
        return False
    try:
        expected_count = 51 if quadratic else 26
        named_nodes = {
            name: _named_set_nodes(model, part, name)
            for name in ('AXIS', 'OUTER', 'TOP')
        }
        expected_labels = {
            'AXIS': set(label for label, value in part_coords.items() if abs(value[0]) <= 1.0e-6),
            'OUTER': set(label for label, value in part_coords.items() if abs(value[0] - 50.0) <= 1.0e-6),
            'TOP': set(label for label, value in part_coords.items() if abs(value[1] - 1.0) <= 1.0e-6),
        }
        observed_labels = {
            name: set(int(node.label) for node in nodes)
            for name, nodes in named_nodes.items()
        }
        if observed_labels['AXIS'] != expected_labels['AXIS'] or len(observed_labels['AXIS']) not in (2, 3):
            log('AXIS set does not exactly cover r=0')
            return False
        if observed_labels['OUTER'] != expected_labels['OUTER'] or len(observed_labels['OUTER']) not in (2, 3):
            log('OUTER set does not exactly cover r=50')
            return False
        if observed_labels['TOP'] != expected_labels['TOP'] or len(observed_labels['TOP']) != expected_count:
            log('TOP set does not exactly cover z=1')
            return False
        top_nodes = sorted(
            [(int(node.label), float(node.coordinates[0])) for node in named_nodes['TOP']],
            key=lambda item: item[1],
        )
    except Exception:
        log('required AXIS/OUTER/TOP node sets are missing')
        return False

    try:
        input_text, CAE_INPUT_PATH = _export_input(model)
    except Exception:
        log('cannot export CAE model to input for task-specific checks')
        log(traceback.format_exc())
        return False
    blocks = _keyword_blocks(input_text)
    upper = input_text.upper()
    current_step = None
    all_steps = set()
    static_steps = set()
    cload_blocks = []
    for header, lines in blocks:
        if re.match(r'^\*STEP(?:\s*,|$)', header, re.I):
            current_step = ci(_header_option(header, 'NAME'))
            if current_step:
                all_steps.add(current_step)
        elif re.match(r'^\*END STEP(?:\s*,|$)', header, re.I):
            current_step = None
        elif re.match(r'^\*STATIC(?:\s*,|$)', header, re.I) and current_step:
            static_steps.add(current_step)
        elif re.match(r'^\*CLOAD(?:\s*,|$)', header, re.I):
            cload_blocks.append((current_step, lines))
    if all_steps != {'STEP-PRESSURE'} or static_steps != {'STEP-PRESSURE'}:
        log('CAE must contain exactly one static user step named Step-Pressure')
        return False
    forbidden_loads = (
        '*DLOAD', '*DSLOAD', '*DFLUX', '*DSFLUX', '*CFLUX', '*BODY HEAT FLUX',
        '*FILM', '*RADIATE', '*TEMPERATURE', '*CONNECTOR LOAD',
    )
    if not cload_blocks or any(token in upper for token in forbidden_loads):
        log('loading must use concentrated nodal forces only')
        return False
    forbidden_model_keywords = (
        '*EQUATION', '*MPC', '*COUPLING', '*KINEMATIC COUPLING',
        '*DISTRIBUTING COUPLING', '*RIGID BODY', '*TIE', '*CONNECTOR',
        '*SPRING', '*FOUNDATION', '*INITIAL CONDITIONS', '*IMPERFECTION',
    )
    if any(
        any(
            ci(header) == token
            or ci(header).startswith(token + ',')
            or ci(header).startswith(token + ' ')
            for token in forbidden_model_keywords
        )
        for header, lines in blocks
    ):
        log('additional constraints, connectors, or initial states are not allowed')
        return False

    nsets = _parse_nsets(input_text)
    boundary_dofs = {}
    for header, lines in blocks:
        if not re.match(r'^\*BOUNDARY(?:\s*,|$)', header, re.I):
            continue
        if _header_option(header, 'OP') or _header_option(header, 'AMPLITUDE') or _header_option(header, 'TYPE'):
            log('BOUNDARY OP/amplitude/type variants are not allowed in this task')
            return False
        for line in lines:
            fields = [value.strip() for value in line.split(',')]
            if len(fields) < 2:
                log('invalid BOUNDARY data line')
                return False
            labels = _resolve_nset_labels(fields[0], nsets)
            try:
                first_dof = int(fields[1])
                last_dof = int(fields[2]) if len(fields) > 2 and fields[2] else first_dof
                magnitude = float(fields[3].replace('D', 'E').replace('d', 'e')) if len(fields) > 3 and fields[3] else 0.0
            except Exception:
                log('invalid BOUNDARY data values')
                return False
            if not labels or abs(magnitude) > 1.0e-12:
                log('BOUNDARY targets unknown nodes or prescribes nonzero motion')
                return False
            for label in labels:
                boundary_dofs.setdefault(label, set()).update(range(first_dof, last_dof + 1))
    expected_boundary_dofs = {}
    for label in observed_labels['AXIS']:
        expected_boundary_dofs.setdefault(label, set()).add(1)
    for label in observed_labels['OUTER']:
        expected_boundary_dofs.setdefault(label, set()).update((1, 2))
    if boundary_dofs != expected_boundary_dofs:
        log('AXIS/OUTER boundary nodes or DOFs are incorrect')
        return False

    top_labels = set(label for label, radius in top_nodes)
    loads_by_label = {}
    for step_name, lines in cload_blocks:
        if step_name != 'STEP-PRESSURE':
            log('CLOAD appears outside Step-Pressure')
            return False
        header = next((candidate for candidate, candidate_lines in blocks if candidate_lines is lines), '')
        if _header_option(header, 'OP') or _header_option(header, 'AMPLITUDE'):
            log('CLOAD OP/amplitude variants are not allowed in this task')
            return False
        for line in lines:
            fields = [value.strip() for value in line.split(',')]
            if len(fields) < 3:
                log('invalid CLOAD data line')
                return False
            labels = _resolve_nset_labels(fields[0], nsets)
            try:
                dof = int(fields[1])
                magnitude = float(fields[2].replace('D', 'E').replace('d', 'e'))
            except Exception:
                log('invalid CLOAD values')
                return False
            if dof != 2 or len(labels) != 1 or labels[0] not in top_labels:
                log('each CLOAD must target one TOP node in U2 only')
                return False
            loads_by_label[labels[0]] = loads_by_label.get(labels[0], 0.0) + magnitude

    sorted_radii = [radius for label, radius in top_nodes]
    expected_by_label = {}
    for index, (label, radius) in enumerate(top_nodes):
        if index == 0:
            delta = 0.5 * (sorted_radii[1] - radius)
        elif index == len(top_nodes) - 1:
            delta = 0.5 * (radius - sorted_radii[index - 1])
        else:
            delta = 0.5 * (sorted_radii[index + 1] - sorted_radii[index - 1])
        expected_by_label[label] = -0.1 * 2.0 * math.pi * radius * delta
    loads = []
    for label, expected in expected_by_label.items():
        magnitude = loads_by_label.get(label, 0.0)
        if abs(expected) <= 1.0e-12:
            if abs(magnitude) > 1.0e-12:
                log('axis node must carry zero equivalent force')
                return False
            continue
        if label not in loads_by_label:
            log('each nonzero TOP node must have a CLOAD contribution')
            return False
        if not math.isclose(magnitude, expected, rel_tol=2.0e-4, abs_tol=2.0e-5):
            log('TOP nodal load does not match annular tributary formula')
            return False
        loads.append((label, magnitude))
    if set(loads_by_label) - set(expected_by_label):
        log('CLOAD exists outside TOP')
        return False
    total = builtins.sum(magnitude for label, magnitude in loads)
    if not math.isclose(total, -0.1 * math.pi * 50.0 ** 2, rel_tol=2.0e-4, abs_tol=2.0e-3):
        log('TOP nodal force total is not -785.398 N')
        return False

    node_output = set()
    element_output = set()
    for header, lines in blocks:
        tokens = set(ci(token) for line in lines for token in re.split(r'[\s,]+', line) if token.strip())
        if re.match(r'^\*NODE OUTPUT(?:\s*,|$)', header, re.I):
            node_output.update(tokens)
        elif re.match(r'^\*ELEMENT OUTPUT(?:\s*,|$)', header, re.I):
            element_output.update(tokens)
    if not {'U', 'RF'}.issubset(node_output):
        log('U and RF field output request is missing')
        return False
    if 'S' not in element_output:
        log('S field output request is missing')
        return False

    material_names = {ci(name): name for name in model.materials.keys()}
    steel_name = material_names.get('STEEL')
    if steel_name is None:
        log('material named Steel is missing')
        return False
    try:
        elastic_row = list(model.materials[steel_name].elastic.table[0])
        if (
            len(elastic_row) < 2
            or not close_enough(elastic_row[0], 210000.0)
            or not close_enough(elastic_row[1], 0.3)
        ):
            log('Steel elastic first row is not E=210000, nu=0.3')
            return False
    except Exception:
        log('cannot inspect Steel elastic data')
        return False
    section_assignments = []
    try:
        for assignment in part.sectionAssignments:
            section_name = assignment.sectionName
            section = model.sections[section_name]
            section_material = ci(getattr(section, 'material', ''))
            section_type = ci(section.__class__.__name__)
            section_assignments.append((section_type, section_material))
    except Exception:
        log('cannot inspect CAE section assignments')
        return False
    if not section_assignments or any(
        'HOMOGENEOUSSOLIDSECTION' not in section_type or material_name != 'STEEL'
        for section_type, material_name in section_assignments
    ):
        log('every CAE section assignment must use a Steel homogeneous solid section')
        return False

    expected_element_labels = set(int(element.label) for element in part.elements)
    elsets = _parse_elsets(input_text)
    steel_coverage = set()
    wrong_coverage = set()
    for header, lines in blocks:
        if not re.match(r'^\*SOLID SECTION(?:\s*,|$)', header, re.I):
            continue
        set_name = _header_option(header, 'ELSET')
        material_name = ci(_header_option(header, 'MATERIAL'))
        labels = set(_resolve_elset_labels(set_name or '', elsets)).intersection(expected_element_labels)
        if 'COMPOSITE' in ci(header):
            wrong_coverage.update(labels)
        elif material_name == 'STEEL':
            steel_coverage.update(labels)
        else:
            wrong_coverage.update(labels)
    if steel_coverage != expected_element_labels or wrong_coverage:
        log('exported input does not assign only Steel homogeneous solid section to every plate element')
        return False

    CAE_MESH_SIGNATURE = _parse_inp_mesh(input_text)
    if len(CAE_MESH_SIGNATURE['nodes']) != node_count or len(CAE_MESH_SIGNATURE['elements']) != element_count:
        log('cannot construct a complete CAE mesh signature')
        return False
    return True

def field_value_key(value):
    instance_name = ci(getattr(getattr(value, 'instance', None), 'name', ''))
    position = ci(getattr(value, 'position', ''))
    try:
        return (instance_name, 'NODE', int(value.nodeLabel), position)
    except Exception:
        pass
    section_point = getattr(value, 'sectionPoint', None)
    try:
        section_number = int(getattr(section_point, 'number', 0) or 0)
    except Exception:
        section_number = 0
    return (
        instance_name,
        'ELEMENT',
        int(value.elementLabel),
        int(getattr(value, 'integrationPoint', 0) or 0),
        section_number,
        position,
    )

def extract_field_signature(frame, field_name):
    try:
        field = frame.fieldOutputs[field_name]
        if field_name == 'S':
            invariants = set(ci(value) for value in getattr(field, 'validInvariants', ()))
            if 'MISES' not in invariants:
                log('S field does not declare the MISES invariant')
                return None
        signature = {}
        for value in field.values:
            key = field_value_key(value)
            data = tuple(float(item) for item in flatten_numbers(field_value_data(value)))
            if not data or not all(math.isfinite(item) for item in data):
                log(field_name + ' field contains non-finite or empty data')
                return None
            if field_name == 'S':
                mises = float(value.mises)
                if not math.isfinite(mises):
                    log('S field contains non-finite Mises data')
                    return None
                data = data + (mises,)
            if key in signature:
                log(field_name + ' field contains a duplicate location key')
                return None
            signature[key] = data
        if not signature:
            log(field_name + ' field signature is empty')
            return None
        return signature
    except Exception:
        log('cannot extract complete ' + field_name + ' field signature')
        log(traceback.format_exc())
        return None

def task01_expected_ip_count(element_type):
    element_type = ci(element_type)
    if element_type.startswith('CAX4'):
        return 1 if element_type.startswith('CAX4R') else 4
    if element_type.startswith('CAX8'):
        return 4 if element_type.startswith('CAX8R') else 9
    return None

def check_task01_field_coverage(frame, instance, node_labels, elements):
    try:
        instance_name = ci(instance.name)
        expected_nodes = set(int(label) for label in node_labels)
        for field_name in ('U', 'RF'):
            observed_nodes = set()
            for value in frame.fieldOutputs[field_name].values:
                if ci(getattr(value, 'position', '')) != 'NODAL':
                    continue
                if ci(getattr(getattr(value, 'instance', None), 'name', '')) != instance_name:
                    continue
                observed_nodes.add(int(value.nodeLabel))
            if observed_nodes != expected_nodes:
                log('%s field does not cover every plate node' % field_name)
                return False

        expected_elements = set(int(label) for label in elements)
        integration_points = {}
        for value in frame.fieldOutputs['S'].values:
            if ci(getattr(value, 'position', '')) != 'INTEGRATION_POINT':
                continue
            if ci(getattr(getattr(value, 'instance', None), 'name', '')) != instance_name:
                continue
            element_label = int(value.elementLabel)
            integration_point = int(getattr(value, 'integrationPoint', 0) or 0)
            integration_points.setdefault(element_label, set()).add(integration_point)
        if set(integration_points) != expected_elements:
            log('S field does not cover every plate element')
            return False
        for element_label, (element_type, connectivity) in elements.items():
            expected_count = task01_expected_ip_count(element_type)
            expected_points = set(range(1, expected_count + 1)) if expected_count is not None else set()
            if integration_points.get(int(element_label), set()) != expected_points:
                log(
                    'S field integration-point coverage is incomplete for element %s (%s)'
                    % (element_label, element_type)
                )
                return False
        return True
    except Exception:
        log('cannot verify complete U/RF/S field coverage')
        log(traceback.format_exc())
        return False

def extract_task01_response(odb, frame):
    try:
        instances = [
            odb.rootAssembly.instances[name]
            for name in odb.rootAssembly.instances.keys()
            if len(odb.rootAssembly.instances[name].nodes) or len(odb.rootAssembly.instances[name].elements)
        ]
        if len(instances) != 1:
            log('ODB must contain exactly one meshed plate instance')
            return None
        instance = instances[0]
        if ci(instance.name) != CAE_MESH_SIGNATURE.get('instance_name'):
            log('CAE and ODB instance names do not match')
            return None
        coords = {
            int(node.label): tuple(float(value) for value in node.coordinates[:2])
            for node in instance.nodes
        }
        odb_elements = {
            int(element.label): (ci(element.type), tuple(int(value) for value in element.connectivity))
            for element in instance.elements
        }
        cae_coords = CAE_MESH_SIGNATURE.get('nodes', {})
        cae_elements = CAE_MESH_SIGNATURE.get('elements', {})
        if set(coords) != set(cae_coords) or odb_elements != cae_elements:
            log('CAE and ODB mesh labels, types, or connectivity do not match')
            return None
        if any(
            len(coords[label]) != len(cae_coords[label])
            or any(abs(coords[label][index] - cae_coords[label][index]) > 1.0e-7 for index in range(len(coords[label])))
            for label in coords
        ):
            log('CAE and ODB nodal coordinates do not match')
            return None
        center_labels = [label for label, value in coords.items() if abs(value[0]) <= 1.0e-6 and abs(value[1] - 1.0) <= 1.0e-6]
        outer_labels = set(label for label, value in coords.items() if abs(value[0] - 50.0) <= 1.0e-6)
        if len(center_labels) != 1 or len(outer_labels) not in (2, 3):
            log('ODB center or OUTER nodes are incorrect')
            return None
        if not check_task01_field_coverage(frame, instance, coords, odb_elements):
            return None
        field_signatures = {}
        for field_name in ('U', 'RF', 'S'):
            field_signatures[field_name] = extract_field_signature(frame, field_name)
            if field_signatures[field_name] is None:
                return None
        u2 = None
        for value in frame.fieldOutputs['U'].values:
            if int(value.nodeLabel) == center_labels[0]:
                u2 = float(field_value_data(value)[1])
                break
        mises_values = []
        for value in frame.fieldOutputs['S'].values:
            if ci(getattr(value, 'position', '')) != 'INTEGRATION_POINT':
                continue
            try:
                mises_values.append(float(value.mises))
            except Exception:
                pass
        support_rf2 = 0.0
        for value in frame.fieldOutputs['RF'].values:
            if int(value.nodeLabel) in outer_labels:
                support_rf2 += float(field_value_data(value)[1])
        if u2 is None or not mises_values:
            log('cannot extract center U2 or Mises from ODB')
            return None
        max_mises = max(mises_values)
        if not (-2.0 <= u2 <= -0.01) or not (5.0 <= max_mises <= 5000.0):
            log('ODB response is outside physical sanity limits')
            return None
        if not math.isclose(support_rf2, 0.1 * math.pi * 50.0 ** 2, rel_tol=0.02, abs_tol=0.5):
            log('ODB OUTER reaction does not balance the applied load')
            return None
        return {
            'center_deflection': u2,
            'max_mises': max_mises,
            'support_rf2': support_rf2,
            'field_signatures': field_signatures,
        }
    except Exception:
        log('task-specific ODB extraction failed')
        log(traceback.format_exc())
        return None

def check_task01_sidecar(response):
    try:
        with open(METRICS_PATH, 'r') as stream:
            metrics = json.load(stream)
        sidecar_u2 = float(metrics['center_deflection'])
        sidecar_mises = float(metrics['max_mises'])
    except Exception:
        log('cannot read task metrics sidecar')
        return False
    if not math.isclose(sidecar_u2, response['center_deflection'], rel_tol=1.0e-3, abs_tol=5.0e-4):
        log('metrics center_deflection does not match ODB')
        return False
    if not math.isclose(sidecar_mises, response['max_mises'], rel_tol=1.0e-4, abs_tol=5.0e-3):
        log('metrics max_mises does not match ODB')
        return False
    return True

def task01_last_frame(odb, source_name):
    step_names = list(odb.steps.keys())
    matching_steps = [name for name in step_names if ci(name) == 'STEP-PRESSURE']
    if len(step_names) != 1 or len(matching_steps) != 1:
        log(source_name + ' must contain only Step-Pressure')
        return None
    step = odb.steps[matching_steps[0]]
    if not step.frames:
        log(source_name + ' Step-Pressure has no frames')
        return None
    return step.frames[-1]

def compare_task01_responses(submitted, resolved):
    tolerances = {
        'center_deflection': (1.0e-4, 5.0e-5),
        'max_mises': (2.0e-4, 2.0e-2),
        'support_rf2': (1.0e-4, 5.0e-2),
    }
    for name, (relative, absolute) in tolerances.items():
        if not math.isclose(submitted[name], resolved[name], rel_tol=relative, abs_tol=absolute):
            log('submitted ODB does not match CAE re-solve for ' + name)
            return False
    field_tolerances = {
        'U': (1.0e-6, 1.0e-9),
        'RF': (1.0e-6, 1.0e-6),
        'S': (2.0e-5, 2.0e-4),
    }
    for field_name, (relative, absolute) in field_tolerances.items():
        submitted_field = submitted['field_signatures'][field_name]
        resolved_field = resolved['field_signatures'][field_name]
        if set(submitted_field) != set(resolved_field):
            log('submitted ODB does not match CAE re-solve ' + field_name + ' locations')
            return False
        for key in submitted_field:
            submitted_values = submitted_field[key]
            resolved_values = resolved_field[key]
            if len(submitted_values) != len(resolved_values) or any(
                not math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute)
                for actual, expected in zip(submitted_values, resolved_values)
            ):
                log('submitted ODB does not match CAE re-solve ' + field_name + ' at ' + repr(key))
                return False
    return True

def resolve_cae_and_compare(submitted_response):
    work_dir = tempfile.mkdtemp(prefix='Task01AbaqusResolve_')
    job_name = re.sub(r'[^A-Za-z0-9]', '', os.path.basename(work_dir))[:48]
    old_cwd = os.getcwd()
    odb = None
    try:
        os.chdir(work_dir)
        if job_name in mdb.jobs:
            del mdb.jobs[job_name]
        if not CAE_INPUT_PATH or not os.path.isfile(CAE_INPUT_PATH):
            log('validated CAE input deck is unavailable for re-solve')
            return False
        job = mdb.JobFromInputFile(
            name=job_name,
            inputFileName=CAE_INPUT_PATH,
            queue='',
            waitHours=0,
            waitMinutes=0,
            scratch=work_dir,
            userSubroutine='',
            numCpus=1,
            numDomains=1,
        )
        job.submit(consistencyChecking=ON)
        job.waitForCompletion()
        job_status = ci(job.status)
        sta_path = os.path.join(work_dir, job_name + '.sta')
        sta_text = ''
        if os.path.isfile(sta_path):
            with open(sta_path, 'r') as stream:
                sta_text = stream.read()
        sta_completed = 'THE ANALYSIS HAS COMPLETED SUCCESSFULLY' in ci(sta_text)
        if 'ABORT' in job_status or 'TERMINAT' in job_status:
            log('CAE re-solve failed with status: ' + str(job.status))
            return False
        if job_status != 'COMPLETED' and not sta_completed:
            log('CAE re-solve lacks completed status and successful STA evidence: ' + str(job.status))
            return False
        resolved_path = os.path.join(work_dir, job_name + '.odb')
        if not os.path.isfile(resolved_path) or os.path.getsize(resolved_path) <= 0:
            log('CAE re-solve did not produce a nonempty ODB')
            return False
        odb = openOdb(path=resolved_path, readOnly=True)
        frame = task01_last_frame(odb, 'CAE re-solve ODB')
        if frame is None:
            return False
        field_names = set(ci(name) for name in frame.fieldOutputs.keys())
        if not check_abaqus_result_fields(field_names) or not check_abaqus_metrics(frame):
            return False
        resolved_response = extract_task01_response(odb, frame)
        if resolved_response is None:
            return False
        return compare_task01_responses(submitted_response, resolved_response)
    except Exception:
        log('CAE re-solve failed')
        log(traceback.format_exc())
        return False
    finally:
        try:
            if 'job' in locals() and ci(job.status) in ('SUBMITTED', 'RUNNING'):
                job.kill()
        except Exception:
            pass
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass
        try:
            if job_name in mdb.jobs:
                del mdb.jobs[job_name]
        except Exception:
            pass
        try:
            os.chdir(old_cwd)
        except Exception:
            pass
        shutil.rmtree(work_dir, ignore_errors=True)

def check_abaqus_result_fields(field_names):
    expected = [ci(x) for x in SPEC.get('expected_result_fields', [])]
    if not expected:
        return True
    missing = [f for f in expected if f not in field_names]
    if missing:
        log('missing result fields: %s from %s' % (missing, sorted(field_names)))
        return False
    return True

def field_value_data(value):
    for attribute in ('dataDouble', 'data'):
        try:
            data = getattr(value, attribute)
            if data is not None:
                return data
        except Exception:
            pass
    raise RuntimeError('field value has no readable numeric data')

def field_has_numeric_data(field):
    try:
        values = field.values
        count = len(values)
        if count < 1:
            return False
        for i in range(count):
            v = values[i]
            try:
                data = field_value_data(v)
            except Exception:
                continue
            values_to_check = flatten_numbers(data)
            if any(math.isfinite(value) and abs(value) > 1.0e-15 for value in values_to_check):
                return True
    except Exception:
        return False
    return False

def check_abaqus_metrics(frame):
    expected = [ci(x) for x in SPEC.get('expected_result_fields', [])]
    for field_name in expected:
        try:
            field = frame.fieldOutputs[field_name]
        except Exception:
            log('cannot read expected field for metrics: ' + field_name)
            return False
        if not field_has_numeric_data(field):
            log('field has no numeric data: ' + field_name)
            return False
    return True

def check_cae():
    global CAE_MODEL_NAME
    openMdb(pathName=CAE_PATH)
    try:
        job_names = [name for name in mdb.jobs.keys() if ci(name) == 'JOB-PLATE']
        if len(job_names) != 1:
            log('CAE must contain exactly one job named Job-Plate')
            return False
        job = mdb.jobs[job_names[0]]
        model = mdb.models[job.model]
        CAE_MODEL_NAME = model.name
    except Exception:
        log('cannot resolve the Job-Plate model from CAE')
        return False
    try:
        meshed_parts = [
            model.parts[name] for name in model.parts.keys()
            if len(model.parts[name].nodes) or len(model.parts[name].elements)
        ]
        meshed_instances = [
            model.rootAssembly.instances[name] for name in model.rootAssembly.instances.keys()
            if len(model.rootAssembly.instances[name].nodes) or len(model.rootAssembly.instances[name].elements)
        ]
    except Exception:
        log('cannot inspect CAE parts or instances')
        return False
    if len(meshed_parts) != 1 or len(meshed_instances) != 1:
        log('CAE must contain exactly one meshed plate part and instance')
        return False
    part = meshed_parts[0]
    try:
        if len(part.nodes) < 2 or len(part.elements) < 1:
            log('mesh too small')
            return False
    except Exception:
        log('cannot inspect mesh')
        return False
    try:
        if set(ci(name) for name in model.steps.keys()) != {'INITIAL', 'STEP-PRESSURE'}:
            log('CAE must contain Initial and exactly one user step, Step-Pressure')
            return False
        for repo_name in ('constraints', 'interactions', 'predefinedFields'):
            if len(getattr(model, repo_name).keys()) != 0:
                log('CAE contains an unauthorized repository object: ' + repo_name)
                return False
    except Exception:
        log('cannot inspect task-specific CAE repositories')
        return False
    ok = (
        check_abaqus_model_rules(model)
        and check_abaqus_geometry(model, part)
        and check_abaqus_materials(model)
        and check_abaqus_analysis_step(model)
        and check_abaqus_boundary_loads(model)
        and check_task01_cae(model, part)
    )
    if ok:
        CAE_MESH_SIGNATURE['instance_name'] = ci(meshed_instances[0].name)
    return ok

def check_odb():
    odb = None
    submitted_response = None
    submitted_ok = False
    try:
        odb = openOdb(path=ODB_PATH, readOnly=True)
        last_frame = task01_last_frame(odb, 'submitted ODB')
        if last_frame is None:
            return False
        field_names = set(ci(name) for name in last_frame.fieldOutputs.keys())
        if not check_abaqus_result_fields(field_names):
            return False
        if not check_abaqus_metrics(last_frame):
            return False
        submitted_response = extract_task01_response(odb, last_frame)
        if submitted_response is None or not check_task01_sidecar(submitted_response):
            return False
        for prefix in [ci(value) for value in RULES.get('abaqus_result_prefixes', [])]:
            matching = [name for name in field_names if name.startswith(prefix)]
            if not matching:
                log('missing task-specific result field prefix: ' + prefix)
                return False
            if not any(field_has_numeric_data(last_frame.fieldOutputs[name]) for name in matching):
                log('task-specific result field has no nonzero numeric data: ' + prefix)
                return False
        try:
            status = ci(getattr(odb.diagnosticData, 'jobStatus', ''))
            if 'ABORT' in status or 'TERMINAT' in status:
                log('result diagnostic failure: ' + status)
                return False
            if status and 'COMPLETED' not in status:
                log('result is not a completed analysis: ' + status)
                return False
        except Exception:
            pass
        submitted_ok = True
    except Exception:
        log(traceback.format_exc())
        return False
    finally:
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass
    if not submitted_ok or submitted_response is None:
        return False
    return resolve_cae_and_compare(submitted_response)

def main():
    ok = False
    try:
        ok = check_cae() and check_odb()
    except Exception:
        log(traceback.format_exc())
        ok = False
    finally:
        try:
            mdb.close()
        except Exception:
            pass
    try:
        with open(RESULT_PATH, 'w') as f:
            f.write('True\n' if ok else 'False\n')
        with open(os.path.join(os.path.dirname(RESULT_PATH), '__open_choice_abaqus_detail.txt'), 'w') as f:
            f.write('\n'.join(DETAILS) + '\n')
    except Exception:
        pass
    print('True' if ok else 'False')

if __name__ == '__main__':
    main()
    '''
    process = None
    try:
        cae_copy = work_dir / 'submitted.cae'
        odb_copy = work_dir / 'submitted.odb'
        metrics_copy = work_dir / 'metrics.json'
        shutil.copy2(cae_path, cae_copy)
        shutil.copy2(odb_path, odb_copy)
        shutil.copy2(root / 'metrics.json', metrics_copy)
        checker_source = checker_source.replace('__SPEC__', repr(TASK_SPEC))
        checker_source = checker_source.replace('__RULES__', repr(MODEL_RULES))
        checker_source = checker_source.replace('__CAE_PATH__', repr(str(cae_copy)))
        checker_source = checker_source.replace('__ODB_PATH__', repr(str(odb_copy)))
        checker_source = checker_source.replace('__METRICS_PATH__', repr(str(metrics_copy)))
        checker_source = checker_source.replace('__RESULT_PATH__', repr(str(result)))
        checker.write_text(checker_source, encoding='utf-8')
        process = subprocess.Popen(
            [ABAQUS_COMMAND, 'cae', 'noGUI=' + str(checker)],
            cwd=str(work_dir),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        try:
            stdout, stderr = process.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            subprocess.run(
                ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                text=True,
                capture_output=True,
                timeout=60,
                shell=False,
            )
            stdout, stderr = process.communicate(timeout=60)
            log('abaqus checker timed out and its process tree was terminated')
            return False
        log('abaqus checker returncode=%s' % process.returncode)
        if stdout:
            log('abaqus stdout tail=' + stdout[-1000:])
        if stderr:
            log('abaqus stderr tail=' + stderr[-1000:])
        detail = work_dir / '__open_choice_abaqus_detail.txt'
        if detail.exists():
            for line in detail.read_text(encoding='utf-8', errors='ignore').splitlines():
                if line.strip():
                    log('abaqus detail=' + line.strip())
        if process.returncode != 0:
            return False
        return result.read_text(encoding='utf-8', errors='ignore').strip() == 'True'
    except Exception as exc:
        log('abaqus checker failed to run: %s' % exc)
        return False
    finally:
        try:
            if process is not None and process.poll() is None:
                subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                    text=True,
                    capture_output=True,
                    timeout=60,
                    shell=False,
                )
        except Exception:
            pass
        shutil.rmtree(work_dir, ignore_errors=True)


def close_mapdl(mapdl):
    if mapdl is not None:
        try:
            mapdl.exit()
        except Exception:
            pass


def _try_get(mapdl, *args):
    try:
        return float(mapdl.get_value(*args))
    except Exception:
        return None


def _safe_run(mapdl, command):
    try:
        out = mapdl.run(command)
        return '' if out is None else str(out)
    except Exception as exc:
        log('command failed %s: %s' % (command, exc))
        return ''


def numbers_from_text(text):
    values = []
    for token in re.findall(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?', text or ''):
        try:
            values.append(float(token.replace('D', 'E').replace('d', 'e')))
        except Exception:
            pass
    return values


def number_requirement_met(values, requirement):
    candidates = requirement if isinstance(requirement, (tuple, list)) else [requirement]
    return any(
        math.isclose(actual, float(expected), rel_tol=2.0e-3, abs_tol=max(1.0e-12, abs(float(expected)) * 1.0e-6))
        for actual in values
        for expected in candidates
    )


def check_ansys_model_rules(mapdl):
    rules = MODEL_RULES
    element_text = _safe_run(mapdl, 'ETLIST,ALL').upper()
    element_any = [str(token).upper() for token in rules.get('ansys_elements_any', [])]
    if element_any and not any(token in element_text for token in element_any):
        log('ANSYS element family mismatch')
        return False
    for token in [str(value).upper() for value in rules.get('ansys_elements_all', [])]:
        if token not in element_text:
            log('missing required ANSYS element family: ' + token)
            return False
    material_text = _safe_run(mapdl, 'MPLIST,ALL')
    material_values = numbers_from_text(material_text)
    for requirement in rules.get('ansys_material_numbers', []):
        if not number_requirement_met(material_values, requirement):
            log('ANSYS material property mismatch: %s' % (requirement,))
            return False
    variants = rules.get('unit_variants', [])
    if variants:
        try:
            rows = [[float(value) for value in row[:3]] for row in mapdl.mesh.nodes]
            cols = list(zip(*rows))
            bb = {'x': (min(cols[0]), max(cols[0])), 'y': (min(cols[1]), max(cols[1])), 'z': (min(cols[2]), max(cols[2]))}
        except Exception:
            bb = None
        if not any(
            geometry_values_match_scale(bb, float(variant['geometry_scale']))
            and all(number_requirement_met(material_values, requirement) for requirement in variant.get('ansys_material_numbers', []))
            for variant in variants
        ):
            log('ANSYS geometry/material unit combination mismatch')
            return False
    load_tokens = [str(token).upper() for token in rules.get('ansys_load_tokens_any', [])]
    if load_tokens:
        load_text = '\n'.join([
            _safe_run(mapdl, 'DLIST,ALL'),
            _safe_run(mapdl, 'FLIST,ALL'),
            _safe_run(mapdl, 'SFLIST,ALL'),
            _safe_run(mapdl, 'BFLIST,ALL'),
            _safe_run(mapdl, 'BFELIST,ALL'),
            _safe_run(mapdl, 'SFELIST,ALL'),
        ]).upper()
        if not any(token in load_text for token in load_tokens):
            log('ANSYS load type mismatch')
            return False
    return True


def geometry_values_match_scale(bb, scale):
    if not bb:
        return False
    span_hints = TASK_SPEC.get('span_hint') or {}
    bounds = MODEL_RULES.get('bounds') or TASK_SPEC.get('bounds_hint') or {}
    for axis, target in span_hints.items():
        if axis == 'min_span' or axis not in bb:
            continue
        expected = float(target) * scale
        observed = bb[axis][1] - bb[axis][0]
        tolerance = max(1.0e-5, abs(expected) * 0.02)
        if abs(observed - expected) > tolerance:
            return False
    for axis, target in bounds.items():
        if axis == 'min_span' or axis not in bb:
            continue
        expected_lo, expected_hi = [float(value) * scale for value in target]
        observed_lo, observed_hi = bb[axis]
        tolerance = max(1.0e-5, abs(expected_hi - expected_lo) * 0.02)
        if abs(observed_lo - expected_lo) > tolerance or abs(observed_hi - expected_hi) > tolerance:
            return False
    min_span = bounds.get('min_span') or span_hints.get('min_span')
    if min_span is not None and max(value[1] - value[0] for value in bb.values()) < float(min_span) * scale * 0.98:
        return False
    return True

def check_geometry_values(bb):
    for scale in MODEL_RULES.get('geometry_scales', [1.0]):
        if geometry_values_match_scale(bb, float(scale)):
            return True
    log('geometry bounds do not match the task')
    return False

def check_ansys_node_shape_rules(rows):
    index = {'x': 0, 'y': 1, 'z': 2}
    hole = MODEL_RULES.get('circular_hole')
    if hole:
        axes = [index[value] for value in hole.get('axes', ['x', 'y'])]
        center = [float(value) for value in hole['center']]
        radius = float(hole['radius'])
        tolerance = max(0.25, radius * 0.12)
        distances = [
            math.sqrt(sum((point[axis] - center[position]) ** 2 for position, axis in enumerate(axes)))
            for point in rows
        ]
        if sum(abs(value - radius) <= tolerance for value in distances) < int(hole.get('min_nodes', 4)):
            log('circular-hole boundary nodes not found')
            return False
        if any(value < radius - tolerance for value in distances):
            log('mesh occupies the required circular hole')
            return False
    cylinder = MODEL_RULES.get('solid_cylinder')
    if cylinder:
        axial = index[cylinder.get('axis', 'y')]
        transverse = [value for value in (0, 1, 2) if value != axial]
        center = [float(value) for value in cylinder.get('center', [0.0, 0.0])]
        radius = float(cylinder['radius'])
        tolerance = max(0.2, radius * 0.08)
        distances = [
            math.sqrt(sum((point[axis] - center[position]) ** 2 for position, axis in enumerate(transverse)))
            for point in rows
        ]
        if max(distances or [0.0]) > radius + tolerance:
            log('shaft cross-section is not circular')
            return False
        if sum(abs(value - radius) <= tolerance for value in distances) < int(cylinder.get('min_nodes', 6)):
            log('circular shaft boundary nodes not found')
            return False
    sphere = MODEL_RULES.get('sphere_surface')
    if sphere:
        center = [float(value) for value in sphere['center']]
        radius = float(sphere['radius'])
        tolerance = max(0.25, radius * 0.08)
        distances = [math.sqrt(sum((point[i] - center[i]) ** 2 for i in range(3))) for point in rows]
        if sum(abs(value - radius) <= tolerance for value in distances) < int(sphere.get('min_nodes', 8)):
            log('spherical contact body surface nodes not found')
            return False
    return True


def check_ansys_geometry(mapdl):
    try:
        nodes = mapdl.mesh.nodes
        if nodes is None or len(nodes) < 2:
            log('no nodes available')
            return False
        rows = [[float(c) for c in row[:3]] for row in nodes]
        cols = list(zip(*rows))
        bb = {'x': (min(cols[0]), max(cols[0])), 'y': (min(cols[1]), max(cols[1]))}
        if len(cols) > 2:
            bb['z'] = (min(cols[2]), max(cols[2]))
        return check_geometry_values(bb) and check_ansys_node_shape_rules(rows)
    except Exception as exc:
        log('geometry check failed: %s' % exc)
        return False


def check_ansys_materials(mapdl):
    text = _safe_run(mapdl, 'MPLIST,ALL')
    if text.strip() and 'NO MATERIAL' not in text.upper() and 'ERROR' not in text.upper():
        return True
    try:
        count = _try_get(mapdl, 'MAT', 0, 'COUNT')
        return count is not None and count >= 1
    except Exception:
        return False


def check_ansys_boundary_loads(mapdl):
    kind = TASK_SPEC.get('analysis_kind', '')
    d_text = _safe_run(mapdl, 'DLIST,ALL')
    has_bc = bool(d_text.strip()) and 'NO ' not in d_text.upper()
    if not has_bc:
        log('no boundary-condition evidence found')
        return False
    if kind == 'modal':
        return True
    load_text = '\n'.join([
        _safe_run(mapdl, 'FLIST,ALL'),
        _safe_run(mapdl, 'SFLIST,ALL'),
        _safe_run(mapdl, 'BFLIST,ALL'),
        _safe_run(mapdl, 'BFELIST,ALL'),
        _safe_run(mapdl, 'SFELIST,ALL'),
        d_text if kind in ('thermal', 'thermal_structural') else '',
    ])
    if not load_text.strip() or ('NO ' in load_text.upper() and not any(ch.isdigit() for ch in load_text)):
        log('no load/predefined evidence found')
        return False
    return True


def check_ansys_analysis_step(mapdl, result_path):
    kind = TASK_SPEC.get('analysis_kind', '')
    suffix = result_path.suffix.lower()
    if kind == 'thermal' and suffix != '.rth':
        log('thermal task expected thermal result artifact')
        return False
    return True


def check_ansys_result_fields(mapdl):
    # MAPDL does not expose a portable field-name registry like ODB; use metric
    # extraction as the field/readability check for parity with Abaqus fields.
    return check_ansys_metrics(mapdl)


def check_ansys_metrics(mapdl):
    metrics = ' '.join(TASK_SPEC.get('metrics', [])).lower()
    checked = 0
    if any(k in metrics for k in ['displacement', 'deflection', 'twist']):
        val = _try_get(mapdl, 'NODE', 0, 'U', 'SUM')
        if val is None:
            try:
                mapdl.run('NSORT,U,SUM,0,1,ALL')
                val = float(mapdl.get_value('SORT', 0, 'MAX'))
            except Exception:
                val = None
        if val is None or not (-1.0e6 <= val <= 1.0e6):
            log('invalid displacement metric')
            return False
        checked += 1
    if any(k in metrics for k in ['stress', 'mises', 'contact', 'reaction']):
        val = None
        try:
            mapdl.run('NSORT,S,EQV,0,1,ALL')
            val = float(mapdl.get_value('SORT', 0, 'MAX'))
        except Exception:
            pass
        if val is None or abs(val) <= 1.0e-12 or abs(val) > 1.0e9:
            log('invalid stress/contact metric')
            return False
        checked += 1
    if any(k in metrics for k in ['temperature', 'thermal', 'heat']):
        val = None
        for comp in ('TEMP', 'T'):
            try:
                mapdl.run('NSORT,%s,,0,1,ALL' % comp)
                val = float(mapdl.get_value('SORT', 0, 'MAX'))
                break
            except Exception:
                pass
        if val is None or not (-1000.0 <= val <= 5000.0):
            log('invalid temperature metric')
            return False
        checked += 1
    if any(k in metrics for k in ['frequency', 'freq']):
        val = None
        try:
            val = float(mapdl.get_value('MODE', 1, 'FREQ'))
        except Exception:
            pass
        if val is None or val <= 0.0:
            log('invalid modal metric')
            return False
        checked += 1
    if any(k in metrics for k in ['buckling', 'factor']):
        val = None
        try:
            val = float(mapdl.get_value('MODE', 1, 'FREQ'))
        except Exception:
            pass
        if val is None or not math.isfinite(val) or abs(val) <= 1.0e-12:
            log('invalid buckling eigenvalue metric')
            return False
        checked += 1
    return checked > 0 or bool(TASK_SPEC.get('expected_result_fields'))


def check_ansys_with_mapdl(root, model_path, result_path):
    work_dir = Path(tempfile.mkdtemp(prefix='__task01_ansys_eval_', dir=str(root)))
    input_path = work_dir / 'check.inp'
    output_path = work_dir / 'check.out'
    submitted_model_path = work_dir / 'submitted_model.db'
    submitted_result_path = work_dir / 'submitted_result.rst'
    values_path = work_dir / 'values.txt'
    node_audit_path = work_dir / 'nodes.txt'
    node_force_audit_path = work_dir / 'node_forces.txt'
    element_audit_path = work_dir / 'elements.txt'
    element_connectivity_audit_path = work_dir / 'element_connectivity.txt'
    load_audit_path = work_dir / 'loads.cdb'
    recheck_field_path = work_dir / 'recheck_fields.txt'
    result_field_path = work_dir / 'result_fields.txt'
    recheck_stress_path = work_dir / 'recheck_stress.txt'
    result_stress_path = work_dir / 'result_stress.txt'
    job_name = 'check'

    try:
        rst_node_labels, rst_element_labels, rst_set_count = read_ansys_rst_mesh_labels(result_path)
    except Exception as exc:
        log('cannot read submitted ANSYS result mesh: %s' % exc)
        shutil.rmtree(work_dir, ignore_errors=True)
        return False
    if (
        rst_set_count < 1
        or len(rst_node_labels) != len(set(rst_node_labels))
        or len(rst_element_labels) != len(set(rst_element_labels))
    ):
        log('submitted ANSYS result mesh has invalid labels or no result set')
        shutil.rmtree(work_dir, ignore_errors=True)
        return False

    def apdl_path(path, with_suffix=True):
        value = path if with_suffix else path.with_suffix('')
        return str(value).replace("'", "''")

    def cdb_command_records(path):
        records = []
        text = path.read_text(encoding='utf-8', errors='ignore')
        for physical_line in text.splitlines():
            for record in physical_line.split('$'):
                record = record.strip()
                if not record or record.startswith('!') or record.upper().startswith('/COM'):
                    continue
                record = record.split('!', 1)[0].strip()
                if not record:
                    continue
                fields = [field.strip() for field in record.split(',')]
                token = re.split(r'\s+', fields[0], maxsplit=1)[0].upper()
                if token:
                    records.append((token, fields[1:]))
        return records

    def cdb_number_is_zero(raw):
        try:
            return abs(float(raw.replace('D', 'E').replace('d', 'e'))) <= 1.0e-14
        except Exception:
            return False

    def unauthorized_cdb_loads(path):
        always_forbidden = {
            'SF', 'SFE', 'SFA', 'SFL', 'SFK', 'SFGRAD', 'SFCONTROL',
            'BF', 'BFE', 'BFA', 'BFL', 'BFK', 'BFV', 'TUNIF',
            'FJ', 'FK', 'SLOAD',
        }
        zero_vector_defaults = {
            'ACEL', 'OMEGA', 'DOMEGA', 'CGOMEGA', 'CGOMGA', 'DCGOMG',
        }
        forbidden = []
        for token, args in cdb_command_records(path):
            if token in always_forbidden:
                forbidden.append(token)
            elif token == 'BFUNIF':
                safe = (
                    len(args) >= 2
                    and args[0].strip().upper() == 'TEMP'
                    and (
                        args[1].strip().upper() == '_TINY'
                        or cdb_number_is_zero(args[1])
                    )
                )
                if not safe:
                    forbidden.append(token)
            elif token == 'IRLF':
                try:
                    key = float(args[0].replace('D', 'E').replace('d', 'e'))
                except Exception:
                    key = None
                if key not in (0.0, -1.0):
                    forbidden.append(token)
            elif token in zero_vector_defaults:
                values = [value for value in args if value.strip()]
                if not values or not all(cdb_number_is_zero(value) for value in values):
                    forbidden.append(token)
            elif token in {'CMACEL', 'CMOMEGA', 'CMDOMEGA'}:
                forbidden.append(token)
        return sorted(set(forbidden))

    def numeric_rows(path, width):
        rows = []
        for line in path.read_text(encoding='utf-8', errors='ignore').splitlines():
            fields = [field.strip() for field in line.split(',') if field.strip()]
            if not fields:
                continue
            try:
                row = [float(field.replace('D', 'E').replace('d', 'e')) for field in fields]
            except Exception:
                continue
            if len(row) != width or not all(math.isfinite(value) for value in row):
                raise ValueError('malformed numeric audit row')
            rows.append(row)
        return rows

    def coordinate_matches(actual, expected, tolerance=1.0e-6):
        return all(abs(float(actual[index]) - float(expected[index])) <= tolerance for index in range(len(expected)))

    apdl = r'''/BATCH
/FILNAME,check,1
RESUME,'__MODEL_BASE__','db'
/FILNAME,check,1
/PREP7
CSYS,0
ALLSEL,ALL
CDWRITE,LOAD,'__LOAD_BASE__','cdb',,,,UNBLOCKED
*GET,node_count,NODE,0,COUNT
*GET,element_count,ELEM,0,COUNT
*GET,x_min,NODE,0,MNLOC,X
*GET,x_max,NODE,0,MXLOC,X
*GET,y_min,NODE,0,MNLOC,Y
*GET,y_max,NODE,0,MXLOC,Y
*GET,z_min,NODE,0,MNLOC,Z
*GET,z_max,NODE,0,MXLOC,Z
*GET,db_analysis_type,ACTIVE,0,ANTY
*GET,cp_count,CP,0,NUM
*GET,ce_count,CE,0,NUM
*GET,current_element,ELEM,0,NUM,MIN
bad_enam=0
bad_k3=0
bad_k1=0
bad_live=0
bad_mat=0
n182=0
n183=0
*CFOPEN,'__ELEMENT_BASE__','txt'
*DO,loop_index,1,element_count
*GET,element_type,ELEM,current_element,ATTR,TYPE
*GET,element_material,ELEM,current_element,ATTR,MAT
*GET,element_name,ETYP,element_type,ATTR,ENAM
*GET,element_k1,ETYP,element_type,ATTR,KOP1
*GET,element_k3,ETYP,element_type,ATTR,KOP3
*GET,element_live,ELEM,current_element,ATTR,LIVE
*GET,element_ex,EX,element_material,TEMP,0
*GET,element_nu,PRXY,element_material,TEMP,0
*GET,element_nuxy,NUXY,element_material,TEMP,0
element_tb_ex=0
element_tb_nu=0
*GET,element_tb_ex,ELASTIC,element_material,TEMP,0,CONST,1,ISOT
*GET,element_tb_nu,ELASTIC,element_material,TEMP,0,CONST,2,ISOT
*GET,en1,ELEM,current_element,NODE,1
*GET,en2,ELEM,current_element,NODE,2
*GET,en3,ELEM,current_element,NODE,3
*GET,en4,ELEM,current_element,NODE,4
en5=0
en6=0
en7=0
en8=0
element_name_ok=0
*IF,element_name,EQ,182,THEN
element_name_ok=1
n182=n182+1
*ENDIF
*IF,element_name,EQ,183,THEN
element_name_ok=1
n183=n183+1
*GET,en5,ELEM,current_element,NODE,5
*GET,en6,ELEM,current_element,NODE,6
*GET,en7,ELEM,current_element,NODE,7
*GET,en8,ELEM,current_element,NODE,8
*IF,element_k1,NE,0,THEN
bad_k1=bad_k1+1
*ENDIF
*ENDIF
*IF,element_name_ok,NE,1,THEN
bad_enam=bad_enam+1
*ENDIF
*IF,element_k3,NE,1,THEN
bad_k3=bad_k3+1
*ENDIF
*IF,element_live,NE,1,THEN
bad_live=bad_live+1
*ENDIF
material_bad=0
material_mp_ok=0
*IF,ABS(element_ex-210000),LE,0.21,THEN
*IF,ABS(element_nu-0.3),LE,3E-7,THEN
material_mp_ok=1
*ENDIF
*IF,ABS(element_nuxy-0.3),LE,3E-7,THEN
material_mp_ok=1
*ENDIF
*ENDIF
material_tb_ok=1
*IF,ABS(element_tb_ex-210000),GT,0.21,THEN
material_tb_ok=0
*ENDIF
*IF,ABS(element_tb_nu-0.3),GT,3E-7,THEN
material_tb_ok=0
*ENDIF
*IF,material_mp_ok+material_tb_ok,LT,1,THEN
material_bad=1
*ENDIF
bad_mat=bad_mat+material_bad
*VWRITE,current_element,element_name,element_k1,element_k3,element_live,element_material
(F16.0,5(',',F16.0))
current_element=ELNEXT(current_element)
*ENDDO
*CFCLOS
ALLSEL,ALL
*GET,current_element,ELEM,0,NUM,MIN
*CFOPEN,'__ELEMENT_CONNECTIVITY_BASE__','txt'
*DO,loop_index,1,element_count
*GET,element_type,ELEM,current_element,ATTR,TYPE
*GET,element_name,ETYP,element_type,ATTR,ENAM
*GET,en1,ELEM,current_element,NODE,1
*GET,en2,ELEM,current_element,NODE,2
*GET,en3,ELEM,current_element,NODE,3
*GET,en4,ELEM,current_element,NODE,4
en5=0
en6=0
en7=0
en8=0
*IF,element_name,EQ,183,THEN
*GET,en5,ELEM,current_element,NODE,5
*GET,en6,ELEM,current_element,NODE,6
*GET,en7,ELEM,current_element,NODE,7
*GET,en8,ELEM,current_element,NODE,8
*ENDIF
*VWRITE,current_element,en1,en2,en3,en4,en5,en6,en7,en8
(F13.0,8(',',F13.0))
current_element=ELNEXT(current_element)
*ENDDO
*CFCLOS
ALLSEL,ALL
NSLE,S
*GET,attached_node_count,NODE,0,COUNT
ALLSEL,ALL
*GET,axis_type,COMP,AXIS,TYPE
*GET,outer_type,COMP,OUTER,TYPE
*GET,top_type,COMP,TOP,TYPE
CMSEL,S,AXIS
*GET,axis_count,NODE,0,COUNT
*GET,axis_x_min,NODE,0,MNLOC,X
*GET,axis_x_max,NODE,0,MXLOC,X
*GET,axis_y_min,NODE,0,MNLOC,Y
*GET,axis_y_max,NODE,0,MXLOC,Y
CMSEL,S,OUTER
*GET,outer_count,NODE,0,COUNT
*GET,outer_x_min,NODE,0,MNLOC,X
*GET,outer_x_max,NODE,0,MXLOC,X
*GET,outer_y_min,NODE,0,MNLOC,Y
*GET,outer_y_max,NODE,0,MXLOC,Y
CMSEL,S,TOP
*GET,top_count,NODE,0,COUNT
*GET,top_x_min,NODE,0,MNLOC,X
*GET,top_x_max,NODE,0,MXLOC,X
*GET,top_y_min,NODE,0,MNLOC,Y
*GET,top_y_max,NODE,0,MXLOC,Y
SELTOL,1E-6
ALLSEL,ALL
CMSEL,S,AXIS
NSEL,U,LOC,X,0
*GET,axis_extra,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,LOC,X,0
CMSEL,U,AXIS
*GET,axis_missing,NODE,0,COUNT
ALLSEL,ALL
CMSEL,S,OUTER
NSEL,U,LOC,X,50
*GET,outer_extra,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,LOC,X,50
CMSEL,U,OUTER
*GET,outer_missing,NODE,0,COUNT
ALLSEL,ALL
CMSEL,S,TOP
NSEL,U,LOC,Y,1
*GET,top_extra,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,LOC,Y,1
CMSEL,U,TOP
*GET,top_missing,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,LOC,X,0
*GET,axis_geometry_count,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,LOC,X,50
*GET,outer_geometry_count,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,D,UX
*GET,ux_constraint_count,NODE,0,COUNT
ALLSEL,ALL
NSEL,S,D,UY
*GET,uy_constraint_count,NODE,0,COUNT
ALLSEL,ALL
CMSEL,S,AXIS
NSEL,R,D,UX
*GET,axis_ux_count,NODE,0,COUNT
CMSEL,S,AXIS
NSEL,R,D,UY
*GET,axis_uy_count,NODE,0,COUNT
CMSEL,S,OUTER
NSEL,R,D,UX
*GET,outer_ux_count,NODE,0,COUNT
CMSEL,S,OUTER
NSEL,R,D,UY
*GET,outer_uy_count,NODE,0,COUNT
CMSEL,S,AXIS
*GET,current_node,NODE,0,NUM,MIN
axis_ux_value_abs=0
*DO,loop_index,1,axis_count
*GET,bc_value,NODE,current_node,D,UX
axis_ux_value_abs=axis_ux_value_abs+ABS(bc_value)
current_node=NDNEXT(current_node)
*ENDDO
CMSEL,S,OUTER
*GET,current_node,NODE,0,NUM,MIN
outer_ux_value_abs=0
outer_uy_value_abs=0
*DO,loop_index,1,outer_count
*GET,bc_value,NODE,current_node,D,UX
outer_ux_value_abs=outer_ux_value_abs+ABS(bc_value)
*GET,bc_value,NODE,current_node,D,UY
outer_uy_value_abs=outer_uy_value_abs+ABS(bc_value)
current_node=NDNEXT(current_node)
*ENDDO
ALLSEL,ALL
*GET,current_node,NODE,0,NUM,MIN
total_fy=0
nonzero_load_count=0
top_loop_count=0
all_fx_abs=0
all_fz_abs=0
off_top_fy_abs=0
off_top_fy_count=0
*CFOPEN,'__NODE_BASE__','txt'
*DO,loop_index,1,node_count
*GET,node_fx,NODE,current_node,F,FX
*GET,node_fy,NODE,current_node,F,FY
*GET,node_fz,NODE,current_node,F,FZ
*GET,node_radius,NODE,current_node,LOC,X
*GET,node_y,NODE,current_node,LOC,Y
*GET,node_z,NODE,current_node,LOC,Z
*GET,node_ang_xy,NODE,current_node,ANG,XY
*GET,node_ang_yz,NODE,current_node,ANG,YZ
*GET,node_ang_zx,NODE,current_node,ANG,ZX
*VWRITE,current_node,node_radius,node_y,node_z,node_ang_xy,node_ang_yz,node_ang_zx
(F16.0,6(',',E16.8))
all_fx_abs=all_fx_abs+ABS(node_fx)
all_fz_abs=all_fz_abs+ABS(node_fz)
*IF,ABS(node_y-1),LE,1E-6,THEN
top_loop_count=top_loop_count+1
*IF,ABS(node_fy),GT,1E-12,THEN
nonzero_load_count=nonzero_load_count+1
*ENDIF
total_fy=total_fy+node_fy
*ELSE
off_top_fy_abs=off_top_fy_abs+ABS(node_fy)
*IF,ABS(node_fy),GT,1E-12,THEN
off_top_fy_count=off_top_fy_count+1
*ENDIF
*ENDIF
current_node=NDNEXT(current_node)
*ENDDO
*CFCLOS
ALLSEL,ALL
*GET,current_node,NODE,0,NUM,MIN
*CFOPEN,'__NODE_FORCE_BASE__','txt'
*DO,loop_index,1,node_count
*GET,node_fx,NODE,current_node,F,FX
*GET,node_fy,NODE,current_node,F,FY
*GET,node_fz,NODE,current_node,F,FZ
*VWRITE,current_node,node_fx,node_fy,node_fz
(F16.0,3(',',E24.16))
current_node=NDNEXT(current_node)
*ENDDO
*CFCLOS
ALLSEL,ALL
FINISH
/POST1
CSYS,0
FILE,'__RESULT_BASE__','rst'
SET,LAST
RSYS,0
*GET,result_analysis_type,ACTIVE,0,ANTY
*GET,result_load_step,ACTIVE,0,SET,LSTP
*GET,result_set_count,ACTIVE,0,SET,NSET
NSEL,S,LOC,X,0
NSEL,R,LOC,Y,1
*GET,center_count,NODE,0,COUNT
*GET,center_node,NODE,0,NUM,MIN
*GET,center_u2,NODE,center_node,U,Y
ALLSEL,ALL
/GRAPHICS,FULL
NSORT,S,EQV,0,1,ALL
*GET,max_mises,SORT,0,MAX
CMSEL,S,OUTER
*GET,current_node,NODE,0,NUM,MIN
support_fy=0
*DO,loop_index,1,outer_count
*GET,node_rf,NODE,current_node,RF,FY
support_fy=support_fy+node_rf
current_node=NDNEXT(current_node)
*ENDDO
ALLSEL,ALL
*GET,current_node,NODE,0,NUM,MIN
*CFOPEN,'__RESULT_FIELD_BASE__','txt'
*DO,loop_index,1,node_count
field_ux=0
field_uy=0
field_rfx=0
field_rfy=0
field_seqv=0
*GET,field_ux,NODE,current_node,U,X
*GET,field_uy,NODE,current_node,U,Y
*GET,field_rfx,NODE,current_node,RF,FX
*GET,field_rfy,NODE,current_node,RF,FY
*GET,field_seqv,NODE,current_node,S,EQV
*VWRITE,current_node,field_ux,field_uy,field_rfx,field_rfy,field_seqv
(F16.0,5(',',E20.12))
current_node=NDNEXT(current_node)
*ENDDO
*CFCLOS
ALLSEL,ALL
*GET,current_node,NODE,0,NUM,MIN
*CFOPEN,'__RESULT_STRESS_BASE__','txt'
*DO,loop_index,1,node_count
field_sx=0
field_sy=0
field_sz=0
field_sxy=0
*GET,field_sx,NODE,current_node,S,X
*GET,field_sy,NODE,current_node,S,Y
*GET,field_sz,NODE,current_node,S,Z
*GET,field_sxy,NODE,current_node,S,XY
*VWRITE,current_node,field_sx,field_sy,field_sz,field_sxy
(F16.0,4(',',E24.16))
current_node=NDNEXT(current_node)
*ENDDO
*CFCLOS
FINISH
/SOLU
ANTYPE,STATIC,NEW
OUTRES,ALL,ALL
SOLVE
FINISH
/POST1
CSYS,0
FILE,'__RECHECK_BASE__','rst'
SET,LAST
RSYS,0
*GET,recheck_analysis_type,ACTIVE,0,ANTY
*GET,recheck_load_step,ACTIVE,0,SET,LSTP
NSEL,S,LOC,X,0
NSEL,R,LOC,Y,1
*GET,recheck_center_node,NODE,0,NUM,MIN
*GET,recheck_center_u2,NODE,recheck_center_node,U,Y
ALLSEL,ALL
/GRAPHICS,FULL
NSORT,S,EQV,0,1,ALL
*GET,recheck_max_mises,SORT,0,MAX
CMSEL,S,OUTER
*GET,current_node,NODE,0,NUM,MIN
recheck_support_fy=0
*DO,loop_index,1,outer_count
*GET,node_rf,NODE,current_node,RF,FY
recheck_support_fy=recheck_support_fy+node_rf
current_node=NDNEXT(current_node)
*ENDDO
ALLSEL,ALL
*GET,current_node,NODE,0,NUM,MIN
*CFOPEN,'__RECHECK_FIELD_BASE__','txt'
*DO,loop_index,1,node_count
field_ux=0
field_uy=0
field_rfx=0
field_rfy=0
field_seqv=0
*GET,field_ux,NODE,current_node,U,X
*GET,field_uy,NODE,current_node,U,Y
*GET,field_rfx,NODE,current_node,RF,FX
*GET,field_rfy,NODE,current_node,RF,FY
*GET,field_seqv,NODE,current_node,S,EQV
*VWRITE,current_node,field_ux,field_uy,field_rfx,field_rfy,field_seqv
(F16.0,5(',',E20.12))
current_node=NDNEXT(current_node)
*ENDDO
*CFCLOS
ALLSEL,ALL
*GET,current_node,NODE,0,NUM,MIN
*CFOPEN,'__RECHECK_STRESS_BASE__','txt'
*DO,loop_index,1,node_count
field_sx=0
field_sy=0
field_sz=0
field_sxy=0
*GET,field_sx,NODE,current_node,S,X
*GET,field_sy,NODE,current_node,S,Y
*GET,field_sz,NODE,current_node,S,Z
*GET,field_sxy,NODE,current_node,S,XY
*VWRITE,current_node,field_sx,field_sy,field_sz,field_sxy
(F16.0,4(',',E24.16))
current_node=NDNEXT(current_node)
*ENDDO
*CFCLOS
*CFOPEN,'__VALUES_BASE__','txt'
*VWRITE,node_count
('node_count=',E24.16)
*VWRITE,element_count
('element_count=',E24.16)
*VWRITE,x_min
('x_min=',E24.16)
*VWRITE,x_max
('x_max=',E24.16)
*VWRITE,y_min
('y_min=',E24.16)
*VWRITE,y_max
('y_max=',E24.16)
*VWRITE,z_min
('z_min=',E24.16)
*VWRITE,z_max
('z_max=',E24.16)
*VWRITE,db_analysis_type
('db_analysis_type=',E24.16)
*VWRITE,cp_count
('cp_count=',E24.16)
*VWRITE,ce_count
('ce_count=',E24.16)
*VWRITE,bad_enam
('bad_enam=',E24.16)
*VWRITE,bad_k3
('bad_k3=',E24.16)
*VWRITE,bad_k1
('bad_k1=',E24.16)
*VWRITE,bad_live
('bad_live=',E24.16)
*VWRITE,bad_mat
('bad_mat=',E24.16)
*VWRITE,n182
('n182=',E24.16)
*VWRITE,n183
('n183=',E24.16)
*VWRITE,attached_node_count
('attached_node_count=',E24.16)
*VWRITE,axis_type
('axis_type=',E24.16)
*VWRITE,outer_type
('outer_type=',E24.16)
*VWRITE,top_type
('top_type=',E24.16)
*VWRITE,axis_extra
('axis_extra=',E24.16)
*VWRITE,axis_missing
('axis_missing=',E24.16)
*VWRITE,outer_extra
('outer_extra=',E24.16)
*VWRITE,outer_missing
('outer_missing=',E24.16)
*VWRITE,top_extra
('top_extra=',E24.16)
*VWRITE,top_missing
('top_missing=',E24.16)
*VWRITE,axis_count
('axis_count=',E24.16)
*VWRITE,outer_count
('outer_count=',E24.16)
*VWRITE,top_count
('top_count=',E24.16)
*VWRITE,axis_x_min
('axis_x_min=',E24.16)
*VWRITE,axis_x_max
('axis_x_max=',E24.16)
*VWRITE,axis_y_min
('axis_y_min=',E24.16)
*VWRITE,axis_y_max
('axis_y_max=',E24.16)
*VWRITE,outer_x_min
('outer_x_min=',E24.16)
*VWRITE,outer_x_max
('outer_x_max=',E24.16)
*VWRITE,outer_y_min
('outer_y_min=',E24.16)
*VWRITE,outer_y_max
('outer_y_max=',E24.16)
*VWRITE,top_x_min
('top_x_min=',E24.16)
*VWRITE,top_x_max
('top_x_max=',E24.16)
*VWRITE,top_y_min
('top_y_min=',E24.16)
*VWRITE,top_y_max
('top_y_max=',E24.16)
*VWRITE,axis_geometry_count
('axis_geometry_count=',E24.16)
*VWRITE,outer_geometry_count
('outer_geometry_count=',E24.16)
*VWRITE,ux_constraint_count
('ux_constraint_count=',E24.16)
*VWRITE,uy_constraint_count
('uy_constraint_count=',E24.16)
*VWRITE,axis_ux_count
('axis_ux_count=',E24.16)
*VWRITE,axis_uy_count
('axis_uy_count=',E24.16)
*VWRITE,outer_ux_count
('outer_ux_count=',E24.16)
*VWRITE,outer_uy_count
('outer_uy_count=',E24.16)
*VWRITE,axis_ux_value_abs
('axis_ux_value_abs=',E24.16)
*VWRITE,outer_ux_value_abs
('outer_ux_value_abs=',E24.16)
*VWRITE,outer_uy_value_abs
('outer_uy_value_abs=',E24.16)
*VWRITE,nonzero_load_count
('nonzero_load_count=',E24.16)
*VWRITE,top_loop_count
('top_loop_count=',E24.16)
*VWRITE,all_fx_abs
('all_fx_abs=',E24.16)
*VWRITE,all_fz_abs
('all_fz_abs=',E24.16)
*VWRITE,off_top_fy_abs
('off_top_fy_abs=',E24.16)
*VWRITE,off_top_fy_count
('off_top_fy_count=',E24.16)
*VWRITE,total_fy
('total_fy=',E24.16)
*VWRITE,recheck_analysis_type
('recheck_analysis_type=',E24.16)
*VWRITE,recheck_load_step
('recheck_load_step=',E24.16)
*VWRITE,recheck_center_u2
('recheck_center_u2=',E24.16)
*VWRITE,recheck_max_mises
('recheck_max_mises=',E24.16)
*VWRITE,recheck_support_fy
('recheck_support_fy=',E24.16)
*VWRITE,result_analysis_type
('result_analysis_type=',E24.16)
*VWRITE,result_load_step
('result_load_step=',E24.16)
*VWRITE,result_set_count
('result_set_count=',E24.16)
*VWRITE,center_count
('center_count=',E24.16)
*VWRITE,center_u2
('center_u2=',E24.16)
*VWRITE,max_mises
('max_mises=',E24.16)
*VWRITE,support_fy
('support_fy=',E24.16)
*CFCLOS
FINISH
/EXIT,NOSAVE
'''
    apdl = apdl.replace('__MODEL_BASE__', 'submitted_model')
    apdl = apdl.replace('__RESULT_BASE__', 'submitted_result')
    apdl = apdl.replace('__RECHECK_BASE__', apdl_path(work_dir / job_name, False))
    apdl = apdl.replace('__VALUES_BASE__', apdl_path(values_path, False))
    apdl = apdl.replace('__NODE_BASE__', apdl_path(node_audit_path, False))
    apdl = apdl.replace('__NODE_FORCE_BASE__', apdl_path(node_force_audit_path, False))
    apdl = apdl.replace('__ELEMENT_BASE__', apdl_path(element_audit_path, False))
    apdl = apdl.replace('__ELEMENT_CONNECTIVITY_BASE__', apdl_path(element_connectivity_audit_path, False))
    apdl = apdl.replace('__LOAD_BASE__', apdl_path(load_audit_path, False))
    apdl = apdl.replace('__RECHECK_FIELD_BASE__', apdl_path(recheck_field_path, False))
    apdl = apdl.replace('__RESULT_FIELD_BASE__', apdl_path(result_field_path, False))
    apdl = apdl.replace('__RECHECK_STRESS_BASE__', apdl_path(recheck_stress_path, False))
    apdl = apdl.replace('__RESULT_STRESS_BASE__', apdl_path(result_stress_path, False))
    try:
        stale_paths = {
            input_path, output_path, values_path, node_audit_path,
            node_force_audit_path, element_audit_path,
            element_connectivity_audit_path, load_audit_path,
            recheck_field_path, result_field_path,
            recheck_stress_path, result_stress_path,
        }
        stale_paths.update(work_dir.glob(job_name + '*'))
        for stale in stale_paths:
            try:
                if stale.is_file():
                    stale.unlink()
            except Exception:
                pass
        shutil.copy2(model_path, submitted_model_path)
        shutil.copy2(result_path, submitted_result_path)
        input_path.write_text(apdl, encoding='ascii')
        completed = subprocess.run(
            [
                ANSYS_EXEC,
                '-b',
                '-np',
                '1',
                '-j',
                job_name,
                '-dir',
                str(work_dir),
                '-i',
                str(input_path),
                '-o',
                str(output_path),
            ],
            cwd=str(work_dir),
            text=True,
            capture_output=True,
            timeout=900,
            shell=False,
        )
        log('ANSYS native checker returncode=%s' % completed.returncode)
        if completed.returncode != 0 or not is_nonempty(values_path):
            log('ANSYS native checker did not produce values')
            return False
        output_text = output_path.read_text(encoding='utf-8', errors='ignore')
        if re.search(r'\*\*\*\s+ERROR', output_text, re.I):
            log('ANSYS native checker reported an error')
            return False
        if not all(is_nonempty(path) for path in (
            load_audit_path, node_audit_path, node_force_audit_path,
            element_audit_path, element_connectivity_audit_path,
            recheck_field_path, result_field_path,
            recheck_stress_path, result_stress_path,
        )):
            log('ANSYS model/load audit files were not produced')
            return False
        present_forbidden = unauthorized_cdb_loads(load_audit_path)
        if present_forbidden:
            log('ANSYS model contains unauthorized load commands: %s' % present_forbidden)
            return False
        values = {}
        for line in values_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            if '=' not in line:
                continue
            key, raw = line.split('=', 1)
            try:
                values[key.strip()] = float(raw.strip().replace('D', 'E').replace('d', 'e'))
            except Exception:
                pass
        required = {
            'node_count', 'element_count', 'x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max',
            'db_analysis_type', 'cp_count', 'ce_count',
            'bad_enam', 'bad_k3', 'bad_k1', 'bad_live', 'bad_mat', 'n182', 'n183',
            'attached_node_count',
            'axis_type', 'outer_type', 'top_type',
            'axis_extra', 'axis_missing', 'outer_extra', 'outer_missing',
            'top_extra', 'top_missing', 'axis_count', 'outer_count',
            'top_count', 'ux_constraint_count', 'uy_constraint_count',
            'axis_x_min', 'axis_x_max', 'axis_y_min', 'axis_y_max',
            'outer_x_min', 'outer_x_max', 'outer_y_min', 'outer_y_max',
            'top_x_min', 'top_x_max', 'top_y_min', 'top_y_max',
            'axis_geometry_count', 'outer_geometry_count',
            'axis_ux_count', 'axis_uy_count', 'outer_ux_count', 'outer_uy_count',
            'axis_ux_value_abs', 'outer_ux_value_abs', 'outer_uy_value_abs',
            'top_loop_count', 'all_fx_abs', 'all_fz_abs', 'off_top_fy_abs',
            'off_top_fy_count',
            'nonzero_load_count', 'total_fy',
            'recheck_analysis_type', 'recheck_load_step', 'recheck_center_u2',
            'recheck_max_mises', 'recheck_support_fy',
            'result_analysis_type', 'result_load_step', 'result_set_count',
            'center_count', 'center_u2',
            'max_mises', 'support_fy',
        }
        if not required.issubset(values):
            log('ANSYS checker values are incomplete: %s' % sorted(required - set(values)))
            return False
        quadratic = int(round(values['node_count'])) == 128
        expected_boundary_nodes = 3 if quadratic else 2
        expected_top_nodes = 51 if quadratic else 26

        try:
            node_geometry_rows = numeric_rows(node_audit_path, 7)
            node_force_rows = numeric_rows(node_force_audit_path, 4)
            element_summary_rows = numeric_rows(element_audit_path, 6)
            element_connectivity_rows = numeric_rows(element_connectivity_audit_path, 9)
        except Exception as exc:
            log('cannot parse ANSYS mesh audit: %s' % exc)
            return False
        if (
            len(node_geometry_rows) != int(round(values['node_count']))
            or len(node_force_rows) != int(round(values['node_count']))
            or len(element_summary_rows) != 25
            or len(element_connectivity_rows) != 25
        ):
            log('ANSYS mesh audit row counts are incorrect')
            return False

        def rows_by_integer_label(rows):
            result = {}
            for row in rows:
                label = int(round(row[0]))
                if abs(row[0] - label) > 1.0e-8 or label in result:
                    raise ValueError('invalid or duplicate audit label')
                result[label] = row
            return result

        try:
            node_geometry = rows_by_integer_label(node_geometry_rows)
            node_forces = rows_by_integer_label(node_force_rows)
            element_summaries = rows_by_integer_label(element_summary_rows)
            element_connectivity = rows_by_integer_label(element_connectivity_rows)
        except Exception as exc:
            log('ANSYS audit contains invalid labels: %s' % exc)
            return False
        if set(node_geometry) != set(node_forces) or set(element_summaries) != set(element_connectivity):
            log('ANSYS split audit files do not refer to the same entities')
            return False
        if set(rst_node_labels) != set(node_geometry) or set(rst_element_labels) != set(element_summaries):
            log('submitted ANSYS RST mesh labels do not match the DB mesh')
            return False
        node_rows = [node_geometry[label] + node_forces[label][1:] for label in sorted(node_geometry)]
        element_rows = [
            element_summaries[label] + element_connectivity[label][1:]
            for label in sorted(element_summaries)
        ]

        try:
            recheck_fields = rows_by_integer_label(numeric_rows(recheck_field_path, 6))
            result_fields = rows_by_integer_label(numeric_rows(result_field_path, 6))
            recheck_stress = rows_by_integer_label(numeric_rows(recheck_stress_path, 5))
            result_stress = rows_by_integer_label(numeric_rows(result_stress_path, 5))
        except Exception as exc:
            log('cannot parse ANSYS result-field audit: %s' % exc)
            return False
        if any(
            set(records) != set(node_geometry)
            for records in (recheck_fields, result_fields, recheck_stress, result_stress)
        ):
            log('ANSYS submitted or re-solved field audit is missing nodes')
            return False

        audited_nodes = {}
        for row in node_rows:
            label = int(round(row[0]))
            if abs(row[0] - label) > 1.0e-8 or label in audited_nodes:
                log('ANSYS node audit contains an invalid or duplicate label')
                return False
            coordinates = tuple(row[1:4])
            angles = tuple(row[4:7])
            forces = tuple(row[7:10])
            if any(abs(angle) > 1.0e-8 for angle in angles):
                log('ANSYS nodal coordinate systems must be global Cartesian')
                return False
            audited_nodes[label] = {'coordinates': coordinates, 'forces': forces}

        if quadratic:
            expected_coordinates = (
                [(float(radius), 0.0, 0.0) for radius in range(51)]
                + [(float(radius), 1.0, 0.0) for radius in range(51)]
                + [(float(radius), 0.5, 0.0) for radius in range(0, 51, 2)]
            )
        else:
            expected_coordinates = (
                [(float(radius), 0.0, 0.0) for radius in range(0, 51, 2)]
                + [(float(radius), 1.0, 0.0) for radius in range(0, 51, 2)]
            )
        unmatched_coordinates = set(range(len(expected_coordinates)))
        normalized_coordinates = {}
        for label, record in audited_nodes.items():
            matches = [
                index for index in unmatched_coordinates
                if coordinate_matches(record['coordinates'], expected_coordinates[index])
            ]
            if len(matches) != 1:
                log('ANSYS nodes do not form the required structured 2 mm by 1 element mesh')
                return False
            match = matches[0]
            unmatched_coordinates.remove(match)
            normalized_coordinates[label] = expected_coordinates[match]
        if unmatched_coordinates:
            log('ANSYS structured mesh coordinates are incomplete')
            return False

        seen_elements = set()
        seen_radial_bins = set()
        connected_nodes = set()
        stress_node_labels = set()
        for row in element_rows:
            element_label = int(round(row[0]))
            element_name = int(round(row[1]))
            element_k1 = int(round(row[2]))
            element_k3 = int(round(row[3]))
            element_live = int(round(row[4]))
            raw_node_labels = [int(round(value)) for value in row[6:14] if int(round(value)) > 0]
            if element_label in seen_elements or element_name not in (182, 183):
                log('ANSYS element audit contains an invalid or duplicate element')
                return False
            seen_elements.add(element_label)
            expected_node_total = 8 if element_name == 183 else 4
            if (
                element_k3 != 1
                or element_live != 1
                or (element_name == 183 and element_k1 != 0)
                or len(raw_node_labels) != expected_node_total
                or len(set(raw_node_labels)) != expected_node_total
                or any(label not in normalized_coordinates for label in raw_node_labels)
            ):
                log('ANSYS element shape, formulation, live state, or connectivity is incorrect')
                return False
            observed_coordinates = tuple(normalized_coordinates[label] for label in raw_node_labels)
            matching_bins = []
            for radial_bin in range(25):
                lo = float(2 * radial_bin)
                hi = lo + 2.0
                corners = (
                    (lo, 0.0, 0.0), (hi, 0.0, 0.0),
                    (hi, 1.0, 0.0), (lo, 1.0, 0.0),
                )
                expected_sequences = []
                if element_name == 183:
                    mid = lo + 1.0
                    mids = (
                        (mid, 0.0, 0.0), (hi, 0.5, 0.0),
                        (mid, 1.0, 0.0), (lo, 0.5, 0.0),
                    )
                    for shift in range(4):
                        expected_sequences.append(
                            corners[shift:] + corners[:shift] + mids[shift:] + mids[:shift]
                        )
                else:
                    for shift in range(4):
                        expected_sequences.append(corners[shift:] + corners[:shift])
                if observed_coordinates in expected_sequences:
                    matching_bins.append(radial_bin)
            if len(matching_bins) != 1 or matching_bins[0] in seen_radial_bins:
                log('ANSYS elements do not cover each structured radial cell exactly once')
                return False
            seen_radial_bins.add(matching_bins[0])
            connected_nodes.update(raw_node_labels)
            stress_node_labels.update(raw_node_labels[:4])
        if seen_radial_bins != set(range(25)) or connected_nodes != set(audited_nodes):
            log('ANSYS mesh has a missing cell or an unattached node')
            return False

        field_tolerances = {
            1: (1.0e-5, 1.0e-8),
            2: (1.0e-5, 1.0e-8),
            3: (1.0e-5, 1.0e-5),
            4: (1.0e-5, 1.0e-5),
            5: (2.0e-5, 2.0e-4),
        }
        for label in sorted(recheck_fields):
            x_coordinate = audited_nodes[label]['coordinates'][0]
            component_indices = [1, 2]
            if abs(x_coordinate) <= 1.0e-6 or abs(x_coordinate - 50.0) <= 1.0e-6:
                component_indices.append(3)
            if abs(x_coordinate - 50.0) <= 1.0e-6:
                component_indices.append(4)
            if label in stress_node_labels:
                component_indices.append(5)
            for index in component_indices:
                relative, absolute = field_tolerances[index]
                if not math.isclose(
                    recheck_fields[label][index],
                    result_fields[label][index],
                    rel_tol=relative,
                    abs_tol=absolute,
                ):
                    log(
                        'ANSYS submitted RST field differs from DB re-solve at node %s component %s: %.16g vs %.16g'
                        % (label, index, recheck_fields[label][index], result_fields[label][index])
                    )
                    return False
            if label in stress_node_labels:
                for index in range(1, 5):
                    if not math.isclose(
                        recheck_stress[label][index],
                        result_stress[label][index],
                        rel_tol=2.0e-5,
                        abs_tol=2.0e-4,
                    ):
                        log(
                            'ANSYS submitted RST stress tensor differs from DB re-solve at node %s component %s: %.16g vs %.16g'
                            % (label, index, recheck_stress[label][index], result_stress[label][index])
                        )
                        return False

        top_nodes = sorted(
            [
                (record['coordinates'][0], record['forces'][1], label)
                for label, record in audited_nodes.items()
                if abs(record['coordinates'][1] - 1.0) <= 1.0e-6
            ],
            key=lambda item: item[0],
        )
        if len(top_nodes) != expected_top_nodes:
            log('ANSYS TOP coordinate audit is incomplete')
            return False
        expected_nonzero = 0
        for index, (radius, force_y, label) in enumerate(top_nodes):
            if index == 0:
                delta = 0.5 * (top_nodes[1][0] - radius)
            elif index == len(top_nodes) - 1:
                delta = 0.5 * (radius - top_nodes[index - 1][0])
            else:
                delta = 0.5 * (top_nodes[index + 1][0] - top_nodes[index - 1][0])
            expected_force = -0.1 * 2.0 * math.pi * radius * delta
            if not math.isclose(force_y, expected_force, rel_tol=2.0e-4, abs_tol=2.0e-5):
                log('ANSYS TOP nodal load does not match the actual-neighbor annular formula')
                return False
            if abs(expected_force) > 1.0e-12:
                expected_nonzero += 1
        for record in audited_nodes.values():
            x_force, y_force, z_force = record['forces']
            if abs(x_force) > 1.0e-10 or abs(z_force) > 1.0e-10:
                log('ANSYS model contains a non-FY nodal force')
                return False
            if abs(record['coordinates'][1] - 1.0) > 1.0e-6 and abs(y_force) > 1.0e-10:
                log('ANSYS model contains an FY load outside TOP')
                return False

        checks = [
            int(round(values['node_count'])) in (52, 128),
            int(round(values['element_count'])) == 25,
            math.isclose(values['x_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['x_max'], 50.0, abs_tol=1.0e-6),
            math.isclose(values['y_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['y_max'], 1.0, abs_tol=1.0e-6),
            math.isclose(values['z_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['z_max'], 0.0, abs_tol=1.0e-6),
            int(round(values['db_analysis_type'])) == 0,
            int(round(values['cp_count'])) == 0,
            int(round(values['ce_count'])) == 0,
            int(round(values['bad_enam'])) == 0,
            int(round(values['bad_k3'])) == 0,
            int(round(values['bad_k1'])) == 0,
            int(round(values['bad_live'])) == 0,
            int(round(values['bad_mat'])) == 0,
            int(round(values['n182'] + values['n183'])) == int(round(values['element_count'])),
            int(round(values['attached_node_count'])) == int(round(values['node_count'])),
            int(round(values['axis_type'])) == 1,
            int(round(values['outer_type'])) == 1,
            int(round(values['top_type'])) == 1,
            all(int(round(values[name])) == 0 for name in (
                'axis_extra', 'axis_missing', 'outer_extra', 'outer_missing',
                'top_extra', 'top_missing',
            )),
            int(round(values['axis_count'])) == expected_boundary_nodes,
            int(round(values['outer_count'])) == expected_boundary_nodes,
            int(round(values['top_count'])) == expected_top_nodes,
            int(round(values['axis_geometry_count'])) == expected_boundary_nodes,
            int(round(values['outer_geometry_count'])) == expected_boundary_nodes,
            math.isclose(values['axis_x_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['axis_x_max'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['axis_y_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['axis_y_max'], 1.0, abs_tol=1.0e-6),
            math.isclose(values['outer_x_min'], 50.0, abs_tol=1.0e-6),
            math.isclose(values['outer_x_max'], 50.0, abs_tol=1.0e-6),
            math.isclose(values['outer_y_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['outer_y_max'], 1.0, abs_tol=1.0e-6),
            math.isclose(values['top_x_min'], 0.0, abs_tol=1.0e-6),
            math.isclose(values['top_x_max'], 50.0, abs_tol=1.0e-6),
            math.isclose(values['top_y_min'], 1.0, abs_tol=1.0e-6),
            math.isclose(values['top_y_max'], 1.0, abs_tol=1.0e-6),
            int(round(values['ux_constraint_count'])) == expected_boundary_nodes * 2,
            int(round(values['uy_constraint_count'])) == expected_boundary_nodes,
            int(round(values['axis_ux_count'])) == expected_boundary_nodes,
            int(round(values['axis_uy_count'])) == 0,
            int(round(values['outer_ux_count'])) == expected_boundary_nodes,
            int(round(values['outer_uy_count'])) == expected_boundary_nodes,
            values['axis_ux_value_abs'] <= 1.0e-10,
            values['outer_ux_value_abs'] <= 1.0e-10,
            values['outer_uy_value_abs'] <= 1.0e-10,
            int(round(values['top_loop_count'])) == expected_top_nodes,
            int(round(values['nonzero_load_count'])) == expected_nonzero,
            values['all_fx_abs'] <= 1.0e-10,
            values['all_fz_abs'] <= 1.0e-10,
            values['off_top_fy_abs'] <= 1.0e-10,
            int(round(values['off_top_fy_count'])) == 0,
            math.isclose(values['total_fy'], -0.1 * math.pi * 50.0 ** 2, rel_tol=2.0e-4, abs_tol=2.0e-3),
            int(round(values['recheck_analysis_type'])) == 0,
            int(round(values['recheck_load_step'])) == 1,
            int(round(values['result_analysis_type'])) == 0,
            int(round(values['result_load_step'])) == 1,
            int(round(values['result_set_count'])) >= 1,
            int(round(values['center_count'])) == 1,
            -2.0 <= values['center_u2'] <= -0.01,
            5.0 <= values['max_mises'] <= 5000.0,
            math.isclose(values['support_fy'], 0.1 * math.pi * 50.0 ** 2, rel_tol=0.02, abs_tol=0.5),
            math.isclose(values['recheck_center_u2'], values['center_u2'], rel_tol=1.0e-4, abs_tol=5.0e-5),
            math.isclose(values['recheck_max_mises'], values['max_mises'], rel_tol=2.0e-4, abs_tol=2.0e-2),
            math.isclose(values['recheck_support_fy'], values['support_fy'], rel_tol=1.0e-4, abs_tol=5.0e-2),
        ]
        if not all(checks):
            log('ANSYS task-specific model/result checks failed: %s' % values)
            return False
        try:
            metrics = json.loads((root / 'metrics.json').read_text(encoding='utf-8'))
            sidecar_u2 = float(metrics['center_deflection'])
            sidecar_mises = float(metrics['max_mises'])
        except Exception:
            log('cannot read ANSYS metrics sidecar')
            return False
        if not math.isclose(sidecar_u2, values['center_u2'], rel_tol=1.0e-3, abs_tol=5.0e-4):
            log('metrics center_deflection does not match RST')
            return False
        if not math.isclose(sidecar_mises, values['max_mises'], rel_tol=1.0e-4, abs_tol=5.0e-3):
            log('metrics max_mises does not match RST')
            return False
        return True
    except Exception as exc:
        log('ANSYS native branch failed: %s' % exc)
        return False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def evaluate():
    desktop = desktop_dir()
    root = desktop / 'result'
    if not root.is_dir():
        log('result directory missing')
        return False, desktop
    if not has_solver_artifact(root):
        log('no solver result artifact found')
        return False, desktop
    if not check_cli_metrics_json(root):
        return False, desktop
    abaqus_pair = find_abaqus_pair(root)
    if abaqus_pair:
        log('trying Abaqus-compatible branch')
        if run_abaqus_checker(desktop, abaqus_pair[0], abaqus_pair[1]):
            return True, desktop
        log('Abaqus-compatible branch did not pass')
    ansys_artifacts = find_ansys_artifacts(root)
    if ansys_artifacts:
        log('trying ANSYS-compatible branch')
        if check_ansys_with_mapdl(desktop, ansys_artifacts[0], ansys_artifacts[1]):
            return True, desktop
        log('ANSYS-compatible branch did not pass')
    log('no acceptable solver branch passed')
    return False, desktop


def main():
    passed, root = evaluate()
    write_detail(root, passed)
    sys.stdout.write('True\n' if passed else 'False\n')


if __name__ == '__main__':
    main()
