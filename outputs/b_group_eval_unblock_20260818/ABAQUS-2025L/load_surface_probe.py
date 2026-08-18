# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *

import os
import traceback


desktop = r'C:\Users\user\Desktop'
cae_names = ['Job-FlangeHole.cae', 'Job-UDL.cae', 'Job-Contact.cae']
cae_path = None
for name in cae_names:
    candidate = os.path.join(desktop, name)
    if os.path.exists(candidate):
        cae_path = candidate
        break
output_path = os.path.join(desktop, 'load_surface_probe.txt')
lines = []


def log(value):
    lines.append(str(value))


def entity_summary(owner, attribute):
    try:
        entities = getattr(owner, attribute)
        values = []
        for entity in entities:
            item = {'repr': str(entity)}
            try:
                item['label'] = entity.label
            except Exception:
                pass
            try:
                item['coordinates'] = tuple(float(x) for x in entity.coordinates)
            except Exception:
                pass
            try:
                item['centroid'] = tuple(float(x) for x in entity.getCentroid())
            except Exception:
                pass
            try:
                item['node_labels'] = [node.label for node in entity.getNodes()]
            except Exception:
                pass
            values.append(item)
        log('%s count=%s values=%s' % (attribute, str(len(entities)), str(values)))
    except Exception as exc:
        log('%s error=%s' % (attribute, str(exc)))


try:
    if cae_path is None:
        raise RuntimeError('No staged CAE found')
    openMdb(pathName=cae_path)
    log('cae=' + cae_path)
    for model_name in mdb.models.keys():
        model = mdb.models[model_name]
        if len(model.parts.keys()) == 0:
            continue
        log('MODEL=' + str(model_name))
        model.keywordBlock.synchVersions(storeNodesAndElements=True)
        for index, raw in enumerate(model.keywordBlock.sieBlocks):
            text = str(raw)
            upper = text.upper()
            if any(token in upper for token in [
                    '*STEP', '*END STEP', '*DLOAD', '*DSLOAD', '*CLOAD', '*SURFACE',
                    '*ELSET', '*NSET', '*BOUNDARY']):
                log('KEYWORD[%s]=%r' % (str(index), text))

        for load_name in model.loads.keys():
            load = model.loads[load_name]
            log('LOAD name=%r class=%s repr=%s' %
                (load_name, load.__class__.__name__, str(load)))
            for attribute in ['region', 'createStepName', 'magnitude', 'traction',
                              'directionVector', 'localCsys', 'distributionType']:
                try:
                    log('LOAD %s=%r' % (attribute, getattr(load, attribute)))
                except Exception as exc:
                    log('LOAD %s error=%s' % (attribute, str(exc)))

        assembly = model.rootAssembly
        for repo_name in ['sets', 'surfaces', 'allSets', 'allSurfaces']:
            repo = getattr(assembly, repo_name)
            for region_name in repo.keys():
                region = repo[region_name]
                log('REGION repo=%s name=%r repr=%s' %
                    (repo_name, region_name, str(region)))
                for attribute in ['nodes', 'elements', 'edges', 'faces', 'side1Faces',
                                  'side2Faces', 'side1Edges', 'side2Edges', 'end1Edges',
                                  'end2Edges']:
                    entity_summary(region, attribute)
        try:
            os.chdir(desktop)
            job_name = list(mdb.jobs.keys())[0]
            mdb.jobs[job_name].writeInput(consistencyChecking=OFF)
            inp_path = os.path.join(desktop, str(job_name) + '.inp')
            inp_lines = open(inp_path, 'r').read().splitlines()
            for index, line in enumerate(inp_lines):
                if ('PICKEDSURF' in line.upper() or
                        line.upper().startswith('*SURFACE')):
                    start = max(0, index - 2)
                    end = min(len(inp_lines), index + 5)
                    log('INP[%s:%s]=%r' % (str(start), str(end), '\n'.join(inp_lines[start:end])))
        except Exception as exc:
            log('WRITE_INPUT_ERROR=' + str(exc))
except Exception as exc:
    log('EXCEPTION=%s: %s' % (exc.__class__.__name__, str(exc)))
    log(traceback.format_exc())
finally:
    handle = open(output_path, 'w')
    handle.write('\n'.join(lines) + '\n')
    handle.close()
