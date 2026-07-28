from abaqus import *
from abaqusConstants import *
import mesh
import os
import regionToolset

Mdb()
model = mdb.Model(name="TSVCellModel")
sketch = model.ConstrainedSketch(name="TSVCellProfile", sheetSize=100.0)
sketch.rectangle(point1=(0.0,0.0), point2=(0.12,0.12))
part = model.Part(name="TSVCell", dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=sketch, depth=0.3)
material = model.Material(name="TSVCellMaterial")
material.Elastic(table=((90000.0,0.3),))
model.HomogeneousSolidSection(name="TSVCellSection", material="TSVCellMaterial")
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName="TSVCellSection")
assembly = model.rootAssembly
instance = assembly.Instance(name="TSVCell-1", part=part, dependent=ON)
model.StaticStep(name="LoadStep", previous="Initial", nlgeom=OFF)
fixed = instance.faces.findAt(((0.06,0.06,0.0),))
loaded = instance.faces.findAt(((0.06,0.06,0.3),))
model.DisplacementBC(name="BottomFixed", createStepName="Initial",
    region=regionToolset.Region(faces=fixed), u1=0.0, u2=0.0, u3=0.0)
model.Pressure(name="TopPressure", createStepName="LoadStep",
    region=regionToolset.Region(side1Faces=loaded), magnitude=2.0)
part.seedPart(size=0.03, deviationFactor=0.1, minSizeFactor=0.1)
part.setElementType(regions=(part.cells,),
    elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),))
part.generateMesh()
job = mdb.Job(name="TSVCellJob", model="TSVCellModel", description="Homogenized TSV unit cell")
job.writeInput(consistencyChecking=OFF)
mdb.saveAs(pathName=os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "TSVCell.cae"))
