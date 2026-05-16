#!/usr/bin/env python3
"""Batch fix task JSON + eval.py; writes tools/TASK_DATASET_CHANGELOG.md"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK_ROOT = REPO / "task"

SNAPSHOT_BY_FOLDER: dict[str, str] = {
    "blender": "Blender-4.2.3",
    "bonsai": "Bonsai-0.8.5",
    "openstudio": "OpenStudio-1.11.0",
    "librecad": "LibreCAD2.2.0.2",
    "freecad": "FreeCAD0.21.2",
    "freecad-path": "freecad-path0.21.2",
    "solvespace": "solvespace3.1ds1-3.1build2",
    "openscad": "OpenSCAD2021.01",
    "brl-cad": "BRL-CAD7.32.2",
    "openfoam": "OpenFOAM11",
    "calculix": "CalculiX-2.21",
    "fenics": "FEniCS",
    "floris": "FLORIS4.6.4",
    "kicad": "kicad-10.0.2",
    "eagle": "eagle-7.7.0",
    "autocad": "AutoCAD2024",
    "revit": "Revit2025",
    "archicad": "ArchiCAD-27",
    "ansys": "ANSYS-2024R1",
    "abaqus": "Abaqus-2023",
    "altium-designer": "altium-designer",
    "zbrush": "ZBrush-2024",
    "solidworks": "SolidWorks-2025",
    "sketchup": "SketchUp2026",
    "cadence-orcad": "OrCAD24.1",
    "solidcam": "SolidCAM-2025",
    "nx-cam": "NX-CAM",
    "openfast": "openfast5",
}

ORCAD_CAPTURE_WIN = r"C:\Cadence\SPB_24.1\tools\bin\capture.exe"


def _folder_key(path: Path) -> str | None:
    parts = path.parts
    try:
        i = parts.index("task")
    except ValueError:
        return None
    if i + 2 < len(parts):
        return parts[i + 2].lower()
    return None


def _dedupe_desktop_path(s: str) -> str:
    pairs = [
        ("C:\\Users\\User\\Desktop\\C:\\Users\\User\\Desktop\\", "C:\\Users\\User\\Desktop\\"),
        (
            "C:\\Users\\Administrator\\Desktop\\C:\\Users\\Administrator\\Desktop\\",
            "C:\\Users\\Administrator\\Desktop\\",
        ),
        (
            "C:\\\\Users\\\\User\\\\Desktop\\\\C:\\\\Users\\\\User\\\\Desktop\\\\",
            "C:\\\\Users\\\\User\\\\Desktop\\\\",
        ),
        (
            "C:\\\\Users\\\\Administrator\\\\Desktop\\\\C:\\\\Users\\\\Administrator\\\\Desktop\\\\",
            "C:\\\\Users\\\\Administrator\\\\Desktop\\\\",
        ),
    ]
    for a, b in pairs:
        while a in s:
            s = s.replace(a, b)
    return s


def _normalize_windows_paths_in_string(s: str) -> str:
    s = s.replace("users/administer", "Users/Administrator")
    s = s.replace("Users/administer", "Users/Administrator")
    s = s.replace("users/user", "Users/User")
    s = s.replace("users/User", "Users/User")
    return s


def _capitalize_sentences(instr: str) -> str:
    if not instr:
        return instr
    t = re.sub(r"\n{2,}", " ", instr)
    t = re.sub(r"\n(?![\n#])", " ", t)
    t = re.sub(r"[ \t]+", " ", t).strip()

    def cap_after(m: re.Match[str]) -> str:
        sep, sp, ch = m.group(1), m.group(2), m.group(3)
        return sep + sp + ch.upper()

    t = re.sub(r"([.!?])(\s+)([a-z])", cap_after, t)
    if t and t[0].isalpha() and t[0].islower():
        t = t[0].upper() + t[1:]
    return t


def _strip_version_mentions(instr: str) -> str:
    repl = [
        (r"\bBlender\s+[\d.]+\b", "Blender"),
        (r"\bAutoCAD\s+\d{4}\b", "AutoCAD"),
        (r"\bRevit\s+\d{4}\b", "Revit"),
        (r"\bOrCAD\s+X?\s*[\d.]+\b", "OrCAD"),
        (r"\bOpenStudio\s+[\d.]+\b", "OpenStudio"),
        (r"\bFreeCAD\s+[\d.]+\b", "FreeCAD"),
        (r"\bSketchUp\s+\d{4}\b", "SketchUp"),
        (r"\bpemnstudi[\d.]+\b", "PEMStudio"),
        (r"\bPEMStudio\s*[\d.]+\b", "PEMStudio"),
        (r"\bFusion\s+360\s+\d{4}\b", "Fusion 360"),
    ]
    for pat, rep in repl:
        instr = re.sub(pat, rep, instr, flags=re.I)
    return instr


def _fix_expected_rules(data: dict) -> bool:
    ev = data.get("evaluator")
    if not isinstance(ev, dict):
        return False
    exp_block = ev.get("expected")
    if not isinstance(exp_block, dict):
        return False
    rules = exp_block.get("rules")
    if not isinstance(rules, dict):
        return False
    exp = rules.get("expected")
    if not isinstance(exp, str):
        return False
    new = re.sub(r"(?<![A-Za-z])true(?![A-Za-z])", "True", exp)
    new = re.sub(r"(?<![A-Za-z])false(?![A-Za-z])", "False", new)
    if new != exp:
        rules["expected"] = new
        return True
    return False


def _fix_blender_eval_command(data: dict, path: Path) -> bool:
    apps = [a.lower() for a in (data.get("related_apps") or [])]
    if "blender" not in apps:
        return False
    ev = data.get("evaluator")
    if not isinstance(ev, dict):
        return False
    res = ev.get("result")
    if not isinstance(res, dict) or res.get("type") != "vm_command_line":
        return False
    cmd = res.get("command")
    if not isinstance(cmd, str):
        return False
    if "blender" in cmd.lower() and "--background" in cmd and "--python" in cmd:
        return False
    m = re.search(r"(?i)python\s+([\"']?)([^\s\"']+eval\.py)\1?", cmd)
    if m:
        script = m.group(2)
        res["command"] = f'blender --background --python "{script}"'
        return True
    return False


def _set_snapshot(data: dict, folder_key: str | None) -> bool:
    if not folder_key:
        return False
    want = SNAPSHOT_BY_FOLDER.get(folder_key)
    if not want:
        return False
    if (data.get("snapshot") or "") != want:
        data["snapshot"] = want
        return True
    return False


def _fill_orcad_launch_if_empty(data: dict, fk: str | None, path: Path) -> bool:
    if fk != "cadence-orcad" or "task-v" not in path.parts:
        return False
    changed = False
    for block in data.get("config") or []:
        if block.get("type") != "launch":
            continue
        params = block.get("parameters") or {}
        cmd = params.get("command")
        if cmd == [] or cmd is None:
            params["command"] = [ORCAD_CAPTURE_WIN]
            block["parameters"] = params
            changed = True
    return changed


def _strip_solidworks_solidcam_open(instr: str, fk: str | None) -> str:
    if fk == "solidworks":
        instr = re.sub(
            r"^Open\s+C:\\Users\\User\\Desktop\\([^\\\s]+\.(?:step|STEP|SLDPRT|SLDASM|sldprt|sldasm))\s+in\s+SolidWorks\.\s*",
            r"The starter file \1 is already open. ",
            instr,
            flags=re.I,
        )
        instr = re.sub(
            r"^Open\s+C:\\Users\\Administrator\\Desktop\\([^\\\s]+\.(?:step|STEP|SLDPRT|SLDASM|sldprt|sldasm))\s+in\s+SolidWorks\.\s*",
            r"The starter file \1 is already open. ",
            instr,
            flags=re.I,
        )
        instr = re.sub(
            r"Using SolidWorks command-line automation,\s*open\s+",
            "Using SolidWorks command-line automation, use input file ",
            instr,
            flags=re.I,
        )
    elif fk == "solidcam":
        instr = re.sub(
            r"^Open or import the initial file\(s\) from the Desktop:\s*C:\\Users\\User\\Desktop\\([^\\\s]+\.step)\.\s*",
            r"The starter part \1 is already loaded. ",
            instr,
            flags=re.I,
        )
        instr = re.sub(
            r"Import\s+C:\\Users\\User\\Desktop\\([^\\\s]+\.step)\s+and\s+",
            r"Using that part, ",
            instr,
            flags=re.I,
        )
    return instr


def _special_instruction_fixes(instr: str, rel_posix: str) -> str:
    if rel_posix.endswith("task-v/blender/task-01/task-01.json"):
        instr = instr.replace("(brick.x + gap) \\ 2", "(brick.x + gap) / 2")
        instr = instr.replace("8-vertex\\6-face", "8-vertex/6-face")
    if rel_posix.endswith("task-v/blender/task-32/task-32.json"):
        instr = instr.replace("writing BOTH files to ``.", "writing both OBJ and MTL files to the current working directory.")
        instr = instr.replace("writing BOTH files to ``", "writing both OBJ and MTL files to the current working directory")
    if rel_posix.endswith("task-v/cadence-orcad/task-32/task-32.json"):
        instr = (
            "Look at CUSTOM.OLB in OrCAD Capture Part Editor. "
            "Create a new package named `QUAD_OPAMP` in that library and set `Multiple-Part Package Type` to `Heterogeneous`. "
            "Pin graphics are optional and may be omitted. "
            "Save the library so the Desktop deliverable remains `CUSTOM.OLB`."
        )
    if rel_posix.endswith("task-c/cadence-orcad/task-27/task-27.json"):
        instr = instr.replace(
            "`C:\\\\Users\\\\User\\\\Desktop\\\\nc_param.txt`, Run",
            "`C:\\\\Users\\\\User\\\\Desktop\\\\nc_param.txt`. Run",
        )
    return instr


def process_json(path: Path, changelog: list[str]) -> bool:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        changelog.append(f"SKIP invalid JSON {path}: {e}")
        return False
    orig = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    bits: list[str] = []
    fk = _folder_key(path)
    rel = str(path.relative_to(REPO)).replace("\\", "/")

    if _set_snapshot(data, fk):
        bits.append("snapshot")

    if _fix_expected_rules(data):
        bits.append("expected rules true/false")

    if _fix_blender_eval_command(data, path):
        bits.append("blender eval command")

    if _fill_orcad_launch_if_empty(data, fk, path):
        bits.append("orcad launch command")

    instr = data.get("instruction")
    if isinstance(instr, str):
        ni = instr
        ni = _special_instruction_fixes(ni, rel)
        ni = _strip_solidworks_solidcam_open(ni, fk)
        ni = _dedupe_desktop_path(ni)
        ni = _normalize_windows_paths_in_string(ni)
        ni = _strip_version_mentions(ni)
        ni = _capitalize_sentences(ni)
        if ni != instr:
            data["instruction"] = ni
            bits.append("instruction")

    new_raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if new_raw != orig:
        path.write_text(new_raw, encoding="utf-8")
        changelog.append(f"{path.relative_to(REPO)}: {', '.join(bits)}")
        return True
    return False


def fix_eval_py_prints(changelog: list[str]) -> None:
    for ep in TASK_ROOT.rglob("eval.py"):
        txt = ep.read_text(encoding="utf-8")
        new = txt
        new = re.sub(
            r'print\("True"\s+if',
            'print("true" if',
            new,
        )
        new = re.sub(
            r'else\s+"False"\)',
            'else "false")',
            new,
        )
        if new != txt:
            ep.write_text(new, encoding="utf-8")
            changelog.append(f"eval.py print true/false: {ep.relative_to(REPO)}")


def delete_generate_scripts(changelog: list[str]) -> None:
    for p in TASK_ROOT.rglob("generate.py"):
        p.unlink()
        changelog.append(f"DELETED {p.relative_to(REPO)}")


def audit_numbering(changelog: list[str]) -> None:
    import os

    for base in ("task-v", "task-c"):
        b = TASK_ROOT / base
        if not b.exists():
            continue
        for sw in sorted(b.iterdir()):
            if not sw.is_dir():
                continue
            nums: list[int] = []
            for name in os.listdir(sw):
                m = re.match(r"task-(\d+)$", name)
                if m and (sw / name).is_dir():
                    nums.append(int(m.group(1)))
            nums.sort()
            if not nums:
                continue
            missing = [i for i in range(1, max(nums)) if i not in nums]
            if missing:
                changelog.append(
                    f"NUM_GAP {sw.relative_to(TASK_ROOT)}: missing {missing[:40]}{'...' if len(missing) > 40 else ''}"
                )


def main() -> None:
    changelog: list[str] = []
    for jf in sorted(TASK_ROOT.rglob("task-*.json")):
        if jf.suffix == ".json" and jf.name.startswith("task-"):
            process_json(jf, changelog)
    fix_eval_py_prints(changelog)
    delete_generate_scripts(changelog)
    audit_numbering(changelog)
    out = REPO / "tools" / "TASK_DATASET_CHANGELOG.md"
    out.write_text(
        "# Task dataset batch fixes\n\n" + "\n".join(f"- {line}" for line in changelog),
        encoding="utf-8",
    )
    print(f"Wrote {out} with {len(changelog)} lines")


if __name__ == "__main__":
    main()
