from pathlib import Path

from ansys.mapdl.core import launch_mapdl


desktop = Path(r"C:\Users\user\Desktop")
output = desktop / "probe_ansys_license_output.txt"
mapdl = launch_mapdl(
    exec_file=r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe",
    jobname="probe_ansys_license",
    run_location=str(desktop),
    nproc=1,
    override=True,
    cleanup_on_exit=True,
    license_type="ansys",
    mapdl_output=str(output),
    start_timeout=180,
)
try:
    print(mapdl.run("/STATUS,PROD"))
finally:
    mapdl.exit()
