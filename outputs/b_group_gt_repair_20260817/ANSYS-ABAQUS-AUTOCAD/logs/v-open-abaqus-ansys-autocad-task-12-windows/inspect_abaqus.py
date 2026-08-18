from abaqus import mdb
from odbAccess import openOdb
import json
import os


desktop = r"C:\Users\user\Desktop"
stem = "plate_v12_fixed"
openMdb(pathName=os.path.join(desktop, stem + ".cae"))
model = mdb.models["AxisymmetricPlateV12"]
part = model.parts["Plate"]
nodes = [tuple(float(v) for v in node.coordinates) for node in part.nodes]
assembly = model.rootAssembly
model.keywordBlock.synchVersions(storeNodesAndElements=False)
keyword_text = "\n".join(str(block) for block in model.keywordBlock.sieBlocks)

def region_nodes(region):
    values = []
    try:
        for group in region.nodes:
            for node in group:
                values.append(tuple(float(v) for v in node.coordinates))
    except Exception:
        pass
    return values

evidence = {
    "bbox": {
        "x": [min(p[0] for p in nodes), max(p[0] for p in nodes)],
        "y": [min(p[1] for p in nodes), max(p[1] for p in nodes)],
    },
    "node_count": len(part.nodes),
    "element_count": len(part.elements),
    "element_types": sorted(set(str(element.type) for element in part.elements)),
    "elastic_table": model.materials["Steel"].elastic.table,
    "boundary_sets": {
        "AxisEdge": region_nodes(assembly.sets["AxisEdge"]),
        "OuterEdge": region_nodes(assembly.sets["OuterEdge"]),
    },
    "boundary_condition_names": list(model.boundaryConditions.keys()),
    "load_names": list(model.loads.keys()),
    "surface_names": list(assembly.surfaces.keys()),
    "keyword_block": keyword_text,
}

odb = openOdb(path=os.path.join(desktop, stem + ".odb"), readOnly=True)
try:
    step = odb.steps["StaticPressure"]
    frame = step.frames[-1]
    displacements = [tuple(float(v) for v in value.data) for value in frame.fieldOutputs["U"].values]
    stresses = [float(value.mises) for value in frame.fieldOutputs["S"].values]
    evidence["odb"] = {
        "job_status": str(odb.diagnosticData.jobStatus),
        "frame_count": len(step.frames),
        "min_u2": min(value[1] for value in displacements),
        "max_displacement": max((value[0] ** 2 + value[1] ** 2) ** 0.5
                                for value in displacements),
        "max_mises": max(stresses),
    }
finally:
    odb.close()

with open(os.path.join(desktop, "v12_abaqus_inspect.json"), "w") as stream:
    json.dump(evidence, stream, indent=2, sort_keys=True)
print(json.dumps(evidence["odb"]))
