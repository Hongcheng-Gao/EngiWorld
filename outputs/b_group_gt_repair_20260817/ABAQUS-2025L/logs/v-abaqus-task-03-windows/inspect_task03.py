# -*- coding: utf-8 -*-
from abaqus import *


openMdb(pathName=r'C:\Users\user\Desktop\Job-FlangeHole.cae')
model = None
best_score = -1
for model_key in mdb.models.keys():
    candidate = mdb.models[model_key]
    score = 0
    for part_key in candidate.parts.keys():
        part = candidate.parts[part_key]
        score += len(part.elements) * 2 + len(part.nodes)
    if score > best_score:
        best_score = score
        model = candidate
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r u1=%r u2=%r u3=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'u1', '<missing>'), getattr(obj, 'u2', '<missing>'),
        getattr(obj, 'u3', '<missing>')))
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r magnitude=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitude', '<missing>')))
handle = open(r'C:\Users\user\Documents\task03_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK03_API_INSPECT_COMPLETE')
