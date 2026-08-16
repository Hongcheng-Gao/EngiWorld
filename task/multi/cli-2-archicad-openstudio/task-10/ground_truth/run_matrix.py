import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import zipfile
from pathlib import Path

archive = Path(r"C:\Users\user\Documents\ew10-r2-formal-default.zip")
evaluator = Path(r"C:\Users\user\Desktop\eval.py")
matrix_root = Path(r"C:\EW10-R2-MATRIX")
if matrix_root.exists():
    shutil.rmtree(matrix_root)
matrix_root.mkdir()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rebind_sql_hashes(root):
    sql_hash = sha256(root / "run/eplusout.sql")
    simtx_path = root / "openstudio_simulation_transaction.json"
    simtx = load(simtx_path)
    simtx["sql_sha256"] = sql_hash
    for sample in simtx["stable_file_samples"]:
        sample["sql_sha256"] = sql_hash
    save(simtx_path, simtx)

    posttx_path = root / "openstudio_postprocess_transaction.json"
    posttx = load(posttx_path)
    posttx["sql_sha256"] = sql_hash
    save(posttx_path, posttx)

    flow_path = root / "flow_report.json"
    flow = load(flow_path)
    flow["energyplus_sql_sha256"] = sql_hash
    save(flow_path, flow)
    posttx = load(posttx_path)
    posttx["flow_report_sha256"] = sha256(flow_path)
    save(posttx_path, posttx)


def mutate_json_record(root, key, value):
    handoff_path = root / "handoff.json"
    handoff = load(handoff_path)
    handoff["spaces"][0][key] = value
    save(handoff_path, handoff)


def reorder_hourly_series(root):
    connection = sqlite3.connect(root / "run/eplusout.sql")
    try:
        rows = connection.execute(
            "SELECT rd.rowid,rd.Value FROM ReportData rd "
            "JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) "
            "JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? "
            "AND d.ReportingFrequency='Hourly' AND COALESCE(t.WarmupFlag,0)=0 "
            "ORDER BY t.EnvironmentPeriodIndex,t.Month,t.Day,t.Hour,t.Minute,t.Interval,rd.TimeIndex LIMIT 2",
            ("CONSULT IDEAL LOADS", "Zone Ideal Loads Zone Total Heating Energy"),
        ).fetchall()
        assert len(rows) == 2 and rows[0][1] != rows[1][1]
        connection.execute("UPDATE ReportData SET Value=? WHERE rowid=?", (rows[1][1], rows[0][0]))
        connection.execute("UPDATE ReportData SET Value=? WHERE rowid=?", (rows[0][1], rows[1][0]))
        connection.commit()
    finally:
        connection.close()
    rebind_sql_hashes(root)


def mutate_errors(root):
    connection = sqlite3.connect(root / "run/eplusout.sql")
    try:
        connection.execute("UPDATE Errors SET ErrorMessage=ErrorMessage||' FORGED' WHERE ErrorIndex=(SELECT MIN(ErrorIndex) FROM Errors)")
        connection.commit()
    finally:
        connection.close()
    rebind_sql_hashes(root)


def mutate_completion(root):
    connection = sqlite3.connect(root / "run/eplusout.sql")
    try:
        connection.execute("UPDATE Simulations SET Completed='TRUE',CompletedSuccessfully='TRUE'")
        connection.commit()
    finally:
        connection.close()
    rebind_sql_hashes(root)


cases = [
    ("formal-default", "valid", lambda root: None),
    ("broken-handoff-chain", "invalid", lambda root: mutate_json_record(root, "schedule", "FORGED")),
    ("invalid-target-gid", "invalid", lambda root: mutate_json_record(root, "ifc_global_id", "0" * 22)),
    ("duplicate-target-binding", "invalid", lambda root: mutate_json_record(root, "ifc_global_id", "2donn1s$15fQstYK6K7bhA")),
    ("forged-ifc-area", "invalid", lambda root: mutate_json_record(root, "floor_area_m2", 15)),
    ("false-door-attribution", "invalid", lambda root: mutate_json_record(root, "door_count", 1)),
    ("false-window-attribution", "invalid", lambda root: mutate_json_record(root, "window_count", 1)),
    ("offline-ifc-space-mutation", "invalid", lambda root: (root / "stage1.ifc").write_bytes((root / "stage1.ifc").read_bytes().replace(b"CONTAMINATED-SUPPORT", b"CONTAMINATED-FORGED ", 1))),
    ("missing-ideal-loads", "invalid", lambda root: (root / "result.osm").write_text((root / "result.osm").read_text(errors="ignore").replace("OS:ZoneHVAC:IdealLoadsAirSystem,", "OS:Broken:IdealLoadsAirSystem,", 1), encoding="utf-8")),
    ("patched-idf", "invalid", lambda root: (root / "in.idf").write_text((root / "in.idf").read_text(errors="ignore") + "\n! OFFLINE PATCH\n", encoding="utf-8")),
    ("same-sum-max-time-reorder", "invalid", reorder_hourly_series),
    ("errors-table-mutation", "invalid", mutate_errors),
    ("completion-flags-mutation", "invalid", mutate_completion),
]

results = []
for name, expected, mutate in cases:
    root = matrix_root / name
    root.mkdir()
    with zipfile.ZipFile(archive) as stream:
        stream.extractall(root)
    mutate(root)
    completed = subprocess.run([sys.executable, str(evaluator), str(root)], text=True, capture_output=True, timeout=240)
    actual = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    metrics = load(root / "multi_metrics.json")
    results.append({"case": name, "expected": expected, "actual": actual, "passed": (actual == "True") == (expected == "valid"), "errors": metrics.get("errors", [])})
    shutil.rmtree(root)

report = {"schema": "engiworld.eval-matrix.v2", "isolated_cases": len(results), "all_expected": all(x["passed"] for x in results), "results": results}
(matrix_root / "EVAL_MATRIX.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
