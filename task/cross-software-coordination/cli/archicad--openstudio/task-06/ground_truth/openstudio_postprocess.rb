require 'openstudio'
require 'json'
require 'digest'
require 'time'
root='C:/Users/user/Desktop'
py='C:/Users/user/Documents/ew06-postprocess.py'
started=Time.now.utc.iso8601(7)
model=OpenStudio::Model::Model.load(OpenStudio::Path.new(root+'/result.osm')).get
window_area=model.getSubSurfaces.select{|s| s.subSurfaceType.downcase.include?('window')}.sum(&:grossArea)
wall_area=model.getSurfaces.select{|s| s.surfaceType=='Wall' && s.outsideBoundaryCondition=='Outdoors'}.sum(&:grossArea)
flow=JSON.parse(File.read(root+'/flow_report.json'))
flow['osm_sha256']=Digest::SHA256.file(root+'/result.osm').hexdigest
flow['window_area_m2']=window_area; flow['gross_outdoor_wall_area_m2']=wall_area; flow['window_wall_ratio']=window_area/wall_area
flow['schedule_set']=model.getSchedules.map{|x| x.nameString}.sort
flow['construction_set']=model.getConstructions.map{|x| x.nameString}.sort
File.write(root+'/flow_report.json',JSON.pretty_generate(flow)+"\n")
ok=system('python',py,root)
raise 'EW06 postprocess failed' unless ok
record={'stage'=>'openstudio_native_postprocess_final_delivery','executable'=>'C:\\openstudio-3.10.0\\bin\\openstudio.exe','executable_sha256'=>Digest::SHA256.file('C:/openstudio-3.10.0/bin/openstudio.exe').hexdigest,'arguments'=>['C:\\Users\\user\\Documents\\ew06-postprocess.rb'],'working_directory'=>'C:\\Users\\user\\Desktop','started_at_utc'=>started,'completed_at_utc'=>Time.now.utc.iso8601(7),'exit_code'=>0,'openstudio_version'=>OpenStudio.openStudioVersion,'script_sha256'=>Digest::SHA256.file(__FILE__).hexdigest,'python_postprocessor_sha256'=>Digest::SHA256.file(py).hexdigest,'result_osm_sha256'=>Digest::SHA256.file(root+'/result.osm').hexdigest,'flow_report_sha256'=>Digest::SHA256.file(root+'/flow_report.json').hexdigest,'model_summary_sha256'=>Digest::SHA256.file(root+'/model_summary.csv').hexdigest,'sql_sha256'=>Digest::SHA256.file(root+'/run/eplusout.sql').hexdigest}
File.write(root+'/openstudio_postprocess_transaction.json',JSON.pretty_generate(record)+"\n")
puts JSON.generate(record)
