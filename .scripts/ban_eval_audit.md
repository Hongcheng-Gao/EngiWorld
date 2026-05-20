# 禁脚本 instruction vs eval 检测审计

判定说明：
- **instruction 禁脚本**：含 `external script files is strictly prohibited`、`GUI-only`、`helper script` 等（不含「Do not use X GUI」——后者表示必须用 CLI）。
- **eval 有检测**：`has_forbidden_py_file`、`GUI_BYPASS_*`、`_desktop_script_artifacts` 等。

## 1. 按 tier + 软件汇总

| tier | 软件 | 禁脚本题数 | eval 有检测 | **缺口（禁了但未检）** | 无禁脚本题数 |
|---|---|---:|---:|---:|---:|
| task-c | abaqus | 0 | 0 | **0** | 20 |
| task-c | altium-designer | 0 | 0 | **0** | 25 |
| task-c | ansys | 0 | 0 | **0** | 20 |
| task-c | archicad | 0 | 0 | **0** | 20 |
| task-c | autocad | 0 | 0 | **0** | 20 |
| task-c | blender | 0 | 0 | **0** | 50 |
| task-c | bonsai | 0 | 0 | **0** | 20 |
| task-c | brl-cad | 0 | 0 | **0** | 20 |
| task-c | cadence-orcad | 0 | 0 | **0** | 30 |
| task-c | calculix | 0 | 0 | **0** | 20 |
| task-c | eagle | 0 | 0 | **0** | 23 |
| task-c | fenics | 0 | 0 | **0** | 20 |
| task-c | floris | 0 | 0 | **0** | 20 |
| task-c | freecad | 0 | 0 | **0** | 20 |
| task-c | freecad-path | 0 | 0 | **0** | 20 |
| task-c | kicad | 0 | 0 | **0** | 23 |
| task-c | openfast | 0 | 0 | **0** | 20 |
| task-c | openfoam | 0 | 0 | **0** | 20 |
| task-c | openscad | 0 | 0 | **0** | 20 |
| task-c | openstudio | 0 | 0 | **0** | 20 |
| task-c | revit | 0 | 0 | **0** | 20 |
| task-c | solidcam | 0 | 0 | **0** | 20 |
| task-c | solidworks | 0 | 0 | **0** | 20 |
| task-v | abaqus | 20 | 20 | **0** | 0 |
| task-v | altium-designer | 0 | 0 | **0** | 24 |
| task-v | ansys | 20 | 20 | **0** | 0 |
| task-v | archicad | 20 | 20 | **0** | 0 |
| task-v | autocad | 20 | 20 | **0** | 0 |
| task-v | blender | 0 | 0 | **0** | 40 |
| task-v | bonsai | 20 | 20 | **0** | 0 |
| task-v | cadence-orcad | 0 | 0 | **0** | 30 |
| task-v | eagle | 0 | 0 | **0** | 23 |
| task-v | freecad | 20 | 20 | **0** | 0 |
| task-v | freecad-path | 20 | 20 | **0** | 0 |
| task-v | kicad | 0 | 0 | **0** | 24 |
| task-v | librecad | 20 | 20 | **0** | 0 |
| task-v | openscad | 20 | 20 | **0** | 0 |
| task-v | openstudio | 20 | 20 | **0** | 0 |
| task-v | revit | 16 | 16 | **0** | 0 |
| task-v | solidcam | 20 | 20 | **0** | 0 |
| task-v | solidworks | 20 | 20 | **0** | 0 |
| task-v | solvespace | 20 | 20 | **0** | 0 |
| task-v | zbrush | 0 | 0 | **0** | 30 |

## 2. tier 合计

| tier | 禁脚本题数 | eval 有检测 | 缺口 | 无禁脚本题数 |
|---|---:|---:|---:|---:|
| task-c | 0 | 0 | **0** | 511 |
| task-v | 276 | 276 | **0** | 171 |

## 3. 缺口明细（instruction 禁脚本且 eval 未检测）

### task-c（共 0 题）

- 无

### task-v（共 0 题）

- 无


## 4. 已有检测的软件（禁脚本且 eval 覆盖）

- **task-c**: 无
- **task-v**: abaqus(20), ansys(20), archicad(20), autocad(20), bonsai(20), freecad(20), freecad-path(20), librecad(20), openscad(20), openstudio(20), revit(16), solidcam(20), solidworks(20), solvespace(20)