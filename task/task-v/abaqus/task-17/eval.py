# -*- coding: utf-8 -*-
# Evaluator
# Run with:
#   abaqus cae noGUI=eval.py
#
# Final stdout must be exactly one line:
#   true
# or
#   false

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import os
import sys
import math

TASK_ID = 'task-17'
GT = {'job_name': 'Job-ThermalStress', 'model_name': 'Model-ThermalStress', 'part_names': ['BAR'], 'unit_system': 'N-mm-MPa', 'model_counts': {'element_count': 80, 'instance_count': 1, 'node_count': 189}, 'step_info': {'frame_count': 2, 'last_frame_value': 1.0, 'step_names': ['Step-ThermalStress'], 'target_step': 'Step-ThermalStress'}, 'field_availability': {'COPEN': False, 'CPRESS': False, 'NT11': False, 'RF': True, 'S': True, 'U': True, 'UR': False}, 'task_specific': {'avg_mises_midsection': 254.7119903564453}}
METRICS = {'mid_x': 50.0}

REL_TOL = 5.0e-3
ABS_TOL = 1.0e-6
ABS_TOL_ZERO = 1.0e-8


def output_result(value):
    try:
        sys.__stdout__.write('True\n' if value else 'False\n')
        sys.__stdout__.flush()
    except Exception:
        try:
            sys.stdout.write('True\n' if value else 'False\n')
            sys.stdout.flush()
        except Exception:
            pass


def close_enough(obs, exp, rel_tol=REL_TOL, abs_tol=ABS_TOL):
    try:
        obsf = float(obs)
        expf = float(exp)
    except Exception:
        return False
    tol = max(float(abs_tol), float(rel_tol) * abs(expf))
    return abs(obsf - expf) <= tol


def get_desktop(job_name):
    candidates = []
    up = os.environ.get('USERPROFILE', None)
    if up:
        candidates.append(os.path.join(up, 'Desktop'))
    candidates.append(r'C:\Users\Administrator\Desktop')
    candidates.append(r'C:\Users\User\Desktop')

    for d in candidates:
        if os.path.exists(os.path.join(d, job_name + '.odb')) or os.path.exists(os.path.join(d, job_name + '.cae')):
            return d

    for d in candidates:
        if os.path.isdir(d):
            return d

    return r'C:\Users\Administrator\Desktop'


def has_forbidden_py_file(desktop_path):
    try:
        entries = os.listdir(desktop_path)
    except:
        return True

    for name in entries:
        try:
            full_path = os.path.join(desktop_path, name)
            if not os.path.isfile(full_path):
                continue
        except:
            return True

        lower_name = name.lower()
        if lower_name.endswith('.py') and lower_name != 'eval.py':
            return True

    return False


def find_step_case_insensitive(steps, target):
    tu = str(target).upper()
    for k in steps.keys():
        if str(k).upper() == tu:
            return k
    return None


def get_main_instance(root_assembly):
    best = None
    best_n = -1
    for k in root_assembly.instances.keys():
        inst = root_assembly.instances[k]
        try:
            n = len(inst.nodes)
        except Exception:
            n = -1
        if n > best_n:
            best_n = n
            best = inst
    return best


def repo_get_field(repo, name):
    try:
        if name in repo.keys():
            return repo[name]
    except Exception:
        pass
    return None


def safe_data_component(data, idx=0):
    try:
        return float(data[idx])
    except Exception:
        try:
            return float(data)
        except Exception:
            return None


def nearest_node_value(field_values, inst, target, comp_idx=0, use_abs=False):
    best_dist = None
    best_val = None
    for v in field_values:
        if v.nodeLabel is None:
            continue
        try:
            node = inst.getNodeFromLabel(v.nodeLabel)
            x, y, z = node.coordinates
            d = math.sqrt((float(x)-target[0])**2 + (float(y)-target[1])**2 + (float(z)-target[2])**2)
            val = safe_data_component(v.data, comp_idx)
            if val is None:
                continue
            if best_dist is None or d < best_dist:
                best_dist = d
                best_val = abs(val) if use_abs else val
        except Exception:
            pass
    return best_val


def max_mises_midspan(s_field_values, inst, x_target, tol=3.0):
    vals = []
    for v in s_field_values:
        if v.mises is None or v.elementLabel is None:
            continue
        try:
            elem = inst.getElementFromLabel(v.elementLabel)
            xs = [inst.getNodeFromLabel(nid).coordinates[0] for nid in elem.connectivity]
            cx = sum(xs) / float(len(xs))
            if abs(float(cx) - float(x_target)) <= float(tol):
                vals.append(float(v.mises))
        except Exception:
            pass
    if len(vals) == 0:
        return None
    return max(vals)


def parse_first_eigen(step):
    for frame in step.frames[1:]:
        desc = frame.description or ''
        try:
            tokens = desc.replace(',', ' ').replace(':', ' ').split()
            for i, tok in enumerate(tokens):
                if tok.lower().startswith('eigenvalue') and i + 1 < len(tokens):
                    try:
                        return float(tokens[i + 1])
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if frame.frameValue is not None and float(frame.frameValue) > 0.0:
                return float(frame.frameValue)
        except Exception:
            pass
    return None


def parse_first_frequency(step):
    if len(step.frames) > 1:
        frame = step.frames[1]
        try:
            if frame.frameValue is not None and float(frame.frameValue) > 0.0:
                return float(frame.frameValue)
        except Exception:
            pass
        desc = frame.description or ''
        try:
            tokens = desc.replace(',', ' ').replace(':', ' ').split()
            for i, tok in enumerate(tokens):
                if tok.lower().startswith('frequency') and i + 1 < len(tokens):
                    try:
                        return float(tokens[i + 1])
                    except Exception:
                        pass
        except Exception:
            pass
    return None


def detect_category():
    ts = GT['task_specific']
    keys = set(ts.keys())
    if 'nt11_near_center_x50y25z5' in keys:
        return 'heat_steady'
    if 'rp_rotation_mag' in keys:
        return 'torsion'
    if 'has_penetration' in keys:
        return 'contact_block_plate'
    if 'u2_midspan_bottom' in keys:
        return 'beam_udl'
    if 'all_buckle_eigenvalues' in keys:
        return 'buckle_plate'
    if 'first_natural_frequency' in keys:
        return 'modal_cantilever'
    if 'avg_mises_midsection' in keys:
        return 'thermal_stress'
    if 'analysis_end_time' in keys:
        return 'heat_transient'
    if 'max_mises_near_hole_flag' in keys:
        return 'hole_shell_tension'
    return 'unknown'


def collect_task_specific(category, inst, step, last_frame, fields):
    out = {}

    if category == 'heat_steady':
        t_field = repo_get_field(fields, 'NT11')
        if t_field is not None:
            vals = []
            for v in t_field.values:
                tv = safe_data_component(v.data, 0)
                if tv is not None:
                    vals.append(tv)
            out['nt11_min'] = min(vals) if vals else None
            out['nt11_max'] = max(vals) if vals else None
            out['nt11_near_center_x50y25z5'] = nearest_node_value(t_field.values, inst, METRICS['mid_pt'], comp_idx=0, use_abs=False)

    elif category == 'torsion':
        s_field = repo_get_field(fields, 'S')
        ur_field = repo_get_field(fields, 'UR')

        max_mises = None
        at_flag = False
        if s_field is not None:
            mm = -1.0
            for v in s_field.values:
                if v.mises is None:
                    continue
                vm = float(v.mises)
                if vm > mm:
                    mm = vm
                    try:
                        inst_ref = v.instance if v.instance is not None else inst
                        elem = inst_ref.getElementFromLabel(v.elementLabel)
                        xs = [float(inst_ref.getNodeFromLabel(nid).coordinates[0]) for nid in elem.connectivity]
                        ys = [float(inst_ref.getNodeFromLabel(nid).coordinates[1]) for nid in elem.connectivity]
                        zs = [float(inst_ref.getNodeFromLabel(nid).coordinates[2]) for nid in elem.connectivity]
                        cx = sum(xs) / float(len(xs))
                        cy = sum(ys) / float(len(ys))
                        cz = sum(zs) / float(len(zs))
                        rr = math.sqrt(cx * cx + cz * cz)
                        at_flag = (abs(cy - METRICS['length']) < 3.0 and abs(rr - METRICS['radius']) < 1.5)
                    except Exception:
                        at_flag = False
            if mm >= 0.0:
                max_mises = mm

        rp_rot = None
        if ur_field is not None:
            best = 0.0
            for val in ur_field.values:
                try:
                    data = val.data
                    if len(data) > 0:
                        best = max(best, max(abs(float(d)) for d in data))
                except Exception:
                    pass
            rp_rot = best

        out['max_mises'] = max_mises
        out['max_mises_at_free_end_outer_surface'] = bool(at_flag)
        out['rp_rotation_mag'] = rp_rot

    elif category == 'contact_block_plate':
        cpress = repo_get_field(fields, 'CPRESS')
        copen = repo_get_field(fields, 'COPEN')
        s_field = repo_get_field(fields, 'S')

        has_cpress = cpress is not None
        has_copen = copen is not None
        has_pen = False
        cpress_vals = []

        if copen is not None:
            for v in copen.values:
                vv = safe_data_component(v.data, 0)
                if vv is not None and vv < -1.0e-6:
                    has_pen = True

        if cpress is not None:
            for v in cpress.values:
                cv = safe_data_component(v.data, 0)
                if cv is not None:
                    cpress_vals.append(cv)

        max_mises = None
        if s_field is not None:
            vals = [float(v.mises) for v in s_field.values if v.mises is not None]
            if vals:
                max_mises = max(vals)

        out['has_cpress'] = bool(has_cpress)
        out['has_copen'] = bool(has_copen)
        out['has_penetration'] = bool(has_pen)
        out['cpress_max'] = max(cpress_vals) if cpress_vals else None
        out['cpress_avg'] = (sum(cpress_vals) / float(len(cpress_vals))) if cpress_vals else None
        out['max_mises'] = max_mises

    elif category == 'beam_udl':
        u_field = repo_get_field(fields, 'U')
        s_field = repo_get_field(fields, 'S')

        out['u2_midspan_bottom'] = None
        out['max_mises_midspan'] = None

        if u_field is not None:
            out['u2_midspan_bottom'] = nearest_node_value(u_field.values, inst, METRICS['u_pt'], comp_idx=1, use_abs=True)
        if s_field is not None:
            out['max_mises_midspan'] = max_mises_midspan(s_field.values, inst, METRICS['mid_x'], tol=3.0)

    elif category == 'buckle_plate':
        out['first_buckle_eigenvalue'] = parse_first_eigen(step)
        vals = []
        for frame in step.frames[1:]:
            ev = None
            desc = frame.description or ''
            try:
                tokens = desc.replace(',', ' ').replace(':', ' ').split()
                for i, tok in enumerate(tokens):
                    if tok.lower().startswith('eigenvalue') and i + 1 < len(tokens):
                        try:
                            ev = float(tokens[i + 1])
                        except Exception:
                            ev = None
                        break
            except Exception:
                ev = None
            if ev is None:
                try:
                    if frame.frameValue is not None and float(frame.frameValue) > 0.0:
                        ev = float(frame.frameValue)
                except Exception:
                    ev = None
            if ev is not None:
                vals.append(ev)
        out['all_buckle_eigenvalues'] = vals
        out['has_mode_frames'] = (len(step.frames) > 1)

    elif category == 'modal_cantilever':
        out['first_natural_frequency'] = parse_first_frequency(step)

    elif category == 'thermal_stress':
        s_field = repo_get_field(fields, 'S')
        out['avg_mises_midsection'] = None
        if s_field is not None:
            mids = []
            mid_x = METRICS['mid_x']
            for v in s_field.values:
                if v.mises is None or v.elementLabel is None:
                    continue
                try:
                    elem = inst.getElementFromLabel(v.elementLabel)
                    xs = [inst.getNodeFromLabel(nid).coordinates[0] for nid in elem.connectivity]
                    cx = sum(xs) / float(len(xs))
                    if abs(float(cx) - float(mid_x)) <= 5.0:
                        mids.append(float(v.mises))
                except Exception:
                    pass
            if mids:
                out['avg_mises_midsection'] = sum(mids) / float(len(mids))

    elif category == 'heat_transient':
        t_field = repo_get_field(fields, 'NT11')
        x0_vals = []
        x5_vals = []
        all_vals = []
        if t_field is not None:
            for v in t_field.values:
                if v.nodeLabel is None:
                    continue
                try:
                    inst_ref = v.instance if v.instance is not None else inst
                    node = inst_ref.getNodeFromLabel(v.nodeLabel)
                    x = float(node.coordinates[0])
                    t = safe_data_component(v.data, 0)
                    if t is None:
                        continue
                    all_vals.append(t)
                    if abs(x - 0.0) <= 2.5:
                        x0_vals.append(t)
                    if 3.5 <= x <= 6.5:
                        x5_vals.append(t)
                except Exception:
                    pass

        out['analysis_end_time'] = float(last_frame.frameValue) if last_frame is not None else None
        out['nt11_avg_x0_face'] = (sum(x0_vals) / float(len(x0_vals))) if x0_vals else None
        out['nt11_avg_x5_band'] = (sum(x5_vals) / float(len(x5_vals))) if x5_vals else None
        out['nt11_max'] = max(all_vals) if all_vals else None
        out['nt11_min'] = min(all_vals) if all_vals else None

    elif category == 'hole_shell_tension':
        s_field = repo_get_field(fields, 'S')
        max_mises = None
        at_hole = False
        max_loc = None

        if s_field is not None:
            mm = -1.0
            center = METRICS['hole_center']
            hole_r = METRICS['hole_r']
            for v in s_field.values:
                if v.mises is None:
                    continue
                vm = float(v.mises)
                if vm > mm:
                    mm = vm
                    try:
                        inst_ref = v.instance if v.instance is not None else inst
                        elem = inst_ref.getElementFromLabel(v.elementLabel)
                        xs = []
                        ys = []
                        zs = []
                        for nid in elem.connectivity:
                            nd = inst_ref.getNodeFromLabel(nid)
                            xs.append(float(nd.coordinates[0]))
                            ys.append(float(nd.coordinates[1]))
                            zs.append(float(nd.coordinates[2]))
                        cx = sum(xs) / float(len(xs))
                        cy = sum(ys) / float(len(ys))
                        cz = sum(zs) / float(len(zs))
                        max_loc = [cx, cy, cz]
                        dist = math.sqrt((cx-center[0])**2 + (cy-center[1])**2)
                        at_hole = dist < hole_r * 1.5
                    except Exception:
                        at_hole = False
            if mm >= 0.0:
                max_mises = mm

        out['max_mises'] = max_mises
        out['max_mises_location'] = max_loc
        out['max_mises_near_hole_flag'] = bool(at_hole)

    return out


def compare_scalar(obs, exp):
    if exp is None:
        return obs is None
    if isinstance(exp, bool):
        return bool(obs) == exp
    if isinstance(exp, (int, float)):
        at = ABS_TOL_ZERO if abs(float(exp)) < 1.0e-8 else ABS_TOL
        return close_enough(obs, exp, rel_tol=REL_TOL, abs_tol=at)
    return obs == exp


def compare_values(obs, exp):
    if isinstance(exp, list):
        if not isinstance(obs, list):
            return False
        if len(obs) != len(exp):
            return False
        for i in range(len(exp)):
            if not compare_values(obs[i], exp[i]):
                return False
        return True
    return compare_scalar(obs, exp)


def check_task():
    job_name = GT['job_name']
    desktop = get_desktop(job_name)

    if has_forbidden_py_file(desktop):
        return False

    cae_path = os.path.join(desktop, job_name + '.cae')
    odb_path = os.path.join(desktop, job_name + '.odb')

    if not os.path.exists(cae_path):
        return False
    if not os.path.exists(odb_path):
        return False

    try:
        openMdb(pathName=cae_path)
    except Exception:
        return False

    odb = None
    try:
        odb = openOdb(path=odb_path, readOnly=True)

        exp_step = GT.get('step_info', {})
        step_key = find_step_case_insensitive(odb.steps, exp_step.get('target_step'))
        if step_key is None:
            return False

        step = odb.steps[step_key]
        if len(step.frames) == 0:
            return False
        last_frame = step.frames[-1]

        # Keep a lightweight time-sanity check with tolerance.
        if not compare_values(float(last_frame.frameValue), exp_step.get('last_frame_value')):
            return False

        inst = get_main_instance(odb.rootAssembly)
        if inst is None:
            return False

        fo = last_frame.fieldOutputs

        category = detect_category()
        obs_ts = collect_task_specific(category, inst, step, last_frame, fo)
        exp_ts = GT.get('task_specific', {})

        for k, ev in exp_ts.items():
            ov = obs_ts.get(k, None)
            if not compare_values(ov, ev):
                return False

        return True

    except Exception:
        return False
    finally:
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass


def main():
    ok = check_task()
    output_result(ok)


if __name__ == '__main__':
    main()
