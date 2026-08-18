# -*- coding: utf-8 -*-
from abaqus import *
from odbAccess import openOdb


openMdb(pathName=r'C:\Users\user\Desktop\Job-Modal-A.cae')
model = mdb.models['Model-Modal-A']
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r u1=%r u2=%r u3=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'u1', '<missing>'), getattr(obj, 'u2', '<missing>'),
        getattr(obj, 'u3', '<missing>')))
model.keywordBlock.synchVersions(storeNodesAndElements=False)
for index, block in enumerate(model.keywordBlock.sieBlocks):
    if '*BOUNDARY' in block.upper():
        lines.append('KEYWORD[%d]=%r' % (index, block))
odb = openOdb(path=r'C:\Users\user\Desktop\Job-Modal-A.odb', readOnly=True)
step = odb.steps['Step-Modal-A']
lines.append('ODB frames=%d descriptions=%r' % (
    len(step.frames), [frame.description for frame in step.frames]))
odb.close()
handle = open(r'C:\Users\user\Documents\task13_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK13_API_INSPECT_COMPLETE')
