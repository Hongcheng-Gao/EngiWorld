from abaqus import mdb
from abaqusConstants import (
    ANALYSIS, AXISYMMETRIC, CAX8R, DEFORMABLE_BODY, DEFAULT, FINER, OFF, ON, QUAD,
    SINGLE, STANDARD, STRUCTURED, UNSET,
)
import mesh
import os


desktop = r"C:\Users\user\Desktop"
stem = "plate_v12_fixed"
os.chdir(desktop)
model = mdb.Model(name="AxisymmetricPlateV12")
sketch = model.ConstrainedSketch(name="PlateProfile", sheetSize=120.0)
sketch.ConstructionLine(point1=(0.0, -10.0), point2=(0.0, 10.0))
sketch.rectangle(point1=(0.0, 0.0), point2=(50.0, 1.0))
part = model.Part(name="Plate", dimensionality=AXISYMMETRIC, type=DEFORMABLE_BODY)
part.BaseShell(sketch=sketch)

material = model.Material(name="Steel")
material.Elastic(table=((210000.0, 0.3),))
model.HomogeneousSolidSection(name="PlateSection", material="Steel", thickness=None)
part.SectionAssignment(region=part.Set(name="PlateCells", faces=part.faces),
                       sectionName="PlateSection")
part.setMeshControls(regions=part.faces, elemShape=QUAD, technique=STRUCTURED)
part.setElementType(regions=(part.faces,),
                    elemTypes=(mesh.ElemType(elemCode=CAX8R, elemLibrary=STANDARD),))
part.seedPart(size=2.0, deviationFactor=0.1, minSizeFactor=0.1)
part.generateMesh()

assembly = model.rootAssembly
instance = assembly.Instance(name="Plate-1", part=part, dependent=ON)
axis_edge = instance.edges.findAt(((0.0, 0.5, 0.0),))
outer_edge = instance.edges.findAt(((50.0, 0.5, 0.0),))
top_edge = instance.edges.findAt(((25.0, 1.0, 0.0),))
model.StaticStep(name="StaticPressure", previous="Initial")
model.DisplacementBC(name="AxisSymmetry", createStepName="Initial",
                     region=assembly.Set(name="AxisEdge", edges=axis_edge),
                     u1=0.0, u2=UNSET)
model.DisplacementBC(name="OuterClamp", createStepName="Initial",
                     region=assembly.Set(name="OuterEdge", edges=outer_edge),
                     u1=0.0, u2=0.0)
top_surface = assembly.Surface(name="TopSurfaceY1", side1Edges=top_edge)
model.Pressure(name="TopPressure", createStepName="StaticPressure",
               region=top_surface, magnitude=0.1)

cae_path = os.path.join(desktop, stem + ".cae")
mdb.saveAs(pathName=cae_path)
job = mdb.Job(name=stem, model=model.name, type=ANALYSIS,
              explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE,
              multiprocessingMode=DEFAULT, numCpus=1, numDomains=1)
job.submit(consistencyChecking=OFF)
job.waitForCompletion()
mdb.save()
print("generated %s with %d elements and %d nodes" %
      (stem, len(part.elements), len(part.nodes)))
