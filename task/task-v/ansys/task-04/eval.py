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
    "temperature_at_x4mm_degC": 84.73999072205697,
    "temperature_at_x6mm_degC": 77.38573277153104,
    "max_temperature_degC": 100.0,
    "min_temperature_degC": 20.476805994130366,
    "x0_boundary_total_heat_flow_W": -76.86148285865784,
}

TOLERANCE = {
    "default": {"rel": 0.02, "abs": 0.5},
    "x0_boundary_total_heat_flow_W": {"rel": 0.10, "abs": 2.0},
}


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def has_forbidden_py_file(root: Path) -> bool:
    try:
        entries = list(root.iterdir())
    except Exception:
        return True

    for path in entries:
        try:
            if not path.is_file():
                continue
        except Exception:
            return True

        name = path.name.lower()
        if name.endswith(".py") and name != "eval.py":
            return True

    return False


def within_tolerance(name: str, truth: float, pred: float) -> bool:
    tol = TOLERANCE.get(name, TOLERANCE["default"])
    rel = tol["rel"]
    abs_tol = tol["abs"]
    if truth == 0:
        return abs(pred - truth) <= abs_tol
    return abs(pred - truth) <= max(abs(truth) * rel, abs_tol)


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
        raise RuntimeError(f"No node found near ({x}, {y}, {z}).")
    return node


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


def heat_flow_on_x(mapdl, x: float, tol: float = 1e-3) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    if int(mapdl.get_value("NODE", 0, "COUNT")) < 1:
        raise RuntimeError("No nodes selected for X face.")
    mapdl.fsum()
    heat = float(mapdl.get_value("FSUM", 0, "ITEM", "HEAT"))
    allsel(mapdl)
    return heat


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set("LAST")

    n4 = node_at(mapdl, x=4.0, y=10.0, z=10.0)
    n6 = node_at(mapdl, x=6.0, y=10.0, z=10.0)
    return {
        "temperature_at_x4mm_degC": float(mapdl.get_value("NODE", n4, "TEMP")),
        "temperature_at_x6mm_degC": float(mapdl.get_value("NODE", n6, "TEMP")),
        "max_temperature_degC": sort_max(mapdl, "TEMP"),
        "min_temperature_degC": sort_min(mapdl, "TEMP"),
        "x0_boundary_total_heat_flow_W": heat_flow_on_x(mapdl, x=0.0),
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

    if has_forbidden_py_file(DESKTOP):
        return False

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
        if name not in pred:
            return False
        if not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
