#!/usr/bin/env python3
import re
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
DESKTOP = Path("C:/Users/Administrator/Desktop")

import ifcopenshell
import ifcopenshell.geom


SPEC = {
    "required_ifc": "result.ifc",
    "required_pdf": "result.pdf",
    "min_ifc_bytes": 500,
    "min_pdf_bytes": 200,
    "schema": "IFC4",
    "counts": {
        "IfcProject": 1,
        "IfcSite": 1,
        "IfcBuilding": 1,
        "IfcBuildingStorey": 1,
        "IfcSpace": 1,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcDoor": 1,
        "IfcWindow": 4,
    },
    "forbidden_counts": {
        "IfcRoof": 0,
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcCurtainWall": 0,
        "IfcBuildingElementProxy": 0,
    },
    "required_space_names": ["retail space"],
    "pdf_pages": 1,
    "pdf_tokens": ["STOREFRONT ELEVATION", "Main street facade"],
}


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return len(gids) == len(set(gids))


def page_count(path):
    try:
        doc = fitz.open(str(path))
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        pass
    if _HAS_PDFMINER:
        try:
            with open(str(path), "rb") as f:
                return sum(1 for _ in _PDFPage.get_pages(f))
        except Exception:
            pass
    raise RuntimeError("cannot determine page count")


def extract_pdf_text(path):
    try:
        doc = fitz.open(str(path))
        text = "".join(page.get_text("text") for page in doc)
        doc.close()
        return text
    except Exception:
        pass
    if _HAS_PDFMINER:
        try:
            return _pdfminer_extract_text(str(path))
        except Exception:
            pass
    raise RuntimeError("cannot extract PDF text")


def check_counts(model):
    for ifc_class, expected in SPEC["counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    for ifc_class, expected in SPEC["forbidden_counts"].items():
        if entity_count(model, ifc_class) != expected:
            return False
    return True


def check_spaces(model):
    names = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]
    return all(norm(required) in names for required in SPEC["required_space_names"])


def check_pdf(pdf_path):
    if page_count(pdf_path) != SPEC["pdf_pages"]:
        return False
    text = re.sub(r"\s+", " ", extract_pdf_text(pdf_path).lower()).strip()
    return all(token.lower() in text for token in SPEC["pdf_tokens"])




def geometry_settings():
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    return settings


def combined_bbox(model, ifc_class):
    xs, ys, zs = [], [], []
    settings = geometry_settings()
    for element in model.by_type(ifc_class):
        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
            verts = shape.geometry.verts
        except Exception:
            continue
        xs.extend(verts[0::3])
        ys.extend(verts[1::3])
        zs.extend(verts[2::3])
    if not xs:
        return None
    return [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]


def bbox_close(actual, expected, tolerance):
    return actual is not None and all(abs(a - e) <= tolerance for a, e in zip(actual, expected))


def check_geometry(model):
    tolerance = SPEC.get("bbox_tolerance", 0.35)
    for ifc_class, expected in SPEC.get("bbox", {}).items():
        if not bbox_close(combined_bbox(model, ifc_class), expected, tolerance):
            return False
    return True

def evaluate(result_dir):
    root = Path(result_dir)
    ifc_path = root / SPEC["required_ifc"]
    pdf_path = root / SPEC["required_pdf"]
    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_ifc_bytes"]:
        return False
    if not pdf_path.is_file() or pdf_path.stat().st_size < SPEC["min_pdf_bytes"]:
        return False
    model = ifcopenshell.open(str(ifc_path))
    return (
        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])
        and unique_global_ids(model)
        and check_counts(model)
        and check_spaces(model)
        and check_geometry(model)
        and check_pdf(pdf_path)
    )


def main():
    try:
        finish(evaluate(DESKTOP))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
