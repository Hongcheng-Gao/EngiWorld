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

import ifcopenshell


DESKTOP = Path("C:/Users/Administrator/Desktop")


GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr"
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv"
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "openstudio", "energyplus", "blender --background", "revitbatchprocessor"
)


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    paths = [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]
    return paths


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item"))
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True


SPEC = {'title': 'Farm Shop and Greenhouse Link Drawing Set and Room Schedule', 'starts_from_init': False, 'required_outputs': {'result.ifc': 500, 'result.pdf': 500, 'result.txt': 20}, 'schema': 'IFC4', 'storey_count': 1, 'space_names': ['SHOP', 'PREP', 'STORE', 'OFFICE', 'WC', 'GREENHOUSE'], 'min_counts': {'IfcWall': 24, 'IfcSlab': 2, 'IfcRoof': 2}, 'bbox_exact': {'min': [0.0, 0.0, 0.0], 'max': [16.0, 8.0, 3.92]}, 'bbox_tolerance': 0.5, 'csv_headers': ['RoomNumber', 'RoomName', 'Area'], 'csv_rows': [['F01', 'SHOP', 25.0], ['F02', 'PREP', 9.0], ['F03', 'STORE', 6.0], ['F04', 'OFFICE', 9.0], ['F05', 'WC', 4.0], ['F06', 'GREENHOUSE', 48.0]], 'csv_numeric_tolerance': 0.1, 'pdf_page_count': 2, 'pdf_tokens': ['A101', 'A201', 'FLOOR PLAN', 'SECTION', 'FARM SHOP AND GREENHOUSE LINK', 'SHOP', 'GREENHOUSE', 'PREP']}


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
    for cls, minimum in SPEC.get("min_counts", {}).items():
        if len(model.by_type(cls)) < minimum:
            return False
    records = {norm(getattr(space, "Name", "")): parent_storey_id(space) for space in spaces}
    if set(records) != expected_names:
        return False
    if any(storey_id is None for storey_id in records.values()):
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
    tol = SPEC.get("bbox_tolerance", 0.5)
    for actual, target in zip(mins, SPEC["bbox_exact"]["min"]):
        if abs(float(actual) - float(target)) > tol:
            return False
    for actual, target in zip(maxs, SPEC["bbox_exact"]["max"]):
        if abs(float(actual) - float(target)) > tol:
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
    root = DESKTOP
    if not check_no_gui_bypass(root):
        return False
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
