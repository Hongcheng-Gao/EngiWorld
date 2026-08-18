from __future__ import print_function

import json
import os

from abaqus import openMdb


desktop = r"C:\Users\user\Desktop"
openMdb(pathName=os.path.join(desktop, "Job-Contact.cae"))
report = {}
for model_name in mdb.models.keys():
    model = mdb.models[model_name]
    parts = {}
    for part_name in model.parts.keys():
        part = model.parts[part_name]
        parts[part_name] = {
            "nodes": len(part.nodes),
            "elements": len(part.elements),
            "element_types": sorted(set(str(element.type) for element in part.elements)),
        }
    repositories = {}
    for repository_name in (
        "interactions",
        "interactionProperties",
        "loads",
        "boundaryConditions",
        "constraints",
        "steps",
        "materials",
    ):
        repository = getattr(model, repository_name, None)
        if repository is None:
            repositories[repository_name] = []
        else:
            repositories[repository_name] = [
                {
                    "key": str(key),
                    "class": repository[key].__class__.__name__,
                    "type": str(getattr(repository[key], "type", "")),
                }
                for key in repository.keys()
            ]
    report[str(model_name)] = {
        "parts": parts,
        "repositories": repositories,
    }
report_text = json.dumps(report, indent=2, sort_keys=True)
with open(os.path.join(desktop, "inspect_cae_report.json"), "w") as stream:
    stream.write(report_text)
    stream.write("\n")
print(report_text)
