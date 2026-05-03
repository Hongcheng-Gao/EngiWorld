from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
DB_FILE = DESKTOP / "apdl_transient_thermal.db"
RESULT_FILE = DESKTOP / "apdl_transient_thermal.rth"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_transient_thermal"
MAPDL_PORT = 50104

GROUND_TRUTH = {
    "temp_x4_c": 84.73999072205697,
    "temp_x6_c": 77.38573277153104,
    "temp_max_c": 100.0,
    "temp_min_c": 20.476805994130366,
}

TOLERANCE = {
    "default": {"rel": 0.03, "abs": 0.6},
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


def node_at_x(mapdl, x: float, tol: float = 1e-3) -> int:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    mapdl.nsel("R", "LOC", "Y", 10.0 - tol, 10.0 + tol)
    mapdl.nsel("R", "LOC", "Z", 10.0 - tol, 10.0 + tol)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    allsel(mapdl)
    if node < 1:
        raise RuntimeError("Node not found for temperature probe.")
    return node


def sort_max(mapdl, item: str) -> float:
    mapdl.run(f"NSORT,{item},,0,1,ALL")
    return float(mapdl.get_value("SORT", 0, "MAX"))


def sort_min(mapdl, item: str) -> float:
    mapdl.run(f"NSORT,{item},,0,0,ALL")
    return float(mapdl.get_value("SORT", 0, "MIN"))


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set(1, "LAST")

    n4 = node_at_x(mapdl, 4.0)
    n6 = node_at_x(mapdl, 6.0)
    return {
        "temp_x4_c": float(mapdl.get_value("NODE", n4, "TEMP")),
        "temp_x6_c": float(mapdl.get_value("NODE", n6, "TEMP")),
        "temp_max_c": sort_max(mapdl, "TEMP"),
        "temp_min_c": sort_min(mapdl, "TEMP"),
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
    print("true" if evaluate() else "false")


if __name__ == "__main__":
    main()
