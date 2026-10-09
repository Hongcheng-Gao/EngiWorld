[English](README.md) | [简体中文](README_CN.md)

本目录包含 task-01 初始模型及该算例的可执行工作流约定。

运行时将 `init.ifc`、`workflow_spec.json`、指定 IFC 转换器、三个阶段启动器、OpenStudio 转换程序和 `weather.epw` 上传至 `C:\Users\user\Desktop`。按阶段编号顺序执行启动器；缺少原生程序、桥接组件、指定版本或上游产物时，启动器会报错并停止。
