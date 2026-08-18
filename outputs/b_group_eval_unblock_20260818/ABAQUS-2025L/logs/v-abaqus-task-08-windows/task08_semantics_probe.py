# -*- coding: utf-8 -*-
from abaqus import *
from odbAccess import openOdb

import os


desktop = r'C:\Users\user\Desktop'
openMdb(pathName=os.path.join(desktop, 'Job-Contact.cae'))
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

for key in model.boundaryConditions.keys():
    bc = model.boundaryConditions[key]
    fields = ['bc=%s' % key, 'class=%s' % bc.__class__.__name__]
    for attr in ('createStepName', 'region'):
        try:
            fields.append('%s=%s' % (attr, str(getattr(bc, attr))))
        except Exception as exc:
            fields.append('%s=<%s>' % (attr, exc.__class__.__name__))
    lines.append(' '.join(fields))

for repo_name in ('surfaces', 'allSurfaces', 'allInternalSurfaces'):
    repo = getattr(model.rootAssembly, repo_name)
    for key in repo.keys():
        surface = repo[key]
        try:
            lines.append('%s=%s %s' % (repo_name, key, bbox(surface.nodes)))
        except Exception as exc:
            lines.append('%s=%s nodes=<%s>' % (repo_name, key, exc.__class__.__name__))

for key in model.rootAssembly.instances.keys():
    instance = model.rootAssembly.instances[key]
    lines.append('instance=%s %s' % (key, bbox(instance.nodes)))

for key in model.interactions.keys():
    item = model.interactions[key]
    fields = ['interaction=%s' % key, 'class=%s' % item.__class__.__name__]
    for attr in ('createStepName', 'master', 'slave', 'interactionProperty'):
        try:
            fields.append('%s=%s' % (attr, str(getattr(item, attr))))
        except Exception as exc:
            fields.append('%s=<%s>' % (attr, exc.__class__.__name__))
    lines.append(' '.join(fields))

for key in model.rootAssembly.features.keys():
    item = model.rootAssembly.features[key]
    fields = ['assembly_feature=%s' % key, 'class=%s' % item.__class__.__name__]
    for attr in ('master', 'slave'):
        try:
            fields.append('%s=%s' % (attr, str(getattr(item, attr))))
        except Exception as exc:
            fields.append('%s=<%s>' % (attr, exc.__class__.__name__))
    lines.append(' '.join(fields))

model.keywordBlock.synchVersions(storeNodesAndElements=False)
step_name = 'Initial'
for raw in model.keywordBlock.sieBlocks:
    stripped = [line.strip() for line in str(raw).splitlines()
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
    elif (header.startswith('*DLOAD') or header.startswith('*DSLOAD') or
          header.startswith('*BOUNDARY') or header.startswith('*CONTACT')):
        lines.append('keyword_step=%s | %s' % (step_name, ' | '.join(stripped)))

odb = openOdb(path=os.path.join(desktop, 'Job-Contact.odb'), readOnly=True)
try:
    for key in odb.rootAssembly.surfaces.keys():
        surface = odb.rootAssembly.surfaces[key]
        coords = []
        try:
            for node_array in surface.nodes:
                for node in node_array:
                    coords.append(tuple(float(value) for value in node.coordinates))
        except Exception as exc:
            lines.append('odb_surface=%s nodes=<%s>' % (key, exc.__class__.__name__))
        if coords:
            lines.append('odb_surface=%s x=%s..%s y=%s..%s z=%s..%s n=%s' % (
                key, min(point[0] for point in coords), max(point[0] for point in coords),
                min(point[1] for point in coords), max(point[1] for point in coords),
                min(point[2] for point in coords), max(point[2] for point in coords),
                len(coords)))
finally:
    odb.close()

for line in lines:
    print(line)

with open(os.path.join(desktop, 'task08_semantics_probe.txt'), 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
