from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50119
JOBNAME = "eval_wb_buckling"

WBPJ_FILE = DESKTOP / "wb_buckling.wbpj"
DB_FILE = DESKTOP / "wb_buckling.db"
RESULT_FILE = DESKTOP / "wb_buckling.rst"
REQUIRED_FILES = [WBPJ_FILE, DB_FILE, RESULT_FILE]

GROUND_TRUTH = {
    "buckling_multiplier": 1726.7420790501085,
    "top_rotx_mode1": -0.0031407950322749605,
    "top_rotz_mode1": -0.002658487015404436,
}

TOLERANCE = {
    "default": {"rel": 0.10, "abs": 1e-4},
    "buckling_multiplier": {"rel": 0.10, "abs": 5.0},
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


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set(1, 1)

    multiplier = float(mapdl.get_value("MODE", 1, "FREQ"))
    top = node_at(mapdl, x=0.0, y=1000.0, z=0.0)
    top_rotx = float(mapdl.get_value("NODE", top, "ROT", "X"))
    top_rotz = float(mapdl.get_value("NODE", top, "ROT", "Z"))

    return {
        "buckling_multiplier": multiplier,
        "top_rotx_mode1": top_rotx,
        "top_rotz_mode1": top_rotz,
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
