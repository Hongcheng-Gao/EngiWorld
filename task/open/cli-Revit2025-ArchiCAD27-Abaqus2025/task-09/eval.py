#!/usr/bin/env python3
import hashlib
import math
import os
import re
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np

SPEC = {
  "absent_space_tokens": [
    "Training Hall"
  ],
  "bbox_ranges_m": {
    "x": [
      19.4,
      21.2
    ],
    "y": [
      7.4,
      9.2
    ],
    "z": [
      2.5,
      3.5
    ]
  },
  "required_counts": {
    "IfcBuilding": 1,
    "IfcBuildingStorey": 1,
    "IfcProject": 1,
    "IfcSite": 1,
    "IfcSlab": 1,
    "IfcSpace": 4,
    "IfcWall": 7
  },
  "forbidden": [
    "IfcBuildingElementProxy"
  ],
  "min_counts": {},
  "min_file_bytes": 6000,
  "min_shaped_products": 9,
  "space_tokens": [
    "Foyer",
    "Classroom A",
    "Classroom B",
    "Store"
  ],
  "storey_tokens": [
    "Ground Floor"
  ]
}
DESKTOP = Path(os.environ.get("ENGIWORLD_DESKTOP", "C:/Users/user/Desktop"))
DIRECT_IFC_TOOLS = ("ifcopenshell", "xbim", "ifcpatch", "ifcconvert", "ifccsv", "ifcclash")
ALLOWED_WORKFLOW_TOKENS = (
    "revit.exe", "autodesk.revit", "document.export", "ifcexportoptions",
    "archicad", "ifccommandserver", "api.executeaddoncommand", "abaqus",
)


def finish(ok):
    print("True" if ok else "False")
    raise SystemExit(0)


def norm(value):
    text = str(value or "").replace("_", " ").replace("-", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text_safe(path, limit=None):
    try:
        data = Path(path).read_bytes()
    except Exception:
        return ""
    if limit is not None:
        data = data[:limit]
    return data.decode("utf-8", errors="ignore")


def native_export_provenance(path, model):
    apps = " ".join(
        " ".join(str(getattr(app, attr, "") or "") for attr in ("ApplicationIdentifier", "ApplicationFullName", "Version"))
        for app in model.by_type("IfcApplication")
    )
    fields = []
    try:
        header = model.wrapped_data.header
        header = header() if callable(header) else header
        file_name = header.file_name
        fields.extend((file_name.preprocessor_version or "", file_name.originating_system or ""))
    except Exception:
        pass
    text = f"{apps} {' '.join(str(v) for v in fields)} {read_text_safe(path, 8000)}".lower()
    if any(token in text for token in DIRECT_IFC_TOOLS) or "/dev/null" in text:
        return False
    revit_2025 = "revit" in text and ("2025" in text or re.search(r"\b25(?:\.|\b)", text))
    archicad_27 = "archicad" in text and re.search(r"\b27(?:\.|\b)", text)
    abaqus_2025 = ("abaqus" in text or "simulia" in text) and "2025" in text
    return bool(revit_2025 or archicad_27 or abaqus_2025)


def history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def history_contains_bypass(root):
    for path in history_paths(root):
        if not path.is_file():
            continue
        for raw_line in read_text_safe(path).lower().splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line or "result.ifc" not in line:
                continue
            direct_tool = any(token in line for token in DIRECT_IFC_TOOLS)
            direct_copy = re.search(r"\b(copy|copy-item|cp)\b.*init\.ifc.*result\.ifc", line)
            direct_write = any(token in line for token in (">", "tee ", "out-file", "set-content", ".write(", "write_text"))
            allowed = any(token in line for token in ALLOWED_WORKFLOW_TOKENS)
            if direct_tool or direct_copy or (direct_write and not allowed):
                return True
    return False


def unique_global_ids(model):
    gids = [entity.GlobalId for entity in model.by_type("IfcRoot") if getattr(entity, "GlobalId", None)]
    return bool(gids) and len(gids) == len(set(gids))


def entity_count(model, ifc_class):
    return len(model.by_type(ifc_class))


def check_counts(model):
    for ifc_class, expected in SPEC["required_counts"].items():
        if entity_count(model, ifc_class) < expected:
            return False
    for ifc_class, minimum in SPEC["min_counts"].items():
        if entity_count(model, ifc_class) < minimum:
            return False
    return all(entity_count(model, ifc_class) == 0 for ifc_class in SPEC["forbidden"])


def space_label(space):
    return norm(f"{getattr(space, 'Name', '')} {getattr(space, 'LongName', '')}")


def parent_storey(space, model):
    for rel in getattr(space, "Decomposes", None) or []:
        parent = getattr(rel, "RelatingObject", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    for rel in getattr(space, "ContainedInStructure", None) or []:
        parent = getattr(rel, "RelatingStructure", None)
        if parent and parent.is_a("IfcBuildingStorey"):
            return parent
    for rel in model.by_type("IfcRelAggregates"):
        parent = getattr(rel, "RelatingObject", None)
        if parent and parent.is_a("IfcBuildingStorey") and space in (getattr(rel, "RelatedObjects", None) or []):
            return parent
    return None


def spaces_match_required_program(model):
    spaces = model.by_type("IfcSpace")
    storeys = sorted(
        model.by_type("IfcBuildingStorey"),
        key=lambda storey: (
            float(getattr(storey, "Elevation", 0.0) or 0.0),
            norm(getattr(storey, "Name", "")),
            storey.id(),
        ),
    )
    storey_ranks = {storey.id(): index for index, storey in enumerate(storeys)}
    required_ranks = SPEC.get("space_storey_ranks", {})
    candidates = []
    for token in SPEC["space_tokens"]:
        options = []
        for index, space in enumerate(spaces):
            if norm(token) not in space_label(space):
                continue
            expected_rank = required_ranks.get(token)
            parent = parent_storey(space, model)
            if expected_rank is not None and (
                parent is None or storey_ranks.get(parent.id()) != expected_rank
            ):
                continue
            options.append(index)
        candidates.append(options)
    if any(not options for options in candidates):
        return False
    order = sorted(range(len(candidates)), key=lambda index: len(candidates[index]))

    def assign(position, used):
        if position == len(order):
            return True
        for space_index in candidates[order[position]]:
            if space_index not in used and assign(position + 1, used | {space_index}):
                return True
        return False

    return assign(0, set())


def check_names(model):
    if not spaces_match_required_program(model):
        return False
    space_names = [space_label(s) for s in model.by_type("IfcSpace")]
    for token in SPEC["absent_space_tokens"]:
        if any(norm(token) in name for name in space_names):
            return False
    return True


def shape_records(model):
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    records = []
    for product in model.by_type("IfcProduct"):
        if product.is_a("IfcOpeningElement") or not getattr(product, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, product)
            verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
        except Exception:
            continue
        if verts.size:
            records.append((product, verts))
    return records


def check_geometry(model):
    records = shape_records(model)
    if len(records) < SPEC["min_shaped_products"]:
        return False
    mins = np.min([verts.min(axis=0) for _, verts in records], axis=0)
    maxs = np.max([verts.max(axis=0) for _, verts in records], axis=0)
    spans = maxs - mins
    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):
        low, high = SPEC["bbox_ranges_m"][axis]
        value = float(spans[idx])
        if not (low <= value <= high) or not math.isfinite(value):
            return False
    return True


def model_bbox(model):
    records = shape_records(model)
    if not records:
        return None
    mins = np.min([verts.min(axis=0) for _, verts in records], axis=0)
    maxs = np.max([verts.max(axis=0) for _, verts in records], axis=0)
    return mins, maxs


def check_baseline(init_model, result_model):
    for ifc_class in (
        "IfcBuildingStorey", "IfcWall", "IfcSlab", "IfcRoof", "IfcDoor",
        "IfcWindow", "IfcStair", "IfcColumn",
    ):
        if entity_count(result_model, ifc_class) < entity_count(init_model, ifc_class):
            return False
    init_bbox = model_bbox(init_model)
    result_bbox = model_bbox(result_model)
    if init_bbox is None or result_bbox is None:
        return False
    return all(
        abs(float(before) - float(after)) <= 1.25
        for before, after in zip(
            np.concatenate(init_bbox),
            np.concatenate(result_bbox),
        )
    )


def init_path_for(result_dir):
    beside = Path(result_dir) / "init.ifc"
    if beside.is_file():
        return beside
    local = Path(result_dir).parent / "init_file" / "init.ifc"
    if local.is_file():
        return local
    remote = DESKTOP / "init.ifc"
    return remote if remote.is_file() else None


def evaluate(result_dir):
    result_dir = Path(result_dir)
    result = result_dir / "result.ifc"
    if not result.is_file() or result.stat().st_size < SPEC["min_file_bytes"]:
        return False
    init = init_path_for(result_dir)
    if init is not None and init.is_file() and sha256(init) == sha256(result):
        return False
    if history_contains_bypass(result_dir):
        return False
    model = ifcopenshell.open(str(result))
    return (
        str(getattr(model, "schema", "")).upper().startswith("IFC4")
        and native_export_provenance(result, model)
        and unique_global_ids(model)
        and check_counts(model)
        and check_names(model)
        and check_geometry(model)
        and (init is None or check_baseline(ifcopenshell.open(str(init)), model))
    )


def main():
    try:
        result_dir = Path(os.environ.get("RESULT_DIR", str(DESKTOP)))
        finish(evaluate(result_dir))
    except Exception:
        finish(False)


if __name__ == "__main__":
    main()
