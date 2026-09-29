#!/usr/bin/env python3
import re
from pathlib import Path

DESKTOP = Path("C:/Users/user/Desktop")

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr"
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = ("result.ifc", "result.pdf", "result.csv", "summary.txt")
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl", "ifcopenshell",
    "revitbatchprocessor", "dynamo"
)

SPEC = {'min_bytes': 500, 'space_names': ['Waiting', 'Exam'], 'min_counts': {'projects': 1, 'storeys': 1, 'spaces': 2, 'walls': 5, 'slabs': 1, 'doors': 2, 'windows': 2}, 'forbidden': []}


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
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
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
    return not _desktop_script_artifacts(root) and not _history_contains_bypass(root)


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ").strip()).lower()


def entity_count(model, classes):
    if isinstance(classes, str):
        classes = [classes]
    # by_type() includes subtypes, so count distinct entities rather than
    # double-counting IfcWallStandardCase as both itself and IfcWall.
    entities = {}
    for name in classes:
        for entity in model.by_type(name):
            entities[entity.id()] = entity
    return len(entities)


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return bool(gids) and len(gids) == len(set(gids))


def check_min_counts(model):
    class_map = {
        "projects": "IfcProject",
        "storeys": "IfcBuildingStorey",
        "spaces": "IfcSpace",
        "walls": ["IfcWall", "IfcWallStandardCase"],
        "slabs": "IfcSlab",
        "roofs": "IfcRoof",
        "doors": "IfcDoor",
        "windows": "IfcWindow",
        "stairs": "IfcStair",
        "columns": "IfcColumn",
        "beams": "IfcBeam",
        "curtain_walls": "IfcCurtainWall",
    }
    for key, minimum in SPEC.get("min_counts", {}).items():
        if entity_count(model, class_map[key]) < minimum:
            return False
    return True



def project_spatial_content_ids(model):
    # IFC spatial structure is decomposed from IfcProject with
    # IfcRelAggregates. Physical products are then spatially contained;
    # decomposed/nested children inherit their parent's project association.
    associated = {project.id() for project in model.by_type("IfcProject")}
    changed = True
    while changed:
        changed = False
        for rel in model.by_type("IfcRelAggregates"):
            if rel.RelatingObject.id() not in associated:
                continue
            for related in rel.RelatedObjects or []:
                if related.id() not in associated:
                    associated.add(related.id())
                    changed = True
        for rel in model.by_type("IfcRelContainedInSpatialStructure"):
            if rel.RelatingStructure.id() not in associated:
                continue
            for related in rel.RelatedElements or []:
                if related.id() not in associated:
                    associated.add(related.id())
                    changed = True
        for rel in model.by_type("IfcRelNests"):
            if rel.RelatingObject.id() not in associated:
                continue
            for related in rel.RelatedObjects or []:
                if related.id() not in associated:
                    associated.add(related.id())
                    changed = True
    return associated


def check_shaped_content(model):
    class_map = {
        "spaces": ["IfcSpace"],
        "walls": ["IfcWall", "IfcWallStandardCase"],
        "slabs": ["IfcSlab"],
        "roofs": ["IfcRoof"],
        "doors": ["IfcDoor"],
        "windows": ["IfcWindow"],
        "stairs": ["IfcStair"],
        "columns": ["IfcColumn"],
        "beams": ["IfcBeam"],
        "curtain_walls": ["IfcCurtainWall"],
    }
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    associated = project_spatial_content_ids(model)
    for key, minimum in SPEC.get("min_counts", {}).items():
        classes = class_map.get(key)
        if not classes:
            continue
        products = {}
        for name in classes:
            for product in model.by_type(name):
                products[product.id()] = product
        shaped = 0
        for product in products.values():
            if product.id() not in associated:
                continue
            try:
                shape = ifcopenshell.geom.create_shape(settings, product)
                vertices = list(shape.geometry.verts)
                if len(vertices) < 9:
                    continue
                spans = [max(vertices[index::3]) - min(vertices[index::3]) for index in range(3)]
                if max(spans) <= 1.0e-6:
                    continue
                shaped += 1
            except Exception:
                continue
        if shaped < minimum:
            return False
    return True

def check_forbidden(model):
    return True


def check_space_names(model):
    names = [norm(getattr(space, "Name", "") or getattr(space, "LongName", "")) for space in model.by_type("IfcSpace")]
    for required in SPEC.get("space_names", []):
        token = norm(required)
        if not any(token in name for name in names):
            return False
    return True


def evaluate(root):
    root = Path(root)
    desktop = DESKTOP if "DESKTOP" in globals() else root.parent
    if not check_no_gui_bypass(desktop):
        return False
    if not root.is_dir():
        return False
    path = root / "result.ifc"
    if not path.is_file() or path.stat().st_size < SPEC.get("min_bytes", 500):
        candidates = sorted(
            p for p in root.iterdir()
            if p.is_file() and p.suffix.lower() == ".ifc" and p.stat().st_size >= SPEC.get("min_bytes", 500)
        )
        if not candidates:
            return False
        path = candidates[0]
    import ifcopenshell
    model = ifcopenshell.open(str(path))
    schema = str(getattr(model, "schema", "")).upper()
    return (
        schema.startswith("IFC")
        and unique_global_ids(model)
        and check_min_counts(model)
        and check_shaped_content(model)
        and check_forbidden(model)
        and check_space_names(model)
    )


def main():
    try:
        finish(evaluate(DESKTOP / "result"))
    except SystemExit:
        raise
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
