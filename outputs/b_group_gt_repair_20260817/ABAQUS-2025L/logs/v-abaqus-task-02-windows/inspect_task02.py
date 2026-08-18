# -*- coding: utf-8 -*-
from abaqus import *
import os


openMdb(pathName=r'C:\Users\user\Desktop\Job-Cylinder.cae')
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
lines = []
lines.append('chosen_model=%r' % model.name)
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r u1=%r u2=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'u1', '<missing>'), getattr(obj, 'u2', '<missing>')))
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r cf1=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'cf1', '<missing>')))
path = r'C:\Users\user\Documents\task02_api_inspect.txt'
handle = open(path, 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK02_API_INSPECT_COMPLETE')
