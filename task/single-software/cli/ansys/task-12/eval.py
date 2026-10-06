from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


DESKTOP = Path(r"C:\Users\user\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50112
JOBNAME = "eval_wb_transient"

WBPJ_FILE = DESKTOP / "wb_transient.wbpj"
DB_FILE = DESKTOP / "wb_transient.db"
RESULT_FILE = DESKTOP / "wb_transient.rst"
REQUIRED_FILES = [WBPJ_FILE, DB_FILE, RESULT_FILE]


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def is_workbench_project(path: Path) -> bool:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return False

    if root.tag != "Storage":
        return False
    project = root.find("Project")
    if project is None:
        return False

    values = {
        child.tag: (child.text or "").strip()
        for child in project
        if child.text
    }
    if values.get("project-type") != "WB2":
        return False
    if values.get("external-version-string") != "2026 R1":
        return False

    if root.find("Addins") is None or root.find("Containers") is None:
        return False

    has_project_reference = False
    has_transient_system = False
    for obj in root.findall(".//Object"):
        class_type = (obj.findtext("class-type") or "").strip()
        member_data = (obj.findtext("member-data") or "").strip()
        object_name = obj.attrib.get("Name", "")
        if (
            class_type == "FileReference"
            and '"DisplayText": "wb_transient.wbpj"' in member_data
            and '"Location": "$(ProjectName).wbpj"' in member_data
        ):
            has_project_reference = True
        if object_name.startswith("/Schematic/") and class_type in {"System", "Component"}:
            if "Transient Structural" in member_data or "Mechanical APDL" in member_data:
                has_transient_system = True
    return has_project_reference and has_transient_system


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


def _listing_value(text: str, label: str) -> float:
    match = re.search(
        rf"^\s*{re.escape(label)}\s*=\s*([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)",
        text,
        flags=re.I | re.M,
    )
    if not match:
        raise RuntimeError(f"{label} not found in MAPDL listing")
    return float(match.group(1))


def model_is_valid(mapdl) -> bool:
    allsel(mapdl)
    nodes = mapdl.mesh.nodes
    if nodes is None or not (21 <= len(nodes) <= 61):
        return False
    if int(mapdl.get_value("ELEM", 0, "COUNT")) != 20:
        return False
    element_types = str(mapdl.etlist()).upper()
    if not any(name in element_types for name in ("BEAM188", "BEAM189")):
        return False

    xs = [float(row[0]) for row in nodes]
    ys = [float(row[1]) for row in nodes]
    zs = [float(row[2]) for row in nodes]
    if abs(min(xs)) > 1e-4 or abs(max(xs) - 1000.0) > 1e-4:
        return False
    if max(abs(value) for value in ys + zs) > 1e-4:
        return False
    reference_nodes = [node_at(mapdl, x, 0.0, 0.0, tol=1e-4) for x in range(0, 1001, 50)]
    if len(set(reference_nodes)) != 21:
        return False

    section = str(mapdl.slist("ALL"))
    if "BEAM SECTION SUBTYPE:  RECTANGLE" not in section.upper():
        return False
    if abs(_listing_value(section, "Area") - 400.0) > 0.1:
        return False
    if abs(_listing_value(section, "Iyy") - 13333.3333) > 2.0:
        return False
    if abs(_listing_value(section, "Izz") - 13333.3333) > 2.0:
        return False

    material = str(mapdl.run("MPLIST,1,ALL"))
    material_values = {}
    for label in ("EX", "NUXY", "PRXY", "DENS"):
        match = re.search(
            rf"^\s*TEMP\s+{label}\s*$\s*([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)",
            material,
            flags=re.I | re.M,
        )
        if match:
            material_values[label] = float(match.group(1))
    if abs(material_values.get("EX", 0.0) - 210000.0) > 1.0:
        return False
    poisson = material_values.get("PRXY", material_values.get("NUXY", 0.0))
    if abs(poisson - 0.3) > 1e-6:
        return False
    if abs(material_values.get("DENS", 0.0) - 7.85e-9) > 1e-12:
        return False

    constraints = str(mapdl.dlist("ALL"))
    rows = re.findall(
        r"^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ)\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)",
        constraints,
        flags=re.M,
    )
    actual_constraints = {(int(node), label, float(value)) for node, label, value in rows}
    left, right = reference_nodes[0], reference_nodes[-1]
    expected_constraints = {
        (left, "UX", 0.0), (left, "UY", 0.0), (left, "UZ", 0.0),
        (right, "UY", 0.0), (right, "UZ", 0.0),
    }
    if actual_constraints != expected_constraints:
        return False

    midpoint = reference_nodes[10]
    loads = str(mapdl.flist("ALL"))
    force_rows = re.findall(
        r"^\s*(\d+)\s+(FX|FY|FZ|MX|MY|MZ)\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)",
        loads,
        flags=re.M,
    )
    if [(int(node), label, float(value)) for node, label, value in force_rows] != [(midpoint, "FY", -1000.0)]:
        return False

    mapdl.finish()
    mapdl.slashsolu()
    status = str(mapdl.run("/STATUS,SOLU")).upper()
    mapdl.finish()
    required_status = (
        "ANALYSIS TYPE", "TRANSIENT", "SOLUTION METHOD", "FULL",
        "NONLINEAR GEOMETRIC EFFECTS", "ON", "STEP CHANGE BOUNDARY CONDITIONS",
        "YES", "DATABASE OUTPUT CONTROLS", "ALL        ALL",
    )
    return all(token in status for token in required_status) and "RAYLEIGH DAMPING MULTIPLIERS" not in status


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    if not model_is_valid(mapdl):
        raise RuntimeError("beam model does not match the instruction")
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
    if len(history) != 50:
        raise RuntimeError("Transient result file must contain exactly 50 saved steps.")
    for index, (time_s, _) in enumerate(history, start=1):
        if abs(time_s - index * 0.001) > 1e-8:
            raise RuntimeError("Transient result times must be 0.001 through 0.050 s.")

    mapdl.set("LAST")
    final_time = float(mapdl.get_value("ACTIVE", 0, "SET", "TIME"))
    if abs(final_time - 0.05) > 1e-8:
        raise RuntimeError("Final transient result time must be 0.05 s.")
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


def passes_process_checks(mapdl, pred: dict, task_name: str) -> bool:
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
    if any(not is_nonempty_file(p) for p in REQUIRED_FILES):
        return False
    if not is_workbench_project(WBPJ_FILE):
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
        ok = passes_process_checks(mapdl, pred, task_name="task-12")
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
