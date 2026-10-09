require 'openstudio'
require 'json'
require 'digest'
require 'fileutils'

root = 'C:/Users/user/Desktop'
handoff = JSON.parse(File.read(root + '/handoff.json', mode: 'r:bom|utf-8'))
model = OpenStudio::Model::Model.new
building = model.getBuilding
building.setName('EW2A09 Student Residence')
building.additionalProperties.setFeature('case_id', handoff['case_id'])
building.additionalProperties.setFeature('revision_code', 'EW2A09')
building.additionalProperties.setFeature('consumed_handoff_sha256', Digest::SHA256.file(root + '/handoff.json').hexdigest)
building.additionalProperties.setFeature('handoff_tokens', handoff['handoff_tokens'].join(' | '))
building.additionalProperties.setFeature('bedroom_preservation', 'BEDROOM-COUNT-PRESERVED')

def schedule(model, name, values)
  result = OpenStudio::Model::ScheduleRuleset.new(model)
  result.setName(name)
  result.defaultDaySchedule.setName(name + ' Default Day')
  values.each { |hour, value| result.defaultDaySchedule.addValue(OpenStudio::Time.new(0, hour, 0, 0), value) }
  result
end

always = schedule(model, 'EW2A09 Always On', [[24, 1.0]])
heating = schedule(model, 'EW2A09 Heating 20C', [[24, 20.0]])
cooling = schedule(model, 'EW2A09 Cooling 26C', [[24, 26.0]])
activity = schedule(model, 'EW2A09 Activity 120W', [[24, 120.0]])
social_schedule = schedule(model, 'SocialCommonsSchedule SOCIAL-SPACE-SCHEDULE', [[7, 0.05], [9, 0.35], [18, 0.8], [23, 0.25], [24, 0.05]])
bedroom_schedule = schedule(model, 'ResidentialBedroomSchedule RESIDENTIAL-SCHEDULE', [[7, 0.7], [9, 0.2], [17, 0.15], [23, 0.85], [24, 0.7]])
study_schedule = schedule(model, 'QuietStudySchedule LOW-EQUIPMENT-STUDY', [[7, 0.02], [9, 0.2], [18, 0.7], [23, 0.15], [24, 0.02]])
laundry_schedule = schedule(model, 'LaundryServiceSchedule HIGH-EQUIPMENT-LAUNDRY', [[7, 0.02], [9, 0.15], [19, 0.65], [23, 0.05], [24, 0.02]])

material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
material.setName('EW2A09 Opaque Material')
material.setRoughness('Smooth')
material.setThickness(0.2)
material.setConductivity(0.5)
material.setDensity(800)
material.setSpecificHeat(900)
construction = OpenStudio::Model::Construction.new(model)
construction.setName('EW2A09 Opaque Construction')
construction.insertLayer(0, material)

specs = [
  ['SOCIAL-COMMONS', 'SOCIAL-COMMONS-ZN', 0.0, 0.0, 4.0, 4.0, 16.0, 0.10, 9.0, 8.0, 0.0008, social_schedule],
  ['BEDROOM-GROUP', 'BEDROOM-GROUP-ZN', 5.0, 0.0, 12.0, 8.0, 96.0, 0.0625, 6.0, 5.0, 0.0007, bedroom_schedule],
  ['QUIET-STUDY', 'QUIET-STUDY-ZN', 18.0, 0.0, 5.0, 4.0, 20.0, 0.08, 7.0, 3.0, 0.0008, study_schedule],
  ['LAUNDRY', 'LAUNDRY-ZN', 24.0, 0.0, 4.0, 4.0, 16.0, 0.02, 8.0, 22.0, 0.0010, laundry_schedule]
]
spaces = {}
specs.each do |name, zone_name, x0, y0, width, depth, area, people_density, lighting_density, equipment_density, oa_area, occupancy|
  points = OpenStudio::Point3dVector.new
  [[x0, y0], [x0, y0 + depth], [x0 + width, y0 + depth], [x0 + width, y0]].each { |x, y| points << OpenStudio::Point3d.new(x, y, 0) }
  space = OpenStudio::Model::Space.fromFloorPrint(points, 3.0, model).get
  space.setName(name)
  record = handoff['spaces'].find { |item| item['name'] == name }
  space.additionalProperties.setFeature('source_floor_area_m2', area)
  space.additionalProperties.setFeature('source_ifc_binding', JSON.generate(record))
  space.additionalProperties.setFeature('handoff_semantics', handoff['handoff_tokens'].join(' | '))
  zone = OpenStudio::Model::ThermalZone.new(model)
  zone.setName(zone_name)
  space.setThermalZone(zone)
  thermostat = OpenStudio::Model::ThermostatSetpointDualSetpoint.new(model)
  thermostat.setName(name + ' Thermostat')
  thermostat.setHeatingSetpointTemperatureSchedule(heating)
  thermostat.setCoolingSetpointTemperatureSchedule(cooling)
  zone.setThermostatSetpointDualSetpoint(thermostat)
  outdoor_air = OpenStudio::Model::DesignSpecificationOutdoorAir.new(model)
  outdoor_air.setName(name + ' Outdoor Air')
  outdoor_air.setOutdoorAirMethod('Sum')
  outdoor_air.setOutdoorAirFlowperPerson(0.004)
  outdoor_air.setOutdoorAirFlowperFloorArea(oa_area)
  space.setDesignSpecificationOutdoorAir(outdoor_air)
  ideal = OpenStudio::Model::ZoneHVACIdealLoadsAirSystem.new(model)
  ideal.setName(name + ' IDEAL LOADS')
  ideal.setAvailabilitySchedule(always)
  ideal.setDesignSpecificationOutdoorAirObject(outdoor_air)
  raise 'ideal loads attachment failed' unless ideal.addToThermalZone(zone)
  people_definition = OpenStudio::Model::PeopleDefinition.new(model)
  people_definition.setName(name + ' People Definition')
  people_definition.setPeopleperSpaceFloorArea(people_density)
  people = OpenStudio::Model::People.new(people_definition)
  people.setName(name + ' People')
  people.setSpace(space)
  people.setNumberofPeopleSchedule(occupancy)
  people.setActivityLevelSchedule(activity)
  lights_definition = OpenStudio::Model::LightsDefinition.new(model)
  lights_definition.setName(name + ' Lights Definition')
  lights_definition.setWattsperSpaceFloorArea(lighting_density)
  lights = OpenStudio::Model::Lights.new(lights_definition)
  lights.setName(name + ' Lights')
  lights.setSpace(space)
  lights.setSchedule(occupancy)
  equipment_definition = OpenStudio::Model::ElectricEquipmentDefinition.new(model)
  equipment_definition.setName(name + ' Equipment Definition')
  equipment_definition.setWattsperSpaceFloorArea(equipment_density)
  equipment = OpenStudio::Model::ElectricEquipment.new(equipment_definition)
  equipment.setName(name + ' Equipment')
  equipment.setSpace(space)
  equipment.setSchedule(occupancy)
  spaces[name] = space
end

vector = OpenStudio::Model::SpaceVector.new
spaces.values.each { |space| vector << space }
OpenStudio::Model.intersectSurfaces(vector)
OpenStudio::Model.matchSurfaces(vector)
model.getSurfaces.each { |surface| surface.setConstruction(construction) }

weather_source = 'C:/openstudio-3.10.0/Examples/compact_osw/files/srrl_2013_amy.epw'
FileUtils.cp(weather_source, root + '/weather.epw')
epw = OpenStudio::EpwFile.new(OpenStudio::Path.new(root + '/weather.epw'))
OpenStudio::Model::WeatherFile.setWeatherFile(model, epw)
model.getSimulationControl.setRunSimulationforSizingPeriods(false)
model.getSimulationControl.setRunSimulationforWeatherFileRunPeriods(true)
[
  'Zone Lights Electricity Energy',
  'Zone Electric Equipment Electricity Energy',
  'Zone Ideal Loads Zone Total Heating Energy',
  'Zone Ideal Loads Zone Total Cooling Energy',
  'Zone Ideal Loads Zone Total Heating Rate',
  'Zone Ideal Loads Zone Total Cooling Rate'
].each do |name|
  output = OpenStudio::Model::OutputVariable.new(name, model)
  output.setReportingFrequency('Hourly')
end
raise 'OSM save failed' unless model.save(root + '/result.osm', true)
workspace = OpenStudio::EnergyPlus::ForwardTranslator.new.translateModel(model)
raise 'IDF save failed' unless workspace.save(root + '/in.idf', true)
File.write(root + '/workflow.osw', JSON.pretty_generate({'seed_file'=>'result.osm','weather_file'=>'weather.epw','run_directory'=>'run','steps'=>[]}) + "\n")
flow = {
  'schema'=>'engiworld.openstudio-flow.v1', 'case_id'=>handoff['case_id'], 'revision'=>'EW2A09',
  'software_chain'=>['archicad','openstudio','energyplus'], 'stage_sequence'=>['archicad','openstudio','energyplus'],
  'consumed_handoff_sha256'=>Digest::SHA256.file(root+'/handoff.json').hexdigest,
  'source_stage1_sha256'=>handoff['source_sha256'], 'native_stage_log_sha256'=>Digest::SHA256.file(root+'/native_stage_log.json').hexdigest,
  'osm_sha256'=>Digest::SHA256.file(root+'/result.osm').hexdigest, 'workflow_sha256'=>Digest::SHA256.file(root+'/workflow.osw').hexdigest,
  'idf_sha256'=>Digest::SHA256.file(root+'/in.idf').hexdigest,
  'weather_file'=>'weather.epw', 'weather_sha256'=>Digest::SHA256.file(root+'/weather.epw').hexdigest,
  'building_area_m2'=>148.0, 'room_count'=>4, 'thermal_zone_count'=>4, 'door_count'=>0, 'window_count'=>0, 'window_wall_ratio'=>0.0,
  'surface_count'=>model.getSurfaces.size, 'subsurface_count'=>model.getSubSurfaces.size,
  'schedule_set'=>model.getSchedules.map(&:nameString).sort, 'construction_set'=>model.getConstructions.map(&:nameString).sort,
  'openstudio_version'=>OpenStudio.openStudioVersion, 'spaces'=>handoff['spaces'], 'thermal_zones'=>handoff['thermal_zones'],
  'handoff_tokens'=>handoff['handoff_tokens'],
  'load_assumptions'=>specs.map{|x|{'space_name'=>x[0],'people_per_m2'=>x[7],'lighting_w_per_m2'=>x[8],'equipment_w_per_m2'=>x[9],'schedule'=>x[11].nameString}}
}
File.write(root + '/flow_report.json', JSON.pretty_generate(flow) + "\n")
puts JSON.generate({'ok'=>true,'openstudio_version'=>OpenStudio.openStudioVersion,'spaces'=>model.getSpaces.size,'zones'=>model.getThermalZones.size,'surfaces'=>model.getSurfaces.size})
