from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="PassivationModel")
sketch = model.ConstrainedSketch(name="PassivationProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(10.0,2.0))
part = model.Part(name="Passivation", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.02)
material = model.Material(name="PassivationMaterial")
material.Elastic(table=((70000.0,0.24),))
model.HomogeneousSolidSection(name="PassivationSection", material="PassivationMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="PassivationSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="Passivation-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((5.0,1.0,0.0),))
loaded = instance.faces.findAt(((5.0,1.0,0.02),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=2.0)
part.seedPart(size=0.5, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="PassivationJob", model="PassivationModel", description="Passivation-film strip")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "Passivation.cae"))
