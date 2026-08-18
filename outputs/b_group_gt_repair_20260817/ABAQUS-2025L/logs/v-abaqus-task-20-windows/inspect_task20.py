# -*- coding: utf-8 -*-
from abaqus import *
from odbAccess import openOdb


openMdb(pathName=r'C:\Users\user\Desktop\Job-Hole-A.cae')
model = mdb.models['Model-Hole-A']
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r u1=%r u2=%r u3=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'u1', '<missing>'), getattr(obj, 'u2', '<missing>'),
        getattr(obj, 'u3', '<missing>')))
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r cf1=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'cf1', '<missing>')))
model.keywordBlock.synchVersions(storeNodesAndElements=False)
for index, block in enumerate(model.keywordBlock.sieBlocks):
    upper = block.upper()
    if '*BOUNDARY' in upper or '*CLOAD' in upper:
        lines.append('KEYWORD[%d]=%r' % (index, block))
odb = openOdb(path=r'C:\Users\user\Desktop\Job-Hole-A.odb', readOnly=True)
step = odb.steps['Step-Tension-A']
lines.append('ODB frames=%d final_time=%r' % (len(step.frames), step.frames[-1].frameValue))
odb.close()
handle = open(r'C:\Users\user\Documents\task20_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK20_API_INSPECT_COMPLETE')
