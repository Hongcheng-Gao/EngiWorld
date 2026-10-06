from __future__ import annotations

import hashlib
import io
import math
import re
import shutil
import socket
import tempfile
import zipfile
from pathlib import Path


DESKTOP = Path(r"C:\Users\user\Desktop")
WBPJ_FILE = DESKTOP / "wb_buckling.wbpj"
DB_FILE = DESKTOP / "wb_buckling.db"
RESULT_FILE = DESKTOP / "wb_buckling.rst"
FILES = (WBPJ_FILE, DB_FILE, RESULT_FILE)
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


def genuine_workbench_project(path: Path) -> bool:
    data = path.read_bytes()
    if len(data) < 4096 or data.lstrip().startswith((b"{", b"[")):
        return False
    corpus = data.decode("latin-1", errors="ignore")
    if zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            parts = [" ".join(archive.namelist())]
            for name in archive.namelist():
                info = archive.getinfo(name)
                if info.file_size <= 2 * 1024 * 1024:
                    parts.append(archive.read(name).decode("latin-1", errors="ignore"))
            corpus = "\n".join(parts)
    lower = corpus.lower()
    has_project = "workbench" in lower or "ansys" in lower or "project" in lower
    has_static = "static structural" in lower or "staticstructural" in lower or "static structural" in lower.replace("_", " ")
    has_buckling = "eigenvalue buckling" in lower or "eigenvaluebuckling" in lower or "buckling" in lower
    return has_project and has_static and has_buckling




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
        exec_file=EXEC_FILE, run_location=str(root), jobname="eval_task19", nproc=1,
        port=free_port(56119), override=True, cleanup_on_exit=True,
    )
    try:
        mapdl.resume(str((root / "case").resolve()), "db")
        mapdl.prep7()
        mapdl.allsel()
        if "BEAM188" not in str(mapdl.run("ETLIST,ALL")).upper():
            return False
        section_text = str(mapdl.run("SLIST,ALL")).upper()
        area = re.search(r"\bAREA\s*=\s*(" + FLOAT + r")", section_text)
        iyy = re.search(r"\bIYY\s*=\s*(" + FLOAT + r")", section_text)
        izz = re.search(r"\bIZZ\s*=\s*(" + FLOAT + r")", section_text)
        if not (
            "RECTANGLE" in section_text
            and area and iyy and izz
            and close(float(area.group(1)), 100.0, 0.1)
            and close(float(iyy.group(1)), 833.333333, 1.0)
            and close(float(izz.group(1)), 833.333333, 1.0)
        ):
            return False
        if int(mapdl.get_value("ELEM", 0, "COUNT")) != 40:
            return False
        if not material_ok(str(mapdl.run("MPLIST,1"))):
            return False

        node_numbers = [int(value) for value in mapdl.mesh.nnum]
        coordinates = [[float(item) for item in row] for row in mapdl.mesh.nodes]
        coordinate_by_node = dict(zip(node_numbers, coordinates))
        if len(node_numbers) != 41 or len(coordinates) != 41:
            return False
        bounds = [(min(row[i] for row in coordinates), max(row[i] for row in coordinates)) for i in range(3)]
        if not (
            close(bounds[0][0], 0.0, 1.0e-6) and close(bounds[0][1], 0.0, 1.0e-6)
            and close(bounds[1][0], 0.0, 1.0e-6) and close(bounds[1][1], 1000.0, 1.0e-5)
            and close(bounds[2][0], 0.0, 1.0e-6) and close(bounds[2][1], 0.0, 1.0e-6)
        ):
            return False
        bottom = {node for node, xyz in coordinate_by_node.items() if abs(xyz[1]) <= 1.0e-6}
        top = {node for node, xyz in coordinate_by_node.items() if abs(xyz[1] - 1000.0) <= 1.0e-6}
        if len(bottom) != 1 or len(top) != 1:
            return False
        bottom_node = next(iter(bottom))
        top_node = next(iter(top))
        constraints = parse_constraints(str(mapdl.run("DLIST,ALL,ALL")))
        for dof in ("UX", "UY", "UZ"):
            if (bottom_node, dof) not in constraints:
                return False
        if (top_node, "UX") not in constraints or (top_node, "UZ") not in constraints or (top_node, "UY") in constraints:
            return False
        forces = parse_forces(str(mapdl.run("FLIST,ALL,ALL")))
        if not close(forces.get((top_node, "FY"), float("nan")), -1.0, 1.0e-4):
            return False

        database_nodes = set(node_numbers)
        mapdl.finish()
        mapdl.post1()
        mapdl.file(str((root / "case").resolve()), "rst")
        mapdl.set(1, 1)
        if set(int(value) for value in mapdl.result.mesh.nnum) != database_nodes:
            return False
        multiplier = float(mapdl.get_value("MODE", 1, "FREQ"))
        lateral_x = max(abs(float(value)) for value in mapdl.post_processing.nodal_displacement("X"))
        lateral_z = max(abs(float(value)) for value in mapdl.post_processing.nodal_displacement("Z"))
        return 1500.0 < multiplier < 2000.0 and max(lateral_x, lateral_z) > 1.0e-8
    finally:
        try:
            mapdl.exit(force=True)
        except Exception:
            pass


def evaluate() -> bool:
    before = require_files()
    if not genuine_workbench_project(WBPJ_FILE):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="ansys_task19_eval_", ignore_cleanup_errors=True) as temp:
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
