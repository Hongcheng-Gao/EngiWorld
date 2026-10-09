#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

MARKER_BEGIN = "ENGIWORLD_OPTIMIZATION_METADATA_BEGIN"
MARKER_END = "ENGIWORLD_OPTIMIZATION_METADATA_END"

OPENSTUDIO_IDF_MEASURE_RB = r"""class UseOptimizedIdf < OpenStudio::Measure::EnergyPlusMeasure
  def name; 'Use Optimized IDF'; end
  def description; 'Loads the evaluator-owned optimized IDF.'; end
  def modeler_description; 'Replaces the translated workspace before bundled EnergyPlus runs.'; end
  def arguments(workspace)
    args = OpenStudio::Measure::OSArgumentVector.new
    args << OpenStudio::Measure::OSArgument.makeStringArgument('idf_path', true)
    args
  end
  def run(workspace, runner, user_arguments)
    super(workspace, runner, user_arguments)
    return false unless runner.validateUserArguments(arguments(workspace), user_arguments)
    source_path = runner.getStringArgumentValue('idf_path', user_arguments)
    loaded = OpenStudio::IdfFile.load(OpenStudio::Path.new(source_path))
    if loaded.empty?
      runner.registerError("Cannot load optimized IDF: #{source_path}")
      return false
    end
    workspace.removeObjects(workspace.objects.map(&:handle))
    source_objects = loaded.get.objects
    added_objects = workspace.addObjects(source_objects)
    if added_objects.size != source_objects.size
      runner.registerError('Could not transfer every optimized IDF object')
      return false
    end
    true
  end
end
UseOptimizedIdf.new.registerWithApplication
"""

OPENSTUDIO_IDF_MEASURE_XML = """<?xml version="1.0"?>
<measure><schema_version>3.1</schema_version><name>use_optimized_idf</name>
<uid>8f9e0f71-f587-4abc-946f-7d41d8290191</uid><version_id>96129dac-770e-4f4e-9187-a3a165b10191</version_id>
<version_modified>2026-08-04T00:00:00Z</version_modified><xml_checksum>00000000</xml_checksum>
<class_name>UseOptimizedIdf</class_name><display_name>Use Optimized IDF</display_name>
<description>Loads the evaluator-owned optimized IDF.</description><modeler_description>Replaces the translated workspace.</modeler_description>
<arguments><argument><name>idf_path</name><display_name>Optimized IDF path</display_name><description>Absolute IDF path.</description>
<type>String</type><required>true</required><model_dependent>false</model_dependent></argument></arguments>
<outputs/><provenances/><tags/><attributes>
<attribute><name>Measure Type</name><value>EnergyPlusMeasure</value><datatype>string</datatype></attribute>
<attribute><name>Measure Language</name><value>Ruby</value><datatype>string</datatype></attribute>
</attributes><files><file><filename>measure.rb</filename><filetype>rb</filetype><usage_type>script</usage_type><checksum>00000000</checksum></file></files></measure>
"""


def desktop() -> Path:
    configured = os.environ.get("ENGIWORLD_DESKTOP")
    if configured:
        return Path(configured)
    return Path("/home/user/Desktop")


DESKTOP = desktop()


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_result(result: dict) -> None:
    for name in ("score.json", "quant_metrics.json"):
        try:
            (DESKTOP / name).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception:
            pass
    print("True" if result.get("valid") else "False")


def metric_close(a: float, b: float, rel: float = 0.03, abs_tol: float = 0.05) -> bool:
    return abs(float(a) - float(b)) <= max(abs_tol, rel * max(abs(float(a)), abs(float(b)), 1.0))


def find_openstudio_cli() -> str | None:
    candidates = [
        shutil.which("openstudio"),
        "/usr/local/bin/openstudio",
        "/usr/bin/openstudio",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    for parent in [Path("/usr/local"), Path("/opt")]:
        if parent.exists():
            for path in parent.glob("openstudio*/bin/openstudio"):
                if path.is_file():
                    return str(path)
    return None


def run_openstudio_for_evaluation(paths: dict[str, Path]) -> tuple[dict[str, Path] | None, list[str]]:
    if os.environ.get("ENGIWORLD_SKIP_OPENSTUDIO_RERUN") == "1":
        return None, []
    cli = find_openstudio_cli()
    if not cli:
        return None, ["openstudio_cli:not_found"]
    workflow_root = Path(tempfile.mkdtemp(prefix="engiworld-openstudio-eval-"))
    shutil.rmtree(workflow_root, ignore_errors=True)
    workflow_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths["optimized"], workflow_root / "optimized.idf")
    shutil.copy2(paths["weather"], workflow_root / "weather.epw")
    measure_dir = workflow_root / "measures" / "use_optimized_idf"
    measure_dir.mkdir(parents=True, exist_ok=True)
    (measure_dir / "measure.rb").write_text(OPENSTUDIO_IDF_MEASURE_RB, encoding="utf-8")
    (measure_dir / "measure.xml").write_text(OPENSTUDIO_IDF_MEASURE_XML, encoding="utf-8")
    workflow = {
        "file_format_version": "0.1",
        "weather_file": "weather.epw",
        "measure_paths": ["measures"],
        "run_options": {"cleanup": False},
        "steps": [
            {
                "measure_dir_name": "use_optimized_idf",
                "arguments": {"idf_path": str(workflow_root / "optimized.idf")},
            }
        ],
    }
    workflow_path = workflow_root / "workflow.osw"
    workflow_path.write_text(json.dumps(workflow, indent=2) + "\n", encoding="utf-8")
    try:
        proc = subprocess.run(
            [cli, "run", "-w", str(workflow_path), "--show-stdout"],
            text=True,
            capture_output=True,
            timeout=240,
        )
    except Exception:
        shutil.rmtree(workflow_root, ignore_errors=True)
        raise
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().replace("\n", " ")[:500]
        shutil.rmtree(workflow_root, ignore_errors=True)
        return None, [f"openstudio_workflow_rerun:failed:{detail}"]
    run_dir = workflow_root / "run"
    rerun = {"sql": run_dir / "eplusout.sql", "err": run_dir / "eplusout.err", "root": workflow_root}
    if not rerun["sql"].is_file():
        shutil.rmtree(workflow_root, ignore_errors=True)
        return None, ["openstudio_workflow_rerun:missing_eplusout_sql"]
    if not rerun["err"].is_file():
        shutil.rmtree(workflow_root, ignore_errors=True)
        return None, ["openstudio_workflow_rerun:missing_eplusout_err"]
    err_text = rerun["err"].read_text(encoding="utf-8", errors="replace")
    if "Fatal" in err_text or "EnergyPlus Completed Successfully" not in err_text or "0 Severe Errors" not in err_text:
        shutil.rmtree(workflow_root, ignore_errors=True)
        return None, ["openstudio_workflow_rerun:simulation_not_successful"]
    return rerun, []


def extract_metadata(idf_path: Path) -> tuple[dict, list[str], str]:
    errors: list[str] = []
    if not idf_path.is_file() or idf_path.stat().st_size < 1500:
        return {}, ["optimized_idf:missing_or_too_small"], ""
    text = idf_path.read_text(encoding="utf-8", errors="replace")
    payload_lines: list[str] = []
    in_block = False
    for raw in text.splitlines():
        line = raw.strip()
        if MARKER_BEGIN in line:
            in_block = True
            continue
        if MARKER_END in line:
            in_block = False
            break
        if in_block:
            # OpenStudio's native IdfFile#save normalizes header comments to
            # `! text`, while hand-authored IDF commonly uses `!- text`.
            # Both are valid EnergyPlus comments and must remain acceptable.
            if line.startswith("!-"):
                line = line[2:].strip()
            elif line.startswith("!"):
                line = line[1:].strip()
            payload_lines.append(line)
    if not payload_lines:
        return {}, ["optimized_idf:missing_metadata_block"], text
    try:
        return json.loads("\n".join(payload_lines)), errors, text
    except Exception as exc:
        return {}, [f"optimized_idf:metadata_json_parse_failed:{exc}"], text


def compute_proxy_metrics(constraints: dict, variables: dict) -> dict:
    base = constraints["energy_model"]["component_reference"]
    baseline = constraints["baseline"]["design_variables"]
    area = float(variables["floor_area_m2"])
    wall = baseline["wall_r_value_m2k_w"] / variables["wall_r_value_m2k_w"]
    roof = baseline["roof_r_value_m2k_w"] / variables["roof_r_value_m2k_w"]
    window = variables["window_u_value_w_m2k"] / baseline["window_u_value_w_m2k"]
    infil = variables["infiltration_ach"] / baseline["infiltration_ach"]
    shgc = variables["window_shgc"] / baseline["window_shgc"]
    wwr = variables["wwr"] / baseline["wwr"]
    shade = variables["shade_ratio"]
    daylight = variables["daylight_control_fraction"]
    lpd = variables["lighting_w_per_m2"] / baseline["lighting_w_per_m2"]
    epd = variables["equipment_w_per_m2"] / baseline["equipment_w_per_m2"]
    occupied = variables.get("occupied_hours_fraction", baseline.get("occupied_hours_fraction", 0.42)) / baseline.get("occupied_hours_fraction", 0.42)
    hvac_avail = variables.get("hvac_availability_fraction", baseline.get("hvac_availability_fraction", 0.72)) / baseline.get("hvac_availability_fraction", 0.72)
    cool_sp = variables["cooling_setpoint_c"]
    heat_sp = variables["heating_setpoint_c"]
    economizer = variables.get("economizer_fraction", 0.20)
    precool = variables.get("precool_hours", 0.0)
    mass = variables.get("thermal_mass_level", 0.35)
    ventilation = variables.get("ventilation_lps_per_person", baseline.get("ventilation_lps_per_person", 8.0))
    ventilation_base = baseline.get("ventilation_lps_per_person", 8.0)

    heating_setpoint_factor = clamp(1.0 + 0.055 * (heat_sp - baseline["heating_setpoint_c"]), 0.78, 1.18)
    cooling_setpoint_factor = clamp(1.0 - 0.065 * (cool_sp - baseline["cooling_setpoint_c"]), 0.72, 1.16)
    internal_gain_factor = 0.55 * lpd + 0.45 * epd
    ventilation_factor = clamp(0.80 + 0.20 * (ventilation / ventilation_base), 0.85, 1.18)

    heating = base["heating_kwh"] * clamp(0.24 + 0.28 * wall + 0.22 * roof + 0.14 * window + 0.12 * infil, 0.45, 1.35) * heating_setpoint_factor * ventilation_factor
    cooling = base["cooling_kwh"] * clamp(0.18 + 0.24 * wwr + 0.24 * shgc + 0.13 * (1.0 - shade) + 0.11 * internal_gain_factor + 0.10 * infil, 0.38, 1.42)
    cooling *= cooling_setpoint_factor * clamp(1.0 - 0.12 * economizer - 0.045 * precool - 0.08 * mass, 0.70, 1.05)
    lighting = base["lighting_kwh"] * lpd * clamp(1.0 - 0.30 * daylight, 0.72, 1.04) * clamp(0.90 + 0.10 * occupied, 0.85, 1.08)
    equipment = base["equipment_kwh"] * epd * clamp(0.86 + 0.14 * occupied, 0.82, 1.08)
    fans = base["fan_kwh"] * clamp(0.76 + 0.24 * hvac_avail, 0.72, 1.10) * ventilation_factor
    hvac = heating + cooling + fans
    total = hvac + lighting + equipment

    comfort_penalty = 0.0
    comfort_penalty += max(0.0, 19.5 - heat_sp) * 18.0
    comfort_penalty += max(0.0, cool_sp - 25.5) * 22.0
    comfort_penalty += max(0.0, 0.62 - variables.get("hvac_availability_fraction", 0.72)) * 90.0
    comfort_penalty += max(0.0, 0.34 - variables["infiltration_ach"]) * 55.0
    comfort_penalty += max(0.0, 7.8 - ventilation) * 20.0
    unmet = max(0.0, base["unmet_hours"] * clamp(0.68 + 0.18 * infil + 0.14 * (1.0 - hvac_avail), 0.55, 1.20) + comfort_penalty - 12.0 * mass)

    peak_cooling = base["peak_cooling_kw"] * clamp(0.20 + 0.27 * wwr + 0.25 * shgc + 0.12 * internal_gain_factor + 0.10 * infil + 0.06 * (1.0 - shade), 0.42, 1.35)
    peak_cooling *= clamp(1.0 - 0.07 * precool - 0.11 * mass - 0.08 * economizer, 0.68, 1.05)
    peak_heating = base["peak_heating_kw"] * clamp(0.25 + 0.28 * wall + 0.22 * roof + 0.15 * window + 0.10 * infil, 0.45, 1.28)
    electricity = cooling + fans + lighting + equipment
    gas = heating
    carbon = electricity * 0.385 + gas * 0.185
    daylight_proxy = clamp(0.22 + 1.15 * variables["wwr"] + 0.42 * daylight - 0.22 * shade, 0.0, 1.0)
    iaq_proxy = clamp(0.45 + 0.055 * ventilation - 0.35 * max(0.0, variables["infiltration_ach"] - 0.45), 0.0, 1.0)
    return {
        "total_site_energy_kwh": round(total, 3),
        "eui_kwh_m2": round(total / area, 4),
        "hvac_energy_kwh": round(hvac, 3),
        "heating_kwh": round(heating, 3),
        "cooling_kwh": round(cooling, 3),
        "lighting_kwh": round(lighting, 3),
        "equipment_kwh": round(equipment, 3),
        "fan_kwh": round(fans, 3),
        "unmet_hours": round(unmet, 3),
        "peak_cooling_kw": round(peak_cooling, 3),
        "peak_heating_kw": round(peak_heating, 3),
        "carbon_kgco2e": round(carbon, 3),
        "daylight_proxy": round(daylight_proxy, 4),
        "iaq_proxy": round(iaq_proxy, 4),
    }


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("select name from sqlite_master where type in ('table','view') and name = ?", (name,)).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, name: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f"pragma table_info({name})")]


def column_named(columns: list[str], *names: str) -> str | None:
    normalized = {col.lower(): col for col in columns}
    for name in names:
        if name.lower() in normalized:
            return normalized[name.lower()]
    return None


def standard_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    columns = table_columns(conn, table)
    rows = conn.execute(f"select * from {table}").fetchall()
    return [dict(zip(columns, row)) for row in rows]


def to_kwh(value: float, units: str) -> float:
    normalized = str(units or "").strip().lower()
    if normalized in {"j", "joule", "joules"}:
        return float(value) / 3_600_000.0
    if normalized in {"gj"}:
        return float(value) * 277.7777777778
    if normalized in {"mj"}:
        return float(value) / 3.6
    return float(value)


def tabular_value(metric: str, value: float, units: str) -> float:
    normalized = str(units or "").strip().lower()
    if metric in {"total_site_energy_kwh", "hvac_energy_kwh", "heating_kwh", "cooling_kwh", "lighting_kwh", "equipment_kwh", "fan_kwh"}:
        return to_kwh(value, normalized)
    if metric == "eui_kwh_m2":
        if normalized in {"mj/m2", "mj/m^2"}:
            return float(value) / 3.6
        if normalized in {"gj/m2", "gj/m^2"}:
            return float(value) * 277.7777777778
    return float(value)


def read_sql_metrics(path: Path, area_m2: float = 0.0, proxy: dict | None = None) -> tuple[dict, list[str]]:
    errors: list[str] = []
    if not path.is_file() or path.stat().st_size < 1024:
        return {}, ["eplusout.sql:missing_or_too_small"]
    try:
        conn = sqlite3.connect(str(path))
    except Exception as exc:
        return {}, [f"eplusout.sql:open_failed:{exc}"]
    metrics: dict[str, float] = {}
    native_schema = False
    try:
        if table_exists(conn, "EWOptimizationMetrics"):
            errors.append("eplusout.sql:forbidden_custom_metrics_table")
        native_schema = table_exists(conn, "ReportDataDictionary") and table_exists(conn, "ReportData") and table_exists(conn, "Time")
        if not native_schema:
            errors.append("eplusout.sql:missing_standard_energyplus_report_tables")
        if table_exists(conn, "TabularDataWithStrings"):
            rows = conn.execute("select RowName,ColumnName,Units,Value from TabularDataWithStrings").fetchall()
            aliases = {
                "total site energy": "total_site_energy_kwh",
                "energy per total building area": "eui_kwh_m2",
                "eui": "eui_kwh_m2",
                "hvac energy": "hvac_energy_kwh",
                "heating energy": "heating_kwh",
                "cooling energy": "cooling_kwh",
                "lighting energy": "lighting_kwh",
                "equipment energy": "equipment_kwh",
                "fan energy": "fan_kwh",
                "unmet hours": "unmet_hours",
                "peak cooling load": "peak_cooling_kw",
                "peak heating load": "peak_heating_kw",
                "carbon emissions": "carbon_kgco2e",
                "daylight proxy": "daylight_proxy",
                "iaq proxy": "iaq_proxy",
            }
            for row_name, column_name, _units, value in rows:
                key = (str(column_name or row_name).strip().lower())
                metric = aliases.get(key)
                if metric:
                    try:
                        metrics[metric] = tabular_value(metric, float(value), str(_units or ""))
                    except Exception:
                        errors.append(f"eplusout.sql:non_numeric_tabular_value:{metric}")
        if native_schema:
            dict_rows = standard_rows(conn, "ReportDataDictionary")
            data_columns = table_columns(conn, "ReportData")
            data_idx_col = column_named(data_columns, "ReportDataDictionaryIndex")
            data_value_col = column_named(data_columns, "Value")
            if not data_idx_col or not data_value_col:
                errors.append("eplusout.sql:report_data_schema_unrecognized")
            else:
                sums_by_idx: dict[str, float] = {}
                for idx, value in conn.execute(f"select {data_idx_col},{data_value_col} from ReportData"):
                    try:
                        sums_by_idx[str(idx)] = sums_by_idx.get(str(idx), 0.0) + float(value)
                    except Exception:
                        errors.append("eplusout.sql:non_numeric_report_data_value")
                meter_values: dict[str, float] = {}
                for row in dict_rows:
                    idx = str(row.get("ReportDataDictionaryIndex", ""))
                    raw_name = str(row.get("Name", "") or row.get("KeyValue", ""))
                    units = str(row.get("Units", ""))
                    if idx not in sums_by_idx or not raw_name:
                        continue
                    key = raw_name.strip().lower().replace(" ", "")
                    meter_values[key] = to_kwh(sums_by_idx[idx], units)

                def meter(*needles: str) -> float | None:
                    normalized_needles = [needle.lower().replace(" ", "") for needle in needles]
                    for name, value in meter_values.items():
                        if any(needle in name for needle in normalized_needles):
                            return value
                    return None

                heating = meter("DistrictHeating:Facility", "Heating:DistrictHeating", "ZoneIdealLoadsSupplyAirTotalHeatingEnergy")
                cooling = meter("DistrictCooling:Facility", "Cooling:DistrictCooling", "ZoneIdealLoadsSupplyAirTotalCoolingEnergy")
                lighting = meter("InteriorLights:Electricity", "Lights:Electricity")
                equipment = meter("InteriorEquipment:Electricity", "ElectricEquipment:Electricity")
                fans = meter("Fans:Electricity")
                electricity = meter("Electricity:Facility")
                if heating is not None:
                    metrics.setdefault("heating_kwh", round(heating, 3))
                if cooling is not None:
                    metrics.setdefault("cooling_kwh", round(cooling, 3))
                if lighting is not None:
                    metrics.setdefault("lighting_kwh", round(lighting, 3))
                if equipment is not None:
                    metrics.setdefault("equipment_kwh", round(equipment, 3))
                if fans is not None:
                    metrics.setdefault("fan_kwh", round(fans, 3))
                if fans is None and native_schema:
                    metrics.setdefault("fan_kwh", 0.0)
                if electricity is not None:
                    total = electricity + float(metrics.get("heating_kwh", 0.0)) + float(metrics.get("cooling_kwh", 0.0))
                    metrics["total_site_energy_kwh"] = round(total, 3)
                else:
                    components = [metrics.get(k) for k in ("heating_kwh", "cooling_kwh", "lighting_kwh", "equipment_kwh", "fan_kwh")]
                    if all(value is not None for value in components):
                        total = sum(float(value) for value in components)
                        metrics["total_site_energy_kwh"] = round(total, 3)
                if all(k in metrics for k in ("heating_kwh", "cooling_kwh", "fan_kwh")):
                    metrics["hvac_energy_kwh"] = round(float(metrics["heating_kwh"]) + float(metrics["cooling_kwh"]) + float(metrics["fan_kwh"]), 3)
                if area_m2 > 0 and "total_site_energy_kwh" in metrics:
                    metrics["eui_kwh_m2"] = round(float(metrics["total_site_energy_kwh"]) / area_m2, 4)
                if "carbon_kgco2e" not in metrics and all(k in metrics for k in ("heating_kwh", "cooling_kwh", "lighting_kwh", "equipment_kwh", "fan_kwh")):
                    carbon = (float(metrics["cooling_kwh"]) + float(metrics["lighting_kwh"]) + float(metrics["equipment_kwh"]) + float(metrics["fan_kwh"])) * 0.385 + float(metrics["heating_kwh"]) * 0.185
                    metrics["carbon_kgco2e"] = round(carbon, 3)
    except Exception as exc:
        errors.append(f"eplusout.sql:query_failed:{exc}")
    finally:
        conn.close()
    if proxy:
        for key in ("hvac_energy_kwh", "unmet_hours", "peak_cooling_kw", "peak_heating_kw", "daylight_proxy", "iaq_proxy", "carbon_kgco2e"):
            if key not in metrics and proxy.get(key) is not None:
                metrics[key] = proxy.get(key)
    if native_schema and not any(key in metrics for key in ("total_site_energy_kwh", "eui_kwh_m2", "heating_kwh", "cooling_kwh", "lighting_kwh", "equipment_kwh")):
        errors.append("eplusout.sql:missing_standard_energy_metrics")
    return metrics, errors


def validate_native_sql_bindings(path: Path, variables: dict, quantities: dict) -> list[str]:
    """Cross-check the evaluator-owned EnergyPlus SQLite interpretation.

    This is independent of submitted metadata and proves that the constrained
    variables reached native EnergyPlus material, surface, infiltration, load,
    and daylight-linked tables through the pinned OpenStudio workflow.
    """
    failures: list[str] = []
    try:
        conn = sqlite3.connect(str(path))
    except Exception as exc:
        return [f"native_bindings_sql_open_failed:{exc}"]

    def close(actual: float, expected: float, label: str, rel: float = 0.01, abs_tol: float = 1e-5) -> None:
        if abs(float(actual) - float(expected)) > max(abs_tol, rel * max(abs(float(actual)), abs(float(expected)), 1.0)):
            failures.append(f"native_binding_mismatch:{label}")

    try:
        simulations = conn.execute(
            "select EnergyPlusVersion,Completed,CompletedSuccessfully from Simulations order by SimulationIndex desc limit 1"
        ).fetchone()
        if not simulations:
            failures.append("missing_simulations_row")
        elif "25.2.0" not in str(simulations[0]):
            failures.append("wrong_energyplus_version")
        severe_count = conn.execute("select count(*) from Errors where ErrorType = 1").fetchone()[0]
        if int(severe_count) != 0:
            failures.append("native_sql_contains_severe_errors")
        if conn.execute("select count(*) from ReportData").fetchone()[0] <= 0:
            failures.append("native_sql_has_no_report_data")

        material_rows = {
            str(name).casefold(): float(resistance)
            for name, resistance in conn.execute("select Name,Resistance from Materials")
            if resistance is not None
        }
        for name, variable in (("wall-mat", "wall_r_value_m2k_w"), ("roof-mat", "roof_r_value_m2k_w")):
            if name not in material_rows:
                failures.append(f"missing_native_material:{name}")
            else:
                close(material_rows[name], float(variables[variable]), variable)

        construction_rows = {
            str(name).casefold(): float(uvalue)
            for name, uvalue in conn.execute("select Name,Uvalue from Constructions")
            if uvalue is not None
        }
        if "window-construction" not in construction_rows:
            failures.append("missing_native_window_construction")
        else:
            close(construction_rows["window-construction"], float(variables["window_u_value_w_m2k"]), "window_u_value_w_m2k", rel=0.015)

        window_area = conn.execute(
            "select coalesce(sum(Area),0) from Surfaces where ClassName = 'Window'"
        ).fetchone()[0]
        close(float(window_area), float(quantities["window_area_m2"]), "window_area_m2")
        close(float(window_area) / float(quantities["exterior_wall_area_m2"]), float(variables["wwr"]), "wwr")

        infiltration = conn.execute(
            "select DesignLevel from NominalInfiltration where upper(ObjectName) = 'VISITOR-OFFICE-INFILTRATION'"
        ).fetchone()
        expected_flow = float(variables["infiltration_ach"]) * float(quantities["floor_area_m2"]) * 3.2 / 3600.0
        if not infiltration:
            failures.append("missing_native_infiltration")
        else:
            close(float(infiltration[0]), expected_flow, "infiltration_ach", rel=0.015)

        lighting = conn.execute(
            "select DesignLevel,FractionReplaceable from NominalLighting where upper(ObjectName) = 'VISITOR-OFFICE-LIGHTS'"
        ).fetchone()
        if not lighting:
            failures.append("missing_native_lighting")
        else:
            close(float(lighting[0]) / float(quantities["floor_area_m2"]), float(variables["lighting_w_per_m2"]), "lighting_w_per_m2")
            if float(variables["daylight_control_fraction"]) > 0 and float(lighting[1]) <= 0:
                failures.append("native_daylighting_has_no_replaceable_lighting")

        equipment = conn.execute(
            "select DesignLevel from NominalElectricEquipment where upper(ObjectName) = 'VISITOR-OFFICE-EQUIPMENT'"
        ).fetchone()
        if not equipment:
            failures.append("missing_native_equipment")
        else:
            close(float(equipment[0]) / float(quantities["floor_area_m2"]), float(variables["equipment_w_per_m2"]), "equipment_w_per_m2")

        people = conn.execute(
            "select NumberOfPeople from NominalPeople where upper(ObjectName) = 'VISITOR-OFFICE-PEOPLE'"
        ).fetchone()
        if not people:
            failures.append("missing_native_people")
        else:
            close(float(people[0]) / float(quantities["floor_area_m2"]), float(variables["people_density_m2"]), "people_density_m2")
    except Exception as exc:
        failures.append(f"native_binding_query_failed:{exc}")
    finally:
        conn.close()
    return failures


def read_energy_report(path: Path) -> tuple[dict, list[str]]:
    if not path.is_file():
        return {}, ["energy_report.csv:missing"]
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except Exception as exc:
        return {}, [f"energy_report.csv:parse_failed:{exc}"]
    if len(rows) != 1:
        return {}, ["energy_report.csv:expected_exactly_one_data_row"]
    return rows[0], []


def parse_idf_objects(text: str) -> list[tuple[str, list[str]]]:
    """Parse enough IDF syntax for independent object/field validation.

    The task IDFs use ordinary comma/semicolon-delimited objects. Comments are
    removed before tokenization, quoted strings are preserved, and malformed
    trailing objects fail closed by returning an explicit marker object.
    """
    cleaned_lines: list[str] = []
    for raw in text.splitlines():
        in_quote = False
        chars: list[str] = []
        for char in raw:
            if char == '"':
                in_quote = not in_quote
                chars.append(char)
            elif char == "!" and not in_quote:
                break
            else:
                chars.append(char)
        cleaned_lines.append("".join(chars))
    content = "\n".join(cleaned_lines)
    objects: list[tuple[str, list[str]]] = []
    token: list[str] = []
    fields: list[str] = []
    in_quote = False
    for char in content:
        if char == '"':
            in_quote = not in_quote
            token.append(char)
        elif char in {",", ";"} and not in_quote:
            fields.append("".join(token).strip().strip('"'))
            token = []
            if char == ";":
                if fields and fields[0]:
                    objects.append((fields[0].lower(), fields[1:]))
                fields = []
        else:
            token.append(char)
    if fields or "".join(token).strip():
        objects.append(("__parse_error__", []))
    return objects


def polygon_area(vertices: list[tuple[float, float, float]]) -> float:
    cross = [0.0, 0.0, 0.0]
    for index, a in enumerate(vertices):
        b = vertices[(index + 1) % len(vertices)]
        cross[0] += a[1] * b[2] - a[2] * b[1]
        cross[1] += a[2] * b[0] - a[0] * b[2]
        cross[2] += a[0] * b[1] - a[1] * b[0]
    return 0.5 * math.sqrt(sum(value * value for value in cross))


def validate_native_idf_bindings(idf_text: str, variables: dict, quantities: dict) -> list[str]:
    failures: list[str] = []
    objects = parse_idf_objects(idf_text)
    if any(kind == "__parse_error__" for kind, _fields in objects):
        return ["optimized_idf:object_parse_failed"]

    def by_type(kind: str) -> list[list[str]]:
        return [fields for object_type, fields in objects if object_type == kind.lower()]

    def named(kind: str, name: str) -> list[str] | None:
        for fields in by_type(kind):
            if fields and fields[0].strip().casefold() == name.casefold():
                return fields
        failures.append(f"optimized_idf:missing_named_object:{kind}:{name}")
        return None

    def number(fields: list[str], index: int, label: str) -> float | None:
        try:
            return float(fields[index])
        except Exception:
            failures.append(f"optimized_idf:non_numeric_field:{label}")
            return None

    def close(actual: float | None, expected: float, label: str, rel: float = 0.002, abs_tol: float = 1e-5) -> None:
        if actual is None:
            return
        if abs(actual - expected) > max(abs_tol, rel * max(abs(actual), abs(expected), 1.0)):
            failures.append(f"optimized_idf:metadata_not_bound_to_object:{label}")

    wall = named("Material", "WALL-MAT")
    roof = named("Material", "ROOF-MAT")
    if wall:
        thickness = number(wall, 2, "WALL-MAT.thickness")
        conductivity = number(wall, 3, "WALL-MAT.conductivity")
        close((thickness / conductivity) if thickness is not None and conductivity else None, float(variables["wall_r_value_m2k_w"]), "wall_r_value_m2k_w")
    if roof:
        thickness = number(roof, 2, "ROOF-MAT.thickness")
        conductivity = number(roof, 3, "ROOF-MAT.conductivity")
        close((thickness / conductivity) if thickness is not None and conductivity else None, float(variables["roof_r_value_m2k_w"]), "roof_r_value_m2k_w")

    glazing = named("WindowMaterial:SimpleGlazingSystem", "LOW-E-GLASS")
    if glazing:
        close(number(glazing, 1, "LOW-E-GLASS.u_factor"), float(variables["window_u_value_w_m2k"]), "window_u_value_w_m2k")
        close(number(glazing, 2, "LOW-E-GLASS.shgc"), float(variables["window_shgc"]), "window_shgc")

    for schedule_name, variable_name in (("HEATING-SP", "heating_setpoint_c"), ("COOLING-SP", "cooling_setpoint_c")):
        schedule = named("Schedule:Compact", schedule_name)
        if schedule:
            numeric_values: list[float] = []
            for value in schedule[2:]:
                try:
                    numeric_values.append(float(value))
                except Exception:
                    pass
            if not numeric_values:
                failures.append(f"optimized_idf:missing_schedule_value:{schedule_name}")
            elif any(abs(value - float(variables[variable_name])) > 1e-6 for value in numeric_values):
                failures.append(f"optimized_idf:metadata_not_bound_to_object:{variable_name}")

    people = named("People", "VISITOR-OFFICE-PEOPLE")
    lights = named("Lights", "VISITOR-OFFICE-LIGHTS")
    equipment = named("ElectricEquipment", "VISITOR-OFFICE-EQUIPMENT")
    if people:
        close(number(people, 5, "People.people_per_area"), float(variables["people_density_m2"]), "people_density_m2")
    if lights:
        close(number(lights, 5, "Lights.watts_per_area"), float(variables["lighting_w_per_m2"]), "lighting_w_per_m2")
        replaceable = number(lights, 10, "Lights.fraction_replaceable")
        if float(variables["daylight_control_fraction"]) > 0 and (replaceable is None or replaceable <= 0):
            failures.append("optimized_idf:daylighting_has_no_replaceable_lighting")
    if equipment:
        close(number(equipment, 5, "ElectricEquipment.watts_per_area"), float(variables["equipment_w_per_m2"]), "equipment_w_per_m2")

    infiltration = named("ZoneInfiltration:DesignFlowRate", "VISITOR-OFFICE-INFILTRATION")
    if infiltration:
        if len(infiltration) <= 11 or infiltration[3].casefold() != "airchanges/hour":
            failures.append("optimized_idf:infiltration_method_not_airchanges_per_hour")
        else:
            close(number(infiltration, 7, "Infiltration.ach"), float(variables["infiltration_ach"]), "infiltration_ach")
            coefficients = [number(infiltration, index, f"Infiltration.coefficient_{index}") for index in range(8, 12)]
            if all(value is not None for value in coefficients) and sum(abs(float(value)) for value in coefficients) <= 1e-12:
                failures.append("optimized_idf:infiltration_all_coefficients_zero")

    windows = by_type("FenestrationSurface:Detailed")
    window_area = 0.0
    for fields in windows:
        try:
            count = int(float(fields[8]))
            coords = [float(value) for value in fields[9:9 + 3 * count]]
            vertices = [tuple(coords[index:index + 3]) for index in range(0, len(coords), 3)]
            if len(vertices) != count:
                raise ValueError("vertex count")
            window_area += polygon_area(vertices)
        except Exception:
            failures.append("optimized_idf:window_geometry_parse_failed")
            break
    close(window_area, float(quantities["window_area_m2"]), "window_area_m2", rel=0.003)
    close(window_area / float(quantities["exterior_wall_area_m2"]), float(variables["wwr"]), "wwr", rel=0.003)

    daylight = by_type("Daylighting:Controls")
    declared_daylight = float(variables["daylight_control_fraction"])
    if declared_daylight > 0:
        if not daylight:
            failures.append("optimized_idf:missing_daylighting_controls")
        else:
            fractions: list[float] = []
            for fields in daylight:
                for index in range(14, len(fields), 3):
                    try:
                        fractions.append(float(fields[index]))
                    except Exception:
                        pass
            if not fractions:
                failures.append("optimized_idf:missing_daylighting_control_fraction")
            else:
                close(sum(fractions), declared_daylight, "daylight_control_fraction", rel=0.003)
    elif daylight:
        failures.append("optimized_idf:unexpected_daylighting_controls")

    return failures


def validate_idf_and_constraints(constraints: dict, metadata: dict, idf_text: str, paths: dict[str, Path]) -> tuple[list[str], dict]:
    failures: list[str] = []
    variables = metadata.get("design_variables") or {}
    quantities = metadata.get("model_quantities") or {}
    hard = constraints["hard_constraints"]
    if metadata.get("case_id") != constraints["case_id"]:
        failures.append("optimized_idf:case_id_mismatch")
    expected_hashes = {
        "source_baseline_sha256": sha256_file(paths["baseline"]),
        "constraints_sha256": sha256_file(paths["constraints"]),
        "weather_sha256": sha256_file(paths["weather"]),
    }
    for key, expected in expected_hashes.items():
        if metadata.get(key) != expected:
            failures.append(f"optimized_idf:{key}_mismatch")
    for name in hard["space_names"] + hard["thermal_zone_names"]:
        if name not in idf_text:
            failures.append(f"optimized_idf:missing_required_name:{name}")
    required_objects = ["Zone,", "BuildingSurface:Detailed", "FenestrationSurface:Detailed", "Output:SQLite"]
    for token in required_objects:
        if token.lower() not in idf_text.lower():
            failures.append(f"optimized_idf:missing_object:{token}")
    for key, expected in {
        "space_count": hard["space_count"],
        "thermal_zone_count": hard["thermal_zone_count"],
    }.items():
        if int(round(float(quantities.get(key, -1)))) != int(expected):
            failures.append(f"optimized_idf:{key}_changed")
    floor = float(quantities.get("floor_area_m2", 0))
    floor_expected = float(constraints["baseline"]["floor_area_m2"])
    if abs(floor - floor_expected) > floor_expected * float(hard["floor_area_tolerance_fraction"]):
        failures.append("optimized_idf:floor_area_out_of_tolerance")
    exterior = float(quantities.get("exterior_wall_area_m2", 0))
    exterior_expected = float(constraints["baseline"]["design_variables"]["exterior_wall_area_m2"])
    if abs(exterior - exterior_expected) > exterior_expected * float(hard["exterior_wall_area_tolerance_fraction"]):
        failures.append("optimized_idf:exterior_wall_area_out_of_tolerance")
    for var_name, bounds in hard["variable_ranges"].items():
        if var_name not in variables:
            failures.append(f"optimized_idf:missing_design_variable:{var_name}")
            continue
        value = float(variables[var_name])
        if value < float(bounds[0]) - 1e-9 or value > float(bounds[1]) + 1e-9:
            failures.append(f"optimized_idf:variable_out_of_range:{var_name}")
    for preserved in ("floor_area_m2", "space_count", "thermal_zone_count", "exterior_wall_area_m2", "window_area_m2"):
        if preserved not in variables:
            failures.append(f"optimized_idf:missing_quantity_variable:{preserved}")
    failures.extend(validate_native_idf_bindings(idf_text, variables, quantities))
    return failures, variables


def validate_reports(constraints: dict, variables: dict, proxy: dict, sql_metrics: dict, report: dict, summary: dict, paths: dict[str, Path], metrics_from_energyplus_rerun: bool) -> list[str]:
    failures: list[str] = []
    required_metrics = [
        "total_site_energy_kwh",
        "eui_kwh_m2",
        "hvac_energy_kwh",
        "heating_kwh",
        "cooling_kwh",
        "lighting_kwh",
        "equipment_kwh",
        "fan_kwh",
        "unmet_hours",
        "peak_cooling_kw",
        "peak_heating_kw",
        "carbon_kgco2e",
        "daylight_proxy",
        "iaq_proxy",
    ]
    for metric in required_metrics:
        if metric not in sql_metrics:
            failures.append(f"eplusout.sql:missing_metric:{metric}")
    if failures:
        return failures
    provenance = sql_metrics.get("_provenance", {})
    if provenance:
        expected = {
            "case_id": constraints["case_id"],
            "optimized_idf_sha256": sha256_file(paths["optimized"]),
            "constraints_sha256": sha256_file(paths["constraints"]),
            "baseline_idf_sha256": sha256_file(paths["baseline"]),
            "weather_sha256": sha256_file(paths["weather"]),
        }
        for key, value in expected.items():
            if provenance.get(key) != value:
                failures.append(f"eplusout.sql:provenance_mismatch:{key}")
    for key, path_key in [
        ("optimized_idf_sha256", "optimized"),
        ("constraints_sha256", "constraints"),
        ("baseline_idf_sha256", "baseline"),
        ("weather_sha256", "weather"),
        ("eplusout_sql_sha256", "sql"),
    ]:
        if str(summary.get(key, "")) != sha256_file(paths[path_key]):
            failures.append(f"design_summary.json:hash_mismatch:{key}")
    if summary.get("case_id") != constraints["case_id"]:
        failures.append("design_summary.json:case_id_mismatch")
    if summary.get("simulation_status") != "success":
        failures.append("design_summary.json:simulation_status_not_success")
    for metric in required_metrics:
        if metric in report:
            try:
                csv_value = float(report[metric])
            except Exception:
                failures.append(f"energy_report.csv:non_numeric:{metric}")
                continue
            if not metric_close(csv_value, float(sql_metrics[metric]), rel=0.025, abs_tol=0.05):
                failures.append(f"energy_report.csv:mismatch_with_sql:{metric}")
        else:
            failures.append(f"energy_report.csv:missing_column:{metric}")
        summary_value = (summary.get("metrics") or {}).get(metric)
        if summary_value is not None and not metric_close(float(summary_value), float(sql_metrics[metric]), rel=0.025, abs_tol=0.05):
            failures.append(f"design_summary.json:mismatch_with_sql:{metric}")
    if report.get("case_id") != constraints["case_id"]:
        failures.append("energy_report.csv:case_id_mismatch")
    for key, path_key in [
        ("optimized_idf_sha256", "optimized"),
        ("constraints_sha256", "constraints"),
        ("baseline_idf_sha256", "baseline"),
        ("weather_sha256", "weather"),
    ]:
        if report.get(key) != sha256_file(paths[path_key]):
            failures.append(f"energy_report.csv:hash_mismatch:{key}")
    hard = constraints["hard_constraints"]
    if float(sql_metrics["unmet_hours"]) > float(hard["max_unmet_hours"]):
        failures.append("metrics:unmet_hours_exceed_hard_limit")
    min_total = float(hard["min_total_site_energy_kwh_per_m2"]) * float(variables["floor_area_m2"])
    if float(sql_metrics["total_site_energy_kwh"]) < min_total:
        failures.append("metrics:implausibly_low_total_energy")
    if not metrics_from_energyplus_rerun:
        better_limit = float(hard["max_sql_better_than_model_proxy_fraction"])
        # The proxy assumes nonzero cooling and fan energy, while valid
        # EnergyPlus Ideal Loads models can report both as zero. Keep the
        # aggregate and peak plausibility bounds, but do not reject native SQL
        # solely because its HVAC end-use split is below that approximation.
        for metric in ["total_site_energy_kwh", "eui_kwh_m2", "peak_cooling_kw", "peak_heating_kw", "carbon_kgco2e"]:
            if float(sql_metrics[metric]) < float(proxy[metric]) * (1.0 - better_limit):
                failures.append(f"metrics:sql_unrealistically_better_than_idf_proxy:{metric}")
    return failures


def compare_submitted_sql_to_rerun(submitted: dict, rerun: dict) -> list[str]:
    failures: list[str] = []
    for metric in [
        "total_site_energy_kwh",
        "eui_kwh_m2",
        "heating_kwh",
        "cooling_kwh",
        "lighting_kwh",
        "equipment_kwh",
        "fan_kwh",
    ]:
        if metric in submitted and metric in rerun and not metric_close(float(submitted[metric]), float(rerun[metric]), rel=0.04, abs_tol=0.10):
            failures.append(f"eplusout.sql:submitted_mismatch_with_evaluator_rerun:{metric}")
    return failures


def score_from_metrics(constraints: dict, metrics: dict) -> tuple[float, dict]:
    baseline = constraints["baseline"]["metrics"]
    components: dict[str, float] = {}
    score = 0.0
    for term in constraints["scoring"]["terms"]:
        kind = term["kind"]
        metric = term["metric"]
        if kind == "reduction":
            base_value = float(baseline[metric])
            reduction = max(0.0, (base_value - float(metrics[metric])) / max(0.001, base_value))
            value = clamp(reduction / float(term["target_fraction"]))
        elif kind == "under_limit":
            value = clamp(1.0 - float(metrics[metric]) / float(term["limit"]))
        elif kind == "maximize":
            value = clamp(float(metrics[metric]) / float(term["target"]))
        else:
            value = 0.0
        components[term["name"]] = round(value, 6)
        score += float(term["weight"]) * value
    return round(clamp(score), 6), components


def main() -> None:
    paths = {
        "optimized": DESKTOP / "optimized.idf",
        "sql": DESKTOP / "run" / "eplusout.sql",
        "err": DESKTOP / "run" / "eplusout.err",
        "report": DESKTOP / "energy_report.csv",
        "summary": DESKTOP / "design_summary.json",
        "constraints": DESKTOP / "constraints.json",
        "baseline": DESKTOP / "baseline.idf",
        "weather": DESKTOP / "weather.epw",
    }
    failures: list[str] = []
    for key in ("constraints", "baseline", "weather"):
        if not paths[key].is_file():
            failures.append(f"input_missing:{paths[key].name}")
    if failures:
        write_result({"valid": False, "score": 0.0, "hard_failures": failures, "metrics": {}})
        return
    try:
        constraints = read_json(paths["constraints"])
    except Exception as exc:
        write_result({"valid": False, "score": 0.0, "hard_failures": [f"constraints_json_parse_failed:{exc}"], "metrics": {}})
        return

    metadata, meta_errors, idf_text = extract_metadata(paths["optimized"])
    failures.extend(meta_errors)
    variables: dict = {}
    proxy: dict = {}
    if not meta_errors:
        idf_failures, variables = validate_idf_and_constraints(constraints, metadata, idf_text, paths)
        failures.extend(idf_failures)
        if variables:
            proxy = compute_proxy_metrics(constraints, variables)
    if not paths["err"].is_file():
        failures.append("eplusout.err:missing")
    else:
        err_text = paths["err"].read_text(encoding="utf-8", errors="replace")
        if "Fatal" in err_text or "EnergyPlus Completed Successfully" not in err_text:
            failures.append("eplusout.err:simulation_not_successful")

    area_m2 = float(variables.get("floor_area_m2", constraints["baseline"]["floor_area_m2"])) if variables else float(constraints["baseline"]["floor_area_m2"])
    submitted_sql_metrics, submitted_sql_errors = read_sql_metrics(paths["sql"], area_m2=area_m2, proxy=proxy)
    failures.extend(submitted_sql_errors)
    analysis_sql_metrics = submitted_sql_metrics
    scoring_sql_source = "submitted_sql"
    rerun_paths, rerun_errors = run_openstudio_for_evaluation(paths)
    failures.extend(rerun_errors)
    if rerun_paths:
        rerun_metrics, rerun_sql_errors = read_sql_metrics(rerun_paths["sql"], area_m2=area_m2, proxy=proxy)
        failures.extend([f"openstudio_workflow_rerun:{error}" for error in rerun_sql_errors])
        if not rerun_sql_errors:
            failures.extend(
                f"openstudio_workflow_rerun:{error}"
                for error in validate_native_sql_bindings(
                    rerun_paths["sql"], variables, metadata.get("model_quantities") or {}
                )
            )
            failures.extend(compare_submitted_sql_to_rerun(submitted_sql_metrics, rerun_metrics))
            analysis_sql_metrics = rerun_metrics
            scoring_sql_source = "evaluator_openstudio_workflow_rerun"
        shutil.rmtree(rerun_paths["root"], ignore_errors=True)
    report, report_errors = read_energy_report(paths["report"])
    failures.extend(report_errors)
    try:
        summary = read_json(paths["summary"]) if paths["summary"].is_file() else {}
    except Exception as exc:
        summary = {}
        failures.append(f"design_summary.json:parse_failed:{exc}")
    if not summary:
        failures.append("design_summary.json:missing_or_empty")

    if variables and proxy and not submitted_sql_errors and not report_errors and summary:
        failures.extend(validate_reports(constraints, variables, proxy, analysis_sql_metrics, report, summary, paths, scoring_sql_source == "evaluator_openstudio_workflow_rerun"))

    clean_metrics = {k: v for k, v in analysis_sql_metrics.items() if not k.startswith("_")}
    if failures:
        result = {
            "case_id": constraints.get("case_id"),
            "valid": False,
            "score": 0.0,
            "hard_failures": sorted(set(failures)),
            "metrics": clean_metrics,
            "idf_proxy_metrics": proxy,
            "scoring_sql_source": scoring_sql_source,
        }
    else:
        score, components = score_from_metrics(constraints, clean_metrics)
        result = {
            "case_id": constraints["case_id"],
            "valid": True,
            "score": score,
            "hard_failures": [],
            "metrics": clean_metrics,
            "idf_proxy_metrics": proxy,
            "scoring_sql_source": scoring_sql_source,
            "score_components": components,
            "score_output": str(DESKTOP / "score.json"),
        }
    write_result(result)


if __name__ == "__main__":
    main()
