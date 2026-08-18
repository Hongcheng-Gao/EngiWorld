# -*- coding: utf-8 -*-
from abaqus import *


openMdb(pathName=r'C:\Users\user\Desktop\Job-UDL.cae')
model = mdb.models['Model-UDL']
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s createStepName=%r u1=%r u2=%r u3=%r ur2=%r ur3=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'u1', '<missing>'), getattr(obj, 'u2', '<missing>'),
        getattr(obj, 'u3', '<missing>'), getattr(obj, 'ur2', '<missing>'),
        getattr(obj, 'ur3', '<missing>')))
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r magnitude=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'magnitude', '<missing>')))
for name in model.constraints.keys():
    obj = model.constraints[name]
    lines.append('CONSTRAINT name=%r class=%s couplingType=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'couplingType', '<missing>')))
handle = open(r'C:\Users\user\Documents\task09_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK09_API_INSPECT_COMPLETE')
