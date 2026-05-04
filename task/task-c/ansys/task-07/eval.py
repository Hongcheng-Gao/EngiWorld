from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
DB_FILE = DESKTOP / "apdl_solid_beam.db"
RESULT_FILE = DESKTOP / "apdl_solid_beam.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_solid_beam"
MAPDL_PORT = 50107

GROUND_TRUTH = {
    "load_point_uy_mm": -0.1876285246244521,
    "max_seqv_mpa": 52.70123620834753,
    "fixed_end_reaction_fy_n": -100.00001525878906,
}

TOLERANCE = {
    "default": {"rel": 0.05, "abs": 5e-4},
    "fixed_end_reaction_fy_n": {"rel": 0.03, "abs": 0.3},
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

    load_node = node_at(mapdl, x=100.0, y=10.0, z=5.0)
    return {
        "load_point_uy_mm": float(mapdl.get_value("NODE", load_node, "U", "Y")),
        "max_seqv_mpa": sort_max(mapdl, "S", "EQV"),
        "fixed_end_reaction_fy_n": reaction_fy_on_x(mapdl, x=0.0),
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
