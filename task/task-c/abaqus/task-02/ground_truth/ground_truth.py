# -*- coding: utf-8 -*-
# Extract ground-truth values from Abaqus ODB for task-02
#
# Run command:
# abaqus python ground_truth.py
#
# Output:
# C:\Users\Administrator\Desktop\Job-Cylinder_ground_truth.json

from odbAccess import openOdb
import os
import json
import math

# ============================================================
# 0. Paths
# ============================================================

work_dir = r'C:\Users\Administrator\Desktop'
job_name = 'Job-Cylinder'

odb_path = os.path.join(work_dir, job_name + '.odb')
json_path = os.path.join(work_dir, job_name + '_ground_truth.json')

if not os.path.exists(odb_path):
    raise RuntimeError('ODB file not found: ' + odb_path)

# ============================================================
# 1. Helper functions
# ============================================================

def find_key_case_insensitive(repo, target_name):
    target_upper = target_name.upper()
    for key in repo.keys():
        if key.upper() == target_upper:
            return key
    raise RuntimeError('Key not found: ' + target_name)


def to_float(x):
    return float(x)


def vector_magnitude(v):
    s = 0.0
    for x in v:
        fx = float(x)
        s += fx * fx
    return math.sqrt(s)


def safe_int_or_none(x):
    if x is None:
        return None
    return int(x)


def update_min_max(stats, value, label):
    if value < stats['min']:
        stats['min'] = value
        stats['min_node'] = label
    if value > stats['max']:
        stats['max'] = value
        stats['max_node'] = label


def mean_of(values):
    if len(values) == 0:
        return None
    return sum(values) / float(len(values))


def get_primary_instance(assembly):
    instance_names = assembly.instances.keys()
    if len(instance_names) == 0:
        raise RuntimeError('No instances found in ODB.')

    best_name = None
    best_nodes = -1
    for name in instance_names:
        inst = assembly.instances[name]
        node_count = len(inst.nodes)
        if node_count > best_nodes:
            best_nodes = node_count
            best_name = name
    return assembly.instances[best_name]


def get_nodeset_case_insensitive(assembly, set_name):
    key = find_key_case_insensitive(assembly.nodeSets, set_name)
    return assembly.nodeSets[key]


def collect_node_labels_in_set(nodeset_obj):
    labels = set()
    for block in nodeset_obj.nodes:
        for node in block:
            labels.add(int(node.label))
    return labels


# ============================================================
# 2. Open ODB and basic handles
# ============================================================

odb = openOdb(path=odb_path, readOnly=True)
assembly = odb.rootAssembly

step_key = find_key_case_insensitive(odb.steps, 'Step-Pressure')
step = odb.steps[step_key]

if len(step.frames) == 0:
    odb.close()
    raise RuntimeError('No frames found in step: ' + step_key)

last_frame = step.frames[-1]

if 'U' not in last_frame.fieldOutputs.keys():
    odb.close()
    raise RuntimeError('Displacement field U not found in ODB.')
if 'RF' not in last_frame.fieldOutputs.keys():
    odb.close()
    raise RuntimeError('Reaction field RF not found in ODB.')
if 'S' not in last_frame.fieldOutputs.keys():
    odb.close()
    raise RuntimeError('Stress field S not found in ODB.')

U_field = last_frame.fieldOutputs['U']
RF_field = last_frame.fieldOutputs['RF']
S_field = last_frame.fieldOutputs['S']

inst = get_primary_instance(assembly)
node_count = len(inst.nodes)
element_count = len(inst.elements)

# Node coordinate map
node_coord = {}
for node in inst.nodes:
    node_coord[int(node.label)] = tuple(node.coordinates)

# ============================================================
# 3. Node sets (case-insensitive, strict required)
# ============================================================

allnodes_set = get_nodeset_case_insensitive(assembly, 'ALLNODES')
inner_set = get_nodeset_case_insensitive(assembly, 'INNER')
outer_set = get_nodeset_case_insensitive(assembly, 'OUTER')
zmin_set = get_nodeset_case_insensitive(assembly, 'ZMIN')
zmax_set = get_nodeset_case_insensitive(assembly, 'ZMAX')

inner_labels = collect_node_labels_in_set(inner_set)
outer_labels = collect_node_labels_in_set(outer_set)
allnodes_labels = collect_node_labels_in_set(allnodes_set)
zmin_labels = collect_node_labels_in_set(zmin_set)
zmax_labels = collect_node_labels_in_set(zmax_set)

# ============================================================
# 4. Global displacement statistics
# ============================================================

max_U_magnitude = -1.0
max_U_magnitude_node = None

max_abs_U1 = -1.0
max_abs_U1_node = None

max_abs_U2 = -1.0
max_abs_U2_node = None

min_U1 = 1.0e100
min_U1_node = None

max_U1 = -1.0e100
max_U1_node = None

for val in U_field.values:
    label = int(val.nodeLabel)
    u1 = to_float(val.data[0])
    u2 = to_float(val.data[1])
    umag = vector_magnitude(val.data)

    if umag > max_U_magnitude:
        max_U_magnitude = umag
        max_U_magnitude_node = label

    if abs(u1) > max_abs_U1:
        max_abs_U1 = abs(u1)
        max_abs_U1_node = label

    if abs(u2) > max_abs_U2:
        max_abs_U2 = abs(u2)
        max_abs_U2_node = label

    if u1 < min_U1:
        min_U1 = u1
        min_U1_node = label

    if u1 > max_U1:
        max_U1 = u1
        max_U1_node = label

# ============================================================
# 5. Displacement on INNER / OUTER node sets (U1)
# ============================================================

inner_u1 = []
outer_u1 = []

inner_stats = {
    'min': 1.0e100,
    'min_node': None,
    'max': -1.0e100,
    'max_node': None
}
outer_stats = {
    'min': 1.0e100,
    'min_node': None,
    'max': -1.0e100,
    'max_node': None
}

for val in U_field.values:
    label = int(val.nodeLabel)
    u1 = to_float(val.data[0])

    if label in inner_labels:
        inner_u1.append(u1)
        update_min_max(inner_stats, u1, label)

    if label in outer_labels:
        outer_u1.append(u1)
        update_min_max(outer_stats, u1, label)

if len(inner_u1) == 0:
    raise RuntimeError('No U values found on INNER node set.')
if len(outer_u1) == 0:
    raise RuntimeError('No U values found on OUTER node set.')

set_displacement = {
    'inner_node_count': len(inner_u1),
    'inner_u1_min': to_float(inner_stats['min']),
    'inner_u1_min_node': int(inner_stats['min_node']),
    'inner_u1_max': to_float(inner_stats['max']),
    'inner_u1_max_node': int(inner_stats['max_node']),
    'inner_u1_avg': to_float(mean_of(inner_u1)),

    'outer_node_count': len(outer_u1),
    'outer_u1_min': to_float(outer_stats['min']),
    'outer_u1_min_node': int(outer_stats['min_node']),
    'outer_u1_max': to_float(outer_stats['max']),
    'outer_u1_max_node': int(outer_stats['max_node']),
    'outer_u1_avg': to_float(mean_of(outer_u1))
}

# ============================================================
# 6. Reaction force statistics on INNER / OUTER and total
# ============================================================

def sum_rf_on_set(target_labels):
    rf1 = 0.0
    rf2 = 0.0
    count = 0
    for val in RF_field.values:
        label = int(val.nodeLabel)
        if label in target_labels:
            rf1 += to_float(val.data[0])
            rf2 += to_float(val.data[1])
            count += 1
    return count, rf1, rf2


inner_rf_count, inner_rf1, inner_rf2 = sum_rf_on_set(inner_labels)
outer_rf_count, outer_rf1, outer_rf2 = sum_rf_on_set(outer_labels)
all_rf_count, all_rf1, all_rf2 = sum_rf_on_set(allnodes_labels)

reaction_force = {
    'inner_node_count': int(inner_rf_count),
    'inner_sum_RF1': to_float(inner_rf1),
    'inner_sum_RF2': to_float(inner_rf2),

    'outer_node_count': int(outer_rf_count),
    'outer_sum_RF1': to_float(outer_rf1),
    'outer_sum_RF2': to_float(outer_rf2),

    'total_node_count': int(all_rf_count),
    'total_sum_RF1': to_float(all_rf1),
    'total_sum_RF2': to_float(all_rf2)
}

# ============================================================
# 7. Stress statistics and radial-band Mises peaks
# ============================================================

max_mises = -1.0
max_mises_element = None
max_abs_S11 = -1.0
max_abs_S11_element = None
max_abs_S22 = -1.0
max_abs_S22_element = None
max_abs_S33 = -1.0
max_abs_S33_element = None

# Build element average radius map once
element_avg_r = {}
for elem in inst.elements:
    eid = int(elem.label)
    rs = []
    for nid in elem.connectivity:
        node = inst.getNodeFromLabel(nid)
        rs.append(float(node.coordinates[0]))
    if len(rs) > 0:
        element_avg_r[eid] = sum(rs) / float(len(rs))

inner_band_mises_max = -1.0
inner_band_mises_element = None
outer_band_mises_max = -1.0
outer_band_mises_element = None

for val in S_field.values:
    eid = safe_int_or_none(val.elementLabel)
    data = val.data

    try:
        mises = to_float(val.mises)
    except:
        mises = None

    if mises is not None and mises > max_mises:
        max_mises = mises
        max_mises_element = eid

    if len(data) >= 1:
        s11 = abs(to_float(data[0]))
        if s11 > max_abs_S11:
            max_abs_S11 = s11
            max_abs_S11_element = eid

    if len(data) >= 2:
        s22 = abs(to_float(data[1]))
        if s22 > max_abs_S22:
            max_abs_S22 = s22
            max_abs_S22_element = eid

    if len(data) >= 3:
        s33 = abs(to_float(data[2]))
        if s33 > max_abs_S33:
            max_abs_S33 = s33
            max_abs_S33_element = eid

    if mises is not None and eid in element_avg_r:
        ravg = element_avg_r[eid]
        if abs(ravg - 52.5) <= 3.0:
            if mises > inner_band_mises_max:
                inner_band_mises_max = mises
                inner_band_mises_element = eid
        if abs(ravg - 97.5) <= 3.0:
            if mises > outer_band_mises_max:
                outer_band_mises_max = mises
                outer_band_mises_element = eid

stress = {
    'max_mises': to_float(max_mises),
    'max_mises_element': safe_int_or_none(max_mises_element),
    'max_abs_S11': to_float(max_abs_S11),
    'max_abs_S11_element': safe_int_or_none(max_abs_S11_element),
    'max_abs_S22': to_float(max_abs_S22),
    'max_abs_S22_element': safe_int_or_none(max_abs_S22_element),
    'max_abs_S33': to_float(max_abs_S33),
    'max_abs_S33_element': safe_int_or_none(max_abs_S33_element)
}

radial_bands = {
    'inner_band_center_r': 52.5,
    'inner_band_tol': 3.0,
    'inner_band_max_mises': to_float(inner_band_mises_max),
    'inner_band_max_mises_element': safe_int_or_none(inner_band_mises_element),
    'outer_band_center_r': 97.5,
    'outer_band_tol': 3.0,
    'outer_band_max_mises': to_float(outer_band_mises_max),
    'outer_band_max_mises_element': safe_int_or_none(outer_band_mises_element)
}

# ============================================================
# 8. Assemble and save JSON
# ============================================================

ground_truth = {
    'job_name': job_name,
    'odb_path': odb_path,
    'step_name': step_key,
    'last_frame_value': to_float(last_frame.frameValue),

    'model_counts': {
        'node_count': int(node_count),
        'element_count': int(element_count),
        'inner_node_count': int(len(inner_labels)),
        'outer_node_count': int(len(outer_labels)),
        'zmin_node_count': int(len(zmin_labels)),
        'zmax_node_count': int(len(zmax_labels))
    },

    'global_displacement': {
        'max_U_magnitude': to_float(max_U_magnitude),
        'max_U_magnitude_node': int(max_U_magnitude_node),
        'max_abs_U1': to_float(max_abs_U1),
        'max_abs_U1_node': int(max_abs_U1_node),
        'max_abs_U2': to_float(max_abs_U2),
        'max_abs_U2_node': int(max_abs_U2_node),
        'min_U1': to_float(min_U1),
        'min_U1_node': int(min_U1_node),
        'max_U1': to_float(max_U1),
        'max_U1_node': int(max_U1_node)
    },

    'set_displacement': set_displacement,
    'reaction_force': reaction_force,
    'stress': stress,
    'radial_bands': radial_bands
}

with open(json_path, 'w') as f:
    json.dump(ground_truth, f, indent=2, sort_keys=True)

print('>>> Ground truth JSON saved:')
print(json_path)

odb.close()
print('>>> Extraction completed.')
