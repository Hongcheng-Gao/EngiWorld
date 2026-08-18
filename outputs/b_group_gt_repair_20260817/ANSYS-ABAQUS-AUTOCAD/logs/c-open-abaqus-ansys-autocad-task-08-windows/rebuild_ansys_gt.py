import json
import math
import os
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "Job-Contact-ANSYS"
ansys_exe = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
mapdl = launch_mapdl(
    exec_file=ansys_exe,
    jobname=stem,
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="meba",
    start_timeout=180,
)
try:
    mapdl.clear("NOSTART")
    mapdl.filname(stem)
    mapdl.prep7()
    mapdl.et(1, "SOLID185")
    mapdl.et(2, "TARGE170")
    mapdl.et(3, "CONTA174")
    mapdl.keyopt(3, 2, 0)
    mapdl.keyopt(3, 4, 0)
    mapdl.keyopt(3, 5, 0)
    mapdl.mp("EX", 1, 210000.0)
    mapdl.mp("PRXY", 1, 0.3)

    mapdl.block(0.0, 100.0, 0.0, 100.0, 0.0, 5.0)
    mapdl.vatt(1, 1, 1)
    mapdl.esize(5.0)
    mapdl.vmesh(1)

    mapdl.block(40.0, 60.0, 40.0, 60.0, 5.0, 35.0)
    mapdl.vatt(1, 1, 1)
    mapdl.esize(3.0)
    mapdl.vmesh(2)

    mapdl.allsel("ALL")
    mapdl.vsel("S", "VOLU", "", 1)
    mapdl.aslv("S")
    mapdl.asel("R", "LOC", "Z", 5.0)
    mapdl.nsla("S", 1)
    mapdl.type(2)
    mapdl.real(1)
    mapdl.esurf()

    mapdl.allsel("ALL")
    mapdl.vsel("S", "VOLU", "", 2)
    mapdl.aslv("S")
    mapdl.asel("R", "LOC", "Z", 5.0)
    mapdl.nsla("S", 1)
    mapdl.type(3)
    mapdl.real(1)
    mapdl.esurf()

    mapdl.allsel("ALL")
    mapdl.nsel("S", "LOC", "Z", 0.0)
    mapdl.d("ALL", "ALL", 0.0)
    mapdl.allsel("ALL")
    mapdl.vsel("S", "VOLU", "", 2)
    mapdl.aslv("S")
    mapdl.asel("R", "LOC", "Z", 35.0)
    mapdl.sfa("ALL", 1, "PRES", 10.0)

    mapdl.allsel("ALL")
    mapdl.finish()
    mapdl.slashsolu()
    mapdl.antype("STATIC")
    mapdl.nlgeom("ON")
    mapdl.autots("ON")
    mapdl.nsubst(10, 100, 1)
    mapdl.neqit(50)
    solve_output = mapdl.solve()
    (desktop / (stem + "_solve.txt")).write_text(str(solve_output), encoding="utf-8")
    if "VERIFICATION RUN ONLY" in str(solve_output).upper():
        raise RuntimeError("ANSYS solved under verification license")
    mapdl.finish()
    mapdl.save(stem, "db")

    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    mapdl.etable("CPRES", "CONT", "PRES")
    mapdl.run("*GET,MAXCP,ETAB,0,MAX,CPRES")
    max_contact_pressure = abs(float(mapdl.parameters["MAXCP"]))

    result = mapdl.result
    last = int(result.nsets) - 1
    _, displacement = result.nodal_solution(last)
    vertical_displacement = max(abs(float(row[2])) for row in displacement)
    reaction, _, dof = result.nodal_reaction_forces(last)
    reaction_force = sum(
        abs(float(value))
        for value, component in zip(reaction, dof)
        if int(component) == 3
    )
    metrics = {
        "max_contact_pressure": max_contact_pressure,
        "vertical_displacement": vertical_displacement,
        "reaction_force": reaction_force,
    }
    if not all(math.isfinite(float(value)) for value in metrics.values()):
        raise RuntimeError("non-finite result metrics: %r" % metrics)
    (desktop / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, sort_keys=True))
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
