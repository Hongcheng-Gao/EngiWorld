from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="LeadframeModel")
sketch = model.ConstrainedSketch(name="LeadframeProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(15.0,1.0))
part = model.Part(name="Leadframe", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.2)
material = model.Material(name="LeadframeMaterial")
material.Elastic(table=((117000.0,0.34),))
model.HomogeneousSolidSection(name="LeadframeSection", material="LeadframeMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="LeadframeSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="Leadframe-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((7.5,0.5,0.0),))
loaded = instance.faces.findAt(((7.5,0.5,0.2),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=25.0)
part.seedPart(size=0.5, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="LeadframeJob", model="LeadframeModel", description="Leadframe finger bending")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "Leadframe.cae"))
