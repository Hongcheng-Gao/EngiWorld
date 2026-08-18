from __future__ import print_function

import os

from abaqus import Mdb
from abaqusConstants import (
    C3D8R,
    CARTESIAN,
    DEFORMABLE_BODY,
    FINER,
    FRICTIONLESS,
    GLOBAL,
    HARD,
    OFF,
    ON,
    SELF,
    STANDARD,
    THREE_D,
)
import mesh
import regionToolset


desktop = r"C:\Users\user\Desktop"
os.chdir(desktop)
Mdb()
model = mdb.models["Model-1"]

block_sketch = model.ConstrainedSketch(name="BlockSketch", sheetSize=120.0)
block_sketch.rectangle(point1=(0.0, 0.0), point2=(20.0, 20.0))
block = model.Part(name="BLOCK", dimensionality=THREE_D, type=DEFORMABLE_BODY)
block.BaseSolidExtrude(sketch=block_sketch, depth=30.0)
del model.sketches["BlockSketch"]

plate_sketch = model.ConstrainedSketch(name="PlateSketch", sheetSize=160.0)
plate_sketch.rectangle(point1=(0.0, 0.0), point2=(100.0, 100.0))
plate = model.Part(name="PLATE", dimensionality=THREE_D, type=DEFORMABLE_BODY)
plate.BaseSolidExtrude(sketch=plate_sketch, depth=5.0)
del model.sketches["PlateSketch"]

steel = model.Material(name="Steel")
steel.Elastic(table=((210000.0, 0.3),))
model.HomogeneousSolidSection(name="SteelSection", material="Steel", thickness=None)
block.SectionAssignment(
    region=regionToolset.Region(cells=block.cells),
    sectionName="SteelSection",
)
plate.SectionAssignment(
    region=regionToolset.Region(cells=plate.cells),
    sectionName="SteelSection",
)

element_type = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD)
block.setElementType(regions=(block.cells,), elemTypes=(element_type,))
block.seedPart(size=3.0, deviationFactor=0.1, minSizeFactor=0.1)
block.generateMesh()
plate.setElementType(regions=(plate.cells,), elemTypes=(element_type,))
plate.seedPart(size=5.0, deviationFactor=0.1, minSizeFactor=0.1)
plate.generateMesh()

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)
block_instance = assembly.Instance(name="BLOCK-1", part=block, dependent=ON)
plate_instance = assembly.Instance(name="PLATE-1", part=plate, dependent=ON)
assembly.translate(instanceList=("BLOCK-1",), vector=(40.0, 40.0, 5.0))
assembly.regenerate()

model.StaticStep(name="Step-1", previous="Initial", nlgeom=ON)

plate_bottom = plate_instance.faces.findAt(((50.0, 50.0, 0.0),))
model.EncastreBC(
    name="BC-PLATE-BOT",
    createStepName="Initial",
    region=regionToolset.Region(faces=plate_bottom),
)

block_top = block_instance.faces.findAt(((50.0, 50.0, 35.0),))
model.Pressure(
    name="LOAD-P",
    createStepName="Step-1",
    region=regionToolset.Region(side1Faces=block_top),
    magnitude=10.0,
)

contact_property = model.ContactProperty("IntProp-1")
contact_property.NormalBehavior(
    pressureOverclosure=HARD,
    allowSeparation=ON,
)
contact_property.TangentialBehavior(formulation=FRICTIONLESS)
model.ContactStd(name="GeneralContact", createStepName="Initial")
general_contact = model.interactions["GeneralContact"]
general_contact.includedPairs.setValuesInStep(stepName="Initial", useAllstar=ON)
general_contact.contactPropertyAssignments.appendInStep(
    stepName="Initial",
    assignments=((GLOBAL, SELF, "IntProp-1"),),
)

job_name = "Job-Contact"
for suffix in (".odb", ".lck", ".log", ".msg", ".sta", ".com", ".prt", ".sim"):
    path = os.path.join(desktop, job_name + suffix)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
mdb.Job(name=job_name, model="Model-1", numCpus=1, numDomains=1)
mdb.saveAs(pathName=os.path.join(desktop, job_name + ".cae"))
mdb.jobs[job_name].submit(consistencyChecking=OFF)
mdb.jobs[job_name].waitForCompletion()
mdb.saveAs(pathName=os.path.join(desktop, job_name + ".cae"))
print("rebuilt " + job_name)
