from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="AluminaSubstrateModel")
sketch = model.ConstrainedSketch(name="AluminaSubstrateProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(20.0,20.0))
part = model.Part(name="AluminaSubstrate", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=1.0)
material = model.Material(name="AluminaSubstrateMaterial")
material.Elastic(table=((300000.0,0.21),))
model.HomogeneousSolidSection(name="AluminaSubstrateSection", material="AluminaSubstrateMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="AluminaSubstrateSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="AluminaSubstrate-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((10.0,10.0,0.0),))
loaded = instance.faces.findAt(((10.0,10.0,1.0),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=350.0)
part.seedPart(size=1.0, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="AluminaSubstrateJob", model="AluminaSubstrateModel", description="Alumina package substrate")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "AluminaSubstrate.cae"))
