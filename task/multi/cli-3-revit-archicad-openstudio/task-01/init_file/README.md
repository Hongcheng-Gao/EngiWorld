This directory contains the task-01 seed and its case-specific executable workflow contract.

At VM runtime, `init.ifc`, `workflow_spec.json`, the pinned IFC translator, the
three stage launchers, the OpenStudio converter, and `weather.epw` are uploaded
to `C:\Users\user\Desktop`. Run the launchers in numeric stage order. Each
launcher fails closed when the required native executable, bridge, version, or
upstream artifact is missing.
