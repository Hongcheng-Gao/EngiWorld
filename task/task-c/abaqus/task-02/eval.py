# -*- coding: utf-8 -*-
# eval_task_02.py
# Run with:
# abaqus cae noGUI=eval_task_02.py
#
# Final stdout must be only:
# true
# or
# false

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import os
import sys
import math
import traceback

# ============================================================
# 1. Paths
# ============================================================

desktop = os.path.join(
    os.environ.get('USERPROFILE', r'C:\Users\user'),
    'Desktop'
)

cae_path = os.path.join(desktop, 'Job-Cylinder.cae')
odb_path = os.path.join(desktop, 'Job-Cylinder.odb')
result_file = os.path.join(desktop, 'eval_result.txt')
error_file = os.path.join(desktop, 'eval_error.txt')

# ============================================================
# 2. Hard-coded ground truth
# ============================================================

GT = {
    'node_count': 33,
    'element_count': 20,
    'step_name': 'Step-Pressure',
    'last_frame_value': 1.0,

    'max_U1': 0.004539682529866695,
    'min_U1': 0.002888888819143176,
    'max_abs_U2': 5.969025866309201e-33,

    'inner_u1_avg': 0.004539682529866695,
    'outer_u1_avg': 0.002888888819143176,

    'max_mises': 21.036849975585938,
    'max_abs_S11': 8.78787899017334,
    'max_abs_S22': 2.0,
    'max_abs_S33': 15.454545021057129,

    'inner_band_max_mises': 21.036849975585938,
    'outer_band_max_mises': 6.221914768218994,

    'total_sum_RF2': 0.0
}

# ============================================================
# 3. Tolerances
# ============================================================

REL_TOL = 1.0e-3
ABS_TOL_SMALL = 1.0e-8
ABS_TOL_NEAR_ZERO = 1.0e-6
ABS_TOL_STRESS = 1.0e-6
ABS_TOL_COORD = 1.0e-8

# ============================================================
# 4. Utility functions
# ============================================================

error_log = []

def log_error(msg):
    error_log.append(str(msg))

def output_result(value):
    result_text = 'True' if value else 'false'
    with open(result_file, 'w') as f:
        f.write(result_text + '\n')
    if not value and error_log:
        with open(error_file, 'w') as f:
            f.write('\n'.join(error_log) + '\n')
    try:
        sys.__stdout__.write(result_text + '\n')
        sys.__stdout__.flush()
    except:
        pass

def close_enough(obs, exp, rel_tol=REL_TOL, abs_tol=ABS_TOL_SMALL):
    obs = float(obs)
    exp = float(exp)
    tol = max(abs_tol, rel_tol * abs(exp))
    ok = abs(obs - exp) <= tol
    if not ok:
        log_error(
            '  FAILED: expected %.12f, got %.12f, tolerance %.12f' % (exp, obs, tol)
        )
    return ok


def vec_mag(v):
    s = 0.0
    for x in v:
        s += float(x) * float(x)
    return math.sqrt(s)


def get_step_key(steps, target):
    target_upper = target.upper()
    for key in steps.keys():
        if key.upper() == target_upper:
            return key
    return None


def get_main_instance(root_assembly):
    best_key = None
    best_nodes = -1
    for key in root_assembly.instances.keys():
        inst = root_assembly.instances[key]
        if len(inst.nodes) > best_nodes:
            best_nodes = len(inst.nodes)
            best_key = key
    if best_key is None:
        return None
    return root_assembly.instances[best_key]


def get_nodeset_key(node_sets, target):
    target_upper = target.upper()
    for key in node_sets.keys():
        kup = key.upper()
        if kup == target_upper or kup.endswith('.' + target_upper):
            return key
    return None


def collect_labels(nodeset_obj):
    labels = set()
    for block in nodeset_obj.nodes:
        for node in block:
            labels.add(int(node.label))
    return labels

# ============================================================
# 5. CAE check
# ============================================================

def check_cae_file():
    if not os.path.exists(cae_path):
        log_error('CAE file not found: %s' % cae_path)
        return False

    try:
        openMdb(pathName=cae_path)
    except Exception as e:
        log_error('Failed to open CAE file: %s' % str(e))
        return False

    max_nodes = -1
    max_elements = -1

    try:
        for model_name in mdb.models.keys():
            model = mdb.models[model_name]

            for part_name in model.parts.keys():
                part = model.parts[part_name]
                try:
                    max_nodes = max(max_nodes, len(part.nodes))
                    max_elements = max(max_elements, len(part.elements))
                except:
                    pass

            try:
                assembly = model.rootAssembly
                for inst_name in assembly.instances.keys():
                    inst = assembly.instances[inst_name]
                    try:
                        max_nodes = max(max_nodes, len(inst.nodes))
                        max_elements = max(max_elements, len(inst.elements))
                    except:
                        pass
            except:
                pass
    except Exception as e:
        log_error('Error reading CAE file: %s' % str(e))
        return False

    if max_nodes != GT['node_count']:
        log_error('CAE node count mismatch: expected %d, got %d' % (GT['node_count'], max_nodes))
        return False
    if max_elements != GT['element_count']:
        log_error('CAE element count mismatch: expected %d, got %d' % (GT['element_count'], max_elements))
        return False

    return True

# ============================================================
# 6. ODB check
# ============================================================

def check_odb_file():
    if not os.path.exists(odb_path):
        log_error('ODB file not found: %s' % odb_path)
        return False

    odb = None

    try:
        odb = openOdb(path=odb_path, readOnly=True)
        root_assembly = odb.rootAssembly

        inst = get_main_instance(root_assembly)
        if inst is None:
            log_error('No instance found in ODB rootAssembly')
            return False

        if len(inst.nodes) != GT['node_count']:
            log_error('ODB node count mismatch: expected %d, got %d' % (GT['node_count'], len(inst.nodes)))
            return False
        if len(inst.elements) != GT['element_count']:
            log_error('ODB element count mismatch: expected %d, got %d' % (GT['element_count'], len(inst.elements)))
            return False

        step_key = get_step_key(odb.steps, GT['step_name'])
        if step_key is None:
            log_error('Step not found: %s' % GT['step_name'])
            return False

        step = odb.steps[step_key]
        if len(step.frames) == 0:
            log_error('Step has no frames')
            return False

        last_frame = step.frames[-1]
        if not close_enough(last_frame.frameValue, GT['last_frame_value'], rel_tol=1.0e-8, abs_tol=1.0e-10):
            log_error('last_frame_value mismatch')
            return False

        if 'U' not in last_frame.fieldOutputs.keys():
            log_error('FieldOutput U not found in last frame')
            return False
        if 'RF' not in last_frame.fieldOutputs.keys():
            log_error('FieldOutput RF not found in last frame')
            return False
        if 'S' not in last_frame.fieldOutputs.keys():
            log_error('FieldOutput S not found in last frame')
            return False

        U_field = last_frame.fieldOutputs['U']
        RF_field = last_frame.fieldOutputs['RF']
        S_field = last_frame.fieldOutputs['S']

        node_coord = {}
        for node in inst.nodes:
            node_coord[int(node.label)] = tuple(node.coordinates)

        # ----------------------------------------------------
        # Global displacement metrics
        # ----------------------------------------------------
        max_U1 = -1.0e100
        min_U1 = 1.0e100
        max_abs_U2 = -1.0

        node_u1 = {}

        for val in U_field.values:
            label = int(val.nodeLabel)
            u1 = float(val.data[0])
            u2 = float(val.data[1])
            node_u1[label] = u1

            max_U1 = max(max_U1, u1)
            min_U1 = min(min_U1, u1)
            max_abs_U2 = max(max_abs_U2, abs(u2))

            # Keep this call so vec_mag utility is used in same style family.
            _ = vec_mag(val.data)

        if not close_enough(max_U1, GT['max_U1']):
            log_error('max_U1 mismatch')
            return False
        if not close_enough(min_U1, GT['min_U1']):
            log_error('min_U1 mismatch')
            return False
        if abs(max_abs_U2 - GT['max_abs_U2']) > ABS_TOL_NEAR_ZERO:
            log_error('max_abs_U2 mismatch: expected %.12e, got %.12e, diff %.12e' % (GT['max_abs_U2'], max_abs_U2, abs(max_abs_U2 - GT['max_abs_U2'])))
            return False

        # ----------------------------------------------------
        # INNER / OUTER set displacement metrics
        # ----------------------------------------------------
        inner_key = get_nodeset_key(root_assembly.nodeSets, 'INNER')
        outer_key = get_nodeset_key(root_assembly.nodeSets, 'OUTER')
        if inner_key is None or outer_key is None:
            log_error('NodeSet INNER or OUTER not found. inner_key=%s, outer_key=%s' % (inner_key, outer_key))
            return False

        inner_labels = collect_labels(root_assembly.nodeSets[inner_key])
        outer_labels = collect_labels(root_assembly.nodeSets[outer_key])
        if len(inner_labels) == 0 or len(outer_labels) == 0:
            log_error('INNER or OUTER node set is empty: inner=%d, outer=%d' % (len(inner_labels), len(outer_labels)))
            return False

        inner_u1 = []
        outer_u1 = []
        for label in inner_labels:
            if label in node_u1:
                inner_u1.append(node_u1[label])
        for label in outer_labels:
            if label in node_u1:
                outer_u1.append(node_u1[label])

        if len(inner_u1) == 0 or len(outer_u1) == 0:
            log_error('No U1 data for INNER or OUTER nodes: inner=%d, outer=%d' % (len(inner_u1), len(outer_u1)))
            return False

        inner_u1_avg = sum(inner_u1) / float(len(inner_u1))
        outer_u1_avg = sum(outer_u1) / float(len(outer_u1))

        if not close_enough(inner_u1_avg, GT['inner_u1_avg']):
            log_error('inner_u1_avg mismatch')
            return False
        if not close_enough(outer_u1_avg, GT['outer_u1_avg']):
            log_error('outer_u1_avg mismatch')
            return False

        # ----------------------------------------------------
        # Total RF2 near-zero check
        # ----------------------------------------------------
        total_sum_rf2 = 0.0
        for val in RF_field.values:
            total_sum_rf2 += float(val.data[1])
        if abs(total_sum_rf2 - GT['total_sum_RF2']) > ABS_TOL_NEAR_ZERO:
            log_error('total_sum_RF2 mismatch: expected %.12f, got %.12f, diff %.12f' % (GT['total_sum_RF2'], total_sum_rf2, abs(total_sum_rf2 - GT['total_sum_RF2'])))
            return False

        # ----------------------------------------------------
        # Stress metrics + radial bands
        # ----------------------------------------------------
        element_avg_r = {}
        for elem in inst.elements:
            rs = []
            for nid in elem.connectivity:
                node = inst.getNodeFromLabel(nid)
                rs.append(float(node.coordinates[0]))
            if len(rs) > 0:
                element_avg_r[int(elem.label)] = sum(rs) / float(len(rs))

        max_mises = -1.0
        max_abs_S11 = -1.0
        max_abs_S22 = -1.0
        max_abs_S33 = -1.0
        inner_band_max_mises = -1.0
        outer_band_max_mises = -1.0

        for val in S_field.values:
            try:
                mises = float(val.mises)
            except:
                mises = None

            if mises is not None:
                max_mises = max(max_mises, mises)

            data = val.data
            if len(data) >= 1:
                max_abs_S11 = max(max_abs_S11, abs(float(data[0])))
            if len(data) >= 2:
                max_abs_S22 = max(max_abs_S22, abs(float(data[1])))
            if len(data) >= 3:
                max_abs_S33 = max(max_abs_S33, abs(float(data[2])))

            if mises is None:
                continue

            try:
                eid = int(val.elementLabel)
            except:
                continue

            if eid not in element_avg_r:
                continue

            ravg = element_avg_r[eid]
            if abs(ravg - 52.5) <= 3.0 + ABS_TOL_COORD:
                inner_band_max_mises = max(inner_band_max_mises, mises)
            if abs(ravg - 97.5) <= 3.0 + ABS_TOL_COORD:
                outer_band_max_mises = max(outer_band_max_mises, mises)

        if not close_enough(max_mises, GT['max_mises'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            log_error('max_mises mismatch')
            return False
        if not close_enough(max_abs_S11, GT['max_abs_S11'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            log_error('max_abs_S11 mismatch')
            return False
        if not close_enough(max_abs_S22, GT['max_abs_S22'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            log_error('max_abs_S22 mismatch')
            return False
        if not close_enough(max_abs_S33, GT['max_abs_S33'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            log_error('max_abs_S33 mismatch')
            return False
        if not close_enough(inner_band_max_mises, GT['inner_band_max_mises'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            log_error('inner_band_max_mises mismatch')
            return False
        if not close_enough(outer_band_max_mises, GT['outer_band_max_mises'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            log_error('outer_band_max_mises mismatch')
            return False

        return True

    except Exception as e:
        log_error('Exception in check_odb_file: %s' % str(e))
        log_error(traceback.format_exc())
        return False

    finally:
        try:
            if odb is not None:
                odb.close()
        except:
            pass

# ============================================================
# 7. Main
# ============================================================

try:
    passed = check_cae_file() and check_odb_file()
except Exception as e:
    log_error('Top-level exception: %s' % str(e))
    log_error(traceback.format_exc())
    passed = False

output_result(passed)