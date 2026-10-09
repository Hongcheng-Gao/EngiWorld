#!/usr/bin/env python3
import filecmp
import os
import re
from pathlib import Path

DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", "C:/Users/user/Desktop"))
SPEC = {'products': [], 'annotations': [{'class': 'IfcSpace', 'name': 'A-LIVING', 'tokens': ['UNIT A', 'RESIDENTIAL', 'PRIMARY LIVING', 'LEASING']}, {'class': 'IfcSpace', 'name': 'B-LIVING', 'tokens': ['UNIT B', 'RESIDENTIAL', 'PRIMARY LIVING', 'LEASING']}]}

DIRECT_IFC_TOOLS = ("ifcopenshell", "xbim", "bcfier", "ifcpatch", "ifcconvert", "ifccsv", "ifcclash")
DIRECT_WRITE_TOKENS = ("result.ifc", "desktop\\result.ifc", "desktop/result.ifc")
ALLOWED_TOOL_TOKENS = (
    "ifccommandserverapp", "ifccommandserver", "graphisoft", "archicad", "/jemi",
    "model.loadfile", "model.savefile", "model.mergefile", "entity.create",
    "entity.get", "entity.delete", "api.executeaddoncommand",
)


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def text_norm(value):
    return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()


def same_name(a, b):
    return text_norm(a) == text_norm(b)


def read_text_safe(path, limit=None):
    try:
        data = path.read_bytes()
    except Exception:
        return ""
    if limit is not None:
        data = data[:limit]
    return data.decode("utf-8", errors="ignore")


def history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def history_contains_bypass(root):
    for path in history_paths(root):
        if not path.is_file():
            continue
        text = read_text_safe(path).lower()
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_result = any(token in line for token in DIRECT_WRITE_TOKENS)
            uses_direct_tool = any(token in line for token in DIRECT_IFC_TOOLS)
            direct_copy = "copy-item" in line or re.search(r"\b(copy|cp)\b.*init\.ifc.*result\.ifc", line)
            writes_file = any(token in line for token in (">", "tee ", "out-file", "set-content", ".write(", "write_text"))
            allowed = any(token in line for token in ALLOWED_TOOL_TOKENS)
            if touches_result and uses_direct_tool:
                return True
            if touches_result and direct_copy:
                return True
            if touches_result and writes_file and not allowed:
                return True
    return False


def header_looks_graphisoft_edm(path):
    text = read_text_safe(path, 7000).lower()
    compact = text.replace(" ", "")
    return "express data manager" in text and "file_schema(('ifc4'))" in compact


def unique_global_ids(model):
    gids = [e.GlobalId for e in model.by_type("IfcRoot") if getattr(e, "GlobalId", None)]
    return bool(gids) and len(gids) == len(set(gids))


def objects_by_name(model, cls, name):
    return [e for e in model.by_type(cls) if same_name(getattr(e, "Name", ""), name)]


def parent_storey(obj, model):
    for rel in getattr(obj, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    for rel in getattr(obj, "Decomposes", None) or []:
        parent = getattr(rel, "RelatingObject", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    for rel in model.by_type("IfcRelContainedInSpatialStructure"):
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey") and obj in (getattr(rel, "RelatedElements", None) or []):
            return parent
    for rel in model.by_type("IfcRelAggregates"):
        parent = getattr(rel, "RelatingObject", None)
        if parent and parent.is_a("IfcBuildingStorey") and obj in (getattr(rel, "RelatedObjects", None) or []):
            return parent
    return None


def related_psets(obj, model):
    psets = []
    seen = set()
    def add(pset):
        if pset and pset.is_a("IfcPropertySet") and pset.id() not in seen:
            seen.add(pset.id())
            psets.append(pset)
    for rel in getattr(obj, "IsDefinedBy", None) or []:
        add(getattr(rel, "RelatingPropertyDefinition", None))
    for rel in model.by_type("IfcRelDefinesByProperties"):
        if obj in (getattr(rel, "RelatedObjects", None) or []):
            add(getattr(rel, "RelatingPropertyDefinition", None))
    return psets


def value_text(value):
    if value is None:
        return ""
    wrapped = getattr(value, "wrappedValue", None)
    if wrapped is not None:
        return str(wrapped)
    return str(value)


def object_search_text(obj, model):
    parts = [getattr(obj, attr, "") for attr in ("Name", "LongName", "ObjectType", "Description", "Tag", "PredefinedType")]
    for pset in related_psets(obj, model):
        parts.append(getattr(pset, "Name", ""))
        for prop in getattr(pset, "HasProperties", None) or []:
            parts.append(getattr(prop, "Name", ""))
            parts.append(value_text(getattr(prop, "NominalValue", None)))
    return text_norm(" ".join(str(p) for p in parts if p is not None))


def has_tokens(obj, model, tokens):
    haystack = object_search_text(obj, model)
    return all(text_norm(token) in haystack for token in tokens)


def ifc_bbox(model):
    try:
        import numpy as np
        import ifcopenshell.geom
    except Exception:
        return None
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


def bbox_preserved(init_model, result_model, tol=0.75):
    init_bbox = ifc_bbox(init_model)
    result_bbox = ifc_bbox(result_model)
    if init_bbox is None or result_bbox is None:
        return True
    for a, b in zip(init_bbox[0] + init_bbox[1], result_bbox[0] + result_bbox[1]):
        if abs(float(a) - float(b)) > tol:
            return False
    return True


def check_baseline(init_model, result_model):
    for cls in ("IfcBuildingStorey", "IfcSpace"):
        init_names = {text_norm(getattr(e, "Name", "")) for e in init_model.by_type(cls)}
        result_names = {text_norm(getattr(e, "Name", "")) for e in result_model.by_type(cls)}
        if not init_names.issubset(result_names):
            return False
    for cls in ("IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow", "IfcStair", "IfcColumn"):
        if len(result_model.by_type(cls)) < len(init_model.by_type(cls)):
            return False
    return bbox_preserved(init_model, result_model)


def check_required_products(init_model, result_model):
    increases = {}
    for item in SPEC.get("products", []):
        increases[item["class"]] = increases.get(item["class"], 0) + 1
        matches = objects_by_name(result_model, item["class"], item["name"])
        if not matches:
            return False
        obj = matches[0]
        if item.get("storey"):
            storey = parent_storey(obj, result_model)
            if storey is None or not same_name(getattr(storey, "Name", ""), item["storey"]):
                return False
        predefined = item.get("predefined")
        if predefined and hasattr(obj, "PredefinedType") and text_norm(getattr(obj, "PredefinedType", "")) != text_norm(predefined):
            return False
        if item.get("tokens") and not has_tokens(obj, result_model, item["tokens"]):
            return False
    for cls, inc in increases.items():
        if len(result_model.by_type(cls)) - len(init_model.by_type(cls)) < inc:
            return False
    return True


def check_annotations(result_model):
    for item in SPEC.get("annotations", []):
        matches = objects_by_name(result_model, item["class"], item["name"])
        if not matches:
            return False
        if not any(has_tokens(obj, result_model, item.get("tokens", [])) for obj in matches):
            return False
    return True


def check_model(init_path, result_path):
    import ifcopenshell

    result_model = ifcopenshell.open(str(result_path))
    if not str(getattr(result_model, "schema", "")).upper().startswith("IFC4"):
        return False
    if not unique_global_ids(result_model):
        return False
    if len(result_model.by_type("IfcBuildingElementProxy")) != 0:
        return False
    init_model = ifcopenshell.open(str(init_path)) if init_path.is_file() else None
    if init_model is not None:
        if not check_baseline(init_model, result_model):
            return False
        if not check_required_products(init_model, result_model):
            return False
    if not check_annotations(result_model):
        return False
    return True


def evaluate(root):
    root = Path(root)
    result = root / "result.ifc"
    init = root / "init.ifc"
    if not result.is_file() or result.stat().st_size < 6000:
        return False
    if init.is_file() and filecmp.cmp(str(init), str(result), shallow=False):
        return False
    if history_contains_bypass(root):
        return False
    if not header_looks_graphisoft_edm(result):
        return False
    return check_model(init, result)


if __name__ == "__main__":
    try:
        finish(evaluate(DESKTOP))
    except Exception:
        finish(False)
