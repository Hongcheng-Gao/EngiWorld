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

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-07-windows',
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
 'required_spaces': ['MARKET-HALL', 'COLD-CHAIN', 'WASTE-HOLDING'],
 'required_zones': ['MARKET-HALL-ZN', 'COLD-CHAIN-ZN', 'WASTE-HOLDING-ZN'],
 'stage1_tokens': ['EW2A07',
                   'EW2A07',
                   'MARKET-HALL','COLD-CHAIN','WASTE-HOLDING','SERVICE-SIDE',
                   'multi-cli-2-archicad-openstudio-task-07-windows'],
 'handoff_tokens': [],
 'osm_tokens': [],
 'summary_tokens': ['MARKET-HALL','COLD-CHAIN','WASTE-HOLDING'],
 'min_windows': 0,
 'min_doors': 0,
 'min_roofs': 0,
 'min_storeys': 1,
 'expected_stage': 'archicad'}

INIT_SHA256 = '41ddc5e8676624a8bd7612e0b01f4bfd9a472e142bd04e99b7bdc835ac54f5b9'
WEATHER_SHA256 = 'c184b947cd34d41c6d6474d63d66dbb82bc0e6cae4c888edcf837348282bce7f'
ARCHICAD_EXE_SHA256 = '594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775'
OPENSTUDIO_EXE_SHA256 = '46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361'
ENERGYPLUS_EXE_SHA256 = '3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5'
TARGETS = {
    'MARKET-HALL': ('MARKET-HALL-ZN', 54.0, '2mZbFQi4b3lB7hjUv9viKA'),
    'COLD-CHAIN': ('COLD-CHAIN-ZN', 9.0, '2i$fL50eb22QnXtqw7YtWf'),
    'WASTE-HOLDING': ('WASTE-HOLDING-ZN', 9.0, '0w_D7uLUP1O8iiPxe1UMfQ'),
}
OPENINGS = {
    '2bcPZT4ID7xBHfAxsMF6ij': ('IfcDoor', 'COLD-CHAIN-DOOR', 2.1, 0.9),
    '2fehOQvov2HRdbq8h$y2J4': ('IfcDoor', 'WASTE-HOLDING-DOOR', 2.1, 0.9),
    '0oMzLX_IHDR9i5xMAMbX1k': ('IfcDoor', 'MARKET-SERVICE-DOOR', 2.1, 0.9),
    '2OFM2uGNj5s9sVVFMK7utu': ('IfcWindow', 'MARKET-HALL-DAYLIGHT-WINDOW', 1.2, 1.8),
}

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


def iso_time(value: Any) -> datetime:
    text=str(value or '')
    if text.endswith('Z'):text=text[:-1]+'+00:00'
    # Windows/.NET timestamps may carry seven fractional-second digits (ticks),
    # while Python datetime is microsecond based. Preserve ordering at the
    # supported precision instead of rejecting native transaction evidence.
    text=re.sub(r'(\.\d{6})\d+(?=(?:[+-]\d{2}:\d{2})?$)',r'\1',text)
    parsed=datetime.fromisoformat(text)
    if parsed.tzinfo is None:raise ValueError('timezone required')
    return parsed


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
        import ifcopenshell.util.element  # type: ignore
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


def osm_objects(text: str) -> List[Tuple[str, List[str]]]:
    objects=[]
    for raw in re.findall(r"(?ms)^OS:[A-Za-z0-9:]+\s*,.*?;", text):
        clean=re.sub(r"!-[^\r\n]*", "", raw); parts=[x.strip() for x in re.split(r"[,;]", clean)]
        objects.append((parts[0].upper(),parts[1:]))
    return objects


def osm_handle(value: Any) -> str:
    return str(value or '').strip().strip('{}')


def osm_vertices(fields: List[str], start: int) -> List[Tuple[float,float,float]]:
    values=fields[start:]; points=[]
    for i in range(0,len(values)-2,3):
        try: points.append((float(values[i]),float(values[i+1]),float(values[i+2])))
        except ValueError: break
    return points


def polygon_area_3d(points: List[Tuple[float,float,float]]) -> float:
    ax=ay=az=0.0
    for a,b in zip(points,points[1:]+points[:1]):ax+=a[1]*b[2]-a[2]*b[1];ay+=a[2]*b[0]-a[0]*b[2];az+=a[0]*b[1]-a[1]*b[0]
    return 0.5*math.sqrt(ax*ax+ay*ay+az*az)


def strict_contains_3d(parent: List[Tuple[float,float,float]], child: List[Tuple[float,float,float]], tol: float=1e-7) -> bool:
    if len(parent)<3 or len(child)<3:return False
    u=tuple(parent[1][i]-parent[0][i] for i in range(3));v=tuple(parent[2][i]-parent[0][i] for i in range(3))
    n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]);length=math.sqrt(sum(x*x for x in n))
    if length<=tol:return False
    n=tuple(x/length for x in n)
    if any(abs(sum(n[i]*(p[i]-parent[0][i]) for i in range(3)))>tol for p in child):return False
    drop=max(range(3),key=lambda i:abs(n[i])); project=lambda p:tuple(p[i] for i in range(3) if i!=drop);poly=[project(p) for p in parent]
    for point in child:
        x,y=project(point);inside=False
        for a,b in zip(poly,poly[1:]+poly[:1]):
            x1,y1=a;x2,y2=b;cross=(x-x1)*(y2-y1)-(y-y1)*(x2-x1)
            if abs(cross)<=tol and min(x1,x2)-tol<=x<=max(x1,x2)+tol and min(y1,y2)-tol<=y<=max(y1,y2)+tol:return False
            if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1:inside=not inside
        if not inside:return False
    return True


def check_ew06_native_and_simulation(root: Path, paths: Dict[str, Path], handoff: Dict[str, Any], flow: Dict[str, Any], errors: List[str]) -> None:
    if sha256_file(paths['init.ifc']) != INIT_SHA256:
        errors.append('init.ifc:sha256_mismatch')
    if sha256_file(paths['weather.epw']) != WEATHER_SHA256:
        errors.append('weather.epw:sha256_mismatch')
    weather_head = read_text(paths['weather.epw'], 300).splitlines()[0] if paths['weather.epw'].stat().st_size else ''
    if not all(x in weather_head for x in ('TMY3', '724666', '39.74', '-105.18')):
        errors.append('weather.epw:location_metadata_mismatch')

    try:
        import ifcopenshell  # type: ignore
        seed = ifcopenshell.open(str(paths['init.ifc'])); stage = ifcopenshell.open(str(paths['stage1.ifc']))
        seed_roots = {x.GlobalId for x in seed.by_type('IfcRoot')}; stage_roots = {x.GlobalId for x in stage.by_type('IfcRoot')}
        if stage_roots - seed_roots != set(OPENINGS) or seed_roots - stage_roots:
            errors.append('stage1.ifc:root_delta_mismatch')
        for name, (zone, area, gid) in TARGETS.items():
            x = stage.by_guid(gid)
            if x is None or not x.is_a('IfcSpace') or x.Name != name or x.LongName != zone:
                errors.append(f'stage1.ifc:target_space_mismatch:{name}')
            quantities = ifcopenshell.util.element.get_psets(x, qtos_only=True) if x else {}
            actual = quantities.get('Qto_SpaceBaseQuantities', {}).get('NetFloorArea')
            if actual is None or abs(float(actual) - area) > 1e-6:
                errors.append(f'stage1.ifc:target_area_mismatch:{name}')
        for gid, (kind, name, height, width) in OPENINGS.items():
            x = stage.by_guid(gid)
            if x is None or not x.is_a(kind) or x.Name != name or abs(float(x.OverallHeight)-height)>1e-9 or abs(float(x.OverallWidth)-width)>1e-9:
                errors.append(f'stage1.ifc:opening_mismatch:{name}')
        rel = stage.by_guid('0Df6S7aU99fgow_MfggdfG')
        related = {x.GlobalId for x in rel.RelatedElements} if rel else set()
        if related != {'1fM01aZybAUOTPzXE9DGQP','1XDDy3eLHErOeOb9zde1sv',*OPENINGS.keys()}:
            errors.append('stage1.ifc:containment_mismatch')
        allowed=set(x[2] for x in TARGETS.values())|{'0JGKVgXG18XAd0hiD9lTcl','0Df6S7aU99fgow_MfggdfG'}
        def canon(value,seen=None):
            seen=set() if seen is None else seen
            if hasattr(value,'is_a') and callable(value.is_a):
                if value.id() in seen:return ('REF',getattr(value,'GlobalId',None),value.is_a())
                seen=seen|{value.id()};attrs=[]
                for i in range(len(value)):
                    try:attrs.append(canon(value[i],seen))
                    except Exception:attrs.append(None)
                return (value.is_a(),tuple(attrs))
            if isinstance(value,(tuple,list)):return tuple(canon(x,seen) for x in value)
            return value
        def root_canon(root):
            def value_canon(value,seen=None):
                seen=set() if seen is None else seen
                if hasattr(value,'is_a') and callable(value.is_a):
                    gid=getattr(value,'GlobalId',None)
                    if gid and value.id()!=root.id():return ('ROOTREF',value.is_a(),gid)
                    if value.id() in seen:return ('REF',gid,value.is_a())
                    return (value.is_a(),tuple(value_canon(value[i],seen|{value.id()}) for i in range(len(value))))
                if isinstance(value,(tuple,list)):return tuple(value_canon(x,seen) for x in value)
                return value
            return value_canon(root)
        for gid in seed_roots-allowed:
            if root_canon(seed.by_guid(gid))!=root_canon(stage.by_guid(gid)):errors.append(f'stage1.ifc:unexpected_recursive_root_change:{gid}')
    except Exception as exc:
        errors.append(f'stage1.ifc:deep_parse_failed:{type(exc).__name__}')

    log = load_json(paths['native_stage_log.json'])
    proc = log.get('command_server_process', {})
    if proc.get('executable_sha256') != ARCHICAD_EXE_SHA256 or '27.0.0 R1 (6000)' not in str(proc.get('product_version')):
        errors.append('native_stage_log.json:archicad_identity_mismatch')
    tx = log.get('native_transactions', {}).get('Items', [])
    methods = [x.get('request', {}).get('method') for x in tx]
    expected = ['Model.LoadFile'] + ['Entity.Modify']*4 + ['Entity.Create']*4 + ['Entity.GetAttribute','Entity.Modify','Model.SaveFile']
    if methods != expected or any(x.get('status') != 200 or not isinstance(x.get('response'), dict) or x['response'].get('error') for x in tx):
        errors.append('native_stage_log.json:transaction_sequence_or_response_mismatch')
    try:
        if tx[0]['request']['params']!={'location':r'C:\Users\user\Desktop\init.ifc'} or tx[-1]['request']['params']!={'location':r'C:\Users\user\Desktop\stage1.ifc'}:raise ValueError
        rename_expected=[('2mZbFQi4b3lB7hjUv9viKA','AISLE','MARKET-HALL','MARKET-HALL-ZN'),('2i$fL50eb22QnXtqw7YtWf','COLD-STORE','COLD-CHAIN','COLD-CHAIN-ZN'),('0w_D7uLUP1O8iiPxe1UMfQ','DRY-STORE','WASTE-HOLDING','WASTE-HOLDING-ZN')]
        for item,ex in zip(tx[1:4],rename_expected):
            a=item['request']['params'];sel=a['select']['IfcSpace'];data=a['EntityData']['IfcSpace']
            if (sel['GlobalId'],sel['Name'],data['Name'],data['LongName'])!=ex or not str(item['response'].get('result','')).isdigit():raise ValueError
        project=tx[4]['request']['params'];desc=project['EntityData']['IfcProject']['Description']
        if project['select']['IfcProject']['GlobalId']!='0JGKVgXG18XAd0hiD9lTcl' or not all(x in desc for x in ('EW2A07','MARKET-HALL','COLD-CHAIN','WASTE-HOLDING','SERVICE-SIDE')):raise ValueError
        created=[]
        for item,(gid,(kind,name,height,width)) in zip(tx[5:9],OPENINGS.items()):
            data=item['request']['params']['EntityData'][kind];rid=str(item['response']['result']);created.append(rid)
            if data['GlobalId']!=gid or data['Name']!=name or float(data['OverallHeight'])!=height or float(data['OverallWidth'])!=width or not rid.isdigit():raise ValueError
        original=[str(x) for x in tx[9]['response']['result']['RelatedElements']];modified=[str(x) for x in tx[10]['request']['params']['EntityData']['IfcRelContainedInSpatialStructure']['RelatedElements']]
        if len(original)!=2 or modified!=original+created:raise ValueError
        if any(x['response'].get('jsonrpc')!='2.0' for x in tx):raise ValueError
    except Exception:errors.append('native_stage_log.json:params_results_binding_mismatch')
    if log.get('artifacts', {}).get('stage1.ifc', {}).get('sha256') != sha256_file(paths['stage1.ifc']):
        errors.append('native_stage_log.json:stage1_hash_mismatch')
    records = handoff.get('spaces', [])
    mapped = {x.get('name'):(x.get('thermal_zone'),float(x.get('floor_area_m2',0)),x.get('ifc_global_id')) for x in records}
    if mapped != TARGETS or handoff.get('source_init_sha256') != INIT_SHA256:
        errors.append('handoff.json:exact_space_mapping_mismatch')
    owner_counts={x.get('name'):(int(x.get('door_count',-1)),int(x.get('window_count',-1))) for x in records}
    if owner_counts!={'MARKET-HALL':(1,1),'COLD-CHAIN':(1,0),'WASTE-HOLDING':(1,0)} or int(handoff.get('door_count',-1))!=3 or int(handoff.get('window_count',-1))!=1:errors.append('handoff.json:opening_owner_counts_mismatch')

    osm = read_text(paths['result.osm'])
    required_objects = {'OS:SPACE':3,'OS:THERMALZONE':3,'OS:PEOPLE':3,'OS:LIGHTS':3,'OS:ELECTRICEQUIPMENT':3,'OS:DESIGNSPECIFICATION:OUTDOORAIR':3,'OS:THERMOSTATSETPOINT:DUALSETPOINT':3,'OS:ZONEHVAC:IDEALLOADSAIRSYSTEM':3,'OS:SUBSURFACE':4}
    for obj, count in required_objects.items():
        actual = len(re.findall(r'(?im)^\s*'+re.escape(obj)+r'\s*,', osm))
        if actual != count: errors.append(f'result.osm:object_count:{obj}:{actual}!={count}')
    for token in ('ColdChainHighEquipment','WasteHoldingLowPeople','MarketPublicSchedule','ServiceSupportSchedule','MARKET-HALL-DAYLIGHT-WINDOW','MARKET-SERVICE-DOOR','COLD-CHAIN-DOOR','WASTE-HOLDING-DOOR'):
        if token.upper() not in osm.upper(): errors.append(f'result.osm:missing_semantic:{token}')
    objects=osm_objects(osm); surfaces={osm_handle(x[0]):x for kind,x in objects if kind=='OS:SURFACE'}
    subs={x[1]:x for kind,x in objects if kind=='OS:SUBSURFACE'}
    space_names={osm_handle(x[0]):x[1] for kind,x in objects if kind=='OS:SPACE'}
    expected_parent_space={'MARKET-HALL-DAYLIGHT-WINDOW':'MARKET-HALL','MARKET-SERVICE-DOOR':'MARKET-HALL','COLD-CHAIN-DOOR':'COLD-CHAIN','WASTE-HOLDING-DOOR':'WASTE-HOLDING'}
    if set(subs)!=set(expected_parent_space):errors.append('result.osm:exact_subsurface_set_mismatch')
    for name,space_name in expected_parent_space.items():
        try:
            sub=subs[name];parent=surfaces[osm_handle(sub[4])]
            if space_names.get(osm_handle(parent[4]))!=space_name:errors.append(f'result.osm:subsurface_parent_space_mismatch:{name}')
            parent_pts=osm_vertices(parent,11);child_pts=osm_vertices(sub,10)
            if not strict_contains_3d(parent_pts,child_pts):errors.append(f'result.osm:subsurface_not_coplanar_strictly_inside:{name}')
        except Exception:errors.append(f'result.osm:subsurface_geometry_parse_failed:{name}')
    spaces_by_name={x[1]:x for kind,x in objects if kind=='OS:SPACE'};spaces_by_handle={osm_handle(x[0]):x for x in spaces_by_name.values()}
    actual_areas={}
    for name,space in spaces_by_name.items():
        floors=[x for kind,x in objects if kind=='OS:SURFACE' and x[2].upper()=='FLOOR' and osm_handle(x[4])==osm_handle(space[0])]
        actual_areas[name]=sum(polygon_area_3d(osm_vertices(x,11)) for x in floors)
    for name,(_,area,_) in TARGETS.items():
        if abs(actual_areas.get(name,0)-area)>1e-6:errors.append(f'result.osm:floor_area_mismatch:{name}')
    definitions={kind:{osm_handle(x[0]):x for k,x in objects if k==kind} for kind in ('OS:PEOPLE:DEFINITION','OS:LIGHTS:DEFINITION','OS:ELECTRICEQUIPMENT:DEFINITION')}
    schedules={osm_handle(x[0]):x for kind,x in objects if kind.startswith('OS:SCHEDULE:')};loads=[]
    for kind in ('OS:PEOPLE','OS:LIGHTS','OS:ELECTRICEQUIPMENT'):
        for k,x in objects:
            if k==kind:loads.append((kind,x))
    by_space={n:[] for n in TARGETS}
    for kind,x in loads:
        space=spaces_by_handle.get(osm_handle(x[3]));definition=definitions[kind+':DEFINITION'].get(osm_handle(x[2]));schedule=schedules.get(osm_handle(x[4]))
        if not space or not definition or not schedule:errors.append(f'result.osm:load_chain_dangling:{x[1]}')
        else:by_space[space[1]].append((kind,definition,schedule))
    if any(sorted(x[0] for x in by_space[n])!=['OS:ELECTRICEQUIPMENT','OS:LIGHTS','OS:PEOPLE'] for n in TARGETS):errors.append('result.osm:load_space_set_mismatch')
    cold_eq=next((d for k,d,s in by_space['COLD-CHAIN'] if k=='OS:ELECTRICEQUIPMENT'),None);waste_p=next((d for k,d,s in by_space['WASTE-HOLDING'] if k=='OS:PEOPLE'),None)
    if not cold_eq or float(cold_eq[4])<20 or not waste_p or not(0<float(waste_p[4])<0.05):errors.append('result.osm:business_load_values_invalid')
    rulesets={x[1]:x for kind,x in objects if kind=='OS:SCHEDULE:RULESET'}
    if 'MarketPublicSchedule' not in rulesets or 'ServiceSupportSchedule' not in rulesets or osm_handle(rulesets['MarketPublicSchedule'][0])==osm_handle(rulesets['ServiceSupportSchedule'][0]):errors.append('result.osm:schedule_profiles_missing_or_shared')
    constants={osm_handle(x[0]):float(x[3]) for kind,x in objects if kind=='OS:SCHEDULE:CONSTANT'}
    thermostats=[x for kind,x in objects if kind=='OS:THERMOSTATSETPOINT:DUALSETPOINT']
    if len(thermostats)!=3 or any(osm_handle(x[2]) not in constants or osm_handle(x[3]) not in constants or constants[osm_handle(x[2])]>=constants[osm_handle(x[3])] for x in thermostats):errors.append('result.osm:thermostat_chain_or_deadband_invalid')
    ideals=[x for kind,x in objects if kind=='OS:ZONEHVAC:IDEALLOADSAIRSYSTEM']
    if len(ideals)!=3 or {x[1].replace(' IDEAL LOADS','') for x in ideals}!=set(TARGETS):errors.append('result.osm:ideal_loads_set_mismatch')
    zones={x[1]:x for kind,x in objects if kind=='OS:THERMALZONE'};thermo_by_handle={osm_handle(x[0]):x for x in thermostats};ideal_by_handle={osm_handle(x[0]):x for x in ideals}
    equipment_lists=[x for kind,x in objects if kind=='OS:ZONEHVAC:EQUIPMENTLIST'];connections=[x for kind,x in objects if kind=='OS:CONNECTION']
    for name,(zone_name,_,_) in TARGETS.items():
        space=spaces_by_name.get(name);zone=zones.get(zone_name)
        lists=[x for x in equipment_lists if zone and osm_handle(x[2])==osm_handle(zone[0])]
        if not space or not zone or osm_handle(space[10])!=osm_handle(zone[0]) or len(lists)!=1 or osm_handle(zone[19]) not in thermo_by_handle:errors.append(f'result.osm:space_zone_thermostat_chain:{name}');continue
        ideal=ideal_by_handle.get(osm_handle(lists[0][4]))
        if not ideal or ideal[1]!=name+' IDEAL LOADS':errors.append(f'result.osm:zone_ideal_equipment_chain:{name}');continue
        for connection_handle in (ideal[3],ideal[4]):
            if not any(osm_handle(x[0])==osm_handle(connection_handle) and osm_handle(ideal[0]) in {osm_handle(x[1]),osm_handle(x[3])} for x in connections):errors.append(f'result.osm:ideal_node_connection_dangling:{name}')
    days={osm_handle(x[0]):x for kind,x in objects if kind=='OS:SCHEDULE:DAY'}
    day_handles=[osm_handle(rulesets[n][3]) for n in ('MarketPublicSchedule','ServiceSupportSchedule') if n in rulesets]
    if len(day_handles)!=2 or len(set(day_handles))!=2:errors.append('result.osm:market_service_day_profiles_shared')
    for h in day_handles:
        day=days.get(h);values=[]
        if day:
            for i in range(6,len(day),3):
                try:values.append(float(day[i]))
                except Exception:pass
        if not day or not any(v>0 for v in values):errors.append('result.osm:schedule_day_has_no_nonzero_period')
    cold = first_number(flow.get('assumptions', {}), 'cold_chain_equipment_w_m2'); waste = first_number(flow.get('assumptions', {}), 'waste_people_m2')
    if cold is None or cold < 20 or waste is None or not (0 < waste < 0.05): errors.append('flow_report:market_use_assumptions_invalid')
    if not (first_number(flow,'window_wall_ratio') or 0) > 0: errors.append('flow_report:invalid_wwr')
    if len(find_values(flow,'schedule_set')[0] if find_values(flow,'schedule_set') else []) < 8: errors.append('flow_report:schedule_inventory_too_small')

    osw = load_json(paths['workflow.osw'])
    if osw.get('seed_file') != 'result.osm' or osw.get('weather_file') != 'weather.epw': errors.append('workflow.osw:binding_mismatch')
    transactions = flow.get('openstudio_cli_transactions', [])
    simtx = transactions[0] if isinstance(transactions, list) and len(transactions) == 1 and isinstance(transactions[0], dict) else {}
    if simtx.get('executable_sha256') != OPENSTUDIO_EXE_SHA256 or simtx.get('energyplus_executable_sha256') != ENERGYPLUS_EXE_SHA256 or simtx.get('exit_code') != 0:
        errors.append('flow_report:openstudio_transaction_identity_or_exit_mismatch')
    if simtx.get('arguments')!=['run','-w',r'C:\Users\user\Desktop\workflow.osw'] or simtx.get('working_directory')!=r'C:\Users\user\Desktop' or simtx.get('related_processes_after_wait')!=0 or simtx.get('result_osm_sha256')!=sha256_file(paths['result.osm']) or simtx.get('workflow_sha256')!=sha256_file(paths['workflow.osw']) or simtx.get('weather_sha256')!=sha256_file(paths['weather.epw']):errors.append('flow_report:openstudio_transaction_args_or_input_hash_mismatch')
    for name,key in (('run/eplusout.sql','sql_sha256'),('run/eplusout.err','err_sha256'),('run/eplusout.end','end_sha256')):
        if simtx.get(key) != sha256_file(paths[name]): errors.append(f'flow_report:openstudio_transaction_{key}_mismatch')
    samples = simtx.get('stable_file_samples', [])
    try:
        sim_times=[iso_time(simtx[x]) for x in ('started_at_utc','openstudio_process_exited_at_utc','completed_at_utc')]
        sample_times=[iso_time(x['sampled_at_utc']) for x in samples]
        if not(sim_times[0]<sim_times[1]<=sample_times[0]<sample_times[-1]<sim_times[2]) or sample_times!=sorted(sample_times) or len(set(sample_times))!=len(sample_times):raise ValueError
        for sample in samples:
            for short,path in (('sql',paths['run/eplusout.sql']),('err',paths['run/eplusout.err']),('end',paths['run/eplusout.end'])):
                if int(sample[f'{short}_size'])!=path.stat().st_size or sample[f'{short}_sha256']!=sha256_file(path):raise ValueError
                mt=iso_time(sample[f'{short}_mtime_utc'])
                if mt>iso_time(sample['sampled_at_utc']):raise ValueError
        for short in ('sql','err','end'):
            if len({x[f'{short}_mtime_utc'] for x in samples})!=1:raise ValueError
    except Exception:errors.append('flow_report:openstudio_transaction_time_or_stable_samples_invalid')
    err = read_text(paths['run/eplusout.err']); end = read_text(paths['run/eplusout.end'])
    forbidden_err=('CHKSBS','NO-OVERLAP','MISSES SUBSURFACE','BASE SURFACE DOES NOT SURROUND SUBSURFACE')
    if 'EnergyPlus Completed Successfully' not in err or '0 Severe Errors' not in err or 'EnergyPlus Completed Successfully' not in end or any(x in err.upper() for x in forbidden_err):
        errors.append('energyplus:unsuccessful_or_severe')
    try:
        conn=sqlite3.connect(str(paths['run/eplusout.sql']))
        simulation=conn.execute('select EnergyPlusVersion,Completed,CompletedSuccessfully from Simulations').fetchall()
        flags=tuple(str(x).upper() for x in simulation[0][1:]) if len(simulation)==1 else ()
        sql_severe=conn.execute('select coalesce(sum(Count),0) from Errors where ErrorType>=1').fetchone()[0]
        false_false_evidence=(flags==('FALSE','FALSE') and sql_severe==0 and 'EnergyPlus Completed Successfully' in err and '0 Severe Errors' in err and 'EnergyPlus Completed Successfully' in end and simtx.get('sql_sha256')==sha256_file(paths['run/eplusout.sql']))
        if conn.execute('pragma integrity_check').fetchone()[0] != 'ok' or len(simulation)!=1 or '25.1.0' not in str(simulation[0][0]) or not(flags==('TRUE','TRUE') or false_false_evidence): errors.append('eplusout.sql:integrity_simulation_version_or_flags')
        hourly=flow.get('simulation',{}).get('hourly_series',[])
        variables=('Zone Lights Electricity Energy','Zone Electric Equipment Electricity Energy','Zone Ideal Loads Zone Total Heating Energy','Zone Ideal Loads Zone Total Cooling Energy','Zone Ideal Loads Zone Total Heating Rate','Zone Ideal Loads Zone Total Cooling Rate')
        expected={(name,var):((name+' IDEAL LOADS') if 'Ideal Loads' in var else zone) for name,(zone,_,_) in TARGETS.items() for var in variables}
        triples=[(x.get('space_name'),x.get('variable'),x.get('key_value')) for x in hourly]
        if len(hourly)!=18 or len(set(triples))!=18 or {(a,b):c for a,b,c in triples}!=expected:errors.append('flow_report:hourly_series_exact_set_mismatch')
        by={(x.get('space_name'),x.get('variable')):x for x in hourly}
        sql_data={}
        for pair,key in expected.items():
            row=conn.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0",(key,pair[1])).fetchone()
            q=(int(row[0]),int(row[1]),float(row[2] or 0),float(row[3] or 0));sql_data[pair]=q
            reported=by.get(pair,{})
            if q[:2]!=(8760,8760) or int(reported.get('count',0))!=q[0] or int(reported.get('unique_time_count',0))!=q[1] or abs(float(reported.get('sum',math.inf))-q[2])>max(1e-6,abs(q[2])*1e-12) or abs(float(reported.get('max',math.inf))-q[3])>max(1e-6,abs(q[3])*1e-12):errors.append(f'eplusout.sql:hourly_series_mismatch:{pair[0]}:{pair[1]}')
        with paths['model_summary.csv'].open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        if len(rows)!=3 or {(x.get('space_name'),x.get('thermal_zone')) for x in rows}!={(n,z) for n,(z,_,_) in TARGETS.items()}:errors.append('model_summary.csv:exact_space_zone_pair_mismatch')
        for row in rows:
            n=row['space_name']; energy=sum(sql_data[(n,v)][2] for v in variables[:4])/3.6e6;peak=max(sql_data[(n,v)][3] for v in variables[4:])
            if abs(float(row['energy_use_kwh'])-energy)>1e-6 or abs(float(row['peak_load_w'])-peak)>1e-6: errors.append(f'model_summary.csv:sql_recompute_mismatch:{n}')
        conn.close()
    except Exception as exc: errors.append(f'eplusout.sql:deep_validation_failed:{type(exc).__name__}')


def check_instruction_semantics(paths: Dict[str, Path], handoff: Dict[str, Any], flow: Dict[str, Any], errors: List[str]) -> None:
    """Validate task semantics without assuming the reference GUIDs, areas, or openings."""
    if sha256_file(paths["init.ifc"]) != INIT_SHA256:
        errors.append("init.ifc:sha256_mismatch")
    try:
        weather_lines = read_text(paths["weather.epw"]).splitlines()
        if len(weather_lines) < 8768 or not weather_lines[0].upper().startswith("LOCATION,"):
            errors.append("weather.epw:invalid_epw")
    except Exception:
        errors.append("weather.epw:invalid_epw")

    stage_spaces: Dict[str, Any] = {}
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.util.element  # type: ignore

        seed = ifcopenshell.open(str(paths["init.ifc"]))
        stage = ifcopenshell.open(str(paths["stage1.ifc"]))
        seed_roots = {str(x.GlobalId): x for x in seed.by_type("IfcRoot") if getattr(x, "GlobalId", None)}
        stage_roots = {str(x.GlobalId): x for x in stage.by_type("IfcRoot") if getattr(x, "GlobalId", None)}
        if not set(seed_roots).issubset(stage_roots):
            errors.append("stage1.ifc:seed_root_removed")

        for name, zone in zip(CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"]):
            matches = [x for x in stage.by_type("IfcSpace") if norm(x.Name) == norm(name)]
            if len(matches) != 1:
                errors.append(f"stage1.ifc:required_space_binding_mismatch:{name}")
                continue
            space = matches[0]
            stage_spaces[name] = space
            if norm(zone) not in norm(space.LongName):
                errors.append(f"stage1.ifc:space_zone_semantics_mismatch:{name}")
            qtos = ifcopenshell.util.element.get_psets(space, qtos_only=True)
            area = qtos.get("Qto_SpaceBaseQuantities", {}).get("NetFloorArea")
            if area is not None and float(area) <= 0:
                errors.append(f"stage1.ifc:space_area_nonpositive:{name}")

        market = stage_spaces.get("MARKET-HALL")
        if market is not None and str(market.GlobalId) in seed_roots:
            before = seed_roots[str(market.GlobalId)]

            def spatial_signature(entity: Any) -> Any:
                def clean(value: Any) -> Any:
                    if isinstance(value, dict):
                        return tuple(sorted((k, clean(v)) for k, v in value.items() if k not in {"id", "Name", "LongName", "Description"}))
                    if isinstance(value, (tuple, list)):
                        return tuple(clean(v) for v in value)
                    return value
                return clean({
                    "ObjectPlacement": getattr(entity, "ObjectPlacement", None).get_info(recursive=True) if getattr(entity, "ObjectPlacement", None) else None,
                    "Representation": getattr(entity, "Representation", None).get_info(recursive=True) if getattr(entity, "Representation", None) else None,
                })

            if spatial_signature(before) != spatial_signature(market):
                errors.append("stage1.ifc:market_hall_envelope_changed")
    except Exception as exc:
        errors.append(f"stage1.ifc:semantic_parse_failed:{type(exc).__name__}")

    records = {str(x.get("name") or x.get("space_name")): x for x in extract_space_records(handoff, errors, "handoff.json")}
    for name, zone in zip(CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"]):
        rec = records.get(name, {})
        native = stage_spaces.get(name)
        if not rec or norm(rec.get("thermal_zone")) != norm(zone):
            errors.append(f"handoff.json:space_zone_binding_mismatch:{name}")
        if native is not None and rec.get("ifc_global_id") != str(native.GlobalId):
            errors.append(f"handoff.json:space_global_id_not_from_stage1:{name}")
        try:
            if float(rec.get("floor_area_m2", 0)) <= 0:
                raise ValueError
        except Exception:
            errors.append(f"handoff.json:space_area_nonpositive:{name}")
    if handoff.get("source_init_sha256") not in (None, sha256_file(paths["init.ifc"])):
        errors.append("handoff.json:source_init_sha256_mismatch")

    log = load_json(paths["native_stage_log.json"])
    process = log.get("command_server_process", {})
    executable = str(process.get("executable_path", "")).replace("\\", "/").lower()
    if "archicad 27" not in executable or not str(process.get("product_version", "")).startswith("27"):
        errors.append("native_stage_log.json:archicad_identity_mismatch")
    artifacts = log.get("artifacts", {})
    for name in ("init.ifc", "stage1.ifc", "handoff.json"):
        if artifacts.get(name, {}).get("sha256") != sha256_file(paths[name]):
            errors.append(f"native_stage_log.json:artifact_hash_mismatch:{name}")
    tx_section = log.get("native_transactions", {})
    transactions = tx_section.get("Items", []) if isinstance(tx_section, dict) else tx_section
    if not isinstance(transactions, list) or len(transactions) < 3:
        errors.append("native_stage_log.json:transactions_missing")
    else:
        methods = [x.get("request", {}).get("method") for x in transactions]
        if methods[0] != "Model.LoadFile" or methods[-1] != "Model.SaveFile":
            errors.append("native_stage_log.json:load_save_order_mismatch")
        if any(x.get("status") != 200 or not isinstance(x.get("response"), dict) or x["response"].get("error") for x in transactions):
            errors.append("native_stage_log.json:transaction_failure")
        if any(token not in json.dumps(transactions, ensure_ascii=False) for token in CASE_SPEC["required_spaces"]):
            errors.append("native_stage_log.json:required_space_transaction_missing")

    osm = read_text(paths["result.osm"])
    objects = osm_objects(osm)
    spaces = {x[1]: x for kind, x in objects if kind == "OS:SPACE" and len(x) > 10}
    zones = {x[1]: x for kind, x in objects if kind == "OS:THERMALZONE" and len(x) > 1}
    for name, zone_name in zip(CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"]):
        space, zone = spaces.get(name), zones.get(zone_name)
        if space is None or zone is None or osm_handle(space[10]) != osm_handle(zone[0]):
            errors.append(f"result.osm:space_zone_relationship_mismatch:{name}")
    schedules = {osm_handle(x[0]) for kind, x in objects if kind.startswith("OS:SCHEDULE") and x}
    definitions = {
        kind: {osm_handle(x[0]) for current, x in objects if current == kind and x}
        for kind in ("OS:PEOPLE:DEFINITION", "OS:LIGHTS:DEFINITION", "OS:ELECTRICEQUIPMENT:DEFINITION")
    }
    space_handles = {name: osm_handle(x[0]) for name, x in spaces.items()}
    schedule_bindings: Dict[str, Set[str]] = {name: set() for name in CASE_SPEC["required_spaces"]}
    for kind in ("OS:PEOPLE", "OS:LIGHTS", "OS:ELECTRICEQUIPMENT"):
        instances = [x for current, x in objects if current == kind and len(x) > 4]
        for name in CASE_SPEC["required_spaces"]:
            matches = [x for x in instances if osm_handle(x[3]) == space_handles.get(name)]
            if (len(matches) != 1 or osm_handle(matches[0][2]) not in definitions[kind + ":DEFINITION"] or
                    osm_handle(matches[0][4]) not in schedules):
                errors.append(f"result.osm:load_chain_invalid:{kind}:{name}")
            else:
                schedule_bindings[name].add(osm_handle(matches[0][4]))
    if schedule_bindings.get("MARKET-HALL") == schedule_bindings.get("COLD-CHAIN") == schedule_bindings.get("WASTE-HOLDING"):
        errors.append("result.osm:public_and_service_schedules_not_distinct")
    if len([1 for kind, _ in objects if kind == "OS:THERMOSTATSETPOINT:DUALSETPOINT"]) < len(CASE_SPEC["required_zones"]):
        errors.append("result.osm:thermostat_count_too_low")
    if len([1 for kind, _ in objects if kind == "OS:ZONEHVAC:IDEALLOADSAIRSYSTEM"]) < len(CASE_SPEC["required_zones"]):
        errors.append("result.osm:ideal_loads_count_too_low")

    osw = load_json(paths["workflow.osw"])
    if Path(str(osw.get("seed_file", ""))).name != "result.osm" or Path(str(osw.get("weather_file", ""))).name != "weather.epw":
        errors.append("workflow.osw:binding_mismatch")
    cli_transactions = flow.get("openstudio_cli_transactions", [])
    simtx = cli_transactions[0] if isinstance(cli_transactions, list) and len(cli_transactions) == 1 and isinstance(cli_transactions[0], dict) else {}
    if simtx.get("exit_code") != 0 or "openstudio" not in str(simtx.get("executable", "")).lower():
        errors.append("flow_report:openstudio_transaction_invalid")
    for filename, key in (("run/eplusout.sql", "sql_sha256"), ("run/eplusout.err", "err_sha256"), ("run/eplusout.end", "end_sha256")):
        if simtx.get(key) != sha256_file(paths[filename]):
            errors.append(f"flow_report:openstudio_transaction_{key}_mismatch")
    err_text, end_text = read_text(paths["run/eplusout.err"]), read_text(paths["run/eplusout.end"])
    if "EnergyPlus Completed Successfully" not in err_text or "0 Severe Errors" not in err_text or "EnergyPlus Completed Successfully" not in end_text:
        errors.append("energyplus:unsuccessful_or_severe")
    try:
        conn = sqlite3.connect(f"file:{paths['run/eplusout.sql']}?mode=ro", uri=True)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        simulations = conn.execute("SELECT COUNT(*) FROM Simulations").fetchone()[0]
        severe = conn.execute("SELECT COUNT(*) FROM Errors WHERE ErrorType >= 1").fetchone()[0]
        conn.close()
        if integrity != "ok" or simulations != 1 or severe != 0:
            errors.append("eplusout.sql:integrity_or_simulation_failure")
    except Exception as exc:
        errors.append(f"eplusout.sql:parse_failed:{type(exc).__name__}")


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
    flow_tokens = ["weather_file", "schedule_set", "construction_set"]
    osm_counts = check_osm(paths["result.osm"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], flow_tokens, errors)
    flow_data = check_flow_report(paths["flow_report.json"], handoff, paths["result.osm"], handoff_data, osm_counts, stage1_info, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
    check_model_summary_csv(paths["model_summary.csv"], handoff_hash, sha256_file(stage1), handoff_data, flow_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors)
    check_instruction_semantics(paths, handoff_data, flow_data, errors)

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
