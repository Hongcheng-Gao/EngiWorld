#!/usr/bin/env python3

import csv

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

    "required_csv": "result.csv",

    "min_ifc_bytes": 500,

    "min_pdf_bytes": 200,

    "min_csv_bytes": 20,

    "schema": "IFC4",

    "counts": {

        "IfcProject": 1,

        "IfcSite": 1,

        "IfcBuilding": 1,

        "IfcBuildingStorey": 2,

        "IfcSpace": 17,

        "IfcWall": 24,

        "IfcSlab": 6,

    },

    "forbidden_counts": {

        "IfcRoof": 0,

        "IfcDoor": 0,

        "IfcWindow": 0,

        "IfcCurtainWall": 0,

        "IfcBuildingElementProxy": 0,

        "IfcStair": 0,

        "IfcColumn": 0,

        "IfcBeam": 0,

    },

    "space_token_counts": {"bedroom": 16, "lounge": 1},

    "required_space_names": ["shared lounge"],

    "pdf_tokens": ["COURTYARD HOTEL PLAN", "A201"],

}





def finish(ok):

    print("true" if ok else "false")

    raise SystemExit(0)





def norm(value):

    text = str(value or "").replace("_", " ").replace("-", " ").lower()

    return re.sub(r"\s+", " ", text).strip()





def entity_count(model, ifc_class):

    return len(model.by_type(ifc_class))





def unique_global_ids(model):

    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]

    return len(gids) == len(set(gids))





def parse_int(value):

    text = str(value).strip().replace(",", "")

    if not re.fullmatch(r"[+-]?\d+", text):

        raise ValueError("not integer")

    return int(text)





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





def parse_csv_rows(path):

    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))

    if not rows:

        return None

    headers = [cell.strip() for cell in rows[0]]

    if headers != ["room name", "area"]:

        return None

    body = [row for row in rows[1:] if any(cell.strip() for cell in row)]

    if len(body) != 17:

        return None

    return body





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

    for token, minimum in SPEC["space_token_counts"].items():

        if sum(1 for name in names if token in name) < minimum:

            return False

    for required in SPEC["required_space_names"]:

        if norm(required) not in names:

            return False

    return True





def check_csv(csv_path):

    rows = parse_csv_rows(csv_path)

    if rows is None:

        return False

    lounge_ok = False

    bedroom_rows = 0

    for name, area, *rest in rows:

        if rest:

            return False

        room_name = norm(name)

        value = parse_int(area)

        if room_name == "shared lounge":

            lounge_ok = value == 60

        elif "bedroom" in room_name:

            bedroom_rows += 1

            if value != 24:

                return False

        else:

            return False

    return lounge_ok and bedroom_rows == 16





def check_pdf(pdf_path):

    if page_count(pdf_path) != 1:

        return False

    text = extract_pdf_text(pdf_path).lower()

    return all(token.lower() in text for token in SPEC["pdf_tokens"])





def evaluate(result_dir):

    root = Path(result_dir)

    ifc_path = root / SPEC["required_ifc"]

    pdf_path = root / SPEC["required_pdf"]

    csv_path = root / SPEC["required_csv"]

    if not ifc_path.is_file() or ifc_path.stat().st_size < SPEC["min_ifc_bytes"]:

        return False

    if not pdf_path.is_file() or pdf_path.stat().st_size < SPEC["min_pdf_bytes"]:

        return False

    if not csv_path.is_file() or csv_path.stat().st_size < SPEC["min_csv_bytes"]:

        return False

    model = ifcopenshell.open(str(ifc_path))

    return (

        str(getattr(model, "schema", "")).upper().startswith(SPEC["schema"])

        and unique_global_ids(model)

        and check_counts(model)

        and check_spaces(model)

        and check_csv(csv_path)

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

