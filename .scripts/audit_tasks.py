"""QA audit for all task JSON under task/."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK_ROOT = REPO / "task"
OUT = REPO / ".scripts" / "task_audit_report.md"

# Ground-truth launch paths (key = related_apps slug)
STANDARD: dict[str, list[str]] = {
    "bonsai": ["blender"],
    "blender": ["blender"],
    "openstudio": ["OpenStudioApp"],
    "librecad": ["librecad"],
    "freecad": ["freecad"],
    "solvespace": ["solvespace"],
    "freecad-path": ["freecad"],
    "openscad": ["openscad"],
    "brl-cad": ["mged"],
    "openfoam": ["foamRun"],
    "calculix": ["ccx"],
    "kicad": ["kicad", "kicad-cli"],
    "eagle": ["/opt/eagle-7.7.0/bin/eagle", "eagle"],
    "autocad": [r"C:\Program Files\Autodesk\AutoCAD 2024\acad.exe", "acad.exe"],
    "revit": [r"C:\Program Files\Autodesk\Revit 2025\Revit.exe", "Revit.exe"],
    "archicad": [r"C:\Program Files\Graphisoft\Archicad 27\Archicad", "Archicad"],
    "ansys": [r"C:\Program Files\ANSYS Inc\v241\Framework\bin\Win64\runwb2.exe", "runwb2.exe"],
    "abaqus": ["launcher.bat", "cmdDirFeature"],
    "altium-designer": [r"D:\Program Files (x86)\Altium\AD17\DXP.EXE", "DXP.EXE"],
    "zbrush": [r"C:\Maxon ZBrush 2025\ZBrush.exe", "ZBrush.exe"],
    "solidworks": [r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS", "SOLIDWORKS"],
    "sketchup": ["SketchUp.exe"],
    "cadence-orcad": [r"C:\Cadence\SPB_24.1\tools\bin\capture.exe", "capture.exe"],
    "solidcam": [r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS", "SOLIDWORKS"],
    "nx-cam": ["ugraf.exe", "NXBIN"],
    "openfast": ["openfast"],
    "ptc-creo": ["creo"],
    "fusion360": ["fusion"],
    "catia": ["catia"],
    "fenics": ["fenics"],
    "floris": ["floris"],
}

LAUNCH_PATTERNS = [
    re.compile(r"Launch\s+.+?\s+with\s+`([^`]+)`", re.I),
    re.compile(r"\[Software\][^\n]*?run\s+`([^`]+)`", re.I),
    re.compile(r"To use .+? run\s+`([^`]+)`", re.I),
    re.compile(r"To start .+? run\s+`([^`]+)`", re.I),
]

DESKTOP_SHORTCUT = re.compile(
    r"Launch\s+\w+.*?(?:from\s+the\s+\w+\s+shortcut\s+on\s+the\s+Desktop|shortcut\s+on\s+the\s+Desktop)",
    re.I,
)

# True "no scripting" bans — exclude "Do not use <App> GUI" (CLI-required tasks).
CODE_BAN_POSITIVE = re.compile(
    r"(?i)(GUI-only\s+requirement|"
    r"do\s+not\s+open\s+(?:Command\s+Prompt|PowerShell|Terminal)|"
    r"do\s+not\s+.*?(?:python|macro|autolisp|dynamo|pyrevit|helper\s+script|external\s+api\s+automation)|"
    r"helper\s+script/code\s+that\s+directly\s+generates|"
    r"must\s+use\s+the\s+gui\b|"
    r"no\s+external\s+code|"
    r"禁止使用.*?(?:脚本|python)|"
    r"不允许.*?(?:ezdxf|accoreconsole)|"
    r"do\s+not\s+use\s+ezdxf|"
    r"do\s+not\s+write\s+any\s+script|"
    r"external\s+script\s+files\s+is\s+strictly\s+prohibited|"
    r"use\s+of\s+external\s+script\s+files\s+is\s+strictly\s+prohibited)"
)
CODE_BAN_NEGATIVE = re.compile(
    r"(?i)do\s+not\s+use\s+(?:the\s+)?(?:\w+\s+)*(?:GUI|graphical\s+user\s+interface|visualization\s+GUI)"
)

EVAL_SCRIPT_CHECK = re.compile(
    r"(?i)(GUI_BYPASS|ACADVER|ezdxf.*(?:forbid|ban|reject)|"
    r"_has_generated_python|trajectory|traj_path|process_list|"
    r"headless|script_artifact|_desktop_script|_history_contains_bypass|"
    r"check_.*script|forbid.*python|no_gui_bypass)"
)

PLACEHOLDER_EVAL = re.compile(
    r"LWPOLYLINE['\"]\s*:\s*1\s*,\s*['\"]TEXT['\"]\s*:\s*1",
)

INSTRUCTION_RECREATE = re.compile(r"(?i)(Recreate|outlines, holes, slots)")

# Apps where task-c expects CLI/scripting (not a ban)
CLI_EXPECTED_APPS = {
    "abaqus", "ansys", "autocad", "freecad", "freecad-path", "openfoam",
    "calculix", "fenics", "floris", "openfast", "openscad", "brl-cad",
    "fusion360", "ptc-creo", "openfoam", "calculix",
}


def norm_path(p: str) -> str:
    return p.replace("\\\\", "\\").replace("/", "\\").strip().rstrip("\\").lower()


def path_matches(actual: str, standards: list[str]) -> bool:
    a = norm_path(actual)
    for s in standards:
        sn = norm_path(s)
        if sn in a or a.endswith(sn.split("\\")[-1]):
            return True
    return False


def extract_launch(instruction: str) -> tuple[str | None, str | None]:
    """Return (kind, path_or_note): kind in launch_path|desktop_shortcut|none"""
    if DESKTOP_SHORTCUT.search(instruction):
        return "desktop_shortcut", DESKTOP_SHORTCUT.search(instruction).group(0)[:80]
    for pat in LAUNCH_PATTERNS:
        m = pat.search(instruction)
        if m:
            return "launch_path", m.group(1)
    if re.search(r"(?i)Launch\s+\w+", instruction):
        return "launch_other", instruction[:120]
    return None, None


def check_path(instruction: str, apps: list[str]) -> tuple[str, str]:
    kind, val = extract_launch(instruction)
    if not kind:
        return "⚠️", "instruction 中未声明启动路径"
    if kind == "desktop_shortcut":
        app = apps[0] if apps else "?"
        std = STANDARD.get(app, [])
        std_s = std[0] if std else "(无标准)"
        return "❌", f"Desktop 快捷方式 vs 标准 `{std_s}`"
    if kind == "launch_other":
        return "⚠️", f"有 Launch 表述但未给出可比对路径: {val}"
    app = apps[0] if apps else ""
    std = STANDARD.get(app, [])
    if not std:
        return "⚠️", f"无标准对照表条目 (app={app}), 实际 `{val}`"
    if path_matches(val or "", std):
        return "✅", ""
    return "❌", f"实际 `{val}` vs 标准 `{std[0]}`"


def instruction_bans_code(instruction: str, apps: list[str], tier: str) -> bool:
    if CODE_BAN_NEGATIVE.search(instruction):
        return False
    if CODE_BAN_POSITIVE.search(instruction):
        return True
    # task-c abaqus/ansys often say "via CLI" — that's NOT a ban
    if tier == "task-c" and apps and apps[0] in CLI_EXPECTED_APPS:
        if re.search(r"(?i)via the command line|CLI|Python scripting", instruction):
            if not re.search(r"(?i)do not.*python", instruction):
                return False
    return False


def eval_checks_script(eval_path: Path | None, eval_src: str) -> bool:
    if eval_src and EVAL_SCRIPT_CHECK.search(eval_src):
        return True
    return False


def check_feasibility(
    instruction: str, apps: list[str], eval_path: Path | None, eval_src: str, tier: str
) -> tuple[str, str]:
    if not apps:
        return "⚠️", "related_apps 为空"
    app = apps[0]
    if app not in STANDARD and tier in ("task-c", "task-v"):
        pass  # still may be ok
    if eval_src and PLACEHOLDER_EVAL.search(eval_src):
        if INSTRUCTION_RECREATE.search(instruction):
            return "❌", "instruction 要求复杂复现但 eval 为占位符 (1 polyline + 1 text)"
    # task-v GUI BIM — feasible if eval validates IFC etc.
    if tier == "task-v" and app in ("revit", "archicad", "openstudio", "bonsai"):
        if "init.ifc" in instruction or "IFC" in instruction:
            return "✅", ""
    if tier == "task-c" and app in CLI_EXPECTED_APPS:
        if re.search(r"(?i)(CLI|command line|scripting|FreeCADCmd|mged|foamRun|ccx)", instruction):
            return "✅", ""
    if tier == "task-c" and app in ("revit", "archicad", "solidworks", "autocad"):
        return "✅", ""
    if tier == "task-v" and app in ("blender", "freecad", "kicad", "eagle"):
        return "✅", ""
    if not eval_path or not eval_path.exists():
        return "⚠️", "缺少 eval.py"
    return "✅", ""


def iter_task_jsons():
    for p in sorted(TASK_ROOT.rglob("task-*.json")):
        if "ground_truth" in p.parts or "init_file" in p.parts:
            continue
        yield p


def main():
    rows: list[dict] = []
    fmt_errors: list[str] = []

    for jpath in iter_task_jsons():
        rel = jpath.relative_to(TASK_ROOT)
        tier = jpath.parts[-4] if len(jpath.parts) >= 4 else ""  # task-c / task-v
        try:
            obj = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception as e:
            fmt_errors.append(f"{rel}: {e}")
            continue

        tid = obj.get("id", jpath.stem)
        instruction = obj.get("instruction", "") or ""
        apps = obj.get("related_apps") or []
        app_s = ",".join(apps) if apps else "?"

        path_status, path_note = check_path(instruction, apps)
        feas_status, feas_note = check_feasibility(
            instruction, apps, jpath.parent / "eval.py", "", tier
        )
        eval_path = jpath.parent / "eval.py"
        eval_src = ""
        if eval_path.exists():
            try:
                eval_src = eval_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
        if feas_note == "缺少 eval.py" or (feas_status == "✅" and eval_src):
            feas_status, feas_note = check_feasibility(
                instruction, apps, eval_path, eval_src, tier
            )

        banned = instruction_bans_code(instruction, apps, tier)
        if banned:
            has_check = eval_checks_script(eval_path, eval_src)
            if has_check:
                ban_status = "✅"
                ban_eval = "有"
            else:
                ban_status = "❌"
                ban_eval = "无"
            ban_inst = "已禁止"
        else:
            ban_status = "⚪"
            ban_eval = "—"
            ban_inst = "未禁止"

        note = "; ".join(x for x in [path_note, feas_note] if x)
        rows.append({
            "id": tid,
            "rel": str(rel).replace("\\", "/"),
            "app": app_s,
            "path": path_status,
            "feas": feas_status,
            "ban_inst": ban_inst,
            "ban_eval": ban_eval,
            "ban_check": ban_status,
            "note": note,
        })

    def cnt(key, val):
        return sum(1 for r in rows if r[key] == val)

    problems = [
        r for r in rows
        if r["path"] == "❌"
        or r["feas"] == "❌"
        or r["ban_check"] == "❌"
        or "格式" in r.get("note", "")
    ]
    path_warn = [r for r in rows if r["path"] == "⚠️"]
    feas_warn = [r for r in rows if r["feas"] == "⚠️"]

    lines = [
        "# Engiworld Task 配置 QA 审计报告",
        "",
        f"扫描根目录: `{TASK_ROOT}` | task JSON 数: **{len(rows)}** | 格式异常: **{len(fmt_errors)}**",
        "",
        "## 1. 总览统计",
        "",
        "| 指标 | 数量 |",
        "|---|---:|",
        f"| 总 task 数 | {len(rows)} |",
        f"| 路径对齐 ✅ | {cnt('path', '✅')} |",
        f"| 路径不对齐 ❌ | {cnt('path', '❌')} |",
        f"| 路径未声明 ⚠️ | {cnt('path', '⚠️')} |",
        f"| 软件能完成 ✅ | {cnt('feas', '✅')} |",
        f"| 软件不能完成 ❌ | {cnt('feas', '❌')} |",
        f"| 能完成歧义 ⚠️ | {cnt('feas', '⚠️')} |",
        f"| 禁码 + eval 一致 ✅ | {cnt('ban_check', '✅')} |",
        f"| 禁码但 eval 缺失 ❌ | {cnt('ban_check', '❌')} |",
        f"| instruction 未禁码 ⚪ | {cnt('ban_check', '⚪')} |",
        f"| 格式异常 JSON | {len(fmt_errors)} |",
        "",
        "## 2. 逐 task 明细（精简：仅路径❌/可行性❌/禁码❌/⚠️路径）",
        "",
        "| task id | 软件 | 路径 | 能否完成 | 禁码 | eval查禁码 | 备注 |",
        "|---|---|---|---|---|---|---|",
    ]

    detail_rows = [
        r for r in rows
        if r["path"] != "✅" or r["feas"] != "✅" or r["ban_check"] != "⚪"
    ]
    for r in detail_rows[:400]:
        note = (r["note"] or "")[:60]
        lines.append(
            f"| {r['id']} | {r['app']} | {r['path']} | {r['feas']} | {r['ban_inst']} | {r['ban_eval']} | {note} |"
        )
    if len(detail_rows) > 400:
        lines.append(f"| … | … | … | … | … | … | （另有 {len(detail_rows)-400} 条，见完整 CSV） |")

    lines.extend(["", "## 3. 问题清单", ""])

    # Group problems
    by_cat: dict[str, list] = {"路径不对齐": [], "软件不支持": [], "禁码eval缺失": [], "其他": []}
    for r in rows:
        if r["path"] == "❌":
            by_cat["路径不对齐"].append(r)
        if r["feas"] == "❌":
            by_cat["软件不支持"].append(r)
        if r["ban_check"] == "❌":
            by_cat["禁码eval缺失"].append(r)

    for cat, items in by_cat.items():
        if not items:
            continue
        lines.append(f"### {cat} ({len(items)})")
        lines.append("")
        for r in items[:25]:
            lines.append(f"- **{r['id']}** (`{r['rel']}`): {r['note'] or cat}")
        if len(items) > 25:
            lines.append(f"- … 另有 {len(items)-25} 项")
        lines.append("")

    if fmt_errors:
        lines.append("### 格式异常")
        for e in fmt_errors[:20]:
            lines.append(f"- {e}")
        lines.append("")

    lines.extend([
        "## 4. 共性问题与全局建议",
        "",
        "1. **Revit task-v (11–16) 等**：instruction 要求 Desktop 快捷方式启动，与标准 `Revit.exe` 路径不一致；建议在 instruction 末尾统一 `[Software] Launch ... Revit.exe` 或 eval 不依赖绝对路径。",
        "2. **大量 task 无 `[Software]` 启动路径**（路径 ⚠️）：Linux/CLI 类（blender、freecad、fenics）instruction 未写 Launch；若 VM 靠 snapshot 预装，可接受；否则补 `[Software]` 块。",
        "3. **GUI-only + eval**：Revit/Archicad/OpenStudio 等 task-v 已用 `GUI_BYPASS_*` 检测脚本绕过；禁码与 eval 一致。",
        "4. **task-c AutoCAD 等**：instruction 已对齐 `acad.exe`；eval 用 ezdxf 验几何（非验 AutoCAD 签名）— 未禁止写码的 task 不属此项缺陷。",
        "5. **占位 eval**：若 instruction 写 Recreate 复杂 DXF 而 eval 仅 1 polyline+1 text，应替换为真实几何校验或放宽 instruction。",
        "",
        "### 修复模板",
        "",
        "**instruction 补标准路径：**",
        "```",
        "[Software] Launch <App> with `C:\\\\...\\\\app.exe`.",
        "```",
        "",
        "**eval 补禁码检查（instruction 已 GUI-only 时）：**",
        "```python",
        "def _check_no_script_bypass(desktop: Path) -> bool:",
        "    # 检测 desktop 上除 eval.py 外的 .py/.ps1 及 shell history 中的 deliverable 生成命令",
        "    ...",
        "```",
        "",
    ])

    OUT.write_text("\n".join(lines), encoding="utf-8")

    # CSV for full detail
    csv_path = REPO / ".scripts" / "task_audit_detail.csv"
    import csv
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            w.writeheader()
            w.writerows(rows)

    print(f"tasks={len(rows)} path_ok={cnt('path','✅')} path_bad={cnt('path','❌')} "
          f"path_warn={cnt('path','⚠️')} feas_bad={cnt('feas','❌')} ban_miss={cnt('ban_check','❌')}")
    print(f"report: {OUT}")
    print(f"csv: {csv_path}")


if __name__ == "__main__":
    main()
