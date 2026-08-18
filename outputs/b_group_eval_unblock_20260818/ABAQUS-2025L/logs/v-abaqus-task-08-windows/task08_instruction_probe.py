# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *

import os


desktop = r'C:\Users\user\Desktop'
openMdb(pathName=os.path.join(desktop, 'Job-Contact.cae'))
model = mdb.models['Model-Contact']
lines = []


def attributes(prefix, value, names):
    for name in names:
        try:
            lines.append('%s.%s=%s' % (prefix, name, str(getattr(value, name))))
        except Exception as exc:
            lines.append('%s.%s=<%s>' % (prefix, name, exc.__class__.__name__))


step = model.steps['Step-Contact']
attributes('step', step, ('initialInc', 'minInc', 'maxInc', 'maxNumInc',
                           'nlgeom', 'previous'))

interaction = model.interactions['Block-on-Plate']
attributes('interaction', interaction,
           ('createStepName', 'sliding', 'main', 'secondary',
            'interactionProperty', 'suppressed'))

prop = model.interactionProperties['Frictionless-Hard']
attributes('property', prop, ('normalBehavior', 'tangentialBehavior'))
for behavior_name in ('normalBehavior', 'tangentialBehavior'):
    try:
        behavior = getattr(prop, behavior_name)
    except Exception:
        continue
    attributes('property.' + behavior_name, behavior,
               ('pressureOverclosure', 'allowSeparation', 'formulation'))

for part_name in ('Block', 'Plate'):
    part = model.parts[part_name]
    for attribute_name, attribute in (('TECHNIQUE', TECHNIQUE),
                                      ('ELEM_SHAPE', ELEM_SHAPE),
                                      ('ALGORITHM', ALGORITHM)):
        try:
            value = part.getMeshControl(part.cells[0], attribute)
            lines.append('%s.mesh_control.%s=%s' %
                         (part_name, attribute_name, str(value)))
        except Exception as exc:
            lines.append('%s.mesh_control.%s=<%s:%s>' %
                         (part_name, attribute_name,
                          exc.__class__.__name__, str(exc)))

model.keywordBlock.synchVersions(storeNodesAndElements=False)
step_name = 'Initial'
for raw in model.keywordBlock.sieBlocks:
    lines_raw = [line.strip() for line in str(raw).splitlines()
                 if line.strip() and not line.lstrip().startswith('**')]
    if not lines_raw:
        continue
    header = lines_raw[0].upper()
    if header.startswith('*STEP'):
        step_name = 'Step-Contact'
    if (header.startswith('*STEP') or header.startswith('*STATIC') or
            header.startswith('*CONTACT PAIR') or
            header.startswith('*SURFACE BEHAVIOR') or
            header.startswith('*FRICTION') or header.startswith('*END STEP')):
        lines.append('keyword_step=%s | %s' %
                     (step_name, ' | '.join(lines_raw)))
    if header.startswith('*END STEP'):
        step_name = 'Initial'

with open(os.path.join(desktop, 'task08_instruction_probe.txt'), 'w') as handle:
    handle.write('\n'.join(lines) + '\n')
for line in lines:
    print(line)
