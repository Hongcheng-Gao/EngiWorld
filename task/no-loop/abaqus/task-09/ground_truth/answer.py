from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="GaNDieModel")
sketch = model.ConstrainedSketch(name="GaNDieProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(4.0,4.0))
part = model.Part(name="GaNDie", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.25)
material = model.Material(name="GaNDieMaterial")
material.Elastic(table=((300000.0,0.23),))
model.HomogeneousSolidSection(name="GaNDieSection", material="GaNDieMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="GaNDieSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="GaNDie-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((2.0,2.0,0.0),))
loaded = instance.faces.findAt(((2.0,2.0,0.25),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=180.0)
part.seedPart(size=0.25, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="GaNDieJob", model="GaNDieModel", description="Gallium-nitride die coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "GaNDie.cae"))
