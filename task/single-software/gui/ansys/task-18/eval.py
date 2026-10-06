from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


DESKTOP = Path(r"C:\Users\user\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50118
JOBNAME = "eval_wb_plate"

WBPJ_FILE = DESKTOP / "wb_plate.wbpj"
DB_FILE = DESKTOP / "wb_plate.db"
RESULT_FILE = DESKTOP / "wb_plate.rst"
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
    has_static_system = False
    for obj in root.findall(".//Object"):
        class_type = (obj.findtext("class-type") or "").strip()
        member_data = (obj.findtext("member-data") or "").strip()
        object_name = obj.attrib.get("Name", "")
        if (
            class_type == "FileReference"
            and '"DisplayText": "wb_plate.wbpj"' in member_data
            and '"Location": "$(ProjectName).wbpj"' in member_data
        ):
            has_project_reference = True
        if object_name.startswith("/Schematic/") and class_type in {"System", "Component"}:
            if "Static Structural" in member_data or "Mechanical APDL" in member_data:
                has_static_system = True
    return has_project_reference and has_static_system


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def node_near(mapdl, x: float, y: float) -> int:
    allsel(mapdl)
    node_ids = [int(value) for value in mapdl.mesh.nnum]
    coordinates = mapdl.mesh.nodes
    node, row = min(
        zip(node_ids, coordinates),
        key=lambda item: (float(item[1][0]) - x) ** 2 + (float(item[1][1]) - y) ** 2,
    )
    distance = ((float(row[0]) - x) ** 2 + (float(row[1]) - y) ** 2) ** 0.5
    if distance > 4.0 or abs(float(row[2])) > 1e-5:
        raise RuntimeError("no plate node sufficiently near the center")
    return node


def sorted_extreme(mapdl, item: str, component: str, maximum: bool) -> float:
    mapdl.run(f"NSORT,{item},{component},0,{1 if maximum else 0},ALL")
    return float(mapdl.get_value("SORT", 0, "MAX" if maximum else "MIN"))


def model_is_valid(mapdl) -> bool:
    allsel(mapdl)
    nodes = mapdl.mesh.nodes
    if nodes is None or not (200 <= len(nodes) <= 10_000):
        return False
    xs = [float(row[0]) for row in nodes]
    ys = [float(row[1]) for row in nodes]
    zs = [float(row[2]) for row in nodes]
    if (
        abs(min(xs)) > 1e-4
        or abs(max(xs) - 100.0) > 1e-4
        or abs(min(ys)) > 1e-4
        or abs(max(ys) - 100.0) > 1e-4
        or max(abs(value) for value in zs) > 1e-5
    ):
        return False
    element_count = int(mapdl.get_value("ELEM", 0, "COUNT"))
    if not (200 <= element_count <= 1_600):
        return False
    if not any(name in str(mapdl.etlist()).upper() for name in ("SHELL181", "SHELL281")):
        return False

    material = str(mapdl.run("MPLIST,1,ALL"))
    ex = re.search(r"^\s*TEMP\s+EX\s*$\s*([-+0-9.Ee]+)", material, flags=re.I | re.M)
    poisson = re.search(r"^\s*TEMP\s+(?:PRXY|NUXY)\s*$\s*([-+0-9.Ee]+)", material, flags=re.I | re.M)
    if not ex or abs(float(ex.group(1)) - 210000.0) > 1.0:
        return False
    if not poisson or abs(float(poisson.group(1)) - 0.3) > 1e-6:
        return False

    section = str(mapdl.slist(1))
    if not re.search(r"Total Thickness\s*=\s*1\.000000", section, flags=re.I):
        return False

    node_ids = [int(value) for value in mapdl.mesh.nnum]
    edge_nodes = {
        node
        for node, x, y in zip(node_ids, xs, ys)
        if min(abs(x), abs(x - 100.0), abs(y), abs(y - 100.0)) <= 1e-4
    }
    constraint_rows = re.findall(
        r"^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ)\s+([-+0-9.Ee]+)",
        str(mapdl.dlist("ALL")),
        flags=re.M,
    )
    if any(abs(float(value)) > 1e-10 for _, _, value in constraint_rows):
        return False
    constrained = {label: set() for label in ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ")}
    for node, label, _ in constraint_rows:
        constrained[label].add(int(node))
    if constrained["UZ"] != edge_nodes:
        return False
    if not (1 <= len(constrained["UX"]) <= 3 and 1 <= len(constrained["UY"]) <= 3):
        return False
    if not constrained["UX"].issubset(edge_nodes) or not constrained["UY"].issubset(edge_nodes):
        return False
    if constrained["ROTX"] or constrained["ROTY"] or constrained["ROTZ"]:
        return False

    load_rows = re.findall(
        r"^\s*(\d+)\s+(\d+)\s+\d+\s+([-+0-9.Ee]+)\s+[-+0-9.Ee]+\s*$",
        str(mapdl.sflist("ALL")),
        flags=re.M,
    )
    loaded_elements = {}
    for element, load_key, value in load_rows:
        if int(element) in loaded_elements:
            return False
        loaded_elements[int(element)] = (int(load_key), float(value))
    return (
        len(loaded_elements) == element_count
        and all(abs(abs(value) - 0.1) <= 1e-8 for _, value in loaded_elements.values())
    )


def edge_reaction_fz(mapdl) -> tuple[int, float]:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "X", -1e-4, 1e-4)
    mapdl.nsel("A", "LOC", "X", 99.9999, 100.0001)
    mapdl.nsel("A", "LOC", "Y", -1e-4, 1e-4)
    mapdl.nsel("A", "LOC", "Y", 99.9999, 100.0001)
    node_ids = [int(value) for value in mapdl.mesh.nnum]
    count = len(node_ids)
    reaction = sum(
        float(mapdl.get_value("NODE", node, "RF", "FZ")) for node in node_ids
    )
    allsel(mapdl)
    return count, reaction


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    if not model_is_valid(mapdl):
        raise RuntimeError("plate model does not match the instruction")

    center = node_near(mapdl, 50.0, 50.0)
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set("LAST")
    edge_count, reaction = edge_reaction_fz(mapdl)
    return {
        "edge_node_count": edge_count,
        "edge_reaction_fz_n": reaction,
        "center_uz_mm": float(mapdl.get_value("NODE", center, "U", "Z")),
        "min_uz_mm": sorted_extreme(mapdl, "U", "Z", maximum=False),
        "max_von_mises_mpa": sorted_extreme(mapdl, "S", "EQV", maximum=True),
    }


def predictions_are_valid(predictions: dict) -> bool:
    if predictions["edge_node_count"] < 40:
        return False
    if abs(predictions["edge_reaction_fz_n"] - 1000.0) > 2.0:
        return False
    if not (-5.0 < predictions["center_uz_mm"] < -0.5):
        return False
    if not (-5.0 < predictions["min_uz_mm"] < -0.5):
        return False
    return 10.0 < predictions["max_von_mises_mpa"] < 1000.0


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
