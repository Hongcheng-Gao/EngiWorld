# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_05_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_05_ansys', '/PREP7', 'ET,1,SOLID185', 'MP,EX,1,70000', 'MP,PRXY,1,0.33', 'MP,DENS,1,2.7e-09', 'MP,ALPX,1,2.3e-05', 'TREF,20', 'BLOCK,0,120,0,8,0,8', 'VATT,1,,1', 'ESIZE,6', 'VMESH,ALL', 'ALLSEL,ALL', 'FINISH', '/SOLU', 'OUTRES,ALL,ALL', 'ANTYPE,STATIC', 'NSEL,S,LOC,X,0', 'D,ALL,UX,0', 'D,ALL,UY,0', 'D,ALL,UZ,0', 'NSEL,S,LOC,X,120', 'D,ALL,UX,0', 'D,ALL,UY,0', 'D,ALL,UZ,0', 'ALLSEL,ALL', 'BFUNIF,TEMP,100', 'ALLSEL,ALL', 'SOLVE', 'FINISH', '/SAVE,gt_task_05_ansys,db', '/POST1', 'SET,LAST', 'FINISH']
METRICS = {'axial_stress': 0.0, 'reaction_force_optional': 0.0}

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
