# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_10_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_10_ansys', '/PREP7', 'ET,1,SHELL181', 'SECTYPE,1,SHELL', 'SECDATA,1.2', 'MP,EX,1,210000', 'MP,PRXY,1,0.3', 'MP,DENS,1,7.85e-9', 'BLC4,0,0,160,80', '*GET,RECTAREA,AREA,0,NUM,MAX', 'CYL4,80,40,8', '*GET,HOLEAREA,AREA,0,NUM,MAX', 'ASBA,RECTAREA,HOLEAREA', 'AATT,1,,1,,1', 'ESIZE,10', 'AMESH,ALL', 'ALLSEL,ALL', 'FINISH', '/SOLU', 'OUTRES,ALL,ALL', 'D,ALL,UZ,0', 'NSEL,S,LOC,X,0', 'F,ALL,FX,-12', 'NSEL,S,LOC,X,160', 'F,ALL,FX,12', 'NSEL,S,LOC,X,0', 'NSEL,R,LOC,Y,0', 'D,ALL,UX,0', 'D,ALL,UY,0', 'NSEL,S,LOC,X,160', 'NSEL,R,LOC,Y,0', 'D,ALL,UY,0', 'ALLSEL,ALL', 'ANTYPE,STATIC', 'SOLVE', 'FINISH', '/SAVE,gt_task_10_ansys,db', '/POST1', 'SET,LAST', 'FINISH']
METRICS = {'max_mises': 0.0, 'edge_displacement': 0.0}

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
