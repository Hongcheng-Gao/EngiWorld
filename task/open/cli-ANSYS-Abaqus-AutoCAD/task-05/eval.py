# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

# Standalone hidden spec. This task does not import a shared evaluator.
TASK_SPEC = {'task_id': 'c-cae-commercial-open-choice-task-05-windows', 'open_choice_id': 'cae-open-choice-005', 'source_task': 'task/task-c/abaqus/task-05', 'original_software': 'abaqus', 'alternative_software': 'ansys', 'distractor_software': 'autocad', 'interface': 'cli', 'domain': 'solid_block_tension', 'analysis_kind': 'static_structural', 'metrics': ['end_displacement', 'max_stress'], 'expected_result_fields': ['U', 'S'], 'require_metrics_json': True, 'visible_goal': 'Analyze a rectangular aluminum block under axial tensile loading; report end displacement and stress.', 'selection_reason': 'Linear elastic solid block tension is a low-risk cross-solver replacement task.', 'artifact_hint': {'ground_truth_files': ['Job-BlockTension.cae', 'Job-BlockTension.odb'], 'abaqus_stems': ['Job-BlockTension'], 'ansys_db_files': [], 'ansys_result_files': []}, 'span_hint': {'x': 120.0, 'y': 12.0, 'z': 8.0}, 'bounds_hint': None}
MODEL_RULES = {'metrics': {'end_displacement': ('abs', 0.003, 0.05), 'max_stress': ('abs', 4.0, 20.0)}, 'bounds': {'x': [0.0, 120.0], 'y': [0.0, 12.0], 'z': [0.0, 8.0]}, 'abaqus_elements_any': ['C3D'], 'abaqus_repo_types': {'loads': ['PRESSURE', 'SURFACETRACTION']}, 'abaqus_material': {'elastic': [[70000.0, 0.33]]}, 'abaqus_step_types': ['STATICSTEP'], 'ansys_elements_any': ['SOLID185', 'SOLID186', 'SOLID187'], 'ansys_material_numbers': [70000.0, 0.33], 'ansys_load_tokens_any': ['FX', 'PRES']}
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
    for cae in caes:
        for odb in odbs:
            if cae.stem.lower() == odb.stem.lower():
                return cae, odb
    log('Abaqus model and result stems do not match')
    return None


def find_ansys_artifacts(root):
    model_files = files_with_suffixes(root, ['.db', '.wbpj'])
    result_files = files_with_suffixes(root, ['.rst', '.rth'])
    if not model_files or not result_files:
        return None
    preferred_result = '.rth' if TASK_SPEC.get('analysis_kind') == 'thermal' else '.rst'
    result_files.sort(key=lambda path: (path.suffix.lower() != preferred_result, path.name.lower()))
    for model in model_files:
        for result in result_files:
            if model.stem.lower() == result.stem.lower():
                return model, result
    log('ANSYS model and result stems do not match')
    return None


def run_abaqus_checker(root, cae_path, odb_path):
    checker = root / '__open_choice_abaqus_checker.py'
    result = root / '__open_choice_abaqus_result.txt'
    checker_source = r'''
# -*- coding: utf-8 -*-
from __future__ import annotations
import math
import os
import traceback
from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

SPEC = __SPEC__
RULES = __RULES__
CAE_PATH = __CAE_PATH__
ODB_PATH = __ODB_PATH__
RESULT_PATH = __RESULT_PATH__
DETAILS = []

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

def check_abaqus_result_fields(field_names):
    expected = [ci(x) for x in SPEC.get('expected_result_fields', [])]
    if not expected:
        return True
    missing = [f for f in expected if f not in field_names]
    if missing:
        log('missing result fields: %s from %s' % (missing, sorted(field_names)))
        return False
    return True

def field_has_numeric_data(field):
    try:
        values = field.values
        count = len(values)
        if count < 1:
            return False
        for i in range(count):
            v = values[i]
            data = getattr(v, 'data', None)
            if data is None:
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
    openMdb(pathName=CAE_PATH)
    model = primary_model()
    if model is None:
        log('no model found')
        return False
    part = primary_part(model)
    if part is None:
        log('no part found')
        return False
    try:
        if len(part.nodes) < 2 or len(part.elements) < 1:
            log('mesh too small')
            return False
    except Exception:
        log('cannot inspect mesh')
        return False
    return (
        check_abaqus_model_rules(model)
        and check_abaqus_geometry(model, part)
        and check_abaqus_materials(model)
        and check_abaqus_analysis_step(model)
        and check_abaqus_boundary_loads(model)
    )

def check_odb():
    odb = None
    try:
        odb = openOdb(path=ODB_PATH, readOnly=True)
        if len(odb.steps.keys()) < 1:
            log('result has no steps')
            return False
        total_frames = 0
        field_names = set()
        last_frame = None
        for sk in odb.steps.keys():
            step = odb.steps[sk]
            total_frames += len(step.frames)
            if step.frames:
                last_frame = step.frames[-1]
                for name in last_frame.fieldOutputs.keys():
                    field_names.add(ci(name))
        if total_frames < 1 or last_frame is None:
            log('result has no frames')
            return False
        if not check_abaqus_result_fields(field_names):
            return False
        if not check_abaqus_metrics(last_frame):
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
        return True
    except Exception:
        log(traceback.format_exc())
        return False
    finally:
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass

def main():
    ok = False
    try:
        ok = check_cae() and check_odb()
    except Exception:
        log(traceback.format_exc())
        ok = False
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
    checker_source = checker_source.replace('__SPEC__', repr(TASK_SPEC))
    checker_source = checker_source.replace('__RULES__', repr(MODEL_RULES))
    checker_source = checker_source.replace('__CAE_PATH__', repr(str(cae_path)))
    checker_source = checker_source.replace('__ODB_PATH__', repr(str(odb_path)))
    checker_source = checker_source.replace('__RESULT_PATH__', repr(str(result)))
    checker.write_text(checker_source, encoding='utf-8')
    try:
        completed = subprocess.run([ABAQUS_COMMAND, 'cae', 'noGUI=' + str(checker)], cwd=str(root), text=True, capture_output=True, timeout=900, shell=False)
        log('abaqus checker returncode=%s' % completed.returncode)
        if completed.stdout:
            log('abaqus stdout tail=' + completed.stdout[-1000:])
        if completed.stderr:
            log('abaqus stderr tail=' + completed.stderr[-1000:])
    except Exception as exc:
        log('abaqus checker failed to run: %s' % exc)
        return False
    try:
        return result.read_text(encoding='utf-8', errors='ignore').strip() == 'True'
    except Exception:
        return False


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
    mapdl = None
    try:
        from ansys.mapdl.core import launch_mapdl
        mapdl = launch_mapdl(exec_file=ANSYS_EXEC, jobname='eval_open_choice_' + TASK_SPEC['task_id'].replace('-', '_'), run_location=str(root), nproc=1, override=True, cleanup_on_exit=False)
        if model_path.suffix.lower() == '.db':
            mapdl.resume(str(model_path.with_suffix('')), 'db')
        else:
            log('project artifact present; using result file inspection')
        if not check_ansys_geometry(mapdl):
            return False
        if not check_ansys_model_rules(mapdl):
            return False
        if not check_ansys_materials(mapdl):
            log('material check failed')
            return False
        if not check_ansys_boundary_loads(mapdl):
            return False
        if not check_ansys_analysis_step(mapdl, result_path):
            return False
        mapdl.post1()
        mapdl.file(str(result_path.with_suffix('')), result_path.suffix.lstrip('.'))
        try:
            mapdl.set('LAST')
        except Exception:
            try:
                mapdl.set(1, 1)
            except Exception as exc:
                log('cannot set result: %s' % exc)
                return False
        return check_ansys_result_fields(mapdl)
    except Exception as exc:
        log('ansys branch failed: %s' % exc)
        return False
    finally:
        close_mapdl(mapdl)


def evaluate():
    root = desktop_dir()
    if not has_solver_artifact(root):
        log('no solver result artifact found')
        return False, root
    if not check_cli_metrics_json(root):
        return False, root
    abaqus_pair = find_abaqus_pair(root)
    if abaqus_pair:
        log('trying Abaqus-compatible branch')
        if run_abaqus_checker(root, abaqus_pair[0], abaqus_pair[1]):
            return True, root
        log('Abaqus-compatible branch did not pass')
    ansys_artifacts = find_ansys_artifacts(root)
    if ansys_artifacts:
        log('trying ANSYS-compatible branch')
        if check_ansys_with_mapdl(root, ansys_artifacts[0], ansys_artifacts[1]):
            return True, root
        log('ANSYS-compatible branch did not pass')
    log('no acceptable solver branch passed')
    return False, root


def main():
    passed, root = evaluate()
    write_detail(root, passed)
    sys.stdout.write('True\n' if passed else 'False\n')


if __name__ == '__main__':
    main()
