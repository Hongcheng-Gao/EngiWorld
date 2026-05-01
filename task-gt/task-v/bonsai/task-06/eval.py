#!/usr/bin/env python3
import csv
import re
from collections import Counter
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_FILES = ("result.ifc", "result.csv")
EXPECTED_SPACES = {"LIVING", "KITCHEN", "BEDROOM", "BATH"}
EXPECTED_COUNTS = {
    "IfcProject": 1,
    "IfcBuildingStorey": 1,
    "IfcSpace": 4,
    "IfcWall": 7,
    "IfcDoor": 3,
    "IfcWindow": 4,
    "IfcSlab": 1,
    "IfcBuildingElementProxy": 0,
}
EXPECTED_CSV_HEADER = ["GlobalId", "Class", "TypeName", "MaterialSummary", "Storey"]
EXPECTED_CSV_CLASS_COUNTS = {"IfcWall": 7, "IfcDoor": 3, "IfcWindow": 4}
EXPECTED_CSV_MATERIAL_COUNTS = {
    "Brick | Insulation | Gypsum": 7,
    "Timber": 3,
    "Aluminium": 4,
}
WALL_MATERIALS = ["BRICK", "INSULATION", "GYPSUM"]


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text.strip()).upper()


def require_files(root):
    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.is_file():
            return False
        if rel.endswith(".ifc") and path.stat().st_size < 100:
            return False
        if rel.endswith(".csv") and path.stat().st_size < 1:
            return False
    return True


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return None, None
    header = [cell.strip() for cell in rows[0]]
    body = []
    for row in rows[1:]:
        if not any(str(cell).strip() for cell in row):
            continue
        padded = row + [""] * max(0, len(header) - len(row))
        body.append({header[i]: padded[i].strip() for i in range(len(header))})
    return header, body


def material_sequences(product):
    sequences = []
    for rel in getattr(product, "HasAssociations", []) or []:
        if not rel.is_a("IfcRelAssociatesMaterial"):
            continue
        mat = rel.RelatingMaterial
        if mat.is_a("IfcMaterial"):
            sequences.append([norm(mat.Name)])
        elif mat.is_a("IfcMaterialLayerSetUsage"):
            layers = mat.ForLayerSet.MaterialLayers or []
            sequences.append([norm(layer.Material.Name) for layer in layers if layer.Material])
        elif mat.is_a("IfcMaterialLayerSet"):
            layers = mat.MaterialLayers or []
            sequences.append([norm(layer.Material.Name) for layer in layers if layer.Material])
        elif mat.is_a("IfcMaterialList"):
            sequences.append([norm(item.Name) for item in mat.Materials if item])
    return sequences


def has_sequence(product, expected):
    return any(sequence == expected for sequence in material_sequences(product))


def has_material(product, expected):
    wanted = norm(expected)
    return any(wanted in sequence for sequence in material_sequences(product))


def check_ifc(root):
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if str(model.schema).upper() != "IFC4":
        return None
    for cls, count in EXPECTED_COUNTS.items():
        if len(model.by_type(cls)) != count:
            return None

    storey = model.by_type("IfcBuildingStorey")[0]
    if getattr(storey, "Name", None) != "Level 00":
        return None

    space_names = {norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")}
    if space_names != EXPECTED_SPACES:
        return None

    for wall in model.by_type("IfcWall"):
        if not has_sequence(wall, WALL_MATERIALS):
            return None
    for door in model.by_type("IfcDoor"):
        if not has_material(door, "Timber"):
            return None
    for window in model.by_type("IfcWindow"):
        if not has_material(window, "Aluminium"):
            return None

    return {
        element.GlobalId: element.is_a()
        for cls in EXPECTED_CSV_CLASS_COUNTS
        for element in model.by_type(cls)
    }


def check_csv(root, ifc_elements):
    header, rows = read_csv(root / "result.csv")
    if header != EXPECTED_CSV_HEADER:
        return False
    if len(rows) != 14:
        return False

    row_ids = [row.get("GlobalId", "") for row in rows]
    if len(set(row_ids)) != len(row_ids):
        return False
    if set(row_ids) != set(ifc_elements):
        return False

    if Counter(row.get("Class", "") for row in rows) != EXPECTED_CSV_CLASS_COUNTS:
        return False
    if Counter(row.get("MaterialSummary", "") for row in rows) != EXPECTED_CSV_MATERIAL_COUNTS:
        return False
    for row in rows:
        if row.get("Class") != ifc_elements[row["GlobalId"]]:
            return False
        if row.get("Storey") != "Level 00":
            return False
    return True


def main():
    try:
        root = DESKTOP
        if not root.is_dir() or not require_files(root):
            emit(False)
        ifc_elements = check_ifc(root)
        emit(bool(ifc_elements) and check_csv(root, ifc_elements))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
