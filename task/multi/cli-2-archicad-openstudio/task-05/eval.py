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

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-05-windows',
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
 'required_spaces': ['MAIN-STUDIO', 'STORAGE', 'FINISHING-BOOTH'],
 'required_zones': ['MAIN-STUDIO-ZN', 'STORAGE-ZN', 'FINISHING-BOOTH-ZN'],
 'stage1_tokens': ['EW2A05', 'MAIN-STUDIO', 'STORAGE', 'FINISHING-BOOTH',
                   'BOOTH-DOOR', 'HIGH-VENT-WINDOW'],
 'handoff_tokens': [],
 'osm_tokens': ['FINISHING-BOOTH-ZN'],
 'summary_tokens': ['MAIN-STUDIO', 'STORAGE', 'FINISHING-BOOTH'],
 'min_windows': 1,
 'min_doors': 1,
 'min_roofs': 0,
 'min_storeys': 1,
 'expected_stage': 'archicad',
 'init_sha256': '6ea42757b6dfc875df89ab031f470e12c9511e8f412f00ddf742d3aa87f07b46',
 'target_spaces': {'MAIN-STUDIO': {'zone': 'MAIN-STUDIO-ZN'},
                   'STORAGE': {'zone': 'STORAGE-ZN'},
                   'FINISHING-BOOTH': {'zone': 'FINISHING-BOOTH-ZN'}},
 'baseline_counts': {'IfcProject': 1, 'IfcSite': 1, 'IfcBuilding': 1, 'IfcBuildingStorey': 1,
                     'IfcSpace': 5, 'IfcWall': 0, 'IfcSlab': 1, 'IfcRoof': 2,
                     'IfcDoor': 0, 'IfcWindow': 0, 'IfcOpeningElement': 0}}

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
    for current_key, value in data.items():
        if norm(current_key) != norm(key):
            continue
        try:
            return float(value)
        except Exception:
            return None
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
    if not init_info.get("parsed_with_ifcopenshell") or not stage1_info.get("parsed_with_ifcopenshell"):
        errors.append("stage1.ifc:ifcopenshell_required_for_exact_semantics")
        return
    try:
        import ifcopenshell  # type: ignore
        from ifcopenshell import validate  # type: ignore
        init_model = ifcopenshell.open(str(init_path))
        stage_model = ifcopenshell.open(str(stage1_path))
        logger = validate.json_logger()
        validate.validate(stage_model, logger)
        if logger.statements:
            errors.append(f"stage1.ifc:schema_validation_errors:{len(logger.statements)}")

        init_roots = {str(x.GlobalId): x for x in init_model.by_type("IfcRoot") if getattr(x, "GlobalId", None)}
        stage_roots = {str(x.GlobalId): x for x in stage_model.by_type("IfcRoot") if getattr(x, "GlobalId", None)}
        if not set(init_roots).issubset(stage_roots):
            errors.append("stage1.ifc:seed_root_removed")
        target_spaces = {
            str(space.GlobalId): (str(space.Name or ""), str(space.LongName or ""))
            for space in stage_model.by_type("IfcSpace")
            if str(space.Name or "") in CASE_SPEC["required_spaces"]
        }
        if {name for name, _ in target_spaces.values()} != set(CASE_SPEC["required_spaces"]):
            errors.append("stage1.ifc:required_space_binding_mismatch")
        project_ids = {str(project.GlobalId) for project in stage_model.by_type("IfcProject")}
        allowed_nested = {gid: {"Name", "LongName"} for gid in target_spaces}
        for gid in project_ids:
            allowed_nested[gid] = {"Description"}
        def canonical(value: Any, ignored: Set[str] | None = None) -> Any:
            ignored = ignored or set()
            if isinstance(value, dict):
                nested_ignored = ignored | allowed_nested.get(str(value.get("GlobalId", "")), set())
                return tuple(sorted((key, canonical(item, nested_ignored)) for key, item in value.items() if key != "id" and key not in nested_ignored))
            if isinstance(value, (tuple, list)):
                return tuple(canonical(item, ignored) for item in value)
            return value

        def root_signature(model: Any, entity: Any, ignored: Set[str]) -> Any:
            forward = canonical(entity.get_info(recursive=True), ignored | {"id"})
            return forward
        for gid, before in init_roots.items():
            after = stage_roots.get(gid)
            if after is None or before.is_a() != after.is_a():
                continue
            before_values = tuple(getattr(before, key, None) for key in ("Name", "LongName", "ObjectType"))
            after_values = tuple(getattr(after, key, None) for key in ("Name", "LongName", "ObjectType"))
            if gid in target_spaces:
                expected_name, expected_long = target_spaces[gid]
                if norm(after_values[0]) != norm(expected_name) or norm(expected_long) not in norm(after_values[1]):
                    errors.append(f"stage1.ifc:target_semantics_mismatch:{gid}")
                if root_signature(init_model, before, {"Name", "LongName"}) != root_signature(stage_model, after, {"Name", "LongName"}):
                    errors.append(f"stage1.ifc:target_recursive_semantics_changed:{gid}")
            elif gid in project_ids:
                if before_values != after_values:
                    errors.append("stage1.ifc:project_non_description_semantics_changed")
                if root_signature(init_model, before, {"Description"}) != root_signature(stage_model, after, {"Description"}):
                    errors.append("stage1.ifc:project_recursive_semantics_changed")
            elif before.is_a("IfcRelContainedInSpatialStructure"):
                if root_signature(init_model, before, {"RelatedElements"}) != root_signature(stage_model, after, {"RelatedElements"}):
                    errors.append("stage1.ifc:containment_non_reference_semantics_changed")
            elif before_values != after_values:
                errors.append(f"stage1.ifc:non_target_semantics_changed:{gid}")
            elif root_signature(init_model, before, set()) != root_signature(stage_model, after, set()):
                errors.append(f"stage1.ifc:non_target_recursive_semantics_changed:{gid}")

        for cls, opening_name in (("IfcDoor", "BOOTH-DOOR"), ("IfcWindow", "HIGH-VENT-WINDOW")):
            matches = [item for item in stage_model.by_type(cls) if norm(item.Name) == norm(opening_name)]
            if len(matches) != 1:
                errors.append(f"stage1.ifc:opening_binding_mismatch:{opening_name}")
                continue
            opening = matches[0]
            try:
                if float(opening.OverallHeight or 0) <= 0 or float(opening.OverallWidth or 0) <= 0:
                    raise ValueError
            except Exception:
                errors.append(f"stage1.ifc:opening_dimensions_nonpositive:{opening_name}")
            rels = list(opening.ContainedInStructure)
            if len(rels) != 1 or not rels[0].RelatingStructure.is_a("IfcBuildingStorey") or opening not in rels[0].RelatedElements:
                errors.append(f"stage1.ifc:opening_containment_invalid:{opening_name}")
    except Exception as exc:
        errors.append(f"stage1.ifc:exact_semantic_validation_failed:{type(exc).__name__}")


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
        spec = CASE_SPEC["target_spaces"].get(str(name))
        if spec and norm(zone) != norm(spec["zone"]):
            errors.append(f"{label}:space_zone_pair_mismatch:{name}")
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
    records_by_name = {str(r.get("name") or r.get("space_name")): r for r in records}
    if not set(CASE_SPEC["required_spaces"]).issubset(records_by_name):
        errors.append(f"{label}:required_space_set_mismatch")
    try:
        import ifcopenshell  # type: ignore
        from ifcopenshell.util.element import get_psets  # type: ignore
        stage_model = ifcopenshell.open(str(source_file))
        stage_space_objects = {str(space.Name or ""): space for space in stage_model.by_type("IfcSpace")}
        stage_spaces = {name: str(space.GlobalId) for name, space in stage_space_objects.items()}
        for name, spec in CASE_SPEC["target_spaces"].items():
            rec = records_by_name.get(name, {})
            if rec.get("ifc_global_id") != stage_spaces.get(name) or norm(rec.get("thermal_zone")) != norm(spec["zone"]):
                errors.append(f"{label}:space_identity_mismatch:{name}")
            quantities = get_psets(stage_space_objects[name], qtos_only=True)
            net_floor_areas = [
                float(value)
                for quantity_set in quantities.values()
                for key, value in quantity_set.items()
                if norm(key) == norm("NetFloorArea")
            ]
            if len(net_floor_areas) != 1:
                errors.append(f"{label}:stage1_net_floor_area_missing_or_ambiguous:{name}")
            else:
                reported_area = float(rec.get("floor_area_m2"))
                if abs(reported_area - net_floor_areas[0]) > 0.01:
                    errors.append(f"{label}:stage1_net_floor_area_mismatch:{name}")
        for cls, opening_name in (("IfcDoor", "BOOTH-DOOR"), ("IfcWindow", "HIGH-VENT-WINDOW")):
            matches = [item for item in stage_model.by_type(cls) if norm(item.Name) == norm(opening_name)]
            if len(matches) != 1:
                errors.append(f"{label}:opening_stage1_binding_mismatch:{opening_name}")
    except Exception as exc:
        errors.append(f"{label}:stage1_cross_reference_failed:{type(exc).__name__}")
    if int(data.get("door_count", -1)) < 1 or int(data.get("window_count", -1)) < 1:
        errors.append(f"{label}:opening_count_below_required")
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


def osm_objects(text: str) -> List[Tuple[str, List[str]]]:
    objects: List[Tuple[str, List[str]]] = []
    for raw in re.findall(r"(?ms)^OS:[A-Za-z0-9:]+\s*,.*?;", text):
        clean = re.sub(r"!-[^\r\n]*", "", raw)
        parts = [p.strip() for p in re.split(r"[,;]", clean)]
        objects.append((parts[0].upper(), parts[1:]))
    return objects


def handle(value: Any) -> str:
    return str(value or "").strip().strip("{}")


def polygon_area_3d(points: List[Tuple[float, float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    ax = ay = az = 0.0
    for left, right in zip(points, points[1:] + points[:1]):
        ax += left[1] * right[2] - left[2] * right[1]
        ay += left[2] * right[0] - left[0] * right[2]
        az += left[0] * right[1] - left[1] * right[0]
    return 0.5 * math.sqrt(ax * ax + ay * ay + az * az)


def polygon_contains_strict_3d(parent: List[Tuple[float, float, float]], child: List[Tuple[float, float, float]], tolerance: float = 1e-7) -> bool:
    if len(parent) < 3 or len(child) < 3:
        return False
    ux, uy, uz = (parent[1][i] - parent[0][i] for i in range(3))
    vx, vy, vz = (parent[2][i] - parent[0][i] for i in range(3))
    normal = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    length = math.sqrt(sum(value * value for value in normal))
    if length <= tolerance:
        return False
    normal = tuple(value / length for value in normal)
    for point in child:
        distance = sum(normal[i] * (point[i] - parent[0][i]) for i in range(3))
        if abs(distance) > tolerance:
            return False
    drop = max(range(3), key=lambda i: abs(normal[i]))
    project = lambda p: tuple(p[i] for i in range(3) if i != drop)
    polygon = [project(point) for point in parent]
    for point3d in child:
        x, y = project(point3d)
        inside = False
        for left, right in zip(polygon, polygon[1:] + polygon[:1]):
            x1, y1 = left
            x2, y2 = right
            cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
            if abs(cross) <= tolerance and min(x1, x2) - tolerance <= x <= max(x1, x2) + tolerance and min(y1, y2) - tolerance <= y <= max(y1, y2) + tolerance:
                return False
            if (y1 > y) != (y2 > y):
                intersection = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < intersection:
                    inside = not inside
        if not inside:
            return False
    return True


def positive_design_value(definition: List[str], area: float, people: float | None = None) -> float | None:
    try:
        method = definition[2].upper()
        if method in {"LIGHTINGLEVEL", "EQUIPMENTLEVEL", "PEOPLE"}:
            return float(definition[3])
        if method in {"WATTS/AREA", "PEOPLE/AREA"}:
            return float(definition[4]) * area
        if method == "WATTS/PERSON" and people is not None:
            return float(definition[5]) * people
        if method == "AREA/PERSON":
            return area / float(definition[5])
    except Exception:
        return None
    return None


def check_osm(path: Path, handoff_hash: str, required_spaces: List[str], required_zones: List[str], required_tokens: List[str], flow_tokens: List[str], errors: List[str], handoff_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
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
    objects = osm_objects(text)
    by_type: Dict[str, List[List[str]]] = {}
    for kind, fields in objects:
        by_type.setdefault(kind, []).append(fields)
    space_records = by_type.get("OS:SPACE", [])
    zone_records = by_type.get("OS:THERMALZONE", [])
    spaces = {x[1]: x for x in space_records if len(x) > 10 and x[1]}
    zones = {x[1]: x for x in zone_records if len(x) > 1 and x[1]}
    if len(spaces) != len(space_records) or len(zones) != len(zone_records):
        errors.append("result.osm:invalid_or_duplicate_space_or_zone")
    space_handles = {name: handle(rec[0]) for name, rec in spaces.items()}
    if not set(required_spaces).issubset(spaces) or not set(required_zones).issubset(zones):
        errors.append("result.osm:required_space_or_zone_missing")
    zone_handles = {handle(zone[0]) for zone in zones.values()}
    referenced_zone_handles = {handle(space[10]) for space in spaces.values()}
    if "" in referenced_zone_handles or not referenced_zone_handles.issubset(zone_handles):
        errors.append("result.osm:space_zone_reference_invalid")
    if zone_handles - referenced_zone_handles:
        errors.append("result.osm:orphan_zone")
    space_floor_areas: Dict[str, float] = {}
    handoff_records = {
        str(record.get("name") or record.get("space_name")): record
        for record in extract_space_records(handoff_data, [], "handoff.json")
    } if handoff_data is not None else {}
    for name, rec in spaces.items():
        space_handle = handle(rec[0])
        floors = [x for x in by_type.get("OS:SURFACE", []) if len(x) > 14 and x[2].upper() == "FLOOR" and handle(x[4]) == space_handle]
        try:
            areas: List[float] = []
            for floor in floors:
                coords = [float(value) for value in floor[11:] if value != ""]
                if len(coords) < 9 or len(coords) % 3:
                    raise ValueError
                areas.append(polygon_area_3d(list(zip(coords[0::3], coords[1::3], coords[2::3]))))
            if not floors or sum(areas) <= 0:
                errors.append(f"result.osm:space_floor_area_mismatch:{name}")
            else:
                space_floor_areas[name] = sum(areas)
                expected_area = handoff_records.get(name, {}).get("floor_area_m2")
                if expected_area is not None and abs(space_floor_areas[name] - float(expected_area)) > 0.01:
                    errors.append(f"result.osm:handoff_floor_area_mismatch:{name}")
        except Exception:
            errors.append(f"result.osm:space_floor_geometry_parse_failed:{name}")
    for name, spec in CASE_SPEC["target_spaces"].items():
        rec = spaces.get(name, [])
        if len(rec) <= 10:
            continue
        zone_handle = rec[10].strip("{}")
        expected_zone = zones.get(spec["zone"], [])
        if not expected_zone or zone_handle != expected_zone[0].strip("{}"):
            errors.append(f"result.osm:space_zone_relationship_mismatch:{name}")
    subs = [x for x in by_type.get("OS:SUBSURFACE", []) if len(x) > 4 and x[1] == "BOOTH-DOOR"]
    surfaces = {handle(x[0]): x for x in by_type.get("OS:SURFACE", []) if len(x) > 14}
    def points(rec: List[str], start: int) -> List[Tuple[float, float, float]]:
        values = [float(value) for value in rec[start:] if value != ""]
        if len(values) < 9 or len(values) % 3:
            raise ValueError
        return list(zip(values[0::3], values[1::3], values[2::3]))

    storage_handle, booth_handle = space_handles.get("STORAGE"), space_handles.get("FINISHING-BOOTH")
    reciprocal = []
    for surface in surfaces.values():
        other = surfaces.get(handle(surface[6])) if len(surface) > 6 and surface[5].upper() == "SURFACE" else None
        if (other and other[5].upper() == "SURFACE" and handle(other[6]) == handle(surface[0]) and
                {handle(surface[4]), handle(other[4])} == {storage_handle, booth_handle}):
            reciprocal.append((surface, other))
    unique_pairs = {(min(handle(a[0]), handle(b[0])), max(handle(a[0]), handle(b[0]))) for a, b in reciprocal}
    if len(unique_pairs) != 1 or len(reciprocal) != 2:
        errors.append("result.osm:storage_booth_reciprocal_boundary_mismatch")
    else:
        a, b = reciprocal[0]
        try:
            pa, pb = points(a, 11), points(b, 11)
            if abs(polygon_area_3d(pa) - polygon_area_3d(pb)) > 1e-7 or {tuple(round(v, 8) for v in p) for p in pa} != {tuple(round(v, 8) for v in p) for p in pb}:
                errors.append("result.osm:storage_booth_boundary_geometry_or_area_mismatch")
            normals = []
            for poly in (pa, pb):
                u, v = tuple(poly[1][i]-poly[0][i] for i in range(3)), tuple(poly[2][i]-poly[0][i] for i in range(3))
                normals.append((u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]))
            if sum(normals[0][i]*normals[1][i] for i in range(3)) >= 0:
                errors.append("result.osm:storage_booth_boundary_not_oppositely_oriented")
        except Exception:
            errors.append("result.osm:storage_booth_boundary_geometry_parse_failed")
    if len(subs) != 1:
        errors.append("result.osm:service_door_count_mismatch")
    else:
        door = subs[0]
        parent = surfaces.get(handle(door[4]))
        booth_handle = handle(spaces.get("FINISHING-BOOTH", [""])[0])
        if parent is None or parent[2].upper() != "WALL" or handle(parent[4]) != booth_handle:
            errors.append("result.osm:booth_door_parent_mismatch")
        try:
            door_coords = [float(x) for x in door[10:] if x != ""]
            parent_coords = [float(x) for x in parent[11:] if x != ""] if parent else []
            door_points = list(zip(door_coords[0::3], door_coords[1::3], door_coords[2::3]))
            parent_points = list(zip(parent_coords[0::3], parent_coords[1::3], parent_coords[2::3]))
            if len(door_points) != 4 or not polygon_contains_strict_3d(parent_points, door_points):
                errors.append("result.osm:booth_door_geometry_not_strictly_inside_parent")
        except Exception:
            errors.append("result.osm:booth_door_geometry_parse_failed")
    expected_subs = {"BOOTH-DOOR": "DOOR", "HIGH-VENT-WINDOW": "OPERABLEWINDOW", "MAIN-STUDIO HIGH DAYLIGHT WINDOW": "FIXEDWINDOW"}
    all_subs = {x[1]: x for x in by_type.get("OS:SUBSURFACE", []) if len(x) > 4}
    counts["_door_count"] = sum("DOOR" in x[2].upper() for x in all_subs.values())
    counts["_window_count"] = sum("WINDOW" in x[2].upper() for x in all_subs.values())
    if not set(expected_subs).issubset(all_subs):
        errors.append("result.osm:required_subsurface_set_mismatch")
    for name, subtype in expected_subs.items():
        sub = all_subs.get(name, [])
        parent = surfaces.get(handle(sub[4])) if len(sub) > 4 else None
        expected_space = "MAIN-STUDIO" if name.startswith("MAIN-STUDIO") else "FINISHING-BOOTH"
        if not sub or sub[2].upper() != subtype or parent is None or handle(parent[4]) != space_handles.get(expected_space):
            errors.append(f"result.osm:subsurface_identity_or_parent_mismatch:{name}")
        try:
            if not polygon_contains_strict_3d(points(parent, 11), points(sub, 10)):
                errors.append(f"result.osm:subsurface_not_coplanar_strictly_inside:{name}")
        except Exception:
            errors.append(f"result.osm:subsurface_geometry_parse_failed:{name}")
    try:
        gross_outdoor_wall_area = sum(polygon_area_3d(points(s, 11)) for s in surfaces.values() if s[2].upper() == "WALL" and s[5].upper() == "OUTDOORS")
        window_area = sum(polygon_area_3d(points(s, 10)) for s in all_subs.values() if "WINDOW" in s[2].upper())
        counts["_gross_outdoor_wall_area"] = gross_outdoor_wall_area
        counts["_window_area"] = window_area
        counts["_wwr"] = window_area / gross_outdoor_wall_area
    except Exception:
        errors.append("result.osm:wwr_geometry_parse_failed")
    type_limits = {handle(x[0]): x for x in by_type.get("OS:SCHEDULETYPELIMITS", []) if len(x) > 4}
    day_schedules = {handle(x[0]): x for x in by_type.get("OS:SCHEDULE:DAY", []) if len(x) > 6}
    schedules = {handle(x[0]): x for x in by_type.get("OS:SCHEDULE:RULESET", []) if len(x) > 3 and handle(x[2]) and handle(x[3])}

    def schedule_semantics(schedule_handle: str, expected: str) -> bool:
        schedule = schedules.get(schedule_handle)
        if schedule is None:
            return False
        limits = type_limits.get(handle(schedule[2]))
        day = day_schedules.get(handle(schedule[3]))
        if limits is None or day is None or handle(day[2]) != handle(schedule[2]):
            return False
        try:
            values = [float(day[index]) for index in range(6, len(day), 3) if day[index] != ""]
        except Exception:
            return False
        unit = (limits[5] if len(limits) > 5 else "").upper()
        if not values:
            return False
        if expected == "fraction":
            return unit not in {"TEMPERATURE", "ACTIVITYLEVEL"} and all(0.0 <= value <= 1.0 for value in values)
        if expected == "activity":
            return unit == "ACTIVITYLEVEL" and all(0.0 < value <= 1000.0 for value in values)
        return unit == "TEMPERATURE" and all(-50.0 <= value <= 60.0 for value in values)

    def schedule_values(schedule_handle: str) -> List[float]:
        schedule = schedules.get(schedule_handle)
        day = day_schedules.get(handle(schedule[3])) if schedule else None
        if day is None:
            return []
        try:
            pairs = [(int(day[index - 2]), int(day[index - 1]), float(day[index])) for index in range(6, len(day), 3) if day[index] != ""]
        except Exception:
            return []
        if not pairs or pairs[-1][:2] != (24, 0) or any(not (0 <= hour <= 24 and 0 <= minute < 60) for hour, minute, _ in pairs):
            return []
        if any(left[:2] >= right[:2] for left, right in zip(pairs, pairs[1:])):
            return []
        return [value for _, _, value in pairs]

    definition_types = {
        "OS:PEOPLE": "OS:PEOPLE:DEFINITION",
        "OS:LIGHTS": "OS:LIGHTS:DEFINITION",
        "OS:ELECTRICEQUIPMENT": "OS:ELECTRICEQUIPMENT:DEFINITION",
    }
    design_values: Dict[str, Dict[str, float]] = {}
    for kind in definition_types:
        definitions = {handle(x[0]): x for x in by_type.get(definition_types[kind], []) if len(x) > 4}
        instances = [x for x in by_type.get(kind, []) if len(x) > 4]
        design_values[kind] = {}
        for space_name in required_spaces:
            matches = [x for x in instances if handle(x[3]) == space_handles.get(space_name)]
            valid = [
                rec for rec in matches
                if definitions.get(handle(rec[2])) is not None
                and schedule_semantics(handle(rec[4]), "fraction")
            ]
            if not valid:
                errors.append(f"result.osm:load_relationship_mismatch:{kind}:{space_name}")
                continue
            people = design_values.get("OS:PEOPLE", {}).get(space_name)
            values = [
                positive_design_value(definitions[handle(rec[2])], space_floor_areas.get(space_name, 1.0), people)
                for rec in valid
            ]
            if any(value is None or value <= 0 for value in values):
                errors.append(f"result.osm:load_definition_invalid:{kind}:{space_name}")
            else:
                design_values[kind][space_name] = sum(float(value) for value in values if value is not None)
            if kind == "OS:PEOPLE" and any(len(rec) <= 5 or not schedule_semantics(handle(rec[5]), "activity") for rec in valid):
                errors.append(f"result.osm:people_activity_schedule_invalid:{space_name}")
    outdoor_air = {handle(x[0]): x for x in by_type.get("OS:DESIGNSPECIFICATION:OUTDOORAIR", []) if len(x) > 6}
    oa_rates = {}
    for space_name, space in spaces.items():
        oa = outdoor_air.get(handle(space[12])) if len(space) > 12 else None
        try:
            if oa is None or oa[2].upper() != "SUM":
                raise ValueError
            rates = [float(oa[index] or 0) for index in (3, 4, 5, 6)]
            if sum(rates) <= 0:
                raise ValueError
            oa_rates[space_name] = rates[1]
        except Exception:
            errors.append(f"result.osm:outdoor_air_invalid:{space_name}")
    if oa_rates.get("FINISHING-BOOTH", 0) <= max(oa_rates.get("MAIN-STUDIO", 0), oa_rates.get("STORAGE", 0)):
        errors.append("result.osm:booth_outdoor_air_not_high")
    equipment_lists = [x for x in by_type.get("OS:ZONEHVAC:EQUIPMENTLIST", []) if len(x) > 6]
    fans = [x for x in by_type.get("OS:FAN:ZONEEXHAUST", []) if len(x) > 7]
    booth_zone = zones.get("FINISHING-BOOTH-ZN", [])
    booth_equipment = [x for x in equipment_lists if booth_zone and handle(x[2]) == handle(booth_zone[0])]
    listed_handles = {handle(x[index]) for x in booth_equipment for index in range(4, len(x), 5)}
    valid_fans = []
    for fan in fans:
        try:
            if (schedule_semantics(handle(fan[2]), "fraction") and
                    float(fan[3]) > 0 and float(fan[4]) > 0 and float(fan[5]) > 0 and
                    handle(fan[0]) in listed_handles):
                valid_fans.append(fan)
        except Exception:
            continue
    if not valid_fans:
        errors.append("result.osm:booth_exhaust_fan_invalid_or_disconnected")
    thermostats = {handle(x[0]): x for x in by_type.get("OS:THERMOSTATSETPOINT:DUALSETPOINT", []) if len(x) > 3}
    if len(thermostats) < len(required_zones):
        errors.append("result.osm:thermostat_count_mismatch")
    for zone_name in required_zones:
        zone = zones.get(zone_name, [])
        thermostat = thermostats.get(handle(zone[19])) if len(zone) > 19 else None
        if thermostat is None:
            errors.append(f"result.osm:zone_thermostat_relationship_mismatch:{zone_name}")
            continue
        heating_handle, cooling_handle = handle(thermostat[2]), handle(thermostat[3])
        heating_values, cooling_values = schedule_values(heating_handle), schedule_values(cooling_handle)
        if not schedule_semantics(heating_handle, "temperature") or not schedule_semantics(cooling_handle, "temperature") or not heating_values or not cooling_values:
            errors.append(f"result.osm:thermostat_schedule_chain_invalid:{zone_name}")
            continue
        if max(heating_values) >= min(cooling_values):
            errors.append(f"result.osm:thermostat_deadband_invalid:{zone_name}")
    ideals = {handle(x[0]): x for x in by_type.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM", []) if len(x) > 4}
    if len(ideals) < len(required_spaces):
        errors.append("result.osm:ideal_loads_count_mismatch")
    for name, spec in CASE_SPEC["target_spaces"].items():
        zone = zones.get(spec["zone"], [])
        zone_equipment = [x for x in equipment_lists if zone and handle(x[2]) == handle(zone[0])]
        listed_handles = {handle(x[index]) for x in zone_equipment for index in range(4, len(x), 5)}
        matching_ideals = set(ideals) & listed_handles
        if not zone or len(matching_ideals) != 1:
            errors.append(f"result.osm:ideal_loads_zone_node_chain_mismatch:{name}")
    default_schedule_sets = {handle(x[0]): x for x in by_type.get("OS:DEFAULTSCHEDULESET", []) if len(x) > 1}
    default_construction_sets = {handle(x[0]): x for x in by_type.get("OS:DEFAULTCONSTRUCTIONSET", []) if len(x) > 1}
    constructions = {handle(x[0]) for x in by_type.get("OS:CONSTRUCTION", []) if len(x) > 3 and handle(x[3])}
    counts["_schedule_set_names"] = {x[1] for x in default_schedule_sets.values()}
    counts["_construction_set_names"] = {x[1] for x in default_construction_sets.values()}
    counts["_space_schedule_sets"] = {handle(x[4]) for x in spaces.values()}
    counts["_space_construction_sets"] = {handle(x[3]) for x in spaces.values()}
    counts["_schedule_set_handles"] = set(default_schedule_sets)
    counts["_construction_set_handles"] = set(default_construction_sets)
    counts["_construction_references_valid"] = all(handle(x[3]) in constructions for x in by_type.get("OS:SURFACE", []) + by_type.get("OS:SUBSURFACE", []) if len(x) > 3)
    counts["_schedule_names"] = sorted(x[1] for x in schedules.values())
    counts["_construction_names"] = sorted(x[1] for x in by_type.get("OS:CONSTRUCTION", []) if len(x) > 1)
    if len(counts["_schedule_names"]) != len(set(counts["_schedule_names"])) or len(counts["_construction_names"]) != len(set(counts["_construction_names"])):
        errors.append("result.osm:duplicate_schedule_or_construction_name")
    return counts


def check_flow_report(
    path: Path,
    handoff_path: Path,
    osm_path: Path,
    handoff_data: Dict[str, Any],
    osm_counts: Dict[str, Any],
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
    if data.get("software_stage") != "openstudio" or int(data.get("archicad_native_transaction_count", -1)) != 12:
        errors.append("flow_report:stage_chain_mismatch")
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
    root = path.parent
    if data.get("weather_file") != "weather.epw" or data.get("weather_sha256") != sha256_file(root / "weather.epw"):
        errors.append("flow_report:weather_dependency_mismatch")
    if data.get("workflow_sha256") != sha256_file(root / "workflow.osw"):
        errors.append("flow_report:workflow_dependency_mismatch")
    if not osm_counts.get("_construction_references_valid"):
        errors.append("result.osm:construction_reference_invalid")

    area = first_number(data, "building_area_m2")
    handoff_area = get_handoff_area(handoff_data)
    if area is not None and handoff_area is not None and abs(area - handoff_area) > max(0.5, handoff_area * 0.03):
        errors.append(f"flow_report:area_mismatch:{area:.3f}!={handoff_area:.3f}")
    room_count = first_number(data, "room_count")
    zone_count = first_number(data, "thermal_zone_count")
    if room_count is not None and int(round(room_count)) != osm_counts["space_count"]:
        errors.append("flow_report:room_count_mismatch")
    if zone_count is not None and int(round(zone_count)) != osm_counts["zone_count"]:
        errors.append("flow_report:thermal_zone_count_mismatch")
    if first_number(data, "surface_count") is not None and int(first_number(data, "surface_count") or 0) != osm_counts["surface_count"]:
        errors.append("flow_report:surface_count_mismatch_osm")
    if first_number(data, "subsurface_count") is not None and int(first_number(data, "subsurface_count") or 0) != osm_counts["subsurface_count"]:
        errors.append("flow_report:subsurface_count_mismatch_osm")
    for key in ("door_count", "window_count"):
        value = first_number(data, key)
        if value is None or not float(value).is_integer():
            errors.append(f"flow_report:{key}_missing_or_invalid")
            continue
        reported = int(value)
        if reported != osm_counts.get(f"_{key}"):
            errors.append(f"flow_report:{key}_mismatch_osm")
    wwr = first_number(data, "window_wall_ratio")
    if wwr is None or abs(wwr - osm_counts.get("_wwr", -1)) > 1e-9:
        errors.append("flow_report:window_wall_ratio_mismatch_osm")
    if abs(float(data.get("gross_outdoor_wall_area_m2", -1)) - osm_counts.get("_gross_outdoor_wall_area", -2)) > 1e-7 or abs(float(data.get("window_area_m2", -1)) - osm_counts.get("_window_area", -2)) > 1e-7:
        errors.append("flow_report:wwr_component_area_mismatch_osm")
    reported_schedules, reported_constructions = data.get("schedule_set"), data.get("construction_set")
    if (not isinstance(reported_schedules, list) or len(reported_schedules) != len(set(reported_schedules)) or set(reported_schedules) != set(osm_counts.get("_schedule_names", [])) or
            not isinstance(reported_constructions, list) or len(reported_constructions) != len(set(reported_constructions)) or set(reported_constructions) != set(osm_counts.get("_construction_names", []))):
        errors.append("flow_report:schedule_or_construction_inventory_mismatch")
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
    sql_hourly = flow_data.get("_sql_hourly", {})
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
            break
        name = next((str(v) for k, v in row.items() if norm(k) == norm("space_name")), "")
        zone = next((str(v) for k, v in row.items() if norm(k) == norm("thermal_zone")), "")
        seen_spaces.add(norm(name))
        seen_zones.add(norm(zone))
        spec = CASE_SPEC["target_spaces"].get(name)
        if spec is None or norm(zone) != norm(spec["zone"]):
            errors.append(f"model_summary.csv:space_zone_pair_mismatch:{name}:{zone}")
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
            handoff_records = {str(r.get("name") or r.get("space_name")): r for r in extract_space_records(handoff_data, [], "handoff.json")}
            handoff_area = handoff_records.get(name, {}).get("floor_area_m2")
            if handoff_area is not None and abs(area - float(handoff_area)) > 0.01:
                errors.append(f"model_summary.csv:handoff_space_area_mismatch:{name}")
        except Exception:
            errors.append(f"model_summary.csv:invalid_area:{name}")
        try:
            energy = float(next((v for k, v in row.items() if norm(k) == norm("energy_use_kwh")), ""))
            peak = float(next((v for k, v in row.items() if norm(k) == norm("peak_load_w")), ""))
            if energy <= 0 or peak <= 0:
                errors.append(f"model_summary.csv:nonpositive_energy_or_peak:{name}")
            total_energy += energy
            actual = sql_hourly.get(name, {})
            energy_vars = ("Zone Lights Electricity Energy", "Zone Electric Equipment Electricity Energy", "Zone Ideal Loads Zone Total Heating Energy", "Zone Ideal Loads Zone Total Cooling Energy")
            rate_vars = ("Zone Ideal Loads Zone Total Heating Rate", "Zone Ideal Loads Zone Total Cooling Rate")
            expected_energy = sum(actual[v][2] for v in energy_vars)
            if name == "FINISHING-BOOTH":
                expected_energy += flow_data.get("_sql_fan", (0, 0, 0.0, 0.0))[2]
            expected_energy /= 3_600_000.0
            expected_peak = max(actual[v][3] for v in rate_vars)
            if abs(energy - expected_energy) > 1e-5 or abs(peak - expected_peak) > 1e-5:
                errors.append(f"model_summary.csv:sql_recalculation_mismatch:{name}")
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


def parse_timestamp(value: Any) -> datetime:
    text = re.sub(r"(\.\d{6})\d+", r"\1", str(value)).replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def check_native_stage_log(path: Path, init_path: Path, stage1_path: Path, handoff_path: Path, errors: List[str]) -> None:
    data = load_json(path)
    if "archicad" not in str(data.get("schema", "")).lower() or data.get("case_id") != CASE_SPEC["case_id"]:
        errors.append("native_stage_log.json:schema_or_case_mismatch")
    process = data.get("command_server_process", {})
    exe = str(process.get("executable_path", "")).replace("\\", "/").lower()
    if "archicad 27" not in exe or not exe.endswith(".exe"):
        errors.append("native_stage_log.json:executable_path_mismatch")
    if not str(process.get("product_version", "")).startswith("27"):
        errors.append("native_stage_log.json:product_version_mismatch")
    artifacts = data.get("artifacts", {})
    for name, expected_path in (("init.ifc", init_path), ("stage1.ifc", stage1_path), ("handoff.json", handoff_path)):
        rec = artifacts.get(name, {})
        if str(rec.get("sha256", "")).lower() != sha256_file(expected_path) or int(rec.get("size", -1)) != expected_path.stat().st_size:
            errors.append(f"native_stage_log.json:artifact_mismatch:{name}")
    if "EXPRESS Data Manager" not in str(artifacts.get("stage1.ifc", {}).get("header_preprocessor")):
        errors.append("native_stage_log.json:missing_archicad_edm_export_evidence")
    section = data.get("native_transactions", {})
    transactions = section.get("Items") if isinstance(section, dict) else section
    if not isinstance(transactions, list) or len(transactions) < 5:
        errors.append("native_stage_log.json:transactions_missing")
        return
    methods = [str(t.get("request", {}).get("method", "")) for t in transactions]
    if methods[0] != "Model.LoadFile" or methods[-1] != "Model.SaveFile":
        errors.append("native_stage_log.json:load_save_order_mismatch")
    for index, transaction in enumerate(transactions):
        request, response = transaction.get("request"), transaction.get("response")
        try:
            parsed_request = json.loads(transaction.get("request_json", ""))
            parsed_response = json.loads(transaction.get("response_text", ""))
        except Exception:
            parsed_request = parsed_response = None
        if parsed_request != request:
            errors.append(f"native_stage_log.json:request_json_mismatch:{index}")
        if parsed_response != response:
            errors.append(f"native_stage_log.json:response_text_mismatch:{index}")
        if transaction.get("status") != 200 or not isinstance(response, dict) or response.get("jsonrpc") != "2.0" or "error" in response:
            errors.append(f"native_stage_log.json:transaction_failure:{index}")
        try:
            if parse_timestamp(transaction["completed_at_utc"]) < parse_timestamp(transaction["started_at_utc"]):
                raise ValueError
        except Exception:
            errors.append(f"native_stage_log.json:invalid_timestamp:{index}")
    if Path(str(transactions[0]["request"].get("params", {}).get("location", "")).replace("\\", "/")).name.lower() != "init.ifc":
        errors.append("native_stage_log.json:load_semantics_mismatch")
    if Path(str(transactions[-1]["request"].get("params", {}).get("location", "")).replace("\\", "/")).name.lower() != "stage1.ifc":
        errors.append("native_stage_log.json:save_semantics_mismatch")
    try:
        import ifcopenshell  # type: ignore
        stage = ifcopenshell.open(str(stage1_path))
        created_handles: Set[str] = set()
        for cls, opening_name in (("IfcDoor", "BOOTH-DOOR"), ("IfcWindow", "HIGH-VENT-WINDOW")):
            native = next(item for item in stage.by_type(cls) if norm(item.Name) == norm(opening_name))
            records = [
                t for t in transactions
                if t.get("request", {}).get("method") == "Entity.Create"
                and norm(t.get("request", {}).get("params", {}).get("EntityData", {}).get(cls, {}).get("Name")) == norm(opening_name)
            ]
            if len(records) != 1:
                raise ValueError
            opening_data = records[0]["request"]["params"]["EntityData"][cls]
            if opening_data.get("GlobalId") != str(native.GlobalId) or float(opening_data.get("OverallHeight", 0)) <= 0 or float(opening_data.get("OverallWidth", 0)) <= 0:
                raise ValueError
            created_handles.add(str(records[0].get("response", {}).get("result", "")))
        containment_updates = [
            t.get("request", {}).get("params", {}).get("EntityData", {}).get("IfcRelContainedInSpatialStructure", {}).get("RelatedElements", [])
            for t in transactions if t.get("request", {}).get("method") == "Entity.Modify"
        ]
        if not created_handles or not any(created_handles.issubset({str(value) for value in values}) for values in containment_updates):
            raise ValueError
        log_text = json.dumps(transactions, ensure_ascii=False)
        if any(token not in log_text for token in CASE_SPEC["required_spaces"]):
            errors.append("native_stage_log.json:required_space_transaction_missing")
    except Exception:
        errors.append("native_stage_log.json:opening_transaction_mismatch")
    try:
        start = parse_timestamp(data["native_stage_started_at_utc"])
        complete = parse_timestamp(data["native_stage_completed_at_utc"])
        if start > parse_timestamp(transactions[0]["started_at_utc"]) or complete < parse_timestamp(transactions[-1]["completed_at_utc"]):
            errors.append("native_stage_log.json:stage_timestamp_bounds_mismatch")
        for left, right in zip(transactions, transactions[1:]):
            if parse_timestamp(left["completed_at_utc"]) > parse_timestamp(right["started_at_utc"]):
                errors.append("native_stage_log.json:transaction_timestamp_order_mismatch")
                break
    except Exception:
        errors.append("native_stage_log.json:stage_timestamp_parse_failed")


def check_native_simulation(root: Path, flow: Dict[str, Any], errors: List[str]) -> None:
    sql_path, err_path, end_path = root / "run/eplusout.sql", root / "run/eplusout.err", root / "run/eplusout.end"
    for key, path in (("energyplus_sql_sha256", sql_path), ("energyplus_err_sha256", err_path), ("energyplus_end_sha256", end_path)):
        if str(flow.get(key, "")).lower() != sha256_file(path):
            errors.append(f"flow_report:{key}_mismatch")
    err_text, end_text = read_text(err_path), read_text(end_path)
    err_summary = re.search(r"EnergyPlus Completed Successfully--\s*(\d+) Warning;\s*(\d+) Severe Errors;\s*Elapsed Time=(\d+hr \d+min\s+[\d.]+sec)\s*$", err_text.strip())
    end_summary = re.fullmatch(r"EnergyPlus Completed Successfully--\s*(\d+) Warning;\s*(\d+) Severe Errors;\s*Elapsed Time=(\d+hr \d+min\s+[\d.]+sec)", end_text.strip())
    if end_summary is None or int(end_summary.group(2)) != 0 or end_path.stat().st_size < 90:
        errors.append("run/eplusout.end:not_successful")
    version_match = re.search(r"^Program Version,(EnergyPlus, Version 25\.1\.0-[0-9a-f]+, YMD=[^\r\n]+),?\s*$", err_text, flags=re.MULTILINE)
    if version_match is None or "**  Fatal  **" in err_text or "CHKSBS" in err_text or "misses SubSurface" in err_text or "PsyPsatFnTemp" in err_text or "Temperature out of range" in err_text or err_path.stat().st_size < 1000:
        errors.append("run/eplusout.err:version_or_fatal_error")
    if err_summary is None or end_summary is None or err_summary.groups() != end_summary.groups():
        errors.append("run/eplusout.err:not_successful")
    sql_warning_rows = -1
    sql_version = ""
    conn = None
    try:
        conn = sqlite3.connect(f"file:{sql_path}?mode=ro", uri=True)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        simulations = conn.execute("SELECT EnergyPlusVersion, Completed, CompletedSuccessfully FROM Simulations").fetchall()
        version = simulations[0][0] if len(simulations) == 1 else ""
        sql_version = str(version)
        simulation_flags = (str(simulations[0][1]).upper(), str(simulations[0][2]).upper()) if len(simulations) == 1 else ("", "")
        report_count = conn.execute("SELECT COUNT(*) FROM ReportData").fetchone()[0]
        fatal_rows = conn.execute("SELECT COUNT(*) FROM Errors WHERE ErrorType IN (2,3)").fetchone()[0]
        sql_warning_rows = int(conn.execute("SELECT COUNT(*) FROM Errors WHERE ErrorType=0").fetchone()[0])
        all_error_counts = {str(kind): int(count) for kind, count in conn.execute("SELECT ErrorType,COUNT(*) FROM Errors GROUP BY ErrorType")}
        calendar = conn.execute("SELECT COUNT(*), COUNT(DISTINCT printf('%02d-%02d-%02d',Month,Day,Hour)), MIN(Month),MAX(Month),MIN(Hour),MAX(Hour) FROM Time WHERE Interval=60 AND WarmupFlag=0").fetchone()
        exact_version = str(version).startswith("EnergyPlus, Version 25.1.0-1c11a3d85f, YMD=")
        flags_valid = simulation_flags in {("TRUE", "TRUE"), ("FALSE", "FALSE")}
        ff_evidence = (simulation_flags != ("FALSE", "FALSE") or
                       (exact_version and err_summary is not None and end_summary is not None and err_summary.groups() == end_summary.groups() and int(err_summary.group(2)) == 0 and fatal_rows == 0 and calendar == (8760, 8760, 1, 12, 1, 24)))
        if len(simulations) != 1 or not flags_valid or not ff_evidence:
            errors.append("run/eplusout.sql:simulation_flags_or_row_count_invalid")
        if integrity != "ok" or not exact_version or report_count < 100000 or fatal_rows != 0 or calendar != (8760, 8760, 1, 12, 1, 24):
            errors.append("run/eplusout.sql:integrity_version_or_data_count")
        flow_series = flow.get("simulation", {}).get("hourly_series", [])
        if not isinstance(flow_series, list):
            flow_series = []
        hourly: Dict[str, Dict[str, Tuple[int, int, float, float]]] = {name: {} for name in CASE_SPEC["required_spaces"]}
        fan_actual = (0, 0, 0.0, 0.0)
        variables = ("Zone Lights Electricity Energy", "Zone Electric Equipment Electricity Energy", "Zone Ideal Loads Zone Total Heating Energy", "Zone Ideal Loads Zone Total Cooling Energy", "Zone Ideal Loads Zone Total Heating Rate", "Zone Ideal Loads Zone Total Cooling Rate")
        semantic_triples = [(str(rec.get("space_name", "")), str(rec.get("key_value", "")), str(rec.get("variable", ""))) for rec in flow_series] if isinstance(flow_series, list) else []
        if len(flow_series) != 19 or len(set(semantic_triples)) != 19:
            errors.append("flow_report:hourly_series_count_mismatch")
        else:
            by_space = {name: [rec for rec in flow_series if rec.get("space_name") == name] for name in CASE_SPEC["required_spaces"]}
            if set(rec.get("space_name") for rec in flow_series) != set(CASE_SPEC["required_spaces"]):
                errors.append("flow_report:hourly_series_space_set_mismatch")
            for name, records in by_space.items():
                expected_vars = set(variables) | ({"Fan Electricity Energy"} if name == "FINISHING-BOOTH" else set())
                if len(records) != len(expected_vars) or {rec.get("variable") for rec in records} != expected_vars:
                    errors.append(f"flow_report:hourly_series_variable_set_mismatch:{name}")
                    continue
                zone = CASE_SPEC["target_spaces"][name]["zone"]
                load_records = [rec for rec in records if rec.get("variable") in variables[:2]]
                ideal_records = [rec for rec in records if rec.get("variable") in variables[2:]]
                fan_records = [rec for rec in records if rec.get("variable") == "Fan Electricity Energy"]
                if any(rec.get("key_value") != zone for rec in load_records) or len({rec.get("key_value") for rec in ideal_records}) != 1 or not str(ideal_records[0].get("key_value", "")).strip():
                    errors.append(f"flow_report:hourly_series_key_semantics_mismatch:{name}")
                if name == "FINISHING-BOOTH" and (len(fan_records) != 1 or not str(fan_records[0].get("key_value", "")).strip()):
                    errors.append("flow_report:fan_series_key_semantics_mismatch")
                for rec in records:
                    row = conn.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0", (rec.get("key_value"), rec.get("variable"))).fetchone()
                    actual = (int(row[0]), int(row[1]), float(row[2] or 0), float(row[3] or 0))
                    hourly[name][str(rec.get("variable"))] = actual
                    if rec.get("variable") == "Fan Electricity Energy":
                        fan_actual = actual
                    if actual[0] != 8760 or actual[1] != 8760 or abs(float(rec.get("sum", 0))-actual[2]) > max(1e-3, abs(actual[2])*1e-9) or abs(float(rec.get("max", 0))-actual[3]) > max(1e-6, abs(actual[3])*1e-9):
                        errors.append("flow_report:hourly_series_value_mismatch")
                        break
            ideal_keys = {next(rec.get("key_value") for rec in records if rec.get("variable") in variables[2:]) for records in by_space.values() if any(rec.get("variable") in variables[2:] for rec in records)}
            fan_key = next((rec.get("key_value") for rec in flow_series if rec.get("variable") == "Fan Electricity Energy"), None)
            if len(ideal_keys) != 3 or fan_key in ideal_keys or fan_actual[0] != 8760 or fan_actual[1] != 8760 or fan_actual[2] <= 0:
                errors.append("flow_report:ideal_or_fan_sql_key_bijection_mismatch")
        flow["_sql_hourly"] = hourly
        flow["_sql_fan"] = fan_actual
        if flow.get("simulation", {}).get("sql_error_type_counts") != all_error_counts:
            errors.append("flow_report:sql_error_type_counts_mismatch")
    except Exception as exc:
        errors.append(f"run/eplusout.sql:parse_failed:{type(exc).__name__}")
    finally:
        if conn is not None:
            conn.close()
    exact_os_hash = "46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361"
    exact_ep_hash = "3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5"
    if str(flow.get("native_cli_executable", "")).replace("\\", "/").lower() != "c:/openstudio-3.10.0/bin/openstudio.exe" or str(flow.get("native_cli_sha256", "")).lower() != exact_os_hash:
        errors.append("flow_report:openstudio_provenance_mismatch")
    if str(flow.get("energyplus_executable", "")).replace("\\", "/").lower() != "c:/openstudio-3.10.0/energyplus/energyplus.exe" or str(flow.get("energyplus_executable_sha256", "")).lower() != exact_ep_hash:
        errors.append("flow_report:energyplus_provenance_mismatch")
    reported_version = str(flow.get("energyplus_version", ""))
    err_version = version_match.group(1).rstrip(",") if version_match is not None else ""
    if not sql_version or reported_version != sql_version or err_version != sql_version:
        errors.append("flow_report:energyplus_version_mismatch")
    if int(flow.get("energyplus_severe_errors", -1)) != 0 or int(flow.get("energyplus_fatal_errors", -1)) != 0:
        errors.append("flow_report:energyplus_error_count_mismatch")
    if err_summary is not None:
        status = str(flow.get("energyplus_status", "")).strip().lstrip("*").strip()
        if not status.endswith(err_summary.group(0)) or sql_warning_rows < 0 or int(err_summary.group(1)) < sql_warning_rows:
            errors.append("flow_report:energyplus_status_mismatch")
        if int(flow.get("energyplus_warning_count", -1)) != int(err_summary.group(1)):
            errors.append("flow_report:energyplus_warning_count_mismatch")
    transactions = flow.get("openstudio_cli_transactions")
    delivery = flow.get("final_delivery")
    if not isinstance(transactions, list) or len(transactions) != 1 or transactions[0] != delivery:
        errors.append("flow_report:final_delivery_transaction_mismatch")
        return
    if (delivery.get("executable") != r"C:\openstudio-3.10.0\bin\openstudio.exe" or
            delivery.get("arguments") != ["run", "-w", r"C:\Users\user\Desktop\workflow.osw"] or
            delivery.get("working_directory") != r"C:\Users\user\Desktop" or
            delivery.get("exit_code") != 0 or delivery.get("related_processes_after_wait") != 0):
        errors.append("flow_report:final_delivery_command_mismatch")
    if delivery.get("executable_sha256") != exact_os_hash:
        errors.append("flow_report:openstudio_executable_hash_mismatch")
    if delivery.get("result_osm_sha256") != sha256_file(root / "result.osm") or delivery.get("workflow_sha256") != sha256_file(root / "workflow.osw") or delivery.get("weather_sha256") != sha256_file(root / "weather.epw"):
        errors.append("flow_report:delivery_input_hash_mismatch")
    for key, path in (("sql_sha256", sql_path), ("err_sha256", err_path), ("end_sha256", end_path)):
        if str(delivery.get(key, "")).lower() != sha256_file(path):
            errors.append(f"flow_report:delivery_{key}_mismatch")
    samples = delivery.get("stable_file_samples", [])
    if len(samples) != 6 or any(int(sample.get("sql_size", -1)) != sql_path.stat().st_size or int(sample.get("err_size", -1)) != err_path.stat().st_size or int(sample.get("end_size", -1)) != end_path.stat().st_size for sample in samples):
        errors.append("flow_report:insufficient_final_file_stability")
    try:
        started = parse_timestamp(delivery["started_at_utc"])
        os_exit = parse_timestamp(delivery["openstudio_process_exited_at_utc"])
        children_exit = parse_timestamp(delivery["related_children_exited_at_utc"])
        completed = parse_timestamp(delivery["completed_at_utc"])
        sampled = [parse_timestamp(x["sampled_at_utc"]) for x in samples]
        mtimes = [parse_timestamp(x[k]) for x in samples for k in ("sql_mtime_utc", "err_mtime_utc", "end_mtime_utc")]
        if not (started <= os_exit <= children_exit <= sampled[0] <= sampled[-1] <= completed) or any(m > children_exit for m in mtimes):
            errors.append("flow_report:final_delivery_timestamp_order_mismatch")
    except Exception:
        errors.append("flow_report:final_delivery_timestamp_parse_failed")


def evaluate(root: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    paths = require_files(root, CASE_SPEC["required_files"], errors)
    if errors:
        return False, errors

    init_path = paths["init.ifc"]
    if sha256_file(init_path) != CASE_SPEC["init_sha256"]:
        errors.append("init.ifc:seed_hash_mismatch")
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
    if "THE EXPRESS DATA MANAGER VERSION 5.02.0100.09" not in stage1_header:
        errors.append("stage1.ifc:not_archicad_edm_export")
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
    try:
        osw = load_json(paths["workflow.osw"])
        if osw.get("seed_file") != "result.osm" or osw.get("weather_file") != "weather.epw" or osw.get("run_directory") != "run" or osw.get("steps") != []:
            errors.append("workflow.osw:structure_mismatch")
    except Exception as exc:
        errors.append(f"workflow.osw:parse_failed:{type(exc).__name__}")
    try:
        epw_lines = paths["weather.epw"].read_text(encoding="utf-8-sig", errors="strict").splitlines()
        if len(epw_lines) < 8768 or not epw_lines[0].upper().startswith("LOCATION,"):
            errors.append("weather.epw:header_or_line_count_mismatch")
        else:
            records = [line.split(",") for line in epw_lines[8:]]
            calendar = {(int(r[1]), int(r[2]), int(r[3])) for r in records if len(r) >= 4}
            if len(records) != 8760 or len(calendar) != 8760 or min(int(r[1]) for r in records) != 1 or max(int(r[1]) for r in records) != 12:
                errors.append("weather.epw:incomplete_unique_calendar")
            for row in records:
                dry_bulb, dew_point, rh, pressure = map(float, row[6:10])
                if not (-90 <= dry_bulb <= 70 and -90 <= dew_point <= dry_bulb + 0.2 and
                        0 <= rh <= 110 and 31000 <= pressure <= 120000):
                    errors.append("weather.epw:unreasonable_psychrometric_field")
                    break
    except Exception as exc:
        errors.append(f"weather.epw:parse_failed:{type(exc).__name__}")
    flow_tokens = ["weather_file", "schedule_set", "construction_set"]
    osm_counts = check_osm(paths["result.osm"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], flow_tokens, errors, handoff_data)
    flow_data = check_flow_report(paths["flow_report.json"], handoff, paths["result.osm"], handoff_data, osm_counts, stage1_info, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
    weather_source = flow_data.get("weather_source")
    if isinstance(weather_source, dict) and weather_source.get("sha256") not in (None, sha256_file(paths["weather.epw"])):
        errors.append("flow_report:weather_source_hash_mismatch")
    if str(flow_data.get("native_stage_log_sha256", "")).lower() != sha256_file(paths["native_stage_log.json"]):
        errors.append("flow_report:native_stage_log_sha256_mismatch")
    check_native_stage_log(paths["native_stage_log.json"], init_path, stage1, handoff, errors)
    check_native_simulation(root, flow_data, errors)
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
