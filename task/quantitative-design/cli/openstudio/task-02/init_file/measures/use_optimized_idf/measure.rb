class UseOptimizedIdf < OpenStudio::Measure::EnergyPlusMeasure
  def name
    'Use Optimized IDF'
  end

  def description
    'Loads the optimized EnergyPlus IDF into the OpenStudio workflow workspace.'
  end

  def modeler_description
    'Replaces the translated workspace before the workflow invokes bundled EnergyPlus.'
  end

  def arguments(workspace)
    args = OpenStudio::Measure::OSArgumentVector.new
    idf_path = OpenStudio::Measure::OSArgument.makeStringArgument('idf_path', true)
    idf_path.setDisplayName('Optimized IDF path')
    args << idf_path
    args
  end

  def run(workspace, runner, user_arguments)
    super(workspace, runner, user_arguments)
    return false unless runner.validateUserArguments(arguments(workspace), user_arguments)

    source_path = runner.getStringArgumentValue('idf_path', user_arguments)
    loaded = OpenStudio::IdfFile.load(OpenStudio::Path.new(source_path))
    if loaded.empty?
      runner.registerError("Cannot load optimized IDF: #{source_path}")
      return false
    end

    workspace.removeObjects(workspace.objects.map(&:handle))
    source_objects = loaded.get.objects
    added_objects = workspace.addObjects(source_objects)
    if added_objects.size != source_objects.size
      runner.registerError('Could not transfer every optimized IDF object into the workflow workspace')
      return false
    end

    runner.registerFinalCondition("Loaded #{added_objects.size} objects from #{source_path}")
    true
  end
end

UseOptimizedIdf.new.registerWithApplication
