# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
import traceback

import numpy as np
from ansys.mapdl.core import launch_mapdl


STEM = "gt_task_06_ansys"
WORKDIR = os.environ.get("TASK06_WORKDIR", r"C:\Users\user\Desktop")
ANSYS_EXEC = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"

COMMANDS = [
    "/CLEAR,NOSTART",
    "/FILNAME,%s" % STEM,
    "/UNITS,MPA",
    "/PREP7",
    "ET,1,SOLID70",
    "MP,KXX,1,45",
    "MP,DENS,1,7.85E-9",
    "MP,C,1,4.5E8",
    "BLOCK,0,60,0,18,0,12",
    "VATT,1,,1",
    "MSHAPE,0,3D",
    "MSHKEY,1",
    "ESIZE,4",
    "VMESH,ALL",
    "ALLSEL,ALL",
    "FINISH",
    "/SOLU",
    "ANTYPE,TRANS,NEW",
    "TRNOPT,FULL",
    "TIMINT,ON,THERM",
    "AUTOTS,ON",
    "KBC,1",
    "OUTRES,ALL,ALL",
    "IC,ALL,TEMP,25",
    "NSEL,S,LOC,X,0",
    "D,ALL,TEMP,95",
    "ALLSEL,ALL",
    "TIME,300",
    "DELTIM,2,,15",
    "CUTCONTROL,TEMPLIMIT,10",
    "SOLVE",
    "FINISH",
]


def average(values):
    return float(np.mean(values)) if len(values) else None


def main():
    if not os.path.isdir(WORKDIR):
        os.makedirs(WORKDIR)
    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC,
            jobname=STEM,
            run_location=WORKDIR,
            nproc=1,
            override=True,
            cleanup_on_exit=False,
            start_timeout=180,
        )
        mapdl.ignore_errors = True
        for command in COMMANDS:
            mapdl.run(command)
        mapdl.save(STEM, "db")
        mapdl.post1()
        mapdl.file(os.path.join(WORKDIR, STEM), "rth")
        mapdl.set("LAST")
        nodes = np.asarray(mapdl.mesh.nodes, dtype=float)
        temperatures = np.asarray(mapdl.post_processing.nodal_temperature(), dtype=float)
        if len(nodes) != len(temperatures):
            raise RuntimeError("Node and temperature arrays do not align")
        heated = temperatures[np.isclose(nodes[:, 0], 0.0, atol=1.0e-6)]
        band = temperatures[(nodes[:, 0] >= 4.0) & (nodes[:, 0] <= 6.0)]
        far = temperatures[np.isclose(nodes[:, 0], 60.0, atol=1.0e-6)]
        metrics = {
            "heated_face_average_temperature": average(heated),
            "x_approximately_5mm_band_average_temperature": average(band),
            "final_probe_temperature": average(band),
            "far_face_average_temperature": average(far),
            "temperature_min": float(np.min(temperatures)),
            "temperature_max": float(np.max(temperatures)),
            "time_value": float(mapdl.get_value("ACTIVE", 0, "SET", "TIME")),
            "node_count": int(len(nodes)),
            "element_count": int(mapdl.get_value("ELEM", 0, "COUNT")),
        }
        with open(os.path.join(WORKDIR, "metrics.json"), "w") as stream:
            json.dump(metrics, stream, indent=2, sort_keys=True)
        with open(os.path.join(WORKDIR, STEM + "_generation.json"), "w") as stream:
            json.dump(
                {
                    "ansys_exec": ANSYS_EXEC,
                    "commands": COMMANDS,
                    "db": os.path.join(WORKDIR, STEM + ".db"),
                    "rth": os.path.join(WORKDIR, STEM + ".rth"),
                    "metrics": metrics,
                },
                stream,
                indent=2,
                sort_keys=True,
            )
        print(json.dumps(metrics, indent=2, sort_keys=True))
    except Exception:
        with open(os.path.join(WORKDIR, STEM + "_error.txt"), "w") as stream:
            stream.write(traceback.format_exc())
        raise
    finally:
        if mapdl is not None:
            try:
                mapdl.exit(force=True)
            except TypeError:
                mapdl.exit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
