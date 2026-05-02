"""Append (or refresh) a CLI-only init `launch` step in each task-c task json.

The init step runs the corresponding software with a headless / CLI-only command
so license / activation issues surface during environment setup even on machines
without a graphical session. The runner already recognises the `launch` setup
type (the same one used in OSWorld and in our task-v jsons), so no schema change
is required.

The script is idempotent and self-replacing: if the file already contains a
launch step whose command matches either the current canonical command or any
previously-written command for that app (see PREVIOUS_LAUNCH_COMMANDS), the
script removes those stale entries and appends the current canonical one.

Usage:
    python add_init_launch.py [--dry-run] [--app APP] [--task TASK_DIR]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "task-c"

# Current canonical CLI-only init command per software.
# Must run successfully on a machine without any graphical display.
LAUNCH_COMMANDS: dict[str, list[str]] = {
    "abaqus": ["cmd", "/c", "abaqus information=version"],
    "altium-designer": [
        "cmd",
        "/c",
        r'if exist "C:\Program Files\Altium\AD26\X2.EXE" (echo OK) '
        r'else (echo MISSING & exit /b 1)',
    ],
    "ansys": [
        r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ansys.exe",
        "-b",
        "-i",
        "nul",
    ],
    "archicad": [
        "cmd",
        "/c",
        r'if exist "C:\Users\Administrator\Desktop\Archicad 29\Archicad Starter.exe" '
        r'(echo OK) else (echo MISSING & exit /b 1)',
    ],
    "autocad": [
        r"C:\Program Files\Autodesk\AutoCAD 2027\accoreconsole.exe",
        "/?",
    ],
    "bonsai": [
        "./blender-4.2.0-linux-x64/blender",
        "--background",
        "--python-expr",
        "import bonsai; print('OK')",
    ],
    "brl-cad": ["bash", "-lc", "echo q | mged -c 2>&1 | head -1"],
    "calculix": ["/usr/bin/ccx", "-v"],
    "eagle": [
        "bash",
        "-lc",
        "test -x /opt/eagle-7.7.0/bin/eagle && echo OK || echo MISSING",
    ],
    "fenics": [
        "bash",
        "-lc",
        "source activate fenicsx 2>/dev/null || conda activate fenicsx; "
        "python -c 'import dolfinx; print(dolfinx.__version__)'",
    ],
    "floris": [
        "python3",
        "-c",
        "from floris import FlorisModel; fm = FlorisModel('defaults'); "
        "fm.run(); print(fm.get_turbine_powers())",
    ],
    "freecad": ["freecadcmd", "--version"],
    "freecad-path": ["freecadcmd", "--version"],
    "fusion360": [
        "cmd",
        "/c",
        r'if exist "C:\Users\Administrator\AppData\Local\Autodesk\webdeploy'
        r'\production\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe" '
        r'(echo OK) else (echo MISSING & exit /b 1)',
    ],
    "kicad": ["kicad-cli", "--version"],
    "openfoam": [
        "bash",
        "-lc",
        "source /opt/openfoam9/etc/bashrc && simpleFoam -help",
    ],
    "openscad": ["openscad", "--version"],
    "openstudio": ["openstudio", "--version"],
    "ptc-creo": [
        "cmd",
        "/c",
        r'if exist "C:\Creo 12.4.0.0\Parametric\bin\parametric.exe" '
        r'(echo OK) else (echo MISSING & exit /b 1)',
    ],
    "revit": [
        "cmd",
        "/c",
        r'if exist "C:\Users\Administrator\Desktop\Revit 2027\Revit.exe" '
        r'(echo OK) else (echo MISSING & exit /b 1)',
    ],
    "sketchup": [
        "cmd",
        "/c",
        r'if exist "C:\Program Files\SketchUp\SketchUp 2026\SketchUp\SketchUp.exe" '
        r'(echo OK) else (echo MISSING & exit /b 1)',
    ],
}

# Previously-written commands per app. Any matching launch step in `config`
# will be removed before the canonical one is appended. Update this whenever
# LAUNCH_COMMANDS changes so reruns clean up stale entries instead of stacking.
PREVIOUS_LAUNCH_COMMANDS: dict[str, list[list[str]]] = {
    "abaqus": [[r"C:\SIMULIA\Commands\abq_cae_open.bat"]],
    "altium-designer": [[r"C:\Program Files\Altium\AD26\X2.exe"]],
    "ansys": [[
        r"C:\Program Files\ANSYS Inc\ANSYS Student\v261\Framework\bin"
        r"\Win64\RunWB2.exe"
    ]],
    "archicad": [[
        r"C:\Users\Administrator\Desktop\Archicad 29\Archicad Starter.exe"
    ]],
    "autocad": [[r"C:\Program Files\Autodesk\AutoCAD 2027\acad.exe"]],
    "bonsai": [["./blender-4.2.0-linux-x64/blender"]],
    "brl-cad": [["mged"]],
    "calculix": [["ccx", "-v"]],
    "eagle": [["/opt/eagle-7.7.0/bin/eagle"]],
    "fenics": [["python3", "-c", "import dolfinx; print(dolfinx.__version__)"]],
    "floris": [["python3", "-c", "import floris; print(floris.__version__)"]],
    "freecad": [["freecad"]],
    "freecad-path": [["freecad"]],
    "fusion360": [[
        r"C:\Users\Administrator\AppData\Local\Autodesk\webdeploy\production"
        r"\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe"
    ]],
    "kicad": [["kicad"]],
    "openfoam": [[
        "bash",
        "-lc",
        "source /opt/openfoam9/etc/bashrc && simpleFoam -help",
    ]],
    "openscad": [["openscad"]],
    "openstudio": [["openstudio", "--version"]],
    "ptc-creo": [[
        r"C:\Program Files\PTC\Creo 12.0.0.0\Parametric\bin\parametric.exe"
    ]],
    "revit": [[r"C:\Users\Administrator\Desktop\Revit 2027\Revit.exe"]],
    "sketchup": [[
        r"C:\Program Files\SketchUp\SketchUp 2026\SketchUp\SketchUp.exe"
    ]],
}


def _step_command(step: Any) -> list[str] | None:
    if not isinstance(step, dict) or step.get("type") != "launch":
        return None
    params = step.get("parameters") or {}
    cmd = params.get("command")
    return cmd if isinstance(cmd, list) else None


def _is_managed_launch(step: Any, app: str) -> bool:
    """True if `step` is a launch step we know how to manage (current or stale)."""
    cmd = _step_command(step)
    if cmd is None:
        return False
    if cmd == LAUNCH_COMMANDS[app]:
        return True
    return cmd in PREVIOUS_LAUNCH_COMMANDS.get(app, [])


def patch_file(path: Path, app: str, dry_run: bool) -> str:
    target_cmd = LAUNCH_COMMANDS[app]
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    config = data.get("config")
    if not isinstance(config, list):
        return f"skip (no config array): {path}"

    cleaned = [step for step in config if not _is_managed_launch(step, app)]
    removed = len(config) - len(cleaned)

    launch_step = {
        "type": "launch",
        "parameters": {"command": target_cmd},
    }
    cleaned.append(launch_step)
    data["config"] = cleaned

    new_text = json.dumps(data, ensure_ascii=False, indent=2)
    if raw.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"

    if new_text == raw:
        return f"skip (already up to date): {path}"

    if dry_run:
        return (
            f"would update {path} (removed {removed} stale launch step(s), "
            f"appended canonical command)"
        )

    path.write_text(new_text, encoding="utf-8", newline="\n")
    return f"patched: {path} (removed {removed} stale)"


def iter_task_jsons(app_filter: str | None, task_filter: str | None):
    for app_dir in sorted(ROOT.iterdir()):
        if not app_dir.is_dir():
            continue
        app = app_dir.name
        if app not in LAUNCH_COMMANDS:
            print(
                f"WARN: no launch command configured for app {app!r}, skipping",
                file=sys.stderr,
            )
            continue
        if app_filter and app_filter != app:
            continue
        for task_dir in sorted(app_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            if task_filter and task_filter != task_dir.name:
                continue
            json_path = task_dir / f"{task_dir.name}.json"
            if not json_path.exists():
                continue
            yield app, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="do not write files, just print what would change")
    parser.add_argument("--app", help="only process this software dir, e.g. ansys")
    parser.add_argument("--task", help="only process this task dir, e.g. task-04")
    args = parser.parse_args()

    if not ROOT.exists():
        print(f"ERROR: {ROOT} does not exist", file=sys.stderr)
        return 2

    total = 0
    patched = 0
    skipped = 0
    for app, json_path in iter_task_jsons(args.app, args.task):
        total += 1
        try:
            status = patch_file(json_path, app, args.dry_run)
        except json.JSONDecodeError as e:
            print(f"ERROR: failed to parse {json_path}: {e}", file=sys.stderr)
            continue
        if status.startswith("skip"):
            skipped += 1
        else:
            patched += 1
        print(status)

    mode = "dry-run" if args.dry_run else "write"
    print(f"\n[{mode}] total={total} patched={patched} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
