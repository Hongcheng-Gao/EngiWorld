from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="LowKLayerModel")
sketch = model.ConstrainedSketch(name="LowKLayerProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(5.0,5.0))
part = model.Part(name="LowKLayer", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.05)
material = model.Material(name="LowKLayerMaterial")
material.Elastic(table=((7000.0,0.25),))
model.HomogeneousSolidSection(name="LowKLayerSection", material="LowKLayerMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="LowKLayerSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="LowKLayer-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((2.5,2.5,0.0),))
loaded = instance.faces.findAt(((2.5,2.5,0.05),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=12.0)
part.seedPart(size=0.25, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="LowKLayerJob", model="LowKLayerModel", description="Low-k dielectric coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "LowKLayer.cae"))
