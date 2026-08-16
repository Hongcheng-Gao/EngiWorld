This directory contains the task-02 retail seed and its executable workflow contract.

At VM runtime, `init.ifc`, `workflow_spec.json`, the task-local Revit bridge,
the pinned IFC translator, the three stage launchers, the OpenStudio converter,
and `weather.epw` are uploaded to `C:\Users\user\Desktop`. Run the launchers in
numeric stage order. Each launcher fails closed when a required executable,
bridge, version, or upstream artifact is missing. The Archicad stage reports and
preserves the boundary relationships actually present in the native files; it
does not synthesize absent second-level relationships.
