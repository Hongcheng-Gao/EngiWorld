# EngiWorld multi-software instruction-rule evaluator.
# This evaluator checks instruction-derived rules and does not compare against reference answer artifacts.
from __future__ import annotations

import calendar
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
  "case_id": "multi-cli-3-revit-archicad-openstudio-task-02-windows",
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
    "run/eplusout.err",
    "run_revit_stage.ps1",
    "EngiWorld.BimBridge.dll",
    "EngiWorld.BimBridge.addin",
    "run_archicad_stage.ps1",
    "openstudio_ifc_to_energy.rb",
    "run_openstudio_stage.ps1"
  ],
  "required_spaces": [
    "RETAIL-SALES",
    "PREP-KITCHEN",
    "DRY-STORAGE"
  ],
  "required_zones": [
    "RETAIL-SALES-ZN",
    "PREP-KITCHEN-ZN",
    "DRY-STORAGE-ZN"
  ],
  "stage1_tokens": [
    "EW3B02",
    "RETAIL-SALES",
    "PREP-KITCHEN",
    "DRY-STORAGE",
    "multi-cli-3-revit-archicad-openstudio-task-02-windows"
  ],
  "stage2_tokens": [
    "RETAIL-SALES",
    "PREP-KITCHEN",
    "DRY-STORAGE",
    "multi-cli-3-revit-archicad-openstudio-task-02-windows"
  ],
  "handoff_tokens": [
    "RETAIL-PUBLIC-SCHEDULE",
    "PREP-HIGH-EQUIPMENT",
    "STORAGE-LOW-OCCUPANCY",
    "SERVICE-BOUNDARY"
  ],
  "osm_tokens": [
    "RetailPublicSchedule",
    "PrepKitchenHighEquipment",
    "DryStorageLowOccupancy",
    "ServiceBoundaryTag"
  ],
  "summary_tokens": [
    "RETAIL-SALES",
    "PREP-KITCHEN",
    "DRY-STORAGE"
  ],
  "min_windows": 0,
  "min_doors": 0,
  "min_roofs": 0,
  "min_storeys": 1,
  "expected_stage": "revit",
  "expected_archicad_stage": "archicad"
}

IMMUTABLE_SHA256 = {
    "init.ifc": "67ff58141aabb4983bf2b7bbe8cffdc0ecde14f5138ec2b1b11f263397e67495",
    "workflow_spec.json": "aeb983d61f971ad2266c3dc6a3ec4fda0fda3a91267f26179c23cdca604a5d01",
    "weather.epw": "369531a54a55856f411e63a80cb9e91a4b4dc2e9ee8e3623d24a809eb0becfc1",
    "archicad_ifc4_translator.json": "419582c9e456fde74fbb9395c91fbd4dd08ceef7525253889095fc8aa87def75",
    "run_revit_stage.ps1": "8aef646b0ea6171b26213e03619f0ae37e1d9c2baf04c9f05cb9755cb35f2137",
    "EngiWorld.BimBridge.dll": "17b77f44012e7217e92b9f931b72b929ee9be36a23d9fb79ae76839e8663fdf4",
    "EngiWorld.BimBridge.addin": "feee0a2bf6f16ceff81b8437d627887a78f9d27a969ec8f6b20d2833b60e085b",
    "run_archicad_stage.ps1": "12edf51352c6c2f0f06fbb718c494daca8eaf85b6d0cac0be1ac65122a174fd4",
    "openstudio_ifc_to_energy.rb": "b1ecf5efe90c79fc765460b2ed2415de42aa7c1087d057702fdae957dcd1eb6d",
    "run_openstudio_stage.ps1": "5eee15384cc78624a434ac54bcf6a085c0467840a08bdf7d1db026d3ed1bfbcf",
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


BRIDGE_SIGNATURE_LAYOUT = {'original_size': 35840, 'checksum_offset': 216, 'original_checksum_hex': '00000000', 'certificate_directory_offset': 280}


def valid_authenticode_signature(path: Path) -> bool:
    """Use Windows trust validation only after the original DLL content matches."""
    binary = shutil.which("powershell.exe")
    if not binary:
        return False
    env = dict(os.environ, ENGIWORLD_SIGNATURE_FILE=str(path.resolve()))
    try:
        result = subprocess.run(
            [binary, "-NoProfile", "-NonInteractive", "-Command",
             "$s=Get-AuthenticodeSignature -LiteralPath $env:ENGIWORLD_SIGNATURE_FILE; "
             "if($s.Status -eq 'Valid'){exit 0}; exit 1"],
            env=env, capture_output=True, timeout=20,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def immutable_file_matches(path: Path, expected_hash: str) -> bool:
    """Allow trusted signature-only changes to the supplied bridge, not code edits.

    PE signing changes the checksum, certificate-directory entry and appended
    certificate table. Restore only those known fields and compare EVERY original
    byte to the pinned hash; this is stricter than hashing selected PE sections.
    See https://learn.microsoft.com/en-us/windows/win32/debug/pe-format .
    """
    if sha256_file(path) == expected_hash:
        return True
    if path.name != "EngiWorld.BimBridge.dll":
        return False
    layout = BRIDGE_SIGNATURE_LAYOUT
    data = path.read_bytes()
    original_size = layout["original_size"]
    directory = layout["certificate_directory_offset"]
    checksum = layout["checksum_offset"]
    if len(data) <= original_size or directory + 8 > original_size:
        return False
    offset = int.from_bytes(data[directory:directory + 4], "little")
    size = int.from_bytes(data[directory + 4:directory + 8], "little")
    # The baseline DLL is already 8-byte aligned. Never exclude original code,
    # accept an overlay after the certificates, or ignore arbitrary new bytes.
    if offset != original_size or offset % 8 or size < 8 or offset + size != len(data):
        return False
    cursor = offset
    while cursor < len(data):
        if cursor + 8 > len(data):
            return False
        length = int.from_bytes(data[cursor:cursor + 4], "little")
        revision = int.from_bytes(data[cursor + 4:cursor + 6], "little")
        kind = int.from_bytes(data[cursor + 6:cursor + 8], "little")
        end = cursor + length
        aligned_end = cursor + ((length + 7) // 8) * 8
        if length <= 8 or revision != 0x0200 or kind != 0x0002 or aligned_end > len(data):
            return False
        if any(data[end:aligned_end]):
            return False
        cursor = aligned_end
    restored = bytearray(data[:original_size])
    restored[checksum:checksum + 4] = bytes.fromhex(layout["original_checksum_hex"])
    restored[directory:directory + 8] = b"\0" * 8
    if hashlib.sha256(restored).hexdigest() != expected_hash:
        return False
    return valid_authenticode_signature(path)


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


def require_tokens(data_or_text: Any, tokens: List[str], errors: List[str], label: str) -> None:
    seen: Set[str] = set()
    for tok in tokens:
        if tok in seen:
            continue
        seen.add(tok)
        if not contains_token(data_or_text, tok):
            errors.append(f"{label}:missing_token:{tok}")


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


def require_metadata_tokens(container: Any, metadata: Dict[str, str], errors: List[str], label: str) -> None:
    for key, value in metadata.items():
        if not value or not contains_token(container, value):
            errors.append(f"{label}:missing_metadata:{key}")


def collect_archicad_energy_model(data: Dict[str, Any], required_spaces: List[str], required_zones: List[str], errors: List[str]) -> Dict[str, Any]:
    metadata: Dict[str, str] = {}
    for key in ("weather_file", "schedule_set", "construction_set"):
        val = data.get(key)
        if not val:
            errors.append(f"archicad_handoff.json:missing_{key}")
        else:
            metadata[key] = str(val)

    building_area = numeric_from_any(data.get("building_area_m2"))
    if building_area is None or building_area <= 0:
        errors.append("archicad_handoff.json:invalid_building_area_m2")

    raw_rows = data.get("spaces")
    rows = [row for row in raw_rows if isinstance(row, dict)] if isinstance(raw_rows, list) else []
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

    raw_zone_rows = data.get("thermal_zones")
    zone_rows = [row for row in raw_zone_rows if isinstance(row, dict)] if isinstance(raw_zone_rows, list) else []
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

    if building_area and total_area and abs(building_area - total_area) > 0.05:
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
        "ids_by_class": {},
        "space_attributes_by_guid": {},
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
    ids_by_class: Dict[str, List[str]] = {}
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
            for attr in ("Name", "LongName", "ObjectType", "Description"):
                val = getattr(ent, attr, None)
                if val:
                    class_names.append(str(val))
        names[cls] = class_names
    try:
        root_ids = [str(ent.GlobalId) for ent in model.by_type("IfcRoot") if getattr(ent, "GlobalId", None)]
        for cls in ("IfcRoot", "IfcProduct", "IfcElement"):
            ids_by_class[cls] = [str(ent.GlobalId) for ent in model.by_type(cls) if getattr(ent, "GlobalId", None)]
        info["space_attributes_by_guid"] = {
            str(ent.GlobalId): {
                "Name": None if getattr(ent, "Name", None) is None else str(ent.Name),
                "LongName": None if getattr(ent, "LongName", None) is None else str(ent.LongName),
            }
            for ent in model.by_type("IfcSpace")
            if getattr(ent, "GlobalId", None)
        }
    except Exception:
        root_ids = []
        ids_by_class = {}
    info["counts"] = counts
    info["root_ids"] = root_ids
    info["ids_by_class"] = ids_by_class
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
    id_class: str = "IfcRoot",
) -> None:
    upstream_ids = set(upstream.get("ids_by_class", {}).get(id_class, []))
    downstream_ids = set(downstream.get("ids_by_class", {}).get(id_class, []))
    if id_class == "IfcRoot":
        upstream_ids = upstream_ids or set(upstream.get("root_ids") or []) or regex_ifc_root_ids(upstream["text"])
        downstream_ids = downstream_ids or set(downstream.get("root_ids") or []) or regex_ifc_root_ids(downstream["text"])
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
    if spec.get("revision") != "EW3B02":
        errors.append("workflow_spec.json:revision_mismatch")
    required_contract_tokens = set(CASE_SPEC["stage1_tokens"] + CASE_SPEC["stage2_tokens"] + CASE_SPEC["handoff_tokens"] + CASE_SPEC["osm_tokens"])
    for token in sorted(required_contract_tokens):
        if not contains_token(spec, token):
            errors.append(f"workflow_spec.json:missing_required_token:{token}")
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
    command_server = translator.get("command_server", {})
    expected_methods = ("Model.LoadFile", "Macro.ValidateIfcModel", "Model.SaveFile")
    if not isinstance(command_server, dict) or any(not contains_token(command_server, method) for method in expected_methods):
        errors.append("archicad_ifc4_translator.json:missing_verified_command_server_methods")
    boundaries = translator.get("space_boundaries", {})
    if not isinstance(boundaries, dict) or boundaries.get("generate_missing_relationships") is not False:
        errors.append("archicad_ifc4_translator.json:boundary_policy_must_not_fabricate")
    return spec


def check_archicad_entity_counts(report: Dict[str, Any], stage2_info: Dict[str, Any], errors: List[str]) -> None:
    counts = report.get("entity_counts")
    if not isinstance(counts, dict):
        errors.append("archicad_validation_report:missing_entity_counts")
        return
    normalized_counts = {norm(key): numeric_from_any(value) for key, value in counts.items()}
    for cls in IFC_CLASSES:
        reported = normalized_counts.get(norm(cls))
        actual = stage2_info["counts"].get(cls, 0)
        if reported is None or int(round(reported)) != actual:
            errors.append(f"archicad_validation_report:entity_count_mismatch:{cls}:{reported}!={actual}")


def check_handoff_ifc_space_identity(
    data: Dict[str, Any],
    ifc_info: Dict[str, Any],
    spec: Dict[str, Any],
    errors: List[str],
    label: str = "archicad_handoff.json",
) -> None:
    ifc_spaces = regex_ifc_spaces(ifc_info["text"])
    raw_rows = data.get("spaces")
    rows = [row for row in raw_rows if isinstance(row, dict)] if isinstance(raw_rows, list) else []
    spec_rows = {row.get("name"): row for row in spec.get("spaces", []) if isinstance(row, dict)}
    for required in CASE_SPEC["required_spaces"]:
        matching = [row for row in rows if str(row.get("name", "")) == required]
        if len(matching) != 1:
            errors.append(f"{label}:space_row_count:{required}:{len(matching)}")
            continue
        row = matching[0]
        if row.get("ifc_guid") != ifc_spaces.get(required):
            errors.append(f"{label}:ifc_guid_mismatch:{required}")
        spec_row = spec_rows.get(required, {})
        for key in ("thermal_zone", "storey"):
            if row.get(key) != spec_row.get(key):
                errors.append(f"{label}:workflow_spec_mapping_mismatch:{required}:{key}")
        geometry = spec_row.get("energy_geometry", {}) if isinstance(spec_row, dict) else {}
        rectangle_area = numeric_from_any(geometry.get("width_m"))
        depth = numeric_from_any(geometry.get("depth_m"))
        reported_area = numeric_from_any(row.get("area_m2"))
        if rectangle_area is None or depth is None or reported_area is None or abs(rectangle_area * depth - reported_area) > max(0.2, reported_area * 0.01):
            errors.append(f"{label}:energy_geometry_area_mismatch:{required}")
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
                    errors.append(f"{label}:space_semantic_mismatch:{required}:{key}")
            elif str(delivered) != str(expected):
                errors.append(f"{label}:space_semantic_mismatch:{required}:{key}")


def check_ifc_native_header(info: Dict[str, Any], filename: str, software: str, errors: List[str], label: str) -> None:
    header = info["text"][:5000]
    if not re.search(rf"FILE_NAME\s*\(\s*'{re.escape(filename)}'", header, flags=re.IGNORECASE):
        errors.append(f"{label}:file_name_header_mismatch")
    if software.upper() not in header.upper():
        errors.append(f"{label}:native_software_header_missing:{software}")


def check_archicad_saved_header(info: Dict[str, Any], errors: List[str]) -> None:
    header = info["text"][:5000]
    if "THE EXPRESS DATA MANAGER VERSION" not in header.upper():
        errors.append("stage2.ifc:edm_save_header_missing")
    if not re.search(r"FILE_NAME\s*\(\s*'(?:stage1|stage2)\.ifc'", header, flags=re.IGNORECASE):
        errors.append("stage2.ifc:source_header_not_preserved")


def check_ifc_space_semantics(
    path: Path,
    handoff: Dict[str, Any] | None,
    workflow_spec: Dict[str, Any],
    errors: List[str],
    label: str,
) -> None:
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.geom  # type: ignore
        import ifcopenshell.util.element  # type: ignore
    except Exception:
        errors.append(f"{label}:ifcopenshell_required_for_semantic_validation")
        return
    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        errors.append(f"{label}:ifcopenshell_parse_failed:{type(exc).__name__}")
        return
    spaces: Dict[str, Any] = {}
    for space in model.by_type("IfcSpace"):
        for attribute in ("LongName", "Name"):
            value = getattr(space, attribute, None)
            if value:
                spaces.setdefault(str(value), space)
    raw_handoff_rows = handoff.get("spaces") if handoff else None
    handoff_rows = {
        str(row.get("name")): row
        for row in (raw_handoff_rows if isinstance(raw_handoff_rows, list) else [])
        if isinstance(row, dict)
    }
    spec_geometry = {
        str(row.get("name")): row.get("energy_geometry", {})
        for row in workflow_spec.get("spaces", [])
        if isinstance(row, dict)
    }
    geometry_settings = ifcopenshell.geom.settings()
    geometry_settings.set(geometry_settings.USE_WORLD_COORDS, True)
    world_bboxes: Dict[str, Tuple[float, float, float, float, float, float]] = {}
    for required in CASE_SPEC["required_spaces"]:
        space = spaces.get(required)
        if space is None:
            errors.append(f"{label}:missing_named_ifcspace:{required}")
            continue
        if not space.ObjectPlacement or not space.Representation:
            errors.append(f"{label}:space_missing_geometry:{required}")
        else:
            try:
                shape = ifcopenshell.geom.create_shape(geometry_settings, space)
                coordinates = list(shape.geometry.verts)
                vertices = [
                    (float(coordinates[index]), float(coordinates[index + 1]), float(coordinates[index + 2]))
                    for index in range(0, len(coordinates), 3)
                ]
                if not vertices:
                    raise ValueError("no vertices")
                world_bboxes[required] = (
                    min(vertex[0] for vertex in vertices), max(vertex[0] for vertex in vertices),
                    min(vertex[1] for vertex in vertices), max(vertex[1] for vertex in vertices),
                    min(vertex[2] for vertex in vertices), max(vertex[2] for vertex in vertices),
                )
            except Exception as exc:
                errors.append(f"{label}:space_geometry_bounds_failed:{required}:{type(exc).__name__}")
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

    expected_bounds: Dict[str, Tuple[float, float, float, float, float, float]] = {}
    for required in CASE_SPEC["required_spaces"]:
        geometry = spec_geometry.get(required, {})
        values = [numeric_from_any(geometry.get(key)) for key in ("x_m", "y_m", "z_m", "width_m", "depth_m", "height_m")]
        if any(value is None for value in values):
            errors.append(f"workflow_spec.json:space_geometry_incomplete:{required}")
            continue
        x, y, z, width, depth, height = (float(value) for value in values)
        expected_bounds[required] = (x, x + width, y, y + depth, z, z + height)
        delivered = world_bboxes.get(required)
        if delivered is None:
            continue
        expected_extents = (width, depth, height)
        delivered_extents = (delivered[1] - delivered[0], delivered[3] - delivered[2], delivered[5] - delivered[4])
        if any(not math.isclose(actual, expected, rel_tol=1e-6, abs_tol=0.01) for actual, expected in zip(delivered_extents, expected_extents)):
            errors.append(f"{label}:space_bbox_extents_mismatch:{required}")

    if set(world_bboxes) == set(CASE_SPEC["required_spaces"]):
        retail = world_bboxes["RETAIL-SALES"]
        prep = world_bboxes["PREP-KITCHEN"]
        storage = world_bboxes["DRY-STORAGE"]
        if not math.isclose(prep[0], retail[0], abs_tol=0.01) or not math.isclose(storage[1], retail[1], abs_tol=0.01):
            errors.append(f"{label}:space_bbox_back_of_house_alignment_mismatch")
        if not math.isclose(prep[1], storage[0], abs_tol=0.01):
            errors.append(f"{label}:space_bbox_service_split_mismatch")
        if not (prep[2] >= retail[3] and storage[2] >= retail[3]):
            errors.append(f"{label}:space_bbox_public_service_overlap")
        for first_name, second_name in (("RETAIL-SALES", "PREP-KITCHEN"), ("RETAIL-SALES", "DRY-STORAGE"), ("PREP-KITCHEN", "DRY-STORAGE")):
            first, second = world_bboxes[first_name], world_bboxes[second_name]
            overlap = all(min(first[index + 1], second[index + 1]) - max(first[index], second[index]) > 0.01 for index in (0, 2, 4))
            if overlap:
                errors.append(f"{label}:space_bbox_overlap:{first_name}:{second_name}")


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
            r"C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe",
            paths["stage1.ifc"],
            paths["stage2.ifc"],
            "stage1.ifc",
            "stage2.ifc",
            ("IFCCommandServerApp.exe", "--p", "--m", "--d", "Model.LoadFile", "Macro.ValidateIfcModel", "Model.SaveFile"),
        ),
        (
            "openstudio",
            r"C:\openstudio-3.10.0\bin\openstudio.exe",
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

    def parse_timestamp(value: Any) -> datetime:
        match = re.fullmatch(
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})",
            str(value or ""),
            flags=re.IGNORECASE,
        )
        if not match:
            raise ValueError("timestamp must be ISO-8601 with an explicit timezone")
        base, fraction, timezone = match.groups()
        normalized_timezone = "+00:00" if timezone.upper() == "Z" else timezone
        normalized_fraction = f".{(fraction + '000000')[:6]}" if fraction else ""
        return datetime.fromisoformat(f"{base}{normalized_fraction}{normalized_timezone}")

    parsed_times: List[Tuple[datetime, datetime]] = []
    stage_times: Dict[str, Tuple[datetime, datetime]] = {}
    for stage, expected_executable, expected_invoked, expected_automation, source, output, input_name, output_name, command_tokens in expectations:
        row = next((item for item in stages if isinstance(item, dict) and item.get("stage") == stage), {})
        if numeric_from_any(row.get("exit_code")) != 0:
            errors.append(f"native_stage_log.json:{stage}:nonzero_exit")
        product_version = str(row.get("product_version", ""))
        file_version = str(row.get("file_version", ""))
        version_valid = (
            (stage == "revit" and (bool(re.match(r"^25\.", product_version)) or bool(re.match(r"^25\.", file_version))))
            or (stage == "archicad" and contains_token(product_version, "Archicad 27") and bool(re.search(r"\bbuild\s+(?:[6-9]\d{3}|\d{5,})\b", product_version, flags=re.IGNORECASE)))
            or (stage == "openstudio" and product_version.startswith("3.10.0"))
        )
        if not version_valid:
            errors.append(f"native_stage_log.json:{stage}:version_mismatch")
        declared_executable = str(row.get("executable", ""))
        invoked_executable = str(row.get("invoked_executable", declared_executable))
        if windows_path(declared_executable) != windows_path(expected_executable):
            errors.append(f"native_stage_log.json:{stage}:unexpected_executable")
        if windows_path(invoked_executable) != windows_path(expected_invoked):
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
                started = parse_timestamp(row["started_utc"])
                finished = parse_timestamp(row["finished_utc"])
                if started.tzinfo is None or finished.tzinfo is None:
                    raise ValueError("timestamps must include a UTC offset")
                if finished < started:
                    errors.append(f"native_stage_log.json:{stage}:timestamps_reversed")
                parsed_times.append((started, finished))
                stage_times[stage] = (started, finished)
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
    validation_report = load_json(paths["archicad_validation_report.json"])
    provenance = validation_report.get("native_provenance")
    transcript = provenance.get("rpc_transcript") if isinstance(provenance, dict) else None
    verified_methods = [
        str(item.get("request", {}).get("method", ""))
        for item in (transcript if isinstance(transcript, list) else [])
        if isinstance(item, dict) and isinstance(item.get("request"), dict)
    ]
    if archicad.get("rpc_method_sequence") != verified_methods:
        errors.append("native_stage_log.json:archicad:rpc_method_sequence_mismatch")
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


def sql_boolean_is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    return str(value or "").strip().upper() in {"1", "TRUE", "YES"}


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
        required_tables = (
            "Simulations",
            "Errors",
            "Zones",
            "EnvironmentPeriods",
            "ReportDataDictionary",
            "ReportData",
            "Time",
            "TabularDataWithStrings",
        )
        for table in required_tables:
            if not sql_table_exists(conn, table):
                errors.append(f"{label}:missing_standard_table:{table}")
        if errors and any(error.startswith(f"{label}:missing_standard_table") for error in errors):
            return result
        simulation_rows = conn.execute(
            "select SimulationIndex, EnergyPlusVersion, Completed, CompletedSuccessfully from Simulations order by SimulationIndex"
        ).fetchall()
        result["simulation_rows"] = [tuple(row) for row in simulation_rows]
        result["version"] = str(simulation_rows[-1][1]) if simulation_rows else ""
        completion_flags: List[Tuple[bool, bool]] = []
        if not simulation_rows:
            errors.append(f"{label}:missing_simulation_record")
        else:
            if len(simulation_rows) != 1:
                errors.append(f"{label}:simulation_row_count_mismatch:{len(simulation_rows)}!=1")
            for index, simulation_row in enumerate(simulation_rows, start=1):
                simulation_index = int(simulation_row[0])
                if simulation_index != 1:
                    errors.append(f"{label}:simulation_index_mismatch:row_{index}:{simulation_index}")
                version = str(simulation_row[1])
                if not re.search(r"EnergyPlus, Version 25\.1\.0-1c11a3d85f(?:,|$)", version):
                    errors.append(f"{label}:energyplus_version_build_mismatch:row_{index}")
                completed = sql_boolean_is_true(simulation_row[2])
                successful = sql_boolean_is_true(simulation_row[3])
                completion_flags.append((completed, successful))
                if completed != successful:
                    errors.append(f"{label}:inconsistent_completion_flags:row_{index}")
        result["completion_flags"] = completion_flags
        result["simulation_signature"] = [
            (int(row[0]), energyplus_sql_build(row[1]), sql_boolean_is_true(row[2]), sql_boolean_is_true(row[3]))
            for row in simulation_rows
        ]
        result["all_simulations_completed"] = bool(completion_flags) and all(
            completed and successful for completed, successful in completion_flags
        )

        populated_tables = ("Zones", "EnvironmentPeriods", "ReportDataDictionary", "ReportData", "Time", "TabularDataWithStrings")
        for table in populated_tables:
            count = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            result[f"{table}_row_count"] = count
            if count <= 0:
                errors.append(f"{label}:empty_standard_table:{table}")

        environment_rows = conn.execute(
            "select EnvironmentPeriodIndex, SimulationIndex, EnvironmentName, EnvironmentType "
            "from EnvironmentPeriods order by EnvironmentPeriodIndex"
        ).fetchall()
        annual_periods = [row for row in environment_rows if int(row[3] or 0) == 3]
        result["annual_environment_periods"] = [tuple(row) for row in annual_periods]
        if len(annual_periods) != 1:
            errors.append(f"{label}:annual_run_period_count_mismatch")
        else:
            annual_index = int(annual_periods[0][0])
            time_rows = conn.execute(
                "select TimeIndex, Year, Month, Day, Hour, Minute, Interval, IntervalType, "
                "coalesce(WarmupFlag, 0), SimulationDays, DayType from Time "
                "where EnvironmentPeriodIndex = ? order by TimeIndex",
                (annual_index,),
            ).fetchall()
            annual_hour_rows = len(time_rows)
            result["annual_hour_rows"] = annual_hour_rows
            if annual_hour_rows != 8760:
                errors.append(f"{label}:annual_hour_count_mismatch:{annual_hour_rows}")
            time_indices = [int(row[0]) for row in time_rows]
            if len(set(time_indices)) != 8760 or set(time_indices) != set(range(1, 8761)):
                errors.append(f"{label}:annual_timeindex_coverage_mismatch")
            years = {int(row[1]) for row in time_rows if row[1] is not None}
            if len(years) != 1 or any(calendar.isleap(year) for year in years):
                errors.append(f"{label}:annual_year_not_single_nonleap")
            timestamps = [(int(row[2]), int(row[3]), int(row[4]), int(row[5])) for row in time_rows]
            expected_timestamps = {
                (month, day, hour, 0)
                for month in range(1, 13)
                for day in range(1, calendar.monthrange(2001, month)[1] + 1)
                for hour in range(1, 25)
            }
            if len(set(timestamps)) != 8760 or set(timestamps) != expected_timestamps:
                errors.append(f"{label}:annual_calendar_coverage_mismatch")
            if any(int(row[6] or 0) != 60 for row in time_rows):
                errors.append(f"{label}:annual_interval_not_hourly")
            if any(int(row[7] or 0) != 1 for row in time_rows):
                errors.append(f"{label}:annual_interval_type_mismatch")
            if any(int(row[8] or 0) != 0 for row in time_rows):
                errors.append(f"{label}:annual_warmup_rows_present")
            simulation_days = [int(row[9]) for row in time_rows]
            expected_simulation_days = [day for day in range(1, 366) for _ in range(24)]
            if simulation_days != expected_simulation_days:
                errors.append(f"{label}:annual_simulation_day_coverage_mismatch")
            result["time_signature"] = hashlib.sha256(
                json.dumps(
                    [
                        (int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6]), int(row[7]), int(row[8] or 0), int(row[9]), str(row[10] or ""))
                        for row in time_rows
                    ],
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

        error_columns = [str(row[1]) for row in conn.execute("pragma table_info(Errors)").fetchall()]
        error_records = conn.execute("select * from Errors order by rowid").fetchall()
        result["error_columns"] = error_columns
        result["error_record_count"] = len(error_records)
        result["error_signature"] = [
            (int(record[2]), str(record[3] or ""), int(record[4] or 0))
            for record in error_records
        ]
        for index, record in enumerate(error_records, start=1):
            record_text = " | ".join(str(value or "") for value in record)
            error_type = numeric_from_any(record[2] if len(record) > 2 else None)
            if (error_type is not None and error_type > 0) or re.search(r"\b(?:severe|fatal)\b", record_text, flags=re.IGNORECASE):
                errors.append(f"{label}:severe_or_fatal_error_record:row_{index}")
        all_zone_rows = conn.execute("select ZoneName, FloorArea, IsPartOfTotalArea from Zones order by ZoneIndex").fetchall()
        if len(all_zone_rows) != len(required_zones):
            errors.append(f"{label}:zone_cardinality_mismatch:{len(all_zone_rows)}")
        zone_rows = [(name, area) for name, area, is_total in all_zone_rows if int(is_total or 0) == 1]
        result["zones"] = {str(name).upper(): float(area or 0.0) for name, area in zone_rows}
        if set(result["zones"]) != {zone.upper() for zone in required_zones}:
            errors.append(f"{label}:zone_name_set_mismatch")
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
        peak_row = conn.execute(
            "select max(rd.Value) / 3600000.0, count(*) from ReportData rd "
            "join ReportDataDictionary d on d.ReportDataDictionaryIndex = rd.ReportDataDictionaryIndex "
            "where upper(d.Name) = 'ELECTRICITY:FACILITY' and upper(d.ReportingFrequency) = 'HOURLY' "
            "and upper(d.Units) = 'J'"
        ).fetchone()
        if not peak_row or int(peak_row[1] or 0) != 8760 or numeric_from_any(peak_row[0]) is None:
            errors.append(f"{label}:missing_hourly_electricity_facility_meter")
        else:
            result["peak_load_kw"] = float(peak_row[0])
            if result["peak_load_kw"] <= 0:
                errors.append(f"{label}:nonpositive_peak_load")
    except Exception as exc:
        errors.append(f"{label}:query_failed:{type(exc).__name__}:{exc}")
    finally:
        conn.close()
    return result


def energyplus_err_signature(text: str) -> Tuple[str, int, int] | None:
    version = re.search(r"EnergyPlus, Version (25\.1\.0-1c11a3d85f)", text)
    summary = re.search(r"EnergyPlus Completed Successfully--\s*(\d+) Warning;\s*(\d+) Severe Errors", text, flags=re.IGNORECASE)
    if not version or not summary:
        return None
    return version.group(1), int(summary.group(1)), int(summary.group(2))


def energyplus_sql_build(value: Any) -> str | None:
    match = re.search(r"EnergyPlus, Version (25\.1\.0-1c11a3d85f)(?:,|$)", str(value or ""))
    return match.group(1) if match else None


def check_energyplus_outputs(paths: Dict[str, Path], handoff: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
    err_text = read_text(paths["run/eplusout.err"])
    if "EnergyPlus Completed Successfully" not in err_text:
        errors.append("eplusout.err:simulation_not_successful")
    if re.search(r"\*\*\s+(?:Severe|Fatal)\s+\*\*", err_text, flags=re.IGNORECASE):
        errors.append("eplusout.err:severe_or_fatal_error")
    err_signature = energyplus_err_signature(err_text)
    if err_signature is None or err_signature[2] != 0:
        errors.append("eplusout.err:version_or_summary_mismatch")
    metrics = read_energyplus_sql(paths["run/eplusout.sql"], CASE_SPEC["required_zones"], errors, "eplusout.sql")
    metrics["err_signature"] = err_signature
    raw_space_rows = handoff.get("spaces")
    space_rows = [row for row in raw_space_rows if isinstance(row, dict)] if isinstance(raw_space_rows, list) else []
    zone_area_by_name = metrics.get("zones", {})
    for row in space_rows:
        zone = str(row.get("thermal_zone", "")).upper()
        handoff_area = numeric_from_any(row.get("area_m2"))
        sql_area = numeric_from_any(zone_area_by_name.get(zone))
        if handoff_area is None or sql_area is None or abs(handoff_area - sql_area) > 0.05:
            errors.append(f"eplusout.sql:zone_area_mismatch:{zone}")
    handoff_total_area = sum(float(row["area_m2"]) for row in space_rows if numeric_from_any(row.get("area_m2")) is not None)
    sql_total_area = sum(float(area) for area in zone_area_by_name.values())
    if not handoff_total_area or not sql_total_area or abs(handoff_total_area - sql_total_area) > 0.05:
        errors.append("eplusout.sql:building_area_mismatch_with_handoff")
    with paths["energy_report.csv"].open("r", encoding="utf-8", newline="") as handle:
        report_rows = list(csv.DictReader(handle))
    if report_rows and metrics.get("total_site_energy_kwh") is not None:
        reported = numeric_value(report_rows[0], "total_site_energy_kwh")
        actual = float(metrics["total_site_energy_kwh"])
        if reported is None or abs(reported - actual) > 0.001:
            errors.append("energy_report.csv:total_site_energy_mismatch_with_sql")
        reported_peak = numeric_value(report_rows[0], "peak_load_kw")
        actual_peak = numeric_from_any(metrics.get("peak_load_kw"))
        if reported_peak is None or actual_peak is None or abs(reported_peak - actual_peak) > max(0.01, actual_peak * 0.01):
            errors.append("energy_report.csv:peak_load_mismatch_with_sql")
        sql_hash = next((str(value).lower() for key, value in report_rows[0].items() if norm(key) == norm("simulation_sql_sha256")), "")
        if sql_hash != sha256_file(paths["run/eplusout.sql"]):
            errors.append("energy_report.csv:simulation_sql_sha256_mismatch")
    flow = load_json(paths["flow_report.json"])
    for key, filename in (("eplusout_sql_sha256", "run/eplusout.sql"), ("eplusout_err_sha256", "run/eplusout.err"), ("workflow_sha256", "workflow.osw")):
        if str(flow.get(key, "")).lower() != sha256_file(paths[filename]):
            errors.append(f"flow_report:{key}_mismatch")
    flow_simulation = flow.get("simulation")
    if not isinstance(flow_simulation, dict) or norm(flow_simulation.get("status")) != norm("EnergyPlus Completed Successfully"):
        errors.append("flow_report:simulation_status_not_successful")
    flow_peak = numeric_from_any(flow_simulation.get("peak_load_kw") if isinstance(flow_simulation, dict) else None)
    sql_peak = numeric_from_any(metrics.get("peak_load_kw"))
    if flow_peak is None or sql_peak is None or abs(flow_peak - sql_peak) > max(0.01, sql_peak * 0.01):
        errors.append("flow_report:peak_load_mismatch_with_sql")
    flow_total = numeric_from_any(flow_simulation.get("total_site_energy_kwh") if isinstance(flow_simulation, dict) else None)
    sql_total = numeric_from_any(metrics.get("total_site_energy_kwh"))
    if flow_total is None or sql_total is None or abs(flow_total - sql_total) > 0.001:
        errors.append("flow_report:total_site_energy_mismatch_with_sql")
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
        rerun_err_text = read_text(rerun_err) if rerun_err.is_file() else ""
        if "EnergyPlus Completed Successfully" not in rerun_err_text:
            errors.append("energyplus_rerun:simulation_not_successful")
            return
        if re.search(r"\*\*\s+(?:Severe|Fatal)\s+\*\*", rerun_err_text, flags=re.IGNORECASE):
            errors.append("energyplus_rerun:severe_or_fatal_error")
            return
        rerun_err_signature = energyplus_err_signature(rerun_err_text)
        if rerun_err_signature is None or rerun_err_signature[2] != 0:
            errors.append("energyplus_rerun:version_or_summary_mismatch")
        rerun_metrics = read_energyplus_sql(rerun_sql, CASE_SPEC["required_zones"], errors, "energyplus_rerun.sql")
        if submitted_metrics.get("simulation_signature") != rerun_metrics.get("simulation_signature"):
            errors.append("energyplus_rerun:simulation_record_state_mismatch")
        if bool(submitted_metrics.get("all_simulations_completed")) != bool(rerun_metrics.get("all_simulations_completed")):
            errors.append("energyplus_rerun:completion_flag_state_mismatch")
        if submitted_metrics.get("time_signature") != rerun_metrics.get("time_signature"):
            errors.append("energyplus_rerun:annual_time_coverage_mismatch")
        if energyplus_sql_build(submitted_metrics.get("version")) != energyplus_sql_build(rerun_metrics.get("version")):
            errors.append("energyplus_rerun:energyplus_version_build_mismatch")
        if submitted_metrics.get("error_signature") != rerun_metrics.get("error_signature"):
            errors.append("energyplus_rerun:error_records_mismatch")
        if submitted_metrics.get("err_signature") != rerun_err_signature:
            errors.append("energyplus_rerun:err_summary_mismatch")
        submitted_zones = submitted_metrics.get("zones", {})
        rerun_zones = rerun_metrics.get("zones", {})
        if set(submitted_zones) != set(rerun_zones):
            errors.append("energyplus_rerun:zone_set_mismatch")
        else:
            for zone in submitted_zones:
                if not math.isclose(float(submitted_zones[zone]), float(rerun_zones[zone]), rel_tol=1e-9, abs_tol=1e-7):
                    errors.append(f"energyplus_rerun:zone_area_mismatch:{zone}")
        submitted = numeric_from_any(submitted_metrics.get("total_site_energy_kwh"))
        rerun = numeric_from_any(rerun_metrics.get("total_site_energy_kwh"))
        if submitted is None or rerun is None or abs(submitted - rerun) > max(1.0, rerun * 0.01):
            errors.append("energyplus_rerun:total_site_energy_mismatch")
        submitted_peak = numeric_from_any(submitted_metrics.get("peak_load_kw"))
        rerun_peak = numeric_from_any(rerun_metrics.get("peak_load_kw"))
        if submitted_peak is None or rerun_peak is None or abs(submitted_peak - rerun_peak) > max(0.01, rerun_peak * 0.01):
            errors.append("energyplus_rerun:peak_load_mismatch")
    finally:
        shutil.rmtree(rerun_dir, ignore_errors=True)


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


def check_seed_spatial_container_preservation(init_path: Path, stage1_path: Path, errors: List[str]) -> None:
    try:
        import ifcopenshell  # type: ignore
        init = ifcopenshell.open(str(init_path))
        stage1 = ifcopenshell.open(str(stage1_path))
    except Exception as exc:
        errors.append(f"init_to_stage1:seed_spatial_parse_failed:{type(exc).__name__}")
        return

    classes = ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey")
    for cls in classes:
        seed_guids = {
            str(item.GlobalId)
            for item in init.by_type(cls)
            if getattr(item, "GlobalId", None)
        }
        delivered_guids = {
            str(item.GlobalId)
            for item in stage1.by_type(cls)
            if getattr(item, "GlobalId", None)
        }
        if not seed_guids:
            errors.append(f"init_to_stage1:seed_spatial_class_missing_in_init:{cls}")
            continue
        missing = sorted(seed_guids - delivered_guids)
        if missing:
            errors.append(f"init_to_stage1:seed_spatial_globalid_not_preserved:{cls}:{','.join(missing)}")

    delivered_class_edges = {
        (rel.RelatingObject.is_a(), child.is_a())
        for rel in stage1.by_type("IfcRelAggregates")
        if rel.RelatingObject.is_a() in classes
        for child in rel.RelatedObjects
        if child.is_a() in classes
    }
    required_class_edges = tuple(zip(classes, classes[1:]))
    for parent_class, child_class in required_class_edges:
        if (parent_class, child_class) not in delivered_class_edges:
            errors.append(f"stage1.ifc:spatial_hierarchy_missing:{parent_class}->{child_class}")


def compare_ifc_forward_value(
    left: Any,
    right: Any,
    path: str,
    seen: Set[Tuple[int, int]],
    follow_root: bool = False,
) -> str | None:
    left_entity = hasattr(left, "is_a")
    right_entity = hasattr(right, "is_a")
    if left_entity or right_entity:
        if not (left_entity and right_entity):
            return path
        if left.is_a() != right.is_a():
            return f"{path}.type"
        left_guid = str(getattr(left, "GlobalId", "") or "") if left.is_a("IfcRoot") else ""
        right_guid = str(getattr(right, "GlobalId", "") or "") if right.is_a("IfcRoot") else ""
        if not follow_root and (left_guid or right_guid):
            return None if (left.is_a(), left_guid) == (right.is_a(), right_guid) else f"{path}.root_ref"
        pair = (int(left.id()), int(right.id()))
        if pair in seen:
            return None
        seen = set(seen)
        seen.add(pair)
        left_names = [left.attribute_name(index) for index in range(len(left)) if left.attribute_name(index) != "OwnerHistory"]
        right_names = [right.attribute_name(index) for index in range(len(right)) if right.attribute_name(index) != "OwnerHistory"]
        if left_names != right_names:
            return f"{path}.attributes"
        for name in left_names:
            found = compare_ifc_forward_value(getattr(left, name), getattr(right, name), f"{path}.{name}", seen)
            if found:
                return found
        return None
    if isinstance(left, (tuple, list)) or isinstance(right, (tuple, list)):
        if not (isinstance(left, (tuple, list)) and isinstance(right, (tuple, list))) or len(left) != len(right):
            return f"{path}.aggregate"
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            found = compare_ifc_forward_value(left_item, right_item, f"{path}[{index}]", seen)
            if found:
                return found
        return None
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
        return None if math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9) else path
    return None if left == right else path


def check_ifc_forward_semantic_preservation(stage1_path: Path, stage2_path: Path, errors: List[str]) -> None:
    try:
        import ifcopenshell  # type: ignore
        stage1 = ifcopenshell.open(str(stage1_path))
        stage2 = ifcopenshell.open(str(stage2_path))
    except Exception as exc:
        errors.append(f"stage1_to_stage2:semantic_parse_failed:{type(exc).__name__}")
        return
    roots1 = {str(item.GlobalId): item for item in stage1.by_type("IfcRoot") if getattr(item, "GlobalId", None)}
    roots2 = {str(item.GlobalId): item for item in stage2.by_type("IfcRoot") if getattr(item, "GlobalId", None)}
    if set(roots1) != set(roots2):
        errors.append("stage1_to_stage2:ifcroot_globalid_set_changed")
        return
    for guid in sorted(roots1):
        left = roots1[guid]
        right = roots2[guid]
        if left.is_a() != right.is_a():
            errors.append(f"stage1_to_stage2:ifcroot_class_changed:{guid}:{left.is_a()}!={right.is_a()}")
            continue
        changed_path = compare_ifc_forward_value(left, right, left.is_a(), set(), follow_root=True)
        if changed_path:
            errors.append(f"stage1_to_stage2:forward_semantics_changed:{guid}:{changed_path}")


def check_seed_ifcelement_preservation(init_path: Path, stage1_path: Path, errors: List[str]) -> None:
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.geom  # type: ignore
        import ifcopenshell.util.element  # type: ignore
        init = ifcopenshell.open(str(init_path))
        stage1 = ifcopenshell.open(str(stage1_path))
    except Exception as exc:
        errors.append(f"init_to_stage1:seed_semantic_parse_failed:{type(exc).__name__}")
        return
    seed = {str(item.GlobalId): item for item in init.by_type("IfcElement") if getattr(item, "GlobalId", None)}
    delivered = {str(item.GlobalId): item for item in stage1.by_type("IfcElement") if getattr(item, "GlobalId", None)}
    if not seed or not set(seed).issubset(delivered):
        errors.append("init_to_stage1:seed_ifcelement_globalid_set_not_preserved")
        return

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    def geometry_signature(element: Any) -> Tuple[Any, ...]:
        shape = ifcopenshell.geom.create_shape(settings, element)
        vertex_list = [
            tuple(round(float(value), 6) for value in shape.geometry.verts[index:index + 3])
            for index in range(0, len(shape.geometry.verts), 3)
        ]
        vertices = tuple(sorted(set(vertex_list)))
        area = 0.0
        signed_volume = 0.0
        for index in range(0, len(shape.geometry.faces), 3):
            first, second, third = (vertex_list[position] for position in shape.geometry.faces[index:index + 3])
            ux, uy, uz = (second[axis] - first[axis] for axis in range(3))
            vx, vy, vz = (third[axis] - first[axis] for axis in range(3))
            cx, cy, cz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            area += 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
            signed_volume += (
                first[0] * (second[1] * third[2] - second[2] * third[1])
                - first[1] * (second[0] * third[2] - second[2] * third[0])
                + first[2] * (second[0] * third[1] - second[1] * third[0])
            ) / 6.0
        if not vertices or area <= 0 or abs(signed_volume) <= 0:
            raise ValueError("non-solid geometry")
        return vertices, round(area, 6), round(abs(signed_volume), 6)

    def semantic_name(value: Any) -> Tuple[str, ...]:
        parts = [norm(part) for part in str(value or "").split(":")]
        if parts and parts[-1].isdigit():
            parts.pop()
        collapsed: List[str] = []
        for part in parts:
            if part and (not collapsed or collapsed[-1] != part):
                collapsed.append(part)
        return tuple(collapsed)

    def property_equal(key: str, left: Any, right: Any) -> bool:
        if isinstance(left, (int, float)) and isinstance(right, (int, float)) and not isinstance(left, bool) and not isinstance(right, bool):
            return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
        if key == "Reference" and isinstance(left, str) and isinstance(right, str):
            return norm(right).endswith(norm(left))
        return left == right

    for guid in sorted(seed):
        upstream = seed[guid]
        downstream = delivered[guid]
        if upstream.is_a() != downstream.is_a():
            errors.append(f"init_to_stage1:seed_ifcelement_class_changed:{guid}")
            continue
        if semantic_name(getattr(upstream, "Name", None)) != semantic_name(getattr(downstream, "Name", None)):
            errors.append(f"init_to_stage1:seed_ifcelement_name_changed:{guid}")
        for attribute in ("Description", "ObjectType", "PredefinedType"):
            if hasattr(upstream, attribute) and semantic_name(getattr(upstream, attribute, None)) != semantic_name(getattr(downstream, attribute, None)):
                errors.append(f"init_to_stage1:seed_ifcelement_attribute_changed:{guid}:{attribute}")
        try:
            if geometry_signature(upstream) != geometry_signature(downstream):
                errors.append(f"init_to_stage1:seed_ifcelement_geometry_changed:{guid}")
        except Exception as exc:
            errors.append(f"init_to_stage1:seed_ifcelement_geometry_failed:{guid}:{type(exc).__name__}")
        upstream_sets = ifcopenshell.util.element.get_psets(upstream)
        downstream_sets = ifcopenshell.util.element.get_psets(downstream)
        for set_name, values in upstream_sets.items():
            if not (set_name.startswith("Pset_") or set_name.startswith("Qto_")):
                continue
            delivered_values = downstream_sets.get(set_name)
            if not isinstance(delivered_values, dict):
                errors.append(f"init_to_stage1:seed_ifcelement_property_set_missing:{guid}:{set_name}")
                continue
            for key, value in values.items():
                if key == "id":
                    continue
                if key not in delivered_values or not property_equal(key, value, delivered_values[key]):
                    errors.append(f"init_to_stage1:seed_ifcelement_property_changed:{guid}:{set_name}:{key}")


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
    if str(data.get("source_sha256", "")).lower() != sha256_file(source_file):
        errors.append(f"{label}:source_sha256_mismatch")
    if data.get("case_id") != CASE_SPEC["case_id"]:
        errors.append(f"{label}:case_id_mismatch")
    if not isinstance(data.get("spaces"), list):
        errors.append(f"{label}:missing_structured_space_section")
    if required_zones and not isinstance(data.get("thermal_zones"), list):
        errors.append(f"{label}:missing_structured_zone_section")
    require_tokens(data, required_spaces, errors, f"{label}:spaces")
    require_tokens(data, required_zones, errors, f"{label}:zones")
    require_tokens(data, required_tokens, errors, f"{label}:handoff_tokens")
    if expected_stage:
        if data.get("software_stage") != expected_stage:
            errors.append(f"{label}:software_stage_not_{expected_stage}")
    for key, upstream in (extra_hashes or {}).items():
        if str(data.get(key, "")).lower() != sha256_file(upstream):
            errors.append(f"{label}:{key}_mismatch")
    return data


def exact_handoff_space_rows(data: Dict[str, Any], label: str, errors: List[str]) -> Dict[str, Dict[str, Any]]:
    raw_rows = data.get("spaces")
    rows = [row for row in raw_rows if isinstance(row, dict)] if isinstance(raw_rows, list) else []
    by_name: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        name = str(row.get("name", ""))
        if name in by_name:
            errors.append(f"{label}:duplicate_space_row:{name}")
        by_name[name] = row
    if len(rows) != len(CASE_SPEC["required_spaces"]) or set(by_name) != set(CASE_SPEC["required_spaces"]):
        errors.append(f"{label}:space_cardinality_mismatch")
    return by_name


def check_handoff_semantic_equivalence(
    revit: Dict[str, Any],
    archicad: Dict[str, Any],
    errors: List[str],
) -> None:
    revit_rows = exact_handoff_space_rows(revit, "revit_handoff.json", errors)
    archicad_rows = exact_handoff_space_rows(archicad, "archicad_handoff.json", errors)
    keys = (
        "name",
        "ifc_guid",
        "thermal_zone",
        "area_m2",
        "storey",
        "schedule_category",
        "people_per_m2",
        "lighting_w_per_m2",
        "equipment_w_per_m2",
        "outdoor_air_l_per_s_person",
    )
    for name in CASE_SPEC["required_spaces"]:
        upstream = revit_rows.get(name, {})
        downstream = archicad_rows.get(name, {})
        for key in keys:
            left = upstream.get(key)
            right = downstream.get(key)
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                equal = math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
            else:
                equal = left == right
            if not equal:
                errors.append(f"archicad_handoff.json:revit_semantic_mismatch:{name}:{key}")
    raw_zone_rows = archicad.get("thermal_zones")
    zone_rows = [row for row in raw_zone_rows if isinstance(row, dict)] if isinstance(raw_zone_rows, list) else []
    zones = {str(row.get("name", "")): row for row in zone_rows}
    expected_zones = {str(row.get("thermal_zone", "")): row for row in archicad_rows.values()}
    if len(zone_rows) != len(CASE_SPEC["required_zones"]) or set(zones) != set(CASE_SPEC["required_zones"]):
        errors.append("archicad_handoff.json:thermal_zone_cardinality_mismatch")
    for zone_name, space_row in expected_zones.items():
        zone_area = numeric_from_any(zones.get(zone_name, {}).get("area_m2"))
        space_area = numeric_from_any(space_row.get("area_m2"))
        if zone_area is None or space_area is None or not math.isclose(zone_area, space_area, rel_tol=1e-9, abs_tol=1e-9):
            errors.append(f"archicad_handoff.json:thermal_zone_area_mismatch:{zone_name}")


def check_validation_report(path: Path, stage1: Path, stage2: Path, required_spaces: List[str], required_tokens: List[str], errors: List[str]) -> Dict[str, Any]:
    data = load_json(path)
    if data.get("case_id") != CASE_SPEC["case_id"]:
        errors.append("archicad_validation_report:case_id_mismatch")
    if data.get("software_stage") != CASE_SPEC.get("expected_archicad_stage", "archicad"):
        errors.append("archicad_validation_report:software_stage_mismatch")
    if str(data.get("source_sha256", "")).lower() != sha256_file(stage1):
        errors.append("archicad_validation_report:source_sha256_mismatch")
    if str(data.get("output_sha256", "")).lower() != sha256_file(stage2):
        errors.append("archicad_validation_report:output_sha256_mismatch")
    if not isinstance(data.get("entity_counts"), dict):
        errors.append("archicad_validation_report:missing_entity_counts")
    if not isinstance(data.get("spaces"), list):
        errors.append("archicad_validation_report:missing_space_section")
    count_differences = data.get("live_saved_count_differences")
    if not isinstance(count_differences, list) or count_differences:
        errors.append("archicad_validation_report:live_saved_count_differences_not_empty")
    require_tokens(data, required_spaces, errors, "archicad_validation_report:spaces")
    require_tokens(data, required_tokens, errors, "archicad_validation_report:qa_tokens")
    blocking = data.get("blocking_errors")
    if blocking not in ([], None, "", "none", "None", 0):
        errors.append("archicad_validation_report:blocking_errors")
    return data


def check_archicad_rpc_provenance(
    report: Dict[str, Any],
    stage1_info: Dict[str, Any],
    stage2_info: Dict[str, Any],
    errors: List[str],
) -> None:
    provenance = report.get("native_provenance")
    transcript = provenance.get("rpc_transcript") if isinstance(provenance, dict) else None
    expected_provenance = {
        "exe": r"C:\Program Files\Graphisoft\Archicad 27\IFCCommandServerApp.exe",
        "port": 19737,
        "model_name": "EW3B02-RUN",
        "database_path": r"C:\Users\user\Documents\EngiWorld-task-02\archicad-ifc-server",
        "health_endpoint": "http://127.0.0.1:19737/HEALTH",
        "jemi_endpoint": "http://127.0.0.1:19737/JEMI",
    }
    if not isinstance(provenance, dict):
        errors.append("archicad_validation_report:missing_native_provenance")
        return
    for key, expected in expected_provenance.items():
        delivered = provenance.get(key)
        if key == "port":
            matches = numeric_from_any(delivered) == expected
        elif key in {"exe", "database_path"}:
            matches = str(delivered or "").replace("/", "\\").casefold() == str(expected).casefold()
        else:
            matches = str(delivered or "") == str(expected)
        if not matches:
            errors.append(f"archicad_validation_report:native_provenance_mismatch:{key}")
    product_version = str(provenance.get("product_version", ""))
    if not contains_token(product_version, "Archicad 27") or not re.search(r"\bbuild\s+(?:[6-9]\d{3}|\d{5,})\b", product_version, flags=re.IGNORECASE):
        errors.append("archicad_validation_report:native_provenance_version_mismatch")
    command_line = str(provenance.get("command_line", ""))
    command_tokens = (
        "IFCCommandServerApp.exe",
        "--p 19737",
        "--m EW3B02-RUN",
        r"--d C:\Users\user\Documents\EngiWorld-task-02\archicad-ifc-server",
        "--sa new_ifc4",
    )
    if any(token.casefold() not in command_line.casefold() for token in command_tokens):
        errors.append("archicad_validation_report:native_provenance_command_mismatch")
    process_id = numeric_from_any(provenance.get("process_id"))
    if process_id is None or process_id <= 0 or not float(process_id).is_integer():
        errors.append("archicad_validation_report:invalid_native_process_id")
    if transcript is None:
        errors.append("archicad_validation_report:missing_rpc_transcript")
        return

    valid_items: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for index, item in enumerate(transcript, start=1):
        if not isinstance(item, dict):
            errors.append(f"archicad_validation_report:rpc_item_not_object:{index}")
            continue
        request = item.get("request")
        response = item.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
            errors.append(f"archicad_validation_report:rpc_envelope_missing:{index}")
            continue
        valid_items.append((request, response))
        if response.get("jsonrpc") != "2.0":
            errors.append(f"archicad_validation_report:rpc_invalid_jsonrpc:{index}")
        if "id" not in response or response.get("id") != request.get("id"):
            errors.append(f"archicad_validation_report:rpc_id_mismatch:{index}")
        if "error" in response:
            errors.append(f"archicad_validation_report:rpc_error_response:{index}")
        if "result" not in response:
            errors.append(f"archicad_validation_report:rpc_missing_result:{index}")

    requests = [request for request, _ in valid_items]
    methods = [str(request.get("method", "")) for request in requests]
    if methods.count("Model.LoadFile") != 1 or methods.count("Macro.ValidateIfcModel") != 1 or methods.count("Model.SaveFile") != 1:
        errors.append("archicad_validation_report:invalid_core_rpc_method_counts")
    elif not (methods.index("Model.LoadFile") < methods.index("Macro.ValidateIfcModel") < methods.index("Model.SaveFile")):
        errors.append("archicad_validation_report:rpc_method_order_mismatch")
    if not methods or methods[-1] != "Model.SaveFile":
        errors.append("archicad_validation_report:save_not_last_rpc")
    if report.get("validation_method") != "Macro.ValidateIfcModel" or report.get("validation_result") is not None:
        errors.append("archicad_validation_report:validation_result_not_clean")

    def rpc_pairs(method: str) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        return [(request, response) for request, response in valid_items if request.get("method") == method]

    load_pairs = rpc_pairs("Model.LoadFile")
    validate_pairs = rpc_pairs("Macro.ValidateIfcModel")
    save_pairs = rpc_pairs("Model.SaveFile")
    if len(load_pairs) == 1:
        request, response = load_pairs[0]
        location = request.get("params", {}).get("Location") if isinstance(request.get("params"), dict) else None
        if str(location or "").replace("/", "\\").casefold() != r"C:\Users\user\Desktop\stage1.ifc".casefold():
            errors.append("archicad_validation_report:load_file_path_mismatch")
        if str(response.get("result", "")).replace("\\", "/").rsplit("/", 1)[-1].casefold() != "stage1.ifc":
            errors.append("archicad_validation_report:load_file_result_mismatch")
    if len(validate_pairs) == 1 and validate_pairs[0][1].get("result") is not None:
        errors.append("archicad_validation_report:validate_rpc_result_not_clean")
    if len(save_pairs) == 1:
        request, response = save_pairs[0]
        location = request.get("params", {}).get("Location") if isinstance(request.get("params"), dict) else None
        if str(location or "").replace("/", "\\").casefold() != r"C:\Users\user\Desktop\stage2.ifc".casefold():
            errors.append("archicad_validation_report:save_file_path_mismatch")
        if response.get("result") is not None:
            errors.append("archicad_validation_report:save_file_result_not_clean")

    live_counts = report.get("live_entity_counts")
    if not isinstance(live_counts, dict):
        errors.append("archicad_validation_report:missing_live_entity_counts")
        live_counts = {}
    entity_gets: Dict[str, List[Dict[str, Any]]] = {}
    for request, response in valid_items:
        if request.get("method") != "Entity.Get":
            continue
        select = request.get("params", {}).get("Select", {}) if isinstance(request.get("params"), dict) else {}
        if isinstance(select, dict) and len(select) == 1:
            entity_gets.setdefault(str(next(iter(select))), []).append(response)

    def response_ref_ids(response: Dict[str, Any]) -> List[str]:
        result = response.get("result")
        values = result if isinstance(result, list) else ([] if result is None else [result])
        return [str(value) for value in values]

    for cls in IFC_CLASSES:
        responses = entity_gets.get(cls, [])
        if len(responses) != 1:
            errors.append(f"archicad_validation_report:missing_live_entity_query:{cls}")
            continue
        response = responses[0]
        result = response.get("result")
        if result is not None and not isinstance(result, (str, int, list)):
            errors.append(f"archicad_validation_report:invalid_live_entity_result_type:{cls}")
        refs = response_ref_ids(response)
        if len(refs) != len(set(refs)):
            errors.append(f"archicad_validation_report:duplicate_live_entity_refs:{cls}")
        live_count = len(refs)
        if numeric_from_any(live_counts.get(cls)) != live_count:
            errors.append(f"archicad_validation_report:live_entity_count_response_mismatch:{cls}")
        if live_count != int(stage2_info.get("counts", {}).get(cls, 0)):
            errors.append(f"archicad_validation_report:live_saved_entity_count_mismatch:{cls}")

    live_spaces_raw = report.get("live_spaces")
    if not isinstance(live_spaces_raw, list):
        errors.append("archicad_validation_report:missing_live_spaces")
        live_spaces_raw = []
    live_spaces = [row for row in live_spaces_raw if isinstance(row, dict)]
    live_by_ref = {str(row.get("ref_id")): row for row in live_spaces if row.get("ref_id") is not None}
    if len(live_spaces) != len(CASE_SPEC["required_spaces"]) or len(live_by_ref) != len(live_spaces):
        errors.append("archicad_validation_report:invalid_live_space_ref_set")
    space_get_responses = entity_gets.get("IfcSpace", [])
    space_get_refs = set(response_ref_ids(space_get_responses[0])) if len(space_get_responses) == 1 else set()
    if space_get_refs != set(live_by_ref):
        errors.append("archicad_validation_report:live_space_refs_not_from_entity_get")

    saved_spaces = stage2_info.get("space_attributes_by_guid", {})
    live_long_names: Set[str] = set()
    for ref_id, row in live_by_ref.items():
        guid = str(row.get("ifc_guid", ""))
        saved = saved_spaces.get(guid)
        if not isinstance(saved, dict):
            errors.append(f"archicad_validation_report:live_space_guid_not_in_stage2:{ref_id}")
            continue
        if row.get("name") != saved.get("Name") or row.get("long_name") != saved.get("LongName"):
            errors.append(f"archicad_validation_report:live_space_saved_value_mismatch:{ref_id}")
        live_long_names.add(str(row.get("long_name", "")))
    if live_long_names != set(CASE_SPEC["required_spaces"]):
        errors.append("archicad_validation_report:live_space_names_mismatch")

    attribute_pairs: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for request, response in valid_items:
        if request.get("method") != "Entity.GetAttribute" or not isinstance(request.get("params"), dict):
            continue
        params = request["params"]
        attribute_pairs.setdefault((str(params.get("Select")), str(params.get("Attribute"))), []).append(response)
    expected_attribute_pairs = {
        (ref_id, attribute)
        for ref_id in live_by_ref
        for attribute in ("GlobalId", "Name", "LongName")
    }
    if set(attribute_pairs) != expected_attribute_pairs:
        errors.append("archicad_validation_report:attribute_query_ref_set_mismatch")
    for ref_id, attribute in sorted(expected_attribute_pairs):
        responses = attribute_pairs.get((ref_id, attribute), [])
        if len(responses) != 1:
            errors.append(f"archicad_validation_report:attribute_query_count:{ref_id}:{attribute}")
            continue
        result = responses[0].get("result")
        if not isinstance(result, dict) or attribute not in result:
            errors.append(f"archicad_validation_report:attribute_result_missing:{ref_id}:{attribute}")
            continue
        row = live_by_ref[ref_id]
        expected = row.get({"GlobalId": "ifc_guid", "Name": "name", "LongName": "long_name"}[attribute])
        if result.get(attribute) != expected:
            errors.append(f"archicad_validation_report:attribute_result_mismatch:{ref_id}:{attribute}")

    boundary = report.get("space_boundaries")
    if not isinstance(boundary, dict) or boundary.get("policy") != "observe_validate_and_preserve_upstream_state_without_fabrication":
        errors.append("archicad_validation_report:invalid_boundary_policy")
    else:
        relationship_pattern = r"\bIFCRELSPACEBOUNDARY(?:1STLEVEL|2NDLEVEL)?\s*\("
        expected = {
            "stage1_relationship_count": len(re.findall(relationship_pattern, stage1_info["text"], flags=re.IGNORECASE)),
            "stage2_relationship_count": len(re.findall(relationship_pattern, stage2_info["text"], flags=re.IGNORECASE)),
            "stage1_second_level_count": len(re.findall(r"\bIFCRELSPACEBOUNDARY2NDLEVEL\s*\(", stage1_info["text"], flags=re.IGNORECASE)),
            "stage2_second_level_count": len(re.findall(r"\bIFCRELSPACEBOUNDARY2NDLEVEL\s*\(", stage2_info["text"], flags=re.IGNORECASE)),
        }
        for key, value in expected.items():
            if numeric_from_any(boundary.get(key)) != value:
                errors.append(f"archicad_validation_report:boundary_count_mismatch:{key}")

    stage1_ids = set(stage1_info.get("root_ids") or [])
    stage2_ids = set(stage2_info.get("root_ids") or [])
    audit = report.get("global_id_audit")
    if not isinstance(audit, dict):
        errors.append("archicad_validation_report:missing_global_id_audit")
    else:
        expected_counts = {
            "stage1_ifcroot_count": len(stage1_info.get("root_ids") or []),
            "stage1_unique_ifcroot_count": len(stage1_ids),
            "stage2_ifcroot_count": len(stage2_info.get("root_ids") or []),
            "stage2_unique_ifcroot_count": len(stage2_ids),
            "preserved_count": len(stage1_ids & stage2_ids),
        }
        for key, value in expected_counts.items():
            if numeric_from_any(audit.get(key)) != value:
                errors.append(f"archicad_validation_report:global_id_audit_mismatch:{key}")
        if audit.get("missing_ids") not in ([], None) or audit.get("duplicate_ids") not in ([], None):
            errors.append("archicad_validation_report:global_id_audit_not_clean")


def parse_labeled_object_file(path: Path, osm: bool, errors: List[str], label: str) -> List[Dict[str, Any]]:
    objects: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None
    type_pattern = re.compile(r"^([A-Za-z][A-Za-z0-9:_]*)\s*,\s*$")
    for line_number, line in enumerate(read_text(path).splitlines(), start=1):
        stripped = line.strip()
        if current is None:
            if not stripped or stripped.startswith("!"):
                continue
            if line[:1].isspace():
                errors.append(f"{label}:orphan_field_line:{line_number}")
                continue
            candidate = line.split("!", 1)[0].strip()
            match = type_pattern.match(candidate)
            if not match or (osm and not match.group(1).upper().startswith("OS:")):
                errors.append(f"{label}:invalid_object_start:{line_number}")
                continue
            current = {"type": match.group(1), "fields": [], "line": line_number}
            continue
        if not stripped or stripped.startswith("!"):
            continue
        if not line[:1].isspace() and type_pattern.match(line.split("!", 1)[0].strip()):
            errors.append(f"{label}:unterminated_object:{current['line']}")
            current = {"type": type_pattern.match(line.split("!", 1)[0].strip()).group(1), "fields": [], "line": line_number}
            continue
        value_part, marker, comment = line.partition("!-")
        value_part = value_part.strip()
        if not value_part:
            continue
        terminator = value_part[-1]
        if terminator not in {",", ";"}:
            errors.append(f"{label}:invalid_field_terminator:{line_number}")
            continue
        value = value_part[:-1].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        field_label = comment.strip() if marker else ""
        current["fields"].append({"value": value, "label": field_label, "line": line_number})
        if terminator == ";":
            objects.append(current)
            current = None
    if current is not None:
        errors.append(f"{label}:unterminated_object:{current['line']}")
    return objects


def labeled_value(obj: Dict[str, Any], wanted: str) -> str | None:
    wanted_norm = norm(wanted)
    for field in obj.get("fields", []):
        label = str(field.get("label", "")).split("{", 1)[0].strip()
        if norm(label) == wanted_norm:
            return str(field.get("value", ""))
    return None


def labeled_values(obj: Dict[str, Any], prefix: str) -> List[str]:
    prefix_norm = norm(prefix)
    values: List[str] = []
    for field in obj.get("fields", []):
        label = str(field.get("label", "")).split("{", 1)[0].strip()
        if norm(label).startswith(prefix_norm):
            values.append(str(field.get("value", "")))
    return values


def polygon_area_3d(vertices: List[Tuple[float, float, float]]) -> float:
    if len(vertices) < 3:
        return 0.0
    nx = ny = nz = 0.0
    for current, following in zip(vertices, vertices[1:] + vertices[:1]):
        nx += (current[1] - following[1]) * (current[2] + following[2])
        ny += (current[2] - following[2]) * (current[0] + following[0])
        nz += (current[0] - following[0]) * (current[1] + following[1])
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def object_vertices(obj: Dict[str, Any], errors: List[str], label: str) -> List[Tuple[float, float, float]]:
    vertices: List[Tuple[float, float, float]] = []
    for raw in labeled_values(obj, "X,Y,Z Vertex"):
        parts = [part.strip() for part in raw.split(",")]
        try:
            if len(parts) != 3:
                raise ValueError("coordinate count")
            vertices.append(tuple(float(part) for part in parts))
        except ValueError:
            errors.append(f"{label}:invalid_vertex")
    return vertices


def check_openstudio_and_idf_semantics(
    osm_path: Path,
    idf_path: Path,
    handoff: Dict[str, Any],
    errors: List[str],
    workflow_spec: Dict[str, Any] | None = None,
) -> None:
    osm_objects = parse_labeled_object_file(osm_path, True, errors, "result.osm")
    idf_objects = parse_labeled_object_file(idf_path, False, errors, "in.idf")
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for obj in osm_objects:
        by_type.setdefault(str(obj["type"]).upper(), []).append(obj)
    idf_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for obj in idf_objects:
        idf_by_type.setdefault(str(obj["type"]).upper(), []).append(obj)

    handle_pattern = re.compile(r"^\{[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\}$")
    handles: Dict[str, Dict[str, Any]] = {}
    for obj in osm_objects:
        handle = labeled_value(obj, "Handle")
        if handle is None or not handle_pattern.match(handle):
            errors.append(f"result.osm:invalid_handle:{obj['type']}:{obj['line']}")
            continue
        if handle in handles:
            errors.append(f"result.osm:duplicate_handle:{handle}")
        handles[handle] = obj

    def named(objects: List[Dict[str, Any]], name: str) -> List[Dict[str, Any]]:
        return [obj for obj in objects if labeled_value(obj, "Name") == name]

    def require_handle(value: str | None, expected_types: Tuple[str, ...], context: str) -> Dict[str, Any] | None:
        obj = handles.get(str(value or ""))
        if obj is None or not any(str(obj["type"]).upper().startswith(expected.upper()) for expected in expected_types):
            errors.append(f"result.osm:invalid_reference:{context}")
            return None
        return obj

    def numeric_field(obj: Dict[str, Any] | None, field: str, context: str) -> float | None:
        value = numeric_from_any(labeled_value(obj or {}, field))
        if value is None:
            errors.append(f"result.osm:missing_numeric_field:{context}:{field}")
        return value

    space_objects = by_type.get("OS:SPACE", [])
    zone_objects = by_type.get("OS:THERMALZONE", [])
    if len(space_objects) != len(CASE_SPEC["required_spaces"]):
        errors.append(f"result.osm:space_cardinality_mismatch:{len(space_objects)}")
    if len(zone_objects) != len(CASE_SPEC["required_zones"]):
        errors.append(f"result.osm:thermal_zone_cardinality_mismatch:{len(zone_objects)}")
    idf_spaces = idf_by_type.get("SPACE", [])
    idf_zones = idf_by_type.get("ZONE", [])
    if len(idf_spaces) != len(CASE_SPEC["required_spaces"]):
        errors.append(f"in.idf:space_cardinality_mismatch:{len(idf_spaces)}")
    if len(idf_zones) != len(CASE_SPEC["required_zones"]):
        errors.append(f"in.idf:zone_cardinality_mismatch:{len(idf_zones)}")

    handoff_rows = exact_handoff_space_rows(handoff, "archicad_handoff.json", errors)
    spec_geometry = {
        str(row.get("name")): row.get("energy_geometry", {})
        for row in ((workflow_spec or {}).get("spaces", []))
        if isinstance(row, dict)
    }
    seen_zone_handles: Set[str] = set()
    seen_thermostat_handles: Set[str] = set()
    seen_idf_thermostat_names: Set[str] = set()
    osm_thermostat_names: Dict[str, str] = {}
    osm_areas: Dict[str, float] = {}
    idf_areas: Dict[str, float] = {}
    osm_shells: Dict[str, Tuple[Tuple[str, Tuple[Tuple[float, float, float], ...]], ...]] = {}
    idf_shells: Dict[str, Tuple[Tuple[str, Tuple[Tuple[float, float, float], ...]], ...]] = {}

    def canonical_surface(surface_type: Any, vertices: List[Tuple[float, float, float]]) -> Tuple[str, Tuple[Tuple[float, float, float], ...]]:
        normalized_type = norm(surface_type)
        if normalized_type in {"ROOFCEILING", "CEILING"}:
            normalized_type = "ROOF"
        return normalized_type, tuple(sorted(tuple(round(value, 6) for value in vertex) for vertex in vertices))

    def check_geometry_bounds(space_name: str, vertices: List[Tuple[float, float, float]], label: str) -> None:
        geometry = spec_geometry.get(space_name, {})
        expected_values = [numeric_from_any(geometry.get(key)) for key in ("x_m", "y_m", "z_m", "width_m", "depth_m", "height_m")]
        if not vertices or any(value is None for value in expected_values):
            errors.append(f"{label}:geometry_bounds_unavailable:{space_name}")
            return
        x, y, z, width, depth, height = (float(value) for value in expected_values)
        actual = (
            min(point[0] for point in vertices), max(point[0] for point in vertices),
            min(point[1] for point in vertices), max(point[1] for point in vertices),
            min(point[2] for point in vertices), max(point[2] for point in vertices),
        )
        expected = (x, x + width, y, y + depth, z, z + height)
        if any(not math.isclose(delivered, wanted, rel_tol=1e-9, abs_tol=1e-6) for delivered, wanted in zip(actual, expected)):
            errors.append(f"{label}:geometry_bounds_mismatch:{space_name}")
    for space_name in CASE_SPEC["required_spaces"]:
        row = handoff_rows.get(space_name, {})
        zone_name = str(row.get("thermal_zone", ""))
        expected_area = numeric_from_any(row.get("area_m2"))
        schedule_name = str(row.get("schedule_category", ""))
        osm_matches = named(space_objects, space_name)
        if len(osm_matches) != 1:
            errors.append(f"result.osm:space_object_count:{space_name}:{len(osm_matches)}")
            continue
        space = osm_matches[0]
        space_handle = str(labeled_value(space, "Handle") or "")
        story = require_handle(labeled_value(space, "Building Story Name"), ("OS:BUILDINGSTORY",), f"{space_name}:building_story")
        if story is not None and labeled_value(story, "Name") != str(row.get("storey", "")):
            errors.append(f"result.osm:building_story_name_mismatch:{space_name}")
        zone = require_handle(labeled_value(space, "Thermal Zone Name"), ("OS:THERMALZONE",), f"{space_name}:thermal_zone")
        if zone is not None:
            zone_handle = str(labeled_value(zone, "Handle") or "")
            if labeled_value(zone, "Name") != zone_name:
                errors.append(f"result.osm:space_zone_name_mismatch:{space_name}")
            if zone_handle in seen_zone_handles:
                errors.append(f"result.osm:thermal_zone_reused:{zone_name}")
            seen_zone_handles.add(zone_handle)
            thermostat = require_handle(labeled_value(zone, "Thermostat Name"), ("OS:THERMOSTATSETPOINT:DUALSETPOINT",), f"{zone_name}:thermostat")
            if norm(labeled_value(zone, "Use Ideal Air Loads")) != "YES":
                errors.append(f"result.osm:ideal_air_loads_not_enabled:{zone_name}")
            if thermostat is not None:
                thermostat_handle = str(labeled_value(thermostat, "Handle") or "")
                if thermostat_handle in seen_thermostat_handles:
                    errors.append(f"result.osm:thermostat_reused:{zone_name}")
                seen_thermostat_handles.add(thermostat_handle)
                osm_thermostat_names[zone_name] = str(labeled_value(thermostat, "Name") or "")
                heating = require_handle(labeled_value(thermostat, "Heating Setpoint Temperature Schedule Name"), ("OS:SCHEDULE",), f"{zone_name}:heating_schedule")
                cooling = require_handle(labeled_value(thermostat, "Cooling Setpoint Temperature Schedule Name"), ("OS:SCHEDULE",), f"{zone_name}:cooling_schedule")
                if heating is not None and cooling is not None and labeled_value(heating, "Handle") == labeled_value(cooling, "Handle"):
                    errors.append(f"result.osm:thermostat_setpoint_schedules_not_distinct:{zone_name}")

        schedule_matches = named(by_type.get("OS:SCHEDULE:RULESET", []), schedule_name)
        if len(schedule_matches) != 1:
            errors.append(f"result.osm:schedule_ruleset_count:{space_name}:{len(schedule_matches)}")
        else:
            require_handle(labeled_value(schedule_matches[0], "Default Day Schedule Name"), ("OS:SCHEDULE:DAY",), f"{space_name}:default_day_schedule")

        oa = require_handle(labeled_value(space, "Design Specification Outdoor Air Object Name"), ("OS:DESIGNSPECIFICATION:OUTDOORAIR",), f"{space_name}:outdoor_air")
        oa_value = numeric_field(oa, "Outdoor Air Flow per Person", space_name) if oa else None
        expected_oa = numeric_from_any(row.get("outdoor_air_l_per_s_person"))
        if oa_value is not None and expected_oa is not None and not math.isclose(oa_value, expected_oa / 1000.0, rel_tol=1e-7, abs_tol=1e-9):
            errors.append(f"result.osm:outdoor_air_mismatch:{space_name}")

        properties = [obj for obj in by_type.get("OS:ADDITIONALPROPERTIES", []) if labeled_value(obj, "Object Name") == space_handle]
        if len(properties) != 1:
            errors.append(f"result.osm:space_additional_properties_count:{space_name}:{len(properties)}")
        else:
            feature_map: Dict[str, str] = {}
            for field in properties[0].get("fields", []):
                match = re.match(r"Feature Name (\d+)", str(field.get("label", "")), flags=re.IGNORECASE)
                if not match:
                    continue
                value_label = f"Feature Value {match.group(1)}"
                value = labeled_value(properties[0], value_label)
                feature_map[str(field.get("value", ""))] = str(value or "")
            if feature_map.get("ifc_guid") != str(row.get("ifc_guid", "")):
                errors.append(f"result.osm:ifc_guid_property_mismatch:{space_name}")
            if numeric_from_any(feature_map.get("ifc_area_m2")) is None or expected_area is None or not math.isclose(float(feature_map["ifc_area_m2"]), expected_area, rel_tol=1e-7, abs_tol=1e-7):
                errors.append(f"result.osm:ifc_area_property_mismatch:{space_name}")
            if feature_map.get("schedule_category") != schedule_name:
                errors.append(f"result.osm:schedule_property_mismatch:{space_name}")

        surfaces = [obj for obj in by_type.get("OS:SURFACE", []) if labeled_value(obj, "Space Name") == space_handle]
        surface_types = {norm(labeled_value(obj, "Surface Type")) for obj in surfaces}
        if not {"FLOOR", "WALL", "ROOFCEILING"}.issubset(surface_types):
            errors.append(f"result.osm:incomplete_surface_types:{space_name}")
        edge_counts: Dict[Tuple[Tuple[float, float, float], Tuple[float, float, float]], int] = {}
        floor_area = 0.0
        osm_canonical_surfaces: List[Tuple[str, Tuple[Tuple[float, float, float], ...]]] = []
        osm_vertices: List[Tuple[float, float, float]] = []
        for surface in surfaces:
            require_handle(labeled_value(surface, "Construction Name"), ("OS:CONSTRUCTION",), f"{space_name}:surface_construction")
            vertices = object_vertices(surface, errors, f"result.osm:{space_name}")
            if len(vertices) < 3 or polygon_area_3d(vertices) <= 0:
                errors.append(f"result.osm:invalid_surface_geometry:{space_name}")
                continue
            osm_vertices.extend(vertices)
            osm_canonical_surfaces.append(canonical_surface(labeled_value(surface, "Surface Type"), vertices))
            if norm(labeled_value(surface, "Surface Type")) == "FLOOR":
                floor_area += polygon_area_3d(vertices)
            rounded = [tuple(round(value, 6) for value in vertex) for vertex in vertices]
            for first, second in zip(rounded, rounded[1:] + rounded[:1]):
                edge = tuple(sorted((first, second)))
                edge_counts[edge] = edge_counts.get(edge, 0) + 1
        if edge_counts and any(count != 2 for count in edge_counts.values()):
            errors.append(f"result.osm:space_shell_not_closed:{space_name}")
        osm_areas[space_name] = floor_area
        osm_shells[space_name] = tuple(sorted(osm_canonical_surfaces))
        check_geometry_bounds(space_name, osm_vertices, "result.osm")
        if expected_area is None or not math.isclose(floor_area, expected_area, rel_tol=0.005, abs_tol=0.05):
            errors.append(f"result.osm:floor_area_mismatch:{space_name}")

        load_specs = (
            ("OS:PEOPLE", "People Definition Name", "OS:PEOPLE:DEFINITION", "People per Space Floor Area", "people_per_m2", "Number of People Schedule Name"),
            ("OS:LIGHTS", "Lights Definition Name", "OS:LIGHTS:DEFINITION", "Watts per Space Floor Area", "lighting_w_per_m2", "Schedule Name"),
            ("OS:ELECTRICEQUIPMENT", "Electric Equipment Definition Name", "OS:ELECTRICEQUIPMENT:DEFINITION", "Watts per Space Floor Area", "equipment_w_per_m2", "Schedule Name"),
        )
        for object_type, definition_field, definition_type, density_field, handoff_key, schedule_field in load_specs:
            loads = [obj for obj in by_type.get(object_type, []) if labeled_value(obj, "Space or SpaceType Name") == space_handle]
            if len(loads) != 1:
                errors.append(f"result.osm:load_object_count:{space_name}:{object_type}:{len(loads)}")
                continue
            definition = require_handle(labeled_value(loads[0], definition_field), (definition_type,), f"{space_name}:{object_type}:definition")
            schedule = require_handle(labeled_value(loads[0], schedule_field), ("OS:SCHEDULE",), f"{space_name}:{object_type}:schedule")
            if schedule is not None and labeled_value(schedule, "Name") != schedule_name:
                errors.append(f"result.osm:load_schedule_mismatch:{space_name}:{object_type}")
            density = numeric_field(definition, density_field, f"{space_name}:{object_type}") if definition else None
            expected_density = numeric_from_any(row.get(handoff_key))
            if density is not None and expected_density is not None and not math.isclose(density, expected_density, rel_tol=1e-7, abs_tol=1e-9):
                errors.append(f"result.osm:load_density_mismatch:{space_name}:{object_type}")

        idf_space_matches = named(idf_spaces, space_name)
        idf_zone_matches = named(idf_zones, zone_name)
        if len(idf_space_matches) != 1 or len(idf_zone_matches) != 1:
            errors.append(f"in.idf:space_or_zone_object_count:{space_name}")
        elif labeled_value(idf_space_matches[0], "Zone Name") != zone_name:
            errors.append(f"in.idf:space_zone_mismatch:{space_name}")
        idf_surfaces = [obj for obj in idf_by_type.get("BUILDINGSURFACE:DETAILED", []) if labeled_value(obj, "Space Name") == space_name]
        idf_floor_area = 0.0
        idf_canonical_surfaces: List[Tuple[str, Tuple[Tuple[float, float, float], ...]]] = []
        idf_vertices: List[Tuple[float, float, float]] = []
        idf_surface_types = {norm(labeled_value(obj, "Surface Type")) for obj in idf_surfaces}
        if not {"FLOOR", "WALL"}.issubset(idf_surface_types) or not ({"ROOF", "CEILING"} & idf_surface_types):
            errors.append(f"in.idf:incomplete_surface_types:{space_name}")
        construction_names = {str(labeled_value(obj, "Name") or "") for obj in idf_by_type.get("CONSTRUCTION", [])}
        for surface in idf_surfaces:
            if labeled_value(surface, "Zone Name") != zone_name or labeled_value(surface, "Construction Name") not in construction_names:
                errors.append(f"in.idf:surface_reference_mismatch:{space_name}")
            vertices = object_vertices(surface, errors, f"in.idf:{space_name}")
            if len(vertices) >= 3:
                idf_vertices.extend(vertices)
                idf_canonical_surfaces.append(canonical_surface(labeled_value(surface, "Surface Type"), vertices))
            if norm(labeled_value(surface, "Surface Type")) == "FLOOR":
                idf_floor_area += polygon_area_3d(vertices)
        idf_areas[space_name] = idf_floor_area
        idf_shells[space_name] = tuple(sorted(idf_canonical_surfaces))
        check_geometry_bounds(space_name, idf_vertices, "in.idf")
        if expected_area is None or not math.isclose(idf_floor_area, expected_area, rel_tol=0.005, abs_tol=0.05) or not math.isclose(idf_floor_area, floor_area, rel_tol=1e-7, abs_tol=1e-7):
            errors.append(f"in.idf:floor_area_mismatch:{space_name}")

        idf_schedule_names = {
            str(labeled_value(obj, "Name") or "")
            for object_type, objects in idf_by_type.items()
            if object_type.startswith("SCHEDULE")
            for obj in objects
        }
        if schedule_name not in idf_schedule_names:
            errors.append(f"in.idf:missing_schedule:{space_name}")
        idf_load_specs = (
            ("PEOPLE", "People per Floor Area", "people_per_m2", "Number of People Schedule Name"),
            ("LIGHTS", "Watts per Floor Area", "lighting_w_per_m2", "Schedule Name"),
            ("ELECTRICEQUIPMENT", "Watts per Floor Area", "equipment_w_per_m2", "Schedule Name"),
        )
        for object_type, density_field, handoff_key, schedule_field in idf_load_specs:
            loads = [obj for obj in idf_by_type.get(object_type, []) if labeled_value(obj, "Zone or ZoneList or Space or SpaceList Name") == space_name]
            if len(loads) != 1:
                errors.append(f"in.idf:load_object_count:{space_name}:{object_type}:{len(loads)}")
                continue
            if labeled_value(loads[0], schedule_field) != schedule_name:
                errors.append(f"in.idf:load_schedule_mismatch:{space_name}:{object_type}")
            density = numeric_from_any(labeled_value(loads[0], density_field))
            expected_density = numeric_from_any(row.get(handoff_key))
            if density is None or expected_density is None or not math.isclose(density, expected_density, rel_tol=1e-7, abs_tol=1e-9):
                errors.append(f"in.idf:load_density_mismatch:{space_name}:{object_type}")
        idf_oa = named(idf_by_type.get("DESIGNSPECIFICATION:OUTDOORAIR", []), f"{space_name} Outdoor Air")
        if len(idf_oa) != 1:
            errors.append(f"in.idf:outdoor_air_object_count:{space_name}:{len(idf_oa)}")
        else:
            value = numeric_from_any(labeled_value(idf_oa[0], "Outdoor Air Flow per Person"))
            if value is None or expected_oa is None or not math.isclose(value, expected_oa / 1000.0, rel_tol=1e-7, abs_tol=1e-9):
                errors.append(f"in.idf:outdoor_air_mismatch:{space_name}")
        controls = [obj for obj in idf_by_type.get("ZONECONTROL:THERMOSTAT", []) if labeled_value(obj, "Zone or ZoneList Name") == zone_name]
        if len(controls) != 1 or norm(labeled_value(controls[0], "Control 1 Object Type") if controls else None) != "THERMOSTATSETPOINT-DUALSETPOINT":
            errors.append(f"in.idf:dual_thermostat_missing:{zone_name}")
        else:
            thermostat_name = str(labeled_value(controls[0], "Control 1 Name") or "")
            if thermostat_name in seen_idf_thermostat_names:
                errors.append(f"in.idf:thermostat_reused:{zone_name}")
            seen_idf_thermostat_names.add(thermostat_name)
            setpoints = named(idf_by_type.get("THERMOSTATSETPOINT:DUALSETPOINT", []), thermostat_name)
            if len(setpoints) != 1:
                errors.append(f"in.idf:dual_setpoint_object_count:{zone_name}:{len(setpoints)}")
            if thermostat_name != osm_thermostat_names.get(zone_name):
                errors.append(f"openstudio_idf:thermostat_mapping_mismatch:{zone_name}")
        ideals = [obj for obj in idf_by_type.get("HVACTEMPLATE:ZONE:IDEALLOADSAIRSYSTEM", []) if labeled_value(obj, "Zone Name") == zone_name]
        if len(ideals) != 1:
            errors.append(f"in.idf:ideal_loads_object_count:{zone_name}:{len(ideals)}")

    if set(osm_areas) == set(CASE_SPEC["required_spaces"]) and set(idf_areas) == set(osm_areas):
        for name in osm_areas:
            if not math.isclose(osm_areas[name], idf_areas[name], rel_tol=1e-7, abs_tol=1e-7):
                errors.append(f"openstudio_idf:space_area_mismatch:{name}")
            if osm_shells.get(name) != idf_shells.get(name):
                errors.append(f"openstudio_idf:surface_geometry_mismatch:{name}")
        if len(set(osm_shells.values())) != len(osm_shells):
            errors.append("result.osm:space_shells_overlap_exactly")
        if len(set(idf_shells.values())) != len(idf_shells):
            errors.append("in.idf:space_shells_overlap_exactly")


def check_osm(
    path: Path,
    handoff_hash: str,
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    errors: List[str],
    stage2_hash: str | None = None,
    metadata: Dict[str, str] | None = None,
    handoff: Dict[str, Any] | None = None,
    idf_path: Path | None = None,
    workflow_spec: Dict[str, Any] | None = None,
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
    if handoff is not None and idf_path is not None:
        check_openstudio_and_idf_semantics(path, idf_path, handoff, errors, workflow_spec=workflow_spec)


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
    if len(rows) != 1:
        errors.append(f"energy_report.csv:row_count_mismatch:{len(rows)}!=1")
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
    if expected_area_m2 and area and abs(area - expected_area_m2) > 0.05:
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
        if abs(eui - expected) > 0.0001:
            errors.append("energy_report.csv:eui_inconsistent_with_total_and_area")
    for key, expected_values in (("space_names", required_spaces), ("thermal_zones", required_zones)):
        raw = str(row_value(row, key) or "")
        delivered = [value.strip() for value in raw.split("|") if value.strip()]
        if len(delivered) != len(expected_values) or set(delivered) != set(expected_values):
            errors.append(f"energy_report.csv:{key}_set_mismatch")


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
    if str(data.get("consumed_handoff_sha256", "")).lower() != sha256_file(handoff_path):
        errors.append("flow_report:consumed_handoff_sha256_mismatch")
    if str(data.get("osm_sha256", "")).lower() != sha256_file(osm_path):
        errors.append("flow_report:osm_sha256_mismatch")
    if idf_path and str(data.get("idf_sha256", "")).lower() != sha256_file(idf_path):
        errors.append("flow_report:idf_sha256_mismatch")
    if energy_report_path and str(data.get("energy_report_sha256", "")).lower() != sha256_file(energy_report_path):
        errors.append("flow_report:energy_report_sha256_mismatch")
    if stage2_path and str(data.get("stage2_sha256", "")).lower() != sha256_file(stage2_path):
        errors.append("flow_report:stage2_sha256_mismatch")
    require_tokens(data, required_spaces, errors, "flow_report:spaces")
    require_tokens(data, required_zones, errors, "flow_report:zones")
    require_tokens(data, CASE_SPEC["software_chain"], errors, "flow_report:software_chain")
    spaces = data.get("spaces")
    zones = data.get("thermal_zones")
    if not isinstance(spaces, list) or len(spaces) != len(required_spaces) or set(map(str, spaces)) != set(required_spaces):
        errors.append("flow_report:space_cardinality_mismatch")
    if not isinstance(zones, list) or len(zones) != len(required_zones) or set(map(str, zones)) != set(required_zones):
        errors.append("flow_report:thermal_zone_cardinality_mismatch")
    if data.get("software_chain") != ["revit", "archicad", "openstudio", "energyplus"]:
        errors.append("flow_report:software_chain_order_mismatch")
    for key, expected_value in (metadata or {}).items():
        if data.get(key) != expected_value:
            errors.append(f"flow_report:metadata_mismatch:{key}")
    require_metadata_tokens(data, metadata or {}, errors, "flow_report")
    if not isinstance(data.get("software_chain"), list):
        errors.append("flow_report:missing_stage_sequence")
    openstudio_version = data.get("openstudio_version")
    if not isinstance(openstudio_version, str) or not openstudio_version:
        errors.append("flow_report:missing_openstudio_version")
    elif not openstudio_version.startswith("3.10.0"):
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
    handoff: Dict[str, Any] | None = None,
) -> None:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != len(required_spaces):
        errors.append(f"model_summary.csv:row_count_mismatch:{len(rows)}!={len(required_spaces)}")
    if not rows:
        return
    fields = {norm(x) for x in (rows[0].keys() if rows else [])}
    for required_col in (
        "case_id",
        "space_name",
        "thermal_zone",
        "ifc_guid",
        "source_handoff_sha256",
        "source_stage2_sha256",
        "area_m2",
        "storey",
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
    expected_rows = exact_handoff_space_rows(handoff, "archicad_handoff.json", errors) if handoff is not None else {}
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
        seen_spaces.append(str(row_value(row, "space_name") or ""))
        seen_zones.append(str(row_value(row, "thermal_zone") or ""))
        val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_handoff_sha256")), "")
        if val != handoff_hash.lower():
            errors.append("model_summary.csv:source_handoff_sha256_mismatch")
        if stage2_hash:
            stage2_val = next((str(v).lower() for k, v in row.items() if norm(k) == norm("source_stage2_sha256")), "")
            if stage2_val != stage2_hash.lower():
                errors.append("model_summary.csv:source_stage2_sha256_mismatch")
        for key, expected_value in (metadata or {}).items():
            if str(row_value(row, key) or "") != str(expected_value):
                errors.append(f"model_summary.csv:row_metadata_mismatch:{row_value(row, 'space_name')}:{key}")
        area = numeric_value(row, "area_m2")
        if area is None or area <= 0:
            errors.append("model_summary.csv:invalid_area_m2")
            continue
        total_area += area
        expected = expected_rows.get(str(row_value(row, "space_name") or ""))
        if expected is not None:
            comparisons = {
                "thermal_zone": (row_value(row, "thermal_zone"), expected.get("thermal_zone")),
                "ifc_guid": (row_value(row, "ifc_guid"), expected.get("ifc_guid")),
                "storey": (row_value(row, "storey"), expected.get("storey")),
            }
            for key, (delivered, wanted) in comparisons.items():
                if str(delivered or "") != str(wanted or ""):
                    errors.append(f"model_summary.csv:handoff_mismatch:{expected.get('name')}:{key}")
            expected_area = numeric_from_any(expected.get("area_m2"))
            if expected_area is None or not math.isclose(area, expected_area, rel_tol=1e-9, abs_tol=1e-9):
                errors.append(f"model_summary.csv:handoff_mismatch:{expected.get('name')}:area_m2")
    for required in required_spaces:
        if sum(norm(value) == norm(required) for value in seen_spaces) != 1:
            errors.append(f"model_summary.csv:space_row_count:{required}")
    for required in required_zones:
        if sum(norm(value) == norm(required) for value in seen_zones) != 1:
            errors.append(f"model_summary.csv:zone_row_count:{required}")
    if expected_area_m2 and total_area and abs(total_area - expected_area_m2) > 0.05:
        errors.append("model_summary.csv:area_sum_mismatch_with_handoff")


def evaluate(root: Path) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    paths = require_files(root, CASE_SPEC["required_files"], errors)
    if errors:
        return False, errors
    for filename, expected_hash in IMMUTABLE_SHA256.items():
        if not immutable_file_matches(paths[filename], expected_hash):
            errors.append(f"immutable_input_sha256_mismatch:{filename}")

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
    check_ifc_space_semantics(stage1, None, workflow_spec, errors, "stage1.ifc")
    check_stage_derives_from_init(init_path, stage1, init_info, stage1_info, errors)
    check_global_id_retention(init_info, stage1_info, 0.80, errors, "init_to_stage1", id_class="IfcProduct")
    check_seed_spatial_container_preservation(init_path, stage1, errors)
    check_seed_ifcelement_preservation(init_path, stage1, errors)

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
        if str(revit_handoff_data.get("input_seed_sha256", "")).lower() != sha256_file(init_path):
            errors.append("revit_handoff.json:input_seed_sha256_mismatch")
        exact_handoff_space_rows(revit_handoff_data, "revit_handoff.json", errors)
        check_handoff_ifc_space_identity(revit_handoff_data, stage1_info, workflow_spec, errors, "revit_handoff.json")
        check_ifc_space_semantics(stage1, revit_handoff_data, workflow_spec, errors, "stage1.ifc")
        stage2 = paths["stage2.ifc"]
        stage2_min_counts = dict(stage1_min_counts)
        stage2_info = check_ifc_basic(stage2, CASE_SPEC["required_spaces"], stage2_min_counts, errors, "stage2.ifc")
        check_archicad_saved_header(stage2_info, errors)
        check_stage2_derives_from_stage1(stage1, stage2, stage1_info, stage2_info, errors)
        check_global_id_retention(stage1_info, stage2_info, 1.0, errors, "stage1_to_stage2")
        check_ifc_forward_semantic_preservation(stage1, stage2, errors)
        archicad_report = check_validation_report(paths["archicad_validation_report.json"], stage1, stage2, CASE_SPEC["required_spaces"], CASE_SPEC["stage2_tokens"], errors)
        check_archicad_entity_counts(archicad_report, stage2_info, errors)
        check_archicad_rpc_provenance(archicad_report, stage1_info, stage2_info, errors)
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
        if str(archicad_handoff_data.get("stage1_sha256", "")).lower() != sha256_file(stage1):
            errors.append("archicad_handoff.json:stage1_sha256_mismatch")
        check_handoff_ifc_space_identity(archicad_handoff_data, stage2_info, workflow_spec, errors)
        check_ifc_space_semantics(stage2, archicad_handoff_data, workflow_spec, errors, "stage2.ifc")
        check_handoff_semantic_equivalence(revit_handoff_data, archicad_handoff_data, errors)
        archicad_model = collect_archicad_energy_model(archicad_handoff_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
        archicad_handoff_hash = sha256_file(archicad_handoff)
        stage2_hash = sha256_file(stage2)
        metadata = archicad_model.get("metadata", {})
        expected_area = archicad_model.get("building_area_m2")
        check_osm(paths["result.osm"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], errors, stage2_hash=stage2_hash, metadata=metadata, handoff=archicad_handoff_data, idf_path=paths["in.idf"], workflow_spec=workflow_spec)
        check_idf(paths["in.idf"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], errors, stage2_hash=stage2_hash, metadata=metadata)
        check_flow_report(paths["flow_report.json"], archicad_handoff, paths["result.osm"], CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors, idf_path=paths["in.idf"], energy_report_path=paths["energy_report.csv"], stage2_path=stage2, metadata=metadata)
        check_model_summary_csv(paths["model_summary.csv"], archicad_handoff_hash, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors, stage2_hash=stage2_hash, expected_area_m2=expected_area, metadata=metadata, handoff=archicad_handoff_data)
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
