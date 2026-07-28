from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="MoldCompoundModel")
sketch = model.ConstrainedSketch(name="MoldCompoundProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(18.0,18.0))
part = model.Part(name="MoldCompound", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=2.0)
material = model.Material(name="MoldCompoundMaterial")
material.Elastic(table=((22000.0,0.3),))
model.HomogeneousSolidSection(name="MoldCompoundSection", material="MoldCompoundMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="MoldCompoundSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="MoldCompound-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((9.0,9.0,0.0),))
loaded = instance.faces.findAt(((9.0,9.0,2.0),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=500.0)
part.seedPart(size=1.0, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="MoldCompoundJob", model="MoldCompoundModel", description="Mold-compound package block")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "MoldCompound.cae"))
