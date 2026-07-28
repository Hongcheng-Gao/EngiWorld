from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="SiliconDieModel")
sketch = model.ConstrainedSketch(name="SiliconDieProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(10.0,10.0))
part = model.Part(name="SiliconDie", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.5)
material = model.Material(name="SiliconDieMaterial")
material.Elastic(table=((130000.0,0.28),))
model.HomogeneousSolidSection(name="SiliconDieSection", material="SiliconDieMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="SiliconDieSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="SiliconDie-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((5.0,5.0,0.0),))
loaded = instance.faces.findAt(((5.0,5.0,0.5),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=5.0)
part.seedPart(size=0.5, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="SiliconDieJob", model="SiliconDieModel", description="Silicon die compression coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "SiliconDie.cae"))
