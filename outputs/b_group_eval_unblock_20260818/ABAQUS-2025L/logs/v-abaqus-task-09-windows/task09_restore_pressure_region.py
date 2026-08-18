# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb

import os
import traceback


desktop = r'C:\Users\user\Desktop'
cae_path = os.path.join(desktop, 'Job-UDL.cae')
odb_path = os.path.join(desktop, 'Job-UDL.odb')
result_path = os.path.join(desktop, 'task09_restore_pressure_region.txt')
lines = ['software=Abaqus/CAE Learning Edition 2025']


def log(value):
    lines.append(str(value))


def close(a, b, tol=5.0e-3):
    return abs(float(a) - float(b)) <= tol


try:
    odb = openOdb(path=odb_path, readOnly=True)
    target_name = None
    try:
        for key in odb.rootAssembly.surfaces.keys():
            surface = odb.rootAssembly.surfaces[key]
            coords = []
            for node_array in surface.nodes:
                for node in node_array:
                    coords.append(tuple(float(value) for value in node.coordinates))
            if (len(coords) >= 4 and close(min(p[0] for p in coords), 0.0) and
                    close(max(p[0] for p in coords), 200.0) and
                    all(close(p[1], 10.0) for p in coords) and
                    close(min(p[2] for p in coords), 0.0) and
                    close(max(p[2] for p in coords), 10.0)):
                target_name = str(key)
                log('solved_odb_target=%s nodes=%s' % (target_name, len(coords)))
                break
    finally:
        odb.close()
    if not target_name:
        raise RuntimeError('solved ODB top surface not found by geometry')

    openMdb(pathName=cae_path)
    model = max([mdb.models[key] for key in mdb.models.keys()],
                key=lambda item: len(item.parts.keys()) + len(item.loads.keys()))
    assembly = model.rootAssembly
    instance = max([assembly.instances[key] for key in assembly.instances.keys()],
                   key=lambda item: len(item.nodes))
    coords = [tuple(float(value) for value in node.coordinates)
              for node in instance.nodes]
    x_min = min(p[0] for p in coords)
    x_max = max(p[0] for p in coords)
    y_max = max(p[1] for p in coords)
    z_min = min(p[2] for p in coords)
    z_max = max(p[2] for p in coords)
    top_face = instance.faces.findAt(
        (((x_min + x_max) / 2.0, y_max, (z_min + z_max) / 2.0),))

    if target_name in assembly.surfaces.keys():
        del assembly.surfaces[target_name]
    target_surface = assembly.Surface(name=target_name, side1Faces=(top_face,))

    old_load_names = list(model.loads.keys())
    for key in old_load_names:
        del model.loads[key]
    model.Pressure(name='UDL_PRESSURE', createStepName='Step-Load',
                   region=target_surface, distributionType=UNIFORM,
                   magnitude=0.05, amplitude=UNSET)
    mdb.saveAs(pathName=cae_path)

    model.keywordBlock.synchVersions(storeNodesAndElements=False)
    keyword = '\n'.join(str(block) for block in model.keywordBlock.sieBlocks)
    expected = '%s, P, 0.05' % target_name
    if expected.upper() not in keyword.upper():
        raise RuntimeError('restored Pressure keyword linkage not found')
    surface_coords = [tuple(float(value) for value in node.coordinates)
                      for node in assembly.surfaces[target_name].nodes]
    log('restored_cae_region=%s nodes=%s x=%s..%s y=%s..%s z=%s..%s' % (
        target_name, len(surface_coords),
        min(p[0] for p in surface_coords), max(p[0] for p in surface_coords),
        min(p[1] for p in surface_coords), max(p[1] for p in surface_coords),
        min(p[2] for p in surface_coords), max(p[2] for p in surface_coords)))
    log('restored_keyword=%s' % expected)
    log('old_load_names=%s new_load=UDL_PRESSURE' % str(old_load_names))
    log('saved_cae=%s' % cae_path)
except Exception as exc:
    log('restore_exception=%s: %s' % (exc.__class__.__name__, str(exc)))
    log(traceback.format_exc())
finally:
    with open(result_path, 'w') as handle:
        handle.write('\n'.join(lines) + '\n')
    for line in lines:
        print(line)
