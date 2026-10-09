from __future__ import annotations

import hashlib
import math
import re
import shutil
import socket
import tempfile
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_eccentric_beam.db"
RESULT_FILE = DESKTOP / "apdl_eccentric_beam.rst"
FILES = (DB_FILE, RESULT_FILE)
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def require_files() -> dict[Path, str]:
    for path in FILES:
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path.name)
    return {path: digest(path) for path in FILES}




def free_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no MAPDL port available")


def close(value: float, target: float, tolerance: float) -> bool:
    return math.isfinite(value) and abs(value - target) <= tolerance


def parse_constraints(text: str) -> set[tuple[int, str]]:
    return {
        (int(node), label.upper())
        for node, label in re.findall(r"(?m)^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ)\s+" + FLOAT, text)
    }


def parse_forces(text: str) -> dict[tuple[int, str], float]:
    values = {}
    for node, label, value in re.findall(r"(?m)^\s*(\d+)\s+(FX|FY|FZ)\s+(" + FLOAT + r")", text):
        values[(int(node), label.upper())] = float(value)
    return values


def material_ok(text: str) -> bool:
    upper = text.upper()
    ex = re.search(r"\bEX\b\s*[=:]?\s*(" + FLOAT + r")", upper)
    nu = re.search(r"\bPRXY\b\s*[=:]?\s*(" + FLOAT + r")", upper)
    return bool(ex and nu and close(float(ex.group(1)), 210000.0, 2.1) and close(float(nu.group(1)), 0.3, 0.003))


def inspect_copy(root: Path) -> bool:
    from ansys.mapdl.core import launch_mapdl

    mapdl = launch_mapdl(
        exec_file=EXEC_FILE, run_location=str(root), jobname="eval_task07", nproc=1,
        port=free_port(56107), override=True, cleanup_on_exit=True,
    )
    try:
        mapdl.resume(str((root / "case").resolve()), "db")
        mapdl.prep7()
        mapdl.allsel()
        if "SOLID185" not in str(mapdl.run("ETLIST,ALL")).upper():
            return False
        if int(mapdl.get_value("ELEM", 0, "COUNT")) != 240:
            return False
        node_numbers = [int(value) for value in mapdl.mesh.nnum]
        coordinates = [[float(item) for item in row] for row in mapdl.mesh.nodes]
        coordinate_by_node = dict(zip(node_numbers, coordinates))
        if not coordinates or len(coordinates) != len(node_numbers):
            return False
        bounds = [(min(row[i] for row in coordinates), max(row[i] for row in coordinates)) for i in range(3)]
        expected = ((0.0, 150.0), (0.0, 20.0), (0.0, 10.0))
        if any(not close(actual[j], expected[i][j], 1.0e-5) for i, actual in enumerate(bounds) for j in (0, 1)):
            return False
        if [len({round(row[i], 8) for row in coordinates}) for i in range(3)] != [31, 5, 3]:
            return False
        if not material_ok(str(mapdl.run("MPLIST,1"))):
            return False

        fixed_nodes = {number for number, xyz in coordinate_by_node.items() if abs(xyz[0]) <= 1.0e-6}
        load_nodes = {
            number for number, xyz in coordinate_by_node.items()
            if abs(xyz[0] - 150.0) <= 1.0e-6 and abs(xyz[1] - 20.0) <= 1.0e-6 and abs(xyz[2] - 10.0) <= 1.0e-6
        }
        constraints = parse_constraints(str(mapdl.run("DLIST,ALL,ALL")))
        forces = parse_forces(str(mapdl.run("FLIST,ALL,ALL")))
        if not fixed_nodes or len(load_nodes) != 1:
            return False
        if any(any((node, dof) not in constraints for dof in ("UX", "UY", "UZ")) for node in fixed_nodes):
            return False
        load_node = next(iter(load_nodes))
        if not close(forces.get((load_node, "FY"), float("nan")), -200.0, 0.02):
            return False

        database_nodes = set(node_numbers)
        mapdl.finish()
        mapdl.post1()
        mapdl.file(str((root / "case").resolve()), "rst")
        mapdl.set("LAST")
        if set(int(value) for value in mapdl.result.mesh.nnum) != database_nodes:
            return False
        uy = float(mapdl.get_value("NODE", load_node, "U", "Y"))
        uz = float(mapdl.get_value("NODE", load_node, "U", "Z"))
        stress = max(abs(float(value)) for value in mapdl.post_processing.nodal_eqv_stress())

        reaction_y = 0.0
        reaction_mx = 0.0
        for node in fixed_nodes:
            _, y, z = coordinate_by_node[node]
            rfy = float(mapdl.get_value("NODE", node, "RF", "FY"))
            rfz = float(mapdl.get_value("NODE", node, "RF", "FZ"))
            reaction_y += rfy
            reaction_mx += (y - 10.0) * rfz - (z - 5.0) * rfy

        return (
            -1.0 < uy < -0.02
            and abs(uz) > 1.0e-5
            and 1.0 < stress < 1000.0
            and abs(abs(reaction_y) - 200.0) <= 4.0
            and abs(abs(reaction_mx) - 1000.0) <= 50.0
        )
    finally:
        try:
            mapdl.exit(force=True)
        except Exception:
            pass


def evaluate() -> bool:
    before = require_files()
    try:
        with tempfile.TemporaryDirectory(prefix="ansys_task07_eval_", ignore_cleanup_errors=True) as temp:
            root = Path(temp)
            shutil.copy2(DB_FILE, root / "case.db")
            shutil.copy2(RESULT_FILE, root / "case.rst")
            passed = inspect_copy(root)
    except Exception:
        passed = False
    after = {path: digest(path) for path in FILES}
    return passed and before == after


if __name__ == "__main__":
    print("True" if evaluate() else "False")
