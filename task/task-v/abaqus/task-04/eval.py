# -*- coding: utf-8 -*-
# Evaluator for task-04
# Run with:
#   abaqus cae noGUI=eval.py
#
# Final stdout must be exactly one line:
#   True
# or
#   False

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import os
import sys
import math

# ============================================================
# 1. Paths
# ============================================================

def get_desktop():
    candidates = []

    userprofile = os.environ.get('USERPROFILE', None)
    if userprofile:
        candidates.append(os.path.join(userprofile, 'Desktop'))

    candidates.append(r'C:\Users\user\Desktop')
    candidates.append(r'C:\Users\User\Desktop')

    for d in candidates:
        if os.path.exists(os.path.join(d, 'Job-Tension.cae')) or \
           os.path.exists(os.path.join(d, 'Job-Tension.odb')):
            return d

    for d in candidates:
        if os.path.isdir(d):
            return d

    return r'C:\Users\user\Desktop'


desktop = get_desktop()
cae_path = os.path.join(desktop, 'Job-Tension.cae')
odb_path = os.path.join(desktop, 'Job-Tension.odb')

# ============================================================
# 2. Fixed ground truth (from task-04 ground_truth/truth_values.json)
# ============================================================

GT = {
    'node_count': 189,
    'element_count': 80,
    'step_name': 'Step-Load',
    'last_frame_value': 1.0,

    'free_end_center_u1': 0.004753996152430773,
    'max_mises': 10.700273513793945,
    'max_abs_u1': 0.004753996152430773,
    'max_abs_u2': 0.00010843262862181291,
    'max_abs_u3': 0.00010843262862181291,
    'central_avg_s11': 10.0,

    'fixed_end_sum_rf1': -1000.0000152587891
}

# ============================================================
# 3. Tolerances
# ============================================================

REL_TOL = 5.0e-3
ABS_TOL_SMALL = 1.0e-8
ABS_TOL_NEAR_ZERO = 1.0e-6
ABS_TOL_FORCE = 1.0e-3
ABS_TOL_COORD = 1.0e-8

# ============================================================
# 4. Utility functions
# ============================================================

def has_forbidden_py_file(desktop_path):
    try:
        entries = os.listdir(desktop_path)
    except Exception:
        return True

    for name in entries:
        try:
            full_path = os.path.join(desktop_path, name)
            if not os.path.isfile(full_path):
                continue
        except Exception:
            return True

        lower_name = name.lower()
        if lower_name.endswith('.py') and lower_name != 'eval.py':
            return True

    return False


def output_result(value):
    text = 'True\n' if value else 'False\n'
    try:
        sys.__stdout__.write(text)
        sys.__stdout__.flush()
    except Exception:
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except Exception:
            pass


def close_enough(obs, exp, rel_tol=REL_TOL, abs_tol=ABS_TOL_SMALL):
    obs = float(obs)
    exp = float(exp)
    tol = max(float(abs_tol), float(rel_tol) * abs(exp))
    return abs(obs - exp) <= tol


def get_step_key(steps, target):
    tu = str(target).upper()
    for k in steps.keys():
        if str(k).upper() == tu:
            return k
    return None


def get_main_instance(root_assembly):
    best_key = None
    best_nodes = -1

    for k in root_assembly.instances.keys():
        inst = root_assembly.instances[k]
        try:
            n = len(inst.nodes)
        except Exception:
            n = -1

        if n > best_nodes:
            best_nodes = n
            best_key = k

    if best_key is None:
        return None

    return root_assembly.instances[best_key]


def coord_extents_from_nodes(nodes):
    xs = []
    ys = []
    zs = []

    for node in nodes:
        x, y, z = node.coordinates
        xs.append(float(x))
        ys.append(float(y))
        zs.append(float(z))

    if len(xs) == 0:
        return None

    return {
        'x_min': min(xs),
        'x_max': max(xs),
        'y_min': min(ys),
        'y_max': max(ys),
        'z_min': min(zs),
        'z_max': max(zs),
        'x_span': max(xs) - min(xs),
        'y_span': max(ys) - min(ys),
        'z_span': max(zs) - min(zs)
    }


def infer_coordinate_mode(ext):
    if ext is None:
        return 'UNKNOWN'

    if abs(ext['x_span'] - 100.0) < 1.0e-6 and \
       abs(ext['y_span'] - 10.0) < 1.0e-6 and \
       abs(ext['z_span'] - 10.0) < 1.0e-6:
        return 'GLOBAL_X_LENGTH'

    if abs(ext['x_span'] - 10.0) < 1.0e-6 and \
       abs(ext['y_span'] - 10.0) < 1.0e-6 and \
       abs(ext['z_span'] - 100.0) < 1.0e-6:
        return 'LOCAL_Z_LENGTH'

    return 'UNKNOWN'


def find_nearest_node(inst, targets):
    best_label = None
    best_distance = None

    for node in inst.nodes:
        x, y, z = node.coordinates
        x = float(x)
        y = float(y)
        z = float(z)

        for target in targets:
            d = math.sqrt(
                (x - target[0]) ** 2 +
                (y - target[1]) ** 2 +
                (z - target[2]) ** 2
            )

            if best_distance is None or d < best_distance:
                best_label = int(node.label)
                best_distance = d

    return best_label, best_distance


def get_field_value_by_node(field, node_label):
    for val in field.values:
        try:
            if int(val.nodeLabel) == int(node_label):
                return val
        except Exception:
            pass
    return None


def get_element_centroids(inst):
    node_coord = {}
    for node in inst.nodes:
        node_coord[int(node.label)] = (
            float(node.coordinates[0]),
            float(node.coordinates[1]),
            float(node.coordinates[2])
        )

    centroids = {}
    for elem in inst.elements:
        xs = []
        ys = []
        zs = []
        for nid in elem.connectivity:
            ni = int(nid)
            if ni in node_coord:
                x, y, z = node_coord[ni]
                xs.append(x)
                ys.append(y)
                zs.append(z)

        if len(xs) > 0:
            centroids[int(elem.label)] = (
                sum(xs) / float(len(xs)),
                sum(ys) / float(len(ys)),
                sum(zs) / float(len(zs))
            )

    return centroids


def get_best_model_from_cae():
    best_model = None
    best_score = -1

    for model_name in mdb.models.keys():
        model = mdb.models[model_name]
        score = 0

        if get_step_key(model.steps, GT['step_name']) is not None:
            score += 100000

        try:
            for part_name in model.parts.keys():
                part = model.parts[part_name]
                score += len(part.nodes) + 2 * len(part.elements)
        except Exception:
            pass

        try:
            for inst_name in model.rootAssembly.instances.keys():
                inst = model.rootAssembly.instances[inst_name]
                score += len(inst.nodes) + 2 * len(inst.elements)
        except Exception:
            pass

        if score > best_score:
            best_score = score
            best_model = model

    return best_model


def get_best_part_or_instance_mesh_from_cae(model):
    best_nodes = -1
    best_elements = -1

    try:
        for part_name in model.parts.keys():
            part = model.parts[part_name]
            try:
                n = len(part.nodes)
                e = len(part.elements)
                if n > best_nodes:
                    best_nodes = n
                    best_elements = e
            except Exception:
                pass
    except Exception:
        pass

    try:
        for inst_name in model.rootAssembly.instances.keys():
            inst = model.rootAssembly.instances[inst_name]
            try:
                n = len(inst.nodes)
                e = len(inst.elements)
                if n > best_nodes:
                    best_nodes = n
                    best_elements = e
            except Exception:
                pass
    except Exception:
        pass

    return best_nodes, best_elements

# ============================================================
# 5. CAE check
# ============================================================

def check_cae_file():
    if not os.path.exists(cae_path):
        return False

    try:
        openMdb(pathName=cae_path)
    except Exception:
        return False

    model = get_best_model_from_cae()
    if model is None:
        return False

    if get_step_key(model.steps, GT['step_name']) is None:
        return False

    n_nodes, n_elements = get_best_part_or_instance_mesh_from_cae(model)

    if int(n_nodes) != int(GT['node_count']):
        return False

    if int(n_elements) != int(GT['element_count']):
        return False

    return True

# ============================================================
# 6. ODB check
# ============================================================

def check_odb_file():
    if not os.path.exists(odb_path):
        return False

    odb = None

    try:
        odb = openOdb(path=odb_path, readOnly=True)

        inst = get_main_instance(odb.rootAssembly)
        if inst is None:
            return False

        if len(inst.nodes) != int(GT['node_count']):
            return False
        if len(inst.elements) != int(GT['element_count']):
            return False

        step_key = get_step_key(odb.steps, GT['step_name'])
        if step_key is None:
            return False

        step = odb.steps[step_key]
        if len(step.frames) == 0:
            return False

        last_frame = step.frames[-1]
        if not close_enough(last_frame.frameValue, GT['last_frame_value'], rel_tol=1.0e-8, abs_tol=1.0e-10):
            return False

        if 'U' not in last_frame.fieldOutputs.keys():
            return False
        if 'S' not in last_frame.fieldOutputs.keys():
            return False
        if 'RF' not in last_frame.fieldOutputs.keys():
            return False

        U_field = last_frame.fieldOutputs['U']
        S_field = last_frame.fieldOutputs['S']
        RF_field = last_frame.fieldOutputs['RF']

        # Displacement metrics
        max_abs_u1 = -1.0
        max_abs_u2 = -1.0
        max_abs_u3 = -1.0

        for val in U_field.values:
            try:
                u1 = float(val.data[0])
                u2 = float(val.data[1])
                u3 = float(val.data[2])
            except Exception:
                return False

            max_abs_u1 = max(max_abs_u1, abs(u1))
            max_abs_u2 = max(max_abs_u2, abs(u2))
            max_abs_u3 = max(max_abs_u3, abs(u3))

        if not close_enough(max_abs_u1, GT['max_abs_u1']):
            return False
        if not close_enough(max_abs_u2, GT['max_abs_u2']):
            return False
        if not close_enough(max_abs_u3, GT['max_abs_u3']):
            return False

        # U1 at free-end center (support both global/local coordinate conventions)
        center_label, center_dist = find_nearest_node(
            inst,
            targets=((100.0, 5.0, 5.0), (5.0, 5.0, 100.0))
        )

        if center_label is None:
            return False

        # Nearest-node fallback tolerance: ensure the point is actually found near expected location.
        if center_dist is None or float(center_dist) > 1.0:
            return False

        center_u = get_field_value_by_node(U_field, center_label)
        if center_u is None:
            return False

        center_u1 = float(center_u.data[0])
        if not close_enough(center_u1, GT['free_end_center_u1']):
            return False

        # Stress metrics
        max_mises = -1.0
        for val in S_field.values:
            try:
                vm = float(val.mises)
                max_mises = max(max_mises, vm)
            except Exception:
                pass

        if max_mises < 0.0:
            return False

        if not close_enough(max_mises, GT['max_mises']):
            return False

        # Central average S11 near midspan
        ext = coord_extents_from_nodes(inst.nodes)
        mode = infer_coordinate_mode(ext)
        centroids = get_element_centroids(inst)

        central_s11 = []
        for val in S_field.values:
            try:
                el = int(val.elementLabel)
            except Exception:
                continue

            if el not in centroids:
                continue

            c = centroids[el]
            if mode == 'GLOBAL_X_LENGTH':
                length_coord = c[0]
            elif mode == 'LOCAL_Z_LENGTH':
                length_coord = c[2]
            else:
                # default to global-X logic for unknown mode
                length_coord = c[0]

            if abs(float(length_coord) - 50.0) <= 5.1:
                try:
                    central_s11.append(float(val.data[0]))
                except Exception:
                    pass

        if len(central_s11) == 0:
            return False

        central_avg_s11 = sum(central_s11) / float(len(central_s11))
        if not close_enough(central_avg_s11, GT['central_avg_s11']):
            return False

        # Fixed-end reaction balance: sum RF1 at constrained end ~ -1000 N
        if ext is None:
            return False

        fixed_labels = set()
        if mode == 'LOCAL_Z_LENGTH':
            fixed_coord = ext['z_min']
            for node in inst.nodes:
                if abs(float(node.coordinates[2]) - float(fixed_coord)) <= ABS_TOL_COORD:
                    fixed_labels.add(int(node.label))
        else:
            fixed_coord = ext['x_min']
            for node in inst.nodes:
                if abs(float(node.coordinates[0]) - float(fixed_coord)) <= ABS_TOL_COORD:
                    fixed_labels.add(int(node.label))

        if len(fixed_labels) == 0:
            return False

        fixed_end_sum_rf1 = 0.0
        for val in RF_field.values:
            try:
                lab = int(val.nodeLabel)
            except Exception:
                continue
            if lab in fixed_labels:
                fixed_end_sum_rf1 += float(val.data[0])

        if not close_enough(fixed_end_sum_rf1, GT['fixed_end_sum_rf1'], rel_tol=REL_TOL, abs_tol=ABS_TOL_FORCE):
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

# ============================================================
# 7. Main
# ============================================================

def main():
    if has_forbidden_py_file(desktop):
        output_result(False)
        return

    try:
        passed = check_cae_file() and check_odb_file()
    except Exception:
        passed = False

    output_result(passed)


if __name__ == '__main__':
    main()
