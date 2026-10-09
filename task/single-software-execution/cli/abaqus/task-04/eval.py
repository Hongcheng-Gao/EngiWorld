# -*- coding: utf-8 -*-
# Process-oriented evaluator
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
import traceback

TASK_ID = 'task-04'
PROCESS_SPEC = {'artifact': {'job_name': 'Job-Tension', 'model_name': 'Model-Tension', 'step_name': 'Step-Load'},
 'process': {'geometry': {'bbox_spans': {'x': 100.0, 'y': 10.0, 'z': 10.0}, 'tol': 0.2},
             'load_signatures': [{'magnitude': 10.0, 'step': 'Step-Load', 'tol': 0.6, 'type_any': ['PRESSURE', 'SURFACETRACTION']}],
             'materials': [{'E': 210000.0, 'name': 'Steel', 'nu': 0.3}],
             'mesh': {'main_element_type': 'C3D8R', 'seed_sizes': [5.0], 'seed_tol': 0.5},
             'min_counts': {'boundary_conditions': 1, 'loads': 1},
             'section': {'material_names': ['Steel'], 'type': 'SOLID'},
             'step': {'kind': 'STATIC'}},
 'solver': {'min_frames': 2}}

ABS_TOL = 1.0e-6
GEOM_TOL = 5.0e-3
MATERIAL_TOL = 1.0e-6
SEED_TOL_DEFAULT = 1.0e-3

DETAILS = []


def log(msg):
    DETAILS.append(str(msg))


def _write_text(path, text):
    try:
        f = open(path, 'w')
        f.write(text)
        f.close()
    except Exception:
        pass


def output_result(value, detail_path=None, result_path=None):
    text = 'True\n' if value else 'False\n'
    if result_path:
        _write_text(result_path, text)
    if detail_path:
        _write_text(detail_path, ''.join([line + '\n' for line in DETAILS]))

    try:
        sys.__stdout__.write(text)
        sys.__stdout__.flush()
    except Exception:
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except Exception:
            pass


def fail(msg):
    log('[FAIL] ' + str(msg))
    return False


def ok(msg):
    log('[PASS] ' + str(msg))
    return True


def safe_float(v, default=None):
    try:
        return float(v)
    except Exception:
        return default


def close_enough(a, b, tol=ABS_TOL, rel=1.0e-3):
    fa = safe_float(a, None)
    fb = safe_float(b, None)
    if fa is None or fb is None:
        return False
    return abs(fa - fb) <= max(float(tol), abs(fb) * float(rel))


def ci(s):
    try:
        return str(s).strip().upper()
    except Exception:
        return ''


def names_equal(a, b):
    return ci(a) == ci(b)


def get_desktop(job_name):
    candidates = []
    up = os.environ.get('USERPROFILE', None)
    if up:
        candidates.append(os.path.join(up, 'Desktop'))
    candidates.append(r'C:\Users\user\Desktop')
    candidates.append(r'C:\Users\User\Desktop')

    for d in candidates:
        if os.path.exists(os.path.join(d, job_name + '.cae')) or os.path.exists(os.path.join(d, job_name + '.odb')):
            return d

    for d in candidates:
        if os.path.isdir(d):
            return d

    return r'C:\Users\user\Desktop'


def find_key_ci(repo, target):
    if target is None:
        return None
    tu = ci(target)
    try:
        for k in repo.keys():
            ku = ci(k)
            if ku == tu or ku.endswith('.' + tu):
                return k
    except Exception:
        return None
    return None


def get_repo_value_ci(repo, target):
    k = find_key_ci(repo, target)
    if k is None:
        return None
    try:
        return repo[k]
    except Exception:
        return None


def symbol_to_bool(v):
    if isinstance(v, bool):
        return v
    vu = ci(v)
    if vu in ('ON', 'TRUE', '1'):
        return True
    if vu in ('OFF', 'FALSE', '0'):
        return False
    return None


def is_set_value(v):
    vu = ci(v)
    if vu in ('', 'NONE', 'UNSET', 'UNCHANGED', 'FREED'):
        return False
    return True


def class_name(obj):
    try:
        return obj.__class__.__name__.upper()
    except Exception:
        try:
            return str(type(obj)).upper()
        except Exception:
            return ''


def step_kind_matches(step_obj, expected_kind):
    text = ' '.join([
        class_name(step_obj),
        ci(getattr(step_obj, 'procedureType', '')),
        ci(getattr(step_obj, 'analysis', '')),
    ])
    ek = ci(expected_kind)
    if ek == 'STATIC':
        return ('STATIC' in text) and ('HEAT' not in text)
    if ek == 'HEAT_TRANSFER':
        return ('HEAT' in text) or ('HEAT_TRANSFER' in text)
    if ek == 'BUCKLE':
        return 'BUCKLE' in text
    if ek == 'FREQUENCY':
        return 'FREQUENCY' in text
    return False


def choose_model(mdb_obj, expected_name=None):
    if expected_name:
        k = find_key_ci(mdb_obj.models, expected_name)
        if k is not None:
            return mdb_obj.models[k]

    best = None
    best_score = -1
    try:
        for mk in mdb_obj.models.keys():
            m = mdb_obj.models[mk]
            score = 0
            try:
                score += len(m.parts.keys()) * 10
            except Exception:
                pass
            try:
                for pk in m.parts.keys():
                    p = m.parts[pk]
                    score += len(p.elements) * 2 + len(p.nodes)
            except Exception:
                pass
            if score > best_score:
                best_score = score
                best = m
    except Exception:
        return None

    return best


def choose_primary_part(model):
    best = None
    best_score = -1
    try:
        for pk in model.parts.keys():
            p = model.parts[pk]
            score = 0
            try:
                score += len(p.elements) * 2 + len(p.nodes)
            except Exception:
                pass
            if score > best_score:
                best_score = score
                best = p
    except Exception:
        return None
    return best


def collect_node_xyz(nodes):
    out = []
    for n in nodes:
        try:
            x, y, z = n.coordinates
            out.append((float(x), float(y), float(z)))
        except Exception:
            pass
    return out


def bbox_from_xyz(xyz):
    if not xyz:
        return None
    xs = [p[0] for p in xyz]
    ys = [p[1] for p in xyz]
    zs = [p[2] for p in xyz]
    return {
        'x_min': min(xs), 'x_max': max(xs),
        'y_min': min(ys), 'y_max': max(ys),
        'z_min': min(zs), 'z_max': max(zs),
        'x_span': max(xs) - min(xs),
        'y_span': max(ys) - min(ys),
        'z_span': max(zs) - min(zs),
    }


def check_bbox(bbox, geom_spec):
    if bbox is None:
        return fail('Geometry bbox is empty')

    tol = float(geom_spec.get('tol', GEOM_TOL))

    spans = geom_spec.get('bbox_spans', None)
    if spans:
        for axis, exp in spans.items():
            key = axis.lower() + '_span'
            obs = bbox.get(key, None)
            if obs is None or not close_enough(obs, exp, tol=tol, rel=1.0e-3):
                return fail('bbox span mismatch for %s: obs=%s exp=%s tol=%s' % (axis, str(obs), str(exp), str(tol)))

    mins = geom_spec.get('bbox_mins', None)
    if mins:
        for axis, exp in mins.items():
            key = axis.lower() + '_min'
            obs = bbox.get(key, None)
            if obs is None or not close_enough(obs, exp, tol=tol, rel=1.0e-3):
                return fail('bbox min mismatch for %s: obs=%s exp=%s tol=%s' % (axis, str(obs), str(exp), str(tol)))

    maxs = geom_spec.get('bbox_maxs', None)
    if maxs:
        for axis, exp in maxs.items():
            key = axis.lower() + '_max'
            obs = bbox.get(key, None)
            if obs is None or not close_enough(obs, exp, tol=tol, rel=1.0e-3):
                return fail('bbox max mismatch for %s: obs=%s exp=%s tol=%s' % (axis, str(obs), str(exp), str(tol)))

    return True


def check_hole(xyz, hole_spec):
    if not hole_spec:
        return True

    cx = float(hole_spec['center'][0])
    cy = float(hole_spec['center'][1])
    r0 = float(hole_spec['radius'])
    tol = float(hole_spec.get('tol', 1.0))
    min_nodes = int(hole_spec.get('min_nodes', 6))

    hits = []
    for x, y, z in xyz:
        rr = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        if abs(rr - r0) <= tol:
            hits.append(rr)

    if len(hits) < min_nodes:
        return fail('hole boundary nodes too few: obs=%s min=%s' % (str(len(hits)), str(min_nodes)))

    ravg = sum(hits) / float(len(hits))
    if not close_enough(ravg, r0, tol=tol, rel=1.0e-3):
        return fail('hole radius mismatch: obs=%s exp=%s tol=%s' % (str(ravg), str(r0), str(tol)))

    return True


def get_element_type_counts(elements):
    counts = {}
    for e in elements:
        t = ci(getattr(e, 'type', 'UNKNOWN'))
        counts[t] = counts.get(t, 0) + 1
    return counts


def check_mesh(part_obj, mesh_spec):
    if not mesh_spec:
        return True

    main_type = ci(mesh_spec.get('main_element_type', ''))
    tol = float(mesh_spec.get('seed_tol', SEED_TOL_DEFAULT))

    try:
        counts = get_element_type_counts(part_obj.elements)
    except Exception:
        return fail('Cannot inspect element types')

    total = 0
    for k in counts:
        total += counts[k]

    if main_type:
        main_count = counts.get(main_type, 0)
        if main_count <= 0:
            return fail('Main element type not found: ' + str(main_type))
        if total > 0 and float(main_count) / float(total) < 0.5:
            return fail('Main element type fraction too low for %s: %s/%s' % (main_type, str(main_count), str(total)))

    seed_sizes = mesh_spec.get('seed_sizes', [])
    if seed_sizes:
        observed = []
        try:
            s = part_obj.getPartSeeds(SIZE)
            sf = safe_float(s, None)
            if sf is not None and sf > 0.0:
                observed.append(sf)
        except Exception:
            pass

        if observed:
            for exp in seed_sizes:
                expf = float(exp)
                ok_seed = False
                for ob in observed:
                    if close_enough(ob, expf, tol=tol, rel=1.0e-3):
                        ok_seed = True
                        break
                if not ok_seed:
                    return fail('seed size mismatch: expected one of %s, observed=%s' % (str(seed_sizes), str(observed)))

    return True


def _read_material_value(mat_obj, field_name):
    obj = getattr(mat_obj, field_name, None)
    if obj is None:
        return None
    tbl = getattr(obj, 'table', None)
    if tbl is None:
        return None
    try:
        if len(tbl) == 0:
            return None
        row0 = tbl[0]
        if len(row0) == 0:
            return None
        return safe_float(row0[0], None)
    except Exception:
        return None


def check_materials(model, mats_spec):
    if not mats_spec:
        return True

    for exp in mats_spec:
        mobj = get_repo_value_ci(model.materials, exp.get('name'))
        if mobj is None:
            return fail('Material not found: ' + str(exp.get('name')))

        if 'E' in exp or 'nu' in exp:
            try:
                e_obs, nu_obs = mobj.elastic.table[0]
            except Exception:
                return fail('Material elastic data missing: ' + str(exp.get('name')))

            if 'E' in exp and not close_enough(e_obs, exp['E'], tol=MATERIAL_TOL, rel=1.0e-3):
                return fail('Material E mismatch for %s: obs=%s exp=%s' % (str(exp.get('name')), str(e_obs), str(exp['E'])))
            if 'nu' in exp and not close_enough(nu_obs, exp['nu'], tol=MATERIAL_TOL, rel=1.0e-3):
                return fail('Material nu mismatch for %s: obs=%s exp=%s' % (str(exp.get('name')), str(nu_obs), str(exp['nu'])))

        if 'density' in exp:
            obs = _read_material_value(mobj, 'density')
            if obs is None or not close_enough(obs, exp['density'], tol=MATERIAL_TOL, rel=5.0e-2):
                return fail('Material density mismatch for %s: obs=%s exp=%s' % (str(exp.get('name')), str(obs), str(exp['density'])))

        if 'conductivity' in exp:
            obs = _read_material_value(mobj, 'conductivity')
            if obs is None:
                return fail('Material conductivity missing for ' + str(exp.get('name')))
            target = exp['conductivity']
            if isinstance(target, (list, tuple)):
                matched = False
                for t in target:
                    if close_enough(obs, t, tol=MATERIAL_TOL, rel=5.0e-2):
                        matched = True
                        break
                if not matched:
                    return fail('Material conductivity mismatch for %s: obs=%s exp_any=%s' % (str(exp.get('name')), str(obs), str(target)))
            else:
                if not close_enough(obs, target, tol=MATERIAL_TOL, rel=5.0e-2):
                    return fail('Material conductivity mismatch for %s: obs=%s exp=%s' % (str(exp.get('name')), str(obs), str(target)))

        if 'specific_heat' in exp:
            obs = _read_material_value(mobj, 'specificHeat')
            if obs is None or not close_enough(obs, exp['specific_heat'], tol=MATERIAL_TOL, rel=5.0e-2):
                return fail('Material specificHeat mismatch for %s: obs=%s exp=%s' % (str(exp.get('name')), str(obs), str(exp['specific_heat'])))

        if 'expansion' in exp:
            obs = _read_material_value(mobj, 'expansion')
            if obs is None or not close_enough(obs, exp['expansion'], tol=MATERIAL_TOL, rel=5.0e-2):
                return fail('Material expansion mismatch for %s: obs=%s exp=%s' % (str(exp.get('name')), str(obs), str(exp['expansion'])))

    return True


def check_section(model, part_obj, section_spec):
    if not section_spec:
        return True

    try:
        assigns = part_obj.sectionAssignments
        if len(assigns) == 0:
            return fail('No section assignment found on primary part')
    except Exception:
        return fail('Cannot inspect section assignments on primary part')

    expected_type = ci(section_spec.get('type', ''))
    expected_materials = [ci(x) for x in section_spec.get('material_names', [])]
    expected_thickness = section_spec.get('thickness', None)
    expected_int_pts = section_spec.get('num_int_pts', None)

    found_match = False
    try:
        for sk in model.sections.keys():
            sec = model.sections[sk]
            sname = class_name(sec)

            if expected_type == 'SHELL' and 'SHELL' not in sname:
                continue
            if expected_type == 'SOLID' and 'SOLID' not in sname:
                continue

            mat_name = ci(getattr(sec, 'material', ''))
            if expected_materials and mat_name not in expected_materials:
                continue

            if expected_thickness is not None:
                th = safe_float(getattr(sec, 'thickness', None), None)
                if th is None or not close_enough(th, expected_thickness, tol=GEOM_TOL, rel=1.0e-3):
                    continue

            if expected_int_pts is not None:
                nipt = getattr(sec, 'numIntPts', None)
                ni = None
                try:
                    ni = int(nipt)
                except Exception:
                    ni = None
                if ni is None or ni != int(expected_int_pts):
                    continue

            found_match = True
            break
    except Exception:
        return fail('Cannot inspect section objects')

    if not found_match:
        return fail('No matching section found for expected section spec')

    return True


def all_set_names(model, part_obj):
    names = []
    try:
        names.extend(list(model.rootAssembly.sets.keys()))
    except Exception:
        pass
    try:
        names.extend(list(model.rootAssembly.nodeSets.keys()))
    except Exception:
        pass
    try:
        names.extend(list(part_obj.sets.keys()))
    except Exception:
        pass
    return names


def set_name_exists(all_names, target):
    tu = ci(target)
    for n in all_names:
        nu = ci(n)
        if nu == tu or nu.endswith('.' + tu):
            return True
    return False


def check_required_sets(model, part_obj, set_names):
    if not set_names:
        return True
    names = all_set_names(model, part_obj)
    for s in set_names:
        if not set_name_exists(names, s):
            return fail('Required set not found: ' + str(s))
    return True


def bc_matches_req(bc_obj, req):
    step_req = req.get('step', None)
    if step_req is not None:
        cstep = getattr(bc_obj, 'createStepName', None)
        if not names_equal(cstep, step_req):
            return False

    dofs = req.get('dofs', {})
    for dof_name in dofs.keys():
        exp = dofs[dof_name]
        obs = getattr(bc_obj, dof_name, None)
        if exp == 'SET':
            if not is_set_value(obs):
                return False
        elif exp == 'UNSET':
            if is_set_value(obs):
                return False
        else:
            if not is_set_value(obs):
                return False
            if not close_enough(obs, exp, tol=ABS_TOL, rel=1.0e-3):
                return False

    return True


def check_bcs(model, bc_specs, min_count=None):
    repo = model.boundaryConditions

    if min_count is not None:
        try:
            if len(repo.keys()) < int(min_count):
                return fail('Boundary condition count too low: obs=%s min=%s' % (str(len(repo.keys())), str(min_count)))
        except Exception:
            return fail('Cannot inspect boundary condition repository')

    if not bc_specs:
        return True

    try:
        bcs = [repo[k] for k in repo.keys()]
    except Exception:
        return fail('Cannot iterate boundary conditions')

    for req in bc_specs:
        matched = False
        for bc in bcs:
            if bc_matches_req(bc, req):
                matched = True
                break
        if not matched:
            return fail('Required BC signature not found: ' + str(req))

    return True


def type_matches_any(obj, tokens):
    if not tokens:
        return True
    txt = class_name(obj)
    for t in tokens:
        if ci(t) in txt:
            return True
    return False


def load_matches_req(load_obj, req):
    if not type_matches_any(load_obj, req.get('type_any', [])):
        return False

    step_req = req.get('step', None)
    if step_req is not None:
        cstep = getattr(load_obj, 'createStepName', None)
        if not names_equal(cstep, step_req):
            return False

    if 'magnitude' in req:
        mag = getattr(load_obj, 'magnitude', None)
        if mag is None:
            return False
        tol = float(req.get('tol', ABS_TOL))
        if not close_enough(mag, req['magnitude'], tol=tol, rel=1.0e-2):
            return False

    comp = req.get('component', None)
    if comp:
        val = getattr(load_obj, comp, None)
        if val is None:
            return False
        if not is_set_value(val):
            return False
        sign = req.get('sign', None)
        vf = safe_float(val, None)
        if vf is None:
            return False
        if sign == 'positive' and vf <= 0.0:
            return False
        if sign == 'negative' and vf >= 0.0:
            return False

    return True


def check_loads(model, load_specs, min_count=None):
    repo = model.loads

    if min_count is not None:
        try:
            if len(repo.keys()) < int(min_count):
                return fail('Load count too low: obs=%s min=%s' % (str(len(repo.keys())), str(min_count)))
        except Exception:
            return fail('Cannot inspect load repository')

    if not load_specs:
        return True

    try:
        loads = [repo[k] for k in repo.keys()]
    except Exception:
        return fail('Cannot iterate loads')

    for req in load_specs:
        matched = False
        for ld in loads:
            if load_matches_req(ld, req):
                matched = True
                break
        if not matched:
            return fail('Required load signature not found: ' + str(req))

    return True


def check_couplings(model, req):
    if not req:
        return True

    min_count = int(req.get('min_count', 0))

    try:
        repo = model.constraints
        couplings = []
        for k in repo.keys():
            c = repo[k]
            if 'COUPLING' in class_name(c):
                ctype = ci(getattr(c, 'couplingType', ''))
                if 'KINEMATIC' in ctype or req.get('accept_any_coupling', False):
                    couplings.append(c)
        if len(couplings) < min_count:
            return fail('Kinematic coupling count too low: obs=%s min=%s' % (str(len(couplings)), str(min_count)))
    except Exception:
        return fail('Cannot inspect coupling constraints')

    return True


def check_contact(model, req):
    if not req:
        return True

    min_interactions = int(req.get('min_interactions', 1))
    min_props = int(req.get('min_properties', 1))

    try:
        if len(model.interactions.keys()) < min_interactions:
            return fail('Interaction count too low: obs=%s min=%s' % (str(len(model.interactions.keys())), str(min_interactions)))
    except Exception:
        return fail('Cannot inspect interactions')

    try:
        if len(model.interactionProperties.keys()) < min_props:
            return fail('Interaction property count too low: obs=%s min=%s' % (str(len(model.interactionProperties.keys())), str(min_props)))
    except Exception:
        return fail('Cannot inspect interaction properties')

    if req.get('hard', False) or req.get('frictionless', False):
        hard_ok = not req.get('hard', False)
        fric_ok = not req.get('frictionless', False)

        try:
            for k in model.interactionProperties.keys():
                ip = model.interactionProperties[k]

                if req.get('hard', False):
                    nb = getattr(ip, 'normalBehavior', None)
                    po = ci(getattr(nb, 'pressureOverclosure', '')) if nb is not None else ''
                    if 'HARD' in po:
                        hard_ok = True

                if req.get('frictionless', False):
                    tb = getattr(ip, 'tangentialBehavior', None)
                    form = ci(getattr(tb, 'formulation', '')) if tb is not None else ''
                    if 'FRICTIONLESS' in form:
                        fric_ok = True
        except Exception:
            pass

        if not hard_ok:
            return fail('Hard contact property not confirmed')
        if not fric_ok:
            return fail('Frictionless tangential behavior not confirmed')

    return True


def check_predefined_temperature(model, reqs):
    if not reqs:
        return True

    try:
        fields = [model.predefinedFields[k] for k in model.predefinedFields.keys()]
    except Exception:
        return fail('Cannot inspect predefined fields')

    for req in reqs:
        step_req = req.get('step', None)
        mag_req = req.get('magnitude', None)

        matched = False
        for pf in fields:
            if 'TEMPERATURE' not in class_name(pf):
                continue
            cstep = getattr(pf, 'createStepName', None)
            if step_req is not None and not names_equal(cstep, step_req):
                continue

            if mag_req is not None:
                mags = getattr(pf, 'magnitudes', None)
                mv = None
                try:
                    if isinstance(mags, (list, tuple)) and len(mags) > 0:
                        mv = safe_float(mags[0], None)
                    else:
                        mv = safe_float(mags, None)
                except Exception:
                    mv = None

                if mv is None:
                    matched = True
                    break

                if close_enough(mv, mag_req, tol=GEOM_TOL, rel=1.0e-2):
                    matched = True
                    break
            else:
                matched = True
                break

        if not matched:
            return fail('Required temperature predefined field not found: ' + str(req))

    return True


def check_step(model, step_spec):
    step_name = PROCESS_SPEC['artifact']['step_name']
    step_key = find_key_ci(model.steps, step_name)
    if step_key is None:
        return fail('Step not found in CAE model: ' + str(step_name))

    step_obj = model.steps[step_key]

    kind = step_spec.get('kind', None)
    if kind is not None and not step_kind_matches(step_obj, kind):
        return fail('Step kind mismatch: expected %s got class=%s procedure=%s' % (
            str(kind), class_name(step_obj), str(getattr(step_obj, 'procedureType', None))))

    if 'nlgeom' in step_spec and step_spec['nlgeom'] is not None:
        exp = bool(step_spec['nlgeom'])
        obs_raw = getattr(step_obj, 'nlgeom', None)
        obs = symbol_to_bool(obs_raw)
        if obs is None or obs != exp:
            return fail('Step nlgeom mismatch: obs=%s exp=%s' % (str(obs_raw), str(exp)))

    if 'num_eigen' in step_spec and step_spec['num_eigen'] is not None:
        obs = getattr(step_obj, 'numEigen', None)
        try:
            oi = int(obs)
        except Exception:
            return fail('Step numEigen unreadable: ' + str(obs))
        if oi != int(step_spec['num_eigen']):
            return fail('Step numEigen mismatch: obs=%s exp=%s' % (str(oi), str(step_spec['num_eigen'])))

    if 'response' in step_spec and step_spec['response'] is not None:
        obs = ci(getattr(step_obj, 'response', ''))
        if ci(step_spec['response']) not in obs:
            return fail('Step response mismatch: obs=%s exp=%s' % (str(obs), str(step_spec['response'])))

    for key, attr in [('time_period', 'timePeriod'), ('initial_inc', 'initialInc'), ('max_inc', 'maxInc'), ('deltmx', 'deltmx')]:
        if key in step_spec and step_spec[key] is not None:
            obs = getattr(step_obj, attr, None)
            if not close_enough(obs, step_spec[key], tol=GEOM_TOL, rel=1.0e-2):
                return fail('Step %s mismatch: obs=%s exp=%s' % (str(attr), str(obs), str(step_spec[key])))

    return True


def check_cae_process(cae_path):
    try:
        openMdb(pathName=cae_path)
    except Exception as e:
        return fail('Cannot open CAE: ' + str(e)), None

    model = choose_model(mdb, PROCESS_SPEC['artifact'].get('model_name', None))
    if model is None:
        return fail('Cannot choose model from CAE'), None

    part_obj = choose_primary_part(model)
    if part_obj is None:
        return fail('Cannot choose primary part from CAE'), None

    proc = PROCESS_SPEC.get('process', {})

    if not check_step(model, proc.get('step', {})):
        return False, model
    ok('Step check passed')

    if not check_materials(model, proc.get('materials', [])):
        return False, model
    ok('Material check passed')

    if not check_section(model, part_obj, proc.get('section', {})):
        return False, model
    ok('Section check passed')

    xyz = collect_node_xyz(part_obj.nodes)
    bbox = bbox_from_xyz(xyz)
    if not check_bbox(bbox, proc.get('geometry', {})):
        return False, model
    if not check_hole(xyz, proc.get('geometry', {}).get('hole', None)):
        return False, model
    ok('Geometry check passed')

    if not check_mesh(part_obj, proc.get('mesh', {})):
        return False, model
    ok('Mesh check passed')

    if not check_required_sets(model, part_obj, proc.get('required_sets', [])):
        return False, model
    ok('Set check passed')

    min_bc = None
    min_load = None
    min_counts = proc.get('min_counts', {})
    if min_counts:
        min_bc = min_counts.get('boundary_conditions', None)
        min_load = min_counts.get('loads', None)

    if not check_bcs(model, proc.get('bc_signatures', []), min_count=min_bc):
        return False, model
    ok('BC check passed')

    load_ok = check_loads(model, proc.get('load_signatures', []), min_count=min_load)
    if load_ok:
        ok('Load check passed')
    else:
        if not check_keyword_bcs_loads_b(model, proc):
            return False, model
        ok('Keyword B-load fallback passed')

    if not check_couplings(model, proc.get('kinematic_coupling', None)):
        return False, model
    if proc.get('kinematic_coupling', None):
        ok('Coupling check passed')

    if not check_contact(model, proc.get('contact', None)):
        return False, model
    if proc.get('contact', None):
        ok('Contact check passed')

    if not check_predefined_temperature(model, proc.get('predefined_temperatures', [])):
        return False, model
    if proc.get('predefined_temperatures', []):
        ok('Predefined temperature check passed')

    return True, model



def check_keyword_bcs_loads_b(model, proc):
    text = ''
    try:
        model.keywordBlock.synchVersions(storeNodesAndElements=False)
        text = '\n'.join([str(x) for x in model.keywordBlock.sieBlocks]).upper()
    except Exception:
        return fail('Cannot read keyword block text for B-task load check')

    # load type presence check from keywords (imported objects may hide attrs)
    for req in proc.get('load_signatures', []):
        types = [ci(x) for x in req.get('type_any', [])]
        matched = False
        for tp in types:
            if 'SURFACETRACTION' in tp and ('*DSLOAD' in text or 'TRVEC' in text):
                matched = True
            if 'PRESSURE' in tp and ('*DLOAD' in text or '*DSLOAD' in text):
                matched = True
            if 'MOMENT' in tp and '*CLOAD' in text:
                matched = True
        if not matched:
            return fail('Keyword load signature not found for any of %s' % str(types))

    return True

def check_odb_completion(odb_path):
    solver_spec = PROCESS_SPEC.get('solver', {})
    min_frames = int(solver_spec.get('min_frames', 1))
    require_mode_frames = bool(solver_spec.get('require_mode_frames', False))

    odb = None
    try:
        odb = openOdb(path=odb_path, readOnly=True)

        step_key = find_key_ci(odb.steps, PROCESS_SPEC['artifact']['step_name'])
        if step_key is None:
            return fail('Target step not found in ODB: ' + str(PROCESS_SPEC['artifact']['step_name']))

        step = odb.steps[step_key]
        nf = len(step.frames)
        if nf < min_frames:
            return fail('ODB frame count too low: obs=%s min=%s' % (str(nf), str(min_frames)))

        if require_mode_frames and nf <= 1:
            return fail('ODB mode frames missing (need >1 frame for perturbation step)')

        try:
            status = ci(getattr(odb.diagnosticData, 'jobStatus', ''))
            if status and ('ABORT' in status or 'TERMINAT' in status):
                return fail('ODB diagnostic status indicates failure: ' + str(status))
        except Exception:
            pass

        last_frame = step.frames[-1]
        try:
            fv = safe_float(last_frame.frameValue, None)
            if fv is None:
                return fail('Last frame value is not numeric')
        except Exception:
            return fail('Cannot read last frame value')

        ok('ODB completion check passed')
        return True

    except Exception as e:
        log(traceback.format_exc())
        return fail('Cannot open/inspect ODB: ' + str(e))
    finally:
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass


def artifact_check(desktop):
    job_name = PROCESS_SPEC['artifact']['job_name']
    cae_path = os.path.join(desktop, job_name + '.cae')
    odb_path = os.path.join(desktop, job_name + '.odb')

    if not os.path.exists(cae_path):
        return fail('CAE missing: ' + cae_path), None, None
    if not os.path.exists(odb_path):
        return fail('ODB missing: ' + odb_path), None, None

    return True, cae_path, odb_path


def check_task():
    job_name = PROCESS_SPEC['artifact']['job_name']
    desktop = get_desktop(job_name)
    detail_path = os.path.join(desktop, 'eval_detail.txt')
    result_path = os.path.join(desktop, 'eval_result.txt')

    ok_art, cae_path, odb_path = artifact_check(desktop)
    if not ok_art:
        output_result(False, detail_path=detail_path, result_path=result_path)
        return False
    ok('Artifact check passed')

    ok_cae, _model = check_cae_process(cae_path)
    if not ok_cae:
        output_result(False, detail_path=detail_path, result_path=result_path)
        return False

    if not check_odb_completion(odb_path):
        output_result(False, detail_path=detail_path, result_path=result_path)
        return False

    output_result(True, detail_path=detail_path, result_path=result_path)
    return True


def main():
    check_task()


if __name__ == '__main__':
    main()
