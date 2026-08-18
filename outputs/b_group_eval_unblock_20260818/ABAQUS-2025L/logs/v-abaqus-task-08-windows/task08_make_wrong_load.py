# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *

import os


desktop = r'C:\Users\user\Desktop'
source = os.path.join(desktop, 'Job-Contact-Source.cae')
target = os.path.join(desktop, 'Job-Contact-WrongLoad.cae')
result = os.path.join(desktop, 'task08_make_wrong_load.txt')


def mesh_counts(model):
    return 'Block:%s/%s Plate:%s/%s BLOCK-1:%s PLATE-1:%s' % (
        len(model.parts['Block'].nodes), len(model.parts['Block'].elements),
        len(model.parts['Plate'].nodes), len(model.parts['Plate'].elements),
        len(model.rootAssembly.instances['BLOCK-1'].nodes),
        len(model.rootAssembly.instances['PLATE-1'].nodes))


openMdb(pathName=source)
model = mdb.models['Model-Contact']
before = mesh_counts(model)
model.loads['Pressure-Top'].setValues(magnitude=2.5)
invalidated = mesh_counts(model)
# Refresh dependent instances before saveAs so their native mesh is serialized.
for part_name in ('Block', 'Plate'):
    part = model.parts[part_name]
    if len(part.nodes) == 0 or len(part.elements) == 0:
        part.generateMesh()
model.rootAssembly.regenerate()
regenerated = mesh_counts(model)
mdb.saveAs(pathName=target)
with open(result, 'w') as handle:
    handle.write('source=%s\n' % source)
    handle.write('mutation=Pressure-Top magnitude 5.0 -> 2.5\n')
    handle.write('mesh_before=%s\n' % before)
    handle.write('mesh_after_setValues=%s\n' % invalidated)
    handle.write('mesh_after_regenerate=%s\n' % regenerated)
    handle.write('target=%s\n' % target)
