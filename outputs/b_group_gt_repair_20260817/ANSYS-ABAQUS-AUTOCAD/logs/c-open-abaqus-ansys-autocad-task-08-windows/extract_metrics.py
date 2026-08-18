from __future__ import print_function

import json
import math
import os

from odbAccess import openOdb


desktop = r"C:\Users\user\Desktop"
odb = openOdb(os.path.join(desktop, "Job-Contact.odb"), readOnly=True)
try:
    frames = []
    for step_name in odb.steps.keys():
        frames.extend(list(odb.steps[step_name].frames))
    frame = frames[-1]

    contact_values = []
    for key in frame.fieldOutputs.keys():
        if str(key).upper().startswith("CPRESS"):
            for value in frame.fieldOutputs[key].values:
                try:
                    contact_values.append(abs(float(value.data)))
                except Exception:
                    pass

    vertical_values = []
    for value in frame.fieldOutputs["U"].values:
        try:
            vertical_values.append(abs(float(value.data[2])))
        except Exception:
            pass

    reaction_values = []
    if "RF" in frame.fieldOutputs.keys():
        for value in frame.fieldOutputs["RF"].values:
            try:
                reaction_values.append(abs(float(value.data[2])))
            except Exception:
                pass

    metrics = {
        "max_contact_pressure": max(contact_values),
        "vertical_displacement": max(vertical_values),
        "reaction_force": sum(reaction_values),
    }
    with open(os.path.join(desktop, "metrics.json"), "w") as stream:
        json.dump(metrics, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(metrics, sort_keys=True))
finally:
    odb.close()
