require 'openstudio'
require 'json'
require 'digest'
require 'time'
require 'fileutils'

root = 'C:/Users/user/Desktop'
handoff = JSON.parse(File.read(root + '/handoff.json', mode: 'r:bom|utf-8'))
model = OpenStudio::Model::Model.new
building = model.getBuilding
building.setName('EW2A10 Clinic Isolation Flow')
building.additionalProperties.setFeature('case_id', handoff['case_id'])
building.additionalProperties.setFeature('revision_code', 'EW2A10')
building.additionalProperties.setFeature('consumed_handoff_sha256', Digest::SHA256.file(root + '/handoff.json').hexdigest)

def schedule(model, name, values)
  result = OpenStudio::Model::ScheduleRuleset.new(model)
  result.setName(name)
  result.defaultDaySchedule.setName(name + ' Default Day')
  values.each { |hour, value| result.defaultDaySchedule.addValue(OpenStudio::Time.new(0, hour, 0, 0), value) }
  result
end

always = schedule(model, 'EW2A10 Always On', [[24, 1.0]])
heating = schedule(model, 'EW2A10 Heating 20C', [[24, 20.0]])
cooling = schedule(model, 'EW2A10 Cooling 24C', [[24, 24.0]])
activity = schedule(model, 'EW2A10 Activity 120W', [[24, 120.0]])
consult_schedule = schedule(model, 'ConsultSchedule', [[7, 0.05], [9, 0.35], [17, 0.75], [20, 0.2], [24, 0.05]])
equipment_schedule = schedule(model, 'EquipmentSchedule', [[7, 0.1], [9, 0.5], [18, 0.9], [22, 0.2], [24, 0.1]])
isolation_schedule = schedule(model, 'IsolationConsultSchedule', [[7, 0.05], [9, 0.25], [17, 0.55], [20, 0.15], [24, 0.05]])
ppe_schedule = schedule(model, 'PPESupportSchedule', [[7, 0.02], [9, 0.15], [18, 0.35], [22, 0.05], [24, 0.02]])
contaminated_schedule = schedule(model, 'ContaminatedSupportLowOccupancy', [[7, 0.01], [9, 0.08], [18, 0.18], [22, 0.03], [24, 0.01]])

material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
material.setName('EW2A10 Opaque Material')
material.setRoughness('Smooth')
material.setThickness(0.2)
material.setConductivity(0.5)
material.setDensity(800)
material.setSpecificHeat(900)
construction = OpenStudio::Model::Construction.new(model)
construction.setName('EW2A10 Opaque Construction')
construction.insertLayer(0, material)

specs = [
  ['CONSULT', 'CONSULT-ZN', 0.0, 3.5, 14.0, 0.10, 10.0, 8.0, 0.0008, consult_schedule],
  ['EQUIPMENT', 'EQUIPMENT-ZN', 3.5, 7.5, 16.0, 0.025, 9.0, 24.0, 0.0006, equipment_schedule],
  ['ISO-CONSULT', 'ISO-CONSULT-ZN', 7.5, 11.0, 14.0, 0.07, 10.0, 10.0, 0.0015, isolation_schedule],
  ['PPE-DONNING', 'PPE-DONNING-ZN', 11.0, 13.0, 8.0, 0.025, 8.0, 5.0, 0.0010, ppe_schedule],
  ['CONTAMINATED-SUPPORT', 'CONTAMINATED-SUPPORT-ZN', 13.0, 15.0, 8.0, 0.0125, 8.0, 7.0, 0.0012, contaminated_schedule]
]
spaces = {}
specs.each do |name, zone_name, x0, x1, area, people_density, lighting_density, equipment_density, oa_area, occupancy|
  points = OpenStudio::Point3dVector.new
  [[x0, 0], [x0, 4], [x1, 4], [x1, 0]].each { |x, y| points << OpenStudio::Point3d.new(x, y, 0) }
  space = OpenStudio::Model::Space.fromFloorPrint(points, 3.0, model).get
  space.setName(name)
  record = handoff['spaces'].find { |item| item['name'] == name }
  space.additionalProperties.setFeature('source_floor_area_m2', area)
  space.additionalProperties.setFeature('source_ifc_binding', JSON.generate(record))
  space.additionalProperties.setFeature('use_assumption', record['equipment_assumption']) if record['equipment_assumption']
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
variables = [
  'Zone Lights Electricity Energy',
  'Zone Electric Equipment Electricity Energy',
  'Zone Ideal Loads Zone Total Heating Energy',
  'Zone Ideal Loads Zone Total Cooling Energy',
  'Zone Ideal Loads Zone Total Heating Rate',
  'Zone Ideal Loads Zone Total Cooling Rate'
]
variables.each do |name|
  output = OpenStudio::Model::OutputVariable.new(name, model)
  output.setReportingFrequency('Hourly')
end
raise 'OSM save failed' unless model.save(root + '/result.osm', true)
translator = OpenStudio::EnergyPlus::ForwardTranslator.new
workspace = translator.translateModel(model)
raise 'IDF save failed' unless workspace.save(root + '/in.idf', true)
File.write(root + '/workflow.osw', JSON.pretty_generate({'seed_file'=>'result.osm','weather_file'=>'weather.epw','run_directory'=>'run','steps'=>[]}) + "\n")
flow = {
  'schema'=>'engiworld.openstudio-flow.v1', 'case_id'=>handoff['case_id'], 'revision'=>'EW2A10',
  'software_chain'=>['archicad','openstudio','energyplus'], 'consumed_handoff_sha256'=>Digest::SHA256.file(root+'/handoff.json').hexdigest,
  'source_stage1_sha256'=>handoff['source_sha256'], 'native_stage_log_sha256'=>Digest::SHA256.file(root+'/native_stage_log.json').hexdigest,
  'osm_sha256'=>Digest::SHA256.file(root+'/result.osm').hexdigest, 'workflow_sha256'=>Digest::SHA256.file(root+'/workflow.osw').hexdigest,
  'idf_sha256'=>Digest::SHA256.file(root+'/in.idf').hexdigest,
  'weather_file'=>'weather.epw', 'weather_sha256'=>Digest::SHA256.file(root+'/weather.epw').hexdigest,
  'building_area_m2'=>60.0, 'room_count'=>5, 'thermal_zone_count'=>5, 'door_count'=>0, 'window_count'=>0, 'window_wall_ratio'=>0.0,
  'surface_count'=>model.getSurfaces.size, 'subsurface_count'=>model.getSubSurfaces.size,
  'schedule_set'=>model.getSchedules.map(&:nameString).sort, 'construction_set'=>model.getConstructions.map(&:nameString).sort,
  'openstudio_version'=>OpenStudio.openStudioVersion, 'spaces'=>handoff['spaces'], 'thermal_zones'=>handoff['thermal_zones'],
  'load_assumptions'=>specs.map{|x|{'space_name'=>x[0],'people_per_m2'=>x[5],'lighting_w_per_m2'=>x[6],'equipment_w_per_m2'=>x[7],'schedule'=>x[9].nameString}}
}
File.write(root + '/flow_report.json', JSON.pretty_generate(flow) + "\n")
puts JSON.generate({'ok'=>true,'openstudio_version'=>OpenStudio.openStudioVersion,'spaces'=>model.getSpaces.size,'zones'=>model.getThermalZones.size,'surfaces'=>model.getSurfaces.size})
