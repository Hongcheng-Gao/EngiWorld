require 'openstudio'
require 'json'
require 'digest'

root = 'C:/Users/user/Desktop'
model = OpenStudio::Model::Model.load(OpenStudio::Path.new(root + '/result.osm')).get
raise 'native OSM reload failed' unless model.getSpaces.size == 4
raise 'postprocess failed' unless system('python', 'C:/Users/user/Documents/ew09-post.py', root)
puts JSON.generate({
  'stage'=>'openstudio_native_postprocess',
  'openstudio_version'=>OpenStudio.openStudioVersion,
  'result_osm_sha256'=>Digest::SHA256.file(root + '/result.osm').hexdigest,
  'flow_report_sha256'=>Digest::SHA256.file(root + '/flow_report.json').hexdigest,
  'model_summary_sha256'=>Digest::SHA256.file(root + '/model_summary.csv').hexdigest,
  'sql_sha256'=>Digest::SHA256.file(root + '/run/eplusout.sql').hexdigest
})
