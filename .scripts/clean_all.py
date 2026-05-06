"""Strip GUI/CLI execution-mode phrases from `instruction` of every task-*.json
under `task/`.

Principle (per user):
  - KEEP the application name (Abaqus, AutoCAD, FreeCAD, ANSYS, PTC Creo, ...)
    and feature names (Path/CAM modules, Sketcher workbench, DynaMesh, ...).
  - ONLY remove HOW it is invoked:
      GUI / graphical user interface / GUI editor /
      CLI / command line / Command Line Interface (CLI) /
      Core Console / Macro Editor / Script Editor /
      Workbench (when used as "X Workbench GUI") /
      keyboard shortcuts (Press F5, Press F6) /
      menu paths (File -> Export -> ...) /
      "automation script" / "API script" / "command-line automation workflow"
      lead-ins.

Default mode: DRY-RUN (writes diffs to .scripts/full_diff.md, no JSON
modifications). Pass --apply to write the cleaned JSON back.
"""
from __future__ import annotations
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\research\project-engiworld\Engiworld\task")
REPORT_DIR = Path(r"D:\research\project-engiworld\Engiworld\.scripts")
DIFF_FILE = REPORT_DIR / "full_diff.md"

# ----------------------------------------------------------------------------
# Rules — applied in order. Tuple is (pattern, replacement). The pattern flags
# default to no-flags; multi-line / case-insensitive needs to be expressed in
# the pattern itself with `(?m)` / `(?i)`.
# ----------------------------------------------------------------------------
RULES: list[tuple[str, str]] = [
    # ---------- Abaqus -----------------------------------------------------
    # "Use Abaqus/CAE via the Command Line Interface (CLI) to" -> "Use Abaqus/CAE to"
    (r"Use Abaqus/CAE via the Command Line Interface \(CLI\) to ",
     "Use Abaqus/CAE to "),
    (r"Use Abaqus/CAE through the graphical user interface to ",
     "Use Abaqus/CAE to "),
    (r"Use the Abaqus/CAE GUI to ",
     "Use Abaqus/CAE to "),
    (r"Use Abaqus/CAE in GUI mode to ",
     "Use Abaqus/CAE to "),
    # "(key GUI operations)" - parenthetical annotation
    (r" \(key GUI operations\)", ""),
    # "noGUI=" flag mention (rare)
    (r"\bnoGUI=\S*\s*", ""),

    # ---------- ANSYS ------------------------------------------------------
    (r"Use ANSYS Mechanical APDL via the Command Line Interface \(CLI\) to ",
     "Use ANSYS Mechanical APDL to "),
    (r"Use ANSYS Workbench via the Command Line Interface \(CLI\) to ",
     "Use ANSYS Workbench to "),
    (r"Use ANSYS Fluent via the Command Line Interface \(CLI\) to ",
     "Use ANSYS Fluent to "),
    (r"Use ANSYS via the Command Line Interface \(CLI\) to ",
     "Use ANSYS to "),
    (r"Use the ANSYS Mechanical APDL GUI to ",
     "Use ANSYS Mechanical APDL to "),
    (r"Use the ANSYS Workbench GUI to ",
     "Use ANSYS Workbench to "),
    (r"Use the ANSYS Fluent GUI to ",
     "Use ANSYS Fluent to "),

    # ---------- AutoCAD ----------------------------------------------------
    # task-c: "Use AutoCAD command line, Core Console, or an AutoCAD
    # automation script. Open only the DXF file(s)..."
    # -> "Use AutoCAD. Open only the DXF file(s)..."
    (r"Use AutoCAD command line, Core Console, or an AutoCAD automation script\.",
     "Use AutoCAD."),

    # ---------- FreeCAD task-c (FreeCADCmd / API workflow) -----------------
    (r"Use FreeCADCmd or a FreeCAD Python automation workflow with the Path/CAM modules\.",
     "Use FreeCAD with the Path/CAM modules."),
    (r"Use FreeCADCmd or a FreeCAD Python automation workflow\.",
     "Use FreeCAD."),
    # ---------- FreeCAD task-v "Using FreeCAD CLI/API," variants -----------
    (r"Using FreeCAD CLI/API, ", "Using FreeCAD, "),
    (r"Using FreeCAD CLI, ", "Using FreeCAD, "),
    (r"Using the FreeCAD command-line API, ", "Using FreeCAD, "),
    (r"Using the FreeCAD command line, ", "Using FreeCAD, "),
    (r"Using the FreeCAD command-line, ", "Using FreeCAD, "),
    (r" in the FreeCAD GUI\b", " in FreeCAD"),

    # ---------- Fusion 360 -------------------------------------------------
    (r"Use a Fusion 360 API script or command-line automation workflow for Fusion-compatible CAM generation\.",
     "Use Fusion 360 for CAM generation."),
    (r"Use a Fusion 360 API script or command-line automation workflow\.",
     "Use Fusion 360."),
    (r"Using the CLI workflow, ", ""),

    # ---------- PTC Creo ---------------------------------------------------
    (r"Use the command-line evaluation workflow to call PTC Creo and ",
     "Use PTC Creo to "),
    # Generic fallback: drop the lead-in. The first-letter capitalizer below
    # restores sentence case when the next verb is lowercase.
    (r"Use the command-line evaluation workflow to ", ""),

    # ---------- OpenSCAD task-v (GUI editor / F5 / F6 / File menu) ---------
    (r" in the OpenSCAD GUI editor\b", " in OpenSCAD"),
    (r"Press F5 to preview and confirm there is no syntax error, then press F6 to fully render\.[ \t]*",
     ""),
    (r"Press F5 to preview[^.]*\.[ \t]*", ""),
    (r"Press F6 to fully render\.[ \t]*", ""),
    (r"Use File\s*->\s*Export\s*->\s*Export as STL and save exactly ",
     "Save as STL named "),
    (r"Use File\s*->\s*Export\s*->\s*Export as STL ",
     "Save as STL "),
    (r"Export a DXF from the GUI and save it as ", "Save as DXF named "),

    # ---------- OpenSCAD task-c (CLI lead-ins) -----------------------------
    (r"In a command-line environment, operate on ", "Operate on "),
    (r" from the command line\.[ \t]*", ". "),
    (r" from the command line:[ \t]*", ":"),
    (r"(?m)^From the command line, ", ""),

    # ---------- "Complete the following / X from the command line:" -------
    # (calculix / fenics / floris / openfoam / others)
    (r"Complete the following from the command line:[ \t]*",
     "Complete the following:"),
    # generic verb form: "Complete a 2D ... analysis from the command line:"
    (r"\bfrom the command line:[ \t]*", ":"),

    # ---------- "Do not use ... GUI" prohibitions --------------------------
    # When it's a standalone bulleted line, drop the entire line.
    (r"(?m)^[ \t]*(?:\d+\.[ \t]*)?Do not use (?:any |the )?[A-Za-z][A-Za-z0-9 ]*? GUI[^.\n]*\.[ \t]*\n?",
     ""),
    # Inline mop-up.
    (r"[ \t]*Do not use (?:any |the )?[A-Za-z][A-Za-z0-9 ]*? GUI[^.\n]*\.[ \t]*",
     " "),

    # ---------- LibreCAD / EAGLE / Altium / SketchUp / ZBrush "in the X GUI/editor" --
    (r" in the LibreCAD graphical interface\b", " in LibreCAD"),
    (r" in the EAGLE board editor\b", " in EAGLE"),
    (r" in EAGLE's schematic editor\b", " in EAGLE"),
    (r" in EAGLE's [A-Za-z][A-Za-z ]*? editor\b", " in EAGLE"),
    (r" in Altium Designer's Schematic Template Editor\b", " in Altium Designer"),

    # ---------- SketchUp ---------------------------------------------------
    (r"Using SketchUp's GUI, ", "Using SketchUp, "),

    # ---------- ZBrush -----------------------------------------------------
    # "Load this OBJ into ZBrush, ..." stays — that mentions ZBrush as the
    # app, not GUI. Leave alone.

    # ---------- generic mop-up: residual " via the Command Line Interface (CLI)" --
    (r" via the Command Line Interface \(CLI\)", ""),

    # ---------- whitespace cleanup: collapse internal multi-spaces only ---
    (r"(?<=\S)  +(?=\S)", " "),
]

COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(p), r) for p, r in RULES
]


# Abbreviations after which we must NOT capitalize the next word.
_ABBREV_RE = re.compile(
    r"\b(?:vs|etc|cf|viz|Mr|Mrs|Dr|Jr|Sr|fig|eq|vol|no|ch|sec|i\.e|e\.g|approx|et al)\.\s+",
    re.IGNORECASE,
)
# Sentence boundary candidate: punct + space(s) + lowercase letter, not after
# a digit or another period (so "2. result" / "v1. foo" / "i.e." stay).
_RECASE_CANDIDATE = re.compile(r"(?<![\d.])([.!?]) +([a-z])")


def _do_recase(text: str) -> str:
    skip = set()
    for m in _ABBREV_RE.finditer(text):
        skip.add(m.end())
    out_chars: list[str] = list(text)
    for m in _RECASE_CANDIDATE.finditer(text):
        if m.start(2) in skip:
            continue
        out_chars[m.start(2)] = m.group(2).upper()
    return "".join(out_chars)


def _first_alpha_index(s: str) -> int:
    for i, ch in enumerate(s):
        if ch.isalpha():
            return i
    return -1


def clean(text: str) -> str:
    out = text
    for rx, repl in COMPILED:
        out = rx.sub(repl, out)
    out = _do_recase(out)
    # If we deleted a leading clause and the cleaned text now starts with a
    # lowercase verb (e.g. "open ..." after dropping "Use the command-line
    # evaluation workflow to "), restore the capitalization. Only do this when
    # the *original* started uppercase, to preserve intentional lowercase
    # starts like "look at X.dxf".
    i_orig = _first_alpha_index(text)
    i_new = _first_alpha_index(out)
    if (
        i_orig >= 0
        and i_new >= 0
        and text[i_orig].isupper()
        and out[i_new].islower()
        and not (i_new + 1 < len(out) and out[i_new + 1].isupper())
    ):
        out = out[:i_new] + out[i_new].upper() + out[i_new + 1:]
    return out


def iter_tasks():
    for top in ("task-c", "task-v"):
        top_dir = ROOT / top
        if not top_dir.exists():
            continue
        for app_dir in sorted(top_dir.iterdir()):
            if not app_dir.is_dir():
                continue
            for task_dir in sorted(app_dir.iterdir()):
                if not task_dir.is_dir() or task_dir.name in ("ground_truth", "init_file"):
                    continue
                jsons = list(task_dir.glob("task-*.json"))
                if not jsons:
                    continue
                yield top, app_dir.name, task_dir, jsons[0]


def main(apply: bool) -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    diff_lines: list[str] = ["# Full instruction cleanup diff\n"]
    changed = 0
    unchanged = 0
    by_app_changed: dict[str, int] = {}

    for top, app, task_dir, jpath in iter_tasks():
        try:
            obj = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception as exc:
            diff_lines.append(f"\n## {top}/{app}/{task_dir.name}: JSON read error: {exc}\n")
            continue
        original = obj.get("instruction", "")
        cleaned = clean(original)
        rel = f"{top}/{app}/{task_dir.name}"

        if cleaned != original:
            changed += 1
            by_app_changed[f"{top}/{app}"] = by_app_changed.get(f"{top}/{app}", 0) + 1
            diff = list(difflib.unified_diff(
                original.splitlines(),
                cleaned.splitlines(),
                fromfile="before",
                tofile="after",
                lineterm="",
                n=1,
            ))
            diff_lines.append(f"\n## {rel}\n")
            diff_lines.append("```diff")
            diff_lines.extend(diff)
            diff_lines.append("```")
            if apply:
                obj["instruction"] = cleaned
                jpath.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        else:
            unchanged += 1

    diff_lines.insert(
        1,
        f"\n_changed={changed}, unchanged={unchanged}, "
        f"apply={'YES' if apply else 'NO (dry-run)'}_\n\n"
        f"### Per-app counts\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in sorted(by_app_changed.items()))
        + "\n",
    )

    DIFF_FILE.write_text("\n".join(diff_lines), encoding="utf-8")
    print(f"changed={changed}, unchanged={unchanged}; "
          f"apply={'YES' if apply else 'NO (dry-run)'}")
    print(f"diff: {DIFF_FILE}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Write cleaned JSON back to disk.")
    args = parser.parse_args()
    sys.exit(main(args.apply))
