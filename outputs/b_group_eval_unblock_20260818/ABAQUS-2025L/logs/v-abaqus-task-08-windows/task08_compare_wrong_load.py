# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *

import os


DESKTOP = r'C:\Users\user\Desktop'
SOURCE = os.path.join(DESKTOP, 'Job-Contact-Source.cae')
VARIANT = os.path.join(DESKTOP, 'Job-Contact-WrongLoad.cae')
RESULT = os.path.join(DESKTOP, 'task08_compare_wrong_load.txt')
MODEL = 'Model-Contact'


def region_name(region):
    if isinstance(region, (list, tuple)):
        return str(region[0]) if region else None
    return str(region) if region is not None else None


def safe_attribute(value, name):
    try:
        return str(getattr(value, name))
    except Exception:
        return '<unavailable>'


def compact(value):
    return ''.join(character for character in str(value).upper()
                   if character.isalnum())


def node_signature(nodes):
    return tuple(sorted(
        (int(node.label), tuple(round(float(value), 9)
                                for value in node.coordinates))
        for node in nodes))


def element_signature(elements):
    return tuple(sorted(
        (int(element.label), str(element.type),
         tuple(int(label) for label in element.connectivity))
        for element in elements))


def nested_node_signature(nodes):
    output = []
    try:
        for value in nodes:
            if hasattr(value, 'coordinates'):
                output.append((int(value.label), tuple(
                    round(float(component), 9)
                    for component in value.coordinates)))
            else:
                output.extend(nested_node_signature(value))
    except Exception:
        pass
    return tuple(sorted(output))


def keyword_signatures(model):
    model.keywordBlock.synchVersions(storeNodesAndElements=False)
    pressure = None
    semantics = []
    included = ('*STEP', '*STATIC', '*CONTACT PAIR', '*SURFACE BEHAVIOR',
                '*FRICTION', '*BOUNDARY', '*OUTPUT', '*NODE OUTPUT',
                '*ELEMENT OUTPUT', '*CONTACT OUTPUT')
    for raw in model.keywordBlock.sieBlocks:
        lines = [line.strip() for line in str(raw).splitlines()
                 if line.strip() and not line.lstrip().startswith('**')]
        if lines and lines[0].upper().startswith('*DSLOAD'):
            for line in lines[1:]:
                fields = [field.strip() for field in line.split(',')]
                if (len(fields) >= 3 and
                        fields[0].upper() == 'SURF_BLOCK_TOP' and
                        fields[1].upper() == 'P'):
                    pressure = float(fields[2])
        elif lines and lines[0].upper().startswith(included):
            semantics.append(tuple(lines))
    return pressure, tuple(semantics)


def signatures(path):
    openMdb(pathName=path)
    model = mdb.models[MODEL]
    assembly = model.rootAssembly
    pressure, keyword_semantics = keyword_signatures(model)
    result = {'pressure': pressure, 'keyword_semantics': keyword_semantics}
    for name in ('Block', 'Plate'):
        part = model.parts[name]
        result['part_' + name + '_nodes'] = node_signature(part.nodes)
        result['part_' + name + '_elements'] = element_signature(part.elements)
        result['part_' + name + '_mesh_controls'] = tuple(
            (int(cell.index), str(part.getMeshControl(cell, TECHNIQUE)),
             str(part.getMeshControl(cell, ELEM_SHAPE)))
            for cell in part.cells)
        result['part_' + name + '_section_assignments'] = tuple(sorted(
            safe_attribute(assignment, 'sectionName')
            for assignment in part.sectionAssignments))
    for name in ('BLOCK-1', 'PLATE-1'):
        instance = assembly.instances[name]
        result['instance_' + name + '_nodes'] = node_signature(instance.nodes)
        result['instance_' + name + '_elements'] = element_signature(
            instance.elements)
    for name in ('SURF_BLOCK_TOP', 'SURF_BLOCK_BOTTOM', 'SURF_PLATE_TOP'):
        result['surface_' + name] = nested_node_signature(
            assembly.surfaces[name].nodes)
    for name in ('SET_PLATE_BOTTOM', 'SET_BLOCK_GUIDE_A',
                 'SET_BLOCK_GUIDE_B'):
        result['set_' + name] = nested_node_signature(assembly.sets[name].nodes)
    result['materials'] = tuple(sorted(
        (str(name), tuple(tuple(float(value) for value in row)
                          for row in model.materials[name].elastic.table))
        for name in model.materials.keys()))
    result['sections'] = tuple(sorted(
        (str(name), model.sections[name].__class__.__name__,
         safe_attribute(model.sections[name], 'material'))
        for name in model.sections.keys()))
    result['steps'] = tuple(sorted(
        (str(name), model.steps[name].__class__.__name__,
         safe_attribute(model.steps[name], 'previous'),
         safe_attribute(model.steps[name], 'nlgeom'),
         safe_attribute(model.steps[name], 'initialInc'),
         safe_attribute(model.steps[name], 'minInc'),
         safe_attribute(model.steps[name], 'maxInc'),
         safe_attribute(model.steps[name], 'maxNumInc'))
        for name in model.steps.keys()))
    result['interactions'] = tuple(sorted(
        (str(name), model.interactions[name].__class__.__name__,
         safe_attribute(model.interactions[name], 'sliding'),
         region_name(getattr(model.interactions[name], 'main', None)),
         region_name(getattr(model.interactions[name], 'secondary', None)),
         safe_attribute(model.interactions[name], 'suppressed'))
        for name in model.interactions.keys()))
    result['interaction_properties'] = tuple(sorted(
        (str(name),
         compact(getattr(model.interactionProperties[name],
                         'normalBehavior', '')),
         compact(getattr(model.interactionProperties[name],
                         'tangentialBehavior', '')))
        for name in model.interactionProperties.keys()))
    result['boundary_conditions'] = tuple(sorted(
        (str(name), model.boundaryConditions[name].__class__.__name__,
         region_name(getattr(model.boundaryConditions[name], 'region', None)),
         safe_attribute(model.boundaryConditions[name], 'suppressed'))
        for name in model.boundaryConditions.keys()))
    result['loads_without_magnitude'] = tuple(sorted(
        (str(name), model.loads[name].__class__.__name__,
         region_name(getattr(model.loads[name], 'region', None)),
         safe_attribute(model.loads[name], 'distributionType'),
         safe_attribute(model.loads[name], 'suppressed'))
        for name in model.loads.keys()))
    result['output_keyword_semantics'] = tuple(
        block for block in keyword_semantics
        if block[0].upper().startswith(('*OUTPUT', '*NODE OUTPUT',
                                        '*ELEMENT OUTPUT', '*CONTACT OUTPUT')))
    result['jobs'] = tuple(sorted(
        (str(name), safe_attribute(mdb.jobs[name], 'model'),
         safe_attribute(mdb.jobs[name], 'type'))
        for name in mdb.jobs.keys()))
    return result


source = signatures(SOURCE)
variant = signatures(VARIANT)
keys = sorted(key for key in source.keys() if key != 'pressure')
lines = [
    'source_pressure=%s' % source['pressure'],
    'variant_pressure=%s' % variant['pressure'],
]
for key in keys:
    lines.append('%s_equal=%s count=%s' % (
        key, source[key] == variant[key], len(source[key])))
lines.append('all_geometry_mesh_regions_semantics_equal=%s' % all(
    source[key] == variant[key] for key in keys))
lines.append('only_intended_pressure_change=%s' % (
    source['pressure'] == 5.0 and variant['pressure'] == 2.5 and
    all(source[key] == variant[key] for key in keys)))

with open(RESULT, 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
for line in lines:
    print(line)
