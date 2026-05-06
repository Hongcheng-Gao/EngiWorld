"""Read-only scan of all tasks. Produces ONE markdown report with two sections:

  1) GUI/CLI phrases present in `instruction` (problem 2 from user)
  2) Instruction <-> eval mismatches detected by heuristics (problem 1)

DOES NOT MODIFY ANY FILES. Just writes the report to .scripts/scan_report.md.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"D:\research\project-engiworld\Engiworld\task")
REPORT = Path(r"D:\research\project-engiworld\Engiworld\.scripts\scan_report.md")

# ---- GUI/CLI phrases to flag --------------------------------------------
# (regex, label) — case-insensitive
GUI_PHRASES: list[tuple[str, str]] = [
    (r"\bUse Abaqus/CAE via the Command Line Interface \(CLI\) to\b", "abaqus CLI prefix"),
    (r"\bUse Abaqus/CAE through the graphical user interface to\b", "abaqus GUI prefix"),
    (r"\bUse the Abaqus/CAE GUI to\b", "abaqus GUI prefix"),
    (r"\bUse Abaqus/CAE in GUI mode to\b", "abaqus GUI mode"),
    (r"\bUse ANSYS via the Command Line Interface \(CLI\) to\b", "ansys CLI prefix"),
    (r"\bUse the ANSYS .* GUI\b", "ansys GUI prefix"),
    (r"\bUse AutoCAD command line, Core Console, or an AutoCAD automation script\.?", "autocad CLI prefix"),
    (r"\bUse FreeCADCmd\b", "FreeCADCmd"),
    (r"\bUse the FreeCAD GUI\b", "freecad GUI"),
    (r"\bin the FreeCAD GUI\b", "freecad GUI"),
    (r"\bin the OpenSCAD GUI editor\b", "openscad GUI editor"),
    (r"\bin the LibreCAD graphical interface\b", "librecad GUI"),
    (r"\bUsing SketchUp's GUI\b", "sketchup GUI"),
    (r"\bUse the command-line evaluation workflow\b", "creo CLI workflow"),
    (r"\bIn a command-line environment\b", "openscad CLI prefix"),
    (r"\bComplete the following from the command line\b", "fenics/floris CLI prefix"),
    (r"\bDo not use any FEniCS GUI\b", "negative GUI mention"),
    (r"\bDo not use FLORIS visualization GUI\b", "negative GUI mention"),
    (r"\bDo not use the ParaView GUI\b", "negative GUI mention"),
    (r"\bDo not use any .* GUI\b", "negative GUI mention"),
    (r"\bvia the Command Line Interface\b", "CLI mention"),
    (r"\bUse a Fusion 360 API script or command-line automation workflow\b", "fusion360 API/CLI"),
    (r"\bUsing the CLI workflow\b", "CLI workflow"),
    (r"\(key GUI operations\)", "GUI annotation"),
    (r"\bNote that .* the GUI\b", "GUI hint"),
    (r"\bPress F\d\b", "GUI keyboard shortcut"),
    (r"File\s*->\s*Export", "GUI menu path"),
    (r"\bFollow Me tool\b", "sketchup GUI tool"),
    (r"\bMacro Editor\b", "GUI editor mention"),
    (r"\bSketcher workbench\b", "freecad workbench"),
    (r"\bPath/CAM Workbench\b", "freecad workbench"),
    (r"\bPart workbench\b", "freecad workbench"),
    (r"\bScript Editor\b", "creo/eagle editor"),
    (r"\bCore Console\b", "autocad core console"),
    (r"\bnoGUI=\b", "abaqus noGUI flag"),
    (r"\bheadless\b", "headless mention"),
    (r"^look at\b", "task-v 'look at' lead"),
]

# ---- Mismatch detection patterns ----------------------------------------

PLACEHOLDER_DXF = re.compile(
    r"DXF_SPECS\s*=\s*\[\s*\{\s*['\"]path['\"]\s*:\s*['\"]autocad_result\.dxf['\"]\s*,"
    r"\s*['\"]summary['\"]\s*:\s*\{\s*['\"]counts['\"]\s*:\s*"
    r"\{\s*['\"]LWPOLYLINE['\"]\s*:\s*1\s*,\s*['\"]TEXT['\"]\s*:\s*1\s*\}",
    re.DOTALL,
)

# eval expects vertices=8, faces=12 (i.e. one cube/box) but instruction
# describes a complex multi-solid part.
TRIVIAL_STL = re.compile(
    r"['\"]vertices['\"]\s*:\s*8\s*,\s*['\"]faces['\"]\s*:\s*12\b",
)

# eval STEP solid_count vs instruction
STEP_BBOX_RE = re.compile(
    r"STEP_SPECS\s*=\s*\[\s*\{[^}]*?['\"]bbox['\"]\s*:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]",
    re.DOTALL,
)
STL_BBOX_RE = re.compile(
    r"STL_SPECS\s*=\s*\[\s*\{[^}]*?['\"]bbox['\"]\s*:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]",
    re.DOTALL,
)
MESH_BBOX_RE = re.compile(
    r"MESH_SPECS\s*=\s*\[\s*\{[^}]*?['\"]bbox['\"]\s*:\s*\[\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\]",
    re.DOTALL,
)


def find_gui_phrases(instruction: str) -> list[str]:
    """Return list of unique labels that match in instruction."""
    hits: list[str] = []
    seen: set[str] = set()
    for pat, label in GUI_PHRASES:
        if re.search(pat, instruction, flags=re.IGNORECASE | re.MULTILINE):
            if label not in seen:
                seen.add(label)
                hits.append(label)
    return hits


def extract_eval_bbox(eval_src: str) -> tuple[float, float, float] | None:
    for rx in (STEP_BBOX_RE, STL_BBOX_RE, MESH_BBOX_RE):
        m = rx.search(eval_src)
        if m:
            return (float(m.group(1)), float(m.group(2)), float(m.group(3)))
    return None


# Numbers explicitly mentioned in instruction (mm-context heuristic).
NUM_DIM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*mm\b")


def detect_mismatch(task_dir: Path, instruction: str) -> list[str]:
    eval_path = task_dir / "eval.py"
    if not eval_path.exists():
        return []
    eval_src = eval_path.read_text(encoding="utf-8", errors="ignore")
    issues: list[str] = []

    # Heuristic 1: autocad-style placeholder eval.
    if PLACEHOLDER_DXF.search(eval_src):
        text_match = re.search(
            r"['\"]texts['\"]\s*:\s*\[\s*['\"](TASK[^'\"]*)['\"]\s*\]",
            eval_src,
        )
        text_required = text_match.group(1) if text_match else "(unknown)"
        if "outlines, holes, slots" in instruction or "Recreate" in instruction:
            issues.append(
                f"PLACEHOLDER_EVAL: eval only checks 1 LWPOLYLINE + 1 TEXT='{text_required}' "
                f"on layer 0, but instruction asks to recreate a complex 2D drawing"
            )

    # Heuristic 2: STL eval expects a cube (8 verts / 12 faces) but instruction
    # mentions multiple solids / parts / holes.
    if TRIVIAL_STL.search(eval_src):
        words = re.findall(
            r"\b(rib|ribs|cap|housing|tool|boss|hole|holes|cylinder|fillet|chamfer|"
            r"slots|bracket|cover|slider|pin|spring|bearing|gear)\b",
            instruction,
            flags=re.IGNORECASE,
        )
        if len(words) >= 2:
            issues.append(
                f"TRIVIAL_STL_EVAL: eval expects vertices=8, faces=12 (a single box), "
                f"but instruction mentions multiple parts/features: {sorted(set(w.lower() for w in words))}"
            )

    # Heuristic 3 (DIM_MISMATCH) was removed — too noisy. Internal feature
    # dimensions (e.g. "ribs 5 mm thick") legitimately don't appear in the
    # part's overall bbox. Need a smarter semantic check; not in this pass.

    # Heuristic 4: instruction output filename vs eval file path. Skip when
    # the eval file is a base64-encoded BUNDLE (some apps like sketchup,
    # zbrush ship their real eval logic compressed).
    is_bundled = "BUNDLE = {" in eval_src
    if not is_bundled:
        inst_files = set(re.findall(
            r"\b([A-Za-z0-9_\-]+\.(?:step|stp|stl|dxf|dwg|ifc|osm|cae|odb|nc|gcode|pdf|obj|dae|brd|sch))\b",
            instruction,
        ))
        eval_files = set(re.findall(
            r"['\"]([A-Za-z0-9_\-/\\:.]+\.(?:step|stp|stl|dxf|dwg|ifc|osm|cae|odb|nc|gcode|pdf|obj|dae|brd|sch))['\"]",
            eval_src,
        ))
        eval_basenames = {Path(p).name for p in eval_files}
        out_inst = {f for f in inst_files
                    if any(k in f.lower() for k in ("result", "output", "out_"))}
        if out_inst and not (out_inst & eval_basenames):
            if not any(any(f in eb for eb in eval_basenames) for f in out_inst):
                issues.append(
                    f"OUTPUT_FILE_MISMATCH: instruction names output {sorted(out_inst)} "
                    f"but eval references {sorted(eval_basenames) or '(none)'}"
                )

    return issues


def iter_tasks():
    for top in ("task-c", "task-v"):
        top_dir = ROOT / top
        if not top_dir.exists():
            continue
        for app_dir in sorted(top_dir.iterdir()):
            if not app_dir.is_dir():
                continue
            for task_dir in sorted(app_dir.iterdir()):
                if not task_dir.is_dir():
                    continue
                if task_dir.name in ("ground_truth", "init_file"):
                    continue
                jsons = list(task_dir.glob("task-*.json"))
                if not jsons:
                    continue
                yield top, app_dir.name, task_dir, jsons[0]


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    gui_rows: list[dict] = []
    mm_rows: list[dict] = []
    all_count = 0
    eval_present = 0
    no_eval = []

    for top, app, task_dir, jpath in iter_tasks():
        try:
            obj = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception as exc:
            mm_rows.append({
                "rel": f"{top}/{app}/{task_dir.name}",
                "issues": [f"JSON_PARSE_ERROR: {exc}"],
                "instruction_preview": "",
            })
            continue
        instruction = obj.get("instruction", "")
        rel = f"{top}/{app}/{task_dir.name}"
        all_count += 1

        # GUI/CLI scan
        labels = find_gui_phrases(instruction)
        if labels:
            gui_rows.append({
                "rel": rel,
                "labels": labels,
                "preview": instruction.splitlines()[0][:200] if instruction else "",
            })

        # mismatch scan
        if (task_dir / "eval.py").exists():
            eval_present += 1
            issues = detect_mismatch(task_dir, instruction)
            if issues:
                mm_rows.append({
                    "rel": rel,
                    "issues": issues,
                    "instruction_preview": instruction[:240].replace("\n", " / "),
                })
        else:
            no_eval.append(rel)

    # ---- Render report ----
    out: list[str] = []
    out.append("# Engiworld task scan report (READ-ONLY, no files modified)\n")
    out.append("")
    out.append("## Summary\n")
    out.append(f"- total tasks scanned: **{all_count}**")
    out.append(f"- with eval.py: **{eval_present}**")
    out.append(f"- without eval.py: **{len(no_eval)}**")
    out.append(f"- instructions with GUI/CLI phrases: **{len(gui_rows)}**")
    out.append(f"- instructions with eval mismatch: **{len(mm_rows)}**")
    out.append("")

    # GUI section grouped by app
    out.append("## A. GUI/CLI phrases in instruction (problem 2)\n")
    out.append("These instructions mention the way to invoke the tool (GUI/CLI/Workbench/etc.) "
               "and should be cleaned. Grouped by app.\n")
    by_app: dict[str, list[dict]] = {}
    for row in gui_rows:
        parts = row["rel"].split("/", 2)
        key = f"{parts[0]}/{parts[1]}"
        by_app.setdefault(key, []).append(row)
    for key in sorted(by_app):
        rows = by_app[key]
        out.append(f"### {key} ({len(rows)} tasks)\n")
        for row in rows:
            out.append(f"- `{row['rel']}` — {', '.join(row['labels'])}")
            out.append(f"  - first line: {row['preview']}")
        out.append("")

    # Mismatch section
    out.append("## B. Instruction <-> eval mismatches (problem 1)\n")
    out.append("Heuristic flags. Each task may have one or more issues. "
               "Categories:\n")
    out.append("- `PLACEHOLDER_EVAL`: eval is the autocad 'one polyline + one TASK NN text' stub")
    out.append("- `TRIVIAL_STL_EVAL`: eval requires vertices=8, faces=12 (a cube), but instruction describes multiple parts/features")
    out.append("- `DIM_MISMATCH`: instruction mentions mm dimensions that do not appear in eval bbox")
    out.append("- `OUTPUT_FILE_MISMATCH`: instruction's output filename is not referenced in eval")
    out.append("- `JSON_PARSE_ERROR`: malformed task json")
    out.append("")
    by_app_mm: dict[str, list[dict]] = {}
    for row in mm_rows:
        parts = row["rel"].split("/", 2)
        key = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else row["rel"]
        by_app_mm.setdefault(key, []).append(row)
    for key in sorted(by_app_mm):
        rows = by_app_mm[key]
        out.append(f"### {key} ({len(rows)} tasks)\n")
        for row in rows:
            out.append(f"- **{row['rel']}**")
            for issue in row["issues"]:
                out.append(f"  - {issue}")
            if row.get("instruction_preview"):
                out.append(f"  - instruction (first 240 chars): {row['instruction_preview']}")
        out.append("")

    if no_eval:
        out.append("## C. Tasks without eval.py (informational)\n")
        for r in no_eval:
            out.append(f"- {r}")
        out.append("")

    REPORT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {REPORT}")
    print(f"tasks={all_count}  with-eval={eval_present}  "
          f"GUI/CLI={len(gui_rows)}  mismatch={len(mm_rows)}  no-eval={len(no_eval)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
