# -*- coding: utf-8 -*-
# eval_job_flangehole_fixed.py
# Run with:
#     abaqus cae noGUI=eval_job_flangehole_fixed.py
#
# Final stdout is intended to be only:
#     true
# or
#     false
#
# This evaluator reads:
#     <Desktop>\Job-FlangeHole.cae
#     <Desktop>\Job-FlangeHole.odb
#
# It also writes:
#     <Desktop>\eval_result.txt
#     <Desktop>\eval_detail.txt

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

    # Prefer the desktop that already contains the target files.
    for d in candidates:
        if os.path.exists(os.path.join(d, 'Job-FlangeHole.cae')) or \
           os.path.exists(os.path.join(d, 'Job-FlangeHole.odb')):
            return d

    for d in candidates:
        if os.path.isdir(d):
            return d

    return r'C:\Users\Administrator\Desktop'


desktop = get_desktop()
cae_path = os.path.join(desktop, 'Job-FlangeHole.cae')
odb_path = os.path.join(desktop, 'Job-FlangeHole.odb')
result_file = os.path.join(desktop, 'eval_result.txt')
detail_file = os.path.join(desktop, 'eval_detail.txt')

DETAILS = []


def log(msg):
    DETAILS.append(str(msg))


# ============================================================
# 2. Hard-coded ground truth
# ============================================================

GT = {
    # File / model
    'step_name': 'Step-HoleTension',
    'last_frame_value': 1.0,

    # Material / section
    'youngs_modulus': 210000.0,
    'poisson_ratio': 0.3,
    'shell_thickness': 1.0,
    'shell_num_int_pts': 5,

    # Geometry from mesh nodes
    'mesh_x_min': 0.0,
    'mesh_x_max': 120.0,
    'mesh_y_min': 0.0,
    'mesh_y_max': 240.0,
    'hole_diameter_from_mesh_avg': 11.999995654927822,
    'hole_boundary_node_count': 16,

    # Mesh
    'cae_num_nodes': 638,
    'cae_num_elements': 605,
    'cae_s4r_count': 583,
    'cae_s3_count': 22,

    'odb_num_nodes': 638,
    'odb_num_elements': 605,
    'odb_s4r_count': 583,
    'odb_s3r_count': 22,

    # Results
    'odb_num_frames': 2,
    'max_u_magnitude': 0.0053171977986313365,
    'max_abs_u1': 0.004665727261453867,
    'max_abs_u2': 0.002775878179818392,
    'max_abs_u3': 1.556629173988425e-17,
    'max_u1': 0.00011847333371406421,
    'min_u1': -0.004665727261453867,
    'max_u2': 0.002775878179818392,
    'min_u2': -1.8799695681082085e-05,
    'max_mises': 16.02847671508789,
    'min_s11': -16.6141357421875,
    'max_s11': -0.3741181790828705
}

# ============================================================
# 3. Tolerances
# ============================================================

ABS_TOL_MATERIAL = 1.0e-6
ABS_TOL_SECTION = 1.0e-6
ABS_TOL_COORD = 1.0e-6
ABS_TOL_FRAME = 1.0e-10

# Mesh is fixed by the instruction, but allow a small tolerance for GUI-generated mesh variations.
NODE_COUNT_TOL = 5
ELEMENT_COUNT_TOL = 5
ELEM_TYPE_COUNT_TOL = 5
HOLE_NODE_COUNT_TOL = 2

ABS_TOL_HOLE_DIAM = 5.0e-3

REL_TOL_DISP = 5.0e-3
ABS_TOL_DISP = 1.0e-8

REL_TOL_STRESS = 5.0e-3
ABS_TOL_STRESS = 1.0e-6

ABS_TOL_U3 = 1.0e-8


# ============================================================
# 4. Utility functions
# ============================================================

def output_result(value):
    result_text = 'true' if value else 'false'

    try:
        with open(result_file, 'w') as f:
            f.write(result_text + '\n')
    except:
        pass

    try:
        with open(detail_file, 'w') as f:
            f.write(result_text + '\n')
            for line in DETAILS:
                f.write(str(line) + '\n')
    except:
        pass

    try:
        sys.__stdout__.write(result_text + '\n')
        sys.__stdout__.flush()
    except:
        try:
            sys.stdout.write(result_text + '\n')
            sys.stdout.flush()
        except:
            pass


def fail(msg):
    log('[FAIL] ' + str(msg))
    return False


def ok(msg):
    log('[PASS] ' + str(msg))
    return True


def close_enough(obs, exp, rel_tol=1.0e-3, abs_tol=1.0e-8):
    obs = float(obs)
    exp = float(exp)
    tol = max(float(abs_tol), float(rel_tol) * abs(exp))
    return abs(obs - exp) <= tol


def count_close(obs, exp, tol):
    return abs(int(obs) - int(exp)) <= int(tol)


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
        return None

    return root_assembly.instances[best_key]


def get_element_type_counts(elements):
    counts = {}
    for elem in elements:
        try:
            etype = str(elem.type)
        except:
            etype = 'UNKNOWN'
        counts[etype] = counts.get(etype, 0) + 1
    return counts


def coord_extents_and_hole_from_nodes(nodes):
    xs = []
    ys = []
    zs = []
    hole_rs = []

    cx = 60.0
    cy = 120.0
    target_r = 6.0

    for node in nodes:
        x, y, z = node.coordinates
        x = float(x)
        y = float(y)
        z = float(z)

        xs.append(x)
        ys.append(y)
        zs.append(z)

        r = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)

        # The reference extraction used abs(r - 6.0) < 1.0.
        if abs(r - target_r) < 1.0:
            hole_rs.append(r)

    if len(xs) == 0:
        return None

    out = {
        'x_min': min(xs),
        'x_max': max(xs),
        'y_min': min(ys),
        'y_max': max(ys),
        'z_min': min(zs),
        'z_max': max(zs),
        'hole_node_count': len(hole_rs),
        'hole_diameter_avg': None
    }

    if len(hole_rs) > 0:
        out['hole_diameter_avg'] = 2.0 * sum(hole_rs) / len(hole_rs)

    return out


def material_ok(model):
    for mat_name in model.materials.keys():
        mat = model.materials[mat_name]
        try:
            E, nu = mat.elastic.table[0]
            if close_enough(E, GT['youngs_modulus'], rel_tol=0.0, abs_tol=ABS_TOL_MATERIAL) and \
               close_enough(nu, GT['poisson_ratio'], rel_tol=0.0, abs_tol=ABS_TOL_MATERIAL):
                log('Material matched: %s, E=%s, nu=%s' % (mat_name, str(E), str(nu)))
                return True
        except:
            pass

    return False


def section_ok(model):
    for sec_name in model.sections.keys():
        sec = model.sections[sec_name]
        try:
            thickness = float(sec.thickness)
        except:
            continue

        if not close_enough(thickness, GT['shell_thickness'], rel_tol=0.0, abs_tol=ABS_TOL_SECTION):
            continue

        # Some Abaqus versions expose numIntPts; some do not. If exposed, check it.
        try:
            nipt = int(sec.numIntPts)
            if nipt != int(GT['shell_num_int_pts']):
                continue
        except:
            pass

        log('Section matched: %s, thickness=%s' % (sec_name, str(thickness)))
        return True

    return False


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
        except:
            pass

        try:
            assembly = model.rootAssembly
            for inst_name in assembly.instances.keys():
                inst = assembly.instances[inst_name]
                score += len(inst.nodes) + 2 * len(inst.elements)
        except:
            pass

        if score > best_score:
            best_score = score
            best_model = model

    return best_model


def get_best_part_or_instance_mesh_from_cae(model):
    best_obj = None
    best_nodes = -1
    best_elements = -1
    best_counts = {}
    best_source = None

    try:
        for part_name in model.parts.keys():
            part = model.parts[part_name]
            try:
                n = len(part.nodes)
                e = len(part.elements)
                if n > best_nodes:
                    best_obj = part
                    best_nodes = n
                    best_elements = e
                    best_counts = get_element_type_counts(part.elements)
                    best_source = 'part:' + part_name
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
                    best_obj = inst
                    best_nodes = n
                    best_elements = e
                    best_counts = get_element_type_counts(inst.elements)
                    best_source = 'instance:' + inst_name
            except:
                pass
    except:
        pass

    return best_obj, best_nodes, best_elements, best_counts, best_source


# ============================================================
# 5. CAE checks
# ============================================================

def check_cae_file():
    if not os.path.exists(cae_path):
        return fail('CAE file not found: ' + cae_path)

    try:
        openMdb(pathName=cae_path)
    except Exception as e:
        return fail('Cannot open CAE: ' + str(e))

    model = get_best_model_from_cae()
    if model is None:
        return fail('No model found in CAE')

    if get_step_key(model.steps, GT['step_name']) is None:
        return fail('Step not found in CAE: ' + GT['step_name'])
    ok('CAE step found: ' + GT['step_name'])

    if not material_ok(model):
        return fail('Steel material properties not found')
    ok('CAE material matched')

    if not section_ok(model):
        return fail('Shell section thickness/integration points not matched')
    ok('CAE shell section matched')

    obj, n_nodes, n_elems, elem_counts, source = get_best_part_or_instance_mesh_from_cae(model)
    log('CAE mesh source: %s' % str(source))
    log('CAE mesh counts: nodes=%s, elements=%s, element_types=%s' %
        (str(n_nodes), str(n_elems), str(elem_counts)))

    if not count_close(n_nodes, GT['cae_num_nodes'], NODE_COUNT_TOL):
        return fail('CAE node count mismatch: observed %s, expected %s' %
                    (str(n_nodes), str(GT['cae_num_nodes'])))

    if not count_close(n_elems, GT['cae_num_elements'], ELEMENT_COUNT_TOL):
        return fail('CAE element count mismatch: observed %s, expected %s' %
                    (str(n_elems), str(GT['cae_num_elements'])))

    if not count_close(elem_counts.get('S4R', 0), GT['cae_s4r_count'], ELEM_TYPE_COUNT_TOL):
        return fail('CAE S4R count mismatch: observed %s, expected %s' %
                    (str(elem_counts.get('S4R', 0)), str(GT['cae_s4r_count'])))

    # In CAE the triangular elements appear as S3 in the extracted truth.
    s3_like_count = elem_counts.get('S3', 0) + elem_counts.get('S3R', 0)
    if not count_close(s3_like_count, GT['cae_s3_count'], ELEM_TYPE_COUNT_TOL):
        return fail('CAE S3/S3R count mismatch: observed %s, expected %s' %
                    (str(s3_like_count), str(GT['cae_s3_count'])))

    ok('CAE mesh matched')

    geom = None
    try:
        geom = coord_extents_and_hole_from_nodes(obj.nodes)
        log('CAE geometry: ' + str(geom))
    except Exception as e:
        return fail('Cannot read CAE mesh geometry: ' + str(e))

    if geom is None:
        return fail('CAE geometry is empty')

    if not close_enough(geom['x_min'], GT['mesh_x_min'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
        return fail('CAE x_min mismatch: ' + str(geom['x_min']))

    if not close_enough(geom['x_max'], GT['mesh_x_max'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
        return fail('CAE x_max mismatch: ' + str(geom['x_max']))

    if not close_enough(geom['y_min'], GT['mesh_y_min'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
        return fail('CAE y_min mismatch: ' + str(geom['y_min']))

    if not close_enough(geom['y_max'], GT['mesh_y_max'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
        return fail('CAE y_max mismatch: ' + str(geom['y_max']))

    if geom['hole_diameter_avg'] is None:
        return fail('CAE hole boundary nodes not found')

    if not close_enough(
        geom['hole_diameter_avg'],
        GT['hole_diameter_from_mesh_avg'],
        rel_tol=0.0,
        abs_tol=ABS_TOL_HOLE_DIAM
    ):
        return fail('CAE hole diameter mismatch: observed %s, expected %s' %
                    (str(geom['hole_diameter_avg']), str(GT['hole_diameter_from_mesh_avg'])))

    if not count_close(geom['hole_node_count'], GT['hole_boundary_node_count'], HOLE_NODE_COUNT_TOL):
        return fail('CAE hole node count mismatch: observed %s, expected %s' %
                    (str(geom['hole_node_count']), str(GT['hole_boundary_node_count'])))

    ok('CAE geometry and hole matched')

    # Do not check exact BC/load internal values here. The reference extraction itself
    # returned null for BC DOFs and null load magnitudes. Only require that objects exist.
    try:
        bc_count = len(model.boundaryConditions.keys())
        load_count = len(model.loads.keys())
        log('CAE BC names: ' + str(list(model.boundaryConditions.keys())))
        log('CAE load names: ' + str(list(model.loads.keys())))

        if bc_count < 3:
            return fail('Expected at least 3 boundary condition objects, observed %s' % str(bc_count))

        if load_count < 2:
            return fail('Expected at least 2 load objects, observed %s' % str(load_count))
    except Exception as e:
        return fail('Cannot inspect CAE loads/BCs: ' + str(e))

    ok('CAE loads and BCs exist')
    return True


# ============================================================
# 6. ODB checks
# ============================================================

def check_odb_file():
    if not os.path.exists(odb_path):
        return fail('ODB file not found: ' + odb_path)

    odb = None

    try:
        odb = openOdb(path=odb_path, readOnly=True)

        inst = get_main_instance(odb.rootAssembly)
        if inst is None:
            return fail('No instance found in ODB')

        if not count_close(len(inst.nodes), GT['odb_num_nodes'], NODE_COUNT_TOL):
            return fail('ODB node count mismatch: observed %s, expected %s' %
                        (str(len(inst.nodes)), str(GT['odb_num_nodes'])))

        if not count_close(len(inst.elements), GT['odb_num_elements'], ELEMENT_COUNT_TOL):
            return fail('ODB element count mismatch: observed %s, expected %s' %
                        (str(len(inst.elements)), str(GT['odb_num_elements'])))

        elem_counts = get_element_type_counts(inst.elements)
        log('ODB element types: ' + str(elem_counts))

        if not count_close(elem_counts.get('S4R', 0), GT['odb_s4r_count'], ELEM_TYPE_COUNT_TOL):
            return fail('ODB S4R count mismatch: observed %s, expected %s' %
                        (str(elem_counts.get('S4R', 0)), str(GT['odb_s4r_count'])))

        # In ODB the triangular elements appear as S3R in the extracted truth.
        s3r_like_count = elem_counts.get('S3R', 0) + elem_counts.get('S3', 0)
        if not count_close(s3r_like_count, GT['odb_s3r_count'], ELEM_TYPE_COUNT_TOL):
            return fail('ODB S3/S3R count mismatch: observed %s, expected %s' %
                        (str(s3r_like_count), str(GT['odb_s3r_count'])))

        ok('ODB mesh matched')

        geom = coord_extents_and_hole_from_nodes(inst.nodes)
        log('ODB geometry: ' + str(geom))

        if geom is None:
            return fail('ODB geometry is empty')

        if not close_enough(geom['x_min'], GT['mesh_x_min'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
            return fail('ODB x_min mismatch: ' + str(geom['x_min']))

        if not close_enough(geom['x_max'], GT['mesh_x_max'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
            return fail('ODB x_max mismatch: ' + str(geom['x_max']))

        if not close_enough(geom['y_min'], GT['mesh_y_min'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
            return fail('ODB y_min mismatch: ' + str(geom['y_min']))

        if not close_enough(geom['y_max'], GT['mesh_y_max'], rel_tol=0.0, abs_tol=ABS_TOL_COORD):
            return fail('ODB y_max mismatch: ' + str(geom['y_max']))

        if geom['hole_diameter_avg'] is None:
            return fail('ODB hole boundary nodes not found')

        if not close_enough(
            geom['hole_diameter_avg'],
            GT['hole_diameter_from_mesh_avg'],
            rel_tol=0.0,
            abs_tol=ABS_TOL_HOLE_DIAM
        ):
            return fail('ODB hole diameter mismatch: observed %s, expected %s' %
                        (str(geom['hole_diameter_avg']), str(GT['hole_diameter_from_mesh_avg'])))

        if not count_close(geom['hole_node_count'], GT['hole_boundary_node_count'], HOLE_NODE_COUNT_TOL):
            return fail('ODB hole node count mismatch: observed %s, expected %s' %
                        (str(geom['hole_node_count']), str(GT['hole_boundary_node_count'])))

        ok('ODB geometry and hole matched')

        step_key = get_step_key(odb.steps, GT['step_name'])
        if step_key is None:
            return fail('ODB step not found: ' + GT['step_name'])

        step = odb.steps[step_key]

        if len(step.frames) != GT['odb_num_frames']:
            return fail('ODB frame count mismatch: observed %s, expected %s' %
                        (str(len(step.frames)), str(GT['odb_num_frames'])))

        if len(step.frames) == 0:
            return fail('ODB step has no frames')

        last_frame = step.frames[-1]

        if not close_enough(last_frame.frameValue, GT['last_frame_value'], rel_tol=1.0e-8, abs_tol=ABS_TOL_FRAME):
            return fail('Last frame value mismatch: observed %s, expected %s' %
                        (str(last_frame.frameValue), str(GT['last_frame_value'])))

        ok('ODB step and frame matched')

        for required in ['U', 'S']:
            if required not in last_frame.fieldOutputs.keys():
                return fail('Required field output not found: ' + required)

        U_field = last_frame.fieldOutputs['U']
        S_field = last_frame.fieldOutputs['S']

        # ----------------------------------------------------
        # Displacement checks
        # ----------------------------------------------------
        max_u_magnitude = -1.0
        max_abs_u1 = -1.0
        max_abs_u2 = -1.0
        max_abs_u3 = -1.0

        max_u1 = None
        min_u1 = None
        max_u2 = None
        min_u2 = None

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

        log('Displacement summary: max|U|=%s, max|U1|=%s, max|U2|=%s, max|U3|=%s, maxU1=%s, minU1=%s, maxU2=%s, minU2=%s' %
            (str(max_u_magnitude), str(max_abs_u1), str(max_abs_u2), str(max_abs_u3),
             str(max_u1), str(min_u1), str(max_u2), str(min_u2)))

        if not close_enough(max_u_magnitude, GT['max_u_magnitude'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('max U magnitude mismatch: observed %s, expected %s' %
                        (str(max_u_magnitude), str(GT['max_u_magnitude'])))

        if not close_enough(max_abs_u1, GT['max_abs_u1'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('max abs U1 mismatch: observed %s, expected %s' %
                        (str(max_abs_u1), str(GT['max_abs_u1'])))

        if not close_enough(max_abs_u2, GT['max_abs_u2'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('max abs U2 mismatch: observed %s, expected %s' %
                        (str(max_abs_u2), str(GT['max_abs_u2'])))

        if max_abs_u3 > ABS_TOL_U3:
            return fail('max abs U3 too large: observed %s' % str(max_abs_u3))

        if not close_enough(max_u1, GT['max_u1'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('max U1 mismatch: observed %s, expected %s' %
                        (str(max_u1), str(GT['max_u1'])))

        if not close_enough(min_u1, GT['min_u1'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('min U1 mismatch: observed %s, expected %s' %
                        (str(min_u1), str(GT['min_u1'])))

        if not close_enough(max_u2, GT['max_u2'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('max U2 mismatch: observed %s, expected %s' %
                        (str(max_u2), str(GT['max_u2'])))

        if not close_enough(min_u2, GT['min_u2'], rel_tol=REL_TOL_DISP, abs_tol=ABS_TOL_DISP):
            return fail('min U2 mismatch: observed %s, expected %s' %
                        (str(min_u2), str(GT['min_u2'])))

        ok('ODB displacement matched')

        # ----------------------------------------------------
        # Stress checks
        # ----------------------------------------------------
        max_mises = -1.0
        max_s11 = None
        min_s11 = None

        for val in S_field.values:
            try:
                mises = float(val.mises)
                max_mises = max(max_mises, mises)
            except:
                pass

            try:
                s11 = float(val.data[0])
                max_s11 = s11 if max_s11 is None else max(max_s11, s11)
                min_s11 = s11 if min_s11 is None else min(min_s11, s11)
            except:
                pass

        log('Stress summary: maxMises=%s, maxS11=%s, minS11=%s' %
            (str(max_mises), str(max_s11), str(min_s11)))

        if not close_enough(max_mises, GT['max_mises'], rel_tol=REL_TOL_STRESS, abs_tol=ABS_TOL_STRESS):
            return fail('max Mises mismatch: observed %s, expected %s' %
                        (str(max_mises), str(GT['max_mises'])))

        if max_s11 is None or not close_enough(max_s11, GT['max_s11'], rel_tol=REL_TOL_STRESS, abs_tol=ABS_TOL_STRESS):
            return fail('max S11 mismatch: observed %s, expected %s' %
                        (str(max_s11), str(GT['max_s11'])))

        if min_s11 is None or not close_enough(min_s11, GT['min_s11'], rel_tol=REL_TOL_STRESS, abs_tol=ABS_TOL_STRESS):
            return fail('min S11 mismatch: observed %s, expected %s' %
                        (str(min_s11), str(GT['min_s11'])))

        ok('ODB stress matched')
        return True

    except Exception as e:
        log('Exception in ODB check: ' + str(e))
        log(traceback.format_exc())
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
    log('Top-level exception: ' + str(e))
    log(traceback.format_exc())
    passed = False

output_result(passed)
