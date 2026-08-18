# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import math
import os
import sys
import traceback


JOB_NAME = 'Job-Contact'
MODEL_NAME = 'Model-Contact'
STEP_NAME = 'Step-Contact'
SEED_NAME = 'Contact-Seed.cae'
GEOM_TOL = 1.0e-4
DETAILS = []


def log(message):
    DETAILS.append(str(message))


def write_text(path, text):
    try:
        handle = open(path, 'w')
        handle.write(text)
        handle.close()
    except Exception:
        pass


def output_result(value, desktop):
    result = 'True\n' if value else 'False\n'
    write_text(os.path.join(desktop, 'eval_result.txt'), result)
    write_text(os.path.join(desktop, 'eval_detail.txt'),
               ''.join(line + '\n' for line in DETAILS))
    try:
        sys.__stdout__.write(result)
        sys.__stdout__.flush()
    except Exception:
        sys.stdout.write(result)
        sys.stdout.flush()


def fail(message):
    log('[FAIL] ' + str(message))
    return False


def passed(message):
    log('[PASS] ' + str(message))
    return True


def ci(value):
    try:
        return str(value).strip().upper()
    except Exception:
        return ''


def compact_name(value):
    return ''.join(character for character in ci(value)
                   if character.isalnum())


def close_enough(observed, expected, tol=1.0e-6, rel=1.0e-4):
    try:
        observed = float(observed)
        expected = float(expected)
    except Exception:
        return False
    return abs(observed - expected) <= max(float(tol), abs(expected) * rel)


def symbol_is_true(value):
    if isinstance(value, bool):
        return value
    return ci(value) in ('ON', 'TRUE', 'YES', '1')


def class_name(value):
    try:
        return value.__class__.__name__.upper()
    except Exception:
        return ci(type(value))


def get_desktop():
    candidates = []
    profile = os.environ.get('USERPROFILE')
    if profile:
        candidates.append(os.path.join(profile, 'Desktop'))
    candidates.extend((r'C:\Users\user\Desktop', r'C:\Users\User\Desktop'))
    for path in candidates:
        if os.path.isdir(path):
            return path
    return r'C:\Users\user\Desktop'


def has_forbidden_python(desktop):
    try:
        names = os.listdir(desktop)
    except Exception:
        return True
    for name in names:
        path = os.path.join(desktop, name)
        if (os.path.isfile(path) and name.lower().endswith('.py') and
                name.lower() != 'eval.py'):
            return True
    return False


def repo_value(repo, target):
    wanted = ci(target)
    try:
        for key in repo.keys():
            if ci(key) == wanted:
                return repo[key]
    except Exception:
        pass
    return None


def region_name(region):
    if isinstance(region, (list, tuple)):
        return str(region[0]) if region else None
    return str(region) if region is not None else None


def walk_node_coords(value, output):
    try:
        coordinates = value.coordinates
        output.append(tuple(float(component) for component in coordinates))
        return
    except Exception:
        pass
    try:
        for child in value:
            walk_node_coords(child, output)
    except Exception:
        pass


def node_coords(nodes):
    output = []
    walk_node_coords(nodes, output)
    return output


def vertex_coords(vertices):
    output = []
    for vertex in vertices:
        try:
            point = vertex.pointOn
            if len(point) == 1 and hasattr(point[0], '__len__'):
                point = point[0]
            output.append(tuple(float(component) for component in point))
        except Exception:
            pass
    return output


def bbox(coords):
    if not coords:
        return None
    return {
        'x_min': min(point[0] for point in coords),
        'x_max': max(point[0] for point in coords),
        'y_min': min(point[1] for point in coords),
        'y_max': max(point[1] for point in coords),
        'z_min': min(point[2] for point in coords),
        'z_max': max(point[2] for point in coords),
    }


def bbox_matches(observed, expected, tol=GEOM_TOL):
    if observed is None:
        return False
    return all(close_enough(observed[key], value, tol=tol, rel=1.0e-6)
               for key, value in expected.items())


def part_bbox(part, meshed):
    coords = node_coords(part.nodes) if meshed else vertex_coords(part.vertices)
    return bbox(coords)


def instance_bbox(instance, meshed):
    coords = node_coords(instance.nodes) if meshed else vertex_coords(instance.vertices)
    return bbox(coords)


def model_geometry_ok(model, meshed):
    block = repo_value(model.parts, 'Block')
    plate = repo_value(model.parts, 'Plate')
    if block is None or plate is None or len(model.parts.keys()) != 2:
        return False
    if not bbox_matches(part_bbox(block, meshed), {
            'x_min': 0.0, 'x_max': 10.0,
            'y_min': 0.0, 'y_max': 10.0,
            'z_min': 0.0, 'z_max': 12.0}):
        return False
    if not bbox_matches(part_bbox(plate, meshed), {
            'x_min': 0.0, 'x_max': 30.0,
            'y_min': 0.0, 'y_max': 30.0,
            'z_min': 0.0, 'z_max': 4.0}):
        return False
    assembly = model.rootAssembly
    block_instance = repo_value(assembly.instances, 'BLOCK-1')
    plate_instance = repo_value(assembly.instances, 'PLATE-1')
    if block_instance is None or plate_instance is None:
        return False
    if not bbox_matches(instance_bbox(block_instance, meshed), {
            'x_min': 10.0, 'x_max': 20.0,
            'y_min': 10.0, 'y_max': 20.0,
            'z_min': 4.0, 'z_max': 16.0}):
        return False
    if not bbox_matches(instance_bbox(plate_instance, meshed), {
            'x_min': 0.0, 'x_max': 30.0,
            'y_min': 0.0, 'y_max': 30.0,
            'z_min': 0.0, 'z_max': 4.0}):
        return False
    return True


def required_region_names(model):
    assembly = model.rootAssembly
    for name in ('SURF_BLOCK_TOP', 'SURF_BLOCK_BOTTOM', 'SURF_PLATE_TOP'):
        if repo_value(assembly.surfaces, name) is None:
            return False
    for name in ('SET_PLATE_BOTTOM', 'SET_BLOCK_GUIDE_A',
                 'SET_BLOCK_GUIDE_B'):
        if repo_value(assembly.sets, name) is None:
            return False
    return True


def check_seed(seed_path):
    try:
        openMdb(pathName=seed_path)
        model = repo_value(mdb.models, MODEL_NAME)
        if model is None:
            return fail('Seed model is missing')
        if not model_geometry_ok(model, meshed=False):
            return fail('Seed geometry/assembly is not the required baseline')
        if not required_region_names(model):
            return fail('Seed named regions are incomplete')
        if (len(model.steps.keys()) != 1 or len(model.interactions.keys()) != 0 or
                len(model.boundaryConditions.keys()) != 0 or
                len(model.loads.keys()) != 0 or len(mdb.jobs.keys()) != 0):
            return fail('Seed is already completed or has analysis objects')
        for part in model.parts.values():
            if len(part.nodes) != 0 or len(part.elements) != 0:
                return fail('Seed must remain unmeshed')
        return passed('Incomplete native seed check passed')
    except Exception as exc:
        log(traceback.format_exc())
        return fail('Cannot inspect seed CAE: ' + str(exc))


def material_section_ok(model):
    material = repo_value(model.materials, 'Steel')
    if material is None:
        return False
    try:
        elastic = material.elastic.table[0]
        if (not close_enough(elastic[0], 210000.0, tol=0.1) or
                not close_enough(elastic[1], 0.3, tol=1.0e-5)):
            return False
    except Exception:
        return False
    section = repo_value(model.sections, 'Steel-Solid')
    if section is None or ci(getattr(section, 'material', '')) != 'STEEL':
        return False
    for part_name in ('Block', 'Plate'):
        part = repo_value(model.parts, part_name)
        if part is None or not part.sectionAssignments:
            return False
        if not any(ci(getattr(item, 'sectionName', '')) == 'STEEL-SOLID'
                   for item in part.sectionAssignments):
            return False
    return True


def mesh_ok(model):
    specifications = {
        'Block': (2.0, 252, 150),
        'Plate': (3.0, 242, 100),
    }
    total_nodes = 0
    for name, (seed, nodes, elements) in specifications.items():
        part = repo_value(model.parts, name)
        if part is None:
            return False
        if (len(part.nodes) != nodes or len(part.elements) != elements or
                not close_enough(part.getPartSeeds(SIZE), seed,
                                 tol=1.0e-3, rel=1.0e-5)):
            return False
        if set(ci(element.type) for element in part.elements) != set(['C3D8R']):
            return False
        for cell in part.cells:
            try:
                technique = part.getMeshControl(cell, TECHNIQUE)
                elem_shape = part.getMeshControl(cell, ELEM_SHAPE)
            except Exception:
                return False
            if ci(technique) != 'STRUCTURED' or ci(elem_shape) != 'HEX':
                log('[FAIL] %s mesh must use STRUCTURED HEX controls' % name)
                return False
        total_nodes += len(part.nodes)
    return total_nodes == 494 and total_nodes < 1000


def surface_bbox(assembly, name):
    surface = repo_value(assembly.surfaces, name)
    return bbox(node_coords(surface.nodes)) if surface is not None else None


def set_bbox(assembly, name):
    region = repo_value(assembly.sets, name)
    return bbox(node_coords(region.nodes)) if region is not None else None


def surface_set_geometry(model):
    assembly = model.rootAssembly
    expected_surfaces = {
        'SURF_BLOCK_TOP': {
            'x_min': 10.0, 'x_max': 20.0,
            'y_min': 10.0, 'y_max': 20.0,
            'z_min': 16.0, 'z_max': 16.0},
        'SURF_BLOCK_BOTTOM': {
            'x_min': 10.0, 'x_max': 20.0,
            'y_min': 10.0, 'y_max': 20.0,
            'z_min': 4.0, 'z_max': 4.0},
        'SURF_PLATE_TOP': {
            'x_min': 0.0, 'x_max': 30.0,
            'y_min': 0.0, 'y_max': 30.0,
            'z_min': 4.0, 'z_max': 4.0},
    }
    for name, expected in expected_surfaces.items():
        if not bbox_matches(surface_bbox(assembly, name), expected):
            return False, None
    expected_sets = {
        'SET_PLATE_BOTTOM': {
            'x_min': 0.0, 'x_max': 30.0,
            'y_min': 0.0, 'y_max': 30.0,
            'z_min': 0.0, 'z_max': 0.0},
        'SET_BLOCK_GUIDE_A': {
            'x_min': 10.0, 'x_max': 10.0,
            'y_min': 10.0, 'y_max': 10.0,
            'z_min': 4.0, 'z_max': 4.0},
        'SET_BLOCK_GUIDE_B': {
            'x_min': 20.0, 'x_max': 20.0,
            'y_min': 10.0, 'y_max': 10.0,
            'z_min': 4.0, 'z_max': 4.0},
    }
    for name, expected in expected_sets.items():
        if not bbox_matches(set_bbox(assembly, name), expected):
            return False, None
    top = expected_surfaces['SURF_BLOCK_TOP']
    area = (top['x_max'] - top['x_min']) * (top['y_max'] - top['y_min'])
    return True, area


def keyword_groups(model):
    model.keywordBlock.synchVersions(storeNodesAndElements=False)
    step_name = 'Initial'
    groups = []
    for raw in model.keywordBlock.sieBlocks:
        lines = [line.strip() for line in str(raw).splitlines()
                 if line.strip() and not line.lstrip().startswith('**')]
        if not lines:
            continue
        header = ci(lines[0])
        if header.startswith('*STEP'):
            step_name = header_parameter(lines[0], 'NAME') or ''
            groups.append((step_name, header, lines[1:]))
        elif header.startswith('*END STEP'):
            step_name = 'Initial'
        else:
            groups.append((step_name, header, lines[1:]))
    return groups


def header_parameter(header, name):
    for field in header.split(',')[1:]:
        pair = field.split('=', 1)
        if len(pair) == 2 and ci(pair[0]) == ci(name):
            return pair[1].strip()
    return None


def header_has_flag(header, name):
    return any(ci(field) == ci(name) for field in header.split(',')[1:])


def line_fields(line):
    return [field.strip() for field in line.split(',')]


def keyword_semantics(model):
    groups = keyword_groups(model)
    step = repo_value(model.steps, STEP_NAME)
    if (step is None or 'STATIC' not in class_name(step) or
            ci(getattr(step, 'previous', '')) != 'INITIAL' or
            not symbol_is_true(getattr(step, 'nlgeom', False)) or
            not close_enough(getattr(step, 'initialInc', None), 0.05,
                             tol=1.0e-10, rel=1.0e-8) or
            not close_enough(getattr(step, 'maxInc', None), 0.1,
                             tol=1.0e-10, rel=1.0e-8) or
            not close_enough(getattr(step, 'minInc', None), 1.0e-8,
                             tol=1.0e-12, rel=1.0e-8) or
            int(getattr(step, 'maxNumInc', -1)) != 200):
        log('[FAIL] StaticStep controls mismatch')
        return False, None
    if len(model.steps.keys()) != 2:
        return False, None

    active_pressures = []
    for load in model.loads.values():
        if ('PRESSURE' in class_name(load) and
                not symbol_is_true(getattr(load, 'suppressed', False)) and
                ci(getattr(load, 'distributionType', '')) == 'UNIFORM'):
            active_pressures.append(load)
    if len(active_pressures) != 1 or len(model.loads.keys()) != 1:
        return False, None
    if ci(region_name(active_pressures[0].region)) != 'SURF_BLOCK_TOP':
        return False, None

    bc_regions = []
    for bc in model.boundaryConditions.values():
        if not symbol_is_true(getattr(bc, 'suppressed', False)):
            bc_regions.append(ci(region_name(getattr(bc, 'region', None))))
    if (len(model.boundaryConditions.keys()) != 3 or
            set(bc_regions) != set(['SET_PLATE_BOTTOM', 'SET_BLOCK_GUIDE_A',
                                    'SET_BLOCK_GUIDE_B'])):
        return False, None
    if len(model.interactions.keys()) != 1 or len(model.interactionProperties.keys()) != 1:
        return False, None
    interaction = list(model.interactions.values())[0]
    if ('SURFACETOSURFACESTD' not in compact_name(class_name(interaction)) or
            symbol_is_true(getattr(interaction, 'suppressed', False)) or
            ci(getattr(interaction, 'sliding', '')) != 'FINITE' or
            ci(region_name(getattr(interaction, 'main', None))) != 'SURF_PLATE_TOP' or
            ci(region_name(getattr(interaction, 'secondary', None))) !=
            'SURF_BLOCK_BOTTOM'):
        log('[FAIL] Finite-sliding surface-to-surface contact object mismatch')
        return False, None
    interaction_property = list(model.interactionProperties.values())[0]
    normal_behavior = compact_name(
        getattr(interaction_property, 'normalBehavior', ''))
    tangential_behavior = compact_name(
        getattr(interaction_property, 'tangentialBehavior', ''))
    if ('PRESSUREOVERCLOSUREHARD' not in normal_behavior or
            'ALLOWSEPARATIONON' not in normal_behavior or
            'FORMULATIONFRICTIONLESS' not in tangential_behavior):
        log('[FAIL] Hard/separation-allowed/frictionless property mismatch')
        return False, None

    pressure_values = []
    boundaries = {}
    step_header_ok = False
    static_controls_ok = False
    contact_ok = False
    hard_ok = False
    frictionless_ok = False
    for step_name, header, lines in groups:
        if step_name == STEP_NAME and header.startswith('*STEP'):
            try:
                step_header_ok = (
                    ci(header_parameter(header, 'NAME')) == ci(STEP_NAME) and
                    ci(header_parameter(header, 'NLGEOM')) in ('YES', 'ON') and
                    int(float(header_parameter(header, 'INC'))) == 200)
            except Exception:
                step_header_ok = False
        if step_name == STEP_NAME and header.startswith('*STATIC'):
            try:
                values = [float(field) for field in line_fields(lines[0])[:4]]
                static_controls_ok = (
                    len(values) == 4 and
                    close_enough(values[0], 0.05, tol=1.0e-10,
                                 rel=1.0e-8) and
                    close_enough(values[1], 1.0, tol=1.0e-10,
                                 rel=1.0e-8) and
                    close_enough(values[2], 1.0e-8, tol=1.0e-12,
                                 rel=1.0e-8) and
                    close_enough(values[3], 0.1, tol=1.0e-10,
                                 rel=1.0e-8))
            except Exception:
                static_controls_ok = False
        if step_name == STEP_NAME and header.startswith('*DSLOAD'):
            for line in lines:
                fields = line_fields(line)
                if (len(fields) >= 3 and ci(fields[0]) == 'SURF_BLOCK_TOP' and
                        ci(fields[1]) == 'P'):
                    try:
                        pressure_values.append(float(fields[2]))
                    except Exception:
                        pass
        if step_name == 'Initial' and header.startswith('*BOUNDARY'):
            for line in lines:
                fields = line_fields(line)
                name = ci(fields[0]) if fields else ''
                if len(fields) >= 2 and ci(fields[1]) == 'ENCASTRE':
                    boundaries.setdefault(name, set()).add('ENCASTRE')
                elif len(fields) >= 3:
                    try:
                        first = int(float(fields[1]))
                        last = int(float(fields[2]))
                        boundaries.setdefault(name, set()).update(range(first, last + 1))
                    except Exception:
                        pass
        if step_name == 'Initial' and header.startswith('*CONTACT PAIR'):
            prop = header_parameter(header, 'INTERACTION')
            for line in lines:
                fields = line_fields(line)
                if (ci(prop) == 'FRICTIONLESS-HARD' and
                        ci(header_parameter(header, 'TYPE')) ==
                        'SURFACE TO SURFACE' and
                        not header_has_flag(header, 'SMALL SLIDING') and
                        len(fields) >= 2 and
                        ci(fields[0]) == 'SURF_BLOCK_BOTTOM' and
                        ci(fields[1]) == 'SURF_PLATE_TOP'):
                    contact_ok = True
        if header.startswith('*SURFACE BEHAVIOR'):
            hard_ok = (
                ci(header_parameter(header, 'PRESSURE-OVERCLOSURE')) == 'HARD' and
                not header_has_flag(header, 'NO SEPARATION'))
        if header.startswith('*FRICTION'):
            for line in lines:
                fields = line_fields(line)
                try:
                    if fields and close_enough(float(fields[0]), 0.0, tol=1.0e-8):
                        frictionless_ok = True
                except Exception:
                    pass

    if not step_header_ok or not static_controls_ok:
        log('[FAIL] Step keyword controls mismatch')
        return False, None
    if len(pressure_values) != 1 or pressure_values[0] <= 0.0:
        return False, None
    if not close_enough(pressure_values[0], 5.0, tol=1.0e-5):
        log('[FAIL] Pressure magnitude mismatch: expected 5.0 MPa, got %s MPa' %
            pressure_values[0])
        return False, None
    if boundaries.get('SET_PLATE_BOTTOM') != set(['ENCASTRE']):
        return False, None
    if boundaries.get('SET_BLOCK_GUIDE_A') != set([1, 2]):
        return False, None
    if boundaries.get('SET_BLOCK_GUIDE_B') != set([2]):
        return False, None
    if not (contact_ok and hard_ok and frictionless_ok):
        return False, None
    return True, pressure_values[0]


def check_completed_cae(cae_path):
    try:
        openMdb(pathName=cae_path)
        model = repo_value(mdb.models, MODEL_NAME)
        if model is None:
            return fail('Completed model is missing'), None, None
        if not model_geometry_ok(model, meshed=True):
            return fail('Completed geometry/assembly mismatch'), None, None
        if not material_section_ok(model):
            return fail('Material/section mismatch'), None, None
        if not mesh_ok(model):
            return fail('C3D8R mesh/seeds/counts mismatch'), None, None
        geometry_ok, pressure_area = surface_set_geometry(model)
        if not geometry_ok:
            return fail('Load/contact/BC region geometry mismatch'), None, None
        semantics_ok, pressure = keyword_semantics(model)
        if not semantics_ok:
            return fail('Step/contact/load/BC semantics mismatch'), None, None
        passed('Completed CAE semantic and mesh checks passed')
        return True, model, pressure * pressure_area
    except Exception as exc:
        log(traceback.format_exc())
        return fail('Cannot inspect completed CAE: ' + str(exc)), None, None


def node_signature(nodes):
    result = []
    for node in nodes:
        try:
            result.append((int(node.label),) + tuple(
                round(float(component), 6) for component in node.coordinates))
        except Exception:
            return None
    return tuple(sorted(result))


def element_signature(instance):
    result = []
    node_map = {}
    for node in instance.nodes:
        node_map[int(node.label)] = tuple(
            round(float(component), 6) for component in node.coordinates)
    for element in instance.elements:
        try:
            element_nodes = list(element.getNodes())
        except Exception:
            try:
                element_nodes = [node_map[int(label)]
                                 for label in element.connectivity]
            except Exception:
                return None
        coordinates = []
        for node in element_nodes:
            if hasattr(node, 'coordinates'):
                coordinates.append(tuple(round(float(component), 6)
                                         for component in node.coordinates))
            else:
                coordinates.append(tuple(node))
        result.append((int(element.label), ci(element.type),
                       tuple(sorted(coordinates))))
    return tuple(sorted(result))


def field_by_prefix(frame, prefix):
    matches = []
    for key in frame.fieldOutputs.keys():
        if ci(key).startswith(ci(prefix)):
            matches.append((key, frame.fieldOutputs[key]))
    return matches[0] if len(matches) == 1 else (None, None)


def vector_magnitude(data):
    try:
        total = 0.0
        for component in data:
            total += float(component) ** 2
        return math.sqrt(total)
    except Exception:
        return abs(float(data))


def check_odb(odb_path, cae_model, applied_force):
    odb = None
    try:
        odb = openOdb(path=odb_path, readOnly=True, readInternalSets=True)
        status = ci(getattr(odb.diagnosticData, 'jobStatus', ''))
        if 'COMPLETED_SUCCESSFULLY' not in status:
            return fail('ODB diagnostic status is not successful')
        version = ci(str(odb.jobData))
        if 'LEARNING EDITION 2025' not in version:
            return fail('ODB was not generated by Abaqus Learning Edition 2025')
        if len(odb.steps.keys()) != 1 or repo_value(odb.steps, STEP_NAME) is None:
            return fail('ODB step mismatch')
        step = repo_value(odb.steps, STEP_NAME)
        if len(step.frames) < 2 or not close_enough(step.frames[-1].frameValue,
                                                   1.0, tol=1.0e-6):
            return fail('ODB completion frame mismatch')

        for name in ('BLOCK-1', 'PLATE-1'):
            cae_instance = repo_value(cae_model.rootAssembly.instances, name)
            odb_instance = repo_value(odb.rootAssembly.instances, name)
            if cae_instance is None or odb_instance is None:
                return fail('CAE/ODB instance missing: ' + name)
            if node_signature(cae_instance.nodes) != node_signature(odb_instance.nodes):
                return fail('CAE/ODB node signature mismatch: ' + name)
            if element_signature(cae_instance) != element_signature(odb_instance):
                return fail('CAE/ODB element signature mismatch: ' + name)

        odb_surfaces = odb.rootAssembly.surfaces
        for name in ('SURF_BLOCK_TOP', 'SURF_BLOCK_BOTTOM', 'SURF_PLATE_TOP'):
            if repo_value(odb_surfaces, name) is None:
                return fail('ODB surface missing: ' + name)

        frame = step.frames[-1]
        u_key, displacement = field_by_prefix(frame, 'U')
        s_key, stress = field_by_prefix(frame, 'S')
        rf_key, reaction = field_by_prefix(frame, 'RF')
        cp_key, contact_pressure = field_by_prefix(frame, 'CPRESS')
        if None in (u_key, s_key, rf_key, cp_key):
            return fail('Required U/S/RF/CPRESS result field missing or ambiguous')
        contact_key = compact_name(cp_key)
        if ('SURFBLOCKBOTTOM' not in contact_key or
                'SURFPLATETOP' not in contact_key):
            return fail('CPRESS field is not for the required contact pair')

        u_values = list(displacement.values)
        s_values = list(stress.values)
        rf_values = list(reaction.values)
        cp_values = list(contact_pressure.values)
        if (len(u_values) != 494 or len(s_values) != 250 or
                len(rf_values) != 494 or not cp_values):
            return fail('Required result field population mismatch')
        max_u = max(vector_magnitude(value.data) for value in u_values)
        max_mises = max(float(value.mises) for value in s_values)
        max_cpress = max(float(value.data) for value in cp_values)
        min_cpress = min(float(value.data) for value in cp_values)
        if not (1.0e-8 < max_u < 0.1):
            return fail('Displacement result is missing or nonphysical')
        if not (0.1 < max_mises < 1000.0):
            return fail('Stress result is missing or nonphysical')
        if max_cpress <= 0.1 or min_cpress < -1.0e-6:
            return fail('CPRESS result is missing or nonphysical')

        reaction_sum = [0.0, 0.0, 0.0]
        for value in rf_values:
            for index in range(min(3, len(value.data))):
                reaction_sum[index] += float(value.data[index])
        if abs(reaction_sum[0]) > max(0.05, applied_force * 1.0e-3):
            return fail('Unexpected total X reaction')
        if abs(reaction_sum[1]) > max(0.05, applied_force * 1.0e-3):
            return fail('Unexpected total Y reaction')
        if (reaction_sum[2] <= 0.0 or
                abs(reaction_sum[2] - applied_force) > applied_force * 0.02):
            return fail('Total RF3 does not balance the pressure load')

        log('[PASS] ODB fields: maxU=%s maxMises=%s maxCPRESS=%s '
            'RF=(%s,%s,%s) applied=%s' %
            (max_u, max_mises, max_cpress, reaction_sum[0],
             reaction_sum[1], reaction_sum[2], applied_force))
        return passed('ODB completion, linkage, fields, and equilibrium checks passed')
    except Exception as exc:
        log(traceback.format_exc())
        return fail('Cannot inspect ODB: ' + str(exc))
    finally:
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass


def check_task():
    desktop = get_desktop()
    if has_forbidden_python(desktop):
        fail('Forbidden Python file found on Desktop')
        output_result(False, desktop)
        return False
    seed_path = os.path.join(desktop, SEED_NAME)
    cae_path = os.path.join(desktop, JOB_NAME + '.cae')
    odb_path = os.path.join(desktop, JOB_NAME + '.odb')
    if not all(os.path.isfile(path) for path in (seed_path, cae_path, odb_path)):
        fail('Seed CAE, completed CAE, or solved ODB is missing')
        output_result(False, desktop)
        return False
    if not check_seed(seed_path):
        output_result(False, desktop)
        return False
    cae_ok, model, applied_force = check_completed_cae(cae_path)
    if not cae_ok:
        output_result(False, desktop)
        return False
    if not check_odb(odb_path, model, applied_force):
        output_result(False, desktop)
        return False
    output_result(True, desktop)
    return True


if __name__ == '__main__':
    check_task()
