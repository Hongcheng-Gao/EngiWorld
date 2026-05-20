# Launch 路径审计与修复报告（已按用户更正）

**更正说明（2026-05-20）**：此前误将路径改为 v241/runwb2 与 EstProducts/2023；用户确认正确路径见下。**task-c 故意不含 `config.launch`**，仅 **task-v** 使用 launch。

---

## 1. 正确标准路径（以用户最新说明为准）

| 软件 | task-v `config.launch` |
|------|------------------------|
| **Abaqus** | `C:\SIMULIA\CAE\2025LE\win_b64\resources\install\le\launcher.bat` + `cae` |
| **ANSYS（APDL/Workbench 等）** | `C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe` + `-g`（task-01 另含 `-np`, `2`） |
| **ANSYS Fluent 题** | `C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe` + `-g`（09–10, 15–17） |

手工 cmd 可写 `launcher.bat cae || pause`；JSON launch 仍为数组 `["...launcher.bat", "cae"]`。

---

## 2. 当前状态

### task-c（abaqus / ansys）

- **无** `type: "launch"`（已从误加的 40 个 JSON 中全部移除）
- 启动说明仅在 instruction 末尾 `[Software] ...`（未改文案；部分 `[Software]` 仍可能写 EstProducts/v241，与 VM 实际路径不一致时需另改）

### task-v（abaqus / ansys）

- **abaqus 20 题**：launch 已恢复为 **2025LE** `le\launcher.bat` + `cae`
- **ansys 20 题**：非 Fluent 题为 **v261 ANSYS261.exe -g**；Fluent 题为 **v261 fluent.exe -g**

---

## 3. 其它软件（未改，仅统计）

原则：**task-c** 多在 instruction 有 `[Software]`，**config 通常无 launch**；**task-v** 多在 config 有 launch，instruction 常无 `[Software]`。

| 应用 | task-c | task-v | 对齐情况 |
|------|--------|--------|----------|
| autocad, freecad, revit, … | 多数有 `[Software]`，无 launch | 多数有 launch，无 `[Software]` | 需人工：从 task-v 抄 launch 到 task-c（本次未做） |
| blender (task-c) | `[Software]` 写 `blender` | — | instruction 与 CLI 名一致 |
| revit (task-v 11–16) | — | launch 为 Desktop 快捷方式 `.lnk` | 与标准 `Revit.exe` 可能不一致（未改） |

完整逐应用统计见脚本运行时的 `launch_path_audit_report.md` 第 3 节（修复前生成）；修复后 **abaqus/ansys 已对齐**。

---

## 4. JSON / eval 完整性

| 检查项 | 结果 |
|--------|------|
| 全部 `task-*.json` 解析 | **0 错误** |
| 全部 `eval.py` 语法 | **0 错误** |
| **损坏已修** | `task-v/ansys/task-01/eval.py` 曾在 `reaction_fy_on_z` 处截断，已补全 `extract_predictions` / `evaluate` / `main` |
| **误报说明** | task-c/abaqus 的 eval 通过 `abaqus cae noGUI=eval.py` 运行，无 `def evaluate()`，属正常模式 |

---

## 5. 仍建议后续处理（未在本次修改）

1. **task-c/ansys**：Fluent/APDL 题的 `[Software]` 均写 `runwb2`，与题目类型不一致；若 VM 按模块启动，应改为 `fluent.exe` / `ANSYS241.exe` 并与 launch 同步。
2. **task-v/abaqus、ansys**：instruction 无 `[Software]`，agent 看不到启动路径（仅环境 launch 配置有）。
3. **eval 内 EXEC_FILE**：部分 ansys eval 仍写 v261 `ANSYS261.exe`（仅影响评测脚本自启 MAPDL，不影响 JSON launch）。
4. **其它 CAD/BIM 软件**：按「task-c 从 task-v 抄 launch」批量补齐（用户要求本次不改）。

---

## 6. 修改文件清单

- `task/task-c/abaqus/task-01` … `task-20`：新增 `config.launch`
- `task/task-v/abaqus/task-01` … `task-20`：更正 launch 路径
- `task/task-c/ansys/task-01` … `task-20`：新增/同步 `config.launch` → `runwb2.exe`
- `task/task-v/ansys/task-01` … `task-20`：按题型更正 launch
- `task/task-v/ansys/task-01/eval.py`：补全截断代码

辅助脚本：`.scripts/audit_launch_paths.py`、`.scripts/fix_launch_escape.py`、`.scripts/sync_launch_from_software.py`、`.scripts/integrity_scan.py`
