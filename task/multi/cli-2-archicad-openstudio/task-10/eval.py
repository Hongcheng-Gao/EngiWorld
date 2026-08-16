# EngiWorld Archicad -> OpenStudio multi-software flow evaluator.
# This evaluator checks instruction-derived artifacts and never compares against ground_truth files.
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-10-windows',
 'mode': 'two_stage',
 'software_chain': ['archicad', 'openstudio'],
 'required_files': ['init.ifc',
                    'stage1.ifc',
                    'handoff.json',
                    'native_stage_log.json',
                    'result.osm',
                    'in.idf',
                    'workflow.osw',
                    'weather.epw',
                    'flow_report.json',
                    'model_summary.csv',
                    'run/eplusout.sql',
                    'run/eplusout.err',
                    'run/eplusout.end'],
 'required_spaces': ['CONSULT', 'EQUIPMENT', 'ISO-CONSULT', 'PPE-DONNING', 'CONTAMINATED-SUPPORT'],
 'required_zones': ['CONSULT-ZN', 'EQUIPMENT-ZN', 'ISO-CONSULT-ZN', 'PPE-DONNING-ZN', 'CONTAMINATED-SUPPORT-ZN'],
 'stage1_tokens': ['EW2A10',
                   'CONSULT',
                   'EQUIPMENT',
                   'ISO-CONSULT',
                   'PPE-DONNING',
                   'CONTAMINATED-SUPPORT',
                   'ISOLATION-FLOW',
                   'multi-cli-2-archicad-openstudio-task-10-windows'],
 'handoff_tokens': ['CLINICAL-VENTILATION',
                    'ISOLATION-CONSULT-SCHEDULE',
                    'PPE-SUPPORT',
                    'CONTAMINATED-SUPPORT-LOW-OCCUPANCY'],
 'osm_tokens': [],
 'summary_tokens': ['CONSULT', 'EQUIPMENT', 'ISO-CONSULT', 'PPE-DONNING', 'CONTAMINATED-SUPPORT'],
 'min_windows': 0,
 'min_doors': 0,
 'min_roofs': 0,
 'min_storeys': 1,
 'expected_stage': 'archicad'}

INIT_SHA256 = "e8b00cf9a09b02690b6650535bf91bdf8e7e67cd86d5eecf7f18a72b6a29ee24"
ARCHICAD_EXE = Path(r"C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe")
OPENSTUDIO_EXE = Path(r"C:\openstudio-3.10.0\bin\openstudio.exe")
ENERGYPLUS_EXE = Path(r"C:\openstudio-3.10.0\EnergyPlus\energyplus.exe")
DIRECT_ATTRIBUTE_EXCLUSIONS = {
    "GlobalId", "OwnerHistory", "ObjectPlacement", "Representation",
}

# Archicad 27 build 6000 rewrites this wall's local placement on a no-op IFC
# load/save while preserving its world-coordinate geometry. Fresh native replay
# below remains the trust anchor for the exact normalized value.
ARCHICAD_NATIVE_NORMALIZATION = {("18xuYo1rnE$AtOko_HTCB7", "ObjectPlacement")}

SEED_TARGET_POOLS = {
    "CONSULT": {"0p_GCOHqL9O8Orvi_YQmfp", "2donn1s$15fQstYK6K7bhA", "2wv7qlrLHECvQ$ovZhAZ6k"},
    "ISO-CONSULT": {"0p_GCOHqL9O8Orvi_YQmfp", "2donn1s$15fQstYK6K7bhA", "2wv7qlrLHECvQ$ovZhAZ6k"},
    "EQUIPMENT": {"38jEfacSPBCBtDO38Sa4ab"},
    "PPE-DONNING": {"3h$isFwRP5_hw8nERq6D$D"},
    "CONTAMINATED-SUPPORT": {"25gwD9sn52YxBd1q5pXbvc"},
}

SPACE_SEMANTICS = {
    "CONSULT": ("CONSULT-ZN", "CLINICAL-VENTILATION"),
    "EQUIPMENT": ("EQUIPMENT-ZN", "CLINICAL-VENTILATION"),
    "ISO-CONSULT": ("ISO-CONSULT-ZN", "ISOLATION-CONSULT-SCHEDULE"),
    "PPE-DONNING": ("PPE-DONNING-ZN", "PPE-SUPPORT"),
    "CONTAMINATED-SUPPORT": ("CONTAMINATED-SUPPORT-ZN", "CONTAMINATED-SUPPORT-LOW-OCCUPANCY"),
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
    text = str(value or "")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    # Windows/.NET DateTimeOffset emits seven fractional-second digits;
    # Python datetime supports microseconds. Trim only unsupported precision.
    text = re.sub(r"(\.\d{6})\d+(?=(?:[+-]\d{2}:\d{2})?$)", r"\1", text)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
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


def check_epw(path: Path, errors: List[str]) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", errors="strict") as stream:
            header = [next(stream).rstrip("\r\n") for _ in range(8)]
            records = [line.rstrip("\r\n") for line in stream if line.strip()]
        location = next(csv.reader([header[0]]))
        if len(location) < 10 or location[0].strip().upper() != "LOCATION" or len(records) < 8760:
            raise ValueError
        for value in location[6:10]:
            float(value)
        for line in (records[0], records[-1]):
            fields = next(csv.reader([line]))
            if len(fields) < 35:
                raise ValueError
            for value in fields[:5]:
                int(value)
    except Exception:
        errors.append("weather.epw:invalid_structure")


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


def authoritative_ifc_spaces(stage_path: Path, handoff: Dict[str, Any], errors: List[str]) -> Dict[str, Dict[str, Any]]:
    """Bind candidate-declared task records to seed-derived IFC properties."""
    result: Dict[str, Dict[str, Any]] = {}
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.util.element  # type: ignore
        model = ifcopenshell.open(str(stage_path))
        by_gid = {str(x.GlobalId): x for x in model.by_type("IfcSpace")}
        records = extract_space_records(handoff, errors, "handoff.json")
        for record in records:
            name = str(record.get("name") or record.get("space_name") or "")
            if name not in SEED_TARGET_POOLS:
                continue
            gid = str(record.get("ifc_global_id") or "")
            entity = by_gid.get(gid)
            if gid not in SEED_TARGET_POOLS[name] or entity is None or str(entity.Name) != name:
                errors.append(f"handoff.json:invalid_ifc_binding:{name}")
                continue
            psets = ifcopenshell.util.element.get_psets(entity)
            area = float(psets.get("Pset_EngiWorld", {}).get("Area"))
            if not math.isclose(float(record.get("floor_area_m2")), area, abs_tol=1e-6):
                errors.append(f"handoff.json:ifc_area_mismatch:{name}")
            long_name = str(getattr(entity, "LongName", None) or "")
            for token in SPACE_SEMANTICS[name]:
                if norm(token) not in norm(long_name): errors.append(f"stage1.ifc:semantic_token:{name}:{token}")
            result[name] = {"gid": gid, "area": area, "long_name": long_name, "record": record}
        if set(result) != set(SEED_TARGET_POOLS): errors.append("handoff.json:incomplete_ifc_bindings")
        if len({x["gid"] for x in result.values()}) != len(result): errors.append("handoff.json:duplicate_ifc_binding")
        ordered = sorted(result.items(), key=lambda item: int(item[1]["record"].get("flow_order", 0)))
        if [name for name, _ in ordered] != CASE_SPEC["required_spaces"]: errors.append("handoff.json:isolation_flow_order")
        for name, item in result.items():
            # This seed has no IfcRelSpaceBoundary or IfcOpeningElement, so no
            # door/window can be authoritatively assigned to an individual space.
            if int(item["record"].get("door_count", -1)) != 0: errors.append(f"handoff.json:door_attribution:{name}")
            if int(item["record"].get("window_count", -1)) != 0: errors.append(f"handoff.json:window_attribution:{name}")
    except Exception as exc:
        errors.append(f"stage1.ifc:authoritative_space_data:{type(exc).__name__}")
    return result


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
    if room_count is not None and int(round(room_count)) != osm_counts["space_count"]:
        errors.append("flow_report:room_count_mismatch_osm")
    if zone_count is not None and int(round(zone_count)) != osm_counts["zone_count"]:
        errors.append("flow_report:thermal_zone_count_mismatch_osm")
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
    result = []
    for raw in re.findall(r"(?ms)^OS:[A-Za-z0-9:]+\s*,.*?;", text):
        clean = re.sub(r"!-[^\r\n]*", "", raw)
        fields = [value.strip() for value in re.split(r"[,;]", clean)]
        result.append((fields[0].upper(), fields[1:]))
    return result


def handle(value: Any) -> str:
    return str(value or "").strip().strip("{}")


def canonical_direct_value(value: Any, active: Set[Tuple[str,int]] | None = None) -> Any:
    active = active or set()
    if isinstance(value, (tuple, list)):
        return tuple(canonical_direct_value(item, active) for item in value)
    if hasattr(value, "is_a") and callable(value.is_a):
        gid = getattr(value, "GlobalId", None)
        if gid:
            return ("IfcRoot", str(value.is_a()), str(gid))
        marker = (str(value.is_a()), int(value.id()))
        if marker in active:
            return ("IfcCycle", str(value.is_a()))
        active.add(marker)
        info = value.get_info(include_identifier=False, recursive=False)
        attributes = tuple(
            (str(key), canonical_direct_value(item, active))
            for key, item in info.items() if key != "type"
        )
        active.remove(marker)
        return ("IfcEntity", str(value.is_a()), attributes)
    if isinstance(value, float):
        return round(value, 12)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def canonical_direct_attributes(entity: Any) -> Dict[str, Any]:
    info = entity.get_info(include_identifier=False, recursive=False)
    return {
        str(key): canonical_direct_value(value)
        for key, value in info.items()
        if key != "type" and key not in DIRECT_ATTRIBUTE_EXCLUSIONS
    }


def canonical_owner_history(entity: Any) -> Any:
    return canonical_direct_value(getattr(entity,"OwnerHistory",None))


def product_host_graph(model: Any) -> Dict[str,Tuple[Tuple[str,str],...]]:
    graph: Dict[str,List[Tuple[str,str]]] = {}
    def add(gid: Any, edge: str, other: Any) -> None:
        if gid and other: graph.setdefault(str(gid),[]).append((edge,str(other)))
    for rel in model.by_type("IfcRelVoidsElement"):
        add(getattr(rel.RelatedOpeningElement,"GlobalId",None),"voids",getattr(rel.RelatingBuildingElement,"GlobalId",None))
    for rel in model.by_type("IfcRelFillsElement"):
        add(getattr(rel.RelatedBuildingElement,"GlobalId",None),"fills",getattr(rel.RelatingOpeningElement,"GlobalId",None))
    for rel in model.by_type("IfcRelContainedInSpatialStructure"):
        host=getattr(rel.RelatingStructure,"GlobalId",None)
        for item in rel.RelatedElements:add(getattr(item,"GlobalId",None),"contained_in",host)
    for rel in model.by_type("IfcRelAggregates"):
        host=getattr(rel.RelatingObject,"GlobalId",None)
        for item in rel.RelatedObjects:add(getattr(item,"GlobalId",None),"aggregated_by",host)
    return {gid:tuple(sorted(edges)) for gid,edges in graph.items()}


def product_representation_metadata(product: Any) -> Any:
    representation=getattr(product,"Representation",None)
    if representation is None:return None
    reps=[]
    for rep in getattr(representation,"Representations",()) or ():
        context=getattr(rep,"ContextOfItems",None)
        reps.append((str(getattr(rep,"RepresentationIdentifier",None)),str(getattr(rep,"RepresentationType",None)),canonical_direct_value(context)))
    return (str(getattr(representation,"Name",None)),str(getattr(representation,"Description",None)),tuple(reps))


def product_world_signature(model: Any, product: Any, hosts: Dict[str,Tuple[Tuple[str,str],...]]) -> Dict[str,Any]:
    import ifcopenshell.geom  # type: ignore
    import ifcopenshell.util.placement  # type: ignore
    placement=getattr(product,"ObjectPlacement",None)
    matrix=ifcopenshell.util.placement.get_local_placement(placement) if placement is not None else None
    placement_signature=None if matrix is None else tuple(round(float(x),9) for row in matrix for x in row)
    geometry=None
    if getattr(product,"Representation",None) is not None:
        settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
        shape=ifcopenshell.geom.create_shape(settings,product);raw=shape.geometry
        vertices=[tuple(float(raw.verts[i+j]) for j in range(3)) for i in range(0,len(raw.verts),3)]
        triangles=[tuple(int(raw.faces[i+j]) for j in range(3)) for i in range(0,len(raw.faces),3)]
        areas=[];signed_volume=0.0;planes: Dict[Tuple[float,...],Dict[str,Any]]={};edges: Dict[Tuple[int,int],int]={}
        for ia,ib,ic in triangles:
            a,b,c=vertices[ia],vertices[ib],vertices[ic]
            ux,uy,uz=(b[i]-a[i] for i in range(3));vx,vy,vz=(c[i]-a[i] for i in range(3))
            nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx;length=math.sqrt(nx*nx+ny*ny+nz*nz);area=length/2.0
            if length>1e-12:
                normal=[nx/length,ny/length,nz/length]
                for component in normal:
                    if abs(component)>1e-9:
                        if component<0:normal=[-x for x in normal]
                        break
                d=-sum(normal[i]*a[i] for i in range(3));key=tuple(round(x,7) for x in (*normal,d));group=planes.setdefault(key,{"area":0.0,"points":[]});group["area"]+=area;group["points"].extend((a,b,c))
            areas.append(area);signed_volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6.0
            for left,right in ((ia,ib),(ib,ic),(ic,ia)):
                edge=tuple(sorted((left,right)));edges[edge]=edges.get(edge,0)+1
        flat=[coordinate for vertex in vertices for coordinate in vertex]
        bbox=tuple(round(value,7) for axis in range(3) for value in (min(v[axis] for v in vertices),max(v[axis] for v in vertices))) if vertices else ()
        faces=[]
        for key,group in planes.items():
            points=group["points"];face_bbox=tuple(round(value,7) for axis in range(3) for value in (min(v[axis] for v in points),max(v[axis] for v in points)))
            faces.append((key,round(group["area"],7),face_bbox))
        geometry=(bbox,round(sum(areas),7),round(abs(signed_volume),7),bool(edges) and all(count==2 for count in edges.values()),tuple(sorted(faces)))
    gid=str(product.GlobalId)
    return {"type":str(product.is_a()),"placement":placement_signature,"representation":product_representation_metadata(product),"geometry":geometry,"hosts":hosts.get(gid,())}


def model_product_signatures(model: Any) -> Dict[str,Dict[str,Any]]:
    hosts=product_host_graph(model)
    return {str(product.GlobalId):product_world_signature(model,product,hosts) for product in model.by_type("IfcProduct")}


def product_equivalence_signature(signature: Dict[str,Any]) -> Dict[str,Any]:
    return {key:value for key,value in signature.items() if key != "placement"}


def parse_labeled_objects(path: Path) -> List[Dict[str, Any]]:
    objects: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    for line_number, line in enumerate(read_text(path).splitlines(), 1):
        if current is None:
            match = re.match(r"^\s*([A-Za-z][A-Za-z0-9:]*)\s*,\s*$", line)
            if match:
                current = {"type": match.group(1).upper(), "fields": [], "line": line_number}
            continue
        value_part, _, comment = line.partition("!-")
        value = value_part.strip().rstrip(",;").strip()
        label = comment.strip() if comment else ""
        current["fields"].append({"value": value, "label": label})
        if ";" in value_part:
            objects.append(current)
            current = None
    return objects


def labeled(obj: Dict[str, Any], wanted: str) -> str | None:
    wanted_norm = norm(wanted)
    for field in obj.get("fields", []):
        if norm(re.sub(r"\s*\{[^}]*\}\s*$", "", str(field.get("label", "")))) == wanted_norm:
            return str(field.get("value", "")).strip()
    return None


def vertices(obj: Dict[str, Any], errors: List[str], label: str) -> List[Tuple[float, float, float]]:
    result: List[Tuple[float, float, float]] = []
    for field in obj.get("fields", []):
        if re.match(r"X,Y,Z Vertex \d+", str(field.get("label", "")), flags=re.IGNORECASE):
            try:
                xyz = tuple(float(x.strip()) for x in str(field.get("value", "")).split(","))
                if len(xyz) != 3 or not all(math.isfinite(x) for x in xyz): raise ValueError
                result.append(xyz)  # type: ignore[arg-type]
            except Exception: errors.append(f"{label}:invalid_vertex")
    return result


def polygon_area(points: List[Tuple[float, float, float]]) -> float:
    if len(points) < 3: return 0.0
    nx = ny = nz = 0.0
    for a, b in zip(points, points[1:] + points[:1]):
        nx += (a[1] - b[1]) * (a[2] + b[2]); ny += (a[2] - b[2]) * (a[0] + b[0]); nz += (a[0] - b[0]) * (a[1] + b[1])
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def canonical_shell(objects: List[Dict[str, Any]], owner_field: str, errors: List[str], label: str) -> Dict[str, Tuple[Any, ...]]:
    shells: Dict[str, List[Any]] = {}
    edges: Dict[str, Dict[Any, int]] = {}
    for obj in objects:
        if obj["type"] not in ("OS:SURFACE", "BUILDINGSURFACE:DETAILED"): continue
        owner = labeled(obj, owner_field) or ""
        pts = vertices(obj, errors, label)
        if not owner or len(pts) < 3 or polygon_area(pts) <= 1e-6:
            errors.append(f"{label}:invalid_surface")
            continue
        stype = norm(labeled(obj, "Surface Type")); stype = "ROOF" if stype in ("ROOFCEILING", "CEILING") else stype
        rounded = [tuple(round(x, 6) for x in p) for p in pts]
        shells.setdefault(owner, []).append((stype, tuple(sorted(rounded))))
        owner_edges = edges.setdefault(owner, {})
        for a, b in zip(rounded, rounded[1:] + rounded[:1]):
            edge = tuple(sorted((a, b))); owner_edges[edge] = owner_edges.get(edge, 0) + 1
    for owner, counts in edges.items():
        if any(value != 2 for value in counts.values()): errors.append(f"{label}:shell_not_closed:{owner}")
    return {owner:tuple(sorted(values)) for owner,values in shells.items()}


def floor_areas(objects: List[Dict[str, Any]], owner_field: str) -> Dict[str,float]:
    result: Dict[str,float] = {}
    for obj in objects:
        if obj["type"] not in ("OS:SURFACE","BUILDINGSURFACE:DETAILED") or norm(labeled(obj,"Surface Type")) != "FLOOR": continue
        owner=labeled(obj,owner_field) or ""; result[owner]=result.get(owner,0.0)+polygon_area(vertices(obj,[],"area"))
    return result


def check_geometry_and_handles(paths: Dict[str, Path], errors: List[str]) -> None:
    osm = parse_labeled_objects(paths["result.osm"]); idf = parse_labeled_objects(paths["in.idf"])
    handles: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(r"^\{[0-9a-fA-F-]{36}\}$")
    for obj in osm:
        value = labeled(obj, "Handle")
        normalized = handle(value)
        if not value or not pattern.fullmatch(value) or normalized in handles: errors.append(f"result.osm:invalid_or_duplicate_handle:{obj['line']}")
        else: handles[normalized] = obj
    osm_spaces = {labeled(x,"Name"):x for x in osm if x["type"]=="OS:SPACE"}
    idf_spaces = {labeled(x,"Name"):x for x in idf if x["type"]=="SPACE"}
    if set(osm_spaces) != set(CASE_SPEC["required_spaces"]) or set(idf_spaces) != set(osm_spaces): errors.append("openstudio_idf:space_set")
    osm_shells = canonical_shell(osm,"Space Name",errors,"result.osm")
    osm_floor_areas=floor_areas(osm,"Space Name")
    named_osm_shells = {name:osm_shells.get(labeled(space,"Handle") or "",()) for name,space in osm_spaces.items()}
    idf_shells = canonical_shell(idf,"Space Name",errors,"in.idf")
    for name in CASE_SPEC["required_spaces"]:
        shell = named_osm_shells.get(name,()); translated = idf_shells.get(name,())
        types = {x[0] for x in shell}
        if not {"FLOOR","WALL","ROOF"}.issubset(types) or len(shell) < 6: errors.append(f"result.osm:incomplete_shell:{name}")
        if shell != translated: errors.append(f"openstudio_idf:surface_geometry_mismatch:{name}")
        floor_area = osm_floor_areas.get(labeled(osm_spaces[name],"Handle") or "",0.0)
        if floor_area <= 1.0: errors.append(f"result.osm:floor_area_invalid:{name}")
    if len(set(named_osm_shells.values())) != len(named_osm_shells): errors.append("result.osm:overlapping_duplicate_shell")


def canonical_forward_translate(paths: Dict[str, Path], errors: List[str]) -> Path | None:
    if os.name != "nt" or not OPENSTUDIO_EXE.is_file(): return None
    temp = Path(tempfile.mkdtemp(prefix="ew10-ft-"))
    script = temp / "forward.rb"; output = temp / "in.idf"
    script.write_text("require 'openstudio'\nm=OpenStudio::Model::Model.load(OpenStudio::Path.new(ARGV[0])).get\nw=OpenStudio::EnergyPlus::ForwardTranslator.new.translateModel(m)\nraise unless w.save(ARGV[1],true)\n")
    proc = subprocess.run([str(OPENSTUDIO_EXE),str(script),str(paths["result.osm"]),str(output)],capture_output=True,text=True,timeout=120)
    if proc.returncode or not output.is_file(): errors.append("openstudio_forward_translation:failed"); shutil.rmtree(temp,ignore_errors=True); return None
    if sha256_file(output) != sha256_file(paths["in.idf"]): errors.append("in.idf:not_canonical_forward_translation")
    return temp


def sql_signature(path: Path, spaces: Dict[str, str], errors: List[str], label: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"series":{}}
    try:
        con=sqlite3.connect(str(path));
        if con.execute("pragma integrity_check").fetchone()[0]!="ok": raise ValueError
        simulation=con.execute("select EnergyPlusVersion,Completed,CompletedSuccessfully from Simulations").fetchall()
        if len(simulation)!=1 or "25.1.0" not in str(simulation[0][0]) or tuple(str(x).upper() for x in simulation[0][1:]) not in (("TRUE","TRUE"),("FALSE","FALSE")): raise ValueError
        result["version"]=str(simulation[0][0]); result["flags"]=tuple(str(x).upper() for x in simulation[0][1:]); result["zones"]={str(x[0]).upper() for x in con.execute("select ZoneName from Zones")}
        result["errors"]=tuple(con.execute("select ErrorType,ErrorMessage,Count from Errors order by ErrorIndex").fetchall())
        variables=("Zone Lights Electricity Energy","Zone Electric Equipment Electricity Energy","Zone Ideal Loads Zone Total Heating Energy","Zone Ideal Loads Zone Total Cooling Energy","Zone Ideal Loads Zone Total Heating Rate","Zone Ideal Loads Zone Total Cooling Rate")
        for space,zone in spaces.items():
            for variable in variables:
                key=space+" IDEAL LOADS" if "Ideal Loads" in variable else zone
                row=con.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND COALESCE(t.WarmupFlag,0)=0",(key,variable)).fetchone()
                values=(int(row[0]),int(row[1]),float(row[2] or 0),float(row[3] or 0)); result["series"][(space,variable)]=values
                if values[:2]!=(8760,8760): errors.append(f"{label}:annual_series:{space}:{variable}")
                samples=con.execute("SELECT t.EnvironmentPeriodIndex,t.Month,t.Day,t.Hour,t.Minute,t.Interval,rd.Value FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND COALESCE(t.WarmupFlag,0)=0 ORDER BY t.EnvironmentPeriodIndex,t.Month,t.Day,t.Hour,t.Minute,t.Interval,rd.TimeIndex",(key,variable)).fetchall()
                digest=hashlib.sha256();
                for sample in samples:
                    coordinates=":".join(str(int(value)) for value in sample[:-1])
                    digest.update(f"{coordinates}:{float(sample[-1]).hex()}\n".encode("ascii"))
                result.setdefault("series_hashes",{})[(space,variable)]=digest.hexdigest()
        con.close()
    except Exception as exc: errors.append(f"{label}:invalid:{type(exc).__name__}")
    return result


def rerun_energyplus(paths: Dict[str, Path], submitted: Dict[str, Any], spaces: Dict[str,str], errors: List[str]) -> None:
    if os.name != "nt" or not OPENSTUDIO_EXE.is_file(): return
    temp=Path(tempfile.mkdtemp(prefix="ew10-openstudio-",dir="C:\\"))
    try:
        shutil.copy2(paths["result.osm"],temp/"result.osm")
        shutil.copy2(paths["weather.epw"],temp/"weather.epw")
        shutil.copy2(paths["workflow.osw"],temp/"workflow.osw")
        proc=subprocess.run([str(OPENSTUDIO_EXE),"run","-w",str(temp/"workflow.osw")],cwd=str(temp),capture_output=True,text=True,timeout=300)
        if proc.returncode: errors.append(f"energyplus_rerun:exit:{proc.returncode}"); return
        replay_idf=temp/"run"/"pre-preprocess.idf"
        if not replay_idf.is_file() or sha256_file(replay_idf) != sha256_file(paths["in.idf"]):
            errors.append("energyplus_rerun:canonical_idf_mismatch")
        err=read_text(temp/"run"/"eplusout.err")
        if "EnergyPlus Completed Successfully" not in err or "0 Severe Errors" not in err: errors.append("energyplus_rerun:unsuccessful")
        fresh=sql_signature(temp/"run"/"eplusout.sql",spaces,errors,"energyplus_rerun.sql")
        if submitted.get("version","").split(", YMD=")[0] != fresh.get("version","").split(", YMD=")[0]: errors.append("energyplus_rerun:version_mismatch")
        if submitted.get("flags") != fresh.get("flags"): errors.append("energyplus_rerun:completion_flags_mismatch")
        if submitted.get("errors") != fresh.get("errors"): errors.append("energyplus_rerun:errors_table_mismatch")
        if submitted.get("zones") != fresh.get("zones"): errors.append("energyplus_rerun:zone_set_mismatch")
        for key,value in submitted.get("series",{}).items():
            other=fresh.get("series",{}).get(key)
            if not other or value[:2]!=other[:2] or any(not math.isclose(value[i],other[i],rel_tol=1e-7,abs_tol=1e-4) for i in (2,3)): errors.append(f"energyplus_rerun:series_mismatch:{key[0]}:{key[1]}")
            if submitted.get("series_hashes",{}).get(key) != fresh.get("series_hashes",{}).get(key): errors.append(f"energyplus_rerun:hourly_hash_mismatch:{key[0]}:{key[1]}")
    finally: shutil.rmtree(temp,ignore_errors=True)


def rerun_archicad_stage(paths: Dict[str, Path], errors: List[str]) -> None:
    if os.name != "nt" or not ARCHICAD_EXE.is_file(): return
    temp = Path(tempfile.mkdtemp(prefix="ew10-ac-rerun-", dir="C:\\"))
    fresh_stage = temp / "stage1.ifc"; fresh_handoff = temp / "handoff.json"; fresh_log = temp / "native_stage_log.json"
    database = temp / "database"; transactions: List[Dict[str, Any]] = []; proc: subprocess.Popen[Any] | None = None
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = int(sock.getsockname()[1]); sock.close()

    def rpc(method: str, params: Dict[str, Any]) -> Any:
        request = {"method": method, "params": params}; raw = json.dumps(request, separators=(",", ":"))
        started = datetime.now().astimezone().isoformat()
        call = urllib.request.Request(f"http://127.0.0.1:{port}/JEMI", data=raw.encode(), headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(call, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8-sig")); status = int(response.status)
        completed = datetime.now().astimezone().isoformat()
        transactions.append({"request":request,"request_json":raw,"status":status,"response":body,"started_at_utc":started,"completed_at_utc":completed})
        if status != 200 or body.get("error"): raise RuntimeError(f"JEMI {method} failed")
        return body.get("result")

    try:
        import ifcopenshell  # type: ignore
        proc = subprocess.Popen([str(ARCHICAD_EXE),"--p",str(port),"--m","EW10-EVAL-RERUN","--d",str(database),"--sa","new_ifc4"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if proc.poll() is not None: raise RuntimeError("IFC command server exited")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/HEALTH",timeout=1) as response:
                    if response.status == 200: break
            except Exception: time.sleep(0.2)
        else: raise TimeoutError("IFC command server health timeout")

        handoff=load_json(paths["handoff.json"])
        declared=authoritative_ifc_spaces(paths["stage1.ifc"],handoff,errors)
        if set(declared) != set(SEED_TARGET_POOLS): raise ValueError("invalid declarations")
        seed=ifcopenshell.open(str(paths["init.ifc"])); seed_roots={x.GlobalId:x for x in seed.by_type("IfcRoot")}
        rpc("Model.LoadFile", {"location":str(paths["init.ifc"])})
        changes = []
        for name in CASE_SPEC["required_spaces"]:
            item=declared[name]; gid=item["gid"]; before=seed_roots[gid]
            changes.append(("IfcSpace",gid,{"Name":str(before.Name)},{"Name":name,"LongName":item["long_name"]}))
        project=next(x for x in ifcopenshell.open(str(paths["stage1.ifc"])).by_type("IfcProject"))
        project_update={}
        if getattr(project,"Description",None): project_update["Description"]=str(project.Description)
        if project_update:
            seed_project=next(x for x in seed.by_type("IfcProject"))
            changes.append(("IfcProject",str(seed_project.GlobalId),{"Name":str(seed_project.Name)},project_update))
        for cls,gid,selector,update in changes:
            selection={"GlobalId":gid,**selector}; result=rpc("Entity.Modify",{"select":{cls:selection},"EntityData":{cls:update}})
            if not result: raise RuntimeError("empty modify result")
        rpc("Model.SaveFile", {"location":str(fresh_stage)})
        if not fresh_stage.is_file(): raise RuntimeError("fresh stage missing")

        import ifcopenshell.geom  # type: ignore
        candidate=ifcopenshell.open(str(paths["stage1.ifc"])); fresh=ifcopenshell.open(str(fresh_stage))
        candidate_roots={x.GlobalId:x for x in candidate.by_type("IfcRoot")}; fresh_roots={x.GlobalId:x for x in fresh.by_type("IfcRoot")}
        mismatch=set(candidate_roots) != set(fresh_roots)
        task_space_names = {item["gid"]:name for name,item in declared.items()}
        project_gid=str(project.GlobalId); allowed_gids=set(task_space_names)|{project_gid}
        allowed_fresh_differences: Dict[str,Set[str]] = {}
        for gid in set(candidate_roots) & set(fresh_roots):
            left,right=candidate_roots[gid],fresh_roots[gid]
            permitted = allowed_fresh_differences.get(gid,set())
            left_attrs=canonical_direct_attributes(left); right_attrs=canonical_direct_attributes(right)
            if set(left_attrs) != set(right_attrs) or any(a not in permitted and left_attrs[a] != right_attrs[a] for a in set(left_attrs) & set(right_attrs)): mismatch=True
            if canonical_owner_history(left) != canonical_owner_history(right): mismatch=True
        for gid,name in task_space_names.items():
            if gid not in candidate_roots or str(candidate_roots[gid].Name) != name: mismatch=True
        for gid in set(candidate_roots) & set(seed_roots):
            for attr in ("Name","LongName","Description","ObjectType"):
                if str(getattr(candidate_roots[gid],attr,None)) != str(getattr(seed_roots[gid],attr,None)) and gid not in allowed_gids: mismatch=True
        candidate_products=model_product_signatures(candidate);fresh_products=model_product_signatures(fresh)
        if set(candidate_products) != set(fresh_products) or any(product_equivalence_signature(candidate_products[gid]) != product_equivalence_signature(fresh_products[gid]) for gid in set(candidate_products) & set(fresh_products)): mismatch=True

        fresh_handoff.write_text(json.dumps({"source_init_sha256":sha256_file(paths["init.ifc"]),"fresh_stage_sha256":sha256_file(fresh_stage),"root_ids":sorted(fresh_roots),"changed_global_ids":[x[1] for x in changes]},indent=2),encoding="utf-8")
        fresh_log.write_text(json.dumps({"executable_sha256":sha256_file(ARCHICAD_EXE),"port":port,"transactions":transactions,"stage_sha256":sha256_file(fresh_stage)},indent=2),encoding="utf-8")
        if handoff.get("source_init_sha256") != sha256_file(paths["init.ifc"]) or handoff.get("source_stage1_sha256") != sha256_file(paths["stage1.ifc"]): mismatch=True
        semantic_text=" ".join(str(getattr(candidate_roots[gid],a,"")) for gid in allowed_gids if gid in candidate_roots for a in ("Name","LongName","Description","ObjectType"))+json.dumps(handoff,ensure_ascii=False)
        for token in ("EW2A10","CLINICAL-VENTILATION","ISOLATION-CONSULT-SCHEDULE","PPE-SUPPORT","CONTAMINATED-SUPPORT-LOW-OCCUPANCY"):
            if token not in semantic_text: mismatch=True
        if mismatch: errors.append("archicad_fresh_rerun:stage_or_handoff_mismatch")
    except Exception as exc:
        errors.append(f"archicad_fresh_rerun:failed:{type(exc).__name__}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
        shutil.rmtree(temp,ignore_errors=True)


def check_task10_deep(root: Path, paths: Dict[str, Path], handoff: Dict[str, Any], flow: Dict[str, Any], errors: List[str]) -> None:
    if sha256_file(paths["init.ifc"]) != INIT_SHA256:
        errors.append("init.ifc:seed_hash_mismatch")
    check_epw(paths["weather.epw"], errors)
    try:
        import ifcopenshell  # type: ignore
        seed = ifcopenshell.open(str(paths["init.ifc"])); stage = ifcopenshell.open(str(paths["stage1.ifc"]))
        seed_roots = {x.GlobalId for x in seed.by_type("IfcRoot")}; stage_roots = {x.GlobalId for x in stage.by_type("IfcRoot")}
        if seed_roots != stage_roots: errors.append("stage1.ifc:seed_root_set_changed")
        names = {str(x.Name):x for x in stage.by_type("IfcSpace")}
        if not set(CASE_SPEC["required_spaces"]).issubset(names): errors.append("stage1.ifc:required_space_missing")
        for cls in ("IfcSpace","IfcWall","IfcSlab","IfcRoof","IfcDoor","IfcWindow","IfcBuildingStorey"):
            if len(stage.by_type(cls)) != len(seed.by_type(cls)): errors.append(f"stage1.ifc:baseline_count_changed:{cls}")
    except Exception as exc:
        errors.append(f"stage1.ifc:deep_parse_failed:{type(exc).__name__}")
    authoritative = authoritative_ifc_spaces(paths["stage1.ifc"], handoff, errors)
    log = load_json(paths["native_stage_log.json"])
    rerun_archicad_stage(paths, errors)
    proc = log.get("command_server_process", {})
    actual_archicad_hash = sha256_file(ARCHICAD_EXE) if ARCHICAD_EXE.is_file() else proc.get("executable_sha256")
    if not actual_archicad_hash or proc.get("executable_sha256") != actual_archicad_hash or "27.0.0" not in str(proc.get("product_version")):
        errors.append("native_stage_log.json:archicad_identity_mismatch")
    txs = log.get("native_transactions", {}).get("Items", [])
    methods = [item.get("request",{}).get("method") for item in txs]
    if not methods or methods[0] != "Model.LoadFile" or methods[-1] != "Model.SaveFile" or methods.count("Entity.Modify") < 6:
        errors.append("native_stage_log.json:transaction_sequence")
    if any(item.get("status") != 200 or item.get("response",{}).get("error") or (item.get("request",{}).get("method") == "Entity.Modify" and not item.get("response",{}).get("result")) for item in txs):
        errors.append("native_stage_log.json:unsuccessful_transaction")
    if log.get("artifacts",{}).get("stage1.ifc",{}).get("sha256") != sha256_file(paths["stage1.ifc"]): errors.append("native_stage_log.json:stage1_hash_mismatch")
    if log.get("artifacts",{}).get("handoff.json",{}).get("sha256") != sha256_file(paths["handoff.json"]): errors.append("native_stage_log.json:handoff_hash_mismatch")
    try:
        if not iso_time(log["native_stage_started_at_utc"]) < iso_time(log["native_stage_completed_at_utc"]): raise ValueError
        load_path = str(txs[0]["request"]["params"]["location"]).lower(); save_path = str(txs[-1]["request"]["params"]["location"]).lower()
        if not load_path.endswith("desktop\\init.ifc") or not save_path.endswith("desktop\\stage1.ifc"): raise ValueError
        for left,right in zip(txs,txs[1:]):
            if iso_time(left["completed_at_utc"]) > iso_time(right["started_at_utc"]): raise ValueError
        import ifcopenshell  # type: ignore
        seed_model=ifcopenshell.open(str(paths["init.ifc"])); stage_model=ifcopenshell.open(str(paths["stage1.ifc"]))
        seed_by_gid={x.GlobalId:x for x in seed_model.by_type("IfcRoot")}; stage_by_gid={x.GlobalId:x for x in stage_model.by_type("IfcRoot")}
        declared_fields=set()
        for item in txs:
            if item.get("request",{}).get("method") != "Entity.Modify": continue
            request=json.loads(item.get("request_json","{}")) if item.get("request_json") else item["request"]
            params=request["params"]; select=params.get("select",{}); update=params.get("EntityData",{})
            cls=next(iter(select)); selector=select[cls]; gid=selector.get("GlobalId"); changes=update.get(cls,{})
            if gid not in seed_by_gid or gid not in stage_by_gid: raise ValueError
            before,after=seed_by_gid[gid],stage_by_gid[gid]
            if selector.get("Name") is not None and str(before.Name)!=str(selector["Name"]): raise ValueError
            if not changes or any(str(getattr(after,key,None))!=str(value) for key,value in changes.items()): raise ValueError
            declared_fields.update((gid,str(key)) for key in changes)
        actual_changed_fields=set()
        for gid in set(seed_by_gid) & set(stage_by_gid):
            before_attrs=canonical_direct_attributes(seed_by_gid[gid]); after_attrs=canonical_direct_attributes(stage_by_gid[gid])
            for attr in set(before_attrs) | set(after_attrs):
                if before_attrs.get(attr) != after_attrs.get(attr): actual_changed_fields.add((gid,attr))
            if canonical_owner_history(seed_by_gid[gid]) != canonical_owner_history(stage_by_gid[gid]): actual_changed_fields.add((gid,"OwnerHistory"))
        seed_products=model_product_signatures(seed_model);stage_products=model_product_signatures(stage_model)
        for gid in set(seed_products) | set(stage_products):
            before=seed_products.get(gid,{});after=stage_products.get(gid,{})
            for attr in ("placement","representation","geometry","hosts"):
                if before.get(attr) != after.get(attr): actual_changed_fields.add((gid,{"placement":"ObjectPlacement","representation":"Representation","geometry":"Representation","hosts":"HostGraph"}[attr]))
        if not actual_changed_fields.issubset(declared_fields | ARCHICAD_NATIVE_NORMALIZATION): raise ValueError
    except Exception:
        errors.append("native_stage_log.json:transaction_artifact_causality")

    text = read_text(paths["result.osm"]); objects = osm_objects(text)
    by_kind: Dict[str,List[List[str]]] = {}
    for kind, fields in objects: by_kind.setdefault(kind,[]).append(fields)
    spaces = {fields[1]:fields for fields in by_kind.get("OS:SPACE",[])}
    zones = {fields[1]:fields for fields in by_kind.get("OS:THERMALZONE",[])}
    zone_by_handle = {handle(fields[0]):name for name,fields in zones.items()}
    exported = {name:zone_by_handle.get(handle(fields[10])) for name,fields in spaces.items() if zone_by_handle.get(handle(fields[10]))}
    if len(exported) != len(spaces): errors.append("result.osm:space_without_zone")
    if set(exported.values()) != set(zones): errors.append("result.osm:orphan_zone")
    if not set(CASE_SPEC["required_spaces"]).issubset(exported): errors.append("result.osm:required_space_missing")
    definitions = {kind:{handle(x[0]):x for x in by_kind.get(kind,[])} for kind in ("OS:PEOPLE:DEFINITION","OS:LIGHTS:DEFINITION","OS:ELECTRICEQUIPMENT:DEFINITION")}
    schedules = {handle(x[0]):x for kind,values in by_kind.items() if kind.startswith("OS:SCHEDULE:") for x in values}
    spaces_by_handle = {handle(x[0]):x for x in spaces.values()}; loads = {name:[] for name in exported}
    for kind in ("OS:PEOPLE","OS:LIGHTS","OS:ELECTRICEQUIPMENT"):
        for item in by_kind.get(kind,[]):
            space = spaces_by_handle.get(handle(item[3])); definition = definitions[kind+":DEFINITION"].get(handle(item[2])); schedule = schedules.get(handle(item[4]))
            if not space or not definition or not schedule: errors.append(f"result.osm:dangling_load:{item[1]}")
            elif space[1] in loads: loads[space[1]].append((kind,definition,schedule))
    if any({x[0] for x in loads[name]} != {"OS:PEOPLE","OS:LIGHTS","OS:ELECTRICEQUIPMENT"} for name in exported): errors.append("result.osm:incomplete_load_set")
    try:
        equipment = {name:next(item for item in loads[name] if item[0]=="OS:ELECTRICEQUIPMENT")[1] for name in CASE_SPEC["required_spaces"]}
        density = {name:float(item[4]) for name,item in equipment.items()}
        if not density["EQUIPMENT"] > density["CONSULT"] or not density["CONTAMINATED-SUPPORT"] < density["ISO-CONSULT"]: errors.append("result.osm:use_load_order_invalid")
    except Exception: errors.append("result.osm:equipment_density_parse")
    thermostat_handles = {handle(x[0]) for x in by_kind.get("OS:THERMOSTATSETPOINT:DUALSETPOINT",[])}
    ideal_handles = {handle(x[0]) for x in by_kind.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM",[])}
    equipment_lists = by_kind.get("OS:ZONEHVAC:EQUIPMENTLIST",[])
    for name, zone_name in exported.items():
        zone = zones[zone_name]; lists = [x for x in equipment_lists if handle(x[2]) == handle(zone[0])]
        if handle(zone[19]) not in thermostat_handles or len(lists) != 1 or handle(lists[0][4]) not in ideal_handles: errors.append(f"result.osm:hvac_chain:{name}")
    rulesets = {x[1]:x for x in by_kind.get("OS:SCHEDULE:RULESET",[])}
    use_schedule_handles = set()
    for name in CASE_SPEC["required_spaces"]:
        for _,_,schedule in loads.get(name,[]): use_schedule_handles.add(handle(schedule[0]))
    if len(use_schedule_handles) < len(CASE_SPEC["required_spaces"]): errors.append("result.osm:use_schedule_profiles_not_distinct")

    check_geometry_and_handles(paths,errors)
    try:
        parsed_osm=parse_labeled_objects(paths["result.osm"])
        osm_spaces={labeled(x,"Name"):x for x in parsed_osm if x["type"]=="OS:SPACE"}
        osm_areas=floor_areas(parsed_osm,"Space Name")
        for name,item in authoritative.items():
            space=osm_spaces[name]; area=osm_areas.get(labeled(space,"Handle") or "",0.0)
            if not math.isclose(area,item["area"],rel_tol=0,abs_tol=0.01): errors.append(f"result.osm:ifc_area_mismatch:{name}")
    except Exception as exc: errors.append(f"result.osm:ifc_area_validation:{type(exc).__name__}")
    ft_temp=canonical_forward_translate(paths,errors)
    if ft_temp: shutil.rmtree(ft_temp,ignore_errors=True)

    osw = load_json(paths["workflow.osw"])
    if osw.get("seed_file") != "result.osm" or osw.get("weather_file") != "weather.epw": errors.append("workflow.osw:binding_mismatch")
    if flow.get("weather_sha256") != sha256_file(paths["weather.epw"]): errors.append("flow_report:weather_hash_mismatch")
    err_text = read_text(paths["run/eplusout.err"]); end_text = read_text(paths["run/eplusout.end"])
    if "EnergyPlus Completed Successfully" not in err_text or "0 Severe Errors" not in err_text or "EnergyPlus Completed Successfully" not in end_text: errors.append("energyplus:unsuccessful")
    try:
        connection = sqlite3.connect(str(paths["run/eplusout.sql"])); simulation = connection.execute("select EnergyPlusVersion,Completed,CompletedSuccessfully from Simulations").fetchall()
        if connection.execute("pragma integrity_check").fetchone()[0] != "ok" or len(simulation)!=1 or "25.1.0" not in str(simulation[0][0]): errors.append("eplusout.sql:integrity_or_version")
        flags=tuple(str(x).upper() for x in simulation[0][1:])
        if flags not in (("TRUE","TRUE"),("FALSE","FALSE")): errors.append("eplusout.sql:completion_flags")
        variables=("Zone Lights Electricity Energy","Zone Electric Equipment Electricity Energy","Zone Ideal Loads Zone Total Heating Energy","Zone Ideal Loads Zone Total Cooling Energy","Zone Ideal Loads Zone Total Heating Rate","Zone Ideal Loads Zone Total Cooling Rate")
        hourly=flow.get("simulation",{}).get("hourly_series",[]); reported={(x.get("space_name"),x.get("variable")):x for x in hourly}
        sql_data={}
        for name in exported:
            for variable in variables:
                item=reported.get((name,variable),{}); key=item.get("key_value")
                row=connection.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0",(key,variable)).fetchone()
                values=(int(row[0]),int(row[1]),float(row[2] or 0),float(row[3] or 0));sql_data[(name,variable)]=values
                if values[:2]!=(8760,8760) or int(item.get("count",0))!=8760 or abs(float(item.get("sum",math.inf))-values[2])>max(1e-6,abs(values[2])*1e-12): errors.append(f"eplusout.sql:hourly_mismatch:{name}:{variable}")
        with paths["model_summary.csv"].open(newline="",encoding="utf-8") as stream: rows=list(csv.DictReader(stream))
        if {(x["space_name"],x["thermal_zone"]) for x in rows} != set(exported.items()): errors.append("model_summary.csv:space_zone_set")
        for row in rows:
            name=row["space_name"]; energy=sum(sql_data[(name,v)][2] for v in variables[:4])/3.6e6; peak=max(sql_data[(name,v)][3] for v in variables[4:])
            if abs(float(row["energy_use_kwh"])-energy)>1e-6 or abs(float(row["peak_load_w"])-peak)>1e-6: errors.append(f"model_summary.csv:sql_recompute:{name}")
        connection.close()
    except Exception as exc: errors.append(f"eplusout.sql:deep_validation:{type(exc).__name__}")
    submitted=sql_signature(paths["run/eplusout.sql"],exported,errors,"submitted.sql")
    rerun_energyplus(paths,submitted,exported,errors)


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
    check_task10_deep(root, paths, handoff_data, flow_data, errors)

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
