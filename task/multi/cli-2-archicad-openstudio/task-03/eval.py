# EngiWorld Archicad -> OpenStudio multi-software flow evaluator.
# This evaluator checks instruction-derived artifacts and never compares against ground_truth files.
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-03-windows',
 'mode': 'two_stage',
 'software_chain': ['archicad', 'openstudio'],
 'required_files': ['init.ifc',
                    'stage1.ifc',
                    'handoff.json',
                    'native_stage_log.json',
                    'result.osm',
                    'workflow.osw',
                    'weather.epw',
                    'flow_report.json',
                    'model_summary.csv',
                    'run/eplusout.sql',
                    'run/eplusout.err',
                    'run/eplusout.end'],
 'required_spaces': ['READING', 'GALLERY', 'QUIET-POD-01', 'QUIET-POD-02'],
 'required_zones': ['READING-ZN', 'GALLERY-ZN', 'QUIET-POD-01-ZN', 'QUIET-POD-02-ZN'],
 'stage1_tokens': ['EW2A03',
                   'READING',
                   'GALLERY',
                   'QUIET-POD-01',
                   'QUIET-POD-02',
                   'multi-cli-2-archicad-openstudio-task-03-windows'],
 'handoff_tokens': ['LIBRARY-STAIR',
                    'ROOF',
                    'low lighting',
                    'independent reservation schedule'],
 'osm_tokens': ['QUIET-POD-01-ZN',
                'QUIET-POD-02-ZN'],
 'summary_tokens': ['READING', 'GALLERY', 'QUIET-POD-01', 'QUIET-POD-02'],
 'min_windows': 0,
 'min_doors': 0,
 'min_roofs': 1,
 'min_storeys': 2,
 'baseline_counts': {'IfcProject': 1,
                     'IfcSite': 1,
                     'IfcBuilding': 1,
                     'IfcBuildingStorey': 2,
                     'IfcSpace': 7,
                     'IfcWall': 0,
                     'IfcSlab': 2,
                     'IfcRoof': 1,
                     'IfcStair': 1,
                     'IfcDoor': 0,
                     'IfcWindow': 0,
                     'IfcOpeningElement': 0},
 'init_sha256': '02ab8c2df6a8c458f86c70116caf4eb1b6973c733a9ec89a4384ecf0ffd5eb3f',
 'target_areas_m2': {'READING': 48.0,
                     'GALLERY': 15.0,
                     'QUIET-POD-01': 9.0,
                     'QUIET-POD-02': 9.0},
 'preserved_space_names': ['G-LOBBY', 'G-STACKS', 'G-WC'],
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
    "IfcStair",
    "IfcDoor",
    "IfcWindow",
    "IfcOpeningElement",
]

TARGET_RENAMES = {
    "3Rlo30Iwj9wgg8TKtd50ps": ("G-READING", "READING"),
    "3ZR0m1Ntb33vV6e1rYTnHX": ("1-GALLERY", "GALLERY"),
    "01lPFJfmrB4BbLjG_CYlLJ": ("1-STUDY-1", "QUIET-POD-01"),
    "0fjp0wxQP12xBe$90sQKG2": ("1-STUDY-2", "QUIET-POD-02"),
}

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


def parse_iso_timestamp(value: Any) -> datetime:
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})?",
        str(value),
    )
    if match is None:
        raise ValueError("invalid ISO-8601 timestamp")
    fraction = f".{match.group(2)[:6]}" if match.group(2) else ""
    timezone = "+00:00" if match.group(3) == "Z" else (match.group(3) or "")
    return datetime.fromisoformat(f"{match.group(1)}{fraction}{timezone}")


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
    with path.open("r", encoding="utf-8-sig") as f:
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


def polygon_area_xy(points: List[Tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(sum(
        points[i][0] * points[(i + 1) % len(points)][1]
        - points[(i + 1) % len(points)][0] * points[i][1]
        for i in range(len(points))
    )) / 2.0


def profile_area_m2(profile: Any, unit_scale: float) -> float | None:
    try:
        if profile.is_a("IfcRectangleProfileDef"):
            return float(profile.XDim) * float(profile.YDim) * unit_scale * unit_scale
        if profile.is_a("IfcCircleProfileDef"):
            return math.pi * float(profile.Radius) ** 2 * unit_scale * unit_scale
        if profile.is_a("IfcArbitraryClosedProfileDef") or profile.is_a("IfcArbitraryProfileDefWithVoids"):
            outer = profile.OuterCurve
            if not outer.is_a("IfcPolyline"):
                return None
            points = [
                (float(point.Coordinates[0]) * unit_scale, float(point.Coordinates[1]) * unit_scale)
                for point in outer.Points
            ]
            area = polygon_area_xy(points)
            for inner in list(getattr(profile, "InnerCurves", None) or []):
                if inner.is_a("IfcPolyline"):
                    inner_points = [
                        (float(point.Coordinates[0]) * unit_scale, float(point.Coordinates[1]) * unit_scale)
                        for point in inner.Points
                    ]
                    area -= polygon_area_xy(inner_points)
            return max(area, 0.0)
    except Exception:
        return None
    return None


def ifc_space_floor_areas(model: Any) -> Dict[str, float]:
    try:
        from ifcopenshell.util.element import get_psets  # type: ignore
        from ifcopenshell.util.unit import calculate_unit_scale  # type: ignore
        unit_scale = float(calculate_unit_scale(model))
    except Exception:
        get_psets = None
        unit_scale = 1.0

    areas: Dict[str, float] = {}
    for space in model.by_type("IfcSpace"):
        name = norm(getattr(space, "Name", None))
        if not name:
            continue
        area: float | None = None
        if get_psets is not None:
            try:
                quantities = get_psets(space, qtos_only=True)
                for quantity_set in quantities.values():
                    if not isinstance(quantity_set, dict):
                        continue
                    for key in ("NetFloorArea", "GrossFloorArea"):
                        value = quantity_set.get(key)
                        if isinstance(value, (int, float)) and float(value) > 0:
                            area = float(value) * unit_scale * unit_scale
                            break
                    if area is not None:
                        break
            except Exception:
                pass
        if area is None:
            representation = getattr(space, "Representation", None)
            for shape_representation in list(getattr(representation, "Representations", None) or []):
                for item in list(getattr(shape_representation, "Items", None) or []):
                    try:
                        candidates = model.traverse(item)
                    except Exception:
                        candidates = [item]
                    for candidate in candidates:
                        if candidate.is_a("IfcExtrudedAreaSolid"):
                            area = profile_area_m2(candidate.SweptArea, unit_scale)
                            if area is not None and area > 0:
                                break
                    if area is not None and area > 0:
                        break
                if area is not None and area > 0:
                    break
        if area is not None and area > 0:
            areas[name] = area
    return areas


def canonical_ifc_value(value: Any, *, is_top: bool = False, stack: Tuple[Tuple[str, int], ...] = ()) -> Any:
    if hasattr(value, "is_a") and hasattr(value, "attribute_name"):
        entity_class = str(value.is_a())
        is_root = bool(value.is_a("IfcRoot"))
        global_id = str(getattr(value, "GlobalId", "") or "") if is_root else ""
        if is_root and not is_top:
            return ("IfcRootRef", entity_class, global_id)
        marker = (entity_class, int(value.id()))
        if marker in stack:
            return ("Cycle", entity_class)
        attributes = []
        for index, nested in enumerate(value):
            attribute = str(value.attribute_name(index))
            if is_top and attribute == "OwnerHistory":
                continue
            if is_top and global_id in TARGET_RENAMES and attribute == "Name":
                continue
            if is_top and entity_class == "IfcProject" and attribute == "Description":
                continue
            attributes.append((attribute, canonical_ifc_value(nested, stack=stack + (marker,))))
        return (entity_class, tuple(attributes))
    if isinstance(value, (tuple, list)):
        return tuple(canonical_ifc_value(item, stack=stack) for item in value)
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, (str, int, bool, type(None))):
        return value
    return repr(value)


def parse_ifc(path: Path, label: str, errors: List[str]) -> Dict[str, Any]:
    text = read_text(path)
    info: Dict[str, Any] = {
        "text": text,
        "counts": ifc_regex_counts(text),
        "schema": "",
        "root_ids": [],
        "roots_by_id": {},
        "semantics_by_id": {},
        "names": {},
        "space_areas": {},
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
    try:
        roots = list(model.by_type("IfcRoot"))
    except Exception:
        roots = []
    root_ids = [str(entity.GlobalId) for entity in roots if getattr(entity, "GlobalId", None)]
    roots_by_id = {}
    semantics_by_id = {}
    for entity in roots:
        global_id = str(getattr(entity, "GlobalId", "") or "")
        if not global_id:
            continue
        roots_by_id[global_id] = {
            "class": str(entity.is_a()),
            "name": str(getattr(entity, "Name", "") or ""),
            "description": str(getattr(entity, "Description", "") or ""),
            "long_name": str(getattr(entity, "LongName", "") or ""),
            "object_type": str(getattr(entity, "ObjectType", "") or ""),
        }
        semantics_by_id[global_id] = canonical_ifc_value(entity, is_top=True)
    info["root_ids"] = root_ids
    info["roots_by_id"] = roots_by_id
    info["semantics_by_id"] = semantics_by_id
    info["names"] = names
    info["space_areas"] = ifc_space_floor_areas(model)
    return info


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
    for cls, expected in CASE_SPEC["baseline_counts"].items():
        base = init_counts.get(cls, 0)
        actual = stage_counts.get(cls, 0)
        if base != expected:
            errors.append(f"init.ifc:unexpected_baseline_count:{cls}:{base}!={expected}")
        if actual != base:
            errors.append(f"stage1.ifc:baseline_count_changed:{cls}:{actual}!={base}")
    if not init_info.get("parsed_with_ifcopenshell") or not stage1_info.get("parsed_with_ifcopenshell"):
        errors.append("ifc:ifcopenshell_required_for_identity_validation")
    init_roots = set((init_info.get("roots_by_id") or {}).keys())
    stage_roots = set((stage1_info.get("roots_by_id") or {}).keys())
    if len(init_roots) != 52:
        errors.append(f"init.ifc:unexpected_ifc_root_count:{len(init_roots)}!=52")
    if init_roots != stage_roots:
        errors.append(f"stage1.ifc:ifc_root_global_id_set_changed:lost={len(init_roots-stage_roots)}:added={len(stage_roots-init_roots)}")
    init_records = init_info.get("roots_by_id") or {}
    stage_records = stage1_info.get("roots_by_id") or {}
    changed_names = []
    for global_id in sorted(init_roots & stage_roots):
        before = init_records[global_id]
        after = stage_records[global_id]
        if before["class"] != after["class"]:
            errors.append(f"stage1.ifc:root_class_changed:{global_id}")
        if before["name"] != after["name"]:
            changed_names.append((global_id, before["class"], before["name"], after["name"]))
        if before["class"] == "IfcSpace":
            for attribute in ("long_name", "object_type", "description"):
                if before[attribute] != after[attribute]:
                    errors.append(f"stage1.ifc:space_{attribute}_changed:{global_id}")
    expected_changes = sorted((gid, "IfcSpace", before, after) for gid, (before, after) in TARGET_RENAMES.items())
    if changed_names != expected_changes:
        errors.append(f"stage1.ifc:not_exact_requested_guid_renames:{changed_names}")
    semantic_changes = [gid for gid in sorted(init_roots & stage_roots) if init_info["semantics_by_id"].get(gid) != stage1_info["semantics_by_id"].get(gid)]
    if semantic_changes:
        errors.append(f"stage1.ifc:unrequested_root_semantic_changes:{semantic_changes}")
    projects = [record for record in stage_records.values() if record["class"] == "IfcProject"]
    if len(projects) != 1 or "EW2A03" not in projects[0]["description"]:
        errors.append("stage1.ifc:project_revision_code_missing")
    stage_names = {norm(name) for name in stage1_info.get("names", {}).get("IfcSpace", [])}
    for name in CASE_SPEC["required_spaces"] + CASE_SPEC["preserved_space_names"]:
        if norm(name) not in stage_names:
            errors.append(f"stage1.ifc:missing_expected_space_name:{name}")
    for name, expected_area in CASE_SPEC["target_areas_m2"].items():
        actual_area = stage1_info.get("space_areas", {}).get(norm(name))
        if actual_area is None or abs(actual_area - expected_area) > max(0.05, expected_area * 0.005):
            errors.append(f"stage1.ifc:space_area_mismatch:{name}:{actual_area}!={expected_area}")
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
    if len(records) != len(required_spaces):
        errors.append(f"{label}:space_record_count_mismatch:{len(records)}!={len(required_spaces)}")
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
        expected_area = stage1_info.get("space_areas", {}).get(norm(name))
        if expected_area is not None:
            try:
                if abs(float(area) - expected_area) > max(0.05, expected_area * 0.005):
                    errors.append(f"{label}:space_area_mismatch_stage1:{name}:{area}!={expected_area}")
            except Exception:
                pass
        for count_key in ("door_count", "window_count"):
            try:
                raw_count = rec.get(count_key)
                count_value = float(raw_count)
                if isinstance(raw_count, bool) or count_value < 0 or not count_value.is_integer():
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{label}:space_invalid_{count_key}:{name}")
        expected_zone = dict(zip(required_spaces, required_zones)).get(str(name))
        if expected_zone is None or norm(zone) != norm(expected_zone):
            errors.append(f"{label}:space_zone_mapping_mismatch:{name}:{zone}")
        expected_area = CASE_SPEC["target_areas_m2"].get(str(name))
        try:
            if expected_area is None or abs(float(area) - expected_area) > 0.01:
                errors.append(f"{label}:required_area_mismatch:{name}:{area}")
        except Exception:
            pass
        expected_gid = next((gid for gid, (_, after) in TARGET_RENAMES.items() if after == name), None)
        if rec.get("ifc_global_id") != expected_gid:
            errors.append(f"{label}:space_global_id_mismatch:{name}")
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
        if reported_total != actual_total:
            errors.append(f"{label}:{count_key}_mismatch_stage1:{reported_total}!={actual_total}")
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
    executable_values = [str(value).replace("\\", "/").lower() for value in find_values(data, "native_cli_executable")]
    if not any(value.endswith("/graphisoft/archicad 27/ifccommandserverapp.exe") for value in executable_values):
        errors.append(f"{label}:missing_archicad_27_ifc_command_server_provenance")
    if "27.0.0 R1 (6000)" not in str(data.get("authoring_software", "")):
        errors.append(f"{label}:archicad_build_not_6000")
    commands = data.get("archicad_api_commands")
    if not isinstance(commands, list) or len(commands) < 7:
        errors.append(f"{label}:missing_archicad_api_command_records")
    else:
        methods = [command.get("method") for command in commands if isinstance(command, dict)]
        if methods[0] != "Model.LoadFile" or methods[-1] != "Model.SaveFile":
            errors.append(f"{label}:invalid_archicad_command_sequence")
        selectors = {
            str(command.get("select", {}).get("IfcSpace", {}).get("Name", ""))
            for command in commands if isinstance(command, dict)
        }
        for expected_selector in ("G-READING", "1-GALLERY", "1-STUDY-1", "1-STUDY-2"):
            if expected_selector not in selectors:
                errors.append(f"{label}:missing_archicad_space_modify:{expected_selector}")
        for command in commands:
            if isinstance(command, dict) and command.get("method") == "Entity.Modify" and not command.get("result_ref"):
                errors.append(f"{label}:archicad_modify_without_result_ref")
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


def parse_osm_objects(text: str) -> List[Dict[str, str]]:
    objects: List[Dict[str, str]] = []
    pattern = re.compile(r"(?ms)^\s*(OS:[A-Z0-9:]+)\s*,\s*(.*?;[^\r\n]*)", re.IGNORECASE)
    for match in pattern.finditer(text):
        fields: Dict[str, str] = {"OBJECT_TYPE": match.group(1).upper()}
        for line in match.group(2).splitlines():
            if "!-" not in line:
                continue
            raw, comment = line.split("!-", 1)
            key = norm(re.sub(r"\s*\{[^}]*\}\s*$", "", comment.strip()))
            value = raw.strip().rstrip(",;").strip()
            if key:
                fields[key] = value
        objects.append(fields)
    return objects


def osm_number(obj: Dict[str, str], key: str) -> float | None:
    try:
        return float(obj.get(norm(key), ""))
    except (TypeError, ValueError):
        return None


def positive_load_magnitude(definition: Dict[str, str], load_type: str, floor_area: float) -> float | None:
    candidates = {
        "OS:PEOPLE": ("NUMBER-OF-PEOPLE", "PEOPLE-PER-SPACE-FLOOR-AREA", "SPACE-FLOOR-AREA-PER-PERSON"),
        "OS:LIGHTS": ("LIGHTING-LEVEL", "WATTS-PER-SPACE-FLOOR-AREA", "WATTS-PER-PERSON"),
        "OS:ELECTRICEQUIPMENT": ("DESIGN-LEVEL", "WATTS-PER-SPACE-FLOOR-AREA", "WATTS-PER-PERSON"),
    }[load_type]
    for key in candidates:
        value = osm_number(definition, key)
        if value is not None and value > 0:
            if key in ("NUMBER-OF-PEOPLE", "LIGHTING-LEVEL", "DESIGN-LEVEL") and floor_area > 0:
                return value / floor_area
            if key == "SPACE-FLOOR-AREA-PER-PERSON":
                return 1.0 / value
            return value
    return None


def schedule_day_profile(day: Dict[str, str]) -> List[Tuple[int, float]] | None:
    profile: List[Tuple[int, float]] = []
    for index in range(1, 100):
        hour_key, minute_key, value_key = norm(f"Hour {index}"), norm(f"Minute {index}"), norm(f"Value Until Time {index}")
        if hour_key not in day:
            break
        try:
            minute = int(float(day[hour_key])) * 60 + int(float(day.get(minute_key, "0")))
            value = float(day[value_key])
        except (KeyError, TypeError, ValueError):
            return None
        if minute <= 0 or minute > 1440 or not math.isfinite(value):
            return None
        profile.append((minute, value))
    if not profile or profile[-1][0] != 1440 or any(profile[i][0] <= profile[i-1][0] for i in range(1, len(profile))):
        return None
    return profile


def effective_weekday_profiles(schedule_handle: str, rulesets: Dict[str, Dict[str, str]], rules: List[Dict[str, str]], days: Dict[str, Dict[str, str]]) -> Dict[str, List[Tuple[int, float]]] | None:
    ruleset = rulesets.get(schedule_handle)
    if ruleset is None:
        return None
    default = schedule_day_profile(days.get(ruleset.get("DEFAULT-DAY-SCHEDULE-NAME", ""), {}))
    if default is None:
        return None
    result = {}
    for weekday in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"):
        applicable = [rule for rule in rules if rule.get("SCHEDULE-RULESET-NAME") == schedule_handle and norm(rule.get(f"APPLY-{weekday}", "")) == "YES"]
        if applicable:
            def order(rule: Dict[str, str]) -> int:
                try: return int(float(rule.get("RULE-ORDER", "999999")))
                except ValueError: return 999999
            profile = schedule_day_profile(days.get(min(applicable, key=order).get("DAY-SCHEDULE-NAME", ""), {}))
            if profile is None: return None
            result[weekday] = profile
        else:
            result[weekday] = default
    return result


def osm_surface_vertices(surface: Dict[str, str]) -> List[Tuple[float, float, float]]:
    vertices = []
    for index in range(1, 100):
        value = surface.get(norm(f"X,Y,Z Vertex {index}"))
        if value is None:
            break
        try:
            coords = tuple(round(float(part.strip()), 7) for part in value.split(","))
        except ValueError:
            return []
        if len(coords) != 3:
            return []
        vertices.append(coords)
    return vertices


def cyclic_equal(first: List[Any], second: List[Any]) -> bool:
    return len(first) == len(second) and bool(first) and any(first == second[offset:] + second[:offset] for offset in range(len(second)))


def check_osm(path: Path, handoff_hash: str, handoff_data: Dict[str, Any], required_spaces: List[str], required_zones: List[str], required_tokens: List[str], flow_tokens: List[str], errors: List[str]) -> Dict[str, int]:
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
    if handoff_hash.upper() not in up:
        errors.append("result.osm:missing_full_handoff_hash")

    objects = parse_osm_objects(text)
    by_type: Dict[str, List[Dict[str, str]]] = {}
    for obj in objects:
        by_type.setdefault(obj["OBJECT_TYPE"], []).append(obj)
    handles = {obj.get("HANDLE", ""): obj for obj in objects if obj.get("HANDLE")}
    space_objects = by_type.get("OS:SPACE", [])
    zone_objects = by_type.get("OS:THERMALZONE", [])
    spaces_by_name = {norm(obj.get("NAME")): obj for obj in space_objects}
    zones_by_name = {norm(obj.get("NAME")): obj for obj in zone_objects}
    for space_name, zone_name in zip(required_spaces, required_zones):
        space_obj = spaces_by_name.get(norm(space_name))
        zone_obj = zones_by_name.get(norm(zone_name))
        if space_obj is None:
            errors.append(f"result.osm:missing_space_object:{space_name}")
            continue
        if zone_obj is None:
            errors.append(f"result.osm:missing_thermal_zone_object:{zone_name}")
            continue
        if space_obj.get("THERMAL-ZONE-NAME") != zone_obj.get("HANDLE"):
            errors.append(f"result.osm:space_zone_link_mismatch:{space_name}:{zone_name}")

    load_specs = (
        ("OS:PEOPLE", "OS:PEOPLE:DEFINITION", "PEOPLE-DEFINITION-NAME", "NUMBER-OF-PEOPLE-SCHEDULE-NAME"),
        ("OS:LIGHTS", "OS:LIGHTS:DEFINITION", "LIGHTS-DEFINITION-NAME", "SCHEDULE-NAME"),
        ("OS:ELECTRICEQUIPMENT", "OS:ELECTRICEQUIPMENT:DEFINITION", "ELECTRIC-EQUIPMENT-DEFINITION-NAME", "SCHEDULE-NAME"),
    )
    load_values: Dict[str, Dict[str, Tuple[float, List[str]]]] = {}
    for load_type, definition_type, definition_key, schedule_key in load_specs:
        assignments = by_type.get(load_type, [])
        definitions = {obj.get("HANDLE"): obj for obj in by_type.get(definition_type, [])}
        per_space: Dict[str, Tuple[float, List[str]]] = {}
        for space_name in required_spaces:
            space_obj = spaces_by_name.get(norm(space_name))
            if space_obj is None:
                continue
            matches = [obj for obj in assignments if obj.get("SPACE-OR-SPACETYPE-NAME") == space_obj.get("HANDLE")]
            if not matches:
                errors.append(f"result.osm:missing_{load_type.lower()}_for_space:{space_name}")
                continue
            magnitudes: List[float] = []
            schedules: List[str] = []
            floor_area = float(CASE_SPEC["target_areas_m2"].get(space_name, 0.0))
            for assignment in matches:
                definition = definitions.get(assignment.get(definition_key))
                magnitude = positive_load_magnitude(definition or {}, load_type, floor_area)
                schedule = assignment.get(schedule_key, "")
                if definition is None or magnitude is None:
                    errors.append(f"result.osm:invalid_{definition_type.lower()}_magnitude:{space_name}")
                    continue
                if not schedule or schedule not in handles:
                    errors.append(f"result.osm:missing_load_schedule_link:{load_type}:{space_name}")
                    continue
                magnitudes.append(magnitude)
                schedules.append(schedule)
            if magnitudes:
                per_space[norm(space_name)] = (sum(magnitudes), schedules)
        load_values[load_type] = per_space

    lighting = load_values.get("OS:LIGHTS", {})
    pod_1_lights = lighting.get(norm("QUIET-POD-01"))
    pod_2_lights = lighting.get(norm("QUIET-POD-02"))
    reading_lights = lighting.get(norm("READING"))
    gallery_lights = lighting.get(norm("GALLERY"))
    if pod_1_lights and pod_2_lights and reading_lights and gallery_lights:
        if pod_1_lights[0] >= min(reading_lights[0], gallery_lights[0]):
            errors.append("result.osm:quiet_pod_01_lighting_not_lower_than_reading_and_gallery")
        if pod_2_lights[0] >= min(reading_lights[0], gallery_lights[0]):
            errors.append("result.osm:quiet_pod_02_lighting_not_lower_than_reading_and_gallery")
        rulesets = {obj.get("HANDLE", ""): obj for obj in by_type.get("OS:SCHEDULE:RULESET", [])}
        rules = by_type.get("OS:SCHEDULE:RULE", [])
        days = {obj.get("HANDLE", ""): obj for obj in by_type.get("OS:SCHEDULE:DAY", [])}
        pod_profiles = []
        for pod_name, schedules in (("QUIET-POD-01", pod_1_lights[1]), ("QUIET-POD-02", pod_2_lights[1])):
            profiles = [effective_weekday_profiles(handle, rulesets, rules, days) for handle in schedules]
            profiles = [profile for profile in profiles if profile is not None]
            if not profiles:
                errors.append(f"result.osm:missing_effective_monday_friday_profile:{pod_name}")
            else:
                pod_profiles.append(profiles)
        if len(pod_profiles) == 2 and pod_profiles[0] == pod_profiles[1]:
            errors.append("result.osm:quiet_pod_schedule_profiles_not_distinct")

    outdoor_air = {obj.get("HANDLE"): obj for obj in by_type.get("OS:DESIGNSPECIFICATION:OUTDOORAIR", [])}
    for space_name in required_spaces:
        space_obj = spaces_by_name.get(norm(space_name))
        if space_obj is None:
            continue
        oa = outdoor_air.get(space_obj.get("DESIGN-SPECIFICATION-OUTDOOR-AIR-OBJECT-NAME"))
        per_person = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-PER-PERSON") or 0.0
        per_area = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-PER-FLOOR-AREA") or 0.0
        absolute = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-RATE") or 0.0
        ach = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-AIR-CHANGES-PER-HOUR") or 0.0
        if oa is None or max(per_person, per_area, absolute, ach) <= 0:
            errors.append(f"result.osm:missing_positive_outdoor_air:{space_name}")

    thermostat_handles = {obj.get("HANDLE") for obj in by_type.get("OS:THERMOSTATSETPOINT:DUALSETPOINT", [])}
    ideal_objects = {obj.get("HANDLE"): obj for obj in by_type.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM", [])}
    ideal_handles = set(ideal_objects)
    equipment_lists = by_type.get("OS:ZONEHVAC:EQUIPMENTLIST", [])
    ideal_names_by_zone: Dict[str, List[str]] = {}
    for zone_name in required_zones:
        zone_obj = zones_by_name.get(norm(zone_name))
        if zone_obj is None:
            continue
        if zone_obj.get("THERMOSTAT-NAME") not in thermostat_handles:
            errors.append(f"result.osm:missing_thermostat_link:{zone_name}")
        linked: List[str] = []
        for equipment_list in equipment_lists:
            if equipment_list.get("THERMAL-ZONE") != zone_obj.get("HANDLE"):
                continue
            for field, handle in equipment_list.items():
                match = re.fullmatch(r"ZONE-EQUIPMENT-(\d+)", field)
                if match is None or handle not in ideal_handles:
                    continue
                slot = match.group(1)
                cooling = osm_number(equipment_list, f"Zone Equipment Cooling Sequence {slot}")
                heating = osm_number(equipment_list, f"Zone Equipment Heating or No-Load Sequence {slot}")
                if cooling is None or heating is None or cooling <= 0 or heating <= 0:
                    errors.append(f"result.osm:invalid_ideal_loads_sequence:{zone_name}:slot_{slot}")
                else:
                    linked.append(handle)
        linked = list(dict.fromkeys(linked))
        if not linked:
            errors.append(f"result.osm:missing_ideal_loads_link:{zone_name}")
        else:
            ideal_names_by_zone[zone_name] = [ideal_objects[handle].get("NAME", "") for handle in linked]

    weather_files = by_type.get("OS:WEATHERFILE", [])
    if not weather_files or not weather_files[0].get("URL", "").replace("\\", "/").lower().endswith("/weather.epw"):
        errors.append("result.osm:weather_file_not_delivered_weather_epw")
    construction_handles = {obj.get("HANDLE") for obj in by_type.get("OS:CONSTRUCTION", [])}
    for surface in by_type.get("OS:SURFACE", []):
        if surface.get("CONSTRUCTION-NAME") not in construction_handles:
            errors.append(f"result.osm:surface_missing_construction:{surface.get('NAME')}")

    floor_areas: Dict[str, float] = {}
    for surface in by_type.get("OS:SURFACE", []):
        if norm(surface.get("SURFACE-TYPE")) != "FLOOR":
            continue
        points: List[Tuple[float, float]] = []
        for key, value in surface.items():
            if not key.startswith("X-Y-Z-VERTEX"):
                continue
            try:
                coords = [float(part.strip()) for part in value.split(",")]
            except ValueError:
                continue
            if len(coords) >= 2:
                points.append((coords[0], coords[1]))
        space_handle = surface.get("SPACE-NAME", "")
        floor_areas[space_handle] = floor_areas.get(space_handle, 0.0) + polygon_area_xy(points)
    handoff_records = {norm(record.get("name")): record for record in extract_space_records(handoff_data, [], "handoff.json")}
    for space_name in required_spaces:
        space_obj = spaces_by_name.get(norm(space_name))
        record = handoff_records.get(norm(space_name))
        if space_obj is None or record is None:
            continue
        expected_area = float(record.get("floor_area_m2"))
        actual_area = floor_areas.get(space_obj.get("HANDLE", ""))
        if actual_area is None or abs(actual_area - expected_area) > max(0.05, expected_area * 0.005):
            errors.append(f"result.osm:floor_area_mismatch_handoff:{space_name}:{actual_area}!={expected_area}")

    surfaces = {obj.get("HANDLE"): obj for obj in by_type.get("OS:SURFACE", []) if obj.get("HANDLE")}
    space_names_by_handle = {obj.get("HANDLE"): norm(obj.get("NAME")) for obj in space_objects}
    adjacent_pairs: Set[Tuple[str, str]] = set()
    for surface in surfaces.values():
        adjacent_handle = surface.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT", "")
        adjacent = surfaces.get(adjacent_handle)
        if adjacent is None:
            continue
        if adjacent.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT") != surface.get("HANDLE"):
            errors.append(f"result.osm:nonreciprocal_adjacent_surface:{surface.get('NAME')}")
            continue
        first_vertices = osm_surface_vertices(surface)
        second_vertices = list(reversed(osm_surface_vertices(adjacent)))
        if not cyclic_equal(first_vertices, second_vertices):
            errors.append(f"result.osm:adjacent_surface_geometry_not_reversed:{surface.get('NAME')}")
            continue
        names = tuple(sorted((
            space_names_by_handle.get(surface.get("SPACE-NAME", ""), ""),
            space_names_by_handle.get(adjacent.get("SPACE-NAME", ""), ""),
        )))
        adjacent_pairs.add(names)
    for pod in ("QUIET-POD-01", "QUIET-POD-02"):
        expected_pair = tuple(sorted((norm("GALLERY"), norm(pod))))
        if expected_pair not in adjacent_pairs:
            errors.append(f"result.osm:quiet_pod_not_adjacent_to_gallery:{pod}")

    output_variable_names = {norm(obj.get("VARIABLE-NAME")) for obj in by_type.get("OS:OUTPUT:VARIABLE", [])}
    for required_output in (
        "Zone Lights Electricity Energy",
        "Zone Electric Equipment Electricity Energy",
        "Zone Ideal Loads Zone Total Heating Energy",
        "Zone Ideal Loads Zone Total Cooling Energy",
        "Zone Ideal Loads Zone Total Heating Rate",
        "Zone Ideal Loads Zone Total Cooling Rate",
    ):
        if norm(required_output) not in output_variable_names:
            errors.append(f"result.osm:missing_simulation_output:{required_output}")

    counts = {
        "space_count": len(space_objects),
        "zone_count": len(zone_objects),
        "surface_count": len(by_type.get("OS:SURFACE", [])),
        "subsurface_count": len(by_type.get("OS:SUBSURFACE", [])),
        "people_count": len(by_type.get("OS:PEOPLE", [])),
        "lights_count": len(by_type.get("OS:LIGHTS", [])),
        "equipment_count": len(by_type.get("OS:ELECTRICEQUIPMENT", [])),
        "outdoor_air_count": len(by_type.get("OS:DESIGNSPECIFICATION:OUTDOORAIR", [])),
        "thermostat_count": len(by_type.get("OS:THERMOSTATSETPOINT:DUALSETPOINT", [])),
        "ideal_loads_count": len(by_type.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM", [])),
        "ideal_names_by_zone": ideal_names_by_zone,
    }
    for key in ("space_count", "zone_count"):
        if counts[key] != len(required_spaces):
            errors.append(f"result.osm:{key}_mismatch:{counts[key]}!={len(required_spaces)}")
    for key in ("people_count", "lights_count", "equipment_count", "outdoor_air_count", "thermostat_count", "ideal_loads_count"):
        if counts[key] < len(required_spaces):
            errors.append(f"result.osm:{key}_too_low:{counts[key]}<{len(required_spaces)}")
    if counts["surface_count"] < len(required_spaces) * 4:
        errors.append(f"result.osm:surface_count_too_low:{counts['surface_count']}<{len(required_spaces) * 4}")
    if counts["subsurface_count"] != 0:
        errors.append(f"result.osm:unexpected_subsurfaces:{counts['subsurface_count']}")
    return counts


def check_flow_report(
    path: Path,
    handoff_path: Path,
    osm_path: Path,
    workflow_path: Path,
    weather_path: Path,
    sql_path: Path,
    err_path: Path,
    end_path: Path,
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
    if str(data.get("source_stage1_sha256", "")).lower() != str(handoff_data.get("source_sha256", "")).lower():
        errors.append("flow_report:source_stage1_sha256_mismatch")
    for key, dependency in (
        ("workflow_sha256", workflow_path),
        ("weather_sha256", weather_path),
        ("energyplus_sql_sha256", sql_path),
        ("energyplus_err_sha256", err_path),
        ("energyplus_end_sha256", end_path),
    ):
        expected = sha256_file(dependency)
        if str(data.get(key, "")).lower() != expected.lower():
            errors.append(f"flow_report:{key}_mismatch")
    transactions = data.get("openstudio_cli_transactions")
    if not isinstance(transactions, list):
        errors.append("flow_report:missing_openstudio_cli_transactions")
        transactions = []
    matching_deliveries = []
    for transaction in transactions:
        if not isinstance(transaction, dict) or transaction.get("stage") != "openstudio_weather_period_simulation_final_delivery":
            continue
        executable = str(transaction.get("executable", "")).replace("\\", "/").lower()
        if (
            executable == "c:/openstudio-3.10.0/bin/openstudio.exe"
            and transaction.get("arguments") == ["run", "-w", r"C:\Users\user\Desktop\workflow.osw"]
            and transaction.get("working_directory") == r"C:\Users\user\Desktop"
            and transaction.get("exit_code") == 0
            and transaction.get("related_processes_after_wait") == 0
            and str(transaction.get("sql_sha256", "")).lower() == sha256_file(sql_path)
            and str(transaction.get("err_sha256", "")).lower() == sha256_file(err_path)
            and str(transaction.get("end_sha256", "")).lower() == sha256_file(end_path)
        ):
            matching_deliveries.append(transaction)
    if len(matching_deliveries) != 1:
        errors.append(f"flow_report:final_openstudio_delivery_transaction_count:{len(matching_deliveries)}")
    else:
        delivery = matching_deliveries[0]
        if data.get("final_delivery_transaction") != delivery:
            errors.append("flow_report:final_delivery_transaction_copy_mismatch")
        samples = delivery.get("stable_file_samples")
        if not isinstance(samples, list) or len(samples) < 4:
            errors.append("flow_report:final_delivery_insufficient_stable_samples")
        else:
            signatures = {
                (sample.get("sql_size"), sample.get("sql_mtime_utc"), sample.get("err_size"), sample.get("err_mtime_utc"), sample.get("end_size"), sample.get("end_mtime_utc"))
                for sample in samples if isinstance(sample, dict)
            }
            expected_sizes = (sql_path.stat().st_size, err_path.stat().st_size, end_path.stat().st_size)
            if len(signatures) != 1 or next(iter(signatures), (None,))[0::2] != expected_sizes:
                errors.append("flow_report:final_delivery_files_not_stably_bound")
        try:
            started = parse_iso_timestamp(delivery["started_at_utc"])
            process_exit = parse_iso_timestamp(delivery["openstudio_process_exited_at_utc"])
            children_exit = parse_iso_timestamp(delivery["related_children_exited_at_utc"])
            completed = parse_iso_timestamp(delivery["completed_at_utc"])
            if not (started <= process_exit <= children_exit <= completed):
                raise ValueError
        except Exception:
            errors.append("flow_report:final_delivery_timestamps_invalid")
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
        if not isinstance(data.get(key), (int, float)) or isinstance(data.get(key), bool):
            errors.append(f"flow_report:missing_numeric:{key}")
    for key in ("weather_file", "schedule_set", "construction_set"):
        vals = [str(v).strip() for v in find_values(data, key) if str(v).strip()]
        if not vals:
            errors.append(f"flow_report:missing_field:{key}")
    weather_vals = [str(v) for v in find_values(data, "weather_file")]
    if weather_vals and not any(v.lower().endswith(".epw") or "design" in v.lower() for v in weather_vals):
        errors.append("flow_report:weather_file_not_epw_or_design_day")
    for key, expected in (
        ("weather_file", "weather.epw"),
        ("workflow", "workflow.osw"),
        ("energyplus_sql", "run/eplusout.sql"),
        ("energyplus_err", "run/eplusout.err"),
    ):
        if str(data.get(key, "")).replace("\\", "/").lower() != expected.lower():
            errors.append(f"flow_report:{key}_path_mismatch")

    area = float(data["building_area_m2"]) if isinstance(data.get("building_area_m2"), (int, float)) else None
    handoff_area = get_handoff_area(handoff_data)
    if area is not None and handoff_area is not None and abs(area - handoff_area) > max(0.5, handoff_area * 0.03):
        errors.append(f"flow_report:area_mismatch:{area:.3f}!={handoff_area:.3f}")
    room_count = data.get("room_count") if isinstance(data.get("room_count"), (int, float)) else None
    zone_count = data.get("thermal_zone_count") if isinstance(data.get("thermal_zone_count"), (int, float)) else None
    if room_count is not None and int(round(room_count)) != len(required_spaces):
        errors.append("flow_report:room_count_mismatch")
    if zone_count is not None and int(round(zone_count)) != len(required_zones):
        errors.append("flow_report:thermal_zone_count_mismatch")
    if isinstance(data.get("surface_count"), (int, float)) and int(data["surface_count"]) != osm_counts["surface_count"]:
        errors.append("flow_report:surface_count_mismatch_osm")
    if isinstance(data.get("subsurface_count"), (int, float)) and int(data["subsurface_count"]) != osm_counts["subsurface_count"]:
        errors.append("flow_report:subsurface_count_mismatch_osm")
    handoff_records = extract_space_records(handoff_data, [], "handoff.json")
    for key, cls in (("door_count", "IfcDoor"), ("window_count", "IfcWindow")):
        val = data.get(key) if isinstance(data.get(key), (int, float)) else None
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
    wwr = data.get("window_wall_ratio") if isinstance(data.get("window_wall_ratio"), (int, float)) else None
    if wwr is not None and not (0.0 <= wwr <= 0.95):
        errors.append("flow_report:window_wall_ratio_out_of_range")
    if data.get("energyplus_status") != "Completed Successfully":
        errors.append("flow_report:energyplus_not_completed_successfully")
    if data.get("energyplus_severe_errors") != 0 or data.get("energyplus_fatal_errors") != 0:
        errors.append("flow_report:energyplus_errors_not_zero")
    object_counts = data.get("model_object_counts")
    if not isinstance(object_counts, dict):
        errors.append("flow_report:missing_model_object_counts")
    else:
        expected_counts = {
            "Space": "space_count",
            "ThermalZone": "zone_count",
            "People": "people_count",
            "Lights": "lights_count",
            "ElectricEquipment": "equipment_count",
            "DesignSpecificationOutdoorAir": "outdoor_air_count",
            "ThermostatSetpointDualSetpoint": "thermostat_count",
            "ZoneHVACIdealLoadsAirSystem": "ideal_loads_count",
        }
        for report_key, osm_key in expected_counts.items():
            if object_counts.get(report_key) != osm_counts.get(osm_key):
                errors.append(f"flow_report:model_object_count_mismatch:{report_key}")
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
    if len(rows) != len(required_spaces):
        errors.append(f"model_summary.csv:row_count_mismatch:{len(rows)}!={len(required_spaces)}")
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
    handoff_records = {norm(record.get("name")): record for record in extract_space_records(handoff_data, [], "handoff.json")}
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
            break
        name = next((str(v) for k, v in row.items() if norm(k) == norm("space_name")), "")
        zone = next((str(v) for k, v in row.items() if norm(k) == norm("thermal_zone")), "")
        expected_zone = str(handoff_records.get(norm(name), {}).get("thermal_zone", ""))
        if not expected_zone or norm(zone) != norm(expected_zone):
            errors.append(f"model_summary.csv:space_zone_pair_mismatch:{name}:{zone}!={expected_zone}")
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
            expected_area = float(handoff_records.get(norm(name), {}).get("floor_area_m2", -1))
            if expected_area <= 0 or abs(area - expected_area) > max(0.05, expected_area * 0.005):
                errors.append(f"model_summary.csv:area_mismatch_handoff_row:{name}:{area}!={expected_area}")
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
    if len(seen_spaces) != len(rows) or len(seen_zones) != len(rows):
        errors.append("model_summary.csv:space_zone_not_bijective")
    handoff_area = get_handoff_area(handoff_data)
    if handoff_area is not None and abs(total_area - handoff_area) > max(0.5, handoff_area * 0.03):
        errors.append(f"model_summary.csv:area_mismatch_handoff:{total_area:.3f}!={handoff_area:.3f}")
    flow_area = flow_data.get("building_area_m2") if isinstance(flow_data.get("building_area_m2"), (int, float)) else None
    if flow_area is not None and abs(total_area - flow_area) > max(0.5, flow_area * 0.03):
        errors.append(f"model_summary.csv:area_mismatch_flow:{total_area:.3f}!={flow_area:.3f}")
    if total_area > 0:
        eui = total_energy / total_area
        if not (5.0 <= eui <= 800.0):
            errors.append(f"model_summary.csv:eui_out_of_range:{eui:.3f}")


def check_workflow_and_weather(workflow_path: Path, weather_path: Path, errors: List[str]) -> None:
    workflow = load_json(workflow_path)
    for key, expected_name in (("seed_file", "result.osm"), ("weather_file", "weather.epw")):
        value = str(workflow.get(key, "")).replace("\\", "/")
        if Path(value).name.lower() != expected_name:
            errors.append(f"workflow.osw:{key}_mismatch")
    run_directory = str(workflow.get("run_directory", "")).replace("\\", "/").rstrip("/")
    if run_directory.lower() != "run" and not run_directory.lower().endswith("/engiworld-task-03/run"):
        errors.append("workflow.osw:run_directory_mismatch")
    if weather_path.stat().st_size < 500_000:
        errors.append("weather.epw:too_small_for_real_epw")
    weather_lines = weather_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if not weather_lines or not weather_lines[0].upper().startswith("LOCATION,"):
        errors.append("weather.epw:missing_location_header")
    if "TMY3" not in weather_lines[0].upper():
        errors.append("weather.epw:not_tmy3")
    hourly = [line for line in weather_lines[8:] if line.strip()]
    if len(hourly) != 8760:
        errors.append(f"weather.epw:hourly_row_count:{len(hourly)}!=8760")
    timestamps = set()
    for index, line in enumerate(hourly, start=1):
        fields = line.split(",")
        try:
            month, day, hour = int(fields[1]), int(fields[2]), int(fields[3])
            if len(fields) < 35 or not (1 <= month <= 12 and 1 <= day <= 31 and 1 <= hour <= 24):
                raise ValueError
            timestamps.add((month, day, hour))
        except (IndexError, ValueError):
            errors.append(f"weather.epw:invalid_hourly_row:{index}")
            break
    if len(timestamps) != 8760:
        errors.append(f"weather.epw:nonunique_or_incomplete_timestamps:{len(timestamps)}")


def check_native_stage_log(path: Path, init_path: Path, stage1_path: Path, handoff_path: Path, handoff_data: Dict[str, Any], errors: List[str]) -> None:
    data = load_json(path)
    if data.get("schema") != "engiworld-archicad-ifc-command-server-native-log-v1":
        errors.append("native_stage_log.json:schema_mismatch")
    if data.get("case_id") != CASE_SPEC["case_id"] or data.get("software_stage") != "archicad":
        errors.append("native_stage_log.json:case_or_stage_mismatch")
    process = data.get("command_server_process")
    if not isinstance(process, dict):
        errors.append("native_stage_log.json:missing_command_server_process")
    else:
        executable = str(process.get("executable_path", "")).replace("\\", "/").lower()
        if not executable.endswith("/graphisoft/archicad 27/ifccommandserverapp.exe"):
            errors.append("native_stage_log.json:executable_path_mismatch")
        if process.get("product_version") != "27.0.0 R1 (6000)" or process.get("file_version") != "27.0.0 R1 (6000)":
            errors.append("native_stage_log.json:archicad_version_mismatch")
        if process.get("executable_sha256") != "594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775":
            errors.append("native_stage_log.json:command_server_executable_hash_mismatch")
        command_line = str(process.get("command_line", "")).replace("\\", "/").upper()
        if "IFCCOMMANDSERVERAPP.EXE" not in command_line or "--SA NEW_IFC4" not in command_line or "C:/EW03" not in command_line:
            errors.append("native_stage_log.json:command_line_not_task03_ifc4_session")
        if not isinstance(process.get("pid"), int) or process.get("pid", 0) <= 0:
            errors.append("native_stage_log.json:invalid_process_id")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("native_stage_log.json:missing_artifact_records")
    else:
        for name, artifact_path in (("init.ifc", init_path), ("stage1.ifc", stage1_path), ("handoff.json", handoff_path)):
            record = artifacts.get(name)
            if not isinstance(record, dict) or record.get("sha256") != sha256_file(artifact_path) or record.get("size") != artifact_path.stat().st_size:
                errors.append(f"native_stage_log.json:artifact_record_mismatch:{name}")
        stage_record = artifacts.get("stage1.ifc", {})
        if stage_record.get("header_contains_preprocessor") is not True or stage_record.get("header_preprocessor") != "The EXPRESS Data Manager Version 5.02.0100.09 : 26 Sep 2013":
            errors.append("native_stage_log.json:missing_edm_export_record")

    transaction_section = data.get("command_transactions")
    transactions = transaction_section.get("value") if isinstance(transaction_section, dict) else transaction_section
    expected_methods = ["Model.LoadFile"] + ["Entity.Modify"] * 5 + ["Model.SaveFile"]
    if not isinstance(transactions, list) or len(transactions) != len(expected_methods):
        errors.append("native_stage_log.json:transaction_count_mismatch")
        transactions = []
    elif [item.get("request", {}).get("method") for item in transactions] != expected_methods:
        errors.append("native_stage_log.json:transaction_sequence_mismatch")
    completed_times: List[datetime] = []
    modify_results: List[int] = []
    for index, transaction in enumerate(transactions):
        request = transaction.get("request", {})
        response = transaction.get("response", {})
        request_json = transaction.get("request_json")
        response_text = transaction.get("response_text")
        try:
            parsed_request = json.loads(request_json) if isinstance(request_json, str) else None
        except json.JSONDecodeError:
            parsed_request = None
        try:
            parsed_response = json.loads(response_text) if isinstance(response_text, str) else None
        except json.JSONDecodeError:
            parsed_response = None
        if parsed_request != request or not isinstance(parsed_request, dict) or not parsed_request:
            errors.append(f"native_stage_log.json:request_json_structured_mismatch:{index}")
        if parsed_response != response or not isinstance(parsed_response, dict) or not parsed_response:
            errors.append(f"native_stage_log.json:response_text_structured_mismatch:{index}")
        if transaction.get("status") != 200 or response.get("jsonrpc") != "2.0":
            errors.append(f"native_stage_log.json:transaction_transport_or_protocol_failure:{index}")
        if response.get("id") != request.get("id") or "error" in response or "result" not in response:
            errors.append(f"native_stage_log.json:jsonrpc_error_response:{index}")
        try:
            started = parse_iso_timestamp(transaction["started_at_utc"])
            completed = parse_iso_timestamp(transaction["completed_at_utc"])
            if completed < started or (completed_times and started < completed_times[-1]):
                raise ValueError
            completed_times.append(completed)
        except Exception:
            errors.append(f"native_stage_log.json:invalid_transaction_timestamps:{index}")
        if request.get("method") == "Entity.Modify":
            try:
                result = int(response["result"])
                if result <= 0:
                    raise ValueError
                modify_results.append(result)
            except Exception:
                errors.append(f"native_stage_log.json:invalid_modify_result:{index}")
    if len(modify_results) != 5 or len(set(modify_results)) != 5:
        errors.append("native_stage_log.json:modify_results_not_distinct_positive_edm_ids")
    if transactions:
        if transactions[0].get("request", {}).get("params") != {"location": r"C:\Users\user\Desktop\init.ifc"} or transactions[0].get("response", {}).get("result") != "init.ifc":
            errors.append("native_stage_log.json:load_semantics_mismatch")
        for offset, (global_id, (before, after)) in enumerate(TARGET_RENAMES.items(), start=1):
            expected = {"select": {"IfcSpace": {"GlobalId": global_id, "Name": before}}, "EntityData": {"IfcSpace": {"Name": after}}}
            if transactions[offset].get("request", {}).get("params") != expected:
                errors.append(f"native_stage_log.json:guid_rename_request_mismatch:{global_id}")
        project_params = transactions[5].get("request", {}).get("params", {})
        if "EW2A03" not in str(project_params.get("EntityData", {}).get("IfcProject", {}).get("Description", "")):
            errors.append("native_stage_log.json:project_revision_request_mismatch")
        if transactions[6].get("request", {}).get("params") != {"location": r"C:\Users\user\Desktop\stage1.ifc"} or transactions[6].get("response", {}).get("result") is not None:
            errors.append("native_stage_log.json:save_semantics_mismatch")
    database = data.get("task_database")
    if not isinstance(database, dict) or str(database.get("path", "")).replace("\\", "/").upper() != "C:/EW03":
        errors.append("native_stage_log.json:task_database_mismatch")
    elif not isinstance(database.get("descriptor_files"), list) or len(database["descriptor_files"]) < 3:
        errors.append("native_stage_log.json:missing_edm_database_descriptors")

    try:
        generated = parse_iso_timestamp(data["generated_at_utc"])
        process_created = parse_iso_timestamp(process["creation_time"])
        init_time = parse_iso_timestamp(artifacts["init.ifc"]["mtime_utc"])
        stage_time = parse_iso_timestamp(artifacts["stage1.ifc"]["mtime_utc"])
        handoff_time = parse_iso_timestamp(artifacts["handoff.json"]["mtime_utc"])
        if not (init_time <= process_created <= stage_time <= handoff_time <= generated):
            errors.append("native_stage_log.json:artifact_timestamps_out_of_sequence")
    except Exception:
        errors.append("native_stage_log.json:invalid_timestamps")


def check_energyplus_sql_and_csv(sql_path: Path, err_path: Path, end_path: Path, csv_path: Path, flow_data: Dict[str, Any], required_zones: List[str], ideal_names_by_zone: Dict[str, List[str]], errors: List[str]) -> None:
    if sql_path.stat().st_size < 1_000_000:
        errors.append("run/eplusout.sql:too_small")
        return
    err_text = read_text(err_path)
    if "EnergyPlus Completed Successfully" not in err_text:
        errors.append("run/eplusout.err:simulation_not_completed_successfully")
    if re.search(r"\*\*\s+(Severe|Fatal)\s+\*\*", err_text, flags=re.IGNORECASE):
        errors.append("run/eplusout.err:contains_severe_or_fatal")
    end_text = read_text(end_path)
    if "EnergyPlus Completed Successfully" not in end_text:
        errors.append("run/eplusout.end:simulation_not_completed_successfully")

    try:
        connection = sqlite3.connect(f"file:{sql_path}?mode=ro&immutable=1", uri=True)
    except Exception as exc:
        errors.append(f"run/eplusout.sql:open_failed:{type(exc).__name__}")
        return
    try:
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in ("ReportDataDictionary", "ReportData", "Errors", "EnvironmentPeriods", "Simulations"):
            if table not in tables:
                errors.append(f"run/eplusout.sql:missing_standard_table:{table}")
        if errors and any(error.startswith("run/eplusout.sql:missing_standard_table") for error in errors):
            return
        severe_or_fatal = int(connection.execute("SELECT COUNT(*) FROM Errors WHERE ErrorType >= 1").fetchone()[0])
        if severe_or_fatal:
            errors.append(f"run/eplusout.sql:severe_or_fatal_errors:{severe_or_fatal}")
        simulation_rows = connection.execute(
            "SELECT SimulationIndex, EnergyPlusVersion, TimeStamp, NumTimestepsPerHour, CAST(Completed AS TEXT), CAST(CompletedSuccessfully AS TEXT) FROM Simulations ORDER BY SimulationIndex"
        ).fetchall()
        simulation_row = simulation_rows[-1] if simulation_rows else None
        if not simulation_row or "25.1.0" not in str(simulation_row[1]):
            errors.append("run/eplusout.sql:energyplus_version_not_25_1_0")
        if simulation_row:
            expected_record = {
                "record_count": len(simulation_rows),
                "simulation_index": str(simulation_row[0]),
                "energyplus_version": str(simulation_row[1]),
                "timestamp": str(simulation_row[2]),
                "num_timesteps_per_hour": str(simulation_row[3]),
                "completed_raw": str(simulation_row[4]),
                "completed_successfully_raw": str(simulation_row[5]),
            }
            if flow_data.get("energyplus_sql_simulations_record") != expected_record:
                errors.append("flow_report:energyplus_sql_simulations_record_mismatch")
            completed_pair = (str(simulation_row[4]).upper(), str(simulation_row[5]).upper())
            evidence = flow_data.get("energyplus_completion_evidence")
            if not isinstance(evidence, dict):
                errors.append("flow_report:missing_energyplus_completion_evidence")
            else:
                if evidence.get("err_completed_successfully") is not True or evidence.get("err_severe_count") != 0 or evidence.get("err_fatal_count") != 0:
                    errors.append("flow_report:completion_evidence_mismatch_err")
                if completed_pair == ("FALSE", "FALSE") and not evidence.get("simulations_flag_anomaly"):
                    errors.append("flow_report:missing_false_simulations_flag_anomaly")
                elif completed_pair not in (("FALSE", "FALSE"), ("TRUE", "TRUE"), ("1", "1")):
                    errors.append(f"run/eplusout.sql:unexpected_completion_flag_pair:{completed_pair}")
                if completed_pair == ("FALSE", "FALSE"):
                    simulation = flow_data.get("simulation", {})
                    anomaly = simulation.get("energyplus_25_1_sql_finalization_order", {}) if isinstance(simulation, dict) else {}
                    samples = simulation.get("stable_file_samples", []) if isinstance(simulation, dict) else []
                    stable = isinstance(samples, list) and len(samples) >= 4 and len({(s.get("sql_size"), s.get("sql_mtime_ns"), s.get("err_size"), s.get("err_mtime_ns"), s.get("end_size"), s.get("end_mtime_ns")) for s in samples if isinstance(s, dict)}) == 1
                    if (
                        "25.1.0-1c11a3d85f" not in str(simulation_row[1])
                        or flow_data.get("energyplus_executable_sha256") != "3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5"
                        or not isinstance(simulation, dict) or simulation.get("native_exit_code") != 0
                        or simulation.get("sqlite_integrity_check") != "ok"
                        or not stable
                        or anomaly.get("source") != "https://github.com/NatLabRockies/EnergyPlus/blob/v25.1.0/src/EnergyPlus/api/EnergyPlusPgm.cc#L358-L398"
                    ):
                        errors.append("run/eplusout.sql:false_false_without_complete_native_25_1_evidence")
        report_data_count = int(connection.execute("SELECT COUNT(*) FROM ReportData").fetchone()[0])
        if flow_data.get("energyplus_sql_report_data_count") != report_data_count:
            errors.append("flow_report:energyplus_sql_report_data_count_mismatch")

        expected_timestamps = {(month, day, hour, 0) for month, days in enumerate((0,31,28,31,30,31,30,31,31,30,31,30,31)) if month for day in range(1, days+1) for hour in range(1,25)}
        weather_rows = connection.execute("SELECT EnvironmentPeriodIndex FROM EnvironmentPeriods WHERE EnvironmentType=3").fetchall()
        if len(weather_rows) != 1:
            errors.append(f"run/eplusout.sql:weather_environment_count:{len(weather_rows)}")
        weather_index = int(weather_rows[0][0]) if len(weather_rows) == 1 else -1

        def series_stat(variable: str, key: str, aggregate: str) -> Tuple[float, int]:
            rows = connection.execute(
                "SELECT rd.TimeIndex, rd.Value, t.Month, t.Day, t.Hour, t.Minute, t.EnvironmentPeriodIndex, t.WarmupFlag, t.Interval, t.IntervalType, d.ReportDataDictionaryIndex "
                "FROM ReportData rd JOIN ReportDataDictionary d ON d.ReportDataDictionaryIndex=rd.ReportDataDictionaryIndex JOIN Time t ON t.TimeIndex=rd.TimeIndex "
                "WHERE UPPER(d.Name)=UPPER(?) AND UPPER(d.KeyValue)=UPPER(?) AND UPPER(d.ReportingFrequency)='HOURLY'",
                (variable, key),
            ).fetchall()
            label = f"{variable}:{key}"
            if len(rows) != 8760 or len({int(row[0]) for row in rows}) != 8760:
                errors.append(f"run/eplusout.sql:hourly_count_or_distinct_timeindex:{label}:{len(rows)}")
            timestamps = {(int(r[2]),int(r[3]),int(r[4]),int(r[5])) for r in rows}
            if timestamps != expected_timestamps:
                errors.append(f"run/eplusout.sql:annual_timestamp_coverage:{label}:{len(timestamps)}")
            if {int(r[6]) for r in rows} != {weather_index} or {int(r[7]) for r in rows} != {0} or {int(r[8]) for r in rows} != {60} or {int(r[9]) for r in rows} != {1}:
                errors.append(f"run/eplusout.sql:hourly_metadata_invalid:{label}")
            if len({int(r[10]) for r in rows}) != 1:
                errors.append(f"run/eplusout.sql:dictionary_count_invalid:{label}")
            values = [float(r[1]) for r in rows]
            result = sum(values) if aggregate == "SUM" else (max(values) if values else float("nan"))
            return result, len(rows)

        sql_metrics: Dict[str, Tuple[float, float]] = {}
        for zone in required_zones:
            energy_j = 0.0
            counts: List[int] = []
            for variable, key in (("Zone Lights Electricity Energy", zone), ("Zone Electric Equipment Electricity Energy", zone)):
                value, count = series_stat(variable, key, "SUM")
                energy_j += value
                counts.append(count)
            ideal_names = ideal_names_by_zone.get(zone, [])
            if not ideal_names:
                errors.append(f"run/eplusout.sql:missing_osm_ideal_name:{zone}")
            for ideal_name in ideal_names:
                for variable in ("Zone Ideal Loads Zone Total Heating Energy", "Zone Ideal Loads Zone Total Cooling Energy"):
                    value, count = series_stat(variable, ideal_name, "SUM")
                    energy_j += value
                    counts.append(count)
            peaks: List[float] = []
            for ideal_name in ideal_names:
                for variable in ("Zone Ideal Loads Zone Total Heating Rate", "Zone Ideal Loads Zone Total Cooling Rate"):
                    value, count = series_stat(variable, ideal_name, "MAX")
                    peaks.append(value)
                    counts.append(count)
            if any(count < 8760 for count in counts) or not math.isfinite(energy_j) or not all(math.isfinite(value) for value in peaks):
                errors.append(f"run/eplusout.sql:missing_full_hourly_series:{zone}:{counts}")
                continue
            sql_metrics[norm(zone)] = (energy_j / 3_600_000.0, max(peaks))

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            zone = str(row.get("thermal_zone", ""))
            expected = sql_metrics.get(norm(zone))
            if expected is None:
                errors.append(f"model_summary.csv:zone_missing_in_sql:{zone}")
                continue
            try:
                reported_energy = float(row["energy_use_kwh"])
                reported_peak = float(row["peak_load_w"])
            except Exception:
                continue
            if abs(reported_energy - expected[0]) > max(0.01, expected[0] * 0.000002):
                errors.append(f"model_summary.csv:energy_mismatch_sql:{zone}:{reported_energy}!={expected[0]:.6f}")
            if abs(reported_peak - expected[1]) > max(0.01, expected[1] * 0.000002):
                errors.append(f"model_summary.csv:peak_mismatch_sql:{zone}:{reported_peak}!={expected[1]:.6f}")
    except sqlite3.DatabaseError as exc:
        errors.append(f"run/eplusout.sql:query_failed:{type(exc).__name__}")
    finally:
        connection.close()


def evaluate(root: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    paths = require_files(root, CASE_SPEC["required_files"], errors)
    if errors:
        return False, errors

    init_path = paths["init.ifc"]
    if sha256_file(init_path) != CASE_SPEC["init_sha256"]:
        errors.append("init.ifc:seed_sha256_mismatch")
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
    is_archicad_27_output = any(signature in stage1_header for signature in (
        "THE EXPRESS DATA MANAGER VERSION 5.02.0100.09",
        "ARCHICAD 27",
        "ARCHICAD-27",
    ))
    if not is_archicad_27_output:
        errors.append("stage1.ifc:not_graphisoft_archicad_27_output")
    check_stage_derives_from_init(init_path, stage1, init_info, stage1_info, errors)

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
    flow_tokens: List[str] = []
    osm_counts = check_osm(paths["result.osm"], handoff_hash, handoff_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], flow_tokens, errors)
    flow_data = check_flow_report(
        paths["flow_report.json"], handoff, paths["result.osm"], paths["workflow.osw"],
        paths["weather.epw"], paths["run/eplusout.sql"], paths["run/eplusout.err"],
        paths["run/eplusout.end"],
        handoff_data, osm_counts, stage1_info, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors,
    )
    if str(flow_data.get("native_stage_log_sha256", "")).lower() != sha256_file(paths["native_stage_log.json"]):
        errors.append("flow_report:native_stage_log_sha256_mismatch")
    check_model_summary_csv(paths["model_summary.csv"], handoff_hash, sha256_file(stage1), handoff_data, flow_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors)
    check_native_stage_log(paths["native_stage_log.json"], init_path, stage1, handoff, handoff_data, errors)
    check_workflow_and_weather(paths["workflow.osw"], paths["weather.epw"], errors)
    check_energyplus_sql_and_csv(paths["run/eplusout.sql"], paths["run/eplusout.err"], paths["run/eplusout.end"], paths["model_summary.csv"], flow_data, CASE_SPEC["required_zones"], osm_counts.get("ideal_names_by_zone", {}), errors)

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
