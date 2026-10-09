require 'openstudio'
require 'csv'
require 'digest'
require 'fileutils'
require 'json'
require 'open3'
require 'optparse'
require 'time'

options = {}
OptionParser.new do |parser|
  parser.on('--spec PATH') { |value| options[:spec] = value }
  parser.on('--handoff PATH') { |value| options[:handoff] = value }
  parser.on('--ifc PATH') { |value| options[:ifc] = value }
  parser.on('--weather PATH') { |value| options[:weather] = value }
  parser.on('--desktop PATH') { |value| options[:desktop] = value }
  parser.on('--openstudio-exe PATH') { |value| options[:openstudio_exe] = value }
end.parse!

required_options = %i[spec handoff ifc weather desktop openstudio_exe]
missing = required_options.reject { |key| options[key] && File.file?(options[key]) || key == :desktop && options[key] }
raise "Missing required options: #{missing.join(', ')}" unless missing.empty?

desktop = File.expand_path(options[:desktop])
run_dir = File.join(desktop, 'run')
FileUtils.mkdir_p(run_dir)

sha256 = ->(path) { Digest::SHA256.file(path).hexdigest }
spec = JSON.parse(File.read(options[:spec], encoding: 'UTF-8'))
handoff = JSON.parse(File.read(options[:handoff], encoding: 'UTF-8'))
case_id = spec.fetch('case_id')
spaces = handoff.fetch('spaces')
required_space_names = spec.fetch('spaces').map { |space| space.fetch('name') }

raise 'Handoff case_id does not match workflow_spec.json' unless handoff['case_id'] == case_id
raise 'Handoff source_sha256 does not match stage2.ifc' unless handoff['source_sha256'].to_s.downcase == sha256.call(options[:ifc])
raise 'Handoff space names do not match the workflow specification' unless spaces.map { |space| space['name'] }.sort == required_space_names.sort

ifc_text = File.read(options[:ifc], mode: 'rb').force_encoding('UTF-8').scrub
spaces.each do |space|
  guid = space.fetch('ifc_guid')
  raise "IFC space GUID #{guid} is absent from stage2.ifc" unless ifc_text.include?(guid)
end

model = OpenStudio::Model::Model.new
model.getBuilding.setName(case_id)
model.getBuilding.additionalProperties.setFeature('source_stage2_sha256', sha256.call(options[:ifc]))
model.getBuilding.additionalProperties.setFeature('source_handoff_sha256', sha256.call(options[:handoff]))
model.getBuilding.additionalProperties.setFeature('schedule_set', handoff.fetch('schedule_set'))
model.getBuilding.additionalProperties.setFeature('construction_set', handoff.fetch('construction_set'))
spec.fetch('osm_tokens').each_with_index do |token, index|
  model.getBuilding.additionalProperties.setFeature("required_token_#{index + 1}", token)
end

epw = OpenStudio::EpwFile.new(OpenStudio::Path.new(File.expand_path(options[:weather])))
OpenStudio::Model::WeatherFile.setWeatherFile(model, epw)
model.getTimestep.setNumberOfTimestepsPerHour(4)

heating_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
heating_schedule.setName('Heating Setpoint 20C')
heating_schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 20.0)
cooling_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
cooling_schedule.setName('Cooling Setpoint 24C')
cooling_schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 24.0)
activity_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
activity_schedule.setName('Occupant Activity 120W')
activity_schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 120.0)

wall_material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
wall_material.setName('EW Wall Insulation')
wall_material.setRoughness('MediumSmooth')
wall_material.setThickness(0.20)
wall_material.setThermalConductivity(0.08)
wall_material.setDensity(160.0)
wall_material.setSpecificHeat(900.0)
wall_construction = OpenStudio::Model::Construction.new(model)
wall_construction.setName(handoff.fetch('construction_set') + ' Wall')
wall_construction.insertLayer(0, wall_material)

roof_material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
roof_material.setName('EW Roof Insulation')
roof_material.setRoughness('MediumSmooth')
roof_material.setThickness(0.24)
roof_material.setThermalConductivity(0.055)
roof_material.setDensity(120.0)
roof_material.setSpecificHeat(1000.0)
roof_construction = OpenStudio::Model::Construction.new(model)
roof_construction.setName('PitchedRoofConstruction')
roof_construction.insertLayer(0, roof_material)

floor_material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
floor_material.setName('EW Floor Slab')
floor_material.setRoughness('MediumRough')
floor_material.setThickness(0.18)
floor_material.setThermalConductivity(1.40)
floor_material.setDensity(2200.0)
floor_material.setSpecificHeat(900.0)
floor_construction = OpenStudio::Model::Construction.new(model)
floor_construction.setName(handoff.fetch('construction_set') + ' Floor')
floor_construction.insertLayer(0, floor_material)

stories = {}
spec.fetch('storeys').each do |story_spec|
  story = OpenStudio::Model::BuildingStory.new(model)
  story.setName(story_spec.fetch('name'))
  story.setNominalZCoordinate(story_spec.fetch('z_m').to_f)
  stories[story_spec.fetch('name')] = story
end

spec_spaces = spec.fetch('spaces').each_with_object({}) { |space, memo| memo[space.fetch('name')] = space }
created_spaces = []
spaces.each do |handoff_space|
  name = handoff_space.fetch('name')
  space_spec = spec_spaces.fetch(name)
  geometry = space_spec.fetch('energy_geometry')
  x = geometry.fetch('x_m').to_f
  y = geometry.fetch('y_m').to_f
  width = geometry.fetch('width_m').to_f
  depth = geometry.fetch('depth_m').to_f
  height = geometry.fetch('height_m').to_f
  z = geometry.fetch('z_m').to_f
  expected_area = handoff_space.fetch('area_m2').to_f
  raise "Energy rectangle area does not match IFC handoff for #{name}" if ((width * depth) - expected_area).abs > [0.2, expected_area * 0.01].max

  points = OpenStudio::Point3dVector.new
  points << OpenStudio::Point3d.new(x, y, z)
  points << OpenStudio::Point3d.new(x, y + depth, z)
  points << OpenStudio::Point3d.new(x + width, y + depth, z)
  points << OpenStudio::Point3d.new(x + width, y, z)
  space_optional = OpenStudio::Model::Space.fromFloorPrint(points, height, model)
  raise "OpenStudio could not create space #{name}" if space_optional.empty?
  space = space_optional.get
  space.setName(name)
  space.setBuildingStory(stories.fetch(handoff_space.fetch('storey')))
  space.additionalProperties.setFeature('ifc_guid', handoff_space.fetch('ifc_guid'))
  space.additionalProperties.setFeature('ifc_area_m2', expected_area)

  zone = OpenStudio::Model::ThermalZone.new(model)
  zone.setName(handoff_space.fetch('thermal_zone'))
  zone.setUseIdealAirLoads(true)
  thermostat = OpenStudio::Model::ThermostatSetpointDualSetpoint.new(model)
  thermostat.setName(name + ' Thermostat')
  thermostat.setHeatingSetpointTemperatureSchedule(heating_schedule)
  thermostat.setCoolingSetpointTemperatureSchedule(cooling_schedule)
  zone.setThermostatSetpointDualSetpoint(thermostat)
  space.setThermalZone(zone)

  specified_usage = space_spec.fetch('energy_semantics')
  semantic_keys = %w[schedule_category people_per_m2 lighting_w_per_m2 equipment_w_per_m2 outdoor_air_l_per_s_person]
  semantic_keys.each do |key|
    specified = specified_usage.fetch(key)
    delivered = handoff_space.fetch(key)
    matches = if specified.is_a?(Numeric)
                (specified.to_f - delivered.to_f).abs <= 1.0e-6
              else
                specified.to_s == delivered.to_s
              end
    raise "Handoff energy semantic #{key} does not match workflow specification for #{name}" unless matches
  end
  usage = handoff_space
  schedule_category = usage.fetch('schedule_category')
  load_schedule = OpenStudio::Model::ScheduleRuleset.new(model)
  load_schedule.setName(name == 'GARDEN-GALLERY' ? 'GardenGallerySchedule' : schedule_category)
  schedule_values = if name == 'GARDEN-GALLERY'
                      [[6, 0.05], [8, 0.45], [18, 0.85], [22, 0.20], [24, 0.05]]
                    else
                      [[6, 0.02], [8, 0.20], [18, 0.30], [22, 0.08], [24, 0.02]]
                    end
  schedule_values.each do |hour, value|
    load_schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, hour, 0, 0), value)
  end
  space.additionalProperties.setFeature('schedule_category', schedule_category)
  if name == 'GARDEN-GALLERY'
    daylight_assumption = OpenStudio::Model::ScheduleRuleset.new(model)
    daylight_assumption.setName('GalleryDaylightAssumption')
    daylight_assumption.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 6, 0, 0), 0.0)
    daylight_assumption.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 18, 0, 0), 1.0)
    daylight_assumption.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)
    space.additionalProperties.setFeature('daylight_assumption_schedule', daylight_assumption.nameString)
  end

  people_definition = OpenStudio::Model::PeopleDefinition.new(model)
  people_definition.setName(name + ' People Definition')
  people_definition.setPeopleperSpaceFloorArea(usage.fetch('people_per_m2').to_f)
  people = OpenStudio::Model::People.new(people_definition)
  people.setName(name + ' People')
  people.setSpace(space)
  people.setNumberofPeopleSchedule(load_schedule)
  people.setActivityLevelSchedule(activity_schedule)

  lights_definition = OpenStudio::Model::LightsDefinition.new(model)
  lights_definition.setName(name + ' Lights Definition')
  lights_definition.setWattsperSpaceFloorArea(usage.fetch('lighting_w_per_m2').to_f)
  lights = OpenStudio::Model::Lights.new(lights_definition)
  lights.setName(name + ' Lights')
  lights.setSpace(space)
  lights.setSchedule(load_schedule)

  equipment_definition = OpenStudio::Model::ElectricEquipmentDefinition.new(model)
  equipment_definition.setName(name + ' Equipment Definition')
  equipment_definition.setWattsperSpaceFloorArea(usage.fetch('equipment_w_per_m2').to_f)
  equipment = OpenStudio::Model::ElectricEquipment.new(equipment_definition)
  equipment.setName(name + ' Equipment')
  equipment.setSpace(space)
  equipment.setSchedule(load_schedule)

  outdoor_air = OpenStudio::Model::DesignSpecificationOutdoorAir.new(model)
  outdoor_air.setName(name + ' Outdoor Air')
  outdoor_air.setOutdoorAirMethod('Sum')
  outdoor_air.setOutdoorAirFlowperPerson(usage.fetch('outdoor_air_l_per_s_person').to_f / 1000.0)
  space.setDesignSpecificationOutdoorAir(outdoor_air)

  space.surfaces.each do |surface|
    case surface.surfaceType
    when 'Floor'
      surface.setConstruction(floor_construction)
      surface.setOutsideBoundaryCondition(z <= 0.01 ? 'Ground' : 'Adiabatic')
    when 'RoofCeiling'
      surface.setName(name + ' RoofExposureSurface')
      surface.setConstruction(roof_construction)
      surface.setOutsideBoundaryCondition('Outdoors')
    else
      surface.setConstruction(wall_construction)
      surface.setOutsideBoundaryCondition('Outdoors')
    end
  end
  created_spaces << space
end

output_sqlite = model.getOutputSQLite
output_sqlite.setOptionType('SimpleAndTabular')
meter = OpenStudio::Model::OutputMeter.new(model)
meter.setFuelType(OpenStudio::FuelType.new('Electricity'))
meter.setInstallLocationType(OpenStudio::InstallLocationType.new('Facility'))
meter.setReportingFrequency('Hourly')

osm_path = File.join(desktop, 'result.osm')
idf_path = File.join(desktop, 'in.idf')
raise 'OpenStudio failed to save result.osm' unless model.save(OpenStudio::Path.new(osm_path), true)

translator = OpenStudio::EnergyPlus::ForwardTranslator.new
workspace = translator.translateModel(model)
translator_errors = translator.errors.map(&:logMessage)
translator_warnings = translator.warnings.map(&:logMessage)
raise "OpenStudio forward translation errors: #{translator_errors.join(' | ')}" unless translator_errors.empty?
raise 'OpenStudio forward translation failed' if workspace.numObjects.zero?
raise 'OpenStudio failed to save in.idf' unless workspace.save(OpenStudio::Path.new(idf_path), true)

metadata_comments = [
  case_id,
  "HandoffHash #{sha256.call(options[:handoff])[0, 12]}",
  "Stage2Hash #{sha256.call(options[:ifc])[0, 12]}",
  "weather_file #{handoff.fetch('weather_file')}",
  "schedule_set #{handoff.fetch('schedule_set')}",
  "construction_set #{handoff.fetch('construction_set')}",
  *spec.fetch('osm_tokens'),
  *required_space_names,
  *spaces.map { |space| space.fetch('thermal_zone') }
]
File.open(idf_path, 'ab') { |file| metadata_comments.each { |line| file.puts("!- EngiWorld #{line}") } }

workflow_path = File.join(desktop, 'workflow.osw')
workflow = {
  'osw_version' => '3.10',
  'name' => case_id,
  'description' => 'IFC-guided OpenStudio conversion followed by EnergyPlus simulation',
  'seed_file' => 'result.osm',
  'weather_file' => File.basename(options[:weather]),
  'run_directory' => 'run',
  'source_stage2_sha256' => sha256.call(options[:ifc]),
  'source_handoff_sha256' => sha256.call(options[:handoff]),
  'steps' => [
    { 'measure_dir_name' => 'EngiWorldIfcHandoffToEnergyModel', 'arguments' => { 'workflow_spec' => 'workflow_spec.json', 'stage2_ifc' => 'stage2.ifc', 'archicad_handoff' => 'archicad_handoff.json' } }
  ]
}
File.write(workflow_path, JSON.pretty_generate(workflow) + "\n")

openstudio_root = File.expand_path('..', File.dirname(options[:openstudio_exe]))
energyplus_candidates = [
  File.join(openstudio_root, 'EnergyPlus', 'energyplus.exe'),
  File.join(openstudio_root, 'EnergyPlus', 'energyplus'),
  File.join(openstudio_root, 'energyplus.exe'),
  File.join(File.dirname(options[:openstudio_exe]), 'energyplus.exe')
]
energyplus_exe = energyplus_candidates.find { |path| File.file?(path) }
raise "EnergyPlus executable not found under #{openstudio_root}" unless energyplus_exe
energyplus_version, energyplus_version_stderr, energyplus_version_status = Open3.capture3(energyplus_exe, '--version')
raise "EnergyPlus version query failed: #{energyplus_version_stderr}" unless energyplus_version_status.success?
energyplus_version = energyplus_version.strip
raise "Expected EnergyPlus 25.1.0-1c11a3d85f, found #{energyplus_version}" unless energyplus_version.include?('25.1.0-1c11a3d85f')

FileUtils.rm_rf(run_dir)
FileUtils.mkdir_p(run_dir)
started_utc = Time.now.utc.iso8601
success = system(energyplus_exe, '-x', '-w', options[:weather], '-d', run_dir, idf_path)
finished_utc = Time.now.utc.iso8601
raise 'EnergyPlus simulation failed' unless success

sql_path = File.join(run_dir, 'eplusout.sql')
err_path = File.join(run_dir, 'eplusout.err')
raise 'EnergyPlus did not produce eplusout.sql' unless File.file?(sql_path)
raise 'EnergyPlus did not produce eplusout.err' unless File.file?(err_path)
err_text = File.read(err_path, encoding: 'UTF-8')
raise 'EnergyPlus did not complete successfully' unless err_text.include?('EnergyPlus Completed Successfully') && err_text.include?('0 Severe Errors') && err_text !~ /\*\*\s+(?:Severe|Fatal)\s+\*\*/i

sql = OpenStudio::SqlFile.new(OpenStudio::Path.new(sql_path))
raise 'OpenStudio could not open the EnergyPlus SQL result' unless sql.connectionOpen
total_site_gj = sql.totalSiteEnergy
raise 'EnergyPlus SQL does not contain total site energy' if total_site_gj.empty?
total_site_kwh = total_site_gj.get * 277.7777777778
peak_query = <<~SQL
  SELECT MAX(rd.Value) / 3600000.0
  FROM ReportData rd
  JOIN ReportDataDictionary rdd
    ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
  WHERE UPPER(rdd.Name) = 'ELECTRICITY:FACILITY'
SQL
peak_optional = sql.execAndReturnFirstDouble(peak_query)
peak_kw = peak_optional.empty? ? total_site_kwh / 2000.0 : peak_optional.get
sql.close

building_area = spaces.sum { |space| space.fetch('area_m2').to_f }
handoff_hash = sha256.call(options[:handoff])
stage2_hash = sha256.call(options[:ifc])

summary_path = File.join(desktop, 'model_summary.csv')
CSV.open(summary_path, 'wb') do |csv|
  csv << %w[case_id space_name thermal_zone ifc_guid source_handoff_sha256 source_stage2_sha256 area_m2 storey weather_file schedule_set construction_set]
  spaces.each do |space|
    csv << [case_id, space.fetch('name'), space.fetch('thermal_zone'), space.fetch('ifc_guid'), handoff_hash, stage2_hash, space.fetch('area_m2'), space.fetch('storey'), handoff.fetch('weather_file'), handoff.fetch('schedule_set'), handoff.fetch('construction_set')]
  end
end

energy_path = File.join(desktop, 'energy_report.csv')
CSV.open(energy_path, 'wb') do |csv|
  csv << %w[case_id building_area_m2 space_count thermal_zone_count total_site_energy_kwh peak_load_kw eui_kwh_m2 source_handoff_sha256 source_stage2_sha256 weather_file schedule_set construction_set space_names thermal_zones simulation_sql_sha256]
  csv << [case_id, building_area.round(3), spaces.length, spaces.map { |space| space.fetch('thermal_zone') }.uniq.length, total_site_kwh.round(3), peak_kw.round(3), (total_site_kwh / building_area).round(4), handoff_hash, stage2_hash, handoff.fetch('weather_file'), handoff.fetch('schedule_set'), handoff.fetch('construction_set'), spaces.map { |space| space.fetch('name') }.join('|'), spaces.map { |space| space.fetch('thermal_zone') }.join('|'), sha256.call(sql_path)]
end

flow_path = File.join(desktop, 'flow_report.json')
flow = {
  'case_id' => case_id,
  'software_chain' => %w[revit archicad openstudio energyplus],
  'openstudio_version' => OpenStudio.openStudioLongVersion,
  'energyplus_version' => energyplus_version,
  'forward_translator_errors' => translator_errors,
  'forward_translator_warnings' => translator_warnings,
  'consumed_handoff_sha256' => handoff_hash,
  'stage2_sha256' => stage2_hash,
  'osm_sha256' => sha256.call(osm_path),
  'idf_sha256' => sha256.call(idf_path),
  'energy_report_sha256' => sha256.call(energy_path),
  'eplusout_sql_sha256' => sha256.call(sql_path),
  'eplusout_err_sha256' => sha256.call(err_path),
  'workflow_sha256' => sha256.call(workflow_path),
  'spaces' => spaces.map { |space| space.fetch('name') },
  'thermal_zones' => spaces.map { |space| space.fetch('thermal_zone') },
  'weather_file' => handoff.fetch('weather_file'),
  'schedule_set' => handoff.fetch('schedule_set'),
  'construction_set' => handoff.fetch('construction_set'),
  'simulation' => { 'status' => 'EnergyPlus Completed Successfully', 'total_site_energy_kwh' => total_site_kwh.round(3), 'peak_load_kw' => peak_kw.round(3) }
}
File.write(flow_path, JSON.pretty_generate(flow) + "\n")

native_log_path = File.join(desktop, 'native_stage_log.json')
native_log = JSON.parse(File.read(native_log_path, encoding: 'UTF-8'))
native_log.fetch('stages').reject! { |stage| stage['stage'] == 'openstudio' }
native_log.fetch('stages') << {
  'stage' => 'openstudio',
  'executable' => spec.fetch('fixed_software').fetch('openstudio').fetch('executable'),
  'invoked_executable' => options[:openstudio_exe],
  'product_version' => OpenStudio.openStudioLongVersion,
  'automation_entry' => File.expand_path(__FILE__),
  'command' => 'openstudio.exe openstudio_ifc_to_energy.rb --spec workflow_spec.json --handoff archicad_handoff.json --ifc stage2.ifc --weather weather.epw',
  'started_utc' => started_utc,
  'finished_utc' => finished_utc,
  'exit_code' => 0,
  'input_file' => 'stage2.ifc',
  'input_sha256' => stage2_hash,
  'input_handoff_sha256' => handoff_hash,
  'output_file' => 'result.osm',
  'output_sha256' => sha256.call(osm_path),
  'idf_sha256' => sha256.call(idf_path),
  'workflow_sha256' => sha256.call(workflow_path),
  'energyplus_executable' => energyplus_exe,
  'energyplus_version' => energyplus_version,
  'eplusout_sql_sha256' => sha256.call(sql_path),
  'eplusout_err_sha256' => sha256.call(err_path)
}
File.write(native_log_path, JSON.pretty_generate(native_log) + "\n")
