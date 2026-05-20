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
DESKTOP = Path("C:/Users/user/Desktop")


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
        "IfcSpace": 6,
        "IfcWall": 9,
        "IfcSlab": 1,
        "IfcRoof": 1,
        "IfcDoor": 4,
        "IfcWindow": 6,
    },
    "forbidden_counts": {
        "IfcStair": 0,
        "IfcColumn": 0,
        "IfcBeam": 0,
        "IfcCurtainWall": 0,
        "IfcBuildingElementProxy": 0,
    },
    "bbox_tolerance": 0.35,
    "bbox": {"IfcWall": [0, 0, 0, 14, 10, 3.2], "IfcSlab": [0, 0, 0, 14, 10, 0.25], "IfcRoof": [0, 0, 3.2, 14, 10, 3.4], "IfcSpace": [0.3, 0.3, 0, 13.7, 9.7, 2.8]},
    "space_token_counts": {"studio": 2, "bath": 2, "kitchenette": 2},
    "pdf_tokens": ["A101 GROUND FLOOR PLAN", "A201 SOUTH ELEVATION", "Studio A", "Studio B"],
    "pdf_pages": 2,
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
    if not check_no_gui_bypass(root):
        return False
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
