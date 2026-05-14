from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50118
JOBNAME = "eval_wb_plate"

WBPJ_FILE = DESKTOP / "wb_plate.wbpj"
DB_FILE = DESKTOP / "wb_plate.db"
RESULT_FILE = DESKTOP / "wb_plate.rst"
REQUIRED_FILES = [WBPJ_FILE, DB_FILE, RESULT_FILE]

GROUND_TRUTH = {
    "center_uz_mm": -2.1156713073584488,
    "min_z_mm": -2.1156713073584488,
    "max_von_mises_mpa": 322.6727777809399,
}

TOLERANCE = {
    "default": {"rel": 0.08, "abs": 0.01},
    "max_von_mises_mpa": {"rel": 0.12, "abs": 0.5},
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


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set("LAST")

    center = node_at(mapdl, x=50.0, y=50.0, z=0.0)
    center_uz = float(mapdl.get_value("NODE", center, "U", "Z"))
    return {
        "center_uz_mm": center_uz,
        "min_z_mm": sort_min(mapdl, "U", "Z"),
        "max_von_mises_mpa": sort_max(mapdl, "S", "EQV"),
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
    print("true" if evaluate() else "false")


if __name__ == "__main__":
    main()
