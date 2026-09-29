[English](README.md) | [简体中文](README_CN.md)

本目录包含 task-02 零售空间初始模型及可执行工作流约定。

运行时将 `init.ifc`、`workflow_spec.json`、任务专属 Revit 桥接程序、指定 IFC 转换器、三个启动器、OpenStudio 转换程序和 `weather.epw` 上传至 `C:\Users\user\Desktop`。按阶段编号执行；缺少程序、桥接组件、版本或上游产物时会报错并停止。Archicad 阶段报告并保留原生文件实际包含的边界关系，不构造不存在的二级关系。
