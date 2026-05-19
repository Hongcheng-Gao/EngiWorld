from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_harmonic.db"
RESULT_FILE = DESKTOP / "apdl_harmonic.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_harmonic"
MAPDL_PORT = 50114

GROUND_TRUTH = {
    "free_end_uy_mm": -2.43344801367377,
}

TOLERANCE = {
    "default": {"rel": 0.08, "abs": 0.02},
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
        raise RuntimeError("Free-end node not found.")
    return node


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set(1, 1)

    free = node_at(mapdl, x=500.0, y=0.0, z=0.0)
    return {
        "free_end_uy_mm": float(mapdl.get_value("NODE", free, "U", "Y")),
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
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
