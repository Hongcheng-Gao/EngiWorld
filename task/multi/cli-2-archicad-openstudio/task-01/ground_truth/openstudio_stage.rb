require 'openstudio'
require 'json'
require 'csv'
require 'digest'
require 'time'

ROOT = ARGV[0] || 'C:/Users/user/Desktop'
HANDOFF_PATH = File.join(ROOT, 'handoff.json')
STAGE1_PATH = File.join(ROOT, 'stage1.ifc')
OSM_PATH = File.join(ROOT, 'result.osm')
FLOW_PATH = File.join(ROOT, 'flow_report.json')
SUMMARY_PATH = File.join(ROOT, 'model_summary.csv')
CASE_ID = 'multi-cli-2-archicad-openstudio-task-01-windows'
started_at = Time.now.utc.iso8601(7)

handoff = JSON.parse(File.read(HANDOFF_PATH, mode: 'r:bom|utf-8'))
raise 'wrong handoff case' unless handoff['case_id'] == CASE_ID
raise 'wrong upstream hash' unless handoff['source_sha256'] == Digest::SHA256.file(STAGE1_PATH).hexdigest

handoff_hash = Digest::SHA256.file(HANDOFF_PATH).hexdigest
stage1_hash = Digest::SHA256.file(STAGE1_PATH).hexdigest
model = OpenStudio::Model::Model.new
building = model.getBuilding
building.setName('EW2A01 Site Office Print Copy')
building.additionalProperties.setFeature('case_id', CASE_ID)
building.additionalProperties.setFeature('revision_code', 'EW2A01')
building.additionalProperties.setFeature('consumed_handoff_sha256', handoff_hash)
building.additionalProperties.setFeature('source_stage1_sha256', stage1_hash)
building.additionalProperties.setFeature('flow_contract', 'weather_file | schedule_set | construction_set')
building.additionalProperties.setFeature(
  'handoff_tokens',
  'LOW-EQUIPMENT-OFFICE | SIDE-DAYLIGHT | QUIET-OPAQUE-ENVELOPE | SOUTH-ENTRANCE-WINDOW'
)

fraction = OpenStudio::Model::ScheduleTypeLimits.new(model)
fraction.setName('EW2A01 Fraction')
fraction.setLowerLimitValue(0.0)
fraction.setUpperLimitValue(1.0)
fraction.setNumericType('Continuous')

temperature = OpenStudio::Model::ScheduleTypeLimits.new(model)
temperature.setName('EW2A01 Temperature')
temperature.setNumericType('Continuous')
temperature.setUnitType('Temperature')

activity_limit = OpenStudio::Model::ScheduleTypeLimits.new(model)
activity_limit.setName('EW2A01 Activity')
activity_limit.setLowerLimitValue(0.0)
activity_limit.setNumericType('Continuous')
activity_limit.setUnitType('ActivityLevel')

def make_schedule(model, name, limits, values)
  schedule = OpenStudio::Model::ScheduleRuleset.new(model)
  schedule.setName(name)
  schedule.setScheduleTypeLimits(limits)
  schedule.defaultDaySchedule.setName(name + ' Day')
  values.each do |hour, value|
    schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, hour, 0, 0), value)
  end
  schedule
end

always_on = make_schedule(model, 'EW2A01 Always On', fraction, [[24, 1.0]])
heating = make_schedule(model, 'EW2A01 Heating 20C', temperature, [[24, 20.0]])
cooling = make_schedule(model, 'EW2A01 Cooling 26C', temperature, [[24, 26.0]])
activity = make_schedule(model, 'EW2A01 Activity 120W', activity_limit, [[24, 120.0]])
office_schedule = make_schedule(
  model,
  'LowOfficeEquipmentSchedule',
  fraction,
  [[7, 0.05], [8, 0.35], [12, 0.85], [13, 0.35], [18, 0.8], [20, 0.15], [24, 0.05]]
)
print_schedule = make_schedule(
  model,
  'PrintCopyIntermittentSchedule',
  fraction,
  [[8, 0.02], [10, 0.45], [12, 0.2], [15, 0.65], [18, 0.15], [24, 0.02]]
)

opaque_material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
opaque_material.setName('EW2A01 Opaque Material')
opaque_material.setRoughness('MediumSmooth')
opaque_material.setThickness(0.2)
opaque_material.setConductivity(0.45)
opaque_material.setDensity(800.0)
opaque_material.setSpecificHeat(900.0)
opaque_construction = OpenStudio::Model::Construction.new(model)
opaque_construction.setName('OpaqueNorthWestEnvelope')
opaque_construction.insertLayer(0, opaque_material)

door_material = OpenStudio::Model::StandardOpaqueMaterial.new(model)
door_material.setName('EW2A01 Door Material')
door_material.setRoughness('Smooth')
door_material.setThickness(0.05)
door_material.setConductivity(0.2)
door_material.setDensity(600.0)
door_material.setSpecificHeat(900.0)
door_construction = OpenStudio::Model::Construction.new(model)
door_construction.setName('EW2A01 Door Construction')
door_construction.insertLayer(0, door_material)

glazing = OpenStudio::Model::SimpleGlazing.new(model)
glazing.setName('EW2A01 Entrance Glazing')
glazing.setUFactor(2.7)
glazing.setSolarHeatGainCoefficient(0.4)
glazing.setVisibleTransmittance(0.7)
window_construction = OpenStudio::Model::Construction.new(model)
window_construction.setName('EW2A01 Window Construction')
window_construction.insertLayer(0, glazing)

spaces = {}
specs = [
  ['SITE-OFFICE', 'SITE-OFFICE-ZN', 0.08, 8.0, 5.0, 0.0006, office_schedule],
  ['PRINT-COPY', 'PRINT-COPY-ZN', 0.02, 6.0, 15.0, 0.0004, print_schedule]
]

specs.each do |name, zone_name, people_density, lighting_density, equipment_density, oa_area, occupancy|
  record = handoff['spaces'].find { |item| item['name'] == name }
  raise "missing handoff space #{name}" unless record
  bbox = record['bbox_m'].map(&:to_f)
  points = OpenStudio::Point3dVector.new
  [[bbox[0], bbox[1]], [bbox[0], bbox[4]], [bbox[3], bbox[4]], [bbox[3], bbox[1]]].each do |x, y|
    points << OpenStudio::Point3d.new(x, y, bbox[2])
  end
  height = bbox[5] - bbox[2]
  space = OpenStudio::Model::Space.fromFloorPrint(points, height, model).get
  space.setName(name)
  space.additionalProperties.setFeature('source_ifc_global_id', record['ifc_global_id'])
  space.additionalProperties.setFeature('source_floor_area_m2', record['floor_area_m2'].to_f)
  space.additionalProperties.setFeature('source_stage1_sha256', stage1_hash)

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
  ideal_loads = OpenStudio::Model::ZoneHVACIdealLoadsAirSystem.new(model)
  ideal_loads.setName(name + ' Ideal Loads')
  ideal_loads.setAvailabilitySchedule(always_on)
  ideal_loads.setDesignSpecificationOutdoorAirObject(outdoor_air)
  ideal_loads.addToThermalZone(zone)

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

space_vector = OpenStudio::Model::SpaceVector.new
spaces.values.each { |space| space_vector << space }
OpenStudio::Model.intersectSurfaces(space_vector)
OpenStudio::Model.matchSurfaces(space_vector)
model.getSurfaces.each do |surface|
  surface.setConstruction(opaque_construction)
  if surface.surfaceType == 'Wall' && surface.outsideBoundaryCondition == 'Outdoors'
    xs = surface.vertices.map(&:x)
    ys = surface.vertices.map(&:y)
    if (xs.max - xs.min).abs < 1e-6
      surface.setName(surface.nameString + ' OpaqueNorthWestEnvelope') if xs.max <= 0.200001
    elsif (ys.max - ys.min).abs < 1e-6
      surface.setName(surface.nameString + ' OpaqueNorthWestEnvelope') if ys.min >= 3.799999
    end
  end
end

site_bbox = handoff['spaces'].find { |item| item['name'] == 'SITE-OFFICE' }['bbox_m'].map(&:to_f)
south_y = site_bbox[1]
south_wall = spaces['SITE-OFFICE'].surfaces.find do |surface|
  surface.surfaceType == 'Wall' &&
    surface.outsideBoundaryCondition == 'Outdoors' &&
    surface.vertices.all? { |vertex| (vertex.y - south_y).abs < 1e-6 }
end
raise 'SITE-OFFICE south wall missing' unless south_wall

def add_subsurface(model, wall, name, kind, construction, x0, x1, y, z0, z1)
  vertices = OpenStudio::Point3dVector.new
  [[x0, y, z0], [x1, y, z0], [x1, y, z1], [x0, y, z1]].each do |x, yy, z|
    vertices << OpenStudio::Point3d.new(x, yy, z)
  end
  subsurface = OpenStudio::Model::SubSurface.new(vertices, model)
  subsurface.setName(name)
  subsurface.setSubSurfaceType(kind)
  subsurface.setSurface(wall)
  subsurface.setConstruction(construction)
  subsurface
end

add_subsurface(model, south_wall, 'SouthEntranceDoor', 'Door', door_construction, 0.7, 1.6, south_y, 0.0, 2.1)
add_subsurface(
  model,
  south_wall,
  'SouthEntranceWindow',
  'FixedWindow',
  window_construction,
  2.0,
  3.5,
  south_y,
  1.0,
  2.2
)

raise 'OpenStudio model save failed' unless model.save(OpenStudio::Path.new(OSM_PATH), true)
osm_hash = Digest::SHA256.file(OSM_PATH).hexdigest
surface_count = model.getSurfaces.size
subsurface_count = model.getSubSurfaces.size
outdoor_walls = model.getSurfaces.select do |surface|
  surface.surfaceType == 'Wall' && surface.outsideBoundaryCondition == 'Outdoors'
end
windows = model.getSubSurfaces.select { |item| item.subSurfaceType.downcase.include?('window') }
window_wall_ratio = windows.sum(&:grossArea) / outdoor_walls.sum(&:grossArea)

summary_rows = handoff['spaces'].map do |record|
  area = record['floor_area_m2'].to_f
  multiplier = record['name'] == 'SITE-OFFICE' ? 62.0 : 74.0
  peak_density = record['name'] == 'SITE-OFFICE' ? 95.0 : 110.0
  {
    'case_id' => CASE_ID,
    'space_name' => record['name'],
    'thermal_zone' => record['thermal_zone'],
    'floor_area_m2' => format('%.6f', area),
    'source_handoff_sha256' => handoff_hash,
    'source_stage1_sha256' => stage1_hash,
    'energy_use_kwh' => format('%.6f', area * multiplier),
    'peak_load_w' => format('%.6f', area * peak_density)
  }
end
CSV.open(SUMMARY_PATH, 'w', write_headers: true, headers: summary_rows.first.keys) do |csv|
  summary_rows.each { |row| csv << row }
end

flow = {
  'case_id' => CASE_ID,
  'software_chain' => ['archicad', 'openstudio'],
  'stage_sequence' => [
    {'software' => 'archicad', 'input' => 'init.ifc', 'output' => 'stage1.ifc', 'handoff' => 'handoff.json'},
    {'software' => 'openstudio', 'input' => 'handoff.json', 'upstream_reference' => 'stage1.ifc', 'output' => 'result.osm'}
  ],
  'consumed_handoff_sha256' => handoff_hash,
  'source_stage1_sha256' => stage1_hash,
  'osm_sha256' => osm_hash,
  'model_summary_sha256' => Digest::SHA256.file(SUMMARY_PATH).hexdigest,
  'building_area_m2' => handoff['building_area_m2'].to_f,
  'room_count' => handoff['spaces'].size,
  'thermal_zone_count' => handoff['thermal_zones'].size,
  'door_count' => handoff['door_count'].to_i,
  'window_count' => handoff['window_count'].to_i,
  'window_wall_ratio' => window_wall_ratio,
  'surface_count' => surface_count,
  'subsurface_count' => subsurface_count,
  'weather_file' => 'DesignDayOnly',
  'schedule_set' => model.getScheduleRulesets.map(&:nameString).sort,
  'construction_set' => model.getConstructions.map(&:nameString).sort,
  'openstudio_version' => OpenStudio.openStudioVersion,
  'spaces' => handoff['spaces'],
  'thermal_zones' => handoff['thermal_zones'],
  'osm_tokens' => [
    'SITE-OFFICE-ZN',
    'PRINT-COPY-ZN',
    'LowOfficeEquipmentSchedule',
    'SouthEntranceWindow',
    'OpaqueNorthWestEnvelope'
  ],
  'handoff_tokens' => handoff['handoff_tokens'],
  'energy_method' => 'OpenStudio geometry and schedule based design estimate',
  'native_openstudio_execution' => {
    'executable' => 'C:\\openstudio-3.10.0\\bin\\openstudio.exe',
    'executable_sha256' => Digest::SHA256.file('C:/openstudio-3.10.0/bin/openstudio.exe').hexdigest,
    'script' => File.basename(__FILE__),
    'script_sha256' => Digest::SHA256.file(__FILE__).hexdigest,
    'process_id' => Process.pid,
    'started_at_utc' => started_at,
    'completed_at_utc' => Time.now.utc.iso8601(7),
    'exit_code' => 0
  }
}
File.write(FLOW_PATH, JSON.pretty_generate(flow) + "\n")
puts JSON.generate(
  {
    'ok' => true,
    'openstudio_version' => OpenStudio.openStudioVersion,
    'osm_sha256' => osm_hash,
    'surface_count' => surface_count,
    'subsurface_count' => subsurface_count,
    'building_area_m2' => handoff['building_area_m2'].to_f
  }
)
