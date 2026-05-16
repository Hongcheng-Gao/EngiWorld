#!/usr/bin/env python3
"""Round-2: OS id suffix, True/False strings, Windows path typos, Pass conditions phrase,
instruction version scrub, recursive string walk. Writes tools/TASK_ROUND2_LOG.md."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "task"
LOG = REPO / "tools" / "TASK_ROUND2_LOG.md"

UBUNTU_FOLDERS = frozenset(
    {
        "openstudio",
        "librecad",
        "freecad",
        "solvespace",
        "freecad-path",
        "blender",
        "openfast",
        "openscad",
        "brl-cad",
        "openfoam",
        "calculix",
        "fenics",
        "floris",
        "kicad",
        "eagle",
        "bonsai",
    }
)
WINDOWS_FOLDERS = frozenset(
    {
        "autocad",
        "revit",
        "archicad",
        "ansys",
        "abaqus",
        "altium-designer",
        "zbrush",
        "solidworks",
        "sketchup",
        "cadence-orcad",
        "solidcam",
        "nx-cam",
    }
)


def folder_os(folder: str) -> str | None:
    f = folder.lower()
    if f in UBUNTU_FOLDERS:
        return "ubuntu"
    if f in WINDOWS_FOLDERS:
        return "windows"
    return None


def walk_strings(obj, fn):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = walk_strings(v, fn)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = walk_strings(v, fn)
        return obj
    if isinstance(obj, str):
        return fn(obj)
    return obj


def fix_windows_typos(s: str) -> str:
    s = s.replace("users/administer", "Users/Administrator")
    s = s.replace("Users/administer", "Users/Administrator")
    s = s.replace("users/Administer", "Users/Administrator")
    s = s.replace("users\\administer", "Users\\Administrator")
    s = s.replace("Users\\administer", "Users\\Administrator")
    s = re.sub(r"(?i)C:\\Users\\administer\\", r"C:\\Users\\Administrator\\", s)
    s = re.sub(r"(?i)C:\\\\Users\\\\administer\\\\", r"C:\\\\Users\\\\Administrator\\\\", s)
    return s


def strip_pass_conditions_phrase(s: str) -> str:
    s = re.sub(r"##+\s*Pass conditions\s*", "", s, flags=re.I)
    s = re.sub(r"\s+in the pass conditions\b", " ", s, flags=re.I)
    s = re.sub(r"\s+per the pass conditions\b", " ", s, flags=re.I)
    s = re.sub(r"\bPass conditions\b\s*:?", "", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s+\.", ".", s)
    return s.strip()


def scrub_instruction_versions(s: str) -> str:
    patterns = [
        (r"\bBlender\s+[\d.]+\b", "Blender"),
        (r"\bBonsai\s+[\d.]+\b", "Bonsai"),
        (r"\bAutoCAD\s+\d{4}\b", "AutoCAD"),
        (r"\bRevit\s+\d{4}\b", "Revit"),
        (r"\bOrCAD\s+X?\s*[\d.]+\b", "OrCAD"),
        (r"\bOpenStudio\s+[\d.]+\b", "OpenStudio"),
        (r"\bFreeCAD\s+[\d.]+\b", "FreeCAD"),
        (r"\bSketchUp\s+\d{4}\b", "SketchUp"),
        (r"\bFusion\s+360\s+[\d.]+\b", "Fusion 360"),
        (r"\bFusion\s+360\b(?!\s)", "Fusion 360"),
        (r"\bNX\s+\d{4}\b", "NX"),
        (r"\bSolidWorks\s+\d{4}\b", "SolidWorks"),
        (r"\bANSYS\s+\d{4}R\d\b", "ANSYS"),
        (r"\bZBrush\s+20\d{2}\b", "ZBrush"),
        (r"\bArchiCAD\s+\d{2}\b", "ArchiCAD"),
        (r"\bKiCad\s+[\d.]+\b", "KiCad"),
        (r"\bOpenFOAM\s+\d+\b", "OpenFOAM"),
        (r"\bOpenFAST\s+[\d.]+\b", "OpenFAST"),
        (r"\bAbaqus\s+20\d{2}\b", "Abaqus"),
        (r"\bAltium\s+Designer\s+[\w.]+\b", "Altium Designer"),
    ]
    for pat, rep in patterns:
        s = re.sub(pat, rep, s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s)
    return s


def fix_expected_tf(obj) -> None:
    if not isinstance(obj, dict):
        return
    ev = obj.get("evaluator")
    if not isinstance(ev, dict):
        return
    exp = ev.get("expected")
    if not isinstance(exp, dict):
        return
    rules = exp.get("rules")
    if not isinstance(rules, dict):
        return
    val = rules.get("expected")
    if isinstance(val, str):
        n = re.sub(r"(?<![A-Za-z])true(?![A-Za-z])", "True", val)
        n = re.sub(r"(?<![A-Za-z])false(?![A-Za-z])", "False", n)
        rules["expected"] = n


def body_os_signals(s: str) -> tuple[bool, bool]:
    has_linux = "/home/user" in s
    has_win = bool(re.search(r"C:\\\\Users", s)) or bool(re.search(r"C:\\Users", s))
    return has_linux, has_win


def rebuild_id(prefix: str, folder: str, task_num: str, os_suffix: str) -> str:
    return f"{prefix}-{folder}-task-{task_num}-{os_suffix}"


def process_task_json(path: Path, audit: list[str], log: list[str]) -> bool:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    parts = path.parts
    try:
        ti = parts.index("task")
    except ValueError:
        return False
    prefix = "c" if parts[ti + 1] == "task-c" else "v"
    folder = parts[ti + 2].lower()
    task_folder = parts[ti + 3]
    m = re.match(r"task-(\d+)$", task_folder)
    if not m:
        return False
    task_num = m.group(1)
    eos = folder_os(folder)
    if eos is None:
        audit.append(f"UNKNOWN_OS_FOLDER\t{path.relative_to(REPO)}\t{folder}")

    before = json.dumps(data, ensure_ascii=False)
    # Recursive Windows path typo fix on all strings
    data = walk_strings(data, fix_windows_typos)

    if "instruction" in data and isinstance(data["instruction"], str):
        ins = strip_pass_conditions_phrase(data["instruction"])
        ins = scrub_instruction_versions(ins)
        data["instruction"] = ins

    fix_expected_tf(data)

    if eos:
        old_id = str(data.get("id", ""))
        new_id = rebuild_id(prefix, folder, task_num, eos)
        if old_id != new_id:
            data["id"] = new_id
            log.append(f"id\t{path.relative_to(REPO)}\t{old_id}\t{new_id}")

    after = json.dumps(data, ensure_ascii=False)
    hl, hw = body_os_signals(after)
    if eos == "ubuntu" and hw and not hl:
        audit.append(f"PATH_OS_WARN\tubuntu_folder_but_windows_paths\t{path.relative_to(REPO)}")
    if eos == "windows" and hl and not hw:
        audit.append(f"PATH_OS_WARN\twindows_folder_but_linux_paths\t{path.relative_to(REPO)}")

    new_raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if new_raw != raw:
        path.write_text(new_raw, encoding="utf-8")
        return True
    return False


def fix_eval_py(path: Path, log: list[str]) -> None:
    t = path.read_text(encoding="utf-8")
    n = t
    n = re.sub(r'print\("true"', 'print("True"', n)
    n = re.sub(r'else\s+"false"\)', 'else "False")', n)
    if n != t:
        path.write_text(n, encoding="utf-8")
        log.append(f"eval.py\t{path.relative_to(REPO)}")


def main() -> None:
    log: list[str] = []
    audit: list[str] = []
    n = 0
    for jf in sorted(TASK.rglob("task-*.json")):
        if jf.name.startswith("task-") and jf.suffix == ".json":
            if process_task_json(jf, audit, log):
                n += 1
    for ep in TASK.rglob("eval.py"):
        fix_eval_py(ep, log)

    LOG.write_text(
        "# Round 2 normalization\n\n## id / eval changes\n"
        + "\n".join(log[:5000])
        + ("\n\n...(truncated)...\n" if len(log) > 5000 else "")
        + "\n\n## Path vs OS audit\n"
        + "\n".join(sorted(set(audit))),
        encoding="utf-8",
    )
    print(f"updated {n} json files, log lines {len(log)}, audit {len(set(audit))}")


if __name__ == "__main__":
    main()
