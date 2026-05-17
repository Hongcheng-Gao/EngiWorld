
import subprocess
from pathlib import Path


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
DB_FILE = DESKTOP / "apdl_solid_beam.db"
RESULT_FILE = DESKTOP / "apdl_solid_beam.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_solid_beam"
MAPDL_PORT = 50110

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
        if name not in pred or not within_tolerance(name, truth, pred[name]):
            return False
    return True


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
