# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_03_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_03_ansys', '/PREP7', 'ET,1,SOLID185', 'MP,EX,1,210000', 'MP,PRXY,1,0.3', 'MP,DENS,1,7.8e-09', 'BLOCK,0,420,0,12,0,10', 'VATT,1,,1', 'ESIZE,12', 'VMESH,ALL', 'ALLSEL,ALL', 'FINISH', '/SOLU', 'OUTRES,ALL,ALL', 'NSEL,S,LOC,X,0', 'D,ALL,ALL,0', 'ALLSEL,ALL', 'ANTYPE,MODAL', 'MODOPT,LANB,4', 'MXPAND,4,,,YES', 'SOLVE', 'FINISH', '/SAVE,gt_task_03_ansys,db', '/POST1', 'SET,LAST', 'FINISH']
METRICS = {'first_frequency': 0.0, 'mode_count': 0.0}

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
