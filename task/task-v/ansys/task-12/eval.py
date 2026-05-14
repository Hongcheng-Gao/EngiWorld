from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\Administrator\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50112
JOBNAME = "eval_wb_transient"

WBPJ_FILE = DESKTOP / "wb_transient.wbpj"
DB_FILE = DESKTOP / "wb_transient.db"
RESULT_FILE = DESKTOP / "wb_transient.rst"
REQUIRED_FILES = [WBPJ_FILE, DB_FILE, RESULT_FILE]

GROUND_TRUTH = {
    "peak_midspan_uy_mm": -14.879390210491861,
    "final_midspan_uy_mm": -11.508421954864733,
    "final_time_s": 0.05,
}

TOLERANCE = {
    "default": {"rel": 0.15, "abs": 0.05},
    "final_time_s": {"rel": 0.0, "abs": 0.005},
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


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))

    mid_node = node_at(mapdl, x=500.0, y=0.0, z=0.0)
    history = []
    for substep in range(1, 500):
        try:
            mapdl.set(1, substep)
            time_s = float(mapdl.get_value("ACTIVE", 0, "SET", "TIME"))
            uy = float(mapdl.get_value("NODE", mid_node, "U", "Y"))
        except Exception:
            break

        if history and abs(time_s - history[-1][0]) <= 1e-12:
            break
        history.append((time_s, uy))

    if not history:
        raise RuntimeError("No transient result set extracted.")

    mapdl.set("LAST")
    final_time = float(mapdl.get_value("ACTIVE", 0, "SET", "TIME"))
    final_uy = float(mapdl.get_value("NODE", mid_node, "U", "Y"))
    peak_uy = min(v for _, v in history)
    peak_uy = min(peak_uy, final_uy)

    return {
        "peak_midspan_uy_mm": peak_uy,
        "final_midspan_uy_mm": final_uy,
        "final_time_s": final_time,
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
