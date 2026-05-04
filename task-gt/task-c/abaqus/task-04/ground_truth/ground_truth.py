# -*- coding: utf-8 -*-
# extract_truth_job_tension.py
# Run with:
#     abaqus cae noGUI=extract_truth_job_tension.py
#
# Purpose:
#     Extract ground-truth values from:
#         <Desktop>\Job-Tension.cae
#         <Desktop>\Job-Tension.odb
#
# Output:
#     <Desktop>\truth_values_job_tension.json
#
# This script is designed for the Job-Tension.py model:
#     100 mm x 10 mm x 10 mm 3D solid bar
#     Steel, E=210000 MPa, nu=0.3
#     Step-Load
#     X=0 fixed, X=100 loaded in +X
#     C3D8R, global seed = 5 mm

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import os
import sys
import json
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
OUT_PATH = os.path.join(desktop, 'truth_values_job_tension.json')

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

    # In the intended final assembly coordinates:
    # X span = 100, Y span = 10, Z span = 10.
    if abs(ext['x_span'] - 100.0) < 1.0e-6 and \
       abs(ext['y_span'] - 10.0) < 1.0e-6 and \
       abs(ext['z_span'] - 10.0) < 1.0e-6:
        return 'GLOBAL_X_LENGTH'

    # In some cases, part/local coordinates may be reported:
    # X span = 10, Y span = 10, Z span = 100.
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


def get_best_model_from_cae():
    best_model_name = None
    best_model = None
    best_score = -1

    for model_name in mdb.models.keys():
        model = mdb.models[model_name]
        score = 0

        if get_step_key(model.steps, STEP_NAME) is not None:
            score += 100000

        try:
            for part_name in model.parts.keys():
                part = model.parts[part_name]
                score += len(part.nodes) + 2 * len(part.elements)
        except:
            pass

        try:
            for inst_name in model.rootAssembly.instances.keys():
                inst = model.rootAssembly.instances[inst_name]
                score += len(inst.nodes) + 2 * len(inst.elements)
        except:
            pass

        if score > best_score:
            best_score = score
            best_model_name = model_name
            best_model = model

    return best_model_name, best_model


def get_best_part_or_instance_mesh_from_cae(model):
    best_source = None
    best_obj = None
    best_nodes = -1
    best_elements = -1
    best_counts = {}

    try:
        for part_name in model.parts.keys():
            part = model.parts[part_name]
            try:
                n = len(part.nodes)
                e = len(part.elements)
                if n > best_nodes:
                    best_source = 'part:' + part_name
                    best_obj = part
                    best_nodes = n
                    best_elements = e
                    best_counts = get_element_type_counts(part.elements)
            except:
                pass
    except:
        pass

    try:
        for inst_name in model.rootAssembly.instances.keys():
            inst = model.rootAssembly.instances[inst_name]
            try:
                n = len(inst.nodes)
                e = len(inst.elements)
                if n > best_nodes:
                    best_source = 'instance:' + inst_name
                    best_obj = inst
                    best_nodes = n
                    best_elements = e
                    best_counts = get_element_type_counts(inst.elements)
            except:
                pass
    except:
        pass

    return best_source, best_obj, best_nodes, best_elements, best_counts


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


# ============================================================
# 3. Extract truth
# ============================================================

truth = {}
truth['cae_path'] = CAE_PATH
truth['odb_path'] = ODB_PATH
truth['cae_exists'] = os.path.exists(CAE_PATH)
truth['odb_exists'] = os.path.exists(ODB_PATH)

try:
    # --------------------------------------------------------
    # CAE truth
    # --------------------------------------------------------
    if truth['cae_exists']:
        openMdb(pathName=CAE_PATH)

        model_name, model = get_best_model_from_cae()
        truth['model_name'] = model_name

        if model is not None:
            truth['step_names_in_cae'] = list(model.steps.keys())
            truth['has_step_load'] = get_step_key(model.steps, STEP_NAME) is not None

            truth['material_truth'] = get_materials_truth(model)
            truth['section_truth'] = get_sections_truth(model)
            truth['load_names'] = sorted(list(model.loads.keys()))
            truth['loads'] = get_loads_truth(model)
            truth['bc_names'] = sorted(list(model.boundaryConditions.keys()))
            truth['boundary_conditions'] = get_bcs_truth(model)

            source, obj, n_nodes, n_elements, elem_counts = get_best_part_or_instance_mesh_from_cae(model)
            truth['cae_mesh_source'] = source
            truth['cae_num_nodes'] = int(n_nodes)
            truth['cae_num_elements'] = int(n_elements)
            truth['cae_element_types'] = elem_counts

            try:
                ext = coord_extents_from_nodes(obj.nodes)
                truth['cae_geometry_extents'] = ext
                truth['cae_coordinate_mode'] = infer_coordinate_mode(ext)
            except:
                truth['cae_geometry_extents'] = None
                truth['cae_coordinate_mode'] = 'UNKNOWN'

            # Get main assembly instance information as well.
            try:
                inst_name, inst = get_main_instance(model.rootAssembly)
                truth['cae_main_instance_name'] = inst_name
                truth['cae_main_instance_num_nodes'] = len(inst.nodes)
                truth['cae_main_instance_num_elements'] = len(inst.elements)
                truth['cae_main_instance_element_types'] = get_element_type_counts(inst.elements)
                truth['cae_main_instance_extents'] = coord_extents_from_nodes(inst.nodes)
                truth['cae_main_instance_coordinate_mode'] = infer_coordinate_mode(
                    truth['cae_main_instance_extents']
                )
            except:
                truth['cae_main_instance_name'] = None

    # --------------------------------------------------------
    # ODB truth
    # --------------------------------------------------------
    if truth['odb_exists']:
        odb = openOdb(path=ODB_PATH, readOnly=True)

        try:
            truth['odb_step_names'] = list(odb.steps.keys())
            truth['odb_has_step_load'] = get_step_key(odb.steps, STEP_NAME) is not None

            try:
                truth['odb_job_status'] = str(odb.diagnosticData.jobStatus)
            except:
                truth['odb_job_status'] = None

            inst_name, inst = get_main_instance(odb.rootAssembly)
            truth['odb_main_instance_name'] = inst_name
            truth['odb_num_nodes'] = len(inst.nodes)
            truth['odb_num_elements'] = len(inst.elements)
            truth['odb_element_types'] = get_element_type_counts(inst.elements)

            ext = coord_extents_from_nodes(inst.nodes)
            truth['odb_geometry_extents'] = ext
            truth['odb_coordinate_mode'] = infer_coordinate_mode(ext)

            step_key = get_step_key(odb.steps, STEP_NAME)
            truth['odb_resolved_step_name'] = step_key

            if step_key is not None:
                step = odb.steps[step_key]
                truth['odb_num_frames'] = len(step.frames)

                if len(step.frames) > 0:
                    last_frame = step.frames[-1]
                    truth['last_frame_value'] = float(last_frame.frameValue)
                    truth['last_frame_description'] = str(last_frame.description)

                    truth['field_output_names'] = list(last_frame.fieldOutputs.keys())

                    # ------------------------------------------------
                    # U field truth
                    # ------------------------------------------------
                    if 'U' in last_frame.fieldOutputs.keys():
                        U_field = last_frame.fieldOutputs['U']

                        max_u_magnitude = -1.0
                        max_abs_u1 = -1.0
                        max_abs_u2 = -1.0
                        max_abs_u3 = -1.0

                        max_u1 = None
                        min_u1 = None
                        max_u2 = None
                        min_u2 = None
                        max_u3 = None
                        min_u3 = None

                        for val in U_field.values:
                            u1 = float(val.data[0])
                            u2 = float(val.data[1])
                            u3 = float(val.data[2])
                            umag = vec_mag(val.data)

                            max_u_magnitude = max(max_u_magnitude, umag)
                            max_abs_u1 = max(max_abs_u1, abs(u1))
                            max_abs_u2 = max(max_abs_u2, abs(u2))
                            max_abs_u3 = max(max_abs_u3, abs(u3))

                            max_u1 = u1 if max_u1 is None else max(max_u1, u1)
                            min_u1 = u1 if min_u1 is None else min(min_u1, u1)
                            max_u2 = u2 if max_u2 is None else max(max_u2, u2)
                            min_u2 = u2 if min_u2 is None else min(min_u2, u2)
                            max_u3 = u3 if max_u3 is None else max(max_u3, u3)
                            min_u3 = u3 if min_u3 is None else min(min_u3, u3)

                        truth['max_u_magnitude'] = float(max_u_magnitude)
                        truth['max_abs_u1'] = float(max_abs_u1)
                        truth['max_abs_u2'] = float(max_abs_u2)
                        truth['max_abs_u3'] = float(max_abs_u3)
                        truth['max_u1'] = float(max_u1)
                        truth['min_u1'] = float(min_u1)
                        truth['max_u2'] = float(max_u2)
                        truth['min_u2'] = float(min_u2)
                        truth['max_u3'] = float(max_u3)
                        truth['min_u3'] = float(min_u3)

                        # Query U1 at the free-end center.
                        # Intended final/global target: (100,5,5)
                        # Compatibility part-local target: (5,5,100)
                        center_label, center_dist, center_coord, matched_target = find_nearest_node(
                            inst,
                            targets=((100.0, 5.0, 5.0), (5.0, 5.0, 100.0))
                        )

                        truth['free_end_center_node_label'] = center_label
                        truth['free_end_center_node_distance'] = float(center_dist)
                        truth['free_end_center_node_coordinate'] = center_coord
                        truth['free_end_center_matched_target'] = matched_target

                        center_val = get_field_value_by_node(U_field, center_label)
                        if center_val is not None:
                            truth['free_end_center_U'] = tuple(float(x) for x in center_val.data)
                            truth['free_end_center_U1'] = float(center_val.data[0])
                            truth['free_end_center_U2'] = float(center_val.data[1])
                            truth['free_end_center_U3'] = float(center_val.data[2])
                        else:
                            truth['free_end_center_U'] = None
                            truth['free_end_center_U1'] = None
                            truth['free_end_center_U2'] = None
                            truth['free_end_center_U3'] = None

                    # ------------------------------------------------
                    # RF field truth
                    # ------------------------------------------------
                    if 'RF' in last_frame.fieldOutputs.keys():
                        RF_field = last_frame.fieldOutputs['RF']
                        node_coord = get_node_coord_dict(inst)

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

                        truth['fixed_end_node_count'] = len(fixed_labels)
                        truth['free_end_node_count'] = len(free_labels)

                        fixed_sum_rf = [0.0, 0.0, 0.0]
                        free_sum_rf = [0.0, 0.0, 0.0]
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

                            if label in free_labels:
                                free_sum_rf[0] += rf1
                                free_sum_rf[1] += rf2
                                free_sum_rf[2] += rf3

                        truth['fixed_end_sum_RF1'] = float(fixed_sum_rf[0])
                        truth['fixed_end_sum_RF2'] = float(fixed_sum_rf[1])
                        truth['fixed_end_sum_RF3'] = float(fixed_sum_rf[2])
                        truth['free_end_sum_RF1'] = float(free_sum_rf[0])
                        truth['free_end_sum_RF2'] = float(free_sum_rf[1])
                        truth['free_end_sum_RF3'] = float(free_sum_rf[2])
                        truth['total_sum_RF1'] = float(total_sum_rf[0])
                        truth['total_sum_RF2'] = float(total_sum_rf[1])
                        truth['total_sum_RF3'] = float(total_sum_rf[2])

                    # ------------------------------------------------
                    # S field truth
                    # ------------------------------------------------
                    if 'S' in last_frame.fieldOutputs.keys():
                        S_field = last_frame.fieldOutputs['S']

                        max_mises = -1.0
                        min_mises = None

                        max_s11 = None
                        min_s11 = None
                        max_abs_s11 = -1.0

                        max_s22 = None
                        min_s22 = None
                        max_abs_s22 = -1.0

                        max_s33 = None
                        min_s33 = None
                        max_abs_s33 = -1.0

                        for val in S_field.values:
                            try:
                                mises = float(val.mises)
                                max_mises = max(max_mises, mises)
                                min_mises = mises if min_mises is None else min(min_mises, mises)
                            except:
                                pass

                            data = val.data

                            if len(data) >= 1:
                                s11 = float(data[0])
                                max_s11 = s11 if max_s11 is None else max(max_s11, s11)
                                min_s11 = s11 if min_s11 is None else min(min_s11, s11)
                                max_abs_s11 = max(max_abs_s11, abs(s11))

                            if len(data) >= 2:
                                s22 = float(data[1])
                                max_s22 = s22 if max_s22 is None else max(max_s22, s22)
                                min_s22 = s22 if min_s22 is None else min(min_s22, s22)
                                max_abs_s22 = max(max_abs_s22, abs(s22))

                            if len(data) >= 3:
                                s33 = float(data[2])
                                max_s33 = s33 if max_s33 is None else max(max_s33, s33)
                                min_s33 = s33 if min_s33 is None else min(min_s33, s33)
                                max_abs_s33 = max(max_abs_s33, abs(s33))

                        truth['max_mises'] = float(max_mises)
                        truth['min_mises'] = float(min_mises) if min_mises is not None else None

                        truth['max_s11'] = float(max_s11) if max_s11 is not None else None
                        truth['min_s11'] = float(min_s11) if min_s11 is not None else None
                        truth['max_abs_s11'] = float(max_abs_s11)

                        truth['max_s22'] = float(max_s22) if max_s22 is not None else None
                        truth['min_s22'] = float(min_s22) if min_s22 is not None else None
                        truth['max_abs_s22'] = float(max_abs_s22)

                        truth['max_s33'] = float(max_s33) if max_s33 is not None else None
                        truth['min_s33'] = float(min_s33) if min_s33 is not None else None
                        truth['max_abs_s33'] = float(max_abs_s33)

                        # Central/midspan stress average.
                        centroids = get_element_centroids(inst)
                        mode = infer_coordinate_mode(ext)

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

                            # Include elements with centroids near the middle.
                            if abs(length_coord - 50.0) <= 5.1:
                                try:
                                    central_s11.append(float(val.data[0]))
                                except:
                                    pass
                                try:
                                    central_mises.append(float(val.mises))
                                except:
                                    pass

                        truth['central_stress_value_count'] = len(central_s11)

                        if len(central_s11) > 0:
                            truth['central_avg_s11'] = float(sum(central_s11) / len(central_s11))
                            truth['central_min_s11'] = float(min(central_s11))
                            truth['central_max_s11'] = float(max(central_s11))
                        else:
                            truth['central_avg_s11'] = None
                            truth['central_min_s11'] = None
                            truth['central_max_s11'] = None

                        if len(central_mises) > 0:
                            truth['central_avg_mises'] = float(sum(central_mises) / len(central_mises))
                            truth['central_min_mises'] = float(min(central_mises))
                            truth['central_max_mises'] = float(max(central_mises))
                        else:
                            truth['central_avg_mises'] = None
                            truth['central_min_mises'] = None
                            truth['central_max_mises'] = None

        finally:
            odb.close()

except Exception:
    truth['extraction_error'] = traceback.format_exc()

# ============================================================
# 4. Save JSON and print
# ============================================================

with open(OUT_PATH, 'w') as f:
    json.dump(truth, f, indent=2, sort_keys=True)

try:
    sys.__stdout__.write('TRUE_VALUES_JSON_PATH = ' + OUT_PATH + '\n')
    sys.__stdout__.write(json.dumps(truth, indent=2, sort_keys=True) + '\n')
    sys.__stdout__.flush()
except:
    print('TRUE_VALUES_JSON_PATH = ' + OUT_PATH)
    print(json.dumps(truth, indent=2, sort_keys=True))
