#!/usr/bin/env python3
import csv
import re
from pathlib import Path


DESKTOP = Path("/home/user/Desktop")

REQUIRED_SPACES = ["Living", "Kitchen", "Bed 1", "Bed 2", "Bath"]
REQUIRED_HEADERS = ["SpaceName", "Level", "NetFloorArea"]
MIN_WALLS = 8
EXPECTED_STOREYS = 1


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
    if len(model.by_type("IfcBuildingStorey")) != EXPECTED_STOREYS:
        return False
    if len(model.by_type("IfcWall")) < MIN_WALLS:
        return False
    if model.by_type("IfcBuildingElementProxy") or model.by_type("IfcFurniture"):
        return False
    spaces = model.by_type("IfcSpace")
    if len(spaces) != len(REQUIRED_SPACES):
        return False
    names = [norm_text(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in spaces]
    if sorted(names) != sorted(norm_text(name) for name in REQUIRED_SPACES):
        return False
    if len(model.by_type("IfcDoor")) < 1:
        return False
    if len(model.by_type("IfcRelVoidsElement")) < 1 or len(model.by_type("IfcRelFillsElement")) < 1:
        return False
    return True


def check_csv(root):
    headers, rows = read_csv(root / "result.csv")
    if not headers or len(rows) != len(REQUIRED_SPACES):
        return False
    header_map = {header_key(header): header for header in headers}
    for header in REQUIRED_HEADERS:
        if header_key(header) not in header_map:
            return False
    by_space = {}
    for row in rows:
        row_by_key = {header_key(key): value for key, value in row.items()}
        name = norm_text(row_by_key.get(header_key("SpaceName"), ""))
        if name:
            by_space.setdefault(name, []).append(row_by_key)
    for space_name in REQUIRED_SPACES:
        matches = by_space.get(norm_text(space_name), [])
        if len(matches) != 1:
            return False
        row = matches[0]
        if norm_text(row.get(header_key("Level"), "")) != norm_text("Ground Floor"):
            return False
        if parse_float(row.get(header_key("NetFloorArea"), "")) <= 0:
            return False
    return True


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
