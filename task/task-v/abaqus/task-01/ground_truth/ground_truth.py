
# -*- coding: utf-8 -*-
# extract_ground_truth.py
# Extract ground-truth values from Abaqus ODB
#
# Run command:
# abaqus python extract_ground_truth.py
#
# Output:
# Job-Plate_ground_truth.json
# Job-Plate_node_U.csv

from odbAccess import openOdb
import os
import json
import math
import csv

# ============================================================
# 0. Paths
# ============================================================

work_dir = r'C:\Users\Administrator\Desktop'
job_name = 'Job-Plate'

odb_path = os.path.join(work_dir, job_name + '.odb')
json_path = os.path.join(work_dir, job_name + '_ground_truth.json')
csv_path = os.path.join(work_dir, job_name + '_node_U.csv')

if not os.path.exists(odb_path):
    raise RuntimeError('ODB file not found: ' + odb_path)

# ============================================================
# 1. Helper functions
# ============================================================

def get_key_case_insensitive(dictionary, target_name):
    """
    Find a key in an Abaqus repository case-insensitively.
    """
    target_upper = target_name.upper()
    for key in dictionary.keys():
        if key.upper() == target_upper:
            return key
    raise RuntimeError('Key not found: ' + target_name)


def vector_magnitude(v):
    s = 0.0
    for x in v:
        s += x * x
    return math.sqrt(s)


def safe_float(x):
    return float(x)


# ============================================================
# 2. Open ODB
# ============================================================

odb = openOdb(path=odb_path, readOnly=True)
assembly = odb.rootAssembly

# Use the first step
step_name = odb.steps.keys()[-1]
step = odb.steps[step_name]

if len(step.frames) == 0:
    odb.close()
    raise RuntimeError('No frames found in ODB.')

last_frame = step.frames[-1]

# Get field outputs
if 'U' not in last_frame.fieldOutputs.keys():
    odb.close()
    raise RuntimeError('Displacement field U not found in ODB.')

U_field = last_frame.fieldOutputs['U']

RF_field = None
if 'RF' in last_frame.fieldOutputs.keys():
    RF_field = last_frame.fieldOutputs['RF']

S_field = None
if 'S' in last_frame.fieldOutputs.keys():
    S_field = last_frame.fieldOutputs['S']

# ============================================================
# 3. Instance, node, and element information
# ============================================================

instance_names = assembly.instances.keys()

if len(instance_names) == 0:
    odb.close()
    raise RuntimeError('No instances found in ODB.')

# Usually PLATE-1
inst_key = instance_names[0]
inst = assembly.instances[inst_key]

node_count = len(inst.nodes)
element_count = len(inst.elements)

# Node coordinate map
node_coord = {}
for node in inst.nodes:
    node_coord[node.label] = tuple(node.coordinates)

# ============================================================
# 4. Get node sets
# ============================================================

node_sets = assembly.nodeSets

top_set = None
axis_set = None
outer_set = None

for name in node_sets.keys():
    if name.upper() == 'TOP':
        top_set = node_sets[name]
    elif name.upper() == 'AXIS':
        axis_set = node_sets[name]
    elif name.upper() == 'OUTER':
        outer_set = node_sets[name]

if top_set is None:
    print('Warning: TOP node set not found.')
if axis_set is None:
    print('Warning: AXIS node set not found.')
if outer_set is None:
    print('Warning: OUTER node set not found.')

# ============================================================
# 5. Displacement results
# ============================================================

all_u_values = U_field.values

max_U_magnitude = -1.0
max_U_magnitude_node = None

max_abs_U1 = -1.0
max_abs_U1_node = None

max_abs_U2 = -1.0
max_abs_U2_node = None

min_U2 = 1.0e100
min_U2_node = None

max_U2 = -1.0e100
max_U2_node = None

node_u_rows = []

for val in all_u_values:
    label = val.nodeLabel
    u = val.data

    u1 = safe_float(u[0])
    u2 = safe_float(u[1])
    umag = vector_magnitude(u)

    coord = node_coord.get(label, None)

    node_u_rows.append({
        'node_label': label,
        'x': coord[0] if coord is not None else None,
        'y': coord[1] if coord is not None else None,
        'U1': u1,
        'U2': u2,
        'Umag': umag
    })

    if umag > max_U_magnitude:
        max_U_magnitude = umag
        max_U_magnitude_node = label

    if abs(u1) > max_abs_U1:
        max_abs_U1 = abs(u1)
        max_abs_U1_node = label

    if abs(u2) > max_abs_U2:
        max_abs_U2 = abs(u2)
        max_abs_U2_node = label

    if u2 < min_U2:
        min_U2 = u2
        min_U2_node = label

    if u2 > max_U2:
        max_U2 = u2
        max_U2_node = label

# ============================================================
# 6. Top node displacement results
# ============================================================

top_results = {}

if top_set is not None:
    U_top = U_field.getSubset(region=top_set)

    top_min_U2 = 1.0e100
    top_min_U2_node = None

    top_max_U2 = -1.0e100
    top_max_U2_node = None

    top_max_abs_U2 = -1.0
    top_max_abs_U2_node = None

    top_axis_node = None
    top_outer_node = None
    top_axis_U2 = None
    top_outer_U2 = None

    # find top nodes by coordinate
    top_values = []

    for val in U_top.values:
        label = val.nodeLabel
        coord = node_coord.get(label, None)
        if coord is None:
            continue

        x = coord[0]
        y = coord[1]
        u1 = safe_float(val.data[0])
        u2 = safe_float(val.data[1])
        top_values.append((label, x, y, u1, u2))

        if u2 < top_min_U2:
            top_min_U2 = u2
            top_min_U2_node = label

        if u2 > top_max_U2:
            top_max_U2 = u2
            top_max_U2_node = label

        if abs(u2) > top_max_abs_U2:
            top_max_abs_U2 = abs(u2)
            top_max_abs_U2_node = label

    if len(top_values) > 0:
        top_values.sort(key=lambda row: row[1])

        top_axis_node = top_values[0][0]
        top_axis_U2 = top_values[0][4]

        top_outer_node = top_values[-1][0]
        top_outer_U2 = top_values[-1][4]

        top_results = {
            'top_node_count': len(top_values),
            'top_x_min': safe_float(top_values[0][1]),
            'top_x_max': safe_float(top_values[-1][1]),
            'top_min_U2': safe_float(top_min_U2),
            'top_min_U2_node': int(top_min_U2_node),
            'top_max_U2': safe_float(top_max_U2),
            'top_max_U2_node': int(top_max_U2_node),
            'top_max_abs_U2': safe_float(top_max_abs_U2),
            'top_max_abs_U2_node': int(top_max_abs_U2_node),
            'top_axis_node': int(top_axis_node),
            'top_axis_U2': safe_float(top_axis_U2),
            'top_outer_node': int(top_outer_node),
            'top_outer_U2': safe_float(top_outer_U2)
        }

# ============================================================
# 7. Reaction force results
# ============================================================

reaction_results = {}

def sum_reaction_force(region_set, name):
    if RF_field is None or region_set is None:
        return None

    RF_subset = RF_field.getSubset(region=region_set)

    rf1 = 0.0
    rf2 = 0.0
    rf_mag_sum = 0.0
    count = 0

    for val in RF_subset.values:
        rf = val.data
        r1 = safe_float(rf[0])
        r2 = safe_float(rf[1])

        rf1 += r1
        rf2 += r2
        rf_mag_sum += math.sqrt(r1 * r1 + r2 * r2)
        count += 1

    return {
        name + '_node_count': count,
        name + '_sum_RF1': safe_float(rf1),
        name + '_sum_RF2': safe_float(rf2),
        name + '_sum_RF_magnitude': safe_float(rf_mag_sum)
    }

axis_rf = sum_reaction_force(axis_set, 'axis')
outer_rf = sum_reaction_force(outer_set, 'outer')

if axis_rf is not None:
    reaction_results.update(axis_rf)

if outer_rf is not None:
    reaction_results.update(outer_rf)

# Overall constrained reaction
if axis_rf is not None and outer_rf is not None:
    total_rf1 = axis_rf['axis_sum_RF1'] + outer_rf['outer_sum_RF1']
    total_rf2 = axis_rf['axis_sum_RF2'] + outer_rf['outer_sum_RF2']

    reaction_results['total_constrained_sum_RF1'] = safe_float(total_rf1)
    reaction_results['total_constrained_sum_RF2'] = safe_float(total_rf2)

# ============================================================
# 8. Stress results
# ============================================================

stress_results = {}

if S_field is not None:
    max_mises = -1.0
    max_mises_element = None

    max_abs_S11 = -1.0
    max_abs_S11_element = None

    max_abs_S22 = -1.0
    max_abs_S22_element = None

    for val in S_field.values:
        eid = val.elementLabel

        try:
            mises = safe_float(val.mises)
        except:
            mises = None

        if mises is not None and mises > max_mises:
            max_mises = mises
            max_mises_element = eid

        sdata = val.data

        if len(sdata) >= 1:
            s11 = safe_float(sdata[0])
            if abs(s11) > max_abs_S11:
                max_abs_S11 = abs(s11)
                max_abs_S11_element = eid

        if len(sdata) >= 2:
            s22 = safe_float(sdata[1])
            if abs(s22) > max_abs_S22:
                max_abs_S22 = abs(s22)
                max_abs_S22_element = eid

    stress_results = {
        'max_mises': safe_float(max_mises),
        'max_mises_element': int(max_mises_element),
        'max_abs_S11': safe_float(max_abs_S11),
        'max_abs_S11_element': int(max_abs_S11_element),
        'max_abs_S22': safe_float(max_abs_S22),
        'max_abs_S22_element': int(max_abs_S22_element)
    }

# ============================================================
# 9. Assemble ground-truth dictionary
# ============================================================

ground_truth = {
    'job_name': job_name,
    'odb_path': odb_path,
    'step_name': step_name,
    'last_frame_value': safe_float(last_frame.frameValue),

    'model_counts': {
        'node_count': int(node_count),
        'element_count': int(element_count)
    },

    'global_displacement': {
        'max_U_magnitude': safe_float(max_U_magnitude),
        'max_U_magnitude_node': int(max_U_magnitude_node),
        'max_abs_U1': safe_float(max_abs_U1),
        'max_abs_U1_node': int(max_abs_U1_node),
        'max_abs_U2': safe_float(max_abs_U2),
        'max_abs_U2_node': int(max_abs_U2_node),
        'min_U2': safe_float(min_U2),
        'min_U2_node': int(min_U2_node),
        'max_U2': safe_float(max_U2),
        'max_U2_node': int(max_U2_node)
    },

    'top_displacement': top_results,

    'reaction_force': reaction_results,

    'stress': stress_results
}

# ============================================================
# 10. Save JSON
# ============================================================

with open(json_path, 'w') as f:
    json.dump(ground_truth, f, indent=2, sort_keys=True)

print('>>> Ground truth JSON saved:')
print(json_path)

# ============================================================
# 11. Save node displacement CSV
# ============================================================

with open(csv_path, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['node_label', 'x', 'y', 'U1', 'U2', 'Umag'])

    for row in node_u_rows:
        writer.writerow([
            row['node_label'],
            row['x'],
            row['y'],
            row['U1'],
            row['U2'],
            row['Umag']
        ])

print('>>> Node displacement CSV saved:')
print(csv_path)

odb.close()

print('>>> Extraction completed.')