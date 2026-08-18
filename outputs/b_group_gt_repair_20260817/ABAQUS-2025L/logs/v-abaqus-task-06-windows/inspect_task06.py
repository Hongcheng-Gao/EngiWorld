# -*- coding: utf-8 -*-
from abaqus import *


openMdb(pathName=r'C:\Users\user\Desktop\Job-Thermal.cae')
model = mdb.models['Model-Thermal']
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r magnitude=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitude', '<missing>')))
handle = open(r'C:\Users\user\Documents\task06_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK06_API_INSPECT_COMPLETE')
