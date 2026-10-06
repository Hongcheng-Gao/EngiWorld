from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ansys.mapdl.core import launch_mapdl


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_plastic.db"
RST_FILE = DESKTOP / "apdl_plastic.rst"
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "gen_gt_apdl_plastic"
MAPDL_PORT = 55113


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

    for name in (".__tmp__.inp", ".__tmp__.out"):
        path = DESKTOP / name
        try:
            if path.exists():
                path.unlink()
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

        # Element/material/plasticity per instruction.
        mapdl.et(1, "SOLID185")
        mapdl.mp("EX", 1, 210000.0)
        mapdl.mp("PRXY", 1, 0.3)
        mapdl.tb("BISO", 1, "", 1)
        mapdl.tbdata(1, 250.0, 0.0)

        # Build a Y-axis cylinder by revolving a Y-radial rectangle.
        # This matches the instruction definition:
        # radius=5 mm, length 0<=Y<=50 mm.
        mapdl.k(1, 0.0, 0.0, 0.0)
        mapdl.k(2, 5.0, 0.0, 0.0)
        mapdl.k(3, 5.0, 50.0, 0.0)
        mapdl.k(4, 0.0, 50.0, 0.0)
        mapdl.k(100, 0.0, 0.0, 0.0)
        mapdl.k(101, 0.0, 50.0, 0.0)
        mapdl.a(1, 2, 3, 4)
        mapdl.vrotat("ALL", "", "", "", "", "", 100, 101, 360, 24)

        # Mesh size 3 mm (tet free mesh for this topology).
        mapdl.run("ESIZE,3")
        mapdl.run("MSHAPE,1,3D")
        mapdl.run("MSHKEY,0")
        mapdl.vmesh("ALL")

        # BCs: fixed face at Y=0, displacement UY=2 at Y=50.
        mapdl.allsel()
        mapdl.nsel("S", "LOC", "Y", 0.0, 0.0)
        mapdl.d("ALL", "UX", 0.0)
        mapdl.d("ALL", "UY", 0.0)
        mapdl.d("ALL", "UZ", 0.0)

        mapdl.allsel()
        mapdl.nsel("S", "LOC", "Y", 50.0, 50.0)
        mapdl.d("ALL", "UY", 2.0)

        mapdl.allsel()
        mapdl.finish()

        mapdl.slashsolu()
        mapdl.antype("STATIC")
        mapdl.nlgeom("ON")
        mapdl.autots("ON")
        mapdl.nsubst(80, 100, 50)
        mapdl.solve()
        mapdl.finish()

        mapdl.save(JOBNAME, "db")

        job_db = DESKTOP / f"{JOBNAME}.db"
        job_rst = DESKTOP / f"{JOBNAME}.rst"
        if not job_db.exists() or not job_rst.exists():
            raise RuntimeError("Generated DB/RST not found.")

        shutil.copy2(job_db, DB_FILE)
        shutil.copy2(job_rst, RST_FILE)
        print("True")
    finally:
        try:
            mapdl.exit()
        except Exception:
            pass


if __name__ == "__main__":
    generate()
