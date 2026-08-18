# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *

import os


DESKTOP = r'C:\Users\user\Desktop'
SEED_CAE = os.path.join(DESKTOP, 'Contact-Seed.cae')
LOG_PATH = os.path.join(DESKTOP, 'task08_create_init.txt')
lines = ['software=Abaqus/CAE Learning Edition 2025']


def log(value):
    lines.append(str(value))


Mdb()
model = mdb.models['Model-1']
mdb.models.changeKey(fromName='Model-1', toName='Model-Contact')
model = mdb.models['Model-Contact']

sketch = model.ConstrainedSketch(name='Block-Profile', sheetSize=40.0)
sketch.rectangle(point1=(0.0, 0.0), point2=(10.0, 10.0))
block = model.Part(name='Block', dimensionality=THREE_D, type=DEFORMABLE_BODY)
block.BaseSolidExtrude(sketch=sketch, depth=12.0)
del model.sketches['Block-Profile']

sketch = model.ConstrainedSketch(name='Plate-Profile', sheetSize=60.0)
sketch.rectangle(point1=(0.0, 0.0), point2=(30.0, 30.0))
plate = model.Part(name='Plate', dimensionality=THREE_D, type=DEFORMABLE_BODY)
plate.BaseSolidExtrude(sketch=sketch, depth=4.0)
del model.sketches['Plate-Profile']

material = model.Material(name='Steel')
material.Elastic(table=((210000.0, 0.3),))
model.HomogeneousSolidSection(name='Steel-Solid', material='Steel', thickness=None)
block.Set(name='SET_BLOCK_ALL', cells=block.cells)
plate.Set(name='SET_PLATE_ALL', cells=plate.cells)
block.SectionAssignment(region=block.sets['SET_BLOCK_ALL'],
                        sectionName='Steel-Solid')
plate.SectionAssignment(region=plate.sets['SET_PLATE_ALL'],
                        sectionName='Steel-Solid')

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)
assembly.Instance(name='BLOCK-1', part=block, dependent=ON)
assembly.Instance(name='PLATE-1', part=plate, dependent=ON)
assembly.translate(instanceList=('BLOCK-1',), vector=(10.0, 10.0, 4.0))
assembly.regenerate()

block_instance = assembly.instances['BLOCK-1']
plate_instance = assembly.instances['PLATE-1']
assembly.Surface(name='SURF_BLOCK_TOP', side1Faces=
                 block_instance.faces.findAt(((15.0, 15.0, 16.0),)))
assembly.Surface(name='SURF_BLOCK_BOTTOM', side1Faces=
                 block_instance.faces.findAt(((15.0, 15.0, 4.0),)))
assembly.Surface(name='SURF_PLATE_TOP', side1Faces=
                 plate_instance.faces.findAt(((15.0, 15.0, 4.0),)))
assembly.Set(name='SET_PLATE_BOTTOM', faces=
             plate_instance.faces.findAt(((15.0, 15.0, 0.0),)))
assembly.Set(name='SET_BLOCK_GUIDE_A', vertices=
             block_instance.vertices.findAt(((10.0, 10.0, 4.0),)))
assembly.Set(name='SET_BLOCK_GUIDE_B', vertices=
             block_instance.vertices.findAt(((20.0, 10.0, 4.0),)))

mdb.saveAs(pathName=SEED_CAE)
log('seed_saved=' + SEED_CAE)
log('seed_model=Model-Contact')
log('seed_geometry=Block:10x10x12 Plate:30x30x4 block_translation:(10,10,4)')
log('seed_regions=SURF_BLOCK_TOP,SURF_BLOCK_BOTTOM,SURF_PLATE_TOP,'
    'SET_PLATE_BOTTOM,SET_BLOCK_GUIDE_A,SET_BLOCK_GUIDE_B')
log('seed_counts=analysis_steps:%s interactions:%s bcs:%s loads:%s jobs:%s '
    'block_mesh_nodes:%s plate_mesh_nodes:%s' %
    (len(model.steps.keys()) - 1, len(model.interactions.keys()),
     len(model.boundaryConditions.keys()), len(model.loads.keys()),
     len(mdb.jobs.keys()), len(block.nodes), len(plate.nodes)))

with open(LOG_PATH, 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
for line in lines:
    print(line)
