from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


CASE_ID = "multi-cli-2-archicad-openstudio-task-05-windows"
OPENSTUDIO_EXE = Path(r"C:\openstudio-3.10.0\bin\openstudio.exe")
ENERGYPLUS_EXE = Path(r"C:\openstudio-3.10.0\EnergyPlus\energyplus.exe")
EXPECTED_OPENSTUDIO_SHA256 = "46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361"
EXPECTED_ENERGYPLUS_SHA256 = "3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5"
VARIABLES = (
    "Zone Lights Electricity Energy",
    "Zone Electric Equipment Electricity Energy",
    "Zone Ideal Loads Zone Total Heating Energy",
    "Zone Ideal Loads Zone Total Cooling Energy",
    "Zone Ideal Loads Zone Total Heating Rate",
    "Zone Ideal Loads Zone Total Cooling Rate",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"Expected an object in {path}")
    return data


def series(connection: sqlite3.Connection, key: str, variable: str) -> tuple[int, int, float, float]:
    row = connection.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT rd.TimeIndex),
               COALESCE(SUM(rd.Value), 0), COALESCE(MAX(rd.Value), 0)
        FROM ReportData rd
        JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex)
        JOIN Time t USING(TimeIndex)
        WHERE d.KeyValue=? AND d.Name=?
          AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0
        """,
        (key, variable),
    ).fetchone()
    assert row is not None
    result = int(row[0]), int(row[1]), float(row[2]), float(row[3])
    if result[0] != 8760 or result[1] != 8760:
        raise RuntimeError(f"Incomplete hourly series for {key!r}/{variable!r}: {result[:2]}")
    return result


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: postprocess_openstudio_task05.py ROOT TRANSACTION_JSON MODEL_EVIDENCE_JSON")
    root = Path(sys.argv[1]).resolve()
    transaction = load_json(Path(sys.argv[2]))
    evidence = load_json(Path(sys.argv[3]))

    paths = {
        "init": root / "init.ifc",
        "stage1": root / "stage1.ifc",
        "handoff": root / "handoff.json",
        "native_log": root / "native_stage_log.json",
        "osm": root / "result.osm",
        "workflow": root / "workflow.osw",
        "weather": root / "weather.epw",
        "sql": root / "run" / "eplusout.sql",
        "err": root / "run" / "eplusout.err",
        "end": root / "run" / "eplusout.end",
        "flow": root / "flow_report.json",
        "summary": root / "model_summary.csv",
    }
    for path in paths.values():
        if path in (paths["flow"], paths["summary"]):
            continue
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(path)

    handoff = load_json(paths["handoff"])
    native_log = load_json(paths["native_log"])
    if handoff.get("case_id") != CASE_ID or evidence.get("case_id") != CASE_ID:
        raise RuntimeError("Task-05 case id mismatch")
    if evidence.get("openstudio_version") != "3.10.0":
        raise RuntimeError("OpenStudio model evidence is not from 3.10.0")

    handoff_hash = sha256(paths["handoff"])
    stage1_hash = sha256(paths["stage1"])
    osm_hash = sha256(paths["osm"])
    workflow_hash = sha256(paths["workflow"])
    weather_hash = sha256(paths["weather"])
    if transaction.get("result_osm_sha256") != osm_hash or transaction.get("workflow_sha256") != workflow_hash:
        raise RuntimeError("Simulation transaction does not bind the delivered OSM/workflow")

    err_text = paths["err"].read_text(encoding="utf-8", errors="replace")
    end_text = paths["end"].read_text(encoding="utf-8", errors="replace").strip()
    status_lines = [line.strip() for line in err_text.splitlines() if "EnergyPlus Completed Successfully" in line]
    if not status_lines or "0 Severe Errors" not in status_lines[-1] or "EnergyPlus Completed Successfully" not in end_text:
        raise RuntimeError("EnergyPlus ERR/END do not report a successful zero-severe run")
    energyplus_status = status_lines[-1]
    warning_match = re.search(r"(\d+) Warning", energyplus_status)
    severe_match = re.search(r"(\d+) Severe Errors", energyplus_status)
    if warning_match is None or severe_match is None:
        raise RuntimeError("Unable to parse EnergyPlus completion status")

    rows_by_name = {row["name"]: row for row in handoff["spaces"]}
    expected_spaces = {
        "MAIN-STUDIO": ("MAIN-STUDIO-ZN", 96.0),
        "STORAGE": ("STORAGE-ZN", 16.0),
        "FINISHING-BOOTH": ("FINISHING-BOOTH-ZN", 12.0),
    }
    if set(rows_by_name) != set(expected_spaces):
        raise RuntimeError(f"Unexpected handoff space set: {set(rows_by_name)}")
    for name, (zone, area) in expected_spaces.items():
        row = rows_by_name[name]
        if row.get("thermal_zone") != zone or abs(float(row.get("floor_area_m2", -1)) - area) > 1e-9:
            raise RuntimeError(f"Handoff space mismatch for {name}: {row}")

    connection = sqlite3.connect(f"file:{paths['sql'].as_posix()}?mode=ro", uri=True)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        simulations = connection.execute(
            "SELECT EnergyPlusVersion, Completed, CompletedSuccessfully FROM Simulations"
        ).fetchall()
        if integrity != "ok" or len(simulations) != 1:
            raise RuntimeError(f"SQL integrity/simulation mismatch: {integrity}/{simulations}")
        energyplus_version = str(simulations[0][0])
        if not energyplus_version.startswith("EnergyPlus, Version 25.1.0-1c11a3d85f, YMD="):
            raise RuntimeError(f"Unexpected EnergyPlus version: {energyplus_version}")
        sql_error_type_counts = {
            str(kind): int(count)
            for kind, count in connection.execute(
                "SELECT ErrorType, COUNT(*) FROM Errors GROUP BY ErrorType"
            )
        }

        hourly_series: list[dict[str, Any]] = []
        values: dict[str, dict[str, tuple[int, int, float, float]]] = {}
        for name, (zone, _area) in expected_spaces.items():
            values[name] = {}
            for variable in VARIABLES:
                key = f"{name} IDEAL LOADS" if "Ideal Loads" in variable else zone
                result = series(connection, key, variable)
                values[name][variable] = result
                hourly_series.append(
                    {
                        "count": result[0],
                        "unique_time_count": result[1],
                        "sum": result[2],
                        "max": result[3],
                        "space_name": name,
                        "key_value": key,
                        "variable": variable,
                    }
                )
        fan_key = "FINISHINGBOOTHEXHAUSTFAN"
        fan_result = series(connection, fan_key, "Fan Electricity Energy")
        hourly_series.append(
            {
                "count": fan_result[0],
                "unique_time_count": fan_result[1],
                "sum": fan_result[2],
                "max": fan_result[3],
                "space_name": "FINISHING-BOOTH",
                "key_value": fan_key,
                "variable": "Fan Electricity Energy",
            }
        )
    finally:
        connection.close()

    summary_rows: list[dict[str, str]] = []
    for name, (zone, area) in expected_spaces.items():
        energy_j = sum(values[name][variable][2] for variable in VARIABLES[:4])
        if name == "FINISHING-BOOTH":
            energy_j += fan_result[2]
        peak_w = max(values[name][variable][3] for variable in VARIABLES[4:])
        if energy_j <= 0 or peak_w <= 0:
            raise RuntimeError(f"Non-positive SQL energy/peak for {name}")
        summary_rows.append(
            {
                "case_id": CASE_ID,
                "space_name": name,
                "thermal_zone": zone,
                "floor_area_m2": f"{area:.2f}",
                "source_handoff_sha256": handoff_hash,
                "source_stage1_sha256": stage1_hash,
                "energy_use_kwh": f"{energy_j / 3_600_000.0:.9f}",
                "peak_load_w": f"{peak_w:.9f}",
            }
        )
    with paths["summary"].open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    first_weather_line = paths["weather"].read_text(encoding="utf-8-sig", errors="replace").splitlines()[0]
    weather_parts = [part.strip() for part in first_weather_line.split(",")]
    if len(weather_parts) < 10 or weather_parts[0].upper() != "LOCATION":
        raise RuntimeError("Invalid EPW LOCATION header")

    native_transactions = native_log.get("native_transactions", {})
    native_items = native_transactions.get("Items", []) if isinstance(native_transactions, dict) else native_transactions
    if not isinstance(native_items, list) or len(native_items) != 12:
        raise RuntimeError("Native Archicad log does not contain exactly 12 transactions")

    window_area = float(evidence["window_area_m2"])
    gross_wall_area = float(evidence["gross_outdoor_wall_area_m2"])
    if window_area <= 0 or gross_wall_area <= 0:
        raise RuntimeError("Invalid OpenStudio window/wall geometry evidence")

    flow = {
        "schema": "engiworld-openstudio-native-flow-report-v2",
        "case_id": CASE_ID,
        "software_stage": "openstudio",
        "consumed_handoff_sha256": handoff_hash,
        "source_stage1_sha256": stage1_hash,
        "native_stage_log_sha256": sha256(paths["native_log"]),
        "osm_sha256": osm_hash,
        "workflow_sha256": workflow_hash,
        "weather_sha256": weather_hash,
        "building_area_m2": sum(area for _zone, area in expected_spaces.values()),
        "room_count": int(evidence["room_count"]),
        "thermal_zone_count": int(evidence["thermal_zone_count"]),
        "door_count": int(evidence["door_count"]),
        "window_count": int(evidence["window_count"]),
        "window_wall_ratio": window_area / gross_wall_area,
        "surface_count": int(evidence["surface_count"]),
        "subsurface_count": int(evidence["subsurface_count"]),
        "weather_file": "weather.epw",
        "schedule_set": evidence["schedule_set"],
        "construction_set": evidence["construction_set"],
        "openstudio_version": evidence["openstudio_version"],
        "native_cli_executable": str(OPENSTUDIO_EXE),
        "native_cli_sha256": sha256(OPENSTUDIO_EXE),
        "energyplus_executable": str(ENERGYPLUS_EXE),
        "energyplus_executable_sha256": sha256(ENERGYPLUS_EXE),
        "energyplus_version": energyplus_version,
        "energyplus_status": energyplus_status,
        "energyplus_warning_count": int(warning_match.group(1)),
        "energyplus_severe_errors": int(severe_match.group(1)),
        "energyplus_fatal_errors": 0,
        "energyplus_sql_sha256": sha256(paths["sql"]),
        "energyplus_err_sha256": sha256(paths["err"]),
        "energyplus_end_sha256": sha256(paths["end"]),
        "model_summary_sha256": sha256(paths["summary"]),
        "spaces": [
            {"name": name, "thermal_zone": zone, "floor_area_m2": area}
            for name, (zone, area) in expected_spaces.items()
        ],
        "ventilation": evidence["ventilation"],
        "weather_source": {
            "kind": "same_station_tmy3",
            "location_data_source": weather_parts[4],
            "wmo": weather_parts[5],
            "latitude": float(weather_parts[6]),
            "longitude": float(weather_parts[7]),
            "time_zone": float(weather_parts[8]),
            "elevation_m": float(weather_parts[9]),
            "sha256": weather_hash,
        },
        "simulation": {
            "sql_integrity_check": integrity,
            "sql_error_type_counts": sql_error_type_counts,
            "hourly_series": hourly_series,
            "energy_accounting": "lights + electric equipment + ideal heating + ideal cooling; booth additionally includes exhaust fan electricity",
            "peak_definition": "maximum hourly ideal heating or cooling rate",
        },
        "openstudio_cli_transactions": [transaction],
        "final_delivery": transaction,
        "archicad_native_transaction_count": len(native_items),
        "window_area_m2": window_area,
        "gross_outdoor_wall_area_m2": gross_wall_area,
        "x_boundaries_m": evidence["x_boundaries_m"],
    }
    if flow["native_cli_sha256"] != EXPECTED_OPENSTUDIO_SHA256:
        raise RuntimeError("OpenStudio executable changed during postprocess")
    if flow["energyplus_executable_sha256"] != EXPECTED_ENERGYPLUS_SHA256:
        raise RuntimeError("EnergyPlus executable changed during postprocess")

    with paths["flow"].open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(flow, stream, indent=2, ensure_ascii=False)
        stream.write("\n")

    print(
        json.dumps(
            {
                "status": "postprocessed",
                "hourly_series": len(hourly_series),
                "building_area_m2": flow["building_area_m2"],
                "window_wall_ratio": flow["window_wall_ratio"],
                "model_summary_sha256": flow["model_summary_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
