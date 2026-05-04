# -*- coding: utf-8 -*-
# Job-FlangeHole.py
# Abaqus/CAE script for a 3D shell tensile analysis of a plate with a central circular hole.
# Run command:
#     abaqus cae script=Job-FlangeHole.py

from abaqus import *
from abaqusConstants import *
from caeModules import *
from driverUtils import executeOnCaeStartup
import mesh
import os

executeOnCaeStartup()

# ============================================================
# 0. Basic parameters
# ============================================================
MODEL_NAME = 'Model-FlangeHole'
PART_NAME = 'FlangeHolePlate'
JOB_NAME = 'Job-FlangeHole'

WIDTH_X = 120.0       # mm
HEIGHT_Y = 240.0      # mm
HOLE_D = 12.0         # mm
HOLE_R = HOLE_D / 2.0 # mm
THICKNESS = 1.0       # mm

E = 210000.0          # MPa = N/mm^2
NU = 0.3
EDGE_LOAD = 8.0       # N/mm

GLOBAL_SEED = 6.0     # mm
HOLE_SEED = 1.2       # mm
TOL = 1.0e-4

# Save on the path specified by the instruction when it exists.
# If that Windows user folder does not exist, fall back to the current user's Desktop.
fixed_desktop = r'C:\Users\User\Desktop'
current_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
SAVE_DIR = fixed_desktop if os.path.isdir(fixed_desktop) else current_desktop
if not os.path.isdir(SAVE_DIR):
    os.makedirs(SAVE_DIR)

os.chdir(SAVE_DIR)

CAE_PATH = os.path.join(SAVE_DIR, JOB_NAME + '.cae')
ODB_PATH = os.path.join(SAVE_DIR, JOB_NAME + '.odb')

# ============================================================
# 1. Clean old model/job in current CAE session
# ============================================================
if MODEL_NAME in mdb.models.keys():
    del mdb.models[MODEL_NAME]

if JOB_NAME in mdb.jobs.keys():
    del mdb.jobs[JOB_NAME]

model = mdb.Model(name=MODEL_NAME)

# ============================================================
# 2. Part: 3D deformable shell plate with central circular hole
# ============================================================
sketch = model.ConstrainedSketch(name='plate_with_hole_profile', sheetSize=400.0)
sketch.rectangle(point1=(0.0, 0.0), point2=(WIDTH_X, HEIGHT_Y))
sketch.CircleByCenterPerimeter(center=(WIDTH_X / 2.0, HEIGHT_Y / 2.0),
                               point1=(WIDTH_X / 2.0 + HOLE_R, HEIGHT_Y / 2.0))

part = model.Part(name=PART_NAME, dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseShell(sketch=sketch)
del sketch

# Useful named sets at part level
part.Set(name='All-Faces', faces=part.faces)

# Hole edge at point (66, 120, 0)
hole_edge = part.edges.findAt(((WIDTH_X / 2.0 + HOLE_R, HEIGHT_Y / 2.0, 0.0),))
part.Set(name='Hole-Edge', edges=(hole_edge,))

# Outer edges at X=0 and X=120
left_edge_p = part.edges.findAt(((0.0, HEIGHT_Y / 2.0, 0.0),))
right_edge_p = part.edges.findAt(((WIDTH_X, HEIGHT_Y / 2.0, 0.0),))
part.Set(name='Left-Edge', edges=(left_edge_p,))
part.Set(name='Right-Edge', edges=(right_edge_p,))

# Corner vertices
bl_v = part.vertices.findAt(((0.0, 0.0, 0.0),))
br_v = part.vertices.findAt(((WIDTH_X, 0.0, 0.0),))
tl_v = part.vertices.findAt(((0.0, HEIGHT_Y, 0.0),))
part.Set(name='BL-Corner', vertices=(bl_v,))
part.Set(name='BR-Corner', vertices=(br_v,))
part.Set(name='TL-Corner', vertices=(tl_v,))

# ============================================================
# 3. Property: Steel + homogeneous shell section
# ============================================================
material = model.Material(name='Steel')
material.Elastic(table=((E, NU),))

model.HomogeneousShellSection(
    name='Shell-1',
    material='Steel',
    thickness=THICKNESS,
    thicknessType=UNIFORM,
    integrationRule=SIMPSON,
    numIntPts=5
)

part.SectionAssignment(region=part.sets['All-Faces'], sectionName='Shell-1')

# ============================================================
# 4. Assembly
# ============================================================
assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)

instance = assembly.Instance(name=PART_NAME + '-1', part=part, dependent=ON)

# Assembly-level sets and surfaces for loads/BCs
assembly.Set(name='BL-Corner', vertices=instance.vertices.findAt(((0.0, 0.0, 0.0),)))
assembly.Set(name='BR-Corner', vertices=instance.vertices.findAt(((WIDTH_X, 0.0, 0.0),)))
assembly.Set(name='TL-Corner', vertices=instance.vertices.findAt(((0.0, HEIGHT_Y, 0.0),)))

left_edge = instance.edges.findAt(((0.0, HEIGHT_Y / 2.0, 0.0),))
right_edge = instance.edges.findAt(((WIDTH_X, HEIGHT_Y / 2.0, 0.0),))

assembly.Set(name='Left-Edge', edges=(left_edge,))
assembly.Set(name='Right-Edge', edges=(right_edge,))

left_surf = assembly.Surface(name='Left-Edge-Surf', side1Edges=(left_edge,))
right_surf = assembly.Surface(name='Right-Edge-Surf', side1Edges=(right_edge,))

# ============================================================
# 5. Step
# ============================================================
model.StaticStep(name='Step-HoleTension', previous='Initial', nlgeom=OFF)

# ============================================================
# 6. Loads and boundary conditions
# ============================================================
# Rigid-body suppression without over-constraining X-direction tension:
#   bottom-left:  U1=U2=U3=0
#   bottom-right: U2=U3=0
#   top-left:     U3=0
model.DisplacementBC(
    name='BC-BL-U123',
    createStepName='Initial',
    region=assembly.sets['BL-Corner'],
    u1=0.0, u2=0.0, u3=0.0,
    ur1=UNSET, ur2=UNSET, ur3=UNSET
)

model.DisplacementBC(
    name='BC-BR-U23',
    createStepName='Initial',
    region=assembly.sets['BR-Corner'],
    u1=UNSET, u2=0.0, u3=0.0,
    ur1=UNSET, ur2=UNSET, ur3=UNSET
)

model.DisplacementBC(
    name='BC-TL-U3',
    createStepName='Initial',
    region=assembly.sets['TL-Corner'],
    u1=UNSET, u2=UNSET, u3=0.0,
    ur1=UNSET, ur2=UNSET, ur3=UNSET
)

# Apply outward line loads on the two vertical edges:
# left edge:  global -X
# right edge: global +X
#
# In some Abaqus versions, ShellEdgeLoad does not support an explicit direction vector.
# Therefore this script first tries the explicit ShellEdgeLoad form. If unavailable,
# it falls back to general SurfaceTraction on the shell edge surfaces, which is
# equivalent for this line-load purpose and preserves the specified global directions.
def apply_outward_edge_load(model_obj, load_name, surf_region, direction_tuple, magnitude):
    try:
        model_obj.ShellEdgeLoad(
            name=load_name,
            createStepName='Step-HoleTension',
            region=surf_region,
            magnitude=magnitude,
            directionVector=((0.0, 0.0, 0.0), direction_tuple),
            distributionType=UNIFORM,
            field='',
            localCsys=None,
            resultant=ON
        )
    except TypeError:
        model_obj.SurfaceTraction(
            name=load_name,
            createStepName='Step-HoleTension',
            region=surf_region,
            magnitude=magnitude,
            directionVector=((0.0, 0.0, 0.0), direction_tuple),
            distributionType=UNIFORM,
            field='',
            localCsys=None,
            traction=GENERAL,
            follower=OFF,
            resultant=ON
        )

apply_outward_edge_load(model, 'EdgeLoad-Left-NegX', left_surf, (-1.0, 0.0, 0.0), EDGE_LOAD)
apply_outward_edge_load(model, 'EdgeLoad-Right-PosX', right_surf, (1.0, 0.0, 0.0), EDGE_LOAD)

# ============================================================
# 7. Mesh: global seed = 6 mm; hole edge seed = 1.2 mm; element type S4R
# ============================================================
part.seedPart(size=GLOBAL_SEED, deviationFactor=0.1, minSizeFactor=0.1)

part.seedEdgeBySize(
    edges=part.sets['Hole-Edge'].edges,
    size=HOLE_SEED,
    deviationFactor=0.1,
    minSizeFactor=0.1,
    constraint=FINER
)

elem_type = mesh.ElemType(
    elemCode=S4R,
    elemLibrary=STANDARD,
    secondOrderAccuracy=OFF,
    hourglassControl=DEFAULT
)

part.setElementType(regions=(part.faces,), elemTypes=(elem_type,))
part.generateMesh()

# Regenerate assembly after part mesh generation
assembly.regenerate()

# ============================================================
# 8. Job
# ============================================================
mdb.Job(
    name=JOB_NAME,
    model=MODEL_NAME,
    description='3D shell tensile analysis of a plate with a central circular hole',
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

mdb.jobs[JOB_NAME].submit()
mdb.jobs[JOB_NAME].waitForCompletion()

# ============================================================
# 9. Save CAE database
# ============================================================
mdb.saveAs(pathName=CAE_PATH)

print('>>> Analysis completed.')
print('>>> CAE saved to: ' + CAE_PATH)
print('>>> ODB expected at: ' + ODB_PATH)
