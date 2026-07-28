from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="SiCDieModel")
sketch = model.ConstrainedSketch(name="SiCDieProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(6.0,6.0))
part = model.Part(name="SiCDie", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.35)
material = model.Material(name="SiCDieMaterial")
material.Elastic(table=((410000.0,0.19),))
model.HomogeneousSolidSection(name="SiCDieSection", material="SiCDieMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="SiCDieSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="SiCDie-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((3.0,3.0,0.0),))
loaded = instance.faces.findAt(((3.0,3.0,0.35),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=300.0)
part.seedPart(size=0.35, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="SiCDieJob", model="SiCDieModel", description="Silicon-carbide die coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "SiCDie.cae"))
