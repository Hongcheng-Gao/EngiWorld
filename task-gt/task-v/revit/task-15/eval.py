#!/usr/bin/env python3
import re
import subprocess
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
        "IfcBuildingStorey": 2,
        "IfcSpace": 2,
        "IfcWall": 8,
        "IfcSlab": 2,
    },
    "forbidden_counts": {
        "IfcRoof": 0,
        "IfcDoor": 0,
        "IfcWindow": 0,
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcCurtainWall": 0,
        "IfcBuildingElementProxy": 0,
    },
    "space_token_counts": {"warehouse": 1, "area": 1},
    "pdf_pages": 1,
    "pdf_tokens": ["WAREHOUSE UPGRADE", "Principal upgrade sheet"],
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


def page_count(path):
    proc = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("pdfinfo failed")
    for line in proc.stdout.splitlines():
        if line.lower().startswith("pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError("missing pages")


def extract_pdf_text(path):
    proc = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("pdftotext failed")
    return proc.stdout


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
