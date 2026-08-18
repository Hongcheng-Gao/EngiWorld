# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import SIZE


openMdb(pathName=r'C:\Users\user\Desktop\Job-Contact.cae')
model = mdb.models['Model-Contact']
lines = ['chosen_model=%r' % model.name]
for name in model.parts.keys():
    part = model.parts[name]
    coords = [node.coordinates for node in part.nodes]
    xs = [p[0] for p in coords]
    ys = [p[1] for p in coords]
    zs = [p[2] for p in coords]
    counts = {}
    for elem in part.elements:
        counts[elem.type] = counts.get(elem.type, 0) + 1
    lines.append('PART name=%r spans=%r seed=%r element_counts=%r' % (
        name, (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)),
        part.getPartSeeds(SIZE), counts))
step = model.steps['Step-1']
lines.append('STEP class=%s nlgeom=%r' % (step.__class__.__name__, getattr(step, 'nlgeom', '<missing>')))
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s' % (name, obj.__class__.__name__))
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r magnitude=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitude', '<missing>')))
for name in model.interactions.keys():
    lines.append('INTERACTION name=%r class=%s' % (name, model.interactions[name].__class__.__name__))
for name in model.interactionProperties.keys():
    obj = model.interactionProperties[name]
    nb = getattr(obj, 'normalBehavior', None)
    tb = getattr(obj, 'tangentialBehavior', None)
    lines.append('PROPERTY name=%r class=%s pressureOverclosure=%r formulation=%r' % (
        name, obj.__class__.__name__, getattr(nb, 'pressureOverclosure', '<missing>'),
        getattr(tb, 'formulation', '<missing>')))
handle = open(r'C:\Users\user\Documents\task08_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK08_API_INSPECT_COMPLETE')
