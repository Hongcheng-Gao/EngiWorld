# EngiWorld multi-software instruction-rule evaluator.
# This evaluator checks instruction-derived rules and does not compare against reference answer artifacts.
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
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
    "energy_report.csv",
    "workflow_spec.json",
    "archicad_ifc4_translator.json",
    "weather.epw",
    "native_stage_log.json",
    "workflow.osw",
    "run/eplusout.sql",
    "run/eplusout.err"
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


def regex_ifc_root_ids(text: str) -> Set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"#\d+\s*=\s*IFC[A-Z0-9_]+\s*\(\s*'([0-9A-Za-z_$]{22})'",
            text,
            flags=re.IGNORECASE,
        )
    }


def regex_ifc_spaces(text: str) -> Dict[str, str]:
    spaces: Dict[str, str] = {}
    pattern = re.compile(
        r"#\d+\s*=\s*IFCSPACE\s*\(\s*'(?P<guid>[0-9A-Za-z_$]{22})'(?P<body>[^;]*?)\);",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        strings = re.findall(r"'([^']*)'", match.group("body"))
        for candidate in strings:
            normalized = norm(candidate)
            for required in CASE_SPEC["required_spaces"]:
                if normalized == norm(required):
                    spaces[required] = match.group("guid")
    return spaces


def check_global_id_retention(
    upstream: Dict[str, Any],
    downstream: Dict[str, Any],
    minimum: float,
    errors: List[str],
    label: str,
) -> None:
    upstream_ids = set(upstream.get("root_ids") or []) or regex_ifc_root_ids(upstream["text"])
    downstream_ids = set(downstream.get("root_ids") or []) or regex_ifc_root_ids(downstream["text"])
    if not upstream_ids:
        errors.append(f"{label}:upstream_has_no_ifcroot_globalids")
        return
    retained = len(upstream_ids & downstream_ids) / len(upstream_ids)
    if retained < minimum:
        errors.append(f"{label}:globalid_retention_too_low:{retained:.3f}<{minimum:.3f}")


def check_workflow_contract(path: Path, translator_path: Path, errors: List[str]) -> Dict[str, Any]:
    spec = load_json(path)
    if spec.get("case_id") != CASE_SPEC["case_id"]:
        errors.append("workflow_spec.json:case_id_mismatch")
    fixed = spec.get("fixed_software")
    if not isinstance(fixed, dict):
        errors.append("workflow_spec.json:missing_fixed_software")
    else:
        expected_versions = {"revit": "2025", "archicad": "27", "openstudio": "3.10.0"}
        expected_executables = {
            "revit": r"C:\Program Files\Autodesk\Revit 2025\Revit.exe",
            "archicad": r"C:\Program Files\Graphisoft\Archicad 27\Archicad Starter.exe",
            "openstudio": r"C:\openstudio-3.10.0\bin\openstudio.exe",
        }
        for software, version in expected_versions.items():
            if software not in fixed or not contains_token(fixed[software], version):
                errors.append(f"workflow_spec.json:unpinned_{software}_version")
            if software in fixed and not contains_token(fixed[software], "executable"):
                errors.append(f"workflow_spec.json:missing_{software}_executable")
            delivered = fixed.get(software, {})
            executable = delivered.get("executable") if isinstance(delivered, dict) else None
            normalized_executable = str(executable or "").replace("/", "\\").casefold()
            if normalized_executable != expected_executables[software].casefold():
                errors.append(f"workflow_spec.json:unexpected_{software}_executable")
        archicad_fixed = fixed.get("archicad", {})
        if not isinstance(archicad_fixed, dict) or numeric_from_any(archicad_fixed.get("minimum_build")) is None or float(archicad_fixed["minimum_build"]) < 6000:
            errors.append("workflow_spec.json:archicad_minimum_build_below_6000")
        openstudio_fixed = fixed.get("openstudio", {})
        if not isinstance(openstudio_fixed, dict) or str(openstudio_fixed.get("energyplus_version", "")) != "25.1.0":
            errors.append("workflow_spec.json:energyplus_version_not_25_1_0")
    exchange = spec.get("ifc_exchange")
    if not isinstance(exchange, dict) or not contains_token(exchange, "IFC4"):
        errors.append("workflow_spec.json:missing_ifc4_exchange_contract")
    spec_spaces = spec.get("spaces")
    if not isinstance(spec_spaces, list):
        errors.append("workflow_spec.json:missing_spaces")
    else:
        for required in CASE_SPEC["required_spaces"]:
            matches = [row for row in spec_spaces if isinstance(row, dict) and row.get("name") == required]
            if len(matches) != 1:
                errors.append(f"workflow_spec.json:space_definition_count:{required}:{len(matches)}")
                continue
            row = matches[0]
            geometry = row.get("energy_geometry")
            semantics = row.get("energy_semantics")
            if not isinstance(geometry, dict) or any(numeric_from_any(geometry.get(key)) in (None, 0.0) for key in ("width_m", "depth_m", "height_m")):
                errors.append(f"workflow_spec.json:invalid_energy_geometry:{required}")
            if not isinstance(semantics, dict) or any(numeric_from_any(semantics.get(key)) is None for key in ("people_per_m2", "lighting_w_per_m2", "equipment_w_per_m2", "outdoor_air_l_per_s_person")):
                errors.append(f"workflow_spec.json:invalid_energy_semantics:{required}")
    translator = load_json(translator_path)
    if translator.get("archicad_major_version") != 27 or translator.get("schema") != "IFC4":
        errors.append("archicad_ifc4_translator.json:version_or_schema_mismatch")
    if not contains_token(translator, "IfcSpace") or not contains_token(translator, "space_boundaries"):
        errors.append("archicad_ifc4_translator.json:missing_space_exchange_settings")
    return spec


def check_archicad_entity_counts(report: Dict[str, Any], stage2_info: Dict[str, Any], errors: List[str]) -> None:
    rows = find_values(report, "entity_counts") + find_values(report, "ifc_counts")
    counts = next((row for row in rows if isinstance(row, dict)), None)
    if counts is None:
        errors.append("archicad_validation_report:missing_entity_counts")
        return
    normalized_counts = {norm(key): numeric_from_any(value) for key, value in counts.items()}
    for cls in IFC_CLASSES:
        reported = normalized_counts.get(norm(cls))
        actual = stage2_info["counts"].get(cls, 0)
        if reported is None or int(round(reported)) != actual:
            errors.append(f"archicad_validation_report:entity_count_mismatch:{cls}:{reported}!={actual}")


def check_handoff_ifc_space_identity(data: Dict[str, Any], stage2_info: Dict[str, Any], spec: Dict[str, Any], errors: List[str]) -> None:
    ifc_spaces = regex_ifc_spaces(stage2_info["text"])
    rows = structured_rows(data, ("spaces", "rooms", "ifc_spaces"))
    spec_rows = {row.get("name"): row for row in spec.get("spaces", []) if isinstance(row, dict)}
    for required in CASE_SPEC["required_spaces"]:
        matching = [row for row in rows if str(row.get("name", "")) == required]
        if len(matching) != 1:
            errors.append(f"archicad_handoff.json:space_row_count:{required}:{len(matching)}")
            continue
        row = matching[0]
        if row.get("ifc_guid") != ifc_spaces.get(required):
            errors.append(f"archicad_handoff.json:ifc_guid_mismatch:{required}")
        spec_row = spec_rows.get(required, {})
        geometry = spec_row.get("energy_geometry", {}) if isinstance(spec_row, dict) else {}
        rectangle_area = numeric_from_any(geometry.get("width_m"))
        depth = numeric_from_any(geometry.get("depth_m"))
        reported_area = numeric_from_any(row.get("area_m2"))
        if rectangle_area is None or depth is None or reported_area is None or abs(rectangle_area * depth - reported_area) > max(0.2, reported_area * 0.01):
            errors.append(f"archicad_handoff.json:energy_geometry_area_mismatch:{required}")
        semantics = spec_row.get("energy_semantics", {}) if isinstance(spec_row, dict) else {}
        for key in ("schedule_category", "people_per_m2", "lighting_w_per_m2", "equipment_w_per_m2", "outdoor_air_l_per_s_person"):
            if key not in semantics:
                errors.append(f"workflow_spec.json:space_missing_semantic:{required}:{key}")
                continue
            expected = semantics[key]
            delivered = row.get(key)
            if isinstance(expected, (int, float)):
                delivered_number = numeric_from_any(delivered)
                if delivered_number is None or abs(delivered_number - float(expected)) > 1e-6:
                    errors.append(f"archicad_handoff.json:space_semantic_mismatch:{required}:{key}")
            elif str(delivered) != str(expected):
                errors.append(f"archicad_handoff.json:space_semantic_mismatch:{required}:{key}")


def check_ifc_native_header(info: Dict[str, Any], filename: str, software: str, errors: List[str], label: str) -> None:
    header = info["text"][:5000]
    if not re.search(rf"FILE_NAME\s*\(\s*'{re.escape(filename)}'", header, flags=re.IGNORECASE):
        errors.append(f"{label}:file_name_header_mismatch")
    if software.upper() not in header.upper():
        errors.append(f"{label}:native_software_header_missing:{software}")


def check_ifc_space_semantics(path: Path, handoff: Dict[str, Any] | None, errors: List[str], label: str) -> None:
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.util.element  # type: ignore
    except Exception:
        errors.append(f"{label}:ifcopenshell_required_for_semantic_validation")
        return
    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        errors.append(f"{label}:ifcopenshell_parse_failed:{type(exc).__name__}")
        return
    spaces = {str(space.Name): space for space in model.by_type("IfcSpace") if getattr(space, "Name", None)}
    handoff_rows = {
        str(row.get("name")): row
        for row in (structured_rows(handoff, ("spaces", "rooms", "ifc_spaces")) if handoff else [])
    }
    for required in CASE_SPEC["required_spaces"]:
        space = spaces.get(required)
        if space is None:
            errors.append(f"{label}:missing_named_ifcspace:{required}")
            continue
        if not space.ObjectPlacement or not space.Representation:
            errors.append(f"{label}:space_missing_geometry:{required}")
        if not any(rel.is_a("IfcRelAggregates") and rel.RelatingObject.is_a("IfcBuildingStorey") for rel in getattr(space, "Decomposes", [])):
            errors.append(f"{label}:space_not_aggregated_by_storey:{required}")
        psets = ifcopenshell.util.element.get_psets(space, psets_only=True)
        qtos = ifcopenshell.util.element.get_psets(space, qtos_only=True)
        energy = psets.get("EngiWorld_EnergyHandoff", {})
        quantities = qtos.get("Qto_SpaceBaseQuantities", {})
        if not energy:
            errors.append(f"{label}:space_missing_energy_pset:{required}")
        if numeric_from_any(quantities.get("GrossFloorArea")) in (None, 0.0):
            errors.append(f"{label}:space_missing_gross_floor_area:{required}")
        if handoff:
            row = handoff_rows.get(required, {})
            if str(getattr(space, "GlobalId", "")) != str(row.get("ifc_guid", "")):
                errors.append(f"{label}:space_globalid_handoff_mismatch:{required}")
            if numeric_from_any(row.get("area_m2")) is not None and numeric_from_any(quantities.get("GrossFloorArea")) is not None:
                if abs(float(row["area_m2"]) - float(quantities["GrossFloorArea"])) > 0.05:
                    errors.append(f"{label}:space_area_handoff_mismatch:{required}")
            property_map = {
                "thermal_zone": "ThermalZone",
                "schedule_category": "ScheduleCategory",
                "lighting_w_per_m2": "LightingPowerDensityWPerM2",
                "equipment_w_per_m2": "EquipmentPowerDensityWPerM2",
                "people_per_m2": "PeoplePerM2",
                "outdoor_air_l_per_s_person": "OutdoorAirLPerSPerson",
            }
            for handoff_key, pset_key in property_map.items():
                delivered, ifc_value = row.get(handoff_key), energy.get(pset_key)
                if isinstance(delivered, (int, float)):
                    if numeric_from_any(ifc_value) is None or abs(float(delivered) - float(ifc_value)) > 1e-6:
                        errors.append(f"{label}:space_property_handoff_mismatch:{required}:{handoff_key}")
                elif str(delivered) != str(ifc_value):
                    errors.append(f"{label}:space_property_handoff_mismatch:{required}:{handoff_key}")


def check_workflow_osw(path: Path, paths: Dict[str, Path], errors: List[str]) -> None:
    workflow = load_json(path)
    expected_scalars = {
        "name": CASE_SPEC["case_id"],
        "seed_file": "result.osm",
        "weather_file": "weather.epw",
        "run_directory": "run",
    }
    for key, expected in expected_scalars.items():
        if str(workflow.get(key, "")).replace("\\", "/").rstrip("/") != expected:
            errors.append(f"workflow.osw:{key}_mismatch")
    if str(workflow.get("osw_version", "")) != "3.10":
        errors.append("workflow.osw:version_not_3_10")
    if str(workflow.get("source_stage2_sha256", "")).lower() != sha256_file(paths["stage2.ifc"]):
        errors.append("workflow.osw:source_stage2_sha256_mismatch")
    if str(workflow.get("source_handoff_sha256", "")).lower() != sha256_file(paths["archicad_handoff.json"]):
        errors.append("workflow.osw:source_handoff_sha256_mismatch")
    steps = workflow.get("steps")
    if not isinstance(steps, list) or not any(
        isinstance(step, dict)
        and contains_token(step.get("measure_dir_name", ""), "EngiWorldIfcHandoffToEnergyModel")
        and contains_token(step.get("arguments", {}), "stage2.ifc")
        and contains_token(step.get("arguments", {}), "archicad_handoff.json")
        for step in steps
    ):
        errors.append("workflow.osw:missing_ifc_handoff_conversion_step")



def check_native_stage_log(path: Path, paths: Dict[str, Path], errors: List[str]) -> None:
    data = load_json(path)
    stages = data.get("stages")
    if not isinstance(stages, list) or [stage.get("stage") for stage in stages if isinstance(stage, dict)] != ["revit", "archicad", "openstudio"]:
        errors.append("native_stage_log.json:stage_order_mismatch")
        return
    expectations = [
        (
            "revit",
            r"C:\Program Files\Autodesk\Revit 2025\Revit.exe",
            r"C:\ProgramData\Autodesk\Revit\Addins\2025\EngiWorld.BimBridge.addin",
            paths["init.ifc"],
            paths["stage1.ifc"],
            "init.ifc",
            "stage1.ifc",
            ("Revit.exe", "ENGIWORLD_BIM_STAGE=revit"),
        ),
        (
            "archicad",
            r"C:\Program Files\Graphisoft\Archicad 27\Archicad Starter.exe",
            r"C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe",
            paths["stage1.ifc"],
            paths["stage2.ifc"],
            "stage1.ifc",
            "stage2.ifc",
            ("IFCCommandServerApp.exe", "workflow_spec.json", "archicad_ifc4_translator.json"),
        ),
        (
            "openstudio",
            r"C:\openstudio-3.10.0\bin\openstudio.exe",
            r"C:\Users\user\Desktop\openstudio_ifc_to_energy.rb",
            paths["stage2.ifc"],
            paths["result.osm"],
            "stage2.ifc",
            "result.osm",
            ("openstudio.exe", "openstudio_ifc_to_energy.rb", "archicad_handoff.json", "weather.epw"),
        ),
    ]

    def windows_path(value: Any) -> str:
        return str(value or "").replace("/", "\\").casefold()

    parsed_times: List[Tuple[datetime, datetime]] = []
    for stage, expected_executable, expected_automation, source, output, input_name, output_name, command_tokens in expectations:
        row = next((item for item in stages if isinstance(item, dict) and item.get("stage") == stage), {})
        if numeric_from_any(row.get("exit_code")) != 0:
            errors.append(f"native_stage_log.json:{stage}:nonzero_exit")
        product_version = str(row.get("product_version", ""))
        version_valid = (
            (stage == "revit" and bool(re.match(r"^25\.", product_version)))
            or (stage == "archicad" and contains_token(product_version, "Archicad 27") and bool(re.search(r"\bbuild\s+(?:[6-9]\d{3}|\d{5,})\b", product_version, flags=re.IGNORECASE)))
            or (stage == "openstudio" and product_version.startswith("3.10.0"))
        )
        if not version_valid:
            errors.append(f"native_stage_log.json:{stage}:version_mismatch")
        declared_executable = str(row.get("executable", ""))
        invoked_executable = str(row.get("invoked_executable", declared_executable))
        if windows_path(declared_executable) != windows_path(expected_executable):
            errors.append(f"native_stage_log.json:{stage}:unexpected_executable")
        if windows_path(invoked_executable) != windows_path(expected_executable):
            errors.append(f"native_stage_log.json:{stage}:invoked_executable_not_pinned_windows_binary")
        automation_entry = str(row.get("automation_entry", "")).strip()
        if windows_path(automation_entry) != windows_path(expected_automation):
            errors.append(f"native_stage_log.json:{stage}:unexpected_automation_entry")
        if str(row.get("input_file", "")).replace("\\", "/") != input_name:
            errors.append(f"native_stage_log.json:{stage}:input_file_mismatch")
        if str(row.get("output_file", "")).replace("\\", "/") != output_name:
            errors.append(f"native_stage_log.json:{stage}:output_file_mismatch")
        command = str(row.get("command", ""))
        if any(token.casefold() not in command.casefold() for token in command_tokens):
            errors.append(f"native_stage_log.json:{stage}:command_mismatch")
        if str(row.get("input_sha256", "")).lower() != sha256_file(source):
            errors.append(f"native_stage_log.json:{stage}:input_sha256_mismatch")
        if str(row.get("output_sha256", "")).lower() != sha256_file(output):
            errors.append(f"native_stage_log.json:{stage}:output_sha256_mismatch")
        if not row.get("started_utc") or not row.get("finished_utc"):
            errors.append(f"native_stage_log.json:{stage}:missing_timestamps")
        else:
            try:
                started = datetime.fromisoformat(str(row["started_utc"]).replace("Z", "+00:00"))
                finished = datetime.fromisoformat(str(row["finished_utc"]).replace("Z", "+00:00"))
                if started.tzinfo is None or finished.tzinfo is None:
                    raise ValueError("timestamps must include a UTC offset")
                if finished < started:
                    errors.append(f"native_stage_log.json:{stage}:timestamps_reversed")
                parsed_times.append((started, finished))
            except (TypeError, ValueError):
                errors.append(f"native_stage_log.json:{stage}:invalid_timestamps")
    if len(parsed_times) == 3:
        for index in range(1, len(parsed_times)):
            if parsed_times[index][0] < parsed_times[index - 1][1]:
                errors.append("native_stage_log.json:stages_overlap_or_out_of_order")
                break
    revit = stages[0]
    if str(revit.get("handoff_sha256", "")).lower() != sha256_file(paths["revit_handoff.json"]):
        errors.append("native_stage_log.json:revit:handoff_sha256_mismatch")
    archicad = stages[1]
    if str(archicad.get("input_handoff_sha256", "")).lower() != sha256_file(paths["revit_handoff.json"]):
        errors.append("native_stage_log.json:archicad:input_handoff_sha256_mismatch")
    for key, filename in (
        ("handoff_sha256", "archicad_handoff.json"),
        ("validation_report_sha256", "archicad_validation_report.json"),
        ("translator_sha256", "archicad_ifc4_translator.json"),
    ):
        if str(archicad.get(key, "")).lower() != sha256_file(paths[filename]):
            errors.append(f"native_stage_log.json:archicad:{key}_mismatch")
    openstudio = stages[2]
    if str(openstudio.get("input_handoff_sha256", "")).lower() != sha256_file(paths["archicad_handoff.json"]):
        errors.append("native_stage_log.json:openstudio:input_handoff_sha256_mismatch")
    energyplus_executable = str(openstudio.get("energyplus_executable", ""))
    normalized_energyplus = windows_path(energyplus_executable)
    if not normalized_energyplus.startswith("c:\\openstudio-3.10.0\\") or not normalized_energyplus.endswith("\\energyplus.exe"):
        errors.append("native_stage_log.json:openstudio:energyplus_executable_not_windows_native")
    for key, filename in (("idf_sha256", "in.idf"), ("workflow_sha256", "workflow.osw"), ("eplusout_sql_sha256", "run/eplusout.sql"), ("eplusout_err_sha256", "run/eplusout.err")):
        if str(openstudio.get(key, "")).lower() != sha256_file(paths[filename]):
            errors.append(f"native_stage_log.json:openstudio:{key}_mismatch")


def sql_table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("select 1 from sqlite_master where type in ('table','view') and name = ?", (name,)).fetchone() is not None


def read_energyplus_sql(path: Path, required_zones: List[str], errors: List[str], label: str) -> Dict[str, Any]:
    if path.stat().st_size < 4096:
        errors.append(f"{label}:too_small")
        return {}
    try:
        conn = sqlite3.connect(str(path))
    except Exception as exc:
        errors.append(f"{label}:open_failed:{type(exc).__name__}")
        return {}
    result: Dict[str, Any] = {}
    try:
        required_tables = ("Simulations", "Zones", "ReportDataDictionary", "ReportData", "Time", "TabularDataWithStrings")
        for table in required_tables:
            if not sql_table_exists(conn, table):
                errors.append(f"{label}:missing_standard_table:{table}")
        if errors and any(error.startswith(f"{label}:missing_standard_table") for error in errors):
            return result
        version_row = conn.execute("select EnergyPlusVersion from Simulations limit 1").fetchone()
        result["version"] = str(version_row[0]) if version_row else ""
        if "25.1" not in result["version"]:
            errors.append(f"{label}:energyplus_version_not_25_1")
        zone_rows = conn.execute("select ZoneName, FloorArea from Zones where IsPartOfTotalArea = 1").fetchall()
        result["zones"] = {str(name).upper(): float(area or 0.0) for name, area in zone_rows}
        for zone in required_zones:
            if zone.upper() not in result["zones"]:
                errors.append(f"{label}:missing_zone:{zone}")
        energy_row = conn.execute(
            "select Units, Value from TabularDataWithStrings "
            "where ReportName='AnnualBuildingUtilityPerformanceSummary' "
            "and TableName='Site and Source Energy' and RowName='Total Site Energy' "
            "and ColumnName='Total Energy' limit 1"
        ).fetchone()
        if not energy_row:
            errors.append(f"{label}:missing_total_site_energy")
        else:
            units, value = str(energy_row[0]).upper(), float(str(energy_row[1]).strip())
            result["total_site_energy_kwh"] = value * 277.7777777778 if units == "GJ" else value
            if result["total_site_energy_kwh"] <= 0:
                errors.append(f"{label}:nonpositive_total_site_energy")
    except Exception as exc:
        errors.append(f"{label}:query_failed:{type(exc).__name__}:{exc}")
    finally:
        conn.close()
    return result


def check_energyplus_outputs(paths: Dict[str, Path], handoff: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
    err_text = read_text(paths["run/eplusout.err"])
    if "EnergyPlus Completed Successfully" not in err_text:
        errors.append("eplusout.err:simulation_not_successful")
    if re.search(r"\*\*\s+Fatal\s+\*\*", err_text, flags=re.IGNORECASE):
        errors.append("eplusout.err:fatal_error")
    metrics = read_energyplus_sql(paths["run/eplusout.sql"], CASE_SPEC["required_zones"], errors, "eplusout.sql")
    space_rows = structured_rows(handoff, ("spaces", "rooms", "ifc_spaces"))
    zone_area_by_name = metrics.get("zones", {})
    for row in space_rows:
        zone = str(row.get("thermal_zone", "")).upper()
        handoff_area = numeric_from_any(row.get("area_m2"))
        sql_area = numeric_from_any(zone_area_by_name.get(zone))
        if handoff_area is None or sql_area is None or abs(handoff_area - sql_area) > max(0.5, handoff_area * 0.02):
            errors.append(f"eplusout.sql:zone_area_mismatch:{zone}")
    with paths["energy_report.csv"].open("r", encoding="utf-8", newline="") as handle:
        report_rows = list(csv.DictReader(handle))
    if report_rows and metrics.get("total_site_energy_kwh") is not None:
        reported = numeric_value(report_rows[0], "total_site_energy_kwh")
        actual = float(metrics["total_site_energy_kwh"])
        if reported is None or abs(reported - actual) > max(1.0, actual * 0.01):
            errors.append("energy_report.csv:total_site_energy_mismatch_with_sql")
        sql_hash = next((str(value).lower() for key, value in report_rows[0].items() if norm(key) == norm("simulation_sql_sha256")), "")
        if sql_hash != sha256_file(paths["run/eplusout.sql"]):
            errors.append("energy_report.csv:simulation_sql_sha256_mismatch")
    flow = load_json(paths["flow_report.json"])
    for key, filename in (("eplusout_sql_sha256", "run/eplusout.sql"), ("eplusout_err_sha256", "run/eplusout.err"), ("workflow_sha256", "workflow.osw")):
        if not any_hash_field(flow, key, sha256_file(paths[filename])):
            errors.append(f"flow_report:{key}_mismatch")
    return metrics


def find_energyplus_binary() -> str | None:
    configured = os.environ.get("ENGIWORLD_ENERGYPLUS_EXE")
    candidates = [
        configured,
        shutil.which("energyplus"),
        r"C:\openstudio-3.10.0\EnergyPlus\energyplus.exe",
        r"C:\openstudio-3.10.0\bin\energyplus.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    return None


def rerun_energyplus(paths: Dict[str, Path], submitted_metrics: Dict[str, Any], errors: List[str]) -> None:
    binary = find_energyplus_binary()
    if not binary:
        errors.append("energyplus_cli:not_found")
        return
    rerun_dir = paths["in.idf"].parent / "_eval_energyplus_rerun"
    shutil.rmtree(rerun_dir, ignore_errors=True)
    rerun_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [binary, "-x", "-w", str(paths["weather.epw"]), "-d", str(rerun_dir), str(paths["in.idf"])],
            text=True,
            capture_output=True,
            timeout=300,
        )
    except Exception as exc:
        errors.append(f"energyplus_rerun:failed:{type(exc).__name__}:{exc}")
        return
    if proc.returncode != 0:
        errors.append(f"energyplus_rerun:nonzero_exit:{proc.returncode}")
        return
    rerun_err = rerun_dir / "eplusout.err"
    rerun_sql = rerun_dir / "eplusout.sql"
    if not rerun_err.is_file() or "EnergyPlus Completed Successfully" not in read_text(rerun_err):
        errors.append("energyplus_rerun:simulation_not_successful")
        return
    rerun_metrics = read_energyplus_sql(rerun_sql, CASE_SPEC["required_zones"], errors, "energyplus_rerun.sql")
    submitted = numeric_from_any(submitted_metrics.get("total_site_energy_kwh"))
    rerun = numeric_from_any(rerun_metrics.get("total_site_energy_kwh"))
    if submitted is None or rerun is None or abs(submitted - rerun) > max(1.0, rerun * 0.01):
        errors.append("energyplus_rerun:total_site_energy_mismatch")


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
    if not re.search(r"\bOS:VERSION\s*,[^;]*\b3\.10\.0\s*;", text, flags=re.IGNORECASE | re.DOTALL):
        errors.append("result.osm:openstudio_version_not_3_10_0")
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
    if not re.search(r"\bVERSION\s*,\s*25\.1(?:\.0)?\s*;", text, flags=re.IGNORECASE | re.DOTALL):
        errors.append("in.idf:energyplus_version_not_25_1")
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
    if row_case != CASE_SPEC["case_id"]:
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
    if data.get("case_id") != CASE_SPEC["case_id"]:
        errors.append("flow_report:case_id_mismatch")
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
    version_values = [str(value) for value in find_values(data, "openstudio_version")]
    if not version_values:
        errors.append("flow_report:missing_openstudio_version")
    elif not any(value.startswith("3.10.0") for value in version_values):
        errors.append("flow_report:openstudio_version_not_3_10_0")
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
    seen_spaces: List[str] = []
    seen_zones: List[str] = []
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
            break
        seen_spaces.append(str(row_value(row, "space_name") or ""))
        seen_zones.append(str(row_value(row, "thermal_zone") or ""))
        val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_handoff_sha256")), "")
        if val != handoff_hash.lower():
            errors.append("model_summary.csv:source_handoff_sha256_mismatch")
            break
        if stage2_hash:
            stage2_val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_stage2_sha256")), "")
            if stage2_val != stage2_hash.lower():
                errors.append("model_summary.csv:source_stage2_sha256_mismatch")
                break
        area = numeric_value(row, "area_m2")
        if area is None or area <= 0:
            errors.append("model_summary.csv:invalid_area_m2")
            break
        total_area += area
    for required in required_spaces:
        if sum(norm(value) == norm(required) for value in seen_spaces) != 1:
            errors.append(f"model_summary.csv:space_row_count:{required}")
    for required in required_zones:
        if sum(norm(value) == norm(required) for value in seen_zones) != 1:
            errors.append(f"model_summary.csv:zone_row_count:{required}")
    if expected_area_m2 and total_area and abs(total_area - expected_area_m2) > max(1.0, expected_area_m2 * 0.05):
        errors.append("model_summary.csv:area_sum_mismatch_with_handoff")


def evaluate(root: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    paths = require_files(root, CASE_SPEC["required_files"], errors)
    if errors:
        return False, errors

    workflow_spec = check_workflow_contract(paths["workflow_spec.json"], paths["archicad_ifc4_translator.json"], errors)

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
    check_ifc_native_header(stage1_info, "stage1.ifc", "Autodesk Revit", errors, "stage1.ifc")
    check_ifc_space_semantics(stage1, None, errors, "stage1.ifc")
    check_stage_derives_from_init(init_path, stage1, init_info, stage1_info, errors)
    check_global_id_retention(init_info, stage1_info, 0.70, errors, "init_to_stage1")

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
        check_ifc_native_header(stage2_info, "stage2.ifc", "GRAPHISOFT Archicad", errors, "stage2.ifc")
        check_stage2_derives_from_stage1(stage1, stage2, stage1_info, stage2_info, errors)
        check_global_id_retention(stage1_info, stage2_info, 0.70, errors, "stage1_to_stage2")
        archicad_report = check_validation_report(paths["archicad_validation_report.json"], stage1, stage2, CASE_SPEC["required_spaces"], CASE_SPEC["stage2_tokens"], errors)
        check_archicad_entity_counts(archicad_report, stage2_info, errors)
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
        check_handoff_ifc_space_identity(archicad_handoff_data, stage2_info, workflow_spec, errors)
        check_ifc_space_semantics(stage2, archicad_handoff_data, errors, "stage2.ifc")
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
        check_workflow_osw(paths["workflow.osw"], paths, errors)
        check_native_stage_log(paths["native_stage_log.json"], paths, errors)
        submitted_metrics = check_energyplus_outputs(paths, archicad_handoff_data, errors)
        rerun_energyplus(paths, submitted_metrics, errors)

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
