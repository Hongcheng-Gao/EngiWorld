# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from abaqus import Mdb, mdb
from abaqusConstants import (
    ANALYTIC_RIGID_SURFACE,
    CARTESIAN,
    CPE4R,
    DEFORMABLE_BODY,
    QUAD,
    STANDARD,
    STRUCTURED,
    TWO_D_PLANAR,
)
import mesh
import regionToolset


DESKTOP = r"C:\Users\user\Desktop"
OUTPUT = os.path.join(DESKTOP, "Task18_PunchPlate_GT.cae")


def main():
    os.chdir(DESKTOP)
    Mdb()
    mdb.models.changeKey(fromName="Model-1", toName="PunchPlate2D")
    model = mdb.models["PunchPlate2D"]
    polymer = model.Material(name="EngineeringPolymer")
    polymer.Elastic(table=((2100.0, 0.35),))
    model.HomogeneousSolidSection(
        name="PlateSection",
        material="EngineeringPolymer",
        thickness=None,
    )

    plate_sketch = model.ConstrainedSketch(name="PlateSketch", sheetSize=80.0)
    plate_sketch.rectangle(point1=(-20.0, -12.0), point2=(20.0, 0.0))
    plate = model.Part(name="Plate", dimensionality=TWO_D_PLANAR, type=DEFORMABLE_BODY)
    plate.BaseShell(sketch=plate_sketch)
    del model.sketches[plate_sketch.name]
    plate.SectionAssignment(region=regionToolset.Region(faces=plate.faces), sectionName="PlateSection")
    plate.setMeshControls(regions=plate.faces, elemShape=QUAD, technique=STRUCTURED)
    plate.setElementType(
        regions=(plate.faces,),
        elemTypes=(mesh.ElemType(elemCode=CPE4R, elemLibrary=STANDARD),),
    )
    plate.seedPart(size=1.0, deviationFactor=0.1, minSizeFactor=0.1)
    plate.generateMesh()
    plate.Surface(name="PLATE_TOP", side1Edges=plate.edges.findAt(((0.0, 0.0, 0.0),)))
    plate.Set(
        name="PLATE_BOTTOM",
        nodes=plate.nodes.getByBoundingBox(yMin=-12.0 - 1.0e-6, yMax=-12.0 + 1.0e-6),
    )

    punch_sketch = model.ConstrainedSketch(name="PunchSketch", sheetSize=20.0)
    punch_sketch.Line(point1=(-5.0, 0.0), point2=(0.0, -5.0))
    punch_sketch.Line(point1=(0.0, -5.0), point2=(5.0, 0.0))
    punch = model.Part(name="Punch", dimensionality=TWO_D_PLANAR, type=ANALYTIC_RIGID_SURFACE)
    punch.AnalyticRigidSurf2DPlanar(sketch=punch_sketch)
    del model.sketches[punch_sketch.name]
    reference = punch.ReferencePoint(point=(0.0, 0.0, 0.0))
    punch.Set(name="PUNCH_RP", referencePoints=(punch.referencePoints[reference.id],))
    punch.Surface(name="PUNCH_CONTACT", side2Edges=punch.edges)

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    assembly.Instance(name="Plate-1", part=plate, dependent=True)
    punch_instance = assembly.Instance(name="Punch-1", part=punch, dependent=True)
    assembly.translate(instanceList=(punch_instance.name,), vector=(0.0, 5.0, 0.0))
    assembly.regenerate()
    mdb.saveAs(pathName=OUTPUT)
    print("saved V-shaped analytical punch candidate")


if __name__ == "__main__":
    main()
