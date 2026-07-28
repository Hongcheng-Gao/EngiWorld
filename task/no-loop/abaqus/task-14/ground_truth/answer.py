from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="RDLLineModel")
sketch = model.ConstrainedSketch(name="RDLLineProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(12.0,0.08))
part = model.Part(name="RDLLine", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.015)
material = model.Material(name="RDLLineMaterial")
material.Elastic(table=((110000.0,0.34),))
model.HomogeneousSolidSection(name="RDLLineSection", material="RDLLineMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="RDLLineSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="RDLLine-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((6.0,0.04,0.0),))
loaded = instance.faces.findAt(((6.0,0.04,0.015),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=5.0)
part.seedPart(size=0.4, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="RDLLineJob", model="RDLLineModel", description="Redistribution-layer line")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "RDLLine.cae"))
