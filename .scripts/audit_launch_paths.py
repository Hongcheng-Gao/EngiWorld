"""Audit launch config vs instruction paths; fix abaqus/ansys; check JSON/eval integrity."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"
REPORT = REPO / ".scripts" / "launch_path_audit_report.md"

ABAQUS_LAUNCH_BAT = (
    r"C:\SIMULIA\EstProducts\2023\win_b64\resources\install\cmdDirFeature\launcher.bat"
)
ABAQUS_LAUNCH_CMD = [ABAQUS_LAUNCH_BAT.replace("\\", "\\\\"), "cae"]

ANSYS_RUNWB2 = r"C:\Program Files\ANSYS Inc\v241\Framework\bin\Win64\runwb2.exe"
ANSYS_APDL = r"C:\Program Files\ANSYS Inc\v241\v241\ansys\bin\Win64\ANSYS241.exe"
ANSYS_FLUENT = r"C:\Program Files\ANSYS Inc\v241\fluent\ntbin\win64\fluent.exe"

OLD_ABAQUS = r"C:\SIMULIA\CAE\2025LE\win_b64\resources\install\le\launcher.bat"
OLD_ANSYS261 = r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe"
OLD_FLUENT261 = r"C:\Program Files\ANSYS Inc\v261\fluent\ntbin\win64\fluent.exe"

SOFTWARE_RE = re.compile(r"\[Software\][^\`]*\`([^\`]+)\`", re.IGNORECASE)


def norm_path(p: str) -> str:
    return p.replace("/", "\\").lower().rstrip("\\")


def extract_software(inst: str) -> str | None:
    m = SOFTWARE_RE.search(inst)
    return m.group(1).strip() if m else None


def get_launch(obj: dict) -> list[str] | None:
    for c in obj.get("config", []):
        if c.get("type") == "launch":
            return c.get("parameters", {}).get("command")
    return None


def ansys_launch_for_instruction(inst: str) -> list[str]:
    low = inst.lower()
    if "fluent" in low[:200]:
        return [ANSYS_FLUENT.replace("\\", "\\\\"), "-g"]
    if "workbench" in low[:200]:
        return [ANSYS_RUNWB2.replace("\\", "\\\\")]
    # APDL / generic ANSYS GUI
    cmd = [ANSYS_APDL.replace("\\", "\\\\"), "-g"]
    if "task-01" in low or "np" in low:
        pass
    return cmd


def set_launch(obj: dict, command: list[str]) -> None:
    cfg = obj.setdefault("config", [])
    for i, c in enumerate(cfg):
        if c.get("type") == "launch":
            c["parameters"]["command"] = command
            return
    upload_idx = next(
        (i for i, c in enumerate(cfg) if c.get("type") == "upload_file"), len(cfg)
    )
    launch_block = {
        "type": "launch",
        "parameters": {"command": command},
    }
    cfg.insert(upload_idx + 1, launch_block)


def check_eval_py(path: Path) -> list[str]:
    issues = []
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return [f"read error: {e}"]
    if not src.strip():
        return ["empty file"]
    try:
        ast.parse(src)
    except SyntaxError as e:
        issues.append(f"syntax error: {e}")
    if "def evaluate(" not in src and "def main(" not in src:
        # some evals use if __name__ only
        if "__main__" not in src and "evaluate" not in src:
            issues.append("missing evaluate()/main()")
    if src.rstrip().endswith("(") or "def reaction_fy_on_z" in src and "return" not in src.split("def reaction_fy_on_z")[-1][:200]:
        tail = src[-300:]
        if "def reaction_fy_on_z" in tail and "return fy" not in tail and "allsel(mapdl)" in tail[-80:]:
            issues.append("likely truncated (reaction_fy_on_z incomplete)")
    return issues


def main(fix: bool = True) -> None:
    lines: list[str] = ["# Launch 路径审计报告\n"]
    path_rows: list[dict] = []
    fixes: list[str] = []
    json_errors: list[str] = []
    eval_issues: list[str] = []

    for top in ("task-c", "task-v"):
        top_dir = TASK / top
        if not top_dir.is_dir():
            continue
        for app_dir in sorted(top_dir.iterdir()):
            if not app_dir.is_dir():
                continue
            app = app_dir.name
            for task_dir in sorted(app_dir.iterdir()):
                if not task_dir.is_dir() or task_dir.name in ("ground_truth", "init_file"):
                    continue
                jsons = list(task_dir.glob("task-*.json"))
                if not jsons:
                    continue
                jpath = jsons[0]
                try:
                    obj = json.loads(jpath.read_text(encoding="utf-8"))
                except Exception as e:
                    json_errors.append(f"{jpath.relative_to(REPO)}: {e}")
                    continue

                inst = obj.get("instruction", "")
                sw = extract_software(inst)
                launch = get_launch(obj)
                rel = f"{top}/{app}/{task_dir.name}"

                eval_path = task_dir / "eval.py"
                if eval_path.exists():
                    ev = check_eval_py(eval_path)
                    if ev:
                        eval_issues.append(f"**{rel}**: " + "; ".join(ev))

                if app == "abaqus" and fix:
                    old_launch = launch
                    if launch != ABAQUS_LAUNCH_CMD:
                        set_launch(obj, ABAQUS_LAUNCH_CMD)
                        fixes.append(f"{rel}: launch {old_launch} -> {ABAQUS_LAUNCH_CMD}")
                    if top == "task-c" and not launch:
                        set_launch(obj, ABAQUS_LAUNCH_CMD)
                        fixes.append(f"{rel}: added launch config")
                    if fix:
                        jpath.write_text(
                            json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )

                elif app == "ansys" and fix:
                    new_cmd = ansys_launch_for_instruction(inst)
                    if "Workbench" in inst and ANSYS_RUNWB2.replace("\\", "\\\\") not in str(launch):
                        new_cmd = [ANSYS_RUNWB2.replace("\\", "\\\\")]
                    elif "Fluent" in inst[:120]:
                        new_cmd = [ANSYS_FLUENT.replace("\\", "\\\\"), "-g"]
                    else:
                        new_cmd = [ANSYS_APDL.replace("\\", "\\\\"), "-g"]
                    # task-01 had -np 2
                    if task_dir.name == "task-01" and top == "task-v":
                        new_cmd = [ANSYS_APDL.replace("\\", "\\\\"), "-g", "-np", "2"]
                    old_launch = launch
                    if launch != new_cmd:
                        if launch:
                            set_launch(obj, new_cmd)
                        else:
                            set_launch(obj, new_cmd)
                        fixes.append(f"{rel}: launch updated")
                    if top == "task-c" and not get_launch(obj):
                        set_launch(obj, new_cmd)
                        fixes.append(f"{rel}: added launch config")
                    jpath.write_text(
                        json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )

                # alignment record
                launch_exe = launch[0] if launch else None
                aligned = None
                if sw and launch_exe:
                    aligned = norm_path(sw.split()[0]) in norm_path(launch_exe) or norm_path(launch_exe) in norm_path(sw)
                elif not sw and not launch:
                    aligned = "both_missing"
                elif not sw and launch:
                    aligned = "instruction_missing"
                elif sw and not launch:
                    aligned = "launch_missing"

                path_rows.append(
                    {
                        "rel": rel,
                        "app": app,
                        "top": top,
                        "software": sw,
                        "launch": launch,
                        "aligned": aligned,
                    }
                )

    # Per-app summary for launch-bearing apps
    lines.append("## 1. 标准路径（用户指定）\n")
    lines.append(f"- **Abaqus**: `{ABAQUS_LAUNCH_BAT}` + 参数 `cae`\n")
    lines.append(f"- **ANSYS Workbench**: `{ANSYS_RUNWB2}`\n")
    lines.append(f"- **ANSYS APDL**（非 Fluent/Workbench 的 v 题 launch 推断）: `{ANSYS_APDL}`\n")
    lines.append(f"- **ANSYS Fluent**（v241 推断）: `{ANSYS_FLUENT}`\n")

    lines.append("\n## 2. Abaqus / ANSYS 修复记录\n")
    if fixes:
        for f in fixes:
            lines.append(f"- {f}\n")
    else:
        lines.append("- （无变更）\n")

    lines.append("\n## 3. 各软件 launch 与 instruction 对齐概览\n")
    by_app: dict[str, list] = {}
    for r in path_rows:
        by_app.setdefault(f"{r['top']}/{r['app']}", []).append(r)

    for key in sorted(by_app.keys()):
        rows = by_app[key]
        has_launch = sum(1 for r in rows if r["launch"])
        has_sw = sum(1 for r in rows if r["software"])
        mismatch = [
            r["rel"]
            for r in rows
            if r["launch"]
            and r["software"]
            and r["aligned"] is False
        ]
        missing_launch = [r["rel"] for r in rows if r["software"] and not r["launch"]]
        missing_sw = [r["rel"] for r in rows if r["launch"] and not r["software"]]
        lines.append(f"\n### {key}\n")
        lines.append(
            f"- 题数 {len(rows)}；config.launch {has_launch}；instruction [Software] {has_sw}\n"
        )
        if mismatch:
            lines.append(f"- **instruction 与 launch 路径不一致** ({len(mismatch)}): ")
            lines.append(", ".join(mismatch[:15]))
            if len(mismatch) > 15:
                lines.append(f" …等共 {len(mismatch)} 题")
            lines.append("\n")
        if missing_launch:
            lines.append(f"- 有 [Software] 无 launch ({len(missing_launch)})\n")
        if missing_sw:
            lines.append(f"- 有 launch 无 [Software] ({len(missing_sw)}): 例 {missing_sw[0]}\n")

    lines.append("\n## 4. JSON 解析错误\n")
    if json_errors:
        for e in json_errors:
            lines.append(f"- {e}\n")
    else:
        lines.append("- 无\n")

    lines.append("\n## 5. eval.py 完整性问题\n")
    if eval_issues:
        for e in eval_issues:
            lines.append(f"- {e}\n")
    else:
        lines.append("- 未发现明显截断/语法错误\n")

    REPORT.write_text("".join(lines), encoding="utf-8")
    print(f"Report: {REPORT}")
    print(f"fixes={len(fixes)}, json_errors={len(json_errors)}, eval_issues={len(eval_issues)}")


if __name__ == "__main__":
    main(fix=True)
