# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
from mesh import ElemType

import os
import traceback


desktop = r'C:\Users\user\Desktop'
source_cae = os.path.join(desktop, 'Job-Contact.cae')
candidate_cae = os.path.join(desktop, 'Job-Contact-Fine.cae')
log_path = os.path.join(desktop, 'task08_fine_mesh_probe.txt')
lines = []


def log(value):
    lines.append(str(value))


try:
    openMdb(pathName=source_cae)
    model = mdb.models['Model-Contact']
    parts = {}
    for key in model.parts.keys():
        parts[str(key).upper()] = model.parts[key]

    specifications = [('BLOCK', 3.0), ('PLATE', 5.0)]
    total_nodes = 0
    total_elements = 0
    for name, size in specifications:
        part = parts[name]
        try:
            part.deleteMesh()
        except Exception:
            pass
        part.seedPart(size=size, deviationFactor=0.1, minSizeFactor=0.1)
        element_type = ElemType(elemCode=C3D8R, elemLibrary=STANDARD)
        part.setElementType(regions=(part.cells,), elemTypes=(element_type,))
        part.generateMesh()
        node_count = len(part.nodes)
        element_count = len(part.elements)
        total_nodes += node_count
        total_elements += element_count
        xs = sorted(set(round(float(node.coordinates[0]), 8) for node in part.nodes))
        ys = sorted(set(round(float(node.coordinates[1]), 8) for node in part.nodes))
        zs = sorted(set(round(float(node.coordinates[2]), 8) for node in part.nodes))
        log('%s seed=%s nodes=%s elements=%s levels=(%s,%s,%s)' %
            (name, str(part.getPartSeeds(SIZE)), str(node_count), str(element_count),
             str(len(xs)), str(len(ys)), str(len(zs))))

    log('assembly_instance_node_sum=%s element_sum=%s' %
        (str(total_nodes), str(total_elements)))
    mdb.saveAs(pathName=candidate_cae)

    if 'Job-Contact-Fine' in mdb.jobs.keys():
        del mdb.jobs['Job-Contact-Fine']
    job = mdb.Job(name='Job-Contact-Fine', model='Model-Contact',
                  type=ANALYSIS, multiprocessingMode=DEFAULT, numCpus=1, numDomains=1)
    job.submit(consistencyChecking=ON)
    job.waitForCompletion()
    log('job_status=%s' % str(job.status))
except Exception as exc:
    log('probe_exception=%s: %s' % (exc.__class__.__name__, str(exc)))
    log(traceback.format_exc())
finally:
    try:
        handle = open(log_path, 'w')
        handle.write('\n'.join(lines) + '\n')
        handle.close()
    except Exception:
        pass
    for line in lines:
        print(line)
