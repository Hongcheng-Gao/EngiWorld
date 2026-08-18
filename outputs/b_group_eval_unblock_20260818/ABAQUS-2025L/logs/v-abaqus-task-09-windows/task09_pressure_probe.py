# -*- coding: utf-8 -*-
from abaqus import *
from odbAccess import openOdb

import os


desktop = r'C:\Users\user\Desktop'
openMdb(pathName=os.path.join(desktop, 'Job-UDL.cae'))
model = max([mdb.models[key] for key in mdb.models.keys()],
            key=lambda item: len(item.parts.keys()) + len(item.loads.keys()))
lines = ['model=%s' % model.name]


def bbox(nodes):
    coords = [tuple(float(value) for value in node.coordinates) for node in nodes]
    if not coords:
        return 'empty'
    return 'x=%s..%s y=%s..%s z=%s..%s n=%s' % (
        min(point[0] for point in coords), max(point[0] for point in coords),
        min(point[1] for point in coords), max(point[1] for point in coords),
        min(point[2] for point in coords), max(point[2] for point in coords),
        len(coords))


for key in model.loads.keys():
    load = model.loads[key]
    fields = ['load=%s' % key, 'class=%s' % load.__class__.__name__]
    for attr in ('createStepName', 'region', 'magnitude', 'distributionType'):
        try:
            fields.append('%s=%s' % (attr, str(getattr(load, attr))))
        except Exception as exc:
            fields.append('%s=<%s>' % (attr, exc.__class__.__name__))
    lines.append(' '.join(fields))
    for attr in ('__members__', '__methods__'):
        try:
            lines.append('load_%s=%s' % (attr, str(getattr(load, attr))))
        except Exception as exc:
            lines.append('load_%s=<%s>' % (attr, exc.__class__.__name__))

for attr in ('__members__', '__methods__'):
    try:
        lines.append('assembly_%s=%s' % (attr, str(getattr(model.rootAssembly, attr))))
    except Exception as exc:
        lines.append('assembly_%s=<%s>' % (attr, exc.__class__.__name__))

for repo_name in ('surfaces', 'allSurfaces', 'allInternalSurfaces'):
    repo = getattr(model.rootAssembly, repo_name)
    for key in repo.keys():
        surface = repo[key]
        try:
            lines.append('%s=%s %s' % (repo_name, key, bbox(surface.nodes)))
        except Exception as exc:
            lines.append('%s=%s nodes=<%s>' % (repo_name, key, exc.__class__.__name__))
        if key == '_PickedSurf12':
            for attr in ('__members__', 'instances', 'sides', 'nodes', 'edges',
                         'elements', 'faces', 'side1Faces', 'side2Faces',
                         'side1Elements', 'side2Elements'):
                try:
                    value = getattr(surface, attr)
                    lines.append('target_surface_%s=%s' % (attr, str(value)))
                    if attr != '__members__':
                        for index, face in enumerate(value):
                            try:
                                lines.append('target_%s_%s_pointOn=%s nodes=%s' % (
                                    attr, index, str(face.pointOn), bbox(face.getNodes())))
                            except Exception as exc:
                                lines.append('target_%s_%s=<%s>' % (
                                    attr, index, exc.__class__.__name__))
                except Exception as exc:
                    lines.append('target_surface_%s=<%s>' % (attr, exc.__class__.__name__))

for key in model.rootAssembly.instances.keys():
    instance = model.rootAssembly.instances[key]
    lines.append('instance=%s %s' % (key, bbox(instance.nodes)))

for repo_name in ('sets', 'allSets', 'allInternalSets'):
    repo = getattr(model.rootAssembly, repo_name)
    lines.append('cae_%s_names=%s' % (repo_name, str(list(repo.keys()))))

model.keywordBlock.synchVersions(storeNodesAndElements=True)
step_name = 'Initial'
for raw in model.keywordBlock.sieBlocks:
    content = str(raw)
    stripped = [line.strip() for line in content.splitlines()
                if line.strip() and not line.lstrip().startswith('**')]
    if not stripped:
        continue
    header = stripped[0].upper()
    if header.startswith('*STEP'):
        step_name = ''
        for field in stripped[0].split(',')[1:]:
            pair = field.split('=', 1)
            if len(pair) == 2 and pair[0].strip().upper() == 'NAME':
                step_name = pair[1].strip()
    elif header.startswith('*END STEP'):
        step_name = 'Initial'
    elif header.startswith('*DLOAD') or header.startswith('*DSLOAD'):
        lines.append('keyword_step=%s | %s' % (step_name, ' | '.join(stripped)))

for raw in model.keywordBlock.sieBlocks:
    content = str(raw)
    if '_PICKEDSURF12' in content.upper():
        lines.append('region_keyword=%s' % ' | '.join(
            line.strip() for line in content.splitlines() if line.strip()))

os.chdir(desktop)
for key in mdb.jobs.keys():
    job = mdb.jobs[key]
    try:
        job.writeInput(consistencyChecking=OFF)
        inp_path = os.path.join(desktop, key + '.inp')
        inp = open(inp_path, 'r').read().splitlines()
        for index, line in enumerate(inp):
            if '_PICKEDSURF12' in line.upper():
                begin = max(0, index - 4)
                end = min(len(inp), index + 5)
                lines.append('inp_region_context=%s' % ' | '.join(
                    item.strip() for item in inp[begin:end] if item.strip()))
    except Exception as exc:
        lines.append('write_input=%s:%s' % (exc.__class__.__name__, str(exc)))

for line in lines:
    print(line)

odb = openOdb(path=os.path.join(desktop, 'Job-UDL.odb'), readOnly=True,
              readInternalSets=True)
try:
    lines.append('odb_members=%s' % str(getattr(odb, '__members__', [])))
    for step_key in odb.steps.keys():
        step = odb.steps[step_key]
        lines.append('odb_step=%s members=%s' % (
            step_key, str(getattr(step, '__members__', []))))
        for attr in ('loadCases', 'historyRegions'):
            try:
                lines.append('odb_step_%s=%s' % (attr, str(getattr(step, attr))))
            except Exception as exc:
                lines.append('odb_step_%s=<%s>' % (attr, exc.__class__.__name__))
    for key in odb.rootAssembly.surfaces.keys():
        surface = odb.rootAssembly.surfaces[key]
        lines.append('odb_surface_members=%s members=%s' % (
            key, str(getattr(surface, '__members__', []))))
        lines.append('odb_surface_identity=%s instanceNames=%s isInternal=%s' % (
            key, str(getattr(surface, 'instanceNames', [])),
            str(getattr(surface, 'isInternal', None))))
        for attr in ('faces', 'sides'):
            try:
                lines.append('odb_surface_%s_%s=%s' % (
                    key, attr, str(getattr(surface, attr))))
            except Exception as exc:
                lines.append('odb_surface_%s_%s=<%s>' % (
                    key, attr, exc.__class__.__name__))
        coords = []
        try:
            for node_array in surface.nodes:
                for node in node_array:
                    coords.append(tuple(float(value) for value in node.coordinates))
        except Exception as exc:
            lines.append('odb_surface=%s nodes=<%s>' % (key, exc.__class__.__name__))
        if coords:
            element_labels = []
            try:
                for element_array in surface.elements:
                    for element in element_array:
                        element_labels.append(int(element.label))
            except Exception:
                pass
            lines.append('odb_surface=%s x=%s..%s y=%s..%s z=%s..%s n=%s' % (
                key, min(point[0] for point in coords), max(point[0] for point in coords),
                min(point[1] for point in coords), max(point[1] for point in coords),
                min(point[2] for point in coords), max(point[2] for point in coords),
                len(coords)))
            lines.append('odb_surface_elements=%s labels=%s' % (
                key, str(sorted(set(element_labels)))))
    lines.append('odb_element_set_names=%s' %
                 str(list(odb.rootAssembly.elementSets.keys())))
    for key in odb.rootAssembly.elementSets.keys():
        labels = []
        for element_array in odb.rootAssembly.elementSets[key].elements:
            for element in element_array:
                labels.append(int(element.label))
        lines.append('odb_element_set=%s members=%s instanceNames=%s isInternal=%s labels=%s' % (
            str(key), str(getattr(odb.rootAssembly.elementSets[key],
                                  '__members__', [])),
            str(getattr(odb.rootAssembly.elementSets[key], 'instanceNames', [])),
            str(getattr(odb.rootAssembly.elementSets[key], 'isInternal', None)),
            str(sorted(set(labels)))))
finally:
    odb.close()

with open(os.path.join(desktop, 'task09_pressure_probe.txt'), 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
