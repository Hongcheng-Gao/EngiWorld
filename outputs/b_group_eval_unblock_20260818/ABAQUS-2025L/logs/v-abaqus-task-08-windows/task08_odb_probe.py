# -*- coding: utf-8 -*-
from odbAccess import openOdb

import math
import os
import traceback


DESKTOP = r'C:\Users\user\Desktop'
ODB_PATH = os.path.join(DESKTOP, 'Job-Contact.odb')
RESULT_PATH = os.path.join(DESKTOP, 'task08_odb_probe.txt')
lines = []


def log(value):
    lines.append(str(value))


def scalar(value):
    try:
        return float(value.data)
    except Exception:
        data = value.data
        return math.sqrt(sum(float(component) ** 2 for component in data))


try:
    odb = openOdb(path=ODB_PATH, readOnly=True, readInternalSets=True)
    log('odb_members=' + str(getattr(odb, '__members__', [])))
    log('diagnostic_status=' + str(getattr(odb.diagnosticData, 'jobStatus', None)))
    log('job_data=' + str(odb.jobData))
    for key in odb.rootAssembly.instances.keys():
        instance = odb.rootAssembly.instances[key]
        coords = [tuple(float(component) for component in node.coordinates)
                  for node in instance.nodes]
        log('instance=%s nodes=%s elements=%s types=%s bbox=(%s,%s,%s,%s,%s,%s)' %
            (key, len(instance.nodes), len(instance.elements),
             str(sorted(set(str(element.type) for element in instance.elements))),
             min(point[0] for point in coords), max(point[0] for point in coords),
             min(point[1] for point in coords), max(point[1] for point in coords),
             min(point[2] for point in coords), max(point[2] for point in coords)))
    log('surfaces=' + str(list(odb.rootAssembly.surfaces.keys())))
    log('node_sets=' + str(list(odb.rootAssembly.nodeSets.keys())))
    log('element_sets=' + str(list(odb.rootAssembly.elementSets.keys())))
    for step_key in odb.steps.keys():
        step = odb.steps[step_key]
        log('step=%s procedure=%s nlgeom=%s timePeriod=%s frames=%s description=%s' %
            (step_key, str(step.procedure), str(step.nlgeom), str(step.timePeriod),
             len(step.frames), str(step.description)))
        frame = step.frames[-1]
        log('last_frame=%s field_keys=%s' %
            (str(frame.frameValue), str(list(frame.fieldOutputs.keys()))))
        for field_name in ('U', 'S', 'RF', 'CPRESS'):
            field_key = None
            for candidate in frame.fieldOutputs.keys():
                if str(candidate).strip().upper().startswith(field_name):
                    field_key = candidate
                    break
            if field_key is None:
                log('field=%s missing' % field_name)
                continue
            field = frame.fieldOutputs[field_key]
            values = list(field.values)
            observed = [scalar(value) for value in values]
            log('field=%s key=%s count=%s min=%s max=%s' %
                (field_name, field_key, len(values), min(observed), max(observed)))
            if field_name == 'S':
                mises = [float(value.mises) for value in values]
                log('stress_mises_min=%s max=%s' % (min(mises), max(mises)))
            if field_name == 'RF':
                sums = [0.0, 0.0, 0.0]
                for value in values:
                    for index in range(min(3, len(value.data))):
                        sums[index] += float(value.data[index])
                log('rf_component_sums=' + str(tuple(sums)))
    odb.close()
except Exception as exc:
    log('exception=%s: %s' % (exc.__class__.__name__, str(exc)))
    log(traceback.format_exc())

with open(RESULT_PATH, 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
for line in lines:
    print(line)
