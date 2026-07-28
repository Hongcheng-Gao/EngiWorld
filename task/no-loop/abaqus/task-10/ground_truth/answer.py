from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="GlassInterposerModel")
sketch = model.ConstrainedSketch(name="GlassInterposerProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(25.0,25.0))
part = model.Part(name="GlassInterposer", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.7)
material = model.Material(name="GlassInterposerMaterial")
material.Elastic(table=((72000.0,0.22),))
model.HomogeneousSolidSection(name="GlassInterposerSection", material="GlassInterposerMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="GlassInterposerSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="GlassInterposer-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((12.5,12.5,0.0),))
loaded = instance.faces.findAt(((12.5,12.5,0.7),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=150.0)
part.seedPart(size=1.5, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="GlassInterposerJob", model="GlassInterposerModel", description="Glass interposer coupon")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "GlassInterposer.cae"))
