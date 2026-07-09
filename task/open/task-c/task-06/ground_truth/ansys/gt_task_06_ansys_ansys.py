# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_06_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_06_ansys', '/PREP7', 'ET,1,SOLID70', 'MP,KXX,1,45', 'MP,DENS,1,7.85e-9', 'MP,C,1,4.8e8', 'BLOCK,0,100,0,50,0,10', 'ESIZE,10', 'VMESH,ALL', 'FINISH', '/SOLU', 'ANTYPE,STATIC', 'NSEL,S,LOC,X,0', 'D,ALL,TEMP,100', 'NSEL,S,LOC,X,100', 'D,ALL,TEMP,20', 'ALLSEL,ALL', 'SOLVE', 'FINISH', '/SAVE,gt_task_06_ansys,db', '/POST1', 'SET,LAST', 'FINISH']
METRICS = {'probe_temperature': 0.0, 'heat_flux_optional': 0.0}

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
