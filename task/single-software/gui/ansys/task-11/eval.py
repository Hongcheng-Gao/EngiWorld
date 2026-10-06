from pathlib import Path
import math
import re
import subprocess
import xml.etree.ElementTree as ET


DESKTOP = Path(r"C:\Users\user\Desktop")
EXEC_FILE = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
MAPDL_PORT = 50111
JOBNAME = "eval_wb_hertz"

WBPJ_FILE = DESKTOP / "wb_hertz.wbpj"
DB_FILE = DESKTOP / "wb_hertz.db"
RESULT_FILE = DESKTOP / "wb_hertz.rst"
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
            and '"DisplayText": "wb_hertz.wbpj"' in member_data
            and '"Location": "$(ProjectName).wbpj"' in member_data
        ):
            has_project_reference = True
        if object_name.startswith("/Schematic/") and class_type in {"System", "Component"}:
            if "Static Structural" in member_data or "Mechanical APDL" in member_data:
                has_static_system = True
    return has_project_reference and has_static_system


def allsel(mapdl) -> None:
    mapdl.run("ALLSEL,ALL")


def sorted_extreme(mapdl, item: str, component: str, maximum: bool) -> float:
    order = 1 if maximum else 0
    mapdl.run(f"NSORT,{item},{component},0,{order},ALL")
    label = "MAX" if maximum else "MIN"
    return float(mapdl.get_value("SORT", 0, label))


def reaction_fy_at_bottom(mapdl) -> float:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "Y", -10.001, -9.999)
    if int(mapdl.get_value("NODE", 0, "COUNT")) < 4:
        raise RuntimeError("plate bottom nodes not found")
    mapdl.fsum()
    value = float(mapdl.get_value("FSUM", 0, "ITEM", "FY"))
    allsel(mapdl)
    return value


def applied_force_fy(mapdl) -> float:
    """Sum external nodal force, including forces applied through a remote pilot node."""
    mapdl.prep7()
    allsel(mapdl)
    node_ids = [int(value) for value in mapdl.mesh.nnum]
    total = sum(float(mapdl.get_value("NODE", node, "F", "FY")) for node in node_ids)
    allsel(mapdl)
    return total


def geometry_is_valid(mapdl) -> bool:
    allsel(mapdl)
    nodes = mapdl.mesh.nodes
    if nodes is None or len(nodes) < 50:
        return False
    xs = [float(row[0]) for row in nodes]
    ys = [float(row[1]) for row in nodes]
    zs = [float(row[2]) for row in nodes]
    bounds = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    expected = (-50.0, 50.0, -10.0, 20.0, -50.0, 50.0)
    if any(abs(actual - target) > 0.05 for actual, target in zip(bounds, expected)):
        return False

    sphere_nodes = []
    surface_nodes = 0
    for x, y, z in zip(xs, ys, zs):
        if y <= 1e-5:
            continue
        radius = math.sqrt(x * x + (y - 10.0) ** 2 + z * z)
        sphere_nodes.append(radius)
        if 9.7 <= radius <= 10.05:
            surface_nodes += 1
    if len(sphere_nodes) < 20 or surface_nodes < 12:
        return False
    if max(sphere_nodes) > 10.05:
        return False
    return True


def mesh_resolution_is_valid(mapdl) -> bool:
    import numpy as np
    from scipy.spatial import cKDTree

    nodes = np.asarray(mapdl.mesh.nodes, dtype=float)
    plate_contact = nodes[
        (nodes[:, 1] <= 0.0)
        & (nodes[:, 1] > -3.0)
        & (np.abs(nodes[:, 0]) < 4.0)
        & (np.abs(nodes[:, 2]) < 4.0)
    ]
    plate_far = nodes[
        (nodes[:, 1] <= 0.0)
        & ((np.abs(nodes[:, 0]) > 35.0) | (np.abs(nodes[:, 2]) > 35.0))
    ]
    if len(plate_contact) < 4 or len(plate_far) < 4:
        return False

    contact_nearest = cKDTree(plate_contact).query(plate_contact, k=2)[0][:, 1]
    far_nearest = cKDTree(plate_far).query(plate_far, k=2)[0][:, 1]
    contact_median = float(np.median(contact_nearest))
    far_upper_quartile = float(np.quantile(far_nearest, 0.75))
    return (
        0.15 <= contact_median <= 0.45
        and 1.4 <= far_upper_quartile <= 2.6
        and far_upper_quartile >= 4.0 * contact_median
    )


def selected_nodes_at_y(mapdl, low: float, high: float) -> list[int]:
    allsel(mapdl)
    mapdl.nsel("S", "LOC", "Y", low, high)
    node_ids = [int(value) for value in mapdl.mesh.nnum]
    if not node_ids:
        raise RuntimeError("required Y-plane nodes not found")
    return node_ids


def selected_constraint_map(mapdl) -> dict[int, set[str]]:
    listing = str(mapdl.dlist("ALL"))
    rows = re.findall(
        r"^\s*(\d+)\s+(UX|UY|UZ|ROTX|ROTY|ROTZ)\s+([-+0-9.Ee]+)",
        listing,
        flags=re.M,
    )
    result = {}
    for node, label, value in rows:
        if abs(float(value)) > 1e-10:
            raise RuntimeError("nonzero displacement constraint found")
        result.setdefault(int(node), set()).add(label)
    return result


def model_setup_is_valid(mapdl) -> bool:
    etlist = str(mapdl.etlist()).upper()
    solid_names = ("SOLID185", "SOLID186", "SOLID187", "SOLID285")
    contact_names = ("CONTA173", "CONTA174", "CONTA175")
    present_solids = [name for name in solid_names if name in etlist]
    present_contacts = [name for name in contact_names if name in etlist]
    if not present_solids or not present_contacts or "TARGE170" not in etlist:
        return False
    for contact_name in present_contacts:
        contact_block = re.search(
            rf"ELEMENT TYPE\s+\d+\s+IS {contact_name}[\s\S]*?KEYOPT\(\s*1-\s*6\)=\s*([0-9\s-]+)",
            etlist,
        )
        if not contact_block:
            return False
        first_six = [int(value) for value in contact_block.group(1).split()[:6]]
        if len(first_six) != 6 or first_six[1] not in (0, 1):
            return False

    type_ids = {}
    for name in (*present_solids, "TARGE170", *present_contacts):
        match = re.search(rf"ELEMENT TYPE\s+(\d+)\s+IS {name}", etlist)
        if not match:
            return False
        type_ids[name] = int(match.group(1))

    solid_element_count = 0
    for name in present_solids:
        allsel(mapdl)
        mapdl.esel("S", "TYPE", "", type_ids[name])
        solid_element_count += int(mapdl.get_value("ELEM", 0, "COUNT"))
    if solid_element_count < 1:
        allsel(mapdl)
        return False

    for name in ("TARGE170", *present_contacts):
        allsel(mapdl)
        mapdl.esel("S", "TYPE", "", type_ids[name])
        if int(mapdl.get_value("ELEM", 0, "COUNT")) < 1:
            allsel(mapdl)
            return False
    allsel(mapdl)

    material = str(mapdl.run("MPLIST,ALL,ALL"))
    ex_values = [float(value) for value in re.findall(r"^\s*TEMP\s+EX\s*$\s*([-+0-9.Ee]+)", material, flags=re.I | re.M)]
    poisson_values = [float(value) for value in re.findall(r"^\s*TEMP\s+(?:PRXY|NUXY)\s*$\s*([-+0-9.Ee]+)", material, flags=re.I | re.M)]
    if not ex_values or any(abs(value - 210000.0) > 1.0 for value in ex_values):
        return False
    if not poisson_values or any(abs(value - 0.3) > 1e-6 for value in poisson_values):
        return False
    if re.search(r"^\s*TEMP\s+MU\s*$", material, flags=re.I | re.M):
        return False
    real_constants = str(mapdl.run("RLIST,ALL"))
    if "COEFFICIENT OF FRICTION" in real_constants.upper():
        return False

    bottom_nodes = selected_nodes_at_y(mapdl, -10.001, -9.999)
    bottom_constraints = selected_constraint_map(mapdl)
    if set(bottom_constraints) != set(bottom_nodes):
        return False
    if any(labels != {"UX", "UY", "UZ"} for labels in bottom_constraints.values()):
        return False

    allsel(mapdl)
    all_constraints = selected_constraint_map(mapdl)
    sphere_constraints = {
        node: labels for node, labels in all_constraints.items()
        if node not in set(bottom_nodes)
    }
    # A single remote point, two minimally constrained sphere nodes, or a
    # larger symmetry-style set are all valid ways to remove lateral modes.
    if not sphere_constraints:
        return False
    if any("UY" in labels or not labels.issubset({"UX", "UZ"}) for labels in sphere_constraints.values()):
        return False
    constrained_dofs = set().union(*sphere_constraints.values())
    if not {"UX", "UZ"}.issubset(constrained_dofs):
        return False
    allsel(mapdl)

    mapdl.finish()
    mapdl.slashsolu()
    status = str(mapdl.run("/STATUS,SOLU")).upper()
    mapdl.finish()
    return (
        "ANALYSIS TYPE" in status
        and "STATIC (STEADY-STATE)" in status
        and "NONLINEAR GEOMETRIC EFFECTS" in status
        and re.search(r"NONLINEAR GEOMETRIC EFFECTS[^\n]*ON", status) is not None
    )


def extract_predictions(mapdl) -> dict:
    mapdl.resume(DB_FILE.stem, "db")
    if not geometry_is_valid(mapdl):
        raise RuntimeError("sphere/plate geometry does not match the instruction")
    if not mesh_resolution_is_valid(mapdl):
        raise RuntimeError("contact-region or far-field mesh size does not match the instruction")
    if not model_setup_is_valid(mapdl):
        raise RuntimeError("contact, material, or support setup does not match the instruction")

    allsel(mapdl)
    total_elements = int(mapdl.get_value("ELEM", 0, "COUNT"))
    top_force = applied_force_fy(mapdl)

    allsel(mapdl)
    mapdl.post1()
    mapdl.file(RESULT_FILE.stem, RESULT_FILE.suffix.lstrip("."))
    mapdl.set("LAST")
    final_time = float(mapdl.get_value("ACTIVE", 0, "SET", "TIME"))
    min_uy = sorted_extreme(mapdl, "U", "Y", maximum=False)
    max_usum = sorted_extreme(mapdl, "U", "SUM", maximum=True)
    max_stress = sorted_extreme(mapdl, "S", "EQV", maximum=True)
    reaction = reaction_fy_at_bottom(mapdl)

    allsel(mapdl)
    mapdl.run("ETABLE,CPRESS,CONT,PRES")
    mapdl.run("ESORT,ETAB,CPRESS,0,1")
    max_contact_pressure = float(mapdl.get_value("SORT", 0, "MAX"))
    allsel(mapdl)

    return {
        "total_elements": total_elements,
        "applied_top_force_fy_n": top_force,
        "bottom_reaction_fy_n": reaction,
        "final_time": final_time,
        "min_uy_mm": min_uy,
        "max_usum_mm": max_usum,
        "max_von_mises_mpa": max_stress,
        "max_contact_pressure_mpa": max_contact_pressure,
    }


def predictions_are_valid(predictions: dict) -> bool:
    if abs(predictions["applied_top_force_fy_n"] + 500.0) > 5.0:
        return False
    if abs(abs(predictions["bottom_reaction_fy_n"]) - 500.0) > 10.0:
        return False
    if abs(predictions["final_time"] - 1.0) > 1e-6:
        return False
    if not (-1.0 < predictions["min_uy_mm"] < -1e-5):
        return False
    if not (1e-5 < predictions["max_usum_mm"] < 2.0):
        return False
    if not (1e-3 < predictions["max_von_mises_mpa"] < 10000.0):
        return False
    if not (1e-3 < predictions["max_contact_pressure_mpa"] < 10000.0):
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
