require 'openstudio'
require 'json'
require 'digest'
require 'time'
root='C:/Users/user/Desktop'
started=Time.now.utc.iso8601(7)
model=OpenStudio::Model::Model.load(OpenStudio::Path.new(root+'/result.osm')).get
raise 'native OSM reload failed' unless model.getSpaces.size == 5
raise 'postprocess failed' unless system('python','C:/Users/user/Documents/ew10-post.py',root)
transaction={'stage'=>'openstudio_native_postprocess','executable'=>'C:\openstudio-3.10.0\bin\openstudio.exe','executable_sha256'=>Digest::SHA256.file('C:/openstudio-3.10.0/bin/openstudio.exe').hexdigest,'arguments'=>['C:\Users\user\Documents\ew10-post.rb'],'started_at_utc'=>started,'completed_at_utc'=>Time.now.utc.iso8601(7),'exit_code'=>0,'openstudio_version'=>OpenStudio.openStudioVersion,'script_sha256'=>Digest::SHA256.file(__FILE__).hexdigest,'python_postprocessor_sha256'=>Digest::SHA256.file('C:/Users/user/Documents/ew10-post.py').hexdigest,'result_osm_sha256'=>Digest::SHA256.file(root+'/result.osm').hexdigest,'flow_report_sha256'=>Digest::SHA256.file(root+'/flow_report.json').hexdigest,'model_summary_sha256'=>Digest::SHA256.file(root+'/model_summary.csv').hexdigest,'sql_sha256'=>Digest::SHA256.file(root+'/run/eplusout.sql').hexdigest}
File.write(root+'/openstudio_postprocess_transaction.json',JSON.pretty_generate(transaction)+"\n")
puts JSON.generate(transaction)
