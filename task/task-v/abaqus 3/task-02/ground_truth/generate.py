# -*- coding: utf-8 -*-
# Abaqus 2025 LE stable version
# Generate INP + CAE + ODB for task-02 cylinder pressure model
#
# Run command:
# abaqus cae noGUI=generate.py

from abaqus import *
from abaqusConstants import *
import os
import math

# ============================================================
# 0. Basic parameters
# ============================================================

work_dir = r'C:\Users\Administrator\Desktop'

job_name = 'Job-Cylinder'
cae_model_name = 'Model-Cylinder-From-INP'

inp_path = os.path.join(work_dir, job_name + '.inp')
cae_path_no_ext = os.path.join(work_dir, job_name)
odb_path = os.path.join(work_dir, job_name + '.odb')

# Geometry (axisymmetric r-z)
RIN = 50.0
ROUT = 100.0
L = 10.0

# Mesh
seed = 5.0
nr = int(round((ROUT - RIN) / seed))
nz = int(round(L / seed))
if nr < 1:
    nr = 1
if nz < 1:
    nz = 1
dr = (ROUT - RIN) / float(nr)
dz = L / float(nz)

# Material
E = 210000.0
nu = 0.3

# Load
pressure = 10.0  # MPa = N/mm^2

# Abaqus Learning Edition node limit
LE_NODE_LIMIT = 1000

os.chdir(work_dir)

# ============================================================
# 1. Clean old files
# ============================================================

old_exts = [
    '.inp', '.odb', '.dat', '.msg', '.sta', '.log', '.com',
    '.prt', '.sim', '.res', '.mdl', '.stt', '.lck', '.cae'
]

for ext in old_exts:
    old_file = os.path.join(work_dir, job_name + ext)
    if os.path.exists(old_file):
        try:
            os.remove(old_file)
            print('>>> Removed old file: ' + old_file)
        except:
            print('>>> Warning: cannot remove old file, please close it: ' + old_file)

if job_name in mdb.jobs.keys():
    del mdb.jobs[job_name]

if cae_model_name in mdb.models.keys():
    del mdb.models[cae_model_name]

# ============================================================
# 2. Generate structured CAX4R mesh
# ============================================================

nodes = []
node_id = 1
for j in range(nz + 1):
    z = j * dz
    for i in range(nr + 1):
        r = RIN + i * dr
        nodes.append((node_id, r, z))
        node_id += 1

def node_label(i, j):
    return j * (nr + 1) + i + 1

elements = []
elem_id = 1
for j in range(nz):
    for i in range(nr):
        n1 = node_label(i, j)
        n2 = node_label(i + 1, j)
        n3 = node_label(i + 1, j + 1)
        n4 = node_label(i, j + 1)
        elements.append((elem_id, n1, n2, n3, n4))
        elem_id += 1

num_nodes = len(nodes)
num_elems = len(elements)

print('>>> Number of nodes    = %d' % num_nodes)
print('>>> Number of elements = %d' % num_elems)

if num_nodes > LE_NODE_LIMIT:
    raise RuntimeError(
        'Node count exceeds Abaqus Learning Edition limit. Increase mesh size.'
    )

# ============================================================
# 3. Define node sets
# ============================================================

all_nodes = []
inner_nodes = []
outer_nodes = []
zmin_nodes = []
zmax_nodes = []

for nid, r, z in nodes:
    all_nodes.append(nid)

    if abs(r - RIN) < 1.0e-8:
        inner_nodes.append((nid, r, z))
    if abs(r - ROUT) < 1.0e-8:
        outer_nodes.append((nid, r, z))
    if abs(z - 0.0) < 1.0e-8:
        zmin_nodes.append((nid, r, z))
    if abs(z - L) < 1.0e-8:
        zmax_nodes.append((nid, r, z))

inner_nodes.sort(key=lambda item: item[2])  # by z
outer_nodes.sort(key=lambda item: item[2])  # by z
zmin_nodes.sort(key=lambda item: item[1])   # by r
zmax_nodes.sort(key=lambda item: item[1])   # by r

# ============================================================
# 4. Equivalent nodal force for internal pressure on INNER
# ============================================================
# For axisymmetric model on inner radial face:
# dF = p * 2*pi*RIN*dz, acting in +U1 (outward radial direction)

loads = []
total_force = 0.0
n_inner = len(inner_nodes)

for k in range(n_inner):
    nid, r, z = inner_nodes[k]

    if n_inner == 1:
        width = L
    elif k == 0:
        width = 0.5 * (inner_nodes[k + 1][2] - inner_nodes[k][2])
    elif k == n_inner - 1:
        width = 0.5 * (inner_nodes[k][2] - inner_nodes[k - 1][2])
    else:
        width = 0.5 * (inner_nodes[k + 1][2] - inner_nodes[k - 1][2])

    force = pressure * 2.0 * math.pi * RIN * width
    total_force += force
    loads.append((nid, force))

theoretical_total = pressure * 2.0 * math.pi * RIN * L

print('>>> Equivalent total inner force  = %.6f N' % total_force)
print('>>> Theoretical total inner force = %.6f N' % theoretical_total)

# ============================================================
# 5. Helper function for writing ID lists
# ============================================================

def write_id_list(f, ids, per_line=16):
    line_items = []
    for value in ids:
        line_items.append(str(value))
        if len(line_items) == per_line:
            f.write(', '.join(line_items) + '\n')
            line_items = []
    if len(line_items) > 0:
        f.write(', '.join(line_items) + '\n')

# ============================================================
# 6. Write Abaqus input file
# ============================================================

with open(inp_path, 'w') as f:
    f.write('*Heading\n')
    f.write('Axisymmetric thick cylinder generated by Python\n')
    f.write('** Units: N, mm, MPa\n')
    f.write('** RIN = %.6f, ROUT = %.6f, L = %.6f, p = %.6f\n' % (RIN, ROUT, L, pressure))
    f.write('** Equivalent total inner force = %.6f N\n' % total_force)
    f.write('** Theoretical total inner force = %.6f N\n' % theoretical_total)

    # Part
    f.write('*Part, name=CylinderPart\n')
    f.write('*Node\n')
    for nid, r, z in nodes:
        f.write('%d, %.10f, %.10f\n' % (nid, r, z))

    f.write('*Element, type=CAX4R, elset=EALL\n')
    for eid, n1, n2, n3, n4 in elements:
        f.write('%d, %d, %d, %d, %d\n' % (eid, n1, n2, n3, n4))

    f.write('*Elset, elset=EALL, generate\n')
    f.write('1, %d, 1\n' % num_elems)

    f.write('*Solid Section, elset=EALL, material=Steel\n')
    f.write(',\n')
    f.write('*End Part\n')

    # Assembly
    f.write('*Assembly, name=Assembly\n')
    f.write('*Instance, name=CYLINDER-1, part=CylinderPart\n')
    f.write('*End Instance\n')

    f.write('*Nset, nset=ALLNODES, instance=CYLINDER-1\n')
    write_id_list(f, all_nodes)

    f.write('*Nset, nset=INNER, instance=CYLINDER-1\n')
    write_id_list(f, [item[0] for item in inner_nodes])

    f.write('*Nset, nset=OUTER, instance=CYLINDER-1\n')
    write_id_list(f, [item[0] for item in outer_nodes])

    f.write('*Nset, nset=ZMIN, instance=CYLINDER-1\n')
    write_id_list(f, [item[0] for item in zmin_nodes])

    f.write('*Nset, nset=ZMAX, instance=CYLINDER-1\n')
    write_id_list(f, [item[0] for item in zmax_nodes])

    for nid, f1 in loads:
        set_name = 'LOAD_NODE_%d' % nid
        f.write('*Nset, nset=%s, instance=CYLINDER-1\n' % set_name)
        f.write('%d\n' % nid)

    f.write('*End Assembly\n')

    # Material
    f.write('*Material, name=Steel\n')
    f.write('*Elastic\n')
    f.write('%.6f, %.6f\n' % (E, nu))

    # Boundary condition
    f.write('** Boundary conditions\n')
    f.write('*Boundary\n')
    f.write('ALLNODES, 2, 2, 0.0\n')

    # Step
    f.write('*Step, name=Step-Pressure, nlgeom=NO\n')
    f.write('*Static\n')
    f.write('1.0, 1.0, 1.0e-05, 1.0\n')

    f.write('** Equivalent nodal forces for inner pressure\n')
    f.write('*Cload\n')
    for nid, f1 in loads:
        set_name = 'LOAD_NODE_%d' % nid
        f.write('%s, 1, %.10f\n' % (set_name, f1))

    # Output
    f.write('*Output, field\n')
    f.write('*Node Output\n')
    f.write('U, RF\n')
    f.write('*Element Output, directions=YES\n')
    f.write('S\n')
    f.write('*End Step\n')

print('>>> INP file written:')
print('>>> ' + inp_path)

# ============================================================
# 7. Import INP and save CAE
# ============================================================

if cae_model_name in mdb.models.keys():
    del mdb.models[cae_model_name]

print('>>> Importing INP into CAE model database...')
mdb.ModelFromInputFile(
    name=cae_model_name,
    inputFileName=inp_path
)

print('>>> Saving CAE file...')
mdb.saveAs(pathName=cae_path_no_ext)

print('>>> CAE file saved:')
print('>>> ' + cae_path_no_ext + '.cae')

# ============================================================
# 8. Submit job from INP file to generate ODB
# ============================================================

if job_name in mdb.jobs.keys():
    del mdb.jobs[job_name]

print('>>> Submitting Abaqus job...')
mdb.JobFromInputFile(
    name=job_name,
    inputFileName=inp_path,
    type=ANALYSIS,
    numCpus=1,
    numDomains=1
)

mdb.jobs[job_name].submit(consistencyChecking=OFF)
mdb.jobs[job_name].waitForCompletion()

print('>>> Job finished.')

# ============================================================
# 9. Check output files
# ============================================================

cae_file = cae_path_no_ext + '.cae'

print('>>> Output check:')
if os.path.exists(cae_file):
    print('>>> CAE exists: ' + cae_file)
else:
    print('>>> CAE missing: ' + cae_file)

if os.path.exists(odb_path):
    print('>>> ODB exists: ' + odb_path)
else:
    print('>>> ODB missing. Please check Job-Cylinder.dat and Job-Cylinder.msg.')

print('>>> DAT file: ' + os.path.join(work_dir, job_name + '.dat'))
print('>>> LOG file: ' + os.path.join(work_dir, job_name + '.log'))
print('>>> STA file: ' + os.path.join(work_dir, job_name + '.sta'))
print('>>> Done.')
