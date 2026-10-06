from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


DESKTOP = Path(r"C:\Users\user\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50120
JOBNAME = "eval_wb_conduction"

WBPJ_FILE = DESKTOP / "wb_conduction.wbpj"
DB_FILE = DESKTOP / "wb_conduction.db"
RESULT_FILE = DESKTOP / "wb_conduction.rth"
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
    has_thermal_system = False
    for obj in root.findall(".//Object"):
        class_type = (obj.findtext("class-type") or "").strip()
        member_data = (obj.findtext("member-data") or "").strip()
        object_name = obj.attrib.get("Name", "")
        if (
            class_type == "FileReference"
            and '"DisplayText": "wb_conduction.wbpj"' in member_data
            and '"Location": "$(ProjectName).wbpj"' in member_data
        ):
            has_project_reference = True
        if object_name.startswith("/Schematic/") and class_type in {"System", "Component"}:
            if "Steady-State Thermal" in member_data or "Mechanical APDL" in member_data:
                has_thermal_system = True
    return has_project_reference and has_thermal_system


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def nodes_at_x(mapdl, x: float, tol: float) -> list[int]:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", x - tol, x + tol)
    node_ids = [int(value) for value in mapdl.mesh.nnum]
    allsel(mapdl)
    if not node_ids:
        raise RuntimeError(f"no nodes found at X={x} mm")
    return node_ids


def sorted_temperature(mapdl, maximum: bool) -> float:
    mapdl.run(f"NSORT,TEMP,,0,{1 if maximum else 0},ALL")
    return float(mapdl.get_value("SORT", 0, "MAX" if maximum else "MIN"))


def model_is_valid(mapdl) -> dict | None:
    allsel(mapdl)
    nodes = mapdl.mesh.nodes
    if nodes is None or not (12 <= len(nodes) <= 2_000_000):
        return None
    coordinates = [[float(row[axis]) for row in nodes] for axis in range(3)]
    bounds = [(min(values), max(values)) for values in coordinates]
    unit_systems = (
        {"length": 100.0, "width": 10.0, "conductivity": 0.05, "tol": 1e-4},
        {"length": 0.1, "width": 0.01, "conductivity": 50.0, "tol": 1e-7},
    )
    units = next(
        (
            candidate
            for candidate in unit_systems
            if all(
                abs(actual - expected) <= candidate["tol"]
                for pair, target in zip(
                    bounds,
                    (
                        (0.0, candidate["length"]),
                        (0.0, candidate["width"]),
                        (0.0, candidate["width"]),
                    ),
                )
                for actual, expected in zip(pair, target)
            )
        ),
        None,
    )
    if units is None:
        return None

    x_sections = (0.0, units["length"] / 2.0, units["length"])
    section_nodes = {
        x: nodes_at_x(mapdl, x, units["tol"])
        for x in x_sections
    }
    if any(len(node_ids) < 4 for node_ids in section_nodes.values()):
        return None
    if not (2 <= int(mapdl.get_value("ELEM", 0, "COUNT")) <= 2_000_000):
        return None
    element_types = str(mapdl.etlist()).upper()
    if not any(name in element_types for name in ("SOLID70", "SOLID90", "SOLID278", "SOLID279")):
        return None

    material = str(mapdl.run("MPLIST,1,KXX"))
    conductivity_match = re.search(
        r"^\s*TEMP\s+KXX\s*$\s*([-+0-9.Ee]+)",
        material,
        flags=re.I | re.M,
    )
    if conductivity_match is None:
        return None
    conductivity = float(conductivity_match.group(1))
    if abs(conductivity - units["conductivity"]) > max(1e-8, units["conductivity"] * 1e-6):
        return None

    rows = re.findall(
        r"^\s*(\d+)\s+TEMP\s+([-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?)",
        str(mapdl.dlist("ALL")),
        flags=re.M,
    )
    actual = {(int(node), float(value)) for node, value in rows}
    expected = {(node, 100.0) for node in section_nodes[x_sections[0]]}
    expected.update((node, 20.0) for node in section_nodes[x_sections[2]])
    if actual != expected:
        return None
    return {"length": units["length"], "mid_x": x_sections[1], "tol": units["tol"]}


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    model = model_is_valid(mapdl)
    if model is None:
        raise RuntimeError("thermal block model does not match the instruction")

    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set("LAST")
    node_ids = [int(value) for value in mapdl.mesh.nnum]
    coordinates = mapdl.mesh.nodes
    temperature_errors = [
        abs(
            float(mapdl.get_value("NODE", node, "TEMP"))
            - (100.0 - 80.0 * float(row[0]) / model["length"])
        )
        for node, row in zip(node_ids, coordinates)
    ]
    return {
        "temps_x50_c": [
            float(mapdl.get_value("NODE", node, "TEMP"))
            for node in nodes_at_x(mapdl, model["mid_x"], model["tol"])
        ],
        "max_linear_field_error_c": max(temperature_errors),
        "temp_max_c": sorted_temperature(mapdl, maximum=True),
        "temp_min_c": sorted_temperature(mapdl, maximum=False),
    }


def predictions_are_valid(predictions: dict) -> bool:
    values = predictions["temps_x50_c"]
    if len(values) < 4 or any(abs(value - 60.0) > 0.1 for value in values):
        return False
    return (
        predictions["max_linear_field_error_c"] <= 0.1
        and
        abs(predictions["temp_max_c"] - 100.0) <= 0.1
        and abs(predictions["temp_min_c"] - 20.0) <= 0.1
    )


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
