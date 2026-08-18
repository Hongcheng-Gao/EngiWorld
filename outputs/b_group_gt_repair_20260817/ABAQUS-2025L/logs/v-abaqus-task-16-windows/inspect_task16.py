# -*- coding: utf-8 -*-
from abaqus import *
from odbAccess import openOdb


openMdb(pathName=r'C:\Users\user\Desktop\Job-TransientHeat-A.cae')
model = mdb.models['Model-TransientHeat-A']
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r magnitude=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitude', '<missing>')))
for name in model.predefinedFields.keys():
    obj = model.predefinedFields[name]
    lines.append('FIELD name=%r class=%s createStepName=%r magnitudes=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitudes', '<missing>')))
model.keywordBlock.synchVersions(storeNodesAndElements=False)
for index, block in enumerate(model.keywordBlock.sieBlocks):
    upper = block.upper()
    if '*BOUNDARY' in upper or '*INITIAL CONDITIONS' in upper:
        lines.append('KEYWORD[%d]=%r' % (index, block))
odb = openOdb(path=r'C:\Users\user\Desktop\Job-TransientHeat-A.odb', readOnly=True)
step = odb.steps['Step-Heat-A']
lines.append('ODB frames=%d final_time=%r' % (len(step.frames), step.frames[-1].frameValue))
odb.close()
handle = open(r'C:\Users\user\Documents\task16_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK16_API_INSPECT_COMPLETE')
