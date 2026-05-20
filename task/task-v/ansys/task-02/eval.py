from pathlib import Path
import subprocess

import sys

_TASK_V_ROOT = Path(__file__).resolve().parents[2]
if str(_TASK_V_ROOT) not in sys.path:
    sys.path.insert(0, str(_TASK_V_ROOT))
from _gui_bypass import check_no_gui_bypass


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_plate.db"
RESULT_FILE = DESKTOP / "apdl_plate.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_plate"
MAPDL_PORT = 50102

GROUND_TRUTH = {
    "center_top_uy_mm": 0.0,
    "max_seqv_mpa": 52.70123620816831,
    "clamped_reaction_fy_n": -12.720306396490388,
}

TOLERANCE = {
    "default": {"rel": 0.08, "abs": 1e-6},
    "clamped_reaction_fy_n": {"rel": 0.05, "abs": 1e-3},
}


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def within_tolerance(name: str, truth: float, pred: float) -> bool:
    tol = TOLERANCE.get(name, TOLERANCE["default"])
    rel = tol["rel"]
    abs_tol = tol["abs"]
    if truth == 0:
        return abs(pred - truth) <= abs_tol
    return abs(pred - truth) <= max(abs(truth) * rel, abs_tol)


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def node_at(mapdl, x: float, y: float, tol: float = 1e-3) -> int:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    mapdl.nsel("R", "LOC", "Y", y - tol, y + tol)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    allsel(mapdl)
    if node < 1:
        raise RuntimeError("Node not found.")
    return node


def sort_max(mapdl, item: str, comp: str = "") -> float:
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def reaction_fy_on_x(mapdl, x: float, tol: float = 1e-3) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    if int(mapdl.get_value("NODE", 0, "COUNT")) < 1:
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

    center = node_at(mapdl, x=0.0, y=10.0)
    return {
        "center_top_uy_mm": float(mapdl.get_value("NODE", center, "U", "Y")),
        "max_seqv_mpa": sort_max(mapdl, "S", "EQV"),
        "clamped_reaction_fy_n": reaction_fy_on_x(mapdl, x=10.0),
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
    if not check_no_gui_bypass(DESKTOP):
        return False
    _kill_ansys_related()

    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False

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
        )
        pred = extract_predictions(mapdl)
    except Exception:
        return False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass

    for name, truth in GROUND_TRUTH.items():
        if name not in pred or not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
