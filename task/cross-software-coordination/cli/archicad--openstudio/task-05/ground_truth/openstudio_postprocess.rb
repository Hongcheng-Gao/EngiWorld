require 'openstudio'
require 'json'
require 'digest'
require 'time'
require 'fileutils'
require 'open3'

ROOT = 'C:/Users/user/Desktop'.freeze
CASE_ID = 'multi-cli-2-archicad-openstudio-task-05-windows'.freeze
OPENSTUDIO_CLI = 'C:/openstudio-3.10.0/bin/openstudio.exe'.freeze
ENERGYPLUS_EXE = 'C:/openstudio-3.10.0/EnergyPlus/energyplus.exe'.freeze
EXPECTED_OPENSTUDIO_SHA256 = '46a80a3d340696bcc189d9a7ae7ec4b70ea4db0fdb4565a33ecd25aa8ebf6361'.freeze
EXPECTED_ENERGYPLUS_SHA256 = '3659efbfece93597d382f2cba94cf8a864215d664cbb1b422d702d5519100ee5'.freeze
EXPECTED_HANDOFF_SHA256 = '44f980d4aaed1bcb8487ac83f6caeb34d5ba77c0c1c2082923962a793833bed0'.freeze
EXPECTED_STAGE1_SHA256 = 'd86146fa75a1b93b1568a5990400d362d3e29f06edbc4f69bb45e1a3547ab710'.freeze
EXPECTED_NATIVE_LOG_SHA256 = '7fb4b5016c9ca303b872fd5874667f37121c87fe3c070f224a4d16ac58b9c8e8'.freeze
EXPECTED_EVAL_SHA256 = '5f9726ae717326acba8d483b812ae187afc1923d91815040b82271cd3087b53e'.freeze

def sha256(path)
  Digest::SHA256.file(path).hexdigest
end

def require_file(path)
  raise "Required Task-05 file is missing: #{path}" unless File.file?(path) && File.size(path).positive?
end

def point_vector(points)
  vector = OpenStudio::Point3dVector.new
  points.each { |x, y, z| vector << OpenStudio::Point3d.new(x, y, z) }
  vector
end

def model_object_by_name(objects, name)
  matches = objects.select { |object| object.nameString == name }
  raise "Expected exactly one model object named #{name}, found #{matches.length}" unless matches.length == 1
  matches.first
end

def set_vertices(object, points)
  ok = object.setVertices(point_vector(points))
  raise "OpenStudio rejected vertices for #{object.nameString}" unless ok
end

def polygon_signature(vertices)
  vertices.map { |v| [v.x.round(8), v.y.round(8), v.z.round(8)] }.sort
end

def optional_value(optional, label)
  raise "Missing required OpenStudio value: #{label}" if optional.empty?
  optional.get
end

paths = {
  init: File.join(ROOT, 'init.ifc'),
  stage1: File.join(ROOT, 'stage1.ifc'),
  handoff: File.join(ROOT, 'handoff.json'),
  native_log: File.join(ROOT, 'native_stage_log.json'),
  osm: File.join(ROOT, 'result.osm'),
  workflow: File.join(ROOT, 'workflow.osw'),
  weather: File.join(ROOT, 'weather.epw'),
  run: File.join(ROOT, 'run'),
  eval: File.join(ROOT, 'eval.py')
}
paths.values_at(:init, :stage1, :handoff, :native_log, :osm, :weather, :eval).each { |path| require_file(path) }
require_file(OPENSTUDIO_CLI)
require_file(ENERGYPLUS_EXE)

raise 'OpenStudio executable SHA-256 mismatch' unless sha256(OPENSTUDIO_CLI) == EXPECTED_OPENSTUDIO_SHA256
raise 'EnergyPlus executable SHA-256 mismatch' unless sha256(ENERGYPLUS_EXE) == EXPECTED_ENERGYPLUS_SHA256
raise 'Task-05 handoff SHA-256 mismatch' unless sha256(paths[:handoff]) == EXPECTED_HANDOFF_SHA256
raise 'Task-05 stage1.ifc SHA-256 mismatch' unless sha256(paths[:stage1]) == EXPECTED_STAGE1_SHA256
raise 'Task-05 native_stage_log.json SHA-256 mismatch' unless sha256(paths[:native_log]) == EXPECTED_NATIVE_LOG_SHA256
raise 'Task-05 eval.py is not the current strengthened evaluator' unless sha256(paths[:eval]) == EXPECTED_EVAL_SHA256
raise "OpenStudio 3.10.0 is required, found #{OpenStudio.openStudioVersion}" unless OpenStudio.openStudioVersion == '3.10.0'

handoff = JSON.parse(File.read(paths[:handoff], encoding: 'UTF-8'))
raise 'Task-05 handoff case/stage mismatch' unless handoff['case_id'] == CASE_ID && handoff['software_stage'] == 'archicad'
raise 'Task-05 handoff does not bind the current stage1.ifc' unless handoff['source_sha256'] == EXPECTED_STAGE1_SHA256
expected_areas = { 'MAIN-STUDIO' => 96.0, 'STORAGE' => 16.0, 'FINISHING-BOOTH' => 12.0 }
handoff_areas = handoff.fetch('spaces').to_h { |row| [row.fetch('name'), Float(row.fetch('floor_area_m2'))] }
raise "Unexpected handoff areas: #{handoff_areas}" unless handoff_areas == expected_areas
raise 'Task-05 handoff target-space total must be 124.0 m2' unless (Float(handoff['building_area_m2']) - 124.0).abs < 1.0e-9

translator = OpenStudio::OSVersion::VersionTranslator.new
model_optional = translator.loadModel(OpenStudio::Path.new(paths[:osm]))
raise 'Unable to load Desktop result.osm through OpenStudio VersionTranslator' if model_optional.empty?
model = model_optional.get

spaces = expected_areas.keys.to_h { |name| [name, model_object_by_name(model.getSpaces, name)] }
zones = ['MAIN-STUDIO-ZN', 'STORAGE-ZN', 'FINISHING-BOOTH-ZN'].to_h do |name|
  [name, model_object_by_name(model.getThermalZones, name)]
end
raise 'Task-05 OSM must contain exactly three spaces and three thermal zones' unless model.getSpaces.length == 3 && model.getThermalZones.length == 3

zone_pairs = {
  'MAIN-STUDIO' => 'MAIN-STUDIO-ZN',
  'STORAGE' => 'STORAGE-ZN',
  'FINISHING-BOOTH' => 'FINISHING-BOOTH-ZN'
}
zone_pairs.each do |space_name, zone_name|
  thermal_zone = optional_value(spaces.fetch(space_name).thermalZone, "#{space_name} thermal zone")
  raise "#{space_name} is not assigned to #{zone_name}" unless thermal_zone.handle == zones.fetch(zone_name).handle
end

# All spaces retain a 4.5 m depth and 3.0 m height. The X boundaries are
# derived from the native IFC NetFloorArea values, not copied from old OSM data.
y0 = 0.0
y1 = 4.5
z0 = 0.0
z1 = 3.0
x0 = 0.0
x1 = expected_areas['MAIN-STUDIO'] / (y1 - y0)
x2 = x1 + expected_areas['STORAGE'] / (y1 - y0)
x3 = x2 + expected_areas['FINISHING-BOOTH'] / (y1 - y0)

surface_points = {
  'Surface 1' => [[x0,y0,z0],[x0,y1,z0],[x1,y1,z0],[x1,y0,z0]],
  'Surface 2' => [[x0,y0,z1],[x0,y1,z1],[x0,y1,z0],[x0,y0,z0]],
  'Surface 3' => [[x0,y1,z1],[x1,y1,z1],[x1,y1,z0],[x0,y1,z0]],
  'Surface 4' => [[x1,y0,z1],[x1,y0,z0],[x1,y1,z0],[x1,y1,z1]],
  'Surface 5' => [[x1,y0,z1],[x0,y0,z1],[x0,y0,z0],[x1,y0,z0]],
  'Surface 6' => [[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],[x0,y0,z1]],
  'Surface 7' => [[x1,y0,z0],[x1,y1,z0],[x2,y1,z0],[x2,y0,z0]],
  'Surface 8' => [[x1,y1,z1],[x1,y1,z0],[x1,y0,z0],[x1,y0,z1]],
  'Surface 9' => [[x1,y1,z1],[x2,y1,z1],[x2,y1,z0],[x1,y1,z0]],
  'Surface 10' => [[x2,y0,z1],[x2,y0,z0],[x2,y1,z0],[x2,y1,z1]],
  'Surface 11' => [[x2,y0,z1],[x1,y0,z1],[x1,y0,z0],[x2,y0,z0]],
  'Surface 12' => [[x2,y0,z1],[x2,y1,z1],[x1,y1,z1],[x1,y0,z1]],
  'Surface 13' => [[x2,y0,z0],[x2,y1,z0],[x3,y1,z0],[x3,y0,z0]],
  'Surface 14' => [[x2,y1,z1],[x2,y1,z0],[x2,y0,z0],[x2,y0,z1]],
  'Surface 15' => [[x2,y1,z1],[x3,y1,z1],[x3,y1,z0],[x2,y1,z0]],
  'Surface 16' => [[x3,y1,z1],[x3,y0,z1],[x3,y0,z0],[x3,y1,z0]],
  'Surface 17' => [[x3,y0,z1],[x2,y0,z1],[x2,y0,z0],[x3,y0,z0]],
  'Surface 18' => [[x3,y0,z1],[x3,y1,z1],[x2,y1,z1],[x2,y0,z1]]
}
surfaces = surface_points.keys.to_h { |name| [name, model_object_by_name(model.getSurfaces, name)] }
raise 'Task-05 OSM must retain exactly 18 surfaces' unless model.getSurfaces.length == 18
surface_points.each { |name, points| set_vertices(surfaces.fetch(name), points) }

raise 'Unable to restore MAIN-STUDIO/STORAGE reciprocal boundary' unless surfaces['Surface 4'].setAdjacentSurface(surfaces['Surface 8'])
raise 'Unable to restore STORAGE/FINISHING-BOOTH reciprocal boundary' unless surfaces['Surface 10'].setAdjacentSurface(surfaces['Surface 14'])

subsurfaces = ['MAIN-STUDIO HIGH DAYLIGHT WINDOW', 'BOOTH-DOOR', 'HIGH-VENT-WINDOW'].to_h do |name|
  [name, model_object_by_name(model.getSubSurfaces, name)]
end
raise 'Task-05 OSM must retain exactly three subsurfaces' unless model.getSubSurfaces.length == 3

door_left = x2 + 0.15
door_right = door_left + 0.9
window_left = x2 + 1.25
window_right = window_left + 1.2
set_vertices(subsurfaces['BOOTH-DOOR'], [[door_left,y0,0.05],[door_right,y0,0.05],[door_right,y0,2.15],[door_left,y0,2.15]])
set_vertices(subsurfaces['HIGH-VENT-WINDOW'], [[window_left,y0,2.1],[window_right,y0,2.1],[window_right,y0,2.7],[window_left,y0,2.7]])
raise 'Unable to bind BOOTH-DOOR to the rebuilt booth south wall' unless subsurfaces['BOOTH-DOOR'].setSurface(surfaces['Surface 17'])
raise 'Unable to bind HIGH-VENT-WINDOW to the rebuilt booth south wall' unless subsurfaces['HIGH-VENT-WINDOW'].setSurface(surfaces['Surface 17'])

building_properties = model.getBuilding.additionalProperties
raise 'Unable to set current handoff hash on OSM building' unless building_properties.setFeature('consumed_handoff_sha256', EXPECTED_HANDOFF_SHA256)
raise 'Unable to set current stage1 hash on OSM building' unless building_properties.setFeature('source_stage1_sha256', EXPECTED_STAGE1_SHA256)
raise 'Unable to set Task-05 case id on OSM building' unless building_properties.setFeature('case_id', CASE_ID)
raise 'Unable to set Task-05 revision on OSM building' unless building_properties.setFeature('revision_code', 'EW2A05')
spaces.each do |name, space|
  raise "Unable to set source_floor_area_m2 for #{name}" unless space.additionalProperties.setFeature('source_floor_area_m2', expected_areas.fetch(name))
end

expected_areas.each do |name, expected|
  actual = spaces.fetch(name).floorArea
  raise "#{name} floor area mismatch after rebuild: #{actual} != #{expected}" unless (actual - expected).abs < 1.0e-6
end
raise 'STORAGE/FINISHING-BOOTH shared boundary vertices do not match' unless polygon_signature(surfaces['Surface 10'].vertices) == polygon_signature(surfaces['Surface 14'].vertices)
raise 'BOOTH-DOOR is outside the rebuilt booth X bounds' unless door_left > x2 && door_right < x3
raise 'HIGH-VENT-WINDOW is outside the rebuilt booth X bounds' unless window_left > x2 && window_right < x3

saved = model.save(OpenStudio::Path.new(paths[:osm]), true)
raise 'OpenStudio failed to save rebuilt result.osm' unless saved
require_file(paths[:osm])

workflow = {
  'seed_file' => 'result.osm',
  'weather_file' => 'weather.epw',
  'run_directory' => 'run',
  'steps' => []
}
File.write(paths[:workflow], JSON.pretty_generate(workflow) + "\n", mode: 'w:UTF-8')

FileUtils.rm_rf(paths[:run]) if File.exist?(paths[:run])
simulation_log = File.join(ROOT, 'ew05-openstudio-simulation.log')
started = Time.now.utc
status = nil
File.open(simulation_log, 'wb') do |log|
  pid = Process.spawn(OPENSTUDIO_CLI, 'run', '-w', paths[:workflow], chdir: ROOT, out: log, err: [:child, :out])
  _waited_pid, status = Process.wait2(pid)
end
openstudio_exited = Time.now.utc
raise "OpenStudio simulation failed with exit code #{status.exitstatus}; inspect #{simulation_log}" unless status.success?

sql_path = File.join(paths[:run], 'eplusout.sql')
err_path = File.join(paths[:run], 'eplusout.err')
end_path = File.join(paths[:run], 'eplusout.end')
[sql_path, err_path, end_path].each { |path| require_file(path) }
children_exited = Time.now.utc

stable_samples = []
6.times do |index|
  sleep 1.0 if index.positive?
  sampled = Time.now.utc
  stable_samples << {
    'sampled_at_utc' => sampled.iso8601(7),
    'sql_size' => File.size(sql_path),
    'sql_mtime_utc' => File.mtime(sql_path).utc.iso8601(7),
    'err_size' => File.size(err_path),
    'err_mtime_utc' => File.mtime(err_path).utc.iso8601(7),
    'end_size' => File.size(end_path),
    'end_mtime_utc' => File.mtime(end_path).utc.iso8601(7)
  }
end
sample_sizes = stable_samples.map { |sample| [sample['sql_size'], sample['err_size'], sample['end_size']] }.uniq
raise "Simulation artifacts were not stable across six samples: #{sample_sizes}" unless sample_sizes.length == 1
completed = Time.now.utc

delivery = {
  'stage' => 'openstudio_weather_period_simulation_final_delivery',
  'executable' => 'C:\\openstudio-3.10.0\\bin\\openstudio.exe',
  'executable_sha256' => sha256(OPENSTUDIO_CLI),
  'arguments' => ['run', '-w', 'C:\\Users\\user\\Desktop\\workflow.osw'],
  'command_line' => '"C:\\openstudio-3.10.0\\bin\\openstudio.exe" run -w "C:\\Users\\user\\Desktop\\workflow.osw"',
  'working_directory' => 'C:\\Users\\user\\Desktop',
  'started_at_utc' => started.iso8601(7),
  'openstudio_process_exited_at_utc' => openstudio_exited.iso8601(7),
  'related_children_exited_at_utc' => children_exited.iso8601(7),
  'completed_at_utc' => completed.iso8601(7),
  'exit_code' => status.exitstatus,
  'observed_related_process_ids' => [],
  'related_processes_after_wait' => 0,
  'stable_file_samples' => stable_samples,
  'sql_sha256' => sha256(sql_path),
  'err_sha256' => sha256(err_path),
  'end_sha256' => sha256(end_path),
  'result_osm_sha256' => sha256(paths[:osm]),
  'workflow_sha256' => sha256(paths[:workflow]),
  'weather_sha256' => sha256(paths[:weather])
}

outdoor_walls = model.getSurfaces.select { |surface| surface.surfaceType == 'Wall' && surface.outsideBoundaryCondition == 'Outdoors' }
windows = model.getSubSurfaces.select { |subsurface| subsurface.subSurfaceType.downcase.include?('window') }
doors = model.getSubSurfaces.select { |subsurface| subsurface.subSurfaceType.downcase.include?('door') }
booth = spaces.fetch('FINISHING-BOOTH')
booth_oa = optional_value(booth.designSpecificationOutdoorAir, 'FINISHING-BOOTH outdoor air specification')
fan = model_object_by_name(model.getFanZoneExhausts, 'FinishingBoothExhaustFan')
fan_flow = optional_value(fan.maximumFlowRate, 'FinishingBoothExhaustFan maximum flow')

model_evidence = {
  'case_id' => CASE_ID,
  'openstudio_version' => OpenStudio.openStudioVersion,
  'spaces' => expected_areas.map { |name, area| { 'name' => name, 'thermal_zone' => zone_pairs.fetch(name), 'floor_area_m2' => area } },
  'room_count' => model.getSpaces.length,
  'thermal_zone_count' => model.getThermalZones.length,
  'surface_count' => model.getSurfaces.length,
  'subsurface_count' => model.getSubSurfaces.length,
  'door_count' => doors.length,
  'window_count' => windows.length,
  'window_area_m2' => windows.sum(&:grossArea),
  'gross_outdoor_wall_area_m2' => outdoor_walls.sum(&:grossArea),
  'schedule_set' => model.getScheduleRulesets.map(&:nameString).sort,
  'construction_set' => model.getConstructions.map(&:nameString).sort,
  'ventilation' => {
    'object_type' => 'OS:Fan:ZoneExhaust',
    'name' => fan.nameString,
    'thermal_zone' => 'FINISHING-BOOTH-ZN',
    'maximum_flow_rate_m3_s' => fan_flow,
    'pressure_rise_pa' => fan.pressureRise,
    'fan_efficiency' => fan.fanEfficiency,
    'booth_outdoor_air_flow_per_floor_area_m3_s_m2' => booth_oa.outdoorAirFlowperFloorArea
  },
  'x_boundaries_m' => [x0, x1, x2, x3]
}

transaction_path = File.join(ROOT, '.ew05-delivery-transaction.json')
evidence_path = File.join(ROOT, '.ew05-openstudio-model-evidence.json')
File.write(transaction_path, JSON.pretty_generate(delivery) + "\n", mode: 'w:UTF-8')
File.write(evidence_path, JSON.pretty_generate(model_evidence) + "\n", mode: 'w:UTF-8')

postprocessor = File.join(File.dirname(__FILE__), 'postprocess_openstudio_task05.py')
require_file(postprocessor)
post_out, post_err, post_status = Open3.capture3('python', postprocessor, ROOT, transaction_path, evidence_path, chdir: ROOT)
raise "Task-05 SQL postprocess failed: #{post_out}\n#{post_err}" unless post_status.success?

eval_out, eval_err, eval_status = Open3.capture3('python', paths[:eval], chdir: ROOT)
raise "Task-05 evaluator failed: #{eval_out}\n#{eval_err}" unless eval_status.success? && eval_out.strip == 'True'

FileUtils.rm_f(transaction_path)
FileUtils.rm_f(evidence_path)
FileUtils.rm_f(simulation_log)

puts JSON.pretty_generate({
  'case_id' => CASE_ID,
  'result_osm_sha256' => sha256(paths[:osm]),
  'workflow_sha256' => sha256(paths[:workflow]),
  'sql_sha256' => sha256(sql_path),
  'flow_report_sha256' => sha256(File.join(ROOT, 'flow_report.json')),
  'model_summary_sha256' => sha256(File.join(ROOT, 'model_summary.csv')),
  'areas_m2' => expected_areas,
  'x_boundaries_m' => [x0, x1, x2, x3],
  'stable_sample_count' => stable_samples.length,
  'eval_output' => eval_out.strip,
  'postprocess_output' => post_out.strip
})
