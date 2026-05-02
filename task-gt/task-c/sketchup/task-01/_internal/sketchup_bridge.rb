require 'json'

module EngiworldSketchupTask01Bridge
  MODE = ENV['ENGIWORLD_TASK01_MODE']
  SUMMARY_JSON = ENV['ENGIWORLD_TASK01_SUMMARY_JSON']
  PARAMS_JSON = ENV['ENGIWORLD_TASK01_PARAMS_JSON']
  OUTPUT_SKP = ENV['ENGIWORLD_TASK01_OUTPUT_SKP']
  ERROR_LOG = ENV['ENGIWORLD_TASK01_ERROR_LOG']

  def self.log_error(message)
    return unless ERROR_LOG && !ERROR_LOG.empty?

    File.write(ERROR_LOG, "#{message}\n")
  rescue StandardError
    nil
  end

  def self.to_m(value)
    value.to_m.to_f
  end

  def self.point_to_a(point)
    [to_m(point.x), to_m(point.y), to_m(point.z)]
  end

  def self.collect_faces(entities, transform, faces)
    entities.each do |entity|
      case entity
      when Sketchup::Face
        pts = entity.outer_loop.vertices.map do |vertex|
          point_to_a(vertex.position.transform(transform))
        end
        faces << pts unless pts.empty?
      when Sketchup::Group
        collect_faces(entity.entities, transform * entity.transformation, faces)
      when Sketchup::ComponentInstance
        collect_faces(entity.definition.entities, transform * entity.transformation, faces)
      end
    end
  end

  def self.clear_root_entities(model)
    model.entities.to_a.each do |entity|
      next unless entity.valid?

      begin
        entity.erase!
      rescue StandardError
        nil
      end
    end
  end

  def self.build_staircase
    raise 'missing PARAMS_JSON' unless PARAMS_JSON && File.exist?(PARAMS_JSON)
    raise 'missing OUTPUT_SKP' unless OUTPUT_SKP && !OUTPUT_SKP.empty?

    params = JSON.parse(File.read(PARAMS_JSON))
    n = (params['total_rise_m'].to_f * 1000.0 / params['max_rise_per_step_mm'].to_f).ceil
    rise = params['total_rise_m'].to_f / n
    run = params['total_run_m'].to_f / n
    thickness = params['tread_thickness_mm'].to_f / 1000.0
    width = params['tread_width_m'].to_f

    model = Sketchup.active_model
    model.start_operation('Engiworld Task01 Build', true)
    clear_root_entities(model)

    n.times do |i|
      x0 = i * run
      x1 = (i + 1) * run
      y0 = 0.0
      y1 = width
      z1 = (i + 1) * rise
      z0 = z1 - thickness

      pts = [
        Geom::Point3d.new(x0.m, y0.m, z0.m),
        Geom::Point3d.new(x1.m, y0.m, z0.m),
        Geom::Point3d.new(x1.m, y1.m, z0.m),
        Geom::Point3d.new(x0.m, y1.m, z0.m)
      ]

      face = model.entities.add_face(pts)
      face.reverse! if face.normal.z < 0
      face.pushpull(thickness.m)
    end

    model.commit_operation

    ok = model.save_copy(OUTPUT_SKP)
    raise "failed to save #{OUTPUT_SKP}" unless ok

    if SUMMARY_JSON && !SUMMARY_JSON.empty?
      File.write(
        SUMMARY_JSON,
        JSON.pretty_generate(
          {
            mode: 'build_staircase',
            output_skp: OUTPUT_SKP
          }
        )
      )
    end
  end

  def self.extract_faces
    faces = []
    collect_faces(Sketchup.active_model.entities, Geom::Transformation.new, faces)
    raise 'missing SUMMARY_JSON' unless SUMMARY_JSON && !SUMMARY_JSON.empty?

    File.write(
      SUMMARY_JSON,
      JSON.pretty_generate(
        {
          mode: 'extract_faces',
          faces: faces
        }
      )
    )
  end

  def self.dispatch
    case MODE
    when 'build_staircase'
      build_staircase
    when 'extract_faces'
      extract_faces
    else
      raise "unsupported mode #{MODE.inspect}"
    end
  rescue StandardError => e
    log_error("#{e.class}: #{e.message}\n#{Array(e.backtrace).join("\n")}")
  ensure
    Sketchup.quit
  end
end

UI.start_timer(1.0, false) do
  EngiworldSketchupTask01Bridge.dispatch
end
