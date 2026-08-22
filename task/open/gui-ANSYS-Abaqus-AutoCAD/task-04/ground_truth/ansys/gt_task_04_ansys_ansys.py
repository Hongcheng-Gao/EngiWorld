# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import math
import os
import traceback
from ansys.mapdl.core import launch_mapdl

STEM = 'gt_task_04_ansys'
DESKTOP = 'C:\\Users\\user\\Desktop'
ANSYS_EXEC = 'C:\\Program Files\\ANSYS Inc\\v261\\ansys\\bin\\winx64\\ANSYS261.exe'
COMMANDS = ['/CLEAR,NOSTART', '/FILNAME,gt_task_04_ansys', '/PREP7', 'ET,1,SOLID185', 'MP,EX,1,210000', 'MP,PRXY,1,0.3', 'MP,DENS,1,7.85e-09', 'MP,ALPX,1,1.2e-05', 'TREF,20', 'BLOCK,0,100,0,10,0,10', 'VATT,1,,1', 'ESIZE,5', 'VMESH,ALL', 'ALLSEL,ALL', 'FINISH', '/SOLU', 'OUTRES,ALL,ALL', 'ANTYPE,STATIC', 'NSEL,S,LOC,X,0', 'D,ALL,UX,0', 'D,ALL,UY,0', 'D,ALL,UZ,0', 'NSEL,S,LOC,X,100', 'D,ALL,UX,0', 'D,ALL,UY,0', 'D,ALL,UZ,0', 'ALLSEL,ALL', 'BFUNIF,TEMP,120', 'ALLSEL,ALL', 'SOLVE', 'FINISH', '/SAVE,gt_task_04_ansys,db', '/POST1', 'SET,LAST', 'FINISH']

def extract_metrics(mapdl):
    result = mapdl.result
    _, stress = result.nodal_stress(-1)
    axial_values = [abs(float(row[0])) for row in stress if math.isfinite(float(row[0]))]
    if not axial_values:
        raise RuntimeError('no finite axial stress values were written to the result')
    axial_stress = max(axial_values)
    nnum, dof, forces = result.nodal_reaction_forces(-1)
    coordinates = {int(node): tuple(float(v) for v in xyz[:3])
                   for node, xyz in zip(result.mesh.nnum, result.mesh.nodes)}
    x_values = [xyz[0] for xyz in coordinates.values()]
    x_min, x_max = min(x_values), max(x_values)
    end_sums = []
    for end_x in (x_min, x_max):
        total = sum(float(value) for node, code, value in zip(nnum, dof, forces)
                    if int(code) == 1 and int(node) in coordinates
                    and abs(coordinates[int(node)][0] - end_x) <= 0.1)
        end_sums.append(abs(total))
    reaction = max(end_sums)
    if axial_stress <= 0.0 or reaction <= 0.0:
        raise RuntimeError('invalid thermal metrics stress=%s reaction=%s' % (axial_stress, reaction))
    return {'axial_stress': axial_stress, 'reaction_force_optional': reaction}

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
        metrics = extract_metrics(mapdl)
        with open(os.path.join(DESKTOP, "metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2, sort_keys=True)
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
