# -*- coding: utf-8 -*-
from abaqus import *


openMdb(pathName=r'C:\Users\user\Desktop\Job-Torsion-A.cae')
model = mdb.models['Model-Torsion-A']
lines = ['chosen_model=%r' % model.name]
for name in model.boundaryConditions.keys():
    obj = model.boundaryConditions[name]
    lines.append('BC name=%r class=%s' % (name, obj.__class__.__name__))
for name in model.loads.keys():
    obj = model.loads[name]
    lines.append('LOAD name=%r class=%s createStepName=%r cm1=%r cm2=%r cm3=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'createStepName', '<missing>'),
        getattr(obj, 'cm1', '<missing>'), getattr(obj, 'cm2', '<missing>'),
        getattr(obj, 'cm3', '<missing>')))
for name in model.constraints.keys():
    obj = model.constraints[name]
    lines.append('CONSTRAINT name=%r class=%s couplingType=%r' % (
        name, obj.__class__.__name__, getattr(obj, 'couplingType', '<missing>')))
handle = open(r'C:\Users\user\Documents\task07_api_inspect.txt', 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK07_API_INSPECT_COMPLETE')
