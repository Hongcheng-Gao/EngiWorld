from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="HeatSpreaderModel")
sketch = model.ConstrainedSketch(name="HeatSpreaderProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(30.0,30.0))
part = model.Part(name="HeatSpreader", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=1.5)
material = model.Material(name="HeatSpreaderMaterial")
material.Elastic(table=((110000.0,0.34),))
model.HomogeneousSolidSection(name="HeatSpreaderSection", material="HeatSpreaderMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="HeatSpreaderSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="HeatSpreader-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((15.0,15.0,0.0),))
loaded = instance.faces.findAt(((15.0,15.0,1.5),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=900.0)
part.seedPart(size=2.0, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="HeatSpreaderJob", model="HeatSpreaderModel", description="Copper heat-spreader coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "HeatSpreader.cae"))
