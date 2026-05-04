# -*- coding: utf-8 -*-
"""
Combined generator + truth extractor for task-20.
Run from task-specific wrapper:
    abaqus cae noGUI=generategt.py
"""

from abaqus import *
from abaqusConstants import *
from caeModules import *
from odbAccess import openOdb
import mesh
import os
import sys
import json
import math
import time
import traceback

ADMIN_DESKTOP = r'C:\Users\Administrator\Desktop'

TASKS = {
    'task-05': {
        'category': 'solid_tension',
        'job_name': 'Job-BlockTension',
        'model_name': 'Model-BlockTension',
        'step_name': 'Step-Load',
        'dims': (120.0, 12.0, 8.0),
        'material': {'name': 'Aluminum', 'E': 70000.0, 'nu': 0.33},
        'seed': 4.0,
        'elem': 'C3D8R',
        'traction': 8.33,
        'metrics': {'mid_x': 60.0, 'u_pt': (120.0, 6.0, 4.0)},
    },
    'task-06': {
        'category': 'heat_steady',
        'job_name': 'Job-Thermal',
        'model_name': 'Model-Thermal',
        'step_name': 'Step-Thermal',
        'dims': (100.0, 50.0, 10.0),
        'material': {'name': 'Copper', 'k': 0.0004},
        'seed': 5.0,
        'elem': 'DC3D8',
        'temp_hot': 100.0,
        'temp_cold': 20.0,
        'metrics': {'mid_pt': (50.0, 25.0, 5.0)},
    },
    'task-07': {
        'category': 'torsion',
        'job_name': 'Job-Torsion',
        'model_name': 'Model-Torsion',
        'step_name': 'Step-Torque',
        'radius': 5.0,
        'length': 100.0,
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed': 2.0,
        'elem': 'C3D8R',
        'moment': 1000.0,
        'axis': 'Y',
    },
    'task-08': {
        'category': 'contact_block_plate',
        'job_name': 'Job-Contact',
        'model_name': 'Model-Contact',
        'step_name': 'Step-1',
        'block': {'x': 20.0, 'y': 20.0, 'z': 30.0},
        'plate': {'x': 100.0, 'y': 100.0, 'z': 5.0},
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed_block': 3.0,
        'seed_plate': 5.0,
        'elem': 'C3D8R',
        'pressure': 10.0,
    },
    'task-09': {
        'category': 'beam_udl',
        'job_name': 'Job-UDL',
        'model_name': 'Model-UDL',
        'step_name': 'Step-Load',
        'dims': (200.0, 10.0, 10.0),
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed': 5.0,
        'elem': 'C3D8R',
        'pressure': 0.05,
        'metrics': {'u_pt': (100.0, 0.0, 5.0), 'mid_x': 100.0},
    },
    'task-10': {
        'category': 'torsion',
        'job_name': 'Job-Torsion',
        'model_name': 'Model-Torsion',
        'step_name': 'Step-Torque',
        'radius': 5.0,
        'length': 100.0,
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed': 2.0,
        'elem': 'C3D8R',
        'moment': 1000.0,
        'axis': 'Y',
    },
    'task-11': {
        'category': 'beam_udl',
        'job_name': 'Job-Beam',
        'model_name': 'Model-Beam',
        'step_name': 'Step-Load',
        'dims': (200.0, 10.0, 10.0),
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed': 5.0,
        'elem': 'C3D8R',
        'pressure': 0.1,
        'metrics': {'u_pt': (100.0, 0.0, 5.0), 'mid_x': 100.0},
    },
    'task-12': {
        'category': 'buckle_plate',
        'job_name': 'Job-Buckle',
        'model_name': 'Model-Buckle',
        'step_name': 'Step-Buckle',
        'size': 100.0,
        'thickness': 1.0,
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed': 5.0,
        'elem': 'S4R',
        'edge_load': 1.0,
        'num_eigen': 3,
    },
    'task-13': {
        'category': 'modal_cantilever',
        'job_name': 'Job-Modal',
        'model_name': 'Model-Modal',
        'step_name': 'Step-Modal',
        'dims': (500.0, 10.0, 10.0),
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3, 'rho': 7.85e-9},
        'seed': 10.0,
        'elem': 'C3D8R',
        'num_eigen': 3,
    },
    'task-14': {
        'category': 'thermal_stress',
        'job_name': 'Job-ThermalStress-A',
        'model_name': 'Model-ThermalStress-A',
        'step_name': 'Step-Thermal-A',
        'dims': (100.0, 10.0, 10.0),
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3, 'alpha': 1.2e-5},
        'seed': 5.0,
        'elem': 'C3D8R',
        'temp0': 20.0,
        'temp1': 120.0,
        'metrics': {'mid_x': 50.0},
    },
    'task-15': {
        'category': 'thermal_stress',
        'job_name': 'Job-ThermalStress-B',
        'model_name': 'Model-ThermalStress-B',
        'step_name': 'Step-Thermal-B',
        'dims': (120.0, 8.0, 8.0),
        'material': {'name': 'Aluminum', 'E': 70000.0, 'nu': 0.33, 'alpha': 2.3e-5},
        'seed': 6.0,
        'elem': 'C3D8R',
        'temp0': 20.0,
        'temp1': 100.0,
        'metrics': {'mid_x': 60.0},
    },
    'task-16': {
        'category': 'heat_transient',
        'job_name': 'Job-TransientHeat',
        'model_name': 'Model-TransientHeat',
        'step_name': 'Step-Heat',
        'dims': (50.0, 20.0, 20.0),
        'material': {'name': 'Steel', 'rho': 7.85e-9, 'k': 0.05, 'cp': 4.6e8},
        'seed': 2.0,
        'elem': 'DC3D8',
        'temp0': 20.0,
        'temp_hot': 100.0,
        'time_period': 400.0,
        'init_inc': 1.0,
        'max_inc': 10.0,
    },
    'task-17': {
        'category': 'thermal_stress',
        'job_name': 'Job-ThermalStress',
        'model_name': 'Model-ThermalStress',
        'step_name': 'Step-ThermalStress',
        'dims': (100.0, 10.0, 10.0),
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3, 'alpha': 1.2e-5},
        'seed': 5.0,
        'elem': 'C3D8R',
        'temp0': 20.0,
        'temp1': 120.0,
        'metrics': {'mid_x': 50.0},
    },
    'task-18': {
        'category': 'modal_cantilever',
        'job_name': 'Job-Modal',
        'model_name': 'Model-Modal',
        'step_name': 'Step-Modal',
        'dims': (500.0, 10.0, 10.0),
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3, 'rho': 7.85e-9},
        'seed': 10.0,
        'elem': 'C3D8R',
        'num_eigen': 3,
    },
    'task-19': {
        'category': 'buckle_plate',
        'job_name': 'Job-Buckle',
        'model_name': 'Model-Buckle',
        'step_name': 'Step-Buckle',
        'size': 100.0,
        'thickness': 1.0,
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed': 5.0,
        'elem': 'S4R',
        'edge_load': 1.0,
        'num_eigen': 3,
    },
    'task-20': {
        'category': 'hole_shell_tension',
        'job_name': 'Job-Hole-A',
        'model_name': 'Model-Hole-A',
        'step_name': 'Step-Tension-A',
        'width': 160.0,
        'height': 80.0,
        'hole_d': 16.0,
        'thickness': 1.2,
        'material': {'name': 'Steel', 'E': 210000.0, 'nu': 0.3},
        'seed_global': 10.0,
        'seed_hole': 4.0,
        'elem': 'S4R',
        'edge_load': 12.0,
    },
}


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%S')


def job_paths(work_dir, job_name):
    return {
        'cae': os.path.join(work_dir, job_name + '.cae'),
        'odb': os.path.join(work_dir, job_name + '.odb'),
        'truth': os.path.join(work_dir, 'truth_values.json'),
    }


def clean_job_files(work_dir, job_name):
    exts = [
        '.cae', '.odb', '.inp', '.dat', '.msg', '.sta', '.log', '.com', '.prt',
        '.sim', '.res', '.mdl', '.stt', '.lck'
    ]
    for ext in exts:
        p = os.path.join(work_dir, job_name + ext)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    try:
        if job_name in mdb.jobs.keys():
            del mdb.jobs[job_name]
    except Exception:
        pass


def create_material_and_section_for_solid(model, part, mat_name, E, nu):
    model.Material(name=mat_name)
    model.materials[mat_name].Elastic(table=((E, nu),))
    sec_name = 'Sec-Solid'
    model.HomogeneousSolidSection(name=sec_name, material=mat_name, thickness=None)
    part.Set(name='ALL_CELLS', cells=part.cells)
    part.SectionAssignment(region=part.sets['ALL_CELLS'], sectionName=sec_name)


def create_bar_part_local_z(model, part_name, length_x, width_y, width_z):
    sketch = model.ConstrainedSketch(name='bar_sketch', sheetSize=max(length_x, width_y, width_z) * 5.0)
    sketch.rectangle(point1=(0.0, 0.0), point2=(width_z, width_y))
    part = model.Part(name=part_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sketch, depth=length_x)
    del sketch
    return part


def place_bar_instance_along_x(assembly, part_name, instance_name, width_z):
    inst = assembly.Instance(name=instance_name, part=assembly.model().parts[part_name] if hasattr(assembly, 'model') else None, dependent=ON)
    # Fallback: if assembly.model() is unavailable, the caller should pass instance directly.
    return inst


def assign_hex_mesh(part, seed, elem_code):
    part.seedPart(size=seed, deviationFactor=0.1, minSizeFactor=0.1)
    try:
        part.setMeshControls(regions=part.cells, elemShape=HEX, technique=STRUCTURED)
    except Exception:
        pass
    elem_type = mesh.ElemType(elemCode=elem_code, elemLibrary=STANDARD)
    part.setElementType(regions=(part.cells,), elemTypes=(elem_type,))
    part.generateMesh()


def find_step_case_insensitive(steps, target):
    tu = target.upper()
    for k in steps.keys():
        if k.upper() == tu:
            return k
    return None


def to_float(x):
    return float(x)


def safe_data_component(data, idx=0):
    try:
        return to_float(data[idx])
    except Exception:
        try:
            return to_float(data)
        except Exception:
            return None


def repo_get_field(repo, name):
    try:
        if name in repo.keys():
            return repo[name]
    except Exception:
        pass
    return None


def get_main_instance(root_assembly):
    best_key = None
    best_n = -1
    for k in root_assembly.instances.keys():
        inst = root_assembly.instances[k]
        n = len(inst.nodes)
        if n > best_n:
            best_n = n
            best_key = k
    if best_key is None:
        return None
    return root_assembly.instances[best_key]


def nearest_node_value(field_values, inst, target, comp_idx=0, use_abs=False):
    best_dist = None
    best_val = None
    for v in field_values:
        if v.nodeLabel is None:
            continue
        try:
            node = inst.getNodeFromLabel(v.nodeLabel)
            x, y, z = node.coordinates
            d = math.sqrt((x - target[0])**2 + (y - target[1])**2 + (z - target[2])**2)
            if best_dist is None or d < best_dist:
                best_dist = d
                value = safe_data_component(v.data, comp_idx)
                if value is None:
                    continue
                best_val = abs(value) if use_abs else value
        except Exception:
            pass
    return best_val


def average_s11_at_x(s_field_values, inst, x_target, tol=3.0):
    vals = []
    for v in s_field_values:
        if v.elementLabel is None or len(v.data) < 1:
            continue
        try:
            elem = inst.getElementFromLabel(v.elementLabel)
            xs = []
            for nid in elem.connectivity:
                node = inst.getNodeFromLabel(nid)
                xs.append(node.coordinates[0])
            if len(xs) == 0:
                continue
            cx = sum(xs) / float(len(xs))
            if abs(cx - x_target) <= tol:
                sv = safe_data_component(v.data, 0)
                if sv is not None:
                    vals.append(sv)
        except Exception:
            pass
    if len(vals) == 0:
        return None
    return sum(vals) / float(len(vals))


def max_mises_midspan(s_field_values, inst, x_target, tol=3.0):
    vals = []
    for v in s_field_values:
        if v.mises is None or v.elementLabel is None:
            continue
        try:
            elem = inst.getElementFromLabel(v.elementLabel)
            xs = [inst.getNodeFromLabel(nid).coordinates[0] for nid in elem.connectivity]
            cx = sum(xs) / float(len(xs))
            if abs(cx - x_target) <= tol:
                vals.append(float(v.mises))
        except Exception:
            pass
    if len(vals) == 0:
        return None
    return max(vals)


def parse_first_eigen(step):
    for frame in step.frames[1:]:
        desc = frame.description or ''
        try:
            tokens = desc.replace(',', ' ').replace(':', ' ').split()
            for i, tok in enumerate(tokens):
                if tok.lower().startswith('eigenvalue') and i + 1 < len(tokens):
                    try:
                        return float(tokens[i + 1])
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            if frame.frameValue is not None and float(frame.frameValue) > 0.0:
                return float(frame.frameValue)
        except Exception:
            pass
    return None


def parse_first_frequency(step):
    if len(step.frames) > 1:
        frame = step.frames[1]
        try:
            if frame.frameValue is not None and float(frame.frameValue) > 0.0:
                return float(frame.frameValue)
        except Exception:
            pass
        desc = frame.description or ''
        try:
            tokens = desc.replace(',', ' ').replace(':', ' ').split()
            for i, tok in enumerate(tokens):
                if tok.lower().startswith('frequency') and i + 1 < len(tokens):
                    try:
                        return float(tokens[i + 1])
                    except Exception:
                        pass
        except Exception:
            pass
    return None


def apply_shell_edge_traction(model, name, step_name, region, magnitude, direction_tuple):
    try:
        model.ShellEdgeLoad(
            name=name,
            createStepName=step_name,
            region=region,
            magnitude=magnitude,
            directionVector=((0.0, 0.0, 0.0), direction_tuple),
            distributionType=UNIFORM,
            field='',
            localCsys=None,
            resultant=ON
        )
        return
    except Exception:
        pass

    try:
        model.SurfaceTraction(
            name=name,
            createStepName=step_name,
            region=region,
            magnitude=magnitude,
            directionVector=((0.0, 0.0, 0.0), direction_tuple),
            distributionType=UNIFORM,
            field='',
            localCsys=None,
            traction=GENERAL,
            follower=OFF,
            resultant=ON
        )
        return
    except Exception:
        pass

    model.SurfaceTraction(
        name=name,
        createStepName=step_name,
        region=region,
        magnitude=magnitude,
        directionVector=((0.0, 0.0, 0.0), direction_tuple),
        distributionType=UNIFORM,
        field='',
        localCsys=None,
        traction=GENERAL,
        follower=OFF
    )


def create_temperature_field(model, name, step_name, region, magnitude):
    try:
        model.Temperature(
            name=name,
            createStepName=step_name,
            region=region,
            distributionType=UNIFORM,
            magnitudes=(magnitude,)
        )
        return
    except Exception:
        pass

    try:
        model.Temperature(
            name=name,
            createStepName=step_name,
            region=region,
            magnitudes=(magnitude,)
        )
        return
    except Exception:
        pass


def create_job(model_name, job_name):
    mdb.Job(
        name=job_name,
        model=model_name,
        description='Auto generated by generategt.py',
        type=ANALYSIS,
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


def build_structural_bar_x(cfg):
    model = mdb.Model(name=cfg['model_name'])
    L, WY, WZ = cfg['dims']

    # Part in local Z-length orientation
    s = model.ConstrainedSketch(name='sk_bar', sheetSize=max(L, WY, WZ) * 5.0)
    s.rectangle(point1=(0.0, 0.0), point2=(WZ, WY))
    part = model.Part(name='BAR', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=s, depth=L)
    del s

    create_material_and_section_for_solid(model, part, cfg['material']['name'], cfg['material']['E'], cfg['material']['nu'])
    assign_hex_mesh(part, cfg['seed'], C3D8R)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='BAR-1', part=part, dependent=ON)

    # Rotate +90 around global Y so local Z -> global X, then shift +WZ in Z
    a.rotate(instanceList=('BAR-1',), axisPoint=(0.0, 0.0, 0.0), axisDirection=(0.0, 1.0, 0.0), angle=90.0)
    a.translate(instanceList=('BAR-1',), vector=(0.0, 0.0, WZ))
    a.regenerate()

    face_x0 = inst.faces.findAt(((0.0, WY / 2.0, WZ / 2.0),))
    face_xL = inst.faces.findAt(((L, WY / 2.0, WZ / 2.0),))

    a.Set(name='SET_FIX', faces=(face_x0,))
    a.Surface(name='SURF_LOAD', side1Faces=(face_xL,))

    model.StaticStep(name=cfg['step_name'], previous='Initial', nlgeom=OFF)
    model.EncastreBC(name='BC-FIX', createStepName='Initial', region=a.sets['SET_FIX'])

    try:
        model.SurfaceTraction(
            name='LOAD-TRAC',
            createStepName=cfg['step_name'],
            region=a.surfaces['SURF_LOAD'],
            magnitude=cfg['traction'],
            directionVector=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
            distributionType=UNIFORM,
            field='',
            localCsys=None,
            traction=GENERAL,
            follower=OFF,
            resultant=OFF
        )
    except Exception:
        model.Pressure(name='LOAD-P', createStepName=cfg['step_name'], region=a.surfaces['SURF_LOAD'], magnitude=cfg['traction'])

    create_job(cfg['model_name'], cfg['job_name'])


def build_heat_block_steady(cfg):
    model = mdb.Model(name=cfg['model_name'])
    LX, LY, LZ = cfg['dims']

    sk = model.ConstrainedSketch(name='sk_heat', sheetSize=max(LX, LY, LZ) * 5.0)
    sk.rectangle(point1=(0.0, 0.0), point2=(LX, LY))
    part = model.Part(name='BLOCK', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sk, depth=LZ)
    del sk

    mat = model.Material(name=cfg['material']['name'])
    mat.Conductivity(table=((cfg['material']['k'],),))
    sec = 'SEC-THERM'
    model.HomogeneousSolidSection(name=sec, material=cfg['material']['name'], thickness=None)
    part.Set(name='ALL_CELLS', cells=part.cells)
    part.SectionAssignment(region=part.sets['ALL_CELLS'], sectionName=sec)

    assign_hex_mesh(part, cfg['seed'], DC3D8)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='BLOCK-1', part=part, dependent=ON)

    face_x0 = inst.faces.findAt(((0.0, LY / 2.0, LZ / 2.0),))
    face_xL = inst.faces.findAt(((LX, LY / 2.0, LZ / 2.0),))

    a.Set(name='SET_X0', faces=(face_x0,))
    a.Set(name='SET_XL', faces=(face_xL,))

    model.HeatTransferStep(name=cfg['step_name'], previous='Initial', response=STEADY_STATE)
    model.TemperatureBC(name='BC-HOT', createStepName=cfg['step_name'], region=a.sets['SET_X0'], magnitude=cfg['temp_hot'])
    model.TemperatureBC(name='BC-COLD', createStepName=cfg['step_name'], region=a.sets['SET_XL'], magnitude=cfg['temp_cold'])

    create_job(cfg['model_name'], cfg['job_name'])


def build_torsion_cylinder(cfg):
    model = mdb.Model(name=cfg['model_name'])
    R = cfg['radius']
    L = cfg['length']

    sk = model.ConstrainedSketch(name='sk_cyl', sheetSize=max(R, L) * 10.0)
    sk.rectangle(point1=(0.0, 0.0), point2=(R, L))
    part = model.Part(name='CYL', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidRevolve(sketch=sk, angle=360.0)
    del sk

    create_material_and_section_for_solid(model, part, cfg['material']['name'], cfg['material']['E'], cfg['material']['nu'])
    assign_hex_mesh(part, cfg['seed'], C3D8R)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='CYL-1', part=part, dependent=ON)

    face_fix = inst.faces.findAt(((0.0, 0.0, R / 2.0),))
    face_free = inst.faces.findAt(((0.0, L, R / 2.0),))

    a.Set(name='SET_FIX', faces=(face_fix,))
    a.Surface(name='SURF_FREE', side1Faces=(face_free,))

    rp = a.ReferencePoint(point=(0.0, L, 0.0))
    rp_obj = a.referencePoints[rp.id]
    a.Set(name='RP-1', referencePoints=(rp_obj,))

    model.StaticStep(name=cfg['step_name'], previous='Initial', nlgeom=OFF)
    model.EncastreBC(name='BC-FIX', createStepName='Initial', region=a.sets['SET_FIX'])

    # Kinematic coupling between free end and RP
    model.Coupling(
        name='COUPLE-RP1',
        controlPoint=a.sets['RP-1'],
        surface=a.surfaces['SURF_FREE'],
        influenceRadius=WHOLE_SURFACE,
        couplingType=KINEMATIC,
        localCsys=None,
        u1=ON, u2=ON, u3=ON,
        ur1=ON, ur2=ON, ur3=ON
    )

    model.Moment(
        name='LOAD-M',
        createStepName=cfg['step_name'],
        region=a.sets['RP-1'],
        cm2=cfg['moment']
    )

    create_job(cfg['model_name'], cfg['job_name'])


def build_contact_block_plate(cfg):
    model = mdb.Model(name=cfg['model_name'])

    bx, by, bz = cfg['block']['x'], cfg['block']['y'], cfg['block']['z']
    px, py, pz = cfg['plate']['x'], cfg['plate']['y'], cfg['plate']['z']

    # Block part
    sk1 = model.ConstrainedSketch(name='sk_block', sheetSize=max(px, py, bz) * 5.0)
    sk1.rectangle(point1=(0.0, 0.0), point2=(bx, by))
    part_b = model.Part(name='BLOCK', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part_b.BaseSolidExtrude(sketch=sk1, depth=bz)
    del sk1

    # Plate part
    sk2 = model.ConstrainedSketch(name='sk_plate', sheetSize=max(px, py, bz) * 5.0)
    sk2.rectangle(point1=(0.0, 0.0), point2=(px, py))
    part_p = model.Part(name='PLATE', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part_p.BaseSolidExtrude(sketch=sk2, depth=pz)
    del sk2

    mat_name = cfg['material']['name']
    model.Material(name=mat_name)
    model.materials[mat_name].Elastic(table=((cfg['material']['E'], cfg['material']['nu']),))
    sec = 'SEC-SOLID'
    model.HomogeneousSolidSection(name=sec, material=mat_name, thickness=None)

    for part in (part_b, part_p):
        part.Set(name='ALL_CELLS', cells=part.cells)
        part.SectionAssignment(region=part.sets['ALL_CELLS'], sectionName=sec)

    assign_hex_mesh(part_b, cfg['seed_block'], C3D8R)
    assign_hex_mesh(part_p, cfg['seed_plate'], C3D8R)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    ib = a.Instance(name='BLOCK-1', part=part_b, dependent=ON)
    ip = a.Instance(name='PLATE-1', part=part_p, dependent=ON)

    # Move block so its bottom center aligns with plate top center
    dx = (px - bx) / 2.0
    dy = (py - by) / 2.0
    dz = pz
    a.translate(instanceList=('BLOCK-1',), vector=(dx, dy, dz))
    a.regenerate()

    plate_bot = ip.faces.findAt(((px / 2.0, py / 2.0, 0.0),))
    plate_top = ip.faces.findAt(((px / 2.0, py / 2.0, pz),))
    block_bot = ib.faces.findAt(((dx + bx / 2.0, dy + by / 2.0, dz),))
    block_top = ib.faces.findAt(((dx + bx / 2.0, dy + by / 2.0, dz + bz),))

    a.Set(name='SET_PLATE_BOT', faces=(plate_bot,))
    a.Surface(name='SURF_PLATE_TOP', side1Faces=(plate_top,))
    a.Surface(name='SURF_BLOCK_BOT', side1Faces=(block_bot,))
    a.Surface(name='SURF_BLOCK_TOP', side1Faces=(block_top,))

    model.StaticStep(name=cfg['step_name'], previous='Initial', nlgeom=ON)
    model.EncastreBC(name='BC-PLATE-BOT', createStepName='Initial', region=a.sets['SET_PLATE_BOT'])
    model.Pressure(name='LOAD-P', createStepName=cfg['step_name'], region=a.surfaces['SURF_BLOCK_TOP'], magnitude=cfg['pressure'])

    model.ContactProperty('IntProp-1')
    model.interactionProperties['IntProp-1'].NormalBehavior(pressureOverclosure=HARD, allowSeparation=ON)
    try:
        model.interactionProperties['IntProp-1'].TangentialBehavior(formulation=FRICTIONLESS)
    except Exception:
        pass

    try:
        model.SurfaceToSurfaceContactStd(
            name='Int-1',
            createStepName=cfg['step_name'],
            main=a.surfaces['SURF_PLATE_TOP'],
            secondary=a.surfaces['SURF_BLOCK_BOT'],
            sliding=FINITE,
            interactionProperty='IntProp-1',
            adjustMethod=NONE,
            initialClearance=OMIT,
            datumAxis=None,
            clearanceRegion=None
        )
    except Exception:
        model.SurfaceToSurfaceContactStd(
            name='Int-1',
            createStepName=cfg['step_name'],
            master=a.surfaces['SURF_PLATE_TOP'],
            slave=a.surfaces['SURF_BLOCK_BOT'],
            sliding=FINITE,
            interactionProperty='IntProp-1',
            adjustMethod=NONE,
            initialClearance=OMIT,
            datumAxis=None,
            clearanceRegion=None
        )

    create_job(cfg['model_name'], cfg['job_name'])


def build_beam_udl(cfg):
    model = mdb.Model(name=cfg['model_name'])
    L, WY, WZ = cfg['dims']

    # Build bar as in structural bar
    s = model.ConstrainedSketch(name='sk_beam', sheetSize=max(L, WY, WZ) * 5.0)
    s.rectangle(point1=(0.0, 0.0), point2=(WZ, WY))
    part = model.Part(name='BEAM', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=s, depth=L)
    del s

    create_material_and_section_for_solid(model, part, cfg['material']['name'], cfg['material']['E'], cfg['material']['nu'])
    assign_hex_mesh(part, cfg['seed'], C3D8R)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='BEAM-1', part=part, dependent=ON)

    a.rotate(instanceList=('BEAM-1',), axisPoint=(0.0, 0.0, 0.0), axisDirection=(0.0, 1.0, 0.0), angle=90.0)
    a.translate(instanceList=('BEAM-1',), vector=(0.0, 0.0, WZ))
    a.regenerate()

    face_l = inst.faces.findAt(((0.0, WY / 2.0, WZ / 2.0),))
    face_r = inst.faces.findAt(((L, WY / 2.0, WZ / 2.0),))
    face_top = inst.faces.findAt(((L / 2.0, WY, WZ / 2.0),))

    a.Surface(name='SURF_LEFT', side1Faces=(face_l,))
    a.Surface(name='SURF_RIGHT', side1Faces=(face_r,))
    a.Surface(name='SURF_TOP', side1Faces=(face_top,))

    rp1 = a.ReferencePoint(point=(0.0, WY / 2.0, WZ / 2.0))
    rp2 = a.ReferencePoint(point=(L, WY / 2.0, WZ / 2.0))
    a.Set(name='RP-1', referencePoints=(a.referencePoints[rp1.id],))
    a.Set(name='RP-2', referencePoints=(a.referencePoints[rp2.id],))

    model.StaticStep(name=cfg['step_name'], previous='Initial', nlgeom=OFF)

    model.Coupling(
        name='COUPLE-L', controlPoint=a.sets['RP-1'], surface=a.surfaces['SURF_LEFT'],
        influenceRadius=WHOLE_SURFACE, couplingType=KINEMATIC,
        localCsys=None, u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON
    )
    model.Coupling(
        name='COUPLE-R', controlPoint=a.sets['RP-2'], surface=a.surfaces['SURF_RIGHT'],
        influenceRadius=WHOLE_SURFACE, couplingType=KINEMATIC,
        localCsys=None, u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON
    )

    # RP-1 pinned-like: U1,U2,U3,UR2,UR3 fixed
    model.DisplacementBC(
        name='BC-RP1', createStepName='Initial', region=a.sets['RP-1'],
        u1=0.0, u2=0.0, u3=0.0, ur1=UNSET, ur2=0.0, ur3=0.0
    )

    # RP-2 roller-like: U2,U3,UR2,UR3 fixed
    model.DisplacementBC(
        name='BC-RP2', createStepName='Initial', region=a.sets['RP-2'],
        u1=UNSET, u2=0.0, u3=0.0, ur1=UNSET, ur2=0.0, ur3=0.0
    )

    # Downward pressure on top surface (-Y), Pressure uses inward normal; this face normal is +Y.
    # Positive pressure therefore acts toward -Y as required.
    model.Pressure(name='LOAD-P', createStepName=cfg['step_name'], region=a.surfaces['SURF_TOP'], magnitude=cfg['pressure'])

    create_job(cfg['model_name'], cfg['job_name'])


def build_buckle_plate(cfg):
    model = mdb.Model(name=cfg['model_name'])
    a_size = cfg['size']

    sk = model.ConstrainedSketch(name='sk_plate', sheetSize=a_size * 5.0)
    sk.rectangle(point1=(0.0, 0.0), point2=(a_size, a_size))
    part = model.Part(name='PLATE', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseShell(sketch=sk)
    del sk

    mat_name = cfg['material']['name']
    model.Material(name=mat_name)
    model.materials[mat_name].Elastic(table=((cfg['material']['E'], cfg['material']['nu']),))
    sec_name = 'SEC-SHELL'
    model.HomogeneousShellSection(name=sec_name, material=mat_name, thickness=cfg['thickness'], numIntPts=5)
    part.Set(name='ALL_FACES', faces=part.faces)
    part.SectionAssignment(region=part.sets['ALL_FACES'], sectionName=sec_name)

    part.seedPart(size=cfg['seed'], deviationFactor=0.1, minSizeFactor=0.1)
    elem_type = mesh.ElemType(elemCode=S4R, elemLibrary=STANDARD)
    part.setElementType(regions=(part.faces,), elemTypes=(elem_type,))
    part.generateMesh()

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='PLATE-1', part=part, dependent=ON)

    edge_x0 = inst.edges.findAt(((0.0, a_size / 2.0, 0.0),))
    edge_x1 = inst.edges.findAt(((a_size, a_size / 2.0, 0.0),))
    edge_y0 = inst.edges.findAt(((a_size / 2.0, 0.0, 0.0),))
    edge_y1 = inst.edges.findAt(((a_size / 2.0, a_size, 0.0),))

    a.Set(name='EDGE_X0', edges=(edge_x0,))
    a.Set(name='EDGE_X1', edges=(edge_x1,))
    a.Set(name='EDGE_Y0', edges=(edge_y0,))
    a.Set(name='EDGE_Y1', edges=(edge_y1,))

    a.Surface(name='SURF_EDGE_X0', side1Edges=(edge_x0,))
    a.Surface(name='SURF_EDGE_X1', side1Edges=(edge_x1,))

    center_v = inst.vertices.findAt(((a_size / 2.0, a_size / 2.0, 0.0),))
    a.Set(name='CENTER_PT', vertices=(center_v,))

    model.BuckleStep(name=cfg['step_name'], previous='Initial', numEigen=cfg['num_eigen'])

    model.DisplacementBC(name='BC-U3-X0', createStepName='Initial', region=a.sets['EDGE_X0'], u3=0.0)
    model.DisplacementBC(name='BC-U3-X1', createStepName='Initial', region=a.sets['EDGE_X1'], u3=0.0)
    model.DisplacementBC(name='BC-U3-Y0', createStepName='Initial', region=a.sets['EDGE_Y0'], u3=0.0)
    model.DisplacementBC(name='BC-U3-Y1', createStepName='Initial', region=a.sets['EDGE_Y1'], u3=0.0)
    model.DisplacementBC(name='BC-CENTER-INPLANE', createStepName='Initial', region=a.sets['CENTER_PT'], u1=0.0, u2=0.0)

    apply_shell_edge_traction(model, 'LOAD-X0-IN', cfg['step_name'], a.surfaces['SURF_EDGE_X0'], cfg['edge_load'], (1.0, 0.0, 0.0))
    apply_shell_edge_traction(model, 'LOAD-X1-IN', cfg['step_name'], a.surfaces['SURF_EDGE_X1'], cfg['edge_load'], (-1.0, 0.0, 0.0))

    create_job(cfg['model_name'], cfg['job_name'])


def build_modal_cantilever(cfg):
    model = mdb.Model(name=cfg['model_name'])
    L, WY, WZ = cfg['dims']

    s = model.ConstrainedSketch(name='sk_modal', sheetSize=max(L, WY, WZ) * 5.0)
    s.rectangle(point1=(0.0, 0.0), point2=(WZ, WY))
    part = model.Part(name='BEAM', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=s, depth=L)
    del s

    mat_name = cfg['material']['name']
    model.Material(name=mat_name)
    model.materials[mat_name].Elastic(table=((cfg['material']['E'], cfg['material']['nu']),))
    model.materials[mat_name].Density(table=((cfg['material']['rho'],),))
    model.HomogeneousSolidSection(name='SEC-SOLID', material=mat_name, thickness=None)
    part.Set(name='ALL_CELLS', cells=part.cells)
    part.SectionAssignment(region=part.sets['ALL_CELLS'], sectionName='SEC-SOLID')

    assign_hex_mesh(part, cfg['seed'], C3D8R)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='BEAM-1', part=part, dependent=ON)
    a.rotate(instanceList=('BEAM-1',), axisPoint=(0.0, 0.0, 0.0), axisDirection=(0.0, 1.0, 0.0), angle=90.0)
    a.translate(instanceList=('BEAM-1',), vector=(0.0, 0.0, WZ))
    a.regenerate()

    face_fix = inst.faces.findAt(((0.0, WY / 2.0, WZ / 2.0),))
    a.Set(name='SET_FIX', faces=(face_fix,))

    model.FrequencyStep(name=cfg['step_name'], previous='Initial', numEigen=cfg['num_eigen'])
    model.EncastreBC(name='BC-FIX', createStepName='Initial', region=a.sets['SET_FIX'])

    create_job(cfg['model_name'], cfg['job_name'])


def build_thermal_stress(cfg):
    model = mdb.Model(name=cfg['model_name'])
    L, WY, WZ = cfg['dims']

    s = model.ConstrainedSketch(name='sk_ths', sheetSize=max(L, WY, WZ) * 5.0)
    s.rectangle(point1=(0.0, 0.0), point2=(WZ, WY))
    part = model.Part(name='BAR', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=s, depth=L)
    del s

    mat_name = cfg['material']['name']
    model.Material(name=mat_name)
    model.materials[mat_name].Elastic(table=((cfg['material']['E'], cfg['material']['nu']),))
    model.materials[mat_name].Expansion(table=((cfg['material']['alpha'],),))
    model.HomogeneousSolidSection(name='SEC-SOLID', material=mat_name, thickness=None)
    part.Set(name='ALL_CELLS', cells=part.cells)
    part.SectionAssignment(region=part.sets['ALL_CELLS'], sectionName='SEC-SOLID')

    assign_hex_mesh(part, cfg['seed'], C3D8R)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='BAR-1', part=part, dependent=ON)
    a.rotate(instanceList=('BAR-1',), axisPoint=(0.0, 0.0, 0.0), axisDirection=(0.0, 1.0, 0.0), angle=90.0)
    a.translate(instanceList=('BAR-1',), vector=(0.0, 0.0, WZ))
    a.regenerate()

    face_l = inst.faces.findAt(((0.0, WY / 2.0, WZ / 2.0),))
    face_r = inst.faces.findAt(((L, WY / 2.0, WZ / 2.0),))
    a.Set(name='SET_FIX_L', faces=(face_l,))
    a.Set(name='SET_FIX_R', faces=(face_r,))
    a.Set(name='SET_ALL_CELLS', cells=inst.cells)

    model.StaticStep(name=cfg['step_name'], previous='Initial', nlgeom=OFF)
    model.EncastreBC(name='BC-L', createStepName='Initial', region=a.sets['SET_FIX_L'])
    model.EncastreBC(name='BC-R', createStepName='Initial', region=a.sets['SET_FIX_R'])

    create_temperature_field(model, 'TEMP-INIT', 'Initial', a.sets['SET_ALL_CELLS'], cfg['temp0'])
    create_temperature_field(model, 'TEMP-STEP', cfg['step_name'], a.sets['SET_ALL_CELLS'], cfg['temp1'])

    create_job(cfg['model_name'], cfg['job_name'])


def build_heat_transient(cfg):
    model = mdb.Model(name=cfg['model_name'])
    LX, LY, LZ = cfg['dims']

    sk = model.ConstrainedSketch(name='sk_trans', sheetSize=max(LX, LY, LZ) * 5.0)
    sk.rectangle(point1=(0.0, 0.0), point2=(LX, LY))
    part = model.Part(name='BLOCK', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sk, depth=LZ)
    del sk

    mat_name = cfg['material']['name']
    model.Material(name=mat_name)
    model.materials[mat_name].Density(table=((cfg['material']['rho'],),))
    model.materials[mat_name].Conductivity(table=((cfg['material']['k'],),))
    model.materials[mat_name].SpecificHeat(table=((cfg['material']['cp'],),))
    model.HomogeneousSolidSection(name='SEC-THERM', material=mat_name, thickness=None)
    part.Set(name='ALL_CELLS', cells=part.cells)
    part.SectionAssignment(region=part.sets['ALL_CELLS'], sectionName='SEC-THERM')

    assign_hex_mesh(part, cfg['seed'], DC3D8)

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='BLOCK-1', part=part, dependent=ON)

    face_x0 = inst.faces.findAt(((0.0, LY / 2.0, LZ / 2.0),))
    a.Set(name='SET_X0', faces=(face_x0,))
    a.Set(name='SET_ALL', cells=inst.cells)

    model.HeatTransferStep(
        name=cfg['step_name'],
        previous='Initial',
        response=TRANSIENT,
        timePeriod=cfg['time_period'],
        initialInc=cfg['init_inc'],
        maxInc=cfg['max_inc']
    )

    # Initial temperature as predefined field
    create_temperature_field(model, 'TEMP-INIT', 'Initial', a.sets['SET_ALL'], cfg['temp0'])
    model.TemperatureBC(name='BC-HOT', createStepName=cfg['step_name'], region=a.sets['SET_X0'], magnitude=cfg['temp_hot'])

    create_job(cfg['model_name'], cfg['job_name'])


def build_hole_shell_tension(cfg):
    model = mdb.Model(name=cfg['model_name'])
    W = cfg['width']
    H = cfg['height']
    R = cfg['hole_d'] / 2.0

    sk = model.ConstrainedSketch(name='sk_hole', sheetSize=max(W, H) * 5.0)
    sk.rectangle(point1=(0.0, 0.0), point2=(W, H))
    sk.CircleByCenterPerimeter(center=(W / 2.0, H / 2.0), point1=(W / 2.0 + R, H / 2.0))
    part = model.Part(name='PLATE', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseShell(sketch=sk)
    del sk

    mat_name = cfg['material']['name']
    model.Material(name=mat_name)
    model.materials[mat_name].Elastic(table=((cfg['material']['E'], cfg['material']['nu']),))
    sec_name = 'SEC-SHELL'
    model.HomogeneousShellSection(name=sec_name, material=mat_name, thickness=cfg['thickness'], numIntPts=5)
    part.Set(name='ALL_FACES', faces=part.faces)
    part.SectionAssignment(region=part.sets['ALL_FACES'], sectionName=sec_name)

    hole_edge = part.edges.findAt(((W / 2.0 + R, H / 2.0, 0.0),))
    part.seedPart(size=cfg['seed_global'], deviationFactor=0.1, minSizeFactor=0.1)
    part.seedEdgeBySize(edges=(hole_edge,), size=cfg['seed_hole'], deviationFactor=0.1, minSizeFactor=0.1, constraint=FINER)

    elem_type = mesh.ElemType(elemCode=S4R, elemLibrary=STANDARD)
    part.setElementType(regions=(part.faces,), elemTypes=(elem_type,))
    part.generateMesh()

    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    inst = a.Instance(name='PLATE-1', part=part, dependent=ON)

    edge_l = inst.edges.findAt(((0.0, H / 2.0, 0.0),))
    edge_r = inst.edges.findAt(((W, H / 2.0, 0.0),))
    bl_v = inst.vertices.findAt(((0.0, 0.0, 0.0),))

    a.Surface(name='SURF_LEFT', side1Edges=(edge_l,))
    a.Surface(name='SURF_RIGHT', side1Edges=(edge_r,))
    a.Set(name='BL', vertices=(bl_v,))

    model.StaticStep(name=cfg['step_name'], previous='Initial', nlgeom=OFF)

    apply_shell_edge_traction(model, 'LOAD-L-OUT', cfg['step_name'], a.surfaces['SURF_LEFT'], cfg['edge_load'], (-1.0, 0.0, 0.0))
    apply_shell_edge_traction(model, 'LOAD-R-OUT', cfg['step_name'], a.surfaces['SURF_RIGHT'], cfg['edge_load'], (1.0, 0.0, 0.0))

    model.DisplacementBC(name='BC-BL', createStepName='Initial', region=a.sets['BL'], u1=0.0, u2=0.0, u3=0.0)

    create_job(cfg['model_name'], cfg['job_name'])


def build_model_for_task(task_id, cfg):
    cat = cfg['category']
    if cat == 'solid_tension':
        build_structural_bar_x(cfg)
    elif cat == 'heat_steady':
        build_heat_block_steady(cfg)
    elif cat == 'torsion':
        build_torsion_cylinder(cfg)
    elif cat == 'contact_block_plate':
        build_contact_block_plate(cfg)
    elif cat == 'beam_udl':
        build_beam_udl(cfg)
    elif cat == 'buckle_plate':
        build_buckle_plate(cfg)
    elif cat == 'modal_cantilever':
        build_modal_cantilever(cfg)
    elif cat == 'thermal_stress':
        build_thermal_stress(cfg)
    elif cat == 'heat_transient':
        build_heat_transient(cfg)
    elif cat == 'hole_shell_tension':
        build_hole_shell_tension(cfg)
    else:
        raise RuntimeError('Unknown category: %s' % cat)


def collect_task_specific(cfg, inst, step, last_frame, fields):
    cat = cfg['category']
    task_specific = {}

    if cat == 'solid_tension':
        s_field = repo_get_field(fields, 'S')
        u_field = repo_get_field(fields, 'U')
        if s_field is not None:
            task_specific['avg_s11_mid_x60'] = average_s11_at_x(s_field.values, inst, cfg['metrics']['mid_x'], tol=3.0)
        if u_field is not None:
            v = nearest_node_value(u_field.values, inst, cfg['metrics']['u_pt'], comp_idx=0, use_abs=True)
            task_specific['u1_free_end_center'] = v

    elif cat == 'heat_steady':
        t_field = repo_get_field(fields, 'NT11')
        if t_field is not None:
            vals = []
            for v in t_field.values:
                tv = safe_data_component(v.data, 0)
                if tv is not None:
                    vals.append(tv)
            task_specific['nt11_min'] = min(vals) if vals else None
            task_specific['nt11_max'] = max(vals) if vals else None
            task_specific['nt11_near_center_x50y25z5'] = nearest_node_value(
                t_field.values, inst, cfg['metrics']['mid_pt'], comp_idx=0, use_abs=False
            )

    elif cat == 'torsion':
        s_field = repo_get_field(fields, 'S')
        ur_field = repo_get_field(fields, 'UR')
        max_mises = None
        at_flag = False
        if s_field is not None:
            mm = -1.0
            for v in s_field.values:
                if v.mises is None:
                    continue
                if v.mises > mm:
                    mm = float(v.mises)
                    try:
                        inst_ref = v.instance if v.instance is not None else inst
                        elem = inst_ref.getElementFromLabel(v.elementLabel)
                        xs = [inst_ref.getNodeFromLabel(nid).coordinates[0] for nid in elem.connectivity]
                        ys = [inst_ref.getNodeFromLabel(nid).coordinates[1] for nid in elem.connectivity]
                        zs = [inst_ref.getNodeFromLabel(nid).coordinates[2] for nid in elem.connectivity]
                        cx = sum(xs) / float(len(xs))
                        cy = sum(ys) / float(len(ys))
                        cz = sum(zs) / float(len(zs))
                        rr = math.sqrt(cx * cx + cz * cz)
                        at_flag = (abs(cy - cfg['length']) < 3.0 and abs(rr - cfg['radius']) < 1.5)
                    except Exception:
                        at_flag = False
            if mm >= 0.0:
                max_mises = mm

        rp_rot = None
        if ur_field is not None:
            best = 0.0
            for val in ur_field.values:
                try:
                    data = val.data
                    if len(data) > 0:
                        best = max(best, max(abs(float(d)) for d in data))
                except Exception:
                    pass
            rp_rot = best

        task_specific['max_mises'] = max_mises
        task_specific['max_mises_at_free_end_outer_surface'] = bool(at_flag)
        task_specific['rp_rotation_mag'] = rp_rot

    elif cat == 'contact_block_plate':
        cpress = repo_get_field(fields, 'CPRESS')
        copen = repo_get_field(fields, 'COPEN')
        s_field = repo_get_field(fields, 'S')

        has_cpress = cpress is not None
        has_copen = copen is not None
        has_pen = False
        cpress_vals = []

        if copen is not None:
            for v in copen.values:
                try:
                    vv = safe_data_component(v.data, 0)
                    if vv is not None and vv < -1.0e-6:
                        has_pen = True
                except Exception:
                    pass

        if cpress is not None:
            for v in cpress.values:
                try:
                    cv = safe_data_component(v.data, 0)
                    if cv is not None:
                        cpress_vals.append(cv)
                except Exception:
                    pass

        max_mises = None
        if s_field is not None:
            vals = [float(v.mises) for v in s_field.values if v.mises is not None]
            if len(vals) > 0:
                max_mises = max(vals)

        task_specific['has_cpress'] = bool(has_cpress)
        task_specific['has_copen'] = bool(has_copen)
        task_specific['has_penetration'] = bool(has_pen)
        task_specific['cpress_max'] = max(cpress_vals) if len(cpress_vals) > 0 else None
        task_specific['cpress_avg'] = (sum(cpress_vals) / float(len(cpress_vals))) if len(cpress_vals) > 0 else None
        task_specific['max_mises'] = max_mises

    elif cat == 'beam_udl':
        u_field = repo_get_field(fields, 'U')
        s_field = repo_get_field(fields, 'S')
        task_specific['u2_midspan_bottom'] = None
        task_specific['max_mises_midspan'] = None
        if u_field is not None:
            task_specific['u2_midspan_bottom'] = nearest_node_value(
                u_field.values, inst, cfg['metrics']['u_pt'], comp_idx=1, use_abs=True
            )
        if s_field is not None:
            task_specific['max_mises_midspan'] = max_mises_midspan(s_field.values, inst, cfg['metrics']['mid_x'], tol=3.0)

    elif cat == 'buckle_plate':
        task_specific['first_buckle_eigenvalue'] = parse_first_eigen(step)

    elif cat == 'modal_cantilever':
        task_specific['first_natural_frequency'] = parse_first_frequency(step)

    elif cat == 'thermal_stress':
        s_field = repo_get_field(fields, 'S')
        task_specific['avg_mises_midsection'] = None
        if s_field is not None:
            mids = []
            mid_x = cfg['metrics']['mid_x']
            for v in s_field.values:
                if v.mises is None or v.elementLabel is None:
                    continue
                try:
                    elem = inst.getElementFromLabel(v.elementLabel)
                    xs = [inst.getNodeFromLabel(nid).coordinates[0] for nid in elem.connectivity]
                    cx = sum(xs) / float(len(xs))
                    if abs(cx - mid_x) <= 5.0:
                        mids.append(float(v.mises))
                except Exception:
                    pass
            if len(mids) > 0:
                task_specific['avg_mises_midsection'] = sum(mids) / float(len(mids))

    elif cat == 'heat_transient':
        t_field = repo_get_field(fields, 'NT11')
        x0_vals = []
        x5_vals = []
        if t_field is not None:
            for v in t_field.values:
                if v.nodeLabel is None:
                    continue
                try:
                    inst_ref = v.instance if v.instance is not None else inst
                    node = inst_ref.getNodeFromLabel(v.nodeLabel)
                    x = float(node.coordinates[0])
                    t = safe_data_component(v.data, 0)
                    if t is None:
                        continue
                    if abs(x - 0.0) <= 2.5:
                        x0_vals.append(t)
                    if 3.5 <= x <= 6.5:
                        x5_vals.append(t)
                except Exception:
                    pass
        task_specific['nt11_avg_x0_face'] = (sum(x0_vals) / float(len(x0_vals))) if len(x0_vals) > 0 else None
        task_specific['nt11_avg_x5_band'] = (sum(x5_vals) / float(len(x5_vals))) if len(x5_vals) > 0 else None
        task_specific['analysis_end_time'] = float(last_frame.frameValue) if last_frame is not None else None

    elif cat == 'hole_shell_tension':
        s_field = repo_get_field(fields, 'S')
        max_mises = None
        at_hole = False
        if s_field is not None:
            hole_center = (cfg['width'] / 2.0, cfg['height'] / 2.0)
            hole_r = cfg['hole_d'] / 2.0
            mm = -1.0
            for v in s_field.values:
                if v.mises is None:
                    continue
                if float(v.mises) > mm:
                    mm = float(v.mises)
                    try:
                        inst_ref = v.instance if v.instance is not None else inst
                        if v.elementLabel is not None:
                            elem = inst_ref.getElementFromLabel(v.elementLabel)
                            xs = []
                            ys = []
                            for nid in elem.connectivity:
                                nd = inst_ref.getNodeFromLabel(nid)
                                xs.append(float(nd.coordinates[0]))
                                ys.append(float(nd.coordinates[1]))
                            cx = sum(xs) / float(len(xs))
                            cy = sum(ys) / float(len(ys))
                            dist = math.sqrt((cx - hole_center[0])**2 + (cy - hole_center[1])**2)
                            at_hole = dist < hole_r * 1.5
                    except Exception:
                        at_hole = False
            if mm >= 0.0:
                max_mises = mm

        task_specific['max_mises'] = max_mises
        task_specific['max_mises_near_hole_flag'] = bool(at_hole)

    return task_specific


def extract_truth(task_id, cfg, paths):
    out = {
        'meta': {
            'task_id': task_id,
            'job_name': cfg['job_name'],
            'model_name': cfg['model_name'],
            'part_names': [],
            'unit_system': 'N-mm-MPa',
            'generated_at': now_iso(),
        },
        'files': {
            'cae_path': paths['cae'],
            'odb_path': paths['odb'],
            'truth_path': paths['truth'],
            'cae_exists': os.path.exists(paths['cae']),
            'odb_exists': os.path.exists(paths['odb']),
        },
        'model_counts': {
            'node_count': None,
            'element_count': None,
            'instance_count': None,
        },
        'step_info': {
            'step_names': [],
            'target_step': cfg['step_name'],
            'frame_count': None,
            'last_frame_value': None,
        },
        'field_availability': {
            'U': False,
            'S': False,
            'RF': False,
            'NT11': False,
            'UR': False,
            'CPRESS': False,
            'COPEN': False,
        },
        'task_specific': {},
    }

    try:
        openMdb(pathName=paths['cae'])
        model = mdb.models[cfg['model_name']] if cfg['model_name'] in mdb.models else None
        if model is not None:
            out['meta']['part_names'] = sorted(model.parts.keys())
    except Exception:
        pass

    odb = None
    try:
        odb = openOdb(path=paths['odb'], readOnly=True)
        out['step_info']['step_names'] = list(odb.steps.keys())
        out['model_counts']['instance_count'] = len(odb.rootAssembly.instances)

        inst = get_main_instance(odb.rootAssembly)
        if inst is not None:
            out['model_counts']['node_count'] = len(inst.nodes)
            out['model_counts']['element_count'] = len(inst.elements)

        step_key = find_step_case_insensitive(odb.steps, cfg['step_name'])
        if step_key is None and len(odb.steps) > 0:
            step_key = list(odb.steps.keys())[0]
        if step_key is None:
            return out

        step = odb.steps[step_key]
        out['step_info']['target_step'] = step_key
        out['step_info']['frame_count'] = len(step.frames)
        if len(step.frames) > 0:
            out['step_info']['last_frame_value'] = float(step.frames[-1].frameValue)

        if len(step.frames) == 0 or inst is None:
            return out

        last_frame = step.frames[-1]
        fo = last_frame.fieldOutputs

        for k in out['field_availability'].keys():
            out['field_availability'][k] = (k in fo.keys())

        out['task_specific'] = collect_task_specific(cfg, inst, step, last_frame, fo)

    except Exception:
        out['task_specific'] = {
            'error': traceback.format_exc().splitlines()[-1]
        }
    finally:
        try:
            if odb is not None:
                odb.close()
        except Exception:
            pass

    return out


def run_task(task_id):
    if task_id not in TASKS:
        raise RuntimeError('Unsupported task id: %s' % task_id)

    cfg = TASKS[task_id]
    work_dir = ADMIN_DESKTOP
    ensure_dir(work_dir)
    os.chdir(work_dir)

    paths = job_paths(work_dir, cfg['job_name'])

    clean_job_files(work_dir, cfg['job_name'])

    if cfg['model_name'] in mdb.models.keys():
        try:
            del mdb.models[cfg['model_name']]
        except Exception:
            pass

    build_model_for_task(task_id, cfg)

    # Save CAE
    try:
        mdb.saveAs(pathName=os.path.splitext(paths['cae'])[0])
    except Exception:
        mdb.saveAs(pathName=paths['cae'])

    # Submit + wait
    mdb.jobs[cfg['job_name']].submit(consistencyChecking=OFF)
    mdb.jobs[cfg['job_name']].waitForCompletion()

    truth = extract_truth(task_id, cfg, paths)

    with open(paths['truth'], 'w') as f:
        json.dump(truth, f, indent=2, sort_keys=True)

    print('>>> TASK: ' + task_id)
    print('>>> CAE: ' + paths['cae'])
    print('>>> ODB: ' + paths['odb'])
    print('>>> TRUTH: ' + paths['truth'])


if __name__ == '__main__':
    run_task('task-20')
