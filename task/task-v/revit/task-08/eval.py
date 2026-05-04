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
        "IfcSpace": 3,
        "IfcWall": 4,
        "IfcSlab": 1,
        "IfcRoof": 1,
        "IfcDoor": 1,
        "IfcWindow": 3,
    },
    "forbidden_counts": {
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcCurtainWall": 0,
        "IfcBuildingElementProxy": 0,
    },
    "space_token_counts": {"event": 1, "storage": 1, "toilet": 1},
    "pdf_pages": 1,
    "pdf_tokens": ["A101 PAVILION PLAN", "Event Room", "Storage", "Toilet"],
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
    return all(sum(1 for name in names if token in name) >= minimum for token, minimum in SPEC["space_token_counts"].items())


def check_pdf(pdf_path):
    if page_count(pdf_path) != SPEC["pdf_pages"]:
        return False
    text = re.sub(r"\s+", " ", extract_pdf_text(pdf_path).lower()).strip()
    return all(token.lower() in text for token in SPEC["pdf_tokens"])


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
