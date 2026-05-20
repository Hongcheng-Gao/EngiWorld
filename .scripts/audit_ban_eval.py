"""Audit: instruction bans scripting vs eval enforcement. Split task-c / task-v."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"
OUT = REPO / ".scripts" / "ban_eval_audit.md"

# --- Instruction: 明确禁止用脚本/代码完成（非「必须用 CLI」类表述）---
STRICT_BAN = re.compile(
    r"(?i)(?:"
    r"external\s+script\s+files\s+is\s+strictly\s+prohibited|"
    r"use\s+of\s+external\s+script\s+files\s+is\s+strictly\s+prohibited|"
    r"helper\s+script/code\s+that\s+directly\s+generates|"
    r"GUI-only\s+requirement|"
    r"must\s+use\s+the\s+gui\b|"
    r"do\s+not\s+open\s+(?:Command\s+Prompt|PowerShell|Terminal)|"
    r"do\s+not\s+write\s+any\s+script|"
    r"no\s+external\s+code|"
    r"禁止使用.*?(?:脚本|python)"
    r")"
)

# 「Do not use X GUI」= 要求 CLI，不算禁脚本
CLI_MANDATE_NOT_BAN = re.compile(
    r"(?i)do\s+not\s+use\s+(?:the\s+)?(?:\w+(?:\s+\w+)*\s+)?(?:GUI|graphical\s+user\s+interface)"
)

# --- Eval: 是否检测绕过（桌面脚本、GUI bypass 等）---
EVAL_CHECKS = [
    ("has_forbidden_py_file", re.compile(r"has_forbidden_py_file\s*\(")),
    ("GUI_BYPASS", re.compile(r"GUI_BYPASS|_desktop_script_artifacts|_history_contains_bypass")),
    ("check_script_generic", re.compile(
        r"(?i)(?:check_(?:no|forbidden|gui).*script|forbid.*(?:py|script)|"
        r"script_artifact|no_gui_bypass|detect.*bypass)"
    )),
    ("trajectory_bypass", re.compile(r"(?i)trajectory.*bypass|traj.*forbidden")),
    ("acadver", re.compile(r"ACADVER|acadver", re.I)),
]


def instruction_bans_scripting(inst: str) -> tuple[bool, str]:
    if CLI_MANDATE_NOT_BAN.search(inst):
        return False, ""
    m = STRICT_BAN.search(inst)
    if m:
        return True, m.group(0)[:80]
    return False, ""


def eval_has_script_check(src: str) -> tuple[bool, list[str]]:
    if not src.strip():
        return False, []
    hits = [name for name, rx in EVAL_CHECKS if rx.search(src)]
    return bool(hits), hits


def iter_tasks():
    for tier in ("task-c", "task-v"):
        root = TASK / tier
        if not root.is_dir():
            continue
        for app_dir in sorted(root.iterdir()):
            if not app_dir.is_dir():
                continue
            app = app_dir.name
            for task_dir in sorted(app_dir.iterdir()):
                if not task_dir.is_dir() or task_dir.name in ("ground_truth", "init_file"):
                    continue
                jsons = list(task_dir.glob("task-*.json"))
                if not jsons:
                    continue
                yield tier, app, task_dir, jsons[0]


def main() -> None:
    rows: list[dict] = []
    by_tier_app: dict[str, dict[str, list]] = defaultdict(
        lambda: {"banned": 0, "eval_ok": 0, "gap": [], "no_ban": 0}
    )

    for tier, app, task_dir, jpath in iter_tasks():
        obj = json.loads(jpath.read_text(encoding="utf-8"))
        inst = obj.get("instruction", "") or ""
        tid = obj.get("id", jpath.stem)
        eval_path = task_dir / "eval.py"
        eval_src = ""
        if eval_path.exists():
            eval_src = eval_path.read_text(encoding="utf-8", errors="replace")

        banned, ban_snip = instruction_bans_scripting(inst)
        has_check, check_hits = eval_has_script_check(eval_src)

        rel = f"{tier}/{app}/{task_dir.name}"
        key = f"{tier}/{app}"
        stats = by_tier_app[key]

        if not banned:
            stats["no_ban"] += 1
            continue

        stats["banned"] += 1
        if has_check:
            stats["eval_ok"] += 1
        else:
            stats["gap"].append(
                {"id": tid, "rel": rel, "ban_snip": ban_snip, "eval_note": "无禁脚本检测"}
            )

        rows.append(
            {
                "tier": tier,
                "app": app,
                "id": tid,
                "rel": rel,
                "banned": banned,
                "has_check": has_check,
                "check_hits": ",".join(check_hits) if check_hits else "",
                "ban_snip": ban_snip,
            }
        )

    lines = [
        "# 禁脚本 instruction vs eval 检测审计",
        "",
        "判定说明：",
        "- **instruction 禁脚本**：含 `external script files is strictly prohibited`、`GUI-only`、`helper script` 等（不含「Do not use X GUI」——后者表示必须用 CLI）。",
        "- **eval 有检测**：`has_forbidden_py_file`、`GUI_BYPASS_*`、`_desktop_script_artifacts` 等。",
        "",
        "## 1. 按 tier + 软件汇总",
        "",
        "| tier | 软件 | 禁脚本题数 | eval 有检测 | **缺口（禁了但未检）** | 无禁脚本题数 |",
        "|---|---|---:|---:|---:|---:|",
    ]

    tier_totals = {"task-c": {"banned": 0, "ok": 0, "gap": 0, "no_ban": 0},
                   "task-v": {"banned": 0, "ok": 0, "gap": 0, "no_ban": 0}}

    for key in sorted(by_tier_app.keys()):
        s = by_tier_app[key]
        tier, app = key.split("/", 1)
        gap_n = len(s["gap"])
        lines.append(
            f"| {tier} | {app} | {s['banned']} | {s['eval_ok']} | **{gap_n}** | {s['no_ban']} |"
        )
        tier_totals[tier]["banned"] += s["banned"]
        tier_totals[tier]["ok"] += s["eval_ok"]
        tier_totals[tier]["gap"] += gap_n
        tier_totals[tier]["no_ban"] += s["no_ban"]

    lines.extend(
        [
            "",
            "## 2. tier 合计",
            "",
            "| tier | 禁脚本题数 | eval 有检测 | 缺口 | 无禁脚本题数 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for tier in ("task-c", "task-v"):
        t = tier_totals[tier]
        lines.append(
            f"| {tier} | {t['banned']} | {t['ok']} | **{t['gap']}** | {t['no_ban']} |"
        )

    lines.extend(["", "## 3. 缺口明细（instruction 禁脚本且 eval 未检测）", ""])

    for tier in ("task-c", "task-v"):
        gaps = [
            r for r in rows if r["tier"] == tier and r["banned"] and not r["has_check"]
        ]
        lines.append(f"### {tier}（共 {len(gaps)} 题）")
        lines.append("")
        if not gaps:
            lines.append("- 无")
            lines.append("")
            continue
        by_app_g: dict[str, list] = defaultdict(list)
        for r in gaps:
            by_app_g[r["app"]].append(r)
        for app in sorted(by_app_g.keys()):
            items = by_app_g[app]
            lines.append(f"#### {app}（{len(items)} 题）")
            lines.append("")
            for r in items:
                lines.append(
                    f"- `{r['id']}`（{r['rel']}）— 禁脚本依据: `{r['ban_snip']}`"
                )
            lines.append("")

    lines.extend(["", "## 4. 已有检测的软件（禁脚本且 eval 覆盖）", ""])
    for tier in ("task-c", "task-v"):
        ok_rows = [r for r in rows if r["tier"] == tier and r["banned"] and r["has_check"]]
        apps_ok = sorted({r["app"] for r in ok_rows})
        if apps_ok:
            parts = []
            for a in apps_ok:
                n = sum(1 for r in ok_rows if r["app"] == a)
                parts.append(f"{a}({n})")
            lines.append(f"- **{tier}**: {', '.join(parts)}")
        else:
            lines.append(f"- **{tier}**: 无")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8")[:2500])
    print(f"\n... full report: {OUT}")


if __name__ == "__main__":
    main()
