# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os

from abaqus import Mdb, mdb
from abaqusConstants import C3D8R, CARTESIAN, DEFORMABLE_BODY, HEX, STANDARD, STRUCTURED, THREE_D
import mesh
import regionToolset


DESKTOP = r"C:\Users\user\Desktop"
INIT_PATH = os.path.join(DESKTOP, "task08_block_plate_init.cae")


def make_block(model, name, width, depth, height, mesh_size):
    sketch = model.ConstrainedSketch(name=name + "Sketch", sheetSize=max(width, depth) * 2.0)
    sketch.rectangle(point1=(0.0, 0.0), point2=(width, depth))
    part = model.Part(name=name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
    part.BaseSolidExtrude(sketch=sketch, depth=height)
    del model.sketches[sketch.name]
    part.SectionAssignment(
        region=regionToolset.Region(cells=part.cells),
        sectionName="SteelSection",
    )
    part.setMeshControls(regions=part.cells, elemShape=HEX, technique=STRUCTURED)
    part.setElementType(
        regions=(part.cells,),
        elemTypes=(mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD),),
    )
    part.seedPart(size=mesh_size, deviationFactor=0.1, minSizeFactor=0.1)
    part.generateMesh()
    return part


def main():
    os.chdir(DESKTOP)
    Mdb()
    mdb.models.changeKey(fromName="Model-1", toName="BlockPlate3D")
    model = mdb.models["BlockPlate3D"]

    steel = model.Material(name="Steel")
    steel.Elastic(table=((210000.0, 0.3),))
    model.HomogeneousSolidSection(name="SteelSection", material="Steel", thickness=None)

    plate = make_block(model, "Plate", 24.0, 24.0, 3.0, 3.0)
    block = make_block(model, "Block", 8.0, 8.0, 8.0, 2.0)

    plate.Surface(name="PLATE_TOP", side1Faces=plate.faces.findAt(((12.0, 12.0, 3.0),)))
    plate.Set(name="PLATE_BOTTOM", nodes=plate.nodes.getByBoundingBox(zMin=-1.0e-6, zMax=1.0e-6))
    block.Surface(name="BLOCK_BOTTOM", side1Faces=block.faces.findAt(((4.0, 4.0, 0.0),)))
    block.Surface(name="BLOCK_TOP", side1Faces=block.faces.findAt(((4.0, 4.0, 8.0),)))
    block.Set(
        name="BLOCK_ANCHOR",
        nodes=block.nodes.getByBoundingBox(
            xMin=-1.0e-6,
            xMax=1.0e-6,
            yMin=-1.0e-6,
            yMax=1.0e-6,
            zMin=8.0 - 1.0e-6,
            zMax=8.0 + 1.0e-6,
        ),
    )
    block.Set(
        name="BLOCK_GUIDE",
        nodes=block.nodes.getByBoundingBox(
            xMin=8.0 - 1.0e-6,
            xMax=8.0 + 1.0e-6,
            yMin=-1.0e-6,
            yMax=1.0e-6,
            zMin=8.0 - 1.0e-6,
            zMax=8.0 + 1.0e-6,
        ),
    )
    block.Set(name="BLOCK_TOP_NODES", nodes=block.nodes.getByBoundingBox(zMin=8.0 - 1.0e-6, zMax=8.0 + 1.0e-6))

    assembly = model.rootAssembly
    assembly.DatumCsysByDefault(CARTESIAN)
    plate_instance = assembly.Instance(name="Plate-1", part=plate, dependent=True)
    block_instance = assembly.Instance(name="Block-1", part=block, dependent=True)
    assembly.translate(instanceList=(block_instance.name,), vector=(8.0, 8.0, 3.0))
    assembly.regenerate()

    mdb.saveAs(pathName=INIT_PATH)
    evidence = {
        "status": "init_created",
        "model": model.name,
        "parts": list(model.parts.keys()),
        "steps": list(model.steps.keys()),
        "interactions": list(model.interactions.keys()),
        "loads": list(model.loads.keys()),
        "jobs": list(mdb.jobs.keys()),
        "plate_nodes": len(plate.nodes),
        "plate_elements": len(plate.elements),
        "block_nodes": len(block.nodes),
        "block_elements": len(block.elements),
        "total_nodes": len(plate.nodes) + len(block.nodes),
    }
    with open(os.path.join(DESKTOP, "task08_init_build.json"), "w") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
