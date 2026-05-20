
# import subprocess
# from pathlib import Path


# DESKTOP = Path(r"C:\Users\user\Desktop")
# DB_FILE = DESKTOP / "apdl_solid_beam.db"
# RESULT_FILE = DESKTOP / "apdl_solid_beam.rst"
# REQUIRED_FILES = [DB_FILE, RESULT_FILE]
# EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
# JOBNAME = "eval_apdl_solid_beam"
# MAPDL_PORT = 50101

# GROUND_TRUTH = {
#     "load_point_UY_mm": -0.18762852462477883,
#     "load_point_USUM_mm": 0.18815225868694857,
#     "max_UY_mm": -0.18762852462477883,
#     "max_USUM_mm": 0.18815225868694857,
#     "max_von_mises_MPa": 52.70123620816831,
#     "reaction_FY_N": -100.00001525878906,
# }

# TOLERANCE = {
#     "default": {"rel": 0.01, "abs": 1e-4},
#     "max_von_mises_MPa": {"rel": 0.01, "abs": 0.05},
#     "reaction_FY_N": {"rel": 0.01, "abs": 0.10},
# }


# def is_nonempty_file(path: Path) -> bool:
#     return path.exists() and path.is_file() and path.stat().st_size > 0


# def within_tolerance(name: str, truth: float, pred: float) -> bool:
#     tol = TOLERANCE.get(name, TOLERANCE["default"])
#     rel = tol["rel"]
#     abs_tol = tol["abs"]
#     if truth == 0:
#         return abs(pred - truth) <= abs_tol
#     return abs(pred - truth) <= max(abs(truth) * rel, abs_tol)


# def allsel(mapdl) -> None:
#     mapdl.run("ALLSEL,ALL")


# def node_at(mapdl, x: float, y: float, z: float, tol: float = 1e-3) -> int:
#     allsel(mapdl)
#     mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
#     mapdl.nsel("R", "LOC", "Y", y - tol, y + tol)
#     mapdl.nsel("R", "LOC", "Z", z - tol, z + tol)
#     node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
#     allsel(mapdl)
#     if node < 1:
#         raise RuntimeError("Node not found.")
#     return node


# def sort_max(mapdl, item: str, comp: str = "") -> float:
#     if comp:
#         mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
#     else:
#         mapdl.run(f"NSORT,{item},,0,1,ALL")
#     return float(mapdl.get_value("SORT", 0, "MAX"))


# def reaction_fy_on_z(mapdl, z: float, tol: float = 1e-3) -> float:
#     allsel(mapdl)
#     mapdl.nsel("S", "LOC", "Z", z - tol, z + tol)
#     if int(mapdl.get_value("NODE", 0, "COUNT")) < 1:
#         raise RuntimeError("No support nodes selected.")
#     mapdl.fsum()
#     fy = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
#     allsel(mapdl)
#     return fy


# def extract_predictions(mapdl) -> dict:
#     mapdl.resume(DB_FILE.stem, "db")
#     mapdl.post1()
#     mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
#     mapdl.set(1, 1)

#     load_node = node_at(mapdl, x=5.0, y=10.0, z=100.0)
#     return {
#         "load_point_UY_mm": float(mapdl.get_value("NODE", load_node, "U", "Y")),
#         "load_point_USUM_mm": float(mapdl.get_value("NODE", load_node, "U", "SUM")),
#         "max_UY_mm": sort_max(mapdl, "U", "Y"),
#         "max_USUM_mm": sort_max(mapdl, "U", "SUM"),
#         "max_von_mises_MPa": sort_max(mapdl, "S", "EQV"),
#         "reaction_FY_N": reaction_fy_on_z(mapdl, z=0.0),
#     }


# def _kill_ansys_related() -> None:
#     for target in (
#         "ANSYS261.exe",
#         "ansys261.exe",
#         "ANSYS.exe",
#         "ansys.exe",
#         "fluent.exe",
#         "Fluent.exe",
#         "cortex.exe",
#         "Cortex.exe",
#     ):
#         try:
#             subprocess.run(
#                 ["taskkill", "/F", "/IM", target],
#                 capture_output=True,
#                 creationflags=0x08000000,
#             )
#         except Exception:
#             pass



# def evaluate() -> bool:
#     _kill_ansys_related()

#     if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
#         return False

#     mapdl = None
#     try:
#         from ansys.mapdl.core import launch_mapdl

#         mapdl = launch_mapdl(
#             exec_file=EXEC_FILE,
#             jobname=JOBNAME,
#             run_location=str(DESKTOP),
#             nproc=1,
#             port=MAPDL_PORT,
#             override=True,
#         )
#         pred = extract_predictions(mapdl)
#     except Exception:
#         return False
#     finally:
#         if mapdl is not None:
#             try:
#                 mapdl.exit()
#             except Exception:
#                 pass

#     for name, truth in GROUND_TRUTH.items():
#         if name not in pred or not within_tolerance(name, truth, pred[name]):
#             return False
#     return True


# def main() -> None:
#     print("True" if evaluate() else "False")


# if __name__ == "__main__":
#     main()
import subprocess
from pathlib import Path
import traceback
import sys
import os

DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_solid_beam.db"
RESULT_FILE = DESKTOP / "apdl_solid_beam.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_solid_beam"
MAPDL_PORT = 50101

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
    return fy


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set(1, 1)

    load_node = node_at(mapdl, x=5.0, y=10.0, z=100.0)
    return {
        "load_point_UY_mm": float(mapdl.get_value("NODE", load_node, "U", "Y")),
        "load_point_USUM_mm": float(mapdl.get_value("NODE", load_node, "U", "SUM")),
        "max_UY_mm": sort_max(mapdl, "U", "Y"),
        "max_USUM_mm": sort_max(mapdl, "U", "SUM"),
        "max_von_mises_MPa": sort_max(mapdl, "S", "EQV"),
        "reaction_FY_N": reaction_fy_on_z(mapdl, z=0.0),
    }


def _kill_ansys_related() -> None:
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


def evaluate() -> bool:
    _kill_ansys_related()

    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False

    # 关键：强制工作目录和输出目录到桌面，避免 Program Files 权限问题
    os.chdir(str(DESKTOP))
    os.environ["ANSYS_OUTDIR"] = str(DESKTOP)
    os.environ["ANSYS_RUNDIR"] = str(DESKTOP)

    mapdl = None
    try:
        from ansys.mapdl.core import launch_mapdl

        mapdl = launch_mapdl(
            exec_file=EXEC_FILE,
            jobname=JOBNAME,
            run_location=str(DESKTOP),
            nproc=1,
            port=MAPDL_PORT,
            override=True,
            additional_switches="-smp",   # 强制共享内存模式，避免分布式弹窗
            start_timeout=120,
        )
        pred = extract_predictions(mapdl)
    except Exception as e:
        log_error("Exception during MAPDL execution: %s" % str(e))
        log_error(traceback.format_exc())
        return False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass

    for name, truth in GROUND_TRUTH.items():
        if name not in pred:
            log_error("Missing prediction for: %s" % name)
            return False
        if not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    passed = False
    try:
        passed = evaluate()
    except Exception as e:
        log_error("Top-level exception: %s" % str(e))
        log_error(traceback.format_exc())
        passed = False
    output_result(passed)


if __name__ == "__main__":
    main()