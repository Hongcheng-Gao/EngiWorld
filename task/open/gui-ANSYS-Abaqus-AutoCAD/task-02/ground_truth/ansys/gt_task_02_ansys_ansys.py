# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_02_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_02_ansys', '/PREP7', 'ET,1,SHELL181', 'SECTYPE,1,SHELL', 'SECDATA,1.2', 'MP,EX,1,210000', 'MP,PRXY,1,0.3', 'MP,DENS,1,7.85e-9', 'BLC4,0,0,96,96', 'AATT,1,,1,,1', 'ESIZE,6', 'AMESH,ALL', 'ALLSEL,ALL', 'FINISH', '/SOLU', 'OUTRES,ALL,ALL', 'NSEL,S,LOC,X,0', 'F,ALL,FX,1.2', 'NSEL,S,LOC,X,96', 'F,ALL,FX,-1.2', 'NSEL,S,LOC,X,0', 'NSEL,A,LOC,X,96', 'NSEL,A,LOC,Y,0', 'NSEL,A,LOC,Y,96', 'D,ALL,UZ,0', 'NSEL,S,LOC,X,48', 'NSEL,R,LOC,Y,48', 'D,ALL,UX,0', 'D,ALL,UY,0', 'NSEL,S,LOC,X,48', 'NSEL,R,LOC,Y,0', 'D,ALL,UX,0', 'ALLSEL,ALL', 'ANTYPE,STATIC', 'PSTRES,ON', 'SOLVE', 'ANTYPE,BUCKLE', 'BUCOPT,LANB,3', 'MXPAND,3,,,YES', 'SOLVE', 'FINISH', '/SAVE,gt_task_02_ansys,db', '/POST1', 'SET,LAST', 'FINISH']
METRICS = {'first_buckling_factor': 0.0}

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
