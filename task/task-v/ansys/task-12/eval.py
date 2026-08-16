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
REQUIRED_FILES = (WBPJ_FILE, DB_FILE, RESULT_FILE)


def is_nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


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


def node_at(mapdl, x: float, tol: float = 1e-4) -> int:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    mapdl.nsel("R", "LOC", "Y", -tol, tol)
    mapdl.nsel("R", "LOC", "Z", -tol, tol)
    node = int(mapdl.get_value("NODE", 0, "NUM", "MIN"))
    allsel(mapdl)
    if node < 1:
        raise RuntimeError(f"node at X={x} mm not found")
    return node


def model_is_valid(mapdl) -> bool:
    allsel(mapdl)
    nodes = mapdl.mesh.nodes
    if nodes is None or not (21 <= len(nodes) <= 61):
        return False
    xs = [float(row[0]) for row in nodes]
    ys = [float(row[1]) for row in nodes]
    zs = [float(row[2]) for row in nodes]
    if abs(min(xs)) > 1e-4 or abs(max(xs) - 1000.0) > 1e-4:
        return False
    if max(abs(value) for value in ys + zs) > 1e-4:
        return False
    reference_nodes = [node_at(mapdl, x) for x in range(0, 1001, 50)]
    if len(set(reference_nodes)) != 21:
        return False
    if int(mapdl.get_value("ELEM", 0, "COUNT")) != 20:
        return False
    element_types = str(mapdl.etlist()).upper()
    if not any(name in element_types for name in ("BEAM188", "BEAM189")):
        return False

    section = str(mapdl.slist("ALL"))
    area = re.search(r"^\s*Area\s*=\s*([-+0-9.Ee]+)", section, flags=re.I | re.M)
    iyy = re.search(r"^\s*Iyy\s*=\s*([-+0-9.Ee]+)", section, flags=re.I | re.M)
    izz = re.search(r"^\s*Izz\s*=\s*([-+0-9.Ee]+)", section, flags=re.I | re.M)
    if (
        "BEAM SECTION SUBTYPE:  RECTANGLE" not in section.upper()
        or not area or not iyy or not izz
        or abs(float(area.group(1)) - 400.0) > 0.1
        or abs(float(iyy.group(1)) - 13333.3333) > 2.0
        or abs(float(izz.group(1)) - 13333.3333) > 2.0
    ):
        return False

    material = str(mapdl.run("MPLIST,1,ALL"))
    def material_value(label: str) -> float:
        match = re.search(
            rf"^\s*TEMP\s+{label}\s*$\s*([-+0-9.Ee]+)",
            material,
            flags=re.I | re.M,
        )
        return float(match.group(1)) if match else float("nan")
    if abs(material_value("EX") - 210000.0) > 1.0:
        return False
    if abs(material_value("PRXY") - 0.3) > 1e-6:
        return False
    if abs(material_value("DENS") - 7.85e-9) > 1e-12:
        return False

    constraints = str(mapdl.dlist("ALL"))
    constraint_rows = re.findall(
        r"^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ)\s+([-+0-9.Ee]+)",
        constraints,
        flags=re.M,
    )
    left, right = node_at(mapdl, 0.0), node_at(mapdl, 1000.0)
    expected_constraints = {
        (left, "UX", 0.0), (left, "UY", 0.0), (left, "UZ", 0.0),
        (right, "UY", 0.0), (right, "UZ", 0.0),
    }
    if {(int(n), label, float(v)) for n, label, v in constraint_rows} != expected_constraints:
        return False

    mid_node = node_at(mapdl, 500.0)
    force_fy = float(mapdl.get_value("NODE", mid_node, "F", "FY"))
    if abs(force_fy + 1000.0) > 1e-6:
        return False
    force_rows = re.findall(
        r"^\s*(\d+)\s+(FX|FY|FZ|MX|MY|MZ)\s+([-+0-9.Ee]+)",
        str(mapdl.flist("ALL")),
        flags=re.M,
    )
    if [(int(n), label, float(v)) for n, label, v in force_rows] != [(mid_node, "FY", -1000.0)]:
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

    mid_node = node_at(mapdl, 500.0)
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))

    history = []
    for substep in range(1, 52):
        try:
            mapdl.set(1, substep)
        except Exception:
            break
        time_s = float(mapdl.get_value("ACTIVE", 0, "SET", "TIME"))
        uy = float(mapdl.get_value("NODE", mid_node, "U", "Y"))
        history.append((time_s, uy))

    mapdl.set("LAST")
    return {
        "history": history,
        "final_time_s": float(mapdl.get_value("ACTIVE", 0, "SET", "TIME")),
        "final_midspan_uy_mm": float(mapdl.get_value("NODE", mid_node, "U", "Y")),
        "peak_midspan_uy_mm": min(value for _, value in history),
    }


def predictions_are_valid(predictions: dict) -> bool:
    history = predictions["history"]
    if len(history) != 50:
        return False
    for index, (time_s, _) in enumerate(history, start=1):
        if abs(time_s - index * 0.001) > 1e-8:
            return False
    if abs(predictions["final_time_s"] - 0.05) > 1e-8:
        return False
    if not (-100.0 < predictions["peak_midspan_uy_mm"] < -0.01):
        return False
    if not (-100.0 < predictions["final_midspan_uy_mm"] < -0.01):
        return False
    return True


def kill_ansys_related() -> None:
    for image in ("ANSYS261.exe", "ANSYS.exe"):
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/IM", image],
                capture_output=True,
                creationflags=0x08000000,
            )
        except Exception:
            pass


def evaluate() -> bool:
    kill_ansys_related()
    if any(not is_nonempty_file(path) for path in REQUIRED_FILES):
        return False
    if not is_workbench_project(WBPJ_FILE):
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
        return predictions_are_valid(extract_predictions(mapdl))
    except Exception:
        return False
    finally:
        if mapdl is not None:
            try:
                mapdl.exit()
            except Exception:
                pass


def main() -> None:
    print("True" if evaluate() else "False")


if __name__ == "__main__":
    main()
