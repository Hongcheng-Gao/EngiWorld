#!/usr/bin/env python3
import csv
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

EXPECTED_STOREY_ELEMENTS = {
    "Ground Floor": ["GF South Wall", "GF North Wall", "GF West Wall", "GF East Wall", "GF Slab"],
    "First Floor": ["FF South Wall", "FF North Wall", "FF West Wall", "FF East Wall", "FF Slab"],
}
EXPECTED_CSV_ROWS = {
    "Ground Floor": {"ElementCount": 5, "TotalSlabArea": 63.0},
    "First Floor": {"ElementCount": 5, "TotalSlabArea": 63.0},
}
REQUIRED_HEADERS = ["Storey", "ElementCount", "TotalSlabArea"]


def emit(ok):
    print("true" if ok else "false")
    raise SystemExit(0)


def norm_text(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).casefold()


def header_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def parse_float(value):
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    return float(text)


def read_csv(path):
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return None, None
    try:
        dialect = csv.Sniffer().sniff(text[:2048])
    except Exception:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    if not rows:
        return None, None
    headers = [cell.strip() for cell in rows[0]]
    body = []
    for raw in rows[1:]:
        if not any(cell.strip() for cell in raw):
            continue
        raw = raw + [""] * max(0, len(headers) - len(raw))
        body.append({headers[i]: raw[i].strip() for i in range(len(headers))})
    return headers, body


def check_outputs(root):
    if not (root / "result.ifc").is_file() or (root / "result.ifc").stat().st_size < 100:
        return False
    if not (root / "result.csv").is_file() or (root / "result.csv").stat().st_size < 1:
        return False
    return True


def check_ifc(root):
    import ifcopenshell

    model = ifcopenshell.open(str(root / "result.ifc"))
    if model.schema.upper() != "IFC4":
        return False
    if len(model.by_type("IfcProject")) != 1 or len(model.by_type("IfcSite")) != 1:
        return False
    if len(model.by_type("IfcBuilding")) != 1:
        return False
    storeys = model.by_type("IfcBuildingStorey")
    if len(storeys) != len(EXPECTED_STOREY_ELEMENTS):
        return False
    storey_by_name = {norm_text(getattr(storey, "Name", "")): storey for storey in storeys}
    for storey_name in EXPECTED_STOREY_ELEMENTS:
        if norm_text(storey_name) not in storey_by_name:
            return False
    if len(model.by_type("IfcWall")) != 8 or len(model.by_type("IfcSlab")) != 2:
        return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    contained = {norm_text(name): [] for name in EXPECTED_STOREY_ELEMENTS}
    for rel in model.by_type("IfcRelContainedInSpatialStructure"):
        structure = getattr(rel, "RelatingStructure", None)
        if structure is None or not structure.is_a("IfcBuildingStorey"):
            continue
        key = norm_text(getattr(structure, "Name", ""))
        if key in contained:
            contained[key].extend(getattr(rel, "RelatedElements", []) or [])
    for storey_name, expected_names in EXPECTED_STOREY_ELEMENTS.items():
        elements = contained[norm_text(storey_name)]
        actual_names = sorted(norm_text(getattr(element, "Name", "")) for element in elements)
        if actual_names != sorted(norm_text(name) for name in expected_names):
            return False
        if sorted(element.is_a() for element in elements) != sorted(["IfcWall"] * 4 + ["IfcSlab"]):
            return False
    return True


def check_csv(root):
    headers, rows = read_csv(root / "result.csv")
    if not headers or len(rows) != len(EXPECTED_CSV_ROWS):
        return False
    header_map = {header_key(header): header for header in headers}
    for header in REQUIRED_HEADERS:
        if header_key(header) not in header_map:
            return False
    seen = set()
    for row in rows:
        by_key = {header_key(key): value for key, value in row.items()}
        storey = by_key.get(header_key("Storey"), "")
        matched = None
        for expected_name in EXPECTED_CSV_ROWS:
            if norm_text(storey) == norm_text(expected_name):
                matched = expected_name
                break
        if matched is None or matched in seen:
            return False
        seen.add(matched)
        expected = EXPECTED_CSV_ROWS[matched]
        if int(parse_float(by_key.get(header_key("ElementCount"), ""))) != expected["ElementCount"]:
            return False
        if abs(parse_float(by_key.get(header_key("TotalSlabArea"), "")) - expected["TotalSlabArea"]) > 0.1:
            return False
    return seen == set(EXPECTED_CSV_ROWS)


def main():
    try:
        root = DESKTOP
        emit(root.is_dir() and check_outputs(root) and check_ifc(root) and check_csv(root))
    except SystemExit:
        raise
    except Exception:
        emit(False)


if __name__ == "__main__":
    main()
