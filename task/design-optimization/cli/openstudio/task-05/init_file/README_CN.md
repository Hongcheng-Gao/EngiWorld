[English](README.md) | [简体中文](README_CN.md)

# 渗透与通风的能耗及空气质量权衡

使用 OpenStudio CLI/SDK 3.11.0，以及 `baseline.idf`、`weather.epw`、`constraints.json`、`workflow.osw` 和提供的 `UseOptimizedIdf` EnergyPlus Measure。IDF 是 EnergyPlus 的工作空间输入：Measure 在模型转换后加载它，随后 `openstudio run -w /home/user/Desktop/workflow.osw` 调用 OpenStudio 自带的 EnergyPlus 25.2 引擎。最终模型保存至 `/home/user/Desktop/optimized.idf`，工作流将模拟输出写入 `/home/user/Desktop/run/`。
