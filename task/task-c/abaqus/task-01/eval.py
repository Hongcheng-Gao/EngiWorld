# -*- coding: utf-8 -*-
# eval_job_plate.py
# Run with:
# abaqus cae noGUI=eval_job_plate.py
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

# ============================================================
# 1. Paths
# ============================================================

desktop = os.path.join(
    os.environ.get('USERPROFILE', r'C:\Users\Administrator'),
    'Desktop'
)

cae_path = os.path.join(desktop, 'Job-Plate.cae')
odb_path = os.path.join(desktop, 'Job-Plate.odb')

# ============================================================
# 2. Hard-coded ground truth
# ============================================================

GT = {
    'node_count': 52,
    'element_count': 25,
    'step_name': 'Step-Pressure',
    'last_frame_value': 1.0,

    'max_U_magnitude': 152.08139268168213,
    'max_abs_U1': 2.068925142288208,
    'max_abs_U2': 152.08139038085938,
    'min_U2': -152.08139038085938,

    'top_node_count': 26,
    'top_x_min': 0.0,
    'top_x_max': 50.0,
    'top_axis_U2': -152.08139038085938,
    'top_outer_U2': -3.6246134127090032e-34,
    'top_max_abs_U2': 152.08139038085938,

    'outer_sum_RF2': 785.3981628417969,
    'total_constrained_sum_RF2': 785.3981628417969,

    'max_mises': 4.2418365478515625,
    'max_abs_S11': 0.02138274721801281,
    'max_abs_S22': 0.07418244332075119
}

# ============================================================
# 3. Tolerances
# ============================================================

REL_TOL = 1.0e-3
ABS_TOL_SMALL = 1.0e-6
ABS_TOL_FORCE = 1.0e-3
ABS_TOL_STRESS = 1.0e-6
ABS_TOL_COORD = 1.0e-8

# ============================================================
# 4. Utility functions
# ============================================================

def output_result(value):
    if value:
        sys.stdout.write('True\n')
    else:
        sys.stdout.write('False\n')
    sys.stdout.flush()

def close_enough(obs, exp, rel_tol=REL_TOL, abs_tol=ABS_TOL_SMALL):
    obs = float(obs)
    exp = float(exp)
    tol = max(abs_tol, rel_tol * abs(exp))
    return abs(obs - exp) <= tol

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
        if len(inst.nodes) > best_nodes:
            best_nodes = len(inst.nodes)
            best_key = k
    if best_key is None:
        return None
    return root_assembly.instances[best_key]

def check_cae_file():
    if not os.path.exists(cae_path):
        return False

    try:
        openMdb(pathName=cae_path)
    except:
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
    except:
        return False

    if max_nodes != GT['node_count']:
        return False

    if max_elements != GT['element_count']:
        return False

    return True

def check_odb_file():
    if not os.path.exists(odb_path):
        return False

    odb = None

    try:
        odb = openOdb(path=odb_path, readOnly=True)
        root_assembly = odb.rootAssembly

        inst = get_main_instance(root_assembly)
        if inst is None:
            return False

        if len(inst.nodes) != GT['node_count']:
            return False

        if len(inst.elements) != GT['element_count']:
            return False

        step_key = get_step_key(odb.steps, GT['step_name'])
        if step_key is None:
            return False

        step = odb.steps[step_key]
        if len(step.frames) == 0:
            return False

        last_frame = step.frames[-1]

        if not close_enough(
            last_frame.frameValue,
            GT['last_frame_value'],
            rel_tol=1.0e-8,
            abs_tol=1.0e-10
        ):
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

        node_coord = {}
        for node in inst.nodes:
            node_coord[node.label] = tuple(node.coordinates)

        # ----------------------------------------------------
        # Global displacement
        # ----------------------------------------------------
        max_U_magnitude = -1.0
        max_abs_U1 = -1.0
        max_abs_U2 = -1.0
        min_U2 = 1.0e100

        for val in U_field.values:
            u1 = float(val.data[0])
            u2 = float(val.data[1])
            umag = vec_mag(val.data)

            max_U_magnitude = max(max_U_magnitude, umag)
            max_abs_U1 = max(max_abs_U1, abs(u1))
            max_abs_U2 = max(max_abs_U2, abs(u2))
            min_U2 = min(min_U2, u2)

        if not close_enough(max_U_magnitude, GT['max_U_magnitude']):
            return False
        if not close_enough(max_abs_U1, GT['max_abs_U1']):
            return False
        if not close_enough(max_abs_U2, GT['max_abs_U2']):
            return False
        if not close_enough(min_U2, GT['min_U2']):
            return False

        # ----------------------------------------------------
        # Top displacement by coordinate
        # ----------------------------------------------------
        ymax = -1.0e100
        for label, coord in node_coord.items():
            ymax = max(ymax, float(coord[1]))

        top_values = []
        for val in U_field.values:
            label = val.nodeLabel
            if label not in node_coord:
                continue

            x = float(node_coord[label][0])
            y = float(node_coord[label][1])

            if abs(y - ymax) <= 1.0e-8:
                u2 = float(val.data[1])
                top_values.append((label, x, y, u2))

        if len(top_values) != GT['top_node_count']:
            return False

        top_values.sort(key=lambda row: row[1])

        top_x_min = top_values[0][1]
        top_x_max = top_values[-1][1]
        top_axis_U2 = top_values[0][3]
        top_outer_U2 = top_values[-1][3]
        top_max_abs_U2 = max(abs(row[3]) for row in top_values)

        if not close_enough(top_x_min, GT['top_x_min'], rel_tol=1.0e-8, abs_tol=ABS_TOL_COORD):
            return False
        if not close_enough(top_x_max, GT['top_x_max'], rel_tol=1.0e-8, abs_tol=ABS_TOL_COORD):
            return False
        if not close_enough(top_axis_U2, GT['top_axis_U2']):
            return False
        if not close_enough(top_outer_U2, GT['top_outer_U2'], rel_tol=REL_TOL, abs_tol=ABS_TOL_SMALL):
            return False
        if not close_enough(top_max_abs_U2, GT['top_max_abs_U2']):
            return False

        # ----------------------------------------------------
        # Reaction forces by coordinate
        # ----------------------------------------------------
        xmax = -1.0e100
        xmin = 1.0e100
        for label, coord in node_coord.items():
            x = float(coord[0])
            xmax = max(xmax, x)
            xmin = min(xmin, x)

        axis_labels = set()
        outer_labels = set()

        for label, coord in node_coord.items():
            x = float(coord[0])
            if abs(x - xmin) <= 1.0e-8:
                axis_labels.add(label)
            if abs(x - xmax) <= 1.0e-8:
                outer_labels.add(label)

        axis_rf2 = 0.0
        outer_rf2 = 0.0

        for val in RF_field.values:
            label = val.nodeLabel
            rf2 = float(val.data[1])

            if label in axis_labels:
                axis_rf2 += rf2

            if label in outer_labels:
                outer_rf2 += rf2

        total_rf2 = axis_rf2 + outer_rf2

        if not close_enough(outer_rf2, GT['outer_sum_RF2'], rel_tol=REL_TOL, abs_tol=ABS_TOL_FORCE):
            return False
        if not close_enough(total_rf2, GT['total_constrained_sum_RF2'], rel_tol=REL_TOL, abs_tol=ABS_TOL_FORCE):
            return False

        # ----------------------------------------------------
        # Stress
        # ----------------------------------------------------
        max_mises = -1.0
        max_abs_S11 = -1.0
        max_abs_S22 = -1.0

        for val in S_field.values:
            try:
                mises = float(val.mises)
                max_mises = max(max_mises, mises)
            except:
                pass

            data = val.data

            if len(data) >= 1:
                max_abs_S11 = max(max_abs_S11, abs(float(data[0])))

            if len(data) >= 2:
                max_abs_S22 = max(max_abs_S22, abs(float(data[1])))

        if not close_enough(max_mises, GT['max_mises'], rel_tol=REL_TOL, abs_tol=ABS_TOL_STRESS):
            return False
        if not close_enough(max_abs_S11, GT['max_abs_S11'], rel_tol=REL_TOL, abs_tol=1.0e-8):
            return False
        if not close_enough(max_abs_S22, GT['max_abs_S22'], rel_tol=REL_TOL, abs_tol=1.0e-8):
            return False

        return True

    except:
        return False

    finally:
        try:
            if odb is not None:
                odb.close()
        except:
            pass

# ============================================================
# 5. Main
# ============================================================

# result_file = os.path.join(desktop, 'eval_result.txt')

# try:
#     passed = check_cae_file() and check_odb_file()
# except:
#     passed = False

# result_text = 'True' if passed else 'false'

# # 1. 输出到命令行
# print(result_text)

# # 2. 同时写入桌面文件，防止 Abaqus noGUI 吞掉 stdout
# with open(result_file, 'w') as f:
#     f.write(result_text + '\n')

# # ============================================================
# # Main
# # ============================================================

result_file = r'C:\Users\Administrator\Desktop\eval_result.txt'

try:
    passed = check_cae_file() and check_odb_file()
except:
    passed = False

result_text = 'True' if passed else 'false'

# 写入结果文件
with open(result_file, 'w') as f:
    f.write(result_text + '\n')

# 尝试输出到终端
try:
    import sys
    sys.__stdout__.write(result_text + '\n')
    sys.__stdout__.flush()
except:
    pass