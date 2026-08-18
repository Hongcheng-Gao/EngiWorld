# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import math
import os

from odbAccess import openOdb


DESKTOP = r"C:\Users\user\Desktop"
ODB_PATH = os.path.join(DESKTOP, "Task18_PunchPlate.odb")
METRICS_PATH = os.path.join(DESKTOP, "metrics.json")
EVIDENCE_PATH = os.path.join(DESKTOP, "task18_metrics_lf_evidence.json")


def scalar(value):
    try:
        return float(value.data)
    except Exception:
        return float(value.data[0])


def main():
    odb = openOdb(path=ODB_PATH, readOnly=True)
    try:
        step = odb.steps["IndentationStep"]
        frame = step.frames[-1]
        pressure_names = [
            name for name in frame.fieldOutputs.keys()
            if str(name).strip().upper().startswith("CPRESS")
        ]
        if len(pressure_names) != 1:
            raise ValueError("unexpected CPRESS fields: %s" % pressure_names)
        pressure_values = [scalar(value) for value in frame.fieldOutputs[pressure_names[0]].values]
        punch_rp = odb.rootAssembly.nodeSets["PUNCH_RP_NODE"]
        displacement_values = frame.fieldOutputs["U"].getSubset(region=punch_rp).values
        reaction_values = frame.fieldOutputs["RF"].getSubset(region=punch_rp).values
        metrics = {
            "max_contact_pressure": max(pressure_values),
            "punch_vertical_displacement": float(displacement_values[0].data[1]),
            "punch_reaction_force": abs(
                math.fsum(float(value.data[1]) for value in reaction_values)
            ),
            "max_mises_stress": max(
                float(value.mises)
                for value in frame.fieldOutputs["S"].values
                if hasattr(value, "mises")
            ),
        }
        evidence = {
            "status": str(odb.diagnosticData.jobStatus),
            "frames": len(step.frames),
            "metrics": metrics,
            "writer": "binary JSON payload with explicit LF terminator",
        }
    finally:
        odb.close()

    payload = json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    payload = payload.replace("\r\n", "\n")
    with open(METRICS_PATH, "wb") as handle:
        handle.write(payload.encode("ascii"))
    with open(EVIDENCE_PATH, "wb") as handle:
        evidence_payload = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").replace("\r\n", "\n")
        handle.write(evidence_payload.encode("ascii"))
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
