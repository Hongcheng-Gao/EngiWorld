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

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-08-windows',
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
 'required_spaces': ['RECEPTION', 'ACCESSIBLE-SUITE', 'HOUSEKEEPING-CLOSET'],
 'required_zones': ['RECEPTION-ZN', 'ACCESSIBLE-SUITE-ZN', 'HOUSEKEEPING-CLOSET-ZN'],
 'stage1_tokens': ['EW2A08','RECEPTION','ACCESSIBLE-SUITE','HOUSEKEEPING-CLOSET'],
 'handoff_tokens': [],
 'osm_tokens': [],
 'summary_tokens': ['RECEPTION','ACCESSIBLE-SUITE','HOUSEKEEPING-CLOSET'],
 'min_windows': 0,
 'min_doors': 0,
 'min_roofs': 0,
 'min_storeys': 1,
 'expected_stage': 'archicad'}

INIT_SHA256 = 'f3530866386efeb0c3857e3a47a87d1b65b8cd0a3bd04ef1d77f950c64a459c3'
ARCHICAD_EXE_SHA256 = '594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775'
OPENSTUDIO_EXE_SHA256 = '46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361'
ENERGYPLUS_EXE_SHA256 = '3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5'
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
    # Native Windows/.NET DateTimeOffset evidence commonly carries seven
    # fractional-second digits. Python datetime is microsecond based, so trim
    # only unsupported tail precision before applying the strict time checks.
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


def check_epw(path: Path, errors: List[str]) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", errors="strict") as f:
            header = [next(f).rstrip("\r\n") for _ in range(8)]
            data = [line.rstrip("\r\n") for line in f if line.strip()]
        location = next(csv.reader([header[0]]))
        if len(location) < 10 or location[0].strip().upper() != "LOCATION":
            raise ValueError("location")
        for value in location[6:10]:
            float(value)
        if len(data) < 8760:
            raise ValueError("annual_records")
        for line in (data[0], data[-1]):
            fields = next(csv.reader([line]))
            if len(fields) < 35:
                raise ValueError("field_count")
            int(fields[0]); int(fields[1]); int(fields[2]); int(fields[3]); int(fields[4])
    except Exception:
        errors.append("weather.epw:invalid_epw_structure")


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

    room_count = first_number(data, "room_count")
    zone_count = first_number(data, "thermal_zone_count")
    if room_count is not None and int(round(room_count)) != osm_counts["space_count"]:
        errors.append("flow_report:room_count_mismatch_osm")
    if zone_count is not None and int(round(zone_count)) != osm_counts["zone_count"]:
        errors.append("flow_report:thermal_zone_count_mismatch_osm")
    if first_number(data, "surface_count") is not None and int(first_number(data, "surface_count") or 0) != osm_counts["surface_count"]:
        errors.append("flow_report:surface_count_mismatch_osm")
    if first_number(data, "subsurface_count") is not None and int(first_number(data, "subsurface_count") or 0) != osm_counts["subsurface_count"]:
        errors.append("flow_report:subsurface_count_mismatch_osm")
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


def check_ew08_native_and_simulation(root: Path, paths: Dict[str, Path], handoff: Dict[str, Any], flow: Dict[str, Any], errors: List[str]) -> None:
    if sha256_file(paths['init.ifc']) != INIT_SHA256:
        errors.append('init.ifc:sha256_mismatch')
    check_epw(paths['weather.epw'], errors)

    records = handoff.get('spaces', [])
    record_by_name = {str(x.get('name')): x for x in records if isinstance(x, dict)}
    targets = {}
    for name, zone in zip(CASE_SPEC['required_spaces'], CASE_SPEC['required_zones']):
        rec = record_by_name.get(name, {})
        try:
            gid = str(rec['ifc_global_id']); area = float(rec['floor_area_m2'])
            if rec.get('thermal_zone') != zone or not gid or area <= 0: raise ValueError
            targets[name] = (zone, area, gid)
        except Exception:
            errors.append(f'handoff.json:invalid_required_space_binding:{name}')

    try:
        import ifcopenshell  # type: ignore
        seed = ifcopenshell.open(str(paths['init.ifc'])); stage = ifcopenshell.open(str(paths['stage1.ifc']))
        seed_roots = {x.GlobalId for x in seed.by_type('IfcRoot')}; stage_roots = {x.GlobalId for x in stage.by_type('IfcRoot')}
        if seed_roots - stage_roots: errors.append('stage1.ifc:seed_root_removed')
        if len([x for x in stage.by_type('IfcSpace') if x.Name == 'RECEPTION']) != 1:
            errors.append('stage1.ifc:reception_not_unique')
        for name, (zone, area, gid) in targets.items():
            x = stage.by_guid(gid)
            if x is None or not x.is_a('IfcSpace') or x.Name != name or x.LongName != zone:
                errors.append(f'stage1.ifc:target_space_mismatch:{name}')
            quantities = ifcopenshell.util.element.get_psets(x, qtos_only=True) if x else {}
            actual = quantities.get('Qto_SpaceBaseQuantities', {}).get('NetFloorArea')
            if actual is None or abs(float(actual) - area) > 1e-6:
                errors.append(f'stage1.ifc:target_area_mismatch:{name}')
        doors=list(stage.by_type('IfcDoor')); windows=list(stage.by_type('IfcWindow'))
        if any(float(getattr(x,'OverallHeight',0) or 0)<=0 or float(getattr(x,'OverallWidth',0) or 0)<=0 for x in doors+windows):
            errors.append('stage1.ifc:opening_dimensions_nonpositive')
        contained={x.GlobalId for rel in stage.by_type('IfcRelContainedInSpatialStructure') for x in rel.RelatedElements}
        if any(x.GlobalId not in contained for x in doors+windows): errors.append('stage1.ifc:opening_not_spatially_contained')
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
        protected = {
            str(x.GlobalId) for x in seed.by_type('IfcRoof')
        } | {
            str(x.GlobalId) for x in seed.by_type('IfcSpace') if norm(x.Name) in {norm('COURT'), norm('COURTYARD')}
        }
        target_ids = {x[2] for x in targets.values()}
        if protected & target_ids:
            errors.append('stage1.ifc:protected_courtyard_or_roof_used_as_target')
        mutable=target_ids|{x.GlobalId for x in seed.by_type('IfcProject')}|{x.GlobalId for x in seed.by_type('IfcRelContainedInSpatialStructure')}
        for gid in seed_roots-mutable:
            if root_canon(seed.by_guid(gid))!=root_canon(stage.by_guid(gid)):errors.append(f'stage1.ifc:unexpected_recursive_root_change:{gid}')
    except Exception as exc:
        errors.append(f'stage1.ifc:deep_parse_failed:{type(exc).__name__}')

    log = load_json(paths['native_stage_log.json'])
    proc = log.get('command_server_process', {})
    proc_exe = str(proc.get('executable_path', '')).replace('\\', '/').lower()
    if 'archicad 27' not in proc_exe or not str(proc.get('product_version', '')).startswith('27'):
        errors.append('native_stage_log.json:archicad_identity_mismatch')
    tx = log.get('native_transactions', {}).get('Items', [])
    methods = [x.get('request', {}).get('method') for x in tx]
    if not methods or methods[0]!='Model.LoadFile' or methods[-1]!='Model.SaveFile' or any(x.get('status') != 200 or not isinstance(x.get('response'), dict) or x['response'].get('error') for x in tx):
        errors.append('native_stage_log.json:transaction_sequence_or_response_mismatch')
    try:
        if tx[0]['request']['params']!={'location':r'C:\Users\user\Desktop\init.ifc'} or tx[-1]['request']['params']!={'location':r'C:\Users\user\Desktop\stage1.ifc'}:raise ValueError
        modified={(p.get('EntityData',{}).get('IfcSpace',{}).get('Name'),p.get('EntityData',{}).get('IfcSpace',{}).get('LongName'),p.get('select',{}).get('IfcSpace',{}).get('GlobalId')) for p in (x['request'].get('params',{}) for x in tx if x['request'].get('method')=='Entity.Modify')}
        for name,(zone,_,gid) in targets.items():
            if (name,zone,gid) not in modified and not any(getattr(x,'Name',None)==name and getattr(x,'LongName',None)==zone for x in seed.by_type('IfcSpace')):raise ValueError
        if not any('EW2A08' in json.dumps(x['request']) for x in tx):raise ValueError
        if any(x['response'].get('jsonrpc')!='2.0' for x in tx):raise ValueError
    except Exception:errors.append('native_stage_log.json:params_results_binding_mismatch')
    if log.get('artifacts', {}).get('stage1.ifc', {}).get('sha256') != sha256_file(paths['stage1.ifc']):
        errors.append('native_stage_log.json:stage1_hash_mismatch')
    if handoff.get('source_init_sha256') != INIT_SHA256:errors.append('handoff.json:source_init_mismatch')
    try:
        if sum(int(x['door_count']) for x in records)!=int(handoff['door_count']) or sum(int(x['window_count']) for x in records)!=int(handoff['window_count']):raise ValueError
    except Exception:errors.append('handoff.json:opening_counts_inconsistent')

    osm = read_text(paths['result.osm'])
    required_objects = {'OS:SPACE':3,'OS:THERMALZONE':3,'OS:DESIGNSPECIFICATION:OUTDOORAIR':3,'OS:THERMOSTATSETPOINT:DUALSETPOINT':3,'OS:ZONEHVAC:IDEALLOADSAIRSYSTEM':3}
    for obj, count in required_objects.items():
        actual = len(re.findall(r'(?im)^\s*'+re.escape(obj)+r'\s*,', osm))
        if actual < count: errors.append(f'result.osm:object_count:{obj}:{actual}<{count}')
    objects=osm_objects(osm); surfaces={osm_handle(x[0]):x for kind,x in objects if kind=='OS:SURFACE'}
    subs={x[1]:x for kind,x in objects if kind=='OS:SUBSURFACE'}
    try:
        reported_doors = int(flow.get('door_count', 0))
        reported_windows = int(flow.get('window_count', 0))
    except (TypeError, ValueError):
        reported_doors = reported_windows = -1
    actual_doors=sum(1 for x in subs.values() if 'DOOR' in x[2].upper());actual_windows=sum(1 for x in subs.values() if 'WINDOW' in x[2].upper())
    if (reported_doors,reported_windows)!=(actual_doors,actual_windows):errors.append('flow_report:opening_counts_mismatch_osm')
    space_names={osm_handle(x[0]):x[1] for kind,x in objects if kind=='OS:SPACE'}
    for name,sub in subs.items():
        try:
            parent=surfaces[osm_handle(sub[4])]
            if space_names.get(osm_handle(parent[4])) not in space_names.values():errors.append(f'result.osm:subsurface_parent_space_mismatch:{name}')
            parent_pts=osm_vertices(parent,11);child_pts=osm_vertices(sub,10)
            if not strict_contains_3d(parent_pts,child_pts):errors.append(f'result.osm:subsurface_not_coplanar_strictly_inside:{name}')
        except Exception:errors.append(f'result.osm:subsurface_geometry_parse_failed:{name}')
    spaces_by_name={x[1]:x for kind,x in objects if kind=='OS:SPACE'};spaces_by_handle={osm_handle(x[0]):x for x in spaces_by_name.values()}
    zones={x[1]:x for kind,x in objects if kind=='OS:THERMALZONE'}
    zone_names_by_handle={osm_handle(x[0]):x[1] for x in zones.values()}
    exported={name:zone_names_by_handle.get(osm_handle(space[10])) for name,space in spaces_by_name.items() if zone_names_by_handle.get(osm_handle(space[10]))}
    if len(exported)!=len(spaces_by_name):errors.append('result.osm:space_without_valid_thermal_zone')
    if set(exported.values())!=set(zones):errors.append('result.osm:orphan_thermal_zone')
    if not set(targets).issubset(exported):errors.append('result.osm:required_spaces_not_exported')
    actual_areas={}
    for name,space in spaces_by_name.items():
        floors=[x for kind,x in objects if kind=='OS:SURFACE' and x[2].upper()=='FLOOR' and osm_handle(x[4])==osm_handle(space[0])]
        actual_areas[name]=sum(polygon_area_3d(osm_vertices(x,11)) for x in floors)
    exported_area=sum(actual_areas.get(name,0) for name in exported)
    flow_area=first_number(flow,'building_area_m2')
    if flow_area is None or abs(flow_area-exported_area)>max(0.5,exported_area*0.03):errors.append('flow_report:area_mismatch_osm')
    for name,(_,area,_) in targets.items():
        if abs(actual_areas.get(name,0)-area)>1e-6:errors.append(f'result.osm:floor_area_mismatch:{name}')
    definitions={kind:{osm_handle(x[0]):x for k,x in objects if k==kind} for kind in ('OS:PEOPLE:DEFINITION','OS:LIGHTS:DEFINITION','OS:ELECTRICEQUIPMENT:DEFINITION')}
    schedules={osm_handle(x[0]):x for kind,x in objects if kind.startswith('OS:SCHEDULE:')};loads=[]
    for kind in ('OS:PEOPLE','OS:LIGHTS','OS:ELECTRICEQUIPMENT'):
        for k,x in objects:
            if k==kind:loads.append((kind,x))
    by_space={n:[] for n in exported}
    for kind,x in loads:
        space=spaces_by_handle.get(osm_handle(x[3]));definition=definitions[kind+':DEFINITION'].get(osm_handle(x[2]));schedule=schedules.get(osm_handle(x[4]))
        if not space or not definition or not schedule:errors.append(f'result.osm:load_chain_dangling:{x[1]}')
        elif space[1] in by_space:by_space[space[1]].append((kind,definition,schedule))
    if any(not by_space[n] for n in exported):errors.append('result.osm:space_has_no_scheduled_load')
    rulesets={x[1]:x for kind,x in objects if kind=='OS:SCHEDULE:RULESET'}
    if len(rulesets)<2:errors.append('result.osm:insufficient_schedule_profiles')
    schedule_values={osm_handle(x[0]):x for kind,x in objects if kind in ('OS:SCHEDULE:CONSTANT','OS:SCHEDULE:RULESET')}
    thermostats=[x for kind,x in objects if kind=='OS:THERMOSTATSETPOINT:DUALSETPOINT']
    if len(thermostats)<len(exported) or any(osm_handle(x[2]) not in schedule_values or osm_handle(x[3]) not in schedule_values for x in thermostats):errors.append('result.osm:thermostat_chain_or_deadband_invalid')
    ideals=[x for kind,x in objects if kind=='OS:ZONEHVAC:IDEALLOADSAIRSYSTEM']
    if len(ideals)<len(exported):errors.append('result.osm:ideal_loads_set_mismatch')
    thermo_by_handle={osm_handle(x[0]):x for x in thermostats};ideal_by_handle={osm_handle(x[0]):x for x in ideals}
    equipment_lists=[x for kind,x in objects if kind=='OS:ZONEHVAC:EQUIPMENTLIST'];connections=[x for kind,x in objects if kind=='OS:CONNECTION']
    ideal_names_by_handle={osm_handle(x[0]):x[1] for x in ideals}
    for name,zone_name in exported.items():
        space=spaces_by_name.get(name);zone=zones.get(zone_name)
        lists=[x for x in equipment_lists if zone and osm_handle(x[2])==osm_handle(zone[0])]
        if not space or not zone or osm_handle(space[10])!=osm_handle(zone[0]) or len(lists)!=1 or osm_handle(zone[19]) not in thermo_by_handle:errors.append(f'result.osm:space_zone_thermostat_chain:{name}');continue
        ideal=ideal_by_handle.get(osm_handle(lists[0][4]))
        if not ideal:errors.append(f'result.osm:zone_ideal_equipment_chain:{name}');continue
        for connection_handle in (ideal[3],ideal[4]):
            if not any(osm_handle(x[0])==osm_handle(connection_handle) and osm_handle(ideal[0]) in {osm_handle(x[1]),osm_handle(x[3])} for x in connections):errors.append(f'result.osm:ideal_node_connection_dangling:{name}')
    days={osm_handle(x[0]):x for kind,x in objects if kind=='OS:SCHEDULE:DAY'}
    load_schedule_handles={osm_handle(s[0]) for values in by_space.values() for _,_,s in values}
    day_handles=[osm_handle(x[3]) for x in rulesets.values() if osm_handle(x[0]) in load_schedule_handles]
    if len(set(day_handles))<2:errors.append('result.osm:scheduled_uses_not_distinct')
    for h in day_handles:
        day=days.get(h);values=[]
        if day:
            for i in range(6,len(day),3):
                try:values.append(float(day[i]))
                except Exception:pass
        if not day or not any(v>0 for v in values):errors.append('result.osm:schedule_day_has_no_nonzero_period')
    schedule_inventory=find_values(flow,'schedule_set')[0] if find_values(flow,'schedule_set') else []
    if not isinstance(schedule_inventory,list) or len(schedule_inventory)<2:errors.append('flow_report:schedule_inventory_incomplete')

    osw = load_json(paths['workflow.osw'])
    if osw.get('seed_file') != 'result.osm' or osw.get('weather_file') != 'weather.epw': errors.append('workflow.osw:binding_mismatch')
    if flow.get('weather_sha256') != sha256_file(paths['weather.epw']):errors.append('flow_report:weather_hash_mismatch')
    cli_transactions = flow.get('openstudio_cli_transactions', [])
    simtx = cli_transactions[0] if isinstance(cli_transactions, list) and len(cli_transactions) == 1 and isinstance(cli_transactions[0], dict) else {}
    if 'openstudio-3.10.0' not in str(simtx.get('executable', '')).replace('\\', '/').lower() or simtx.get('exit_code') != 0:
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
        triples=[(x.get('space_name'),x.get('variable'),x.get('key_value')) for x in hourly]
        expected_pairs={(name,var) for name in exported for var in variables}
        expected={(a,b):c for a,b,c in triples if (a,b) in expected_pairs and isinstance(c,str) and c}
        if len(expected)!=len(expected_pairs) or set(expected)!=expected_pairs:errors.append('flow_report:hourly_series_exported_set_mismatch')
        by={(x.get('space_name'),x.get('variable')):x for x in hourly}
        sql_data={}
        for pair,key in expected.items():
            row=conn.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0",(key,pair[1])).fetchone()
            q=(int(row[0]),int(row[1]),float(row[2] or 0),float(row[3] or 0));sql_data[pair]=q
            reported=by.get(pair,{})
            if q[:2]!=(8760,8760) or int(reported.get('count',0))!=q[0] or int(reported.get('unique_time_count',0))!=q[1] or abs(float(reported.get('sum',math.inf))-q[2])>max(1e-6,abs(q[2])*1e-12) or abs(float(reported.get('max',math.inf))-q[3])>max(1e-6,abs(q[3])*1e-12):errors.append(f'eplusout.sql:hourly_series_mismatch:{pair[0]}:{pair[1]}')
        with paths['model_summary.csv'].open(newline='',encoding='utf-8') as f: rows=list(csv.DictReader(f))
        if {(x.get('space_name'),x.get('thermal_zone')) for x in rows}!=set(exported.items()):errors.append('model_summary.csv:space_zone_pair_mismatch')
        for row in rows:
            n=row['space_name']; energy=sum(sql_data[(n,v)][2] for v in variables[:4])/3.6e6;peak=max(sql_data[(n,v)][3] for v in variables[4:])
            if abs(float(row['energy_use_kwh'])-energy)>1e-6 or abs(float(row['peak_load_w'])-peak)>1e-6: errors.append(f'model_summary.csv:sql_recompute_mismatch:{n}')
        conn.close()
    except Exception as exc: errors.append(f'eplusout.sql:deep_validation_failed:{type(exc).__name__}')


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
    check_ew08_native_and_simulation(root, paths, handoff_data, flow_data, errors)

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
