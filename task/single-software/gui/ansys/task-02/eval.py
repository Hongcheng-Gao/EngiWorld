from __future__ import annotations

import hashlib
import math
import re
import shutil
import socket
import tempfile
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
DB_FILE = DESKTOP / "apdl_plate.db"
RESULT_FILE = DESKTOP / "apdl_plate.rst"
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


def model_coordinates(mapdl):
    node_numbers = [int(value) for value in mapdl.mesh.nnum]
    coordinates = [[float(item) for item in row] for row in mapdl.mesh.nodes]
    if len(node_numbers) != len(coordinates) or not coordinates:
        raise RuntimeError("empty or inconsistent mesh")
    return node_numbers, coordinates, dict(zip(node_numbers, coordinates))


def selected_nodes(node_numbers, coordinates, axis: int, target: float, tolerance: float = 1.0e-6) -> set[int]:
    return {
        number
        for number, xyz in zip(node_numbers, coordinates)
        if abs(xyz[axis] - target) <= tolerance
    }


def parse_constraints(text: str) -> set[tuple[int, str]]:
    return {
        (int(node), label.upper())
        for node, label in re.findall(r"(?m)^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ|TEMP)\s+" + FLOAT, text)
    }


def material_ok(text: str) -> bool:
    upper = text.upper()
    ex = re.search(r"\bEX\b\s*[=:]?\s*(" + FLOAT + r")", upper)
    nu = re.search(r"\bPRXY\b\s*[=:]?\s*(" + FLOAT + r")", upper)
    return bool(ex and nu and close(float(ex.group(1)), 210000.0, 2.1) and close(float(nu.group(1)), 0.3, 0.003))


def reaction(mapdl, nodes: set[int], label: str) -> float:
    values = []
    for node in nodes:
        value = float(mapdl.get_value("NODE", node, "RF", label))
        if math.isfinite(value):
            values.append(value)
    if not values:
        raise RuntimeError("reaction data unavailable")
    return sum(values)


def inspect_copy(root: Path) -> bool:
    from ansys.mapdl.core import launch_mapdl

    mapdl = launch_mapdl(
        exec_file=EXEC_FILE,
        run_location=str(root),
        jobname="eval_task02",
        nproc=1,
        port=free_port(56102),
        override=True,
        cleanup_on_exit=True,
    )
    try:
        mapdl.resume(str((root / "case").resolve()), "db")
        mapdl.prep7()
        mapdl.allsel()

        element_text = str(mapdl.run("ETLIST,ALL"))
        if "PLANE183" not in element_text.upper() or "AXISYMMETRIC MODEL" not in element_text.upper():
            return False
        if int(mapdl.get_value("ELEM", 0, "COUNT")) != 100:
            return False

        node_numbers, coordinates, _ = model_coordinates(mapdl)
        bounds = [(min(row[i] for row in coordinates), max(row[i] for row in coordinates)) for i in range(3)]
        if not (
            close(bounds[0][0], 0.0, 1.0e-6)
            and close(bounds[0][1], 50.0, 1.0e-5)
            and close(bounds[1][0], 0.0, 1.0e-6)
            and close(bounds[1][1], 1.0, 1.0e-6)
        ):
            return False
        x_levels = {round(row[0], 8) for row in coordinates}
        y_levels = {round(row[1], 8) for row in coordinates}
        if len(x_levels) < 51 or len(y_levels) < 9:
            return False
        if not material_ok(str(mapdl.run("MPLIST,1"))):
            return False

        constraints = parse_constraints(str(mapdl.run("DLIST,ALL,ALL")))
        axis_nodes = selected_nodes(node_numbers, coordinates, 0, 0.0)
        clamp_nodes = selected_nodes(node_numbers, coordinates, 0, 50.0)
        if not axis_nodes or not clamp_nodes:
            return False
        if any((node, "UX") not in constraints for node in axis_nodes):
            return False
        if any((node, "UX") not in constraints or (node, "UY") not in constraints for node in clamp_nodes):
            return False

        pressure_text = str(mapdl.run("SFELIST,ALL,ALL"))
        pressure_values = [
            float(value)
            for value in re.findall(r"(?m)^\s*\d+\s+\d+\s+\d+\s+(" + FLOAT + r")\s+", pressure_text)
        ]
        if "PRES" not in pressure_text.upper() or len(pressure_values) != 25 or any(not close(value, 0.1, 1.0e-6) for value in pressure_values):
            return False

        database_nodes = set(node_numbers)
        mapdl.finish()
        mapdl.post1()
        mapdl.file(str((root / "case").resolve()), "rst")
        mapdl.set("LAST")
        if set(int(value) for value in mapdl.result.mesh.nnum) != database_nodes:
            return False
        displacement = mapdl.post_processing.nodal_displacement("NORM")
        stress = mapdl.post_processing.nodal_eqv_stress()
        max_displacement = max(abs(float(value)) for value in displacement)
        max_stress = max(abs(float(value)) for value in stress)
        total_reaction = reaction(mapdl, clamp_nodes, "FY")

        expected_load = 0.1 * math.pi * 50.0**2
        return (
            0.01 < max_displacement < 5.0
            and 5.0 < max_stress < 5000.0
            and abs(abs(total_reaction) - expected_load) <= 0.03 * expected_load
        )
    finally:
        try:
            mapdl.exit(force=True)
        except Exception:
            pass


def evaluate() -> bool:
    before = require_files()
    try:
        with tempfile.TemporaryDirectory(prefix="ansys_task02_eval_", ignore_cleanup_errors=True) as temp:
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
