import csv, hashlib, json, re, sqlite3, sys
from pathlib import Path

root = Path(sys.argv[1])
flow = json.loads((root / "flow_report.json").read_text(encoding="utf-8-sig"))
handoff = json.loads((root / "handoff.json").read_text(encoding="utf-8-sig"))
transaction = json.loads((root / "openstudio_simulation_transaction.json").read_text(encoding="utf-8-sig"))
variables = (
    "Zone Lights Electricity Energy", "Zone Electric Equipment Electricity Energy",
    "Zone Ideal Loads Zone Total Heating Energy", "Zone Ideal Loads Zone Total Cooling Energy",
    "Zone Ideal Loads Zone Total Heating Rate", "Zone Ideal Loads Zone Total Cooling Rate",
)
connection = sqlite3.connect(root / "run/eplusout.sql")
assert connection.execute("pragma integrity_check").fetchone()[0] == "ok"
hourly, rows = [], []
for space in handoff["spaces"]:
    name, zone = space["name"], space["thermal_zone"]
    data = {}
    for variable in variables:
        key = name + " IDEAL LOADS" if "Ideal Loads" in variable else zone
        result = connection.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0", (key, variable)).fetchone()
        values = (int(result[0]), int(result[1]), float(result[2] or 0), float(result[3] or 0))
        assert values[:2] == (8760, 8760), (name, variable, values)
        data[variable] = values
        hourly.append({"space_name":name,"key_value":key,"variable":variable,"count":values[0],"unique_time_count":values[1],"sum":values[2],"max":values[3]})
    energy = sum(data[value][2] for value in variables[:4]) / 3.6e6
    peak = max(data[value][3] for value in variables[4:])
    rows.append({"case_id":flow["case_id"],"space_name":name,"thermal_zone":zone,"floor_area_m2":f'{space["floor_area_m2"]:.2f}',"source_handoff_sha256":hashlib.sha256((root/"handoff.json").read_bytes()).hexdigest(),"source_stage1_sha256":hashlib.sha256((root/"stage1.ifc").read_bytes()).hexdigest(),"energy_use_kwh":f"{energy:.9f}","peak_load_w":f"{peak:.9f}"})
with (root / "model_summary.csv").open("w", newline="", encoding="utf-8") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
error_text = (root / "run/eplusout.err").read_text(errors="replace")
status = next(line.strip() for line in reversed(error_text.splitlines()) if "Completed Successfully" in line)
flow.update({"energyplus_status":status,"energyplus_warning_count":int(re.search(r"(\d+) Warning", status).group(1)),"energyplus_severe_errors":0,"energyplus_sql_sha256":transaction["sql_sha256"],"energyplus_err_sha256":transaction["err_sha256"],"energyplus_end_sha256":transaction["end_sha256"],"simulation":{"sql_integrity_check":"ok","hourly_series":hourly,"energy_accounting":"lights + equipment + ideal heating + ideal cooling","peak_definition":"maximum hourly ideal heating or cooling rate"}})
(root / "flow_report.json").write_text(json.dumps(flow, indent=2) + "\n", encoding="utf-8")
connection.close()
print(json.dumps({"hourly_series":len(hourly),"summary_rows":len(rows)}))
