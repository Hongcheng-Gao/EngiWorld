# Task 05 instance cleanup record

Cleanup was performed immediately after all formal artifacts and the native generation receipt were downloaded and hash-compared. It targeted only files created for `multi/cli-2-archicad-openstudio/task-05` in `C:\Users\user\Desktop`, the dedicated `run` directory, and task-local `C:\EW05-CODEX-*` databases.

The first cleanup pass removed the uploaded seed, all Stage-1/Stage-2 outputs, both audit inputs, the Archicad/OpenStudio/evaluator scripts, `multi_metrics.json`, the native receipt, `run/`, and `__pycache__/eval.cpython-311.pyc`. The post-cleanup comparison found one additional Archicad-generated file, `stage1.ifc.log`. A second explicit pass removed that file.

Final verification confirmed:

- Desktop names exactly matched the pre-run baseline: `__pycache__`, `Archicad 27.lnk`, `desktop.ini`, `generated_files`, `Microsoft Edge.lnk`, `OpenStudioApp.lnk`, `OpenStudioApplication-1.11.1`, `out.osw`, and `reports`;
- no extra or missing Desktop item remained;
- no `C:\EW05-CODEX-*` database remained;
- TCP port 12343 was not listening;
- no `IFCCommandServerApp`, OpenStudio, or EnergyPlus process remained.

After this verification, the CLI2 tunnel, the stale OpenStudio script tunnel, and the separate OpenStudio public SSH forward were closed. Other unrelated instance tunnels were not changed.
