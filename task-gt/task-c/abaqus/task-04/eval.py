# -*- coding: utf-8 -*-
# extract_truth_job_tension.py
# Run with:
#     abaqus cae noGUI=extract_truth_job_tension.py
#
# Purpose:
#     Evaluate the Job-Tension model and output a boolean result.
#
# Output:
#     True
#     or
#     False

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

def get_desktop():
    candidates = []

    userprofile = os.environ.get('USERPROFILE', None)
    if userprofile:
        candidates.append(os.path.join(userprofile, 'Desktop'))

    candidates.append(r'C:\Users\Administrator\Desktop')
    candidates.append(r'C:\Users\User\Desktop')

    for d in candidates:
        if os.path.exists(os.path.join(d, 'Job-Tension.cae')) or \
           os.path.exists(os.path.join(d, 'Job-Tension.odb')):
            return d

    for d in candidates:
        if os.path.isdir(d):
            return d

    return r'C:\Users\Administrator\Desktop'


desktop = get_desktop()

CAE_PATH = os.path.join(desktop, 'Job-Tension.cae')
ODB_PATH = os.path.join(desktop, 'Job-Tension.odb')
STEP_NAME = 'Step-Load'


# ============================================================
# 2. Utility functions
# ============================================================

def vec_mag(v):
    s = 0.0
    for x in v:
        s += float(x) * float(x)
    return math.sqrt(s)


def get_step_key(steps, target):
    target_upper = target.upper()
    for k in steps.keys():
        if k.upper() == target_upper:
            return k
    return None


def get_main_instance(root_assembly):
    best_key = None
    best_nodes = -1

    for k in root_assembly.instances.keys():
        inst = root_assembly.instances[k]
        try:
            n = len(inst.nodes)
        except:
            n = -1

        if n > best_nodes:
            best_nodes = n
            best_key = k

    if best_key is None:
        return None, None

    return best_key, root_assembly.instances[best_key]


def get_element_type_counts(elements):
    counts = {}
    for elem in elements:
        try:
            etype = str(elem.type)
        except:
            etype = 'UNKNOWN'
        counts[etype] = counts.get(etype, 0) + 1
    return counts


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
    best_coord = None
    best_target = None

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
                best_label = node.label
                best_distance = d
                best_coord = (x, y, z)
                best_target = target

    return best_label, best_distance, best_coord, best_target


def get_field_value_by_node(field, node_label):
    for val in field.values:
        if val.nodeLabel == node_label:
            return val
    return None


def get_node_coord_dict(inst):
    node_coord = {}
    for node in inst.nodes:
        node_coord[node.label] = tuple(float(x) for x in node.coordinates)
    return node_coord


def get_element_centroids(inst):
    node_coord = get_node_coord_dict(inst)
    centroids = {}

    for elem in inst.elements:
        xs = []
        ys = []
        zs = []

        for label in elem.connectivity:
            if label in node_coord:
                x, y, z = node_coord[label]
                xs.append(x)
                ys.append(y)
                zs.append(z)

        if len(xs) > 0:
            centroids[elem.label] = (
                sum(xs) / len(xs),
                sum(ys) / len(ys),
                sum(zs) / len(zs)
            )

    return centroids


def get_materials_truth(model):
    out = {}

    for mat_name in model.materials.keys():
        mat = model.materials[mat_name]
        item = {}

        try:
            E, nu = mat.elastic.table[0]
            item['youngs_modulus'] = float(E)
            item['poisson_ratio'] = float(nu)
        except:
            item['youngs_modulus'] = None
            item['poisson_ratio'] = None

        out[mat_name] = item

    return out


def get_sections_truth(model):
    out = {}

    for sec_name in model.sections.keys():
        sec = model.sections[sec_name]
        item = {}
        item['type'] = sec.__class__.__name__

        try:
            item['material'] = str(sec.material)
        except:
            item['material'] = None

        try:
            item['thickness'] = float(sec.thickness)
        except:
            item['thickness'] = None

        out[sec_name] = item

    return out


def get_loads_truth(model):
    out = {}

    for load_name in model.loads.keys():
        load = model.loads[load_name]
        item = {}
        item['type'] = load.__class__.__name__

        try:
            item['magnitude'] = float(load.magnitude)
        except:
            item['magnitude'] = None

        try:
            item['directionVector'] = str(load.directionVector)
        except:
            item['directionVector'] = None

        try:
            item['createStepName'] = str(load.createStepName)
        except:
            item['createStepName'] = None

        out[load_name] = item

    return out


def get_bcs_truth(model):
    out = {}

    for bc_name in model.boundaryConditions.keys():
        bc = model.boundaryConditions[bc_name]
        item = {}
        item['type'] = bc.__class__.__name__

        for dof in ['u1', 'u2', 'u3', 'ur1', 'ur2', 'ur3']:
            try:
                value = getattr(bc, dof)
                if value is None:
                    item[dof] = None
                else:
                    item[dof] = str(value)
            except:
                item[dof] = None

        out[bc_name] = item

    return out


def close_enough(obs, exp, rel_tol=1.0e-4, abs_tol=1.0e-6):
    try:
        obsf = float(obs)
        expf = float(exp)
    except Exception:
        return False
    tol = max(float(abs_tol), float(rel_tol) * abs(expf))
    return abs(obsf - expf) <= tol


def compare_dict_value(actual, expected):
    if expected is None:
        return actual is None
    if isinstance(expected, bool):
        return bool(actual) == expected
    if isinstance(expected, (int, float)):
        return close_enough(actual, expected)
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)):
            return False
        if len(actual) != len(expected):
            return False
        for a, e in zip(actual, expected):
            if not compare_dict_value(a, e):
                return False
        return True
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return False
        for key, exp_value in expected.items():
            if key not in actual:
                return False
            if not compare_dict_value(actual[key], exp_value):
                return False
        return True
    return actual == expected


# ============================================================
# 3. Evaluate
# ============================================================

def check_task():
    expected = {
        'cae_exists': True,
        'odb_exists': True,
        'has_step_load': True,
        'odb_has_step_load': True,
        'odb_num_frames': 2,
        'last_frame_value': 1.0,
        'cae_num_nodes': 189,
        'cae_num_elements': 80,
        'odb_num_nodes': 189,
        'odb_num_elements': 80,
        'cae_element_types': {'C3D8R': 80},
        'odb_element_types': {'C3D8R': 80},
        'material_truth': {'Steel': {'poisson_ratio': 0.3, 'youngs_modulus': 210000.0}},
        'section_truth': {'Solid-Section-Steel': {'material': 'Steel', 'thickness': None, 'type': 'HomogeneousSolidSection'}},
        'max_abs_u1': 0.004753996152430773,
        'free_end_center_U1': 0.004753996152430773,
        'fixed_end_sum_RF1': -1000.0000152587891,
        'total_sum_RF1': -1000.0000152587891,
        'central_avg_s11': 10.0,
        'central_avg_mises': 9.994122982025146,
        'free_end_center_node_distance': 0.0,
        'odb_job_status': 'JOB_STATUS_COMPLETED_SUCCESSFULLY',
    }

    if not os.path.exists(CAE_PATH):
        return False
    if not os.path.exists(ODB_PATH):
        return False

    try:
        openMdb(pathName=CAE_PATH)
    except Exception:
        return False

    truth = {}
    odb = None
    try:
        truth['cae_exists'] = True
        truth['odb_exists'] = True

        model_name = None
        model = None
        for name in mdb.models.keys():
            model_name = name
            model = mdb.models[name]
            break
        if model is None:
            return False

        truth['has_step_load'] = get_step_key(model.steps, STEP_NAME) is not None
        truth['material_truth'] = get_materials_truth(model)
        truth['section_truth'] = get_sections_truth(model)

        source, obj, n_nodes, n_elements, elem_counts = None, None, -1, -1, {}
        try:
            for part_name in model.parts.keys():
                part = model.parts[part_name]
                source = 'part:' + part_name
                obj = part
                n_nodes = len(part.nodes)
                n_elements = len(part.elements)
                elem_counts = get_element_type_counts(part.elements)
                break
        except Exception:
            pass
        truth['cae_num_nodes'] = int(n_nodes)
        truth['cae_num_elements'] = int(n_elements)
        truth['cae_element_types'] = elem_counts

        try:
            ext = coord_extents_from_nodes(obj.nodes)
            truth['cae_coordinate_mode'] = infer_coordinate_mode(ext)
        except Exception:
            truth['cae_coordinate_mode'] = 'UNKNOWN'

        odb = openOdb(path=ODB_PATH, readOnly=True)
        truth['odb_has_step_load'] = get_step_key(odb.steps, STEP_NAME) is not None
        try:
            truth['odb_job_status'] = str(odb.diagnosticData.jobStatus)
        except Exception:
            truth['odb_job_status'] = None

        inst_name, inst = get_main_instance(odb.rootAssembly)
        if inst is None:
            return False
        truth['odb_main_instance_name'] = inst_name
        truth['odb_num_nodes'] = len(inst.nodes)
        truth['odb_num_elements'] = len(inst.elements)
        truth['odb_element_types'] = get_element_type_counts(inst.elements)

        ext = coord_extents_from_nodes(inst.nodes)
        truth['odb_coordinate_mode'] = infer_coordinate_mode(ext)

        step_key = get_step_key(odb.steps, STEP_NAME)
        if step_key is None:
            return False
        step = odb.steps[step_key]
        truth['odb_num_frames'] = len(step.frames)
        if len(step.frames) == 0:
            return False

        last_frame = step.frames[-1]
        truth['last_frame_value'] = float(last_frame.frameValue)
        if not close_enough(truth['last_frame_value'], expected['last_frame_value'], rel_tol=1.0e-8, abs_tol=1.0e-10):
            return False

        if 'U' not in last_frame.fieldOutputs.keys():
            return False
        if 'RF' not in last_frame.fieldOutputs.keys():
            return False
        if 'S' not in last_frame.fieldOutputs.keys():
            return False

        U_field = last_frame.fieldOutputs['U']
        RF_field = last_frame.fieldOutputs['RF']
        S_field = last_frame.fieldOutputs['S']

        node_coord = get_node_coord_dict(inst)
        max_u_magnitude = -1.0
        max_abs_u1 = -1.0
        max_abs_u2 = -1.0
        min_u2 = 1.0e100

        for val in U_field.values:
            try:
                u1 = float(val.data[0])
                u2 = float(val.data[1])
                u3 = float(val.data[2])
                umag = vec_mag(val.data)
            except Exception:
                continue
            max_u_magnitude = max(max_u_magnitude, umag)
            max_abs_u1 = max(max_abs_u1, abs(u1))
            max_abs_u2 = max(max_abs_u2, abs(u2))
            min_u2 = min(min_u2, u2)

        truth['max_abs_u1'] = float(max_abs_u1)

        center_label, center_dist, center_coord, matched_target = find_nearest_node(
            inst,
            targets=((100.0, 5.0, 5.0), (5.0, 5.0, 100.0))
        )
        truth['free_end_center_node_distance'] = float(center_dist)
        center_val = get_field_value_by_node(U_field, center_label)
        if center_val is None:
            return False
        truth['free_end_center_U1'] = float(center_val.data[0])

        fixed_labels = set()
        free_labels = set()
        mode = infer_coordinate_mode(ext)
        if mode == 'GLOBAL_X_LENGTH':
            fixed_coord = ext['x_min']
            free_coord = ext['x_max']
            for label, coord in node_coord.items():
                if abs(coord[0] - fixed_coord) <= 1.0e-8:
                    fixed_labels.add(label)
                if abs(coord[0] - free_coord) <= 1.0e-8:
                    free_labels.add(label)
        elif mode == 'LOCAL_Z_LENGTH':
            fixed_coord = ext['z_min']
            free_coord = ext['z_max']
            for label, coord in node_coord.items():
                if abs(coord[2] - fixed_coord) <= 1.0e-8:
                    fixed_labels.add(label)
                if abs(coord[2] - free_coord) <= 1.0e-8:
                    free_labels.add(label)
        else:
            return False

        fixed_sum_rf = [0.0, 0.0, 0.0]
        total_sum_rf = [0.0, 0.0, 0.0]

        for val in RF_field.values:
            label = val.nodeLabel
            rf1 = float(val.data[0])
            rf2 = float(val.data[1])
            rf3 = float(val.data[2])
            total_sum_rf[0] += rf1
            total_sum_rf[1] += rf2
            total_sum_rf[2] += rf3
            if label in fixed_labels:
                fixed_sum_rf[0] += rf1
                fixed_sum_rf[1] += rf2
                fixed_sum_rf[2] += rf3

        truth['fixed_end_sum_RF1'] = float(fixed_sum_rf[0])
        truth['total_sum_RF1'] = float(total_sum_rf[0])

        centroids = get_element_centroids(inst)
        central_s11 = []
        central_mises = []
        for val in S_field.values:
            el = val.elementLabel
            if el not in centroids:
                continue
            c = centroids[el]
            if mode == 'GLOBAL_X_LENGTH':
                length_coord = c[0]
            elif mode == 'LOCAL_Z_LENGTH':
                length_coord = c[2]
            else:
                continue
            if abs(length_coord - 50.0) <= 5.1:
                try:
                    central_s11.append(float(val.data[0]))
                except Exception:
                    pass
                try:
                    central_mises.append(float(val.mises))
                except Exception:
                    pass

        if len(central_s11) == 0 or len(central_mises) == 0:
            return False
        truth['central_avg_s11'] = float(sum(central_s11) / len(central_s11))
        truth['central_avg_mises'] = float(sum(central_mises) / len(central_mises))

        for key, exp_value in expected.items():
            if key not in truth:
                return False
            if not compare_dict_value(truth[key], exp_value):
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


def output_result(value):
    if value:
        sys.__stdout__.write('True\n')
    else:
        sys.__stdout__.write('False\n')
    sys.__stdout__.flush()


def main():
    try:
        ok = check_task()
    except Exception:
        ok = False
    output_result(ok)


if __name__ == '__main__':
    main()
