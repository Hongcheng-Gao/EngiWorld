from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="SolderCouponModel")
sketch = model.ConstrainedSketch(name="SolderCouponProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(0.5,0.5))
part = model.Part(name="SolderCoupon", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.4)
material = model.Material(name="SolderCouponMaterial")
material.Elastic(table=((50000.0,0.36),))
model.HomogeneousSolidSection(name="SolderCouponSection", material="SolderCouponMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="SolderCouponSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="SolderCoupon-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((0.25,0.25,0.0),))
loaded = instance.faces.findAt(((0.25,0.25,0.4),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=8.0)
part.seedPart(size=0.1, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="SolderCouponJob", model="SolderCouponModel", description="Solder-joint shear coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "SolderCoupon.cae"))
