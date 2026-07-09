# EngiWorld multi-software instruction-rule evaluator.
# This evaluator checks instruction-derived rules and does not compare against reference answer artifacts.
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

CASE_SPEC = {
  "case_id": "multi-cli-3-revit-archicad-openstudio-task-01-windows",
  "mode": "three_stage",
  "software_chain": [
    "revit",
    "archicad",
    "openstudio"
  ],
  "required_files": [
    "init.ifc",
    "stage1.ifc",
    "revit_handoff.json",
    "stage2.ifc",
    "archicad_handoff.json",
    "archicad_validation_report.json",
    "result.osm",
    "in.idf",
    "flow_report.json",
    "model_summary.csv",
    "energy_report.csv"
  ],
  "required_spaces": [
    "COMMUNITY-ACTIVITY",
    "QUIET-COUNSELLING"
  ],
  "required_zones": [
    "COMMUNITY-ACTIVITY-ZN",
    "QUIET-COUNSELLING-ZN"
  ],
  "stage1_tokens": [
    "EW3B01",
    "COMMUNITY-ACTIVITY",
    "QUIET-COUNSELLING",
    "EAST-ROOM-ADDED",
    "multi-cli-3-revit-archicad-openstudio-task-01-windows"
  ],
  "stage2_tokens": [
    "ARCHICAD-QA-PASS",
    "EXTERIOR-BOUNDARY-CLASSIFIED",
    "COMMUNITY-ACTIVITY",
    "QUIET-COUNSELLING",
    "multi-cli-3-revit-archicad-openstudio-task-01-windows"
  ],
  "handoff_tokens": [
    "ACTIVITY-SCHEDULE",
    "COUNSELLING-SCHEDULE",
    "SEPARATE-THERMOSTAT",
    "LOW-COUNSELLING-OCCUPANCY"
  ],
  "osm_tokens": [
    "ActivityRoomSchedule",
    "CounsellingRoomSchedule",
    "SeparateThermostatMetadata",
    "QUIET-COUNSELLING-ZN"
  ],
  "summary_tokens": [
    "COMMUNITY-ACTIVITY",
    "QUIET-COUNSELLING"
  ],
  "min_windows": 2,
  "min_doors": 2,
  "min_roofs": 1,
  "min_storeys": 1,
  "expected_stage": "revit",
  "expected_archicad_stage": "archicad"
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


def scalar_value(data: Dict[str, Any], key: str) -> str | None:
    for val in find_values(data, key):
        if isinstance(val, (str, int, float)) and str(val).strip():
            return str(val).strip()
    return None


def numeric_from_any(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).strip())
    except Exception:
        return None


def row_value(row: Dict[str, Any], key: str) -> Any:
    for k, v in row.items():
        if norm(k) == norm(key):
            return v
    return None


def row_has_any_key(row: Dict[str, Any], keys: Iterable[str]) -> bool:
    row_keys = {norm(k) for k in row.keys()}
    return any(norm(k) in row_keys for k in keys)


def structured_rows(data: Dict[str, Any], keys: Iterable[str]) -> List[Dict[str, Any]]:
    for key in keys:
        for val in find_values(data, key):
            if isinstance(val, list) and any(isinstance(item, dict) for item in val):
                return [item for item in val if isinstance(item, dict)]
    return []


def require_metadata_tokens(container: Any, metadata: Dict[str, str], errors: List[str], label: str) -> None:
    for key, value in metadata.items():
        if not value or not contains_token(container, value):
            errors.append(f"{label}:missing_metadata:{key}")


def collect_archicad_energy_model(data: Dict[str, Any], required_spaces: List[str], required_zones: List[str], errors: List[str]) -> Dict[str, Any]:
    metadata: Dict[str, str] = {}
    for key in ("weather_file", "schedule_set", "construction_set"):
        val = scalar_value(data, key)
        if not val:
            errors.append(f"archicad_handoff.json:missing_{key}")
        else:
            metadata[key] = val

    building_area = numeric_from_any(scalar_value(data, "building_area_m2"))
    if building_area is None or building_area <= 0:
        errors.append("archicad_handoff.json:invalid_building_area_m2")

    rows = structured_rows(data, ("spaces", "rooms", "ifc_spaces"))
    if not rows:
        errors.append("archicad_handoff.json:missing_structured_space_rows")
        return {"building_area_m2": building_area, "space_area_m2": None, "metadata": metadata}

    total_area = 0.0
    for space in required_spaces:
        matches = [row for row in rows if contains_token(row, space)]
        if not matches:
            errors.append(f"archicad_handoff.json:missing_space_row:{space}")
            continue
        row = matches[0]
        area = numeric_from_any(row_value(row, "area_m2"))
        if area is None or area <= 0:
            errors.append(f"archicad_handoff.json:invalid_space_area_m2:{space}")
        else:
            total_area += area
        zone_val = row_value(row, "thermal_zone")
        if not zone_val or not any(contains_token(zone_val, zone) for zone in required_zones):
            errors.append(f"archicad_handoff.json:space_missing_thermal_zone:{space}")
        if not row_has_any_key(row, ("storey", "level", "building_storey")):
            errors.append(f"archicad_handoff.json:space_missing_storey:{space}")

    zone_rows = structured_rows(data, ("thermal_zones", "zones", "zone_names"))
    if not zone_rows:
        errors.append("archicad_handoff.json:missing_structured_zone_rows")
    for zone in required_zones:
        matches = [row for row in zone_rows if contains_token(row, zone)]
        if not matches:
            errors.append(f"archicad_handoff.json:missing_zone_row:{zone}")
            continue
        area = numeric_from_any(row_value(matches[0], "area_m2"))
        if area is None or area <= 0:
            errors.append(f"archicad_handoff.json:invalid_zone_area_m2:{zone}")

    if building_area and total_area and abs(building_area - total_area) > max(1.0, building_area * 0.05):
        errors.append("archicad_handoff.json:building_area_not_sum_of_spaces")
    return {"building_area_m2": building_area, "space_area_m2": total_area or None, "metadata": metadata}


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


def check_stage2_derives_from_stage1(stage1_path: Path, stage2_path: Path, stage1_info: Dict[str, Any], stage2_info: Dict[str, Any], errors: List[str]) -> None:
    if sha256_file(stage1_path) == sha256_file(stage2_path):
        errors.append("stage2.ifc:byte_identical_to_stage1")
    stage2_text = read_text(stage2_path)
    if sha256_file(stage1_path)[:12].upper() not in stage2_text.upper():
        errors.append("stage2.ifc:missing_stage1_hash_prefix")
    ratio = stage2_path.stat().st_size / max(stage1_path.stat().st_size, 1)
    if ratio < 0.08 or ratio > 80:
        errors.append(f"stage2.ifc:size_ratio_implausible:{ratio:.3f}")
    stage1_counts = stage1_info["counts"]
    stage2_counts = stage2_info["counts"]
    for cls in ("IfcProject", "IfcBuilding", "IfcBuildingStorey", "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow", "IfcSpace"):
        base = stage1_counts.get(cls, 0)
        if base <= 0:
            continue
        min_allowed = max(1, math.floor(base * 0.50))
        if stage2_counts.get(cls, 0) < min_allowed:
            errors.append(f"stage2.ifc:baseline_count_drop:{cls}:{stage2_counts.get(cls, 0)}<{min_allowed}")


def check_software_stage(data: Dict[str, Any], expected: str, errors: List[str], label: str) -> None:
    values: List[Any] = []
    for key in ("software_stage", "stage", "authoring_software", "software", "source_software", "tool"):
        values.extend(find_values(data, key))
    if not values:
        errors.append(f"{label}:missing_software_stage")
        return
    if not any(expected.lower() in str(v).lower() for v in values):
        errors.append(f"{label}:software_stage_not_{expected}")


def check_handoff(
    path: Path,
    source_file: Path,
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    errors: List[str],
    label: str,
    expected_stage: str | None = None,
    extra_hashes: Dict[str, Path] | None = None,
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
    for key, upstream in (extra_hashes or {}).items():
        if not any_hash_field(data, key, sha256_file(upstream)):
            errors.append(f"{label}:{key}_mismatch")
    return data


def check_validation_report(path: Path, stage1: Path, stage2: Path, required_spaces: List[str], required_tokens: List[str], errors: List[str]) -> Dict[str, Any]:
    data = load_json(path)
    if not any_hash_field(data, "source_sha256", sha256_file(stage1)):
        errors.append("archicad_validation_report:source_sha256_mismatch")
    if not any_hash_field(data, "output_sha256", sha256_file(stage2)):
        errors.append("archicad_validation_report:output_sha256_mismatch")
    check_software_stage(data, CASE_SPEC.get("expected_archicad_stage", "archicad"), errors, "archicad_validation_report")
    if not has_any_key_like(data, ("entity_counts", "counts", "ifc_counts")):
        errors.append("archicad_validation_report:missing_entity_counts")
    if not has_any_key_like(data, ("spaces", "space_names", "rooms")):
        errors.append("archicad_validation_report:missing_space_section")
    require_tokens(data, required_spaces, errors, "archicad_validation_report:spaces")
    require_tokens(data, required_tokens, errors, "archicad_validation_report:qa_tokens")
    blocking = find_values(data, "blocking_errors") + find_values(data, "errors")
    for item in blocking:
        if isinstance(item, list) and item:
            errors.append("archicad_validation_report:blocking_errors")
        if isinstance(item, str) and item.strip() and item.strip().lower() not in {"none", "[]", "0", "ok", "pass", "passed"}:
            errors.append("archicad_validation_report:blocking_errors")
    return data


def check_osm(
    path: Path,
    handoff_hash: str,
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    errors: List[str],
    stage2_hash: str | None = None,
    metadata: Dict[str, str] | None = None,
) -> None:
    if path.stat().st_size < 1000:
        errors.append("result.osm:too_small")
    text = read_text(path)
    up = text.upper()
    if "OS:VERSION" not in up:
        errors.append("result.osm:no_os_version")
    require_tokens(text, required_spaces, errors, "result.osm:spaces")
    require_tokens(text, required_zones, errors, "result.osm:zones")
    require_tokens(text, required_tokens, errors, "result.osm:tokens")
    if handoff_hash[:12].upper() not in up:
        errors.append("result.osm:missing_handoff_hash_prefix")
    if stage2_hash and stage2_hash[:12].upper() not in up:
        errors.append("result.osm:missing_stage2_hash_prefix")
    require_metadata_tokens(text, metadata or {}, errors, "result.osm")
    space_count = len(re.findall(r"\bOS:SPACE\s*,", up))
    zone_count = len(re.findall(r"\bOS:THERMALZONE\s*,", up))
    if space_count < len(required_spaces):
        errors.append(f"result.osm:space_count_too_low:{space_count}<{len(required_spaces)}")
    if zone_count < len(required_zones):
        errors.append(f"result.osm:thermal_zone_count_too_low:{zone_count}<{len(required_zones)}")


def check_idf(
    path: Path,
    handoff_hash: str,
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    errors: List[str],
    stage2_hash: str | None = None,
    metadata: Dict[str, str] | None = None,
) -> None:
    if path.stat().st_size < 800:
        errors.append("in.idf:too_small")
    text = read_text(path)
    up = text.upper()
    if "VERSION," not in up or "BUILDING," not in up:
        errors.append("in.idf:not_energyplus_idf_like")
    require_tokens(text, required_spaces, errors, "in.idf:spaces")
    require_tokens(text, required_zones, errors, "in.idf:zones")
    require_tokens(text, required_tokens, errors, "in.idf:tokens")
    if handoff_hash[:12].upper() not in up:
        errors.append("in.idf:missing_handoff_hash_prefix")
    if stage2_hash and stage2_hash[:12].upper() not in up:
        errors.append("in.idf:missing_stage2_hash_prefix")
    require_metadata_tokens(text, metadata or {}, errors, "in.idf")
    zone_count = len(re.findall(r"\bZONE\s*,", up))
    surface_count = len(re.findall(r"\bBUILDINGSURFACE:DETAILED\s*,", up))
    if zone_count < len(required_zones):
        errors.append(f"in.idf:zone_count_too_low:{zone_count}<{len(required_zones)}")
    if surface_count < max(len(required_spaces), 2):
        errors.append(f"in.idf:surface_count_too_low:{surface_count}<{max(len(required_spaces), 2)}")


def numeric_value(row: Dict[str, str], key: str) -> float | None:
    for k, v in row.items():
        if norm(k) == norm(key):
            try:
                return float(str(v).strip())
            except Exception:
                return None
    return None


def check_energy_report_csv(
    path: Path,
    handoff_hash: str,
    required_spaces: List[str],
    required_zones: List[str],
    errors: List[str],
    stage2_hash: str | None = None,
    expected_area_m2: float | None = None,
    metadata: Dict[str, str] | None = None,
) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        errors.append("energy_report.csv:no_rows")
        return
    fields = {norm(x) for x in rows[0].keys()}
    for required_col in (
        "case_id",
        "building_area_m2",
        "space_count",
        "thermal_zone_count",
        "total_site_energy_kwh",
        "peak_load_kw",
        "eui_kwh_m2",
        "source_handoff_sha256",
        "source_stage2_sha256",
        "weather_file",
        "schedule_set",
        "construction_set",
    ):
        if norm(required_col) not in fields:
            errors.append(f"energy_report.csv:missing_column:{required_col}")
    text = json.dumps(rows, ensure_ascii=False)
    require_tokens(text, required_spaces, errors, "energy_report.csv:spaces")
    require_tokens(text, required_zones, errors, "energy_report.csv:zones")
    require_metadata_tokens(text, metadata or {}, errors, "energy_report.csv")
    row = rows[0]
    row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
    if row_case and row_case != CASE_SPEC["case_id"]:
        errors.append("energy_report.csv:case_id_mismatch")
    hash_val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_handoff_sha256")), "")
    if hash_val != handoff_hash.lower():
        errors.append("energy_report.csv:source_handoff_sha256_mismatch")
    if stage2_hash:
        stage2_val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_stage2_sha256")), "")
        if stage2_val != stage2_hash.lower():
            errors.append("energy_report.csv:source_stage2_sha256_mismatch")
    area = numeric_value(row, "building_area_m2")
    space_count = numeric_value(row, "space_count")
    zone_count = numeric_value(row, "thermal_zone_count")
    total = numeric_value(row, "total_site_energy_kwh")
    peak = numeric_value(row, "peak_load_kw")
    eui = numeric_value(row, "eui_kwh_m2")
    if area is None or area <= 0:
        errors.append("energy_report.csv:invalid_building_area_m2")
    if expected_area_m2 and area and abs(area - expected_area_m2) > max(1.0, expected_area_m2 * 0.05):
        errors.append("energy_report.csv:building_area_mismatch_with_handoff")
    if space_count is None or int(round(space_count)) != len(required_spaces):
        errors.append("energy_report.csv:space_count_mismatch")
    if zone_count is None or int(round(zone_count)) != len(required_zones):
        errors.append("energy_report.csv:thermal_zone_count_mismatch")
    if total is None or total <= 0:
        errors.append("energy_report.csv:invalid_total_site_energy_kwh")
    if peak is None or peak <= 0:
        errors.append("energy_report.csv:invalid_peak_load_kw")
    if area and total and eui:
        expected = total / area
        if abs(eui - expected) > max(0.5, expected * 0.05):
            errors.append("energy_report.csv:eui_inconsistent_with_total_and_area")


def check_flow_report(
    path: Path,
    handoff_path: Path,
    osm_path: Path,
    required_spaces: List[str],
    required_zones: List[str],
    errors: List[str],
    idf_path: Path | None = None,
    energy_report_path: Path | None = None,
    stage2_path: Path | None = None,
    metadata: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    data = load_json(path)
    if not any_hash_field(data, "consumed_handoff_sha256", sha256_file(handoff_path)):
        errors.append("flow_report:consumed_handoff_sha256_mismatch")
    if not any_hash_field(data, "osm_sha256", sha256_file(osm_path)):
        errors.append("flow_report:osm_sha256_mismatch")
    if idf_path and not any_hash_field(data, "idf_sha256", sha256_file(idf_path)):
        errors.append("flow_report:idf_sha256_mismatch")
    if energy_report_path and not any_hash_field(data, "energy_report_sha256", sha256_file(energy_report_path)):
        errors.append("flow_report:energy_report_sha256_mismatch")
    if stage2_path and not any_hash_field(data, "stage2_sha256", sha256_file(stage2_path)):
        errors.append("flow_report:stage2_sha256_mismatch")
    require_tokens(data, required_spaces, errors, "flow_report:spaces")
    require_tokens(data, required_zones, errors, "flow_report:zones")
    require_tokens(data, CASE_SPEC["software_chain"], errors, "flow_report:software_chain")
    require_metadata_tokens(data, metadata or {}, errors, "flow_report")
    if not has_any_key_like(data, ("software_chain", "stage_sequence", "stages")):
        errors.append("flow_report:missing_stage_sequence")
    if not find_values(data, "openstudio_version") and not contains_token(data, "OpenStudio"):
        errors.append("flow_report:missing_openstudio_version")
    return data


def check_model_summary_csv(
    path: Path,
    handoff_hash: str,
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    errors: List[str],
    stage2_hash: str | None = None,
    expected_area_m2: float | None = None,
    metadata: Dict[str, str] | None = None,
) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < max(len(required_spaces), 1):
        errors.append(f"model_summary.csv:row_count_too_low:{len(rows)}")
        return
    fields = {norm(x) for x in (rows[0].keys() if rows else [])}
    for required_col in (
        "case_id",
        "space_name",
        "thermal_zone",
        "source_handoff_sha256",
        "source_stage2_sha256",
        "area_m2",
        "weather_file",
        "schedule_set",
        "construction_set",
    ):
        if norm(required_col) not in fields:
            errors.append(f"model_summary.csv:missing_column:{required_col}")
    text = json.dumps(rows, ensure_ascii=False)
    require_tokens(text, required_spaces, errors, "model_summary.csv:spaces")
    require_tokens(text, required_zones, errors, "model_summary.csv:zones")
    require_tokens(text, required_tokens, errors, "model_summary.csv:tokens")
    require_metadata_tokens(text, metadata or {}, errors, "model_summary.csv")
    total_area = 0.0
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case and row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
            break
        val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_handoff_sha256")), "")
        if val and val != handoff_hash.lower():
            errors.append("model_summary.csv:source_handoff_sha256_mismatch")
            break
        if stage2_hash:
            stage2_val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_stage2_sha256")), "")
            if stage2_val and stage2_val != stage2_hash.lower():
                errors.append("model_summary.csv:source_stage2_sha256_mismatch")
                break
        area = numeric_value(row, "area_m2")
        if area is None or area <= 0:
            errors.append("model_summary.csv:invalid_area_m2")
            break
        total_area += area
    if expected_area_m2 and total_area and abs(total_area - expected_area_m2) > max(1.0, expected_area_m2 * 0.05):
        errors.append("model_summary.csv:area_sum_mismatch_with_handoff")


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

    if CASE_SPEC["mode"] == "two_stage":
        handoff = paths["handoff.json"]
        check_handoff(
            handoff,
            stage1,
            CASE_SPEC["required_spaces"],
            CASE_SPEC["required_zones"],
            CASE_SPEC["handoff_tokens"],
            errors,
            "handoff.json",
            expected_stage=CASE_SPEC.get("expected_stage"),
        )
        handoff_hash = sha256_file(handoff)
        check_osm(paths["result.osm"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], errors)
        check_idf(paths["in.idf"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], errors)
        check_flow_report(paths["flow_report.json"], handoff, paths["result.osm"], CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors, idf_path=paths.get("in.idf"), energy_report_path=paths.get("energy_report.csv"))
        check_model_summary_csv(paths["model_summary.csv"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors)
        check_energy_report_csv(paths["energy_report.csv"], handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
    else:
        revit_handoff = paths["revit_handoff.json"]
        revit_handoff_data = check_handoff(
            revit_handoff,
            stage1,
            CASE_SPEC["required_spaces"],
            [],
            [],
            errors,
            "revit_handoff.json",
            expected_stage=CASE_SPEC.get("expected_stage"),
        )
        if not any_hash_field(revit_handoff_data, "input_seed_sha256", sha256_file(init_path)):
            errors.append("revit_handoff.json:input_seed_sha256_mismatch")
        stage2 = paths["stage2.ifc"]
        stage2_min_counts = dict(stage1_min_counts)
        stage2_info = check_ifc_basic(stage2, CASE_SPEC["stage2_tokens"], stage2_min_counts, errors, "stage2.ifc")
        check_stage2_derives_from_stage1(stage1, stage2, stage1_info, stage2_info, errors)
        check_validation_report(paths["archicad_validation_report.json"], stage1, stage2, CASE_SPEC["required_spaces"], CASE_SPEC["stage2_tokens"], errors)
        archicad_handoff = paths["archicad_handoff.json"]
        archicad_handoff_data = check_handoff(
            archicad_handoff,
            stage2,
            CASE_SPEC["required_spaces"],
            CASE_SPEC["required_zones"],
            CASE_SPEC["handoff_tokens"],
            errors,
            "archicad_handoff.json",
            expected_stage=CASE_SPEC.get("expected_archicad_stage"),
            extra_hashes={"revit_handoff_sha256": revit_handoff},
        )
        if not any_hash_field(archicad_handoff_data, "stage1_sha256", sha256_file(stage1)):
            errors.append("archicad_handoff.json:stage1_sha256_mismatch")
        archicad_model = collect_archicad_energy_model(archicad_handoff_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
        archicad_handoff_hash = sha256_file(archicad_handoff)
        stage2_hash = sha256_file(stage2)
        metadata = archicad_model.get("metadata", {})
        expected_area = archicad_model.get("building_area_m2")
        check_osm(paths["result.osm"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], errors, stage2_hash=stage2_hash, metadata=metadata)
        check_idf(paths["in.idf"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], errors, stage2_hash=stage2_hash, metadata=metadata)
        check_flow_report(paths["flow_report.json"], archicad_handoff, paths["result.osm"], CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors, idf_path=paths["in.idf"], energy_report_path=paths["energy_report.csv"], stage2_path=stage2, metadata=metadata)
        check_model_summary_csv(paths["model_summary.csv"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors, stage2_hash=stage2_hash, expected_area_m2=expected_area, metadata=metadata)
        check_energy_report_csv(paths["energy_report.csv"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors, stage2_hash=stage2_hash, expected_area_m2=expected_area, metadata=metadata)

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

