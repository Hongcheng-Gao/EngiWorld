from pathlib import Path
import subprocess


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_harmonic.db"
RESULT_FILE = DESKTOP / "apdl_harmonic.rst"
REQUIRED_FILES = [DB_FILE, RESULT_FILE]
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
JOBNAME = "eval_apdl_harmonic"
MAPDL_PORT = 50114


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _is_known_generated_script(name: str) -> bool:
    return (
        (name.startswith("eval_") and name.endswith((".bat", ".cmd")))
        or (name.startswith("tmp") and name.endswith((".jou", ".wbjn")))
    )


def _cleanup_known_generated_scripts(desktop_path: Path) -> None:
    try:
        entries = list(desktop_path.iterdir())
    except Exception:
        return

    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except Exception:
            continue

        name = entry.name.lower()
        if not _is_known_generated_script(name):
            continue

        try:
            entry.unlink()
        except Exception:
            pass


def has_forbidden_script_file(desktop_path: Path) -> bool:
    allowed_names = {"eval.py", "license.py"}
    forbidden_suffixes = {
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
        ".js",
        ".pyw",
        ".jou",
        ".wbjn",
    }
    try:
        entries = desktop_path.iterdir()
    except Exception:
        return True

    for entry in entries:
        try:
            if not entry.is_file():
                continue
        except Exception:
            return True

        name = entry.name.lower()
        if name in allowed_names:
            continue
        if _is_known_generated_script(name):
            continue
        if any(name.endswith(ext) for ext in forbidden_suffixes):
            return True

    return False


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




def _coord_span(arr, axis: int):
    values = [float(v[axis]) for v in arr]
    return min(values), max(values)


def _within(value: float, target: float, tol: float) -> bool:
    return abs(value - target) <= tol


def _check_bounds_from_instruction(mapdl, task_name: str) -> bool:
    nodes = mapdl.mesh.nodes
    if nodes is None or len(nodes) < 2:
        return False

    xmin, xmax = _coord_span(nodes, 0)
    ymin, ymax = _coord_span(nodes, 1)
    zmin, zmax = _coord_span(nodes, 2)

    if task_name == "task-01":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 10.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 10.0, 1e-1) and _within(zmin, 0.0, 1e-2) and _within(zmax, 100.0, 1e-1)
    if task_name == "task-02":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 50.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 1.0, 1e-1)
    if task_name == "task-03":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 100.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 200.0, 1e-1)
    if task_name == "task-04":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 50.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 20.0, 1e-1) and _within(zmin, 0.0, 1e-2) and _within(zmax, 20.0, 1e-1)
    if task_name == "task-05":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 500.0, 5e-1)
    if task_name == "task-06":
        return _within(xmin, 25.0, 1e-1) and _within(xmax, 50.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 10.0, 1e-1)
    if task_name == "task-07":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 100.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 10.0, 1e-1) and _within(zmin, 0.0, 1e-2) and _within(zmax, 10.0, 1e-1)
    if task_name == "task-08":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 100.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 10.0, 1e-1) and _within(zmin, 0.0, 1e-2) and _within(zmax, 10.0, 1e-1)
    if task_name == "task-11":
        return (xmax - xmin) > 10.0 and (ymax - ymin) > 10.0 and (zmax - zmin) > 10.0
    if task_name == "task-12":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 1000.0, 5e-1)
    if task_name == "task-13":
        return _within(ymin, 0.0, 1e-2) and _within(ymax, 50.0, 2e-1)
    if task_name == "task-14":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 500.0, 5e-1)
    if task_name == "task-18":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 100.0, 2e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 100.0, 2e-1)
    if task_name == "task-19":
        return _within(ymin, 0.0, 1e-2) and _within(ymax, 1000.0, 5e-1)
    if task_name == "task-20":
        return _within(xmin, 0.0, 1e-2) and _within(xmax, 100.0, 1e-1) and _within(ymin, 0.0, 1e-2) and _within(ymax, 10.0, 1e-1) and _within(zmin, 0.0, 1e-2) and _within(zmax, 10.0, 1e-1)

    return True


def strict_process_check(mapdl, pred):
    import math
    import re
    FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"

    def close(value, target, tolerance):
        try:
            value = float(value)
        except Exception:
            return False
        return math.isfinite(value) and abs(value - target) <= tolerance

    def constraints(text):
        return {(int(node), dof.upper()) for node, dof in re.findall(
            r"(?m)^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ|TEMP)\s+" + FLOAT, text)}

    def forces(text):
        return {(int(node), dof.upper()): float(value) for node, dof, value in re.findall(
            r"(?m)^\s*(\d+)\s+(FX|FY|FZ)\s+(" + FLOAT + r")", text)}

    mapdl.finish()
    mapdl.resume(DB_FILE.stem, "db")
    mapdl.prep7()
    mapdl.allsel()
    node_numbers = [int(value) for value in mapdl.mesh.nnum]
    coordinates = [[float(item) for item in row] for row in mapdl.mesh.nodes]
    if not coordinates or len(node_numbers) != len(coordinates):
        return False
    by_node = dict(zip(node_numbers, coordinates))
    element_text = str(mapdl.run("ETLIST,ALL")).upper()
    material_text = str(mapdl.run("MPLIST,ALL")).upper()
    dlist = constraints(str(mapdl.run("DLIST,ALL,ALL")))

    if "BEAM188" not in element_text or int(mapdl.get_value("ELEM", 0, "COUNT")) != 20:
        return False
    if not all(token in material_text for token in ("210000", "0.300", "7.850")):
        return False
    fixed = {node for node, xyz in by_node.items() if abs(xyz[0]) <= 1.0e-6}
    loaded = {node for node, xyz in by_node.items() if abs(xyz[0]-500.0) <= 1.0e-6}
    if len(fixed) != 1 or len(loaded) != 1:
        return False
    node0 = next(iter(fixed)); node1 = next(iter(loaded))
    if any((node0, dof) not in dlist for dof in ("UX","UY","UZ","ROTX","ROTY","ROTZ")):
        return False
    flist = forces(str(mapdl.run("FLIST,ALL,ALL")))
    if not close(flist.get((node1, "FY")), -10.0, 0.01):
        return False
    mapdl.finish(); mapdl.post1(); mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip(".")); mapdl.set(1, 1)
    frequency = float(mapdl.get_value("ACTIVE", 0, "SET", "FREQ"))
    return close(frequency, 5.0, 1.0e-4) and math.isfinite(float(pred["free_end_uy_mm"]))


def passes_process_checks(mapdl, pred: dict, task_name: str) -> bool:
    if not strict_process_check(mapdl, pred):
        return False

    mapdl.resume(DB_FILE.stem, "db")
    if not _check_bounds_from_instruction(mapdl, task_name):
        return False

    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    try:
        mapdl.set("LAST")
    except Exception:
        try:
            mapdl.set(1, 1)
        except Exception:
            return False

    for key, val in pred.items():
        try:
            x = float(val)
        except Exception:
            return False

        lk = key.lower()
        if "temp" in lk and not (-1000.0 <= x <= 5000.0):
            return False
        if "freq" in lk and not (x > 0.0):
            return False
        if "reaction" in lk and abs(x) < 1e-9:
            return False
        if ("uy" in lk or "uz" in lk or "ux" in lk or "rot" in lk) and not (-1e6 <= x <= 1e6):
            return False
        if ("von_mises" in lk or "seqv" in lk or "stress" in lk) and abs(x) < 1e-9:
            return False
        if "final_time" in lk and not (x > 0.0):
            return False

    return True

def evaluate() -> bool:
    _kill_ansys_related()
    _cleanup_known_generated_scripts(DESKTOP)

    if has_forbidden_script_file(DESKTOP):
        return False

    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False

    mapdl = None
    ok = False
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
        ok = passes_process_checks(mapdl, pred, task_name="task-14")
    except Exception:
        ok = False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass
    return ok

def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
