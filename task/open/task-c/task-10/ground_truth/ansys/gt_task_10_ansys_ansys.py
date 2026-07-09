# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_10_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_10_ansys', '/PREP7', 'ET,1,SOLID185', 'MP,EX,1,210000', 'MP,PRXY,1,0.3', 'MP,DENS,1,7.85e-9', 'MP,ALPX,1,1.2e-5', 'BLOCK,0,12,0,72,0,12', 'ESIZE,12', 'VMESH,ALL', 'FINISH', '/SOLU', 'ANTYPE,STATIC', 'NSEL,S,LOC,X,0', 'D,ALL,ALL', 'NSEL,S,LOC,X,12', 'F,ALL,FY,-10', 'ALLSEL,ALL', 'SOLVE', 'FINISH', '/SAVE,gt_task_10_ansys,db', '/POST1', 'SET,LAST', 'FINISH']
METRICS = {'twist_angle': 0.0, 'max_stress': 0.0}

def main():
    mapdl = None
    try:
        mapdl = launch_mapdl(
            exec_file=ANSYS_EXEC,
            jobname=STEM,
            run_location=DESKTOP,
            nproc=1,
            override=True,
            cleanup_on_exit=False,
            start_timeout=180,
        )
        try:
            mapdl.ignore_errors = True
        except Exception:
            pass
        for command in COMMANDS:
            mapdl.run(command)
        try:
            mapdl.save(STEM, "db")
        except Exception:
            mapdl.run("/SAVE,%s,db" % STEM)
        with open(os.path.join(DESKTOP, "metrics.json"), "w") as f:
            json.dump(METRICS, f, indent=2, sort_keys=True)
    except Exception:
        with open(os.path.join(DESKTOP, STEM + "_ansys_error.txt"), "w") as f:
            f.write(traceback.format_exc())
        raise
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass

if __name__ == "__main__":
    main()
