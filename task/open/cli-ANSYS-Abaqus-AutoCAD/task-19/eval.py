# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# Standalone hidden spec. This task does not import a shared evaluator.
TASK_SPEC = {'task_id': 'c-cae-commercial-open-choice-task-19-windows', 'open_choice_id': 'cae-open-choice-029', 'source_task': 'task/task-c/ansys/task-19', 'original_software': 'ansys', 'alternative_software': 'abaqus', 'distractor_software': 'autocad', 'interface': 'cli', 'domain': 'column_eigen_buckling', 'analysis_kind': 'buckling', 'metrics': ['first_buckling_factor'], 'expected_result_fields': ['U'], 'require_metrics_json': True, 'visible_goal': 'Run a linear eigenvalue buckling analysis of a pin-ended column under axial compression; report the first load factor.', 'selection_reason': 'Column buckling gives a distinct structural stability domain while staying cross-solver.', 'artifact_hint': {'ground_truth_files': ['wb_buckling.db', 'wb_buckling.rst', 'wb_buckling.wbpj'], 'abaqus_stems': [], 'ansys_db_files': ['wb_buckling.db', 'wb_buckling.wbpj'], 'ansys_result_files': ['wb_buckling.rst']}, 'span_hint': {'y': 1000.0}, 'bounds_hint': {'y': [0.0, 1000.0]}}
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
    if not model_files or not result_files:
        return None
    for model in model_files:
        for result in result_files:
            if model.stem.lower() == result.stem.lower():
                return model, result
    return model_files[0], result_files[0]


def run_abaqus_checker(root, cae_path, odb_path):
    checker = root / '__open_choice_abaqus_checker.py'
    result = root / '__open_choice_abaqus_result.txt'
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
    return check_geometry_bbox(bbox(xyz))

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
        for i in range(min(count, 50)):
            v = values[i]
            data = getattr(v, 'data', None)
            if data is None:
                continue
            if isinstance(data, (float, int)):
                return True
            try:
                if len(data) > 0:
                    return True
            except Exception:
                pass
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
        check_abaqus_geometry(model, part)
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
        try:
            status = ci(getattr(odb.diagnosticData, 'jobStatus', ''))
            if 'ABORT' in status or 'TERMINAT' in status:
                log('result diagnostic failure: ' + status)
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
