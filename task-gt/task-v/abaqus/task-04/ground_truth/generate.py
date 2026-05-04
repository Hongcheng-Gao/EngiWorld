# -*- coding: utf-8 -*-
# Job-Tension.py
# Abaqus/CAE script for a 3D solid tensile analysis of a 100 mm x 10 mm x 10 mm bar.
#
# Run command:
#     abaqus cae script=Job-Tension.py
#
# This script follows the GUI instruction:
# - 3D deformable solid bar, length along global X
# - Steel: E = 210000 MPa, nu = 0.3
# - Solid homogeneous section
# - Static, General step named Step-Load
# - X=0 face fixed
# - X=100 face loaded by general surface traction in global +X direction
# - Global seed size = 5 mm
# - Element type = C3D8R
# - Job name = Job-Tension

from abaqus import *
from abaqusConstants import *
from caeModules import *
from driverUtils import executeOnCaeStartup
from odbAccess import openOdb
import mesh
import os
import math
import shutil

executeOnCaeStartup()

# ============================================================
# 0. Parameters
# ============================================================
MODEL_NAME = 'Model-Tension'
PART_NAME = 'Bar'
JOB_NAME = 'Job-Tension'

LENGTH_X = 100.0      # mm
WIDTH_Y = 10.0        # mm
WIDTH_Z = 10.0        # mm

E = 210000.0          # MPa = N/mm^2
NU = 0.3

TRACTION = 10.0       # MPa = N/mm^2, over 10 mm x 10 mm face -> total 1000 N
GLOBAL_SEED = 5.0     # mm

# Use the path in the instruction if it exists.
# If not, fall back to Administrator Desktop, then the current user's Desktop.
requested_desktop = r'C:\Users\User\Desktop'
admin_desktop = r'C:\Users\Administrator\Desktop'
current_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')

if os.path.isdir(requested_desktop):
    SAVE_DIR = requested_desktop
elif os.path.isdir(admin_desktop):
    SAVE_DIR = admin_desktop
else:
    SAVE_DIR = current_desktop

if not os.path.isdir(SAVE_DIR):
    os.makedirs(SAVE_DIR)

os.chdir(SAVE_DIR)

CAE_PATH = os.path.join(SAVE_DIR, JOB_NAME + '.cae')
ODB_PATH = os.path.join(SAVE_DIR, JOB_NAME + '.odb')
QUERY_PATH = os.path.join(SAVE_DIR, JOB_NAME + '_U1_query.txt')

# ============================================================
# 1. Clean old model/job
# ============================================================
if MODEL_NAME in mdb.models.keys():
    del mdb.models[MODEL_NAME]

if JOB_NAME in mdb.jobs.keys():
    del mdb.jobs[JOB_NAME]

model = mdb.Model(name=MODEL_NAME)

# ============================================================
# 2. Part: 3D deformable solid bar
# ============================================================
# Abaqus base extrusion normally extrudes the sketch along the local Z direction.
# Therefore, the part is first created as a 10 x 10 cross-section extruded 100 mm
# in local Z, then the assembly instance is rotated so that the final bar length
# is aligned with the global X-axis.
sketch = model.ConstrainedSketch(name='bar_profile', sheetSize=200.0)
sketch.rectangle(point1=(0.0, 0.0), point2=(WIDTH_Z, WIDTH_Y))

part = model.Part(name=PART_NAME, dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=LENGTH_X)
del sketch

part.Set(name='All-Cells', cells=part.cells)

# ============================================================
# 3. Property: Steel and solid homogeneous section
# ============================================================
material = model.Material(name='Steel')
material.Elastic(table=((E, NU),))

model.HomogeneousSolidSection(
    name='Solid-Section-Steel',
    material='Steel',
    thickness=None
)

part.SectionAssignment(
    region=part.sets['All-Cells'],
    sectionName='Solid-Section-Steel'
)

# ============================================================
# 4. Mesh: global seed = 5 mm; element type = C3D8R
# ============================================================
part.seedPart(size=GLOBAL_SEED, deviationFactor=0.1, minSizeFactor=0.1)

# Structured hex mesh is used to obtain the intended C3D8R mesh.
part.setMeshControls(regions=part.cells, elemShape=HEX, technique=STRUCTURED)

elem_type = mesh.ElemType(
    elemCode=C3D8R,
    elemLibrary=STANDARD,
    kinematicSplit=AVERAGE_STRAIN,
    secondOrderAccuracy=OFF,
    hourglassControl=DEFAULT,
    distortionControl=DEFAULT
)

part.setElementType(regions=(part.cells,), elemTypes=(elem_type,))
part.generateMesh()

# ============================================================
# 5. Assembly: create one dependent instance and align it with global X
# ============================================================
assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)

instance = assembly.Instance(name=PART_NAME + '-1', part=part, dependent=ON)

# Local part before rotation:
#   local x = 0..10
#   local y = 0..10
#   local z = 0..100
#
# Rotate +90 deg about global Y:
#   global X = local Z
#   global Y = local Y
#   global Z = -local X
#
# Then translate +10 in global Z so the final geometry is:
#   X = 0..100, Y = 0..10, Z = 0..10
assembly.rotate(
    instanceList=(PART_NAME + '-1',),
    axisPoint=(0.0, 0.0, 0.0),
    axisDirection=(0.0, 1.0, 0.0),
    angle=90.0
)
assembly.translate(
    instanceList=(PART_NAME + '-1',),
    vector=(0.0, 0.0, WIDTH_Z)
)
assembly.regenerate()

# Find the two end faces in global assembly coordinates.
fixed_face = instance.faces.findAt(((0.0, WIDTH_Y / 2.0, WIDTH_Z / 2.0),))
loaded_face = instance.faces.findAt(((LENGTH_X, WIDTH_Y / 2.0, WIDTH_Z / 2.0),))

assembly.Set(name='Fixed-Face-X0', faces=(fixed_face,))
assembly.Surface(name='Traction-Face-X100', side1Faces=(loaded_face,))

# ============================================================
# 6. Step
# ============================================================
model.StaticStep(
    name='Step-Load',
    previous='Initial',
    nlgeom=OFF
)

# ============================================================
# 7. Boundary condition and load
# ============================================================
model.EncastreBC(
    name='BC-Fixed-X0',
    createStepName='Initial',
    region=assembly.sets['Fixed-Face-X0']
)

# Use general surface traction rather than Pressure, because pressure is normal to
# the face and sign conventions can be ambiguous. General traction directly defines
# a tensile load in the global +X direction.
traction_region = assembly.surfaces['Traction-Face-X100']

try:
    model.SurfaceTraction(
        name='Traction-PlusX',
        createStepName='Step-Load',
        region=traction_region,
        magnitude=TRACTION,
        directionVector=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        distributionType=UNIFORM,
        field='',
        localCsys=None,
        traction=GENERAL,
        follower=OFF,
        resultant=OFF
    )
except TypeError:
    # Compatibility fallback for Abaqus versions whose SurfaceTraction signature
    # does not expose the resultant argument.
    model.SurfaceTraction(
        name='Traction-PlusX',
        createStepName='Step-Load',
        region=traction_region,
        magnitude=TRACTION,
        directionVector=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
        distributionType=UNIFORM,
        field='',
        localCsys=None,
        traction=GENERAL,
        follower=OFF
    )

# ============================================================
# 8. Job
# ============================================================
mdb.Job(
    name=JOB_NAME,
    model=MODEL_NAME,
    description='3D solid tensile analysis of a 100 mm x 10 mm x 10 mm steel bar',
    type=ANALYSIS,
    atTime=None,
    waitMinutes=0,
    waitHours=0,
    queue=None,
    memory=90,
    memoryUnits=PERCENTAGE,
    getMemoryFromAnalysis=True,
    explicitPrecision=SINGLE,
    nodalOutputPrecision=SINGLE,
    echoPrint=OFF,
    modelPrint=OFF,
    contactPrint=OFF,
    historyPrint=OFF
)

print('>>> Submitting job: ' + JOB_NAME)
mdb.jobs[JOB_NAME].submit()
mdb.jobs[JOB_NAME].waitForCompletion()
print('>>> Job completed.')

# ============================================================
# 9. Save CAE database
# ============================================================
mdb.saveAs(pathName=CAE_PATH)
print('>>> CAE saved to: ' + CAE_PATH)
print('>>> ODB generated at: ' + ODB_PATH)

# ============================================================
# 10. Visualization: open ODB, display Mises stress contour
# ============================================================
try:
    odb_for_view = session.openOdb(name=ODB_PATH)
    vp_name = session.currentViewportName
    viewport = session.viewports[vp_name]
    viewport.setValues(displayedObject=odb_for_view)

    viewport.odbDisplay.setPrimaryVariable(
        variableLabel='S',
        outputPosition=INTEGRATION_POINT,
        refinement=(INVARIANT, 'Mises')
    )
    viewport.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
    print('>>> Mises stress contour displayed in the current viewport.')
except Exception as e:
    print('>>> Warning: ODB visualization step was skipped: ' + str(e))

# ============================================================
# 11. Query U1 at the center of the free end face
#     Target point in final global coordinates:
#       X=100, Y=5, Z=5
# ============================================================
def find_main_instance(odb_obj):
    best_name = None
    best_score = -1
    for name, inst_obj in odb_obj.rootAssembly.instances.items():
        score = len(inst_obj.nodes) + 2 * len(inst_obj.elements)
        if score > best_score:
            best_score = score
            best_name = name
    return best_name, odb_obj.rootAssembly.instances[best_name]


def nearest_node_label(inst_obj, targets):
    best_label = None
    best_dist = None
    best_coord = None
    best_target = None

    for node in inst_obj.nodes:
        x, y, z = node.coordinates
        for target in targets:
            d = math.sqrt(
                (float(x) - target[0]) ** 2 +
                (float(y) - target[1]) ** 2 +
                (float(z) - target[2]) ** 2
            )
            if best_dist is None or d < best_dist:
                best_dist = d
                best_label = node.label
                best_coord = (float(x), float(y), float(z))
                best_target = target

    return best_label, best_dist, best_coord, best_target


try:
    odb = openOdb(path=ODB_PATH, readOnly=True)
    inst_name, odb_inst = find_main_instance(odb)

    # Depending on Abaqus version and how instance transformations are stored,
    # ODB node coordinates may appear either in assembly/global coordinates
    # or in part/local coordinates. Try both:
    #   global target after rotation: (100, 5, 5)
    #   local part target before rotation: (5, 5, 100)
    target_global = (LENGTH_X, WIDTH_Y / 2.0, WIDTH_Z / 2.0)
    target_local = (WIDTH_Z / 2.0, WIDTH_Y / 2.0, LENGTH_X)

    node_label, distance, node_coord, matched_target = nearest_node_label(
        odb_inst,
        targets=(target_global, target_local)
    )

    last_frame = odb.steps['Step-Load'].frames[-1]
    u_subset = last_frame.fieldOutputs['U'].getSubset(region=odb_inst)

    u1_value = None
    u_data = None
    for value in u_subset.values:
        if value.nodeLabel == node_label:
            u_data = value.data
            u1_value = float(value.data[0])
            break

    odb.close()

    query_text = []
    query_text.append('Target global coordinate: X=100, Y=5, Z=5')
    query_text.append('Matched ODB instance: ' + str(inst_name))
    query_text.append('Matched node label: ' + str(node_label))
    query_text.append('Matched node coordinate in ODB: ' + str(node_coord))
    query_text.append('Matched target used for nearest-node search: ' + str(matched_target))
    query_text.append('Distance to matched target: ' + str(distance))
    query_text.append('Displacement vector U = ' + str(u_data))
    query_text.append('Queried U1 = ' + str(u1_value))

    with open(QUERY_PATH, 'w') as f:
        f.write('\n'.join(query_text) + '\n')

    print('>>> U1 query at free-end center completed.')
    print('>>> U1 = ' + str(u1_value))
    print('>>> Query details saved to: ' + QUERY_PATH)

except Exception as e:
    print('>>> Warning: U1 query failed: ' + str(e))

print('>>> Completed all requested operations.')
