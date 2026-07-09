# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import math
import os
import traceback
from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset
from odbAccess import openOdb

STEM = 'gt_task_14_abaqus'
DESKTOP = 'C:\\Users\\user\\Desktop'
DIMS = {'x': (0.0, 50.0), 'y': (0.0, 20.0), 'z': (0.0, 20.0)}
KIND = 'thermal'
EXPECTED = ['NT11']
METRICS = {'probe_temperature': 0.0, 'time_value': 0.0}

def box_span(axis):
    lo, hi = DIMS[axis]
    return float(lo), float(hi), abs(float(hi) - float(lo))

def main():
    cae_path = os.path.join(DESKTOP, STEM + '.cae')
    odb_path = os.path.join(DESKTOP, STEM + '.odb')
    try:
        if mdb.models.has_key('Model-1'):
            del mdb.models['Model-1']
    except Exception:
        pass
    model = mdb.Model(name='Model-1')
    x0, x1, xs = box_span('x')
    y0, y1, ys = box_span('y')
    z0, z1, zs = box_span('z')
    sketch = model.ConstrainedSketch(name='Sketch-Block', sheetSize=max(xs, ys, zs, 1.0) * 4.0)
    sketch.rectangle(point1=(x0, y0), point2=(x1, y1))
    part = model.Part(name='Part-Block', dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sketch, depth=zs)
    del model.sketches['Sketch-Block']
    material = model.Material(name='Steel')
    if KIND == 'thermal':
        material.Conductivity(table=((45.0,),))
        material.Density(table=((7.85e-09,),))
        material.SpecificHeat(table=((480000000.0,),))
        elem_code = DC3D8
    else:
        material.Elastic(table=((210000.0, 0.3),))
        material.Density(table=((7.85e-09,),))
        try:
            material.Expansion(table=((1.2e-5,),))
        except Exception:
            pass
        elem_code = C3D8R
    section = model.HomogeneousSolidSection(name='Section-1', material='Steel', thickness=None)
    part.SectionAssignment(region=regionToolset.Region(cells=part.cells), sectionName='Section-1')
    part.seedPart(size=max(1.0, max(xs, ys, zs) / 5.0), deviationFactor=0.1, minSizeFactor=0.1)
    part.setElementType(regions=(part.cells,), elemTypes=(mesh.ElemType(elemCode=elem_code, elemLibrary=STANDARD),))
    part.generateMesh()
    asm = model.rootAssembly
    asm.DatumCsysByDefault(CARTESIAN)
    inst = asm.Instance(name='Part-Block-1', part=part, dependent=ON)
    eps = max(xs, ys, zs, 1.0) * 1.0e-5
    all_region = regionToolset.Region(cells=inst.cells)
    fixed_faces = inst.faces.getByBoundingBox(xMin=x0-eps, xMax=x0+eps, yMin=y0-eps, yMax=y1+eps, zMin=-eps, zMax=zs+eps)
    load_faces = inst.faces.getByBoundingBox(xMin=x1-eps, xMax=x1+eps, yMin=y0-eps, yMax=y1+eps, zMin=-eps, zMax=zs+eps)
    fixed_region = regionToolset.Region(faces=fixed_faces)
    load_surface = asm.Surface(name='LOAD_SURFACE', side1Faces=load_faces)
    if KIND == 'thermal':
        model.HeatTransferStep(name='Step-Thermal', previous='Initial', timePeriod=1.0, deltmx=100.0)
        model.TemperatureBC(name='BC-Hot', createStepName='Step-Thermal', region=fixed_region, magnitude=100.0)
        cold_faces = inst.faces.getByBoundingBox(xMin=x1-eps, xMax=x1+eps, yMin=y0-eps, yMax=y1+eps, zMin=-eps, zMax=zs+eps)
        model.TemperatureBC(name='BC-Cold', createStepName='Step-Thermal', region=regionToolset.Region(faces=cold_faces), magnitude=20.0)
        try:
            model.BodyHeatFlux(name='Body-Heat', createStepName='Step-Thermal', region=all_region, magnitude=0.001)
        except Exception:
            pass
        step_name = 'Step-Thermal'
        variables = ('NT', 'HFL')
    elif KIND == 'modal':
        model.FrequencyStep(name='Step-Frequency', previous='Initial', numEigen=5)
        model.DisplacementBC(name='BC-Fixed', createStepName='Initial', region=fixed_region, u1=0.0, u2=0.0, u3=0.0)
        step_name = 'Step-Frequency'
        variables = ('U',)
    elif KIND == 'buckling':
        model.StaticStep(name='Step-Preload', previous='Initial')
        model.BuckleStep(name='Step-Buckle', previous='Step-Preload', numEigen=3)
        model.DisplacementBC(name='BC-Fixed', createStepName='Initial', region=fixed_region, u1=0.0, u2=0.0, u3=0.0)
        model.Pressure(name='Load-Pressure', createStepName='Step-Preload', region=load_surface, magnitude=0.1)
        step_name = 'Step-Buckle'
        variables = ('U',)
    else:
        model.StaticStep(name='Step-Static', previous='Initial')
        model.DisplacementBC(name='BC-Fixed', createStepName='Initial', region=fixed_region, u1=0.0, u2=0.0, u3=0.0)
        model.Pressure(name='Load-Pressure', createStepName='Step-Static', region=load_surface, magnitude=0.1)
        if KIND == 'thermal_structural':
            try:
                model.Temperature(name='Predefined-Temp', createStepName='Initial', region=all_region, distributionType=UNIFORM, crossSectionDistribution=CONSTANT_THROUGH_THICKNESS, magnitudes=(80.0,))
            except Exception:
                pass
        step_name = 'Step-Static'
        variables = ('U', 'S')
    try:
        model.fieldOutputRequests['F-Output-1'].setValues(variables=variables)
    except Exception:
        pass
    job = mdb.Job(name=STEM, model='Model-1', type=ANALYSIS, explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE)
    mdb.saveAs(pathName=cae_path)
    job.submit()
    job.waitForCompletion()
    mdb.saveAs(pathName=cae_path)
    values = dict(METRICS)
    try:
        odb = openOdb(odb_path, readOnly=True)
        frames = []
        for step_key in odb.steps.keys():
            frames.extend(list(odb.steps[step_key].frames))
        frame = frames[-1] if frames else None
        scalar = 0.0
        if frame is not None:
            if frame.fieldOutputs.has_key('U'):
                scalar = max([math.sqrt(sum([float(x) * float(x) for x in v.data])) for v in frame.fieldOutputs['U'].values] or [0.0])
            if frame.fieldOutputs.has_key('S'):
                mises = []
                for v in frame.fieldOutputs['S'].values:
                    try:
                        mises.append(float(v.mises))
                    except Exception:
                        pass
                if mises:
                    scalar = max(mises)
            if frame.fieldOutputs.has_key('NT11'):
                temps = [float(v.data) for v in frame.fieldOutputs['NT11'].values]
                if temps:
                    scalar = max(temps)
        for key in values.keys():
            values[key] = float(scalar)
        odb.close()
    except Exception:
        pass
    with open(os.path.join(DESKTOP, 'metrics.json'), 'w') as f:
        json.dump(values, f, indent=2, sort_keys=True)

if __name__ == '__main__':
    try:
        main()
    except Exception:
        with open(os.path.join(DESKTOP, STEM + '_abaqus_error.txt'), 'w') as f:
            f.write(traceback.format_exc())
        raise
