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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

CASE_SPEC = {'case_id': 'multi-cli-2-archicad-openstudio-task-02-windows',
 'mode': 'two_stage',
 'software_chain': ['archicad', 'openstudio', 'energyplus'],
 'required_files': ['init.ifc',
                    'stage1.ifc',
                    'handoff.json',
                    'result.osm',
                    'workflow.osw',
                    'weather.epw',
                    'run/eplusout.sql',
                    'run/eplusout.err',
                    'run/eplusout.end',
                    'native_stage_log.json',
                    'flow_report.json',
                    'model_summary.csv'],
 'required_spaces': ['WAITING', 'CONSULT'],
 'required_zones': ['WAITING-ZN', 'CONSULT-ZN'],
 'stage1_tokens': ['EW2A02'],
 'handoff_tokens': [],
 'osm_tokens': [],
 'summary_tokens': ['WAITING', 'CONSULT'],
 'min_windows': 0,
 'min_doors': 1,
 'min_roofs': 0,
 'min_storeys': 1,
 'expected_stage': 'archicad'}

SEED_SHA256 = "d789e6dad3d9b817036a0e90ee39c9b814a1de0301ab72123a105888935d94da"
TARGET_SPACE_GLOBAL_ID = "0V92O_gT1AyODVhuvEhgNC"
ARCHICAD_EXE_SHA256 = "594a37c581f7434543c6d018b222373b8d0d17b7b44507be15683fa5579dd775"
OPENSTUDIO_EXE_SHA256 = "46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361"
ENERGYPLUS_EXE_SHA256 = "3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5"
ENERGYPLUS_BUILD = "25.1.0-1c11a3d85f"

ENERGY_VARIABLES = (
    ("Zone Lights Electricity Energy", "zone"),
    ("Zone Electric Equipment Electricity Energy", "zone"),
    ("Zone Ideal Loads Zone Total Heating Energy", "ideal"),
    ("Zone Ideal Loads Zone Total Cooling Energy", "ideal"),
)
RATE_VARIABLES = (
    "Zone Ideal Loads Zone Total Heating Rate",
    "Zone Ideal Loads Zone Total Cooling Rate",
)

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
    return abs(
        sum(
            points[i][0] * points[(i + 1) % len(points)][1]
            - points[(i + 1) % len(points)][0] * points[i][1]
            for i in range(len(points))
        )
    ) / 2.0


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
                        if not candidate.is_a("IfcExtrudedAreaSolid"):
                            continue
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


def canonical_ifc_value(
    value: Any,
    *,
    is_top: bool = False,
    stack: Tuple[Tuple[str, int], ...] = (),
) -> Any:
    """Canonicalize an IfcRoot's forward semantic graph without STEP line ids."""
    if hasattr(value, "is_a") and hasattr(value, "attribute_name"):
        entity_class = str(value.is_a())
        is_root = bool(value.is_a("IfcRoot"))
        global_id = str(getattr(value, "GlobalId", "") or "") if is_root else ""
        if is_root and not is_top:
            return ("IfcRootRef", entity_class, global_id)

        marker = (entity_class, int(value.id()))
        if marker in stack:
            return ("Cycle", entity_class)
        attributes: List[Tuple[str, Any]] = []
        for index, nested in enumerate(value):
            attribute = str(value.attribute_name(index))
            if is_top and attribute == "OwnerHistory":
                continue
            if is_top and global_id == TARGET_SPACE_GLOBAL_ID and attribute == "Name":
                continue
            if is_top and entity_class == "IfcProject" and attribute == "Description":
                continue
            attributes.append(
                (
                    attribute,
                    canonical_ifc_value(nested, stack=stack + (marker,)),
                )
            )
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
    roots_by_id: Dict[str, Dict[str, str]] = {}
    semantics_by_id: Dict[str, Any] = {}
    try:
        roots = list(model.by_type("IfcRoot"))
    except Exception:
        roots = []
    root_ids = [
        str(getattr(entity, "GlobalId", "") or "")
        for entity in roots
        if getattr(entity, "GlobalId", None)
    ]
    info["root_ids"] = root_ids
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
    if sha256_file(init_path) != SEED_SHA256:
        errors.append("init.ifc:unexpected_seed_sha256")
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
        actual = stage_counts.get(cls, 0)
        if actual != base:
            errors.append(f"stage1.ifc:baseline_count_changed:{cls}:{actual}!={base}")
    init_roots = set((init_info.get("roots_by_id") or {}).keys())
    stage_roots = set((stage1_info.get("roots_by_id") or {}).keys())
    if not init_info.get("parsed_with_ifcopenshell") or not stage1_info.get("parsed_with_ifcopenshell"):
        errors.append("ifc:ifcopenshell_required_for_identity_validation")
    if init_roots != stage_roots:
        errors.append(
            "stage1.ifc:ifc_root_global_id_set_changed:"
            f"lost={len(init_roots - stage_roots)}:added={len(stage_roots - init_roots)}"
        )
    init_records = init_info.get("roots_by_id") or {}
    stage_records = stage1_info.get("roots_by_id") or {}
    init_semantics = init_info.get("semantics_by_id") or {}
    stage_semantics = stage1_info.get("semantics_by_id") or {}
    changed_names: List[Tuple[str, str, str, str]] = []
    for global_id in sorted(init_roots & stage_roots):
        before = init_records.get(global_id, {})
        after = stage_records.get(global_id, {})
        if before.get("class") != after.get("class"):
            errors.append(f"stage1.ifc:root_class_changed:{global_id}")
        if before.get("name") != after.get("name"):
            changed_names.append(
                (global_id, str(before.get("class")), str(before.get("name")), str(after.get("name")))
            )
        if before.get("class") == "IfcSpace":
            for attribute in ("long_name", "object_type"):
                if before.get(attribute) != after.get(attribute):
                    errors.append(f"stage1.ifc:space_{attribute}_changed:{global_id}")
    expected_rename = [(TARGET_SPACE_GLOBAL_ID, "IfcSpace", "CONSULT-1", "CONSULT")]
    if changed_names != expected_rename:
        errors.append(f"stage1.ifc:not_exact_single_requested_rename:{changed_names}")
    semantic_changes = [
        global_id
        for global_id in sorted(init_roots & stage_roots)
        if init_semantics.get(global_id) != stage_semantics.get(global_id)
    ]
    if semantic_changes:
        errors.append(f"stage1.ifc:unrequested_root_semantic_changes:{semantic_changes}")
    project_records = [record for record in stage_records.values() if record.get("class") == "IfcProject"]
    if len(project_records) != 1 or "EW2A02" not in project_records[0].get("description", ""):
        errors.append("stage1.ifc:project_revision_code_missing")
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
    if str(data.get("source_init_sha256", "")).lower() != SEED_SHA256:
        errors.append(f"{label}:source_init_sha256_mismatch")
    if data.get("ifc_root_global_id_count") != len(stage1_info.get("roots_by_id") or {}):
        errors.append(f"{label}:ifc_root_global_id_count_mismatch")
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
    authoring_values = [str(value) for value in find_values(data, "authoring_software")]
    if not any(
        "27" in value and ("graphisoft" in value.lower() or "archicad" in value.lower())
        for value in authoring_values
    ):
        errors.append(f"{label}:missing_archicad_27_authoring_software")

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
        expected_zone_by_space = dict(zip(required_spaces, required_zones))
        if norm(name) in {norm(value) for value in required_spaces}:
            canonical_name = next(value for value in required_spaces if norm(value) == norm(name))
            if str(zone) != expected_zone_by_space[canonical_name]:
                errors.append(f"{label}:space_zone_mapping_mismatch:{name}:{zone}")
        stage_spaces = {
            norm(record.get("name")): global_id
            for global_id, record in (stage1_info.get("roots_by_id") or {}).items()
            if record.get("class") == "IfcSpace"
        }
        reported_global_id = str(rec.get("ifc_global_id") or "")
        if reported_global_id != stage_spaces.get(norm(name), ""):
            errors.append(f"{label}:space_global_id_mismatch:{name}")
        area = rec.get("floor_area_m2") or rec.get("area_m2") or rec.get("net_floor_area_m2")
        try:
            numeric_area = float(area)
            if numeric_area <= 0:
                errors.append(f"{label}:space_area_nonpositive:{name}")
        except Exception:
            errors.append(f"{label}:space_area_invalid:{name}")
            numeric_area = None
        if numeric_area is not None:
            ifc_area = (stage1_info.get("space_areas") or {}).get(norm(name))
            if ifc_area is None:
                errors.append(f"{label}:space_missing_in_stage1_geometry:{name}")
            elif abs(numeric_area - ifc_area) > max(0.1, ifc_area * 0.02):
                errors.append(f"{label}:space_area_mismatch_stage1:{name}:{numeric_area:.3f}!={ifc_area:.3f}")
        for count_key in ("door_count", "window_count"):
            try:
                raw_count = rec.get(count_key)
                count_value = float(raw_count)
                if isinstance(raw_count, bool) or count_value < 0 or not count_value.is_integer():
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{label}:space_invalid_{count_key}:{name}")
    try:
        record_area_total = sum(float(rec.get("floor_area_m2")) for rec in records)
        reported_building_area = float(data.get("building_area_m2"))
        if abs(record_area_total - reported_building_area) > max(0.1, record_area_total * 0.02):
            errors.append(
                f"{label}:building_area_mismatch_space_records:"
                f"{reported_building_area:.3f}!={record_area_total:.3f}"
            )
    except (TypeError, ValueError):
        errors.append(f"{label}:missing_or_invalid_building_area_m2")
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
        top_level = data.get(count_key)
        try:
            if int(top_level) != actual_total:
                errors.append(f"{label}:top_level_{count_key}_mismatch_stage1:{top_level}!={actual_total}")
        except (TypeError, ValueError):
            errors.append(f"{label}:missing_or_invalid_top_level_{count_key}")
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


def parse_iso_datetime(value: Any) -> datetime | None:
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})",
        str(value),
    )
    if match is None:
        return None
    fraction = (match.group(2) or "0").ljust(6, "0")[:6]
    offset = "+00:00" if match.group(3) == "Z" else match.group(3)
    try:
        parsed = datetime.fromisoformat(f"{match.group(1)}.{fraction}{offset}")
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc)


def check_native_stage_log(
    path: Path,
    init_path: Path,
    stage1_path: Path,
    handoff_path: Path,
    stage1_info: Dict[str, Any],
    errors: List[str],
) -> None:
    data = load_json(path)
    if data.get("case_id") != CASE_SPEC["case_id"] or data.get("software_stage") != "archicad":
        errors.append("native_stage_log:case_or_stage_mismatch")
    process = data.get("command_server_process")
    if not isinstance(process, dict):
        errors.append("native_stage_log:missing_command_server_process")
    else:
        executable = str(process.get("executable_path", "")).replace("/", "\\").lower()
        if executable != r"c:\program files\graphisoft\archicad 27\ifccommandserverapp.exe":
            errors.append("native_stage_log:wrong_archicad_executable_path")
        if str(process.get("executable_sha256", "")).lower() != ARCHICAD_EXE_SHA256:
            errors.append("native_stage_log:wrong_archicad_executable_sha256")
        if not str(process.get("product_version", "")).startswith("27.0.0"):
            errors.append("native_stage_log:wrong_archicad_product_version")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("native_stage_log:missing_artifact_hashes")
    else:
        for name, artifact_path in (
            ("init.ifc", init_path),
            ("stage1.ifc", stage1_path),
            ("handoff.json", handoff_path),
        ):
            record = artifacts.get(name)
            if not isinstance(record, dict) or str(record.get("sha256", "")).lower() != sha256_file(artifact_path):
                errors.append(f"native_stage_log:artifact_hash_mismatch:{name}")

    preservation = data.get("preservation_evidence")
    if not isinstance(preservation, dict):
        errors.append("native_stage_log:missing_preservation_evidence")
    else:
        expected_root_count = len(stage1_info.get("roots_by_id") or {})
        if preservation.get("init_seed_sha256") != SEED_SHA256:
            errors.append("native_stage_log:seed_hash_mismatch")
        if preservation.get("source_stage1_sha256") != sha256_file(stage1_path):
            errors.append("native_stage_log:stage1_hash_mismatch")
        if preservation.get("ifc_root_global_id_count") != expected_root_count:
            errors.append("native_stage_log:root_count_mismatch")
        if preservation.get("seed_and_stage1_global_id_sets_equal") is not True:
            errors.append("native_stage_log:root_preservation_not_confirmed")
        rename = preservation.get("unique_requested_space_rename")
        expected_rename = {
            "global_id": TARGET_SPACE_GLOBAL_ID,
            "before": "CONSULT-1",
            "after": "CONSULT",
        }
        if rename != expected_rename:
            errors.append("native_stage_log:rename_evidence_mismatch")

    transaction_section = data.get("command_transactions")
    transactions = transaction_section.get("value") if isinstance(transaction_section, dict) else None
    if not isinstance(transactions, list) or len(transactions) < 4:
        errors.append("native_stage_log:transactions_missing")
        return
    if transaction_section.get("Count") != len(transactions):
        errors.append("native_stage_log:declared_transaction_count_mismatch")
    methods = [item.get("request", {}).get("method") for item in transactions]
    if methods[0] != "Model.LoadFile" or methods[-1] != "Model.SaveFile":
        errors.append("native_stage_log:load_save_order_mismatch")
    completed_times: List[datetime] = []
    for index, transaction in enumerate(transactions):
        request = transaction.get("request")
        response = transaction.get("response")
        if transaction.get("status") != 200 or not isinstance(request, dict) or not isinstance(response, dict):
            errors.append(f"native_stage_log:transaction_not_successful:{index}")
            continue
        if response.get("jsonrpc") != "2.0":
            errors.append(f"native_stage_log:response_jsonrpc_mismatch:{index}")
        if response.get("id") != request.get("id"):
            errors.append(f"native_stage_log:response_id_mismatch:{index}")
        if "error" in response or "result" not in response:
            errors.append(f"native_stage_log:jsonrpc_error_response:{index}")
        started = parse_iso_datetime(transaction.get("started_at_utc"))
        completed = parse_iso_datetime(transaction.get("completed_at_utc"))
        if started is None or completed is None or completed < started:
            errors.append(f"native_stage_log:invalid_transaction_timestamps:{index}")
        else:
            if completed_times and started < completed_times[-1]:
                errors.append(f"native_stage_log:overlapping_transaction_timestamps:{index}")
            completed_times.append(completed)

    load_request = transactions[0].get("request", {})
    load_params = load_request.get("params")
    expected_init_location = r"C:\Users\user\Desktop\init.ifc"
    if not isinstance(load_params, dict) or str(load_params.get("location", "")).replace("/", "\\").lower() != expected_init_location.lower():
        errors.append("native_stage_log:load_request_path_mismatch")
    load_response = transactions[0].get("response", {})
    if Path(str(load_response.get("result", "")).replace("\\", "/")).name.lower() != "init.ifc":
        errors.append("native_stage_log:load_result_mismatch")

    modify_transactions = [
        item for item in transactions
        if item.get("request", {}).get("method") == "Entity.Modify"
    ]

    def entity_parts(item: Dict[str, Any], entity_class: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        params = item.get("request", {}).get("params", {})
        selector = params.get("select", {}).get(entity_class, {})
        update = params.get("EntityData", {}).get(entity_class, {})
        return selector if isinstance(selector, dict) else {}, update if isinstance(update, dict) else {}

    rename_candidates = []
    for item in modify_transactions:
        selector, update = entity_parts(item, "IfcSpace")
        targets_space = (
            selector.get("GlobalId") == TARGET_SPACE_GLOBAL_ID
            or norm(selector.get("Name")) == norm("CONSULT-1")
        )
        if targets_space and norm(update.get("Name")) == norm("CONSULT"):
            rename_candidates.append(item)
    if len(rename_candidates) != 1:
        errors.append("native_stage_log:rename_request_mismatch")

    project_records_by_id = {
        global_id: record
        for global_id, record in (stage1_info.get("roots_by_id") or {}).items()
        if record.get("class") == "IfcProject"
    }
    project_records = list(project_records_by_id.values())
    expected_project_name = project_records[0].get("name") if len(project_records) == 1 else None
    expected_project_description = project_records[0].get("description") if len(project_records) == 1 else None
    expected_project_ids = set(project_records_by_id)
    project_candidates = []
    for item in modify_transactions:
        selector, update = entity_parts(item, "IfcProject")
        targets_project = (
            selector.get("GlobalId") in expected_project_ids
            or (expected_project_name is not None and selector.get("Name") == expected_project_name)
        )
        description = update.get("Description")
        if targets_project and description == expected_project_description and "EW2A02" in str(description):
            project_candidates.append(item)
    if len(project_candidates) != 1:
        errors.append("native_stage_log:project_revision_request_missing")

    modify_results = [
        item.get("response", {}).get("result")
        for item in rename_candidates + project_candidates
    ]
    if (
        len(modify_results) != 2
        or any(re.fullmatch(r"[1-9]\d*", str(result or "")) is None for result in modify_results)
        or len(set(modify_results)) != len(modify_results)
    ):
        errors.append("native_stage_log:modify_result_invalid")

    save_params = transactions[-1].get("request", {}).get("params")
    expected_stage_location = r"C:\Users\user\Desktop\stage1.ifc"
    if not isinstance(save_params, dict) or str(save_params.get("location", "")).replace("/", "\\").lower() != expected_stage_location.lower():
        errors.append("native_stage_log:save_request_path_mismatch")

    commands = data.get("archicad_api_commands")
    if commands != [transaction.get("request") for transaction in transactions]:
        errors.append("native_stage_log:api_command_list_mismatch")


def check_workflow_and_weather(
    workflow_path: Path,
    weather_path: Path,
    stage1_path: Path,
    handoff_path: Path,
    errors: List[str],
) -> None:
    workflow = load_json(workflow_path)
    if not str(workflow.get("osw_version", "")).startswith("3.10"):
        errors.append("workflow.osw:wrong_version")
    if Path(str(workflow.get("seed_file", ""))).name.lower() != "result.osm":
        errors.append("workflow.osw:wrong_seed_file")
    if Path(str(workflow.get("weather_file", ""))).name.lower() != "weather.epw":
        errors.append("workflow.osw:wrong_weather_file")
    if Path(str(workflow.get("run_directory", ""))).name.lower() != "run":
        errors.append("workflow.osw:wrong_run_directory")
    if str(workflow.get("source_stage1_sha256", "")).lower() != sha256_file(stage1_path):
        errors.append("workflow.osw:stage1_hash_mismatch")
    if str(workflow.get("source_handoff_sha256", "")).lower() != sha256_file(handoff_path):
        errors.append("workflow.osw:handoff_hash_mismatch")

    lines = weather_path.read_text(encoding="utf-8-sig", errors="strict").splitlines()
    if len(lines) < 8 or not lines[0].upper().startswith("LOCATION,"):
        errors.append("weather.epw:missing_location_header")
        return
    hourly_rows = [line for line in lines[8:] if line.strip()]
    if len(hourly_rows) != 8760:
        errors.append(f"weather.epw:hourly_row_count:{len(hourly_rows)}!=8760")
        return
    dry_bulbs: List[float] = []
    for index, line in enumerate(hourly_rows):
        fields = line.split(",")
        if len(fields) < 35:
            errors.append(f"weather.epw:short_hourly_row:{index}")
            break
        try:
            month, day, hour = int(fields[1]), int(fields[2]), int(fields[3])
            dry_bulbs.append(float(fields[6]))
        except (TypeError, ValueError, IndexError):
            errors.append(f"weather.epw:invalid_hourly_row:{index}")
            break
        if not (1 <= month <= 12 and 1 <= day <= 31 and 1 <= hour <= 24):
            errors.append(f"weather.epw:invalid_timestamp:{index}")
            break
    if dry_bulbs and max(dry_bulbs) - min(dry_bulbs) < 5.0:
        errors.append("weather.epw:implausible_temperature_series")


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


def positive_load_density(
    definition: Dict[str, str],
    load_type: str,
    floor_area: float,
) -> float | None:
    if load_type == "OS:PEOPLE":
        people_per_area = osm_number(definition, "People per Space Floor Area") or 0.0
        area_per_person = osm_number(definition, "Space Floor Area per Person") or 0.0
        absolute_people = osm_number(definition, "Number of People") or 0.0
        if people_per_area > 0:
            return people_per_area
        if area_per_person > 0:
            return 1.0 / area_per_person
        if absolute_people > 0 and floor_area > 0:
            return absolute_people / floor_area
        return None

    per_area = osm_number(definition, "Watts per Space Floor Area") or 0.0
    absolute = osm_number(
        definition,
        "Lighting Level" if load_type == "OS:LIGHTS" else "Design Level",
    ) or 0.0
    per_person = osm_number(definition, "Watts per Person") or 0.0
    if per_area > 0:
        return per_area
    if absolute > 0 and floor_area > 0:
        return absolute / floor_area
    if per_person > 0:
        return per_person
    return None


def osm_vertices(
    obj: Dict[str, str],
    space: Dict[str, str] | None = None,
) -> List[Tuple[float, float, float]]:
    indexed: List[Tuple[int, Tuple[float, float, float]]] = []
    for key, value in obj.items():
        match = re.fullmatch(r"X-Y-Z-VERTEX-(\d+)", key)
        if match is None:
            continue
        try:
            coordinates = tuple(float(part.strip()) for part in value.split(","))
        except ValueError:
            continue
        if len(coordinates) >= 3:
            indexed.append((int(match.group(1)), coordinates[:3]))
    indexed.sort(key=lambda item: item[0])
    points = [point for _, point in indexed]
    if space is None:
        return points
    origin_x = osm_number(space, "X Origin") or 0.0
    origin_y = osm_number(space, "Y Origin") or 0.0
    origin_z = osm_number(space, "Z Origin") or 0.0
    angle = math.radians(osm_number(space, "Direction of Relative North") or 0.0)
    cosine, sine = math.cos(angle), math.sin(angle)
    return [
        (
            origin_x + cosine * x - sine * y,
            origin_y + sine * x + cosine * y,
            origin_z + z,
        )
        for x, y, z in points
    ]


def polygon_area_3d(points: List[Tuple[float, float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    normal = [0.0, 0.0, 0.0]
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        normal[0] += (point[1] - following[1]) * (point[2] + following[2])
        normal[1] += (point[2] - following[2]) * (point[0] + following[0])
        normal[2] += (point[0] - following[0]) * (point[1] + following[1])
    return 0.5 * math.sqrt(sum(component * component for component in normal))


def rounded_point(point: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return tuple(round(coordinate, 6) for coordinate in point)


def reversed_polygons_match(
    first: List[Tuple[float, float, float]],
    second: List[Tuple[float, float, float]],
) -> bool:
    if len(first) != len(second) or len(first) < 3:
        return False
    canonical_first = [rounded_point(point) for point in first]
    reversed_second = list(reversed([rounded_point(point) for point in second]))
    return any(
        canonical_first == reversed_second[offset:] + reversed_second[:offset]
        for offset in range(len(reversed_second))
    )


def schedule_day_profile(day: Dict[str, str]) -> List[Tuple[int, float]] | None:
    profile: List[Tuple[int, float]] = []
    for index in range(1, 100):
        hour_key = norm(f"Hour {index}")
        minute_key = norm(f"Minute {index}")
        value_key = norm(f"Value Until Time {index}")
        if hour_key not in day:
            break
        try:
            minute_of_day = int(float(day[hour_key])) * 60 + int(float(day.get(minute_key, "0")))
            value = float(day[value_key])
        except (KeyError, TypeError, ValueError):
            return None
        if minute_of_day <= 0 or minute_of_day > 1440 or not (0.0 <= value <= 1.0):
            return None
        profile.append((minute_of_day, value))
    if not profile or profile[-1][0] != 1440 or any(profile[i][0] <= profile[i - 1][0] for i in range(1, len(profile))):
        return None
    return profile


def effective_weekday_profiles(
    schedule_handle: str,
    rulesets_by_handle: Dict[str, Dict[str, str]],
    rules: List[Dict[str, str]],
    days_by_handle: Dict[str, Dict[str, str]],
) -> Dict[str, List[Tuple[int, float]]] | None:
    ruleset = rulesets_by_handle.get(schedule_handle)
    if ruleset is None:
        return None
    default_profile = schedule_day_profile(
        days_by_handle.get(ruleset.get("DEFAULT-DAY-SCHEDULE-NAME", ""), {})
    )
    if default_profile is None:
        return None
    profiles: Dict[str, List[Tuple[int, float]]] = {}
    for weekday in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"):
        candidates: List[Tuple[int, Dict[str, str]]] = []
        for rule in rules:
            if rule.get("SCHEDULE-RULESET-NAME") != schedule_handle:
                continue
            if norm(rule.get(f"APPLY-{weekday}", "")) != "YES":
                continue
            try:
                order = int(float(rule.get("RULE-ORDER", "999999")))
            except ValueError:
                order = 999999
            candidates.append((order, rule))
        if candidates:
            rule = min(candidates, key=lambda item: item[0])[1]
            profile = schedule_day_profile(days_by_handle.get(rule.get("DAY-SCHEDULE-NAME", ""), {}))
            if profile is None:
                return None
            profiles[weekday] = profile
        else:
            profiles[weekday] = default_profile
    return profiles


def check_osm(
    path: Path,
    handoff_hash: str,
    handoff_data: Dict[str, Any],
    required_spaces: List[str],
    required_zones: List[str],
    required_tokens: List[str],
    flow_tokens: List[str],
    errors: List[str],
) -> Dict[str, Any]:
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
    handles = {
        obj.get("HANDLE", ""): obj
        for obj in objects
        if obj.get("HANDLE")
    }

    space_objects = by_type.get("OS:SPACE", [])
    zone_objects = by_type.get("OS:THERMALZONE", [])
    spaces_by_name = {norm(obj.get("NAME")): obj for obj in space_objects}
    zones_by_name = {norm(obj.get("NAME")): obj for obj in zone_objects}
    handoff_records = {
        norm(record.get("name")): record
        for record in extract_space_records(handoff_data, [], "handoff.json")
    }
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
            try:
                floor_area = float(handoff_records[norm(space_name)]["floor_area_m2"])
            except (KeyError, TypeError, ValueError):
                floor_area = 0.0
            densities: List[float] = []
            schedules: List[str] = []
            for assignment in matches:
                definition = definitions.get(assignment.get(definition_key))
                density = positive_load_density(definition or {}, load_type, floor_area)
                if definition is None or density is None:
                    errors.append(f"result.osm:invalid_{definition_type.lower()}_magnitude:{space_name}")
                    continue
                schedule = assignment.get(schedule_key, "")
                if not schedule or schedule not in handles:
                    errors.append(f"result.osm:missing_load_schedule_link:{load_type}:{space_name}")
                    continue
                densities.append(density)
                schedules.append(schedule)
            if densities:
                per_space[norm(space_name)] = (sum(densities), schedules)
        load_values[load_type] = per_space

    waiting_people = load_values.get("OS:PEOPLE", {}).get(norm("WAITING"))
    consult_people = load_values.get("OS:PEOPLE", {}).get(norm("CONSULT"))
    if waiting_people and consult_people:
        if waiting_people[0] <= consult_people[0]:
            errors.append("result.osm:waiting_people_density_not_higher_than_consult")
        if waiting_people[1][0] == consult_people[1][0]:
            errors.append("result.osm:waiting_and_consult_people_schedules_not_distinct")
    schedule_profiles: Dict[str, Dict[str, List[Tuple[int, float]]]] = {}
    schedule_rulesets = {
        obj.get("HANDLE", ""): obj
        for obj in by_type.get("OS:SCHEDULE:RULESET", [])
    }
    schedule_rules = by_type.get("OS:SCHEDULE:RULE", [])
    schedule_days = {obj.get("HANDLE", ""): obj for obj in by_type.get("OS:SCHEDULE:DAY", [])}
    for space_name, load in (("WAITING", waiting_people), ("CONSULT", consult_people)):
        if not load:
            continue
        profile = effective_weekday_profiles(
            load[1][0], schedule_rulesets, schedule_rules, schedule_days
        )
        if profile is None:
            errors.append(f"result.osm:missing_effective_monday_friday_profile:{space_name}")
        else:
            schedule_profiles[space_name] = profile
    if schedule_profiles.get("WAITING") == schedule_profiles.get("CONSULT"):
        errors.append("result.osm:waiting_and_consult_effective_profiles_equal")

    outdoor_air = {obj.get("HANDLE"): obj for obj in by_type.get("OS:DESIGNSPECIFICATION:OUTDOORAIR", [])}
    for space_name in required_spaces:
        space_obj = spaces_by_name.get(norm(space_name))
        if space_obj is None:
            continue
        oa = outdoor_air.get(space_obj.get("DESIGN-SPECIFICATION-OUTDOOR-AIR-OBJECT-NAME"))
        per_person = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-PER-PERSON") or 0.0
        per_area = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-PER-FLOOR-AREA") or 0.0
        absolute_rate = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-RATE") or 0.0
        air_changes = osm_number(oa or {}, "OUTDOOR-AIR-FLOW-AIR-CHANGES-PER-HOUR") or 0.0
        if oa is None or max(per_person, per_area, absolute_rate, air_changes) <= 0:
            errors.append(f"result.osm:missing_positive_outdoor_air:{space_name}")

    thermostat_handles = {obj.get("HANDLE") for obj in by_type.get("OS:THERMOSTATSETPOINT:DUALSETPOINT", [])}
    ideal_handles = {obj.get("HANDLE") for obj in by_type.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM", [])}
    ideal_objects = {obj.get("HANDLE"): obj for obj in by_type.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM", [])}
    equipment_lists = by_type.get("OS:ZONEHVAC:EQUIPMENTLIST", [])
    ideal_by_zone: Dict[str, List[str]] = {}
    for zone_name in required_zones:
        zone_obj = zones_by_name.get(norm(zone_name))
        if zone_obj is None:
            continue
        if zone_obj.get("THERMOSTAT-NAME") not in thermostat_handles:
            errors.append(f"result.osm:missing_thermostat_link:{zone_name}")
        matching_ideals: List[str] = []
        for equipment_list in equipment_lists:
            if equipment_list.get("THERMAL-ZONE") != zone_obj.get("HANDLE"):
                continue
            for field, equipment_handle in equipment_list.items():
                match = re.fullmatch(r"ZONE-EQUIPMENT-(\d+)", field)
                if match is None or equipment_handle not in ideal_handles:
                    continue
                slot = match.group(1)
                cooling_sequence = osm_number(
                    equipment_list, f"Zone Equipment Cooling Sequence {slot}"
                )
                heating_sequence = osm_number(
                    equipment_list, f"Zone Equipment Heating or No-Load Sequence {slot}"
                )
                if (
                    cooling_sequence is None
                    or heating_sequence is None
                    or cooling_sequence <= 0
                    or heating_sequence <= 0
                    or not cooling_sequence.is_integer()
                    or not heating_sequence.is_integer()
                ):
                    errors.append(
                        f"result.osm:invalid_ideal_loads_sequence:{zone_name}:slot_{slot}"
                    )
                    continue
                matching_ideals.append(equipment_handle)
        matching_ideals = list(dict.fromkeys(matching_ideals))
        if not matching_ideals:
            errors.append(f"result.osm:missing_ideal_loads_link:{zone_name}")
        else:
            ideal_by_zone[zone_name] = [
                ideal_objects[handle].get("NAME", "")
                for handle in matching_ideals
            ]

    weather_files = by_type.get("OS:WEATHERFILE", [])
    if not weather_files or not weather_files[0].get("URL", "").lower().endswith(".epw"):
        errors.append("result.osm:missing_epw_weather_file_object")

    construction_handles = {obj.get("HANDLE") for obj in by_type.get("OS:CONSTRUCTION", [])}
    surfaces = by_type.get("OS:SURFACE", [])
    surfaces_by_handle = {obj.get("HANDLE", ""): obj for obj in surfaces}
    spaces_by_handle = {obj.get("HANDLE", ""): obj for obj in space_objects}
    required_space_names = {norm(name) for name in required_spaces}
    surface_geometry: Dict[str, List[Tuple[float, float, float]]] = {}
    for surface in surfaces:
        if surface.get("CONSTRUCTION-NAME") not in construction_handles:
            errors.append(f"result.osm:surface_missing_construction:{surface.get('NAME')}")
        space_obj = spaces_by_handle.get(surface.get("SPACE-NAME", ""))
        points = osm_vertices(surface, space_obj)
        surface_geometry[surface.get("HANDLE", "")] = points
        if space_obj and norm(space_obj.get("NAME")) in required_space_names:
            if len(points) < 3 or len({rounded_point(point) for point in points}) != len(points):
                errors.append(f"result.osm:invalid_surface_vertices:{surface.get('NAME')}")
            elif polygon_area_3d(points) <= 1e-6:
                errors.append(f"result.osm:zero_area_surface:{surface.get('NAME')}")

    floor_areas: Dict[str, float] = {}
    for surface in surfaces:
        if norm(surface.get("SURFACE-TYPE")) != "FLOOR":
            continue
        points = surface_geometry.get(surface.get("HANDLE", ""), [])
        area = polygon_area_xy([(point[0], point[1]) for point in points])
        space_handle = surface.get("SPACE-NAME", "")
        floor_areas[space_handle] = floor_areas.get(space_handle, 0.0) + area
    for space_name in required_spaces:
        space_obj = spaces_by_name.get(norm(space_name))
        record = handoff_records.get(norm(space_name))
        if space_obj is None or record is None:
            continue
        try:
            expected_area = float(record.get("floor_area_m2"))
        except (TypeError, ValueError):
            continue
        actual_area = floor_areas.get(space_obj.get("HANDLE", ""))
        if actual_area is None or abs(actual_area - expected_area) > max(0.1, expected_area * 0.02):
            errors.append(f"result.osm:floor_area_mismatch_handoff:{space_name}:{actual_area}!={expected_area}")

        space_surfaces = [
            surface
            for surface in surfaces
            if surface.get("SPACE-NAME") == space_obj.get("HANDLE")
        ]
        surface_types = {norm(surface.get("SURFACE-TYPE")) for surface in space_surfaces}
        if "FLOOR" not in surface_types or "ROOFCEILING" not in surface_types:
            errors.append(f"result.osm:space_missing_floor_or_roof:{space_name}")
        edge_counts: Dict[
            Tuple[Tuple[float, float, float], Tuple[float, float, float]], int
        ] = {}
        for surface in space_surfaces:
            points = surface_geometry.get(surface.get("HANDLE", ""), [])
            if len(points) < 3:
                continue
            for index, point in enumerate(points):
                first = rounded_point(point)
                second = rounded_point(points[(index + 1) % len(points)])
                edge = tuple(sorted((first, second)))
                edge_counts[edge] = edge_counts.get(edge, 0) + 1
        if not edge_counts or any(count != 2 for count in edge_counts.values()):
            errors.append(f"result.osm:space_geometry_not_closed:{space_name}")

    reciprocal_surface_spaces: Set[Tuple[str, str]] = set()
    for surface in surfaces:
        if norm(surface.get("OUTSIDE-BOUNDARY-CONDITION")) != "SURFACE":
            continue
        adjacent = surfaces_by_handle.get(surface.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT", ""))
        if adjacent is None or adjacent.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT") != surface.get("HANDLE"):
            errors.append(f"result.osm:interior_surface_not_reciprocal:{surface.get('NAME')}")
            continue
        if not reversed_polygons_match(
            surface_geometry.get(surface.get("HANDLE", ""), []),
            surface_geometry.get(adjacent.get("HANDLE", ""), []),
        ):
            errors.append(f"result.osm:interior_surface_geometry_not_reversed:{surface.get('NAME')}")
        first_space = spaces_by_handle.get(surface.get("SPACE-NAME", ""))
        second_space = spaces_by_handle.get(adjacent.get("SPACE-NAME", ""))
        if first_space and second_space:
            reciprocal_surface_spaces.add(
                tuple(sorted((norm(first_space.get("NAME")), norm(second_space.get("NAME")))))
            )
    required_surface_pair = tuple(sorted((norm("WAITING"), norm("CONSULT"))))
    if required_surface_pair not in reciprocal_surface_spaces:
        errors.append("result.osm:missing_reciprocal_waiting_consult_surface_pair")

    subsurfaces = by_type.get("OS:SUBSURFACE", [])
    door_objects = [obj for obj in subsurfaces if "DOOR" in norm(obj.get("SUB-SURFACE-TYPE"))]
    window_objects = [obj for obj in subsurfaces if "WINDOW" in norm(obj.get("SUB-SURFACE-TYPE"))]
    door_pairs: Set[Tuple[str, str]] = set()
    door_pair_spaces: Set[str] = set()
    for door in door_objects:
        handle = door.get("HANDLE", "")
        adjacent = door.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT", "")
        adjacent_door = handles.get(adjacent)
        if handle and adjacent_door and adjacent_door.get("OBJECT_TYPE") == "OS:SUBSURFACE" and adjacent_door.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT") == handle:
            door_pairs.add(tuple(sorted((handle, adjacent))))
        else:
            errors.append(f"result.osm:door_not_mutually_adjacent:{door.get('NAME')}")
            continue
        parent = surfaces_by_handle.get(door.get("SURFACE-NAME", ""))
        adjacent_parent = surfaces_by_handle.get(adjacent_door.get("SURFACE-NAME", ""))
        if not parent or not adjacent_parent:
            errors.append(f"result.osm:door_missing_parent_surface:{door.get('NAME')}")
            continue
        if norm(parent.get("OUTSIDE-BOUNDARY-CONDITION")) != "SURFACE" or norm(adjacent_parent.get("OUTSIDE-BOUNDARY-CONDITION")) != "SURFACE":
            errors.append(f"result.osm:door_not_on_interior_surfaces:{door.get('NAME')}")
        if parent.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT") != adjacent_parent.get("HANDLE") or adjacent_parent.get("OUTSIDE-BOUNDARY-CONDITION-OBJECT") != parent.get("HANDLE"):
            errors.append(f"result.osm:door_parent_surfaces_not_mutually_adjacent:{door.get('NAME')}")
        parent_space = spaces_by_handle.get(parent.get("SPACE-NAME", ""))
        adjacent_space = spaces_by_handle.get(adjacent_parent.get("SPACE-NAME", ""))
        if door.get("CONSTRUCTION-NAME") not in construction_handles:
            errors.append(f"result.osm:door_missing_construction:{door.get('NAME')}")
        if not reversed_polygons_match(
            osm_vertices(door, parent_space),
            osm_vertices(adjacent_door, adjacent_space),
        ):
            errors.append(f"result.osm:door_geometry_not_reversed:{door.get('NAME')}")
        if parent_space:
            door_pair_spaces.add(norm(parent_space.get("NAME")))
        if adjacent_space:
            door_pair_spaces.add(norm(adjacent_space.get("NAME")))
    logical_door_count = len(door_pairs)
    if logical_door_count < 1:
        errors.append("result.osm:missing_matched_door_pair")
    if door_pair_spaces != {norm("WAITING"), norm("CONSULT")}:
        errors.append("result.osm:door_pair_not_between_waiting_and_consult")

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
        "subsurface_count": len(subsurfaces),
        "door_count": logical_door_count,
        "window_count": len(window_objects),
        "people_count": len(by_type.get("OS:PEOPLE", [])),
        "lights_count": len(by_type.get("OS:LIGHTS", [])),
        "equipment_count": len(by_type.get("OS:ELECTRICEQUIPMENT", [])),
        "outdoor_air_count": len(by_type.get("OS:DESIGNSPECIFICATION:OUTDOORAIR", [])),
        "thermostat_count": len(by_type.get("OS:THERMOSTATSETPOINT:DUALSETPOINT", [])),
        "ideal_loads_count": len(by_type.get("OS:ZONEHVAC:IDEALLOADSAIRSYSTEM", [])),
        "space_zone_map": dict(zip(required_spaces, required_zones)),
        "ideal_by_zone": ideal_by_zone,
        "floor_areas": {
            space_name: floor_areas.get(spaces_by_name.get(norm(space_name), {}).get("HANDLE", ""))
            for space_name in required_spaces
        },
        "schedule_profiles": schedule_profiles,
    }
    for key in ("space_count", "zone_count"):
        if counts[key] != 2:
            errors.append(f"result.osm:required_object_count_not_two:{key}:{counts[key]}")
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
        if rounded != osm_counts.get(key, -1):
            errors.append(f"flow_report:{key}_mismatch_osm:{rounded}!={osm_counts.get(key)}")
    wwr = first_number(data, "window_wall_ratio")
    if wwr is not None and not (0.0 <= wwr <= 0.95):
        errors.append("flow_report:window_wall_ratio_out_of_range")
    status_values = [str(value) for value in find_values(data, "energyplus_status")]
    if not any("completed successfully" in value.lower() for value in status_values):
        errors.append("flow_report:energyplus_not_completed_successfully")
    for key in ("energyplus_severe_errors", "energyplus_fatal_errors"):
        value = first_number(data, key)
        if value is None or value != 0:
            errors.append(f"flow_report:{key}_not_zero")
    object_counts = next(
        (value for value in find_values(data, "model_object_counts") if isinstance(value, dict)),
        None,
    )
    if object_counts is None:
        errors.append("flow_report:missing_model_object_counts")
    else:
        normalized = {norm(key): value for key, value in object_counts.items()}
        expected_counts = {
            "People": osm_counts.get("people_count"),
            "Lights": osm_counts.get("lights_count"),
            "ElectricEquipment": osm_counts.get("equipment_count"),
            "DesignSpecificationOutdoorAir": osm_counts.get("outdoor_air_count"),
            "ThermostatSetpointDualSetpoint": osm_counts.get("thermostat_count"),
            "ZoneHVACIdealLoadsAirSystem": osm_counts.get("ideal_loads_count"),
        }
        for name, expected in expected_counts.items():
            try:
                reported = int(normalized[norm(name)])
            except (KeyError, TypeError, ValueError):
                errors.append(f"flow_report:missing_or_invalid_model_object_count:{name}")
                continue
            if reported != expected:
                errors.append(f"flow_report:model_object_count_mismatch:{name}:{reported}!={expected}")
    return data


def check_flow_dependencies(
    data: Dict[str, Any],
    paths: Dict[str, Path],
    osm_state: Dict[str, Any],
    errors: List[str],
) -> None:
    expected_hashes = {
        "consumed_handoff_sha256": paths["handoff.json"],
        "source_stage1_sha256": paths["stage1.ifc"],
        "osm_sha256": paths["result.osm"],
        "workflow_sha256": paths["workflow.osw"],
        "weather_sha256": paths["weather.epw"],
        "energyplus_sql_sha256": paths["run/eplusout.sql"],
        "energyplus_err_sha256": paths["run/eplusout.err"],
        "energyplus_end_sha256": paths["run/eplusout.end"],
    }
    for key, artifact in expected_hashes.items():
        if str(data.get(key, "")).lower() != sha256_file(artifact):
            errors.append(f"flow_report:top_level_hash_mismatch:{key}")
    if data.get("case_id") != CASE_SPEC["case_id"]:
        errors.append("flow_report:case_id_mismatch")
    if data.get("software_chain") != ["archicad", "openstudio", "energyplus"]:
        errors.append("flow_report:software_chain_mismatch")
    expected_counts = {
        "room_count": osm_state.get("space_count"),
        "thermal_zone_count": osm_state.get("zone_count"),
        "door_count": osm_state.get("door_count"),
        "window_count": osm_state.get("window_count"),
        "surface_count": osm_state.get("surface_count"),
        "subsurface_count": osm_state.get("subsurface_count"),
    }
    for key, expected in expected_counts.items():
        if data.get(key) != expected:
            errors.append(f"flow_report:top_level_count_mismatch:{key}:{data.get(key)}!={expected}")
    if data.get("window_wall_ratio") != 0.0:
        errors.append("flow_report:window_wall_ratio_must_be_zero")
    if data.get("weather_hourly_rows") != 8760:
        errors.append("flow_report:weather_hourly_rows_mismatch")
    if str(data.get("native_cli_executable", "")).replace("\\", "/").lower() != "c:/openstudio-3.10.0/bin/openstudio.exe":
        errors.append("flow_report:wrong_openstudio_executable")
    if str(data.get("native_cli_sha256", "")).lower() != OPENSTUDIO_EXE_SHA256:
        errors.append("flow_report:wrong_openstudio_executable_sha256")
    if str(data.get("energyplus_executable", "")).replace("\\", "/").lower() != "c:/openstudio-3.10.0/energyplus/energyplus.exe":
        errors.append("flow_report:wrong_energyplus_executable")
    if str(data.get("energyplus_executable_sha256", "")).lower() != ENERGYPLUS_EXE_SHA256:
        errors.append("flow_report:wrong_energyplus_executable_sha256")
    reported_profiles = data.get("schedule_profile_evidence")
    if not isinstance(reported_profiles, dict):
        errors.append("flow_report:missing_schedule_profile_evidence")
    else:
        for space_name, weekday_profiles in osm_state.get("schedule_profiles", {}).items():
            record = reported_profiles.get(space_name)
            if not isinstance(record, dict):
                errors.append(f"flow_report:invalid_schedule_profile_evidence:{space_name}")
                continue
            reported_by_weekday: Dict[str, List[Tuple[int, float]]] = {}
            try:
                if isinstance(record.get("weekday_profiles"), dict):
                    for weekday, pairs in record["weekday_profiles"].items():
                        reported_by_weekday[str(weekday).upper()] = [
                            (int(float(hour)) * 60, float(value))
                            for hour, value in pairs
                        ]
                else:
                    compressed = [
                        (int(float(hour)) * 60, float(value))
                        for hour, value in record["hour_value_pairs"]
                    ]
                    if record.get("applies") == "Monday-Friday":
                        reported_by_weekday = {
                            weekday: compressed
                            for weekday in ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")
                        }
            except (KeyError, TypeError, ValueError):
                reported_by_weekday = {}
            if reported_by_weekday != weekday_profiles:
                errors.append(f"flow_report:schedule_profile_mismatch_osm:{space_name}")

    transactions = data.get("openstudio_cli_transactions")
    if not isinstance(transactions, list) or len(transactions) < 3:
        errors.append("flow_report:missing_native_cli_transactions")
    else:
        expected_stages = {
            "openstudio_model_build",
            "openstudio_weather_period_simulation",
            "energyplus_native_verification_run",
        }
        if {record.get("stage") for record in transactions} != expected_stages:
            errors.append("flow_report:native_cli_transaction_stage_mismatch")
        for record in transactions:
            if record.get("exit_code") != 0:
                errors.append(f"flow_report:native_cli_nonzero_exit:{record.get('stage')}")
            started = parse_iso_datetime(record.get("started_at_utc"))
            completed = parse_iso_datetime(record.get("completed_at_utc"))
            if started is None or completed is None or completed < started:
                errors.append(f"flow_report:native_cli_invalid_timestamps:{record.get('stage')}")
            executable = str(record.get("executable", "")).replace("\\", "/").lower()
            if record.get("stage", "").startswith("openstudio_") and executable != "c:/openstudio-3.10.0/bin/openstudio.exe":
                errors.append(f"flow_report:wrong_transaction_executable:{record.get('stage')}")
            if record.get("stage") == "energyplus_native_verification_run":
                if executable != "c:/openstudio-3.10.0/energyplus/energyplus.exe" or str(record.get("executable_sha256", "")).lower() != ENERGYPLUS_EXE_SHA256:
                    errors.append("flow_report:wrong_native_energyplus_provenance")
    postprocess = data.get("native_openstudio_postprocess")
    if not isinstance(postprocess, dict) or postprocess.get("exit_code") != 0:
        errors.append("flow_report:missing_successful_native_openstudio_postprocess")
    else:
        executable = str(postprocess.get("executable", "")).replace("\\", "/").lower()
        if executable != "c:/openstudio-3.10.0/bin/openstudio.exe":
            errors.append("flow_report:wrong_postprocess_executable")


EXPECTED_ANNUAL_HOURS = {
    (month, day, hour, 0)
    for month, days in enumerate((0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31))
    if month
    for day in range(1, days + 1)
    for hour in range(1, 25)
}


def empty_sql_series_stats() -> Dict[str, Any]:
    return {
        "dictionary_indexes": set(),
        "row_count": 0,
        "time_indexes": set(),
        "timestamps": set(),
        "environment_indexes": set(),
        "warmup_flags": set(),
        "intervals": set(),
        "interval_types": set(),
        "total": 0.0,
        "peak": None,
    }


def collect_hourly_sql_series(connection: sqlite3.Connection) -> Dict[Tuple[str, str], Dict[str, Any]]:
    variables = tuple(variable for variable, _ in ENERGY_VARIABLES) + RATE_VARIABLES
    placeholders = ",".join("?" for _ in variables)
    series: Dict[Tuple[str, str], Dict[str, Any]] = {}
    dictionary_rows = connection.execute(
        f"""
        SELECT ReportDataDictionaryIndex, Name, KeyValue
        FROM ReportDataDictionary
        WHERE UPPER(Name) IN ({placeholders})
          AND UPPER(ReportingFrequency) = 'HOURLY'
        """,
        tuple(variable.upper() for variable in variables),
    ).fetchall()
    for dictionary_index, variable, key_value in dictionary_rows:
        key = (str(variable).upper(), str(key_value).upper())
        stats = series.setdefault(key, empty_sql_series_stats())
        stats["dictionary_indexes"].add(int(dictionary_index))

    rows = connection.execute(
        f"""
        SELECT rdd.Name, rdd.KeyValue, rdd.ReportDataDictionaryIndex,
               rd.TimeIndex, rd.Value, t.Month, t.Day, t.Hour, t.Minute,
               t.EnvironmentPeriodIndex, t.WarmupFlag, t.Interval, t.IntervalType
        FROM ReportDataDictionary rdd
        JOIN ReportData rd
          ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
        JOIN Time t
          ON rd.TimeIndex = t.TimeIndex
        WHERE UPPER(rdd.Name) IN ({placeholders})
          AND UPPER(rdd.ReportingFrequency) = 'HOURLY'
        """,
        tuple(variable.upper() for variable in variables),
    )
    for row in rows:
        key = (str(row[0]).upper(), str(row[1]).upper())
        stats = series.setdefault(key, empty_sql_series_stats())
        stats["dictionary_indexes"].add(int(row[2]))
        stats["row_count"] += 1
        stats["time_indexes"].add(int(row[3]))
        value = float(row[4])
        stats["total"] += value
        stats["peak"] = value if stats["peak"] is None else max(stats["peak"], value)
        stats["timestamps"].add((int(row[5]), int(row[6]), int(row[7]), int(row[8])))
        stats["environment_indexes"].add(int(row[9]))
        stats["warmup_flags"].add(int(row[10]))
        stats["intervals"].add(int(row[11]))
        stats["interval_types"].add(int(row[12]))
    return series


def sql_series_stats(
    series: Dict[Tuple[str, str], Dict[str, Any]],
    variable: str,
    key_value: str,
) -> Dict[str, Any]:
    collected = series.get((variable.upper(), key_value.upper()), empty_sql_series_stats())
    return {
        "dictionary_count": len(collected["dictionary_indexes"]),
        "row_count": collected["row_count"],
        "distinct_time_indexes": len(collected["time_indexes"]),
        "timestamps": collected["timestamps"],
        "environment_indexes": collected["environment_indexes"],
        "warmup_flags": collected["warmup_flags"],
        "intervals": collected["intervals"],
        "interval_types": collected["interval_types"],
        "total": collected["total"],
        "peak": collected["peak"] if collected["peak"] is not None else 0.0,
    }


def check_hourly_sql_series(
    stats: Dict[str, Any],
    weather_environment_index: int,
    label: str,
    errors: List[str],
) -> None:
    if stats["dictionary_count"] != 1:
        errors.append(f"eplusout.sql:hourly_dictionary_count:{label}:{stats['dictionary_count']}")
    if stats["row_count"] != 8760:
        errors.append(f"eplusout.sql:hourly_count:{label}:{stats['row_count']}")
    if stats["distinct_time_indexes"] != 8760:
        errors.append(
            f"eplusout.sql:hourly_distinct_time_indexes:{label}:"
            f"{stats['distinct_time_indexes']}"
        )
    if stats["timestamps"] != EXPECTED_ANNUAL_HOURS:
        errors.append(
            f"eplusout.sql:hourly_annual_timestamp_coverage:{label}:"
            f"{len(stats['timestamps'])}"
        )
    if stats["environment_indexes"] != {weather_environment_index}:
        errors.append(f"eplusout.sql:hourly_wrong_environment:{label}")
    if stats["warmup_flags"] != {0}:
        errors.append(f"eplusout.sql:hourly_contains_warmup:{label}")
    if stats["intervals"] != {60} or stats["interval_types"] != {1}:
        errors.append(f"eplusout.sql:hourly_interval_metadata_invalid:{label}")
    if not math.isfinite(stats["total"]) or not math.isfinite(stats["peak"]):
        errors.append(f"eplusout.sql:hourly_nonfinite_values:{label}")


def check_energyplus_evidence(
    sql_path: Path,
    err_path: Path,
    end_path: Path,
    flow_data: Dict[str, Any],
    osm_state: Dict[str, Any],
    errors: List[str],
) -> Dict[str, Dict[str, float]]:
    metrics: Dict[str, Dict[str, float]] = {}
    for suffix in ("-journal", "-wal", "-shm"):
        if Path(str(sql_path) + suffix).exists():
            errors.append(f"eplusout.sql:sqlite_sidecar_present:{suffix}")
    connection: sqlite3.Connection | None = None
    try:
        uri = f"file:{sql_path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            errors.append("eplusout.sql:integrity_check_failed")
        simulation_rows = connection.execute(
            "SELECT SimulationIndex, EnergyPlusVersion, TimeStamp, NumTimestepsPerHour, Completed, CompletedSuccessfully FROM Simulations"
        ).fetchall()
        if len(simulation_rows) != 1:
            errors.append(f"eplusout.sql:simulation_row_count:{len(simulation_rows)}")
            return metrics
        simulation = simulation_rows[0]
        if ENERGYPLUS_BUILD not in str(simulation[1]):
            errors.append("eplusout.sql:wrong_energyplus_build")
        if str(simulation[4]).upper() != "FALSE" or str(simulation[5]).upper() != "FALSE":
            errors.append("eplusout.sql:not_exact_25_1_false_false_state")
        environments = connection.execute(
            "SELECT EnvironmentPeriodIndex, SimulationIndex, EnvironmentName, EnvironmentType FROM EnvironmentPeriods"
        ).fetchall()
        if len(environments) != 1 or int(environments[0][3]) != 3:
            errors.append("eplusout.sql:not_one_weather_run_period")
        weather_environment_index = int(environments[0][0]) if len(environments) == 1 else -1
        report_data_count = int(connection.execute("SELECT COUNT(*) FROM ReportData").fetchone()[0])
        if report_data_count < 12 * 8760:
            errors.append("eplusout.sql:report_data_count_too_low")
        hourly_series = collect_hourly_sql_series(connection)

        for space_name, zone_name in osm_state.get("space_zone_map", {}).items():
            ideal_names = osm_state.get("ideal_by_zone", {}).get(zone_name)
            if not ideal_names:
                errors.append(f"eplusout.sql:missing_ideal_name:{zone_name}")
                continue
            energy_j = 0.0
            for variable, key_kind in ENERGY_VARIABLES:
                key_values = [zone_name] if key_kind == "zone" else ideal_names
                for key_value in key_values:
                    stats = sql_series_stats(hourly_series, variable, key_value)
                    check_hourly_sql_series(
                        stats,
                        weather_environment_index,
                        f"{space_name}:{key_value}:{variable}",
                        errors,
                    )
                    energy_j += stats["total"]
            rate_peaks: List[float] = []
            for variable in RATE_VARIABLES:
                for ideal_name in ideal_names:
                    stats = sql_series_stats(hourly_series, variable, ideal_name)
                    check_hourly_sql_series(
                        stats,
                        weather_environment_index,
                        f"{space_name}:{ideal_name}:{variable}",
                        errors,
                    )
                    rate_peaks.append(stats["peak"])
            metrics[space_name] = {
                "energy_use_kwh": energy_j / 3_600_000.0,
                "peak_load_w": max(rate_peaks),
            }

        simulation_evidence = flow_data.get("simulation")
        if not isinstance(simulation_evidence, dict):
            errors.append("flow_report:missing_simulation_evidence")
            return metrics
        if simulation_evidence.get("native_exit_code") != 0 or not isinstance(simulation_evidence.get("native_pid"), int):
            errors.append("flow_report:invalid_native_energyplus_exit_evidence")
        if simulation_evidence.get("sqlite_integrity_check") != "ok":
            errors.append("flow_report:sqlite_integrity_evidence_mismatch")
        evidence_row = simulation_evidence.get("simulations_row")
        expected_evidence_row = {
            "SimulationIndex": simulation[0],
            "EnergyPlusVersion": simulation[1],
            "TimeStamp": simulation[2],
            "NumTimestepsPerHour": simulation[3],
            "Completed": simulation[4],
            "CompletedSuccessfully": simulation[5],
        }
        if evidence_row != expected_evidence_row:
            errors.append("flow_report:simulation_row_mismatch_sql")
        if simulation_evidence.get("report_data_count") != report_data_count:
            errors.append("flow_report:report_data_count_mismatch_sql")
        started = parse_iso_datetime(simulation_evidence.get("native_started_at_utc"))
        process_exited = parse_iso_datetime(simulation_evidence.get("native_process_exited_at_utc"))
        completed = parse_iso_datetime(simulation_evidence.get("native_completed_at_utc"))
        if started is None or process_exited is None or completed is None or not (started <= process_exited <= completed):
            errors.append("flow_report:invalid_native_energyplus_timestamps")
        samples = simulation_evidence.get("stable_file_samples")
        if not isinstance(samples, list) or len(samples) < 3:
            errors.append("flow_report:insufficient_stable_file_samples")
        else:
            signatures = {
                (
                    sample.get("sql_size"), sample.get("sql_mtime_ns"),
                    sample.get("err_size"), sample.get("err_mtime_ns"),
                    sample.get("end_size"), sample.get("end_mtime_ns"),
                )
                for sample in samples
            }
            if len(signatures) != 1:
                errors.append("flow_report:unstable_native_energyplus_files")
            first = samples[0]
            if first.get("sql_size") != sql_path.stat().st_size or first.get("err_size") != err_path.stat().st_size or first.get("end_size") != end_path.stat().st_size:
                errors.append("flow_report:stable_sample_size_mismatch")
        if simulation_evidence.get("transaction_sidecars") != []:
            errors.append("flow_report:transaction_sidecars_not_empty")
        defect = simulation_evidence.get("energyplus_25_1_sql_finalization_order")
        if not isinstance(defect, dict) or defect.get("observed_completed") != "FALSE" or defect.get("observed_completed_successfully") != "FALSE" or "v25.1.0" not in str(defect.get("source", "")):
            errors.append("flow_report:unsupported_false_false_defect_evidence")
        inventory = flow_data.get("full_disk_sql_inventory")
        inventory_records = inventory.get("records") if isinstance(inventory, dict) else None
        if not isinstance(inventory_records, list) or not any(
            str(record.get("sha256", "")).lower() == sha256_file(sql_path)
            and record.get("integrity_check") == "ok"
            and record.get("simulation_rows") == [expected_evidence_row]
            for record in inventory_records
        ):
            errors.append("flow_report:full_disk_sql_inventory_missing_final_sql")
    except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
        errors.append(f"eplusout.sql:query_failed:{type(exc).__name__}:{exc}")
    finally:
        if connection is not None:
            connection.close()

    err_text = err_path.read_text(encoding="utf-8", errors="replace")
    end_text = end_path.read_text(encoding="utf-8", errors="replace")
    severe = len(re.findall(r"\*\*\s+Severe\s+\*\*", err_text, flags=re.IGNORECASE))
    fatal = len(re.findall(r"\*\*\s+Fatal\s+\*\*", err_text, flags=re.IGNORECASE))
    if "EnergyPlus Completed Successfully" not in err_text or "EnergyPlus Completed Successfully" not in end_text or severe or fatal:
        errors.append(f"energyplus:err_end_not_successful:severe={severe}:fatal={fatal}")
    if flow_data.get("energyplus_status") != "Completed Successfully" or flow_data.get("energyplus_severe_errors") != 0 or flow_data.get("energyplus_fatal_errors") != 0:
        errors.append("flow_report:top_level_energyplus_status_mismatch")
    return metrics


def check_model_summary_csv(
    path: Path,
    handoff_hash: str,
    stage1_hash: str,
    handoff_data: Dict[str, Any],
    flow_data: Dict[str, Any],
    osm_state: Dict[str, Any],
    sql_metrics: Dict[str, Dict[str, float]],
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
    handoff_records = {
        norm(record.get("name") or record.get("space_name")): record
        for record in extract_space_records(handoff_data, [], "handoff.json")
    }
    expected_zone_by_space = {norm(space): zone for space, zone in zip(required_spaces, required_zones)}
    for row in rows:
        row_case = next((str(v) for k, v in row.items() if norm(k) == norm("case_id")), "")
        if row_case != CASE_SPEC["case_id"]:
            errors.append("model_summary.csv:case_id_mismatch")
            break
        name = next((str(v) for k, v in row.items() if norm(k) == norm("space_name")), "")
        zone = next((str(v) for k, v in row.items() if norm(k) == norm("thermal_zone")), "")
        seen_spaces.add(norm(name))
        seen_zones.add(norm(zone))
        if norm(name) not in expected_zone_by_space or zone != expected_zone_by_space.get(norm(name)):
            errors.append(f"model_summary.csv:space_zone_bijection_mismatch:{name}:{zone}")
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
            handoff_record = handoff_records.get(norm(name), {})
            expected_ifc_area = float(handoff_record.get("floor_area_m2"))
            expected_osm_area = float(osm_state.get("floor_areas", {}).get(name))
            if abs(area - expected_ifc_area) > 0.01 or abs(area - expected_osm_area) > 0.01:
                errors.append(f"model_summary.csv:per_space_area_mismatch:{name}")
        except Exception:
            errors.append(f"model_summary.csv:invalid_area:{name}")
        try:
            energy = float(next((v for k, v in row.items() if norm(k) == norm("energy_use_kwh")), ""))
            peak = float(next((v for k, v in row.items() if norm(k) == norm("peak_load_w")), ""))
            if energy <= 0 or peak <= 0:
                errors.append(f"model_summary.csv:nonpositive_energy_or_peak:{name}")
            total_energy += energy
            expected_metrics = sql_metrics.get(name)
            if not expected_metrics:
                errors.append(f"model_summary.csv:missing_sql_metrics:{name}")
            else:
                energy_tolerance = max(1e-5, abs(expected_metrics["energy_use_kwh"]) * 1e-8)
                peak_tolerance = max(1e-5, abs(expected_metrics["peak_load_w"]) * 1e-8)
                if abs(energy - expected_metrics["energy_use_kwh"]) > energy_tolerance:
                    errors.append(f"model_summary.csv:energy_not_derived_from_sql:{name}")
                if abs(peak - expected_metrics["peak_load_w"]) > peak_tolerance:
                    errors.append(f"model_summary.csv:peak_not_derived_from_sql:{name}")
        except Exception:
            errors.append(f"model_summary.csv:invalid_energy_or_peak:{name}")
    for space in required_spaces:
        if norm(space) not in seen_spaces:
            errors.append(f"model_summary.csv:missing_required_space:{space}")
    for zone in required_zones:
        if norm(zone) not in seen_zones:
            errors.append(f"model_summary.csv:missing_required_zone:{zone}")
    if len(seen_spaces) != len(rows) or len(seen_zones) != len(rows):
        errors.append("model_summary.csv:duplicate_space_or_zone")
    flow_spaces = flow_data.get("spaces")
    if not isinstance(flow_spaces, list) or len(flow_spaces) != len(rows):
        errors.append("flow_report:space_rows_count_mismatch")
    else:
        flow_by_space = {str(record.get("space_name")): record for record in flow_spaces if isinstance(record, dict)}
        for row in rows:
            name = str(row.get("space_name", ""))
            record = flow_by_space.get(name)
            if record is None:
                errors.append(f"flow_report:missing_space_metric_row:{name}")
                continue
            for key in ("thermal_zone", "source_handoff_sha256", "source_stage1_sha256"):
                if str(record.get(key)) != str(row.get(key)):
                    errors.append(f"flow_report:space_metric_mismatch:{name}:{key}")
            for key in ("floor_area_m2", "energy_use_kwh", "peak_load_w"):
                try:
                    if abs(float(record.get(key)) - float(row.get(key))) > 1e-5:
                        errors.append(f"flow_report:space_metric_mismatch:{name}:{key}")
                except (TypeError, ValueError):
                    errors.append(f"flow_report:invalid_space_metric:{name}:{key}")
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
    is_archicad_27_output = any(
        signature in stage1_header
        for signature in (
            "THE EXPRESS DATA MANAGER VERSION 5.02.0100.09",
            "ARCHICAD 27",
            "ARCHICAD-27",
        )
    )
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
    check_native_stage_log(
        paths["native_stage_log.json"],
        init_path,
        stage1,
        handoff,
        stage1_info,
        errors,
    )
    check_workflow_and_weather(
        paths["workflow.osw"],
        paths["weather.epw"],
        stage1,
        handoff,
        errors,
    )
    handoff_hash = sha256_file(handoff)
    flow_tokens = ["weather_file", "schedule_set", "construction_set"]
    osm_counts = check_osm(paths["result.osm"], handoff_hash, handoff_data, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], CASE_SPEC["osm_tokens"], flow_tokens, errors)
    flow_data = check_flow_report(paths["flow_report.json"], handoff, paths["result.osm"], handoff_data, osm_counts, stage1_info, CASE_SPEC["required_spaces"], CASE_SPEC["required_zones"], errors)
    check_flow_dependencies(flow_data, paths, osm_counts, errors)
    sql_metrics = check_energyplus_evidence(
        paths["run/eplusout.sql"],
        paths["run/eplusout.err"],
        paths["run/eplusout.end"],
        flow_data,
        osm_counts,
        errors,
    )
    check_model_summary_csv(
        paths["model_summary.csv"], handoff_hash, sha256_file(stage1), handoff_data,
        flow_data, osm_counts, sql_metrics, CASE_SPEC["required_spaces"],
        CASE_SPEC["required_zones"], CASE_SPEC.get("summary_tokens", []), errors,
    )

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
