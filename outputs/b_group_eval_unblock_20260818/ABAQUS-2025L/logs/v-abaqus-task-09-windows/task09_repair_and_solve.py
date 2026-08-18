# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import os
import traceback


desktop = r'C:\Users\user\Desktop'
source_path = os.path.join(desktop, 'Job-UDL.cae')
candidate_path = os.path.join(desktop, 'Job-UDL-Repaired.cae')
result_path = os.path.join(desktop, 'task09_repair_and_solve.txt')
lines = ['software=Abaqus/CAE Learning Edition 2025']


def log(value):
    lines.append(str(value))


def close(a, b, tol=1.0e-5):
    return abs(float(a) - float(b)) <= tol


try:
    os.chdir(desktop)
    openMdb(pathName=source_path)
    model = max([mdb.models[key] for key in mdb.models.keys()],
                key=lambda item: len(item.parts.keys()) + len(item.loads.keys()))
    assembly = model.rootAssembly
    instance = max([assembly.instances[key] for key in assembly.instances.keys()],
                   key=lambda item: len(item.nodes))
    coords = [tuple(float(value) for value in node.coordinates)
              for node in instance.nodes]
    x_min = min(point[0] for point in coords)
    x_max = max(point[0] for point in coords)
    y_min = min(point[1] for point in coords)
    y_max = max(point[1] for point in coords)
    z_min = min(point[2] for point in coords)
    z_max = max(point[2] for point in coords)
    mid_x = (x_min + x_max) / 2.0
    mid_y = (y_min + y_max) / 2.0
    mid_z = (z_min + z_max) / 2.0
    log('instance=%s bbox=x=%s..%s y=%s..%s z=%s..%s' % (
        instance.name, x_min, x_max, y_min, y_max, z_min, z_max))

    left_face = instance.faces.findAt(((x_min, mid_y, mid_z),))
    right_face = instance.faces.findAt(((x_max, mid_y, mid_z),))
    top_face = instance.faces.findAt(((mid_x, y_max, mid_z),))

    for name in ('UDL_END_LEFT', 'UDL_END_RIGHT', 'UDL_TOP'):
        if name in assembly.surfaces.keys():
            del assembly.surfaces[name]
    left_surface = assembly.Surface(name='UDL_END_LEFT', side1Faces=(left_face,))
    right_surface = assembly.Surface(name='UDL_END_RIGHT', side1Faces=(right_face,))
    top_surface = assembly.Surface(name='UDL_TOP', side1Faces=(top_face,))

    left_rp = None
    right_rp = None
    for key in assembly.referencePoints.keys():
        rp = assembly.referencePoints[key]
        point = None
        try:
            point = tuple(float(value) for value in assembly.getCoordinates(rp))
        except Exception:
            pass
        for attr in ('pointOn', 'point', 'coordinates'):
            if point is not None:
                break
            try:
                point = tuple(float(value) for value in getattr(rp, attr))
                break
            except Exception:
                pass
        if point is None:
            raise RuntimeError('cannot read reference point %s: members=%s' % (
                str(key), str(getattr(rp, '__members__', []))))
        if close(point[0], x_min):
            left_rp = rp
        elif close(point[0], x_max):
            right_rp = rp
        log('reference_point key=%s point=%s' % (str(key), str(point)))
    if left_rp is None or right_rp is None:
        raise RuntimeError('could not identify both end reference points')

    for name in ('UDL_RP_LEFT', 'UDL_RP_RIGHT'):
        if name in assembly.sets.keys():
            del assembly.sets[name]
    left_set = assembly.Set(name='UDL_RP_LEFT', referencePoints=(left_rp,))
    right_set = assembly.Set(name='UDL_RP_RIGHT', referencePoints=(right_rp,))

    for key in list(model.constraints.keys()):
        del model.constraints[key]
    model.Coupling(name='UDL_COUPLING_LEFT', controlPoint=left_set,
                   surface=left_surface, influenceRadius=WHOLE_SURFACE,
                   couplingType=KINEMATIC, localCsys=None,
                   u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)
    model.Coupling(name='UDL_COUPLING_RIGHT', controlPoint=right_set,
                   surface=right_surface, influenceRadius=WHOLE_SURFACE,
                   couplingType=KINEMATIC, localCsys=None,
                   u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)

    for key in list(model.boundaryConditions.keys()):
        del model.boundaryConditions[key]
    model.DisplacementBC(name='UDL_PIN', createStepName='Initial', region=left_set,
                         u1=0.0, u2=0.0, u3=0.0, ur1=UNSET, ur2=0.0, ur3=0.0)
    model.DisplacementBC(name='UDL_ROLLER', createStepName='Initial', region=right_set,
                         u1=UNSET, u2=0.0, u3=0.0, ur1=UNSET, ur2=0.0, ur3=0.0)

    for key in list(model.loads.keys()):
        del model.loads[key]
    model.Pressure(name='UDL_PRESSURE', createStepName='Step-Load',
                   region=top_surface, distributionType=UNIFORM,
                   magnitude=0.05, amplitude=UNSET)
    stabilization_fraction = 1.0e-2
    model.steps['Step-Load'].setValues(
        nlgeom=OFF, initialInc=0.01, minInc=1.0e-8, maxInc=0.1,
        maxNumInc=1000, stabilizationMethod=DISSIPATED_ENERGY_FRACTION,
        stabilizationMagnitude=stabilization_fraction,
        adaptiveDampingRatio=0.05)
    log('stabilization_fraction=%s initialInc=0.01 minInc=1e-8 maxInc=0.1 '
        'maxNumInc=1000' % stabilization_fraction)

    for key in list(mdb.jobs.keys()):
        del mdb.jobs[key]
    mdb.Job(name='Job-UDL', model=model.name, type=ANALYSIS,
            multiprocessingMode=DEFAULT, numCpus=1, numDomains=1)
    mdb.saveAs(pathName=candidate_path)
    job = mdb.jobs['Job-UDL']
    job.submit(consistencyChecking=ON)
    job.waitForCompletion()
    log('job_status=%s' % str(job.status))
    if str(job.status).upper() != 'COMPLETED':
        raise RuntimeError('Job-UDL did not complete')

    odb_path = os.path.join(desktop, 'Job-UDL.odb')
    odb = openOdb(path=odb_path, readOnly=True)
    try:
        log('odb_steps=%s' % str(list(odb.steps.keys())))
        log('odb_surfaces=%s' % str(list(odb.rootAssembly.surfaces.keys())))
        if 'UDL_TOP' not in [str(key).upper() for key in odb.rootAssembly.surfaces.keys()]:
            raise RuntimeError('Solved ODB does not retain UDL_TOP surface')
        step = odb.steps['Step-Load']
        log('odb_frames=%s last_frame=%s' % (
            len(step.frames), step.frames[-1].frameValue))
        history = step.historyRegions['Assembly ASSEMBLY'].historyOutputs
        allsd = dict(history['ALLSD'].data)
        allie = dict(history['ALLIE'].data)
        ratios = [abs(float(allsd[time])) / abs(float(value))
                  for time, value in allie.items()
                  if time in allsd and abs(float(value)) > 1.0e-12]
        if not ratios:
            raise RuntimeError('cannot calculate stabilization energy ratio')
        log('max_ALLSD_over_ALLIE=%s' % max(ratios))
    finally:
        odb.close()
    mdb.saveAs(pathName=source_path)
    log('saved_cae=%s' % source_path)
    log('saved_odb=%s' % odb_path)
except Exception as exc:
    log('repair_exception=%s: %s' % (exc.__class__.__name__, str(exc)))
    log(traceback.format_exc())
finally:
    with open(result_path, 'w') as handle:
        handle.write('\n'.join(lines) + '\n')
    for line in lines:
        print(line)
