[English](README.md) | [简体中文](README_CN.md)

# Envelope insulation and glazing energy trim

Use OpenStudio CLI/SDK 3.11.0 with `baseline.idf`, `weather.epw`, `constraints.json`, `workflow.osw`, and the provided `UseOptimizedIdf` EnergyPlus Measure. The IDF is the EnergyPlus workspace input: the Measure loads it after model translation, and `openstudio run -w /home/user/Desktop/workflow.osw` then invokes OpenStudio's bundled EnergyPlus 25.2 engine. Write the final model to `/home/user/Desktop/optimized.idf`; the workflow writes simulation outputs under `/home/user/Desktop/run/`.
