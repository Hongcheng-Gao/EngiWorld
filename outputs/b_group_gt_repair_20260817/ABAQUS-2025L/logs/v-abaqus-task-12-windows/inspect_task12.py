# -*- coding: utf-8 -*-
from abaqus import *


openMdb(pathName=r'C:\Users\user\Desktop\Job-Buckle-A.cae')
model = mdb.models['Model-Buckle-A']
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
handle = open(r'C:\Users\user\Documents\task12_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK12_API_INSPECT_COMPLETE')
