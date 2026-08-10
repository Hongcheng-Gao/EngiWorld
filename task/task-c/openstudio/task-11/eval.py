#!/usr/bin/env python3
import subprocess
import tempfile
from pathlib import Path

RESULT = Path('/home/user/Desktop/result.osm')
RUBY = r"""
require 'openstudio'
require 'json'

SPEC = JSON.parse(%q|{"title": "Two-Story Six-Zone Office Stack", "building": "CLI Stacked Office", "stories": [{"name": "01_OFFICE", "z": 0.0}, {"name": "02_OFFICE", "z": 3.2}], "spaces": [{"name": "T11-L1-WEST", "zone": "T11-L1-WEST Zone", "x0": 0, "y0": 0, "x1": 8, "y1": 10, "z0": 0, "h": 3.2, "story": "01_OFFICE", "space_type": "TASK11 Office Type", "heat": 20, "cool": 25, "ideal": true}, {"name": "T11-L1-CENTER", "zone": "T11-L1-CENTER Zone", "x0": 8, "y0": 0, "x1": 16, "y1": 10, "z0": 0, "h": 3.2, "story": "01_OFFICE", "space_type": "TASK11 Office Type", "heat": 20, "cool": 25, "ideal": true}, {"name": "T11-L1-EAST", "zone": "T11-L1-EAST Zone", "x0": 16, "y0": 0, "x1": 24, "y1": 10, "z0": 0, "h": 3.2, "story": "01_OFFICE", "space_type": "TASK11 Office Type", "heat": 20, "cool": 25, "ideal": true}, {"name": "T11-L2-WEST", "zone": "T11-L2-WEST Zone", "x0": 0, "y0": 0, "x1": 8, "y1": 10, "z0": 3.2, "h": 3.2, "story": "02_OFFICE", "space_type": "TASK11 Upper Office Type", "heat": 21, "cool": 24, "ideal": true}, {"name": "T11-L2-CENTER", "zone": "T11-L2-CENTER Zone", "x0": 8, "y0": 0, "x1": 16, "y1": 10, "z0": 3.2, "h": 3.2, "story": "02_OFFICE", "space_type": "TASK11 Upper Office Type", "heat": 21, "cool": 24, "ideal": true}, {"name": "T11-L2-EAST", "zone": "T11-L2-EAST Zone", "x0": 16, "y0": 0, "x1": 24, "y1": 10, "z0": 3.2, "h": 3.2, "story": "02_OFFICE", "space_type": "TASK11 Upper Office Type", "heat": 21, "cool": 24, "ideal": true}], "constant_schedules": {"TASK11 Occupancy Schedule": 0.8, "TASK11 Load Schedule": 0.9}, "space_types": {"TASK11 Office Type": {"people": 0.045, "people_schedule": "TASK11 Occupancy Schedule", "lights": 8.5, "lights_schedule": "TASK11 Load Schedule", "equipment": 10.0, "equipment_schedule": "TASK11 Load Schedule"}, "TASK11 Upper Office Type": {"people": 0.04, "people_schedule": "TASK11 Occupancy Schedule", "lights": 8.0, "lights_schedule": "TASK11 Load Schedule", "equipment": 9.0, "equipment_schedule": "TASK11 Load Schedule"}}, "windows": [{"space": "T11-L1-WEST", "wall": "south", "start": 1, "end": 7, "sill": 0.9, "head": 2.5, "name": "T11-L1-WEST South FixedWindow"}, {"space": "T11-L1-CENTER", "wall": "south", "start": 9, "end": 15, "sill": 0.9, "head": 2.5, "name": "T11-L1-CENTER South FixedWindow"}, {"space": "T11-L1-EAST", "wall": "south", "start": 17, "end": 23, "sill": 0.9, "head": 2.5, "name": "T11-L1-EAST South FixedWindow"}, {"space": "T11-L2-WEST", "wall": "south", "start": 1, "end": 7, "sill": 0.9, "head": 2.5, "name": "T11-L2-WEST South FixedWindow"}, {"space": "T11-L2-CENTER", "wall": "south", "start": 9, "end": 15, "sill": 0.9, "head": 2.5, "name": "T11-L2-CENTER South FixedWindow"}, {"space": "T11-L2-EAST", "wall": "south", "start": 17, "end": 23, "sill": 0.9, "head": 2.5, "name": "T11-L2-EAST South FixedWindow"}, {"space": "T11-L1-WEST", "wall": "north", "start": 2, "end": 6, "sill": 1.0, "head": 2.4, "name": "T11-L1-WEST North FixedWindow"}, {"space": "T11-L1-CENTER", "wall": "north", "start": 10, "end": 14, "sill": 1.0, "head": 2.4, "name": "T11-L1-CENTER North FixedWindow"}, {"space": "T11-L1-EAST", "wall": "north", "start": 18, "end": 22, "sill": 1.0, "head": 2.4, "name": "T11-L1-EAST North FixedWindow"}, {"space": "T11-L2-WEST", "wall": "north", "start": 2, "end": 6, "sill": 1.0, "head": 2.4, "name": "T11-L2-WEST North FixedWindow"}, {"space": "T11-L2-CENTER", "wall": "north", "start": 10, "end": 14, "sill": 1.0, "head": 2.4, "name": "T11-L2-CENTER North FixedWindow"}, {"space": "T11-L2-EAST", "wall": "north", "start": 18, "end": 22, "sill": 1.0, "head": 2.4, "name": "T11-L2-EAST North FixedWindow"}, {"space": "T11-L1-WEST", "wall": "west", "start": 2, "end": 8, "sill": 1.0, "head": 2.4, "name": "T11-L1-WEST West FixedWindow"}, {"space": "T11-L2-WEST", "wall": "west", "start": 2, "end": 8, "sill": 1.0, "head": 2.4, "name": "T11-L2-WEST West FixedWindow"}, {"space": "T11-L1-EAST", "wall": "east", "start": 2, "end": 8, "sill": 1.0, "head": 2.4, "name": "T11-L1-EAST East FixedWindow"}, {"space": "T11-L2-EAST", "wall": "east", "start": 2, "end": 8, "sill": 1.0, "head": 2.4, "name": "T11-L2-EAST East FixedWindow"}], "id": "11", "metrics": {"bbox": [24, 10, 6.4], "floor_area": 480, "exterior_wall_area": 435.2, "surface_count": 36, "space_count": 6, "zone_count": 6, "story_count": 2, "window_count": 16, "window_area": 124.8, "shading_count": 0, "shading_area": 0, "paired_surface_count": 14, "ground_floor_count": 3}, "difficulty": "medium", "scenario": "当前模型是一栋两层线性办公楼，三段开间在上下两层重复，内部隔墙和楼层叠合关系应保持清晰。业主希望将它标准化为可比较的办公基准模型：一层和二层可采用略有差异的办公负荷，南北立面继续保持有节奏的窗带，楼层之间的相邻关系和长条体量不得被破坏。"}|)
PATH = ARGV[0]
TOL = 0.06

def ok_close(a,b,t=0.06)
  (a.to_f-b.to_f).abs <= t
end

def opt(v)
  return nil if v.nil?
  return v.get if v.respond_to?(:empty?) && !v.empty?
  return nil if v.respond_to?(:empty?) && v.empty?
  v
end

def sched_name(obj)
  return nil if obj.nil?
  s = opt(obj)
  s ? s.nameString : nil
end

def constant_value(model, name)
  s = model.getScheduleConstants.find { |x| x.nameString == name }
  s ? s.value : nil
end

def schedule_by_name(model, name)
  (model.getScheduleConstants + model.getScheduleRulesets).find { |x| x.nameString == name }
end

def points_key(surface)
  surface.vertices.map { |p| [p.x.round(4), p.y.round(4), p.z.round(4)] }.sort
end

def bounds_from_surfaces(surfaces)
  pts = surfaces.flat_map(&:vertices)
  xs = pts.map(&:x); ys = pts.map(&:y); zs = pts.map(&:z)
  [xs.min, ys.min, zs.min, xs.max, ys.max, zs.max]
end

def check_basic(model)
  return false unless model.getBuilding.nameString == SPEC['building']
  return false unless model.getBuildingStorys.size == SPEC['metrics']['story_count']
  return false unless model.getSpaces.size == SPEC['metrics']['space_count']
  return false unless model.getThermalZones.size == SPEC['metrics']['zone_count']
  return false unless model.getSurfaces.size == SPEC['metrics']['surface_count']
  return false unless model.getSubSurfaces.size == SPEC['metrics']['window_count']
  return false unless model.getShadingSurfaces.size == SPEC['metrics']['shading_count']
  return false unless model.getSpaces.map(&:nameString).sort == SPEC['spaces'].map { |s| s['name'] }.sort
  return false unless model.getThermalZones.map(&:nameString).sort == SPEC['spaces'].map { |s| s['zone'] }.sort
  SPEC['spaces'].all? do |s|
    space = model.getSpaceByName(s['name'])
    return false if space.empty?
    space = space.get
    return false if space.thermalZone.empty? || space.thermalZone.get.nameString != s['zone']
    return false if space.buildingStory.empty? || space.buildingStory.get.nameString != s['story']
    return false if s['space_type'] && (space.spaceType.empty? || space.spaceType.get.nameString != s['space_type'])
    return false unless ok_close(space.floorArea, (s['x1']-s['x0'])*(s['y1']-s['y0']), 0.15)
    sb = bounds_from_surfaces(space.surfaces)
    expected_bounds = [s['x0'].to_f, s['y0'].to_f, (s['z0'] || 0).to_f, s['x1'].to_f, s['y1'].to_f, (s['z0'] || 0).to_f + s['h'].to_f]
    return false unless sb.zip(expected_bounds).all? { |a,e| ok_close(a,e,0.06) }
    true
  end
end

def check_geometry(model)
  surfaces = model.getSurfaces
  b = bounds_from_surfaces(surfaces)
  spans = [b[3]-b[0], b[4]-b[1], b[5]-b[2]]
  return false unless spans.zip(SPEC['metrics']['bbox']).all? { |a,e| ok_close(a,e,0.06) }
  floors = surfaces.select { |s| s.surfaceType == 'Floor' }
  walls = surfaces.select { |s| s.surfaceType == 'Wall' }
  ext_walls = walls.select { |s| s.outsideBoundaryCondition == 'Outdoors' }
  paired = surfaces.count { |s| s.outsideBoundaryCondition == 'Surface' }
  return false unless ok_close(floors.map(&:grossArea).sum, SPEC['metrics']['floor_area'], 0.5)
  return false unless ok_close(ext_walls.map(&:grossArea).sum, SPEC['metrics']['exterior_wall_area'], 0.75)
  return false unless paired == SPEC['metrics']['paired_surface_count']
  return false unless floors.count { |s| s.outsideBoundaryCondition == 'Ground' } == SPEC['metrics']['ground_floor_count']
  true
end

def parent_surface(model, space, wall)
  model.getSurfaceByName("#{space} #{wall.capitalize} Wall")
end

def sub_bounds(sub)
  pts = sub.vertices
  xs=pts.map(&:x); ys=pts.map(&:y); zs=pts.map(&:z)
  [xs.min, ys.min, zs.min, xs.max, ys.max, zs.max]
end

def check_windows(model)
  return false unless model.getSubSurfaces.all? { |s| s.subSurfaceType == 'FixedWindow' }
  return false unless ok_close(model.getSubSurfaces.map(&:grossArea).sum, SPEC['metrics']['window_area'], 0.35)
  SPEC.fetch('windows', []).all? do |w|
    parent = parent_surface(model, w['space'], w['wall'])
    return false if parent.empty?
    parent = parent.get
    matches = model.getSubSurfaces.select { |s| !s.surface.empty? && s.surface.get.handle.to_s == parent.handle.to_s }
    s_spec = SPEC['spaces'].find { |sp| sp['name'] == w['space'] }
    return false if s_spec.nil?
    expected_sill = (s_spec['z0'] || 0).to_f + w['sill'].to_f
    expected_head = (s_spec['z0'] || 0).to_f + w['head'].to_f
    expected_area = (w['end']-w['start'])*(w['head']-w['sill'])
    matches.any? do |sub|
      b = sub_bounds(sub)
      axis_ok = if ['south','north'].include?(w['wall'])
        ok_close(b[0], w['start'], 0.06) && ok_close(b[3], w['end'], 0.06)
      else
        ok_close(b[1], w['start'], 0.06) && ok_close(b[4], w['end'], 0.06)
      end
      axis_ok && ok_close(b[2], expected_sill, 0.06) && ok_close(b[5], expected_head, 0.06) && ok_close(sub.grossArea, expected_area, 0.12)
    end
  end
end

def check_schedules(model)
  SPEC.fetch('constant_schedules', {}).each do |name, value|
    return false unless ok_close(constant_value(model, name), value, 0.001)
  end
  SPEC.fetch('ruleset_schedules', {}).each do |name, data|
    rs = model.getScheduleRulesets.find { |s| s.nameString == name }
    return false if rs.nil?
    pairs = rs.defaultDaySchedule.times.zip(rs.defaultDaySchedule.values).map { |t,v| [t.totalHours.round(3), v] }
    return false unless pairs == data['default'].map { |h,v| [h.to_f, v.to_f] }
    data['rules'].each do |rule_spec|
      rule = rs.scheduleRules.find { |r| r.nameString == rule_spec['name'] }
      return false if rule.nil?
      day_checks = {
        'Monday'=>rule.applyMonday, 'Tuesday'=>rule.applyTuesday, 'Wednesday'=>rule.applyWednesday,
        'Thursday'=>rule.applyThursday, 'Friday'=>rule.applyFriday, 'Saturday'=>rule.applySaturday, 'Sunday'=>rule.applySunday
      }
      return false unless rule_spec['days'].all? { |d| day_checks[d] }
      rpairs = rule.daySchedule.times.zip(rule.daySchedule.values).map { |t,v| [t.totalHours.round(3), v] }
      return false unless rpairs == rule_spec['values'].map { |h,v| [h.to_f, v.to_f] }
    end
  end
  true
end

def load_schedule_matches(model, sched_name_expected, actual_optional)
  return true if sched_name_expected.nil?
  s = opt(actual_optional)
  s && s.nameString == sched_name_expected
end

def check_loads(model)
  SPEC.fetch('space_types', {}).each do |name, stspec|
    st = model.getSpaceTypeByName(name)
    return false if st.empty?
    st = st.get
    if stspec['default_schedule_set']
      return false if st.defaultScheduleSet.empty? || st.defaultScheduleSet.get.nameString != stspec['default_schedule_set']
    end
    if stspec.key?('people')
      loads = model.getPeoples.select { |p| !p.spaceType.empty? && p.spaceType.get.handle.to_s == st.handle.to_s }
      return false unless loads.size == 1
      p = loads[0]
      return false unless ok_close(p.peopleDefinition.peopleperSpaceFloorArea, stspec['people'], 0.0005)
      return false unless load_schedule_matches(model, stspec['people_schedule'], p.numberofPeopleSchedule)
    end
    if stspec.key?('lights')
      loads = model.getLightss.select { |l| !l.spaceType.empty? && l.spaceType.get.handle.to_s == st.handle.to_s }
      return false unless loads.size == 1
      l = loads[0]
      return false unless ok_close(l.lightsDefinition.wattsperSpaceFloorArea, stspec['lights'], 0.001)
      return false unless load_schedule_matches(model, stspec['lights_schedule'], l.schedule)
    end
    if stspec.key?('equipment')
      loads = model.getElectricEquipments.select { |e| !e.spaceType.empty? && e.spaceType.get.handle.to_s == st.handle.to_s }
      return false unless loads.size == 1
      e = loads[0]
      return false unless ok_close(e.electricEquipmentDefinition.wattsperSpaceFloorArea, stspec['equipment'], 0.001)
      return false unless load_schedule_matches(model, stspec['equipment_schedule'], e.schedule)
    end
  end
  SPEC.fetch('default_schedule_sets', {}).each do |name, dspec|
    ds = model.getDefaultScheduleSetByName(name)
    return false if ds.empty?
    ds = ds.get
    return false if dspec['people'] && (ds.numberofPeopleSchedule.empty? || ds.numberofPeopleSchedule.get.nameString != dspec['people'])
    return false if dspec['lights'] && (ds.lightingSchedule.empty? || ds.lightingSchedule.get.nameString != dspec['lights'])
    return false if dspec['equipment'] && (ds.electricEquipmentSchedule.empty? || ds.electricEquipmentSchedule.get.nameString != dspec['equipment'])
  end
  SPEC.fetch('space_default_sets', {}).each do |space_name, ds_name|
    space = model.getSpaceByName(space_name)
    return false if space.empty? || space.get.defaultScheduleSet.empty? || space.get.defaultScheduleSet.get.nameString != ds_name
  end
  true
end

def check_thermostats(model)
  SPEC['spaces'].each do |s|
    zone = model.getThermalZoneByName(s['zone'])
    return false if zone.empty?
    zone = zone.get
    if s['heat'].nil?
      return false if zone.useIdealAirLoads
      return false unless zone.thermostatSetpointDualSetpoint.empty?
    else
      return false unless zone.useIdealAirLoads
      return false if zone.thermostatSetpointDualSetpoint.empty?
      t = zone.thermostatSetpointDualSetpoint.get
      return false if t.heatingSetpointTemperatureSchedule.empty? || t.coolingSetpointTemperatureSchedule.empty?
      return false unless ok_close(opt(t.heatingSetpointTemperatureSchedule).to_ScheduleConstant.get.value, s['heat'], 0.01)
      return false unless ok_close(opt(t.coolingSetpointTemperatureSchedule).to_ScheduleConstant.get.value, s['cool'], 0.01)
    end
  end
  true
end

def check_infiltration_oa(model)
  inf_spec = SPEC.fetch('infiltration', {})
  if inf_spec['all']
    model.getSpaces.each do |space|
      objs = space.spaceInfiltrationDesignFlowRates
      return false unless objs.size == 1
      return false unless ok_close(objs[0].flowperExteriorSurfaceArea, inf_spec['all']['flow_per_exterior_area'], 0.000001)
      return false unless objs[0].schedule.empty? == false && objs[0].schedule.get.nameString == inf_spec['all']['schedule']
    end
  end
  oa_spec = SPEC.fetch('outdoor_air', {})
  if oa_spec['all']
    model.getSpaces.each do |space|
      return false if space.designSpecificationOutdoorAir.empty?
      oa=space.designSpecificationOutdoorAir.get
      return false unless oa.outdoorAirMethod == 'Sum'
      return false unless ok_close(oa.outdoorAirFlowperPerson, oa_spec['all']['per_person'], 0.000001)
      return false unless ok_close(oa.outdoorAirFlowperFloorArea, oa_spec['all']['per_floor_area'], 0.000001)
      return false unless oa.outdoorAirFlowRateFractionSchedule.empty? == false && oa.outdoorAirFlowRateFractionSchedule.get.nameString == oa_spec['all']['schedule']
    end
  else
    oa_spec.each do |space_name, expected|
      space = model.getSpaceByName(space_name)
      return false if space.empty? || space.get.designSpecificationOutdoorAir.empty?
      oa=space.get.designSpecificationOutdoorAir.get
      return false unless ok_close(oa.outdoorAirFlowperPerson, expected['per_person'], 0.000001)
      return false unless ok_close(oa.outdoorAirFlowperFloorArea, expected['per_floor_area'], 0.000001)
    end
  end
  true
end

def check_daylighting(model)
  specs = SPEC.fetch('daylighting', [])
  return false unless model.getDaylightingControls.size == specs.size
  return false unless model.getIlluminanceMaps.size == specs.size
  specs.all? do |d|
    space = model.getSpaceByName(d['space'])
    return false if space.empty?
    controls = model.getDaylightingControls.select { |c| !c.space.empty? && c.space.get.handle.to_s == space.get.handle.to_s }
    return false unless controls.size == 1
    c=controls[0]
    return false unless ok_close(c.positionXCoordinate, d['point'][0], 0.06) && ok_close(c.positionYCoordinate, d['point'][1], 0.06) && ok_close(c.positionZCoordinate, d['point'][2], 0.06)
    return false unless ok_close(c.illuminanceSetpoint, d['setpoint'], 0.5)
    return false unless c.lightingControlType == 'Continuous'
    maps = model.getIlluminanceMaps.select { |im| !im.space.empty? && im.space.get.handle.to_s == space.get.handle.to_s }
    return false unless maps.size == 1
    im=maps[0]
    return false if space.get.thermalZone.empty?
    zone = space.get.thermalZone.get
    return false if zone.primaryDaylightingControl.empty? || zone.primaryDaylightingControl.get.handle.to_s != c.handle.to_s
    return false unless zone.fractionofZoneControlledbyPrimaryDaylightingControl > 0.0
    return false if zone.illuminanceMap.empty? || zone.illuminanceMap.get.handle.to_s != im.handle.to_s
    return false unless ok_close(im.originXCoordinate, d['map_origin'][0], 0.06) && ok_close(im.originYCoordinate, d['map_origin'][1], 0.06) && ok_close(im.originZCoordinate, d['map_origin'][2], 0.06)
    return false unless ok_close(im.xLength, d['map_lengths'][0], 0.06) && ok_close(im.yLength, d['map_lengths'][1], 0.06)
    return false unless im.numberofXGridPoints == d['map_grid'][0] && im.numberofYGridPoints == d['map_grid'][1]
    true
  end
end

def check_shading(model)
  return false unless ok_close(model.getShadingSurfaces.map(&:grossArea).sum, SPEC['metrics']['shading_area'], 0.25)
  SPEC.fetch('shading', []).all? do |sh|
    s = model.getShadingSurfaceByName(sh['name'])
    return false if s.empty?
    b = sub_bounds(s.get)
    ok_close(b[0], sh['x0'], 0.06) && ok_close(b[3], sh['x1'], 0.06) && ok_close(b[1], sh['y0'], 0.06) && ok_close(b[4], sh['y1'], 0.06) && ok_close(b[2], sh['z'], 0.06) && ok_close(b[5], sh['z'], 0.06)
  end
end

def check_constructions(model)
  c = SPEC.fetch('constructions', nil)
  return true if c.nil?
  c.each do |kind, cspec|
    next if kind == 'window'
    con = model.getConstructionByName(cspec['name'])
    return false if con.empty?
    layers = con.get.layers
    return false unless layers.size == cspec['layers'].size
    return false unless layers.map(&:nameString) == cspec['layers'].map { |layer| layer['name'] }
    targets = case kind
      when 'wall' then model.getSurfaces.select { |s| s.surfaceType == 'Wall' && s.outsideBoundaryCondition == 'Outdoors' }
      when 'roof' then model.getSurfaces.select { |s| s.surfaceType == 'RoofCeiling' && s.outsideBoundaryCondition == 'Outdoors' }
      when 'floor' then model.getSurfaces.select { |s| s.surfaceType == 'Floor' && s.outsideBoundaryCondition == 'Ground' }
      else []
    end
    return false if targets.empty?
    return false unless targets.all? { |surface| !surface.construction.empty? && surface.construction.get.handle.to_s == con.get.handle.to_s }
    cspec['layers'].each do |mspec|
      mat = model.getStandardOpaqueMaterialByName(mspec['name'])
      return false if mat.empty?
      mat = mat.get
      return false unless ok_close(mat.thickness, mspec['thickness'], 0.0005)
      return false unless ok_close(mat.conductivity, mspec['conductivity'], 0.0005)
      return false unless ok_close(mat.density, mspec['density'], 0.5)
      return false unless ok_close(mat.specificHeat, mspec['specific_heat'], 0.5)
    end
  end
  if c['window']
    con = model.getConstructionByName(c['window']['name'])
    return false if con.empty?
    layers = con.get.layers
    return false unless layers.size == 1
    g_optional = layers[0].to_SimpleGlazing
    return false if g_optional.empty?
    g = g_optional.get
    return false unless ok_close(g.uFactor, c['window']['u_factor'], 0.02) && ok_close(g.solarHeatGainCoefficient, c['window']['shgc'], 0.01) && ok_close(g.visibleTransmittance, c['window']['vt'], 0.01)
    return false unless model.getSubSurfaces.all? { |sub| !sub.construction.empty? && sub.construction.get.handle.to_s == con.get.handle.to_s }
  end
  true
end

def check_water_exterior_output(model)
  SPEC.fetch('water_use', []).each do |w|
    eq = model.getWaterUseEquipmentByName(w['name'])
    return false if eq.empty?
    eq = eq.get
    return false if eq.space.empty? || eq.space.get.nameString != w['space']
    d = eq.waterUseEquipmentDefinition
    return false unless ok_close(d.peakFlowRate, w['peak_flow'], 0.000001)
    return false if eq.flowRateFractionSchedule.empty? || eq.flowRateFractionSchedule.get.nameString != w['flow_schedule']
    return false if d.targetTemperatureSchedule.empty? || d.targetTemperatureSchedule.get.nameString != w['target_temp_schedule']
    return false unless d.endUseSubcategory == w['end_use']
  end
  SPEC.fetch('exterior_lights', []).each do |e|
    obj = model.getExteriorLightsByName(e['name'])
    return false if obj.empty?
    obj=obj.get
    return false unless ok_close(obj.exteriorLightsDefinition.designLevel, e['design_level'], 0.01)
    return false if obj.schedule.empty? || obj.schedule.get.nameString != e['schedule']
    return false unless obj.controlOption == e['control']
  end
  SPEC.fetch('output_variables', []).each do |v|
    obj = model.getOutputVariableByName(v['name'])
    return false if obj.empty?
    obj=obj.get
    return false unless obj.variableName == v['variable']
    kv = obj.keyValue
    kv = kv.get if kv.respond_to?(:get) && (!kv.respond_to?(:empty?) || !kv.empty?)
    return false if kv.nil? || kv != v['key']
    return false unless obj.reportingFrequency == v['frequency']
  end
  SPEC.fetch('output_meters', []).each do |m|
    obj = model.getOutputMeterByName(m['name'])
    return false if obj.empty?
    return false unless obj.get.reportingFrequency == m['frequency']
  end
  true
end

def check_pv(model)
  pv = SPEC.fetch('pv', nil)
  return true if pv.nil?
  return false unless model.getGeneratorPVWattss.size == pv['generators'].size
  pv['generators'].each do |g|
    obj = model.getGeneratorPVWattsByName(g['name'])
    return false if obj.empty?
    obj=obj.get
    return false unless ok_close(obj.dcSystemCapacity, g['capacity'], 0.1)
    return false unless obj.moduleType == g['module']
    return false unless obj.arrayType == g['array']
    return false unless ok_close(obj.systemLosses, g['losses'], 0.001)
    return false unless ok_close(obj.tiltAngle, g['tilt'], 0.1)
    return false unless ok_close(obj.azimuthAngle, g['azimuth'], 0.1)
    if g['surface_space']
      return false if obj.surface.empty?
      expected_surface = model.getSurfaceByName("#{g['surface_space']} #{g.fetch('surface', 'roof').capitalize}")
      return false if expected_surface.empty? || obj.surface.get.handle.to_s != expected_surface.get.handle.to_s
    end
  end
  inv = model.getElectricLoadCenterInverterPVWattsByName(pv['inverter']['name'])
  return false if inv.empty?
  inv=inv.get
  return false unless ok_close(inv.dcToACSizeRatio, pv['inverter']['dc_to_ac'], 0.001)
  return false unless ok_close(inv.inverterEfficiency, pv['inverter']['efficiency'], 0.001)
  dist = model.getElectricLoadCenterDistributionByName(pv['distribution'])
  return false if dist.empty?
  dist=dist.get
  return false unless dist.generatorOperationSchemeType == pv['operation']
  return false unless dist.electricalBussType == pv['bus']
  return false if dist.inverter.empty? || dist.inverter.get.handle.to_s != inv.handle.to_s
  expected_generators = pv['generators'].map { |g| model.getGeneratorPVWattsByName(g['name']).get.handle.to_s }.sort
  return false unless dist.generators.map { |g| g.handle.to_s }.sort == expected_generators
  true
end

loaded = OpenStudio::Model::Model.load(OpenStudio::Path.new(PATH))
if loaded.empty?
  puts 'OS_EVAL_FALSE'
  exit 0
end
model = loaded.get
checks = [
  method(:check_basic), method(:check_geometry), method(:check_windows), method(:check_schedules), method(:check_loads), method(:check_thermostats), method(:check_infiltration_oa), method(:check_daylighting), method(:check_shading), method(:check_constructions), method(:check_water_exterior_output), method(:check_pv)
]
ok = checks.all? { |m| m.call(model) }
puts(ok ? 'OS_EVAL_TRUE' : 'OS_EVAL_FALSE')
"""

def main():
    if not RESULT.is_file() or RESULT.stat().st_size < 1000:
        print('False')
        return
    with tempfile.NamedTemporaryFile('w', suffix='.rb', delete=False, encoding='utf-8') as f:
        f.write(RUBY)
        script = Path(f.name)
    try:
        proc = subprocess.run(['openstudio', '--loglevel', 'Error', 'execute_ruby_script', str(script), str(RESULT)], text=True, capture_output=True, timeout=90)
        ok = proc.returncode == 0 and 'OS_EVAL_TRUE' in proc.stdout
    except Exception:
        ok = False
    finally:
        script.unlink(missing_ok=True)
    print('True' if ok else 'False')

if __name__ == '__main__':
    main()
