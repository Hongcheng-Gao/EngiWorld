# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Standalone hidden spec. This task does not import a shared evaluator.
TASK_SPEC = {'task_id': 'v-open-abaqus-ansys-autocad-task-06-windows', 'open_choice_id': 'cae-open-choice-016', 'source_task': 'task/task-v/abaqus/task-16', 'original_software': 'abaqus', 'alternative_software': 'ansys', 'distractor_software': 'autocad', 'interface': 'gui', 'domain': 'transient_heat_block_gui', 'analysis_kind': 'thermal', 'metrics': ['heated_face_average_temperature', 'x_approximately_5mm_band_average_temperature', 'time_value'], 'expected_result_fields': ['NT11'], 'require_metrics_json': False, 'visible_goal': 'Using only an interactive graphical workflow, solve the transient heat-transfer block and report the final average temperatures near X = 0 and X approximately 5 mm together with the final analysis time.', 'selection_reason': 'Transient thermal analysis is supported in both tools and has solver-result evidence.', 'artifact_hint': {'ground_truth_files': ['Job-TransientHeat-A.cae', 'Job-TransientHeat-A.odb', 'gt_task_06_ansys.db', 'gt_task_06_ansys.rth'], 'abaqus_stems': ['Job-TransientHeat-A'], 'ansys_db_files': ['gt_task_06_ansys.db'], 'ansys_result_files': ['gt_task_06_ansys.rth']}, 'span_hint': {'x': 60.0, 'y': 18.0, 'z': 12.0}, 'bounds_hint': None}
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
    return caes[0], odbs[0]


def find_ansys_artifacts(root):
    model_files = files_with_suffixes(root, ['.db', '.wbpj'])
    result_files = files_with_suffixes(root, ['.rst', '.rth'])
    if TASK_SPEC.get('analysis_kind') == 'thermal':
        result_files = sorted(result_files, key=lambda p: (p.suffix.lower() != '.rth', p.name.lower()))
    if not model_files or not result_files:
        return None
    for model in model_files:
        for result in result_files:
            if model.stem.lower() == result.stem.lower():
                return model, result
    return model_files[0], result_files[0]


def run_abaqus_checker(root, cae_path, odb_path):
    checker_source = r'''
# -*- coding: utf-8 -*-
from __future__ import annotations
import os
import traceback
from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

SPEC = __SPEC__
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

def check_geometry_bbox(bb):
    if bb is None:
        log('no nodal bbox')
        return False
    for axis, target in (SPEC.get('span_hint') or {}).items():
        if axis == 'min_span' or axis not in bb:
            continue
        obs = bb[axis][1] - bb[axis][0]
        tol = max(0.25, abs(float(target)) * 0.10)
        if abs(obs - float(target)) > tol:
            log('span mismatch %s obs=%s target=%s tol=%s' % (axis, obs, target, tol))
            return False
    bounds = SPEC.get('bounds_hint') or {}
    for axis, target in bounds.items():
        if axis == 'min_span' or axis not in bb:
            continue
        lo, hi = target
        obs_lo, obs_hi = bb[axis]
        tol = max(0.5, abs(float(hi) - float(lo)) * 0.10)
        if abs(obs_lo - float(lo)) > tol or abs(obs_hi - float(hi)) > tol:
            log('bounds mismatch %s obs=%s target=%s tol=%s' % (axis, bb[axis], target, tol))
            return False
    min_span = bounds.get('min_span') or (SPEC.get('span_hint') or {}).get('min_span')
    if min_span is not None and max(bb[a][1] - bb[a][0] for a in bb) < float(min_span):
        log('min_span not met')
        return False
    return True

def step_text(step_obj):
    return ' '.join([ci(step_obj.__class__.__name__), ci(getattr(step_obj, 'procedureType', '')), ci(getattr(step_obj, 'analysis', ''))])

def check_abaqus_geometry(part):
    return check_geometry_bbox(bbox(collect_xyz(part.nodes)))

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
    if kind in ('static_structural', 'contact', 'thermal_structural') and ('STATIC' not in texts and kind != 'thermal_structural'):
        log('static step not found')
        return False
    if kind == 'thermal' and ('HEAT' not in texts and 'TRANSFER' not in texts):
        log('heat transfer step not found')
        return False
    return True

def find_key(repo, target):
    wanted = ci(target)
    try:
        for key in repo.keys():
            if ci(key) == wanted:
                return key
    except Exception:
        pass
    return None

try:
    TEXT_TYPES = (str, bytes)
except Exception:
    TEXT_TYPES = (str,)

INP_LOAD_EVIDENCE_CARDS = (
    '*CLOAD', '*DLOAD', '*DSLOAD', '*TEMPERATURE', '*INITIAL CONDITIONS',
    '*CFLUX', '*DFLUX', '*FILM', '*RADIATE', '*CONTACT', '*CONTACT PAIR',
    '*SURFACE INTERACTION', '*TIE', '*FRICTION', '*GAP'
)

def inp_has_load_evidence(path):
    try:
        with open(path, 'r') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('**'):
                    continue
                head = ci(line.split(',', 1)[0])
                for card in INP_LOAD_EVIDENCE_CARDS:
                    if head.startswith(card):
                        return True
    except Exception as exc:
        log('cannot scan exported inp for load evidence: %s' % exc)
    return False

def write_job_input(job_name, root_dir):
    old_cwd = os.getcwd()
    try:
        os.chdir(root_dir)
        mdb.jobs[job_name].writeInput(consistencyChecking=OFF)
    except Exception as exc:
        log('cannot export inp from job %s: %s' % (job_name, exc))
        return None
    finally:
        try:
            os.chdir(old_cwd)
        except Exception:
            pass
    path = os.path.join(root_dir, str(job_name) + '.inp')
    if os.path.exists(path):
        return path
    return None

def model_name_for_job(model):
    name = getattr(model, 'name', None)
    if name:
        return name
    try:
        for key in mdb.models.keys():
            if mdb.models[key] is model:
                return key
    except Exception:
        pass
    return None

def abaqus_inp_has_action_evidence(model):
    root_dir = os.path.dirname(RESULT_PATH) or os.getcwd()
    model_name = model_name_for_job(model)
    if model_name:
        try:
            for job_name in mdb.jobs.keys():
                job = mdb.jobs[job_name]
                if ci(getattr(job, 'model', '')) == ci(model_name):
                    path = write_job_input(job_name, root_dir)
                    if path and inp_has_load_evidence(path):
                        log('load/action evidence found in exported inp from existing job')
                        return True
        except Exception:
            pass
    if not model_name:
        log('cannot determine model name for inp fallback')
        return False
    temp_job = '__open_choice_eval_inp'
    try:
        try:
            if temp_job in mdb.jobs.keys():
                del mdb.jobs[temp_job]
        except Exception:
            pass
        mdb.Job(name=temp_job, model=model_name)
        path = write_job_input(temp_job, root_dir)
        if path:
            if inp_has_load_evidence(path):
                log('load/action evidence found in exported inp fallback')
                return True
            log('exported inp has no load/action cards: ' + os.path.basename(path))
    except Exception as exc:
        log('inp fallback job creation failed: %s' % exc)
    finally:
        try:
            if temp_job in mdb.jobs.keys():
                del mdb.jobs[temp_job]
        except Exception:
            pass
    return False

def check_abaqus_boundary_loads(model):
    kind = SPEC.get('analysis_kind', '')
    try:
        bc_count = len(model.boundaryConditions.keys())
    except Exception:
        bc_count = 0
    if bc_count < 1:
        log('no boundary condition found')
        return False
    if kind == 'modal':
        return True
    counts = []
    for repo_name in ('loads', 'predefinedFields', 'interactions', 'constraints'):
        try:
            counts.append(len(getattr(model, repo_name).keys()))
        except Exception:
            counts.append(0)
    action_count = 0
    for count in counts:
        action_count += count
    if action_count < 1:
        log('action repositories empty; trying inp fallback')
        if not abaqus_inp_has_action_evidence(model):
            if kind == 'thermal_structural':
                log('thermal_structural action accepted through boundary conditions plus ODB stress checks')
                return True
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

def data_has_numeric(data):
    if data is None:
        return False
    try:
        if hasattr(data, '__iter__') and not isinstance(data, TEXT_TYPES):
            for x in data:
                try:
                    float(x)
                    return True
                except Exception:
                    pass
            return False
        float(data)
        return True
    except Exception:
        return False

def field_has_numeric_data(field):
    try:
        n = 0
        for v in field.values:
            if data_has_numeric(getattr(v, 'data', None)):
                return True
            n += 1
            if n > 5000:
                break
    except Exception:
        return False
    return False

def field_output_map(frame):
    out = {}
    try:
        for key in frame.fieldOutputs.keys():
            out[ci(key)] = key
    except Exception:
        pass
    return out

def select_abaqus_result_frame(odb, expected):
    selected = None
    selected_names = set()
    best_count = -1
    total_frames = 0
    all_names = set()
    try:
        for sk in odb.steps.keys():
            step = odb.steps[sk]
            try:
                frame_count = len(step.frames)
            except Exception:
                frame_count = 0
            total_frames += frame_count
            for idx in range(frame_count):
                frame = step.frames[idx]
                fmap = field_output_map(frame)
                names = set(fmap.keys())
                all_names.update(names)
                count = 0
                for f in expected:
                    if f in names:
                        count += 1
                if selected is None or count > best_count or (count == best_count and count == len(expected)):
                    selected = frame
                    selected_names = names
                    best_count = count
    except Exception as exc:
        log('cannot iterate odb frames: %s' % exc)
        log(traceback.format_exc())
    return selected, selected_names, all_names, total_frames

def check_abaqus_metrics(frame):
    expected = [ci(x) for x in SPEC.get('expected_result_fields', [])]
    fmap = field_output_map(frame)
    for field_name in expected:
        key = fmap.get(field_name)
        if key is None:
            log('cannot read expected field for metrics: ' + field_name)
            return False
        try:
            field = frame.fieldOutputs[key]
        except Exception:
            log('cannot read expected field for metrics: ' + field_name)
            return False
        if not field_has_numeric_data(field):
            log('field has no numeric data: ' + field_name)
            return False
    return True


def _numbers(value):
    out = []
    if value is None:
        return out
    if not isinstance(value, TEXT_TYPES):
        try:
            for item in value:
                out.extend(_numbers(item))
            return out
        except TypeError:
            pass
    try:
        out.append(float(value))
    except Exception:
        pass
    return out

def _repo_values(repo):
    out = []
    try:
        for key in repo.keys():
            out.append(repo[key])
    except Exception:
        pass
    return out

def _material_numbers(material, attr):
    try:
        obj = getattr(material, attr)
        return _numbers(getattr(obj, 'table', None))
    except Exception:
        return []

def _near(value, target, rel=0.02, absolute=1.0e-8):
    try:
        return abs(float(value) - float(target)) <= max(absolute, abs(float(target)) * rel)
    except Exception:
        return False

def _all_region_nodes(value):
    out = []
    if value is None:
        return out
    try:
        if hasattr(value, 'coordinates'):
            return [value]
    except Exception:
        pass
    if isinstance(value, (list, tuple)):
        for item in value:
            out.extend(_all_region_nodes(item))
        return out
    try:
        for item in value:
            out.extend(_all_region_nodes(item))
    except Exception:
        pass
    return out

def _load_region_nodes(model, load):
    region = getattr(load, 'region', None)
    try:
        nodes = _all_region_nodes(region.nodes)
        if nodes:
            return nodes
    except Exception:
        pass
    label = ci(region)
    try:
        for key in model.rootAssembly.sets.keys():
            if ci(key) in label or label in ci(key):
                nodes = _all_region_nodes(model.rootAssembly.sets[key].nodes)
                if nodes:
                    return nodes
    except Exception:
        pass
    return []

def _part_element_types(part):
    out = set()
    try:
        for element in part.elements:
            out.add(ci(getattr(element, 'type', '')))
    except Exception:
        pass
    return out

def _material_ok(model, domain):
    materials = _repo_values(model.materials)
    if not materials:
        log('strict check: no material')
        return False
    material = materials[0]
    elastic = _material_numbers(material, 'elastic')
    if domain not in ('transient_heat_block_gui', 'transient_thermal_conduction_gui', 'steady_state_thermal_block_gui'):
        expected = {
            'constrained_thermal_stress_b_gui': (70000.0, 0.33),
        }.get(domain, (210000.0, 0.3))
        if len(elastic) < 2 or not _near(elastic[0], expected[0], 0.01) or not _near(elastic[1], expected[1], 0.02):
            log('strict check: elastic constants mismatch %s expected=%s' % (elastic, expected))
            return False
    if domain in ('cantilever_modal_a_gui', 'cantilever_modal_b_gui', 'fixed_fixed_beam_modal_gui'):
        density = _material_numbers(material, 'density')
        target = {'cantilever_modal_a_gui': 7.8e-9, 'cantilever_modal_b_gui': 7.95e-9}.get(domain, 7.85e-9)
        if not density or not _near(density[0], target, 0.03, 1.0e-12):
            log('strict check: density mismatch %s target=%s' % (density, target))
            return False
    if domain in ('transient_thermal_conduction_gui', 'steady_state_thermal_block_gui'):
        conductivity = _material_numbers(material, 'conductivity')
        target = 0.05
        if not conductivity or not _near(conductivity[0], target, 0.03):
            log('strict check: conductivity mismatch %s target=%s' % (conductivity, target))
            return False
    if domain == 'transient_heat_block_gui':
        steel_key = find_key(model.materials, 'Steel')
        if steel_key is None:
            log('strict check: material Steel is missing')
            return False
        steel = model.materials[steel_key]
        density = _material_numbers(steel, 'density')
        specific_heat = _material_numbers(steel, 'specificHeat')
        conductivity = _material_numbers(steel, 'conductivity')
        if not density or not _near(density[0], 7.85e-9, 0.02, 1.0e-12):
            log('strict check: Steel density mismatch %s' % density)
            return False
        if not specific_heat or not _near(specific_heat[0], 4.5e8, 0.02):
            log('strict check: Steel specific heat mismatch %s' % specific_heat)
            return False
        if not conductivity or not _near(conductivity[0], 45.0, 0.02):
            log('strict check: Steel conductivity must be 45 mJ/(s mm K), got %s' % conductivity)
            return False
    return True

def _step_objects(model):
    return _repo_values(model.steps)

def _step_attr_matches(steps, attr, target, rel=0.02):
    for step in steps:
        if _near(getattr(step, attr, None), target, rel):
            return True
    return False

def _has_step_text(steps, token):
    token = ci(token)
    return any(token in step_text(step) for step in steps)

def _task_load_at_single_node(model, component, magnitude, target):
    for load in _repo_values(model.loads):
        value = getattr(load, component, None)
        if not _near(value, magnitude, 0.01):
            continue
        nodes = _load_region_nodes(model, load)
        if len(nodes) != 1:
            continue
        try:
            xyz = tuple(float(v) for v in nodes[0].coordinates)
        except Exception:
            continue
        if len(xyz) == len(target) and all(_near(a, b, 0.0, 0.05) for a, b in zip(xyz, target)):
            return True
    return False

def check_abaqus_task_specific(model, part):
    domain = SPEC.get('domain', '')
    if not _material_ok(model, domain):
        return False
    steps = _step_objects(model)
    types = _part_element_types(part)
    element_count = 0
    node_count = 0
    try:
        element_count = len(part.elements)
        node_count = len(part.nodes)
    except Exception:
        pass

    solid_domains = set(('simply_supported_beam_udl_gui', 'cantilever_modal_a_gui',
        'constrained_thermal_stress_a_gui', 'constrained_thermal_stress_b_gui',
        'thermal_stress_bar_gui', 'cantilever_modal_b_gui', 'solid_cantilever_static_gui',
        'coupled_thermal_structural_bar_gui'))
    if domain in solid_domains and not any(t.startswith('C3D') for t in types):
        log('strict check: expected 3D structural solid elements, got %s' % sorted(types))
        return False
    if domain in ('thin_plate_buckling_a_gui', 'thin_plate_buckling_b_gui_only') and not any(t.startswith('S') for t in types):
        log('strict check: expected shell elements, got %s' % sorted(types))
        return False
    if domain in ('transient_heat_block_gui', 'transient_thermal_conduction_gui', 'steady_state_thermal_block_gui') and not any(t.startswith('DC3D') for t in types):
        log('strict check: expected 3D heat-transfer elements, got %s' % sorted(types))
        return False
    if domain in ('axisymmetric_circular_plate_static_gui', 'axisymmetric_thick_cylinder_pressure_gui') and not any(t.startswith('CAX') for t in types):
        log('strict check: expected axisymmetric elements, got %s' % sorted(types))
        return False
    if domain == 'plane_stress_plate_hole_gui' and not any(t.startswith('CPS') for t in types):
        log('strict check: expected plane-stress elements, got %s' % sorted(types))
        return False
    if domain in ('fixed_fixed_beam_modal_gui', 'column_eigen_buckling_gui') and not any(t.startswith('B') for t in types):
        log('strict check: expected beam elements, got %s' % sorted(types))
        return False

    mode_targets = {'cantilever_modal_a_gui': 4, 'cantilever_modal_b_gui': 5, 'fixed_fixed_beam_modal_gui': 3}
    if domain in mode_targets:
        if not any(float(getattr(step, 'numEigen', 0) or 0) >= mode_targets[domain] for step in steps):
            log('strict check: insufficient requested modes')
            return False
    if domain in ('thin_plate_buckling_a_gui', 'thin_plate_buckling_b_gui_only'):
        if not any(float(getattr(step, 'numEigen', 0) or 0) >= 3 for step in steps):
            log('strict check: three buckling eigenvalues not requested')
            return False
    if domain == 'transient_heat_block_gui':
        step_key = find_key(model.steps, 'Step-Heat-A')
        if step_key is None:
            log('strict check: Step-Heat-A is missing')
            return False
        heat_step = model.steps[step_key]
        if not (_step_attr_matches([heat_step], 'timePeriod', 300.0) and
                _step_attr_matches([heat_step], 'initialInc', 2.0) and
                _step_attr_matches([heat_step], 'maxInc', 15.0) and
                _step_attr_matches([heat_step], 'deltmx', 10.0)):
            log('strict check: transient step parameters do not match 300/2/15/DELTMX=10')
            return False
        if types != set(('DC3D8',)):
            log('strict check: task-06 requires DC3D8 elements, got %s' % sorted(types))
            return False
        if element_count < 180 or node_count < 300:
            log('strict check: 4 mm block mesh is too coarse elements=%s nodes=%s' % (element_count, node_count))
            return False
        try:
            seed_size = float(part.getPartSeeds(attribute=SIZE))
        except Exception:
            seed_size = None
        if seed_size is None or not _near(seed_size, 4.0, 0.10, 0.25):
            log('strict check: global seed size is not approximately 4 mm: %s' % seed_size)
            return False
        has_steel_section = False
        for section in _repo_values(model.sections):
            if ci(getattr(section, 'material', '')) == 'STEEL':
                has_steel_section = True
                break
        if not has_steel_section:
            log('strict check: no homogeneous solid section uses Steel')
            return False
        steel_assignments = 0
        try:
            for assignment in part.sectionAssignments:
                section_name = getattr(assignment, 'sectionName', '')
                section_key = find_key(model.sections, section_name)
                if section_key is not None and ci(getattr(model.sections[section_key], 'material', '')) == 'STEEL':
                    steel_assignments += 1
        except Exception:
            steel_assignments = 0
        if len(part.cells) != 1 or steel_assignments < 1:
            log('strict check: Steel section is not assigned to the whole block')
            return False
        instances = _repo_values(model.rootAssembly.instances)
        if len(instances) != 1:
            log('strict check: expected one block instance, got %s' % len(instances))
            return False
        dependent = getattr(instances[0], 'dependent', None)
        if dependent != ON and ci(dependent) not in ('ON', '1', 'TRUE'):
            log('strict check: block instance is not dependent')
            return False
        job_key = find_key(mdb.jobs, 'Job-TransientHeat-A')
        if job_key is None:
            log('strict check: Job-TransientHeat-A is missing from the CAE database')
            return False
    if domain == 'transient_thermal_conduction_gui':
        if not (_step_attr_matches(steps, 'timePeriod', 10.0) and _step_attr_matches(steps, 'initialInc', 0.1)):
            log('strict check: transient step time/increment mismatch')
            return False
        if element_count < 2000:
            log('strict check: 2 mm thermal mesh evidence missing elements=%s' % element_count)
            return False
    if domain == 'steady_state_thermal_block_gui':
        responses = ' '.join(ci(getattr(step, 'response', '')) for step in steps)
        if 'STEADY' not in responses:
            log('strict check: heat-transfer step is not steady state')
            return False
    if domain == 'plane_stress_plate_hole_gui' and element_count < 700:
        log('strict check: 5 mm/1 mm locally refined mesh evidence missing elements=%s' % element_count)
        return False
    if domain == 'fixed_fixed_beam_modal_gui' and not (18 <= element_count <= 24 and 19 <= node_count <= 30):
        log('strict check: expected about 20 beam divisions')
        return False
    if domain == 'solid_cantilever_static_gui':
        if not _task_load_at_single_node(model, 'cf2', -100.0, (5.0, 10.0, 100.0)):
            log('strict check: -100 N load is not applied to the single specified node')
            return False
    if domain == 'column_eigen_buckling_gui':
        if not _task_load_at_single_node(model, 'cf2', -1.0, (0.0, 1000.0, 0.0)):
            log('strict check: -1 N reference load is not applied at the column top node')
            return False
    if domain == 'coupled_thermal_structural_bar_gui':
        expansion = _material_numbers(_repo_values(model.materials)[0], 'expansion')
        if not expansion or not _near(expansion[0], 1.5e-5, 0.02, 1.0e-8):
            log('strict check: thermal expansion coefficient mismatch')
            return False
        zero = None
        try:
            zero = float(getattr(_repo_values(model.materials)[0].expansion, 'zero'))
        except Exception:
            pass
        temps = []
        for field in _repo_values(model.predefinedFields):
            temps.extend(_numbers(getattr(field, 'magnitudes', None)))
        if not (_near(zero, 20.0) or (any(_near(v, 20.0) for v in temps) and any(_near(v, 100.0) for v in temps))):
            log('strict check: 20 C thermal reference/initial field is missing')
            return False
    if domain == 'hertz_contact_static_gui':
        if len(_repo_values(model.parts)) < 2 or len(_repo_values(model.interactions)) < 1:
            log('strict check: sphere/plate parts or contact interaction missing')
            return False
        if not any('ON' in ci(getattr(step, 'nlgeom', '')) for step in steps):
            log('strict check: large deflection is not enabled')
            return False
    return True

def _odb_nodes(odb):
    xyz = []
    try:
        for key in odb.rootAssembly.instances.keys():
            for node in odb.rootAssembly.instances[key].nodes:
                c = tuple(float(v) for v in node.coordinates)
                if len(c) == 2:
                    c = (c[0], c[1], 0.0)
                xyz.append(c[:3])
    except Exception:
        pass
    return xyz

def _odb_element_types(odb):
    out = set()
    try:
        for key in odb.rootAssembly.instances.keys():
            for element in odb.rootAssembly.instances[key].elements:
                out.add(ci(getattr(element, 'type', '')))
    except Exception:
        pass
    return out

def _odb_frames(odb):
    out = []
    try:
        for key in odb.steps.keys():
            out.extend(list(odb.steps[key].frames))
    except Exception:
        pass
    return out

def _field_scalars(frame, name, invariant=False):
    values = []
    try:
        field = frame.fieldOutputs[name]
    except Exception:
        return values
    for item in field.values:
        if invariant:
            try:
                values.append(abs(float(item.mises)))
                continue
            except Exception:
                pass
        data = getattr(item, 'data', None)
        nums = _numbers(data)
        if nums:
            if len(nums) == 1:
                values.append(nums[0])
            else:
                squared = 0.0
                for number in nums:
                    squared += number * number
                values.append(squared ** 0.5)
    return values

def _frame_field(frame, names, invariant=False):
    for name in names:
        values = _field_scalars(frame, name, invariant=invariant)
        if values:
            return values
    return []

def _odb_temperature_records(odb, frame):
    coordinates = {}
    try:
        for instance_name in odb.rootAssembly.instances.keys():
            instance = odb.rootAssembly.instances[instance_name]
            for node in instance.nodes:
                coordinates[(ci(instance_name), int(node.label))] = tuple(float(v) for v in node.coordinates[:3])
    except Exception as exc:
        log('strict ODB check: cannot map node coordinates: %s' % exc)
        return []
    field = None
    for name in ('NT11', 'NT'):
        try:
            field = frame.fieldOutputs[name]
            break
        except Exception:
            pass
    if field is None:
        return []
    records = []
    for item in field.values:
        try:
            instance_name = ci(item.instance.name)
            label = int(item.nodeLabel)
            xyz = coordinates.get((instance_name, label))
            values = _numbers(getattr(item, 'data', None))
            if xyz is not None and values:
                records.append((xyz, values[0]))
        except Exception:
            pass
    return records

def _average(values):
    return sum(values) / float(len(values)) if values else None

def _thermal_profile_ok(records, heated_target, band_range, far_range):
    if len(records) < 300:
        log('strict thermal profile check: insufficient coordinate-temperature records')
        return False
    heated = [value for xyz, value in records if abs(xyz[0]) <= 0.1]
    band = [value for xyz, value in records if 3.5 <= xyz[0] <= 6.5]
    far = [value for xyz, value in records if abs(xyz[0] - 60.0) <= 0.1]
    heated_avg = _average(heated)
    band_avg = _average(band)
    far_avg = _average(far)
    if heated_avg is None or not (heated_target[0] <= heated_avg <= heated_target[1]):
        log('strict thermal profile check: X=0 average mismatch %s' % heated_avg)
        return False
    if band_avg is None or not (band_range[0] <= band_avg <= band_range[1]):
        log('strict thermal profile check: X approximately 5 mm average mismatch %s' % band_avg)
        return False
    if far_avg is None or not (far_range[0] <= far_avg <= far_range[1]):
        log('strict thermal profile check: X=60 average mismatch %s' % far_avg)
        return False
    groups = {}
    for xyz, value in records:
        key = round(float(xyz[0]), 6)
        groups.setdefault(key, []).append(value)
    profile = [(x, _average(groups[x])) for x in sorted(groups.keys())]
    if len(profile) < 8 or profile[0][1] - profile[-1][1] < 3.0:
        log('strict thermal profile check: solved field is uniform or has insufficient X resolution')
        return False
    for left, right in zip(profile, profile[1:]):
        if right[1] > left[1] + 0.75:
            log('strict thermal profile check: temperature does not decay from X=0')
            return False
    return True

def check_abaqus_odb_specific(odb):
    domain = SPEC.get('domain', '')
    frames = _odb_frames(odb)
    if not frames:
        return False
    final = frames[-1]
    types = _odb_element_types(odb)
    xyz = _odb_nodes(odb)
    times = [float(getattr(frame, 'frameValue', 0.0)) for frame in frames]
    stress = _frame_field(final, ('S',), invariant=True)
    disp = _frame_field(final, ('U',))
    temp = _frame_field(final, ('NT11', 'NT'))

    if domain in ('cantilever_modal_a_gui', 'cantilever_modal_b_gui', 'fixed_fixed_beam_modal_gui'):
        target = {'cantilever_modal_a_gui': 4, 'cantilever_modal_b_gui': 5, 'fixed_fixed_beam_modal_gui': 3}[domain]
        positive = [t for t in times if t > 0.0]
        if len(positive) < target:
            log('strict ODB check: insufficient solved modal frames')
            return False
    if domain in ('thin_plate_buckling_a_gui', 'thin_plate_buckling_b_gui_only'):
        if len([t for t in times if t != 0.0]) < 3:
            log('strict ODB check: insufficient buckling frames')
            return False
    if domain == 'simply_supported_beam_udl_gui':
        if not disp or not (0.07 <= max(abs(v) for v in disp) <= 0.25):
            log('strict ODB check: beam deflection is inconsistent with 0.1 MPa pressure')
            return False
    if domain in ('constrained_thermal_stress_a_gui', 'thermal_stress_bar_gui'):
        if not stress or max(stress) < 180.0:
            log('strict ODB check: expected restrained thermal stress is absent')
            return False
    if domain == 'constrained_thermal_stress_b_gui':
        if not stress or not (100.0 <= max(stress) <= 300.0):
            log('strict ODB check: aluminum thermal stress is implausible')
            return False
    if domain == 'solid_cantilever_static_gui':
        if not disp or not (0.10 <= max(abs(v) for v in disp) <= 0.35):
            log('strict ODB check: cantilever response is inconsistent with 100 N')
            return False
    if domain == 'plane_stress_plate_hole_gui':
        if not stress or not (20.0 <= max(stress) <= 60.0):
            log('strict ODB check: plate-hole stress concentration is implausible')
            return False
        if xyz:
            radius = min(((p[0] - 50.0) ** 2 + (p[1] - 100.0) ** 2) ** 0.5 for p in xyz)
            if not (4.5 <= radius <= 5.5):
                log('strict ODB check: 10 mm central hole is not represented')
                return False
    if domain == 'transient_heat_block_gui':
        if types != set(('DC3D8',)):
            log('strict ODB check: task-06 requires DC3D8 result elements')
            return False
        if not times or not _near(max(times), 300.0, 0.005):
            log('strict ODB check: final thermal time mismatch')
            return False
        initial_records = _odb_temperature_records(odb, frames[0])
        initial_values = [value for xyz, value in initial_records]
        if not initial_values or min(initial_values) < 24.5 or max(initial_values) > 25.5:
            log('strict ODB check: initial uniform 25 C field is missing')
            return False
        final_records = _odb_temperature_records(odb, final)
        if not _thermal_profile_ok(final_records, (93.0, 97.0), (88.0, 96.0), (75.0, 94.0)):
            return False
    if domain == 'transient_thermal_conduction_gui':
        target_time = 10.0
        low_target = 20.0
        high_target = 100.0
        if not times or not _near(max(times), target_time, 0.005):
            log('strict ODB check: final thermal time mismatch')
            return False
        if not temp or min(temp) < low_target - 2.0 or max(temp) < high_target - 1.0 or max(temp) > high_target + 2.0:
            log('strict ODB check: thermal field range mismatch')
            return False
    if domain == 'axisymmetric_circular_plate_static_gui' and not any(t.startswith('CAX') for t in types):
        return False
    if domain == 'axisymmetric_thick_cylinder_pressure_gui' and not any(t.startswith('CAX') for t in types):
        return False
    if domain == 'coupled_thermal_structural_bar_gui':
        if not stress or not (235.0 <= max(stress) <= 275.0):
            log('strict ODB check: stress does not reflect an 80 C restrained temperature rise')
            return False
    if domain == 'hertz_contact_static_gui':
        field_names = set()
        for frame in frames:
            field_names.update(field_output_map(frame).keys())
        if 'CPRESS' not in field_names:
            log('strict ODB check: contact pressure field missing')
            return False
        if xyz:
            bb = bbox(xyz)
            if bb['y'][1] < 19.0 or bb['z'][0] > -49.0 or bb['z'][1] < 49.0:
                log('strict ODB check: full sphere-on-centered-plate geometry missing')
                return False
            spherical = sum(1 for p in xyz if p[1] >= -0.1 and abs(((p[0]) ** 2 + (p[1] - 10.0) ** 2 + (p[2]) ** 2) ** 0.5 - 10.0) <= 0.5)
            if spherical < 12:
                log('strict ODB check: spherical surface evidence missing')
                return False
    if domain == 'column_eigen_buckling_gui' and not any(t.startswith('B') for t in types):
        return False
    if domain == 'steady_state_thermal_block_gui':
        if not temp or min(temp) < 19.0 or max(temp) > 101.0 or min(temp) > 21.0 or max(temp) < 99.0:
            log('strict ODB check: 20-100 C steady field missing')
            return False
        if xyz:
            midpoint = [temp[i] for i, p in enumerate(xyz[:len(temp)]) if abs(p[0] - 50.0) <= 0.1]
            if midpoint and not (57.0 <= sum(midpoint) / len(midpoint) <= 63.0):
                log('strict ODB check: midpoint temperature is not approximately 60 C')
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
        check_abaqus_geometry(part)
        and check_abaqus_materials(model)
        and check_abaqus_analysis_step(model)
        and check_abaqus_boundary_loads(model)
        and check_abaqus_task_specific(model, part)
    )

def check_odb():
    odb = None
    try:
        odb = openOdb(path=ODB_PATH, readOnly=True)
        if len(odb.steps.keys()) < 1:
            log('result has no steps')
            return False
        expected = [ci(x) for x in SPEC.get('expected_result_fields', [])]
        frame, frame_names, all_field_names, total_frames = select_abaqus_result_frame(odb, expected)
        if total_frames < 1 or frame is None:
            log('result has no frames')
            return False
        if not check_abaqus_result_fields(all_field_names):
            return False
        if not check_abaqus_metrics(frame):
            log('selected frame fields: %s' % sorted(frame_names))
            return False
        try:
            status = ci(getattr(odb.diagnosticData, 'jobStatus', ''))
            if 'ABORT' in status or 'TERMINAT' in status:
                log('result diagnostic failure: ' + status)
                return False
        except Exception:
            pass
        if not check_abaqus_odb_specific(odb):
            return False
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
    scratch = Path(tempfile.mkdtemp(prefix='__open_choice_abaqus_', dir=str(root)))
    try:
        scratch_cae = scratch / cae_path.name
        scratch_odb = scratch / odb_path.name
        checker = scratch / '__open_choice_abaqus_checker.py'
        result = scratch / '__open_choice_abaqus_result.txt'
        shutil.copy2(str(cae_path), str(scratch_cae))
        shutil.copy2(str(odb_path), str(scratch_odb))
        checker_source = checker_source.replace('__SPEC__', repr(TASK_SPEC))
        checker_source = checker_source.replace('__CAE_PATH__', repr(str(scratch_cae)))
        checker_source = checker_source.replace('__ODB_PATH__', repr(str(scratch_odb)))
        checker_source = checker_source.replace('__RESULT_PATH__', repr(str(result)))
        checker.write_text(checker_source, encoding='utf-8')
        try:
            completed = subprocess.run([ABAQUS_COMMAND, 'cae', 'noGUI=' + str(checker)], cwd=str(scratch), text=True, capture_output=True, timeout=900, shell=False)
            log('abaqus checker returncode=%s' % completed.returncode)
            if completed.stdout:
                log('abaqus stdout tail=' + completed.stdout[-1000:])
            if completed.stderr:
                log('abaqus stderr tail=' + completed.stderr[-1000:])
        except Exception as exc:
            log('abaqus checker failed to run: %s' % exc)
            return False
        try:
            passed = result.read_text(encoding='utf-8', errors='ignore').strip() == 'True'
            detail_path = scratch / '__open_choice_abaqus_detail.txt'
            if detail_path.exists():
                detail_text = detail_path.read_text(encoding='utf-8', errors='ignore').strip()
                if detail_text:
                    log('abaqus checker detail=' + detail_text[-4000:])
            return passed
        except Exception:
            return False
    finally:
        remove_scratch(scratch)


def close_mapdl(mapdl):
    if mapdl is None:
        return
    try:
        mapdl.exit(force=True)
    except TypeError:
        try:
            mapdl.exit()
        except Exception as exc:
            log('MAPDL exit failed: %s' % exc)
    except Exception as exc:
        log('MAPDL force exit failed: %s' % exc)


def remove_scratch(scratch):
    if scratch is None:
        return
    last_error = None
    for attempt in range(10):
        try:
            shutil.rmtree(str(scratch))
        except FileNotFoundError:
            return
        except Exception as exc:
            last_error = exc
        else:
            if not scratch.exists():
                return
            last_error = RuntimeError('directory still exists')
        if attempt < 9:
            time.sleep(0.5)
    log('scratch cleanup failed after 10 attempts for %s: %s' % (scratch, last_error))


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


def _mplist_value(text, label):
    lines = str(text).splitlines()
    wanted = str(label).upper()
    number_pattern = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
    for index, line in enumerate(lines):
        tokens = line.upper().split()
        if not tokens or tokens[0] != 'TEMP' or wanted not in tokens[1:]:
            continue
        for following in lines[index + 1:index + 4]:
            numbers = re.findall(number_pattern, following)
            if numbers:
                try:
                    return float(numbers[-1])
                except Exception:
                    pass
    return None


def check_geometry_values(bb):
    if not bb:
        return False
    for axis, target in (TASK_SPEC.get('span_hint') or {}).items():
        if axis == 'min_span' or axis not in bb:
            continue
        obs = bb[axis][1] - bb[axis][0]
        tol = max(0.25, abs(float(target)) * 0.10)
        if abs(obs - float(target)) > tol:
            log('span mismatch axis=%s obs=%s target=%s tol=%s' % (axis, obs, target, tol))
            return False
    bounds = TASK_SPEC.get('bounds_hint') or {}
    for axis, target in bounds.items():
        if axis == 'min_span' or axis not in bb:
            continue
        target_lo, target_hi = target
        lo, hi = bb[axis]
        tol = max(0.5, abs(float(target_hi) - float(target_lo)) * 0.10)
        if abs(lo - float(target_lo)) > tol or abs(hi - float(target_hi)) > tol:
            log('bounds mismatch axis=%s obs=%s target=%s tol=%s' % (axis, (lo, hi), target, tol))
            return False
    min_span = bounds.get('min_span') or (TASK_SPEC.get('span_hint') or {}).get('min_span')
    if min_span is not None:
        if max(v[1] - v[0] for v in bb.values()) < float(min_span):
            log('min_span not met')
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
        return check_geometry_values(bb)
    except Exception as exc:
        log('geometry check failed: %s' % exc)
        return False


def check_ansys_materials(mapdl):
    text = _safe_run(mapdl, 'MPLIST,ALL')
    if TASK_SPEC.get('domain') == 'transient_heat_block_gui':
        density = _mplist_value(text, 'DENS')
        conductivity = _mplist_value(text, 'KXX')
        specific_heat = _mplist_value(text, 'C')
        if density is None or not _close(density, 7.85e-9, 0.02, 1.0e-12):
            log('strict material check: ANSYS density mismatch %s' % density)
            return False
        if conductivity is None or not _close(conductivity, 45.0, 0.02):
            log('strict material check: ANSYS KXX must be 45 mJ/(s mm K), got %s' % conductivity)
            return False
        if specific_heat is None or not _close(specific_heat, 4.5e8, 0.02):
            log('strict material check: ANSYS specific heat mismatch %s' % specific_heat)
            return False
        return True
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
        checked += 1
    return checked > 0 or bool(TASK_SPEC.get('expected_result_fields'))



def _binary_records(result, method_name, set_index):
    try:
        nnum, dof, values = getattr(result, method_name)(set_index)
    except Exception:
        return []
    node_index = {int(node): index for index, node in enumerate(result.mesh.nnum)}
    records = []
    for node, code, value in zip(nnum, dof, values):
        index = node_index.get(int(node))
        xyz = None if index is None else tuple(float(v) for v in result.mesh.nodes[index][:3])
        records.append((int(code), float(value), xyz))
    return records

def _close(value, target, rel=0.02, absolute=1.0e-7):
    return abs(float(value) - float(target)) <= max(absolute, abs(float(target)) * rel)

def _force_sum(records, dof, axis=None, target=None, tol=0.1):
    total = 0.0
    for code, value, xyz in records:
        if code != dof:
            continue
        if axis is not None and (xyz is None or abs(xyz[axis] - target) > tol):
            continue
        total += value
    return total

def _binary_stress_max(result, set_index):
    try:
        import numpy as np
        _, stress = result.nodal_stress(set_index)
        stress = np.asarray(stress, dtype=float)
        stress = stress[np.isfinite(stress).all(axis=1)]
        if not stress.size:
            return None
        sx, sy, sz, sxy, syz, sxz = stress[:, :6].T
        mises = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3.0 * (sxy ** 2 + syz ** 2 + sxz ** 2))
        return float(mises.max())
    except Exception:
        return None

def _binary_solution_max(result, set_index):
    try:
        import numpy as np
        _, values = result.nodal_solution(set_index)
        values = np.asarray(values, dtype=float)
        if values.ndim == 1:
            return float(np.nanmax(np.abs(values)))
        return float(np.nanmax(np.linalg.norm(values, axis=1)))
    except Exception:
        return None

def _binary_temperature(result, set_index):
    try:
        import numpy as np
        nnum, values = result.nodal_temperature(set_index)
        values = np.asarray(values, dtype=float)
        aligned = np.full(int(result.mesh.nnum.size), np.nan, dtype=float)
        node_index = {int(node): index for index, node in enumerate(result.mesh.nnum)}
        for node, value in zip(nnum, values):
            index = node_index.get(int(node))
            if index is not None:
                aligned[index] = float(value)
        finite = aligned[np.isfinite(aligned)]
        if not finite.size:
            return None, None, None
        return aligned, float(np.min(finite)), float(np.max(finite))
    except Exception:
        return None, None, None

def _ansys_thermal_profile_ok(nodes, temperatures):
    import numpy as np
    if temperatures is None or len(temperatures) != len(nodes):
        log('strict binary check: temperature/node arrays do not align')
        return False
    finite = np.isfinite(temperatures)
    if int(np.count_nonzero(finite)) < 300:
        log('strict binary check: insufficient nodal temperatures')
        return False
    def average(mask):
        selected = temperatures[finite & mask]
        return None if not selected.size else float(np.mean(selected))
    heated = average(np.isclose(nodes[:, 0], 0.0, atol=0.1))
    band = average((nodes[:, 0] >= 3.5) & (nodes[:, 0] <= 6.5))
    far = average(np.isclose(nodes[:, 0], 60.0, atol=0.1))
    if heated is None or not (93.0 <= heated <= 97.0):
        log('strict binary check: X=0 average mismatch %s' % heated)
        return False
    if band is None or not (88.0 <= band <= 96.0):
        log('strict binary check: X approximately 5 mm average mismatch %s' % band)
        return False
    if far is None or not (75.0 <= far <= 94.0):
        log('strict binary check: X=60 average mismatch %s' % far)
        return False
    profile = []
    for x_value in sorted(set(round(float(v), 6) for v in nodes[finite, 0])):
        value = average(np.isclose(nodes[:, 0], x_value, atol=1.0e-5))
        if value is not None:
            profile.append((x_value, value))
    if len(profile) < 8 or profile[0][1] - profile[-1][1] < 3.0:
        log('strict binary check: solved field is uniform or has insufficient X resolution')
        return False
    for left, right in zip(profile, profile[1:]):
        if right[1] > left[1] + 0.75:
            log('strict binary check: temperature does not decay from X=0')
            return False
    return True

def _ansys_temperature_bcs_ok(records):
    temp_bcs = [(value, xyz) for code, value, xyz in records if code == 20 and abs(value) > 1.0e-9]
    return bool(temp_bcs) and not any(
        not _close(value, 95.0, 0.01) or xyz is None or abs(xyz[0]) > 0.1
        for value, xyz in temp_bcs
    )

def _ansys_time_controls_ok(times):
    positive = [float(value) for value in times if float(value) > 0.0]
    if not positive:
        return False
    increments = [positive[0]] + [right - left for left, right in zip(positive, positive[1:])]
    return increments[0] <= 2.1 and min(increments) > 0.0 and max(increments) <= 15.1

def check_ansys_result_binary(result_path):
    try:
        import numpy as np
        from ansys.mapdl import reader
        result = reader.read_binary(str(result_path))
    except Exception as exc:
        log('strict binary result reader failed: %s' % exc)
        return False
    domain = TASK_SPEC.get('domain', '')
    nodes = np.asarray(result.mesh.nodes, dtype=float)
    if nodes.size == 0 or int(result.nsets) < 1:
        log('strict binary check: empty result')
        return False
    last = int(result.nsets) - 1
    element_types = set(int(v) for v in result.mesh.etype)
    element_count = int(result.mesh.enum.size)
    node_count = int(result.mesh.nnum.size)
    bbox_values = [(float(nodes[:, i].min()), float(nodes[:, i].max())) for i in range(3)]
    forces = _binary_records(result, 'nodal_input_force', last)
    bcs = _binary_records(result, 'nodal_boundary_conditions', last)
    times = [float(v) for v in result.time_values]
    stress_max = _binary_stress_max(result, last)
    solution_max = _binary_solution_max(result, last)
    temperatures, temp_min, temp_max = _binary_temperature(result, last)

    required_type = {
        'simply_supported_beam_udl_gui': 185, 'thin_plate_buckling_a_gui': 181,
        'cantilever_modal_a_gui': 185, 'constrained_thermal_stress_a_gui': 185,
        'constrained_thermal_stress_b_gui': 185,
        'thermal_stress_bar_gui': 185, 'cantilever_modal_b_gui': 185,
        'thin_plate_buckling_b_gui_only': 181, 'plate_hole_tension_gui_only': 181,
        'solid_cantilever_static_gui': 185, 'axisymmetric_circular_plate_static_gui': 183,
        'plane_stress_plate_hole_gui': 183, 'transient_thermal_conduction_gui': 70,
        'fixed_fixed_beam_modal_gui': 188, 'axisymmetric_thick_cylinder_pressure_gui': 183,
        'coupled_thermal_structural_bar_gui': 185, 'column_eigen_buckling_gui': 188,
        'steady_state_thermal_block_gui': 70,
    }.get(domain)
    if domain == 'transient_heat_block_gui' and not element_types.intersection(set((70, 278))):
        log('strict binary check: task-06 requires SOLID70 or SOLID278, got %s' % sorted(element_types))
        return False
    if required_type is not None and required_type not in element_types:
        log('strict binary check: element type mismatch %s expected %s' % (sorted(element_types), required_type))
        return False

    if domain == 'simply_supported_beam_udl_gui':
        if not _close(_force_sum(forces, 2), -200.0, 0.03):
            log('strict binary check: top-load resultant is not -200 N')
            return False
        if any(xyz is None or abs(xyz[1] - 10.0) > 0.1 for code, value, xyz in forces if code == 2 and abs(value) > 1.0e-12):
            log('strict binary check: UDL is not confined to the top face')
            return False
        if solution_max is None or not (0.07 <= solution_max <= 0.25):
            log('strict binary check: deflection is inconsistent with q=1 N/mm')
            return False
    elif domain == 'thin_plate_buckling_a_gui':
        if not (_close(_force_sum(forces, 1, 0, 0.0), 115.2, 0.03) and _close(_force_sum(forces, 1, 0, 96.0), -115.2, 0.03)):
            log('strict binary check: 1.2 N/mm tributary edge loads missing')
            return False
        if element_count < 200:
            return False
    elif domain == 'cantilever_modal_a_gui':
        if int(result.nsets) < 4 or not times or min(times) <= 0.0:
            log('strict binary check: four solved modes missing')
            return False
    elif domain in ('constrained_thermal_stress_a_gui', 'thermal_stress_bar_gui'):
        if temp_min is None or not (_close(temp_min, 120.0, 0.01) and _close(temp_max, 120.0, 0.01)) or stress_max is None or stress_max < 180.0:
            log('strict binary check: 120 C restrained thermal response missing')
            return False
    elif domain == 'constrained_thermal_stress_b_gui':
        if temp_min is None or not (_close(temp_min, 100.0, 0.01) and _close(temp_max, 100.0, 0.01)) or stress_max is None or not (100.0 <= stress_max <= 300.0):
            log('strict binary check: aluminum thermal response mismatch')
            return False
    elif domain == 'transient_heat_block_gui':
        positive_times = [value for value in times if value > 0.0]
        if int(result.nsets) < 3 or not positive_times or not _close(positive_times[-1], 300.0, 0.005):
            log('strict binary check: transient time/temperature history mismatch')
            return False
        if not _ansys_time_controls_ok(positive_times):
            log('strict binary check: initial/max time increments do not reflect 2 s / 15 s controls')
            return False
        if not _ansys_temperature_bcs_ok(bcs):
            log('strict binary check: 95 C temperature BC is not confined to X=0')
            return False
        initial_temperatures, _, _ = _binary_temperature(result, 0)
        if initial_temperatures is None:
            log('strict binary check: first transient result set is unreadable')
            return False
        initial_far = initial_temperatures[np.isfinite(initial_temperatures) & np.isclose(nodes[:, 0], 60.0, atol=0.1)]
        if not initial_far.size or not (24.0 <= float(np.mean(initial_far)) <= 26.0):
            log('strict binary check: initial uniform 25 C field is not evidenced at the far face')
            return False
        if not _ansys_thermal_profile_ok(nodes, temperatures):
            return False
        if element_count < 180 or node_count < 300:
            log('strict binary check: 4 mm mesh is too coarse')
            return False
    elif domain == 'cantilever_modal_b_gui':
        if int(result.nsets) < 5 or not times or min(times) <= 0.0:
            return False
    elif domain == 'thin_plate_buckling_b_gui_only':
        if not (_close(_force_sum(forces, 1, 0, 0.0), 108.0, 0.03) and _close(_force_sum(forces, 1, 0, 120.0), -108.0, 0.03)):
            log('strict binary check: 0.9 N/mm tributary edge loads missing')
            return False
    elif domain == 'plate_hole_tension_gui_only':
        if not (_close(_force_sum(forces, 1, 0, 0.0), -960.0, 0.03) and _close(_force_sum(forces, 1, 0, 160.0), 960.0, 0.03)):
            log('strict binary check: 12 N/mm tributary edge loads missing')
            return False
        radius = float(np.min(np.sqrt((nodes[:, 0] - 80.0) ** 2 + (nodes[:, 1] - 40.0) ** 2)))
        if not (7.4 <= radius <= 8.6):
            log('strict binary check: central 16 mm hole missing')
            return False
    elif domain == 'solid_cantilever_static_gui':
        active = [(value, xyz) for code, value, xyz in forces if code == 2 and abs(value) > 1.0e-9]
        if len(active) != 1 or not _close(active[0][0], -100.0, 0.01) or active[0][1] is None or any(abs(a-b) > 0.1 for a,b in zip(active[0][1], (5.0, 10.0, 100.0))):
            log('strict binary check: single -100 N load at (5,10,100) missing')
            return False
        if solution_max is None or not (0.10 <= solution_max <= 0.35):
            return False
    elif domain == 'axisymmetric_circular_plate_static_gui':
        if stress_max is None or not (80.0 <= stress_max <= 300.0):
            return False
    elif domain == 'plane_stress_plate_hole_gui':
        radius = float(np.min(np.sqrt((nodes[:, 0] - 50.0) ** 2 + (nodes[:, 1] - 100.0) ** 2)))
        if element_count < 700 or not (4.5 <= radius <= 5.5) or stress_max is None or not (20.0 <= stress_max <= 60.0):
            log('strict binary check: locally refined 10 mm hole/stress evidence missing')
            return False
    elif domain == 'transient_thermal_conduction_gui':
        has_x4 = bool(np.any(np.isclose(nodes[:, 0], 4.0, atol=0.1)))
        has_x6 = bool(np.any(np.isclose(nodes[:, 0], 6.0, atol=0.1)))
        if element_count < 2000 or not has_x4 or not has_x6 or not _close(times[-1], 10.0, 0.005) or temp_min is None or temp_min < 19.0 or temp_max < 99.0:
            log('strict binary check: 2 mm mesh/final transient field mismatch')
            return False
    elif domain == 'fixed_fixed_beam_modal_gui':
        if not (18 <= element_count <= 22 and int(result.nsets) >= 3):
            log('strict binary check: 20 beam elements/three modes missing')
            return False
        end_bcs = [(code, xyz) for code, value, xyz in bcs if xyz is not None and (abs(xyz[0]) < 0.1 or abs(xyz[0]-500.0) < 0.1)]
        for x in (0.0, 500.0):
            codes = set(code for code, xyz in end_bcs if abs(xyz[0]-x) < 0.1)
            if not set((1,2,3,4,5,6)).issubset(codes):
                log('strict binary check: all six beam DOFs are not fixed at both ends')
                return False
    elif domain == 'axisymmetric_thick_cylinder_pressure_gui':
        forbidden = [(code, xyz) for code, value, xyz in bcs if code == 1 and xyz is not None and (abs(xyz[0]-25.0) < 0.1 or abs(xyz[0]-50.0) < 0.1)]
        if forbidden or stress_max is None or not (10.0 <= stress_max <= 50.0):
            log('strict binary check: cylinder radial freedom/stress mismatch')
            return False
    elif domain == 'coupled_thermal_structural_bar_gui':
        if temp_min is None or not (_close(temp_min, 100.0, 0.01) and _close(temp_max, 100.0, 0.01)) or stress_max is None or not (235.0 <= stress_max <= 275.0):
            log('strict binary check: 80 C restrained thermal stress mismatch')
            return False
    elif domain == 'hertz_contact_static_gui':
        if not (any(t in element_types for t in (170,171,172,173,174,175,176,177)) and len(element_types) >= 2):
            log('strict binary check: contact elements missing')
            return False
        if bbox_values[1][1] < 19.0 or bbox_values[2][0] > -49.0 or bbox_values[2][1] < 49.0 or not _close(_force_sum(forces, 2), -500.0, 0.03):
            log('strict binary check: sphere/plate geometry or -500 N force missing')
            return False
    elif domain == 'column_eigen_buckling_gui':
        active = [(value, xyz) for code, value, xyz in forces if code == 2 and abs(value) > 1.0e-9]
        if len(active) != 1 or not _close(active[0][0], -1.0, 0.01) or active[0][1] is None or abs(active[0][1][1]-1000.0) > 0.1 or not times or times[-1] <= 0.0:
            return False
    elif domain == 'steady_state_thermal_block_gui':
        if int(result.nsets) != 1 or temp_min is None or not _close(temp_min, 20.0, 0.02) or not _close(temp_max, 100.0, 0.02):
            return False
        mid = temperatures[np.isclose(nodes[:, 0], 50.0, atol=0.1)] if temperatures is not None and len(temperatures) == len(nodes) else []
        if len(mid) and not (57.0 <= float(np.mean(mid)) <= 63.0):
            log('strict binary check: midpoint steady temperature is not about 60 C')
            return False
    return True


def check_ansys_with_mapdl(root, model_path, result_path):
    mapdl = None
    scratch = None
    try:
        if not check_ansys_result_binary(result_path):
            return False
        scratch = Path(tempfile.mkdtemp(prefix='__open_choice_ansys_', dir=str(root)))
        scratch_model = scratch / model_path.name
        scratch_result = scratch / result_path.name
        shutil.copy2(str(model_path), str(scratch_model))
        shutil.copy2(str(result_path), str(scratch_result))
        from ansys.mapdl.core import launch_mapdl
        mapdl = launch_mapdl(exec_file=ANSYS_EXEC, jobname='eval_open_choice_' + TASK_SPEC['task_id'].replace('-', '_'), run_location=str(scratch), nproc=1, override=True, cleanup_on_exit=True)
        if scratch_model.suffix.lower() == '.db':
            mapdl.resume(str(scratch_model.with_suffix('')), 'db')
        else:
            log('project artifact present; using result file inspection')
        if not check_ansys_geometry(mapdl):
            return False
        if not check_ansys_materials(mapdl):
            log('material check failed')
            return False
        if not check_ansys_boundary_loads(mapdl):
            return False
        if not check_ansys_analysis_step(mapdl, result_path):
            return False
        mapdl.post1()
        mapdl.file(str(scratch_result.with_suffix('')), scratch_result.suffix.lstrip('.'))
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
        remove_scratch(scratch)


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
