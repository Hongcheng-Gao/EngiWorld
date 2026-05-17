#!/usr/bin/env python3
import csv
import re
import sys
try:
    import fitz
except ImportError:
    import pymupdf as fitz
try:
    from pdfminer.high_level import extract_text as _pdfminer_extract_text
    from pdfminer.pdfpage import PDFPage as _PDFPage
    _HAS_PDFMINER = True
except ImportError:
    _HAS_PDFMINER = False

from pathlib import Path

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


SPEC = {'title': 'Corner Bakery and Cafe Drawing Set and Room Schedule', 'starts_from_init': False, 'required_outputs': {'result.ifc': 500, 'result.pdf': 500, 'result.txt': 20}, 'schema': 'IFC4', 'storey_count': 1, 'space_names': ['CAFE', 'COUNTER', 'BAKERY', 'DISHWASH', 'DRY-STORE', 'COLD-STORE', 'STAFF', 'WC'], 'min_wall_count': 12, 'slab_count': 1, 'roof_count': 1, 'bbox_exact': {'min': [0.0, 0.0, 0.0], 'max': [14.0, 8.0, 3.6]}, 'bbox_tolerance': 0.1, 'wall_thickness_range': [0.1, 0.2], 'wall_height_range': [3.0, 3.3], 'slab_bbox': {'min': [0.0, 0.0, 0.0], 'max': [14.0, 8.0, 0.25]}, 'slab_bbox_tolerance': 0.1, 'roof_bbox': {'min': [0.0, 0.0, 3.4], 'max': [14.0, 8.0, 3.6]}, 'roof_bbox_tolerance': 0.1, 'space_boxes': {'CAFE': {'min': [0.0, 0.0, 0.0], 'max': [6.0, 5.0, 3.0], 'area': 30.0}, 'COUNTER': {'min': [6.0, 1.0, 0.0], 'max': [8.0, 4.0, 3.0], 'area': 6.0}, 'BAKERY': {'min': [8.0, 0.0, 0.0], 'max': [13.0, 5.0, 3.0], 'area': 25.0}, 'DISHWASH': {'min': [8.0, 5.0, 0.0], 'max': [10.0, 7.0, 3.0], 'area': 4.0}, 'DRY-STORE': {'min': [10.0, 5.0, 0.0], 'max': [12.0, 7.0, 3.0], 'area': 4.0}, 'COLD-STORE': {'min': [12.0, 5.0, 0.0], 'max': [14.0, 7.0, 3.0], 'area': 4.0}, 'STAFF': {'min': [0.0, 5.0, 0.0], 'max': [4.0, 8.0, 3.0], 'area': 12.0}, 'WC': {'min': [4.0, 5.0, 0.0], 'max': [6.0, 7.0, 3.0], 'area': 4.0}}, 'space_box_tolerance': 0.1, 'space_area_tolerance': 0.1, 'csv_headers': ['RoomNumber', 'RoomName', 'Area'], 'csv_rows': [['B01', 'CAFE', 30.0], ['B02', 'COUNTER', 6.0], ['B03', 'BAKERY', 25.0], ['B04', 'DISHWASH', 4.0], ['B05', 'DRY-STORE', 4.0], ['B06', 'COLD-STORE', 4.0], ['B07', 'STAFF', 12.0], ['B08', 'WC', 4.0]], 'csv_numeric_tolerance': 0.1, 'pdf_page_count': 2, 'pdf_tokens': ['A101', 'A201', 'FLOOR PLAN', 'ELEVATION', 'CORNER BAKERY AND CAFE', 'CAFE', 'BAKERY', 'COUNTER']}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", "-").strip()).upper()


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def parent_storey_id(obj):
    for rel in getattr(obj, "Decomposes", None) or []:
        parent = getattr(rel, "RelatingObject", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent.id()
    for rel in getattr(obj, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent.id()
    return None


def ifc_bbox(model):
    import numpy as np
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    mins = None
    maxs = None
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        except Exception:
            continue
        if verts.size == 0:
            continue
        pmin = verts.min(axis=0)
        pmax = verts.max(axis=0)
        mins = pmin if mins is None else np.minimum(mins, pmin)
        maxs = pmax if maxs is None else np.maximum(maxs, pmax)
    if mins is None or maxs is None:
        return None
    return mins.tolist(), maxs.tolist()


def product_bbox(product):
    import numpy as np
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    if verts.size == 0:
        return None
    return verts.min(axis=0).tolist(), verts.max(axis=0).tolist()


def combined_bbox(products):
    import numpy as np

    mins = None
    maxs = None
    for product in products:
        bbox = product_bbox(product)
        if bbox is None:
            continue
        pmin, pmax = bbox
        pmin = np.array(pmin, dtype=float)
        pmax = np.array(pmax, dtype=float)
        mins = pmin if mins is None else np.minimum(mins, pmin)
        maxs = pmax if maxs is None else np.maximum(maxs, pmax)
    if mins is None or maxs is None:
        return None
    return mins.tolist(), maxs.tolist()


def bbox_matches(actual_bbox, expected_bbox, tolerance):
    if actual_bbox is None:
        return False
    mins, maxs = actual_bbox
    for actual, target in zip(mins, expected_bbox["min"]):
        if abs(float(actual) - float(target)) > tolerance:
            return False
    for actual, target in zip(maxs, expected_bbox["max"]):
        if abs(float(actual) - float(target)) > tolerance:
            return False
    return True


def is_wall_like(entity):
    return entity.is_a("IfcWall") or entity.is_a("IfcWallStandardCase")


def parse_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f, delimiter="\t"))


def parse_pdf(path):
    try:
        doc = fitz.open(str(path))
        pages = doc.page_count
        text = "".join(page.get_text("text") for page in doc)
        doc.close()
        return pages, text.upper()
    except Exception:
        pass
    try:
        import fitz

        doc = fitz.open(str(path))
        text = "\n".join(page.get_text("text") for page in doc)
        return doc.page_count, text.upper()
    except Exception:
        pass
    try:
        from pdfminer.high_level import extract_text
        from pdfminer.pdfpage import PDFPage

        with path.open("rb") as f:
            pages = sum(1 for _ in PDFPage.get_pages(f))
        return pages, extract_text(str(path)).upper()
    except Exception:
        pass
    if _HAS_PDFMINER:
        try:
            with open(str(path), "rb") as f:
                pages = sum(1 for _ in _PDFPage.get_pages(f))
            text = _pdfminer_extract_text(str(path))
            return pages, text.upper()
        except Exception:
            pass
    return None, None


def compare_cell(actual, expected, tolerance):
    if isinstance(expected, (int, float)):
        try:
            return abs(float(str(actual).strip()) - float(expected)) <= tolerance
        except Exception:
            return False
    return str(actual).strip() == str(expected)


def check_ifc(model):
    if not str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"]):
        return False
    if not unique_global_ids(model):
        return False
    if len(model.by_type("IfcBuildingStorey")) != SPEC["storey_count"]:
        return False
    spaces = model.by_type("IfcSpace")
    expected_names = {norm(name) for name in SPEC["space_names"]}
    if len(spaces) != len(expected_names):
        return False
    walls = [e for e in model.by_type("IfcProduct") if is_wall_like(e)]
    if len(walls) < SPEC["min_wall_count"]:
        return False
    slabs = model.by_type("IfcSlab")
    roofs = model.by_type("IfcRoof")
    if len(slabs) < SPEC["slab_count"] or len(roofs) < SPEC["roof_count"]:
        return False
    valid_wall_count = 0
    for wall in walls:
        bbox = product_bbox(wall)
        if bbox is None:
            continue
        mins, maxs = bbox
        dx = abs(float(maxs[0]) - float(mins[0]))
        dy = abs(float(maxs[1]) - float(mins[1]))
        dz = abs(float(maxs[2]) - float(mins[2]))
        thickness = min(dx, dy)
        if SPEC["wall_thickness_range"][0] <= thickness <= SPEC["wall_thickness_range"][1] and SPEC["wall_height_range"][0] <= dz <= SPEC["wall_height_range"][1]:
            valid_wall_count += 1
    if valid_wall_count < SPEC["min_wall_count"]:
        return False
    if not bbox_matches(combined_bbox(slabs), SPEC["slab_bbox"], SPEC["slab_bbox_tolerance"]):
        return False
    if not bbox_matches(combined_bbox(roofs), SPEC["roof_bbox"], SPEC["roof_bbox_tolerance"]):
        return False
    records = {norm(getattr(space, "Name", "")): parent_storey_id(space) for space in spaces}
    if set(records) != expected_names:
        return False
    if any(storey_id is None for storey_id in records.values()):
        return False
    for space in spaces:
        name = norm(getattr(space, "Name", ""))
        if name not in SPEC.get("space_boxes", {}):
            continue
        bbox = product_bbox(space)
        if bbox is None:
            return False
        mins, maxs = bbox
        expected = SPEC["space_boxes"][name]
        tol = SPEC.get("space_box_tolerance", 0.25)
        for actual, target in zip(mins, expected["min"]):
            if abs(float(actual) - float(target)) > tol:
                return False
        for actual, target in zip(maxs, expected["max"]):
            if abs(float(actual) - float(target)) > tol:
                return False
        area = abs((float(maxs[0]) - float(mins[0])) * (float(maxs[1]) - float(mins[1])))
        if abs(area - float(expected["area"])) > SPEC.get("space_area_tolerance", 0.1):
            return False
    if SPEC.get("storey_groups"):
        group_storeys = {}
        for group, names in SPEC["storey_groups"].items():
            ids = {records[norm(name)] for name in names}
            if len(ids) != 1:
                return False
            group_storeys[group] = next(iter(ids))
        if len(set(group_storeys.values())) != len(group_storeys):
            return False
    elif SPEC["storey_count"] == 1:
        if len(set(records.values())) != 1:
            return False
    bbox = ifc_bbox(model)
    if bbox is None:
        return False
    mins, maxs = bbox
    if not bbox_matches((mins, maxs), SPEC["bbox_exact"], SPEC.get("bbox_tolerance", 0.5)):
        return False
    return True


def check_csv(path):
    if "result.txt" not in SPEC["required_outputs"]:
        return True
    rows = parse_csv(path)
    if not rows or rows[0] != SPEC["csv_headers"]:
        return False
    body = rows[1:]
    if len(body) != len(SPEC["csv_rows"]):
        return False
    tolerance = SPEC.get("csv_numeric_tolerance", 0.1)
    for actual_row, expected_row in zip(body, SPEC["csv_rows"]):
        if len(actual_row) != len(expected_row):
            return False
        for actual, expected in zip(actual_row, expected_row):
            if not compare_cell(actual, expected, tolerance):
                return False
    return True


def check_pdf(path):
    if "result.pdf" not in SPEC["required_outputs"]:
        return True
    pages, text = parse_pdf(path)
    if pages is None or text is None:
        return False
    if pages != SPEC["pdf_page_count"]:
        return False
    for token in SPEC.get("pdf_tokens", []):
        if str(token).upper() not in text:
            return False
    return True


def evaluate():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DESKTOP
    for rel, min_bytes in SPEC["required_outputs"].items():
        path = root / rel
        if not path.is_file() or path.stat().st_size < min_bytes:
            return False
    model = ifcopenshell.open(str(root / "result.ifc"))
    return check_ifc(model) and check_csv(root / "result.txt") and check_pdf(root / "result.pdf")


def main():
    try:
        finish(evaluate())
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
