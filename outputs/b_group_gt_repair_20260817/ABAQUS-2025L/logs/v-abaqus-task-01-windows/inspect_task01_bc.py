# -*- coding: utf-8 -*-
from abaqus import *
import os


desktop = r'C:\Users\user\Desktop'
openMdb(pathName=os.path.join(desktop, 'Job-Plate.cae'))
model = mdb.models['Model-Plate']
lines = []
for name in model.boundaryConditions.keys():
    bc = model.boundaryConditions[name]
    lines.append('name=%r class=%s createStepName=%r u1=%r u2=%r ur3=%r' % (
        name,
        bc.__class__.__name__,
        getattr(bc, 'createStepName', '<missing>'),
        getattr(bc, 'u1', '<missing>'),
        getattr(bc, 'u2', '<missing>'),
        getattr(bc, 'ur3', '<missing>')))
    try:
        lines.append('initial_values=%r' % bc.getValuesInStep(stepName='Initial'))
    except Exception as exc:
        lines.append('initial_values_error=%r' % exc)

path = r'C:\Users\user\Documents\task01_bc_inspect.txt'
handle = open(path, 'w')
handle.write('\n'.join(lines) + '\n')
handle.close()
print('TASK01_BC_INSPECT_COMPLETE')
