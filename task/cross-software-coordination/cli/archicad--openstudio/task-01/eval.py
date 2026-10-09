# EngiWorld Archicad -> OpenStudio multi-software flow evaluator.
# This evaluator checks instruction-derived artifacts and never compares against ground_truth files.
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-01-windows',
 'mode': 'two_stage',
 'software_chain': ['archicad', 'openstudio'],
 'required_files': ['init.ifc',
                    'stage1.ifc',
                    'handoff.json',
                    'result.osm',
                    'flow_report.json',
                    'model_summary.csv'],
 'required_spaces': ['SITE-OFFICE', 'PRINT-COPY'],
 'required_zones': ['SITE-OFFICE-ZN', 'PRINT-COPY-ZN'],
 'stage1_tokens': ['EW2A01',
                   'EW2A01',
                   'SITE-OFFICE',
                   'PRINT-COPY',
                   'SOUTH-ENTRANCE-WINDOW',
                   'OPAQUE-NORTH-WEST',
                   'multi-cli-2-archicad-openstudio-task-01-windows'],
 'handoff_tokens': ['LOW-EQUIPMENT-OFFICE',
                    'SIDE-DAYLIGHT',
                    'QUIET-OPAQUE-ENVELOPE',
                    'SOUTH-ENTRANCE-WINDOW'],
 'osm_tokens': ['SITE-OFFICE-ZN',
                'PRINT-COPY-ZN',
                'LowOfficeEquipmentSchedule',
                'SouthEntranceWindow',
                'OpaqueNorthWestEnvelope'],
 'summary_tokens': ['SITE-OFFICE', 'PRINT-COPY'],
 'min_windows': 1,
 'min_doors': 1,
 'min_roofs': 0,
 'min_storeys': 1,
 'expected_stage': 'archicad'}

IFC_CLASSES = [
    "IfcProject",
    "IfcSite",
    "IfcBuilding",
    "IfcBuildingStorey",
    "IfcSpace",
    "IfcWall",
    "IfcSlab",
    "IfcRoof",
    "IfcDoor",
    "IfcWindow",
    "IfcOpeningElement",
]

REQUIRED_SUMMARY_COLUMNS = [
    "case_id",
    "space_name",
    "thermal_zone",
    "floor_area_m2",
    "source_handoff_sha256",
    "source_stage1_sha256",
    "energy_use_kwh",
    "peak_load_w",
]


def finish(ok: bool, errors: List[str] | None = None) -> None:
    try:
        root = desktop_or_arg()
        metrics = {
            "ok": bool(ok),
            "case_id": CASE_SPEC.get("case_id"),
            "policy": "instruction_rule_no_reference_answer_comparison",
            "errors": errors or [],
        }
        (root / "multi_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    print("True" if ok else "False")
    raise SystemExit(0)


def desktop_or_arg() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    for candidate in (Path(r"C:\Users\user\Desktop"), Path("/home/user/Desktop"), Path.cwd()):
        try:
            if candidate.exists():
                return candidate.resolve()
        except Exception:
            pass
    return Path.cwd().resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", str(value or "").upper()).strip("-")


def contains_token(container: Any, token: str) -> bool:
    raw = container if isinstance(container, str) else json.dumps(container, ensure_ascii=False, sort_keys=True)
    return token.upper() in raw.upper() or norm(token) in norm(raw)


def read_text(path: Path, limit: int = 25_000_000) -> str:
    data = path.read_bytes()
    if len(data) > limit:
        data = data[:limit]
    return data.decode("utf-8", errors="ignore")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return data


def require_files(root: Path, names: Iterable[str], errors: List[str]) -> Dict[str, Path]:
    paths: Dict[str, Path] = {}
    for name in names:
        p = root / name
        paths[name] = p
        if not p.is_file() or p.stat().st_size <= 0:
            errors.append(f"missing_or_empty:{name}")
    return paths


def find_values(obj: Any, wanted_key: str) -> List[Any]:
    vals: List[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if norm(k) == norm(wanted_key):
                vals.append(v)
            vals.extend(find_values(v, wanted_key))
    elif isinstance(obj, list):
        for item in obj:
            vals.extend(find_values(item, wanted_key))
    return vals


def first_number(data: Dict[str, Any], key: str) -> float | None:
    for val in find_values(data, key):
        try:
            return float(val)
        except Exception:
            continue
    return None


def collect_keys(obj: Any) -> Set[str]:
    keys: Set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(norm(k))
            keys.update(collect_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            keys.update(collect_keys(item))
    return keys


def has_any_key_like(data: Dict[str, Any], candidates: Iterable[str]) -> bool:
    keys = collect_keys(data)
    wanted = [norm(c) for c in candidates]
    return any(any(w in key or key in w for w in wanted) for key in keys)


def any_hash_field(data: Dict[str, Any], key: str, expected: str) -> bool:
    return any(str(v).lower() == expected.lower() for v in find_values(data, key))


def require_tokens(data_or_text: Any, tokens: List[str], errors: List[str], label: str) -> None:
    seen: Set[str] = set()
    for tok in tokens:
        if tok in seen:
            continue
        seen.add(tok)
        if not contains_token(data_or_text, tok):
            errors.append(f"{label}:missing_token:{tok}")


def ifc_regex_counts(text: str) -> Dict[str, int]:
    up = text.upper()
    counts: Dict[str, int] = {}
    for cls in IFC_CLASSES:
        counts[cls] = len(re.findall(r"\b" + re.escape(cls.upper()) + r"\s*\(", up))
    counts["IfcRoof"] += len(re.findall(r"\bIFCROOFSTANDARDCASE\s*\(", up))
    return counts


def parse_ifc(path: Path, label: str, errors: List[str]) -> Dict[str, Any]:
    text = read_text(path)
    info: Dict[str, Any] = {
        "text": text,
        "counts": ifc_regex_counts(text),
        "schema": "",
        "root_ids": [],
        "names": {},
        "parsed_with_ifcopenshell": False,
    }
    try:
        import ifcopenshell  # type: ignore
    except Exception:
        return info

    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        errors.append(f"{label}:ifcopenshell_parse_failed:{type(exc).__name__}")
        return info

    info["parsed_with_ifcopenshell"] = True
    info["schema"] = str(getattr(model, "schema", ""))
    root_ids: List[str] = []
    names: Dict[str, List[str]] = {}
    counts: Dict[str, int] = {}
    for cls in IFC_CLASSES:
        try:
            entities = list(model.by_type(cls))
        except Exception:
            entities = []
        counts[cls] = len(entities)
        class_names: List[str] = []
        for ent in entities:
            gid = getattr(ent, "GlobalId", None)
            if gid:
                root_ids.append(str(gid))
            for attr in ("Name", "LongName", "ObjectType", "Description"):
                val = getattr(ent, attr, None)
                if val:
                    class_names.append(str(val))
        names[cls] = class_names
    info["counts"] = counts
    info["root_ids"] = root_ids
    info["names"] = names
    return info


def split_step_args(value: str) -> List[str]:
    args: List[str] = []
    start = 0
    depth = 0
    in_string = False
    index = 0
    while index < len(value):
        char = value[index]
        if char == "'":
            if in_string and index + 1 < len(value) and value[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                args.append(value[start:index].strip())
                start = index + 1
        index += 1
    args.append(value[start:].strip())
    return args


def parse_step_graph(text: str) -> Dict[int, Dict[str, Any]]:
    graph: Dict[int, Dict[str, Any]] = {}
    pattern = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(text):
        ref = int(match.group(1))
        graph[ref] = {
            "type": match.group(2).upper(),
            "args": split_step_args(match.group(3)),
        }
    return graph


def step_ref(value: str) -> int | None:
    match = re.fullmatch(r"\s*#(\d+)\s*", value)
    return int(match.group(1)) if match else None


def step_refs(value: str) -> List[int]:
    return [int(item) for item in re.findall(r"#(\d+)", value)]


def step_string(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return ""


def step_numbers(value: str) -> List[float]:
    pattern = r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[Ee][-+]?\d+)?"
    return [float(item) for item in re.findall(pattern, value)]


def step_entities_of_type(graph: Dict[int, Dict[str, Any]], ifc_type: str) -> List[int]:
    wanted = ifc_type.upper()
    return [ref for ref, entity in graph.items() if entity["type"] == wanted]


def step_entity_name(graph: Dict[int, Dict[str, Any]], ref: int) -> str:
    entity = graph.get(ref)
    if not entity or len(entity["args"]) < 3:
        return ""
    return step_string(entity["args"][2])


def step_placement_origin(
    graph: Dict[int, Dict[str, Any]],
    placement_ref: int | None,
    visited: Set[int] | None = None,
) -> Tuple[float, float, float] | None:
    if placement_ref is None:
        return (0.0, 0.0, 0.0)
    if visited is None:
        visited = set()
    if placement_ref in visited:
        return None
    visited.add(placement_ref)
    placement = graph.get(placement_ref)
    if not placement or placement["type"] != "IFCLOCALPLACEMENT" or len(placement["args"]) < 2:
        return None
    parent = step_placement_origin(graph, step_ref(placement["args"][0]), visited)
    axis_ref = step_ref(placement["args"][1])
    axis = graph.get(axis_ref or -1)
    if parent is None or not axis or axis["type"] != "IFCAXIS2PLACEMENT3D" or not axis["args"]:
        return None
    point = graph.get(step_ref(axis["args"][0]) or -1)
    if not point or point["type"] != "IFCCARTESIANPOINT" or not point["args"]:
        return None
    values = step_numbers(point["args"][0])
    if len(values) < 2:
        return None
    while len(values) < 3:
        values.append(0.0)
    return (parent[0] + values[0], parent[1] + values[1], parent[2] + values[2])


def step_product_geometry(graph: Dict[int, Dict[str, Any]], product_ref: int) -> Dict[str, Any] | None:
    product = graph.get(product_ref)
    if not product or len(product["args"]) < 7:
        return None
    placement_ref = step_ref(product["args"][5])
    representation_ref = step_ref(product["args"][6])
    origin = step_placement_origin(graph, placement_ref)
    representation = graph.get(representation_ref or -1)
    if origin is None or not representation or representation["type"] != "IFCPRODUCTDEFINITIONSHAPE":
        return None
    if len(representation["args"]) < 3:
        return None
    shape_refs = step_refs(representation["args"][2])
    if not shape_refs:
        return None
    shape = graph.get(shape_refs[0])
    if not shape or shape["type"] != "IFCSHAPEREPRESENTATION" or len(shape["args"]) < 4:
        return None
    solid_refs = step_refs(shape["args"][3])
    if not solid_refs:
        return None
    solid = graph.get(solid_refs[0])
    if not solid or solid["type"] != "IFCEXTRUDEDAREASOLID" or len(solid["args"]) < 4:
        return None
    profile = graph.get(step_ref(solid["args"][0]) or -1)
    solid_axis = graph.get(step_ref(solid["args"][1]) or -1)
    if not profile or profile["type"] != "IFCARBITRARYCLOSEDPROFILEDEF" or len(profile["args"]) < 3:
        return None
    curve = graph.get(step_ref(profile["args"][2]) or -1)
    if not curve or curve["type"] != "IFCPOLYLINE" or not curve["args"]:
        return None
    points: List[Tuple[float, float]] = []
    for point_ref in step_refs(curve["args"][0]):
        point = graph.get(point_ref)
        if not point or point["type"] != "IFCCARTESIANPOINT" or not point["args"]:
            return None
        values = step_numbers(point["args"][0])
        if len(values) < 2:
            return None
        points.append((values[0], values[1]))
    if len(points) < 4:
        return None
    solid_offset = (0.0, 0.0, 0.0)
    if solid_axis and solid_axis["type"] == "IFCAXIS2PLACEMENT3D" and solid_axis["args"]:
        solid_point = graph.get(step_ref(solid_axis["args"][0]) or -1)
        if solid_point and solid_point["type"] == "IFCCARTESIANPOINT" and solid_point["args"]:
            values = step_numbers(solid_point["args"][0])
            while len(values) < 3:
                values.append(0.0)
            solid_offset = (values[0], values[1], values[2])
    try:
        depth = float(solid["args"][3])
    except ValueError:
        return None
    area = 0.0
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    area = abs(area) / 2.0
    x_values = [point[0] + origin[0] + solid_offset[0] for point in points]
    y_values = [point[1] + origin[1] + solid_offset[1] for point in points]
    z_min = origin[2] + solid_offset[2]
    return {
        "placement_ref": placement_ref,
        "representation_ref": representation_ref,
        "area_m2": area,
        "bbox_m": [min(x_values), min(y_values), z_min, max(x_values), max(y_values), z_min + depth],
    }


def bbox_overlap_area(first: List[float], second: List[float]) -> float:
    overlap_x = max(0.0, min(first[3], second[3]) - max(first[0], second[0]))
    overlap_y = max(0.0, min(first[4], second[4]) - max(first[1], second[1]))
    return overlap_x * overlap_y


def check_ifc_geometry_topology(stage1_info: Dict[str, Any], errors: List[str]) -> None:
    graph = parse_step_graph(str(stage1_info["text"]))
    stage1_info["step_graph"] = graph
    expected_counts = {
        "IFCSPACE": 2,
        "IFCDOOR": 1,
        "IFCWINDOW": 1,
        "IFCOPENINGELEMENT": 2,
        "IFCRELVOIDSELEMENT": 2,
        "IFCRELFILLSELEMENT": 2,
    }
    for ifc_type, expected in expected_counts.items():
        actual = len(step_entities_of_type(graph, ifc_type))
        if actual != expected:
            errors.append(f"stage1.ifc:strict_count_mismatch:{ifc_type}:{actual}!={expected}")

    product_refs = (
        step_entities_of_type(graph, "IFCSPACE")
        + step_entities_of_type(graph, "IFCDOOR")
        + step_entities_of_type(graph, "IFCWINDOW")
        + step_entities_of_type(graph, "IFCOPENINGELEMENT")
    )
    products: Dict[int, Dict[str, Any]] = {}
    placement_refs: List[int] = []
    representation_refs: List[int] = []
    for ref in product_refs:
        geometry = step_product_geometry(graph, ref)
        if geometry is None or geometry["area_m2"] <= 0:
            errors.append(f"stage1.ifc:missing_or_invalid_product_geometry:{step_entity_name(graph, ref) or ref}")
            continue
        products[ref] = geometry
        if geometry["placement_ref"] is not None:
            placement_refs.append(int(geometry["placement_ref"]))
        if geometry["representation_ref"] is not None:
            representation_refs.append(int(geometry["representation_ref"]))
    if len(placement_refs) != len(set(placement_refs)):
        errors.append("stage1.ifc:products_share_object_placement")
    if len(representation_refs) != len(set(representation_refs)):
        errors.append("stage1.ifc:products_share_representation")

    spaces: Dict[str, Dict[str, Any]] = {}
    for ref in step_entities_of_type(graph, "IFCSPACE"):
        entity = graph[ref]
        name = step_entity_name(graph, ref)
        geometry = products.get(ref)
        if geometry is not None:
            spaces[name] = {
                **geometry,
                "ref": ref,
                "ifc_global_id": step_string(entity["args"][0]),
            }
    if set(spaces) != set(CASE_SPEC["required_spaces"]):
        errors.append(f"stage1.ifc:space_name_set_mismatch:{sorted(spaces)}")
    if all(name in spaces for name in CASE_SPEC["required_spaces"]):
        first = spaces[CASE_SPEC["required_spaces"][0]]
        second = spaces[CASE_SPEC["required_spaces"][1]]
        overlap = bbox_overlap_area(first["bbox_m"], second["bbox_m"])
        if overlap > 1e-6:
            errors.append(f"stage1.ifc:spaces_overlap:{overlap:.6f}")
        if abs(sum(item["area_m2"] for item in spaces.values()) - 20.16) > 0.01:
            errors.append("stage1.ifc:space_area_total_mismatch")

    storey_refs = set(step_entities_of_type(graph, "IFCBUILDINGSTOREY"))
    owned_spaces: Set[int] = set()
    for relation_ref in step_entities_of_type(graph, "IFCRELAGGREGATES"):
        args = graph[relation_ref]["args"]
        if len(args) > 5 and step_ref(args[4]) in storey_refs:
            owned_spaces.update(step_refs(args[5]))
    expected_space_refs = set(step_entities_of_type(graph, "IFCSPACE"))
    if not expected_space_refs.issubset(owned_spaces):
        errors.append("stage1.ifc:spaces_not_owned_by_storey")

    door_window_refs = set(step_entities_of_type(graph, "IFCDOOR") + step_entities_of_type(graph, "IFCWINDOW"))
    contained: Set[int] = set()
    for relation_ref in step_entities_of_type(graph, "IFCRELCONTAINEDINSPATIALSTRUCTURE"):
        args = graph[relation_ref]["args"]
        if len(args) > 5 and step_ref(args[5]) in storey_refs:
            contained.update(step_refs(args[4]))
    if not door_window_refs.issubset(contained):
        errors.append("stage1.ifc:door_or_window_not_storey_contained")

    void_pairs: List[Tuple[int, int]] = []
    for ref in step_entities_of_type(graph, "IFCRELVOIDSELEMENT"):
        args = graph[ref]["args"]
        if len(args) > 5 and step_ref(args[4]) is not None and step_ref(args[5]) is not None:
            void_pairs.append((int(step_ref(args[4]) or 0), int(step_ref(args[5]) or 0)))
    fill_pairs: List[Tuple[int, int]] = []
    for ref in step_entities_of_type(graph, "IFCRELFILLSELEMENT"):
        args = graph[ref]["args"]
        if len(args) > 5 and step_ref(args[4]) is not None and step_ref(args[5]) is not None:
            fill_pairs.append((int(step_ref(args[4]) or 0), int(step_ref(args[5]) or 0)))
    south_walls = {
        ref for ref in step_entities_of_type(graph, "IFCWALL") if step_entity_name(graph, ref).upper() == "SOUTH WALL"
    }
    opening_refs = set(step_entities_of_type(graph, "IFCOPENINGELEMENT"))
    if len(void_pairs) != 2 or any(host not in south_walls or opening not in opening_refs for host, opening in void_pairs):
        errors.append("stage1.ifc:invalid_south_wall_void_relationships")
    if len(fill_pairs) != 2 or {opening for opening, _ in fill_pairs} != opening_refs:
        errors.append("stage1.ifc:invalid_opening_fill_relationships")
    if {filling for _, filling in fill_pairs} != door_window_refs:
        errors.append("stage1.ifc:door_window_fill_set_mismatch")

    site_office = spaces.get("SITE-OFFICE")
    if site_office is not None:
        site_bbox = site_office["bbox_m"]
        for ref in door_window_refs:
            geometry = products.get(ref)
            if geometry is None:
                continue
            bbox = geometry["bbox_m"]
            if bbox[0] < site_bbox[0] - 1e-6 or bbox[3] > site_bbox[3] + 1e-6:
                errors.append(f"stage1.ifc:filling_outside_site_office_x:{step_entity_name(graph, ref)}")
            if bbox[1] < -0.02 or bbox[4] > 0.22 or bbox[2] < -1e-6 or bbox[5] > 3.01:
                errors.append(f"stage1.ifc:filling_outside_south_wall:{step_entity_name(graph, ref)}")
    stage1_info["geometry"] = {"spaces": spaces, "products": products}


def check_ifc_basic(
    path: Path,
    required_tokens: List[str],
    min_counts: Dict[str, int],
    errors: List[str],
    label: str,
    require_ifc4: bool = True,
) -> Dict[str, Any]:
    if path.stat().st_size < 1000:
        errors.append(f"{label}:too_small")
    info = parse_ifc(path, label, errors)
    text = info["text"]
    up = text.upper()
    if "ISO-10303-21" not in up or "FILE_SCHEMA" not in up or "IFC" not in up:
        errors.append(f"{label}:not_step_ifc_like")
    if require_ifc4 and "IFC4" not in up and "IFC4" not in str(info.get("schema", "")).upper():
        errors.append(f"{label}:schema_not_ifc4")
    root_ids = info.get("root_ids") or []
    if root_ids and len(root_ids) != len(set(root_ids)):
        errors.append(f"{label}:duplicate_global_ids")
    require_tokens(text, required_tokens, errors, label)
    counts = info["counts"]
    for cls, expected_min in min_counts.items():
        if counts.get(cls, 0) < int(expected_min):
            errors.append(f"{label}:count_too_low:{cls}:{counts.get(cls, 0)}<{expected_min}")
    return info


def check_stage_derives_from_init(init_path: Path, stage1_path: Path, init_info: Dict[str, Any], stage1_info: Dict[str, Any], errors: List[str]) -> None:
    if sha256_file(init_path) == sha256_file(stage1_path):
        errors.append("stage1.ifc:byte_identical_to_init")
    init_size = max(init_path.stat().st_size, 1)
    stage_size = stage1_path.stat().st_size
    ratio = stage_size / init_size
    if ratio < 0.08 or ratio > 80:
        errors.append(f"stage1.ifc:size_ratio_implausible:{ratio:.3f}")
    init_counts = init_info["counts"]
    stage_counts = stage1_info["counts"]
    for cls in ("IfcProject", "IfcBuilding", "IfcBuildingStorey"):
        if init_counts.get(cls, 0) > 0 and stage_counts.get(cls, 0) < 1:
            errors.append(f"stage1.ifc:lost_required_baseline_class:{cls}")
    for cls in ("IfcWall", "IfcSlab", "IfcDoor", "IfcWindow", "IfcRoof"):
        base = init_counts.get(cls, 0)
        if base <= 0:
            continue
        min_allowed = max(1, math.floor(base * 0.35))
        if stage_counts.get(cls, 0) < min_allowed:
            errors.append(f"stage1.ifc:baseline_count_drop:{cls}:{stage_counts.get(cls, 0)}<{min_allowed}")
    if not any(stage_counts.get(cls, 0) > 0 for cls in ("IfcWall", "IfcSlab", "IfcSpace")):
        errors.append("stage1.ifc:not_a_building_model")


def check_software_stage(data: Dict[str, Any], expected: str, errors: List[str], label: str) -> None:
    values: List[Any] = []
    for key in ("software_stage", "stage", "authoring_software", "software", "source_software", "tool"):
        values.extend(find_values(data, key))
    if not values:
        errors.append(f"{label}:missing_software_stage")
        return
    if not any(expected.lower() in str(v).lower() for v in values):
        errors.append(f"{label}:software_stage_not_{expected}")


def extract_space_records(data: Dict[str, Any], errors: List[str], label: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for key in ("spaces", "space_names", "rooms", "ifc_spaces"):
        for val in find_values(data, key):
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        records.append(item)
                    elif isinstance(item, str):
                        records.append({"name": item})
            elif isinstance(val, dict):
                for name, item in val.items():
                    rec = {"name": name}
                    if isinstance(item, dict):
                        rec.update(item)
                    records.append(rec)
    dedup: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        name = str(rec.get("name") or rec.get("space_name") or rec.get("room") or "")
        if name:
            dedup[norm(name)] = rec
    records = list(dedup.values())
    if not records:
        errors.append(f"{label}:missing_space_records")
    return records


def check_handoff(
    path: Path,
    source_file: Path,
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    stage1_info: Dict[str, Any],
    errors: List[str],
    label: str,
    expected_stage: str | None = None,
) -> Dict[str, Any]:
    data = load_json(path)
    if not any_hash_field(data, "source_sha256", sha256_file(source_file)):
        errors.append(f"{label}:source_sha256_mismatch")
    if not contains_token(data, CASE_SPEC["case_id"]):
        errors.append(f"{label}:case_id_missing")
    if not has_any_key_like(data, ("spaces", "space_names", "rooms", "ifc_spaces")):
        errors.append(f"{label}:missing_structured_space_section")
    if required_zones and not has_any_key_like(data, ("thermal_zones", "zones", "zone_names")):
        errors.append(f"{label}:missing_structured_zone_section")
    require_tokens(data, required_spaces, errors, f"{label}:spaces")
    require_tokens(data, required_zones, errors, f"{label}:zones")
    require_tokens(data, required_tokens, errors, f"{label}:handoff_tokens")
    if expected_stage:
        check_software_stage(data, expected_stage, errors, label)

    records = extract_space_records(data, errors, label)
    seen_spaces = {norm(r.get("name") or r.get("space_name")) for r in records}
    for space in required_spaces:
        if norm(space) not in seen_spaces:
            errors.append(f"{label}:missing_space_record:{space}")
    for rec in records:
        name = rec.get("name") or rec.get("space_name")
        zone = rec.get("thermal_zone") or rec.get("zone") or rec.get("thermalZone")
        if not zone:
            errors.append(f"{label}:space_missing_thermal_zone:{name}")
        area = rec.get("floor_area_m2") or rec.get("area_m2") or rec.get("net_floor_area_m2")
        try:
            if float(area) <= 0:
                errors.append(f"{label}:space_area_nonpositive:{name}")
        except Exception:
            errors.append(f"{label}:space_area_invalid:{name}")
        for count_key in ("door_count", "window_count"):
            try:
                raw_count = rec.get(count_key)
                count_value = float(raw_count)
                if isinstance(raw_count, bool) or count_value < 0 or not count_value.is_integer():
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{label}:space_invalid_{count_key}:{name}")
    for count_key, cls, minimum in (
        ("door_count", "IfcDoor", int(CASE_SPEC.get("min_doors", 0))),
        ("window_count", "IfcWindow", int(CASE_SPEC.get("min_windows", 0))),
    ):
        try:
            reported_total = sum(int(rec[count_key]) for rec in records)
        except (KeyError, TypeError, ValueError):
            continue
        if reported_total < minimum:
            errors.append(f"{label}:{count_key}_below_case_minimum:{reported_total}<{minimum}")
        actual_total = int(stage1_info["counts"].get(cls, 0))
        if reported_total > actual_total:
            errors.append(f"{label}:{count_key}_exceeds_stage1:{reported_total}>{actual_total}")
    count_sections = (
        find_values(data, "bim_counts")
        + find_values(data, "ifc_counts")
        + find_values(data, "entity_counts")
    )
    bim_counts = next((value for value in count_sections if isinstance(value, dict)), None)
    if bim_counts is None:
        errors.append(f"{label}:missing_bim_counts")
    else:
        normalized_counts = {norm(key): value for key, value in bim_counts.items()}
        for cls in IFC_CLASSES:
            try:
                reported = int(normalized_counts[norm(cls)])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{label}:missing_or_invalid_bim_count:{cls}")
                continue
            actual = int(stage1_info["counts"].get(cls, 0))
            if reported != actual:
                errors.append(f"{label}:bim_count_mismatch:{cls}:{reported}!={actual}")
        graph = stage1_info.get("step_graph") or {}
        for key, ifc_type in (
            ("IfcOpeningElement", "IFCOPENINGELEMENT"),
            ("IfcRelVoidsElement", "IFCRELVOIDSELEMENT"),
            ("IfcRelFillsElement", "IFCRELFILLSELEMENT"),
        ):
            actual = len(step_entities_of_type(graph, ifc_type))
            try:
                reported = int(normalized_counts[norm(key)])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{label}:missing_or_invalid_bim_count:{key}")
                continue
            if reported != actual:
                errors.append(f"{label}:bim_count_mismatch:{key}:{reported}!={actual}")

    stage_spaces = (stage1_info.get("geometry") or {}).get("spaces") or {}
    records_by_name = {
        norm(record.get("name") or record.get("space_name")): record
        for record in records
    }
    for name, geometry in stage_spaces.items():
        record = records_by_name.get(norm(name))
        if record is None:
            continue
        try:
            reported_area = float(
                record.get("floor_area_m2")
                or record.get("area_m2")
                or record.get("net_floor_area_m2")
            )
            if abs(reported_area - float(geometry["area_m2"])) > 0.01:
                errors.append(f"{label}:space_area_mismatch_ifc:{name}")
        except (TypeError, ValueError):
            pass
        if str(record.get("ifc_global_id") or "") != str(geometry.get("ifc_global_id") or ""):
            errors.append(f"{label}:space_global_id_mismatch_ifc:{name}")
        reported_bbox = record.get("bbox_m")
        if isinstance(reported_bbox, list) and len(reported_bbox) == 6:
            try:
                if any(
                    abs(float(reported) - float(actual)) > 0.01
                    for reported, actual in zip(reported_bbox, geometry["bbox_m"])
                ):
                    errors.append(f"{label}:space_bbox_mismatch_ifc:{name}")
            except (TypeError, ValueError):
                errors.append(f"{label}:space_bbox_invalid:{name}")
        else:
            errors.append(f"{label}:space_bbox_missing:{name}")
    if stage_spaces:
        stage_area = sum(float(item["area_m2"]) for item in stage_spaces.values())
        reported_total = first_number(data, "building_area_m2")
        if reported_total is None or abs(reported_total - stage_area) > 0.01:
            errors.append(f"{label}:building_area_mismatch_ifc")
    overlap_values = find_values(data, "space_overlap_area_m2")
    if not overlap_values:
        errors.append(f"{label}:missing_space_overlap_area")
    else:
        try:
            if abs(float(overlap_values[0])) > 1e-8:
                errors.append(f"{label}:space_overlap_area_nonzero")
        except (TypeError, ValueError):
            errors.append(f"{label}:space_overlap_area_invalid")
    return data


def get_handoff_area(data: Dict[str, Any]) -> float | None:
    direct = first_number(data, "building_area_m2") or first_number(data, "total_floor_area_m2")
    if direct and direct > 0:
        return direct
    total = 0.0
    found = False
    for rec in extract_space_records(data, [], "handoff.json"):
        area = rec.get("floor_area_m2") or rec.get("area_m2") or rec.get("net_floor_area_m2")
        try:
            total += float(area)
            found = True
        except Exception:
            pass
    return total if found else None


def parse_osm_objects(text: str) -> List[Dict[str, Any]]:
    objects: List[Dict[str, Any]] = []
    current_type: str | None = None
    fields: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if current_type is None:
            match = re.match(r"^(OS:[A-Za-z0-9:]+)\s*,\s*$", line, flags=re.IGNORECASE)
            if match:
                current_type = match.group(1).upper()
                fields = []
            continue
        value = raw_line.split("!-", 1)[0].strip()
        if not value:
            continue
        terminal = value.endswith(";")
        if value.endswith((",", ";")):
            value = value[:-1].strip()
        fields.append(value)
        if terminal:
            objects.append({"type": current_type, "fields": fields})
            current_type = None
            fields = []
    return objects


def check_osm_relationships(text: str, required_spaces: List[str], required_zones: List[str], errors: List[str]) -> None:
    objects = parse_osm_objects(text)
    by_type: Dict[str, List[List[str]]] = {}
    for obj in objects:
        by_type.setdefault(str(obj["type"]), []).append(list(obj["fields"]))

    zones = {fields[1]: fields[0] for fields in by_type.get("OS:THERMALZONE", []) if len(fields) > 1}
    if set(required_zones) - set(zones):
        errors.append("result.osm:missing_required_thermal_zone_objects")
    spaces = {fields[1]: fields for fields in by_type.get("OS:SPACE", []) if len(fields) > 10}
    for space_name, zone_name in zip(required_spaces, required_zones):
        fields = spaces.get(space_name)
        if fields is None or fields[10] != zones.get(zone_name):
            errors.append(f"result.osm:space_zone_link_mismatch:{space_name}:{zone_name}")

    surfaces = {fields[0] for fields in by_type.get("OS:SURFACE", []) if fields}
    hosted_types: List[str] = []
    for fields in by_type.get("OS:SUBSURFACE", []):
        if len(fields) > 4 and fields[4] in surfaces:
            hosted_types.append(fields[2].upper())
    if not any("DOOR" in value for value in hosted_types):
        errors.append("result.osm:missing_hosted_door")
    if not any("WINDOW" in value for value in hosted_types):
        errors.append("result.osm:missing_hosted_window")

    days = {fields[0]: fields for fields in by_type.get("OS:SCHEDULE:DAY", []) if fields}
    schedules = {
        fields[1]: fields
        for fields in by_type.get("OS:SCHEDULE:RULESET", [])
        if len(fields) > 3
    }
    equipment_schedule = schedules.get("LowOfficeEquipmentSchedule")
    if equipment_schedule is None or equipment_schedule[3] not in days:
        errors.append("result.osm:invalid_low_office_equipment_schedule_link")
    else:
        values = []
        for token in days[equipment_schedule[3]][4:]:
            try:
                values.append(float(token))
            except ValueError:
                continue
        if not values or any(not math.isfinite(value) for value in values):
            errors.append("result.osm:invalid_low_office_equipment_schedule_values")


def check_osm(path: Path, handoff_hash: str, required_spaces: List[str], required_zones: List[str], required_tokens: List[str], flow_tokens: List[str], errors: List[str]) -> Dict[str, int]:
    if path.stat().st_size < 1000:
        errors.append("result.osm:too_small")
    text = read_text(path)
    up = text.upper()
    if "OS:VERSION" not in up:
        errors.append("result.osm:no_os_version")
    if not re.search(r"\bOS:VERSION\s*,[^;]*\b3\.10\.0\s*;", text, flags=re.IGNORECASE | re.DOTALL):
        errors.append("result.osm:openstudio_version_not_3_10_0")
    require_tokens(text, required_spaces, errors, "result.osm:spaces")
    require_tokens(text, required_zones, errors, "result.osm:zones")
    require_tokens(text, required_tokens, errors, "result.osm:tokens")
    require_tokens(text, flow_tokens, errors, "result.osm:flow_tokens")
    if handoff_hash[:12].upper() not in up:
        errors.append("result.osm:missing_handoff_hash_prefix")
    check_osm_relationships(text, required_spaces, required_zones, errors)
    counts = {
        "space_count": len(re.findall(r"\bOS:SPACE\s*,", up)),
        "zone_count": len(re.findall(r"\bOS:THERMALZONE\s*,", up)),
        "surface_count": len(re.findall(r"\bOS:SURFACE\s*,", up)),
        "subsurface_count": len(re.findall(r"\bOS:SUBSURFACE\s*,", up)),
    }
    if counts["space_count"] < len(required_spaces):
        errors.append(f"result.osm:space_count_too_low:{counts['space_count']}<{len(required_spaces)}")
    if counts["zone_count"] < len(required_zones):
        errors.append(f"result.osm:thermal_zone_count_too_low:{counts['zone_count']}<{len(required_zones)}")
    if counts["surface_count"] < len(required_spaces) * 4:
        errors.append(f"result.osm:surface_count_too_low:{counts['surface_count']}<{len(required_spaces) * 4}")
    min_subsurfaces = int(CASE_SPEC.get("min_windows", 0)) + int(CASE_SPEC.get("min_doors", 0))
    if counts["subsurface_count"] < min_subsurfaces:
        errors.append(f"result.osm:subsurface_count_too_low:{counts['subsurface_count']}<{min_subsurfaces}")
    return counts


def check_flow_report(
    path: Path,
    handoff_path: Path,
    osm_path: Path,
    handoff_data: Dict[str, Any],
    osm_counts: Dict[str, int],
    stage1_info: Dict[str, Any],
    required_spaces: List[str],
    required_zones: List[str],
    errors: List[str],
) -> Dict[str, Any]:
    data = load_json(path)
    if not any_hash_field(data, "consumed_handoff_sha256", sha256_file(handoff_path)):
        errors.append("flow_report:consumed_handoff_sha256_mismatch")
    if not any_hash_field(data, "osm_sha256", sha256_file(osm_path)):
        errors.append("flow_report:osm_sha256_mismatch")
    require_tokens(data, required_spaces, errors, "flow_report:spaces")
    require_tokens(data, required_zones, errors, "flow_report:zones")
    require_tokens(data, CASE_SPEC["software_chain"], errors, "flow_report:software_chain")
    if not has_any_key_like(data, ("software_chain", "stage_sequence", "stages")):
        errors.append("flow_report:missing_stage_sequence")
    version_values = [str(value).strip() for value in find_values(data, "openstudio_version")]
    if not version_values:
        errors.append("flow_report:missing_openstudio_version")
    elif not any(value.startswith("3.10.0") for value in version_values):
        errors.append("flow_report:openstudio_version_not_3_10_0")

    for key in ("building_area_m2", "room_count", "thermal_zone_count", "door_count", "window_count", "window_wall_ratio", "surface_count", "subsurface_count"):
        if first_number(data, key) is None:
            errors.append(f"flow_report:missing_numeric:{key}")
    for key in ("weather_file", "schedule_set", "construction_set"):
        vals = [str(v).strip() for v in find_values(data, key) if str(v).strip()]
        if not vals:
            errors.append(f"flow_report:missing_field:{key}")
    weather_vals = [str(v) for v in find_values(data, "weather_file")]
    if weather_vals and not any(v.lower().endswith(".epw") or "design" in v.lower() for v in weather_vals):
        errors.append("flow_report:weather_file_not_epw_or_design_day")

    area = first_number(data, "building_area_m2")
    handoff_area = get_handoff_area(handoff_data)
    if area is not None and handoff_area is not None and abs(area - handoff_area) > max(0.5, handoff_area * 0.03):
        errors.append(f"flow_report:area_mismatch:{area:.3f}!={handoff_area:.3f}")
    room_count = first_number(data, "room_count")
    zone_count = first_number(data, "thermal_zone_count")
    if room_count is not None and int(round(room_count)) != len(required_spaces):
        errors.append("flow_report:room_count_mismatch")
    if zone_count is not None and int(round(zone_count)) != len(required_zones):
        errors.append("flow_report:thermal_zone_count_mismatch")
    if first_number(data, "surface_count") is not None and int(first_number(data, "surface_count") or 0) != osm_counts["surface_count"]:
        errors.append("flow_report:surface_count_mismatch_osm")
    if first_number(data, "subsurface_count") is not None and int(first_number(data, "subsurface_count") or 0) != osm_counts["subsurface_count"]:
        errors.append("flow_report:subsurface_count_mismatch_osm")
    handoff_records = extract_space_records(handoff_data, [], "handoff.json")
    for key, cls in (("door_count", "IfcDoor"), ("window_count", "IfcWindow")):
        val = first_number(data, key)
        if val is None:
            continue
        if not float(val).is_integer():
            errors.append(f"flow_report:{key}_not_integer")
            continue
        rounded = int(val)
        if rounded > stage1_info["counts"].get(cls, 0):
            errors.append(f"flow_report:{key}_exceeds_stage1")
        try:
            handoff_total = sum(int(rec[key]) for rec in handoff_records)
        except (KeyError, TypeError, ValueError):
            continue
        if rounded != handoff_total:
            errors.append(f"flow_report:{key}_mismatch_handoff:{rounded}!={handoff_total}")
    wwr = first_number(data, "window_wall_ratio")
    if wwr is not None and not (0.0 <= wwr <= 0.95):
        errors.append("flow_report:window_wall_ratio_out_of_range")
    return data


def check_model_summary_csv(
    path: Path,
    handoff_hash: str,
    stage1_hash: str,
    handoff_data: Dict[str, Any],
    flow_data: Dict[str, Any],
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    errors: List[str],
) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < max(len(required_spaces), 1):
        errors.append(f"model_summary.csv:row_count_too_low:{len(rows)}")
        return
    fields = {norm(x) for x in (rows[0].keys() if rows else [])}
    for required_col in REQUIRED_SUMMARY_COLUMNS:
        if norm(required_col) not in fields:
            errors.append(f"model_summary.csv:missing_column:{required_col}")
    text = json.dumps(rows, ensure_ascii=False)
    require_tokens(text, required_spaces, errors, "model_summary.csv:spaces")
    require_tokens(text, required_zones, errors, "model_summary.csv:zones")
    require_tokens(text, required_tokens, errors, "model_summary.csv:tokens")
    seen_spaces: Set[str] = set()
    seen_zones: Set[str] = set()
    total_area = 0.0
    total_energy = 0.0
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
            break
        name = next((str(v) for k, v in row.items() if norm(k) == norm("space_name")), "")
        zone = next((str(v) for k, v in row.items() if norm(k) == norm("thermal_zone")), "")
        seen_spaces.add(norm(name))
        seen_zones.add(norm(zone))
        val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_handoff_sha256")), "")
        if val != handoff_hash.lower():
            errors.append("model_summary.csv:source_handoff_sha256_mismatch")
            break
        stage_val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_stage1_sha256")), "")
        if stage_val != stage1_hash.lower():
            errors.append("model_summary.csv:source_stage1_sha256_mismatch")
            break
        try:
            area = float(next((v for k, v in row.items() if norm(k) == norm("floor_area_m2")), ""))
            if area <= 0:
                errors.append(f"model_summary.csv:nonpositive_area:{name}")
            total_area += area
        except Exception:
            errors.append(f"model_summary.csv:invalid_area:{name}")
        try:
            energy = float(next((v for k, v in row.items() if norm(k) == norm("energy_use_kwh")), ""))
            peak = float(next((v for k, v in row.items() if norm(k) == norm("peak_load_w")), ""))
            if energy <= 0 or peak <= 0:
                errors.append(f"model_summary.csv:nonpositive_energy_or_peak:{name}")
            total_energy += energy
        except Exception:
            errors.append(f"model_summary.csv:invalid_energy_or_peak:{name}")
    for space in required_spaces:
        if norm(space) not in seen_spaces:
            errors.append(f"model_summary.csv:missing_required_space:{space}")
    for zone in required_zones:
        if norm(zone) not in seen_zones:
            errors.append(f"model_summary.csv:missing_required_zone:{zone}")
    handoff_area = get_handoff_area(handoff_data)
    if handoff_area is not None and abs(total_area - handoff_area) > max(0.5, handoff_area * 0.03):
        errors.append(f"model_summary.csv:area_mismatch_handoff:{total_area:.3f}!={handoff_area:.3f}")
    flow_area = first_number(flow_data, "building_area_m2")
    if flow_area is not None and abs(total_area - flow_area) > max(0.5, flow_area * 0.03):
        errors.append(f"model_summary.csv:area_mismatch_flow:{total_area:.3f}!={flow_area:.3f}")
    if total_area > 0:
        eui = total_energy / total_area
        if not (5.0 <= eui <= 800.0):
            errors.append(f"model_summary.csv:eui_out_of_range:{eui:.3f}")


def evaluate(root: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    paths = require_files(root, CASE_SPEC["required_files"], errors)
    if errors:
        return False, errors

    init_path = paths["init.ifc"]
    init_info = check_ifc_basic(
        init_path,
        [],
        {"IfcProject": 1, "IfcBuilding": 1, "IfcBuildingStorey": 1},
        errors,
        "init.ifc",
        require_ifc4=False,
    )

    stage1 = paths["stage1.ifc"]
    stage1_min_counts = {
        "IfcSpace": len(CASE_SPEC["required_spaces"]),
        "IfcDoor": CASE_SPEC.get("min_doors", 0),
        "IfcWindow": CASE_SPEC.get("min_windows", 0),
        "IfcBuildingStorey": CASE_SPEC.get("min_storeys", 1),
    }
    if CASE_SPEC.get("min_roofs", 0):
        stage1_min_counts["IfcRoof"] = CASE_SPEC.get("min_roofs", 0)
    stage1_info = check_ifc_basic(stage1, CASE_SPEC["stage1_tokens"], stage1_min_counts, errors, "stage1.ifc")
    stage1_header = stage1_info["text"][:5000].upper()
    is_archicad_27 = "ARCHICAD 27" in stage1_header or bool(
        re.search(r"IFCAPPLICATION\([^;]*'27'[^;]*'ARCHICAD", stage1_header)
    )
    if "IFCOPENSHELL" in stage1_header or not is_archicad_27:
        errors.append("stage1.ifc:archicad_version_not_27")
    check_stage_derives_from_init(init_path, stage1, init_info, stage1_info, errors)
    check_ifc_geometry_topology(stage1_info, errors)

    handoff = paths["handoff.json"]
    handoff_data = check_handoff(
        handoff,
        stage1,
        CASE_SPEC["required_spaces"],
        CASE_SPEC["required_zones"],
        CASE_SPEC["handoff_tokens"],
        stage1_info,
        errors,
        "handoff.json",
        expected_stage=CASE_SPEC.get("expected_stage"),
    )
    handoff_hash = sha256_file(handoff)
    flow_tokens = ["weather_file", "schedule_set", "construction_set"]
    osm_counts = check_osm(paths["result.osm"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], flow_tokens, errors)
    flow_data = check_flow_report(paths["flow_report.json"], handoff, paths["result.osm"], handoff_data, osm_counts, stage1_info, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
    check_model_summary_csv(paths["model_summary.csv"], handoff_hash, sha256_file(stage1), handoff_data, flow_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors)

    return not errors, errors


def main() -> None:
    try:
        root = desktop_or_arg()
        ok, errors = evaluate(root)
        finish(ok, errors)
    except SystemExit:
        raise
    except Exception as exc:
        finish(False, [f"exception:{type(exc).__name__}:{exc}"])


if __name__ == "__main__":
    main()
