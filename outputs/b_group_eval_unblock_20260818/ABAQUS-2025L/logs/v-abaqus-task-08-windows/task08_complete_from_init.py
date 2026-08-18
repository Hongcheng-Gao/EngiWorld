# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *
from mesh import ElemType

import hashlib
import os
import traceback


DESKTOP = r'C:\Users\user\Desktop'
SEED_CAE = os.path.join(DESKTOP, 'Contact-Seed.cae')
GT_CAE = os.path.join(DESKTOP, 'Job-Contact.cae')
LOG_PATH = os.path.join(DESKTOP, 'task08_complete_from_init.txt')
lines = ['software=Abaqus/CAE Learning Edition 2025']


def log(value):
    lines.append(str(value))


def sha256_file(path):
    digest = hashlib.sha256()
    handle = open(path, 'rb')
    try:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    finally:
        handle.close()
    return digest.hexdigest()


def bounds(nodes):
    coords = [tuple(float(value) for value in node.coordinates) for node in nodes]
    return (min(point[0] for point in coords), max(point[0] for point in coords),
            min(point[1] for point in coords), max(point[1] for point in coords),
            min(point[2] for point in coords), max(point[2] for point in coords))


try:
    log('seed_sha256_before_open=' + sha256_file(SEED_CAE))
    openMdb(pathName=SEED_CAE)
    log('gt_source_opened=' + SEED_CAE)
    model = mdb.models['Model-Contact']
    assembly = model.rootAssembly
    block = model.parts['Block']
    plate = model.parts['Plate']

    log('source_counts=analysis_steps:%s interactions:%s bcs:%s loads:%s jobs:%s '
        'block_mesh_nodes:%s plate_mesh_nodes:%s' %
        (len(model.steps.keys()) - 1, len(model.interactions.keys()),
         len(model.boundaryConditions.keys()), len(model.loads.keys()),
         len(mdb.jobs.keys()), len(block.nodes), len(plate.nodes)))

    model.StaticStep(name='Step-Contact', previous='Initial', nlgeom=ON,
                     initialInc=0.05, minInc=1.0e-8, maxInc=0.1,
                     maxNumInc=200)
    contact_property = model.ContactProperty('Frictionless-Hard')
    contact_property.NormalBehavior(pressureOverclosure=HARD,
                                    allowSeparation=ON,
                                    constraintEnforcementMethod=DEFAULT)
    contact_property.TangentialBehavior(formulation=FRICTIONLESS)
    model.SurfaceToSurfaceContactStd(
        name='Block-on-Plate', createStepName='Initial',
        main=assembly.surfaces['SURF_PLATE_TOP'],
        secondary=assembly.surfaces['SURF_BLOCK_BOTTOM'],
        sliding=FINITE, thickness=ON,
        interactionProperty='Frictionless-Hard',
        adjustMethod=NONE, initialClearance=OMIT)

    model.EncastreBC(name='BC-Plate-Bottom', createStepName='Initial',
                     region=assembly.sets['SET_PLATE_BOTTOM'])
    model.DisplacementBC(name='BC-Block-Guide-A', createStepName='Initial',
                         region=assembly.sets['SET_BLOCK_GUIDE_A'],
                         u1=0.0, u2=0.0, u3=UNSET,
                         ur1=UNSET, ur2=UNSET, ur3=UNSET)
    model.DisplacementBC(name='BC-Block-Guide-B', createStepName='Initial',
                         region=assembly.sets['SET_BLOCK_GUIDE_B'],
                         u1=UNSET, u2=0.0, u3=UNSET,
                         ur1=UNSET, ur2=UNSET, ur3=UNSET)
    model.Pressure(name='Pressure-Top', createStepName='Step-Contact',
                   region=assembly.surfaces['SURF_BLOCK_TOP'],
                   distributionType=UNIFORM, magnitude=5.0)

    element_type = ElemType(elemCode=C3D8R, elemLibrary=STANDARD,
                            secondOrderAccuracy=OFF,
                            kinematicSplit=AVERAGE_STRAIN,
                            hourglassControl=DEFAULT,
                            distortionControl=DEFAULT)
    for part, seed in ((block, 2.0), (plate, 3.0)):
        part.seedPart(size=seed, deviationFactor=0.1, minSizeFactor=0.1)
        part.setMeshControls(regions=part.cells, elemShape=HEX,
                             technique=STRUCTURED)
        part.setElementType(regions=(part.cells,), elemTypes=(element_type,))
        part.generateMesh()
    assembly.regenerate()

    model.FieldOutputRequest(name='F-Output-Contact',
                             createStepName='Step-Contact',
                             variables=('S', 'U', 'RF', 'CSTRESS'))
    log('block_mesh=seed:%s nodes:%s elements:%s bounds:%s' %
        (block.getPartSeeds(SIZE), len(block.nodes), len(block.elements),
         str(bounds(block.nodes))))
    log('plate_mesh=seed:%s nodes:%s elements:%s bounds:%s' %
        (plate.getPartSeeds(SIZE), len(plate.nodes), len(plate.elements),
         str(bounds(plate.nodes))))
    log('assembly_nodes=%s assembly_elements=%s' %
        (len(block.nodes) + len(plate.nodes),
         len(block.elements) + len(plate.elements)))

    os.chdir(DESKTOP)
    job = mdb.Job(name='Job-Contact', model='Model-Contact', type=ANALYSIS,
                  memory=90, memoryUnits=PERCENTAGE,
                  multiprocessingMode=DEFAULT, numCpus=1, numDomains=1)
    mdb.saveAs(pathName=GT_CAE)
    job.writeInput(consistencyChecking=ON)
    log('input_written=' + os.path.join(DESKTOP, 'Job-Contact.inp'))
    job.submit(consistencyChecking=ON)
    job.waitForCompletion()
    mdb.save()
    log('job_status_wrapper=' + str(job.status))
    log('gt_cae_sha256_after_solve_save=' + sha256_file(GT_CAE))
    log('gt_odb_sha256=' + sha256_file(os.path.join(DESKTOP,
                                                    'Job-Contact.odb')))
    mdb.close()
    log('gt_cae_sha256_after_close=' + sha256_file(GT_CAE))
    openMdb(pathName=GT_CAE)
    reopened = mdb.models['Model-Contact']
    log('reopen_counts=steps:%s interactions:%s bcs:%s loads:%s jobs:%s '
        'block_nodes:%s plate_nodes:%s' %
        (len(reopened.steps.keys()) - 1, len(reopened.interactions.keys()),
         len(reopened.boundaryConditions.keys()), len(reopened.loads.keys()),
         len(mdb.jobs.keys()), len(reopened.parts['Block'].nodes),
         len(reopened.parts['Plate'].nodes)))
    mdb.save()
    mdb.close()
    log('gt_cae_sha256_final_closed=' + sha256_file(GT_CAE))
except Exception as exc:
    log('exception=%s: %s' % (exc.__class__.__name__, str(exc)))
    log(traceback.format_exc())
finally:
    with open(LOG_PATH, 'w') as handle:
        handle.write('\n'.join(lines) + '\n')
    for line in lines:
        print(line)
