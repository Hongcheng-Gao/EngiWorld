require 'json'
require 'openstudio'

def point(x, y, z)
  OpenStudio::Point3d.new(x, y, z)
end

def polygon(points)
  poly = OpenStudio::Point3dVector.new
  points.each { |p| poly << point(*p) }
  poly
end

def add_surface(model, name, type, space, obc, points)
  surface = OpenStudio::Model::Surface.new(polygon(points), model)
  surface.setName(name)
  surface.setSurfaceType(type)
  surface.setSpace(space)
  surface.setOutsideBoundaryCondition(obc)
  surface
end

def add_window(model, surface, name, width, height, sill, x0)
  bb = surface.vertices
  xs = bb.map(&:x)
  ys = bb.map(&:y)
  zs = bb.map(&:z)
  minx, maxx = xs.min, xs.max
  miny, maxy = ys.min, ys.max
  z0 = zs.min + sill
  z1 = z0 + height
  if (maxx - minx).abs >= (maxy - miny).abs
    y = miny
    x1 = [minx + x0 + width, maxx - 0.2].min
    x0_abs = x1 - width
    pts = [[x0_abs, y, z0], [x1, y, z0], [x1, y, z1], [x0_abs, y, z1]]
  else
    x = minx
    y1 = [miny + x0 + width, maxy - 0.2].min
    y0_abs = y1 - width
    pts = [[x, y0_abs, z0], [x, y1, z0], [x, y1, z1], [x, y0_abs, z1]]
  end
  sub = OpenStudio::Model::SubSurface.new(polygon(pts), model)
  sub.setName(name)
  sub.setSubSurfaceType('FixedWindow')
  sub.setSurface(surface)
  sub
end

def add_loads(model, space, name, people: false, lights: false, equipment: false)
  schedule = OpenStudio::Model::ScheduleRuleset.new(model)
  schedule.setName("#{name} Occupied Schedule")
  schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 8, 0, 0), 0.0)
  schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 18, 0, 0), 1.0)
  schedule.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 0.0)

  if people
    definition = OpenStudio::Model::PeopleDefinition.new(model)
    definition.setName("#{name} People Definition")
    definition.setPeopleperSpaceFloorArea(0.05)
    load = OpenStudio::Model::People.new(definition)
    load.setName("#{name} People")
    load.setSpace(space)
    load.setNumberofPeopleSchedule(schedule)
  end

  if lights
    definition = OpenStudio::Model::LightsDefinition.new(model)
    definition.setName("#{name} Lights Definition")
    definition.setWattsperSpaceFloorArea(8.0)
    load = OpenStudio::Model::Lights.new(definition)
    load.setName("#{name} Lights")
    load.setSpace(space)
    load.setSchedule(schedule)
  end

  if equipment
    definition = OpenStudio::Model::ElectricEquipmentDefinition.new(model)
    definition.setName("#{name} Equipment Definition")
    definition.setWattsperSpaceFloorArea(6.0)
    load = OpenStudio::Model::ElectricEquipment.new(definition)
    load.setName("#{name} Equipment")
    load.setSpace(space)
    load.setSchedule(schedule)
  end
end

def add_thermostat(model, zone, name)
  heat = OpenStudio::Model::ScheduleRuleset.new(model)
  heat.setName("#{name} Heating Setpoint")
  heat.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 21.0)
  cool = OpenStudio::Model::ScheduleRuleset.new(model)
  cool.setName("#{name} Cooling Setpoint")
  cool.defaultDaySchedule.addValue(OpenStudio::Time.new(0, 24, 0, 0), 24.0)
  thermostat = OpenStudio::Model::ThermostatSetpointDualSetpoint.new(model)
  thermostat.setName("#{name} Thermostat")
  thermostat.setHeatingSetpointTemperatureSchedule(heat)
  thermostat.setCoolingSetpointTemperatureSchedule(cool)
  zone.setThermostatSetpointDualSetpoint(thermostat)
  thermostat
end

def add_ideal_loads(model, zone, name)
  system = OpenStudio::Model::ZoneHVACIdealLoadsAirSystem.new(model)
  system.setName("#{name} Ideal Loads")
  system.addToThermalZone(zone)
  system
end

def add_zone(model, space, name, story, thermostat: false, ideal_loads: false)
  zone = OpenStudio::Model::ThermalZone.new(model)
  zone.setName("#{name} Zone")
  space.setThermalZone(zone)
  space.setBuildingStory(story)
  add_thermostat(model, zone, name) if thermostat
  add_ideal_loads(model, zone, name) if ideal_loads
  zone
end

def build_rectangular_model(spec)
  model = OpenStudio::Model::Model.new
  story = OpenStudio::Model::BuildingStory.new(model)
  story.setName(spec.fetch('story_name', 'Ground Story'))
  height = spec.fetch('height', 3.2)
  spaces = {}
  wall_surfaces = []
  space_type = nil
  if spec.fetch('space_types', 0).to_i > 0
    space_type = OpenStudio::Model::SpaceType.new(model)
    space_type.setName('OfficeType')
  end

  spec.fetch('spaces').each do |s|
    x0 = s.fetch('x0')
    y0 = s.fetch('y0')
    x1 = s.fetch('x1')
    y1 = s.fetch('y1')
    name = s.fetch('name')
    space = OpenStudio::Model::Space.new(model)
    space.setName(name)
    space.setSpaceType(space_type) if space_type
    spaces[name] = space

    add_surface(model, "#{name} Floor", 'Floor', space, 'Ground',
      [[x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]])
    add_surface(model, "#{name} Roof", 'RoofCeiling', space, 'Outdoors',
      [[x0, y1, height], [x1, y1, height], [x1, y0, height], [x0, y0, height]])
    walls = [
      ['South', [[x0, y0, 0], [x1, y0, 0], [x1, y0, height], [x0, y0, height]]],
      ['East', [[x1, y0, 0], [x1, y1, 0], [x1, y1, height], [x1, y0, height]]],
      ['North', [[x1, y1, 0], [x0, y1, 0], [x0, y1, height], [x1, y1, height]]],
      ['West', [[x0, y1, 0], [x0, y0, 0], [x0, y0, height], [x0, y1, height]]],
    ]
    walls.each do |dir, pts|
      wall_surfaces << add_surface(model, "#{name} #{dir} Wall", 'Wall', space, 'Outdoors', pts)
    end
    unless spec['no_space_links']
      add_zone(model, space, name, story, thermostat: s['thermostat'], ideal_loads: s['ideal_loads'])
    end
    add_loads(model, space, name, people: s['people'], lights: s['lights'], equipment: s['equipment'])
  end

  unless spec['skip_surface_matching']
    space_vector = OpenStudio::Model::SpaceVector.new
    model.getSpaces.each { |space| space_vector << space }
    OpenStudio::Model.intersectSurfaces(space_vector)
    OpenStudio::Model.matchSurfaces(space_vector)
  end

  spec.fetch('windows', []).each_with_index do |w, index|
    wall = wall_surfaces.find { |s| s.nameString == w.fetch('surface') }
    raise "missing window parent surface #{w.fetch('surface')}" unless wall
    add_window(model, wall, w.fetch('name', "Window #{index + 1}"), w.fetch('width'), w.fetch('height'), w.fetch('sill', 1.0), w.fetch('offset', 0.8))
  end

  if spec['shading']
    group = OpenStudio::Model::ShadingSurfaceGroup.new(model)
    group.setName('Simple Exterior Shading')
    spec['shading'].each_with_index do |sh, index|
      surf = OpenStudio::Model::ShadingSurface.new(polygon(sh.fetch('points')), model)
      surf.setName(sh.fetch('name', "Overhang #{index + 1}"))
      surf.setShadingSurfaceGroup(group)
    end
  end

  model
end

spec = JSON.parse(File.read(ARGV.fetch(0)))
output = ARGV.fetch(1)
model = build_rectangular_model(spec)
model.save(output, true)
