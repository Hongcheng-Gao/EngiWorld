from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="UnderfillModel")
sketch = model.ConstrainedSketch(name="UnderfillProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(12.0,12.0))
part = model.Part(name="Underfill", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.3)
material = model.Material(name="UnderfillMaterial")
material.Elastic(table=((8500.0,0.33),))
model.HomogeneousSolidSection(name="UnderfillSection", material="UnderfillMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="UnderfillSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="Underfill-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((6.0,6.0,0.0),))
loaded = instance.faces.findAt(((6.0,6.0,0.3),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=120.0)
part.seedPart(size=0.4, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="UnderfillJob", model="UnderfillModel", description="Underfill compression coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "Underfill.cae"))
