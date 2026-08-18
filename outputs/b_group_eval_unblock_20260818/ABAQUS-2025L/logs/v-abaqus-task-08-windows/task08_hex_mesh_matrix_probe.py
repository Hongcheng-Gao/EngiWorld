# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from mesh import ElemType

import os
import traceback


desktop = r'C:\Users\user\Desktop'
source_cae = os.path.join(desktop, 'Job-Contact.cae')
result_path = os.path.join(desktop, 'task08_hex_mesh_matrix_probe.txt')
lines = ['software=Abaqus/CAE Learning Edition 2025']


def log(value):
    lines.append(str(value))


def spans(part):
    coords = [tuple(float(value) for value in node.coordinates) for node in part.nodes]
    return tuple(round(max(point[index] for point in coords) -
                       min(point[index] for point in coords), 6)
                 for index in range(3))


def identify_parts(model):
    found = {}
    for key in model.parts.keys():
        part = model.parts[key]
        dimensions = spans(part)
        if dimensions == (20.0, 20.0, 30.0):
            found['block'] = (key, part, 3.0)
        elif dimensions == (100.0, 100.0, 5.0):
            found['plate'] = (key, part, 5.0)
    return found


controls = [
    ('structured', {'elemShape': HEX, 'technique': STRUCTURED}),
    ('sweep_default', {'elemShape': HEX, 'technique': SWEEP}),
    ('sweep_advancing_front',
     {'elemShape': HEX, 'technique': SWEEP, 'algorithm': ADVANCING_FRONT}),
    ('sweep_medial_axis',
     {'elemShape': HEX, 'technique': SWEEP, 'algorithm': MEDIAL_AXIS}),
]

for control_name, control_args in controls:
    log('BEGIN control=%s' % control_name)
    try:
        openMdb(pathName=source_cae)
        model = max([mdb.models[key] for key in mdb.models.keys()],
                    key=lambda item: len(item.parts.keys()) + len(item.loads.keys()))
        parts = identify_parts(model)
        if sorted(parts.keys()) != ['block', 'plate']:
            raise RuntimeError('could not identify both rectangular-solid parts')

        total_nodes = 0
        total_elements = 0
        for role in ('block', 'plate'):
            key, part, seed = parts[role]
            try:
                part.deleteMesh()
            except Exception:
                pass
            part.seedPart(size=seed, deviationFactor=0.1, minSizeFactor=0.1)
            part.setElementType(
                regions=(part.cells,),
                elemTypes=(ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
            part.setMeshControls(regions=part.cells, **control_args)
            part.generateMesh()

            node_count = len(part.nodes)
            element_count = len(part.elements)
            total_nodes += node_count
            total_elements += element_count
            coords = [tuple(float(value) for value in node.coordinates)
                      for node in part.nodes]
            levels = tuple(len(set(round(point[index], 8) for point in coords))
                           for index in range(3))
            observed = {}
            for attribute_name in ('TECHNIQUE', 'ALGORITHM', 'ELEM_SHAPE'):
                try:
                    observed[attribute_name.lower()] = str(part.getMeshControl(
                        part.cells[0], globals()[attribute_name]))
                except Exception as exc:
                    observed[attribute_name.lower()] = '<%s:%s>' % (
                        exc.__class__.__name__, str(exc))
            log('part role=%s name=%s requested_seed=%s stored_seed=%s '
                'nodes=%s elements=%s coordinate_levels=%s controls=%s' % (
                    role, key, seed, part.getPartSeeds(SIZE), node_count,
                    element_count, str(levels), str(observed)))

        log('assembly control=%s nodes=%s elements=%s' % (
            control_name, total_nodes, total_elements))
        job_name = 'Probe-' + control_name.replace('_', '-')
        if job_name in mdb.jobs.keys():
            del mdb.jobs[job_name]
        job = mdb.Job(name=job_name, model=model.name, type=ANALYSIS,
                      multiprocessingMode=DEFAULT, numCpus=1, numDomains=1)
        try:
            job.submit(consistencyChecking=ON)
            job.waitForCompletion()
            log('submit control=%s status=%s' % (control_name, str(job.status)))
        except Exception as exc:
            log('submit control=%s exception=%s: %s' % (
                control_name, exc.__class__.__name__, str(exc)))
    except Exception as exc:
        log('control=%s inapplicable_or_failed=%s: %s' % (
            control_name, exc.__class__.__name__, str(exc)))
        log(traceback.format_exc())
    log('END control=%s' % control_name)

with open(result_path, 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
for line in lines:
    print(line)
