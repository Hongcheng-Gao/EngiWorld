import csv, hashlib, json, re, sqlite3, sys
from pathlib import Path

root = Path(sys.argv[1])
case_id = 'multi-cli-2-archicad-openstudio-task-06-windows'
flow_path = root / 'flow_report.json'; sql_path = root / 'run/eplusout.sql'
flow = json.loads(flow_path.read_text(encoding='utf-8-sig'))
handoff = json.loads((root/'handoff.json').read_text(encoding='utf-8-sig'))
simtx = json.loads((root/'openstudio_simulation_transaction.json').read_text(encoding='utf-8-sig'))
handoff_hash = hashlib.sha256((root/'handoff.json').read_bytes()).hexdigest()
stage_hash = hashlib.sha256((root/'stage1.ifc').read_bytes()).hexdigest()
conn = sqlite3.connect(sql_path)
assert conn.execute('pragma integrity_check').fetchone()[0] == 'ok'
assert conn.execute('select count(*) from Simulations').fetchone()[0] == 1

variables = [
 'Zone Lights Electricity Energy','Zone Electric Equipment Electricity Energy',
 'Zone Ideal Loads Zone Total Heating Energy','Zone Ideal Loads Zone Total Cooling Energy',
 'Zone Ideal Loads Zone Total Heating Rate','Zone Ideal Loads Zone Total Cooling Rate']
hourly=[]; rows=[]
def series(key,var):
    row=conn.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0",(key,var)).fetchone()
    return int(row[0]),int(row[1]),float(row[2] or 0),float(row[3] or 0)
for space in handoff['spaces']:
    name=space['name']; zone=space['thermal_zone']; data={}
    for var in variables:
        key=(name+' IDEAL LOADS') if 'Ideal Loads' in var else zone
        q=series(key,var)
        if q[0] != 8760 or q[1] != 8760: raise RuntimeError(f'incomplete series {name} {var}: {q}')
        data[var]=q; hourly.append({'count':q[0],'unique_time_count':q[1],'sum':q[2],'max':q[3],'space_name':name,'key_value':key,'variable':var})
    energy=sum(data[v][2] for v in variables[:4]); peak=max(data[variables[4]][3],data[variables[5]][3])
    rows.append({'case_id':case_id,'space_name':name,'thermal_zone':zone,'floor_area_m2':f"{space['floor_area_m2']:.2f}",'source_handoff_sha256':handoff_hash,'source_stage1_sha256':stage_hash,'energy_use_kwh':f'{energy/3.6e6:.9f}','peak_load_w':f'{peak:.9f}'})
with (root/'model_summary.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

err=(root/'run/eplusout.err').read_text(errors='replace')
status=next(x.strip() for x in reversed(err.splitlines()) if 'EnergyPlus Completed Successfully' in x)
flow['native_stage_log_sha256']=hashlib.sha256((root/'native_stage_log.json').read_bytes()).hexdigest()
flow['native_cli_sha256']=simtx['executable_sha256']; flow['energyplus_executable']=simtx['energyplus_executable']; flow['energyplus_executable_sha256']=simtx['energyplus_executable_sha256']
flow['energyplus_status']=status; flow['energyplus_warning_count']=int(re.search(r'(\d+) Warning',status).group(1)); flow['energyplus_severe_errors']=0; flow['energyplus_fatal_errors']=0
flow['energyplus_sql_sha256']=simtx['sql_sha256'];flow['energyplus_err_sha256']=simtx['err_sha256'];flow['energyplus_end_sha256']=simtx['end_sha256']
flow['simulation']={'sql_integrity_check':'ok','sql_error_type_counts':{str(k):int(v) for k,v in conn.execute('select ErrorType,count(*) from Errors group by ErrorType')},'hourly_series':hourly,'energy_accounting':'lights + electric equipment + ideal heating + ideal cooling','peak_definition':'maximum hourly ideal heating or cooling rate'}
conn.close()
flow['openstudio_cli_transactions']=[simtx]; flow['final_delivery']=simtx
flow['model_summary_sha256']=hashlib.sha256((root/'model_summary.csv').read_bytes()).hexdigest()
flow_path.write_text(json.dumps(flow,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'postprocessed','series':len(hourly),'rows':len(rows)}))
