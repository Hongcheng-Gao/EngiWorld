from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="CopperInterposerModel")
sketch = model.ConstrainedSketch(name="CopperInterposerProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(20.0,12.0))
part = model.Part(name="CopperInterposer", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.8)
material = model.Material(name="CopperInterposerMaterial")
material.Elastic(table=((110000.0,0.34),))
model.HomogeneousSolidSection(name="CopperInterposerSection", material="CopperInterposerMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="CopperInterposerSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="CopperInterposer-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((10.0,6.0,0.0),))
loaded = instance.faces.findAt(((10.0,6.0,0.8),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=200.0)
part.seedPart(size=1.0, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="CopperInterposerJob", model="CopperInterposerModel", description="Copper interposer bending coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "CopperInterposer.cae"))
