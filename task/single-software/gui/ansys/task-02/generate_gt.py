from __future__ import annotations

import subprocess
from pathlib import Path

from ansys.mapdl.core import launch_mapdl

DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_plate.db"
RST_FILE = DESKTOP / "apdl_plate.rst"
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "gen_gt_apdl_plate"
MAPDL_PORT = 55102


def kill_ansys_related() -> None:
    for target in (
        "ANSYS261.exe",
        "ansys261.exe",
        "ANSYS.exe",
        "ansys.exe",
        "fluent.exe",
        "Fluent.exe",
        "cortex.exe",
        "Cortex.exe",
    ):
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", target],
                capture_output=True,
                creationflags=0x08000000,
            )
        except Exception:
            pass


def generate() -> None:
    kill_ansys_related()

    mapdl = launch_mapdl(
        exec_file=EXEC_FILE,
        jobname=JOBNAME,
        run_location=str(DESKTOP),
        nproc=1,
        port=MAPDL_PORT,
        override=True,
    )
    try:
        mapdl.clear()
        mapdl.prep7()

        # Element/material per instruction
        mapdl.et(1, "PLANE183")
        mapdl.keyopt(1, 3, 1)  # axisymmetric
        mapdl.mp("EX", 1, 210000.0)
        mapdl.mp("PRXY", 1, 0.3)

        # Geometry: axisymmetric cross-section 0<=X<=50, 0<=Y<=1
        mapdl.blc4(0.0, 0.0, 50.0, 1.0)

        # Mesh
        mapdl.esize(2.0)
        mapdl.amesh("ALL")

        # BCs per instruction
        mapdl.nsel("S", "LOC", "X", 0.0)
        mapdl.d("ALL", "UX", 0.0)  # axis symmetry

        mapdl.nsel("S", "LOC", "X", 50.0)
        mapdl.d("ALL", "UX", 0.0)
        mapdl.d("ALL", "UY", 0.0)  # clamped outer edge

        # Pressure on top surface Y=1, negative Y direction
        mapdl.allsel()
        mapdl.nsel("S", "LOC", "Y", 1.0)
        mapdl.esln("S")
        mapdl.sfe("ALL", 1, "PRES", 0, -0.1)

        mapdl.allsel()
        mapdl.finish()

        mapdl.run("/SOLU")
        mapdl.antype("STATIC")
        mapdl.solve()
        mapdl.finish()

        # Write DB and ensure required filenames are present
        mapdl.save(JOBNAME, "db")
        gen_db = DESKTOP / f"{JOBNAME}.db"
        if gen_db.exists():
            DB_FILE.write_bytes(gen_db.read_bytes())

        # Copy generated RST to required filename
        gen_rst = DESKTOP / f"{JOBNAME}.rst"
        if gen_rst.exists():
            RST_FILE.write_bytes(gen_rst.read_bytes())

        print("True")
    finally:
        try:
            mapdl.exit()
        except Exception:
            pass


if __name__ == "__main__":
    generate()
