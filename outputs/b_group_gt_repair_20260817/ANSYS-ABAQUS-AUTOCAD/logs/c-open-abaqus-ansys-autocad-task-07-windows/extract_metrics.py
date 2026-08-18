from __future__ import print_function

import json
import math
import os

from odbAccess import openOdb


desktop = r"C:\Users\user\Desktop"
odb_path = os.path.join(desktop, "Job-Torsion-A.odb")
metrics_path = os.path.join(desktop, "metrics.json")

odb = openOdb(odb_path, readOnly=True)
try:
    frames = []
    for step_name in odb.steps.keys():
        frames.extend(list(odb.steps[step_name].frames))
    frame = frames[-1]

    coordinates = {}
    coordinates_by_label = {}
    ymax = None
    for instance_name in odb.rootAssembly.instances.keys():
        instance = odb.rootAssembly.instances[instance_name]
        for node in instance.nodes:
            xyz = tuple(float(value) for value in node.coordinates)
            coordinates[(instance_name, int(node.label))] = xyz
            coordinates_by_label[int(node.label)] = xyz
            if ymax is None or xyz[1] > ymax:
                ymax = xyz[1]

    twist_values = []
    for value in frame.fieldOutputs["U"].values:
        instance = getattr(value, "instance", None)
        instance_name = getattr(instance, "name", None)
        xyz = coordinates.get((instance_name, int(value.nodeLabel)))
        if xyz is None:
            xyz = coordinates_by_label.get(int(value.nodeLabel))
        if xyz is None or abs(xyz[1] - ymax) > 1.0e-4:
            continue
        x, _, z = xyz
        radius2 = x * x + z * z
        if radius2 <= 1.0e-8:
            continue
        ux, _, uz = [float(component) for component in value.data[:3]]
        twist_values.append((z * ux - x * uz) / radius2)

    mises_values = []
    for value in frame.fieldOutputs["S"].values:
        try:
            mises_values.append(abs(float(value.mises)))
        except Exception:
            pass

    twist_angle = sum(twist_values) / float(len(twist_values))
    max_stress = max(mises_values)
    metrics = {
        "twist_angle": abs(twist_angle),
        "max_stress": max_stress,
    }
    with open(metrics_path, "w") as stream:
        json.dump(metrics, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(metrics, sort_keys=True))
finally:
    odb.close()
