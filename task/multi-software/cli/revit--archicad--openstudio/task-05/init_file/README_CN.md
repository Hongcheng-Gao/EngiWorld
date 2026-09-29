[English](README.md) | [简体中文](README_CN.md)

本目录包含固定的 task-05 IFC4 初始模型及可执行的原生工作流约定。

初始模型有两层，每层为 10.0 m × 7.0 m，室内房间平面为 9.8 m × 6.8 m。一层的两个房间由一面内墙分隔，二层有一个房间。Revit 阶段只移除一层的这面隔墙，在上层创建一条房间分隔线，并在原有二层楼板上创建真实开口。初始模型本身没有开口，因此工作流要求“创建”而非“保留”。

本任务使用的官方版本参考：

- Revit 2025 API 与 IFC 导出：https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html
- Revit 2025 `NewOpening(Element, CurveArray, Boolean)`：https://www.revitapidocs.com/2025/ab1718f9-45fb-b3d3-827e-32ff81cf929c.htm
- Archicad 27 IFC：https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- Archicad JSON 接口：https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0：https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- EnergyPlus 25.1 SQLite 输出：https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html
