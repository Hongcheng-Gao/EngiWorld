import csv, hashlib, json, sqlite3, sys
from pathlib import Path

root=Path(sys.argv[1]); flow_path=root/'flow_report.json'; osm_path=root/'result.osm'; sql_path=root/'run/eplusout.sql'; err_path=root/'run/eplusout.err'
sys.path.insert(0,str(root)); ev=__import__('eval')
errors=[]; handoff_hash=hashlib.sha256((root/'handoff.json').read_bytes()).hexdigest()
osm=ev.check_osm(osm_path,handoff_hash,ev.CASE_SPEC['required_spaces'],ev.CASE_SPEC['required_zones'],ev.CASE_SPEC['osm_tokens'],['weather_file','schedule_set','construction_set'],errors)
if errors: raise RuntimeError(errors)
flow=json.loads(flow_path.read_text(encoding='utf-8-sig'))
flow['window_area_m2']=osm['_window_area']; flow['gross_outdoor_wall_area_m2']=osm['_gross_outdoor_wall_area']; flow['window_wall_ratio']=osm['_wwr']
flow['schedule_set']=osm['_schedule_names']; flow['construction_set']=osm['_construction_names']
flow['weather_source']={k:v for k,v in flow['weather_source'].items() if k not in ('source_task','source_path_in_that_delivery')}
c=sqlite3.connect(str(sql_path)); flow['simulation']['sql_error_type_counts']={str(k):int(v) for k,v in c.execute('select ErrorType,count(*) from Errors group by ErrorType')}
status=next(x.strip() for x in reversed(err_path.read_text(errors='replace').splitlines()) if 'EnergyPlus Completed Successfully' in x)
import re
flow['energyplus_warning_count']=int(re.search(r'(\d+) Warning',status).group(1)); flow['energyplus_status']=status
variables=['Zone Lights Electricity Energy','Zone Electric Equipment Electricity Energy','Zone Ideal Loads Zone Total Heating Energy','Zone Ideal Loads Zone Total Cooling Energy','Zone Ideal Loads Zone Total Heating Rate','Zone Ideal Loads Zone Total Cooling Rate']
spaces={'MAIN-STUDIO':('MAIN-STUDIO-ZN',31.78),'STORAGE':('STORAGE-ZN',15.44),'FINISHING-BOOTH':('FINISHING-BOOTH-ZN',27.0)}
hourly=[]; rows=[]
def series(key,var):
 r=c.execute("SELECT COUNT(*),COUNT(DISTINCT rd.TimeIndex),SUM(rd.Value),MAX(rd.Value) FROM ReportData rd JOIN ReportDataDictionary d USING(ReportDataDictionaryIndex) JOIN Time t USING(TimeIndex) WHERE d.KeyValue=? AND d.Name=? AND d.ReportingFrequency='Hourly' AND t.WarmupFlag=0",(key,var)).fetchone();return int(r[0]),int(r[1]),float(r[2] or 0),float(r[3] or 0)
all_data={}
for name,(zone,area) in spaces.items():
 all_data[name]={}
 for var in variables:
  key=f'{name} IDEAL LOADS' if 'Ideal Loads' in var else zone; q=series(key,var);all_data[name][var]=q;hourly.append({'count':q[0],'unique_time_count':q[1],'sum':q[2],'max':q[3],'space_name':name,'key_value':key,'variable':var})
fan=series('FINISHINGBOOTHEXHAUSTFAN','Fan Electricity Energy');hourly.append({'count':fan[0],'unique_time_count':fan[1],'sum':fan[2],'max':fan[3],'space_name':'FINISHING-BOOTH','key_value':'FINISHINGBOOTHEXHAUSTFAN','variable':'Fan Electricity Energy'})
c.close(); flow['simulation']['hourly_series']=hourly
for name,(zone,area) in spaces.items():
 energy=sum(all_data[name][v][2] for v in variables[:4])+(fan[2] if name=='FINISHING-BOOTH' else 0);peak=max(all_data[name][variables[4]][3],all_data[name][variables[5]][3])
 rows.append({'case_id':ev.CASE_SPEC['case_id'],'space_name':name,'thermal_zone':zone,'floor_area_m2':f'{area:.2f}','source_handoff_sha256':handoff_hash,'source_stage1_sha256':hashlib.sha256((root/'stage1.ifc').read_bytes()).hexdigest(),'energy_use_kwh':f'{energy/3.6e6:.9f}','peak_load_w':f'{peak:.9f}'})
with (root/'model_summary.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
flow['model_summary_sha256']=hashlib.sha256((root/'model_summary.csv').read_bytes()).hexdigest()
flow_path.write_text(json.dumps(flow,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'postprocessed','wwr':flow['window_wall_ratio'],'series':len(hourly)}))
