require 'openstudio'
require 'json'
require 'digest'
require 'time'
root='C:/Users/user/Desktop'
py='C:/Users/user/Documents/ew05-postprocess-v2.py'
started=Time.now.utc.iso8601(7)
ok=system('python',py,root)
raise 'postprocess failed' unless ok
record={
  'stage'=>'openstudio_native_postprocess_final_delivery',
  'executable'=>'C:\\openstudio-3.10.0\\bin\\openstudio.exe',
  'executable_sha256'=>Digest::SHA256.file('C:/openstudio-3.10.0/bin/openstudio.exe').hexdigest,
  'arguments'=>['C:\\Users\\user\\Documents\\ew05-postprocess-v2.rb'],
  'working_directory'=>'C:\\Users\\user\\Desktop',
  'started_at_utc'=>started,
  'completed_at_utc'=>Time.now.utc.iso8601(7),
  'exit_code'=>0,
  'openstudio_version'=>OpenStudio.openStudioVersion,
  'script_sha256'=>Digest::SHA256.file(__FILE__).hexdigest,
  'python_postprocessor_sha256'=>Digest::SHA256.file(py).hexdigest,
  'result_osm_sha256'=>Digest::SHA256.file(root+'/result.osm').hexdigest,
  'flow_report_sha256'=>Digest::SHA256.file(root+'/flow_report.json').hexdigest,
  'model_summary_sha256'=>Digest::SHA256.file(root+'/model_summary.csv').hexdigest,
  'sql_sha256'=>Digest::SHA256.file(root+'/run/eplusout.sql').hexdigest
}
File.write(root+'/openstudio_postprocess_transaction.json',JSON.pretty_generate(record)+"\n")
puts JSON.generate(record)
