from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50111
JOBNAME = "eval_wb_hertz"

WBPJ_FILE = DESKTOP / "wb_hertz.wbpj"
DB_FILE = DESKTOP / "wb_hertz.db"
RESULT_FILE = DESKTOP / "wb_hertz.rst"
REQUIRED_FILES = [WBPJ_FILE, DB_FILE, RESULT_FILE]

GROUND_TRUTH = {
    "min_uy_mm": -2.846456732381085e-05,
    "max_usum_mm": 2.846907197953902e-05,
    "max_von_mises_mpa": 0.5386189405709895,
    "bottom_reaction_fy_n": -499.99999389378354,
}

TOLERANCE = {
    "default": {"rel": 0.10, "abs": 1e-6},
    "max_von_mises_mpa": {"rel": 0.10, "abs": 1e-3},
    "bottom_reaction_fy_n": {"rel": 0.02, "abs": 1.0},
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


def sort_max(mapdl, item: str, comp: str = "") -> float:
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,1,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def sort_min(mapdl, item: str, comp: str = "") -> float:
    if comp:
        mapdl.run(f"NSORT,{item},{comp},0,0,ALL")
    else:
        mapdl.run(f"NSORT,{item},,0,0,ALL")
    return float(mapdl.get_value("SORT", 0, "MIN"))


def reaction_fy_on_plane(mapdl, axis: str, value: float, tol: float = 1e-3) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", axis, value - tol, value + tol)
    count = int(mapdl.get_value("NODE", 0, "COUNT"))
    if count < 1:
        raise RuntimeError(f"No nodes found on {axis}={value}.")
    mapdl.fsum()
    fy = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
    allsel(mapdl)
    return fy


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set("LAST")

    return {
        "min_uy_mm": sort_min(mapdl, "U", "Y"),
        "max_usum_mm": sort_max(mapdl, "U", "SUM"),
        "max_von_mises_mpa": sort_max(mapdl, "S", "EQV"),
        "bottom_reaction_fy_n": reaction_fy_on_plane(mapdl, "Y", -10.0),
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

    if any(not is_nonempty_file(path) for path in REQUIRED_FILES):
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
        if name not in pred:
            return False
        if not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
