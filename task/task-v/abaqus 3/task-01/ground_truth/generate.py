# -*- coding: utf-8 -*-
# Abaqus 2025 LE stable version
# Generate INP + CAE + ODB
#
# Run command:
# abaqus cae noGUI=1.py

from abaqus import *
from abaqusConstants import *
import os
import math

# ============================================================
# 0. Basic parameters
# ============================================================

work_dir = r'C:\Users\Administrator\Desktop'

job_name = 'Job-Plate'
cae_model_name = 'Model-Plate-From-INP'

inp_path = os.path.join(work_dir, job_name + '.inp')
cae_path_no_ext = os.path.join(work_dir, job_name)
odb_path = os.path.join(work_dir, job_name + '.odb')

# Geometry
R = 50.0          # radius, mm
H = 1.0           # axial thickness / height, mm

# Mesh
dr_target = 2.0   # radial mesh size, mm
nz = 1            # number of elements through thickness

# Material
E = 210000.0      # MPa = N/mm^2
nu = 0.3

# Load
pressure = 0.1    # N/mm^2, downward pressure on top surface

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

nr = int(round(R / dr_target))
if nr < 1:
    nr = 1

dr = R / float(nr)
dz = H / float(nz)

nodes = []
node_id = 1

# Coordinate system for axisymmetric model:
# x = radial coordinate r
# y = axial coordinate z
for j in range(nz + 1):
    z = j * dz
    for i in range(nr + 1):
        r = i * dr
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
        'Node count exceeds Abaqus Learning Edition limit. '
        'Increase dr_target.'
    )

# ============================================================
# 3. Define node sets
# ============================================================

axis_nodes = []
outer_nodes = []
top_nodes = []

for nid, r, z in nodes:
    if abs(r - 0.0) < 1.0e-8:
        axis_nodes.append(nid)

    if abs(r - R) < 1.0e-8:
        outer_nodes.append(nid)

    if abs(z - H) < 1.0e-8:
        top_nodes.append((nid, r, z))

top_nodes.sort(key=lambda item: item[1])

# ============================================================
# 4. Equivalent nodal force for top pressure
# ============================================================
# For axisymmetric model:
# dF = p * 2*pi*r*dr
#
# This gives the same total force as:
# F = p * pi * R^2

loads = []
total_force = 0.0
n_top = len(top_nodes)

for k in range(n_top):
    nid, r, z = top_nodes[k]

    if n_top == 1:
        width = R
    elif k == 0:
        width = 0.5 * (top_nodes[k + 1][1] - top_nodes[k][1])
    elif k == n_top - 1:
        width = 0.5 * (top_nodes[k][1] - top_nodes[k - 1][1])
    else:
        width = 0.5 * (top_nodes[k + 1][1] - top_nodes[k - 1][1])

    force = pressure * 2.0 * math.pi * r * width
    total_force += force

    # r = 0 node has zero circumferential area, so skip zero force
    if abs(force) > 1.0e-12:
        loads.append((nid, -force))

theoretical_force = pressure * math.pi * R * R

print('>>> Equivalent total force   = %.6f N' % total_force)
print('>>> Theoretical total force  = %.6f N' % theoretical_force)

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
    f.write('Axisymmetric CAX4R plate model generated by Python\n')
    f.write('** Units: N, mm, MPa\n')
    f.write('** R = %.6f, H = %.6f, pressure = %.6f\n' % (R, H, pressure))
    f.write('** Equivalent total force = %.6f N\n' % total_force)
    f.write('** Theoretical total force = %.6f N\n' % theoretical_force)

    # --------------------------------------------------------
    # Part
    # --------------------------------------------------------
    f.write('*Part, name=PlatePart\n')

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

    # --------------------------------------------------------
    # Assembly
    # --------------------------------------------------------
    f.write('*Assembly, name=Assembly\n')

    f.write('*Instance, name=Plate-1, part=PlatePart\n')
    f.write('*End Instance\n')

    f.write('*Nset, nset=AXIS, instance=Plate-1\n')
    write_id_list(f, axis_nodes)

    f.write('*Nset, nset=OUTER, instance=Plate-1\n')
    write_id_list(f, outer_nodes)

    f.write('*Nset, nset=TOP, instance=Plate-1\n')
    write_id_list(f, [item[0] for item in top_nodes])

    # Individual node sets for concentrated loads
    for nid, fy in loads:
        set_name = 'LOAD_NODE_%d' % nid
        f.write('*Nset, nset=%s, instance=Plate-1\n' % set_name)
        f.write('%d\n' % nid)

    f.write('*End Assembly\n')

    # --------------------------------------------------------
    # Material
    # --------------------------------------------------------
    f.write('*Material, name=Steel\n')
    f.write('*Elastic\n')
    f.write('%.6f, %.6f\n' % (E, nu))

    # --------------------------------------------------------
    # Boundary conditions
    # --------------------------------------------------------
    f.write('** Boundary conditions\n')
    f.write('*Boundary\n')

    # Axisymmetric axis: radial displacement U1 = 0
    f.write('AXIS, 1, 1, 0.0\n')

    # Outer edge fixed: U1 = U2 = 0
    f.write('OUTER, 1, 2, 0.0\n')

    # --------------------------------------------------------
    # Step
    # --------------------------------------------------------
    f.write('*Step, name=Step-Pressure, nlgeom=NO\n')
    f.write('*Static\n')
    f.write('1.0, 1.0, 1.0e-05, 1.0\n')

    f.write('** Equivalent nodal forces for top pressure\n')
    f.write('*Cload\n')

    for nid, fy in loads:
        set_name = 'LOAD_NODE_%d' % nid
        f.write('%s, 2, %.10f\n' % (set_name, fy))

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------
    f.write('*Output, field\n')
    f.write('*Node Output\n')
    f.write('U, RF\n')
    f.write('*Element Output, directions=YES\n')
    f.write('S, E\n')

    f.write('*Output, history\n')
    f.write('*Node Output, nset=TOP\n')
    f.write('U2,\n')

    f.write('*End Step\n')

print('>>> INP file written:')
print('>>> ' + inp_path)

# ============================================================
# 7. Import INP into Abaqus/CAE and save CAE file
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
    print('>>> ODB missing. Please check Job-Plate.dat and Job-Plate.msg.')

print('>>> DAT file: ' + os.path.join(work_dir, job_name + '.dat'))
print('>>> LOG file: ' + os.path.join(work_dir, job_name + '.log'))
print('>>> STA file: ' + os.path.join(work_dir, job_name + '.sta'))

print('>>> Done.')