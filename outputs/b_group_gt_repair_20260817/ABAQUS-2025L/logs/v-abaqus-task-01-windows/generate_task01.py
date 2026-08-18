# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import mesh
import os
import math


desktop = r'C:\Users\user\Desktop'
job_name = 'Job-Plate'
model_name = 'Model-Plate'
cae_path = os.path.join(desktop, job_name + '.cae')

os.chdir(desktop)
for ext in ('.cae', '.odb', '.lck', '.com', '.dat', '.inp', '.log', '.msg', '.prt', '.sim', '.sta'):
    path = os.path.join(desktop, job_name + ext)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

Mdb()
if 'Model-1' in mdb.models.keys():
    mdb.models.changeKey(fromName='Model-1', toName=model_name)
model = mdb.models[model_name]

sketch = model.ConstrainedSketch(name='Plate-Profile', sheetSize=100.0)
sketch.ConstructionLine(point1=(0.0, -10.0), point2=(0.0, 10.0))
sketch.rectangle(point1=(0.0, 0.0), point2=(50.0, 1.0))
part = model.Part(name='Plate', dimensionality=AXISYMMETRIC, type=DEFORMABLE_BODY)
part.BaseShell(sketch=sketch)
del model.sketches['Plate-Profile']

steel = model.Material(name='Steel')
steel.Elastic(table=((210000.0, 0.3),))
model.HomogeneousSolidSection(name='Plate-Section', material='Steel', thickness=None)
part.SectionAssignment(region=part.Set(name='PLATE', faces=part.faces), sectionName='Plate-Section')

part.setMeshControls(regions=part.faces, elemShape=QUAD, technique=STRUCTURED)
elem_type = mesh.ElemType(elemCode=CAX4R, elemLibrary=STANDARD)
part.setElementType(regions=(part.faces,), elemTypes=(elem_type,))
part.seedPart(size=2.0, deviationFactor=0.1, minSizeFactor=0.1)
part.generateMesh()

tol = 1.0e-6
part.Set(name='AXIS', nodes=part.nodes.getByBoundingBox(xMin=-tol, xMax=tol,
                                                         yMin=-tol, yMax=1.0 + tol))
part.Set(name='OUTER', nodes=part.nodes.getByBoundingBox(xMin=50.0 - tol, xMax=50.0 + tol,
                                                          yMin=-tol, yMax=1.0 + tol))
part.Set(name='TOP', nodes=part.nodes.getByBoundingBox(xMin=-tol, xMax=50.0 + tol,
                                                        yMin=1.0 - tol, yMax=1.0 + tol))

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)
instance = assembly.Instance(name='Plate-1', part=part, dependent=ON)
assembly.Set(name='AXIS', nodes=instance.nodes.getByBoundingBox(xMin=-tol, xMax=tol,
                                                                 yMin=-tol, yMax=1.0 + tol))
assembly.Set(name='OUTER', nodes=instance.nodes.getByBoundingBox(xMin=50.0 - tol, xMax=50.0 + tol,
                                                                  yMin=-tol, yMax=1.0 + tol))
top_nodes = list(instance.nodes.getByBoundingBox(xMin=-tol, xMax=50.0 + tol,
                                                  yMin=1.0 - tol, yMax=1.0 + tol))
top_nodes.sort(key=lambda node: node.coordinates[0])
assembly.Set(name='TOP', nodes=instance.nodes.sequenceFromLabels(labels=tuple(node.label for node in top_nodes)))

model.DisplacementBC(name='BC-Axis', createStepName='Initial', region=assembly.sets['AXIS'],
                     u1=0.0, u2=UNSET, ur3=UNSET, amplitude=UNSET,
                     distributionType=UNIFORM, fieldName='', localCsys=None)
model.DisplacementBC(name='BC-Outer', createStepName='Initial', region=assembly.sets['OUTER'],
                     u1=0.0, u2=0.0, ur3=UNSET, amplitude=UNSET,
                     distributionType=UNIFORM, fieldName='', localCsys=None)

model.StaticStep(name='Step-Pressure', previous='Initial')
model.fieldOutputRequests['F-Output-1'].setValues(variables=('S', 'U', 'RF'))

pressure = 0.1
for index, node in enumerate(top_nodes):
    radius = float(node.coordinates[0])
    if index == 0:
        delta_r = 0.5 * (float(top_nodes[1].coordinates[0]) - radius)
    elif index == len(top_nodes) - 1:
        delta_r = 0.5 * (radius - float(top_nodes[index - 1].coordinates[0]))
    else:
        delta_r = 0.5 * (float(top_nodes[index + 1].coordinates[0]) -
                         float(top_nodes[index - 1].coordinates[0]))
    force = -pressure * 2.0 * math.pi * radius * delta_r
    if abs(force) < 1.0e-12:
        continue
    set_name = 'TOP-NODE-%02d' % index
    assembly.Set(name=set_name, nodes=instance.nodes.sequenceFromLabels(labels=(node.label,)))
    model.ConcentratedForce(name='Pressure-Node-%02d' % index,
                            createStepName='Step-Pressure',
                            region=assembly.sets[set_name], cf2=force)

mdb.saveAs(pathName=cae_path)
job = mdb.Job(name=job_name, model=model_name, type=ANALYSIS,
              explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE,
              description='Axisymmetric circular plate under equivalent nodal pressure loads',
              numCpus=1, numDomains=1)
job.submit(consistencyChecking=OFF)
job.waitForCompletion()
mdb.save()
print('TASK01_GENERATION_COMPLETE')
