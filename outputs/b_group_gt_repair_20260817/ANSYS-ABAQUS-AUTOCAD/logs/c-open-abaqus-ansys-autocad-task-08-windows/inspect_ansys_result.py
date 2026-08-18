from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
stem = "Job-Contact-ANSYS"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="inspect_contact",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=False,
)
try:
    mapdl.resume(str(desktop / stem), "db")
    mapdl.post1()
    mapdl.file(str(desktop / stem), "rst")
    mapdl.set("LAST")
    etable_output = str(mapdl.etable("CPRES", "CONT", "PRES"))
    pretab_output = str(mapdl.pretab("CPRES"))
    (desktop / "contact_etable.txt").write_text(
        etable_output + "\n--- PRETAB ---\n" + pretab_output + "\n",
        encoding="utf-8",
    )
finally:
    try:
        mapdl.exit()
    except Exception:
        pass
