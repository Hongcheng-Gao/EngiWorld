import subprocess
from pathlib import Path
import traceback
import sys

DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_solid_beam.db"
RESULT_FILE = DESKTOP / "apdl_solid_beam.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_solid_beam"
MAPDL_PORT = 50110

RESULT_TXT = DESKTOP / "eval_result.txt"
ERROR_TXT = DESKTOP / "eval_error.txt"

GROUND_TRUTH = {
    "load_point_UY_mm": -0.18762852462477883,
    "load_point_USUM_mm": 0.18815225868694857,
    "max_UY_mm": -0.18762852462477883,
    "max_USUM_mm": 0.18815225868694857,
    "max_von_mises_MPa": 52.70123620816831,
    "reaction_FY_N": -100.00001525878906,
}

TOLERANCE = {
    "default": {"rel": 0.01, "abs": 1e-4},
    "max_von_mises_MPa": {"rel": 0.01, "abs": 0.05},
    "reaction_FY_N": {"rel": 0.01, "abs": 0.10},
}

error_log = []

def log_error(msg):
    error_log.append(str(msg))

def output_result(value):
    result_text = "True" if value else "False"
    with open(RESULT_TXT, "w") as f:
        f.write(result_text + "\n")
    if not value and error_log:
        with open(ERROR_TXT, "w") as f:
            f.write("\n".join(error_log) + "\n")
    try:
        sys.__stdout__.write(result_text + "\n")
        sys.__stdout__.flush()
    except:
        pass


def is_nonempty_file(path: Path) -> bool:
    ok = path.exists() and path.is_file() and path.stat().st_size > 0
    if not ok:
        log_error("Required file missing or empty: %s" % path)
    return ok


def within_tolerance(name: str, truth: float, pred: float) -> bool:
    tol = TOLERANCE.get(name, TOLERANCE["default"])
    rel = tol["rel"]
    abs_tol = tol["abs"]
    if truth == 0:
        ok = abs(pred - truth) <= abs_tol
    else:
        ok = abs(pred - truth) <= max(abs(truth) * rel, abs_tol)
    if not ok:
        log_error(
            "  FAILED %s: expected %.12f, got %.12f, tolerance %.12f (rel=%.4f, abs=%.6f)"
            % (name, truth, pred, max(abs(truth) * rel, abs_tol) if truth != 0 else abs_tol, rel, abs_tol)
        )
    return ok


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def node_at(mapdl, x: float, y: float, z: float, tol: float = 1e-3) -> int:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    mapdl.nsel("R", "LOC", "Y", y - tol, y + tol)
    mapdl.nsel("R", "LOC", "Z", z - tol, z + tol)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    allsel(mapdl)
    if node < 1:
        log_error("Node not found at (%.3f, %.3f, %.3f)" % (x, y, z))
        raise RuntimeError("Node not found.")
    return node


def sort_max(mapdl, item: str, comp: str = "") -> float:
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def reaction_fy_on_z(mapdl, z: float, tol: float = 1e-3) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "Z", z - tol, z + tol)
    count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if count < 1:
        log_error("No support nodes found at Z=%.3f" % z)
        raise RuntimeError("No support nodes selected.")
    mapdl.fsum()
    fy = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
    allsel(mapdl)