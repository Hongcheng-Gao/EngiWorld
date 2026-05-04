# -*- coding: utf-8 -*-
# extract_truth.py
# Run:
#   abaqus cae noGUI=extract_truth.py

from abaqus import *
from abaqusConstants import *
from odbAccess import openOdb
import os
import json
import math

DESKTOP = r'C:\Users\Administrator\Desktop'
CAE_PATH = os.path.join(DESKTOP, 'Job-FlangeHole.cae')
ODB_PATH = os.path.join(DESKTOP, 'Job-FlangeHole.odb')
OUT_PATH = os.path.join(DESKTOP, 'truth_values.json')

MODEL_NAME = 'Model-FlangeHole'
PART_NAME = 'FlangeHolePlate'
INSTANCE_NAME = 'FLANGEHOLEPLATE-1'
STEP_NAME = 'Step-HoleTension'

truth = {}

# ============================================================
# 1. Read CAE: model definition truth
# ============================================================
openMdb(pathName=CAE_PATH)

model = mdb.models[MODEL_NAME]
part = model.parts[PART_NAME]

truth['cae_exists'] = os.path.exists(CAE_PATH)
truth['odb_exists'] = os.path.exists(ODB_PATH)

# ---------- Material ----------
mat = model.materials['Steel']
E, nu = mat.elastic.table[0]
truth['material_name'] = 'Steel'
truth['youngs_modulus'] = float(E)
truth['poisson_ratio'] = float(nu)

# ---------- Section ----------
section = model.sections['Shell-1']
truth['section_name'] = 'Shell-1'
truth['shell_thickness'] = float(section.thickness)

# Some Abaqus versions expose numIntPts directly; some do not.
try:
    truth['shell_num_int_pts'] = int(section.numIntPts)
except Exception:
    truth['shell_num_int_pts'] = None

# ---------- Step ----------
truth['has_step_hole_tension'] = STEP_NAME in model.steps.keys()

# ---------- Loads ----------
truth['load_names'] = sorted(model.loads.keys())
truth['bc_names'] = sorted(model.boundaryConditions.keys())

# Try to extract load magnitudes if available.
truth['loads'] = {}
for lname, load in model.loads.items():
    item = {}
    try:
        item['magnitude'] = float(load.magnitude)
    except Exception:
        item['magnitude'] = None
    try:
        item['directionVector'] = str(load.directionVector)
    except Exception:
        item['directionVector'] = None
    item['type'] = load.__class__.__name__
    truth['loads'][lname] = item

# ---------- Boundary conditions ----------
truth['boundary_conditions'] = {}
for bc_name, bc in model.boundaryConditions.items():
    item = {}
    for dof in ['u1', 'u2', 'u3', 'ur1', 'ur2', 'ur3']:
        try:
            value = getattr(bc, dof)
            if value is None:
                item[dof] = None
            else:
                item[dof] = str(value)
        except Exception:
            item[dof] = None
    truth['boundary_conditions'][bc_name] = item

# ---------- Mesh from CAE ----------
truth['cae_num_nodes'] = len(part.nodes)
truth['cae_num_elements'] = len(part.elements)

elem_types = {}
for elem in part.elements:
    try:
        etype = str(elem.type)
    except Exception:
        etype = 'UNKNOWN'
    elem_types[etype] = elem_types.get(etype, 0) + 1

truth['cae_element_types'] = elem_types

# ---------- Approximate geometry from mesh nodes ----------
xs = []
ys = []
hole_rs = []

cx = 60.0
cy = 120.0

for node in part.nodes:
    x, y, z = node.coordinates
    xs.append(float(x))
    ys.append(float(y))

    r = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
    if abs(r - 6.0) < 1.0:
        hole_rs.append(float(r))

truth['mesh_x_min'] = min(xs)
truth['mesh_x_max'] = max(xs)
truth['mesh_y_min'] = min(ys)
truth['mesh_y_max'] = max(ys)

if hole_rs:
    truth['hole_radius_from_mesh_avg'] = sum(hole_rs) / len(hole_rs)
    truth['hole_diameter_from_mesh_avg'] = 2.0 * truth['hole_radius_from_mesh_avg']
    truth['hole_boundary_node_count'] = len(hole_rs)
else:
    truth['hole_radius_from_mesh_avg'] = None
    truth['hole_diameter_from_mesh_avg'] = None
    truth['hole_boundary_node_count'] = 0

# ============================================================
# 2. Read ODB: result truth
# ============================================================
odb = openOdb(path=ODB_PATH, readOnly=True)

truth['odb_step_names'] = list(odb.steps.keys())
truth['odb_has_step_hole_tension'] = STEP_NAME in odb.steps.keys()

# Job status, if available.
try:
    truth['odb_job_status'] = str(odb.diagnosticData.jobStatus)
except Exception:
    truth['odb_job_status'] = None

inst = odb.rootAssembly.instances[INSTANCE_NAME]
truth['odb_num_nodes'] = len(inst.nodes)
truth['odb_num_elements'] = len(inst.elements)

odb_elem_types = {}
for elem in inst.elements:
    etype = elem.type
    odb_elem_types[etype] = odb_elem_types.get(etype, 0) + 1

truth['odb_element_types'] = odb_elem_types

step = odb.steps[STEP_NAME]
last_frame = step.frames[-1]

truth['odb_num_frames'] = len(step.frames)
truth['last_frame_value'] = float(last_frame.frameValue)

# ---------- Displacement U ----------
u_field = last_frame.fieldOutputs['U']

max_u_mag = -1.0
max_u1_abs = -1.0
max_u2_abs = -1.0
max_u3_abs = -1.0

max_u1 = None
min_u1 = None
max_u2 = None
min_u2 = None
max_u3 = None
min_u3 = None

for v in u_field.values:
    u1, u2, u3 = v.data

    mag = math.sqrt(u1 ** 2 + u2 ** 2 + u3 ** 2)
    if mag > max_u_mag:
        max_u_mag = mag

    max_u1_abs = max(max_u1_abs, abs(u1))
    max_u2_abs = max(max_u2_abs, abs(u2))
    max_u3_abs = max(max_u3_abs, abs(u3))

    max_u1 = u1 if max_u1 is None else max(max_u1, u1)
    min_u1 = u1 if min_u1 is None else min(min_u1, u1)
    max_u2 = u2 if max_u2 is None else max(max_u2, u2)
    min_u2 = u2 if min_u2 is None else min(min_u2, u2)
    max_u3 = u3 if max_u3 is None else max(max_u3, u3)
    min_u3 = u3 if min_u3 is None else min(min_u3, u3)

truth['max_u_magnitude'] = float(max_u_mag)
truth['max_abs_u1'] = float(max_u1_abs)
truth['max_abs_u2'] = float(max_u2_abs)
truth['max_abs_u3'] = float(max_u3_abs)
truth['max_u1'] = float(max_u1)
truth['min_u1'] = float(min_u1)
truth['max_u2'] = float(max_u2)
truth['min_u2'] = float(min_u2)
truth['max_u3'] = float(max_u3)
truth['min_u3'] = float(min_u3)

# ---------- Stress S ----------
s_field = last_frame.fieldOutputs['S']

max_mises = -1.0
max_s11 = None
min_s11 = None

for v in s_field.values:
    try:
        mises = v.mises
        if mises > max_mises:
            max_mises = mises
    except Exception:
        pass

    try:
        s11 = v.data[0]
        max_s11 = s11 if max_s11 is None else max(max_s11, s11)
        min_s11 = s11 if min_s11 is None else min(min_s11, s11)
    except Exception:
        pass

truth['max_mises'] = float(max_mises)
truth['max_s11'] = float(max_s11) if max_s11 is not None else None
truth['min_s11'] = float(min_s11) if min_s11 is not None else None

odb.close()

# ============================================================
# 3. Save truth JSON
# ============================================================
with open(OUT_PATH, 'w') as f:
    json.dump(truth, f, indent=2, sort_keys=True)

print('TRUE_VALUES_JSON_PATH = ' + OUT_PATH)
print(json.dumps(truth, indent=2, sort_keys=True))