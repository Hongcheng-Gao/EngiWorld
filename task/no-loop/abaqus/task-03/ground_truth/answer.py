from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="DieAttachModel")
sketch = model.ConstrainedSketch(name="DieAttachProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(8.0,8.0))
part = model.Part(name="DieAttach", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.15)
material = model.Material(name="DieAttachMaterial")
material.Elastic(table=((5000.0,0.35),))
model.HomogeneousSolidSection(name="DieAttachSection", material="DieAttachMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="DieAttachSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="DieAttach-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((4.0,4.0,0.0),))
loaded = instance.faces.findAt(((4.0,4.0,0.15),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=80.0)
part.seedPart(size=0.25, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="DieAttachJob", model="DieAttachModel", description="Epoxy die-attach shear coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "DieAttach.cae"))
