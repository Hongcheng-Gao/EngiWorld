# -*- coding: utf-8 -*-
from abaqus import *


openMdb(pathName=r'C:\Users\user\Desktop\Job-Tension.cae')
model = None
best_score = -1
for model_key in mdb.models.keys():
    candidate = mdb.models[model_key]
    score = 0
    for part_key in candidate.parts.keys():
        score += len(candidate.parts[part_key].elements) * 2 + len(candidate.parts[part_key].nodes)
    if score > best_score:
        best_score = score
        model = candidate
lines = ['chosen_model=%r bc_count=%d load_count=%d' % (
    model.name, len(model.boundaryConditions.keys()), len(model.loads.keys()))]
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r magnitude=%r traction=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitude', '<missing>'), getattr(obj, 'traction', '<missing>')))
handle = open(r'C:\Users\user\Documents\task04_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK04_API_INSPECT_COMPLETE')
